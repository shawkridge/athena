"""Test database implementation using SQLite for unit tests.

This provides a lightweight SQLite database for testing purposes,
avoiding the need for a PostgreSQL server in unit tests.
"""

import sqlite3
from pathlib import Path
from typing import Optional


class TestDatabase:
    """Simple SQLite database for testing."""

    def __init__(self, db_path: str):
        """Initialize test database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        # Return rows as dict-like objects
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
