# backend/api/main.py
# Urban Intelligence Framework v2.0.0
# FastAPI application entry point — REST + GraphQL + WebSocket

"""
FastAPI application factory.

Mounts:
- REST API routers: /api/v1/cities, /predictions, /monitoring, /experiments
- GraphQL endpoint: /graphql (Strawberry)
- WebSocket: /ws/{city_id}
- Health check: /health
- Prometheus metrics: /metrics
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from src.config import settings
from src.database import db

from api.graphql_schema import graphql_app
from api.routers import cities, experiments, monitoring, predictions
from api.websocket import ws_router

logger = structlog.get_logger(__name__)

# —— Lifespan —————————————————————————————————————————————————————————————————


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown event handler."""
    logger.info("Urban Intelligence API starting", version="2.0.0")
    settings.ensure_directories()
    db.connect()
    yield
    logger.info("Urban Intelligence API shutting down")
    db.close()


# —— Application factory ——————————————————————————————————————————————————————


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Urban Intelligence Framework",
        description=(
            "ML platform for Airbnb price prediction with transfer learning"
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # —— Middleware ———————————————————————————————————————————————————————————
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # —— REST routers —————————————————————————————————————————————————————————
    prefix = "/api/v1"
    app.include_router(
        cities.router, prefix=f"{prefix}/cities", tags=["Cities"]
    )
    app.include_router(
        predictions.router,
        prefix=f"{prefix}/predictions",
        tags=["Predictions"],
    )
    app.include_router(
        monitoring.router, prefix=f"{prefix}/monitoring", tags=["Monitoring"]
    )
    app.include_router(
        experiments.router,
        prefix=f"{prefix}/experiments",
        tags=["Experiments"],
    )

    # —— GraphQL ——————————————————————————————————————————————————————————————
    app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])

    # ── WebSocket ─────────────────────────────────────────────────────────
    app.include_router(ws_router, tags=["WebSocket"])

    # ── Prometheus metrics ────────────────────────────────────────────────
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check() -> JSONResponse:
        """Liveness probe — returns 200 when the API is ready."""
        return JSONResponse({"status": "ok", "version": "2.0.0"})

    return app


# ── Module-level singleton (used by uvicorn) ──────────────────────────────
app = create_app()


def main() -> None:
    """CLI entry point for `urban-api`."""
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=False,
    )
