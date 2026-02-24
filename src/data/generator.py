# src/data/generator.py
# Urban Intelligence Framework - Synthetic Data Generator
# Creates realistic test data for development and testing

"""
Synthetic data generator for the Urban Intelligence Framework.

Creates realistic Airbnb-like data for testing and development.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """
    Generates synthetic Airbnb listings data.

    Example:
        >>> generator = SyntheticDataGenerator(n_samples=1000)
        >>> df = generator.generate()
    """

    # Configuration for realistic data generation
    ROOM_TYPES = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
    ROOM_TYPE_WEIGHTS = [0.6, 0.3, 0.05, 0.05]

    PROPERTY_TYPES = [
        "Apartment",
        "House",
        "Condominium",
        "Loft",
        "Townhouse",
        "Villa",
        "Guest suite",
        "Serviced apartment",
    ]

    NEIGHBORHOODS = [
        "Centro",
        "Salamanca",
        "Chamberí",
        "Retiro",
        "Chamartín",
        "Tetuán",
        "Arganzuela",
        "Moncloa",
        "Latina",
        "Carabanchel",
    ]

    def __init__(
        self,
        n_samples: int = 10000,
        seed: int = 42,
        city_center: tuple[float, float] = (40.4168, -3.7038),  # Madrid
        spread: float = 0.05,
    ) -> None:
        """Initialize the generator."""
        self.n_samples = n_samples
        self.seed = seed
        self.city_center = city_center
        self.spread = spread
        self._rng = np.random.default_rng(seed)

    def generate(self) -> pl.DataFrame:
        """Generate synthetic listings data."""
        logger.info(f"Generating {self.n_samples} synthetic listings...")

        # Generate IDs
        ids = list(range(1, self.n_samples + 1))

        # Generate room types
        room_types = self._rng.choice(
            self.ROOM_TYPES,
            size=self.n_samples,
            p=self.ROOM_TYPE_WEIGHTS,
        ).tolist()

        # Generate property types
        property_types = self._rng.choice(
            self.PROPERTY_TYPES,
            size=self.n_samples,
        ).tolist()

        # Generate neighborhoods
        neighborhoods = self._rng.choice(self.NEIGHBORHOODS, size=self.n_samples).tolist()

        # Generate coordinates
        latitudes = self._rng.normal(self.city_center[0], self.spread, self.n_samples).tolist()
        longitudes = self._rng.normal(self.city_center[1], self.spread, self.n_samples).tolist()

        # Generate numeric features
        accommodates = self._rng.integers(1, 12, self.n_samples).tolist()
        bedrooms = [max(1, int(a * 0.4 + self._rng.integers(0, 2))) for a in accommodates]
        beds = [max(1, int(b + self._rng.integers(0, 2))) for b in bedrooms]
        bathrooms = [max(0.5, round(b * 0.6 + self._rng.random() * 0.5, 1)) for b in bedrooms]

        # Generate prices based on features
        base_prices = []
        for i in range(self.n_samples):
            base = 30.0
            if room_types[i] == "Entire home/apt":
                base *= 2.5
            elif room_types[i] == "Private room":
                base *= 1.0
            elif room_types[i] == "Shared room":
                base *= 0.5
            else:
                base *= 1.5

            base += accommodates[i] * 10
            base += bedrooms[i] * 15
            base *= 1 + self._rng.random() * 0.5
            base_prices.append(round(max(20, base), 2))

        # Generate other features
        minimum_nights = self._rng.integers(1, 7, self.n_samples).tolist()
        maximum_nights = self._rng.integers(30, 365, self.n_samples).tolist()
        availability_365 = self._rng.integers(0, 365, self.n_samples).tolist()
        number_of_reviews = self._rng.integers(0, 300, self.n_samples).tolist()
        review_scores = [
            round(3.5 + self._rng.random() * 1.5, 2) if nr > 0 else None for nr in number_of_reviews
        ]
        reviews_per_month = [
            round(nr / 12 + self._rng.random(), 2) if nr > 0 else 0 for nr in number_of_reviews
        ]

        # Generate boolean features
        instant_bookable = self._rng.choice(["t", "f"], self.n_samples, p=[0.4, 0.6]).tolist()
        host_is_superhost = self._rng.choice(["t", "f"], self.n_samples, p=[0.2, 0.8]).tolist()

        # Generate host features
        host_listings_count = self._rng.integers(1, 20, self.n_samples).tolist()

        # Generate names
        names = [f"Cozy {property_types[i]} in {neighborhoods[i]}" for i in range(self.n_samples)]

        # Create DataFrame
        df = pl.DataFrame(
            {
                "id": ids,
                "name": names,
                "latitude": latitudes,
                "longitude": longitudes,
                "room_type": room_types,
                "property_type": property_types,
                "neighborhood_cleansed": neighborhoods,
                "price": base_prices,
                "accomodates": accommodates,
                "bedrooms": bedrooms,
                "beds": beds,
                "bathrooms": bathrooms,
                "minimum_nights": minimum_nights,
                "maximum_nights": maximum_nights,
                "availability_365": availability_365,
                "number_of_reviews": number_of_reviews,
                "review_scores_rating": review_scores,
                "reviews_per_month": reviews_per_month,
                "instant_bookable": instant_bookable,
                "host_is_superhost": host_is_superhost,
                "host_listings_count": host_listings_count,
            }
        )

        logger.info(f"Generated {df.height} listings with {df.width} columns")
        return df
