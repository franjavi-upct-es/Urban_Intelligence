# backend/src/monitoring/performance_monitor.py
# Urban Intelligence Framework v2.0.0
# Real-time performance monitoring and alerting system

"""
PerformanceMonitor module.

Tracks model prediction quality over time using a rolling window.
Fires alerts when metrics exceed configurable thresholds and exposes
a summary suitable for real-time WebSocket broadcast.

Monitored metrics:
- RMSE, MAE, R²  (when ground-truth actuals are available)
- Prediction latency (ms)
- Request rate (req/min)
- Error rate (HTTP 5xx)
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import structlog

from src.database import db

logger = structlog.get_logger(__name__)


@dataclass
class Alert:
    """An alert raised when a metric threshold is breached."""

    alert_id: str
    city_id: str
    metric: str
    current_value: float
    threshold: float
    severity: str  # "warning" | "critical"
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False


@dataclass
class MonitoringSnapshot:
    """A point-in-time summary of model health metrics."""

    city_id: str
    timestamp: datetime
    rmse: float | None
    mae: float | None
    r2: float | None
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    request_rate: float  # requests per minute in the last window
    error_rate: float  # fraction of failed predictions
    n_predictions: int
    active_alerts: list[Alert]


class PerformanceMonitor:
    """
    Rolling-window performance monitor for deployed models.

    Parameters
    ----------
    window_size : int
        Number of recent observations to keep in each rolling window.
    rmse_warning_threshold : float
        Triggers a WARNING alert when RMSE exceeds this value.
    rmse_critical_threshold : float
        Triggers a CRITICAL alert when RMSE exceeds this value.
    latency_warning_ms : float
        Triggers a WARNING alert when p95 latency exceeds this value.
    """

    def __init__(
        self,
        city_id: str = "unknown",
        window_size: int = 1000,
        rmse_warning_threshold: float = 0.3,
        rmse_critical_threshold: float = 0.6,
        latency_warning_ms: float = 500.0,
    ) -> None:
        self.city_id = city_id
        self.window_size = window_size
        self.rmse_warning_threshold = rmse_warning_threshold
        self.rmse_critical_threshold = rmse_critical_threshold
        self.latency_warning_ms = latency_warning_ms

        # Rolling buffers
        self._predictions: deque[float] = deque(maxlen=window_size)
        self._actuals: deque[float] = deque(maxlen=window_size)
        self._latencies_ms: deque[float] = deque(maxlen=window_size)
        self._errors: deque[bool] = deque(maxlen=window_size)
        self._timestamps: deque[float] = deque(maxlen=window_size)

        self._active_alerts: dict[str, Alert] = {}

    # ── Recording ─────────────────────────────────────────────────────────

    def record_prediction(
        self,
        predicted: float,
        actual: float | None = None,
        latency_ms: float | None = None,
        is_error: bool = False,
    ) -> None:
        """
        Record a single prediction observation.

        Args:
            predicted: Model prediction value.
            actual: Ground-truth value (if available, e.g., after booking).
            latency_ms: Time taken to generate the prediction (ms).
            is_error: True if the prediction request resulted in an error.
        """
        self._timestamps.append(time.time())
        self._predictions.append(predicted)
        self._errors.append(is_error)

        if actual is not None:
            self._actuals.append(actual)

        if latency_ms is not None:
            self._latencies_ms.append(latency_ms)

        # Trigger alert checks every 50 new observations
        if len(self._predictions) % 50 == 0:
            self._check_alerts()

    # ── Snapshot ──────────────────────────────────────────────────────────

    def get_snapshot(self) -> MonitoringSnapshot:
        """Return a current-state snapshot of all monitored metrics."""
        preds = np.array(self._predictions)
        acts = np.array(self._actuals)
        lats = np.array(self._latencies_ms)

        rmse = mae = r2 = None
        if len(acts) > 0 and len(acts) == len(preds):
            errors = preds[-len(acts) :] - acts
            rmse = float(np.sqrt(np.mean(errors**2)))
            mae = float(np.mean(np.abs(errors)))
            ss_res = np.sum(errors**2)
            ss_tot = np.sum((acts - acts.mean()) ** 2) or 1.0
            r2 = float(1 - ss_res / ss_tot)

        avg_latency = float(lats.mean()) if len(lats) > 0 else None
        p95_latency = float(np.percentile(lats, 95)) if len(lats) > 0 else None

        # Request rate: predictions in last 60 seconds
        now = time.time()
        recent = sum(1 for t in self._timestamps if now - t <= 60)
        request_rate = float(recent)

        error_rate = sum(self._errors) / max(len(self._errors), 1)

        return MonitoringSnapshot(
            city_id=self.city_id,
            timestamp=datetime.now(UTC),
            rmse=rmse,
            mae=mae,
            r2=r2,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            request_rate=request_rate,
            error_rate=error_rate,
            n_predictions=len(self._predictions),
            active_alerts=list(self._active_alerts.values()),
        )

    def get_active_alerts(self) -> list[Alert]:
        """Return all currently active (unresolved) alerts."""
        return [a for a in self._active_alerts.values() if not a.resolved]

    def resolve_alert(self, alert_id: str) -> None:
        """Mark an alert as resolved."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].resolved = True
            logger.info("Alert resolved", id=alert_id)

    # ── Alert checking ────────────────────────────────────────────────────

    def _check_alerts(self) -> None:
        """Evaluate thresholds and fire or resolve alerts."""
        preds = np.array(self._predictions)
        acts = np.array(self._actuals)

        if len(acts) > 0 and len(acts) == len(preds):
            errors = preds[-len(acts) :] - acts
            current_rmse = float(np.sqrt(np.mean(errors**2)))
            self._maybe_fire_alert(
                metric="rmse",
                value=current_rmse,
                warning_threshold=self.rmse_warning_threshold,
                critical_threshold=self.rmse_critical_threshold,
            )

        lats = np.array(self._latencies_ms)
        if len(lats) > 0:
            p95 = float(np.percentile(lats, 95))
            self._maybe_fire_alert(
                metric="p95_latency_ms",
                value=p95,
                warning_threshold=self.latency_warning_ms,
                critical_threshold=self.latency_warning_ms * 2,
            )

    def _maybe_fire_alert(
        self,
        metric: str,
        value: float,
        warning_threshold: float,
        critical_threshold: float,
    ) -> None:
        """Fire a new alert or update severity if thresholds are breached."""
        alert_key = f"{self.city_id}_{metric}"

        if value >= critical_threshold:
            severity = "critical"
        elif value >= warning_threshold:
            severity = "warning"
        else:
            # Threshold not breached — resolve existing alert if any
            if alert_key in self._active_alerts:
                self._active_alerts[alert_key].resolved = True
            return

        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            city_id=self.city_id,
            metric=metric,
            current_value=round(value, 4),
            threshold=critical_threshold
            if severity == "critical"
            else warning_threshold,
            severity=severity,
            message=f"{metric} {severity.upper()}: "
            f"{value:.4f} exceeds threshold",
        )
        self._active_alerts[alert_key] = alert

        # Persist to database
        import json

        db.execute(
            """
            INSERT INTO monitoring_events (
                event_id,
                event_type,
                city_id,
                severity,
                payload
            )
            VALUES (?, 'alert', ?, ?, ?)
            """,
            [
                alert.alert_id,
                self.city_id,
                severity,
                json.dumps(
                    {
                        "metric": metric,
                        "current_value": value,
                        "threshold": alert.threshold,
                        "message": alert.message,
                    }
                ),
            ],
        )
        logger.warning(
            "Alert fired",
            id=alert.alert_id,
            city=self.city_id,
            metric=metric,
            severity=severity,
            value=round(value, 4),
        )
