#!/usr/bin/env python3
"""Diagnostic test for SyncCursor INSERT with RETURNING issue."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from athena.core.database_postgres import PostgresDatabase


def test_insert_with_returning():
    """Test that SyncCursor can handle INSERT with RETURNING."""
    logger.info("=== Testing SyncCursor INSERT with RETURNING ===")

    db = PostgresDatabase(dbname="athena_test")

    # Get a cursor
    cursor = db.get_cursor()
    logger.info(f"Got cursor: {cursor}")
    logger.info(f"Initial _results: {cursor._results}")

    # Execute INSERT with RETURNING - use unique name
    import time
    project_name = f"test_project_{int(time.time() * 1000) % 1000000}"
    project_path = f"/test/path/{int(time.time() * 1000) % 1000000}"

    query = """
    INSERT INTO projects (name, path)
    VALUES (%s, %s)
    RETURNING id, name, path
    """

    logger.info(f"Executing: {query.strip()}")
    logger.info(f"Params: ({project_name}, {project_path})")

    try:
        cursor.execute(query, (project_name, project_path))
        logger.info("✅ execute() completed successfully")
    except Exception as e:
        logger.error(f"❌ execute() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info(f"After execute():")
    logger.info(f"  cursor._results type: {type(cursor._results)}")
    logger.info(f"  cursor._results: {cursor._results}")
    logger.info(f"  cursor._row_index: {cursor._row_index}")

    # Try to fetch
    if cursor._results is not None and len(cursor._results) > 0:
        row = cursor.fetchone()
        logger.info(f"✅ fetchone() returned: {row}")
        if row:
            logger.info(f"   ID: {row[0]}, Name: {row[1]}, Path: {row[2]}")
            return True
        else:
            logger.error("❌ fetchone() returned None")
            return False
    else:
        logger.error(f"❌ cursor._results is empty or None")
        logger.error(f"   Length: {len(cursor._results) if cursor._results else 0}")
        return False


def test_select_from_projects():
    """Test that we can SELECT from projects table."""
    logger.info("\n=== Testing SELECT from projects table ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    query = "SELECT id, name, path FROM projects LIMIT 1"
    logger.info(f"Executing: {query}")

    try:
        cursor.execute(query)
        logger.info("✅ execute() completed")
    except Exception as e:
        logger.error(f"❌ execute() failed: {e}")
        return False

    logger.info(f"cursor._results: {cursor._results}")

    if cursor._results and len(cursor._results) > 0:
        row = cursor.fetchone()
        logger.info(f"✅ fetchone() returned: {row}")
        return True
    else:
        logger.info("⚠️  No rows in projects table (expected for empty database)")
        return True


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("SyncCursor INSERT with RETURNING Diagnostic Test")
    logger.info("=" * 70)

    # Test 1: SELECT from projects
    test_select_from_projects()

    # Test 2: INSERT with RETURNING
    success = test_insert_with_returning()

    logger.info("\n" + "=" * 70)
    if success:
        logger.info("✅ All tests passed")
    else:
        logger.info("❌ Tests failed")
    logger.info("=" * 70)
