"""Unit Tests for TodoWrite ↔ Athena Planning Integration

Tests the mapping layer and sync functionality between TodoWrite and Athena.
"""

import pytest
from datetime import datetime
from typing import Any, Dict

# Import the integration module
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from athena.integration.todowrite_sync import (
    convert_todo_to_plan,
    convert_plan_to_todo,
    convert_todo_list_to_plans,
    convert_plan_list_to_todos,
    detect_sync_conflict,
    resolve_sync_conflict,
    get_sync_metadata,
    get_sync_statistics,
    TodoWriteStatus,
    AthenaTaskStatus,
    PriorityLevel,
    _map_todowrite_to_athena_status,
    _map_athena_to_todowrite_status,
    _determine_phase_from_todo_status,
    _extract_priority_hint,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_todo():
    """Sample TodoWrite todo item."""
    return {
        "content": "Implement feature X",
        "status": "pending",
        "activeForm": "Implementing feature X",
    }


@pytest.fixture
def sample_todo_in_progress():
    """Sample TodoWrite todo in progress."""
    return {
        "content": "Fix critical bug",
        "status": "in_progress",
        "activeForm": "Fixing critical bug",
    }


@pytest.fixture
def sample_todo_completed():
    """Sample TodoWrite todo completed."""
    return {
        "content": "Write documentation",
        "status": "completed",
        "activeForm": "Wrote documentation",
    }


@pytest.fixture
def sample_plan():
    """Sample Athena plan."""
    return {
        "goal": "Implement feature X",
        "description": "Detailed implementation plan",
        "status": "pending",
        "phase": 1,
        "priority": 5,
        "project_id": 1,
        "created_at": datetime.now().isoformat(),
        "source": "manual",
        "tags": ["feature"],
        "steps": [],
        "assumptions": [],
        "risks": [],
    }


@pytest.fixture
def sample_plan_from_todo():
    """Sample Athena plan created from TodoWrite."""
    return {
        "goal": "Implement feature Y",
        "description": "Implementing feature Y",
        "status": "in_progress",
        "phase": 3,
        "priority": 5,
        "project_id": 1,
        "created_at": datetime.now().isoformat(),
        "source": "todowrite",
        "tags": ["todowrite"],
        "steps": [],
        "assumptions": [],
        "risks": [],
        "original_todo": {
            "content": "Implement feature Y",
            "status": "in_progress",
            "activeForm": "Implementing feature Y",
        },
    }


# ============================================================================
# BASIC CONVERSION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_convert_todo_to_plan_pending(sample_todo):
    """Test converting a pending todo to a plan."""
    plan = await convert_todo_to_plan(sample_todo, project_id=1)

    assert plan["goal"] == "Implement feature X"
    assert plan["status"] == "pending"
    assert plan["phase"] == 1
    assert plan["project_id"] == 1
    assert plan["source"] == "todowrite"
    assert "todowrite" in plan["tags"]


@pytest.mark.asyncio
async def test_convert_todo_to_plan_in_progress(sample_todo_in_progress):
    """Test converting an in_progress todo to a plan."""
    plan = await convert_todo_to_plan(sample_todo_in_progress, project_id=1)

    assert plan["goal"] == "Fix critical bug"
    assert plan["status"] == "in_progress"
    assert plan["phase"] == 3  # Execution phase
    assert plan["priority"] == 9  # CRITICAL detected


@pytest.mark.asyncio
async def test_convert_todo_to_plan_completed(sample_todo_completed):
    """Test converting a completed todo to a plan."""
    plan = await convert_todo_to_plan(sample_todo_completed, project_id=1)

    assert plan["goal"] == "Write documentation"
    assert plan["status"] == "completed"
    assert plan["phase"] == 5  # Complete phase


@pytest.mark.asyncio
async def test_convert_todo_to_plan_invalid_input():
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError):
        await convert_todo_to_plan({}, project_id=1)

    with pytest.raises(ValueError):
        await convert_todo_to_plan({"status": "pending"}, project_id=1)  # Missing content


def test_convert_plan_to_todo(sample_plan):
    """Test converting a plan to a todo."""
    todo = convert_plan_to_todo(sample_plan)

    assert todo["content"] == "Implement feature X"
    assert todo["status"] == "pending"
    assert todo["activeForm"] == "Detailed implementation plan"


def test_convert_plan_to_todo_from_todowrite(sample_plan_from_todo):
    """Test converting a plan created from TodoWrite back to todo."""
    todo = convert_plan_to_todo(sample_plan_from_todo)

    # Should reconstruct original todo with updated status
    assert todo["content"] == "Implement feature Y"
    assert todo["status"] == "in_progress"
    assert todo["activeForm"] == "Implementing feature Y"


def test_convert_plan_to_todo_invalid_input():
    """Test that invalid input raises ValueError."""
    with pytest.raises(ValueError):
        convert_plan_to_todo({})

    with pytest.raises(ValueError):
        convert_plan_to_todo({"status": "pending"})  # Missing goal


# ============================================================================
# BATCH CONVERSION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_convert_todo_list_to_plans():
    """Test converting a list of todos to plans."""
    todos = [
        {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
        {"content": "Task 3", "status": "completed", "activeForm": "Completed task 3"},
    ]

    plans = await convert_todo_list_to_plans(todos, project_id=1)

    assert len(plans) == 3
    assert plans[0]["status"] == "pending"
    assert plans[1]["status"] == "in_progress"
    assert plans[2]["status"] == "completed"


def test_convert_plan_list_to_todos(sample_plan):
    """Test converting a list of plans to todos."""
    plans = [
        sample_plan,
        {**sample_plan, "goal": "Task 2", "status": "in_progress"},
        {**sample_plan, "goal": "Task 3", "status": "completed"},
    ]

    todos = convert_plan_list_to_todos(plans)

    assert len(todos) == 3
    assert todos[0]["status"] == "pending"
    assert todos[1]["status"] == "in_progress"
    assert todos[2]["status"] == "completed"


# ============================================================================
# STATUS MAPPING TESTS
# ============================================================================

def test_map_todowrite_to_athena_status():
    """Test TodoWrite to Athena status mapping."""
    assert _map_todowrite_to_athena_status("pending") == "pending"
    assert _map_todowrite_to_athena_status("in_progress") == "in_progress"
    assert _map_todowrite_to_athena_status("completed") == "completed"


def test_map_athena_to_todowrite_status():
    """Test Athena to TodoWrite status mapping."""
    # Simple mappings
    assert _map_athena_to_todowrite_status("pending") == "pending"
    assert _map_athena_to_todowrite_status("in_progress") == "in_progress"
    assert _map_athena_to_todowrite_status("completed") == "completed"

    # Athena-specific states map to in_progress
    assert _map_athena_to_todowrite_status("planning") == "in_progress"
    assert _map_athena_to_todowrite_status("ready") == "in_progress"
    assert _map_athena_to_todowrite_status("blocked") == "in_progress"

    # Terminal states map to completed
    assert _map_athena_to_todowrite_status("failed") == "completed"
    assert _map_athena_to_todowrite_status("cancelled") == "completed"


def test_status_mapping_round_trip():
    """Test that status mapping is consistent in round trips."""
    # pending → pending
    todo_status = "pending"
    athena = _map_todowrite_to_athena_status(todo_status)
    back = _map_athena_to_todowrite_status(athena)
    assert back == todo_status

    # in_progress → in_progress
    todo_status = "in_progress"
    athena = _map_todowrite_to_athena_status(todo_status)
    back = _map_athena_to_todowrite_status(athena)
    assert back == todo_status

    # completed → completed
    todo_status = "completed"
    athena = _map_todowrite_to_athena_status(todo_status)
    back = _map_athena_to_todowrite_status(athena)
    assert back == todo_status


# ============================================================================
# PHASE DETERMINATION TESTS
# ============================================================================

def test_determine_phase_from_todo_status():
    """Test phase determination from TodoWrite status."""
    assert _determine_phase_from_todo_status("pending") == 1  # Planning
    assert _determine_phase_from_todo_status("in_progress") == 3  # Execution
    assert _determine_phase_from_todo_status("completed") == 5  # Complete


# ============================================================================
# PRIORITY EXTRACTION TESTS
# ============================================================================

def test_extract_priority_from_content():
    """Test priority extraction from todo content."""
    # Critical priority
    assert _extract_priority_hint("CRITICAL: Fix authentication bug") == 9
    assert _extract_priority_hint("URGENT: Deploy hotfix") == 9
    assert _extract_priority_hint("BLOCKING: Database connection") == 9

    # High priority
    assert _extract_priority_hint("HIGH PRIORITY: Refactor API") == 7

    # Important
    assert _extract_priority_hint("IMPORTANT: Update dependencies") == 6

    # Low priority
    assert _extract_priority_hint("LOW PRIORITY: Cleanup code") == 2

    # Default
    assert _extract_priority_hint("Normal task") == 5


# ============================================================================
# SYNC CONFLICT DETECTION TESTS
# ============================================================================

def test_detect_sync_conflict_status_mismatch():
    """Test conflict detection when status differs."""
    todo = {"content": "Task X", "status": "pending", "activeForm": "Doing task"}
    plan = {"goal": "Task X", "status": "in_progress"}

    has_conflict, description = detect_sync_conflict(todo, plan)
    assert has_conflict
    assert "Status mismatch" in description


def test_detect_sync_conflict_content_mismatch():
    """Test conflict detection when content differs."""
    todo = {"content": "Task X", "status": "pending", "activeForm": "Doing task"}
    plan = {"goal": "Task Y", "status": "pending"}

    has_conflict, description = detect_sync_conflict(todo, plan)
    assert has_conflict
    assert "Content mismatch" in description


def test_detect_sync_conflict_no_conflict():
    """Test that no conflict is detected when statuses match."""
    todo = {"content": "Task X", "status": "pending", "activeForm": "Doing task"}
    plan = {"goal": "Task X", "status": "pending"}

    has_conflict, description = detect_sync_conflict(todo, plan)
    assert not has_conflict
    assert description is None


def test_detect_sync_conflict_with_mapping():
    """Test conflict detection with status mapping."""
    # planning in Athena maps to in_progress in TodoWrite
    todo = {"content": "Task X", "status": "in_progress", "activeForm": "Doing task"}
    plan = {"goal": "Task X", "status": "planning"}

    has_conflict, description = detect_sync_conflict(todo, plan)
    # No conflict because planning maps to in_progress
    assert not has_conflict


# ============================================================================
# SYNC CONFLICT RESOLUTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_resolve_sync_conflict_todo_wins(sample_todo, sample_plan):
    """Test resolving conflict by preferring todo."""
    result = await resolve_sync_conflict(sample_todo, sample_plan, prefer="todo")

    assert result["resolution"] == "todo_wins"
    assert result["todo"]["content"] == "Implement feature X"
    assert result["plan"]["goal"] == "Implement feature X"


@pytest.mark.asyncio
async def test_resolve_sync_conflict_plan_wins(sample_todo, sample_plan):
    """Test resolving conflict by preferring plan."""
    result = await resolve_sync_conflict(sample_todo, sample_plan, prefer="plan")

    assert result["resolution"] == "plan_wins"
    assert result["plan"]["goal"] == "Implement feature X"


# ============================================================================
# SYNC METADATA TESTS
# ============================================================================

def test_sync_metadata_mapping():
    """Test sync metadata tracking."""
    metadata = get_sync_metadata()

    # Map todo to plan
    metadata.map_todo_to_plan("todo_1", "plan_1")
    assert metadata.todo_to_plan_mapping["todo_1"] == "plan_1"

    # Map plan to todo
    metadata.map_plan_to_todo("plan_2", "todo_2")
    assert metadata.plan_to_todo_mapping["plan_2"] == "todo_2"


def test_sync_metadata_pending():
    """Test pending sync tracking."""
    metadata = get_sync_metadata()

    metadata.mark_pending_sync("item_1")
    assert "item_1" in metadata.pending_sync

    # Marking as mapped removes from pending
    metadata.map_todo_to_plan("item_1", "plan_1")
    assert "item_1" not in metadata.pending_sync


@pytest.mark.asyncio
async def test_get_sync_statistics():
    """Test getting sync statistics."""
    stats = await get_sync_statistics()

    assert "last_sync" in stats
    assert "todo_to_plan_mappings" in stats
    assert "plan_to_todo_mappings" in stats
    assert "pending_sync_count" in stats
    assert "total_tracked_items" in stats


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_convert_todo_with_special_characters(sample_todo):
    """Test converting todo with special characters."""
    sample_todo["content"] = "Task with special chars: @#$%^&*()"
    plan = await convert_todo_to_plan(sample_todo, project_id=1)

    assert "@#$%^&*()" in plan["goal"]


@pytest.mark.asyncio
async def test_convert_todo_with_very_long_content(sample_todo):
    """Test converting todo with very long content."""
    long_content = "A" * 10000
    sample_todo["content"] = long_content
    plan = await convert_todo_to_plan(sample_todo, project_id=1)

    assert plan["goal"] == long_content


@pytest.mark.asyncio
async def test_convert_todo_without_active_form(sample_todo):
    """Test converting todo without activeForm field."""
    del sample_todo["activeForm"]
    plan = await convert_todo_to_plan(sample_todo, project_id=1)

    assert plan["description"] == sample_todo["content"]


def test_convert_plan_with_missing_status():
    """Test converting plan with missing status field."""
    plan = {"goal": "Task X"}  # No status field
    todo = convert_plan_to_todo(plan)

    assert todo["status"] == "pending"  # Default


@pytest.mark.asyncio
async def test_roundtrip_conversion():
    """Test that converting todo → plan → todo preserves content."""
    original_todo = {
        "content": "Implement feature Z",
        "status": "pending",
        "activeForm": "Implementing feature Z",
    }

    # Convert to plan
    plan = await convert_todo_to_plan(original_todo, project_id=1)

    # Convert back to todo
    recovered_todo = convert_plan_to_todo(plan)

    # Should recover original
    assert recovered_todo["content"] == original_todo["content"]
    assert recovered_todo["status"] == original_todo["status"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_sync_workflow():
    """Test a complete sync workflow."""
    # Start with a TodoWrite item
    original_todo = {
        "content": "Full sync test",
        "status": "pending",
        "activeForm": "Testing full sync",
    }

    # 1. Convert todo to plan
    plan = await convert_todo_to_plan(original_todo, project_id=1)
    assert plan["source"] == "todowrite"

    # 2. Record mapping
    metadata = get_sync_metadata()
    metadata.map_todo_to_plan("todo_123", "plan_123")
    assert metadata.todo_to_plan_mapping["todo_123"] == "plan_123"

    # 3. Simulate plan status change
    plan["status"] = "in_progress"

    # 4. Check for conflicts
    updated_todo = {**original_todo, "status": "pending"}
    has_conflict, _ = detect_sync_conflict(updated_todo, plan)
    assert has_conflict

    # 5. Resolve by preferring plan
    resolved = await resolve_sync_conflict(updated_todo, plan, prefer="plan")
    assert resolved["todo"]["status"] == "in_progress"

    # 6. Convert resolved plan back to todo
    final_todo = convert_plan_to_todo(resolved["plan"])
    assert final_todo["status"] == "in_progress"
