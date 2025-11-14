#!/usr/bin/env python3
"""Diagnostic test for SyncCursor async/sync bridge issue."""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from athena.core.database_postgres import PostgresDatabase, SyncCursor


async def test_async_database_works():
    """Test that async database operations work."""
    logger.info("=== Testing async database operations ===")
    db = PostgresDatabase()
    await db.initialize()

    # Try a simple async query
    async with db.get_connection() as conn:
        cursor = await conn.execute("SELECT 1 as test_value")
        result = await cursor.fetchone()
        logger.info(f"Async query result: {result}")
        assert result is not None, "Async query should return a result"

    await db.close()
    logger.info("✅ Async database operations work")


def test_sync_cursor_execute():
    """Test that SyncCursor.execute() properly sets _results."""
    logger.info("=== Testing SyncCursor.execute() ===")

    # Create database
    db = PostgresDatabase()

    # Get a sync cursor
    cursor = db.get_cursor()
    logger.info(f"Got cursor: {cursor}")
    logger.info(f"Initial _results: {cursor._results}")

    # Execute a simple query
    logger.info("Calling cursor.execute('SELECT 1 as test_value')")
    result = cursor.execute("SELECT 1 as test_value")

    logger.info(f"After execute():")
    logger.info(f"  cursor._results: {cursor._results}")
    logger.info(f"  cursor._results is None: {cursor._results is None}")

    # Try to fetch
    if cursor._results is not None:
        row = cursor.fetchone()
        logger.info(f"✅ fetchone() returned: {row}")
    else:
        logger.error("❌ cursor._results is still None after execute()")
        logger.error("This is the SyncCursor bridge issue!")
        return False

    return True


def test_sync_cursor_with_create():
    """Test that SyncCursor can handle INSERT."""
    logger.info("=== Testing SyncCursor INSERT ===")

    db = PostgresDatabase()
    cursor = db.get_cursor()

    # Try a simple INSERT
    logger.info("Calling cursor.execute(INSERT query)")
    cursor.execute(
        "INSERT INTO test_table (value) VALUES (%s)",
        ("test_value",)
    )

    logger.info(f"After INSERT execute():")
    logger.info(f"  cursor._lastrowid: {cursor._lastrowid}")
    logger.info(f"  cursor._rowcount: {cursor._rowcount}")

    return True


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("SyncCursor Async/Sync Bridge Diagnostic Test")
    logger.info("=" * 60)

    # Test 1: Async works
    try:
        asyncio.run(test_async_database_works())
    except Exception as e:
        logger.error(f"Async database test failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: SyncCursor.execute()
    try:
        success = test_sync_cursor_execute()
        if success:
            logger.info("\n✅ SyncCursor works correctly")
        else:
            logger.error("\n❌ SyncCursor bridge is broken")
    except Exception as e:
        logger.error(f"SyncCursor test failed: {e}")
        import traceback
        traceback.print_exc()
