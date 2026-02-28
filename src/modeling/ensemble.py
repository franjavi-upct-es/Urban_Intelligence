# src/modeling/ensemble.py
# Urban Intelligence Framework - Multi-Model Ensemble
# Combines multiple models for improved predictions

"""
Ensemble modeling for the Urban Intelligence Framework.

This module provides:
    - Model stacking and blending
    - Weighted averaging
    - Model selection based on performance
    - Dynamic ensemble weighting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import joblib
import numpy as np

logger = logging.getLogger(__name__)


class PredictorProtocol(Protocol):
    """Protocol for predictors in the ensemble."""

    def predict(self, X: np.ndarray) -> np.ndarray: ...

    def fit(self, X: np.ndarray, y: np.ndarray) -> Any: ...


@dataclass
class ModelInfo:
    """Information about a model in the ensemble."""

    name: str
    model: Any
    weight: float = 1.0
    metrics: dict[str, float] = field(default_factory=dict)
    version: str = "1.0.0"

    @property
    def mae(self) -> float:
        """Get MAE from metrics."""
        return self.metrics.get("mae", float("inf"))


class EnsembleModel:
    """
    Ensemble model combining multiple base models.

    Supports multiple ensemble strategies:
        - Simple averaging
        - Weighted averaging (based on validation performance)
        - Stacking with meta-learner

    Example:
        >>> ensemble = EnsembleModel(strategy="weighted")
        >>> ensemble.add_model("xgboost", xgb_model, weight=0.6)
        >>> ensemble.add_model("lightgbm", lgb_model, weight=0.4)
        >>> predictions = ensemble.predict(X)
    """

    STRATEGIES = ["average", "weighted", "stacking"]

    def __init__(
        self,
        strategy: str = "weighted",
        meta_learner: Any = None,
    ) -> None:
        """Initialize the ensemble.

        Args:
            strategy: Ensemble strategy ('average', 'weighted', 'stacking')
            meta_learner: Meta-learner for stacking strategy
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Strategy must be one of {self.STRATEGIES}")

        self.strategy = strategy
        self.meta_learner = meta_learner
        self.models: dict[str, ModelInfo] = {}
        self._is_fitted = False

    def add_model(
        self,
        name: str,
        model: Any,
        weight: float = 1.0,
        metrics: dict[str, float] | None = None,
        version: str = "1.0.0",
    ) -> None:
        """Add a model to the ensemble.

        Args:
            name: Unique name for the model
            model: Trained model with predict method
            weight: Model weight for weighted averaging
            metrics: Model performance metrics
            version: Model version string
        """
        self.models[name] = ModelInfo(
            name=name,
            model=model,
            weight=weight,
            metrics=metrics or {},
            version=version,
        )
        logger.info(f"Added model '{name}' to ensemble (weight={weight:.2f})")

    def remove_model(self, name: str) -> None:
        """Remove a model from the ensemble.

        Args:
            name: Name of model to remove
        """
        if name in self.models:
            del self.models[name]
            logger.info(f"Removed model '{name}' from ensemble")

    def fit(self, X: np.ndarray, y: np.ndarray) -> EnsembleModel:
        """Fit the ensemble (for stacking strategy).

        Args:
            X: Training features
            y: Training targets

        Returns:
            Self for method chaining
        """
        if self.strategy == "stacking" and self.meta_learner is not None:
            # Generate base model predictions
            base_predictions = self._get_base_predictions(X)

            # Fit meta-learner on base predictions
            self.meta_learner.fit(base_predictions, y)
            logger.info("Fitted meta-learner for stacking ensemble")

        self._is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate ensemble predictions.

        Args:
            X: Features to predict

        Returns:
            Ensemble predictions
        """
        if not self.models:
            raise ValueError("No models in ensemble. Add models first.")

        if self.strategy == "stacking":
            return self._predict_stacking(X)
        elif self.strategy == "weighted":
            return self._predict_weighted(X)
        else:
            return self._predict_average(X)

    def predict_with_uncertainty(
        self,
        X: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate predictions with uncertainty estimates.

        Args:
            X: Features to predict

        Returns:
            Tuple of (predictions, uncertainties)
        """
        predictions = []
        for model_info in self.models.values():
            pred = model_info.model.predict(X)
            predictions.append(pred)

        predictions = np.array(predictions)

        # Mean prediction
        mean_pred = np.mean(predictions, axis=0)

        # Standard deviation as uncertainty
        std_pred = np.std(predictions, axis=0)

        return mean_pred, std_pred

    def _predict_average(self, X: np.ndarray) -> np.ndarray:
        """Simple averaging of predictions."""
        predictions = []
        for model_info in self.models.values():
            pred = model_info.model.predict(X)
            predictions.append(pred)

        return np.mean(predictions, axis=0)

    def _predict_weighted(self, X: np.ndarray) -> np.ndarray:
        """Weighted averaging of predictions."""
        predictions = []
        weights = []

        for model_info in self.models.values():
            pred = model_info.model.predict(X)
            predictions.append(pred)
            weights.append(model_info.weight)

        # Normalize weights
        weights = np.array(weights)
        weights = weights / np.sum(weights)

        # Weighted average
        weighted_preds = np.zeros(len(X))
        for pred, weight in zip(predictions, weights, strict=False):
            weighted_preds += pred * weight

        return weighted_preds

    def _predict_stacking(self, X: np.ndarray) -> np.ndarray:
        """Stacking with meta-learner."""
        if self.meta_learner is None:
            raise ValueError("Meta-learner not set for stacking")

        base_predictions = self._get_base_predictions(X)
        return self.meta_learner.predict(base_predictions)

    def _get_base_predictions(self, X: np.ndarray) -> np.ndarray:
        """Get predictions from all base models."""
        predictions = []
        for model_info in self.models.values():
            pred = model_info.model.predict(X)
            predictions.append(pred)

        return np.column_stack(predictions)

    def optimize_weights(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> dict[str, float]:
        """Optimize model weights based on validation data.

        Args:
            X_val: Validation features
            y_val: Validation targets

        Returns:
            Dictionary of optimized weights
        """
        from scipy.optimize import minimize

        # Get predictions from each model
        predictions = {}
        for name, model_info in self.models.items():
            predictions[name] = model_info.model.predict(X_val)

        def objective(weights: np.ndarray) -> float:
            """Minimize MAE."""
            weights = np.abs(weights)  # Ensure positive
            weights = weights / weights.sum()  # Normalize

            ensemble_pred = np.zeros(len(y_val))
            for i, name in enumerate(self.models.keys()):
                ensemble_pred += predictions[name] * weights[i]

            return np.mean(np.abs(y_val - ensemble_pred))

        # Initial weights
        n_models = len(self.models)
        initial_weights = np.ones(n_models) / n_models

        # Optimize
        result = minimize(
            objective,
            initial_weights,
            method="Nelder-Mead",
            options={"maxiter": 1000},
        )

        # Update weights
        optimized_weights = np.abs(result.x)
        optimized_weights = optimized_weights / optimized_weights.sum()

        for i, name in enumerate(self.models.keys()):
            self.models[name].weight = float(optimized_weights[i])

        logger.info(
            f"Optimized weights: {dict(zip(self.models.keys(), optimized_weights, strict=False))}"
        )

        return {name: self.models[name].weight for name in self.models}

    def get_model_contributions(self) -> dict[str, float]:
        """Get contribution of each model.

        Returns:
            Dictionary of model contributions (normalized weights)
        """
        total_weight = sum(m.weight for m in self.models.values())
        return {name: m.weight / total_weight for name, m in self.models.items()}

    def save(self, path: Path) -> None:
        """Save ensemble to disk.

        Args:
            path: Path to save ensemble
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            joblib.dump(
                {
                    "strategy": self.strategy,
                    "models": self.models,
                    "meta_learner": self.meta_learner,
                },
                f,
            )

        logger.info(f"Saved ensemble to {path}")

    @classmethod
    def load(cls, path: Path) -> EnsembleModel:
        """Load ensemble from disk.

        Args:
            path: Path to load ensemble from

        Returns:
            Loaded ensemble
        """
        with open(path, "rb") as f:
            data = joblib.load(f)

        ensemble = cls(
            strategy=data["strategy"],
            meta_learner=data["meta_learner"],
        )
        ensemble.models = data["models"]
        ensemble._is_fitted = True

        logger.info(f"Loaded ensemble from {path}")
        return ensemble

    def __repr__(self) -> str:
        models_str = ", ".join(f"{n}({m.weight:.2f})" for n, m in self.models.items())
        return f"EnsembleModel(strategy={self.strategy}, models=[{models_str}])"
