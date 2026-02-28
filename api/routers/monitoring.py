# api/routers/monitoring.py
# Urban Intelligence Framework - Monitoring API Router
# Performance monitoring and drift detection endpoints

"""
API router for monitoring endpoints.

Provides endpoints for:
    - Performance metrics
    - Drift detection reports
    - Alerts management
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.monitoring import DriftDetector, PerformanceMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Global monitors (set from main app)
_performance_monitor: PerformanceMonitor | None = None
_drift_detector: DriftDetector | None = None


def set_monitors(
    performance: PerformanceMonitor,
    drift: DriftDetector,
) -> None:
    """Set the monitoring instances."""
    global _performance_monitor, _drift_detector
    _performance_monitor = performance
    _drift_detector = drift


def get_performance_monitor() -> PerformanceMonitor:
    """Get the performance monitor."""
    if _performance_monitor is None:
        raise HTTPException(status_code=503, detail="Performance monitor not initialized")
    return _performance_monitor


def get_drift_detector() -> DriftDetector:
    """Get the drift detector."""
    if _drift_detector is None:
        raise HTTPException(status_code=503, detail="Drift detector not initialized")
    return _drift_detector


# =============================================================================
# Response Models
# =============================================================================


class PerformanceMetricsResponse(BaseModel):
    """Response model for performance metrics."""

    mae: float = Field(description="Mean Absolute Error")
    rmse: float = Field(description="Root Mean Squared Error")
    r2: float = Field(description="R² Score")
    mape: float = Field(description="Mean Absolute Percentage Error")
    latency_mean_ms: float = Field(description="Mean prediction latency (ms)")
    latency_p50_ms: float = Field(description="P50 prediction latency (ms)")
    latency_p95_ms: float = Field(description="P95 prediction latency (ms)")
    latency_p99_ms: float = Field(description="P99 prediction latency (ms)")
    prediction_count: int = Field(description="Total predictions in window")
    error_rate: float = Field(description="Error rate (%)")


class DriftReportResponse(BaseModel):
    """Response model for drift report."""

    report_time: str
    total_features: int
    features_with_drift: int
    drift_percentage: float
    overall_severity: str
    feature_reports: list[dict[str, Any]]
    recommendations: list[str]


class AlertResponse(BaseModel):
    """Response model for an alert."""

    alert_id: str
    timestamp: str
    level: str
    metric_name: str
    current_value: float
    threshold_value: float
    message: str


class AlertsListResponse(BaseModel):
    """Response model for alerts list."""

    alerts: list[AlertResponse]
    total: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics() -> PerformanceMetricsResponse:
    """Get current performance metrics."""
    monitor = get_performance_monitor()
    metrics = monitor.compute_metrics()

    return PerformanceMetricsResponse(
        mae=metrics.get("mae", 0),
        rmse=metrics.get("rmse", 0),
        r2=metrics.get("r2", 0),
        mape=metrics.get("mape", 0),
        latency_mean_ms=metrics.get("latency_mean_ms", 0),
        latency_p50_ms=metrics.get("latency_p50_ms", 0),
        latency_p95_ms=metrics.get("latency_p95_ms", 0),
        latency_p99_ms=metrics.get("latency_p99_ms", 0),
        prediction_count=int(metrics.get("prediction_count", 0)),
        error_rate=metrics.get("error_rate", 0),
    )


@router.get("/performance/report")
async def get_performance_report() -> dict[str, Any]:
    """Get comprehensive performance report."""
    monitor = get_performance_monitor()
    return monitor.get_performance_report()


@router.get("/drift", response_model=DriftReportResponse)
async def get_drift_report() -> DriftReportResponse:
    """Get current drift detection report."""
    detector = get_drift_detector()

    # Get latest report if available
    if not hasattr(detector, "_latest_report") or detector._latest_report is None:
        return DriftReportResponse(
            report_time=datetime.now().isoformat(),
            total_features=0,
            features_with_drift=0,
            drift_percentage=0,
            overall_severity="none",
            feature_reports=[],
            recommendations=["No drift data available. Run drift detection first."],
        )

    report = detector._latest_report
    return DriftReportResponse(
        report_time=report.timestamp.isoformat(),
        total_features=report.total_features,
        features_with_drift=report.features_with_drift,
        drift_percentage=report.drift_percentage,
        overall_severity=report.overall_severity.value,
        feature_reports=[fr.to_dict() for fr in report.feature_reports],
        recommendations=report.recommendations,
    )


@router.post("/drift/check")
async def trigger_drift_check() -> dict[str, Any]:
    """Trigger a drift detection check."""
    _ = get_drift_detector()

    # In production, this would compare against current production data
    # For now, return status
    return {
        "status": "triggered",
        "message": "Drift detection check initiated",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/alerts", response_model=AlertsListResponse)
async def get_alerts(
    limit: int = Query(default=10, ge=1, le=100),
    level: str | None = Query(default=None, description="Filter by level"),
) -> AlertsListResponse:
    """Get recent alerts."""
    monitor = get_performance_monitor()

    alerts = monitor.alerts[-limit:]

    if level:
        alerts = [a for a in alerts if a.level.value == level]

    return AlertsListResponse(
        alerts=[
            AlertResponse(
                alert_id=a.alert_id,
                timestamp=a.timestamp.isoformat(),
                level=a.level.value,
                metric_name=a.metric_name,
                current_value=a.current_value,
                threshold_value=a.threshold_value,
                message=a.message,
            )
            for a in reversed(alerts)
        ],
        total=len(monitor.alerts),
    )


@router.get("/health/detailed")
async def get_detailed_health() -> dict[str, Any]:
    """Get detailed health status including monitoring metrics."""
    monitor = get_performance_monitor()
    metrics = monitor.compute_metrics()

    should_retrain, retrain_reason = monitor.should_retrain()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "mae": metrics.get("mae", 0),
            "error_rate": metrics.get("error_rate", 0),
            "prediction_count": metrics.get("prediction_count", 0),
            "latency_p95_ms": metrics.get("latency_p95_ms", 0),
        },
        "thresholds": {
            "mae_threshold": monitor.mae_threshold,
            "error_rate_threshold": monitor.error_rate_threshold,
            "latency_threshold_ms": monitor.latency_threshold_ms,
        },
        "status_details": {
            "mae_ok": metrics.get("mae", 0) <= monitor.mae_threshold,
            "error_rate_ok": metrics.get("error_rate", 0) <= monitor.error_rate_threshold,
            "latency_ok": metrics.get("latency_p95_ms", 0) <= monitor.latency_threshold_ms,
        },
        "retraining": {
            "should_retrain": should_retrain,
            "reason": retrain_reason,
        },
        "active_alerts": len([a for a in monitor.alerts if a.level.value in ["error", "critical"]]),
    }


@router.post("/thresholds")
async def update_thresholds(
    mae: float | None = Query(default=None, description="New MAE threshold"),
    rmse: float | None = Query(default=None, description="New RMSE threshold"),
    latency: float | None = Query(default=None, description="New latency threshold (ms)"),
    error_rate: float | None = Query(default=None, description="New error rate threshold (%)"),
) -> dict[str, Any]:
    """Update monitoring thresholds."""
    monitor = get_performance_monitor()

    updated = {}

    if mae is not None:
        monitor.mae_threshold = mae
        updated["mae_threshold"] = mae

    if rmse is not None:
        monitor.rmse_threshold = rmse
        updated["rmse_threshold"] = rmse

    if latency is not None:
        monitor.latency_threshold_ms = latency
        updated["latency_threshold_ms"] = latency

    if error_rate is not None:
        monitor.error_rate_threshold = error_rate
        updated["error_rate_threshold"] = error_rate

    return {
        "status": "updated",
        "updated_thresholds": updated,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/reset")
async def reset_monitoring() -> dict[str, Any]:
    """Reset all monitoring data."""
    monitor = get_performance_monitor()
    monitor.reset()

    return {
        "status": "reset",
        "message": "Monitoring data cleared",
        "timestamp": datetime.now().isoformat(),
    }
