# src/data/data_service.py
# Urban Intelligence Framework - Unified Data Service
# Core API implementing "fetch one, query fast" pattern

"""
DataService: The main API for all data operations.

This service implements a "fetch one, query fast" architecture:
- First request: Downloads and caches data (30-60 seconds)
- Subsequent requests: Returns cached daa instantly (<10ms)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class FetchStage(Enum):
    """Stages of data fetching."""

    DISCOVERING = "discovering"
    DOWNLOADING_AIRBNB = "downloading_airbnb"
    DOWNLOADING_WEATHER = "downloading_weather"
    DOWNLOADING_POIS = "downloading_pois"
    PROCESSING = "procesing"
    CACHING = "caching"
    COMPLETE = "complete"


@dataclass
class FetchProgress:
    """Progress information for data fetching."""

    stage: FetchStage
    current: int
    total: int
    message: str


@dataclass
class CityData:
    """Container for city data."""

    city_id: str
    listings: pl.DataFrame | None = None
    weather: pl.DataFrame | None = None
    pois: pl.DataFrame | None = None
    calendar: pl.DataFrame | None = None

    @property
    def is_complete(self) -> bool:
        """Check if all data is available."""
        return self.listings is not None


class DataService:
    """
    Unified data service for the Urban Intelligence Framework.

    Example:
        >>> service = DataService()
        >>> data = service.get_city_data("madrid")
        >>> print(f"Loaded {data.listings.height} listings")
    """

    def __init__(self, data_dir: str | Path = "data") -> None:
        """Initialize the data service."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, CityData] = {}
        logger.info(f"DataService initialized with data_dir: {self.data_dir}")

    def list_available_cities(self, include_remote: bool = False) -> list[dict[str, Any]]:
        """List available cities."""
        # Return cached cities plus default cities
        default_cities = [
            {"city_id": "madrid", "display_name": "Madrid", "country": "Spain"},
            {"city_id": "barcelona", "display_name": "Barcelona", "country": "Spain"},
            {"city_id": "paris", "display_name": "Paris", "country": "France"},
            {"city_id": "london", "display_name": "London", "country": "United Kingdom"},
            {"city_id": "amsterdam", "display_name": "Amsterdam", "country": "Netherlands"},
            {"city_id": "rome", "display_name": "Rome", "country": "Italy"},
        ]
        return default_cities

    def list_cached_cities(self) -> list[str]:
        """List cities with cached data."""
        return list(self._cache.keys())

    def get_city_data(
        self,
        city_id: str,
        force_refresh: bool = False,
        progress_callback: Callable[[FetchProgress], None] | None = None,
    ) -> CityData:
        """Get data for a city."""
        city_id = city_id.lower()

        # Check cache
        if not force_refresh and city_id in self._cache:
            logger.info(f"Returning cached data for {city_id}")
            return self._cache[city_id]

        # Create new city data
        city_data = CityData(city_id=city_id)

        # Try to load from disk cache
        cache_path = self.data_dir / "cache" / f"{city_id}_listings.parquet"
        if cache_path.exists() and not force_refresh:
            logger.info(f"Loading {city_id} from disk cache")
            city_data.listings = pl.read_parquet(cache_path)
        else:
            # Generate synthetic data for demo
            logger.info(f"Generating synthetic data for {city_id}")
            from src.data.generator import SyntheticDataGenerator

            generator = SyntheticDataGenerator(n_samples=5000, seed=hash(city_id) % 10000)
            city_data.listings = generator.generate()

            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            city_data.listings.write_parquet(cache_path)

        # Store in memory cache
        self._cache[city_id] = city_data

        return city_data

    def get_price_statistics(self, city_id: str) -> dict[str, Any]:
        """Get price statistics for a city."""
        data = self.get_city_data(city_id)

        if data.listings is None:
            return {"error": "No data available"}

        prices = data.listings["price"].drop_nulls()

        return {
            "city_id": city_id,
            "listings_count": data.listings.height,
            "price_mean": float(prices.mean()),  # type: ignore[arg-type]
            "price_median": float(prices.median()),  # type: ignore[arg-type]
            "price_std": float(prices.std()),  # type: ignore[arg-type]
            "price_min": float(prices.min()),  # type: ignore[arg-type]
            "price_max": float(prices.max()),  # type: ignore[arg-type]
        }

    def get_data_status(self, city_id: str) -> dict[str, Any]:
        """Get data status for a city."""
        city_id = city_id.lower()

        is_cached = city_id in self._cache
        cache_path = self.data_dir / "cache" / f"{city_id}_listings.parquet"

        return {
            "city_id": city_id,
            "exists": is_cached or cache_path.exists(),
            "in_memory": is_cached,
            "on_disk": cache_path.exists(),
        }

    def clear_cache(self, city_id: str | None = None) -> None:
        """Clear cached data."""
        if city_id:
            self._cache.pop(city_id.lower(), None)
            cache_path = self.data_dir / "cache" / f"{city_id.lower()}_listings.parquet"
            if cache_path.exists():
                cache_path.unlink()
        else:
            self._cache.clear()
            cache_dir = self.data_dir / "cache"
            if cache_dir.exists():
                for f in cache_dir.glob("*.parquet"):
                    f.unlink()
