# src/modeling/forecasting.py
# Urban Intelligence Framwork - Time Series Price Forecasting
# Predicts future price trends

"""
Time series forecasting for price prediction.

This module provides:
    - Seasonal decomposition
    - Trend analysis
    - Future price forecasting
    - Confidence intervals
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import polars as pl

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Result of a price forecast."""

    dates: list[datetime]
    predictions: list[float]
    lower_bound: list[float]
    upper_bound: list[float]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dates": [d.isoformat() for d in self.dates],
            "predictions": self.predictions,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "confidence": self.confidence,
        }


class PriceForcaster:
    """
    Time series forecaster for Airbnb prices.

    Uses seasonal decomposition and exponential smoothing
    to forecast future prices.

    Example:
        >>> forecaster = PriceForcaster()
        >>> forecaster.fit(historrical_prices)
        >>> forecast = forecaster.forcast(horizon=30)
    """

    def __init__(
        self,
        seasonal_period: int = 7,  # Weely seasonality
        trend_smoothing: float = 0.1,
        seasonal_smoothing: float = 0.3,
    ) -> None:
        """
        Initialize the forecaster.

        Args:
            seasonal_period: Period for seasonality (7 for weekly)
            trend_smoothing: Smoothing factor for trend
            seasonal_smoothing: Smoothing factor for seasonality
        """
        self.seasonal_period = seasonal_period
        self.trend_smoothing = trend_smoothing
        self.seasonal_smoothing = seasonal_smoothing

        self._level: float = 0.0
        self._trend: float = 0.0
        self._seasonal: list[float] = []
        self._residual_std: float = 0.0
        self._is_fitted = False

    def fit(
        self,
        prices: list[float] | np.ndarray,
        dates: list[datetime] | None = None,
    ) -> PriceForcaster:
        """
        Fit the forecaster to historical data.

        Args:
            prices: Historical price values
            dates: Corresponding dates (optional)

        Returns:
            Self for method chaining
        """
        prices = np.array(prices)
        n = len(prices)

        if n < self.seasonal_period * 2:
            raise ValueError(f"Need at least {self.seasonal_period * 2} data points")

        # Initialize components
        self._level = np.mean(prices[: self.seasonal_period])
        self._trend = (
            np.mean(prices[self.seasonal_period : 2 * self.seasonal_period])
            - np.mean(prices[: self.seasonal_period])
        ) / self.seasonal_period

        # Initialize seasonal factors
        self._seasonal = []
        for i in range(self.seasonal_period):
            seasonal_values = prices[i :: self.seasonal_period]
            overall_mean = np.mean(prices)
            self._seasonal.append(
                np.mean(seasonal_values) - overall_mean if overall_mean > 0 else 1.0
            )

        # Holt-Winters triple exponential smoothing
        fitted_values = []
        for t in range(n):
            season_idx = t % self.seasonal_period

            if t == 0:
                fitted_values.append(self._level)
                continue

            # Previous values
            prev_level = self._level
            prev_trend = self._trend

            # Update level
            self._level = self.trend_smoothing * (prices[t] / self._seasonal[season_idx]) + (
                1 - self.trend_smoothing
            ) * (prev_level + prev_trend)

            # Update trend
            self._seasonal[season_idx] = (
                self.seasonal_smoothing * (prices[t] / self._level)
                + (1 - self.seasonal_smoothing) * self._seasonal[season_idx]
            )

            # Fitted value
            fitted = (prev_level + prev_trend) * self._seasonal[season_idx]
            fitted_values.append(fitted)

        # Calculate residual standard deviation
        residuals = prices - np.array(fitted_values)
        self._residual_std = np.std(residuals)

        self._is_fitted = True
        logger.info(f"Fitted forecaster on {n} data points")

        return self

    def forecast(
        self,
        horizon: int = 30,
        confidence: float = 0.95,
        start_date: datetime | None = None,
    ) -> ForecastResult:
        """
        Generate price forecasts.

        Args:
            horizon: Number of periods to forecast
            confidence: Confidence level for intervals
            start_date: Start date for forecast

        Returns:
            ForecastResult with predictions and intervals
        """
        if not self._is_fitted:
            raise ValueError("Forecaster not fitted. Call fit() first.")

        # Generate forecasts
        predictions = []
        for h in range(1, horizon + 1):
            season_idx = h % self.seasonal_period
            pred = (self._level + h * self._trend) * self._seasonal[season_idx]
            predictions.append(max(0, pred))  # Prices can't be negative

        # Calculate confidence intervals
        # Wider intervals for longer horizons
        from scipy import stats

        z_score = stats.norm.ppf((1 + confidence) / 2)

        lower_bound = []
        upper_bound = []
        for h, pred in enumerate(predictions, 1):
            # Uncertainty grows with horizon
            std = self._residual_std * np.sqrt(h)
            margin = z_score * std
            lower_bound.append(max(0, pred - margin))
            upper_bound.append(pred + margin)

        # Generate dates
        if start_date is None:
            start_date = datetime.now()

        dates = [start_date + timedelta(days=i) for i in range(1, horizon + 1)]

        return ForecastResult(
            dates=dates,
            predictions=predictions,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence=confidence,
        )

    def detect_anomalies(
        self,
        prices: list[float] | np.ndarray,
        threshold: float = 2.0,
    ) -> list[int]:
        """
        Detect price anomalies.

        Args:
            prices: Prices values to check
            threshold: Number of standard deviations for anomaly

        Returns:
            List of anomaly indices
        """
        if not self._is_fitted:
            raise ValueError("Forecaster not fitted. Call fit() first.")

        prices = np.array(prices)
        anomalies = []

        for i, price in enumerate(prices):
            season_idx = i % self.seasonal_period
            expected = self._level * self._seasonal[season_idx]

            if abs(price - expected) > threshold * self._residual_std:
                anomalies.append(i)

        return anomalies

    def get_seasonality(self) -> dict[int, float]:
        """
        Get seasonal factors.

        Returns:
            Dictionary mapping period index to seasonal factor
        """
        return dict(enumerate(self._seasonal))

    def get_trend(self) -> float:
        """
        Get trend component.

        Returns:
            Trend value (positive = increasing, negative = decreasing)
        """
        return self._trend


class SeasonalAnalyzer:
    """
    Analyzes seasonal patterns in princing data.

    Example:
        >>> analyzer = SeasonalAnalyzer()
        >>> patterns = analyzer.analyze(prices_df, date_col="date", price_col="price")
    """

    def __init__(self) -> None:
        """Initialize the analyzer."""
        pass

    def analyze(
        self,
        df: pl.DataFrame,
        date_column: str = "date",
        price_column: str = "price",
    ) -> dict[str, Any]:
        """
        Analyze seasonal patterns.

        Args:
            df: DataFrame with price data
            date_column: Name of date column
            price_column: Name of price column

        Returns:
            Dictionary with seasonal analysis results
        """
        # Ensure date column is datetime
        if df[date_column].dtype != pl.Utf8:
            df = df.with_columns(pl.col(date_column).str.to_date())

        # Add temporal features
        df = df.with_columns(
            [
                pl.col(date_column).dt.weekday().alias("day_of_week"),
                pl.col(date_column).dt.month().alias("month"),
                pl.col(date_column).dt.week().alias("week"),
            ]
        )

        # Day of week patterns
        dow_pattern = (
            df.group_by("day_of_week")
            .agg(pl.col(price_column).mean().alias("avg_price"))
            .sort("day_of_week")
        )

        # Monthly patterns
        monthly_pattern = (
            df.group_by("month").agg(pl.col(price_column).mean().alias("avg_price")).sort("month")
        )

        # Calculate indices relative to overall mean
        overall_mean = df[price_column].mean()

        dow_index = {
            row["day_of_week"]: row["avg_price"] / overall_mean
            for row in dow_pattern.iter_rows(named=True)
        }

        monthly_index = {
            row["month"]: row["avg_price"] / overall_mean
            for row in monthly_pattern.iter_rows(named=True)
        }

        # Identify peak periods
        peak_days = [d for d, idx in dow_index.items() if idx > 1.1]
        peak_months = [m for m, idx in monthly_index.items() if idx > 1.1]

        return {
            "day_of_week_index": dow_index,
            "monthly_pattern": monthly_index,
            "peak_days": peak_days,
            "peak_months": peak_months,
            "overall_mean": overall_mean,
            "weekend_premium": (dow_index.get(5, 1) + dow_index.get(6)) / 2 - 1,
        }
