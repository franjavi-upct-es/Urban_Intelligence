# backend/tests/conftest.py
# Urban Intelligence Framework v2.0.0
# Pytest configuration and shared fixtures

"""Shared pytest fixtures for all test modules."""

import sys
from pathlib import Path

import pytest

# Ensure backend root is on sys.path when running pytest from project root
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Initialise test-safe settings (in-memory DB, temp paths)."""
    import tempfile

    from src.config import settings

    with tempfile.TemporaryDirectory() as tmp:
        settings.database_path = Path(tmp) / "test.db"
        settings.raw_data_path = Path(tmp) / "raw"
        settings.processed_data_path = Path(tmp) / "processed"
        settings.ensure_directories()
        yield
