"""Phase 5: Monitoring Dashboard - Real-time task health tracking.

Tests for:
- TaskHealth scoring and status determination
- TaskMonitor real-time monitoring
- Project dashboard aggregation
- Performance under load
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.prospective.monitoring import TaskHealth, TaskMonitor
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskStatus,
    TaskPriority,
)
from athena.prospective.store import ProspectiveStore


@pytest.fixture
def task_monitor(tmp_path):
    """Create task monitor for testing."""
    db = Database(tmp_path / "test.db")
    return TaskMonitor(db)


@pytest.fixture
def prospective_store(tmp_path):
    """Create prospective store for testing."""
    db = Database(tmp_path / "test.db")
    return ProspectiveStore(db)


class TestTaskHealth:
    """Test TaskHealth model and scoring."""

    def test_task_health_initialization(self):
        """Test TaskHealth initialization."""
        health = TaskHealth(
            task_id=1,
            health_status="healthy",
            phase=TaskPhase.EXECUTING,
            progress_percent=50.0,
            health_score=0.85,
            duration_variance=0.1,
            blockers=0,
            errors=0,
            warnings=0,
        )

        assert health.task_id == 1
        assert health.health_status == "healthy"
        assert health.health_score == 0.85
        assert health.progress_percent == 50.0
        assert health.timestamp is not None

    def test_task_health_status_healthy(self):
        """Test healthy status determination."""
        health = TaskHealth(
            task_id=1,
            health_status="healthy",
            phase=TaskPhase.EXECUTING,
            progress_percent=75.0,
            health_score=0.90,
            duration_variance=0.05,
            blockers=0,
            errors=0,
            warnings=0,
        )

        assert health.health_status == TaskHealth.HEALTHY
        assert health.health_score >= 0.75

    def test_task_health_status_warning(self):
        """Test warning status determination."""
        health = TaskHealth(
            task_id=1,
            health_status="warning",
            phase=TaskPhase.EXECUTING,
            progress_percent=50.0,
            health_score=0.60,
            duration_variance=0.5,
            blockers=0,
            errors=1,
            warnings=2,
        )

        assert health.health_status == TaskHealth.WARNING
        assert 0.5 <= health.health_score < 0.75

    def test_task_health_status_critical(self):
        """Test critical status determination."""
        health = TaskHealth(
            task_id=1,
            health_status="critical",
            phase=TaskPhase.EXECUTING,
            progress_percent=30.0,
            health_score=0.40,
            duration_variance=1.0,
            blockers=2,
            errors=3,
            warnings=4,
        )

        assert health.health_status == TaskHealth.CRITICAL
        assert health.health_score < 0.5

    def test_task_health_to_dict(self):
        """Test TaskHealth serialization."""
        health = TaskHealth(
            task_id=1,
            health_status="healthy",
            phase=TaskPhase.EXECUTING,
            progress_percent=50.0,
            health_score=0.85,
            duration_variance=0.1,
            blockers=0,
            errors=0,
            warnings=0,
        )

        data = health.to_dict()

        assert "task_id" in data
        assert "health_status" in data
        assert "health_score" in data
        assert "progress_percent" in data
        assert data["task_id"] == 1
        assert data["health_score"] == 0.85


class TestTaskMonitor:
    """Test TaskMonitor functionality."""

    @pytest.mark.asyncio
    async def test_monitor_initialization(self, task_monitor):
        """Test TaskMonitor initialization."""
        assert task_monitor.db is not None
        assert task_monitor.prospective_store is not None
        assert task_monitor.last_check is not None

    @pytest.mark.asyncio
    async def test_get_task_health_nonexistent(self, task_monitor):
        """Test get_task_health for nonexistent task."""
        health = await task_monitor.get_task_health(999)
        assert health is None

    @pytest.mark.asyncio
    async def test_get_task_health_simple_task(
        self, task_monitor, prospective_store
    ):
        """Test get_task_health for a simple task."""
        # Create a task
        task = ProspectiveTask(
            project_id=1,
            content="Test task",
            active_form="Executing: Test task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)

        # Get health
        health = await task_monitor.get_task_health(task_id)

        assert health is not None
        assert health.task_id == task_id
        assert health.phase == TaskPhase.EXECUTING
        assert health.progress_percent >= 0
        assert 0.0 <= health.health_score <= 1.0

    @pytest.mark.asyncio
    async def test_progress_calculation(self, task_monitor, prospective_store):
        """Test progress calculation by phase."""
        phases = [
            (TaskPhase.PLANNING, 10),
            (TaskPhase.PLAN_READY, 20),
            (TaskPhase.EXECUTING, 60),
            (TaskPhase.VERIFYING, 90),
            (TaskPhase.COMPLETED, 100),
        ]

        for phase, expected_progress in phases:
            task = ProspectiveTask(
                project_id=1,
                content=f"Test {phase}",
                active_form="Executing: Test {phase}",
                priority=TaskPriority.MEDIUM,
                phase=phase,
                status=TaskStatus.PENDING,
            )
            task_id = prospective_store.create_task(task)
            health = await task_monitor.get_task_health(task_id)

            assert health.progress_percent == expected_progress

    @pytest.mark.asyncio
    async def test_get_project_dashboard(
        self, task_monitor, prospective_store
    ):
        """Test project dashboard aggregation."""
        project_id = 1

        # Create multiple tasks
        for i in range(5):
            task = ProspectiveTask(
                content=f"Task {i}",
                active_form="Executing: Task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.EXECUTING if i < 3 else TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED if i >= 3 else TaskStatus.PENDING,
                project_id=project_id,
            )
            prospective_store.create_task(task)

        # Get dashboard
        dashboard = await task_monitor.get_project_dashboard(project_id)

        assert dashboard["project_id"] == project_id
        assert "summary" in dashboard
        assert "health" in dashboard
        assert "phases" in dashboard
        assert "priorities" in dashboard

        # Check summary
        assert dashboard["summary"]["total_tasks"] == 5
        assert dashboard["summary"]["completed"] >= 2
        assert dashboard["summary"]["in_progress"] >= 0

        # Check health aggregation
        assert "average_score" in dashboard["health"]
        assert "statuses" in dashboard["health"]
        assert 0.0 <= dashboard["health"]["average_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_get_active_tasks_status(
        self, task_monitor, prospective_store
    ):
        """Test active tasks status retrieval."""
        project_id = 1

        # Create active tasks
        for i in range(3):
            task = ProspectiveTask(
                content=f"Active Task {i}",
                active_form="Executing: Active Task {i}",
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                phase=TaskPhase.EXECUTING,
                status=TaskStatus.PENDING,
                project_id=project_id,
            )
            prospective_store.create_task(task)

        # Create completed task (should not appear in active)
        task = ProspectiveTask(
            content="Completed Task",
            active_form="Executing: Completed Task",
            priority=TaskPriority.LOW,
            phase=TaskPhase.COMPLETED,
            status=TaskStatus.COMPLETED,
            project_id=project_id,
        )
        prospective_store.create_task(task)

        # Get active tasks
        active = await task_monitor.get_active_tasks_status(project_id)

        assert len(active) > 0
        assert all(t["phase"] == "EXECUTING" for t in active)
        assert all("health_score" in t for t in active)

    @pytest.mark.asyncio
    async def test_health_score_with_variance(
        self, task_monitor, prospective_store
    ):
        """Test health score calculation with variance."""
        # On-track task
        task1 = ProspectiveTask(
            project_id=1,
            content="On-track task",
            active_form="Executing: On-track task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
        )
        created1 = prospective_store.create_task(task1)
        health1 = await task_monitor.get_task_health(created1.id)

        # Health score should be reasonable
        assert health1.health_score > 0.5

    @pytest.mark.asyncio
    async def test_health_degradation_with_blockers(
        self, task_monitor, prospective_store
    ):
        """Test health degradation with blockers."""
        task = ProspectiveTask(
            project_id=1,
            content="Blocked task",
            active_form="Executing: Blocked task",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            blocked_reason="Waiting for approval",
        )
        task_id = prospective_store.create_task(task)
        health = await task_monitor.get_task_health(task_id)

        # Health should be lower due to blocker
        assert health.blockers >= 1
        # Health score should reflect the blocker
        assert health.health_score < 1.0


class TestTaskMonitorPerformance:
    """Performance tests for Phase 5 Monitoring Dashboard."""

    @pytest.mark.asyncio
    async def test_single_task_health_latency(self, task_monitor, prospective_store):
        """Test latency for single task health check."""
        task = ProspectiveTask(
            project_id=1,
            content="Test task",
            active_form="Executing: Test task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)

        import time

        start = time.perf_counter()
        health = await task_monitor.get_task_health(task_id)
        duration_ms = (time.perf_counter() - start) * 1000

        assert health is not None
        assert duration_ms < 100  # Should be < 100ms

    @pytest.mark.asyncio
    async def test_dashboard_aggregation_latency(
        self, task_monitor, prospective_store
    ):
        """Test latency for project dashboard aggregation."""
        project_id = 1

        # Create 10 tasks
        for i in range(10):
            task = ProspectiveTask(
                content=f"Task {i}",
                active_form="Executing: Task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.EXECUTING,
                status=TaskStatus.PENDING,
                project_id=project_id,
            )
            prospective_store.create_task(task)

        import time

        start = time.perf_counter()
        dashboard = await task_monitor.get_project_dashboard(project_id)
        duration_ms = (time.perf_counter() - start) * 1000

        assert dashboard is not None
        assert duration_ms < 500  # Should be < 500ms for 10 tasks


class TestDashboardIntegration:
    """Integration tests for monitoring dashboard."""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(
        self, task_monitor, prospective_store
    ):
        """Test complete monitoring workflow."""
        project_id = 1

        # Create initial tasks
        tasks = []
        for i in range(3):
            task = ProspectiveTask(
                content=f"Task {i}",
                active_form="Executing: Task {i}",
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                project_id=project_id,
            )
            created = prospective_store.create_task(task)
            tasks.append(created)

        # Get initial dashboard
        dashboard1 = await task_monitor.get_project_dashboard(project_id)
        assert dashboard1["summary"]["total_tasks"] == 3

        # Advance tasks
        for task in tasks:
            task.phase = TaskPhase.EXECUTING
            prospective_store.update(task)

        # Get updated dashboard
        dashboard2 = await task_monitor.get_project_dashboard(project_id)
        assert dashboard2["summary"]["in_progress"] > 0

        # Get individual task health
        for task in tasks:
            health = await task_monitor.get_task_health(task.id)
            assert health is not None
            assert health.progress_percent > 10  # Advanced from planning

    @pytest.mark.asyncio
    async def test_health_monitoring_with_priority_escalation(
        self, task_monitor, prospective_store
    ):
        """Test health monitoring with priority-based escalation."""
        # High-priority task should escalate issues faster
        task_high = ProspectiveTask(
            project_id=1,
            content="Critical task",
            active_form="Executing: Critical task",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
        )
        created_high = prospective_store.create_task(task_high)
        health_high = await task_monitor.get_task_health(created_high.id)

        # Regular task
        task_normal = ProspectiveTask(
            project_id=1,
            content="Normal task",
            active_form="Executing: Normal task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
        )
        created_normal = prospective_store.create_task(task_normal)
        health_normal = await task_monitor.get_task_health(created_normal.id)

        # Both should have health scores
        assert health_high.health_score > 0
        assert health_normal.health_score > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
