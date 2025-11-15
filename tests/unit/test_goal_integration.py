"""
Tests for goal decomposition and prospective memory integration (Phase 4 Extension).

Tests the integration of:
- GoalDecompositionService (decomposes goals)
- GoalToProspectiveConverter (saves to prospective memory)
- MCP handlers for decompose_and_store_goal
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from athena.planning.models import Goal, TaskNode, DecomposedGoal, DecompositionResult
from athena.planning.goal_decomposition import GoalDecompositionService
from athena.planning.goal_integration import (
    GoalToProspectiveConverter,
    GoalIntegrationResult,
)
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPhase, TaskPriority
from athena.mcp.handlers_goal_decomposition import GoalDecompositionHandlersMixin


class TestGoalToProspectiveConverter:
    """Tests for GoalToProspectiveConverter."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.get_cursor = Mock()
        return db

    @pytest.fixture
    def converter(self, mock_db):
        """Create a converter with mocked dependencies."""
        with patch("athena.planning.goal_integration.ProspectiveStore"):
            with patch("athena.planning.goal_integration.DependencyManager"):
                converter = GoalToProspectiveConverter(mock_db)
                # Mock the stores
                converter.prospective_store = AsyncMock()
                converter.dependency_manager = AsyncMock()
                return converter

    @pytest.fixture
    def sample_goal(self):
        """Create a sample goal."""
        return Goal(
            id="goal_1",
            title="Build notification system",
            description="Create a real-time notification system",
            context="Web application",
        )

    @pytest.fixture
    def sample_decomposed_goal(self, sample_goal):
        """Create a sample decomposed goal."""
        task1 = TaskNode(
            id="task_1",
            title="Design architecture",
            description="Design the system architecture",
            estimated_effort_minutes=120,
            estimated_complexity=7,
            estimated_priority=8,
            tags=["design"],
        )

        task2 = TaskNode(
            id="task_2",
            title="Implementation",
            description="Implement the system",
            estimated_effort_minutes=480,
            estimated_complexity=8,
            estimated_priority=9,
            tags=["coding"],
            parent_id="task_1",
        )

        return DecomposedGoal(
            goal_id=sample_goal.id,
            goal_title=sample_goal.title,
            root_tasks=[task1],
            all_tasks={"task_1": task1, "task_2": task2},
            total_estimated_effort=600,
            avg_complexity=7.5,
            num_tasks=2,
            max_depth=2,
            critical_path_length=480,
        )

    @pytest.mark.asyncio
    async def test_integrate_decomposed_goal_success(
        self, converter, sample_goal, sample_decomposed_goal
    ):
        """Test successful integration of decomposed goal."""
        # Mock the create method to return tasks with IDs
        async def mock_create(task):
            task.id = len([1, 2])  # Simulate ID assignment
            return task

        converter.prospective_store.create = mock_create

        result = await converter.integrate_decomposed_goal(
            sample_decomposed_goal,
            sample_goal,
            project_id=1,
            assignee="claude",
        )

        assert result.success is True
        assert result.goal_id == sample_goal.id
        assert len(result.created_task_ids) > 0

    @pytest.mark.asyncio
    async def test_priority_inference(self, converter):
        """Test priority inference from decomposition metrics."""
        # Critical task
        priority = converter._infer_priority(complexity=9, original_priority=9, is_critical=True)
        assert priority == TaskPriority.CRITICAL

        # High priority task
        priority = converter._infer_priority(complexity=8, original_priority=7, is_critical=False)
        assert priority == TaskPriority.HIGH

        # Medium priority task
        priority = converter._infer_priority(complexity=5, original_priority=5, is_critical=False)
        assert priority == TaskPriority.MEDIUM

        # Low priority task
        priority = converter._infer_priority(complexity=2, original_priority=2, is_critical=False)
        assert priority == TaskPriority.LOW

    def test_plan_creation_from_task_node(self, converter, sample_decomposed_goal):
        """Test plan creation from task node."""
        task = sample_decomposed_goal.all_tasks["task_1"]
        plan = converter._create_plan_from_task_node(task, sample_decomposed_goal)

        assert plan is not None
        assert plan.estimated_duration_minutes == task.estimated_effort_minutes
        assert plan.validated is False

    def test_due_date_calculation(self, converter):
        """Test due date calculation from effort estimate."""
        # 8 hours = 480 minutes = 1 day
        due_date = converter._calculate_due_date(480)
        assert due_date is not None
        assert due_date.date() == datetime.now().date() + pytest.approx(
            iter([1]), abs=1  # Approximate 1 day offset
        )

        # No effort = no due date
        due_date = converter._calculate_due_date(0)
        assert due_date is None

    @pytest.mark.asyncio
    async def test_integration_validation(
        self, converter, sample_goal, sample_decomposed_goal
    ):
        """Test integration validation warnings."""
        warnings = converter._validate_integration(
            sample_decomposed_goal, created_task_ids=[1, 2]
        )

        # Should have no warnings for this case (all tasks created)
        assert isinstance(warnings, list)

        # Test with missing tasks
        warnings = converter._validate_integration(
            sample_decomposed_goal, created_task_ids=[1]  # Only 1 instead of 2
        )
        assert any("Only created" in w for w in warnings)


class TestGoalDecompositionServiceIntegration:
    """Tests for GoalDecompositionService with prospective memory integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def service_with_db(self, mock_db):
        """Create a service with database."""
        service = GoalDecompositionService(db=mock_db)
        # Mock the converter
        service.converter = AsyncMock()
        return service

    @pytest.fixture
    def sample_goal(self):
        """Create a sample goal."""
        return Goal(
            id="goal_1",
            title="Build API",
            description="Create a REST API",
        )

    @pytest.mark.asyncio
    async def test_decompose_and_store_goal_without_db(self):
        """Test decompose_and_store_goal fails without DB."""
        service = GoalDecompositionService()  # No DB
        goal = Goal(
            id="goal_1",
            title="Test",
            description="Test goal",
        )

        result = await service.decompose_and_store_goal(goal)

        assert result["success"] is False
        assert "not initialized" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_decompose_and_store_goal_success(self, service_with_db, sample_goal):
        """Test successful decomposition and storage."""
        # Mock decompose_goal
        mock_decomp_result = DecompositionResult(
            success=True,
            decomposed_goal=DecomposedGoal(
                goal_id=sample_goal.id,
                goal_title=sample_goal.title,
                total_estimated_effort=100,
                num_tasks=2,
                avg_complexity=5.0,
                critical_path_length=100,
            ),
        )
        service_with_db.decompose_goal = Mock(return_value=mock_decomp_result)

        # Mock converter result
        service_with_db.converter.integrate_decomposed_goal = AsyncMock(
            return_value=GoalIntegrationResult(
                success=True,
                goal_id=sample_goal.id,
                created_task_ids=[1, 2],
                task_mapping={"task_1": 1, "task_2": 2},
                dependencies_created=1,
            )
        )

        result = await service_with_db.decompose_and_store_goal(sample_goal)

        assert result["success"] is True
        assert len(result["task_ids"]) == 2
        assert result["decomposition"]["num_tasks"] == 2


class TestGoalDecompositionMCPHandlers:
    """Tests for MCP handlers with decompose_and_store_goal."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def handlers(self, mock_db):
        """Create handlers with mock database."""
        handlers = GoalDecompositionHandlersMixin(db=mock_db)
        # Mock the service
        handlers.decomposition_service = Mock()
        handlers.decomposition_service.decompose_and_store_goal = AsyncMock()
        return handlers

    def test_tool_index_includes_decompose_and_store(self, handlers):
        """Test that tool index includes decompose_and_store_goal."""
        index = handlers.decomposition_tools_index

        assert "decompose_and_store_goal" in index
        assert index["decompose_and_store_goal"]["requires_database"] is True

    def test_schema_for_decompose_and_store(self, handlers):
        """Test schema for decompose_and_store_goal."""
        schema = handlers.get_tool_schema("decompose_and_store_goal")

        assert schema["name"] == "decompose_and_store_goal"
        assert "goal_id" in schema["inputSchema"]["properties"]
        assert "title" in schema["inputSchema"]["properties"]
        assert "assignee" in schema["inputSchema"]["properties"]

    @pytest.mark.asyncio
    async def test_decompose_and_store_goal_handler(self, handlers):
        """Test decompose_and_store_goal MCP handler."""
        mock_result = {
            "success": True,
            "goal_id": "goal_1",
            "task_ids": [1, 2],
            "dependencies_created": 1,
        }
        handlers.decomposition_service.decompose_and_store_goal = AsyncMock(
            return_value=mock_result
        )

        result = await handlers.decompose_and_store_goal(
            goal_id="goal_1",
            title="Build API",
            description="Create REST API",
        )

        assert result["success"] is True
        assert "goal_id" in result
        assert "num_tasks_created" in result["summary"]

    @pytest.mark.asyncio
    async def test_decompose_and_store_goal_without_db(self):
        """Test that decompose_and_store_goal fails without database."""
        handlers = GoalDecompositionHandlersMixin()  # No DB

        result = await handlers.decompose_and_store_goal(
            goal_id="goal_1",
            title="Build API",
            description="Create REST API",
        )

        assert result["success"] is False
        assert "not initialized" in result["error"].lower()


class TestIntegrationEndToEnd:
    """End-to-end integration tests."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_full_goal_decomposition_workflow(self, mock_db):
        """Test full workflow from goal to prospective tasks."""
        # This is a high-level integration test
        goal = Goal(
            id="goal_1",
            title="Build real-time notifications",
            description="Create a system for real-time notifications",
        )

        service = GoalDecompositionService(db=mock_db)

        # Decompose goal (without storage, as converter would fail without real DB)
        result = service.decompose_goal(goal)

        assert result.success is True
        assert result.decomposed_goal is not None
        assert result.decomposed_goal.num_tasks > 0
        assert result.decomposed_goal.total_estimated_effort > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
