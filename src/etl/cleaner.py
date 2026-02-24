# src/etl/cleaner.py
# Urban Intelligence Framework - Data Cleaner
# High-performance data cleaning using Polars

"""
Data cleaning pipeline using Polars.

This module handles common data quality issues:
- Price parsing from strings
- Coordinate validation
- Null handling
- Outlier removal
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class AirbnbCleaner:
    """
    Cleans raw Airbnb listings data.

    Example:
        >>> cleaner = AirbnbCleaner()
        >>> cleaned_df = cleaner.clean(raw_df)
    """

    def __init__(
        self,
        price_min: float = 10.0,
        price_max: float = 10000.0,
        remove_outliers: bool = True,
        outlier_std: float = 3.0,
    ) -> None:
        """Initialize the cleaner."""
        self.price_min = price_min
        self.price_max = price_max
        self.remove_outliers = remove_outliers
        self.outlier_std = outlier_std
        self.cleaning_stats: dict[str, Any] = {}

    def clean(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean the listings DataFrame."""
        logger.info(f"Starting cleaning: {df.height} rows, {df.width} columns")
        initial_rows = df.height

        # Step 1: Clean price column
        df = self._clean_price(df)

        # Step 2: Clean coordinates
        df = self._clean_coordinates(df)

        # Step 3: Clean numeric columns
        df = self._clean_numeric_columns(df)

        # Step 4: Clean categorical columns
        df = self._clean_categorical_columns(df)

        # Step 5: Remove outliers
        if self.remove_outliers:
            df = self._remove_outliers(df)

        # Step 6: Drop rows with null prices
        df = df.filter(pl.col("price").is_not_null())

        # Record stats
        self.cleaning_stats = {
            "initial_rows": initial_rows,
            "final_rows": df.height,
            "rows_removed": initial_rows - df.height,
            "removal_rate": (initial_rows - df.height) / initial_rows * 100
            if initial_rows > 0
            else 0,
        }

        logger.info(
            f"Cleaning complete: {df.height} rows remaining "
            f"({self.cleaning_stats['removal_rate']:.1f}% removed)"
        )
        return df

    def _clean_price(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean price column."""
        if "price" not in df.columns:
            return df

        # If price is string, parse it
        if df["price"].dtype == pl.Utf8:
            df = df.with_columns(
                pl.col("price")
                .str.replace_all(r"[$,€£]", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
                .alias("price")
            )

        # Filter price range
        df = df.filter((pl.col("price") >= self.price_min) & (pl.col("price") <= self.price_max))

        return df

    def _clean_coordinates(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean coordinate columns."""
        if "latitude" in df.columns:
            df = df.filter((pl.col("latitude") >= -90) & (pl.col("latitude") <= 90))

        if "longitude" in df.columns:
            df = df.filter((pl.col("longitude") >= -180) & (pl.col("longitude") <= 180))

        return df

    def _clean_numeric_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean numeric columns."""
        numeric_cols = [
            "accommodates",
            "bedrooms",
            "beds",
            "bathrooms",
            "minimum_nights",
            "maximum_nights",
            "availability_365",
            "number_of_reviews",
            "reviews_per_month",
            "host_listings_count",
        ]

        for col in numeric_cols:
            if col in df.columns:
                # Fill nulls with reasonable defaults
                if col in ["bedrooms", "bathrooms", "beds"]:
                    df = df.with_columns(pl.col(col).fill_null(1))
                elif col in ["reviews_per_month"]:
                    df = df.with_columns(pl.col(col).fill_null(0))

        # Fill review_scores_rating nulls with median or default
        if "review_scores_rating" in df.columns:
            median_score = df["review_scores_rating"].median()
            if median_score is None:
                median_score = 4.5
            df = df.with_columns(pl.col("review_scores_rating").fill_null(median_score))

        return df

    def _clean_categorical_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Clean categorical columns."""
        # Convert boolean-like strings
        bool_cols = ["instant_bookable", "host_is_superhost"]

        for col in bool_cols:
            if col in df.columns and df[col].dtype == pl.Utf8:
                df = df.with_columns(
                    pl.when(pl.col(col).str.to_lowercase().is_in(["t", "true", "1", "yes"]))
                    .then(True)
                    .otherwise(False)
                    .alias(col)
                )

        return df

    def _remove_outliers(self, df: pl.DataFrame) -> pl.DataFrame:
        """Remove price outliers using IQR method."""
        if "price" not in df.columns:
            return df

        prices = df["price"]
        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)

        if q1 is None or q3 is None:
            return df

        q1_val = float(q1)  # type: ignore[arg-type]
        q3_val = float(q3)  # type: ignore[arg-type]
        iqr = q3_val - q1_val
        lower_bound = q1_val - 1.5 * iqr
        upper_bound = q3_val + 1.5 * iqr

        df = df.filter((pl.col("price") >= lower_bound) & (pl.col("price") <= upper_bound))

        return df

    def get_cleaning_report(self) -> dict[str, Any]:
        """Get cleaning statistics report."""
        return self.cleaning_stats
