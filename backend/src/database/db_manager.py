# backend/src/database/db_manager.py
# Urban Intelligence Framework v2.0.0
# DuckDB-based local OLAP engine for fast analytical queries

"""
Database manager module.

Provides a thread-safe DuckDB connection manager that supports:
- Parquet file registration as virtual tables
- Fast analytical SQL queries
- Schema management and migrations
"""

import re
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb
import polars as pl
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)
_SAFE_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseManager:
    """
    Thread-safe wrapper around DuckDB with Polars integration.

    Uses a single persistent connection per instance, protected by a
    re-entrant lock to allow nested usage within the same thread.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or settings.database_path
        self._lock = threading.RLock()
        self._conn: duckdb.DuckDBPyConnection | None = None

    # ── Lifecycle ────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the DuckDB connection and initialise schema."""
        if self._conn is not None:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self._db_path))
        logger.info("DuckDB connected", path=str(self._db_path))
        self._init_schema()

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DuckDB connection closed")

    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager that ensures a live connection."""
        if self._conn is None:
            self.connect()
        with self._lock:
            yield self._conn  # type: ignore[misc]

    # ── Schema initialisation ────────────────────────────────────────────

    def _init_schema(self) -> None:
        """Create core tables if they do not already exist."""
        ddl_statements = [
            # City registry
            """
            CREATE TABLE IF NOT EXISTS cities (
                city_id     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                country     TEXT,
                latitude    DOUBLE,
                longitude   DOUBLE,
                currency    TEXT DEFAULT 'USD',
                last_fetched TIMESTAMP,
                listing_count INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Predictions log
            """
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                city_id       TEXT,
                model_version TEXT,
                predicted_price DOUBLE NOT NULL,
                actual_price    DOUBLE,
                features        JSON,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Model metadata
            """
            CREATE TABLE IF NOT EXISTS model_registry (
                model_id      TEXT PRIMARY KEY,
                city_id       TEXT,
                model_type    TEXT,
                mlflow_run_id TEXT,
                metrics       JSON,
                params        JSON,
                is_active     BOOLEAN DEFAULT false,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # Monitoring events
            """
            CREATE TABLE IF NOT EXISTS monitoring_events (
                event_id    TEXT PRIMARY KEY,
                event_type  TEXT NOT NULL,
                city_id     TEXT,
                severity    TEXT DEFAULT 'info',
                payload     JSON,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # A/B experiments
            """
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                status        TEXT DEFAULT 'draft',
                config        JSON,
                metrics       JSON,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        with self._lock:
            for stmt in ddl_statements:
                self._conn.execute(stmt)  # type: ignore[union-attr]
        logger.info("Database schema initialised")

    # ── Query helpers ────────────────────────────────────────────────────

    def query(self, sql: str, params: list[Any] | None = None) -> pl.DataFrame:
        """Execute a SELECT query and return a Polars DataFrame."""
        with self.connection() as conn:
            result = conn.execute(sql, params or [])
            frame = pl.from_arrow(result.arrow())
            return (
                frame if isinstance(frame, pl.DataFrame) else frame.to_frame()
            )

    def read_table(self, name: str) -> pl.DataFrame:
        """Read a DuckDB table/view by validated identifier."""
        if not _SAFE_SQL_IDENTIFIER.fullmatch(name):
            raise ValueError(f"Unsafe table/view name: {name}")
        with self.connection() as conn:
            rel = conn.table(name)
            frame = pl.from_arrow(rel.arrow())
            return (
                frame if isinstance(frame, pl.DataFrame) else frame.to_frame()
            )

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        """Execute a non-SELECT statement (INSERT / UPDATE / DELETE / DDL)."""
        with self.connection() as conn:
            conn.execute(sql, params or [])

    def register_parquet(self, name: str, path: Path) -> None:
        """
        Register a Parquet file as a virtual DuckDB view.

        After registration, the file is queryable as `SELECT * FROM {name}`.
        """
        if not _SAFE_SQL_IDENTIFIER.fullmatch(name):
            raise ValueError(f"Unsafe view name: {name}")

        with self.connection() as conn:
            conn.from_parquet(str(path)).create_view(name, replace=True)
        logger.info("Parquet view registered", name=name, path=str(path))

    def table_exists(self, table_name: str) -> bool:
        """Return True if a table or view with the given name exists."""
        with self.connection() as conn:
            result = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()
            return bool(result and result[0] > 0)


# ── Module-level singleton ────────────────────────────────────────────────
db = DatabaseManager()
