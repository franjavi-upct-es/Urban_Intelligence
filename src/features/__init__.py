# src/features/__init__.py
# Urban Intelligence Framework - Feature Engineering Module
# Advanced feature extraction for ML models

"""
Feature engineering module for the Urban Intelligence Framework.

This module provides advanced feature extraction capabilities:
    - Calendar and seasonal features
    - Text and sentiment features
    - Geospatial features
    - Price pattern features

Example:
    >>> from src.features import CalendarFeatureEngineer, TextFeatureEngineer
    >>>
    >>> calendar_eng = CalendarFeatureEngineer(city="madrid")
    >>> text_eng = TextFeatureEngineer()
    >>>
    >>> df = calendar_eng.create_features(listings_df, calendar_df)
    >>> df = text_eng.create_features(df, reviews_df)
"""

from src.features.calendar_features import CalendarFeatureEngineer, SeasonalPriceAdjuster
from src.features.feature_store import FeatureDefinition, FeatureSet, FeatureStore, FeatureType
from src.features.text_features import ReviewAggregator, SentimentScore, TextFeatureEngineer

__all__ = [
    # Calendar features
    "CalendarFeatureEngineer",
    "SeasonalPriceAdjuster",
    # Test features
    "TextFeatureEngineer",
    "ReviewAggregator",
    "SentimentScore",
    # Feature store
    "FeatureStore",
    "FeatureDefinition",
    "FeatureSet",
    "FeatureType",
]
