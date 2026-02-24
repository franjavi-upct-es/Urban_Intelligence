# src/etl/transformer.py
# Urban Intelligence Framework - Feature Transformer
# Feature engineering and encoding

"""
Feature transformation for ML models.

This module handles:
- Feature engineering
- Categorical encoding
- Feature scaling
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class FeatureTransformer:
    """
    Transforms cleaned data into ML-ready features.

    Example:
        >>> transformer = FeatureTransformer()
        >>> features_df = transformer.transform(cleaned_df)
    """

    def __init__(self) -> None:
        """Initialize the transformer."""
        self.fitted = False
        self.categorical_mappings: dict[str, dict[Any, int]] = {}

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Transform the DataFrame."""
        logger.info(f"Starting transformation: {df.height} rows")

        # Step 1: Create derived features
        df = self._create_derived_features(df)

        # Step 2: Encode categorical variables
        df = self._encode_categorical(df)

        # Step 3: Encode boolean variables
        df = self._encode_categorical(df)

        logger.info(f"Transformation complete: {df.width} columns")
        return df

    def _create_derived_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Create derived features."""
        # Price per person
        if "price" in df.columns and "accommodates" in df.columns:
            df = df.with_columns(
                (pl.col("price") / pl.col("accommodates").clip(lower_bound=1)).alias(
                    "price_per_person"
                )
            )

        # Bed to bedroom ratio
        if "beds" in df.columns and "bedrooms" in df.columns:
            df = df.with_columns(
                (pl.col("beds") / pl.col("bedrooms").clip(1, None)).alias("bed_bedroom_ratio")
            )

        # Review frequency
        if "number_of_reviews" in df.columns and "availability_365" in df.columns:
            df = df.with_columns(
                (pl.col("number_of_reviews") / (pl.col("availability_365") + 1) * 365).alias(
                    "review_rate"
                )
            )

        # If highly rated
        if "review_scores_rating" in df.columns:
            df = df.with_columns(
                (pl.col("review_scores_rating") >= 4.5).cast(pl.Int32).alias("is_highly_rated")
            )

        return df

    def _encode_categorical(self, df: pl.DataFrame) -> pl.DataFrame:
        """Encode boolean columns as integers."""
        bool_cols = ["instant_bookable", "host_is_superhost"]

        for col in bool_cols:
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(pl.Int32).alias(f"{col}_encoded"))

        return df
