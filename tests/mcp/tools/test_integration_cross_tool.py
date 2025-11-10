"""Integration tests for cross-tool interactions."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from athena.mcp.tools.memory_tools import RecallTool, RememberTool, OptimizeTool
from athena.mcp.tools.system_tools import SystemHealthCheckTool, HealthReportTool
from athena.mcp.tools.retrieval_tools import SmartRetrieveTool
from athena.mcp.tools.planning_tools import DecomposeTool, ValidatePlanTool, OptimizePlanTool
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_memory_store():
    """Create mock memory store."""
    store = Mock()
    store.recall_with_reranking = Mock(return_value=[])
    store.store_memory = Mock(return_value=1)
    store.optimize = Mock(return_value={
        "before_count": 100,
        "after_count": 80,
        "pruned": 20,
        "dry_run": False,
        "avg_score_before": 0.6,
        "avg_score_after": 0.75
    })
    return store


@pytest.fixture
def mock_project_manager():
    """Create mock project manager."""
    manager = Mock()
    mock_project = Mock()
    mock_project.id = 1
    manager.require_project = Mock(return_value=mock_project)
    return manager


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server."""
    server = Mock()
    server._health_checker = AsyncMock()
    server._health_checker.check = AsyncMock(return_value={
        "status": "healthy",
        "issues": []
    })
    server._health_checker.generate_report = AsyncMock(return_value={
        "summary": "System is healthy",
        "metrics": {}
    })
    return server


@pytest.fixture
def mock_planning_store():
    """Create mock planning store."""
    store = Mock()
    store.store_plan = Mock(return_value=1)
    store.get_plan = Mock(return_value={
        "id": 1,
        "title": "Test Plan",
        "steps": []
    })
    return store


@pytest.fixture
def mock_plan_validator():
    """Create mock plan validator."""
    validator = Mock()
    validator.validate = Mock(return_value={
        "valid": True,
        "issues": [],
        "score": 0.95
    })
    return validator


# Tool fixtures
@pytest.fixture
def recall_tool(mock_memory_store, mock_project_manager):
    return RecallTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def remember_tool(mock_memory_store, mock_project_manager):
    return RememberTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def optimize_memory_tool(mock_memory_store, mock_project_manager):
    return OptimizeTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def health_check_tool(mock_mcp_server):
    return SystemHealthCheckTool(mock_mcp_server)


@pytest.fixture
def health_report_tool(mock_mcp_server):
    return HealthReportTool(mock_mcp_server)


@pytest.fixture
def smart_retrieve_tool(mock_memory_store, mock_project_manager):
    return SmartRetrieveTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def decompose_tool(mock_planning_store):
    return DecomposeTool(mock_planning_store)


@pytest.fixture
def validate_plan_tool(mock_plan_validator):
    return ValidatePlanTool(mock_plan_validator)


@pytest.fixture
def optimize_plan_tool(mock_planning_store):
    return OptimizePlanTool(mock_planning_store)


class TestMemoryRetrievalSystemIntegration:
    """Test memory and retrieval system integration."""

    @pytest.mark.asyncio
    async def test_remember_then_smart_retrieve(self, remember_tool, smart_retrieve_tool, mock_memory_store):
        """Test remembering content then smart retrieval."""
        # Remember
        mock_memory_store.store_memory.return_value = 42
        remember_result = await remember_tool.execute(
            content="Machine learning fundamentals",
            tags=["ml", "learning"]
        )
        assert remember_result.status == ToolStatus.SUCCESS

        # Smart retrieve
        mock_memory_store.recall_with_reranking.return_value = []
        retrieve_result = await smart_retrieve_tool.execute(
            query="machine learning concepts",
            strategy="hyde"
        )
        assert retrieve_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_recall_optimize_memory_workflow(self, recall_tool, optimize_memory_tool, mock_memory_store):
        """Test recall and optimize memory together."""
        # Recall
        mock_memory_store.recall_with_reranking.return_value = []
        recall_result = await recall_tool.execute(query="important data")
        assert recall_result.status == ToolStatus.SUCCESS

        # Optimize memory
        optimize_result = await optimize_memory_tool.execute()
        assert optimize_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_smart_retrieve_with_system_health_check(self, smart_retrieve_tool, health_check_tool, mock_memory_store, mock_mcp_server):
        """Test smart retrieve while monitoring system health."""
        # Check system health first
        health_result = await health_check_tool.execute()
        assert health_result.status == ToolStatus.SUCCESS
        assert health_result.data["status"] in ["healthy", "unknown", "degraded"]

        # Perform retrieval
        mock_memory_store.recall_with_reranking.return_value = []
        retrieve_result = await smart_retrieve_tool.execute(query="test")
        assert retrieve_result.status == ToolStatus.SUCCESS


class TestPlanningMemoryIntegration:
    """Test planning and memory system integration."""

    @pytest.mark.asyncio
    async def test_decompose_task_remember_plan(self, decompose_tool, remember_tool, mock_planning_store, mock_memory_store):
        """Test decomposing task and remembering plan."""
        # Decompose
        decompose_result = await decompose_tool.execute(task="Build system architecture")
        assert decompose_result.status == ToolStatus.SUCCESS
        plan_id = decompose_result.data["plan_id"]

        # Remember plan
        mock_memory_store.store_memory.return_value = plan_id
        remember_result = await remember_tool.execute(
            content=f"Plan ID: {plan_id}",
            memory_type="procedural",
            tags=["plan", "architecture"]
        )
        assert remember_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_recall_plan_then_validate(self, recall_tool, validate_plan_tool, mock_memory_store, mock_plan_validator):
        """Test recalling plan information then validating."""
        # Recall plan
        mock_result = Mock()
        mock_result.similarity = 0.95
        mock_result.memory = Mock()
        mock_result.memory.id = 1
        mock_result.memory.content = "Plan details"
        mock_result.memory.memory_type = "procedural"
        mock_result.memory.tags = ["plan"]
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        recall_result = await recall_tool.execute(query="plan")
        assert recall_result.status == ToolStatus.SUCCESS

        # Validate plan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.90
        }
        validate_result = await validate_plan_tool.execute(plan_id=1)
        assert validate_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_optimize_plan_and_memory_together(self, optimize_plan_tool, optimize_memory_tool, mock_planning_store, mock_memory_store):
        """Test optimizing both plan and memory simultaneously."""
        # Optimize plan
        plan_opt = await optimize_plan_tool.execute(plan_id=1, objective="time")
        assert plan_opt.status == ToolStatus.SUCCESS

        # Optimize memory
        mem_opt = await optimize_memory_tool.execute()
        assert mem_opt.status == ToolStatus.SUCCESS


class TestSystemHealthAndRetrieval:
    """Test system health monitoring with retrieval operations."""

    @pytest.mark.asyncio
    async def test_health_check_during_retrieval(self, health_check_tool, smart_retrieve_tool, mock_mcp_server, mock_memory_store):
        """Test health check while performing retrieval."""
        import asyncio

        mock_memory_store.recall_with_reranking.return_value = []

        # Run both concurrently
        health_task = health_check_tool.execute()
        retrieve_task = smart_retrieve_tool.execute(query="concurrent test")

        health_result, retrieve_result = await asyncio.gather(health_task, retrieve_task)

        assert health_result.status == ToolStatus.SUCCESS
        assert retrieve_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_health_report_impacts_operation_safety(self, health_report_tool, recall_tool, mock_mcp_server, mock_memory_store):
        """Test health report influences operation decisions."""
        # Get health report
        report_result = await health_report_tool.execute(include_metrics=True)
        assert report_result.status == ToolStatus.SUCCESS

        # Based on health, perform recall
        mock_memory_store.recall_with_reranking.return_value = []
        recall_result = await recall_tool.execute(query="safe query")
        assert recall_result.status == ToolStatus.SUCCESS


class TestFullSystemWorkflow:
    """Test complete system workflows across multiple tools."""

    @pytest.mark.asyncio
    async def test_full_workflow_remember_decompose_validate(
        self,
        remember_tool,
        decompose_tool,
        validate_plan_tool,
        mock_memory_store,
        mock_planning_store,
        mock_plan_validator
    ):
        """Test complete workflow: remember → decompose → validate."""
        # Remember task description
        mock_memory_store.store_memory.return_value = 1
        remember_result = await remember_tool.execute(
            content="Implement REST API with authentication",
            tags=["task", "api"]
        )
        assert remember_result.status == ToolStatus.SUCCESS

        # Decompose task
        decompose_result = await decompose_tool.execute(
            task="Implement REST API with authentication"
        )
        assert decompose_result.status == ToolStatus.SUCCESS
        plan_id = decompose_result.data["plan_id"]

        # Validate decomposed plan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.92
        }
        validate_result = await validate_plan_tool.execute(plan_id=plan_id)
        assert validate_result.status == ToolStatus.SUCCESS
        assert validate_result.data["valid"] is True

    @pytest.mark.asyncio
    async def test_end_to_end_planning_with_health_checks(
        self,
        decompose_tool,
        validate_plan_tool,
        optimize_plan_tool,
        health_check_tool,
        mock_planning_store,
        mock_plan_validator,
        mock_mcp_server
    ):
        """Test end-to-end planning with health monitoring."""
        # Initial health check
        health1 = await health_check_tool.execute()
        assert health1.status == ToolStatus.SUCCESS

        # Decompose
        decompose_result = await decompose_tool.execute(task="Complex project")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Check health again
        health2 = await health_check_tool.execute()
        assert health2.status == ToolStatus.SUCCESS

        # Validate plan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.88
        }
        validate_result = await validate_plan_tool.execute(plan_id=1)
        assert validate_result.status == ToolStatus.SUCCESS

        # Optimize
        optimize_result = await optimize_plan_tool.execute(plan_id=1, objective="resources")
        assert optimize_result.status == ToolStatus.SUCCESS

        # Final health check
        health3 = await health_check_tool.execute()
        assert health3.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_multi_tool_error_resilience(
        self,
        remember_tool,
        recall_tool,
        optimize_memory_tool,
        decompose_tool,
        health_check_tool,
        mock_memory_store,
        mock_planning_store,
        mock_mcp_server
    ):
        """Test system resilience with multiple tool interactions."""
        # Operation 1: Remember (succeeds)
        mock_memory_store.store_memory.return_value = 1
        result1 = await remember_tool.execute(content="Test content")
        assert result1.status == ToolStatus.SUCCESS

        # Operation 2: Recall (might fail, but system continues)
        mock_memory_store.recall_with_reranking.return_value = []
        result2 = await recall_tool.execute(query="test")
        assert result2.status == ToolStatus.SUCCESS

        # Operation 3: Decompose (succeeds)
        result3 = await decompose_tool.execute(task="Task")
        assert result3.status == ToolStatus.SUCCESS

        # Operation 4: Optimize memory (succeeds)
        result4 = await optimize_memory_tool.execute()
        assert result4.status == ToolStatus.SUCCESS

        # Operation 5: Health check (succeeds)
        result5 = await health_check_tool.execute()
        assert result5.status == ToolStatus.SUCCESS

        # All operations completed despite potential failures
        assert all([
            result1.status == ToolStatus.SUCCESS,
            result2.status == ToolStatus.SUCCESS,
            result3.status == ToolStatus.SUCCESS,
            result4.status == ToolStatus.SUCCESS,
            result5.status == ToolStatus.SUCCESS,
        ])
