# src/validation/expectations.py
# Urban Intelligence Framework - Data Expectations
# Defines data quality expectations and validation logic

"""
Data validation using Great Expectations patterns.

This module defines expectations (validation rules) for:
    - Raw Airbnb listings data
    - Cleaned and transformed data
    - Enriched data with weather and POI features
    - Model input features

The validation system data quality at each pipeline stage.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation failures."""

    WARNING = "warning"  # Log but continue
    ERROR = "error"  # Log and flag, but continue
    CRITICAL = "critical"  # Stop pipeline execution


@dataclass
class ExpectationResult:
    """Result of a single expectation check."""

    expectation_name: str
    success: bool
    observed_value: Any
    expected_value: Any
    severity: ValidationSeverity
    message: str
    column: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validation a dataset."""

    dataset_name: str
    validation_time: datetime
    total_expectations: int
    successful_expectations: int
    failed_expectations: int
    results: list[ExpectationResult]
    overall_success: bool

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (
            (self.successful_expectations / self.total_expectations) * 100
            if self.total_expectations == 0
            else 100.0
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dataset_name": self.dataset_name,
            "validation_time": self.validation_time.isoformat(),
            "total_expectations": self.total_expectations,
            "successful_expectations": self.successful_expectations,
            "failed_expectations": self.failed_expectations,
            "success_rate": self.success_rate,
            "overall_success": self.overall_success,
            "results": [
                {
                    "name": r.expectation_name,
                    "success": r.success,
                    "observed": str(r.observed_value),
                    "expected": str(r.expected_value),
                    "severity": r.severity.value,
                    "message": r.message,
                    "column": r.column,
                }
                for r in self.results
            ],
        }

    def save_report(self, path: Path) -> None:
        """Save validation report to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class DataValidator:
    """
    Validates data against defined expectations.

    This class provides methods to validate DataFrames at different
    stages of the pipeline, ensuring data quality throughout.

    Example:
        >>> validator = DataValidator()
        >>> result = validator.validate_raw_listings(raw_df)
        >>> if not result.overall_success:
        ...     logger.warning(f"Validation failed: {result.failed_expectations} issues")
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """
        Initialize the validator.

        Args:
            strict_mode: If True, treat all failures as critical
        """
        self.strict_mode = strict_mode
        self.results_history: list[ValidationResult] = []

    # =========================================================================
    # Raw Data Validation
    # =========================================================================

    def validate_raw_listings(self, df: pl.DataFrame) -> ValidationResult:
        """
        Validate raw Airbnb listings data.

        Args:
            df: Raw listings DataFrame

        Returns:
            ValidationResult with all expectation results
        """
        results = []

        # Check required columns exists
        required_columns = ["id", "price", "latitude", "longitude"]
        for col in required_columns:
            results.append(self._expect_column_exists(df, col, ValidationSeverity.CRITICAL))

        # Check ID uniqueness
        if "id" in df.columns:
            results.append(self._expect_column_unique(df, "id", ValidationSeverity.ERROR))

        # Check coordinate ranges
        if "latitude" in df.columns:
            results.append(
                self._expect_column_values_between(
                    df, "latitude", -90, 90, ValidationSeverity.ERROR
                )
            )

        if "longitude" in df.columns:
            results.append(
                self._expect_column_values_between(
                    df, "longitude", -180, 180, ValidationSeverity.ERROR
                )
            )

        # Check price column
        if "price" in df.columns:
            results.append(
                self._expect_column_not_null(
                    df, "price", max_null_pct=50, severity=ValidationSeverity.WARNING
                )
            )

        return self._create_validation_result("raw_listings", results)

    def validate_cleaned_listings(self, df: pl.DataFrame) -> ValidationResult:
        """
        Validate cleaned listings data.

        Args:
            df: Cleaned listings DataFrame

        Returns:
            ValidationResult with all expectation checks
        """
        results = []

        # Price should be numeric and positive
        if "price" in df.columns:
            results.append(
                self._expect_column_values_between(df, "price", 1, 50000, ValidationSeverity.ERROR)
            )
            results.append(
                self._expect_column_not_null(
                    df, "price", max_null_pct=5, severity=ValidationSeverity.ERROR
                )
            )

        # Coordinates should have no null after cleaning
        for col in ["latitude", "longitude"]:
            if col in df.columns:
                results.append(
                    self._expect_column_not_null(
                        df, col, max_null_pct=1, severity=ValidationSeverity.ERROR
                    )
                )

        # Room type should be valid
        if "room_type" in df.columns:
            valid_room_types = ["Entire home/apt", "Private room", "Shared room", "Hotel room"]
            results.append(
                self._expect_column_values_in_set(
                    df, "room_type", valid_room_types, ValidationSeverity.WARNING
                )
            )

        # Numeric columns should be reasonable
        if "accommodates" in df.columns:
            results.append(
                self._expect_column_values_between(
                    df, "accommodates", 1, 50, ValidationSeverity.WARNING
                )
            )

        if "bedrooms" in df.columns:
            results.append(
                self._expect_column_values_between(
                    df, "bedrooms", 0, 30, ValidationSeverity.WARNING
                )
            )

        return self._create_validation_result("cleaned_listings", results)

    def validate_enriched_listings(self, df: pl.DataFrame) -> ValidationResult:
        """Validate enriched listings data with weather and POI features.

        Args:
            df: Enriched listings DataFrame

        Returns:
            ValidationResult with all expectation checks
        """
        results = []

        # Check enrichment columns exist
        enrichment_columns = [
            "climate_avg_temp_c",
            "poi_metro_station_count",
            "poi_total_score",
        ]

        for col in enrichment_columns:
            # These are optional - just log if missing
            if col in df.columns:
                results.append(
                    self._expect_column_not_null(
                        df, col, max_null_pct=20, severity=ValidationSeverity.WARNING
                    )
                )

        # POI counts should be non-negative
        poi_count_cols = [c for c in df.columns if c.startswith("poi_") and "count" in c]
        for col in poi_count_cols:
            results.append(
                self._expect_column_values_between(df, col, 0, 10000, ValidationSeverity.WARNING)
            )

        return self._create_validation_result("enriched_listings", results)

    def validate_model_input(
        self, df: pl.DataFrame, feature_columns: list[str]
    ) -> ValidationResult:
        """Validate data before model training/prediction.

        Args:
            df: DataFrame to validate
            feature_columns: List of feature column names

        Returns:
            ValidationResult with all expectation checks
        """
        results = []

        # All feature columns must exist
        for col in feature_columns:
            results.append(self._expect_column_exists(df, col, ValidationSeverity.CRITICAL))

        # No nulls in features
        for col in feature_columns:
            if col in df.columns:
                results.append(
                    self._expect_column_not_null(
                        df, col, max_null_pct=0, severity=ValidationSeverity.CRITICAL
                    )
                )

        # Check for infinite values
        numeric_cols = [
            c
            for c in feature_columns
            if c in df.columns and df[c].dtype in [pl.Float64, pl.Float32]
        ]
        for col in numeric_cols:
            results.append(self._expect_no_infinite_values(df, col, ValidationSeverity.CRITICAL))

        return self._create_validation_result("model_input", results)

    # =========================================================================
    # Expectation Methods
    # =========================================================================

    def _expect_column_exists(
        self, df: pl.DataFrame, column: str, severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if column exists in DataFrame."""
        exists = column in df.columns
        return ExpectationResult(
            expectation_name="expect_column_exists",
            success=exists,
            observed_value=column in df.columns,
            expected_value=True,
            severity=severity,
            message=f"Column '{column}' {'exists' if exists else 'is missing'}",
            column=column,
        )

    def _expect_column_unique(
        self, df: pl.DataFrame, column: str, severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if column values are unique."""
        if column not in df.columns:
            return ExpectationResult(
                expectation_name="expect_column_unique",
                success=False,
                observed_value=None,
                expected_value="unique values",
                severity=severity,
                message=f"Column '{column}' does not exist",
                column=column,
            )

        total = df.height
        unique = df[column].n_unique()
        is_unique = total == unique

        return ExpectationResult(
            expectation_name="expect_column_unique",
            success=is_unique,
            observed_value=f"{unique}/{total} unique",
            expected_value="all unique",
            severity=severity,
            message=f"Column '{column}' has {unique}/{total} unique values",
            column=column,
            details={"total": total, "unique": unique, "duplicates": total - unique},
        )

    def _expect_column_not_null(
        self, df: pl.DataFrame, column: str, max_null_pct: float, severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if column has acceptable null percentage."""
        if column not in df.columns:
            return ExpectationResult(
                expectation_name="expect_column_not_null",
                success=False,
                observed_value=None,
                expected_value=f"<= {max_null_pct}% nulls",
                severity=severity,
                message=f"Column '{column}' does not exist",
                column=column,
            )

        null_count = df[column].null_count()
        total = df.height
        null_pct = (null_count / total * 100) if total > 0 else 0
        success = null_pct <= max_null_pct

        return ExpectationResult(
            expectation_name="expect_column_not_null",
            success=success,
            observed_value=f"{null_pct:.2f}% nulls",
            expected_value=f"<= {max_null_pct}% nulls",
            severity=severity,
            message=f"Column '{column}' has {null_pct:.2f}% null values",
            column=column,
            details={"null_count": null_count, "total": total, "null_pct": null_pct},
        )

    def _expect_column_values_between(
        self,
        df: pl.DataFrame,
        column: str,
        min_value: float,
        max_value: float,
        severity: ValidationSeverity,
    ) -> ExpectationResult:
        """Check if column values are within range."""
        if column not in df.columns:
            return ExpectationResult(
                expectation_name="expect_column_values_between",
                success=False,
                observed_value=None,
                expected_value=f"[{min_value}, {max_value}]",
                severity=severity,
                message=f"Column '{column}' does not exist",
                column=column,
            )

        col_min = df[column].min()
        col_max = df[column].max()

        # Handle null values
        if col_min is None or col_max is None:
            return ExpectationResult(
                expectation_name="expect_column_values_between",
                success=False,
                observed_value="all null",
                expected_value=f"[{min_value}, {max_value}]",
                severity=severity,
                message=f"Column '{column}' is all null",
                column=column,
            )

        col_min_f = float(col_min)  # type: ignore[arg-type]
        col_max_f = float(col_max)  # type: ignore[arg-type]
        success = col_min_f >= min_value and col_max_f <= max_value

        return ExpectationResult(
            expectation_name="expect_column_values_between",
            success=success,
            observed_value=f"[{col_min_f}, {col_max_f}]",
            expected_value=f"[{min_value}, {max_value}]",
            severity=severity,
            message=f"Column '{column}' range is [{col_min_f}, {col_max_f}]",
            column=column,
            details={"observed_min": col_min_f, "observed_max": col_max_f},
        )

    def _expect_column_values_in_set(
        self, df: pl.DataFrame, column: str, valid_values: list[Any], severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if column values are in allowed set."""
        if column not in df.columns:
            return ExpectationResult(
                expectation_name="expect_column_values_in_set",
                success=False,
                observed_value=None,
                expected_value=str(valid_values),
                severity=severity,
                message=f"Column '{column}' does not exist",
                column=column,
            )

        unique_values = df[column].unique().to_list()
        invalid_values = [v for v in unique_values if v not in valid_values and v is not None]
        success = len(invalid_values) == 0

        return ExpectationResult(
            expectation_name="expect_column_values_in_set",
            success=success,
            observed_value=str(unique_values[:10]),  # Limit output
            expected_value=str(valid_values),
            severity=severity,
            message=f"Column '{column}' has {len(invalid_values)} invalid values",
            column=column,
            details={"invalid_values": invalid_values[:10], "unique_count": len(unique_values)},
        )

    def _expect_row_count_between(
        self, df: pl.DataFrame, min_count: int, max_count: int, severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if row count is within expected range."""
        count = df.height
        success = min_count <= count <= max_count

        return ExpectationResult(
            expectation_name="expect_row_count_between",
            success=success,
            observed_value=count,
            expected_value=f"[{min_count}, {max_count}]",
            severity=severity,
            message=f"DataFrame has {count} rows",
            details={"row_count": count},
        )

    def _expect_no_infinite_values(
        self, df: pl.DataFrame, column: str, severity: ValidationSeverity
    ) -> ExpectationResult:
        """Check if column has no infinite values."""
        if column not in df.columns:
            return ExpectationResult(
                expectation_name="expect_no_infinite_values",
                success=False,
                observed_value=None,
                expected_value="no infinite values",
                severity=severity,
                message=f"Column '{column}' does not exist",
                column=column,
            )

        inf_count = df.filter(pl.col(column).is_infinite()).height
        success = inf_count == 0

        return ExpectationResult(
            expectation_name="expect_no_infinite_values",
            success=success,
            observed_value=f"{inf_count} infinite values",
            expected_value="0 infinite values",
            severity=severity,
            message=f"Column '{column}' has {inf_count} infinite values",
            column=column,
            details={"infinite_count": inf_count},
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_validation_result(
        self, dataset_name: str, results: list[ExpectationResult]
    ) -> ValidationResult:
        """Create a ValidationResult from expectation results."""
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        # Determine overall success
        critical_failures = any(
            not r.success and r.severity == ValidationSeverity.CRITICAL for r in results
        )
        overall_success = not critical_failures if not self.strict_mode else failed == 0

        result = ValidationResult(
            dataset_name=dataset_name,
            validation_time=datetime.now(),
            total_expectations=len(results),
            successful_expectations=successful,
            failed_expectations=failed,
            results=results,
            overall_success=overall_success,
        )

        self.results_history.append(result)
        return result
