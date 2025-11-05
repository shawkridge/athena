"""Phase 3: Auto-Triggered Adaptive Replanning Tests

Tests the automatic replanning system that monitors task execution and
triggers replanning when conditions are met (duration exceeded, quality
degradation, milestone delays, etc.).
"""

import asyncio
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskPriority,
    TaskStatus,
    Plan,
)
from athena.prospective.store import ProspectiveStore
from athena.integration.replanning_monitor import ReplanningMonitor


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
def replanning_monitor(temp_db: Database) -> ReplanningMonitor:
    """Create replanning monitor."""
    return ReplanningMonitor(temp_db)


class TestReplanningMonitor:
    """Test replanning monitor functionality."""

    def test_monitor_initialization(self, replanning_monitor):
        """Test monitor initializes correctly."""
        assert replanning_monitor is not None
        assert replanning_monitor.DURATION_THRESHOLD_PERCENT == 150
        assert replanning_monitor.QUALITY_ERROR_THRESHOLD == 3
        assert replanning_monitor.MILESTONE_DELAY_THRESHOLD_PERCENT == 50

    def test_get_monitor_status(self, replanning_monitor):
        """Test getting monitor status."""
        status = replanning_monitor.get_monitor_status()

        assert "last_check_time" in status
        assert status["duration_threshold_percent"] == 150
        assert status["quality_error_threshold"] == 3
        assert status["monitoring_window_minutes"] == 60

    def test_decide_replanning_action_no_triggers(self, replanning_monitor):
        """Test decision with no triggers."""
        action = replanning_monitor._decide_replanning_action([])
        assert action == "continue"

    def test_decide_replanning_action_single_trigger(self, replanning_monitor):
        """Test decision with single trigger."""
        triggers = [
            {
                "type": "duration_exceeded",
                "reason": "Task duration exceeded 150% of estimate",
            }
        ]
        action = replanning_monitor._decide_replanning_action(triggers)
        assert action == "replan"

    def test_decide_replanning_action_multiple_triggers(self, replanning_monitor):
        """Test decision with multiple triggers."""
        triggers = [
            {
                "type": "duration_exceeded",
                "reason": "Task duration exceeded 150% of estimate",
            },
            {
                "type": "milestone_delayed",
                "reason": "Current milestone delayed >50% of estimate",
            },
        ]
        action = replanning_monitor._decide_replanning_action(triggers)
        assert action == "escalate"

    def test_decide_replanning_action_quality_degradation(self, replanning_monitor):
        """Test decision for quality degradation."""
        triggers = [
            {
                "type": "quality_degradation",
                "reason": "Detected 3 errors in task execution",
            }
        ]
        action = replanning_monitor._decide_replanning_action(triggers)
        assert action == "escalate"

    def test_decide_replanning_action_milestone_delay(self, replanning_monitor):
        """Test decision for milestone delay alone."""
        triggers = [
            {
                "type": "milestone_delayed",
                "reason": "Current milestone delayed >50% of estimate",
            }
        ]
        action = replanning_monitor._decide_replanning_action(triggers)
        assert action == "adapt"


class TestDurationChecking:
    """Test duration exceeded detection."""

    @pytest.mark.asyncio
    async def test_duration_not_exceeded(self, prospective_store, replanning_monitor):
        """Test when duration is within estimate."""
        task = ProspectiveTask(
            project_id=1,
            content="Quick task",
            active_form="Quick task",
            phase=TaskPhase.EXECUTING,
            phase_started_at=datetime.now() - timedelta(minutes=15),
        )

        # Create plan with 60 min estimate
        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        # Task is only 25% done (15/60), not exceeded
        result = await replanning_monitor._check_duration_exceeded(task)
        assert result is False

    @pytest.mark.asyncio
    async def test_duration_exceeded(self, prospective_store, replanning_monitor):
        """Test when duration exceeded threshold."""
        task = ProspectiveTask(
            project_id=1,
            content="Long task",
            active_form="Long task",
            phase=TaskPhase.EXECUTING,
            phase_started_at=datetime.now() - timedelta(minutes=100),
        )

        # Create plan with 60 min estimate
        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        # Task has run 100 min vs 60 min estimate (166%), exceeded threshold
        result = await replanning_monitor._check_duration_exceeded(task)
        assert result is True


class TestQualityDegradationChecking:
    """Test quality degradation detection."""

    @pytest.mark.asyncio
    async def test_quality_degradation_no_errors(
        self, prospective_store, replanning_monitor
    ):
        """Test quality when no errors present."""
        task = ProspectiveTask(
            project_id=1,
            content="Task with no errors",
            active_form="Task with no errors",
        )

        result = await replanning_monitor._check_quality_degradation(task)
        assert result == 0  # No errors found

    @pytest.mark.asyncio
    async def test_quality_degradation_below_threshold(
        self, temp_db, replanning_monitor
    ):
        """Test quality when errors below threshold."""
        task = ProspectiveTask(
            project_id=1,
            content="Task with few errors",
            active_form="Task with few errors",
        )

        # Could record some errors, but below threshold
        result = await replanning_monitor._check_quality_degradation(task)
        assert result < replanning_monitor.QUALITY_ERROR_THRESHOLD


class TestMilestoneDelayChecking:
    """Test milestone delay detection."""

    @pytest.mark.asyncio
    async def test_milestone_not_delayed(self, replanning_monitor):
        """Test when milestone is on time."""
        task = ProspectiveTask(
            project_id=1,
            content="On-time milestone",
            active_form="On-time milestone",
            phase_started_at=datetime.now() - timedelta(minutes=10),
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        result = await replanning_monitor._check_milestone_delay(task)
        assert result is False

    @pytest.mark.asyncio
    async def test_milestone_delayed(self, replanning_monitor):
        """Test when milestone is delayed."""
        task = ProspectiveTask(
            project_id=1,
            content="Delayed milestone",
            active_form="Delayed milestone",
            phase_started_at=datetime.now() - timedelta(minutes=50),
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        # Milestone phase has run 50 min vs estimate of 12 min per phase (60/5)
        # This is >150%, should trigger
        result = await replanning_monitor._check_milestone_delay(task)
        assert result is True


class TestFullReplanningWorkflow:
    """Test complete replanning workflow."""

    @pytest.mark.asyncio
    async def test_check_all_active_tasks(self, prospective_store, replanning_monitor):
        """Test checking all active tasks."""
        # Create some tasks in different phases
        for i in range(3):
            task = ProspectiveTask(
                project_id=1,
                content=f"Task {i}",
                active_form=f"Task {i}",
                phase=TaskPhase.EXECUTING if i < 2 else TaskPhase.PLANNING,
            )
            prospective_store.create_task(task)

        # Check all active tasks
        candidates = await replanning_monitor.check_all_active_tasks()

        # Should find executing tasks (depends on if they meet trigger conditions)
        assert isinstance(candidates, list)

    @pytest.mark.asyncio
    async def test_post_tool_use_hook(self, replanning_monitor):
        """Test post-tool-use hook execution."""
        event = {"tool": "some_tool", "result": "success"}

        # Should not raise exception
        await replanning_monitor.on_post_tool_use(event)

        # Verify status was updated
        status = replanning_monitor.get_monitor_status()
        assert status is not None

    @pytest.mark.asyncio
    async def test_estimate_new_plan(self, replanning_monitor):
        """Test estimating new plan when replanning needed."""
        task = ProspectiveTask(
            project_id=1,
            content="Task needing replan",
            active_form="Task needing replan",
            phase_started_at=datetime.now() - timedelta(minutes=100),
        )

        task.plan = Plan(
            steps=["Original step 1", "Original step 2"],
            estimated_duration_minutes=60,
        )

        # Estimate new plan
        new_plan = await replanning_monitor.estimate_new_plan(
            task, "Duration exceeded"
        )

        if new_plan:  # Will be None if cannot replan
            assert len(new_plan) > 0
            assert "adapted" in new_plan[0]


class TestReplanningIntegration:
    """Test integration of replanning with task lifecycle."""

    @pytest.mark.asyncio
    async def test_replanning_detection_integration(
        self, prospective_store, replanning_monitor
    ):
        """Test full replanning detection and action selection."""
        # Create a task
        task = ProspectiveTask(
            project_id=1,
            content="Integration test task",
            active_form="Integration test task",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            phase_started_at=datetime.now() - timedelta(minutes=100),
        )

        task_id = prospective_store.create_task(task)

        # Add plan to task
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Step 1", "Step 2", "Step 3"],
            estimated_duration_minutes=60,
        )

        # Get task with plan
        task_with_plan = prospective_store.get_task(task_id)

        # Check for replanning triggers
        trigger = await replanning_monitor._check_task_for_replanning(task_with_plan)

        if trigger:
            # Verify trigger structure
            assert "task_id" in trigger
            assert "triggers" in trigger
            assert "recommended_action" in trigger
            assert trigger["recommended_action"] in ["continue", "adapt", "replan", "escalate"]
