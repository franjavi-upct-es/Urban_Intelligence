# backend/src/features/calendar_features.py
# Urban Intelligence Framework v2.0.0
# Calendar and seasonal feature engineering for price prediction

"""
CalendarFeatureEngineer module.

Extracts temporal and seasonal signals that influence Airbnb pricing:
- Day of week / month / year
- Season (spring, summer, autumn, winter)
- Public holiday proximity flags
- Weekend indicator
- Peak tourism season flag
"""

from __future__ import annotations

from datetime import date

import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# ── Approximate peak tourism seasons per city ─────────────────────────────
# Format: list of (month_start, month_end) inclusive tuples
PEAK_SEASONS: dict[str, list[tuple[int, int]]] = {
    "london": [(6, 8)],  # Summer
    "paris": [(5, 9)],  # Late spring – early autumn
    "barcelona": [(6, 9)],  # Summer
    "new-york": [(5, 9), (11, 12)],  # Summer + Christmas/NYE
    "amsterdam": [(4, 9)],  # Spring–summer (tulips + summer)
    "lisbon": [(6, 9)],
    "madrid": [(5, 9)],
    "berlin": [(5, 9)],
    "rome": [(4, 10)],  # Long tourist season
    "tokyo": [(3, 5), (9, 11)],  # Cherry blossom + autumn foliage
}


class CalendarFeatureEngineer:
    """
    Enriches a listings DataFrame with calendar-derived features.

    Expected input: DataFrame with at least a 'host_since' date column.
    All generated columns are prefixed with 'cal_'.
    """

    def __init__(
        self, city_id: str = "london", reference_date: date | None = None
    ) -> None:
        self.city_id = city_id
        self.reference_date = reference_date or date.today()

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add calendar features to the DataFrame.

        Added columns:
        - cal_host_tenure_days: days since the host registered
        - cal_host_tenure_years: approximate years of host experience
        - cal_season: 'spring', 'summer', 'autumn', 'winter'
        - cal_is_peak_season: 1 if current month is peak tourism season
        - cal_days_to_weekend: days until next Saturday
        - cal_month: current month (1–12)
        - cal_quarter: current quarter (1–4)
        """
        logger.debug(
            "Adding calendar features", city=self.city_id, rows=len(df)
        )

        ref = self.reference_date

        # ── Host tenure ───────────────────────────────────────────────────
        if "host_since" in df.columns:
            df = df.with_columns(
                pl.col("host_since")
                .cast(pl.Utf8)
                .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                .alias("_host_since_parsed")
            )
            df = df.with_columns(
                [
                    (
                        pl.lit(ref.toordinal())
                        - pl.col("_host_since_parsed")
                        .dt.to_string("%Y-%m-%d")
                        .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
                        .dt.ordinal_day()
                    )
                    .cast(pl.Float64)
                    .alias("cal_host_tenure_days"),
                ]
            ).drop("_host_since_parsed")

            # Simpler version: fill with median if parsing failed
            median_tenure = 365 * 3.0
            df = df.with_columns(
                pl.col("cal_host_tenure_days")
                .fill_null(median_tenure)
                .alias("cal_host_tenure_days")
            )
            df = df.with_columns(
                (pl.col("cal_host_tenure_days") / 365.25).alias(
                    "cal_host_tenure_years"
                )
            )

        # ── Month and quarter ─────────────────────────────────────────────
        df = df.with_columns(
            [
                pl.lit(ref.month).cast(pl.Int8).alias("cal_month"),
                pl.lit((ref.month - 1) // 3 + 1)
                .cast(pl.Int8)
                .alias("cal_quarter"),
            ]
        )

        # ── Season ────────────────────────────────────────────────────────
        season = self._get_season(ref.month)
        df = df.with_columns(pl.lit(season).alias("cal_season"))

        # ── Peak season flag ──────────────────────────────────────────────
        is_peak = self._is_peak_season(self.city_id, ref.month)
        df = df.with_columns(
            pl.lit(int(is_peak)).cast(pl.Int8).alias("cal_is_peak_season")
        )

        # ── Days to weekend ───────────────────────────────────────────────
        # Monday=0 … Sunday=6; Saturday=5, Sunday=6
        weekday = ref.weekday()
        days_to_sat = (5 - weekday) % 7
        df = df.with_columns(
            pl.lit(days_to_sat).cast(pl.Int8).alias("cal_days_to_weekend")
        )

        # ── Is weekend ────────────────────────────────────────────────────
        df = df.with_columns(
            pl.lit(int(weekday >= 5)).cast(pl.Int8).alias("cal_is_weekend")
        )

        logger.debug(
            "Calendar features added",
            new_cols=[c for c in df.columns if c.startswith("cal_")],
        )
        return df

    # ── Static helpers ────────────────────────────────────────────────────

    @staticmethod
    def _get_season(month: int) -> str:
        """Return Northern Hemisphere season name for a given month."""
        if month in (3, 4, 5):
            return "spring"
        elif month in (6, 7, 8):
            return "summer"
        elif month in (9, 10, 11):
            return "autumn"
        else:
            return "winter"

    @staticmethod
    def _is_peak_season(city_id: str, month: int) -> bool:
        """
        Return True if the given month falls within any peak season window.
        """
        windows = PEAK_SEASONS.get(city_id, [(6, 8)])
        return any(start <= month <= end for start, end in windows)
