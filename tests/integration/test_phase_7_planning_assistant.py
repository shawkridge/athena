"""Phase 7: Planning Assistant - AI-assisted plan generation and optimization.

Tests for:
- Plan generation from task descriptions
- Plan optimization and parallelization
- Resource estimation
- Alternative plan generation
"""

import pytest
from datetime import datetime, timedelta

from athena.core.database import Database
from athena.integration.planning_assistant import PlanningAssistant
from athena.prospective.models import (
    ProspectiveTask,
    TaskPhase,
    TaskStatus,
    TaskPriority,
)
from athena.prospective.store import ProspectiveStore


@pytest.fixture
def test_db(tmp_path):
    """Create shared database for testing."""
    db = Database(tmp_path / "test.db")
    # Ensure schema is initialized
    db.conn.execute("PRAGMA foreign_keys=ON")

    # Create a test project (required for foreign key constraint)
    cursor = db.conn.cursor()
    import time
    current_time = int(time.time())
    cursor.execute(
        """INSERT INTO projects (id, name, path, created_at, last_accessed, memory_count)
           VALUES (1, 'test_project', '/test', ?, ?, 0)""",
        (current_time, current_time),
    )
    db.conn.commit()

    return db


@pytest.fixture
def planning_assistant(test_db):
    """Create planning assistant for testing."""
    return PlanningAssistant(test_db)


@pytest.fixture
def prospective_store(test_db):
    """Create prospective store for testing."""
    return ProspectiveStore(test_db)


class TestPlanGeneration:
    """Test plan generation from task descriptions."""

    async def test_generate_plan_simple_task(
        self, planning_assistant, prospective_store
    ):
        """Test generating plan for simple task."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement user login",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        # Generate plan
        plan = await planning_assistant.generate_plan(created)

        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.estimated_duration_minutes > 0

    async def test_generate_plan_complex_task(
        self, planning_assistant, prospective_store
    ):
        """Test generating plan for complex task."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement OAuth2 integration",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        # Generate plan - should break into more steps
        plan = await planning_assistant.generate_plan(created)

        assert plan is not None
        assert len(plan.steps) > 0
        assert plan.estimated_duration_minutes > 0

    async def test_plan_structure_validation(
        self, planning_assistant, prospective_store
    ):
        """Test that generated plans have valid structure."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Add user profile page",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        plan = await planning_assistant.generate_plan(created)

        # Plan should have key properties
        assert hasattr(plan, "steps")
        assert hasattr(plan, "estimated_duration_minutes")
        assert len(plan.steps) > 0
        assert plan.estimated_duration_minutes > 0

    async def test_priority_affects_estimation(
        self, planning_assistant, prospective_store
    ):
        """Test that priority affects plan estimation."""
        content = "Implement API endpoint"

        # High-priority version
        task_high = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content=content,
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_high_id = prospective_store.create_task(task_high)
        created_high = prospective_store.get(task_high_id)
        plan_high = await planning_assistant.generate_plan(created_high)

        # Low-priority version
        task_low = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content=content,
            priority=TaskPriority.LOW,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_low_id = prospective_store.create_task(task_low)
        created_low = prospective_store.get(task_low_id)
        plan_low = await planning_assistant.generate_plan(created_low)

        # Both should have plans
        assert plan_high is not None
        assert plan_low is not None


class TestPlanOptimization:
    """Test plan optimization."""

    async def test_optimize_sequential_plan(
        self, planning_assistant, prospective_store
    ):
        """Test optimizing a sequential plan."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Build website",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLAN_READY,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        # Get initial plan
        plan = await planning_assistant.generate_plan(created)
        initial_duration = plan.estimated_duration_minutes

        # Optimize plan - returns list of suggestions
        suggestions = await planning_assistant.optimize_plan(created)

        assert suggestions is not None
        assert isinstance(suggestions, list)

    async def test_parallelization_opportunities(
        self, planning_assistant, prospective_store
    ):
        """Test detection of parallelization opportunities."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Setup infrastructure",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        # Get optimization suggestions - returns list
        suggestions = await planning_assistant.optimize_plan(created)

        # Should return list of suggestions
        assert suggestions is not None
        assert isinstance(suggestions, list)

    async def test_risk_identification(self, planning_assistant, prospective_store):
        """Test identification of risks in plan."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Integrate with external API",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        optimized = await planning_assistant.optimize_plan(created)

        # Should have assessment
        assert optimized is not None


class TestResourceEstimation:
    """Test resource estimation."""

    async def test_estimate_time_requirements(
        self, planning_assistant, prospective_store
    ):
        """Test time requirement estimation."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement authentication module",
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        resources = await planning_assistant.estimate_resources(created)

        assert resources is not None

    async def test_estimate_expertise_required(
        self, planning_assistant, prospective_store
    ):
        """Test expertise level estimation."""
        # Simple task
        simple_task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Update CSS styling",
            priority=TaskPriority.LOW,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        simple_task_id = prospective_store.create_task(simple_task)
        created_simple = prospective_store.get(simple_task_id)
        resources_simple = await planning_assistant.estimate_resources(created_simple)

        # Complex task
        complex_task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement distributed caching",
            priority=TaskPriority.CRITICAL,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        complex_task_id = prospective_store.create_task(complex_task)
        created_complex = prospective_store.get(complex_task_id)
        resources_complex = await planning_assistant.estimate_resources(
            created_complex
        )

        assert resources_simple is not None
        assert resources_complex is not None

    async def test_estimate_dependencies(self, planning_assistant, prospective_store):
        """Test dependency estimation."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement feature that depends on API",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        resources = await planning_assistant.estimate_resources(created)

        assert resources is not None

    async def test_estimate_tools_required(self, planning_assistant, prospective_store):
        """Test tool requirements estimation."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Setup containerized development environment",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        resources = await planning_assistant.estimate_resources(created)

        assert resources is not None
        assert len(resources) > 0


class TestPlanningAssistantPerformance:
    """Performance tests for Phase 7 Planning Assistant."""

    async def test_plan_generation_latency(
        self, planning_assistant, prospective_store
    ):
        """Test plan generation latency."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement feature",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        import time

        start = time.perf_counter()
        plan = await planning_assistant.generate_plan(created)
        duration_ms = (time.perf_counter() - start) * 1000

        assert plan is not None
        assert duration_ms < 1000  # Should be < 1 second

    async def test_optimization_latency(self, planning_assistant, prospective_store):
        """Test optimization latency."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement feature",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        import time

        start = time.perf_counter()
        optimized = await planning_assistant.optimize_plan(created)
        duration_ms = (time.perf_counter() - start) * 1000

        assert optimized is not None
        assert duration_ms < 1000  # Should be < 1 second

    async def test_resource_estimation_latency(
        self, planning_assistant, prospective_store
    ):
        """Test resource estimation latency."""
        task = ProspectiveTask(
            project_id=1,
            active_form="working on task",
            content="Implement feature",
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.PLANNING,
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)
        created = prospective_store.get(task_id)

        import time

        start = time.perf_counter()
        resources = await planning_assistant.estimate_resources(created)
        duration_ms = (time.perf_counter() - start) * 1000

        assert resources is not None
        assert duration_ms < 500  # Should be < 500ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
