# src/features/feature_store.py
# Urban Intelligence Framework - Feature Store
# Centralized feature management and versioning

"""
Feature Store for the Urban Intelligence Framework.

This module provides:
    - Centralized feature definitions
    - Feature versioning
    - Feature computation and caching
    - Feature serving for training and inference
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Types of features."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BINARY = "binary"
    TEXT = "text"
    TEMPORAL = "temporal"
    FEOSPATIAL = "geospatial"


@dataclass
class FeatureDefinition:
    """Definition of a feature."""

    name: str
    feature_type: FeatureType
    description: str
    version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    transform_fn: Callable | None = None
    default_value: Any = None
    nullable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "feature_type": self.feature_type.value,
            "description": self.description,
            "version": self.version,
            "dependencies": self.dependencies,
            "default_value": self.default_value,
            "nullable": self.nullable,
        }


@dataclass
class FeatureSet:
    """A collection of features."""

    name: str
    features: list[FeatureDefinition]
    description: str = ""
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def feature_names(self) -> list[str]:
        """Get list of feature names."""
        return [f.name for f in self.features]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "features": [f.to_dict() for f in self.features],
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }


class FeatureStore:
    """
    Centralized feature store for ML features.

    Provides:
        - Feature registration and discovery
        - Feature computation with caching
        - Feature versioning
        - Features serving for training/inference

    Example:
        >>> store = FeatureStore()
        >>> store.register_feature(
        ...     name="price_per_person",
        ...     feature_type=FeatureType.NUMERIC,
        ...     description="Price divided by accomodates",
        ...     transform_fn=lambda df: df["price"] / df["accommodates"],
        ... )
        >>> features = store.compute_features(df, ["price_per_person"])
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize the feature store.

        Args:
            cache_dir: Directory for feature cache
            enable_cache: Whether to enable caching
        """
        self.cache_dir = cache_dir or Path("data/feature_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.enable_cache = enable_cache

        self.features: dict[str, FeatureDefinition] = {}
        self.feature_sets: dict[str, FeatureSet] = {}

        # Register built-in features
        self._register_builtin_features()

    def _register_builtin_features(self) -> None:
        """Register built-in feature definitions."""

        # Price features
        self.register_feature(
            name="price_per_person",
            feature_type=FeatureType.NUMERIC,
            description="Nightly price per guest",
            transform_fn=lambda df: (df["price"] / df["accommodates"].clip(1, None)).alias(
                "price_per_person"
            ),
        )

        self.register_feature(
            name="price_per_bedroom",
            feature_type=FeatureType.NUMERIC,
            description="Nightly price per bedroom",
            transform_fn=lambda df: (df["price"] / df["bedrooms"].clip(1, None)).alias(
                "price_per_bedroom"
            ),
        )

        # Capacity features
        self.register_feature(
            name="beds_per_bedroom",
            feature_type=FeatureType.NUMERIC,
            description="Ratio of beds to bedroom",
            transform_fn=lambda df: (df["beds"] / df["bedrooms"].clip(1, None)).alias(
                "beds_per_bedroom"
            ),
        )

        self.register_feature(
            name="bathrooms_per_bedroom",
            feature_type=FeatureType.NUMERIC,
            description="Ratio of bathrooms to bedroom",
            transform_fn=lambda df: (df["bathrooms"] / df["bedrooms"].clip(1, None)).alias(
                "bathrooms_per_bedroom"
            ),
        )

        # Review features
        self.register_feature(
            name="is_highly_rated",
            feature_type=FeatureType.BINARY,
            description="Rating >= 4.5",
            transform_fn=lambda df: (
                (df["review_scores_rating"] >= 4.5).cast(pl.Int32).alias("is_highly_rated")
            ),
        )

        self.register_feature(
            name="reviews_per_availability",
            feature_type=FeatureType.NUMERIC,
            description="Reviews normalized by availability",
            transform_fn=lambda df: (
                df["number_of_reviews"] / (df["availability_365"] + 1) * 365
            ).alias("reviews_per_availability"),
        )

        # Host features
        self.register_feature(
            name="is_professional_host",
            feature_type=FeatureType.BINARY,
            description="Host has 5+ listings",
            transform_fn=lambda df: (
                (df["host_listings_count"] >= 5).cast(pl.Int32).alias("is_professional_host")
            ),
        )

        # Room type encoding
        self.register_feature(
            name="is_entire_home",
            feature_type=FeatureType.BINARY,
            description="Room type is entire home/apt",
            transform_fn=lambda df: (
                (df["room_type"] == "Entire home/apt").cast(pl.Int32).alias("is_entire_home")
            ),
        )

        self.register_feature(
            name="is_private_room",
            feature_type=FeatureType.BINARY,
            description="Room type is private room",
            transform_fn=lambda df: (
                (df["room_type"] == "Private room").cast(pl.Int32).alias("is_private_room")
            ),
        )

        # Create default feature set
        self.create_feature_set(
            name="default",
            feature_names=[
                "price_per_person",
                "beds_per_bedroom",
                "is_highly_rated",
                "is_entire_home",
                "is_private_room",
            ],
            description="Default feature set for price prediction",
        )

        logger.info(f"Registered {len(self.features)} built-in features")

    def register_feature(
        self,
        name: str,
        feature_type: FeatureType,
        description: str,
        transform_fn: Callable | None = None,
        version: str = "1.0.0",
        dependencies: list[str] | None = None,
        default_value: Any = None,
    ) -> FeatureDefinition:
        """
        Register a new feature.

        Args:
            name: Feature name
            feature_type: Type of feature
            description: Feature description
            transform_fn: Function to compute feature
            version: Feature version
            dependencies: List of dependent features
            default_value: Default value for nulls

        Returns:
            Registered feature definition
        """
        feature = FeatureDefinition(
            name=name,
            feature_type=feature_type,
            description=description,
            version=version,
            dependencies=dependencies or [],
            transform_fn=transform_fn,
            default_value=default_value,
        )

        self.features[name] = feature
        logger.debug(f"Register feature: {name}")

        return feature

    def create_feature_set(
        self,
        name: str,
        feature_names: list[str],
        description: str = "",
        version: str = "1.0.0",
    ) -> FeatureSet:
        """
        Create a feature set.

        Args:
            name: Feature set name
            feature_names: List of feature names to include
            description: Feature set description
            version: Feature set version

        Returns:
            Created feature set
        """
        features = []
        for fname in feature_names:
            if fname not in self.features:
                raise ValueError(f"Unknown feature: {fname}")
            features.append(self.features[fname])

        feature_set = FeatureSet(
            name=name, features=features, description=description, version=version
        )

        self.feature_sets[name] = feature_set
        logger.info(f"Created feature set '{name}' with {len(features)} features")

        return feature_set

    def compute_features(
        self,
        df: pl.DataFrame,
        feature_names: list[str] | None = None,
        feature_set: str | None = None,
    ) -> pl.DataFrame:
        """
        Compute features for a DataFrame.

        Args:
            df: Input DataFrame
            feature_names: List of features to compute
            feature_set: Name of feature set to use

        Returns:
            DataFrame with computed features
        """
        # Determine which features to compute
        if feature_set:
            if feature_set not in self.feature_sets:
                raise ValueError(f"Unknown feature set: {feature_set}")
            feature_to_compute = self.feature_sets[feature_set].feature_names
        elif feature_names:
            feature_to_compute = feature_names
        else:
            feature_to_compute = list(self.features.keys())

        # Check cache
        cache_key = self._get_cache_key(df, feature_to_compute)
        if self.enable_cache:
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Loaded {len(feature_to_compute)} features from cache")
                return cached

        # Compute features
        result_df = df.clone()

        for fname in feature_to_compute:
            if fname not in self.features:
                logger.warning(f"Unknown feature: {fname}, skipping")
                continue

            feature = self.features[fname]

            if feature.transform_fn is not None:
                try:
                    new_col = feature.transform_fn(result_df)
                    result_df = result_df.with_columns(new_col)
                except Exception as e:
                    logger.error(f"Failed to compute feature {fname}: {e}")
                    if feature.default_value is not None:
                        result_df = result_df.with_columns(
                            pl.lit(feature.default_value).alias(fname)
                        )

        # Save to cache
        if self.enable_cache:
            self._save_to_cache(cache_key, result_df)

        logger.info(f"Computed {len(feature_to_compute)} features")
        return result_df

    def get_feature_vector(
        self,
        df: pl.DataFrame,
        feature_names: list[str],
    ) -> np.ndarray:
        """
        Get feature matrix as numpy array.

        Args:
            df: DataFrame with features
            feature_names: Features to include

        Returns:
            Feature matrix
        """
        # Ensure features are computed
        df = self.compute_features(df, feature_names)

        # Select and convert
        available = [f for f in feature_names if f in df.columns]
        return df.select(available).to_numpy()

    def list_features(self) -> list[dict[str, Any]]:
        """
        List all registered features.

        Returns:
            List of feature definitions
        """
        return [f.to_dict() for f in self.features.values()]

    def list_feature_sets(self) -> list[dict[str, Any]]:
        """
        List all feature sets.

        Returns:
            List of feature definitions
        """
        return [fs.to_dict() for fs in self.feature_sets.values()]

    def _get_cache_key(self, df: pl.DataFrame, features: list[str]) -> str:
        """Generate cache key for features."""
        # Hash based on data shape and features
        data_hash = hashlib.md5(
            f"{df.height}_{df.width}_{sorted(features)}".encode(), usedforsecurity=False
        ).hexdigest()[:16]
        return data_hash

    def _load_from_cache(self, cache_key: str) -> pl.DataFrame | None:
        """Load features from cache."""
        cache_path = self.cache_dir / f"{cache_key}.parquet"
        if cache_path.exists():
            try:
                return pl.read_parquet(cache_path)
            except Exception:
                return None
        return None

    def _save_to_cache(self, cache_key: str, df: pl.DataFrame) -> None:
        """Save features to cache."""
        cache_path = self.cache_dir / f"{cache_key}.parquet"
        try:
            df.write_parquet(cache_path)
        except Exception as e:
            logger.warning(f"Failed to cache feature: {e}")

    def clear_cache(self) -> None:
        """Clear the feature cache."""
        for f in self.cache_dir.glob("*.parquet"):
            f.unlink()
        logger.info("Cleared feature cache")
