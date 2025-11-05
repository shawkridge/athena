"""Unit tests for action cycles layer."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from athena.ai_coordination.action_cycles import (
    ActionCycle,
    CycleStatus,
    LessonLearned,
    PlanAssumption,
)
from athena.ai_coordination.action_cycle_store import ActionCycleStore
from athena.core.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def store(temp_db):
    """Create an ActionCycleStore with temporary database."""
    return ActionCycleStore(temp_db)


@pytest.fixture
def goal_id():
    """Generate a unique goal ID."""
    return str(uuid4())


class TestActionCycleStore:
    """Tests for ActionCycleStore."""

    def test_create_cycle_basic(self, store, goal_id):
        """Test creating a basic action cycle."""
        cycle_id = store.create_cycle(
            goal_description="Implement user authentication",
            plan_description="Add JWT token validation to API",
            session_id="test_session",
            goal_id=goal_id,
            goal_priority=8.0,
        )

        assert cycle_id is not None
        assert isinstance(cycle_id, int)

        # Verify retrieval
        cycle = store.get_cycle(cycle_id)
        assert cycle is not None
        assert cycle.goal_id == goal_id
        assert cycle.goal_description == "Implement user authentication"
        assert cycle.status == CycleStatus.PLANNING

    def test_create_cycle_with_assumptions(self, store):
        """Test creating cycle with plan assumptions."""
        assumptions = [
            PlanAssumption(assumption="User table exists", confidence=0.9, critical=True),
            PlanAssumption(assumption="JWT library available", confidence=0.95, critical=True),
        ]

        cycle_id = store.create_cycle(
            goal_description="Auth system",
            plan_description="JWT-based auth",
            session_id="test_session",
            plan_assumptions=assumptions,
        )

        cycle = store.get_cycle(cycle_id)
        assert len(cycle.plan_assumptions) == 2
        assert cycle.plan_assumptions[0].critical is True

    def test_start_execution(self, store):
        """Test starting execution phase."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        assert store.get_cycle(cycle_id).status == CycleStatus.PLANNING

        store.start_execution(cycle_id)

        cycle = store.get_cycle(cycle_id)
        assert cycle.status == CycleStatus.EXECUTING
        assert cycle.started_execution_at is not None

    def test_record_execution_result_success(self, store):
        """Test recording a successful execution."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        exec_id = store.record_execution_result(
            cycle_id=cycle_id,
            attempt_number=1,
            outcome="success",
            execution_id=str(uuid4()),
            duration_seconds=300,
            code_changes_count=5,
        )

        assert exec_id is not None

        cycle = store.get_cycle(cycle_id)
        assert cycle.total_executions == 1
        assert cycle.successful_executions == 1
        assert cycle.success_rate == 1.0
        assert len(cycle.executions) == 1

    def test_record_execution_result_failure(self, store):
        """Test recording a failed execution."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(
            cycle_id=cycle_id,
            attempt_number=1,
            outcome="failure",
            errors_encountered=2,
        )

        cycle = store.get_cycle(cycle_id)
        assert cycle.total_executions == 1
        assert cycle.failed_executions == 1
        assert cycle.success_rate == 0.0

    def test_record_multiple_executions(self, store):
        """Test recording multiple execution attempts."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)

        # First attempt: failure
        store.record_execution_result(cycle_id, 1, "failure")

        # Second attempt: partial
        store.record_execution_result(cycle_id, 2, "partial")

        # Third attempt: success
        store.record_execution_result(cycle_id, 3, "success")

        cycle = store.get_cycle(cycle_id)
        assert cycle.total_executions == 3
        assert cycle.successful_executions == 1
        assert cycle.failed_executions == 1
        assert cycle.partial_executions == 1
        assert cycle.success_rate == pytest.approx(1 / 3, abs=0.01)

    def test_should_replan_on_failure(self, store):
        """Test replanning detection on failure."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "failure")

        assert store.should_replan(cycle_id) is True

    def test_should_replan_on_low_success_rate(self, store):
        """Test replanning detection on low success rate."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)

        # Record 3 attempts with only 1 success
        store.record_execution_result(cycle_id, 1, "failure")
        store.record_execution_result(cycle_id, 2, "failure")
        store.record_execution_result(cycle_id, 3, "success")

        assert store.should_replan(cycle_id) is True

    def test_should_replan_on_consecutive_failures(self, store):
        """Test replanning detection on consecutive failures."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "failure")
        store.record_execution_result(cycle_id, 2, "failure")

        assert store.should_replan(cycle_id) is True

    def test_trigger_replan(self, store):
        """Test triggering replanning."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Original plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "failure")

        # Trigger replan
        store.trigger_replan(
            cycle_id,
            new_plan_description="Revised plan based on failure",
            reason="Initial approach had concurrency issues",
        )

        cycle = store.get_cycle(cycle_id)
        assert cycle.plan_description == "Revised plan based on failure"
        assert cycle.replanning_count == 1
        assert len(cycle.plan_adjustments) == 1
        assert "concurrency" in cycle.plan_adjustments[0].reason

    def test_add_lesson(self, store):
        """Test adding lessons learned."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "success")

        store.add_lesson(
            cycle_id,
            lesson="Always validate input before processing",
            source_attempt=1,
            confidence=0.95,
            applies_to=["security", "error handling"],
            can_create_procedure=True,
        )

        cycle = store.get_cycle(cycle_id)
        assert len(cycle.lessons_learned) == 1
        assert cycle.lessons_learned[0].lesson == "Always validate input before processing"
        assert cycle.lessons_learned[0].can_create_procedure is True

    def test_complete_cycle_success(self, store):
        """Test completing a successful cycle."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "success")
        store.add_lesson(cycle_id, "Lesson 1", 1)

        store.complete_cycle(cycle_id, final_status="completed")

        cycle = store.get_cycle(cycle_id)
        assert cycle.status == CycleStatus.COMPLETED
        assert cycle.completed_at is not None
        assert cycle.reason_abandoned is None

    def test_abandon_cycle(self, store):
        """Test abandoning a cycle."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
            max_attempts=2,
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "failure")
        store.record_execution_result(cycle_id, 2, "failure")

        store.abandon_cycle(cycle_id, reason="Max attempts exceeded")

        cycle = store.get_cycle(cycle_id)
        assert cycle.status == CycleStatus.ABANDONED
        assert "Max attempts" in cycle.reason_abandoned

    def test_get_active_cycle(self, store, goal_id):
        """Test retrieving active cycle for goal."""
        cycle_id = store.create_cycle(
            goal_description="Goal 1",
            plan_description="Plan",
            session_id="test_session",
            goal_id=goal_id,
        )

        active = store.get_active_cycle(goal_id)
        assert active is not None
        assert active.id == cycle_id

        # Complete the cycle
        store.complete_cycle(cycle_id)

        # Should not be active anymore
        active = store.get_active_cycle(goal_id)
        assert active is None

    def test_get_cycles_for_goal(self, store, goal_id):
        """Test retrieving all cycles for a goal."""
        # Create multiple cycles
        id1 = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan 1",
            session_id="session1",
            goal_id=goal_id,
        )
        id2 = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan 2",
            session_id="session2",
            goal_id=goal_id,
        )

        cycles = store.get_cycles_for_goal(goal_id)
        assert len(cycles) == 2
        assert all(c.goal_id == goal_id for c in cycles)

    def test_get_execution_summary(self, store):
        """Test getting execution summary."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        store.start_execution(cycle_id)
        store.record_execution_result(cycle_id, 1, "failure")
        store.record_execution_result(cycle_id, 2, "success")
        store.trigger_replan(cycle_id, "New plan")
        store.add_lesson(cycle_id, "Lesson", 2)

        summary = store.get_execution_summary(cycle_id)

        assert summary["total_attempts"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["replanning_count"] == 1
        assert summary["lessons_learned_count"] == 1

    def test_get_active_cycles(self, store):
        """Test retrieving all active cycles in session."""
        session_id = "test_session"

        # Create cycles
        id1 = store.create_cycle("Goal 1", "Plan", session_id)
        id2 = store.create_cycle("Goal 2", "Plan", session_id)
        id3 = store.create_cycle("Goal 3", "Plan", session_id)

        # Complete one
        store.complete_cycle(id1)

        active = store.get_active_cycles(session_id)
        assert len(active) == 2
        assert all(c.status in [CycleStatus.PLANNING, CycleStatus.EXECUTING, CycleStatus.LEARNING] for c in active)

    def test_mark_consolidated(self, store):
        """Test marking cycle as consolidated."""
        cycle_id = store.create_cycle(
            goal_description="Goal",
            plan_description="Plan",
            session_id="test_session",
        )

        cycle = store.get_cycle(cycle_id)
        assert cycle.consolidation_status == "unconsolidated"

        store.mark_consolidated(cycle_id)

        cycle = store.get_cycle(cycle_id)
        assert cycle.consolidation_status == "consolidated"
        assert cycle.consolidated_at is not None

    def test_get_unconsolidated_cycles(self, store):
        """Test retrieving unconsolidated cycles."""
        # Create cycles
        id1 = store.create_cycle("Goal 1", "Plan", "session")
        id2 = store.create_cycle("Goal 2", "Plan", "session")
        id3 = store.create_cycle("Goal 3", "Plan", "session")

        # Consolidate some
        store.mark_consolidated(id1)

        unconsolidated = store.get_unconsolidated_cycles()
        assert len(unconsolidated) == 2

    def test_full_cycle_orchestration(self, store):
        """Test full cycle from creation to completion."""
        cycle_id = store.create_cycle(
            goal_description="Implement feature X",
            plan_description="Step-by-step implementation",
            session_id="test_session",
            goal_priority=7.0,
            plan_assumptions=[
                PlanAssumption(assumption="Dependency available", confidence=0.9, critical=True),
            ],
        )

        # Start execution
        store.start_execution(cycle_id)
        cycle = store.get_cycle(cycle_id)
        assert cycle.status == CycleStatus.EXECUTING

        # First attempt: failure
        store.record_execution_result(
            cycle_id, 1, "failure",
            errors_encountered=1,
            lessons_from_attempt=["Check dependency availability first"],
        )

        # Should trigger replan
        assert store.should_replan(cycle_id) is True

        # Replan
        store.trigger_replan(
            cycle_id,
            "Updated plan with dependency check",
            reason="Initial approach failed due to missing dependency",
        )

        # Second attempt: success
        store.record_execution_result(
            cycle_id, 2, "success",
            duration_seconds=600,
            code_changes_count=15,
        )

        # Add lessons
        store.add_lesson(
            cycle_id,
            "Always verify dependencies upfront",
            source_attempt=2,
            confidence=0.95,
            applies_to=["planning", "integration"],
        )

        # Complete cycle
        store.complete_cycle(cycle_id)

        # Verify final state
        cycle = store.get_cycle(cycle_id)
        assert cycle.status == CycleStatus.COMPLETED
        assert cycle.total_executions == 2
        assert cycle.successful_executions == 1
        assert cycle.failed_executions == 1
        assert cycle.replanning_count == 1
        assert len(cycle.lessons_learned) == 1
        assert cycle.success_rate == pytest.approx(0.5, abs=0.01)
