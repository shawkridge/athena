"""Phase 6: Analytics Integration Tests

Tests estimation accuracy, phase efficiency, learning effectiveness, and pattern discovery.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.prospective.models import ProspectiveTask, TaskPhase, TaskPriority, TaskStatus, Plan
from athena.prospective.store import ProspectiveStore
from athena.integration.analytics import TaskAnalytics, EstimationAccuracy, PhaseEfficiency


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
def analytics(temp_db: Database) -> TaskAnalytics:
    """Create analytics engine."""
    return TaskAnalytics(temp_db)


class TestEstimationAccuracy:
    """Test estimation accuracy metrics."""

    def test_create_estimation_accuracy(self):
        """Test creating estimation accuracy object."""
        acc = EstimationAccuracy(
            total_tasks=10,
            accurate_estimates=7,
            underestimated_count=2,
            overestimated_count=1,
            average_variance_percent=15.5,
            accuracy_rate=0.7,
        )

        assert acc.total_tasks == 10
        assert acc.accurate_estimates == 7
        assert acc.accuracy_rate == 0.7

    def test_estimation_accuracy_to_dict(self):
        """Test converting to dictionary."""
        acc = EstimationAccuracy(
            total_tasks=5,
            accurate_estimates=4,
            underestimated_count=1,
            overestimated_count=0,
            average_variance_percent=10.0,
            accuracy_rate=0.8,
        )

        acc_dict = acc.to_dict()
        assert acc_dict["total_tasks"] == 5
        assert acc_dict["accuracy_rate"] == 0.8


class TestTaskAnalytics:
    """Test task analytics functionality."""

    def test_analytics_initialization(self, analytics):
        """Test analytics initializes correctly."""
        assert analytics is not None
        assert analytics.prospective_store is not None

    @pytest.mark.asyncio
    async def test_analyze_estimation_accuracy_empty(self, analytics):
        """Test estimation accuracy with no completed tasks."""
        acc = await analytics.analyze_estimation_accuracy(project_id=999)

        assert acc.total_tasks == 0
        assert acc.accuracy_rate == 0.0

    @pytest.mark.asyncio
    async def test_analyze_phase_efficiency(self, prospective_store, analytics):
        """Test phase efficiency analysis."""
        project_id = 1

        # Create task with phase metrics
        task = ProspectiveTask(
            project_id=project_id,
            content="Test efficiency",
            active_form="Testing",
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
        )
        task_id = prospective_store.create_task(task)

        # Analyze
        efficiencies = await analytics.analyze_phase_efficiency(project_id)

        assert isinstance(efficiencies, list)

    @pytest.mark.asyncio
    async def test_analyze_learning_effectiveness(self, prospective_store, analytics):
        """Test learning effectiveness tracking."""
        project_id = 1

        # Create completed task with lessons
        task = ProspectiveTask(
            project_id=project_id,
            content="Test learning",
            active_form="Testing",
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            lessons_learned="Learned about X; Learned about Y",
        )
        prospective_store.create_task(task)

        # Analyze
        learning = await analytics.analyze_learning_effectiveness(project_id)

        assert "total_completed" in learning
        assert "learning_rate" in learning

    @pytest.mark.asyncio
    async def test_discover_patterns(self, prospective_store, analytics):
        """Test pattern discovery."""
        project_id = 1

        # Create tasks
        for i in range(3):
            task = ProspectiveTask(
                project_id=project_id,
                content=f"Task {i}",
                active_form=f"Task {i}",
                status=TaskStatus.COMPLETED,
                phase=TaskPhase.COMPLETED,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                actual_duration_minutes=60.0,
            )
            prospective_store.create_task(task)

        # Discover patterns
        patterns = await analytics.discover_patterns(project_id)

        assert "average_duration_minutes" in patterns
        assert "completion_rate" in patterns
        assert patterns["completion_rate"] > 0


class TestAnalyticsIntegration:
    """Test analytics system integration."""

    @pytest.mark.asyncio
    async def test_full_analytics_summary(self, prospective_store, analytics):
        """Test comprehensive analytics summary."""
        project_id = 1

        # Create sample tasks
        task = ProspectiveTask(
            project_id=project_id,
            content="Analytics test task",
            active_form="Testing analytics",
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            priority=TaskPriority.HIGH,
            actual_duration_minutes=45.0,
        )
        prospective_store.create_task(task)

        # Get summary
        summary = await analytics.get_project_analytics_summary(project_id)

        assert summary["project_id"] == project_id
        assert "estimation_accuracy" in summary
        assert "phase_efficiency" in summary
        assert "learning_effectiveness" in summary
        assert "discovered_patterns" in summary
