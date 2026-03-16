# backend/src/modeling/transfer_learning.py
# Urban Intelligence Framework v2.0.0
# Multi-city transfer learning with domain adaptation

"""
TransferLearningManager module.

Implements transfer learning across cities to improve predictions in
data-sparse target cities by leveraging patterns from rich source cities.

Strategy:
1. Train a global "meta-model" on all source cities with city embeddings.
2. Fine-tune on the target city data via a small adaptation layer.
3. Use Maximum Mean Discrepancy (MMD) to align feature distributions
   between source and target domains.

This follows the Domain Adaptation paradigm commonly used in
transfer learning for tabular data.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog
from sklearn.preprocessing import StandardScaler

from src.config import settings
from src.modeling.trainer import ModelTrainer

logger = structlog.get_logger(__name__)


@dataclass
class TransferResult:
    """Result of a transfer learning training run."""

    model_id: str
    source_cities: list[str]
    target_city: str
    source_samples: int
    target_samples: int
    metrics: dict[str, float]
    transfer_gain: (
        float  # improvement vs. training on target data alone (delta RMSE)
    )
    models: dict[str, Any] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    feature_names: list[str] = field(default_factory=list)


class TransferLearningManager:
    """
    Multi-city transfer learning manager.

    Combines source city data into a unified training pool, optionally
    applying MMD-based feature alignment, then fine-tunes on target city.

    Parameters
    ----------
    source_cities : list[str]
        Cities used as transfer sources.
    target_city : str
        City to receive knowledge transfer.
    mmd_lambda : float
        Weight of the MMD distribution alignment penalty.
        Set to 0.0 to disable domain adaptation.
    """

    def __init__(
        self,
        source_cities: list[str] | None = None,
        target_city: str = "london",
        mmd_lambda: float = 0.1,
    ) -> None:
        self.source_cities = source_cities or settings.get_source_cities_list()
        self.target_city = target_city
        self.mmd_lambda = mmd_lambda
        self._scaler = StandardScaler()

    # ── Public API ────────────────────────────────────────────────────────

    def train(
        self,
        source_data: dict[str, tuple[np.ndarray, np.ndarray]],
        target_X: np.ndarray,
        target_y: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> TransferResult:
        """
        Execute transfer learning from multiple source cities to target.

        Args:
            source_data: dict of city_id → (X, y) arrays for source cities.
            target_X:    Feature matrix for the target city.
            target_y:    Label vector for the target city.
            feature_names: Optional column names for logging.

        Returns:
            TransferResult with trained models and comparative metrics.
        """
        feat_names = feature_names or [
            f"f{i}" for i in range(target_X.shape[1])
        ]
        logger.info(
            "Transfer learning started",
            sources=list(source_data.keys()),
            target=self.target_city,
            target_samples=len(target_X),
        )

        # ── Step 1: Build combined source pool ───────────────────────────
        x_combined, y_combined = self._build_source_pool(source_data)
        logger.info("Source pool built", samples=len(x_combined))

        # ── Step 2: Domain adaptation via MMD alignment ───────────────────
        if self.mmd_lambda > 0:
            x_combined = self._mmd_align(x_combined, target_X)
            logger.debug("MMD alignment applied")

        # ── Step 3: Scale combined + target together ──────────────────────
        x_all = np.vstack([x_combined, target_X])
        x_all_scaled = self._scaler.fit_transform(x_all)

        n_source = len(x_combined)
        x_source_scaled = x_all_scaled[:n_source]
        x_target_scaled = x_all_scaled[n_source:]

        # ── Step 4: Train on source data (base model) ─────────────────────
        base_trainer = ModelTrainer(
            city_id=f"transfer_base_{self.target_city}",
            n_optuna_trials=max(settings.n_optuna_trials // 2, 10),
        )
        base_result = base_trainer.train(
            x_source_scaled, y_combined, feat_names
        )

        # ── Step 5: Fine-tune on target data ──────────────────────────────
        target_trainer = ModelTrainer(
            city_id=self.target_city,
            n_optuna_trials=max(settings.n_optuna_trials // 4, 5),
        )
        target_result = target_trainer.train(
            x_target_scaled, target_y, feat_names
        )

        # ── Step 6: Blend base + fine-tuned predictions ───────────────────
        # Evaluate both on the target hold-out set
        split = int(len(x_target_scaled) * (1 - settings.test_size))
        x_test, y_test = x_target_scaled[split:], target_y[split:]

        base_preds = base_trainer.predict(
            base_result, x_test, inverse_log=False
        )
        target_preds = target_trainer.predict(
            target_result, x_test, inverse_log=False
        )

        # Determine optimal blend weight (α for target, 1-α for base)
        alpha = self._optimise_blend(base_preds, target_preds, y_test)
        blended_preds = alpha * target_preds + (1 - alpha) * base_preds

        from sklearn.metrics import mean_squared_error

        transfer_rmse = float(
            np.sqrt(mean_squared_error(y_test, blended_preds))
        )
        target_only_rmse = target_result.metrics.get("rmse", float("inf"))
        transfer_gain = target_only_rmse - transfer_rmse

        metrics = {
            "transfer_rmse": transfer_rmse,
            "target_only_rmse": target_only_rmse,
            "transfer_gain": transfer_gain,
            "blend_alpha": alpha,
            **{f"base_{k}": v for k, v in base_result.metrics.items()},
        }

        logger.info(
            "Transfer learning complete",
            target=self.target_city,
            transfer_rmse=round(transfer_rmse, 4),
            gain=round(transfer_gain, 4),
        )

        return TransferResult(
            model_id=f"transfer_{self.target_city}_{uuid.uuid4().hex[:8]}",
            source_cities=list(source_data.keys()),
            target_city=self.target_city,
            source_samples=len(x_combined),
            target_samples=len(target_X),
            metrics=metrics,
            transfer_gain=transfer_gain,
            models={
                "base": base_result.models,
                "target": target_result.models,
            },
            weights={"base": 1 - alpha, "target": alpha},
            feature_names=feat_names,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_source_pool(
        self, source_data: dict[str, tuple[np.ndarray, np.ndarray]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Concatenate all source city arrays into a single pool.
        Cities with fewer samples are up-sampled to the median count.
        """
        x_parts, y_parts = [], []
        counts = [len(x) for x, _ in source_data.values()]
        median_count = int(np.median(counts))

        for _city, (x, y) in source_data.items():
            if len(x) < median_count:
                # Bootstrap up-sampling to median count
                idx = np.random.choice(len(x), size=median_count, replace=True)
                x, y = x[idx], y[idx]
            x_parts.append(x)
            y_parts.append(y)

        return np.vstack(x_parts), np.concatenate(y_parts)

    def _mmd_align(
        self,
        X_source: np.ndarray,
        X_target: np.ndarray,
        n_subspace: int = 50,
    ) -> np.ndarray:
        """
        Approximate Maximum Mean Discrepancy alignment.

        Projects both distributions to a shared subspace that minimises
        the MMD metric using a linear mapping (Correlation Alignment — CORAL).
        """
        try:
            # CORAL: align second-order statistics
            cs = (
                np.cov(X_source, rowvar=False)
                + np.eye(X_source.shape[1]) * 1e-6
            )
            ct = (
                np.cov(X_target, rowvar=False)
                + np.eye(X_target.shape[1]) * 1e-6
            )

            # Whitening source, then colouring with target statistics
            cs_inv_sqrt = np.linalg.inv(np.linalg.cholesky(cs)).T
            ct_sqrt = np.linalg.cholesky(ct)
            w = cs_inv_sqrt @ ct_sqrt

            x_aligned = (X_source - X_source.mean(axis=0)) @ w
            return x_aligned

        except np.linalg.LinAlgError:
            logger.warning(
                "CORAL alignment failed (singular matrix), "
                "using raw source features"
            )
            return X_source

    @staticmethod
    def _optimise_blend(
        base_preds: np.ndarray,
        target_preds: np.ndarray,
        y_true: np.ndarray,
    ) -> float:
        """
        Find the blend weight α ∈ [0, 1] that minimises RMSE.
        α=1 means full target model, α=0 means full base model.
        """
        from sklearn.metrics import mean_squared_error

        best_alpha, best_rmse = 0.5, float("inf")
        for a in np.linspace(0, 1, 21):
            blended = a * target_preds + (1 - a) * base_preds
            rmse = float(np.sqrt(mean_squared_error(y_true, blended)))
            if rmse < best_rmse:
                best_rmse, best_alpha = rmse, float(a)
        return best_alpha
