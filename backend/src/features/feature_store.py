# backend/src/features/feature_store.py
# Urban Intelligence Framework v2.0.0
# Feature store — centralized feature versioning and retrieval

"""
FeatureStore module.

Provides a lightweight feature store with:
- Feature registration and versioning
- Materialized feature sets per city stored as Parquet
- Feature statistics and lineage tracking
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import polars as pl
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


def _to_float(value: object) -> float | None:
    """Safely convert scalar values to float for persisted metadata."""
    return float(value) if isinstance(value, (int, float)) else None


@dataclass
class FeatureSetMeta:
    """Metadata for a registered feature set."""

    name: str
    city_id: str
    version: str
    feature_names: list[str]
    n_rows: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    stats: dict = field(default_factory=dict)


class FeatureStore:
    """
    Lightweight file-based feature store.

    Feature sets are saved as versioned Parquet files under:
        {processed_data_path}/features/{city_id}/{name}_v{version}.parquet

    Metadata is persited as JSON alongside each Parquet file.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        self._base = base_path or (settings.processed_data_path / "features")
        self._base.mkdir(parents=True, exist_ok=True)

    # —— Write ————————————————————————————————————————————————————————————————

    def save(
        self,
        df: pl.DataFrame,
        name: str,
        city_id: str,
        version: str = "1.0",
    ) -> FeatureSetMeta:
        """
        Persist a feature DataFrame to the store.

        Returns the metadata object saved alongside the Parquet file.
        """
        path = self._parquet_path(city_id, name, version)
        path.parent.mkdir(parents=True, exist_ok=True)

        df.write_parquet(path)

        # Compute basic statistics for numeric columns
        numeric_cols = [
            c
            for c in df.columns
            if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64)
        ]
        stats: dict = {}
        for col in numeric_cols[:20]:  # cap at 20 columns to keep meta lean
            s = df[col].drop_nulls()
            if len(s) > 0:
                mean_v = s.mean()
                std_v = s.std()
                min_v = s.min()
                max_v = s.max()
                mean_f = _to_float(mean_v)
                std_f = _to_float(std_v)
                min_f = _to_float(min_v)
                max_f = _to_float(max_v)
                if None in (mean_f, std_f, min_f, max_f):
                    continue
                stats[col] = {
                    "mean": mean_f,
                    "std": std_f,
                    "min": min_f,
                    "max": max_f,
                    "null_count": int(df[col].null_count()),
                }

        meta = FeatureSetMeta(
            name=name,
            city_id=city_id,
            version=version,
            feature_names=df.columns,
            n_rows=len(df),
            stats=stats,
        )

        # Save metadata as JSON
        meta_path = path.with_suffix(".json")
        with meta_path.open("w") as f:
            json.dump(
                {
                    "name": meta.name,
                    "city_id": meta.city_id,
                    "version": meta.version,
                    "feature_names": meta.feature_names,
                    "n_rows": meta.n_rows,
                    "created_at": meta.created_at.isoformat(),
                    "stats": meta.stats,
                },
                f,
                indent=2,
            )

        logger.info(
            "Feature set saved",
            name=name,
            city=city_id,
            version=version,
            rows=len(df),
        )
        return meta

    # —— Read —————————————————————————————————————————————————————————————————

    def load(
        self, name: str, city_id: str, version: str = "1.0"
    ) -> pl.DataFrame:
        """Load a feature set by name, city, and version."""
        path = self._parquet_path(city_id, name, version)
        if not path.exists():
            raise FileNotFoundError(
                f"Feature set '{name}' v{version} for city "
                f"'{city_id}' not found at {path}"
            )
        return pl.read_parquet(path)

    def load_meta(
        self, name: str, city_id: str, version: str = "1.0"
    ) -> FeatureSetMeta:
        """
        Load metadata for a feature set without loading the full DataFrame.
        """
        meta_path = self._parquet_path(city_id, name, version).with_suffix(
            ".json"
        )
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata not found: {meta_path}")
        with meta_path.open() as f:
            data = json.load(f)
        return FeatureSetMeta(
            name=data["name"],
            city_id=data["city_id"],
            version=data["version"],
            feature_names=data["feature_names"],
            n_rows=data["n_rows"],
            created_at=datetime.fromisoformat(data["created_at"]),
            stats=data.get("stats", {}),
        )

    def list_feature_sets(self, city_id: str | None = None) -> list[dict]:
        """
        List all registered feature sets, optionally filtered by city.

        Returns a list of dicts with keys: name, city_id, version, n_rows.
        """
        results = []
        search_root = self._base / city_id if city_id else self._base
        for meta_path in search_root.rglob("*.json"):
            try:
                with meta_path.open() as f:
                    data = json.load(f)
                results.append(
                    {
                        "name": data["name"],
                        "city_id": data["city_id"],
                        "version": data["version"],
                        "n_rows": data["n_rows"],
                        "created_at": data["created_at"],
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Skipping invalid feature metadata",
                    path=str(meta_path),
                    error=str(exc),
                )
        return results

    def exists(self, name: str, city_id: str, version: str = "1.0") -> bool:
        """Return True if a feature set with the given coordinates exists."""
        return self._parquet_path(city_id, name, version).exists()

    # —— Helpers ——————————————————————————————————————————————————————————————

    def _parquet_path(self, city_id: str, name: str, version: str) -> Path:
        return self._base / city_id / f"{name}_v{version}.parquet"
