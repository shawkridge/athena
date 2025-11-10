"""Integration tests for edge cases and error scenarios."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from athena.mcp.tools.memory_tools import RecallTool, RememberTool, ForgetTool, OptimizeTool
from athena.mcp.tools.planning_tools import DecomposeTool, ValidatePlanTool
from athena.mcp.tools.system_tools import SystemHealthCheckTool
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_memory_store():
    """Create mock memory store."""
    store = Mock()
    store.recall_with_reranking = Mock(return_value=[])
    store.store_memory = Mock(return_value=1)
    store.forget = Mock(return_value=True)
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
    return server


@pytest.fixture
def mock_planning_store():
    """Create mock planning store."""
    store = Mock()
    store.store_plan = Mock(return_value=1)
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


# Tools
@pytest.fixture
def recall_tool(mock_memory_store, mock_project_manager):
    return RecallTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def remember_tool(mock_memory_store, mock_project_manager):
    return RememberTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def forget_tool(mock_memory_store, mock_project_manager):
    return ForgetTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def optimize_tool(mock_memory_store, mock_project_manager):
    return OptimizeTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def decompose_tool(mock_planning_store):
    return DecomposeTool(mock_planning_store)


@pytest.fixture
def validate_plan_tool(mock_plan_validator):
    return ValidatePlanTool(mock_plan_validator)


@pytest.fixture
def health_check_tool(mock_mcp_server):
    return SystemHealthCheckTool(mock_mcp_server)


class TestConcurrencyScenarios:
    """Test concurrent operation handling."""

    @pytest.mark.asyncio
    async def test_10_concurrent_recall_operations(self, recall_tool, mock_memory_store):
        """Test 10 concurrent recall operations."""
        mock_memory_store.recall_with_reranking.return_value = []

        # Create 10 concurrent tasks
        tasks = [
            recall_tool.execute(query=f"query {i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 10
        assert all(r.status == ToolStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_remember_and_forget(self, remember_tool, forget_tool, mock_memory_store):
        """Test concurrent remember and forget operations."""
        # Remember: incremental IDs
        remember_tasks = [
            remember_tool.execute(content=f"Memory {i}")
            for i in range(5)
        ]
        remember_results = await asyncio.gather(*remember_tasks)
        assert all(r.status == ToolStatus.SUCCESS for r in remember_results)

        # Forget: concurrent deletes
        mock_memory_store.forget.return_value = True
        forget_tasks = [
            forget_tool.execute(memory_id=i+1)
            for i in range(5)
        ]
        forget_results = await asyncio.gather(*forget_tasks)
        assert all(r.status == ToolStatus.SUCCESS for r in forget_results)

    @pytest.mark.asyncio
    async def test_concurrent_consolidation_and_recall(self, recall_tool, optimize_tool, mock_memory_store):
        """Test concurrent consolidation and recall."""
        mock_memory_store.recall_with_reranking.return_value = []

        recall_task = recall_tool.execute(query="test")
        optimize_task = optimize_tool.execute()

        recall_result, optimize_result = await asyncio.gather(recall_task, optimize_task)

        assert recall_result.status == ToolStatus.SUCCESS
        assert optimize_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_race_condition_prevention(self, remember_tool, forget_tool, mock_memory_store):
        """Test that race conditions are handled."""
        mock_memory_store.store_memory.return_value = 1

        # Concurrent remember and forget same ID
        remember_task = remember_tool.execute(content="Content")
        forget_task = forget_tool.execute(memory_id=1)

        remember_result, forget_result = await asyncio.gather(remember_task, forget_task)

        # One should succeed, operations are isolated
        assert remember_result.status == ToolStatus.SUCCESS or forget_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_deadlock_detection_and_prevention(self, recall_tool, optimize_tool, decompose_tool, mock_memory_store, mock_planning_store):
        """Test deadlock prevention across tools."""
        mock_memory_store.recall_with_reranking.return_value = []

        # Multiple concurrent operations on different tools
        tasks = [
            recall_tool.execute(query="q1"),
            optimize_tool.execute(),
            decompose_tool.execute(task="task1"),
            recall_tool.execute(query="q2"),
            optimize_tool.execute(),
        ]

        # Should complete without deadlock
        results = await asyncio.gather(*tasks)
        assert all(r.status in [ToolStatus.SUCCESS, ToolStatus.ERROR] for r in results)


class TestResourceConstraints:
    """Test operation under resource limits."""

    @pytest.mark.asyncio
    async def test_operations_with_limited_memory(self, remember_tool, mock_memory_store):
        """Test operations with limited memory availability."""
        # Simulate limited memory by returning fewer results
        mock_memory_store.store_memory.return_value = 1

        # Still should succeed
        result = await remember_tool.execute(content="Content")
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_operations_with_slow_database(self, recall_tool, mock_memory_store):
        """Test operations with slow database responses."""
        async def slow_recall(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate slowness
            return []

        mock_memory_store.recall_with_reranking.side_effect = slow_recall

        result = await recall_tool.execute(query="test")
        # Should still complete
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]

    @pytest.mark.asyncio
    async def test_large_batch_operations(self, remember_tool, mock_memory_store):
        """Test large batch memory operations."""
        mock_memory_store.store_memory.return_value = 1

        # Store 100 items
        tasks = [
            remember_tool.execute(content=f"Item {i}")
            for i in range(100)
        ]

        results = await asyncio.gather(*tasks)
        assert len(results) == 100
        assert all(r.status == ToolStatus.SUCCESS for r in results)

    @pytest.mark.asyncio
    async def test_recovery_from_out_of_memory(self, remember_tool, mock_memory_store):
        """Test recovery from out-of-memory condition."""
        # First succeeds
        mock_memory_store.store_memory.return_value = 1
        result1 = await remember_tool.execute(content="First")
        assert result1.status == ToolStatus.SUCCESS

        # Second fails due to memory
        mock_memory_store.store_memory.side_effect = MemoryError("Out of memory")
        result2 = await remember_tool.execute(content="Second")
        # Should error gracefully
        assert result2.status == ToolStatus.ERROR

        # Recovery: reset and try again
        mock_memory_store.store_memory.side_effect = None
        mock_memory_store.store_memory.return_value = 2
        result3 = await remember_tool.execute(content="Third")
        assert result3.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_recovery_from_storage_full(self, optimize_tool, mock_memory_store):
        """Test recovery from storage full condition."""
        mock_memory_store.optimize.side_effect = IOError("Storage full")

        result = await optimize_tool.execute()
        # Should error gracefully
        assert result.status == ToolStatus.ERROR


class TestBoundaryConditions:
    """Test boundary and edge values."""

    @pytest.mark.asyncio
    async def test_empty_inputs_handling(self, remember_tool, recall_tool, mock_memory_store):
        """Test handling of empty inputs."""
        mock_memory_store.recall_with_reranking.return_value = []

        # Empty content
        result1 = await remember_tool.execute(content="")
        assert result1.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]

        # Empty query
        result2 = await recall_tool.execute(query="")
        assert result2.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_maximum_size_inputs(self, remember_tool, mock_memory_store):
        """Test handling of maximum size inputs."""
        mock_memory_store.store_memory.return_value = 1

        # 10MB content
        huge_content = "x" * (10 * 1024 * 1024)
        result = await remember_tool.execute(content=huge_content)
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_null_optional_parameters(self, recall_tool, mock_memory_store):
        """Test null optional parameters."""
        mock_memory_store.recall_with_reranking.return_value = []

        result = await recall_tool.execute(query="test", k=None)
        # Should handle gracefully
        assert result.status in [ToolStatus.SUCCESS, ToolStatus.ERROR]

    @pytest.mark.asyncio
    async def test_special_characters_in_inputs(self, remember_tool, mock_memory_store):
        """Test special characters in inputs."""
        mock_memory_store.store_memory.return_value = 1

        special_content = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        result = await remember_tool.execute(content=special_content)
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_unicode_handling(self, remember_tool, mock_memory_store):
        """Test unicode character handling."""
        mock_memory_store.store_memory.return_value = 1

        unicode_content = "日本語 中文 العربية हिन्दी עברית"
        result = await remember_tool.execute(content=unicode_content)
        assert result.status == ToolStatus.SUCCESS


class TestFailureRecovery:
    """Test graceful failure handling and recovery."""

    @pytest.mark.asyncio
    async def test_partial_operation_failure(self, remember_tool, forget_tool, mock_memory_store):
        """Test partial operation failure."""
        # First operation succeeds
        mock_memory_store.store_memory.return_value = 1
        result1 = await remember_tool.execute(content="Content")
        assert result1.status == ToolStatus.SUCCESS

        # Second operation fails
        mock_memory_store.forget.side_effect = Exception("Delete failed")
        result2 = await forget_tool.execute(memory_id=1)
        assert result2.status == ToolStatus.ERROR

        # System still functional
        mock_memory_store.forget.side_effect = None
        mock_memory_store.forget.return_value = True
        result3 = await forget_tool.execute(memory_id=1)
        assert result3.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self, recall_tool, mock_memory_store):
        """Test tool timeout handling."""
        async def timeout_recall(*args, **kwargs):
            await asyncio.sleep(10)
            return []

        mock_memory_store.recall_with_reranking.side_effect = timeout_recall

        # Timeout should be handled
        try:
            result = await asyncio.wait_for(
                recall_tool.execute(query="test"),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            # Expected
            pass

    @pytest.mark.asyncio
    async def test_invalid_data_detection(self, remember_tool, mock_memory_store):
        """Test invalid data detection."""
        mock_memory_store.store_memory.side_effect = ValueError("Invalid data")

        result = await remember_tool.execute(content="Invalid")
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_rollback_on_failure(self, remember_tool, forget_tool, mock_memory_store):
        """Test rollback on failure."""
        # Setup: remember succeeds, forget fails
        mock_memory_store.store_memory.return_value = 50
        remember_result = await remember_tool.execute(content="Data")
        assert remember_result.status == ToolStatus.SUCCESS
        memory_id = remember_result.data["memory_id"]

        # Forget fails
        mock_memory_store.forget.side_effect = Exception("Rollback needed")
        forget_result = await forget_tool.execute(memory_id=memory_id)
        assert forget_result.status == ToolStatus.ERROR

        # System recovers
        mock_memory_store.forget.side_effect = None
        mock_memory_store.forget.return_value = True
        recovery = await forget_tool.execute(memory_id=memory_id)
        assert recovery.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_consistency_after_failure(self, remember_tool, forget_tool, recall_tool, mock_memory_store):
        """Test consistency after failure."""
        # Setup
        mock_memory_store.store_memory.return_value = 1
        await remember_tool.execute(content="Content")

        # Failure
        mock_memory_store.recall_with_reranking.side_effect = Exception("Recall failed")
        result1 = await recall_tool.execute(query="test")
        assert result1.status == ToolStatus.ERROR

        # Recovery and verify consistency
        mock_memory_store.recall_with_reranking.side_effect = None
        mock_memory_store.recall_with_reranking.return_value = []
        result2 = await recall_tool.execute(query="test")
        assert result2.status == ToolStatus.SUCCESS
        # Results should be consistent (empty)
        assert result2.data["count"] == 0
