# src/experiments/ab_testing.py
# Urban Intelligence Framework - A/B Testing Framework
# Compare model versions in production

"""
A/B Testing framework for model comparison.

This module provides:
    - Experiment creation and management
    - Traffic splitting
    - Statistical significance testing
    - Results analysis
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """Status of an experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """A variant in an A/B testing."""

    id: str
    name: str
    model_version: str
    traffic_percentage: float
    predictions: list[tuple[float, float | None]] = field(
        default_factory=list
    )  # (predicted, actual)

    @property
    def prediction_count(self) -> int:
        """Get number of predictions."""
        return len(self.predictions)

    @property
    def mae(self) -> float:
        """Calculate MAE for this variant."""

        if not self.predictions:
            return 0.0
        errors = [abs(p - a) for p, a in self.predictions if a is not None]
        return np.mean(errors) if errors else 0.0

    @property
    def rmse(self) -> float:
        """Calculate RMSE for this variant."""
        if not self.predictions:
            return 0.0
        errors = [(p - a) ** 2 for p, a in self.predictions if a is not None]
        return np.sqrt(np.mean(errors)) if errors else 0.0

    def get_metrics(self) -> dict[str, float]:
        """Get all metrics for this variant."""
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "prediction_count": self.prediction_count,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert variant to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "model_version": self.model_version,
            "traffic_percentage": self.traffic_percentage,
            "prediction_count": self.prediction_count,
            "metrics": self.get_metrics(),
        }


@dataclass
class ExperimentResult:
    """Results of an A/B experiment."""

    winner: str | None
    confidence: float
    lift: float
    p_value: float
    is_significant: bool
    variants: dict[str, dict[str, float]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "winner": self.winner,
            "confidence": self.confidence,
            "lift": self.lift,
            "p_value": self.p_value,
            "is_significant": self.is_significant,
            "variants": self.variants,
        }


@dataclass
class Experiment:
    """An A/B testing experiment."""

    id: str
    name: str
    description: str
    status: ExperimentStatus
    variants: list[Variant]
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
    min_samples_per_variant: int = 100
    confidence_threshold: float = 0.95

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "variants": [v.to_dict() for v in self.variants],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "metrics": self.get_results().to_dict()
            if self.status != ExperimentStatus.DRAFT
            else {},
        }

    def get_results(self) -> ExperimentResult:
        """Get experiment results with statistical analysis."""

        if len(self.variants) < 2:
            return ExperimentResult(
                winner=None,
                confidence=0.0,
                lift=0.0,
                p_value=1.0,
                is_significant=False,
                variants={},
            )

        # Get metrics for each variant
        variant_metrics = {v.id: v.get_metrics() for v in self.variants}

        # Find best variant by MAE
        best_variant = min(self.variants, key=lambda v: v.mae if v.mae > 0 else float("inf"))

        # Statistical significance test (t-test between variants)
        if len(self.variants) == 2:
            v1, v2 = self.variants

            errors1 = [abs(p - a) for p, a in v1.predictions if a is not None]
            errors2 = [abs(p - a) for p, a in v2.predictions if a is not None]

            if len(errors1) >= 30 and len(errors2) >= 30:
                t_stat, p_value = stats.ttest_ind(errors1, errors2)
                is_significant = p_value < (1 - self.confidence_threshold)
                confidence = 1 - p_value
            else:
                p_value = 1.0
                is_significant = False
                confidence = 0.0
        else:
            # For more than 2 variants, use ANOVA
            error_groups = [
                [abs(p - a) for p, a in v.predictions if a is not None] for v in self.variants
            ]

            if all(len(g) >= 30 for g in error_groups):
                f_stat, p_value = stats.f_oneway(*error_groups)
                is_significant = p_value < (1 - self.confidence_threshold)
                confidence = 1 - p_value
            else:
                p_value = 1.0
                is_significant = False
                confidence = 0.0

        # Calculate lift
        baseline = self.variants[0]
        if baseline.mae > 0 and best_variant.mae > 0:
            lift = (baseline.mae - best_variant.mae) / baseline.mae * 100
        else:
            lift = 0.0

        return ExperimentResult(
            winner=best_variant.name if is_significant else None,
            confidence=confidence,
            lift=lift,
            p_value=p_value,
            is_significant=is_significant,
            variants=variant_metrics,
        )


class ABTestingManager:
    """
    Manages A/B testing experiments.

    Example:
        >>> manager = ABTestingManager()
        >>> exp = manager.create_experiment(
        ...     name="XGBoost vs LightGBM",
        ...     variants=[
        ...         {"name": "control", "model_version": "xgb-1.0.0", "traffic": 50},
        ...         {"name": "treatment", "model_version": "lgb-1.0.0", "traffic": 50},
        ...     ]
        ... )
        >>> manager.start_experiment(exp.id)
        >>> variant = manager.assign_variant(exp.id, user_id="user123")
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """
        Initialize the A/B testing manager.

        Args:
            storage_path: Path to store experiment data
        """
        self.storage_path = storage_path or Path("data/experiments")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.experiments: dict[str, Experiment] = {}

        # Load existing experiments
        self._load_experiments()

    def _load_experiments(self) -> None:
        """Load experiments from disk."""
        for path in self.storage_path.glob("*.json"):
            try:
                with open(path) as f:
                    _ = json.load(f)
                # Reconstruct experiment from JSON
                # (simplified - full implementation would deserialize properly)
                logger.debug(f"Loaded experiment from {path}")
            except Exception as e:
                logger.error(f"Failed to load experiment from {path}: {e}")

    def create_experiment(
        self,
        name: str,
        description: str,
        variants: list[dict[str, Any]],
        min_samples: int = 100,
        confidence: float = 0.95,
    ) -> Experiment:
        """
        Create a new experiment.

        Args:
            name: Experiment name
            description: Experiment description
            variants: List of variant configurations
            min_samples: Minimum samples per variant
            confidence: Confidence threshold for significance

        Returns:
            Created Experiment
        """
        exp_id = str(uuid.uuid4())[:8]

        variant_objects = []
        for v in variants:
            variant_objects.append(
                Variant(
                    id=str(uuid.uuid4())[:8],
                    name=v["name"],
                    model_version=v["model_version"],
                    traffic_percentage=v.get("traffic", 50),
                )
            )

        # Normalize traffic percentages
        total_traffic = sum(v.traffic_percentage for v in variant_objects)
        for var in variant_objects:
            var.traffic_percentage = var.traffic_percentage / total_traffic * 100

        experiment = Experiment(
            id=exp_id,
            name=name,
            description=description,
            status=ExperimentStatus.DRAFT,
            variants=variant_objects,
            created_at=datetime.now(),
            min_samples_per_variant=min_samples,
            confidence_threshold=confidence,
        )

        self.experiments[exp_id] = experiment
        self._save_experiment(experiment)

        logger.info(f"Created experiment '{name}' with {len(variants)} variants")
        return experiment

    def start_experiment(self, experiment_id: str) -> Experiment:
        """
        Start an experiment.

        Args:
            experiment_id: ID of the experiment to start

        Returns:
            Updated experiment
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment not found: {experiment_id}")

        if exp.status == ExperimentStatus.RUNNING:
            logger.warning(f"Experiment {experiment_id} already running")
            return exp

        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now()

        self._save_experiment(exp)
        logger.info(f"Stated experiment {experiment_id}")

        return exp

    def stop_experiment(self, experiment_id: str) -> Experiment:
        """
        Stop an experiment.

        Args:
            experiment_id: ID of the experiment to stop

        Returns:
            Updated experiment
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            raise ValueError(f"Experiment not found: {experiment_id}")

        if exp.status != ExperimentStatus.RUNNING:
            logger.warning(f"Experiment {experiment_id} is not running")
            return exp

        exp.status = ExperimentStatus.COMPLETED
        exp.ended_at = datetime.now()

        self._save_experiment(exp)
        logger.info(f"Stopped experiment {experiment_id}")

        return exp

    def assign_variant(
        self,
        experiment_id: str,
        user_id: str,
    ) -> Variant | None:
        """
        Assign a user to a variant.

        Uses consistent hashing to ensure same user always gets same variant.

        Args:
            experiment_id: Experiment ID
            user_id: User identifier

        Returns:
            Assigned variant or None if experiment not running
        """
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            logger.warning(f"Experiment {experiment_id} is not running")
            return None

        # Consisten hashing
        hash_input = f"{experiment_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest(), 16)
        bucket = hash_value % 100

        # Assign to variant based on traffic split
        cumulative: float = 0
        for variant in exp.variants:
            cumulative += variant.traffic_percentage
            if bucket < cumulative:
                logger.debug(f"Assigned user {user_id} to variant {variant.name}")
                return variant

        return exp.variants[-1]  # Fallback to last variant

    def record_prediction(
        self,
        experiment_id: str,
        variant_id: str,
        predicted: float,
        actual: float | None = None,
    ) -> None:
        """
        Record a prediction for an experiment variant.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
            predicted: Predicted value
            actual: Actual value (can be updated later)
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            return

        for variant in exp.variants:
            if variant.id == variant_id:
                variant.predictions.append((predicted, actual))
                break

        # Periodically save
        if sum(v.prediction_count for v in exp.variants) % 100 == 0:
            self._save_experiment(exp)

    def update_actual(
        self,
        experiment_id: str,
        variant_id: str,
        predicted: float,
        actual: float,
    ) -> None:
        """
        Update actual value for a prediction.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
            predicted: Predicted value
            actual: Actual value
        """
        exp = self.experiments.get(experiment_id)
        if not exp:
            return

        for variant in exp.variants:
            if variant.id == variant_id:
                for i, (pred, _) in enumerate(variant.predictions):
                    if abs(pred - predicted) < 0.01:
                        variant.predictions[i] = (predicted, actual)
                        break
                break

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get an experiment by ID."""
        return self.experiments.get(experiment_id)

    def list_experiments(
        self,
        status: ExperimentStatus | None = None,
    ) -> list[Experiment]:
        """
        List all experiments.

        Args:
            status: Filter by status

        Returns:
            List of experiments
        """
        experiments = list(self.experiments.values())

        if status:
            experiments = [e for e in experiments if e.status == status]

        return sorted(experiments, key=lambda e: e.created_at, reverse=True)

    def _save_experiment(self, experiment: Experiment) -> bool:
        """Save experiment to disk."""
        path = self.storage_path / f"{experiment.id}.json"
        with open(path, "w") as f:
            json.dump(experiment.to_dict(), f, indent=2, default=str)
        return True
