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

    Local configuration (no Docker):
    - ATHENA_POSTGRES_HOST: localhost (local Postgres)
    - ATHENA_POSTGRES_PORT: 5432
    - ATHENA_POSTGRES_DB: athena
    - ATHENA_POSTGRES_USER: postgres (default Postgres user)
    - ATHENA_POSTGRES_PASSWORD: postgres (default Postgres password)

    Usage:
        # Automatic creation with localhost defaults
        db = DatabaseFactory.create()

        # Custom PostgreSQL connection
        db = DatabaseFactory.create(
            host='localhost',
            port=5432,
            dbname='athena',
            user='postgres',
            password='postgres'
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
        """Create PostgreSQL database instance.

        Configuration priority:
        1. Explicit kwargs (passed to method)
        2. Environment variables (for host-based development)
        3. Docker defaults (fallback)

        Environment variables:
        - ATHENA_POSTGRES_HOST: PostgreSQL host (default: "localhost")
        - ATHENA_POSTGRES_PORT: PostgreSQL port (default: 5432)
        - ATHENA_POSTGRES_DB: Database name (default: athena)
        - ATHENA_POSTGRES_USER: Database user (default: postgres)
        - ATHENA_POSTGRES_PASSWORD: Database password (default: postgres)

        Args:
            **kwargs: PostgreSQL-specific config (overrides environment/defaults)

        Returns:
            PostgresDatabase instance
        """

        # Configuration with proper priority: kwargs > env > defaults
        # Defaults changed from Docker (postgres/athena) to localhost Postgres (localhost/postgres)
        config = {
            'host': kwargs.get(
                'host',
                os.environ.get('ATHENA_POSTGRES_HOST', 'localhost')
            ),
            'port': int(kwargs.get(
                'port',
                os.environ.get('ATHENA_POSTGRES_PORT', '5432')
            )),
            'dbname': kwargs.get(
                'dbname',
                os.environ.get('ATHENA_POSTGRES_DB', 'athena')
            ),
            'user': kwargs.get(
                'user',
                os.environ.get('ATHENA_POSTGRES_USER', 'postgres')
            ),
            'password': kwargs.get(
                'password',
                os.environ.get('ATHENA_POSTGRES_PASSWORD', 'postgres')
            ),
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
        # Use localhost defaults
        db = get_database()

        # Custom configuration
        db = get_database(
            host='localhost',
            port=5432,
            dbname='athena',
            user='postgres',
            password='postgres'
        )
    """
    return DatabaseFactory.create(**kwargs)
