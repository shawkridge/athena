"""Database module - PostgreSQL only (no SQLite).

This module provides backward compatibility by re-exporting PostgreSQL database class.
All direct imports from this module are now routed to PostgreSQL implementation.
"""

from .database_postgres import PostgresDatabase

# Maintain backward compatibility with existing imports
Database = PostgresDatabase

__all__ = ["Database", "PostgresDatabase"]
