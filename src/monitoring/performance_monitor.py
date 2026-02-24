# src/monitoring/performance_monitor.py
# Urban Intelligence Framework - Model Performance Monitoring
# Tracks model performance metrics over time and detects degradation

"""
Performance monitoring for the Urban Intelligence Framework.

This module tracks model performance over time and provides:
    - Rolling metric computation
    - Performance degradation detection
    - Automated alerts when metrics fall below thresholds
    - Historical performance tracking
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceAlert:
    """Alert triggered by performance monitoring."""

    alert_id: str
    timestamp: datetime
    level: AlertLevel
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""

        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class PerformanceSnapshot:
    """Snapshot of model performance at a point in time."""

    timestamp: datetime
    metrics: dict[str, float]
    prediction_count: int
    error_count: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""

        return {
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "prediction_count": self.prediction_count,
            "error_count": self.error_count,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
        }


class PerformanceMonitor:
    """
    Montiors model performance and detects degradation.

    This class tracks predictions, computes performance metrics,
    and generates alerts when performance falls below thresholds.

    Example:
        >>> monitor = PerformanceMonitor(
        ...     mae_threshold=30.0,
        ...     latency_threshold_ms=100.0
        ... )
        >>> monitor.record_prediction(predicted=150.0, actual=140.0, latency_ms=25.0)
        >>> report = monitor.get_performance_report()
    """

    def __init__(
        self,
        mae_threshold: float = 25.0,
        rmse_threshold: float = 35.0,
        mape_threshold: float = 20.0,
        latency_threshold_ms: float = 100.0,
        error_rate_threshold: float = 5.0,
        window_size: int = 1000,
        alert_cooldown_minutes: int = 30,
    ) -> None:
        """
        Initialize the performance monitor.

        Args:
            mae_threshold: Maximum acceptable MAE
            rmse_threshold: Maximum acceptable RMSE
            mape_threshold: Maximum acceptable MAPE (percentage)
            latency_threshold_ms: Maximum acceptable P95 latency in ms
            error_rate_threshold: Maximum acceptable error rate (percentage)
            window_size: Number of predictions to keep in rolling window
            alert_cooldown_minutes: Minimum time between alerts of same type
        """
        self.mae_threshold = mae_threshold
        self.rmse_threshold = rmse_threshold
        self.mape_threshold = mape_threshold
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.window_size = window_size
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)

        # Rolling window storage
        self.predictions: list[float] = []
        self.actuals: list[float] = []
        self.latencies: list[float] = []
        self.timestamps: list[datetime] = []
        self.errors: list[bool] = []

        # Alert tracking
        self.alerts: list[PerformanceAlert] = []
        self.last_alert_time: dict[str, datetime] = {}

        # Historical snapshots
        self.snapshots: list[PerformanceSnapshot] = []

        # Counter for alert IDs
        self._alert_counter = 0

    def record_prediction(
        self,
        predicted: float,
        actual: float | None = None,
        latency_ms: float = 0.0,
        is_error: bool = False,
    ) -> list[PerformanceAlert]:
        """
        Record a prediction and check for alerts.

        Args:
            predicted: Predicted value
            actual: Actual value (None if not available yet)
            latency_ms: Prediction latency in milliseconds
            is_error: Whether the prediction resulted in an error

        Returns:
            List of alerts triggered by this prediction
        """
        now = datetime.now()

        self.predictions.append(predicted)
        self.actuals.append(actual if actual is not None else float("nan"))
        self.latencies.append(latency_ms)
        self.timestamps.append(now)
        self.errors.append(is_error)

        # Trim to window size
        if len(self.predictions) > self.window_size:
            self.predictions = self.predictions[-self.window_size :]
            self.actuals = self.actuals[-self.window_size :]
            self.latencies = self.latencies[-self.window_size :]
            self.timestamps = self.timestamps[-self.window_size :]
            self.errors = self.errors[-self.window_size :]

        # Check for alerts
        return self._check_alerts()

    def update_actual(self, predicted: float, actual: float) -> None:
        """
        Update the actual value for a prediction.

        Args:
            predicted: The predicted value to update
            actual: The actual observed value
        """
        # Find the prediction and update its actual value
        for i in range(len(self.predictions) - 1, -1, -1):
            if abs(self.predictions[i] - predicted) < 0.01:
                self.actuals[i] = actual
                break

    def compute_metrics(self) -> dict[str, float]:
        """
        Compute current performance metrics.

        Returns:
            Dictionary of metric names to values
        """
        metrics = {}

        # Get valid predictions (with actuals)
        valid_pairs = [
            (p, a) for p, a in zip(self.predictions, self.actuals, strict=False) if not np.isnan(a)
        ]

        if len(valid_pairs) > 0:
            preds = np.array([p for p, _ in valid_pairs])
            acts = np.array([a for _, a in valid_pairs])

            # MAE
            metrics["mae"] = float(np.mean(np.abs(preds - acts)))

            # RMSE
            metrics["rmse"] = float(np.sqrt(np.mean((preds - acts) ** 2)))

            # MAPE (avoid division by zero)
            non_zero_mask = acts != 0
            if np.any(non_zero_mask):
                mape = (
                    np.mean(
                        np.abs((acts[non_zero_mask] - preds[non_zero_mask]) / acts[non_zero_mask])
                    )
                    * 100
                )
                metrics["mape"] = float(mape)
            else:
                metrics["mae"] = 0.0

            # R²
            ss_res = np.sum((acts - preds) ** 2)
            ss_tot = np.sum((acts - np.mean(acts)) ** 2)
            metrics["r2"] = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        # Latency metrics
        if self.latencies:
            latencies = np.array(self.latencies)
            metrics["latency_mean_ms"] = float(np.mean(latencies))
            metrics["latency_p50_ms"] = float(np.percentile(latencies, 50))
            metrics["latency_p95_ms"] = float(np.percentile(latencies, 95))
            metrics["latency_p99_ms"] = float(np.percentile(latencies, 99))

        # Error rate
        if self.errors:
            metrics["error_rate"] = float(sum(self.errors) / len(self.errors) * 100)

        # Prediction volume
        metrics["prediction_count"] = len(self.predictions)
        metrics["valid_pairs_count"] = len(valid_pairs)

        return metrics

    def _check_alerts(self) -> list[PerformanceAlert]:
        """
        Check thresholds and generate alerts.

        Returns:
            List of new alerts
        """
        alerts = []
        metrics = self.compute_metrics()

        # Check MAE threshold
        if metrics.get("mae", 0) > self.mae_threshold:
            alert = self._create_alert_if_allowed(
                metric_name="mae",
                current_value=metrics["mae"],
                threshold_value=self.mae_threshold,
                level=AlertLevel.WARNING
                if metrics["mae"] < self.mae_threshold * 1.5
                else AlertLevel.ERROR,
                message=f"MAE ({metrics['mae']:.2f}) exceeds thresholds ({self.mae_threshold})",
            )
            if alert:
                alerts.append(alert)

        # Check RMSE threshold
        if metrics.get("rmse", 0) > self.rmse_threshold:
            alert = self._create_alert_if_allowed(
                metric_name="rmse",
                current_value=metrics["rmse"],
                threshold_value=self.rmse_threshold,
                level=AlertLevel.WARNING,
                message=f"RMSE ({metrics['rmse']:.2f}) exceeds thresholds ({self.rmse_threshold})",
            )
            if alert:
                alerts.append(alert)

        # Check MAPE threshold
        if metrics.get("mape", 0) > self.mape_threshold:
            alert = self._create_alert_if_allowed(
                metric_name="mape",
                current_value=metrics["mape"],
                threshold_value=self.mape_threshold,
                level=AlertLevel.WARNING,
                message="MAPE ({metrics['mape']:.2f}%) exceeds "
                f"thresholds ({self.mape_threshold}%)",
            )
            if alert:
                alerts.append(alert)

        # Check latency threshold
        latency_p95 = metrics.get("latency_p95_ms", 0)
        if latency_p95 > self.latency_threshold_ms:
            alert = self._create_alert_if_allowed(
                metric_name="latency_p95",
                current_value=latency_p95,
                threshold_value=self.latency_threshold_ms,
                level=AlertLevel.WARNING
                if latency_p95 < self.latency_threshold_ms * 2
                else AlertLevel.ERROR,
                message=f"P95 latency ({latency_p95:.2f}ms) exceeds "
                f"threshold ({self.latency_threshold_ms}ms)",
            )
            if alert:
                alerts.append(alert)

        # Check error rate threshold
        error_rate = metrics.get("error_rate", 0)
        if error_rate > self.error_rate_threshold:
            alert = self._create_alert_if_allowed(
                metric_name="error_rate",
                current_value=error_rate,
                threshold_value=self.error_rate_threshold,
                level=AlertLevel.ERROR
                if error_rate > self.error_rate_threshold * 2
                else AlertLevel.WARNING,
                message=(
                    f"Error rate ({error_rate:.2f}%) exceeds "
                    f"threshold ({self.error_rate_threshold}%)"
                ),
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _create_alert_if_allowed(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        level: AlertLevel,
        message: str,
    ) -> PerformanceAlert | None:
        """
        Create an alert if cooldown has passed.

        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            level: Alert severity level
            message: Alert message

        Returns:
            Alert if created, None if in cooldown
        """
        now = datetime.now()
        last_alert = self.last_alert_time.get(metric_name)

        if last_alert and (now - last_alert) < self.alert_cooldown:
            return None  # Still in cooldown

        self._alert_counter += 1
        alert = PerformanceAlert(
            alert_id=f"PERF-{self._alert_counter:.5d}",
            timestamp=now,
            level=level,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            message=message,
        )

        self.alerts.append(alert)
        self.last_alert_time[metric_name] = now

        logger.warning(f"Performance alert: {message}")

        return alert

    def create_snapshot(self) -> PerformanceSnapshot:
        """
        Create a performance snapshot.

        Returns:
            PerformanceSnapshot with current metrics
        """
        metrics = self.compute_metrics()

        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            metrics=metrics,
            prediction_count=len(self.predictions),
            error_count=sum(self.errors),
            latency_p50_ms=metrics.get("latency_p50_ms", 0.0),
            latency_p95_ms=metrics.get("latency_p95_ms", 0.0),
            latency_p99_ms=metrics.get("latency_p99_ms", 0.0),
        )

        self.snapshots.append(snapshot)
        return snapshot

    def get_performance_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive performance report.

        Returns:
            Dictionary with performance report data
        """
        metrics = self.compute_metrics()

        return {
            "report_time": datetime.now().isoformat(),
            "window_size": self.window_size,
            "prediction_count": len(self.predictions),
            "metrics": metrics,
            "thresholds": {
                "mae": self.mae_threshold,
                "rmse": self.rmse_threshold,
                "mape": self.mape_threshold,
                "latency_p95_ms": self.latency_threshold_ms,
                "error_rate": self.error_rate_threshold,
            },
            "threshold_status": {
                "mae": "OK" if metrics.get("mae", 0) <= self.mae_threshold else "EXCEEDED",
                "rmse": "OK" if metrics.get("rmse", 0) <= self.rmse_threshold else "EXCEEDED",
                "mape": "OK" if metrics.get("mape", 0) <= self.mape_threshold else "EXCEEDED",
                "latency": "OK"
                if metrics.get("latency_p95_ms", 0) <= self.latency_threshold_ms
                else "EXCEEDED",
                "error_rate": "OK"
                if metrics.get("error_rate", 0) <= self.error_rate_threshold
                else "EXCEEDED",
            },
            "recent_alerts": [a.to_dict() for a in self.alerts[-10:]],
            "total_alerts": len(self.alerts),
        }

    def save_report(self, path: Path) -> None:
        """
        Save performance report to JSON file.

        Args:
            path: Path to save the report
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        report = self.get_performance_report()

        with open(path, "w") as f:
            json.dump(report, f, indent=2)

    def should_retrain(self) -> tuple[bool, str]:
        """
        Determine if model should be retrained based on performance.

        Returns:
            Tuple of (should_retrain, reason)
        """
        metrics = self.compute_metrics()

        # Check for critical degradation
        if metrics.get("mae", 0) > self.mae_threshold * 2:
            return True, f"MAE ({metrics['mae']:.2f}) is 2x above threshold"
        if metrics.get("mape", 0) > self.mape_threshold * 2:
            return True, f"MAPE ({metrics['mape']:.2f}%) is 2x above threshold"
        if metrics.get("error_rate", 0) > self.error_rate_threshold * 3:
            return True, f"Error rate ({metrics['error_rate']:.2f}%) is 3x above threshold"

        # Check for sustained degradation
        recent_alerts = [
            a for a in self.alerts if (datetime.now() - a.timestamp) < timedelta(hours=24)
        ]

        error_alerts = [
            a for a in recent_alerts if a.level in {AlertLevel.ERROR, AlertLevel.CRITICAL}
        ]
        if len(error_alerts) >= 5:
            return True, f"{len(error_alerts)} error-level alerts in last 24 hours"

        return False, "Performance within acceptable bounds"

    def reset(self) -> None:
        """Reset all monitoring data."""
        self.predictions.clear()
        self.actuals.clear()
        self.latencies.clear()
        self.timestamps.clear()
        self.errors.clear()
        self.alerts.clear()
        self.last_alert_time.clear()
        logger.info("Performance monitor reset")
