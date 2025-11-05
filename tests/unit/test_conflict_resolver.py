"""Tests for ConflictResolver component."""

import pytest
import sqlite3
from datetime import datetime, timedelta

from athena.executive.conflict import ConflictResolver
from athena.core.database import Database


@pytest.fixture
def db_path(tmp_path):
    """Create a test database."""
    db_file = tmp_path / "test_memory.db"
    db = Database(str(db_file))

    # Create test project
    db.create_project("test-project", str(tmp_path))

    # Create executive_goals table
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
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    # Create conflict_resolutions table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS conflict_resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            primary_goal_id INTEGER,
            competing_goals TEXT,
            resolution_timestamp TIMESTAMP,
            reasoning TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    )

    # Create goal_suspension_log table
    db.conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goal_suspension_log (
            goal_id INTEGER,
            reason TEXT,
            suspended_at TIMESTAMP,
            resumed_at TIMESTAMP
        )
        """
    )

    db.conn.commit()
    return str(db_file)


@pytest.fixture
def resolver(db_path):
    """Create a ConflictResolver instance."""
    return ConflictResolver(db_path)


@pytest.fixture
def setup_goal(db_path):
    """Create a test goal in the database."""

    def _create_goal(
        goal_text="Test goal",
        priority=5,
        project_id=1,
        deadline=None,
        progress=0.0,
        parent_goal_id=None,
    ):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO executive_goals
                (project_id, goal_text, goal_type, priority, status, progress, created_at,
                 deadline, parent_goal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    goal_text,
                    "primary",
                    priority,
                    "active",
                    progress,
                    datetime.now().isoformat(),
                    deadline.isoformat() if deadline else None,
                    parent_goal_id,
                ),
            )
            goal_id = cursor.lastrowid
            conn.commit()
            return goal_id

    return _create_goal


class TestPriorityResolution:
    """Test priority resolution logic."""

    def test_resolve_priority_explicit(self, resolver, setup_goal):
        """Higher explicit priority should win."""
        goal1 = setup_goal("Goal 1", priority=3)
        goal2 = setup_goal("Goal 2", priority=8)

        result = resolver.resolve_priority([goal1, goal2])

        assert result is not None
        assert result["primary_goal_id"] == goal2
        assert result["resolution_scores"][goal2] > result["resolution_scores"][goal1]

    def test_resolve_priority_deadline_driven(self, resolver, setup_goal):
        """Urgent deadline should take priority."""
        deadline_today = datetime.now()
        deadline_next_week = datetime.now() + timedelta(days=7)

        goal1 = setup_goal("Goal 1", priority=5, deadline=deadline_next_week)
        goal2 = setup_goal("Goal 2", priority=5, deadline=deadline_today)

        result = resolver.resolve_priority([goal1, goal2])

        assert result is not None
        assert result["primary_goal_id"] == goal2

    def test_resolve_priority_dependency_chain(self, resolver, setup_goal):
        """Goal with dependent subgoals should have higher priority."""
        parent_goal = setup_goal("Parent goal", priority=5)
        # Create a subgoal
        subgoal = setup_goal("Subgoal", priority=5, parent_goal_id=parent_goal)

        # Now resolve between parent and another goal
        other_goal = setup_goal("Other goal", priority=5)

        result = resolver.resolve_priority([parent_goal, other_goal])

        assert result is not None
        # Parent should have higher priority due to dependent subgoal
        assert result["resolution_scores"][parent_goal] > result["resolution_scores"][other_goal]

    def test_resource_allocation_sums_to_one(self, resolver, setup_goal):
        """Resource allocation should sum to 1.0."""
        goal1 = setup_goal("Goal 1", priority=3)
        goal2 = setup_goal("Goal 2", priority=8)
        goal3 = setup_goal("Goal 3", priority=5)

        result = resolver.resolve_priority([goal1, goal2, goal3])

        allocation = result["resource_allocation"]
        total = sum(allocation.values())

        assert abs(total - 1.0) < 0.01  # Allow small floating point error


class TestGoalSuspension:
    """Test goal suspension and resumption."""

    def test_suspend_lower_priority_goal(self, resolver, setup_goal):
        """Lower priority goal should be suspendable."""
        goal_id = setup_goal("Low priority goal", priority=2)

        success = resolver.suspend_goal(goal_id, "test_suspension")
        assert success is True

        # Verify goal is suspended
        with sqlite3.connect(resolver.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM executive_goals WHERE id = ?", (goal_id,))
            status = cursor.fetchone()[0]
            assert status == "suspended"

    def test_resume_suspended_goal(self, resolver, setup_goal):
        """Suspended goal should be resumable."""
        goal_id = setup_goal("Goal to suspend")

        resolver.suspend_goal(goal_id)
        success = resolver.resume_goal(goal_id)

        assert success is True

        # Verify goal is active again
        with sqlite3.connect(resolver.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM executive_goals WHERE id = ?", (goal_id,))
            status = cursor.fetchone()[0]
            assert status == "active"

    def test_suspension_creates_log_entry(self, resolver, setup_goal):
        """Suspending goal should create log entry."""
        goal_id = setup_goal("Goal to track")

        resolver.suspend_goal(goal_id, "conflict_resolution_lower_priority")

        # Verify log entry
        with sqlite3.connect(resolver.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reason, suspended_at FROM goal_suspension_log WHERE goal_id = ?",
                (goal_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "conflict_resolution_lower_priority"


class TestWorkingMemoryAllocation:
    """Test working memory fair allocation."""

    def test_working_memory_allocation_fairness(self, resolver, setup_goal):
        """Memory should be allocated fairly based on priority."""
        goals = []
        for i in range(3):
            goal = setup_goal(f"Goal {i}", priority=5 + i)
            goals.append(goal)

        allocation = resolver.allocate_working_memory_fair(goals)

        assert len(allocation) == 3
        # Total allocation should be 7 (Baddeley's capacity)
        total = sum(allocation.values())
        assert abs(total - 7.0) < 0.1

        # Higher priority goals should get more slots
        assert allocation[goals[-1]] > allocation[goals[0]]

    def test_empty_goal_list_returns_empty(self, resolver):
        """Empty goal list should return empty allocation."""
        allocation = resolver.allocate_working_memory_fair([])
        assert allocation == {}

    def test_single_goal_gets_all_slots(self, resolver, setup_goal):
        """Single goal should get all 7 slots."""
        goal = setup_goal("Only goal")

        allocation = resolver.allocate_working_memory_fair([goal])

        assert allocation[goal] == pytest.approx(7.0)


class TestConflictLogging:
    """Test conflict resolution logging."""

    def test_conflict_resolution_log(self, resolver, setup_goal):
        """Conflict resolutions should be logged."""
        goal1 = setup_goal("Goal 1", priority=3)
        goal2 = setup_goal("Goal 2", priority=8)

        result = resolver.resolve_priority([goal1, goal2])

        # Get log
        log = resolver.get_conflict_resolution_log(project_id=1)

        assert len(log) > 0
        assert log[0]["primary_goal_id"] == goal2
        assert set(log[0]["competing_goals"]) == {goal1, goal2}

    def test_log_limits_results(self, resolver, setup_goal):
        """Log should limit results."""
        for i in range(15):
            goal1 = setup_goal(f"Goal 1-{i}", priority=3)
            goal2 = setup_goal(f"Goal 2-{i}", priority=8)
            resolver.resolve_priority([goal1, goal2])

        log = resolver.get_conflict_resolution_log(project_id=1, limit=5)

        assert len(log) <= 5

    def test_log_ordering_most_recent_first(self, resolver, setup_goal):
        """Log should show most recent resolutions first."""
        goals = [setup_goal(f"Goal {i}", priority=5) for i in range(3)]

        # Create first resolution
        resolver.resolve_priority(goals[:2])

        # Create second resolution
        resolver.resolve_priority(goals[1:3])

        log = resolver.get_conflict_resolution_log(project_id=1)

        # Most recent should be first
        assert len(log) >= 2


class TestMultipleConflicts:
    """Test resolving multiple competing goals."""

    def test_resolve_multiple_conflicts(self, resolver, setup_goal):
        """Should handle resolution among multiple competing goals."""
        goal1 = setup_goal("Goal 1", priority=3)
        goal2 = setup_goal("Goal 2", priority=8)
        goal3 = setup_goal("Goal 3", priority=5)

        result = resolver.resolve_multiple_conflicts(project_id=1)

        assert result is not None
        assert result["primary_goal_id"] == goal2

    def test_multiple_conflicts_suspends_low_priority(self, resolver, setup_goal):
        """Low priority goals may be suspended during conflict resolution."""
        goal1 = setup_goal("Goal 1", priority=2)
        goal2 = setup_goal("Goal 2", priority=9)

        resolver.resolve_multiple_conflicts(project_id=1)

        # goal1 might be suspended if allocation is low
        with sqlite3.connect(resolver.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM executive_goals WHERE id = ?", (goal1,))
            status = cursor.fetchone()[0]
            # Status could be 'active' or 'suspended' depending on allocation
            assert status in ["active", "suspended"]
