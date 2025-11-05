"""Phase 5: Monitoring Dashboard Integration Tests

Tests the real-time task monitoring and health tracking system.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.prospective.models import ProspectiveTask, TaskPhase, TaskPriority, TaskStatus, Plan
from athena.prospective.store import ProspectiveStore
from athena.prospective.monitoring import TaskMonitor, TaskHealth


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
def task_monitor(temp_db: Database) -> TaskMonitor:
    """Create task monitor."""
    return TaskMonitor(temp_db)


class TestTaskHealth:
    """Test task health models."""

    def test_create_task_health(self):
        """Test creating task health object."""
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
        assert health.health_status == TaskHealth.HEALTHY
        assert health.progress_percent == 50.0

    def test_task_health_to_dict(self):
        """Test converting task health to dictionary."""
        health = TaskHealth(
            task_id=1,
            health_status="warning",
            phase=TaskPhase.EXECUTING,
            progress_percent=75.0,
            health_score=0.65,
            duration_variance=0.5,
            blockers=1,
            errors=2,
            warnings=1,
        )

        health_dict = health.to_dict()
        assert health_dict["task_id"] == 1
        assert health_dict["health_status"] == "warning"
        assert health_dict["health_score"] == 0.65


class TestTaskMonitor:
    """Test task monitoring functionality."""

    def test_monitor_initialization(self, task_monitor):
        """Test monitor initializes correctly."""
        assert task_monitor is not None
        assert task_monitor.prospective_store is not None

    @pytest.mark.asyncio
    async def test_get_task_health_not_found(self, task_monitor):
        """Test getting health of non-existent task."""
        health = await task_monitor.get_task_health(999)
        assert health is None

    @pytest.mark.asyncio
    async def test_get_task_health_healthy_task(self, prospective_store, task_monitor):
        """Test health check of a healthy task."""
        # Create task
        task = ProspectiveTask(
            project_id=1,
            content="Quick implementation",
            active_form="Implementing",
            status=TaskStatus.PENDING,
            phase=TaskPhase.EXECUTING,
        )
        task_id = prospective_store.create_task(task)

        # Add plan to task
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=30,
        )

        # Check health
        health = await task_monitor.get_task_health(task_id)

        assert health is not None
        assert health.progress_percent > 0
        assert health.health_status in ["healthy", "warning", "critical"]

    @pytest.mark.asyncio
    async def test_get_project_dashboard(self, prospective_store, task_monitor):
        """Test getting project dashboard."""
        project_id = 1

        # Create multiple tasks
        for i in range(3):
            task = ProspectiveTask(
                project_id=project_id,
                content=f"Task {i}",
                active_form=f"Task {i}",
                status=TaskStatus.PENDING if i < 2 else TaskStatus.COMPLETED,
                phase=TaskPhase.PLANNING if i == 0 else TaskPhase.EXECUTING,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
            )
            prospective_store.create_task(task)

        # Get dashboard
        dashboard = await task_monitor.get_project_dashboard(project_id)

        assert dashboard["project_id"] == project_id
        assert dashboard["summary"]["total_tasks"] == 3
        assert dashboard["summary"]["completed"] == 1
        assert "health" in dashboard
        assert "phases" in dashboard

    @pytest.mark.asyncio
    async def test_get_active_tasks_status(self, prospective_store, task_monitor):
        """Test getting status of active tasks."""
        project_id = 1

        # Create executing task
        task = ProspectiveTask(
            project_id=project_id,
            content="Active task",
            active_form="Active task",
            phase=TaskPhase.EXECUTING,
        )
        task_id = prospective_store.create_task(task)

        # Get active tasks
        active = await task_monitor.get_active_tasks_status(project_id)

        assert isinstance(active, list)
        assert any(t["task_id"] == task_id for t in active)


class TestHealthMetrics:
    """Test health metric calculations."""

    @pytest.mark.asyncio
    async def test_progress_calculation(self, prospective_store, task_monitor):
        """Test task progress calculation."""
        task = ProspectiveTask(
            project_id=1,
            content="Test progress",
            active_form="Testing progress",
            status=TaskStatus.PENDING,
            phase=TaskPhase.EXECUTING,
        )
        task_id = prospective_store.create_task(task)

        progress = task_monitor._calculate_progress(prospective_store.get_task(task_id))
        assert 0 <= progress <= 100

    @pytest.mark.asyncio
    async def test_duration_variance_on_track(self, prospective_store, task_monitor):
        """Test duration variance when on track."""
        task = ProspectiveTask(
            project_id=1,
            content="Quick task",
            active_form="Quick task",
            phase=TaskPhase.EXECUTING,
        )
        task_id = prospective_store.create_task(task)

        # Add plan
        prospective_store.create_plan_for_task(task_id, ["Step 1"], 30)

        task = prospective_store.get_task(task_id)
        variance = task_monitor._calculate_duration_variance(task)

        # Variance should be small since task just started
        assert isinstance(variance, float)

    @pytest.mark.asyncio
    async def test_health_score_calculation(self, task_monitor):
        """Test health score calculation."""
        # Healthy scenario
        healthy_score = task_monitor._calculate_health_score(0.1, 0, 0)
        assert healthy_score > 0.8

        # Problematic scenario
        critical_score = task_monitor._calculate_health_score(1.0, 5, 1)
        assert critical_score < 0.5

    def test_health_status_determination(self, task_monitor):
        """Test determining health status from metrics."""
        # Healthy
        healthy = task_monitor._determine_health_status(0.9, 0, 0)
        assert healthy == TaskHealth.HEALTHY

        # Warning
        warning = task_monitor._determine_health_status(0.5, 2, 0)
        assert warning == TaskHealth.WARNING

        # Critical
        critical = task_monitor._determine_health_status(0.3, 5, 1)
        assert critical == TaskHealth.CRITICAL


class TestMonitoringIntegration:
    """Test monitoring system integration."""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self, prospective_store, task_monitor):
        """Test complete monitoring workflow."""
        project_id = 1

        # Create task
        task = ProspectiveTask(
            project_id=project_id,
            content="Full monitoring test",
            active_form="Testing monitoring",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            phase_started_at=datetime.now() - timedelta(minutes=20),
        )
        task_id = prospective_store.create_task(task)

        # Add plan
        prospective_store.create_plan_for_task(task_id, ["A", "B", "C"], 60)

        # Get health
        health = await task_monitor.get_task_health(task_id)
        assert health is not None
        assert health.task_id == task_id

        # Get dashboard
        dashboard = await task_monitor.get_project_dashboard(project_id)
        assert dashboard["summary"]["total_tasks"] >= 1

        # Get active tasks
        active = await task_monitor.get_active_tasks_status(project_id)
        assert len(active) > 0
