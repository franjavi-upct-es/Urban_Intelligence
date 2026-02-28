# src/monitoring/drift_detector.py
# Urban Intelligence Framework - Data and Model Drift Detection
# Detects when data distribution or model performance changes significantly

"""
Drift detection for the Urban Intelligence Framework.

This module implements statistical tests to detect:
    - Data drift: When input feature distributions change
    - Concept drift: When the relationship between features and target changes
    - Model performance degradation

Detection methods:
    - Kolmogorov-Smirnov test for continuous features
    - Chi-squared test for categorical features
    - Population Stability Index (PSI) for overall distribution changes.
    - Performance metric degradation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scipy import stats

logger = logging.getLogger(__name__)


class DriftSeverity(Enum):
    """Severity levels for drift detection."""

    NONE = "none"  # No significant drift
    LOW = "low"  # Minor drift, monitor
    MEDIUM = "medium"  # Moderate drift, consider retraining
    HIGH = "high"  # Significant drift, retraining recommended
    CRITICAL = "critical"  # Severe drift, immediate action needed


@dataclass
class FeatureDriftResult:
    """Result of drift detection for a single feature."""

    feature_name: str
    statistic: float
    p_value: float
    psi: float | None
    drift_detected: bool
    severity: DriftSeverity
    reference_stats: dict[str, float]
    current_stats: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_name": self.feature_name,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "psi": self.psi,
            "drift_detected": self.drift_detected,
            "severity": self.severity.value,
            "reference_stats": self.reference_stats,
            "current_stats": self.current_stats,
        }


@dataclass
class DriftReport:
    """Complete drift detection report."""

    report_time: datetime
    reference_period: str
    current_period: str
    total_features: int
    features_with_drift: int
    overall_severity: DriftSeverity
    feature_results: list[FeatureDriftResult]
    recommendations: list[str] = field(default_factory=list)

    @property
    def drift_percentage(self) -> float:
        """Calculate percentage of features with drift."""
        if self.total_features == 0:
            return 0.0
        return (self.features_with_drift / self.total_features) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_time": self.report_time.isoformat(),
            "reference_period": self.reference_period,
            "current_period": self.current_period,
            "total_features": self.total_features,
            "features_with_drift": self.features_with_drift,
            "overall_severity": self.overall_severity.value,
            "drift_percentage": self.drift_percentage,
            "feature_results": [r.to_dict() for r in self.feature_results],
            "recommendations": self.recommendations,
        }

    def save(self, path: Path) -> None:
        """Save report to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class DriftDetector:
    """
    Detects data and concept drift in ML pipelines.

    This class compares a reference dataset (typically training data)
    with current production data to detect distribution shifts.

    Example:
        >>> detector = DriftDetector()
        >>> detector.set_reference(training_df)
        >>> report = detector.detect_drift(production_df)
        >>> if report.overall_severity >= DriftSeverity.HIGH:
        ...     trigger_retraining()
    """

    # Thesholds for drift severity
    PSI_THRESHOLDS = {
        DriftSeverity.LOW: 0.1,
        DriftSeverity.MEDIUM: 0.2,
        DriftSeverity.HIGH: 0.3,
        DriftSeverity.CRITICAL: 0.5,
    }

    P_VALUE_THRESHOLD = 0.05

    def __init__(
        self,
        numeric_features: list[str] | None = None,
        categorical_features: list[str] | None = None,
    ) -> None:
        """
        Initialize the drift detector.

        Args:
            numeric_features: List of numeric feature names to monitor
            categorical_features: List of categorical feature names to monitor
        """
        self.numeric_features = numeric_features or []
        self.categorical_features = categorical_features or []
        self.reference_data: pl.DataFrame | None = None
        self.reference_stats: dict[str, dict[str, float]] = {}

    def set_reference(self, df: pl.DataFrame) -> None:
        """
        Set the reference dataset for drift comparison.

        Args:
            df: Refernece DataFrame (typically training data)
        """
        self.reference_data = df
        self.reference_stats = self._compute_statistics(df)
        logger.info(f"Reference data set with {df.height} samples.")

    def detect_drift(
        self,
        current_df: pl.DataFrame,
        reference_period: str = "training",
        current_period: str = "production",
    ) -> DriftReport:
        """
        Detect drift between reference and current data.

        Args:
            current_df: Current DataFrame to compare
            reference_period: Label for reference period
            current_period: Label for current period

        Returns:
            DriftReport with detailed results
        """
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference() first.")

        feature_results = []

        # Detect drift in numeric features
        for feature in self.numeric_features:
            if feature in self.reference_data.columns and feature in current_df.columns:
                result = self._detect_numeric_drift(feature, current_df)
                feature_results.append(result)

        # Detect drift in categorical features
        for feature in self.categorical_features:
            if feature in self.reference_data.columns and feature in current_df.columns:
                result = self._detect_categorical_drift(feature, current_df)
                feature_results.append(result)

        # Determine overall severity
        features_with_drift = sum(1 for r in feature_results if r.drift_detected)
        overall_severity = self._determine_overall_severity(feature_results)

        # Generate recommendations
        recommendations = self._generate_recommendations(feature_results, overall_severity)

        return DriftReport(
            report_time=datetime.now(),
            reference_period=reference_period,
            current_period=current_period,
            total_features=len(feature_results),
            features_with_drift=features_with_drift,
            overall_severity=overall_severity,
            feature_results=feature_results,
            recommendations=recommendations,
        )

    def _detect_numeric_drift(self, feature: str, current_df: pl.DataFrame) -> FeatureDriftResult:
        """Detect drift in a numeric feature using KS test."""
        assert self.reference_data is not None
        ref_values = self.reference_data[feature].drop_nulls().to_numpy()
        cur_values = current_df[feature].drop_nulls().to_numpy()

        # Kolmogorov-Smirnov test
        statistic, p_value = stats.ks_2samp(ref_values, cur_values)

        # Calculate PSI
        psi = self._calculate_psi(ref_values, cur_values)

        # Determine drift
        drift_detected = p_value < self.P_VALUE_THRESHOLD
        severity = self._psi_to_severity(psi)

        # Calculate statistics
        ref_stats = {
            "mean": float(np.mean(ref_values)),
            "std": float(np.std(ref_values)),
            "min": float(np.min(ref_values)),
            "max": float(np.max(ref_values)),
            "median": float(np.median(ref_values)),
        }
        cur_stats = {
            "mean": float(np.mean(cur_values)),
            "std": float(np.std(cur_values)),
            "min": float(np.min(cur_values)),
            "max": float(np.max(cur_values)),
            "median": float(np.median(cur_values)),
        }

        return FeatureDriftResult(
            feature_name=feature,
            statistic=float(statistic),
            p_value=float(p_value),
            psi=psi,
            drift_detected=drift_detected,
            severity=severity,
            reference_stats=ref_stats,
            current_stats=cur_stats,
        )

    def _detect_categorical_drift(
        self, feature: str, current_df: pl.DataFrame
    ) -> FeatureDriftResult:
        """Detect drift in a categorical feature using chi-squared test."""
        assert self.reference_data is not None
        ref_counts = self.reference_data[feature].value_counts()
        cur_counts = current_df[feature].value_counts()

        # Align categories
        all_categories = set(ref_counts[feature].to_list()) | set(cur_counts[feature].to_list())

        ref_freq = []
        cur_freq = []

        for cat in all_categories:
            ref_val = ref_counts.filter(pl.col(feature) == cat)["count"]
            cur_val = cur_counts.filter(pl.col(feature) == cat)["count"]

            ref_freq.append(ref_val[0] if len(ref_val) > 0 else 0)
            cur_freq.append(cur_val[0] if len(cur_val) > 0 else 0)

        # Chi-squared test
        ref_arr = np.array(ref_freq, dtype=float) + 1  # Add smoothing
        cur_arr = np.array(cur_freq, dtype=float) + 1

        # Normalize to same total
        ref_arr = ref_arr / ref_arr.sum() * cur_arr.sum()

        statistic, p_value = stats.chisquare(cur_arr, ref_arr)

        # Calculate PSI for categorical
        psi = self._calculate_categorical_psi(ref_arr, cur_arr)

        drift_detected = p_value < self.P_VALUE_THRESHOLD
        severity = self._psi_to_severity(psi)

        return FeatureDriftResult(
            feature_name=feature,
            statistic=float(statistic),
            p_value=float(p_value),
            psi=psi,
            drift_detected=drift_detected,
            severity=severity,
            reference_stats={"n_categories": len(all_categories)},
            current_stats={"n_categories": len(all_categories)},
        )

    def _calculate_psi(self, reference: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
        """Calculate Population Stability Index."""
        # Create bins from reference data
        _, bin_edges = np.histogram(reference, bins=n_bins)

        # Calculate proportions
        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        cur_counts, _ = np.histogram(current, bins=bin_edges)

        # Add smoothing to avoid division by zero
        ref_props = (ref_counts + 1) / (len(reference) + n_bins)
        cur_props = (cur_counts + 1) / (len(current) + n_bins)

        # Calculate PSI
        psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))

        return float(psi)

    def _calculate_categorical_psi(self, ref_freq: np.ndarray, cur_freq: np.ndarray) -> float:
        """Calculate PSI for categorical features."""
        ref_props = ref_freq / ref_freq.sum()
        cur_props = cur_freq / cur_freq.sum()

        # Add small value to avoid log(0)
        ref_props = np.clip(ref_props, 1e-10, 1)
        cur_props = np.clip(cur_props, 1e-10, 1)

        psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))

        return float(psi)

    def _psi_to_severity(self, psi: float) -> DriftSeverity:
        """Convert PSI value to drift severity."""
        if psi >= self.PSI_THRESHOLDS[DriftSeverity.CRITICAL]:
            return DriftSeverity.CRITICAL
        elif psi >= self.PSI_THRESHOLDS[DriftSeverity.HIGH]:
            return DriftSeverity.HIGH
        elif psi >= self.PSI_THRESHOLDS[DriftSeverity.MEDIUM]:
            return DriftSeverity.MEDIUM
        elif psi >= self.PSI_THRESHOLDS[DriftSeverity.LOW]:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _compute_statistics(self, df: pl.DataFrame) -> dict[str, dict[str, float]]:
        """Compute statistics for all monitored features."""
        stats = {}

        for feature in self.numeric_features:
            if feature in df.columns:
                values = df[feature].drop_nulls()
                stats[feature] = {
                    "mean": float(values.mean() or 0),  # type: ignore[arg-type]
                    "std": float(values.std() or 0),  # type: ignore[arg-type]
                    "min": float(values.min() or 0),  # type: ignore[arg-type]
                    "max": float(values.max() or 0),  # type: ignore[arg-type]
                }

        return stats

    def _determine_overall_severity(self, results: list[FeatureDriftResult]) -> DriftSeverity:
        """Determine overall drift severity from individual results."""
        if not results:
            return DriftSeverity.NONE

        # Count severities
        severity_counts = dict.fromkeys(DriftSeverity, 0)
        for r in results:
            severity_counts[r.severity] += 1

        # Determine overall based on worst and count
        if severity_counts[DriftSeverity.CRITICAL] > 0:
            return DriftSeverity.CRITICAL
        elif severity_counts[DriftSeverity.HIGH] >= len(results) * 0.3:
            return DriftSeverity.HIGH
        elif severity_counts[DriftSeverity.MEDIUM] >= len(results) * 0.3:
            return DriftSeverity.MEDIUM
        elif severity_counts[DriftSeverity.LOW] >= len(results) * 0.5:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _generate_recommendations(
        self, results: list[FeatureDriftResult], overall_severity: DriftSeverity
    ) -> list[str]:
        """Generate actionable recommendations based on drift results."""
        recommendations = []

        if overall_severity == DriftSeverity.CRITICAL:
            recommendations.append(
                "URGENT: Significant data drift detected. Immediate model retraining recommended."
            )
        elif overall_severity == DriftSeverity.HIGH:
            recommendations.append(
                "High drift detected. Schedule model retraining within 1-2 weeks."
            )
        elif overall_severity == DriftSeverity.MEDIUM:
            recommendations.append("Moderate drift detected. Monitor closely and plan retraining.")

        # Feature-specific recommendations
        drifted_features = [r for r in results if r.drift_detected]
        if drifted_features:
            feature_names = [f.feature_name for f in drifted_features[:5]]
            recommendations.append(f"Features with significant drift: {', '.join(feature_names)}")

        # Check for specific patterns
        high_drift_features = [
            r for r in results if r.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        ]
        if len(high_drift_features) > len(results) * 0.5:
            recommendations.append(
                "More than half of features show high drift. Consider reviewing data pipeline."
            )

        return recommendations
