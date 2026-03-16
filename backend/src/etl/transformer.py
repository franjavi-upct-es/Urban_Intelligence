# backend/src/etl/transformer.py
# Urban Intelligence Framework v2.0.0
# Feature engineering transformer — converts clean listings to
# ML-ready features

"""
FeatureTransformer module.

Transforms a cleaned Airbnb listings DataFrame into a feature matrix
suitable for XGBoost / LightGBM / CatBoost training. Responsibilities:
- One-hot encoding of categorical columns
- Log transformation of skewed numerical features
- Spatial distance features (distance to city centre)
- Interaction terms (e.g. bedrooms × review_score)
- Feature metadata tracking
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# City centres for distance feature calculation
CITY_CENTRES: dict[str, tuple[float, float]] = {
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "barcelona": (41.3851, 2.1734),
    "new-york": (40.7128, -74.0060),
    "amsterdam": (52.3676, 4.9041),
    "lisbon": (38.7169, -9.1399),
    "madrid": (40.4168, -3.7038),
    "berlin": (52.5200, 13.4050),
    "rome": (41.9028, 12.4964),
    "tokyo": (35.6762, 139.6503),
}


@dataclass
class TransformResult:
    """Output of the feature transformer."""

    features: pl.DataFrame  # Final feature matrix (X)
    target: pl.Series  # Target vector (y = log1p(price))
    feature_names: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    numerical_columns: list[str] = field(default_factory=list)


class FeatureTransformer:
    """
    Transforms a clean Airbnb DataFrame into an ML-ready feature matrix.

    Parameters
    ----------
    city_id : str
        Used to compute distance-to-centre features.
    log_transform_price : bool
        If True, the target will be log1p(price).
    """

    # Categorical columns to one-hot encode
    _CAT_COLS = ["room_type", "property_type", "neighbourhood_cleansed"]

    # Numerical columns to include directly (after imputation)
    _NUM_COLS = [
        "accommodates",
        "bathrooms",
        "bedrooms",
        "beds",
        "amenity_count",
        "minimum_nights",
        "availability_30",
        "availability_60",
        "availability_90",
        "availability_365",
        "number_of_reviews",
        "reviews_per_month",
        "review_scores_rating",
        "review_scores_accuracy",
        "review_scores_cleanliness",
        "review_scores_checkin",
        "review_scores_communication",
        "review_scores_location",
        "review_scores_value",
        "host_response_rate",
        "host_acceptance_rate",
        "host_listings_count",
        "calculated_host_listings_count",
    ]

    # Log-transform these skewed features
    _LOG_COLS = [
        "number_of_reviews",
        "reviews_per_month",
        "host_listings_count",
        "calculated_host_listings_count",
        "minimum_nights",
    ]

    def __init__(
        self, city_id: str = "london", log_transform_price: bool = True
    ) -> None:
        self.city_id = city_id
        self.log_transform_price = log_transform_price
        self._fitted_categories: dict[str, list[str]] = {}

    # ── Public interface ──────────────────────────────────────────────────

    def fit_transform(self, df: pl.DataFrame) -> TransformResult:
        """
        Fit the transformer on df and return transformed features + target.
        """
        logger.info(
            "Starting feature transformation", city=self.city_id, rows=len(df)
        )

        df = self._add_distance_features(df)
        df = self._add_boolean_features(df)
        df = self._add_interaction_features(df)
        df = self._log_transform_numerics(df)
        df, cat_col_names = self._encode_categoricals(df)

        # ── Collect final numeric features ────────────────────────────────
        available_num = [c for c in self._NUM_COLS if c in df.columns]
        log_names = [
            f"log_{c}" for c in self._LOG_COLS if f"log_{c}" in df.columns
        ]
        extra_num = [
            "dist_to_centre",
            "is_superhost_int",
            "is_instant_bookable_int",
            "bedrooms_x_rating",
            "beds_per_bedroom",
        ]
        extra_num = [c for c in extra_num if c in df.columns]

        final_cols = available_num + log_names + extra_num + cat_col_names

        # Remove duplicates while preserving order
        seen: set[str] = set()
        final_cols = [c for c in final_cols if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]

        feature_df = df.select([c for c in final_cols if c in df.columns])

        # ── Target ────────────────────────────────────────────────────────
        if "price" not in df.columns:
            raise ValueError(
                "Column 'price' is required to build the target variable."
            )

        if self.log_transform_price:
            target = df["price"].log1p()
        else:
            target = df["price"]

        logger.info(
            "Feature transformation complete", features=len(feature_df.columns)
        )

        return TransformResult(
            features=feature_df,
            target=target,
            feature_names=feature_df.columns,
            categorical_columns=cat_col_names,
            numerical_columns=[
                c for c in final_cols if c not in cat_col_names
            ],
        )

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Transform new data using previously fitted category mappings.
        Requires fit_transform() to have been called first.
        """
        if not self._fitted_categories:
            raise RuntimeError("Call fit_transform() before transform().")

        df = self._add_distance_features(df)
        df = self._add_boolean_features(df)
        df = self._add_interaction_features(df)
        df = self._log_transform_numerics(df)
        df, _ = self._encode_categoricals(df, use_fitted=True)
        return df

    # ── Private helpers ───────────────────────────────────────────────────

    def _add_distance_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add geodesic distance from listing to city centre (km)."""
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return df

        centre = CITY_CENTRES.get(self.city_id, (0.0, 0.0))
        clat, clon = math.radians(centre[0]), math.radians(centre[1])

        def haversine_km(lat: float, lon: float) -> float:
            rlat, rlon = math.radians(lat), math.radians(lon)
            dlat, dlon = rlat - clat, rlon - clon
            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(rlat) * math.cos(clat) * math.sin(dlon / 2) ** 2
            )
            return 6371.0 * 2 * math.asin(math.sqrt(a))

        distances = [
            haversine_km(lat, lon)
            for lat, lon in zip(
                df["latitude"].to_list(),
                df["longitude"].to_list(),
                strict=False,
            )
        ]
        return df.with_columns(
            pl.Series("dist_to_centre", distances, dtype=pl.Float64)
        )

    def _add_boolean_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Convert boolean columns to integer (0/1) for tree models."""
        if "host_is_superhost" in df.columns:
            df = df.with_columns(
                pl.col("host_is_superhost")
                .cast(pl.Int8)
                .alias("is_superhost_int")
            )
        if "instant_bookable" in df.columns:
            df = df.with_columns(
                pl.col("instant_bookable")
                .cast(pl.Int8)
                .alias("is_instant_bookable_int")
            )
        return df

    def _add_interaction_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """Create interaction terms between important features."""
        if "bedrooms" in df.columns and "review_scores_rating" in df.columns:
            df = df.with_columns(
                (pl.col("bedrooms") * pl.col("review_scores_rating")).alias(
                    "bedrooms_x_rating"
                )
            )
        if "beds" in df.columns and "bedrooms" in df.columns:
            df = df.with_columns(
                (
                    pl.col("beds") / pl.col("bedrooms").clip(lower_bound=1)
                ).alias("beds_per_bedroom")
            )
        return df

    def _log_transform_numerics(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply log1p transform to skewed numerical features."""
        exprs = []
        for col in self._LOG_COLS:
            if col in df.columns:
                exprs.append(
                    pl.col(col)
                    .cast(pl.Float64)
                    .clip(lower_bound=0)
                    .log1p()
                    .alias(f"log_{col}")
                )
        if exprs:
            df = df.with_columns(exprs)
        return df

    def _encode_categoricals(
        self,
        df: pl.DataFrame,
        use_fitted: bool = False,
    ) -> tuple[pl.DataFrame, list[str]]:
        """
        One-hot encode categorical columns.

        When use_fitted=True, uses the categories saved during fit_transform
        to ensure consistent column ordering at inference time.
        """
        new_col_names: list[str] = []

        for col in self._CAT_COLS:
            if col not in df.columns:
                continue

            if use_fitted and col in self._fitted_categories:
                categories = self._fitted_categories[col]
            else:
                categories = sorted(
                    df[col].cast(pl.Utf8).drop_nulls().unique().to_list()
                )
                self._fitted_categories[col] = categories

            for cat in categories:
                safe_name = (
                    f"{col}_{cat.lower().replace(' ', '_').replace('/', '_')}"
                )
                df = df.with_columns(
                    (pl.col(col).cast(pl.Utf8) == cat)
                    .cast(pl.Int8)
                    .alias(safe_name)
                )
                new_col_names.append(safe_name)

        return df, new_col_names
