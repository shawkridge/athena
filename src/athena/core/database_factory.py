"""Database factory for supporting multiple backends (SQLite, PostgreSQL).

This module provides configuration-driven database selection,
allowing seamless transition from Phase 4 (SQLite) to Phase 5 (PostgreSQL).
"""

import os
from typing import Union, Optional
from pathlib import Path

# Try to import both backends
try:
    from .database import Database as SQLiteDatabase
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

try:
    from .database_postgres import PostgresDatabase
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseFactory:
    """Factory for creating database instances based on configuration.

    Priority order:
    1. ATHENA_DB_TYPE environment variable
    2. ATHENA_POSTGRES_* environment variables (for PostgreSQL)
    3. ATHENA_DB_PATH environment variable (for SQLite)
    4. Default: SQLite at ~/.athena/memory.db

    Usage:
        # Automatic selection based on environment
        db = DatabaseFactory.create()

        # Force PostgreSQL
        db = DatabaseFactory.create(backend='postgres')

        # Force SQLite
        db = DatabaseFactory.create(backend='sqlite')

        # Custom PostgreSQL connection
        db = DatabaseFactory.create(
            backend='postgres',
            host='localhost',
            port=5432,
            dbname='athena',
            user='athena',
            password='athena_dev'
        )
    """

    # Supported backends
    BACKENDS = {
        'sqlite': SQLiteDatabase if SQLITE_AVAILABLE else None,
        'postgres': PostgresDatabase if POSTGRES_AVAILABLE else None,
        'postgresql': PostgresDatabase if POSTGRES_AVAILABLE else None,
    }

    @classmethod
    def create(
        cls,
        backend: Optional[str] = None,
        **kwargs
    ) -> Union[SQLiteDatabase, PostgresDatabase]:
        """Create a database instance.

        Args:
            backend: Database backend ('sqlite', 'postgres', or None for auto-detect)
            **kwargs: Backend-specific configuration

        Returns:
            Database instance (SQLiteDatabase or PostgresDatabase)

        Raises:
            ValueError: If backend is not available or invalid
        """

        # Auto-detect backend if not specified
        if backend is None:
            backend = cls._detect_backend()

        backend = backend.lower()

        if backend not in cls.BACKENDS:
            raise ValueError(
                f"Unknown backend: {backend}. "
                f"Supported: {list(cls.BACKENDS.keys())}"
            )

        backend_class = cls.BACKENDS[backend]
        if backend_class is None:
            raise ValueError(
                f"Backend '{backend}' is not available. "
                f"Install required dependencies (psycopg for PostgreSQL, sqlite3 for SQLite)"
            )

        # Create instance based on backend
        if backend == 'sqlite':
            return cls._create_sqlite(**kwargs)
        else:  # postgres or postgresql
            return cls._create_postgres(**kwargs)

    @classmethod
    def _detect_backend(cls) -> str:
        """Detect backend from environment.

        Detection priority:
        1. ATHENA_DB_TYPE environment variable
        2. ATHENA_POSTGRES_HOST (if set, use PostgreSQL)
        3. Default to SQLite

        Returns:
            Backend name ('sqlite' or 'postgres')
        """

        # Check explicit backend selection
        if 'ATHENA_DB_TYPE' in os.environ:
            return os.environ['ATHENA_DB_TYPE'].lower()

        # Check PostgreSQL environment variables
        if os.environ.get('ATHENA_POSTGRES_HOST'):
            return 'postgres'

        # Default to SQLite
        return 'sqlite'

    @classmethod
    def _create_sqlite(cls, **kwargs) -> SQLiteDatabase:
        """Create SQLite database instance.

        Args:
            **kwargs: SQLite-specific config (db_path)

        Returns:
            SQLiteDatabase instance
        """

        # Get database path from kwargs or environment
        if 'db_path' in kwargs:
            db_path = kwargs['db_path']
        else:
            db_path = os.environ.get(
                'ATHENA_DB_PATH',
                str(Path.home() / '.athena' / 'memory.db')
            )

        return SQLiteDatabase(db_path)

    @classmethod
    def _create_postgres(cls, **kwargs) -> PostgresDatabase:
        """Create PostgreSQL database instance.

        Args:
            **kwargs: PostgreSQL-specific config (host, port, dbname, user, password, etc.)

        Returns:
            PostgresDatabase instance
        """

        # Get configuration from kwargs or environment
        config = {
            'host': kwargs.get('host') or os.environ.get('ATHENA_POSTGRES_HOST', 'localhost'),
            'port': int(kwargs.get('port') or os.environ.get('ATHENA_POSTGRES_PORT', '5432')),
            'dbname': kwargs.get('dbname') or os.environ.get('ATHENA_POSTGRES_DBNAME', 'athena'),
            'user': kwargs.get('user') or os.environ.get('ATHENA_POSTGRES_USER', 'athena'),
            'password': kwargs.get('password') or os.environ.get('ATHENA_POSTGRES_PASSWORD', 'athena_dev'),
            'min_size': int(kwargs.get('min_size') or os.environ.get('ATHENA_POSTGRES_MIN_SIZE', '2')),
            'max_size': int(kwargs.get('max_size') or os.environ.get('ATHENA_POSTGRES_MAX_SIZE', '10')),
        }

        return PostgresDatabase(**config)

    @classmethod
    def get_available_backends(cls) -> list[str]:
        """Get list of available backends.

        Returns:
            List of available backend names
        """
        return [name for name, impl in cls.BACKENDS.items() if impl is not None]

    @classmethod
    def is_backend_available(cls, backend: str) -> bool:
        """Check if a backend is available.

        Args:
            backend: Backend name to check

        Returns:
            True if available, False otherwise
        """
        return cls.BACKENDS.get(backend.lower()) is not None


# Convenience function for quick database creation
def get_database(
    backend: Optional[str] = None,
    **kwargs
) -> Union[SQLiteDatabase, PostgresDatabase]:
    """Get a database instance.

    This is a convenience function that wraps DatabaseFactory.create().

    Args:
        backend: Database backend ('sqlite', 'postgres', or None for auto-detect)
        **kwargs: Backend-specific configuration

    Returns:
        Database instance

    Example:
        # Auto-detect from environment
        db = get_database()

        # Explicit PostgreSQL
        db = get_database(backend='postgres')

        # Custom configuration
        db = get_database(
            backend='postgres',
            host='localhost',
            port=5432,
            dbname='athena',
            user='athena',
            password='athena_dev'
        )
    """
    return DatabaseFactory.create(backend, **kwargs)
