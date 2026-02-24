# tests/integration/test_pipeline.py
# Urban Intelligence Framework - Pipeline Integration Tests
# End-to-end tests for the complete ML pipeline

"""
Integration tests for the Urban Intelligence pipeline.

These tests verify that all components work together correctly:
    - Data generation and loading
    - ETL processing
    - Model training
    - Prediction serving
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest


class TestDataPipeline:
    """Integration tests for data pipeline."""

    @pytest.fixture
    def temp_data_dir(self) -> Path:
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_synthetic_data_generation(self, temp_data_dir: Path) -> None:
        """Test that synthetic data generation works end-to-end."""
        from src.data.generator import SyntheticDataGenerator

        generator = SyntheticDataGenerator(n_samples=100, seed=42)
        df = generator.generate()

        # Verify basic structure
        assert df.height == 100
        assert "price" in df.columns
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "room_type" in df.columns

        # Verify data quality
        assert df["price"].null_count() < 10  # Allow some nulls
        assert df["latitude"].min() >= -90
        assert df["latitude"].max() <= 90

    def test_etl_pipeline(self, temp_data_dir: Path) -> None:
        """Test that ETL pipeline processes data correctly."""
        from src.data.generator import SyntheticDataGenerator
        from src.etl.cleaner import AirbnbCleaner
        from src.etl.transformer import FeatureTransformer

        # Generate test data
        generator = SyntheticDataGenerator(n_samples=200, seed=42)
        raw_df = generator.generate()

        # Run cleaner
        cleaner = AirbnbCleaner()
        cleaned_df = cleaner.clean(raw_df)

        # Verify cleaning
        assert cleaned_df.height > 0
        assert cleaned_df["price"].null_count() == 0  # Prices should be cleaned

        # Run transformer
        transformer = FeatureTransformer()
        transformed_df = transformer.transform(cleaned_df)

        # Verify transformation
        assert transformed_df.width >= cleaned_df.width  # Should add features

    def test_full_training_pipeline(self, temp_data_dir: Path) -> None:
        """Test the complete training pipeline."""
        from src.data.generator import SyntheticDataGenerator
        from src.etl.cleaner import AirbnbCleaner
        from src.etl.transformer import FeatureTransformer
        from src.modeling.trainer import ModelTrainer

        # Generate and process data
        generator = SyntheticDataGenerator(n_samples=500, seed=42)
        raw_df = generator.generate()

        cleaner = AirbnbCleaner()
        cleaned_df = cleaner.clean(raw_df)

        transformer = FeatureTransformer()
        transformed_df = transformer.transform(cleaned_df)

        # Prepare features and target
        feature_cols = [
            c for c in transformed_df.columns if c not in ["price", "id", "name", "description"]
        ]

        # Filter to numeric columns only
        numeric_cols = [
            c
            for c in feature_cols
            if transformed_df[c].dtype in [pl.Float64, pl.Int64, pl.Float32, pl.Int32]
        ]

        if len(numeric_cols) < 5:
            pytest.skip("Not enough numeric features for training")

        features_array = transformed_df.select(numeric_cols[:10]).to_numpy()
        y = transformed_df["price"].to_numpy()

        # Train model (quick test with minimal optimization)
        trainer = ModelTrainer(n_trials=2, cv_folds=2)
        model, metrics = trainer.train(features_array, y)

        # Verify model
        assert model is not None
        assert "mae" in metrics or "test_mae" in metrics


class TestAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for API."""
        from fastapi.testclient import TestClient

        from api.main import app

        return TestClient(app)

    def test_health_endpoint(self, client) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self, client) -> None:
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_cities_endpoint(self, client) -> None:
        """Test cities listing endpoint."""
        response = client.get("/cities")
        # May return 503 if data service not initialized
        assert response.status_code in [200, 503]

    def test_prediction_validation(self, client) -> None:
        """Test prediction endpoint input validation."""
        # Invalid request (missing required fields)
        response = client.post("/predict", json={})
        assert response.status_code == 422  # Validation error

        # Valid request structure (may fail if model not loaded)
        valid_request = {
            "accommodates": 4,
            "bedrooms": 2,
            "beds": 2,
            "bathrooms": 1,
            "latitude": 40.4168,
            "longitude": -3.7038,
            "room_type": "Entire home/apt",
        }
        response = client.post("/predict", json=valid_request)
        # Should be 200 (success) or 503 (model not loaded)
        assert response.status_code in [200, 503]


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
            yield Path(f.name)

    def test_duckdb_operations(self, temp_db: Path) -> None:
        """Test DuckDB manager operations."""
        from src.database.duckdb_manager import DuckDBManager

        manager = DuckDBManager(temp_db)

        # Store and retrieve
        manager.conn.execute("CREATE TABLE test_listings AS SELECT * FROM test_df")

        result = manager.conn.execute("SELECT COUNT(*) FROM test_listings").fetchone()
        assert result[0] == 3

        manager.close()

    def test_cache_manager(self, temp_db: Path) -> None:
        """Test cache manager operations."""
        from src.data.city_registry import CacheManager

        cache = CacheManager(temp_db)

        # Create test data
        listings_df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "price": [100.0, 150.0, 200.0],
                "latitude": [40.4, 40.5, 40.6],
                "longitude": [-3.7, -3.8, -3.9],
            }
        )

        # Store listings
        count = cache.store_listings("test_city", listings_df)
        assert count == 3

        # Retrieve listings
        retrieved = cache.get_listings("test_city")
        assert retrieved.height == 3

        cache.close()


class TestEnrichmentIntegration:
    """Integration tests for data enrichment."""

    def test_weather_enrichment(self) -> None:
        """Test weather data enrichment."""
        from src.enrichment.weather import WeatherEnricher

        # Create mock weather data
        weather_df = pl.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "temp_mean_c": [10.0, 12.0, 11.0],
                "temp_max_c": [15.0, 18.0, 16.0],
                "temp_min_c": [5.0, 6.0, 6.0],
                "precipitation_mm": [0.0, 5.0, 2.0],
                "sunshine_hours": [8.0, 4.0, 6.0],
            }
        )

        # Test enricher initialization
        enricher = WeatherEnricher(weather_df)
        assert enricher is not None

    def test_poi_enrichment(self) -> None:
        """Test POI data enrichment."""
        from src.enrichment.spatial import SpatialEnricher

        # Create mock POI data
        pois_df = pl.DataFrame(
            {
                "poi_id": [1, 2, 3],
                "category": ["metro_station", "restaurant", "park"],
                "latitude": [40.4168, 40.4200, 40.4100],
                "longitude": [-3.7038, -3.7000, -3.7100],
            }
        )

        # Test enricher
        enricher = SpatialEnricher(pois_df)
        assert enricher is not None


# =============================================================================
# Fixtures for all tests
# =============================================================================


@pytest.fixture(scope="session")
def sample_listings() -> pl.DataFrame:
    """Create sample listings for testing."""
    return pl.DataFrame(
        {
            "id": list(range(1, 101)),
            "price": [100.0 + i * 10 for i in range(100)],
            "latitude": [40.4 + i * 0.001 for i in range(100)],
            "longitude": [-3.7 - i * 0.001 for i in range(100)],
            "room_type": ["Entire home/apt"] * 50 + ["Private room"] * 50,
            "accommodates": [2 + (i % 4) for i in range(100)],
            "bedrooms": [1 + (i % 3) for i in range(100)],
            "beds": [1 + (i % 4) for i in range(100)],
            "bathrooms": [1.0 + (i % 2) * 0.5 for i in range(100)],
        }
    )
