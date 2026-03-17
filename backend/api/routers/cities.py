# backend/api/routers/cities.py
# Urban Intelligence Framework v2.0.0
# REST router for city data management endpoints

"""
Cities router.

Endpoints:
- GET  /api/v1/cities               — list all available cities
- GET  /api/v1/cities/{city_id}     — get city metadata and stats
- POST /api/v1/cities/{city_id}/fetch — trigger data fetch for a city
- GET  /api/v1/cities/{city_id}/listings — query cached listings
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from src.data.data_service import INSIDE_AIRBNB_CATALOGUE, DataService

router = APIRouter()
_service = DataService()


# ── Response models ───────────────────────────────────────────────────────


class CityInfo(BaseModel):
    city_id: str
    name: str
    country: str
    latitude: float
    longitude: float
    currency: str
    is_cached: bool
    listing_count: int | None = None


class FetchRequest(BaseModel):
    force_refresh: bool = False


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/", response_model=list[CityInfo])
async def list_cities() -> list[dict[str, Any]]:
    """Return all cities available in the Inside Airbnb catalogue."""
    cities = _service.get_available_cities()
    return [
        {
            **city,
            "listing_count": None,  # populated lazily when data is fetched
        }
        for city in cities
    ]


@router.get("/{city_id}", response_model=CityInfo)
async def get_city(city_id: str) -> dict[str, Any]:
    """Return metadata for a single city."""
    if city_id not in INSIDE_AIRBNB_CATALOGUE:
        raise HTTPException(
            status_code=404, detail=f"City '{city_id}' not found"
        )

    cities = {c["city_id"]: c for c in _service.get_available_cities()}
    city = cities[city_id]
    return {**city, "listing_count": None}


@router.post("/{city_id}/fetch")
async def fetch_city(
    city_id: str,
    body: FetchRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Trigger a background data fetch for the given city.

    Returns immediately with a job acknowledgement. Frontend should
    subscribe to the WebSocket /ws/{city_id} for progress updates.
    """
    if city_id not in INSIDE_AIRBNB_CATALOGUE:
        raise HTTPException(
            status_code=404, detail=f"City '{city_id}' not found"
        )

    background_tasks.add_task(
        _service.fetch_city,
        city_id=city_id,
        force_refresh=body.force_refresh,
    )

    return {
        "message": f"Fetch initiated for {city_id}",
        "city_id": city_id,
        "background": True,
    }


@router.get("/{city_id}/listings")
async def get_listings(
    city_id: str,
    limit: int = Query(default=100, ge=1, le=5000),
    room_type: str | None = Query(default=None),
    neighbourhood: str | None = Query(default=None),
) -> dict[str, Any]:
    """
    Return cached listings for a city, with optional filters.

    Query params:
    - limit:         maximum rows to return
    - room_type:     filter by room type (e.g. "Entire home/apt")
    - neighbourhood: filter by neighbourhood
    """
    try:
        filters: dict[str, Any] = {}
        if room_type:
            filters["room_type"] = room_type
        if neighbourhood:
            filters["neighbourhood_cleansed"] = neighbourhood

        df = _service.query_listings(city_id, filters=filters, limit=limit)

        return {
            "city_id": city_id,
            "total": len(df),
            "listings": df.to_dicts(),
        }

    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
