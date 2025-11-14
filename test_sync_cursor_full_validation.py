#!/usr/bin/env python3
"""Full validation test for SyncCursor bridge fix."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from athena.core.database_postgres import PostgresDatabase
from athena.core.models import Project


def test_synccursor_with_project_creation():
    """Test that SyncCursor can create and retrieve projects."""
    logger.info("=== Test 1: Project Creation with SyncCursor ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    # Insert project
    project_name = f"validation_test_{int(__import__('time').time() * 1000) % 1000000}"
    project_path = f"/validation/{project_name}"

    cursor.execute(
        "INSERT INTO projects (name, path) VALUES (%s, %s) RETURNING id, name, path",
        (project_name, project_path)
    )

    result = cursor.fetchone()
    assert result is not None, "fetchone() should return a result"
    assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
    assert result['name'] == project_name, f"Name mismatch: {result['name']} != {project_name}"

    project_id = result['id']
    logger.info(f"✅ Created project: {project_name} (ID: {project_id})")

    return project_id


def test_synccursor_select():
    """Test that SyncCursor can SELECT properly."""
    logger.info("\n=== Test 2: SELECT with SyncCursor ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    # Select from projects
    cursor.execute("SELECT id, name, path FROM projects LIMIT 5")
    results = cursor.fetchall()

    logger.info(f"✅ Retrieved {len(results)} projects")
    for row in results:
        logger.info(f"   - {row['name']} (ID: {row['id']})")

    return len(results) > 0


def test_synccursor_update_with_returning():
    """Test that SyncCursor can UPDATE with RETURNING."""
    logger.info("\n=== Test 3: UPDATE with RETURNING ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    # Create a project first
    project_name = f"update_test_{int(__import__('time').time() * 1000) % 1000000}"
    cursor.execute(
        "INSERT INTO projects (name, path) VALUES (%s, %s) RETURNING id",
        (project_name, f"/update/{project_name}")
    )
    project_id = cursor.fetchone()['id']

    # Update it with RETURNING
    new_description = "Updated via SyncCursor"
    cursor.execute(
        "UPDATE projects SET description = %s WHERE id = %s RETURNING id, name, description",
        (new_description, project_id)
    )

    result = cursor.fetchone()
    assert result is not None, "UPDATE with RETURNING should return a result"
    assert result['description'] == new_description, "Description should be updated"

    logger.info(f"✅ Updated project {project_id}: {result['name']}")
    return True


def test_synccursor_delete_with_returning():
    """Test that SyncCursor can DELETE with RETURNING."""
    logger.info("\n=== Test 4: DELETE with RETURNING ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    # Create a project to delete
    project_name = f"delete_test_{int(__import__('time').time() * 1000) % 1000000}"
    cursor.execute(
        "INSERT INTO projects (name, path) VALUES (%s, %s) RETURNING id",
        (project_name, f"/delete/{project_name}")
    )
    project_id = cursor.fetchone()['id']

    # Delete with RETURNING
    cursor.execute(
        "DELETE FROM projects WHERE id = %s RETURNING id, name",
        (project_id,)
    )

    result = cursor.fetchone()
    assert result is not None, "DELETE with RETURNING should return a result"
    assert result['id'] == project_id, "Deleted project ID should match"

    logger.info(f"✅ Deleted project {project_id}: {result['name']}")
    return True


def test_synccursor_with_parameters():
    """Test that SyncCursor properly handles parameterized queries."""
    logger.info("\n=== Test 5: Parameterized Queries ===")

    db = PostgresDatabase(dbname="athena_test")
    cursor = db.get_cursor()

    # Insert with parameters
    project_name = f"param_test_{int(__import__('time').time() * 1000) % 1000000}"
    cursor.execute(
        "INSERT INTO projects (name, path, description) VALUES (%s, %s, %s) RETURNING id",
        (project_name, f"/param/{project_name}", "Test with params")
    )

    project_id = cursor.fetchone()['id']
    logger.info(f"✅ Inserted with parameters: ID={project_id}")

    # Select with parameters
    cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    result = cursor.fetchone()
    assert result is not None, "Should find project by ID"

    logger.info(f"✅ Retrieved project using parameter: {result['name']}")
    return True


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("SyncCursor Bridge - Full Validation Test")
    logger.info("=" * 70)

    tests = [
        ("Project Creation", test_synccursor_with_project_creation),
        ("SELECT", test_synccursor_select),
        ("UPDATE with RETURNING", test_synccursor_update_with_returning),
        ("DELETE with RETURNING", test_synccursor_delete_with_returning),
        ("Parameterized Queries", test_synccursor_with_parameters),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                logger.error(f"❌ {test_name} returned False")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} failed: {e}")
            import traceback
            traceback.print_exc()

    logger.info("\n" + "=" * 70)
    logger.info(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        logger.info("✅ ALL TESTS PASSED - SyncCursor bridge is fixed!")
    else:
        logger.info(f"❌ {failed} test(s) failed")
    logger.info("=" * 70)
