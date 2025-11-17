"""Integration Tests for TodoWrite ↔ Database Sync

Tests the full workflow of syncing todos to the database and back,
including conflict detection and resolution.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from athena.integration.todowrite_sync import convert_todo_to_plan, convert_plan_to_todo
from athena.integration.sync_operations import (
    sync_todo_to_database,
    sync_todo_status_change,
    get_active_plans,
    get_completed_plans,
    get_sync_summary,
    export_plans_as_todos,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_todo():
    """Sample TodoWrite todo."""
    return {
        "id": "todo_1",
        "content": "Implement feature X",
        "status": "pending",
        "activeForm": "Implementing feature X",
    }


@pytest.fixture
def sample_todo_in_progress():
    """Sample TodoWrite todo in progress."""
    return {
        "id": "todo_2",
        "content": "CRITICAL: Fix authentication bug",
        "status": "in_progress",
        "activeForm": "Fixing authentication bug",
    }


@pytest.fixture
def sample_todo_completed():
    """Sample completed TodoWrite todo."""
    return {
        "id": "todo_3",
        "content": "Write documentation",
        "status": "completed",
        "activeForm": "Wrote documentation",
    }


# ============================================================================
# DATABASE SYNC TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sync_todo_to_database(sample_todo):
    """Test syncing a todo to the database."""
    success, plan_id = await sync_todo_to_database(sample_todo, project_id=1)

    assert success
    assert plan_id is not None
    assert isinstance(plan_id, str)
    assert plan_id.startswith("plan_")


@pytest.mark.asyncio
async def test_sync_todo_with_priority_detection(sample_todo_in_progress):
    """Test that priority is auto-detected from content."""
    success, plan_id = await sync_todo_to_database(sample_todo_in_progress, project_id=1)

    assert success

    # Plan should have high priority due to CRITICAL keyword
    plan = await convert_todo_to_plan(sample_todo_in_progress, project_id=1)
    assert plan["priority"] == 9


@pytest.mark.asyncio
async def test_sync_status_change(sample_todo):
    """Test syncing status changes."""
    # First sync the todo
    success, plan_id = await sync_todo_to_database(sample_todo, project_id=1)
    assert success

    # Change status
    success, message = await sync_todo_status_change(
        sample_todo["id"],
        "in_progress",
        project_id=1,
    )

    assert success
    assert "in_progress" in message.lower() or plan_id in message


@pytest.mark.asyncio
async def test_get_active_plans():
    """Test retrieving active plans."""
    # Sync a few todos
    todos = [
        {
            "id": "todo_active_1",
            "content": "Active task 1",
            "status": "in_progress",
            "activeForm": "Working on task 1",
        },
        {
            "id": "todo_active_2",
            "content": "Active task 2",
            "status": "pending",
            "activeForm": "Todo task 2",
        },
        {
            "id": "todo_completed",
            "content": "Completed task",
            "status": "completed",
            "activeForm": "Finished task",
        },
    ]

    for todo in todos:
        await sync_todo_to_database(todo, project_id=1)

    # Get active plans
    active = await get_active_plans(project_id=1, limit=10)

    # Should include pending and in_progress, not completed
    statuses = {p["status"] for p in active}
    assert "in_progress" in statuses or "planning" in statuses or "ready" in statuses
    assert "completed" not in statuses


@pytest.mark.asyncio
async def test_get_completed_plans(sample_todo_completed):
    """Test retrieving completed plans."""
    # Sync a completed todo
    success, plan_id = await sync_todo_to_database(sample_todo_completed, project_id=1)
    assert success

    # Get completed plans
    completed = await get_completed_plans(project_id=1)

    # Should have at least one completed plan
    assert len(completed) >= 1
    assert all(p["status"] == "completed" for p in completed)


@pytest.mark.asyncio
async def test_get_sync_summary():
    """Test getting sync summary."""
    summary = await get_sync_summary(project_id=1)

    assert "statistics" in summary
    assert "pending_syncs" in summary
    assert "conflicts" in summary
    assert summary["pending_syncs"] >= 0
    assert summary["conflicts"] >= 0


@pytest.mark.asyncio
async def test_export_plans_as_todos():
    """Test exporting plans back as todos."""
    # Sync some todos first
    todos = [
        {
            "id": "todo_export_1",
            "content": "Task to export 1",
            "status": "pending",
            "activeForm": "Doing export task 1",
        },
        {
            "id": "todo_export_2",
            "content": "Task to export 2",
            "status": "in_progress",
            "activeForm": "Doing export task 2",
        },
    ]

    for todo in todos:
        await sync_todo_to_database(todo, project_id=1)

    # Export as todos
    exported = await export_plans_as_todos(project_id=1)

    assert len(exported) > 0
    assert all("content" in t and "status" in t for t in exported)


@pytest.mark.asyncio
async def test_roundtrip_sync():
    """Test full roundtrip: todo → database → todo."""
    original_todo = {
        "id": "todo_roundtrip",
        "content": "Roundtrip test task",
        "status": "pending",
        "activeForm": "Testing roundtrip",
    }

    # 1. Sync todo to database
    success, plan_id = await sync_todo_to_database(original_todo, project_id=1)
    assert success

    # 2. Change status in database
    success, _ = await sync_todo_status_change(
        original_todo["id"],
        "in_progress",
        project_id=1,
    )
    assert success

    # 3. Get active plans (should include our todo)
    active = await get_active_plans(project_id=1, limit=100)
    plan_ids = [p["plan_id"] for p in active]

    # Our plan should be in active plans
    assert plan_id in plan_ids

    # 4. Export back to todos
    exported = await export_plans_as_todos(project_id=1)
    matching = [t for t in exported if "Roundtrip test task" in t.get("content", "")]

    # Should find our todo
    assert len(matching) > 0


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@pytest.mark.asyncio
async def test_batch_sync():
    """Test syncing multiple todos at once."""
    todos = [
        {
            "id": f"todo_batch_{i}",
            "content": f"Batch task {i}",
            "status": ["pending", "in_progress", "completed"][i % 3],
            "activeForm": f"Doing batch task {i}",
        }
        for i in range(5)
    ]

    results = []
    for todo in todos:
        success, plan_id = await sync_todo_to_database(todo, project_id=1)
        results.append((success, plan_id))

    # All should succeed
    assert all(success for success, _ in results)
    assert len(results) == 5


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_sync_todo_with_special_characters(sample_todo):
    """Test syncing todo with special characters."""
    sample_todo["content"] = "Task with special chars: @#$%^&*()"
    success, plan_id = await sync_todo_to_database(sample_todo, project_id=1)

    assert success
    assert plan_id is not None


@pytest.mark.asyncio
async def test_sync_todo_with_very_long_content(sample_todo):
    """Test syncing todo with very long content."""
    sample_todo["content"] = "A" * 10000
    success, plan_id = await sync_todo_to_database(sample_todo, project_id=1)

    assert success
    assert plan_id is not None


@pytest.mark.asyncio
async def test_sync_todo_without_id(sample_todo):
    """Test syncing todo without explicit ID."""
    del sample_todo["id"]
    success, plan_id = await sync_todo_to_database(sample_todo, project_id=1)

    assert success
    assert plan_id is not None


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sync_performance_100_todos():
    """Test performance of syncing 100 todos."""
    import time

    todos = [
        {
            "id": f"perf_todo_{i}",
            "content": f"Performance test todo {i}",
            "status": ["pending", "in_progress"][i % 2],
            "activeForm": f"Perf task {i}",
        }
        for i in range(100)
    ]

    start = time.time()

    results = []
    for todo in todos:
        success, plan_id = await sync_todo_to_database(todo, project_id=1)
        results.append((success, plan_id))

    elapsed = time.time() - start

    assert all(success for success, _ in results)
    assert elapsed < 10.0

    per_item = elapsed / 100
    assert per_item < 0.1


# ============================================================================
# ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_sync_status_change_nonexistent_todo():
    """Test status change for non-existent todo."""
    success, message = await sync_todo_status_change(
        "nonexistent_todo",
        "in_progress",
        project_id=1,
    )

    assert not success
    assert "not found" in message.lower() or "error" in message.lower()
