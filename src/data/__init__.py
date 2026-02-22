# src/data/__init__.py
# Urban Intelligence Framework - Data Module
# Unified data acquisition, caching, and management

"""
Data Module for the Urban Intelligence Framework.

This module provides a unified interface for all data operations:
    - Automatic discovery of available cities
    - Intelligent caching with DuckBD
    - Multi-source data integration (Airbnb, Weather, POIs)
    - "Fetch one, query fast" architecture
"""

from src.data.data_service import CityData, DataService, FetchProgress
from src.data.generator import SyntheticDataGenerator

__all__ = ["DataService", "CityData", "FetchProgress", "SyntheticDataGenerator"]
