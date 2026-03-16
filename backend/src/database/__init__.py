# backend/src/database/__init__.py
# Urban Intelligence Framework v2.0.0
# Database module exports

"""DuckDB-based local OLAP engine."""

from src.database.db_manager import DatabaseManager, db

__all__ = ["DatabaseManager", "db"]
