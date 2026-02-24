# src/config.py
# Urban Intelligence Framework - Centralized Configuration
# Uses Pydantic for type-safe settings management

"""
Centralized configuration module for the Urban Intelligence Framework.

This module provides a single source of truth for all configuration parameters
across the application, following the 12-factor app methodology.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="URBAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project paths
    project_root: Path = Field(
        default=Path(__file__).parent.parent, description="Root directory of the project"
    )
    database_path: Path = Field(
        default=Path("data/urban_intelligence.db"), description="Path to the DuckDB database file"
    )
    raw_data_path: Path = Field(
        default=Path("data/raw"), description="Directory for raw input data"
    )
    processed_data_path: Path = Field(
        default=Path("data/processed"), description="Directory for processed data"
    )

    # MLflow configuration
    mlflow_tracking_uri: str = Field(default="mlruns", description="URI for MLflow tracking server")
    experiment_name: str = Field(
        default="airbnb-price-prediction", description="Name of the MLflow experiment"
    )

    # Model training configuration
    n_optuna_trials: int = Field(default=50, ge=10, le=500)
    cv_folds: int = Field(default=5, ge=3, le=10)
    random_seed: int = Field(default=42)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)

    # Logging configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")

    # Data generation settings
    n_synthetic_samples: int = Field(default=10000, ge=1000, le=100000)

    # Feature engineering settings
    price_min: float = Field(default=10.0)
    price_max: float = Field(default=10000.0)

    @field_validator("database_path", "raw_data_path", "processed_data_path", mode="before")
    @classmethod
    def resolve_paths(cls, value: str | Path) -> Path:
        """Convert string paths to Path objects."""
        return Path(value)

    def get_absolute_path(self, relative_path: Path) -> Path:
        """Convert a relative path to absolute path based on project root."""
        if relative_path.is_absolute():
            return relative_path
        return self.project_root / relative_path

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.get_absolute_path(self.raw_data_path),
            self.get_absolute_path(self.processed_data_path),
            self.get_absolute_path(self.database_path).parent,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance - singleton pattern
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None


class FeatureColumns:
    """Centralized definition of feature column names."""

    TARGET: str = "price"

    NUMERIC_FEATURES: list[str] = [
        "accommodates",
        "bedrooms",
        "beds",
        "bathrooms",
        "latitude",
        "longitude",
        "minimum_nights",
        "maximum_nights",
        "availability_365",
        "number_of_reviews",
        "review_scores_rating",
        "reviews_per_month",
        "host_listings_count",
    ]

    CATEGORICAL_FEATURES: list[str] = [
        "neighbourhood_cleansed",
        "property_type",
        "room_type",
        "instant_bookable",
        "host_is_superhost",
    ]

    DERIVED_FEATURES: list[str] = [
        "price_per_person",
        "has_pool",
        "has_wifi",
        "has_parking",
        "has_kitchen",
        "amenity_count",
        "description_length",
    ]

    @classmethod
    def all_features(cls) -> list[str]:
        """Get all feature column names."""
        return cls.NUMERIC_FEATURES + cls.CATEGORICAL_FEATURES + cls.DERIVED_FEATURES


__all__ = ["Settings", "get_settings", "reset_settings", "FeatureColumns"]
