# backend/src/etl/cleaner.py
# Urban Intelligence Framework v2.0.0
# Polars-based ETL cleaner for raw Airbnb listings

"""
AirbnbCleaner module.

Transforms raw Inside Airbnb CSV data into a clean, analysis-ready
Polars DataFrame. Handles:
- Price string parsing ("$1,234.56" → 1234.56)
- Boolean string normalization ("t"/"f" → True/False)
- Outlier removal using IQR method
- Missing value imputation per column type
- Column subset selection
"""

from __future__ import annotations

import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# Columns to keep from the raw dataset
_KEEP_COLUMNS = [
    "id",
    "name",
    "description",
    "neighborhood_overview",
    "latitude",
    "longitude",
    "neighbourhood_cleansed",
    "property_type",
    "room_type",
    "accommodates",
    "bathrooms",
    "bathrooms_text",
    "bedrooms",
    "beds",
    "amenities",
    "price",
    "minimum_nights",
    "maximum_nights",
    "availability_30",
    "availability_60",
    "availability_90",
    "availability_365",
    "number_of_reviews",
    "number_of_reviews_ltm",
    "review_scores_rating",
    "review_scores_accuracy",
    "review_scores_cleanliness",
    "review_scores_checkin",
    "review_scores_communication",
    "review_scores_location",
    "review_scores_value",
    "reviews_per_month",
    "host_since",
    "host_response_rate",
    "host_acceptance_rate",
    "host_is_superhost",
    "host_listings_count",
    "instant_bookable",
    "calculated_host_listings_count",
]


class AirbnbCleaner:
    """
    Cleans raw Airbnb listings data using Polars lazy evaluation.

    Parameters
    ----------
    price_min : float
        Minimum valid price (rows below this are dropped).
    price_max : float
        Maximum valid price (rows above this are dropped).
    drop_null_threshold : float
        Columns with more than this fraction of nulls are dropped entirely.
    """

    def __init__(
        self,
        price_min: float = 10.0,
        price_max: float = 5000.0,
        drop_null_threshold: float = 0.8,
    ) -> None:
        self.price_min = price_min
        self.price_max = price_max
        self.drop_null_threshold = drop_null_threshold

    def clean(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Execute the full cleaning pipeline.

        Returns a clean Polars DataFrame with standardised columns and types.
        """
        logger.info(
            "Starting ETL cleaning", rows=len(df), cols=len(df.columns)
        )

        # ── 1. Select available columns ───────────────────────────────────
        available = [c for c in _KEEP_COLUMNS if c in df.columns]
        df = df.select(available)

        # ── 2. Parse price column ─────────────────────────────────────────
        if "price" in df.columns:
            df = df.with_columns(
                pl.col("price")
                .cast(pl.Utf8)
                .str.replace_all(r"[$,]", "")
                .cast(pl.Float64, strict=False)
                .alias("price")
            )
            # Drop rows outside valid price range
            df = df.filter(
                pl.col("price").is_not_null()
                & pl.col("price").is_between(self.price_min, self.price_max)
            )

        # ── 3. Boolean columns ────────────────────────────────────────────
        bool_cols = ["host_is_superhost", "instant_bookable"]
        for col in bool_cols:
            if col in df.columns:
                df = df.with_columns(
                    pl.col(col)
                    .cast(pl.Utf8)
                    .str.to_lowercase()
                    .map_elements(lambda v: v == "t", return_dtype=pl.Boolean)
                    .alias(col)
                )

        # ── 4. Percentage columns ─────────────────────────────────────────
        pct_cols = ["host_response_rate", "host_acceptance_rate"]
        for col in pct_cols:
            if col in df.columns:
                df = df.with_columns(
                    pl.col(col)
                    .cast(pl.Utf8)
                    .str.replace("%", "")
                    .cast(pl.Float64, strict=False)
                    .truediv(100.0)
                    .alias(col)
                )

        # ── 5. Numeric coercion ───────────────────────────────────────────
        numeric_cols = [
            "accommodates",
            "bathrooms",
            "bedrooms",
            "beds",
            "minimum_nights",
            "maximum_nights",
            "availability_30",
            "availability_60",
            "availability_90",
            "availability_365",
            "number_of_reviews",
            "number_of_reviews_ltm",
            "review_scores_rating",
            "review_scores_accuracy",
            "review_scores_cleanliness",
            "review_scores_checkin",
            "review_scores_communication",
            "review_scores_location",
            "review_scores_value",
            "reviews_per_month",
            "host_listings_count",
            "calculated_host_listings_count",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df = df.with_columns(
                    pl.col(col).cast(pl.Float64, strict=False).alias(col)
                )

        # ── 6. Latitude / longitude bounds ────────────────────────────────
        if "latitude" in df.columns and "longitude" in df.columns:
            df = df.with_columns(
                [
                    pl.col("latitude").cast(pl.Float64, strict=False),
                    pl.col("longitude").cast(pl.Float64, strict=False),
                ]
            )
            df = df.filter(
                pl.col("latitude").is_between(-90.0, 90.0)
                & pl.col("longitude").is_between(-180.0, 180.0)
            )

        # ── 7. Drop high-null columns ─────────────────────────────────────
        null_fractions = {
            col: df[col].null_count() / max(len(df), 1) for col in df.columns
        }
        high_null_cols = [
            col
            for col, frac in null_fractions.items()
            if frac > self.drop_null_threshold
        ]
        if high_null_cols:
            logger.debug("Dropping high-null columns", cols=high_null_cols)
            df = df.drop(high_null_cols)

        # ── 8. Impute remaining nulls ─────────────────────────────────────
        for col in df.columns:
            dtype = df[col].dtype
            null_count = df[col].null_count()
            if null_count == 0:
                continue
            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32):
                median_val = df[col].median()
                df = df.with_columns(pl.col(col).fill_null(median_val))
            elif dtype == pl.Boolean:
                df = df.with_columns(pl.col(col).fill_null(False))
            else:
                df = df.with_columns(pl.col(col).fill_null("unknown"))

        # ── 9. IQR outlier removal on price ──────────────────────────────
        if "price" in df.columns:
            q1 = df["price"].quantile(0.01)
            q3 = df["price"].quantile(0.99)
            df = df.filter(pl.col("price").is_between(q1, q3))

        # ── 10. Count amenities ───────────────────────────────────────────
        if "amenities" in df.columns and "amenity_count" not in df.columns:
            df = df.with_columns(
                pl.col("amenities")
                .str.count_matches(",")
                .add(1)
                .alias("amenity_count")
            )

        logger.info(
            "ETL cleaning complete", rows=len(df), cols=len(df.columns)
        )
        return df
