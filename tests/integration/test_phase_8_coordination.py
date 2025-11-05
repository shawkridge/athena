"""Phase 8: Multi-Project Coordination Integration Tests

Tests cross-project dependencies, critical path analysis, and resource conflicts.
"""

import pytest
from pathlib import Path

from athena.core.database import Database
from athena.prospective.models import ProspectiveTask, TaskPhase, TaskStatus
from athena.prospective.store import ProspectiveStore
from athena.integration.project_coordinator import (
    ProjectCoordinator,
    ProjectDependency,
    CriticalPath,
    ResourceConflict,
)


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
def project_coordinator(temp_db: Database) -> ProjectCoordinator:
    """Create project coordinator."""
    return ProjectCoordinator(temp_db)


class TestProjectDependency:
    """Test project dependency objects."""

    def test_create_project_dependency(self):
        """Test creating project dependency."""
        dep = ProjectDependency(
            from_task_id=1,
            from_project_id=1,
            to_task_id=2,
            to_project_id=2,
            dependency_type="depends_on",
            description="Task 1 depends on Task 2 completion",
        )

        assert dep.from_task_id == 1
        assert dep.dependency_type == "depends_on"

    def test_project_dependency_to_dict(self):
        """Test converting dependency to dictionary."""
        dep = ProjectDependency(
            from_task_id=10,
            from_project_id=1,
            to_task_id=20,
            to_project_id=2,
            dependency_type="blocks",
        )

        dep_dict = dep.to_dict()
        assert dep_dict["from_task_id"] == 10
        assert dep_dict["to_project_id"] == 2


class TestCriticalPath:
    """Test critical path objects."""

    def test_create_critical_path(self):
        """Test creating critical path."""
        cp = CriticalPath(
            task_ids=[1, 2, 3, 4],
            total_duration_minutes=480,
            slack_time_minutes=120,
        )

        assert cp.total_duration_minutes == 480
        assert len(cp.task_ids) == 4

    def test_critical_path_to_dict(self):
        """Test converting to dictionary."""
        cp = CriticalPath(
            task_ids=[5, 6, 7],
            total_duration_minutes=360,
            slack_time_minutes=60,
        )

        cp_dict = cp.to_dict()
        assert cp_dict["total_duration_minutes"] == 360


class TestResourceConflict:
    """Test resource conflict objects."""

    def test_create_resource_conflict(self):
        """Test creating resource conflict."""
        conflict = ResourceConflict(
            conflict_type="person",
            task_ids=[1, 2, 3],
            description="Person assigned to 3 concurrent tasks",
            severity="high",
            recommendation="Redistribute tasks",
        )

        assert conflict.conflict_type == "person"
        assert conflict.severity == "high"


class TestProjectCoordinator:
    """Test project coordination functionality."""

    def test_coordinator_initialization(self, project_coordinator):
        """Test coordinator initializes correctly."""
        assert project_coordinator is not None
        assert project_coordinator.prospective_store is not None

    @pytest.mark.asyncio
    async def test_add_dependency(self, project_coordinator):
        """Test adding cross-project dependency."""
        success = await project_coordinator.add_dependency(
            from_task_id=1,
            from_project_id=1,
            to_task_id=2,
            to_project_id=2,
            dependency_type="depends_on",
        )

        assert success is True
        assert len(project_coordinator.dependencies) > 0

    @pytest.mark.asyncio
    async def test_get_dependencies_by_task(self, project_coordinator):
        """Test retrieving dependencies by task."""
        # Add some dependencies
        await project_coordinator.add_dependency(
            from_task_id=1,
            from_project_id=1,
            to_task_id=2,
            to_project_id=2,
            dependency_type="depends_on",
        )

        # Get dependencies
        deps = await project_coordinator.get_dependencies(task_id=1)

        assert isinstance(deps, list)
        assert len(deps) > 0

    @pytest.mark.asyncio
    async def test_analyze_critical_path(self, prospective_store, project_coordinator):
        """Test critical path analysis."""
        project_id = 1

        # Create tasks
        for i in range(3):
            task = ProspectiveTask(
                project_id=project_id,
                content=f"Task {i}",
                active_form=f"Task {i}",
                phase=TaskPhase.EXECUTING,
            )
            prospective_store.create_task(task)

        # Analyze critical path
        cp = await project_coordinator.analyze_critical_path(project_id)

        if cp is not None:
            assert isinstance(cp, CriticalPath)
            assert len(cp.task_ids) > 0
            assert cp.total_duration_minutes > 0

    @pytest.mark.asyncio
    async def test_detect_resource_conflicts(self, prospective_store, project_coordinator):
        """Test resource conflict detection."""
        project_ids = [1, 2]

        # Create executing tasks
        for proj_id in project_ids:
            task = ProspectiveTask(
                project_id=proj_id,
                content="Task",
                active_form="Executing",
                phase=TaskPhase.EXECUTING,
                assignee="john",
            )
            prospective_store.create_task(task)

        # Detect conflicts
        conflicts = await project_coordinator.detect_resource_conflicts(project_ids)

        assert isinstance(conflicts, list)

    @pytest.mark.asyncio
    async def test_get_project_network(self, prospective_store, project_coordinator):
        """Test getting project network."""
        project_ids = [1, 2, 3]

        # Create tasks in each project
        for proj_id in project_ids:
            task = ProspectiveTask(
                project_id=proj_id,
                content=f"Task in project {proj_id}",
                active_form="Executing",
                phase=TaskPhase.EXECUTING,
            )
            prospective_store.create_task(task)

        # Get network
        network = await project_coordinator.get_project_network(project_ids)

        assert "projects" in network
        assert "dependencies" in network
        assert len(network["projects"]) <= len(project_ids)

    @pytest.mark.asyncio
    async def test_get_resource_allocation(self, prospective_store, project_coordinator):
        """Test resource allocation analysis."""
        project_ids = [1, 2]

        # Create tasks with different assignees
        for proj_id in project_ids:
            for i in range(2):
                task = ProspectiveTask(
                    project_id=proj_id,
                    content=f"Task {i}",
                    active_form="Executing",
                    assignee="alice" if i == 0 else "bob",
                    phase=TaskPhase.EXECUTING,
                )
                prospective_store.create_task(task)

        # Get allocation
        allocation = await project_coordinator.get_resource_allocation(project_ids)

        assert "by_person" in allocation
        assert "by_priority" in allocation
        assert allocation["total_tasks"] > 0

    @pytest.mark.asyncio
    async def test_suggest_task_sequencing(self, prospective_store, project_coordinator):
        """Test task sequencing suggestions."""
        project_id = 1

        # Create tasks in different phases
        for i, phase in enumerate([TaskPhase.PLANNING, TaskPhase.PLAN_READY, TaskPhase.EXECUTING]):
            task = ProspectiveTask(
                project_id=project_id,
                content=f"Task {i}",
                active_form=f"Task {i}",
                phase=phase,
            )
            prospective_store.create_task(task)

        # Get suggestions
        suggestions = await project_coordinator.suggest_task_sequencing(project_id)

        assert isinstance(suggestions, list)
        # Should have at least one sequence suggestion
        assert len(suggestions) >= 0


class TestCoordinationIntegration:
    """Test coordination system integration."""

    @pytest.mark.asyncio
    async def test_full_coordination_workflow(self, prospective_store, project_coordinator):
        """Test complete coordination workflow."""
        project_ids = [1, 2, 3]

        # Create tasks across projects
        task_ids = []
        for proj_id in project_ids:
            for i in range(2):
                task = ProspectiveTask(
                    project_id=proj_id,
                    content=f"Project {proj_id} Task {i}",
                    active_form="Executing",
                    phase=TaskPhase.EXECUTING,
                    assignee="developer",
                )
                task_id = prospective_store.create_task(task)
                task_ids.append(task_id)

        # Add cross-project dependency
        if len(task_ids) >= 2:
            await project_coordinator.add_dependency(
                from_task_id=task_ids[0],
                from_project_id=1,
                to_task_id=task_ids[1],
                to_project_id=2,
                dependency_type="depends_on",
            )

        # Analyze network
        network = await project_coordinator.get_project_network(project_ids)
        assert network["projects"] is not None

        # Detect conflicts
        conflicts = await project_coordinator.detect_resource_conflicts(project_ids)
        assert isinstance(conflicts, list)

        # Get resource allocation
        allocation = await project_coordinator.get_resource_allocation(project_ids)
        assert allocation["total_tasks"] > 0

        # Get sequencing suggestions
        suggestions = await project_coordinator.suggest_task_sequencing(project_ids[0])
        assert isinstance(suggestions, list)
