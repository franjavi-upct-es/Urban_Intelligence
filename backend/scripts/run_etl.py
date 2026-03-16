# backend/scripts/run_etl.py
# Urban Intelligence Framework v2.0.0
# CLI script: run the full ETL pipeline for one or all cities

"""
run_etl.py

Downloads raw data, cleans it, engineers features, and saves Parquet
artefacts to disk for downstream model training.

Usage:
    python scripts/run_etl.py                    # all cities in catalogue
    python scripts/run_etl.py --city london      # single city
    python scripts/run_etl.py --city london paris barcelona
    python scripts/run_etl.py --skip-download    # use cached raw data
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the backend root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from src.config import settings
from src.data.data_service import INSIDE_AIRBNB_CATALOGUE, DataService
from src.etl.cleaner import AirbnbCleaner
from src.etl.transformer import FeatureTransformer
from src.features.calendar_features import CalendarFeatureEngineer
from src.features.feature_store import FeatureStore
from src.features.text_features import TextFeatureEngineer
from src.validation.expectations import DataValidator

logger = structlog.get_logger(__name__)


async def run_city_etl(
    city_id: str,
    skip_download: bool = False,
    use_nlp: bool = False,
) -> None:
    """
    Run the complete ETL pipeline for a single city.

    Steps:
    1. Fetch raw listings (skipped if skip_download=True and cache exists).
    2. Validate raw data.
    3. Clean with AirbnbCleaner.
    4. Validate cleaned data.
    5. Engineer calendar, text, and tabular features.
    6. Validate enriched data.
    7. Save processed feature matrix to FeatureStore.
    """
    logger.info("ETL started", city=city_id)

    service = DataService()
    cleaner = AirbnbCleaner(price_min=10.0, price_max=5000.0)
    transformer = FeatureTransformer(city_id=city_id, log_transform_price=True)
    calendar_eng = CalendarFeatureEngineer(city_id=city_id)
    text_eng = TextFeatureEngineer(use_transformers=use_nlp)
    validator = DataValidator()
    store = FeatureStore()

    settings.ensure_directories()

    # ── Step 1: Fetch raw data ────────────────────────────────────────────
    logger.info("Fetching data", city=city_id, skip_download=skip_download)

    def log_progress(p):
        logger.info("Fetch progress", step=p.step, percent=p.percent)

    city_data = await service.fetch_city(
        city_id=city_id,
        force_refresh=not skip_download,
        on_progress=log_progress,
    )
    raw_df = city_data.listings
    logger.info("Raw data loaded", rows=len(raw_df))

    # ── Step 2: Validate raw ──────────────────────────────────────────────
    raw_report = validator.validate(
        raw_df, stage="raw", dataset_name=f"{city_id}_raw"
    )
    logger.info(
        "Raw validation",
        passed=raw_report.n_passed,
        failed=raw_report.n_failed,
        success=raw_report.success,
    )
    if not raw_report.success:
        logger.warning(
            "Raw validation failures",
            failures=[
                r.expectation for r in raw_report.results if not r.passed
            ],
        )

    # ── Step 3: Clean ─────────────────────────────────────────────────────
    clean_df = cleaner.clean(raw_df)
    logger.info("Cleaning complete", rows=len(clean_df))

    # ── Step 4: Validate cleaned ──────────────────────────────────────────
    clean_report = validator.validate(
        clean_df, stage="cleaned", dataset_name=f"{city_id}_cleaned"
    )
    if not clean_report.success:
        logger.warning(
            "Cleaned validation failures",
            failures=[
                r.expectation for r in clean_report.results if not r.passed
            ],
        )

    # ── Step 5: Feature engineering ───────────────────────────────────────
    enriched_df = calendar_eng.transform(clean_df)
    enriched_df = text_eng.fit_transform(enriched_df)

    # ── Step 6: Validate enriched ─────────────────────────────────────────
    enrich_report = validator.validate(
        enriched_df, stage="enriched", dataset_name=f"{city_id}_enriched"
    )
    logger.info("Enriched validation", success=enrich_report.success)

    # ── Step 7: Final feature transform + validate ────────────────────────
    result = transformer.fit_transform(enriched_df)
    model_report = validator.validate(
        result.features,
        stage="model_input",
        dataset_name=f"{city_id}_model_input",
    )
    logger.info("Model-input validation", success=model_report.success)

    # ── Step 8: Save to feature store ─────────────────────────────────────
    meta = store.save(
        df=result.features.with_columns(
            result.target.alias("target_log_price")
        ),
        name="features_with_target",
        city_id=city_id,
        version="2.0",
    )
    logger.info(
        "ETL complete",
        city=city_id,
        n_features=len(result.feature_names),
        rows=meta.n_rows,
    )


async def main_async(args: argparse.Namespace) -> None:
    cities = args.cities or list(INSIDE_AIRBNB_CATALOGUE.keys())

    logger.info("ETL pipeline starting", cities=cities)
    for city_id in cities:
        try:
            await run_city_etl(
                city_id=city_id,
                skip_download=args.skip_download or args.synthetic,
                use_nlp=args.use_nlp,
            )
        except Exception as exc:
            logger.error("ETL failed for city", city=city_id, error=str(exc))

    logger.info("ETL pipeline complete")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Urban Intelligence ETL Pipeline"
    )
    parser.add_argument(
        "--city",
        "--cities",
        dest="cities",
        nargs="+",
        metavar="CITY",
        help="City IDs to process (default: all)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading raw data; use cached Parquet if available",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help=(
            "Skip all downloads and use synthetic data. "
            "Useful for offline development or when insideairbnb.com is unreachable."
        ),
    )
    parser.add_argument(
        "--use-nlp",
        action="store_true",
        help="Enable transformer NLP feature extraction (requires torch)",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
