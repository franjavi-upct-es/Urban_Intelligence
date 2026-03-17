# backend/api/websocket.py
# Urban Intelligence Framework v2.0.0
# WebSocket router for real-time progress and monitoring updates

"""
WebSocket module.

Provides two WebSocket endpoints:

- /ws/{city_id}   : streams FetchProgress events while data is being
                    downloaded and processed for a city.
- /ws/monitor     : broadcasts live monitoring snapshots every 5 seconds
                    for all active cities.

Message format (JSON):
    {
        "type":    "progress" | "monitoring" | "alert" | "error",
        "payload": { ... }
    }
"""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.data.data_service import DataService, FetchProgress
from src.monitoring.performance_monitor import PerformanceMonitor

logger = structlog.get_logger(__name__)
ws_router = APIRouter()

_service = DataService()
_monitors: dict[str, PerformanceMonitor] = {}


# ── Connection manager ────────────────────────────────────────────────────


class ConnectionManager:
    """Tracks active WebSocket connections per channel."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(channel, []).append(ws)
        logger.debug("WebSocket connected", channel=channel)

    def disconnect(self, channel: str, ws: WebSocket) -> None:
        conns = self._connections.get(channel, [])
        if ws in conns:
            conns.remove(ws)
        logger.debug("WebSocket disconnected", channel=channel)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        """Send a JSON message to all connections on a channel."""
        dead: list[WebSocket] = []
        for ws in self._connections.get(channel, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)

    async def send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single WebSocket."""
        with suppress(Exception):
            await ws.send_text(json.dumps(message))


manager = ConnectionManager()


# ── City fetch progress WebSocket ─────────────────────────────────────────


@ws_router.websocket("/ws/{city_id}")
async def city_fetch_ws(websocket: WebSocket, city_id: str) -> None:
    """
    Stream data-fetch progress for a given city.

    The client should send {"action": "fetch", "force_refresh": false}
    to trigger a fetch. Progress events are broadcast until complete.
    """
    await manager.connect(city_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send(
                    websocket, {"type": "error", "payload": "Invalid JSON"}
                )
                continue

            action = msg.get("action")

            if action == "fetch":
                force_refresh = bool(msg.get("force_refresh", False))
                await _handle_fetch(websocket, city_id, force_refresh)

            elif action == "ping":
                await manager.send(websocket, {"type": "pong"})

            else:
                await manager.send(
                    websocket,
                    {"type": "error", "payload": f"Unknown action: {action}"},
                )

    except WebSocketDisconnect:
        manager.disconnect(city_id, websocket)


async def _handle_fetch(
    websocket: WebSocket,
    city_id: str,
    force_refresh: bool,
) -> None:
    """Run fetch_city and stream progress events back over the WebSocket."""

    def on_progress(progress: FetchProgress) -> None:
        asyncio.create_task(
            manager.send(
                websocket,
                {
                    "type": "progress",
                    "payload": {
                        "city_id": progress.city_id,
                        "step": progress.step,
                        "current": progress.current,
                        "total": progress.total,
                        "percent": progress.percent,
                        "message": progress.message,
                    },
                },
            )
        )

    try:
        city_data = await _service.fetch_city(
            city_id=city_id,
            force_refresh=force_refresh,
            on_progress=on_progress,
        )
        await manager.send(
            websocket,
            {
                "type": "complete",
                "payload": {
                    "city_id": city_data.city_id,
                    "listing_count": city_data.listing_count,
                    "fetched_at": city_data.fetched_at.isoformat(),
                },
            },
        )
    except Exception as exc:
        await manager.send(
            websocket,
            {"type": "error", "payload": str(exc)},
        )


# ── Live monitoring broadcast WebSocket ───────────────────────────────────


@ws_router.websocket("/ws/monitor")
async def monitoring_ws(websocket: WebSocket) -> None:
    """
    Broadcast live monitoring snapshots for all active cities every 5 seconds.

    No client message required — updates stream automatically after connect.
    """
    await manager.connect("monitor", websocket)

    try:
        while True:
            snapshots = []
            for _city_id, monitor in _monitors.items():
                snap = monitor.get_snapshot()
                snapshots.append(
                    {
                        "city_id": snap.city_id,
                        "timestamp": snap.timestamp.isoformat(),
                        "rmse": snap.rmse,
                        "mae": snap.mae,
                        "avg_latency_ms": snap.avg_latency_ms,
                        "request_rate": snap.request_rate,
                        "n_predictions": snap.n_predictions,
                        "active_alerts": len(snap.active_alerts),
                    }
                )

            await manager.send(
                websocket,
                {"type": "monitoring", "payload": snapshots},
            )
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect("monitor", websocket)
    except Exception as exc:
        logger.warning("Monitoring WebSocket error", error=str(exc))
        manager.disconnect("monitor", websocket)
