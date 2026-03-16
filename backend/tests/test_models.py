# backend/tests/test_models.py
# Urban Intelligence Framework v2.0.0
# Unit tests for ETL, features, modeling, and monitoring modules

"""
Unit tests for the core pipeline components.

Tests are designed to run quickly using synthetic data (no network calls).
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest
from src.data.generator import SyntheticDataGenerator
from src.etl.cleaner import AirbnbCleaner
from src.etl.transformer import FeatureTransformer
from src.features.calendar_features import CalendarFeatureEngineer
from src.features.text_features import TextFeatureEngineer
from src.modeling.ab_testing import ABTestingManager, Variant
from src.monitoring.drift_detector import DriftDetector
from src.monitoring.performance_monitor import PerformanceMonitor
from src.validation.expectations import DataValidator

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def small_raw_df() -> pl.DataFrame:
    """Generate a small synthetic raw DataFrame for testing."""
    gen = SyntheticDataGenerator(seed=42)
    return gen.generate(city_id="london", n_samples=500)


@pytest.fixture
def clean_df(small_raw_df: pl.DataFrame) -> pl.DataFrame:
    """Return a cleaned version of the small raw DataFrame."""
    cleaner = AirbnbCleaner()
    return cleaner.clean(small_raw_df)


# ── Generator tests ───────────────────────────────────────────────────────


class TestSyntheticDataGenerator:
    def test_generates_expected_rows(self):
        gen = SyntheticDataGenerator(seed=0)
        df = gen.generate(n_samples=200)
        assert len(df) == 200

    def test_price_within_bounds(self):
        gen = SyntheticDataGenerator(seed=1)
        df = gen.generate(n_samples=1000)
        assert df["price"].min() >= 10.0
        assert df["price"].max() <= 10_000.0

    def test_has_required_columns(self):
        gen = SyntheticDataGenerator(seed=2)
        df = gen.generate()
        for col in (
            "id",
            "latitude",
            "longitude",
            "room_type",
            "bedrooms",
            "price",
        ):
            assert col in df.columns

    def test_multiple_cities(self):
        gen = SyntheticDataGenerator(seed=3)
        for city in ("london", "paris", "barcelona", "new-york"):
            df = gen.generate(city_id=city, n_samples=100)
            assert len(df) == 100


# ── Cleaner tests ─────────────────────────────────────────────────────────


class TestAirbnbCleaner:
    def test_removes_null_prices(self, small_raw_df):
        dirty = small_raw_df.with_columns(
            pl.when(pl.int_range(pl.len()) % 10 == 0)
            .then(None)
            .otherwise(pl.col("price"))
            .alias("price")
        )
        cleaner = AirbnbCleaner()
        cleaned = cleaner.clean(dirty)
        assert cleaned["price"].null_count() == 0

    def test_price_range_enforced(self, small_raw_df):
        cleaner = AirbnbCleaner(price_min=50.0, price_max=1000.0)
        cleaned = cleaner.clean(small_raw_df)
        assert cleaned["price"].min() >= 50.0
        assert cleaned["price"].max() <= 1000.0

    def test_output_has_fewer_rows(self, small_raw_df):
        cleaner = AirbnbCleaner()
        cleaned = cleaner.clean(small_raw_df)
        # Should drop some outliers; output ≤ input
        assert len(cleaned) <= len(small_raw_df)

    def test_no_high_null_columns(self, small_raw_df):
        cleaner = AirbnbCleaner(drop_null_threshold=0.5)
        cleaned = cleaner.clean(small_raw_df)
        for col in cleaned.columns:
            null_rate = cleaned[col].null_count() / max(len(cleaned), 1)
            assert null_rate <= 0.5, f"Column {col} has {null_rate:.1%} nulls"


# ── Transformer tests ─────────────────────────────────────────────────────


class TestFeatureTransformer:
    def test_returns_transform_result(self, clean_df):
        transformer = FeatureTransformer(city_id="london")
        result = transformer.fit_transform(clean_df)
        assert result.features is not None
        assert len(result.feature_names) > 0
        assert len(result.target) == len(clean_df)

    def test_no_null_features(self, clean_df):
        transformer = FeatureTransformer(city_id="london")
        result = transformer.fit_transform(clean_df)
        total_nulls = sum(
            result.features[c].null_count() for c in result.features.columns
        )
        assert total_nulls == 0

    def test_target_log_transformed(self, clean_df):
        transformer = FeatureTransformer(
            city_id="london", log_transform_price=True
        )
        result = transformer.fit_transform(clean_df)
        # log1p values should be positive and smaller than raw prices
        assert float(result.target.min()) > 0
        raw_price_max = float(clean_df["price"].max())
        assert float(result.target.max()) < raw_price_max


# ── Calendar features tests ───────────────────────────────────────────────


class TestCalendarFeatureEngineer:
    def test_adds_cal_columns(self, clean_df):
        eng = CalendarFeatureEngineer(city_id="london")
        df = eng.transform(clean_df)
        cal_cols = [c for c in df.columns if c.startswith("cal_")]
        assert len(cal_cols) >= 4

    def test_peak_season_binary(self, clean_df):
        eng = CalendarFeatureEngineer(city_id="barcelona")
        df = eng.transform(clean_df)
        assert "cal_is_peak_season" in df.columns
        assert set(df["cal_is_peak_season"].to_list()).issubset({0, 1})


# ── Text features tests ───────────────────────────────────────────────────


class TestTextFeatureEngineer:
    def test_adds_nlp_columns(self, clean_df):
        eng = TextFeatureEngineer(use_transformers=False)
        df = eng.fit_transform(clean_df)
        assert "nlp_sentiment_score" in df.columns

    def test_sentiment_range(self, clean_df):
        eng = TextFeatureEngineer(use_transformers=False)
        df = eng.fit_transform(clean_df)
        scores = df["nlp_sentiment_score"].to_list()
        assert all(-1.0 <= s <= 1.0 for s in scores)


# ── Drift detector tests ──────────────────────────────────────────────────


class TestDriftDetector:
    def test_no_drift_on_same_distribution(self, clean_df):
        detector = DriftDetector(significance_level=0.01)
        transformer = FeatureTransformer(city_id="london")
        result = transformer.fit_transform(clean_df)
        feature_df = result.features

        detector.fit(feature_df)
        report = detector.detect(feature_df, city_id="london")
        # Same distribution — should report no drift or very low score
        assert report.overall_drift_score < 0.5

    def test_drift_detected_on_different_distribution(self):
        rng = np.random.default_rng(42)
        ref = pl.DataFrame({"x": rng.normal(0, 1, 500).tolist()})
        shifted = pl.DataFrame({"x": rng.normal(5, 1, 500).tolist()})

        detector = DriftDetector(significance_level=0.05)
        detector.fit(ref)
        report = detector.detect(shifted, city_id="test")
        assert report.n_drifted_features >= 1


# ── Performance monitor tests ─────────────────────────────────────────────


class TestPerformanceMonitor:
    def test_snapshot_empty(self):
        monitor = PerformanceMonitor(city_id="london")
        snap = monitor.get_snapshot()
        assert snap.n_predictions == 0
        assert snap.rmse is None

    def test_records_predictions(self):
        monitor = PerformanceMonitor(city_id="london")
        for i in range(10):
            monitor.record_prediction(
                predicted=100.0 + i,
                actual=105.0 + i,
                latency_ms=50.0,
            )
        snap = monitor.get_snapshot()
        assert snap.n_predictions == 10
        assert snap.rmse is not None
        assert snap.avg_latency_ms is not None

    def test_alert_fires_on_high_rmse(self):
        monitor = PerformanceMonitor(
            city_id="london",
            rmse_warning_threshold=0.05,
            rmse_critical_threshold=0.10,
        )
        # Record very bad predictions
        for _ in range(100):
            monitor.record_prediction(
                predicted=500.0, actual=50.0, latency_ms=10.0
            )
        alerts = monitor.get_active_alerts()
        assert len(alerts) > 0
        assert any(a.metric == "rmse" for a in alerts)


# ── A/B testing tests ─────────────────────────────────────────────────────


class TestABTestingManager:
    def test_create_experiment(self):
        mgr = ABTestingManager()
        exp_id = mgr.create_experiment(
            name="Test Exp",
            variants=[
                Variant("control", "model_a", 0.5),
                Variant("treatment", "model_b", 0.5),
            ],
        )
        assert exp_id.startswith("exp_")

    def test_invalid_split_raises(self):
        mgr = ABTestingManager()
        with pytest.raises(ValueError, match="sum to 1.0"):
            mgr.create_experiment(
                name="Bad",
                variants=[
                    Variant("a", "m1", 0.3),
                    Variant("b", "m2", 0.3),
                ],
            )

    def test_consistent_hashing(self):
        mgr = ABTestingManager()
        exp_id = mgr.create_experiment(
            name="Hash Test",
            variants=[
                Variant("control", "m1", 0.5),
                Variant("treatment", "m2", 0.5),
            ],
        )
        mgr.start_experiment(exp_id)
        # Same key should always get same variant
        results = [
            mgr.assign_variant(exp_id, "listing_42").name for _ in range(10)
        ]
        assert len(set(results)) == 1  # all the same

    def test_analyse_returns_result(self):
        mgr = ABTestingManager()
        exp_id = mgr.create_experiment(
            name="Analyse Test",
            variants=[
                Variant("control", "m1", 0.5),
                Variant("treatment", "m2", 0.5),
            ],
        )
        mgr.start_experiment(exp_id)
        # Record some observations with different quality
        rng = np.random.default_rng(42)
        for _ in range(50):
            mgr.record_observation(
                exp_id, "control", rng.normal(100, 10), rng.normal(105, 10)
            )
            mgr.record_observation(
                exp_id, "treatment", rng.normal(100, 10), rng.normal(102, 8)
            )
        result = mgr.analyse(exp_id)
        assert result.experiment_id == exp_id
        assert isinstance(result.p_value, float)


# ── Validation tests ──────────────────────────────────────────────────────


class TestDataValidator:
    def test_valid_raw_data(self, small_raw_df):
        validator = DataValidator()
        report = validator.validate(small_raw_df, stage="raw")
        assert report.n_rows == len(small_raw_df)
        assert report.success_rate > 0.5

    def test_empty_dataframe_fails(self):
        validator = DataValidator()
        empty = pl.DataFrame({"id": [], "price": []})
        report = validator.validate(empty, stage="raw")
        # expect_not_empty should fail
        assert report.n_failed >= 1
