# backend/src/data/__init__.py
# Urban Intelligence Framework v2.0.0
# Data module exports

"""Data acquisition, caching, and synthetic generation."""

from src.data.data_service import CityData, DataService, FetchProgress
from src.data.generator import SyntheticDataGenerator

__all__ = [
    "DataService",
    "CityData",
    "FetchProgress",
    "SyntheticDataGenerator",
]
