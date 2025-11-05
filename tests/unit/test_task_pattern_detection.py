"""Tests for task pattern detection (Gap 1: Task->Consolidation sync)."""

import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority
from athena.prospective.store import ProspectiveStore


@pytest.fixture
def prospective_store(tmp_path):
    """Create a prospective store for testing."""
    db = Database(tmp_path / "test.db")
    store = ProspectiveStore(db)
    store._ensure_schema()
    return store


def test_find_recent_completed_tasks(prospective_store):
    """Test finding recently completed tasks."""
    project_id = 1

    # Create some completed tasks
    now = datetime.now()
    for i in range(3):
        task = ProspectiveTask(
            project_id=project_id,
            content=f"Test task {i}",
            active_form=f"Testing task {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Create an old completed task (outside time window)
    old_task = ProspectiveTask(
        project_id=project_id,
        content="Old task",
        active_form="Testing old task",
        status=TaskStatus.COMPLETED,
        created_at=now - timedelta(days=10),
        completed_at=now - timedelta(days=10),
    )
    prospective_store.create_task(old_task)

    # Find recent tasks
    recent = prospective_store.find_recent_completed_tasks(
        project_id=project_id,
        hours_back=24,
    )

    # Should find 3 recent tasks, not the old one
    assert len(recent) == 3
    assert all(task.content.startswith("Test task") for task in recent)


def test_detect_task_patterns(prospective_store):
    """Test detecting patterns in completed tasks."""
    project_id = 1

    # Create repeated tasks with similar names (first 3 words must match for pattern grouping)
    now = datetime.now()
    pattern_names = [
        "Fix authentication bug in JWT module",
        "Fix authentication bug in OAuth handler",
        "Fix authentication bug in session manager",
        "Refactor database migration schema",
        "Refactor database migration script",
    ]

    for name in pattern_names:
        task = ProspectiveTask(
            project_id=project_id,
            content=name,
            active_form=f"Working on {name}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Detect patterns
    patterns = prospective_store.detect_task_patterns(
        project_id=project_id,
        min_occurrences=2,
        time_window_hours=24,
    )

    # Should find patterns
    assert len(patterns) > 0

    # Check that we have the Fix authentication pattern
    pattern_contents = [p["content"] for p in patterns]
    fix_auth_pattern = [p for p in patterns if "Fix authentication" in p["content"]]
    assert len(fix_auth_pattern) > 0
    assert fix_auth_pattern[0]["count"] == 3

    # Check that Refactor pattern is also detected
    refactor_pattern = [p for p in patterns if "Refactor database migration" in p["content"]]
    assert len(refactor_pattern) > 0
    assert refactor_pattern[0]["count"] == 2


def test_detect_task_patterns_min_occurrences(prospective_store):
    """Test that patterns respect min_occurrences threshold."""
    project_id = 1

    # Create tasks with different frequencies
    now = datetime.now()
    for i in range(5):
        # High frequency pattern (5 times)
        task = ProspectiveTask(
            project_id=project_id,
            content=f"Fix bug in module {i}",
            active_form=f"Fixing bug in module {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Create low frequency task (1 time, below threshold)
    low_freq_task = ProspectiveTask(
        project_id=project_id,
        content="Unique one-off task",
        active_form="Doing unique task",
        status=TaskStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=1),
    )
    prospective_store.create_task(low_freq_task)

    # Detect patterns with min_occurrences=2
    patterns = prospective_store.detect_task_patterns(
        project_id=project_id,
        min_occurrences=2,
        time_window_hours=24,
    )

    # Should find the "Fix bug" pattern but not the "Unique" one
    assert len(patterns) >= 1
    pattern_contents = [p["content"] for p in patterns]
    assert any("Fix bug" in p for p in pattern_contents)
    assert not any("Unique" in p for p in pattern_contents)


def test_detect_task_patterns_empty(prospective_store):
    """Test detecting patterns when no patterns exist."""
    project_id = 1

    # Create all unique tasks
    now = datetime.now()
    for i in range(3):
        task = ProspectiveTask(
            project_id=project_id,
            content=f"Unique task {i} with special content",
            active_form=f"Working on unique task {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Detect patterns with min_occurrences=2
    patterns = prospective_store.detect_task_patterns(
        project_id=project_id,
        min_occurrences=2,
        time_window_hours=24,
    )

    # Should find no patterns since all tasks are unique
    assert len(patterns) == 0


def test_find_similar_tasks(prospective_store):
    """Test finding similar tasks."""
    project_id = 1

    # Create a reference task
    now = datetime.now()
    ref_task = ProspectiveTask(
        project_id=project_id,
        content="Fix authentication bug",
        active_form="Fixing auth bug",
        status=TaskStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=1),
    )
    ref_id = prospective_store.create_task(ref_task)

    # Create similar completed tasks
    for i in range(3):
        task = ProspectiveTask(
            project_id=project_id,
            content=f"Fix authentication bug in module {i}",
            active_form=f"Fixing auth bug in module {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Get reference task
    ref_task = prospective_store.get_task(ref_id)

    # Find similar tasks
    similar = prospective_store.find_similar_tasks(
        ref_task,
        project_id=project_id,
        limit=10,
    )

    # Should find the 3 similar completed tasks
    assert len(similar) == 3
    assert all("Fix authentication bug" in t.content for t in similar)


def test_pattern_detection_respects_project_isolation(prospective_store):
    """Test that pattern detection respects project isolation."""
    # Create tasks in project 1
    now = datetime.now()
    for i in range(3):
        task = ProspectiveTask(
            project_id=1,
            content=f"Fix bug in project 1, iteration {i}",
            active_form=f"Fixing bug in project 1, iteration {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Create different tasks in project 2
    for i in range(2):
        task = ProspectiveTask(
            project_id=2,
            content=f"Implement feature in project 2, version {i}",
            active_form=f"Implementing feature in project 2, version {i}",
            status=TaskStatus.COMPLETED,
            created_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
        )
        prospective_store.create_task(task)

    # Detect patterns for project 1
    patterns_p1 = prospective_store.detect_task_patterns(
        project_id=1,
        min_occurrences=2,
        time_window_hours=24,
    )

    # Detect patterns for project 2
    patterns_p2 = prospective_store.detect_task_patterns(
        project_id=2,
        min_occurrences=2,
        time_window_hours=24,
    )

    # Project 1 should have "Fix bug" pattern
    p1_contents = [p["content"] for p in patterns_p1]
    assert any("Fix bug" in p for p in p1_contents)

    # Project 2 should have "Implement feature" pattern
    p2_contents = [p["content"] for p in patterns_p2]
    assert any("Implement feature" in p for p in p2_contents)

    # Project 1 patterns should NOT contain project 2 content
    assert not any("Implement feature" in p for p in p1_contents)
    # Project 2 patterns should NOT contain project 1 content
    assert not any("Fix bug" in p for p in p2_contents)
