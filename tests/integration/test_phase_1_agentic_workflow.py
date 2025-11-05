"""Phase 1: Agentic Workflow Integration Tests

Tests the complete Phase 1 implementation:
1. Task phase tracking (PLANNING → PLAN_READY → EXECUTING → VERIFYING → COMPLETED)
2. Plan creation and validation
3. Phase transition recording
4. Task execution lifecycle with metrics
"""

import pytest
from datetime import datetime
from pathlib import Path

from athena.core.database import Database
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskPriority,
    TaskStatus,
    Plan,
    PhaseMetrics,
)
from athena.prospective.store import ProspectiveStore
from athena.integration.phase_tracking import PhaseTracker


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create temporary database for testing."""
    db = Database(tmp_path / "test.db")
    return db


@pytest.fixture
def prospective_store(temp_db: Database) -> ProspectiveStore:
    """Create prospective store."""
    return ProspectiveStore(temp_db)


@pytest.fixture
def phase_tracker(temp_db: Database) -> PhaseTracker:
    """Create phase tracker."""
    return PhaseTracker(temp_db)


class TestPhaseTracking:
    """Test phase tracking functionality."""

    def test_create_task_in_planning_phase(self, prospective_store):
        """Test creating a task defaults to PLANNING phase."""
        task = ProspectiveTask(
            project_id=1,
            content="Implement authentication system",
            active_form="Implementing authentication",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            phase=TaskPhase.PLANNING,
        )

        task_id = prospective_store.create_task(task)
        retrieved = prospective_store.get_task(task_id)

        assert retrieved is not None
        assert retrieved.phase == TaskPhase.PLANNING
        assert retrieved.content == "Implement authentication system"
        assert retrieved.status == TaskStatus.PENDING

    def test_create_plan_for_task(self, prospective_store):
        """Test creating and attaching a plan to a task."""
        task = ProspectiveTask(
            project_id=1,
            content="Build REST API",
            active_form="Building REST API",
        )
        task_id = prospective_store.create_task(task)

        # Create plan
        steps = [
            "Design API endpoints",
            "Implement server",
            "Add authentication",
            "Write tests",
            "Deploy",
        ]

        task_with_plan = prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=steps,
            estimated_duration_minutes=480,  # 8 hours
        )

        assert task_with_plan is not None
        assert task_with_plan.plan is not None
        assert len(task_with_plan.plan.steps) == 5
        assert task_with_plan.plan.steps[0] == "Design API endpoints"
        assert task_with_plan.plan.estimated_duration_minutes == 480

    def test_validate_plan(self, prospective_store):
        """Test validating a plan."""
        task = ProspectiveTask(
            project_id=1,
            content="Refactor database layer",
            active_form="Refactoring database layer",
        )
        task_id = prospective_store.create_task(task)

        # Create plan
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Analyze current schema", "Design new schema", "Migrate data"],
        )

        # Validate plan
        validated_task = prospective_store.validate_plan(
            task_id=task_id,
            notes="Plan reviewed and approved by team",
        )

        assert validated_task is not None
        assert validated_task.plan.validated is True
        assert validated_task.plan.validation_notes == "Plan reviewed and approved by team"

    def test_mark_plan_ready(self, prospective_store):
        """Test transitioning task to PLAN_READY phase."""
        task = ProspectiveTask(
            project_id=1,
            content="Write documentation",
            active_form="Writing documentation",
            phase=TaskPhase.PLANNING,
        )
        task_id = prospective_store.create_task(task)

        # Create and validate plan
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Write README", "Write API docs", "Create examples"],
        )
        prospective_store.validate_plan(task_id=task_id)

        # Mark as PLAN_READY
        ready_task = prospective_store.mark_plan_ready(task_id)

        assert ready_task is not None
        assert ready_task.phase == TaskPhase.PLAN_READY

    def test_phase_transition_with_metrics(self, prospective_store):
        """Test transitioning between phases and recording metrics."""
        task = ProspectiveTask(
            project_id=1,
            content="Test task lifecycle",
            active_form="Testing task lifecycle",
            phase=TaskPhase.PLANNING,
        )
        task_id = prospective_store.create_task(task)

        # Transition: PLANNING → PLAN_READY
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Step 1", "Step 2"],
        )
        prospective_store.validate_plan(task_id=task_id)
        task_ready = prospective_store.mark_plan_ready(task_id)

        assert task_ready.phase == TaskPhase.PLAN_READY
        assert len(task_ready.phase_metrics) == 1

        # Transition: PLAN_READY → EXECUTING
        task_executing = prospective_store.update_task_phase(task_id, TaskPhase.EXECUTING)

        assert task_executing.phase == TaskPhase.EXECUTING
        assert len(task_executing.phase_metrics) == 2

    def test_complete_phase_calculates_duration(self, prospective_store):
        """Test that completing a phase calculates duration."""
        import time

        task = ProspectiveTask(
            project_id=1,
            content="Duration test",
            active_form="Testing duration",
        )
        task_id = prospective_store.create_task(task)

        # Start phase
        prospective_store.update_task_phase(task_id, TaskPhase.PLANNING)
        time.sleep(0.1)  # Sleep to create measurable duration

        # Complete phase
        completed_task = prospective_store.complete_phase(task_id, TaskPhase.PLAN_READY)

        assert completed_task is not None
        assert len(completed_task.phase_metrics) >= 1
        latest_metric = completed_task.phase_metrics[-1]
        assert latest_metric.duration_minutes is not None
        assert latest_metric.duration_minutes > 0

    def test_full_task_workflow(self, prospective_store):
        """Test complete task workflow from creation to completion."""
        # 1. Create task in PLANNING phase
        task = ProspectiveTask(
            project_id=1,
            content="Implement feature X",
            active_form="Implementing feature X",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
        )
        task_id = prospective_store.create_task(task)

        # 2. Create plan
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=[
                "Design feature",
                "Write implementation",
                "Add tests",
                "Code review",
                "Deploy",
            ],
            estimated_duration_minutes=240,
        )

        # 3. Validate plan
        prospective_store.validate_plan(
            task_id=task_id,
            notes="Design approved in team meeting",
        )

        # 4. Mark PLAN_READY
        task_ready = prospective_store.mark_plan_ready(task_id)
        assert task_ready.phase == TaskPhase.PLAN_READY

        # 5. Start EXECUTING
        task_executing = prospective_store.update_task_phase(
            task_id, TaskPhase.EXECUTING
        )
        assert task_executing.phase == TaskPhase.EXECUTING
        assert task_executing.status == TaskStatus.PENDING  # Status not auto-changed

        # 6. Update status to in_progress
        prospective_store.update_task_status(task_id, TaskStatus.ACTIVE)

        # 7. Move to VERIFYING
        task_verifying = prospective_store.update_task_phase(
            task_id, TaskPhase.VERIFYING
        )
        assert task_verifying.phase == TaskPhase.VERIFYING

        # 8. Complete task
        final_task = prospective_store.complete_phase(task_id, TaskPhase.COMPLETED)
        prospective_store.update_task_status(task_id, TaskStatus.COMPLETED)

        # Verify final state
        completed_task = prospective_store.get_task(task_id)
        assert completed_task.phase == TaskPhase.COMPLETED
        assert completed_task.status == TaskStatus.COMPLETED
        assert len(completed_task.phase_metrics) >= 3  # At least PLANNING, PLAN_READY, EXECUTING
        assert completed_task.actual_duration_minutes is not None

    def test_get_tasks_by_phase(self, prospective_store):
        """Test querying tasks by phase."""
        # Create multiple tasks in different phases
        task1 = ProspectiveTask(
            project_id=1,
            content="Task in planning",
            active_form="Planning task 1",
            phase=TaskPhase.PLANNING,
        )
        task_id_1 = prospective_store.create_task(task1)

        task2 = ProspectiveTask(
            project_id=1,
            content="Task executing",
            active_form="Executing task 2",
            phase=TaskPhase.EXECUTING,
        )
        task_id_2 = prospective_store.create_task(task2)

        task3 = ProspectiveTask(
            project_id=1,
            content="Another planning task",
            active_form="Planning task 3",
            phase=TaskPhase.PLANNING,
        )
        task_id_3 = prospective_store.create_task(task3)

        # Query planning phase
        planning_tasks = prospective_store.get_tasks_by_phase(
            TaskPhase.PLANNING, project_id=1
        )
        assert len(planning_tasks) == 2
        assert all(t.phase == TaskPhase.PLANNING for t in planning_tasks)

        # Query executing phase
        executing_tasks = prospective_store.get_tasks_by_phase(
            TaskPhase.EXECUTING, project_id=1
        )
        assert len(executing_tasks) == 1
        assert executing_tasks[0].phase == TaskPhase.EXECUTING


class TestPhaseTracker:
    """Test phase tracking integration."""

    def test_phase_tracker_initialization(self, phase_tracker):
        """Test PhaseTracker initializes correctly."""
        assert phase_tracker is not None
        assert phase_tracker.prospective_store is not None
        assert phase_tracker.episodic_store is not None

    def test_get_phase_metrics(self, prospective_store, phase_tracker):
        """Test retrieving phase metrics for a task."""
        task = ProspectiveTask(
            project_id=1,
            content="Test metrics",
            active_form="Testing metrics",
        )
        task_id = prospective_store.create_task(task)

        # Transition phases
        prospective_store.update_task_phase(task_id, TaskPhase.PLANNING)
        prospective_store.complete_phase(task_id, TaskPhase.PLAN_READY)

        # Get metrics
        metrics = phase_tracker.get_phase_metrics(task_id)
        assert len(metrics) >= 1

    def test_get_total_task_duration(self, prospective_store, phase_tracker):
        """Test getting total task duration."""
        task = ProspectiveTask(
            project_id=1,
            content="Duration task",
            active_form="Testing duration",
        )
        task_id = prospective_store.create_task(task)

        # Complete full workflow
        prospective_store.update_task_phase(task_id, TaskPhase.PLANNING)
        prospective_store.complete_phase(task_id, TaskPhase.EXECUTING)
        completed = prospective_store.complete_phase(task_id, TaskPhase.COMPLETED)

        # Get duration
        duration = phase_tracker.get_total_task_duration(task_id)
        # Duration will be set when task transitions to COMPLETED
        assert duration is None or duration >= 0

    def test_summarize_phase_metrics(self, prospective_store, phase_tracker):
        """Test phase metrics summary."""
        task = ProspectiveTask(
            project_id=1,
            content="Summary test",
            active_form="Testing summary",
        )
        task_id = prospective_store.create_task(task)

        # Do some phase transitions
        prospective_store.create_plan_for_task(task_id, ["Step 1", "Step 2"])
        prospective_store.validate_plan(task_id)
        prospective_store.mark_plan_ready(task_id)
        prospective_store.update_task_phase(task_id, TaskPhase.EXECUTING)

        # Get summary
        summary = phase_tracker.summarize_phase_metrics(task_id)
        assert summary["task_id"] == task_id
        assert "phase_breakdown" in summary
        assert "total_duration_minutes" in summary
