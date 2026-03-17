# backend/api/graphql_schema.py
# Urban Intelligence Framework v2.0.0
# GraphQL schema and resolvers using Strawberry

"""
GraphQL API schema.

Provides an alternative query interface alongside the REST API.
Types: City, Listing, Prediction, MonitoringMetrics
Queries: cities, city, listings, recentPredictions, monitoringSnapshot
Mutations: triggerFetch, resolvAlert
"""

from __future__ import annotations

from dataclasses import dataclass

import strawberry
from strawberry.fastapi import GraphQLRouter

from src.data.data_service import INSIDE_AIRBNB_CATALOGUE, DataService

_service = DataService()


# ── GraphQL types ─────────────────────────────────────────────────────────


@strawberry.type
@dataclass
class City:
    city_id: str
    name: str
    country: str
    latitude: float
    longitude: float
    currency: str
    is_cached: bool


@strawberry.type
@dataclass
class ListingSummary:
    listing_id: str
    neighbourhood: str
    room_type: str
    bedrooms: float | None
    price: float | None
    review_scores_rating: float | None


@strawberry.type
@dataclass
class PredictionResult:
    city_id: str
    predicted_price: float
    currency: str
    confidence_lower: float
    confidence_upper: float


@strawberry.type
@dataclass
class MonitoringMetrics:
    city_id: str
    n_predictions: int
    rmse: float | None
    mae: float | None
    r2: float | None
    avg_latency_ms: float | None
    active_alerts: int


# ── Query resolvers ───────────────────────────────────────────────────────


@strawberry.type
class Query:
    @strawberry.field
    def cities(self) -> list[City]:
        """Return all available cities."""
        return [
            City(
                city_id=city_id,
                name=meta["name"],
                country=meta["country"],
                latitude=meta["lat"],
                longitude=meta["lon"],
                currency=meta["currency"],
                is_cached=(
                    _service._raw_path / f"{city_id}_listings.parquet"
                ).exists(),
            )
            for city_id, meta in INSIDE_AIRBNB_CATALOGUE.items()
        ]

    @strawberry.field
    def city(self, city_id: str) -> City | None:
        """Return a single city by ID."""
        meta = INSIDE_AIRBNB_CATALOGUE.get(city_id)
        if not meta:
            return None
        return City(
            city_id=city_id,
            name=meta["name"],
            country=meta["country"],
            latitude=meta["lat"],
            longitude=meta["lon"],
            currency=meta["currency"],
            is_cached=(
                _service._raw_path / f"{city_id}_listings.parquet"
            ).exists(),
        )

    @strawberry.field
    def listings(
        self,
        city_id: str,
        limit: int = 50,
        room_type: str | None = None,
    ) -> list[ListingSummary]:
        """Return cached listings for a city."""
        try:
            filters = {}
            if room_type:
                filters["room_type"] = room_type
            df = _service.query_listings(city_id, filters=filters, limit=limit)
            results = []
            for row in df.to_dicts():
                results.append(
                    ListingSummary(
                        listing_id=str(row.get("id", "")),
                        neighbourhood=str(
                            row.get("neighbourhood_cleansed", "")
                        ),
                        room_type=str(row.get("room_type", "")),
                        bedrooms=float(row["bedrooms"])
                        if row.get("bedrooms") is not None
                        else None,
                        price=float(row["price"])
                        if row.get("price") is not None
                        else None,
                        review_scores_rating=(
                            float(row["review_scores_rating"])
                            if row.get("review_scores_rating") is not None
                            else None
                        ),
                    )
                )
            return results
        except RuntimeError:
            return []

    @strawberry.field
    def monitoring_snapshot(self, city_id: str) -> MonitoringMetrics:
        """Return current monitoring metrics for a city."""
        from api.routers.monitoring import _get_monitor

        monitor = _get_monitor(city_id)
        snap = monitor.get_snapshot()
        return MonitoringMetrics(
            city_id=city_id,
            n_predictions=snap.n_predictions,
            rmse=snap.rmse,
            mae=snap.mae,
            r2=snap.r2,
            avg_latency_ms=snap.avg_latency_ms,
            active_alerts=len(snap.active_alerts),
        )


# ── Mutation resolvers ────────────────────────────────────────────────────


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def trigger_fetch(
        self, city_id: str, force_refresh: bool = False
    ) -> str:
        """Trigger a background data fetch for a city."""
        import asyncio

        asyncio.create_task(
            _service.fetch_city(city_id, force_refresh=force_refresh)
        )
        return f"Fetch triggered for {city_id}"

    @strawberry.mutation
    def resolve_alert(self, alert_id: str) -> str:
        """Resolve a monitoring alert."""
        from api.routers.monitoring import _monitors

        for monitor in _monitors.values():
            if alert_id in monitor._active_alerts:
                monitor.resolve_alert(alert_id)
                return f"Alert {alert_id} resolved"
        return f"Alert {alert_id} not found"


# ── Router instance ───────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, graphql_ide=True)
