# backend/tests/test_api.py
# Urban Intelligence Framework v2.0.0
# API endpoint integration tests

"""
Integration tests for FastAPI endpoints.

Uses pytest + httpx.AsyncClient for async HTTP testing.
"""

from __future__ import annotations

import pytest
from api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    """Async HTTP test client fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Health check ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health should return 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── Cities ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_cities(client: AsyncClient):
    """GET /api/v1/cities should return a non-empty list."""
    response = await client.get("/api/v1/cities/")
    assert response.status_code == 200
    cities = response.json()
    assert isinstance(cities, list)
    assert len(cities) > 0
    # Each city must have required keys
    first = cities[0]
    for key in ("city_id", "name", "country", "latitude", "longitude"):
        assert key in first


@pytest.mark.asyncio
async def test_get_city_found(client: AsyncClient):
    """GET /api/v1/cities/london should return London metadata."""
    response = await client.get("/api/v1/cities/london")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "london"
    assert data["name"] == "London"


@pytest.mark.asyncio
async def test_get_city_not_found(client: AsyncClient):
    """GET /api/v1/cities/unknown_city should return 404."""
    response = await client.get("/api/v1/cities/unknown_city_xyz")
    assert response.status_code == 404


# ── Predictions ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_predict_single(client: AsyncClient):
    """POST /api/v1/predictions/single should return a valid prediction."""
    payload = {
        "city_id": "london",
        "room_type": "Entire home/apt",
        "property_type": "Apartment",
        "neighbourhood": "Westminster",
        "accommodates": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1.0,
        "amenity_count": 15,
        "review_scores_rating": 4.7,
        "number_of_reviews": 50,
        "availability_365": 200,
        "minimum_nights": 2,
        "host_is_superhost": True,
        "instant_bookable": False,
        "latitude": 51.5074,
        "longitude": -0.1278,
    }
    response = await client.post("/api/v1/predictions/single", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_price" in data
    assert data["predicted_price"] > 0
    assert "confidence_interval" in data
    assert "lower" in data["confidence_interval"]
    assert "upper" in data["confidence_interval"]


@pytest.mark.asyncio
async def test_predict_batch(client: AsyncClient):
    """POST /api/v1/predictions/batch should return one result per listing."""
    listings = [
        {
            "city_id": "paris",
            "room_type": "Private room",
            "accommodates": 1,
            "bedrooms": 1,
            "beds": 1,
            "bathrooms": 1.0,
            "amenity_count": 8,
            "review_scores_rating": 4.2,
            "number_of_reviews": 10,
            "availability_365": 100,
            "minimum_nights": 1,
            "host_is_superhost": False,
            "instant_bookable": True,
            "latitude": 48.8566,
            "longitude": 2.3522,
        }
        for _ in range(5)
    ]
    response = await client.post(
        "/api/v1/predictions/batch", json={"listings": listings}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["predictions"]) == 5


@pytest.mark.asyncio
async def test_predict_batch_limit(client: AsyncClient):
    """POST /api/v1/predictions/batch with >500 items should return 422."""
    listings = [
        {
            "city_id": "london",
            "room_type": "Private room",
            "accommodates": 1,
            "bedrooms": 1,
            "beds": 1,
            "bathrooms": 1.0,
            "amenity_count": 5,
            "review_scores_rating": 4.0,
            "number_of_reviews": 5,
            "availability_365": 50,
            "minimum_nights": 1,
            "host_is_superhost": False,
            "instant_bookable": False,
            "latitude": 51.5,
            "longitude": -0.1,
        }
        for _ in range(501)
    ]
    response = await client.post(
        "/api/v1/predictions/batch", json={"listings": listings}
    )
    assert response.status_code == 422


# ── Monitoring ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_monitoring_snapshot(client: AsyncClient):
    """GET /api/v1/monitoring/snapshot/london should return a valid snapshot."""
    response = await client.get("/api/v1/monitoring/snapshot/london")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "london"
    assert "n_predictions" in data
    assert "active_alerts" in data


@pytest.mark.asyncio
async def test_monitoring_alerts(client: AsyncClient):
    """GET /api/v1/monitoring/alerts should return an alerts list."""
    response = await client.get("/api/v1/monitoring/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


# ── Experiments ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_experiment(client: AsyncClient):
    """POST then GET /api/v1/experiments should reflect the new experiment."""
    create_payload = {
        "name": "Test A/B Experiment",
        "description": "XGBoost vs Ensemble",
        "variants": [
            {"name": "control", "model_id": "xgb_v1", "traffic_split": 0.5},
            {
                "name": "treatment",
                "model_id": "ensemble_v2",
                "traffic_split": 0.5,
            },
        ],
    }
    create_resp = await client.post(
        "/api/v1/experiments/", json=create_payload
    )
    assert create_resp.status_code == 200
    exp_id = create_resp.json()["experiment_id"]
    assert exp_id.startswith("exp_")

    list_resp = await client.get("/api/v1/experiments/")
    assert list_resp.status_code == 200
    experiment_ids = [e["id"] for e in list_resp.json()["experiments"]]
    assert exp_id in experiment_ids


@pytest.mark.asyncio
async def test_experiment_invalid_split(client: AsyncClient):
    """Creating an experiment where splits don't sum to 1.0 should return 422."""
    payload = {
        "name": "Bad Split",
        "variants": [
            {"name": "a", "model_id": "m1", "traffic_split": 0.3},
            {"name": "b", "model_id": "m2", "traffic_split": 0.3},
        ],
    }
    response = await client.post("/api/v1/experiments/", json=payload)
    assert response.status_code == 422
