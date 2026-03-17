# backend/scripts/scheduled_retrain.py
# Urban Intelligence Framework v2.0.0
# Scheduled retraining trigger based on drift detection

"""
scheduled_retrain.py

Checks drift reports and model age for each city.
Triggers a full ETL + retraining cycle if:
  - Drift score exceeds the "retrain" threshold, OR
  - The current model is older than MAX_MODEL_AGE_DAYS.

Designed to run as a cron job or Kubernetes CronJob:
    0 2 * * * python scripts/scheduled_retrain.py   # daily at 02:00

Usage:
    python scripts/scheduled_retrain.py
    python scripts/scheduled_retrain.py --city london --force
    python scripts/scheduled_retrain.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from src.config import settings
from src.data.data_service import INSIDE_AIRBNB_CATALOGUE
from src.database import db

logger = structlog.get_logger(__name__)

MAX_MODEL_AGE_DAYS = 14  # Retrain if model is older than 2 weeks
DRIFT_RETRAIN_SCORE = 0.4  # Retrain if drift score exceeds this


def should_retrain(city_id: str, model_path: Path) -> tuple[bool, str]:
    """
    Determine whether a city's model needs retraining.

    Returns (should_retrain: bool, reason: str).
    """
    # ── Check model age ───────────────────────────────────────────────────
    if not model_path.exists():
        return True, "no_model_found"

    model_age_days = (time.time() - model_path.stat().st_mtime) / 86400
    if model_age_days > MAX_MODEL_AGE_DAYS:
        return True, f"model_age_{model_age_days:.1f}_days"

    # ── Check latest drift score from DB ──────────────────────────────────
    db.connect()
    try:
        df = db.query(
            """
            SELECT payload
            FROM monitoring_events
            WHERE event_type = 'drift_detection'
              AND city_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [city_id],
        )
        if not df.is_empty():
            import json

            payload = json.loads(df["payload"][0])
            drift_score = float(payload.get("overall_drift_score", 0.0))
            if drift_score > DRIFT_RETRAIN_SCORE:
                return True, f"drift_score_{drift_score:.3f}"
    except Exception as exc:
        logger.warning(
            "Could not query drift score", city=city_id, error=str(exc)
        )

    return False, "no_retrain_needed"


async def retrain_city(city_id: str, dry_run: bool = False) -> None:
    """Run ETL + training for a city (unless dry_run is True)."""
    from scripts.run_etl import run_city_etl
    from scripts.run_training import FeatureStore, train_city

    if dry_run:
        logger.info("[DRY RUN] Would retrain", city=city_id)
        return

    logger.info("Retraining started", city=city_id)

    # ETL
    await run_city_etl(city_id=city_id, skip_download=False)

    # Training
    store = FeatureStore()
    train_city(
        city_id=city_id,
        store=store,
        n_trials=max(
            settings.n_optuna_trials // 2, 10
        ),  # fewer trials for scheduled runs
        use_transfer=settings.transfer_learning_enabled,
        source_cities=settings.get_source_cities_list(),
    )

    logger.info("Retraining complete", city=city_id)


async def main_async(args: argparse.Namespace) -> None:
    cities = args.cities or list(INSIDE_AIRBNB_CATALOGUE.keys())
    model_dir = Path("data/models")

    retrain_count = 0
    skip_count = 0

    logger.info(
        "Scheduled retrain check started",
        cities=cities,
        dry_run=args.dry_run,
        force=args.force,
    )

    for city_id in cities:
        model_path = model_dir / f"{city_id}_model.pkl"

        if args.force:
            needs_retrain, reason = True, "forced"
        else:
            needs_retrain, reason = should_retrain(city_id, model_path)

        if needs_retrain:
            logger.info("Retraining required", city=city_id, reason=reason)
            try:
                await retrain_city(city_id, dry_run=args.dry_run)
                retrain_count += 1
            except Exception as exc:
                logger.error("Retraining failed", city=city_id, error=str(exc))
        else:
            logger.info("No retrain needed", city=city_id, reason=reason)
            skip_count += 1

    logger.info(
        "Scheduled retrain check complete",
        retrained=retrain_count,
        skipped=skip_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduled Retraining Check")
    parser.add_argument(
        "--city",
        "--cities",
        dest="cities",
        nargs="+",
        metavar="CITY",
        help="City IDs to check (default: all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force retraining regardless of drift/age checks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check conditions and log what would be retrained, but do not train",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
