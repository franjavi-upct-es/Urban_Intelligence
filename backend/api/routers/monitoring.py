# backend/api/routers/monitoring.py
# Urban Intelligence Framework v2.0.0
# REST router for monitoring, drift detection, and alerting

"""
Monitoring router.

Endpoints:
- GET  /api/v1/monitoring/snapshot/{city_id} — current performance snapshot
- GET  /api/v1/monitoring/drift/{city_id}    — latest drift report
- GET  /api/v1/monitoring/alerts             — all active alerts
- POST /api/v1/monitoring/alerts/{id}/resolve — resolve an alert
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from src.monitoring.performance_monitor import PerformanceMonitor

router = APIRouter()

# In-memory registry of per-city monitors
_monitors: dict[str, PerformanceMonitor] = {}


def _get_monitor(city_id: str) -> PerformanceMonitor:
    """Return (or create) the monitor for a city."""
    if city_id not in _monitors:
        _monitors[city_id] = PerformanceMonitor(city_id=city_id)
    return _monitors[city_id]


@router.get("/snapshot/{city_id}")
async def get_snapshot(city_id: str) -> dict[str, Any]:
    """Return the current performance snapshot for a city's model."""
    monitor = _get_monitor(city_id)
    snap = monitor.get_snapshot()

    return {
        "city_id": snap.city_id,
        "timestamp": snap.timestamp.isoformat(),
        "rmse": snap.rmse,
        "mae": snap.mae,
        "r2": snap.r2,
        "avg_latency_ms": snap.avg_latency_ms,
        "p95_latency_ms": snap.p95_latency_ms,
        "request_rate": snap.request_rate,
        "error_rate": snap.error_rate,
        "n_predictions": snap.n_predictions,
        "active_alerts": [
            {
                "alert_id": a.alert_id,
                "metric": a.metric,
                "current_value": a.current_value,
                "threshold": a.threshold,
                "severity": a.severity,
                "message": a.message,
                "created_at": a.created_at.isoformat(),
            }
            for a in snap.active_alerts
        ],
    }


@router.get("/alerts")
async def get_all_alerts() -> dict[str, Any]:
    """Return all active alerts across all monitored cities."""
    all_alerts = []
    for city_id, monitor in _monitors.items():
        for alert in monitor.get_active_alerts():
            all_alerts.append(
                {
                    "alert_id": alert.alert_id,
                    "city_id": city_id,
                    "metric": alert.metric,
                    "severity": alert.severity,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "created_at": alert.created_at.isoformat(),
                }
            )
    return {"total": len(all_alerts), "alerts": all_alerts}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> dict[str, str]:
    """Resolve a specific alert by its ID."""
    for monitor in _monitors.values():
        if alert_id in monitor._active_alerts:
            monitor.resolve_alert(alert_id)
            return {"message": f"Alert {alert_id} resolved"}
    raise HTTPException(
        status_code=404, detail=f"Alert '{alert_id}' not found"
    )


@router.get("/cities")
async def get_monitored_cities() -> dict[str, Any]:
    """Return the list of cities currently being monitored."""
    return {
        "cities": [
            {
                "city_id": city_id,
                "n_predictions": m.get_snapshot().n_predictions,
                "active_alerts": len(m.get_active_alerts()),
            }
            for city_id, m in _monitors.items()
        ]
    }
