# src/modeling/trainer.py
# Urban Intelligence Framework - Model Trainer
# XGBoost training with MLflow tracking and Optuna optimization

"""
Model training with XGBoost and Optuna.

This module provides:
- XGBoost gradient boosting model training
- Hyperparameter optimization with Optuna
- MLflow experiment tracking
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Trains XGBoost models with optional hyperparameter optimization.

    Example:
        >>> trainer = ModelTrainer(n_trials=50)
        >>> model, metrics = trainer.train(x, y)
    """

    def __init__(
        self,
        n_trials: int = 50,
        cv_folds: int = 5,
        random_seed: int = 42,
        test_size: float = 0.2,
    ) -> None:
        """Initialize the trainer."""
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.random_seed = random_seed
        self.test_size = test_size
        self.best_params: dict[str, Any] = {}
        self.model = None

    def train(
        self,
        x: np.ndarray,
        y: np.ndarray,
        optimize: bool = True,
    ) -> tuple[Any, dict[str, float]]:
        """Train the model.

        Args:
            x: Feature matrix
            y: Target vector
            optimize: Whether to run hyperparameter optimization

        Returns:
            Tuple of (trained model, metrics dictionary)
        """
        logger.info(f"Training with {x.shape[0]} samples, {x.shape[1]} features")

        # Split data
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=self.test_size, random_state=self.random_seed
        )

        # Import XGBoost
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost not installed. Using sklearn GradientBoosting.")
            from sklearn.ensemble import GradientBoostingRegressor

            model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                random_state=self.random_seed,
            )
            model.fit(x_train, y_train)

            y_pred = model.predict(x_test)
            metrics = self._compute_metrics(y_test, y_pred)

            self.model = model
            return model, metrics

        # Run optimization if requested
        if optimize and self.n_trials > 0:
            self.best_params = self._optimize_hyperparameters(x_train, y_train)
        else:
            self.best_params = {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
            }

        # Train final model
        model = xgb.XGBRegressor(
            **self.best_params,
            random_state=self.random_seed,
            n_jobs=-1,
        )

        model.fit(x_train, y_train)

        # Evaluate
        y_pred = model.predict(x_test)
        metrics = self._compute_metrics(y_test, y_pred)

        # Cross-validation score
        cv_scores = cross_val_score(
            model, x_train, y_train, cv=self.cv_folds, scoring="neg_mean_absolute_error"
        )
        metrics["cv_mae_mean"] = float(-cv_scores.mean())
        metrics["cv_mae_std"] = float(cv_scores.std())

        self.model = model

        logger.info(f"Training complete. Test MAE: {metrics['mae']:.2f}")
        return model, metrics

    def _optimize_hyperparameters(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> dict[str, Any]:
        """Optimize hyperparameters using Optuna."""
        try:
            import optuna
            import xgboost as xgb
        except ImportError:
            logger.warning("Optuna not installed. Using default parameters.")
            return {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
            }

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        def objective(trial: optuna.trial.Trial) -> float:
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
            }

            model = xgb.XGBRegressor(**params, random_state=self.random_seed, n_jobs=-1)

            scores = cross_val_score(
                model,
                x,
                y,
                cv=min(self.cv_folds, 3),  # Use fewer folds for speed
                scoring="neg_mean_absolute_error",
            )

            return -scores.mean()

        logger.info(f"Running Optuna optimization with {self.n_trials} trials...")
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

        logger.info(f"Best MAE: {study.best_value:.2f}")
        return study.best_params

    def _compute_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> dict[str, float]:
        """Compute evaluation metrics."""
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2": float(r2_score(y_true, y_pred)),
            "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        }

    def save_model(self, path: Path) -> None:
        """Save the trained model."""
        if self.model is None:
            raise ValueError("No model to save. Train first.")

        import joblib

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            joblib.dump(
                {
                    "model": self.model,
                    "best_params": self.best_params,
                },
                f,
            )

        logger.info(f"Model saved to {path}")

    def load_model(self, path: Path) -> Any:
        """Load a trained model."""
        import joblib

        with open(path, "rb") as f:
            data = joblib.load(f)

        self.model = data["model"]
        self.best_params = data.get("best_params", {})

        logger.info(f"Model loaded from {path}")
        return self.model
