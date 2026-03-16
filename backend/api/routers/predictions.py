# backend/api/routers/predictions.py
# Urban Intelligence Framework v2.0.0
# REST router for price prediction endpoints

"""
Predictions router.

Endpoints:
- POST /api/v1/predictions/single  — predict price for one listing
- POST /api/v1/predictions/batch   — predict prices for multiple listings
- GET  /api/v1/predictions/history — recent prediction log
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# In-memory prediction log (replace with DB query in production)
_prediction_log: list[dict[str, Any]] = []


# ── Request / Response models ─────────────────────────────────────────────


class ListingFeatures(BaseModel):
    """Feature inputs for a single listing price prediction."""

    city_id: str = Field(..., examples=["london"])
    room_type: str = Field(..., examples=["Entire home/apt"])
    property_type: str = Field(default="Apartment")
    neighbourhood: str = Field(default="unknown")
    accommodates: int = Field(default=2, ge=1, le=20)
    bedrooms: int = Field(default=1, ge=0, le=15)
    beds: int = Field(default=1, ge=0, le=20)
    bathrooms: float = Field(default=1.0, ge=0.0, le=10.0)
    amenity_count: int = Field(default=10, ge=0, le=100)
    review_scores_rating: float = Field(default=4.5, ge=0.0, le=5.0)
    number_of_reviews: int = Field(default=20, ge=0)
    availability_365: int = Field(default=180, ge=0, le=365)
    minimum_nights: int = Field(default=2, ge=1)
    host_is_superhost: bool = Field(default=False)
    instant_bookable: bool = Field(default=False)
    latitude: float = Field(default=51.5074)
    longitude: float = Field(default=-0.1278)


class PredictionResponse(BaseModel):
    """Price prediction result."""

    prediction_id: str
    city_id: str
    predicted_price: float
    currency: str
    confidence_interval: dict[str, float]  # {"lower": x, "upper": y}
    latency_ms: float
    model_version: str


class BatchPredictionRequest(BaseModel):
    """Batch of listings for bulk prediction."""

    listings: list[ListingFeatures]


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/single", response_model=PredictionResponse)
async def predict_single(features: ListingFeatures) -> dict[str, Any]:
    """
    Predict the nightly price for a single listing.

    Uses the latest trained ensemble model for the requested city.
    Falls back to a rule-based estimator if no trained model exists.
    """
    t0 = time.perf_counter()

    # ── Try to load trained model, fall back to heuristic ─────────────────
    try:
        predicted_price, ci = _run_model_prediction(features)
    except Exception:
        predicted_price, ci = _heuristic_prediction(features)

    latency_ms = (time.perf_counter() - t0) * 1000

    prediction_id = f"pred_{uuid.uuid4().hex[:12]}"
    result: dict[str, Any] = {
        "prediction_id": prediction_id,
        "city_id": features.city_id,
        "predicted_price": round(predicted_price, 2),
        "currency": "USD",
        "confidence_interval": ci,
        "latency_ms": round(latency_ms, 2),
        "model_version": "2.0.0",
    }

    # Append to in-memory log (trimmed to last 1000)
    _prediction_log.append(result)
    if len(_prediction_log) > 1000:
        _prediction_log.pop(0)

    return result


@router.post("/batch")
async def predict_batch(request: BatchPredictionRequest) -> dict[str, Any]:
    """
    Predict prices for a batch of listings.

    Returns an array of predictions in the same order as the input.
    """
    if len(request.listings) > 500:
        raise HTTPException(
            status_code=422,
            detail="Batch size must not exceed 500 listings.",
        )

    results = []
    for listing in request.listings:
        try:
            price, ci = _run_model_prediction(listing)
        except Exception:
            price, ci = _heuristic_prediction(listing)
        results.append(
            {
                "city_id": listing.city_id,
                "predicted_price": round(price, 2),
                "confidence_interval": ci,
            }
        )

    return {"count": len(results), "predictions": results}


@router.get("/history")
async def prediction_history(limit: int = 50) -> dict[str, Any]:
    """Return the most recent prediction log entries."""
    recent = _prediction_log[-limit:][::-1]
    return {"total": len(_prediction_log), "history": recent}


# ── Internal helpers ──────────────────────────────────────────────────────


def _run_model_prediction(
    features: ListingFeatures,
) -> tuple[float, dict[str, float]]:
    """
    Attempt to load the trained model from disk and run inference.
    Raises if no model is available.
    """
    from pathlib import Path

    import joblib

    model_path = Path("data/models") / f"{features.city_id}_model.pkl"
    if not model_path.exists():
        raise FileNotFoundError("No trained model found")

    model = joblib.load(model_path)
    x = _features_to_array(features)
    import numpy as np

    raw_pred = float(model.predict(x)[0])
    price = float(np.expm1(raw_pred))
    ci = {"lower": round(price * 0.85, 2), "upper": round(price * 1.15, 2)}
    return price, ci


def _heuristic_prediction(
    features: ListingFeatures,
) -> tuple[float, dict[str, float]]:
    """
    Rule-based price estimator used when no trained model is available.

    Based on median city prices and known multipliers.
    """
    base_prices: dict[str, float] = {
        "london": 140,
        "paris": 120,
        "barcelona": 100,
        "new-york": 190,
        "amsterdam": 130,
        "lisbon": 90,
        "madrid": 95,
        "berlin": 100,
        "rome": 110,
        "tokyo": 85,
    }
    room_mult = {
        "Entire home/apt": 1.4,
        "Private room": 0.65,
        "Shared room": 0.35,
        "Hotel room": 1.1,
    }

    base = base_prices.get(features.city_id, 120.0)
    mult = room_mult.get(features.room_type, 1.0)
    bedroom_adj = features.bedrooms * 8
    amenity_adj = features.amenity_count * 0.5
    rating_adj = (features.review_scores_rating - 3.5) * 10
    superhost_adj = 10.0 if features.host_is_superhost else 0.0

    price = (
        base * mult + bedroom_adj + amenity_adj + rating_adj + superhost_adj
    )
    price = max(10.0, price)

    ci = {"lower": round(price * 0.80, 2), "upper": round(price * 1.20, 2)}
    return round(price, 2), ci


def _features_to_array(features: ListingFeatures):
    """Convert a ListingFeatures Pydantic model to a 2D numpy array."""
    import numpy as np

    return np.array(
        [
            [
                features.accommodates,
                features.bathrooms,
                features.bedrooms,
                features.beds,
                features.amenity_count,
                features.minimum_nights,
                features.availability_365,
                features.number_of_reviews,
                0.0,  # reviews_per_month placeholder
                features.review_scores_rating,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,  # individual review score placeholders
                0.0,  # host_response_rate
                0.0,  # host_acceptance_rate
                1.0,  # host_listings_count
                1.0,  # calculated_host_listings_count
                0.0,  # dist_to_centre (not computed here)
                int(features.host_is_superhost),
                int(features.instant_bookable),
                features.bedrooms
                * features.review_scores_rating,  # bedrooms_x_rating
                features.beds / max(features.bedrooms, 1),  # beds_per_bedroom
            ]
        ]
    )
