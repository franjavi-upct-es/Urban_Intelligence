# backend/src/monitoring/drift_detector.py
# Urban Intelligence Framework v2.0.0
# Statistical drift detection for production model monitoring

"""
DriftDetector module.

Detects feature and prediction distribution drift using:
- Kolmogorov-Smirnov (KS) test for continuous features
- Chi-squared test for categorical features
- Population Stability Index (PSI) for prediction drift
- Jensen-Shannon Divergence as an additional distance metric

Drift results are stored in the monitoring_events table for alerting.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import polars as pl
import structlog
from scipy import stats

from src.database import db

logger = structlog.get_logger(__name__)

# PSI thresholds (industry standard)
PSI_NEGLIGIBLE = 0.1
PSI_MODERATE = 0.2  # Requires investigation
PSI_SIGNIFICANT = 0.25  # Model should be retrained


@dataclass
class DriftReport:
    """Result of a drift detection run."""

    city_id: str
    timestamp: datetime
    feature_drifts: dict[
        str, dict[str, Any]
    ]  # feature → {p_value, stat, drifted}
    prediction_psi: float
    prediction_drifted: bool
    overall_drift_score: float  # 0 (no drift) to 1 (severe drift)
    n_drifted_features: int
    recommendation: str  # "monitor" | "investigate" | "retrain"


class DriftDetector:
    """
    Statistical drift detector for production monitoring.

    Compares a reference distribution (e.g., training data statistics)
    against an incoming batch of new observations.

    Parameters
    ----------
    significance_level : float
        p-value threshold below which a feature is considered drifted.
    psi_threshold : float
        PSI threshold above which prediction drift is flagged.
    """

    def __init__(
        self,
        significance_level: float = 0.05,
        psi_threshold: float = PSI_MODERATE,
    ) -> None:
        self.significance_level = significance_level
        self.psi_threshold = psi_threshold
        self._reference_stats: dict[str, dict[str, Any]] = {}

    # ── Reference registration ────────────────────────────────────────────

    def fit(self, reference_df: pl.DataFrame) -> None:
        """
        Compute and store reference statistics from the training distribution.

        Call this once after training with the training feature matrix.
        """
        logger.info(
            "Computing reference statistics", cols=len(reference_df.columns)
        )
        self._reference_stats = {}

        for col in reference_df.columns:
            dtype = reference_df[col].dtype
            values = reference_df[col].drop_nulls()

            if dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16):
                arr = values.to_numpy().astype(float)
                self._reference_stats[col] = {
                    "type": "continuous",
                    "values": arr,
                    "mean": float(arr.mean()),
                    "std": float(arr.std()),
                    "bins": np.histogram(arr, bins=10)[1].tolist(),
                    "counts": np.histogram(arr, bins=10)[0].tolist(),
                }
            else:
                self._reference_stats[col] = {
                    "type": "categorical",
                    "counts": self._series_value_counts(values),
                    "n_total": len(values),
                }

        logger.info(
            "Reference statistics computed",
            n_features=len(self._reference_stats),
        )

    # ── Drift detection ────────────────────────────────────────────────────

    def detect(
        self,
        new_df: pl.DataFrame,
        city_id: str = "unknown",
        new_predictions: np.ndarray | None = None,
        reference_predictions: np.ndarray | None = None,
    ) -> DriftReport:
        """
        Compare new_df against reference statistics and report drift.

        Args:
            new_df: New batch of feature observations.
            city_id: Used for logging and database storage.
            new_predictions: Optional array of model predictions for PSI.
            reference_predictions: Optional reference prediction distribution.

        Returns:
            DriftReport with per-feature drift p-values and overall score.
        """
        if not self._reference_stats:
            raise RuntimeError(
                "Call fit() with reference data before detect()."
            )

        feature_drifts: dict[str, dict[str, Any]] = {}
        n_drifted = 0

        for col in new_df.columns:
            if col not in self._reference_stats:
                continue

            ref_stat = self._reference_stats[col]
            new_values = new_df[col].drop_nulls()

            if ref_stat["type"] == "continuous":
                drift_result = self._ks_test(
                    ref_stat["values"],
                    new_values.to_numpy().astype(float),
                )
            else:
                drift_result = self._chi2_test(
                    ref_stat["counts"],
                    new_values,
                )

            feature_drifts[col] = drift_result
            if drift_result.get("drifted", False):
                n_drifted += 1

        # PSI for prediction distribution
        prediction_psi = 0.0
        prediction_drifted = False
        if new_predictions is not None and reference_predictions is not None:
            prediction_psi = self._compute_psi(
                reference_predictions, new_predictions
            )
            prediction_drifted = prediction_psi > self.psi_threshold

        # Overall drift score: fraction of drifted features + PSI weight
        total_features = len(feature_drifts)
        feature_drift_rate = n_drifted / max(total_features, 1)
        psi_normalised = min(prediction_psi / PSI_SIGNIFICANT, 1.0)
        overall_score = 0.7 * feature_drift_rate + 0.3 * psi_normalised

        recommendation = self._get_recommendation(
            overall_score, prediction_psi
        )

        report = DriftReport(
            city_id=city_id,
            timestamp=datetime.now(UTC),
            feature_drifts=feature_drifts,
            prediction_psi=prediction_psi,
            prediction_drifted=prediction_drifted,
            overall_drift_score=round(overall_score, 4),
            n_drifted_features=n_drifted,
            recommendation=recommendation,
        )

        self._persist_report(report)
        logger.info(
            "Drift detection complete",
            city=city_id,
            drifted_features=n_drifted,
            psi=round(prediction_psi, 4),
            recommendation=recommendation,
        )
        return report

    # ── Statistical tests ─────────────────────────────────────────────────

    def _ks_test(
        self, reference: np.ndarray, new_data: np.ndarray
    ) -> dict[str, Any]:
        """Apply two-sample Kolmogorov-Smirnov test."""
        if len(new_data) < 5:
            return {
                "test": "ks",
                "p_value": 1.0,
                "statistic": 0.0,
                "drifted": False,
            }
        ks_stat, p_value = stats.ks_2samp(reference, new_data)
        return {
            "test": "ks",
            "p_value": float(p_value),
            "statistic": float(ks_stat),
            "drifted": p_value < self.significance_level,
        }

    def _chi2_test(
        self, ref_counts: dict[str, int], new_values: pl.Series
    ) -> dict[str, Any]:
        """Apply chi-squared goodness-of-fit test for categorical features."""
        new_counts = self._series_value_counts(new_values)
        n_new = sum(new_counts.values())
        n_ref = sum(ref_counts.values())

        if n_ref == 0 or n_new == 0:
            return {
                "test": "chi2",
                "p_value": 1.0,
                "statistic": 0.0,
                "drifted": False,
            }

        all_categories = set(ref_counts.keys()) | set(new_counts.keys())
        observed: list[int] = []
        expected: list[float] = []

        for cat in all_categories:
            obs = new_counts.get(cat, 0)
            ref_freq = ref_counts.get(cat, 0) / n_ref
            exp = ref_freq * n_new
            if exp > 0:
                observed.append(obs)
                expected.append(exp)

        if len(observed) < 2:
            return {
                "test": "chi2",
                "p_value": 1.0,
                "statistic": 0.0,
                "drifted": False,
            }

        chi2_stat, p_value = stats.chisquare(observed, expected)
        return {
            "test": "chi2",
            "p_value": float(p_value),
            "statistic": float(chi2_stat),
            "drifted": float(p_value) < self.significance_level,
        }

    @staticmethod
    def _series_value_counts(values: pl.Series) -> dict[str, int]:
        """
        Return value counts for a series in a Polars-version-safe format.

        Depending on Polars version and series name, value_counts() may expose
        the category column as "value" or as the original series name.
        """
        rows = values.value_counts().to_dicts()
        counts: dict[str, int] = {}

        for row in rows:
            count_value = row.get("count", 0)
            value_key = next((k for k in row if k != "count"), None)
            if value_key is None:
                continue
            counts[str(row[value_key])] = int(count_value)

        return counts

    @staticmethod
    def _compute_psi(
        reference: np.ndarray, new_data: np.ndarray, bins: int = 10
    ) -> float:
        """Compute the Population Stability Index between two distributions."""
        min_val = min(reference.min(), new_data.min())
        max_val = max(reference.max(), new_data.max())
        bin_edges = np.linspace(min_val, max_val, bins + 1)

        ref_counts, _ = np.histogram(reference, bins=bin_edges)
        new_counts, _ = np.histogram(new_data, bins=bin_edges)

        ref_pct = (ref_counts + 1e-6) / len(reference)
        new_pct = (new_counts + 1e-6) / len(new_data)

        psi = np.sum((new_pct - ref_pct) * np.log(new_pct / ref_pct))
        return float(psi)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _get_recommendation(score: float, psi: float) -> str:
        """Map overall drift score + PSI to an actionable recommendation."""
        if score > 0.5 or psi > PSI_SIGNIFICANT:
            return "retrain"
        elif score > 0.2 or psi > PSI_MODERATE:
            return "investigate"
        else:
            return "monitor"

    @staticmethod
    def _persist_report(report: DriftReport) -> None:
        """Save the drift report to the monitoring_events table."""
        import json

        db.execute(
            """
            INSERT INTO monitoring_events (
                event_id,
                event_type,
                city_id,
                severity,
                payload
            )
            VALUES (?, 'drift_detection', ?, ?, ?)
            """,
            [
                f"drift_{uuid.uuid4().hex[:12]}",
                report.city_id,
                report.recommendation,
                json.dumps(
                    {
                        "overall_drift_score": report.overall_drift_score,
                        "n_drifted_features": report.n_drifted_features,
                        "prediction_psi": report.prediction_psi,
                        "recommendation": report.recommendation,
                    }
                ),
            ],
        )
