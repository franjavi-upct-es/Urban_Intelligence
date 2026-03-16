# backend/src/validation/expectations.py
# Urban Intelligence Framework v2.0.0

"""
DataValidator module.

Validates DataFrames at each pipeline stage using a declarative rule set.
Modelled after the Great Expectations API but implemented directly with
Polars for zero extra dependencies.

Validation stages:
- raw: basic schema checks on freshly downloaded data
- cleaned: post-ETL quality checks
- enriched: feature-engieered data checks
- model_input: final checks before ML training / inference
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import polars as pl
import structlog

logger = structlog.get_logger(__name__)

# —— Expectation result ———————————————————————————————————————————————————————


@dataclass
class ExpectationResult:
    """Result of a single validation expectation."""

    expectation: str  # human-readable rule name
    column: str | None
    passed: bool
    observed_value: Any
    expected_value: Any
    message: str = ""


@dataclass
class ValidationReport:
    """Summary of all expectations for a single validation run."""

    stage: str
    dataset_name: str
    n_rows: int
    n_columns: int
    results: list[ExpectationResult] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def n_failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def success(self) -> bool:
        """True if all expectations pass."""
        return self.n_failed == 0

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 1.0
        return self.n_passed / len(self.results)


# —— Validator ————————————————————————————————————————————————————————————————


class DataValidator:
    """
    Validates DataFrames against a declarative set of expectations.

    Expectations are plain Python methods that check a single rule and
    return an ExpectationResult.
    """

    # —— Public API ———————————————————————————————————————————————————————————

    def validate(
        self,
        df: pl.DataFrame,
        stage: str,
        dataset_name: str = "dataframe",
    ) -> ValidationReport:
        """
        Run all expectations for the given pipeline stage.

        Args:
            df: DataFrame to validate
            stage: One of "raw" | "cleaned" | "enriched" | "model_input".
            dataset_name: Human-readable name for the report.

        Returns:
            ValidationReport with per-expectation results.
        """
        report = ValidationReport(
            stage=stage,
            dataset_name=dataset_name,
            n_rows=len(df),
            n_columns=len(df.columns),
        )

        stage_rules = self._get_stage_rules(stage)
        for rule_fn in stage_rules:
            results = rule_fn(df)
            if isinstance(results, list):
                report.results.extend(results)
            else:
                report.results.append(results)

        logger.info(
            "Validation complete",
            stage=stage,
            passed=report.n_passed,
            failed=report.n_failed,
            success=report.success,
        )
        return report

    # —— Stage rule sets ——————————————————————————————————————————————————————

    def _get_stage_rules(self, stage: str) -> list[Callable]:
        """Return the list of rule functions for a given pipeline stage."""
        rules: dict[str, list[Callable]] = {
            "raw": [
                self._expect_not_empty,
                self._expect_id_column,
                self._expect_price_column,
                self._expect_lat_lon,
            ],
            "cleaned": [
                self._expect_not_empty,
                self._expect_no_null_price,
                self._expect_price_range,
                self._expect_lat_lon,
                self._expect_room_type_values,
            ],
            "enriched": [
                self._expect_not_empty,
                self._expect_feature_columns,
                self._expect_no_inf_values,
            ],
            "model_input": [
                self._expect_not_empty,
                self._expect_numeric_features,
                self._expect_no_null_features,
                self._expect_no_inf_values,
            ],
        }
        return rules.get(stage, [self._expect_not_empty])

    # —— Individual expectations ——————————————————————————————————————————————

    def _expect_not_empty(self, df: pl.DataFrame) -> ExpectationResult:
        """Dataset must have at least 1 row."""
        return ExpectationResult(
            expectation="expect_row_count_greater_than_zero",
            column=None,
            passed=len(df) > 0,
            observed_value=len(df),
            expected_value=">0",
        )

    def _expect_id_column(self, df: pl.DataFrame) -> list[ExpectationResult]:
        """An 'id' column must exist and have no nulls."""
        results = []
        results.append(
            ExpectationResult(
                expectation="expect_column_to_exist",
                column="id",
                passed="id" in df.columns,
                observed_value="id" in df.columns,
                expected_value=True,
            )
        )
        if "id" in df.columns:
            null_count = df["id"].null_count()
            results.append(
                ExpectationResult(
                    expectation="expect_column_values_to_not_be_null",
                    column="id",
                    passed=null_count == 0,
                    observed_value=null_count,
                    expected_value=0,
                )
            )
        return results

    def _expect_price_column(self, df: pl.DataFrame) -> ExpectationResult:
        """A 'price' column must exist."""
        return ExpectationResult(
            expectation="expect_price_column_to_exist",
            column="price",
            passed="price" in df.columns,
            observed_value="price" in df.columns,
            expected_value=True,
        )

    def _expect_no_null_price(self, df: pl.DataFrame) -> ExpectationResult:
        """Price column must have zero nulls after cleaning."""
        if "price" not in df.columns:
            return ExpectationResult(
                "expect_no_null_price", "price", False, "missing", 0
            )
        null_count = df["price"].null_count()
        return ExpectationResult(
            expectation="expect_column_values_to_not_be_null",
            column="price",
            passed=null_count == 0,
            observed_value=null_count,
            expected_value=0,
        )

    def _expect_price_range(self, df: pl.DataFrame) -> ExpectationResult:
        """All prices must be between $5 and $50,000."""
        if "price" not in df.columns:
            return ExpectationResult(
                "expect_price_range", "price", False, "missing", "[5, 50000]"
            )
        out_of_range = df.filter(
            ~pl.col("price").is_between(5.0, 50_000.0)
        ).height
        return ExpectationResult(
            expectation="expect_column_values_to_be_between",
            column="price",
            passed=out_of_range == 0,
            observed_value=out_of_range,
            expected_value=0,
            message=f"{out_of_range} rows outside [5, 50000]",
        )

    def _expect_lat_lon(self, df: pl.DataFrame) -> list[ExpectationResult]:
        """Latitude must be in [-90, 90] and longitude in [-180, 180]."""
        results = []
        for col, lo, hi in [("latitude", -90, 90), ("longitude", -180, 180)]:
            if col not in df.columns:
                results.append(
                    ExpectationResult(
                        f"expect_{col}_column_exists",
                        col,
                        False,
                        "missing",
                        "present",
                    )
                )
                continue
            bad = df.filter(~pl.col(col).is_between(lo, hi)).height
            results.append(
                ExpectationResult(
                    expectation=f"expect_{col}_in_range",
                    column=col,
                    passed=bad == 0,
                    observed_value=bad,
                    expected_value=0,
                )
            )
        return results

    def _expect_room_type_values(self, df: pl.DataFrame) -> ExpectationResult:
        """Room type must be one of the known Aribnb categories."""
        valid_types = {
            "Entire home/apt",
            "Private room",
            "Shared room",
            "Hotel room",
        }
        if "room_type" not in df.columns:
            return ExpectationResult(
                "expect_room_type_values",
                "room_type",
                True,
                "missing",
                valid_types,
            )
        unexpected = df.filter(
            ~pl.col("room_type").is_in(list(valid_types))
        ).height
        return ExpectationResult(
            expectation="expect_column_values_to_be_in_set",
            column="room_type",
            passed=unexpected == 0,
            observed_value=unexpected,
            expected_value=0,
        )

    def _expect_feature_columns(self, df: pl.DataFrame) -> ExpectationResult:
        """Enriched data must have at least 10 feature columns."""
        n_cols = len(df.columns)
        return ExpectationResult(
            expectation="expect_table_column_count_to_be_greater_than",
            column=None,
            passed=n_cols >= 10,
            observed_value=n_cols,
            expected_value=">=10",
        )

    def _expect_no_inf_values(self, df: pl.DataFrame) -> ExpectationResult:
        """No numeric column should contain infinite values."""
        inf_count = 0
        for col in df.columns:
            if df[col].dtype in (pl.Float64, pl.Float32):
                inf_count += df.filter(pl.col(col).is_infinite()).height
        return ExpectationResult(
            expectation="expect_no_infinite_values",
            column=None,
            passed=inf_count == 0,
            observed_value=inf_count,
            expected_value=0,
        )

    def _expect_numeric_features(self, df: pl.DataFrame) -> ExpectationResult:
        """Model input must contain only numeric columns."""
        non_numeric = [
            c
            for c in df.columns
            if df[c].dtype
            not in (
                pl.Float64,
                pl.Float32,
                pl.Int64,
                pl.Int32,
                pl.Int16,
                pl.Int8,
            )
        ]
        return ExpectationResult(
            expectation="expect_all_features_to_be_numeric",
            column=None,
            passed=len(non_numeric) == 0,
            observed_value=non_numeric,
            expected_value=[],
        )

    def _expect_no_null_features(self, df: pl.DataFrame) -> ExpectationResult:
        """No feature column may have null values at model input stage."""
        total_nulls = sum(df[c].null_count() for c in df.columns)
        return ExpectationResult(
            expectation="expect_no_null_values_in_feature_matrix",
            column=None,
            passed=total_nulls == 0,
            observed_value=total_nulls,
            expected_value=0,
        )
