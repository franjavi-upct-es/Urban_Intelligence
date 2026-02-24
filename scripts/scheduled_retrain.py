# scripts/scheduled_retrain.py
# Urban Intelligence Framework - Scheduled Retraining
# Automated model retraining based on drift detection and schedules

"""
Scheduled retraining script for the Urban Intelligence Framework.

This script orchestrates automated model retraining based on:
    - Time-based schedules (daily, weekly, monthly)
    - Data drift detection triggers
    - Performance degradation triggers
    - Manual trigger support

Usage:
    # Check if retraining is needed
    python scripts/scheduled_retrain.py --check

    # Force retraining
    python scripts/scheduled_retrain.py --force

    # Run with specific city
    python scripts/scheduled_retrain.py --city madrid --force

    # Dry run (check without executing)
    python scripts/scheduled_retrain.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitoring.drift_detector import DriftDetector, DriftSeverity
from src.monitoring.performance_monitor import PerformanceMonitor
from src.validation.expectations import DataValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_RETRAIN_INTERVAL_DAYS = 30
MIN_SAMPLES_FOR_DRIFT = 1000
DRIFT_CHECK_INTERVAL_HOURS = 24

RETRAIN_STATE_FILE = Path("data/retrain_state.json")


# =============================================================================
# State Management
# =============================================================================


def load_retrain_state() -> dict[str, Any]:
    """Load retraining state from disk.

    Returns:
        Dictionary with state information
    """
    if RETRAIN_STATE_FILE.exists():
        with open(RETRAIN_STATE_FILE) as f:
            return json.load(f)
    return {
        "last_retrain": None,
        "last_drift_check": None,
        "retrain_count": 0,
        "drift_triggered_count": 0,
        "performance_triggered_count": 0,
    }


def save_retrain_state(state: dict[str, Any]) -> None:
    """Save retraining state to disk.

    Args:
        state: State dictionary to save
    """
    RETRAIN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RETRAIN_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


# =============================================================================
# Trigger Evaluation
# =============================================================================


def check_time_trigger(
    state: dict[str, Any],
    interval_days: int = DEFAULT_RETRAIN_INTERVAL_DAYS,
) -> tuple[bool, str]:
    """Check if time-based retraining is needed.

    Args:
        state: Current state dictionary
        interval_days: Days between scheduled retrains

    Returns:
        Tuple of (should_retrain, reason)
    """
    last_retrain = state.get("last_retrain")

    if last_retrain is None:
        return True, "No previous training recorded"

    last_dt = datetime.fromisoformat(last_retrain)
    days_since = (datetime.now() - last_dt).days

    if days_since >= interval_days:
        return True, f"Scheduled retrain: {days_since} days since last training"

    return False, f"Not due: {interval_days - days_since} days until scheduled retrain"


def check_drift_trigger(
    reference_df: pl.DataFrame | None,
    current_df: pl.DataFrame | None,
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[bool, str, dict[str, Any] | None]:
    """Check if drift-based retraining is needed.

    Args:
        reference_df: Reference (training) data
        current_df: Current production data
        numeric_features: List of numeric feature names
        categorical_features: List of categorical feature names

    Returns:
        Tuple of (should_retrain, reason, drift_report)
    """
    if reference_df is None or current_df is None:
        return False, "Missing data for drift comparison", None

    if current_df.height < MIN_SAMPLES_FOR_DRIFT:
        return False, f"Insufficient samples: {current_df.height} < {MIN_SAMPLES_FOR_DRIFT}", None

    detector = DriftDetector(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
    )

    detector.set_reference(reference_df)
    report = detector.detect_drift(current_df)

    if report.overall_severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
        return True, f"Drift detected: {report.overall_severity.value}", report.to_dict()

    return False, f"Drift within bounds: {report.overall_severity.value}", report.to_dict()


def check_performance_trigger(
    monitor: PerformanceMonitor | None,
) -> tuple[bool, str]:
    """Check if performance-based retraining is needed.

    Args:
        monitor: Performance monitor instance

    Returns:
        Tuple of (should_retrain, reason)
    """
    if monitor is None:
        return False, "No performance monitor available"

    should_retrain, reason = monitor.should_retrain()
    return should_retrain, reason


# =============================================================================
# Retraining Execution
# =============================================================================


def execute_retrain(
    city: str,
    optimize: bool = True,
    n_trials: int = 50,
) -> dict[str, Any]:
    """Execute the retraining pipeline.

    Args:
        city: City to train model for
        optimize: Whether to run hyperparameter optimization
        n_trials: Number of Optuna trials if optimizing

    Returns:
        Dictionary with training results
    """
    logger.info(f"Starting retraining for city: {city}")

    results = {
        "city": city,
        "start_time": datetime.now().isoformat(),
        "optimize": optimize,
        "status": "started",
    }

    try:
        # Import training modules
        from src.data import DataService
        from src.etl.cleaner import AirbnbCleaner
        from src.etl.transformer import FeatureTransformer
        from src.modeling.trainer import ModelTrainer

        # Step 1: Load data
        logger.info("Step 1: Loading data...")
        service = DataService()
        data = service.get_city_data(city)

        if data.listings is None or data.listings.height == 0:
            raise ValueError(f"No data available for {city}")

        results["raw_samples"] = data.listings.height
        logger.info(f"Loaded {data.listings.height} listings")

        # Step 2: Validate raw data
        logger.info("Step 2: Validating raw data...")
        validator = DataValidator()
        validation_result = validator.validate_raw_listings(data.listings)

        if not validation_result.overall_success:
            logger.warning(f"Validation issues: {validation_result.failed_expectations}")

        results["validation"] = {
            "success_rate": validation_result.success_rate,
            "failed_checks": validation_result.failed_expectations,
        }

        # Step 3: Clean data
        logger.info("Step 3: Cleaning data...")
        cleaner = AirbnbCleaner()
        cleaned_df = cleaner.clean(data.listings)
        results["cleaned_samples"] = cleaned_df.height
        logger.info(f"After cleaning: {cleaned_df.height} listings")

        # Step 4: Transform features
        logger.info("Step 4: Transforming features...")
        transformer = FeatureTransformer()
        transformed_df = transformer.transform(cleaned_df)
        results["feature_count"] = transformed_df.width
        logger.info(f"Features: {transformed_df.width}")

        # Step 5: Prepare training data
        logger.info("Step 5: Preparing training data...")

        # Select numeric columns for training
        feature_cols = [
            c
            for c in transformed_df.columns
            if c not in ["price", "id", "name", "description", "host_name"]
            and transformed_df[c].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]
        ]

        x = transformed_df.select(feature_cols).to_numpy()
        y = transformed_df["price"].to_numpy()

        results["training_features"] = len(feature_cols)
        results["training_samples"] = len(y)

        # Step 6: Train model
        logger.info("Step 6: Training model...")
        trainer = ModelTrainer(
            n_trials=n_trials if optimize else 10,
            cv_folds=5,
        )

        model, metrics = trainer.train(x, y)

        results["metrics"] = metrics
        results["status"] = "completed"
        results["end_time"] = datetime.now().isoformat()

        logger.info(f"Training completed. Metrics: {metrics}")

        # Step 7: Save model
        logger.info("Step 7: Saving model...")
        model_path = Path("models") / f"{city}_model.pkl"
        model_path.parent.mkdir(parents=True, exist_ok=True)

        import joblib

        with open(model_path, "wb") as f:
            joblib.dump(
                {
                    "model": model,
                    "version": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "metrics": metrics,
                    "features": feature_cols,
                    "city": city,
                },
                f,
            )

        results["model_path"] = str(model_path)
        logger.info(f"Model saved to {model_path}")

    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        results["status"] = "failed"
        results["error"] = str(e)
        results["end_time"] = datetime.now().isoformat()

    return results


# =============================================================================
# Main Orchestration
# =============================================================================


def run_scheduled_retrain(
    city: str = "madrid",
    force: bool = False,
    dry_run: bool = False,
    check_only: bool = False,
    optimize: bool = True,
    n_trials: int = 50,
) -> dict[str, Any]:
    """Run the scheduled retraining workflow.

    Args:
        city: City to process
        force: Force retraining regardless of triggers
        dry_run: Check triggers but don't execute
        check_only: Only report trigger status
        optimize: Run hyperparameter optimization
        n_trials: Number of Optuna trials

    Returns:
        Dictionary with workflow results
    """
    logger.info("=" * 60)
    logger.info("SCHEDULED RETRAINING WORKFLOW")
    logger.info("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "city": city,
        "force": force,
        "dry_run": dry_run,
    }

    # Load state
    state = load_retrain_state()
    results["previous_retrains"] = state.get("retrain_count", 0)

    # Check triggers
    triggers = {}

    # Time trigger
    time_should, time_reason = check_time_trigger(state)
    triggers["time"] = {"triggered": time_should, "reason": time_reason}

    # Note: Drift and performance triggers would need data to evaluate
    # In a real deployment, these would load reference data and production data
    triggers["drift"] = {"triggered": False, "reason": "Drift check not configured"}
    triggers["performance"] = {"triggered": False, "reason": "Performance monitor not configured"}

    results["triggers"] = triggers

    # Determine if we should retrain
    should_retrain = force or any(t["triggered"] for t in triggers.values())
    results["should_retrain"] = should_retrain

    if check_only:
        logger.info("Check-only mode: Reporting trigger status")
        for name, trigger in triggers.items():
            status = "TRIGGERED" if trigger["triggered"] else "not triggered"
            logger.info(f"  {name}: {status} - {trigger['reason']}")
        return results

    if not should_retrain:
        logger.info("No retraining needed")
        return results

    if dry_run:
        logger.info("Dry run mode: Would execute retraining")
        results["action"] = "would_retrain"
        return results

    # Execute retraining
    logger.info("Executing retraining...")
    retrain_results = execute_retrain(city, optimize=optimize, n_trials=n_trials)
    results["retrain_results"] = retrain_results

    # Update state
    if retrain_results["status"] == "completed":
        state["last_retrain"] = datetime.now().isoformat()
        state["retrain_count"] = state.get("retrain_count", 0) + 1

        if triggers["drift"]["triggered"]:
            state["drift_triggered_count"] = state.get("drift_triggered_count", 0) + 1
        if triggers["performance"]["triggered"]:
            state["performance_triggered_count"] = state.get("performance_triggered_count", 0) + 1

        save_retrain_state(state)
        logger.info("State updated")

    logger.info("=" * 60)
    logger.info("WORKFLOW COMPLETE")
    logger.info("=" * 60)

    return results


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for scheduled retraining."""
    parser = argparse.ArgumentParser(
        description="Urban Intelligence Scheduled Retraining",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/scheduled_retrain.py --check
    python scripts/scheduled_retrain.py --force
    python scripts/scheduled_retrain.py --city madrid --force
    python scripts/scheduled_retrain.py --dry-run
        """,
    )

    parser.add_argument(
        "--city",
        default="madrid",
        help="City to train model for (default: madrid)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force retraining regardless of triggers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check triggers but don't execute retraining",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check and report trigger status",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Skip hyperparameter optimization",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=50,
        help="Number of Optuna trials (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    # Run workflow
    results = run_scheduled_retrain(
        city=args.city,
        force=args.force,
        dry_run=args.dry_run,
        check_only=args.check,
        optimize=not args.no_optimize,
        n_trials=args.trials,
    )

    # Save results if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {args.output}")

    # Exit with appropriate code
    if results.get("retrain_results", {}).get("status") == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
