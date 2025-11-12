"""Database module - PostgreSQL only (no SQLite).

This module provides backward compatibility by re-exporting PostgreSQL database class.
All direct imports from this module are now routed to PostgreSQL implementation.

Also provides a singleton pattern for centralized database access across the codebase.
"""

from typing import Optional
from .database_postgres import PostgresDatabase

# Maintain backward compatibility with existing imports
Database = PostgresDatabase

# Global singleton instance
_database_instance: Optional[PostgresDatabase] = None
_initialized = False


def get_database(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "athena",
    user: str = "postgres",
    password: str = "postgres",
    min_size: int = 2,
    max_size: int = 10,
) -> PostgresDatabase:
    """Get or create the global Database singleton instance.

    This function implements a singleton pattern for database access, ensuring
    that all modules across Athena use a single connection pool instead of
    creating multiple instances.

    The singleton is created on first call with provided parameters. Subsequent
    calls return the same instance, ignoring any new parameters passed.

    Args:
        host: PostgreSQL server host (default: localhost)
        port: PostgreSQL server port (default: 5432)
        dbname: Database name (default: athena)
        user: Database user (default: postgres)
        password: Database password (default: postgres)
        min_size: Minimum connections in pool (default: 2)
        max_size: Maximum connections in pool (default: 10)

    Returns:
        PostgresDatabase singleton instance

    Note:
        The async connection pool is lazily initialized on first use (when
        await db.initialize() is called). This is intentional to support
        both sync and async contexts without forcing event loop creation
        during singleton instantiation.

    Example:
        # First call creates the instance
        db = get_database(host="localhost", port=5432)

        # Subsequent calls return the same instance
        db2 = get_database()  # Returns same instance, ignores parameters
        assert db is db2  # True

        # If using in async context, initialize the pool
        await db.initialize()

    Benefits:
        - Single connection pool shared across all modules
        - Reduced memory overhead (no duplicate pools)
        - Centralized configuration (all uses same defaults)
        - Easy to swap implementation (only change this function)
        - Enables caching, fallback logic, and connection pooling improvements
        - Lazy initialization avoids event loop requirements during startup
    """
    global _database_instance, _initialized

    if _database_instance is None:
        _database_instance = PostgresDatabase(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            min_size=min_size,
            max_size=max_size,
        )
        _initialized = True

    return _database_instance


async def initialize_database(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "athena",
    user: str = "postgres",
    password: str = "postgres",
    min_size: int = 2,
    max_size: int = 10,
) -> PostgresDatabase:
    """Initialize the global Database singleton with async pool setup.

    This is an async version of get_database() that also initializes the
    connection pool. Use this at application startup to ensure the pool
    is ready before any code tries to use it.

    Args:
        host: PostgreSQL server host (default: localhost)
        port: PostgreSQL server port (default: 5432)
        dbname: Database name (default: athena)
        user: Database user (default: postgres)
        password: Database password (default: postgres)
        min_size: Minimum connections in pool (default: 2)
        max_size: Maximum connections in pool (default: 10)

    Returns:
        PostgresDatabase singleton instance with initialized async pool

    Example (in your main/startup code):
        # Initialize at startup
        db = await initialize_database(host="localhost")
        # Pool is now ready for queries

        # Later code can just get it
        db2 = get_database()  # Returns already-initialized singleton

    Benefits over get_database():
        - Pool is initialized immediately (no lazy initialization)
        - Errors during pool setup happen at startup, not at first query
        - Clearer intent (explicitly initializing for production)
        - Better for detecting configuration errors early
    """
    db = get_database(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        min_size=min_size,
        max_size=max_size,
    )
    # Initialize the connection pool
    await db.initialize()
    return db


def reset_database() -> None:
    """Reset the database singleton (primarily for testing).

    This function resets the global database instance, allowing a fresh
    singleton to be created with different parameters.

    Use Case:
        - Testing with different database configurations
        - Switching between test/production databases
        - Cleaning up resources between test suites

    Example:
        # Create instance with test configuration
        db = get_database(dbname="test_athena")

        # ... run tests ...

        # Reset for next test
        reset_database()
        db2 = get_database(dbname="test_athena_2")
    """
    global _database_instance, _initialized
    _database_instance = None
    _initialized = False


__all__ = ["Database", "PostgresDatabase", "get_database", "initialize_database", "reset_database"]
