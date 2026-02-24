# src/validation/__init__.py
# Urban Intelligence Framework - Data Validation Module
# Great Expectations integration for data quality assurance

"""
Data validation module using Great Expectations.

This module provides automated data quality checks and validation
for all data flowing through the pipeline.
"""

from src.validation.expectations import DataValidator, ValidationResult

__all__ = [
    "DataValidator",
    "ValidationResult",
]
