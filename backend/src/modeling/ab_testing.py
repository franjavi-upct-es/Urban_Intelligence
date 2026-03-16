# backend/src/modeling/ab_testing.py
# Urban Intelligence Framework v2.0.0
# A/B testing framework with statistical significance testing

"""
ABTestingManager module.

Manages A/B experiments comparing model variants. Supports:
- Traffic splitting with consistent hashing (same user → same variant)
- Metric tracking per variant (RMSE, MAE, latency)
- Statistical significance testing (Welch's t-test, ANOVA)
- Experiment lifecycle: draft → running → paused → completed
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import numpy as np
import structlog
from scipy import stats

from src.database import db

logger = structlog.get_logger(__name__)


class ExperimentStatus(StrEnum):
    """Lifecycle states for an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """A single variant within an A/B experiment."""

    name: str
    model_id: str
    traffic_split: (
        float  # fraction of traffic (0.0 – 1.0); splits must sum to 1.0
    )
    predictions: list[float] = field(default_factory=list)
    actuals: list[float] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)

    @property
    def n_samples(self) -> int:
        return len(self.predictions)

    @property
    def rmse(self) -> float | None:
        if not self.actuals:
            return None
        errors = np.array(self.predictions) - np.array(self.actuals)
        return float(np.sqrt(np.mean(errors**2)))

    @property
    def mae(self) -> float | None:
        if not self.actuals:
            return None
        return float(
            np.mean(
                np.abs(np.array(self.predictions) - np.array(self.actuals))
            )
        )

    @property
    def avg_latency_ms(self) -> float | None:
        return float(np.mean(self.latencies_ms)) if self.latencies_ms else None


@dataclass
class ExperimentResult:
    """Statistical analysis of a completed A/B experiment."""

    experiment_id: str
    winner: str | None  # variant name of the winner, or None if inconclusive
    p_value: float
    is_significant: bool
    confidence_level: float
    variant_metrics: dict[str, dict[str, Any]]
    test_method: str  # "t-test" or "anova"


class ABTestingManager:
    """
    Manages A/B experiments over model predictions.

    Usage example::

        mgr = ABTestingManager()
        exp_id = mgr.create_experiment(
            name="XGBoost vs Ensemble",
            variants=[
                Variant("control", model_id="xgb_v1", traffic_split=0.5),
                Variant("treatment", model_id="ensemble_v2", traffic_split=0.5),
            ],
        )
        mgr.start_experiment(exp_id)
        variant = mgr.assign_variant(exp_id, user_key="listing_12345")
        mgr.record_observation(exp_id, variant.name, predicted=95.0, actual=102.0)
        result = mgr.analyse(exp_id, confidence=0.95)
    """

    def __init__(self) -> None:
        self._experiments: dict[str, dict[str, Any]] = {}

    # ── Experiment lifecycle ──────────────────────────────────────────────

    def create_experiment(
        self,
        name: str,
        variants: list[Variant],
        description: str = "",
    ) -> str:
        """
        Register a new experiment. Returns the experiment ID.
        Traffic splits must sum to approximately 1.0.
        """
        total_split = sum(v.traffic_split for v in variants)
        if abs(total_split - 1.0) > 0.01:
            raise ValueError(
                f"Variant traffic splits must sum to 1.0, got {total_split:.2f}"
            )

        exp_id = f"exp_{uuid.uuid4().hex[:12]}"
        self._experiments[exp_id] = {
            "id": exp_id,
            "name": name,
            "description": description,
            "status": ExperimentStatus.DRAFT,
            "variants": {v.name: v for v in variants},
            "created_at": datetime.now(UTC),
            "started_at": None,
            "ended_at": None,
        }

        # Persist to database
        db.execute(
            "INSERT INTO experiments (experiment_id, name, status, config) VALUES (?, ?, ?, ?)",
            [
                exp_id,
                name,
                ExperimentStatus.DRAFT.value,
                json.dumps(
                    {
                        "description": description,
                        "variants": [
                            {
                                "name": v.name,
                                "model_id": v.model_id,
                                "split": v.traffic_split,
                            }
                            for v in variants
                        ],
                    }
                ),
            ],
        )

        logger.info(
            "Experiment created",
            id=exp_id,
            name=name,
            variants=[v.name for v in variants],
        )
        return exp_id

    def start_experiment(self, experiment_id: str) -> None:
        """Transition experiment from DRAFT to RUNNING."""
        exp = self._get_experiment(experiment_id)
        if exp["status"] != ExperimentStatus.DRAFT:
            raise ValueError(
                f"Can only start DRAFT experiments (current: {exp['status']})"
            )
        exp["status"] = ExperimentStatus.RUNNING
        exp["started_at"] = datetime.now(UTC)
        db.execute(
            "UPDATE experiments SET status = ?, updated_at = ? WHERE experiment_id = ?",
            [
                ExperimentStatus.RUNNING.value,
                datetime.now(UTC).isoformat(),
                experiment_id,
            ],
        )
        logger.info("Experiment started", id=experiment_id)

    def pause_experiment(self, experiment_id: str) -> None:
        """Pause a running experiment."""
        exp = self._get_experiment(experiment_id)
        exp["status"] = ExperimentStatus.PAUSED
        db.execute(
            "UPDATE experiments SET status = ? WHERE experiment_id = ?",
            [ExperimentStatus.PAUSED.value, experiment_id],
        )

    def complete_experiment(self, experiment_id: str) -> ExperimentResult:
        """Stop experiment, run analysis, and return the result."""
        exp = self._get_experiment(experiment_id)
        exp["status"] = ExperimentStatus.COMPLETED
        exp["ended_at"] = datetime.now(UTC)
        db.execute(
            "UPDATE experiments SET status = ? WHERE experiment_id = ?",
            [ExperimentStatus.COMPLETED.value, experiment_id],
        )
        return self.analyse(experiment_id)

    # ── Assignment & observation ──────────────────────────────────────────

    def assign_variant(self, experiment_id: str, user_key: str) -> Variant:
        """
        Deterministically assign a user/listing to a variant using
        consistent hashing. Same user_key always returns same variant.
        """
        exp = self._get_experiment(experiment_id)
        if exp["status"] != ExperimentStatus.RUNNING:
            raise RuntimeError("Experiment is not RUNNING")

        # Consistent hash in [0, 1)
        hash_bytes = hashlib.sha256(
            f"{experiment_id}:{user_key}".encode()
        ).digest()
        hash_value = int.from_bytes(hash_bytes[:4], "big") / (2**32)

        cumulative = 0.0
        variants: list[Variant] = list(exp["variants"].values())
        for variant in variants:
            cumulative += variant.traffic_split
            if hash_value < cumulative:
                return variant

        return variants[-1]  # fallback to last variant

    def record_observation(
        self,
        experiment_id: str,
        variant_name: str,
        predicted: float,
        actual: float | None = None,
        latency_ms: float | None = None,
    ) -> None:
        """Record a prediction (and optionally an actual value) for a variant."""
        exp = self._get_experiment(experiment_id)
        variant = exp["variants"].get(variant_name)
        if variant is None:
            raise ValueError(
                f"Variant '{variant_name}' not found in experiment {experiment_id}"
            )

        variant.predictions.append(predicted)
        if actual is not None:
            variant.actuals.append(actual)
        if latency_ms is not None:
            variant.latencies_ms.append(latency_ms)

    # ── Statistical analysis ──────────────────────────────────────────────

    def analyse(
        self,
        experiment_id: str,
        confidence: float = 0.95,
    ) -> ExperimentResult:
        """
        Run statistical significance tests on variant errors.

        Uses:
        - Welch's t-test for 2 variants
        - One-way ANOVA for 3+ variants
        """
        exp = self._get_experiment(experiment_id)
        variants: dict[str, Variant] = exp["variants"]

        error_groups: list[np.ndarray] = []
        variant_metrics: dict[str, dict[str, Any]] = {}

        for name, v in variants.items():
            if v.actuals:
                errors = np.abs(np.array(v.predictions) - np.array(v.actuals))
                error_groups.append(errors)
            variant_metrics[name] = {
                "n_samples": v.n_samples,
                "rmse": v.rmse,
                "mae": v.mae,
                "avg_latency_ms": v.avg_latency_ms,
            }

        p_value = 1.0
        test_method = "none"

        if len(error_groups) == 2 and all(len(g) > 1 for g in error_groups):
            _, p_value = stats.ttest_ind(*error_groups, equal_var=False)
            test_method = "welch-t-test"
        elif len(error_groups) > 2 and all(len(g) > 1 for g in error_groups):
            _, p_value = stats.f_oneway(*error_groups)
            test_method = "anova"

        is_significant = p_value < (1.0 - confidence)
        winner: str | None = None

        if is_significant:
            # Winner = variant with lowest MAE
            winner = min(
                (name for name, v in variants.items() if v.actuals),
                key=lambda n: variant_metrics[n]["mae"] or float("inf"),
                default=None,
            )

        result = ExperimentResult(
            experiment_id=experiment_id,
            winner=winner,
            p_value=float(p_value),
            is_significant=is_significant,
            confidence_level=confidence,
            variant_metrics=variant_metrics,
            test_method=test_method,
        )

        logger.info(
            "Experiment analysed",
            id=experiment_id,
            winner=winner,
            p_value=round(float(p_value), 4),
            significant=is_significant,
        )
        return result

    def list_experiments(self) -> list[dict[str, Any]]:
        """Return metadata for all registered experiments."""
        return [
            {
                "id": exp["id"],
                "name": exp["name"],
                "status": exp["status"].value,
                "created_at": exp["created_at"].isoformat(),
                "variants": list(exp["variants"].keys()),
            }
            for exp in self._experiments.values()
        ]

    # ── Internal helpers ──────────────────────────────────────────────────

    def _get_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Return experiment dict or raise KeyError."""
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment '{experiment_id}' not found")
        return self._experiments[experiment_id]
