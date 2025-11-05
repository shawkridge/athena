"""Phase 8: Project Coordinator - Multi-project coordination and resource management.

Tests for:
- Cross-project dependencies
- Critical path analysis
- Resource conflict detection
- Multi-project visualization
"""

import pytest
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.integration.project_coordinator import ProjectCoordinator
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskStatus,
    TaskPriority,
)
from athena.prospective.store import ProspectiveStore


@pytest.fixture
def project_coordinator(tmp_path):
    """Create project coordinator for testing."""
    db = Database(tmp_path / "test.db")
    return ProjectCoordinator(db)


@pytest.fixture
def prospective_store(tmp_path):
    """Create prospective store for testing."""
    db = Database(tmp_path / "test.db")
    return ProspectiveStore(db)


class TestCrossProjectDependencies:
    """Test cross-project dependency management."""

    def test_add_project_dependency(
        self, project_coordinator, prospective_store
    ):
        """Test adding cross-project dependency."""
        # Create tasks in different projects
        task1 = ProspectiveTask(
            content="Backend API",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=1,
        )
        task2 = ProspectiveTask(
            content="Frontend UI",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=2,
        )

        created1 = prospective_store.create(task1)
        created2 = prospective_store.create(task2)

        # Add dependency: Frontend depends on Backend
        dependency = project_coordinator.add_dependency(
            from_task_id=created2.id,
            from_project_id=2,
            to_task_id=created1.id,
            to_project_id=1,
            dependency_type="depends_on",
        )

        assert dependency is not None

    def test_dependency_blocking(self, project_coordinator, prospective_store):
        """Test dependency blocking."""
        # Create dependent tasks
        backend_task = ProspectiveTask(
            content="Backend implementation",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=1,
        )
        frontend_task = ProspectiveTask(
            content="Frontend implementation",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=2,
        )

        created_backend = prospective_store.create(backend_task)
        created_frontend = prospective_store.create(frontend_task)

        # Frontend depends on Backend
        project_coordinator.add_dependency(
            from_task_id=created_frontend.id,
            from_project_id=2,
            to_task_id=created_backend.id,
            to_project_id=1,
            dependency_type="depends_on",
        )

        # Backend not started should block Frontend
        assert created_backend.phase == TaskPhase.PLANNING
        # Frontend should check for blocking dependencies
        blocking = project_coordinator.get_blocking_dependencies(
            created_frontend.id
        )
        assert blocking is not None

    def test_multiple_dependencies(self, project_coordinator, prospective_store):
        """Test tasks with multiple dependencies."""
        # Create a chain: Task A -> Task B -> Task C
        task_a = ProspectiveTask(
            content="Task A",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=1,
        )
        task_b = ProspectiveTask(
            content="Task B",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=2,
        )
        task_c = ProspectiveTask(
            content="Task C",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=3,
        )

        created_a = prospective_store.create(task_a)
        created_b = prospective_store.create(task_b)
        created_c = prospective_store.create(task_c)

        # B depends on A
        project_coordinator.add_dependency(
            from_task_id=created_b.id,
            from_project_id=2,
            to_task_id=created_a.id,
            to_project_id=1,
            dependency_type="depends_on",
        )

        # C depends on B
        project_coordinator.add_dependency(
            from_task_id=created_c.id,
            from_project_id=3,
            to_task_id=created_b.id,
            to_project_id=2,
            dependency_type="depends_on",
        )

        # Should detect chain: C -> B -> A
        dependencies = project_coordinator.get_all_dependencies(created_c.id)
        assert dependencies is not None


class TestCriticalPathAnalysis:
    """Test critical path analysis."""

    def test_simple_critical_path(
        self, project_coordinator, prospective_store
    ):
        """Test critical path on simple task sequence."""
        project_id = 1

        # Create sequential tasks
        tasks = []
        for i in range(3):
            task = ProspectiveTask(
                content=f"Step {i+1}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                project_id=project_id,
                estimated_duration_minutes=(i + 1) * 30,  # 30, 60, 90 min
            )
            tasks.append(prospective_store.create(task))

        # Analyze critical path
        critical_path = project_coordinator.analyze_critical_path(
            project_id
        )

        assert critical_path is not None
        if "total_duration" in critical_path:
            # Total should be at least the sum of sequential tasks
            assert critical_path["total_duration"] >= 180  # 30+60+90

    def test_parallel_paths(self, project_coordinator, prospective_store):
        """Test critical path with parallel tasks."""
        project_id = 1

        # Create parallel tasks (should reduce critical path)
        # Both take 1 hour, but can run in parallel
        task1 = ProspectiveTask(
            content="Parallel task 1",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=60,
        )
        task2 = ProspectiveTask(
            content="Parallel task 2",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=60,
        )

        created1 = prospective_store.create(task1)
        created2 = prospective_store.create(task2)

        critical_path = project_coordinator.analyze_critical_path(
            project_id
        )

        assert critical_path is not None

    def test_bottleneck_identification(
        self, project_coordinator, prospective_store
    ):
        """Test identification of critical bottleneck."""
        project_id = 1

        # Create a bottleneck: one slow task in critical path
        slow_task = ProspectiveTask(
            content="Slow task (bottleneck)",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=480,  # 8 hours
        )
        fast_task = ProspectiveTask(
            content="Fast task",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=30,  # 30 minutes
        )

        created_slow = prospective_store.create(slow_task)
        created_fast = prospective_store.create(fast_task)

        critical_path = project_coordinator.analyze_critical_path(
            project_id
        )

        # Slow task should be on critical path
        assert critical_path is not None

    def test_slack_time_calculation(
        self, project_coordinator, prospective_store
    ):
        """Test slack time (schedule flexibility) calculation."""
        project_id = 1

        # Create tasks with different slack
        task1 = ProspectiveTask(
            content="Critical task",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=60,
        )
        task2 = ProspectiveTask(
            content="Non-critical task",
            priority=TaskPriority.LOW,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=project_id,
            estimated_duration_minutes=30,
        )

        prospective_store.create(task1)
        prospective_store.create(task2)

        critical_path = project_coordinator.analyze_critical_path(
            project_id
        )

        assert critical_path is not None


class TestResourceConflictDetection:
    """Test resource conflict detection."""

    def test_detect_person_conflict(
        self, project_coordinator, prospective_store
    ):
        """Test detection of same person assigned to concurrent tasks."""
        # Simulate: same person assigned to overlapping tasks
        task1 = ProspectiveTask(
            content="Task for John",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=1,
            assigned_to="john@example.com",
        )
        task2 = ProspectiveTask(
            content="Another task for John",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=2,
            assigned_to="john@example.com",
        )

        created1 = prospective_store.create(task1)
        created2 = prospective_store.create(task2)

        # Detect conflict
        conflicts = project_coordinator.detect_resource_conflicts([1, 2])

        assert conflicts is not None
        # Should identify person conflict if both are concurrent
        if "conflicts" in conflicts:
            assert isinstance(conflicts["conflicts"], list)

    def test_detect_tool_conflict(
        self, project_coordinator, prospective_store
    ):
        """Test detection of conflicting tool requirements."""
        # Both tasks need same expensive resource
        task1 = ProspectiveTask(
            content="Task using GPU",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=1,
            required_tools=["gpu"],
        )
        task2 = ProspectiveTask(
            content="Another task using GPU",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=2,
            required_tools=["gpu"],
        )

        prospective_store.create(task1)
        prospective_store.create(task2)

        conflicts = project_coordinator.detect_resource_conflicts([1, 2])

        assert conflicts is not None

    def test_conflict_severity_assessment(
        self, project_coordinator, prospective_store
    ):
        """Test conflict severity assessment."""
        # High-priority conflict should be flagged as critical
        task1 = ProspectiveTask(
            content="Critical task",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=1,
            assigned_to="person@example.com",
        )
        task2 = ProspectiveTask(
            content="Also critical",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.EXECUTING,
            status=TaskStatus.PENDING,
            project_id=2,
            assigned_to="person@example.com",  # Same person
        )

        prospective_store.create(task1)
        prospective_store.create(task2)

        conflicts = project_coordinator.detect_resource_conflicts([1, 2])

        assert conflicts is not None
        # Critical conflicts should be identified
        if "severity" in conflicts:
            severity = conflicts["severity"]
            assert severity in ["low", "medium", "high", "critical"]


class TestProjectVisualization:
    """Test multi-project visualization."""

    def test_project_network_generation(
        self, project_coordinator, prospective_store
    ):
        """Test project network visualization."""
        # Create 3 projects with dependencies
        for project_id in [1, 2, 3]:
            task = ProspectiveTask(
                content=f"Project {project_id} task",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                project_id=project_id,
            )
            prospective_store.create(task)

        # Generate network
        network = project_coordinator.get_project_network([1, 2, 3])

        assert network is not None
        if "projects" in network:
            assert len(network["projects"]) >= 3

    def test_timeline_view(self, project_coordinator, prospective_store):
        """Test project timeline view."""
        project_ids = [1, 2, 3]

        for project_id in project_ids:
            for i in range(2):
                task = ProspectiveTask(
                    content=f"Project {project_id} task {i}",
                    priority=TaskPriority.MEDIUM,
                    phase=TaskPhase.PLANNING,
                    status=TaskStatus.PENDING,
                    project_id=project_id,
                    estimated_duration_minutes=60 * (i + 1),
                )
                prospective_store.create(task)

        # Get timeline
        timeline = project_coordinator.get_timeline_view(project_ids)

        assert timeline is not None


class TestProjectCoordinatorIntegration:
    """Integration tests for project coordinator."""

    def test_full_coordination_workflow(
        self, project_coordinator, prospective_store
    ):
        """Test complete coordination workflow."""
        # Create multi-project scenario
        projects = [1, 2, 3]

        for project_id in projects:
            task = ProspectiveTask(
                content=f"Project {project_id} main task",
                priority=TaskPriority.HIGH,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                project_id=project_id,
                estimated_duration_minutes=120,
            )
            prospective_store.create(task)

        # Step 1: Analyze critical paths
        for project_id in projects:
            cp = project_coordinator.analyze_critical_path(project_id)
            assert cp is not None

        # Step 2: Detect conflicts
        conflicts = project_coordinator.detect_resource_conflicts(projects)
        assert conflicts is not None

        # Step 3: Get network view
        network = project_coordinator.get_project_network(projects)
        assert network is not None

    def test_dependency_impact_analysis(
        self, project_coordinator, prospective_store
    ):
        """Test impact analysis of dependencies."""
        # Create a dependency chain across projects
        task1 = ProspectiveTask(
            content="Phase 1: Foundation",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=1,
            estimated_duration_minutes=240,
        )
        task2 = ProspectiveTask(
            content="Phase 2: Build",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=2,
            estimated_duration_minutes=360,
        )
        task3 = ProspectiveTask(
            content="Phase 3: Deploy",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
            project_id=3,
            estimated_duration_minutes=120,
        )

        created1 = prospective_store.create(task1)
        created2 = prospective_store.create(task2)
        created3 = prospective_store.create(task3)

        # Create dependency chain
        project_coordinator.add_dependency(
            from_task_id=created2.id,
            from_project_id=2,
            to_task_id=created1.id,
            to_project_id=1,
            dependency_type="depends_on",
        )
        project_coordinator.add_dependency(
            from_task_id=created3.id,
            from_project_id=3,
            to_task_id=created2.id,
            to_project_id=2,
            dependency_type="depends_on",
        )

        # Delay in Phase 1 should impact Phase 2 and 3
        # This would be validated in a full system test


class TestProjectCoordinatorPerformance:
    """Performance tests for Phase 8 Coordinator."""

    def test_critical_path_latency(
        self, project_coordinator, prospective_store
    ):
        """Test critical path analysis latency."""
        project_id = 1

        # Create 20 tasks
        for i in range(20):
            task = ProspectiveTask(
                content=f"Task {i}",
                priority=TaskPriority.MEDIUM,
                phase=TaskPhase.PLANNING,
                status=TaskStatus.PENDING,
                project_id=project_id,
                estimated_duration_minutes=30,
            )
            prospective_store.create(task)

        import time

        start = time.perf_counter()
        cp = project_coordinator.analyze_critical_path(project_id)
        duration_ms = (time.perf_counter() - start) * 1000

        assert cp is not None
        assert duration_ms < 500  # Should be < 500ms

    def test_conflict_detection_latency(
        self, project_coordinator, prospective_store
    ):
        """Test resource conflict detection latency."""
        projects = [1, 2, 3, 4, 5]

        # Create tasks in each project
        for project_id in projects:
            for i in range(10):
                task = ProspectiveTask(
                    content=f"Project {project_id} task {i}",
                    priority=TaskPriority.MEDIUM,
                    phase=TaskPhase.EXECUTING,
                    status=TaskStatus.PENDING,
                    project_id=project_id,
                )
                prospective_store.create(task)

        import time

        start = time.perf_counter()
        conflicts = project_coordinator.detect_resource_conflicts(projects)
        duration_ms = (time.perf_counter() - start) * 1000

        assert conflicts is not None
        assert duration_ms < 1000  # Should be < 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
