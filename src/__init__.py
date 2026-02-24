# src/__init__.py
# Urban Intelligence Framework - Main Package
# Entry point for the urban intelligence ML framework

"""
Urban Intelligence Framework for Airbnb Price Prediction.

This package provides a complete end-to-end solution for analyzing and predicting
Airbnb rental prices using modern data engineering tools.

Modules:
    - data: Data acquisition, caching, and management
    - etl: Extract, Transform, Load pipelines
    - enrichment: Feature enrichment (spatial, weather)
    - features: Advanced feature engineering
    - modeling: ML model training and optimization
    - monitoring: Drift detection and performance monitoring
    - validation: Data quality validation
    - database: DuckDB management
    - utils: Utility functions
"""

__version__ = "1.0.0"
__author__ = "Urban Intelligence Team"

from src.config import FeatureColumns, get_settings

__all__ = [
    "get_settings",
    "FeatureColumns",
    "__version__",
]
