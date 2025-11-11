"""Database factory for PostgreSQL backend only.

Docker-only configuration: PostgreSQL is the only supported backend.
No SQLite fallback.
"""

import os
from typing import Optional

try:
    from .database_postgres import PostgresDatabase
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseFactory:
    """Factory for creating PostgreSQL database instances.

    Docker configuration (no fallback):
    - ATHENA_POSTGRES_HOST: postgres (Docker service name)
    - ATHENA_POSTGRES_PORT: 5432
    - ATHENA_POSTGRES_DB: athena
    - ATHENA_POSTGRES_USER: athena
    - ATHENA_POSTGRES_PASSWORD: athena_password

    Usage:
        # Automatic creation with hardcoded Docker defaults
        db = DatabaseFactory.create()

        # Custom PostgreSQL connection
        db = DatabaseFactory.create(
            host='localhost',
            port=5432,
            dbname='athena',
            user='athena',
            password='athena_password'
        )
    """

    # Only PostgreSQL supported
    BACKENDS = {
        'postgres': PostgresDatabase if POSTGRES_AVAILABLE else None,
        'postgresql': PostgresDatabase if POSTGRES_AVAILABLE else None,
    }

    @classmethod
    def create(
        cls,
        backend: Optional[str] = None,
        **kwargs
    ) -> PostgresDatabase:
        """Create a PostgreSQL database instance.

        Args:
            backend: Ignored (PostgreSQL only)
            **kwargs: PostgreSQL-specific configuration

        Returns:
            PostgresDatabase instance

        Raises:
            ValueError: If PostgreSQL backend is not available
        """

        # PostgreSQL only
        backend_class = cls.BACKENDS.get('postgres')
        if backend_class is None:
            raise ValueError(
                "PostgreSQL backend is not available. "
                "Install required dependencies: pip install psycopg[binary]>=3.1.0"
            )

        return cls._create_postgres(**kwargs)


    @classmethod
    def _create_postgres(cls, **kwargs) -> PostgresDatabase:
        """Create PostgreSQL database instance with hardcoded Docker defaults.

        Docker configuration (no fallback):
        - host: postgres (Docker service name)
        - port: 5432
        - dbname: athena
        - user: athena
        - password: athena_password

        Args:
            **kwargs: PostgreSQL-specific config (only used if passed explicitly)

        Returns:
            PostgresDatabase instance
        """

        # Hardcoded Docker defaults - no environment variable fallback
        config = {
            'host': kwargs.get('host', 'postgres'),
            'port': int(kwargs.get('port', '5432')),
            'dbname': kwargs.get('dbname', 'athena'),
            'user': kwargs.get('user', 'athena'),
            'password': kwargs.get('password', 'athena_password'),
            'min_size': int(kwargs.get('min_size', '2')),
            'max_size': int(kwargs.get('max_size', '10')),
        }

        return PostgresDatabase(**config)

    @classmethod
    def get_available_backends(cls) -> list[str]:
        """Get list of available backends.

        Returns:
            List of available backend names (PostgreSQL only)
        """
        return [name for name, impl in cls.BACKENDS.items() if impl is not None]

    @classmethod
    def is_backend_available(cls, backend: str) -> bool:
        """Check if a backend is available.

        Args:
            backend: Backend name to check

        Returns:
            True if PostgreSQL is available, False otherwise
        """
        return cls.BACKENDS.get(backend.lower()) is not None


# Convenience function for quick database creation
def get_database(**kwargs) -> PostgresDatabase:
    """Get a PostgreSQL database instance.

    This is a convenience function that wraps DatabaseFactory.create().

    Args:
        **kwargs: PostgreSQL-specific configuration (optional, uses hardcoded Docker defaults)

    Returns:
        PostgresDatabase instance

    Example:
        # Use hardcoded Docker defaults
        db = get_database()

        # Custom configuration
        db = get_database(
            host='localhost',
            port=5432,
            dbname='athena',
            user='athena',
            password='athena_password'
        )
    """
    return DatabaseFactory.create(**kwargs)
