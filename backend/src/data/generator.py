# backend/src/data/generator.py
# Urban Intelligence Framework v2.0.0
# Synthetic Airbnb listing generator for offline testing and demos

"""
SyntheticDataGenerator module.

Generates realistic-looking Airbnb listings with price labels for use
in tests, CI pipelines, and demo environments where real data is
not available or impractical to fetch.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

# ── City archetypes ───────────────────────────────────────────────────────
# Each archetype defines the statistical profile of listings in that city.

CITY_ARCHETYPES: dict[str, dict] = {
    "london": {
        "price_mean": 150,
        "price_std": 80,
        "neighbourhoods": [
            "Westminster",
            "Chelsea",
            "Shoreditch",
            "Camden",
            "Hackney",
        ],
        "lat_center": 51.5074,
        "lon_center": -0.1278,
        "radius": 0.12,
    },
    "paris": {
        "price_mean": 130,
        "price_std": 70,
        "neighbourhoods": [
            "Marais",
            "Montmartre",
            "Saint-Germain",
            "Bastille",
            "Oberkampf",
        ],
        "lat_center": 48.8566,
        "lon_center": 2.3522,
        "radius": 0.08,
    },
    "barcelona": {
        "price_mean": 110,
        "price_std": 55,
        "neighbourhoods": [
            "Eixample",
            "Gràcia",
            "Born",
            "Barceloneta",
            "Poblenou",
        ],
        "lat_center": 41.3851,
        "lon_center": 2.1734,
        "radius": 0.08,
    },
    "new-york": {
        "price_mean": 200,
        "price_std": 120,
        "neighbourhoods": [
            "Manhattan",
            "Brooklyn",
            "Queens",
            "Williamsburg",
            "Harlem",
        ],
        "lat_center": 40.7128,
        "lon_center": -74.0060,
        "radius": 0.15,
    },
    "amsterdam": {
        "price_mean": 140,
        "price_std": 65,
        "neighbourhoods": [
            "Centrum",
            "De Pijp",
            "Jordaan",
            "Oud-West",
            "Noord",
        ],
        "lat_center": 52.3676,
        "lon_center": 4.9041,
        "radius": 0.05,
    },
}

ROOM_TYPES = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
ROOM_TYPE_WEIGHTS = [0.55, 0.35, 0.05, 0.05]
PROPERTY_TYPES = [
    "Apartment",
    "House",
    "Condo",
    "Loft",
    "Villa",
    "Studio",
    "Townhouse",
]
AMENITIES_POOL = [
    "Wifi",
    "Kitchen",
    "Free parking",
    "Washer",
    "Dryer",
    "Air conditioning",
    "Heating",
    "Pool",
    "Hot tub",
    "Gym",
    "Elevator",
    "Doorman",
    "Smoke detector",
    "Carbon monoxide detector",
    "First aid kit",
    "Fire extinguisher",
]


class SyntheticDataGenerator:
    """
    Generates synthetic Airbnb listing data with realistic price signals.

    Price is determined by a combination of:
    - Base city price level
    - Room type multiplier
    - Number of bedrooms / beds
    - Amenity count
    - Review score (quality signal)
    - Seasonal noise
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed or settings.random_seed)

    def generate(
        self,
        city_id: str = "london",
        n_samples: int | None = None,
    ) -> pl.DataFrame:
        """
        Generate a synthetic listings DataFrame for the given city.

        Args:
            city_id:   City key from CITY_ARCHETYPES (falls back to london).
            n_samples: Number of rows to generate.

        Returns:
            Polars DataFrame with columns matching the Inside Airbnb schema
            subset.
        """
        n = n_samples or settings.n_synthetic_samples
        archetype = CITY_ARCHETYPES.get(city_id, CITY_ARCHETYPES["london"])

        logger.info("Generating synthetic data", city=city_id, n_samples=n)

        # ── IDs ───────────────────────────────────────────────────────────
        ids = [f"SYNTH_{city_id}_{i:07d}" for i in range(n)]

        # ── Location ──────────────────────────────────────────────────────
        lat = self._rng.normal(
            archetype["lat_center"], archetype["radius"], n
        ).tolist()
        lon = self._rng.normal(
            archetype["lon_center"], archetype["radius"], n
        ).tolist()
        neighbourhood = self._rng.choice(
            archetype["neighbourhoods"], n
        ).tolist()

        # ── Room & property types ─────────────────────────────────────────
        room_type = self._rng.choice(
            ROOM_TYPES, n, p=ROOM_TYPE_WEIGHTS
        ).tolist()
        property_type = self._rng.choice(PROPERTY_TYPES, n).tolist()

        # ── Capacity ──────────────────────────────────────────────────────
        bedrooms = self._rng.integers(1, 6, n).tolist()
        beds = [b + self._rng.integers(0, 2) for b in bedrooms]
        bathrooms = self._rng.integers(1, 4, n).tolist()
        accommodates = [b * 2 + self._rng.integers(0, 3) for b in bedrooms]

        # ── Amenities ─────────────────────────────────────────────────────
        amenity_counts = self._rng.integers(5, len(AMENITIES_POOL), n)
        amenities = [
            str(
                self._rng.choice(
                    AMENITIES_POOL,
                    size=int(count),
                    replace=False,
                ).tolist()
            )
            for count in amenity_counts
        ]

        # ── Reviews ───────────────────────────────────────────────────────
        review_scores_rating = self._rng.uniform(3.0, 5.0, n).round(2).tolist()
        number_of_reviews = self._rng.integers(0, 500, n).tolist()

        # ── Availability ──────────────────────────────────────────────────
        availability_365 = self._rng.integers(0, 366, n).tolist()
        minimum_nights = self._rng.choice([1, 2, 3, 7, 14, 30], n).tolist()

        # ── Price (target variable) ───────────────────────────────────────
        room_multiplier = {
            "Entire home/apt": 1.4,
            "Private room": 0.65,
            "Shared room": 0.35,
            "Hotel room": 1.1,
        }
        base_prices = self._rng.normal(
            archetype["price_mean"], archetype["price_std"], n
        )
        multipliers = np.array([room_multiplier[rt] for rt in room_type])
        bedroom_boost = np.array(bedrooms) * 8
        amenity_boost = amenity_counts * 1.5
        review_boost = (np.array(review_scores_rating) - 3.5) * 10
        seasonal_noise = self._rng.normal(0, 5, n)

        raw_prices = (
            base_prices * multipliers
            + bedroom_boost
            + amenity_boost
            + review_boost
            + seasonal_noise
        )
        prices = np.clip(raw_prices, settings.price_min, settings.price_max)

        # ── Host created date ─────────────────────────────────────────────
        base_date = datetime(2012, 1, 1)
        host_since = [
            (
                base_date
                + timedelta(days=int(self._rng.integers(0, 365 * 12)))
            ).strftime("%Y-%m-%d")
            for _ in range(n)
        ]

        return pl.DataFrame(
            {
                "id": ids,
                "latitude": lat,
                "longitude": lon,
                "neighbourhood_cleansed": neighbourhood,
                "room_type": room_type,
                "property_type": property_type,
                "bedrooms": bedrooms,
                "beds": [int(b) for b in beds],
                "bathrooms": bathrooms,
                "accommodates": [int(a) for a in accommodates],
                "amenities": amenities,
                "amenity_count": [int(c) for c in amenity_counts],
                "review_scores_rating": review_scores_rating,
                "number_of_reviews": number_of_reviews,
                "availability_365": availability_365,
                "minimum_nights": minimum_nights,
                "host_since": host_since,
                "price": prices.round(2).tolist(),
            }
        )
