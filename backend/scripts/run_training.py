# backend/scripts/run_training.py
# Urban Intelligence Framework v2.0.0
# CLI script: train ensemble models for one or all cities

"""
run_training.py

Loads processed feature sets from the FeatureStore, trains an XGBoost +
LightGBM + CatBoost ensemble, optionally applies transfer learning, and
saves the final model to disk.

Usage:
    python scripts/run_training.py                       # all cities
    python scripts/run_training.py --city london         # single city
    python scripts/run_training.py --city london --transfer
        # with transfer learning
    python scripts/run_training.py --trials 20
        # fewer Optuna trials (faster)
"""

from __future__ import annotations

import argparse
import pickle  # nosec B403
from pathlib import Path

import numpy as np
import structlog

from src.config import settings
from src.data.data_service import INSIDE_AIRBNB_CATALOGUE
from src.features.feature_store import FeatureStore
from src.modeling.trainer import ModelTrainer
from src.modeling.transfer_learning import TransferLearningManager

logger = structlog.get_logger(__name__)

MODEL_OUTPUT_DIR = Path("data/models")


def load_features(
    city_id: str, store: FeatureStore
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Load the feature matrix and target vector from the FeatureStore.

    Returns (x, y, feature_names).
    Raises FileNotFoundError if the city has not been processed by the ETL.
    """
    df = store.load("features_with_target", city_id, version="2.0")

    target_col = "target_log_price"
    if target_col not in df.columns:
        # Fall back: if the target wasn't embedded, use raw price
        if "price" not in df.columns:
            raise ValueError(f"No target column found for city '{city_id}'")
        import numpy as _np

        y = _np.log1p(df["price"].to_numpy().astype(float))
        feature_cols = [c for c in df.columns if c != "price"]
    else:
        y = df[target_col].to_numpy().astype(float)
        feature_cols = [c for c in df.columns if c != target_col]

    x = df.select(feature_cols).to_numpy().astype(float)
    return x, y, feature_cols


def train_city(
    city_id: str,
    store: FeatureStore,
    n_trials: int,
    use_transfer: bool,
    source_cities: list[str],
) -> None:
    """Train and save the model for a single city."""
    logger.info("Training started", city=city_id)

    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load features ─────────────────────────────────────────────────────
    try:
        x, y, feature_names = load_features(city_id, store)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Feature loading failed", city=city_id, error=str(exc))
        logger.info("Generating synthetic data as fallback", city=city_id)
        from src.data.generator import SyntheticDataGenerator
        from src.etl.transformer import FeatureTransformer

        gen = SyntheticDataGenerator()
        raw = gen.generate(
            city_id=city_id, n_samples=settings.n_synthetic_samples
        )
        transformer = FeatureTransformer(city_id=city_id)
        result = transformer.fit_transform(raw)
        x = result.features.to_numpy().astype(float)
        y = result.target.to_numpy().astype(float)
        feature_names = result.feature_names

    logger.info(
        "Features loaded", city=city_id, samples=len(x), features=x.shape[1]
    )

    # ── Transfer learning ─────────────────────────────────────────────────
    if use_transfer and source_cities:
        source_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for src_city in source_cities:
            if src_city == city_id:
                continue
            try:
                x_src, y_src, _ = load_features(src_city, store)
                source_data[src_city] = (x_src, y_src)
            except Exception:
                logger.warning("Source city data unavailable", city=src_city)

        if source_data:
            tl_manager = TransferLearningManager(
                source_cities=list(source_data.keys()),
                target_city=city_id,
            )
            tl_result = tl_manager.train(source_data, x, y, feature_names)
            logger.info(
                "Transfer learning result",
                city=city_id,
                transfer_gain=round(tl_result.transfer_gain, 4),
                metrics=tl_result.metrics,
            )
            # Save combined model bundle
            model_path = MODEL_OUTPUT_DIR / f"{city_id}_transfer_model.pkl"
            with model_path.open("wb") as f:
                pickle.dump(
                    {"result": tl_result, "feature_names": feature_names}, f
                )
            logger.info("Transfer model saved", path=str(model_path))
            return

    # ── Standard ensemble training ────────────────────────────────────────
    trainer = ModelTrainer(
        city_id=city_id,
        n_optuna_trials=n_trials,
    )
    train_result = trainer.train(x, y, feature_names)

    logger.info(
        "Training complete",
        city=city_id,
        rmse=round(train_result.metrics.get("rmse", 0), 4),
        mae=round(train_result.metrics.get("mae", 0), 4),
        r2=round(train_result.metrics.get("r2", 0), 4),
    )

    # ── Save model to disk ────────────────────────────────────────────────
    model_path = MODEL_OUTPUT_DIR / f"{city_id}_model.pkl"
    with model_path.open("wb") as f:
        pickle.dump(
            {"result": train_result, "feature_names": feature_names}, f
        )
    logger.info("Model saved", path=str(model_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Urban Intelligence Model Trainer"
    )
    parser.add_argument(
        "--city",
        "--cities",
        dest="cities",
        nargs="+",
        metavar="CITY",
        help="City IDs to train (default: all with available features)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=settings.n_optuna_trials,
        help=f"Number of Optuna trials (default: {settings.n_optuna_trials})",
    )
    parser.add_argument(
        "--transfer",
        action="store_true",
        help="Enable multi-city transfer learning",
    )
    parser.add_argument(
        "--source-cities",
        dest="source_cities",
        nargs="+",
        metavar="CITY",
        default=settings.get_source_cities_list(),
        help="Source cities for transfer learning",
    )
    args = parser.parse_args()

    store = FeatureStore()
    cities = args.cities or list(INSIDE_AIRBNB_CATALOGUE.keys())

    logger.info(
        "Training pipeline starting",
        cities=cities,
        trials=args.trials,
        transfer=args.transfer,
    )

    for city_id in cities:
        try:
            train_city(
                city_id=city_id,
                store=store,
                n_trials=args.trials,
                use_transfer=args.transfer,
                source_cities=args.source_cities or [],
            )
        except Exception as exc:
            logger.error("Training failed", city=city_id, error=str(exc))

    logger.info("Training pipeline complete")


if __name__ == "__main__":
    main()
