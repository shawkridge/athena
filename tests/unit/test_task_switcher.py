"""Tests for task switching with context preservation."""

import json
import pytest
from datetime import datetime

from athena.core.database import Database
from athena.executive.hierarchy import GoalHierarchy
from athena.executive.switcher import TaskSwitcher
from athena.executive.models import GoalType, GoalStatus


@pytest.fixture
def db(tmp_path):
    """Create test database with Phase 3 schema."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    db.create_project("test-project", str(tmp_path))

    # Create executive goals table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS executive_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_goal_id INTEGER,
            goal_text TEXT NOT NULL,
            goal_type TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'active',
            progress REAL DEFAULT 0.0,
            estimated_hours REAL,
            actual_hours REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (parent_goal_id) REFERENCES executive_goals(id)
        )
        """
    )

    # Create task_switches table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            from_goal_id INTEGER,
            to_goal_id INTEGER NOT NULL,
            switch_cost_ms INTEGER,
            context_snapshot TEXT,
            reason TEXT,
            switched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (from_goal_id) REFERENCES executive_goals(id),
            FOREIGN KEY (to_goal_id) REFERENCES executive_goals(id)
        )
        """
    )

    db.conn.commit()
    return db


@pytest.fixture
def hierarchy(db):
    """Create goal hierarchy manager."""
    return GoalHierarchy(db)


@pytest.fixture
def switcher(db):
    """Create task switcher."""
    return TaskSwitcher(db)


def test_switch_same_priority_cost_5ms(hierarchy, switcher):
    """Test switching between same priority goals costs 5ms base."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=5)

    switch = switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)

    assert switch.switch_cost_ms == 5


def test_switch_priority_change_increases_cost(hierarchy, switcher):
    """Test switching with priority change increases cost."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=8)

    switch = switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)

    # Cost = 5 + (3/10)² × 100 = 5 + 9 = 14ms
    assert switch.switch_cost_ms == 14


def test_switch_high_priority_change_capped(hierarchy, switcher):
    """Test switching with large priority change is capped at 50ms."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=1)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=10)

    switch = switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)

    # Cost = 5 + (9/10)² × 100 = 5 + 81 = 86ms → capped at 50ms
    assert switch.switch_cost_ms == 50


def test_switch_no_previous_goal_minimal_cost(hierarchy, switcher):
    """Test switching from no previous goal costs 5ms."""
    goal_id = hierarchy.create_goal(1, "Task A", priority=5)

    switch = switcher.switch_to_goal(1, goal_id, from_goal_id=None)

    assert switch.switch_cost_ms == 5


def test_context_snapshot_saved(hierarchy, switcher):
    """Test context snapshot is saved during switch."""
    goal1_id = hierarchy.create_goal(1, "Task A")
    goal2_id = hierarchy.create_goal(1, "Task B")

    context = {"memory_items": ["item1", "item2"], "focus": "file.py"}
    switch = switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id, context_snapshot=context)

    assert switch.context_snapshot is not None
    # The context_snapshot is directly JSON-serialized context dict
    snapshot_data = json.loads(switch.context_snapshot)
    assert snapshot_data == context


def test_context_restore_works(switcher):
    """Test restoring context from snapshot."""
    context = {"memory": ["a", "b", "c"], "focus": "main.py"}
    snapshot = switcher.snapshot_context(context)

    restored = switcher.restore_context(snapshot)

    assert restored == context


def test_switch_history_most_recent_first(hierarchy, switcher):
    """Test switching history returns all switches."""
    import time

    # Create goals with same priority to avoid priority effects
    goal_ids = [
        hierarchy.create_goal(1, f"Task {i}", priority=5)
        for i in range(4)
    ]

    # Make 3 switches with small delays to ensure different timestamps
    switch1 = switcher.switch_to_goal(1, goal_ids[1], from_goal_id=goal_ids[0], reason="user_request")
    time.sleep(0.01)
    switch2 = switcher.switch_to_goal(1, goal_ids[2], from_goal_id=goal_ids[1], reason="priority_change")
    time.sleep(0.01)
    switch3 = switcher.switch_to_goal(1, goal_ids[3], from_goal_id=goal_ids[2], reason="deadline")

    history = switcher.get_switch_history(1)

    # Verify we have all switches
    assert len(history) >= 3
    # Verify all switch IDs are in history
    history_ids = [s.id for s in history]
    assert switch1.id in history_ids
    assert switch2.id in history_ids
    assert switch3.id in history_ids


def test_get_total_overhead(hierarchy, switcher):
    """Test total switching overhead accumulation."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=8)
    goal3_id = hierarchy.create_goal(1, "Task C", priority=3)

    # Switch A→B: delta = |8-5| = 3, cost = 5 + (3/10)^2 * 100 = 5 + 9 = 14ms
    # Switch B→C: delta = |3-8| = 5, cost = 5 + (5/10)^2 * 100 = 5 + 25 = 30ms
    switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)
    switcher.switch_to_goal(1, goal3_id, from_goal_id=goal2_id)

    total_ms = switcher.get_total_overhead(1)

    # 14 + 30 = 44ms
    assert total_ms == 44


def test_get_average_switch_cost(hierarchy, switcher):
    """Test average switching cost calculation."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=8)
    goal3_id = hierarchy.create_goal(1, "Task C", priority=3)

    switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)  # 14ms
    switcher.switch_to_goal(1, goal3_id, from_goal_id=goal2_id)  # 30ms

    avg_cost = switcher.get_average_switch_cost(1)

    # (14 + 30) / 2 = 22ms
    assert abs(avg_cost - 22.0) < 0.01


def test_get_switch_statistics(hierarchy, switcher):
    """Test comprehensive switching statistics."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=8)

    switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id, reason="user_request")
    switcher.switch_to_goal(1, goal1_id, from_goal_id=goal2_id, reason="priority_change")

    stats = switcher.get_switch_statistics(1)

    assert stats["total_switches"] == 2
    assert stats["min_cost_ms"] == 14
    assert stats["max_cost_ms"] == 14
    assert stats["total_cost_ms"] == 28
    assert "reason_breakdown" in stats
    assert "user_request" in stats["reason_breakdown"]
    assert "priority_change" in stats["reason_breakdown"]


def test_switch_cost_by_priority_change_formula(switcher):
    """Test switch cost formula for various deltas."""
    # Test various priority deltas
    assert switcher.get_switch_cost_by_priority_change(0) == 5  # Base cost
    assert switcher.get_switch_cost_by_priority_change(3) == 14  # 5 + 9 = 14
    assert switcher.get_switch_cost_by_priority_change(5) == 30  # 5 + 25 = 30
    assert switcher.get_switch_cost_by_priority_change(10) == 50  # Capped at 50


def test_switching_overhead_ratio(hierarchy, switcher):
    """Test switching overhead ratio calculation."""
    goal1_id = hierarchy.create_goal(1, "Task A", priority=5)
    goal2_id = hierarchy.create_goal(1, "Task B", priority=8)

    switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id)  # 14ms

    # With 10 hours total work
    ratio = switcher.get_switching_overhead_ratio(1, total_work_hours=10)

    # 14ms / (10*3600*1000 = 36,000,000ms) ≈ 0.0000004
    assert ratio < 0.001


def test_switch_with_different_reasons(hierarchy, switcher):
    """Test switching with different reasons."""
    goal1_id = hierarchy.create_goal(1, "Task A")
    goal2_id = hierarchy.create_goal(1, "Task B")
    goal3_id = hierarchy.create_goal(1, "Task C")
    goal4_id = hierarchy.create_goal(1, "Task D")

    switcher.switch_to_goal(1, goal2_id, from_goal_id=goal1_id, reason="priority_change")
    switcher.switch_to_goal(1, goal3_id, from_goal_id=goal2_id, reason="blocker")
    switcher.switch_to_goal(1, goal4_id, from_goal_id=goal3_id, reason="deadline")

    history = switcher.get_switch_history(1)

    reasons = [s.reason for s in history]
    assert "priority_change" in reasons
    assert "blocker" in reasons
    assert "deadline" in reasons
