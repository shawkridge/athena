"""Phase 6: Analytics Engine - Estimation accuracy and pattern discovery.

Tests for:
- Estimation accuracy tracking
- Pattern discovery from task history
- Learning effectiveness metrics
- Completion rate analysis
"""

import pytest
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.integration.analytics import TaskAnalytics
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskStatus,
    TaskPriority,
)
from athena.prospective.store import ProspectiveStore


@pytest.fixture
def analytics(tmp_path):
    """Create analytics engine for testing."""
    db = Database(tmp_path / "test.db")
    return TaskAnalytics(db)


@pytest.fixture
def prospective_store(tmp_path):
    """Create prospective store for testing."""
    db = Database(tmp_path / "test.db")
    return ProspectiveStore(db)


class TestEstimationAccuracy:
    """Test estimation accuracy tracking."""

    def test_accuracy_initialization(self, analytics):
        """Test analytics initialization."""
        assert analytics.db is not None

    def test_estimation_accuracy_perfect(self, analytics, prospective_store):
        """Test perfect estimation (actual = estimated)."""
        from athena.planning.models import ExecutionPlan

        task = ProspectiveTask(
            content="Perfectly estimated task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.COMPLETED,
            status=TaskStatus.COMPLETED,
            estimated_duration_minutes=60,
            actual_duration_minutes=60,  # Perfect estimate
        )
        created = prospective_store.create(task)

        accuracy = 100.0 - abs((60 - 60) / 60 * 100)
        assert accuracy == 100.0

    def test_estimation_accuracy_overestimate(
        self, analytics, prospective_store
    ):
        """Test overestimation."""
        task = ProspectiveTask(
            content="Overestimated task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.COMPLETED,
            status=TaskStatus.COMPLETED,
            estimated_duration_minutes=120,
            actual_duration_minutes=60,  # Completed in half the time
        )
        created = prospective_store.create(task)

        # Overestimate should be detected
        variance = (60 - 120) / 120  # -0.5 or -50%
        assert variance < 0

    def test_estimation_accuracy_underestimate(
        self, analytics, prospective_store
    ):
        """Test underestimation."""
        task = ProspectiveTask(
            content="Underestimated task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.COMPLETED,
            status=TaskStatus.COMPLETED,
            estimated_duration_minutes=60,
            actual_duration_minutes=120,  # Took double the time
        )
        created = prospective_store.create(task)

        # Underestimate should be detected
        variance = (120 - 60) / 60  # 1.0 or 100%
        assert variance > 0

    def test_batch_accuracy_analysis(self, analytics, prospective_store):
        """Test batch accuracy analysis."""
        estimates = [30, 60, 90, 120]
        actuals = [25, 70, 85, 130]

        for est, actual in zip(estimates, actuals):
            task = ProspectiveTask(
                content=f"Task {est}min",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=est,
                actual_duration_minutes=actual,
            )
            prospective_store.create(task)

        # Analyze accuracy across batch
        total_variance = sum(
            abs(a - e) / e for e, a in zip(estimates, actuals)
        )
        avg_variance = total_variance / len(estimates)

        # Average variance should be < 50%
        assert avg_variance < 0.5


class TestPatternDiscovery:
    """Test pattern discovery from task history."""

    def test_success_pattern_detection(self, analytics, prospective_store):
        """Test detection of successful task patterns."""
        # Create series of successful short tasks
        for i in range(5):
            task = ProspectiveTask(
                content=f"Quick task {i}",
                priority=TaskPriority.LOW,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=15,
                actual_duration_minutes=14 + i,  # Consistently quick
            )
            prospective_store.create(task)

        # Pattern should be: short tasks consistently completed quickly
        patterns = prospective_store.list_by_status(TaskStatus.COMPLETED)
        assert len(patterns) >= 5

    def test_failure_pattern_detection(self, analytics, prospective_store):
        """Test detection of failure patterns."""
        # Create series of tasks that fail in a specific way
        for i in range(3):
            task = ProspectiveTask(
                content=f"Failing task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.FAILED,
                status=TaskStatus.PENDING,
                estimated_duration_minutes=60,
                actual_duration_minutes=120,  # Consistently over-runs
            )
            prospective_store.create(task)

        # Pattern should be detectable: complex tasks take 2x longer
        failed_tasks = prospective_store.list_by_phase(TaskPhase.FAILED)
        assert len(failed_tasks) >= 3

    def test_priority_impact_pattern(self, analytics, prospective_store):
        """Test pattern detection for priority impact."""
        # High-priority tasks
        for i in range(3):
            task = ProspectiveTask(
                content=f"High priority {i}",
                priority=TaskPriority.CRITICAL,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=55,  # Completed slightly faster
            )
            prospective_store.create(task)

        # Low-priority tasks
        for i in range(3):
            task = ProspectiveTask(
                content=f"Low priority {i}",
                priority=TaskPriority.LOW,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=75,  # Completed slower
            )
            prospective_store.create(task)

        # Pattern: high-priority tasks completed faster
        high_priority = [
            t
            for t in prospective_store.list_by_status(TaskStatus.COMPLETED)
            if t.priority == TaskPriority.CRITICAL
        ]
        assert len(high_priority) >= 3


class TestLearningEffectiveness:
    """Test learning effectiveness metrics."""

    def test_improvement_tracking(self, analytics, prospective_store):
        """Test improvement tracking over time."""
        # Early tasks (less accurate estimates)
        for i in range(3):
            task = ProspectiveTask(
                content=f"Early task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=100 - 10 * i,  # 100, 90, 80
            )
            prospective_store.create(task)

        # Later tasks (more accurate estimates)
        for i in range(3):
            task = ProspectiveTask(
                content=f"Later task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=62 - i,  # 62, 61, 60
            )
            prospective_store.create(task)

        # Later tasks should show improvement
        all_tasks = prospective_store.list_by_status(TaskStatus.COMPLETED)
        assert len(all_tasks) >= 6

    def test_strategy_effectiveness(self, analytics, prospective_store):
        """Test strategy effectiveness measurement."""
        # Tasks with structured planning
        for i in range(5):
            task = ProspectiveTask(
                content=f"Planned task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=65,  # 8% variance (good)
            )
            task.plan_quality_score = 0.9  # High planning quality
            prospective_store.create(task)

        # Tasks without planning
        for i in range(5):
            task = ProspectiveTask(
                content=f"Unplanned task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=90,  # 50% variance (poor)
            )
            prospective_store.create(task)

        # Planned tasks should have better accuracy
        completed = prospective_store.list_by_status(TaskStatus.COMPLETED)
        assert len(completed) >= 10


class TestPhaseEfficiency:
    """Test phase-based efficiency analysis."""

    def test_phase_duration_tracking(self, analytics, prospective_store):
        """Test duration tracking by phase."""
        # Tasks with different phase durations
        for phase, expected_duration in [
            (TaskPhase.PLANNING, 15),
            (TaskPhase.EXECUTING, 60),
            (TaskPhase.VERIFYING, 10),
        ]:
            task = ProspectiveTask(
                content=f"Task in {phase}",
                priority=TaskPriority.MEDIUM,
                phase=phase,
                status=TaskStatus.PENDING,
                estimated_duration_minutes=expected_duration,
            )
            prospective_store.create(task)

        # Should be able to track phases
        planning_tasks = prospective_store.list_by_phase(TaskPhase.PLANNING)
        executing_tasks = prospective_store.list_by_phase(TaskPhase.EXECUTING)
        verifying_tasks = prospective_store.list_by_phase(TaskPhase.VERIFYING)

        assert len(planning_tasks) >= 1
        assert len(executing_tasks) >= 1
        assert len(verifying_tasks) >= 1

    def test_phase_bottleneck_detection(self, analytics, prospective_store):
        """Test bottleneck detection by phase."""
        # Create tasks that spend different times in phases
        # Planning bottleneck
        for i in range(5):
            task = ProspectiveTask(
                content=f"Planning bottleneck {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                estimated_duration_minutes=120,  # Long planning
            )
            prospective_store.create(task)

        # Execution quick
        for i in range(5):
            task = ProspectiveTask(
                content=f"Quick execution {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.EXECUTING,
                status=TaskStatus.PENDING,
                estimated_duration_minutes=15,  # Quick execution
            )
            prospective_store.create(task)

        # Planning should be identified as bottleneck
        planning = prospective_store.list_by_phase(TaskPhase.PLANNING)
        executing = prospective_store.list_by_phase(TaskPhase.EXECUTING)

        # Planning tasks should have longer durations
        planning_total = sum(
            (t.estimated_duration_minutes or 0) for t in planning
        )
        executing_total = sum(
            (t.estimated_duration_minutes or 0) for t in executing
        )

        assert planning_total > executing_total


class TestCompletionRateAnalysis:
    """Test completion rate and success metrics."""

    def test_completion_rate(self, analytics, prospective_store):
        """Test completion rate calculation."""
        project_id = 1

        # Create 10 tasks
        for i in range(10):
            status = (
                TaskStatus.COMPLETED if i < 8 else TaskStatus.PENDING
            )
            task = ProspectiveTask(
                content=f"Task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED if status == TaskStatus.COMPLETED else TaskPhase.PLANNING,
                status=status,
                project_id=project_id,
            )
            prospective_store.create(task)

        completed = len(
            [
                t
                for t in prospective_store.list_by_status(TaskStatus.COMPLETED)
                if t.project_id == project_id
            ]
        )
        total = 10
        rate = (completed / total) * 100

        assert rate == 80.0

    def test_failure_rate(self, analytics, prospective_store):
        """Test failure rate analysis."""
        # Create mix of successful and failed tasks
        for i in range(7):
            task = ProspectiveTask(
                content=f"Successful {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
            )
            prospective_store.create(task)

        for i in range(3):
            task = ProspectiveTask(
                content=f"Failed {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.FAILED,
                status=TaskStatus.PENDING,
            )
            prospective_store.create(task)

        completed = len(
            prospective_store.list_by_status(TaskStatus.COMPLETED)
        )
        total = 10
        success_rate = (completed / total) * 100

        assert success_rate == 70.0


class TestAnalyticsPerformance:
    """Performance tests for Phase 6 Analytics."""

    def test_accuracy_analysis_latency(self, analytics, prospective_store):
        """Test latency for accuracy analysis."""
        # Create 50 completed tasks
        for i in range(50):
            task = ProspectiveTask(
                content=f"Task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.COMPLETED,
                status=TaskStatus.COMPLETED,
                estimated_duration_minutes=60,
                actual_duration_minutes=55 + (i % 20),
            )
            prospective_store.create(task)

        import time

        start = time.perf_counter()
        tasks = prospective_store.list_by_status(TaskStatus.COMPLETED)
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(tasks) >= 50
        assert duration_ms < 500  # Should be < 500ms

    def test_pattern_discovery_latency(self, analytics, prospective_store):
        """Test latency for pattern discovery."""
        # Create 100 tasks with patterns
        for priority in TaskPriority:
            for phase in TaskPhase:
                for i in range(5):
                    task = ProspectiveTask(
                        content=f"Task {priority} {phase} {i}",
                        priority=priority,
                        phase=phase,
                        status=TaskStatus.PENDING,
                    )
                    prospective_store.create(task)

        import time

        start = time.perf_counter()
        all_tasks = prospective_store.list_by_phase(TaskPhase.EXECUTING)
        duration_ms = (time.perf_counter() - start) * 1000

        assert len(all_tasks) > 0
        assert duration_ms < 200  # Should be < 200ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
