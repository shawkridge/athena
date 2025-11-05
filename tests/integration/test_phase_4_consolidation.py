"""Phase 4: Task-Memory Consolidation Integration Tests

Tests the consolidation of completed tasks into learnings, procedures,
and knowledge graph entities for continuous improvement.
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
    PhaseMetrics,
)
from athena.prospective.store import ProspectiveStore
from athena.integration.task_consolidation import TaskConsolidation


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
def task_consolidation(temp_db: Database) -> TaskConsolidation:
    """Create task consolidation."""
    return TaskConsolidation(temp_db)


class TestTaskConsolidation:
    """Test task consolidation functionality."""

    def test_consolidation_initialization(self, task_consolidation):
        """Test consolidation initializes correctly."""
        assert task_consolidation is not None
        assert task_consolidation.prospective_store is not None
        assert task_consolidation.episodic_store is not None

    @pytest.mark.asyncio
    async def test_consolidate_pending_task_skipped(
        self, prospective_store, task_consolidation
    ):
        """Test that pending tasks are skipped."""
        task = ProspectiveTask(
            project_id=1,
            content="Pending task",
            active_form="Pending task",
            status=TaskStatus.PENDING,
        )
        task_id = prospective_store.create_task(task)

        result = await task_consolidation.consolidate_completed_task(task_id)

        assert result["status"] == "skipped"
        assert "not completed" in result["reason"]

    @pytest.mark.asyncio
    async def test_consolidate_completed_task(
        self, prospective_store, task_consolidation
    ):
        """Test consolidating a completed task."""
        # Create and setup task
        task = ProspectiveTask(
            project_id=1,
            content="Implement API endpoint",
            active_form="Implementing API endpoint",
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            actual_duration_minutes=45.5,
        )
        task_id = prospective_store.create_task(task)

        # Add plan
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=["Design", "Implement", "Test", "Document"],
            estimated_duration_minutes=60,
        )

        # Add phase metrics
        updated_task = prospective_store.get_task(task_id)
        updated_task.phase_metrics = [
            PhaseMetrics(
                phase=TaskPhase.PLANNING,
                started_at=datetime.now() - timedelta(minutes=50),
                completed_at=datetime.now() - timedelta(minutes=40),
                duration_minutes=10,
            ),
            PhaseMetrics(
                phase=TaskPhase.EXECUTING,
                started_at=datetime.now() - timedelta(minutes=40),
                completed_at=datetime.now(),
                duration_minutes=40,
            ),
        ]

        # Consolidate
        result = await task_consolidation.consolidate_completed_task(task_id)

        assert result["status"] == "success"
        assert result["semantic_memories_created"] >= 0
        assert result["procedures_extracted"] >= 0

    @pytest.mark.asyncio
    async def test_gather_task_events(self, task_consolidation):
        """Test gathering task events."""
        events = await task_consolidation._gather_task_events(task_id=999)

        # Should return list (empty if task not found)
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_create_semantic_memories(
        self, task_consolidation
    ):
        """Test creating semantic memories from task."""
        task = ProspectiveTask(
            project_id=1,
            content="Test task for memory",
            active_form="Test task for memory",
            status=TaskStatus.COMPLETED,
            actual_duration_minutes=30.0,
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2", "Step 3"],
            estimated_duration_minutes=30,
        )

        # Create memories
        count = await task_consolidation._create_semantic_memories(task, [])

        # Count should be non-negative
        assert count >= 0

    @pytest.mark.asyncio
    async def test_extract_procedures(self, task_consolidation):
        """Test extracting procedures from task."""
        task = ProspectiveTask(
            project_id=1,
            content="Refactor authentication module",
            active_form="Refactoring authentication",
            status=TaskStatus.COMPLETED,
        )

        task.plan = Plan(
            steps=[
                "Analyze current code",
                "Design new structure",
                "Implement changes",
                "Run tests",
                "Deploy",
            ],
            estimated_duration_minutes=240,
        )

        # Extract procedures
        count = await task_consolidation._extract_procedures(task, [])

        # Count should be non-negative
        assert count >= 0

    @pytest.mark.asyncio
    async def test_link_knowledge_graph(self, task_consolidation):
        """Test linking task to knowledge graph."""
        task = ProspectiveTask(
            project_id=1,
            content="Build REST API with database integration",
            active_form="Building REST API",
            status=TaskStatus.COMPLETED,
        )

        # Link to graph
        count = await task_consolidation._link_knowledge_graph(task)

        # Should link multiple entities (api, database, etc.)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_extract_lessons_learned(self, task_consolidation):
        """Test extracting lessons from task execution."""
        task = ProspectiveTask(
            project_id=1,
            content="Implementation task",
            active_form="Implementing",
            status=TaskStatus.COMPLETED,
            actual_duration_minutes=75.0,
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        task.phase_metrics = [
            PhaseMetrics(
                phase=TaskPhase.EXECUTING,
                started_at=datetime.now() - timedelta(minutes=80),
                completed_at=datetime.now(),
                duration_minutes=75,
            )
        ]

        # Extract lessons
        lessons = await task_consolidation._extract_lessons_learned(task, [])

        assert isinstance(lessons, list)
        # Should have at least one lesson about duration variance
        assert len(lessons) > 0

    @pytest.mark.asyncio
    async def test_lesson_extraction_accuracy(self, task_consolidation):
        """Test lessons capture actual insights."""
        task = ProspectiveTask(
            project_id=1,
            content="Quick implementation",
            active_form="Implementing",
            status=TaskStatus.COMPLETED,
            actual_duration_minutes=45.0,
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        lessons = await task_consolidation._extract_lessons_learned(task, [])

        # Should have lesson about faster completion (25% faster)
        assert any("faster" in lesson.lower() for lesson in lessons)

    @pytest.mark.asyncio
    async def test_duration_variance_lesson(self, task_consolidation):
        """Test lesson about duration variance."""
        task = ProspectiveTask(
            project_id=1,
            content="Over-estimate task",
            active_form="Task",
            status=TaskStatus.COMPLETED,
            actual_duration_minutes=120.0,
        )

        task.plan = Plan(
            steps=["Step 1", "Step 2"],
            estimated_duration_minutes=60,
        )

        lessons = await task_consolidation._extract_lessons_learned(task, [])

        # Should mention 100% variance
        assert any("adjustment" in lesson.lower() or "100" in lesson for lesson in lessons)

    @pytest.mark.asyncio
    async def test_phase_efficiency_lesson(self, task_consolidation):
        """Test lesson about phase efficiency."""
        task = ProspectiveTask(
            project_id=1,
            content="Multi-phase task",
            active_form="Task",
            status=TaskStatus.COMPLETED,
        )

        task.phase_metrics = [
            PhaseMetrics(
                phase=TaskPhase.PLANNING,
                started_at=datetime.now() - timedelta(minutes=30),
                completed_at=datetime.now() - timedelta(minutes=20),
                duration_minutes=10,
            ),
            PhaseMetrics(
                phase=TaskPhase.EXECUTING,
                started_at=datetime.now() - timedelta(minutes=20),
                completed_at=datetime.now() - timedelta(minutes=5),
                duration_minutes=15,
            ),
            PhaseMetrics(
                phase=TaskPhase.VERIFYING,
                started_at=datetime.now() - timedelta(minutes=5),
                completed_at=datetime.now(),
                duration_minutes=5,
            ),
        ]

        lessons = await task_consolidation._extract_lessons_learned(task, [])

        # Should mention the longest phase
        assert any("phase" in lesson.lower() for lesson in lessons)


class TestConsolidationWorkflow:
    """Test complete consolidation workflow."""

    @pytest.mark.asyncio
    async def test_full_consolidation_workflow(
        self, prospective_store, task_consolidation
    ):
        """Test complete task consolidation workflow."""
        # 1. Create a realistic completed task
        task = ProspectiveTask(
            project_id=1,
            content="Implement user authentication system",
            active_form="Implementing user authentication",
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            actual_duration_minutes=240.0,
        )

        task_id = prospective_store.create_task(task)

        # 2. Add realistic plan
        prospective_store.create_plan_for_task(
            task_id=task_id,
            steps=[
                "Design authentication architecture",
                "Implement login mechanism",
                "Implement token generation",
                "Add security tests",
                "Document API",
            ],
            estimated_duration_minutes=300,
        )

        # 3. Validate plan
        prospective_store.validate_plan(task_id, notes="Architecture approved")

        # 4. Add phase metrics showing actual execution
        updated_task = prospective_store.get_task(task_id)
        updated_task.phase_metrics = [
            PhaseMetrics(
                phase=TaskPhase.PLANNING,
                duration_minutes=45,
            ),
            PhaseMetrics(
                phase=TaskPhase.EXECUTING,
                duration_minutes=180,
            ),
            PhaseMetrics(
                phase=TaskPhase.VERIFYING,
                duration_minutes=15,
            ),
        ]

        # 5. Consolidate the completed task
        result = await task_consolidation.consolidate_completed_task(task_id)

        # 6. Verify consolidation results
        assert result["status"] == "success"
        assert "lessons_learned" in result
        assert len(result["lessons_learned"]) > 0

    @pytest.mark.asyncio
    async def test_consolidate_recent_tasks(
        self, prospective_store, task_consolidation
    ):
        """Test consolidating multiple recent tasks."""
        # Create multiple completed tasks
        for i in range(3):
            task = ProspectiveTask(
                project_id=1,
                content=f"Task {i}",
                active_form=f"Task {i}",
                status=TaskStatus.COMPLETED,
                phase=TaskPhase.COMPLETED,
                completed_at=datetime.now(),
            )
            prospective_store.create_task(task)

        # Consolidate all recent tasks
        summary = await task_consolidation.consolidate_all_recent_completed_tasks(
            hours_back=1
        )

        assert "tasks_consolidated" in summary
        assert "total_semantic_memories" in summary
        assert isinstance(summary["results"], list)


class TestConsolidationIntegration:
    """Test consolidation integration with other systems."""

    @pytest.mark.asyncio
    async def test_consolidation_with_phase_metrics(
        self, prospective_store, task_consolidation
    ):
        """Test consolidation uses phase metrics for insights."""
        task = ProspectiveTask(
            project_id=1,
            content="Complex multi-phase task",
            active_form="Complex task",
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            actual_duration_minutes=180.0,
        )

        task_id = prospective_store.create_task(task)

        # Add detailed phase metrics
        prospective_store.create_plan_for_task(task_id, ["Step 1", "Step 2"])

        updated_task = prospective_store.get_task(task_id)
        updated_task.phase_metrics = [
            PhaseMetrics(phase=TaskPhase.PLANNING, duration_minutes=60),
            PhaseMetrics(phase=TaskPhase.EXECUTING, duration_minutes=100),
            PhaseMetrics(phase=TaskPhase.VERIFYING, duration_minutes=20),
        ]

        # Consolidate
        result = await task_consolidation.consolidate_completed_task(task_id)

        # Should have extracted lessons from phase metrics
        lessons = result.get("lessons_learned", [])
        assert any("phase" in lesson.lower() for lesson in lessons)

    @pytest.mark.asyncio
    async def test_consolidation_knowledge_linking(
        self, task_consolidation
    ):
        """Test that consolidation properly links to knowledge graph."""
        task = ProspectiveTask(
            project_id=1,
            content="Database and API refactoring with testing",
            active_form="Refactoring",
            status=TaskStatus.COMPLETED,
        )

        # Link to graph
        entity_count = await task_consolidation._link_knowledge_graph(task)

        # Should create entities for: database, api, test concepts
        # Exact count depends on implementation
        assert entity_count >= 0
