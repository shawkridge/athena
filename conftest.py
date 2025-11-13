"""Root pytest configuration for Athena - PostgreSQL testing setup.

Provides:
- PostgreSQL database fixtures with proper isolation
- Environment variable configuration
- Database cleanup between tests
- Async context handling for PostgreSQL tests
"""

import pytest
import os
import sys
from pathlib import Path


# ============================================================================
# PostgreSQL Configuration
# ============================================================================

# Default PostgreSQL connection parameters
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "athena_test")

# Check if PostgreSQL is available
def is_postgres_available() -> bool:
    """Check if PostgreSQL server is available."""
    try:
        import psycopg
        conn = psycopg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "postgres: mark test as requiring PostgreSQL"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Auto-skip PostgreSQL Tests if Not Available
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Auto-skip PostgreSQL tests if database not available."""
    # Check once at startup
    postgres_available = is_postgres_available()

    for item in items:
        # Mark all unit tests that import athena as needing postgres
        if "athena" in str(item.fspath):
            if not postgres_available:
                item.add_marker(
                    pytest.mark.skip(
                        reason="PostgreSQL server not available. "
                        "Start PostgreSQL or set POSTGRES_HOST environment variable"
                    )
                )


# ============================================================================
# PostgreSQL Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def postgres_available():
    """Session-level fixture indicating if PostgreSQL is available."""
    return is_postgres_available()


@pytest.fixture
def reset_database_singleton():
    """Reset the database singleton between tests for isolation."""
    from athena.core.database import reset_database
    reset_database()
    yield
    reset_database()


@pytest.fixture
def test_db(reset_database_singleton):
    """Provide a test database connection to PostgreSQL.

    Uses the athena_test database. Assumes PostgreSQL is running.
    """
    from athena.core.database import get_database

    # Get database singleton (uses test database)
    db = get_database(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
    )

    yield db

    # No cleanup needed - tests use same DB with isolation


@pytest.fixture
def test_project(test_db):
    """Create a test project in the database."""
    project = test_db.create_project(
        name="test_project",
        path="/test/project"
    )
    yield project
    # Cleanup: project is deleted when database is reset


# ============================================================================
# Async Support
# ============================================================================

@pytest.fixture
def event_loop():
    """Provide event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Logging Configuration
# ============================================================================

def pytest_configure_logging(config):
    """Configure logging for tests."""
    import logging
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings and errors during tests
        format="%(name)s - %(levelname)s - %(message)s"
    )


# ============================================================================
# Test Timeout Configuration
# ============================================================================

pytest_plugins = ["pytest-asyncio"]

# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line(
        "asyncio_mode", "auto"
    )
