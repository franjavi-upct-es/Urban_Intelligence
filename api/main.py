# api/main.py
# Urban Intelligence Framework - FastAPI Application
# RESTful API for model serving and data access

"""
FastAPI application for the Urban Intelligence Framework.

This module provides a production-ready REST API with:
    - Price prediction endpoints
    - City data queries
    - Model management
    - Health checks and monitoring

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.data import DataService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Request/Response
# =============================================================================


class ListingFeatures(BaseModel):
    """Input features for price prediction."""

    accommodates: int = Field(ge=1, le=20, description="Number of guests")
    bedrooms: float = Field(ge=0, le=20, description="Number of bedrooms")
    beds: float = Field(ge=0, le=30, description="Number of beds")
    bathrooms: float = Field(ge=0, le=10, description="Number of bathrooms")
    latitude: float = Field(ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(ge=-180, le=180, description="Longitude coordinate")
    room_type: str = Field(description="Type of room (Entire home/apt, Private room, etc.)")
    property_type: str = Field(default="Apartment", description="Type of property")
    minimum_nights: int = Field(default=1, ge=1, description="Minimum nights required")
    availability_365: int = Field(default=180, ge=0, le=365, description="Days available per year")
    number_of_reviews: int = Field(default=0, ge=0, description="Total number of reviews")
    review_scores_rating: float | None = Field(
        default=None, ge=0, le=5, description="Overall rating"
    )
    instant_bookable: bool = Field(default=False, description="Can be booked instantly")
    host_is_superhost: bool = Field(default=False, description="Host is a superhost")

    @field_validator("room_type")
    @classmethod
    def validate_room_type(cls, v: str) -> str:
        valid_types = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
        if v not in valid_types:
            raise ValueError(f"room_type must be one of {valid_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "accommodates": 4,
                "bedrooms": 2,
                "beds": 2,
                "bathrooms": 1,
                "latitude": 40.4168,
                "longitude": -3.7038,
                "room_type": "Entire home/apt",
                "property_type": "Apartment",
                "minimum_nights": 2,
                "availability_365": 200,
                "number_of_reviews": 50,
                "review_scores_rating": 4.5,
                "instant_bookable": True,
                "host_is_superhost": False,
            }
        }


class PredictionResponse(BaseModel):
    """Response model for price predictions."""

    predicted_price: float = Field(description="Predicted nightly price in local currency")
    confidence_interval: tuple[float, float] = Field(description="95% confidence interval")
    currency: str = Field(default="USD", description="Currency of the price")
    model_version: str = Field(description="Version of the model used")
    prediction_timestamp: datetime = Field(description="When the prediction was made")
    features_used: dict[str, Any] = Field(description="Features used for prediction")


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions."""

    listings: list[ListingFeatures] = Field(min_length=1, max_length=100)


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions."""

    predictions: list[PredictionResponse]
    total_count: int
    processing_time_ms: float


class CityInfo(BaseModel):
    """Information about a city."""

    city_id: str
    display_name: str
    country: str
    listing_count: int
    airbnb_status: str
    weather_status: str
    poi_status: str
    last_updated: datetime | None


class CityListResponse(BaseModel):
    """Response model for city listing."""

    cities: list[CityInfo]
    total_count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    model_loaded: bool
    database_connected: bool
    timestamp: datetime


class ModelInfo(BaseModel):
    """Information about the loaded model."""

    model_type: str
    version: str
    trained_at: datetime | None
    metrics: dict[str, float]
    feature_importance: dict[str, float]


# =============================================================================
# Application State
# =============================================================================


class AppState:
    """Application state container."""

    def __init__(self) -> None:
        self.model = None
        self.model_version = "not_loaded"
        self.model_metrics: dict[str, float] = {}
        self.feature_importance: dict[str, float] = {}
        self.data_service: DataService | None = None
        self.settings = get_settings()

    def load_model(self) -> bool:
        """Load the trained model from disk."""
        model_paths = [
            Path("models/best_model.pkl"),
            Path("models/xgboost_model.pkl"),
            Path("models/model.pkl"),
        ]

        for model_path in model_paths:
            if model_path.exists():
                try:
                    model_data = joblib.load(model_path)

                    if isinstance(model_data, dict):
                        self.model = model_data.get("model")
                        self.model_version = model_data.get("version", "1.0.0")
                        self.model_metrics = model_data.get("metrics", {})
                        self.feature_importance = model_data.get("feature_importance", {})
                    else:
                        self.model = model_data
                        self.model_version = "1.0.0"

                    logger.info(f"Model loaded from {model_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to load model from {model_path}: {e}")

        logger.warning("No trained model found")
        return False

    def initialize_data_service(self) -> None:
        """Initialize the data service."""
        try:
            self.data_service = DataService(data_dir="data")
            logger.info("Data service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize data service: {e}")


# Global application state
app_state = AppState()


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Urban Intelligence API...")
    app_state.load_model()
    app_state.initialize_data_service()

    yield

    # Shutdown
    logger.info("Shutting down Urban Intelligence API...")
    if app_state.data_service:
        logger.info("Data service shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Urban Intelligence API",
    description="REST API for Airbnb price prediction and city data access",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health and Info Endpoints
# =============================================================================


@app.get("/", tags=["Info"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Urban Intelligence API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_loaded=app_state.model is not None,
        database_connected=app_state.data_service is not None,
        timestamp=datetime.now(),
    )


@app.get("/model/info", response_model=ModelInfo, tags=["Model"])
async def get_model_info() -> ModelInfo:
    """Get information about the loaded model."""
    if app_state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return ModelInfo(
        model_type="XGBoost",
        version=app_state.model_version,
        trained_at=None,  # Would come from model metadata
        metrics=app_state.model_metrics,
        feature_importance=app_state.feature_importance,
    )


# =============================================================================
# Prediction Endpoints
# =============================================================================


@app.post("/predict", response_model=PredictionResponse, tags=["Predictions"])
async def predict_price(features: ListingFeatures) -> PredictionResponse:
    """Predict the price for a single listing."""
    if app_state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Prepare features for prediction
        feature_dict = features.model_dump()

        # Convert to format expected by model
        features_array = _prepare_features(feature_dict)

        # Make prediction
        prediction = float(app_state.model.predict(features_array)[0])

        # Calculate confidence interval (simplified)
        std_error = prediction * 0.15  # Approximate 15% error
        ci_lower = max(0, prediction - 1.96 * std_error)
        ci_upper = prediction + 1.96 * std_error

        return PredictionResponse(
            predicted_price=round(prediction, 2),
            confidence_interval=(round(ci_lower, 2), round(ci_upper, 2)),
            currency="USD",
            model_version=app_state.model_version,
            prediction_timestamp=datetime.now(),
            features_used=feature_dict,
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}") from e


@app.post("/predict/batch", response_model=BatchPredictionResponse, tags=["Predictions"])
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """Predict prices for multiple listings."""
    if app_state.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    import time

    start_time = time.time()

    predictions = []
    for listing in request.listings:
        try:
            feature_dict = listing.model_dump()
            features_array = _prepare_features(feature_dict)
            prediction = float(app_state.model.predict(features_array)[0])

            std_error = prediction * 0.15
            ci_lower = max(0, prediction - 1.96 * std_error)
            ci_upper = prediction + 1.96 * std_error

            predictions.append(
                PredictionResponse(
                    predicted_price=round(prediction, 2),
                    confidence_interval=(round(ci_lower, 2), round(ci_upper, 2)),
                    currency="USD",
                    model_version=app_state.model_version,
                    prediction_timestamp=datetime.now(),
                    features_used=feature_dict,
                )
            )
        except Exception as e:
            logger.error(f"Batch prediction error for listing: {e}")

    processing_time = (time.time() - start_time) * 1000

    return BatchPredictionResponse(
        predictions=predictions,
        total_count=len(predictions),
        processing_time_ms=round(processing_time, 2),
    )


# =============================================================================
# City Data Endpoints
# =============================================================================


@app.get("/cities", response_model=CityListResponse, tags=["Cities"])
async def list_cities(
    cached_only: bool = Query(False, description="Only return cities with cached data"),
) -> CityListResponse:
    """List all available cities."""
    if app_state.data_service is None:
        raise HTTPException(status_code=503, detail="Data service not available")

    try:
        if cached_only:
            city_ids = app_state.data_service.list_cached_cities()
            city_infos = [
                CityInfo(
                    city_id=cid,
                    display_name=cid.title(),
                    country="Unknown",
                    listing_count=0,
                    airbnb_status="cached",
                    weather_status="unknown",
                    poi_status="unknown",
                    last_updated=None,
                )
                for cid in city_ids
            ]
        else:
            cities_raw = app_state.data_service.list_available_cities(include_remote=True)
            city_infos = [
                CityInfo(
                    city_id=city["city_id"],
                    display_name=city.get("display_name", city["city_id"]),
                    country=city.get("country", "Unknown"),
                    listing_count=city.get("listing_count", 0),
                    airbnb_status=city.get("airbnb_status", "unknown"),
                    weather_status=city.get("weather_status", "unknown"),
                    poi_status=city.get("poi_status", "unknown"),
                    last_updated=city.get("airbnb_last_updated"),
                )
                for city in cities_raw
            ]

        return CityListResponse(
            cities=city_infos,
            total_count=len(city_infos),
        )

    except Exception as e:
        logger.error(f"Error listing cities: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/cities/{city_id}", tags=["Cities"])
async def get_city(city_id: str) -> dict[str, Any]:
    """Get detailed information about a specific city."""
    if app_state.data_service is None:
        raise HTTPException(status_code=503, detail="Data service not available")

    try:
        status = app_state.data_service.get_data_status(city_id)

        if not status.get("exists", False):
            raise HTTPException(status_code=404, detail=f"City not found: {city_id}")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting city {city_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/cities/{city_id}/fetch", tags=["Cities"])
async def fetch_city_data(
    city_id: str,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force refresh even if data exists"),
) -> dict[str, str]:
    """Trigger data fetch for a city (runs in background)."""
    if app_state.data_service is None:
        raise HTTPException(status_code=503, detail="Data service not available")

    data_service = app_state.data_service

    async def fetch_task() -> None:
        try:
            data_service.get_city_data(city_id, force_refresh=force)
            logger.info(f"Data fetch completed for {city_id}")
        except Exception as e:
            logger.error(f"Background fetch failed for {city_id}: {e}")

    background_tasks.add_task(fetch_task)

    return {
        "message": f"Data fetch initiated for {city_id}",
        "status": "processing",
        "check_status_at": f"/cities/{city_id}",
    }


@app.get("/cities/{city_id}/statistics", tags=["Cities"])
async def get_city_statistics(city_id: str) -> dict[str, Any]:
    """Get price statistics for a city."""
    if app_state.data_service is None:
        raise HTTPException(status_code=503, detail="Data service not available")

    try:
        stats = app_state.data_service.get_price_statistics(city_id)

        if stats.get("listings_count", 0) == 0:
            raise HTTPException(
                status_code=404, detail=f"No data available for {city_id}. Fetch data first."
            )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics for {city_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Helper Functions
# =============================================================================


def _prepare_features(feature_dict: dict) -> np.ndarray:
    """Prepare features for model prediction.

    Args:
        feature_dict: Dictionary of listing features

    Returns:
        NumPy array ready for prediction
    """
    # Define feature order (must match training)
    numeric_features = [
        "accommodates",
        "bedrooms",
        "beds",
        "bathrooms",
        "latitude",
        "longitude",
        "minimum_nights",
        "availability_365",
        "number_of_reviews",
    ]

    # Build feature vector
    features = []
    for feat in numeric_features:
        value = feature_dict.get(feat, 0)
        features.append(float(value) if value is not None else 0.0)

    # Add review score (with default)
    review_score = feature_dict.get("review_scores_rating")
    features.append(float(review_score) if review_score else 4.5)

    # Add boolean features
    features.append(1.0 if feature_dict.get("instant_bookable") else 0.0)
    features.append(1.0 if feature_dict.get("host_is_superhost") else 0.0)

    # Encode room type
    room_type_map = {
        "Entire home/apt": [1, 0, 0, 0],
        "Private room": [0, 1, 0, 0],
        "Shared room": [0, 0, 1, 0],
        "Hotel room": [0, 0, 0, 1],
    }
    room_encoding = room_type_map.get(
        feature_dict.get("room_type", "Entire home/apt"), [1, 0, 0, 0]
    )
    features.extend(room_encoding)

    return np.array([features])


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),  # nosec B104
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        workers=int(os.getenv("API_WORKERS", "1")),
    )
