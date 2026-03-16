# backend/src/modeling/trainer.py
# Urban Intelligence Framework v2.0.0
# Ensemble model trainer with MLflow tracking and Optuna hyperparameter search

"""
ModelTrainer module.

Trains an ensemble of XGBoost, LightGBM, and CatBoost models on
Airbnb listing feature matrices. Integrates with MLflow for experiment
tracking and Optuna for Bayesian hyperparameter optimisation.

Training flow:
1. Split data into train / validation / test sets.
2. For each base model type, run Optuna to find best hyperparameters.
3. Train final models on train+validation with best params.
4. Combine predictions via weighted averaging (weights optimised on val).
5. Log all metrics and artefacts to MLflow.
6. Return a TrainingResult with all trained models and metrics.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import mlflow
import mlflow.sklearn
import numpy as np
import polars as pl
import structlog
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold

from src.config import settings

logger = structlog.get_logger(__name__)


# ── Result container ──────────────────────────────────────────────────────


@dataclass
class TrainingResult:
    """Container for the outcome of a training run."""

    model_id: str
    city_id: str
    mlflow_run_id: str
    models: dict[str, Any]  # model_name → fitted model object
    weights: dict[str, float]  # model_name → ensemble weight
    metrics: dict[str, float]  # metric_name → value (on test set)
    feature_names: list[str]
    training_time_s: float
    n_samples: int

    @property
    def primary_metric(self) -> float:
        """Return primary evaluation metric (RMSE on log-scale)."""
        return self.metrics.get("rmse", float("inf"))


# ── Trainer ───────────────────────────────────────────────────────────────


class ModelTrainer:
    """
    Ensemble trainer for Airbnb price prediction.

    Parameters
    ----------
    city_id : str
        City identifier (used for MLflow tags and model registry keys).
    n_optuna_trials : int
        Number of Optuna trials for hyperparameter search per model.
    cv_folds : int
        Number of cross-validation folds.
    """

    def __init__(
        self,
        city_id: str = "london",
        n_optuna_trials: int | None = None,
        cv_folds: int | None = None,
    ) -> None:
        self.city_id = city_id
        self.n_optuna_trials = n_optuna_trials or settings.n_optuna_trials
        self.cv_folds = cv_folds or settings.cv_folds

    # ── Public interface ──────────────────────────────────────────────────

    def train(
        self,
        X: pl.DataFrame | np.ndarray,
        y: pl.Series | np.ndarray,
        feature_names: list[str] | None = None,
    ) -> TrainingResult:
        """
        Run the full training pipeline and return a TrainingResult.

        Args:
            X : Feature matrix (rows=samples, cols=features).
            y : Target vector (log1p-transformed prices recommended).
            feature_names : Optional list of feature column names.
        """
        start = time.perf_counter()
        model_id = f"{self.city_id}_{uuid.uuid4().hex[:8]}"

        # Convert Polars to NumPy
        x_np = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X)
        y_np = y.to_numpy() if hasattr(y, "to_numpy") else np.asarray(y)
        feat_names = feature_names or [f"f{i}" for i in range(x_np.shape[1])]

        logger.info("Training started", city=self.city_id, samples=len(x_np))

        # ── Train/test split ──────────────────────────────────────────────
        split = int(len(x_np) * (1 - settings.test_size))
        x_train, x_test = x_np[:split], x_np[split:]
        y_train, y_test = y_np[:split], y_np[split:]

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.experiment_name)

        with mlflow.start_run(run_name=f"{self.city_id}_ensemble") as run:
            mlflow.set_tags(
                {
                    "city": self.city_id,
                    "model_type": "ensemble",
                    "version": "2.0.0",
                }
            )
            mlflow.log_params(
                {
                    "n_optuna_trials": self.n_optuna_trials,
                    "cv_folds": self.cv_folds,
                    "n_train": len(x_train),
                    "n_test": len(x_test),
                }
            )

            # ── Optimise and train each base model ────────────────────────
            models: dict[str, Any] = {}
            val_preds: dict[str, np.ndarray] = {}

            for model_type in ("xgboost", "lightgbm", "catboost"):
                try:
                    model, val_pred = self._train_base_model(
                        model_type, x_train, y_train, x_test
                    )
                    models[model_type] = model
                    val_preds[model_type] = val_pred
                    logger.info("Base model trained", type=model_type)
                except ImportError:
                    logger.warning(
                        "Model library not installed, skipping",
                        type=model_type,
                    )

            if not models:
                raise RuntimeError(
                    "No model libraries available (xgboost/lightgbm/catboost)."
                )

            # ── Optimise ensemble weights ─────────────────────────────────
            weights = self._optimise_weights(val_preds, y_test)

            # ── Final ensemble prediction ─────────────────────────────────
            ensemble_pred = sum(
                weights[name] * pred for name, pred in val_preds.items()
            )

            # ── Metrics ───────────────────────────────────────────────────
            metrics = self._compute_metrics(y_test, ensemble_pred)
            mlflow.log_metrics(metrics)

            # ── Log feature importances ───────────────────────────────────
            if "xgboost" in models:
                fi = dict(
                    zip(
                        feat_names,
                        models["xgboost"].feature_importances_,
                        strict=False,
                    )
                )
                top_features = sorted(
                    fi.items(), key=lambda x: x[1], reverse=True
                )[:20]
                mlflow.log_dict(
                    dict(top_features), "feature_importance_top20.json"
                )

        training_time = time.perf_counter() - start
        logger.info(
            "Training complete",
            city=self.city_id,
            rmse=metrics.get("rmse"),
            time_s=round(training_time, 2),
        )

        return TrainingResult(
            model_id=model_id,
            city_id=self.city_id,
            mlflow_run_id=run.info.run_id,
            models=models,
            weights=weights,
            metrics=metrics,
            feature_names=feat_names,
            training_time_s=training_time,
            n_samples=len(x_np),
        )

    def predict(
        self,
        result: TrainingResult,
        X: pl.DataFrame | np.ndarray,
        inverse_log: bool = True,
    ) -> np.ndarray:
        """
        Generate ensemble predictions using a TrainingResult.

        Args:
            result:      Output of train().
            X:           Feature matrix.
            inverse_log: If True, apply expm1 to reverse log1p transform.

        Returns:
            Array of predicted prices.
        """
        x_np = X.to_numpy() if hasattr(X, "to_numpy") else np.asarray(X)
        preds = sum(
            result.weights[name] * model.predict(x_np)
            for name, model in result.models.items()
        )
        return np.expm1(preds) if inverse_log else preds

    # ── Private helpers ───────────────────────────────────────────────────

    def _train_base_model(
        self,
        model_type: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
    ) -> tuple[Any, np.ndarray]:
        """
        Optimise hyperparameters with Optuna, then train the final model.
        Returns (trained_model, val_predictions).
        """
        import optuna

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        best_params = self._run_optuna(model_type, X_train, y_train)
        model = self._build_model(model_type, best_params)
        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        return model, val_pred

    def _run_optuna(
        self, model_type: str, X: np.ndarray, y: np.ndarray
    ) -> dict[str, Any]:
        """Run Optuna Bayesian optimisation and return best hyperparameters."""
        import optuna

        def objective(trial: optuna.Trial) -> float:
            params = self._suggest_params(trial, model_type)
            model = self._build_model(model_type, params)
            kf = KFold(
                n_splits=min(self.cv_folds, 3), shuffle=True, random_state=42
            )
            scores: list[float] = []
            for train_idx, val_idx in kf.split(X):
                model.fit(X[train_idx], y[train_idx])
                pred = model.predict(X[val_idx])
                scores.append(
                    float(np.sqrt(mean_squared_error(y[val_idx], pred)))
                )
            return float(np.mean(scores))

        study = optuna.create_study(direction="minimize")
        study.optimize(
            objective, n_trials=self.n_optuna_trials, show_progress_bar=False
        )
        return study.best_params

    def _suggest_params(self, trial: Any, model_type: str) -> dict[str, Any]:
        """Return Optuna trial suggestions for the given model type."""
        if model_type == "xgboost":
            return {
                "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 8),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree", 0.6, 1.0
                ),
                "reg_alpha": trial.suggest_float(
                    "reg_alpha", 1e-4, 10.0, log=True
                ),
                "reg_lambda": trial.suggest_float(
                    "reg_lambda", 1e-4, 10.0, log=True
                ),
                "random_state": settings.random_seed,
            }
        elif model_type == "lightgbm":
            return {
                "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 8),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "num_leaves": trial.suggest_int("num_leaves", 20, 150),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float(
                    "colsample_bytree", 0.6, 1.0
                ),
                "random_state": settings.random_seed,
                "verbose": -1,
            }
        else:  # catboost
            return {
                "iterations": trial.suggest_int("iterations", 200, 800),
                "depth": trial.suggest_int("depth", 3, 8),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1, 10),
                "random_seed": settings.random_seed,
                "verbose": False,
            }

    def _build_model(self, model_type: str, params: dict[str, Any]) -> Any:
        """Instantiate a model with the given parameters."""
        if model_type == "xgboost":
            from xgboost import XGBRegressor

            return XGBRegressor(**params)
        elif model_type == "lightgbm":
            from lightgbm import LGBMRegressor

            return LGBMRegressor(**params)
        else:  # catboost
            from catboost import CatBoostRegressor

            return CatBoostRegressor(**params)

    def _optimise_weights(
        self, val_preds: dict[str, np.ndarray], y_true: np.ndarray
    ) -> dict[str, float]:
        """
        Find ensemble weights that minimise RMSE on the validation set.
        Uses a simple grid search over integer weight combinations summing
        to 10.
        """
        model_names = list(val_preds.keys())
        n = len(model_names)

        if n == 1:
            return {model_names[0]: 1.0}

        best_rmse = float("inf")
        best_weights = dict.fromkeys(model_names, 1.0 / n)

        # Grid search with integer weights 1..8
        from itertools import product as iproduct

        for combo in iproduct(range(1, 9), repeat=n):
            total = sum(combo)
            w = [c / total for c in combo]
            ensemble = sum(w[i] * val_preds[model_names[i]] for i in range(n))
            rmse = float(np.sqrt(mean_squared_error(y_true, ensemble)))
            if rmse < best_rmse:
                best_rmse = rmse
                best_weights = {model_names[i]: w[i] for i in range(n)}

        logger.info(
            "Ensemble weights optimised",
            weights=best_weights,
            val_rmse=round(best_rmse, 4),
        )
        return best_weights

    @staticmethod
    def _compute_metrics(
        y_true: np.ndarray, y_pred: np.ndarray
    ) -> dict[str, float]:
        """Compute a standard set of regression metrics."""
        mse = mean_squared_error(y_true, y_pred)
        return {
            "rmse": float(np.sqrt(mse)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
            "mse": float(mse),
        }
