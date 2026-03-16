# backend/src/config.py
# Urban Intelligence Framework v2.0.0
# Centralized configuration with Pydantic Settings

"""
Centralized configuration module for the Urban Intelligence Framework.

All settings are sourced from environment variables (prefixed URBAN_)
or a .env file, following the 12-factor app methodology.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings with full env-var support."""

    model_config = SettingsConfigDict(
        env_prefix="URBAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Project paths ─────────────────────────────────────────────────────
    project_root: Path = Field(
        default=Path(__file__).parent.parent,
        description="Absolute root of the project",
    )
    database_path: Path = Field(
        default=Path("data/urban_intelligence.db"),
        description="DuckDB database file path",
    )
    raw_data_path: Path = Field(default=Path("data/raw"))
    processed_data_path: Path = Field(default=Path("data/processed"))

    # ── MLflow ────────────────────────────────────────────────────────────
    mlflow_tracking_uri: str = Field(default="http://localhost:5001")
    experiment_name: str = Field(default="airbnb-price-prediction")

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379")

    # ── Model training ────────────────────────────────────────────────────
    n_optuna_trials: int = Field(default=50, ge=10, le=500)
    cv_folds: int = Field(default=5, ge=3, le=10)
    random_seed: int = Field(default=42)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)

    # ── Transfer learning ─────────────────────────────────────────────────
    transfer_learning_enabled: bool = Field(default=True)
    source_cities: str = Field(default="london,paris,barcelona")

    # ── NLP ───────────────────────────────────────────────────────────────
    nlp_model: str = Field(default="distilbert-base-uncased")
    nlp_model_revision: str = Field(default="main")
    nlp_max_length: int = Field(default=128)

    # ── Computer vision ───────────────────────────────────────────────────
    cv_model: str = Field(default="efficientnet_b0")
    cv_batch_size: int = Field(default=32)

    # ── API ───────────────────────────────────────────────────────────────
    api_rate_limit: int = Field(
        default=100, description="Requests per minute per IP"
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000"
    )

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        Field(default="INFO")
    )

    # ── Data generation ───────────────────────────────────────────────────
    n_synthetic_samples: int = Field(default=10_000, ge=1_000, le=100_000)
    price_min: float = Field(default=10.0)
    price_max: float = Field(default=10_000.0)

    @field_validator(
        "database_path", "raw_data_path", "processed_data_path", mode="before"
    )
    @classmethod
    def resolve_paths(cls, v: str | Path) -> Path:
        """Ensure all path fields are proper Path objects."""
        return Path(v)

    def get_source_cities_list(self) -> list[str]:
        """Return source cities as a list, stripping whitespace."""
        return [c.strip() for c in self.source_cities.split(",") if c.strip()]

    def get_cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_directories(self) -> None:
        """Create all required data directories if they don't exist."""
        for path in (self.raw_data_path, self.processed_data_path):
            abs_path = path if path.is_absolute() else self.project_root / path
            abs_path.mkdir(parents=True, exist_ok=True)

        db_dir = (
            self.database_path.parent
            if self.database_path.is_absolute()
            else (self.project_root / self.database_path).parent
        )
        db_dir.mkdir(parents=True, exist_ok=True)


# ── Singleton instance ────────────────────────────────────────────────────
settings = Settings()
