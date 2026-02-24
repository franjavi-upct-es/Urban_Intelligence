# src/features/calendar_features.py
# Urban Intelligence Framework - Calendar and Seasonal Features
# Extracts temporal patterns that affect pricing

"""
Calendar and seasonal feature engineering.

This module creates features based on:
    - Day of week patterns (weekends vs weekdays)
    - Monthly seasonality
    - Holiday effects
    - Special events
    - Booking lead time patterns
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)

# =============================================================================
# Holiday Definitions
# =============================================================================

# Spanish holidays (can be extended for other countries)
SPANISH_HOLIDAYS_2024 = [
    ("2024-01-01", "New Year's Day"),
    ("2024-01-06", "Epiphany"),
    ("2024-03-28", "Maundy Thursday"),
    ("2024-03-29", "Good Friday"),
    ("2024-05-01", "Labour Day"),
    ("2024-08-15", "Assumption"),
    ("2024-10-12", "National Day"),
    ("2024-11-01", "All Saints' Day"),
    ("2024-12-06", "Constitution Day"),
    ("2024-12-08", "Immaculate Conception"),
    ("2024-12-25", "Christmas Day"),
]

SPANISH_HOLIDAYS_2025 = [
    ("2025-01-01", "New Year's Day"),
    ("2025-01-06", "Epiphany"),
    ("2025-04-17", "Maundy Thursday"),
    ("2025-04-18", "Good Friday"),
    ("2025-05-01", "Labour Day"),
    ("2025-08-15", "Assumption"),
    ("2025-10-12", "National Day"),
    ("2025-11-01", "All Saints' Day"),
    ("2025-12-06", "Constitution Day"),
    ("2025-12-08", "Immaculate Conception"),
    ("2025-12-25", "Christmas Day"),
]

# Peak seasons by city
PEAK_SEASONS = {
    "madrid": [(3, 5), (9, 11)],  # Spring and Fall
    "barcelona": [(6, 8)],  # Summer
    "paris": [(4, 6), (9, 10)],  # Spring and Fall
    "london": [(6, 8)],  # Summer
    "amsterdam": [(4, 9)],  # Spring through Summer
    "rome": [(4, 6), (9, 10)],  # Spring and Fall
    "default": [(6, 8)],  # Summer default
}


class CalendarFeatureEngineer:
    """
    Creates calendar-based features for pricing models.

    This class extracts temporal patterns from dates and caledar data
    that are known to affect short-term rental pricing.

    Example:
        >>> engineer = CalendarFeatureEngineer(city="madrid")
        >>> feature_df = engineer.create_features(listings_df, calendar_df)
    """

    def __init__(
        self,
        city: str = "default",
        include_holidays: bool = True,
        include_seasonality: bool = True,
        include_events: bool = True,
    ) -> None:
        """
        Initialize the calendar feature engineer.

        Args:
            city: City name for city-specific patterns
            include_holidays: Whether to include holiday features
            include_seasonality: Whether to include seasonal features
            include_events: Whether to include event features
        """
        self.city = city.lower()
        self.include_holidays = include_holidays
        self.include_seasonality = include_seasonality
        self.include_events = include_events

        # Build holiday lookup
        self.holidays = self._build_holiday_lookup()

        # Get peak seasons for city
        self.peak_seasons = PEAK_SEASONS.get(self.city, PEAK_SEASONS["default"])

    def _build_holiday_lookup(self) -> set[str]:
        """Build a set of holiday dates for fast lookup."""
        holidays = set()

        for date_str, _ in SPANISH_HOLIDAYS_2024 + SPANISH_HOLIDAYS_2025:
            holidays.add(date_str)

        return holidays

    def create_features(
        self,
        df: pl.DataFrame,
        calendar_df: pl.DataFrame | None = None,
        date_column: str = "date",
    ) -> pl.DataFrame:
        """
        Create calendar features.

        Args:
            df: Input DataFrame with listings
            calendar_df: Optional calendar DataFrame with availability/prices
            date_column: Name of date column in calendar_df

        Returns:
            DataFrame with added calendar features
        """
        result_df = df.clone()

        # If we have calendar data, extract features from it
        if calendar_df is not None and date_column in calendar_df.columns:
            result_df = self._add_calendar_features(result_df, calendar_df, date_column)

        # Add static temporal features based on current date
        result_df = self._add_current_temporal_features(result_df)

        logger.info(f"Created calendar features, new columns: {result_df.width - df.width}")

        return result_df

    def _add_calendar_features(
        self,
        df: pl.DataFrame,
        calendar_df: pl.DataFrame,
        date_column: str,
    ) -> pl.DataFrame:
        """
        Add features from calendar data.

        Args:
            df: Listings DataFrame
            calendar_df: Calendar DataFrame with daily data
            date_column: Name of date column

        Returns:
            DataFrame with calendar-derived features
        """
        # Ensure date column is proper date type
        if calendar_df[date_column].dtype != pl.Date:
            calendar_df = calendar_df.with_columns(
                pl.col(date_column).str.to_date().alias(date_column)
            )

        # Add temporal features to calendar
        calendar_with_features = calendar_df.with_columns(
            [
                pl.col(date_column).dt.weekday().alias("day_of_week"),
                pl.col(date_column).dt.month().alias("month"),
                pl.col(date_column).dt.day().alias("day_of_month"),
                pl.col(date_column).dt.week().alias("week_of_year"),
            ]
        )

        # Add derived features
        calendar_with_features = calendar_with_features.with_columns(
            [
                # Week indicator
                (pl.col("day_of_week") >= 5).cast(pl.Int32).alias("is_weekend"),
                # Holiday indicator
                pl.col(date_column)
                .cast(pl.Utf8)
                .is_in(list(self.holidays))
                .cast(pl.Int32)
                .alias("is_holiday"),
            ]
        )

        # Add peak season indicator
        calendar_with_features = self._add_peak_season(calendar_with_features)

        # Aggregate by listings if listing_id exists
        if "listing_id" in calendar_with_features.columns:
            agg_features = calendar_with_features.group_by("listing_id").agg(
                [
                    # Availability patterns
                    pl.col("available").mean().alias("avg_availability"),
                    pl.col("available")
                    .filter(pl.col("is_weekend") == 1)
                    .mean()
                    .alias("weekend_availability"),
                    pl.col("available")
                    .filter(pl.col("is_weekend") == 0)
                    .mean()
                    .alias("weekday_availability"),
                    # Price patterns (if price column exists)
                    pl.col("price").mean().alias("avg_calendar_price")
                    if "price" in calendar_with_features
                    else pl.lit(None).alias("avg_calendar_price"),
                    # Booking patterns
                    pl.col("is_weekend").sum().alias("total_weekend_days"),
                    pl.col("is_holiday").sum().alias("total_holiday_days"),
                    pl.col("is_peak_season").sum().alias("total_peak_days"),
                ]
            )

            # Join back to listings
            if "id" in df.columns:
                df = df.join(agg_features, left_on="id", right_on="listing_id", how="left")

        return df

    def _add_current_temporal_features(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add features based on current date.

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with temporal features
        """
        now = datetime.now()

        # Current temporal context
        current_month = now.month
        current_day_of_week = now.weekday()

        # Is currently peak season
        is_peak = any(start <= current_month <= end for start, end in self.peak_seasons)

        # Days until next holiday
        next_holiday = self._days_until_next_holiday(now)

        # Add features
        df = df.with_columns(
            [
                pl.lit(current_month).alias("current_month"),
                pl.lit(current_day_of_week).alias("current_day_of_week"),
                pl.lit(int(is_peak)).alias("is_current_peak_season"),
                pl.lit(next_holiday).alias("days_until_holiday"),
                pl.lit(int(current_day_of_week >= 5)).alias("is_current_weekend"),
            ]
        )

        return df

    def _add_peak_season(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Add peak season indicator.

        Args:
            df: DataFrame with month column

        Returns:
            DataFrame with peak season feature
        """
        # Build peak season expression
        peak_conditions = []
        for start_month, end_month in self.peak_seasons:
            peak_conditions.append(
                (pl.col("month") >= start_month) & (pl.col("month") <= end_month)
            )

        if peak_conditions:
            peak_expr = peak_conditions[0]
            for cond in peak_conditions[1:]:
                peak_expr = peak_expr | cond

            df = df.with_columns(peak_expr.cast(pl.Int32).alias("is_peak_season"))
        else:
            df = df.with_columns(pl.lit(0).alias("is_peak_season"))

        return df

    def _days_until_next_holiday(self, from_date: datetime) -> int:
        """
        Calculate days until next holiday.

        Args:
            from_date: Starting date

        Returns:
            Number of days until next holiday
        """
        from_date_str = from_date.strftime("%Y-%m-%d")

        future_holidays = [h for h in sorted(self.holidays) if h >= from_date_str]

        if not future_holidays:
            return 365  # Default if not future holidays found

        next_holiday = datetime.strptime(future_holidays[0], "%Y-%m-%d")
        return (next_holiday - from_date).days

    def extract_calendar_statistics(
        self, calendar_df: pl.DataFrame, date_column: str = "date"
    ) -> dict[str, Any]:
        """
        Extract summary statistics from calendar data.

        Args:
            calendar_df: Calendar DataFrame
            date_column: Name of date column

        Returns:
            Dictionary of calendar statistics
        """
        stats: dict[str, Any] = {}

        # Basic stats
        stats["total_days"] = calendar_df.height

        if "available" in calendar_df.columns:
            stats["availability_rate"] = calendar_df["available"].mean()
            stats["total_available_days"] = calendar_df["available"].sum()

        if "price" in calendar_df.columns:
            stats["avg_price"] = calendar_df["price"].mean()
            stats["min_price"] = calendar_df["price"].min()
            stats["max_price"] = calendar_df["price"].max()
            stats["price_std"] = calendar_df["price"].std()

        # Date range
        if date_column in calendar_df.columns:
            dates = calendar_df[date_column]
            if dates.dtype == pl.Utf8:
                dates = dates.str.to_date()
            stats["date_range_start"] = str(dates.min())
            stats["date_range_end"] = str(dates.max())

        return stats


class SeasonalPriceAdjuster:
    """
    Adjusts prices based on seasonal patterns.

    This class learns seasonal price multipliers from historical data
    and can apply them to base prices.
    """

    def __init__(self) -> None:
        """Initialize the seasonal adjuster."""
        self.monthly_multipliers: dict[int, float] = {}
        self.weekday_multipliers: dict[int, float] = {}
        self.holiday_multiplier: float = 1.0
        self.is_fitted: bool = False

    def fit(
        self,
        calendar_df: pl.DataFrame,
        price_column: str = "price",
        date_column: str = "date",
    ) -> SeasonalPriceAdjuster:
        """
        Fit seasonal multipliers from calendar data.

        Args:
            calendar_df: Calendar DataFrame with prices
            price_column: Name of price column
            date_column: Name of date column

        Returns:
            Self for method chaining
        """
        if price_column not in calendar_df.columns:
            logger.warning(f"Price column '{price_column}' not found")
            return self

        # Ensure date column is proper type
        df = calendar_df.clone()
        if df[date_column].dtype == pl.Utf8:
            df = df.with_columns(pl.col(date_column).str.to_date())

        # Add temporal columns
        df = df.with_columns(
            [
                pl.col(date_column).dt.month().alias("month"),
                pl.col(date_column).dt.weekday().alias("weekday"),
            ]
        )

        # Calculate overall average
        overall_avg = df[price_column].mean()

        if overall_avg is None or overall_avg == 0:
            logger.warning("Cannot fit: average price is zero or null")
            return self

        # Calculate monthly multipliers
        monthly_avg = df.group_by("month").agg(pl.col(price_column).mean().alias("avg_price"))

        for row in monthly_avg.iter_rows(named=True):
            self.monthly_multipliers[row["month"]] = row["avg_price"] / overall_avg

        # Calculate weekday multipliers
        weekday_avg = df.group_by("weekday").agg(pl.col(price_column).mean().alias("avg_price"))

        for row in weekday_avg.iter_rows(named=True):
            self.weekday_multipliers[row["weekday"]] = row["avg_price"] / overall_avg

        self.is_fitted = True
        logger.info("Seasonal price adjuster fitted")

        return self

    def adjust_price(
        self,
        base_price: float,
        month: int,
        weekday: int,
        is_holiday: bool = False,
    ) -> float:
        """
        Adjust a base price for seasonal factors.

        Args:
            base_price: Base price to adjust
            month: Day of week (0=Monday, 6=Sunday)
            is_holiday: Whether date is a holiday

        Returns:
            Seasonally adjusted price
        """
        if not self.is_fitted:
            return base_price

        multiplier = 1.0

        # Apply monthly adjustment
        multiplier *= self.monthly_multipliers.get(month, 1.0)

        # Apply weekday adjustment
        multiplier *= self.weekday_multipliers.get(weekday, 1.0)

        # Apply holiday adjustment
        if is_holiday:
            multiplier *= self.holiday_multiplier

        return base_price * multiplier

    def get_multipliers_summary(self) -> dict[str, Any]:
        """
        Get summary of fitted multipliers.

        Returns:
            Dictionary with multiplier information
        """
        return {
            "monthly_multipliers": self.monthly_multipliers,
            "weekday_multipliers": self.weekday_multipliers,
            "holiday_multiplier": self.holiday_multiplier,
            "is_fitted": self.is_fitted,
        }
