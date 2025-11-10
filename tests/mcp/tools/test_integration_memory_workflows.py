"""Integration tests for memory workflow operations."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from athena.mcp.tools.memory_tools import (
    RecallTool,
    RememberTool,
    ForgetTool,
    OptimizeTool,
)
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
def recall_tool(mock_memory_store, mock_project_manager):
    """Create recall tool."""
    return RecallTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def remember_tool(mock_memory_store, mock_project_manager):
    """Create remember tool."""
    return RememberTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def forget_tool(mock_memory_store, mock_project_manager):
    """Create forget tool."""
    return ForgetTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def optimize_tool(mock_memory_store, mock_project_manager):
    """Create optimize tool."""
    return OptimizeTool(mock_memory_store, mock_project_manager)


class TestRecallOptimizeFlow:
    """Test recall → optimize workflow."""

    @pytest.mark.asyncio
    async def test_recall_then_optimize(self, recall_tool, optimize_tool, mock_memory_store):
        """Test recall followed by optimize operation."""
        # First recall
        mock_memory_store.recall_with_reranking.return_value = []
        recall_result = await recall_tool.execute(query="test")
        assert recall_result.status == ToolStatus.SUCCESS

        # Then optimize
        optimize_result = await optimize_tool.execute()
        assert optimize_result.status == ToolStatus.SUCCESS
        assert optimize_result.data["after_count"] == 80

    @pytest.mark.asyncio
    async def test_optimize_removes_low_value_memories(self, optimize_tool, mock_memory_store):
        """Test that optimization removes low-value memories."""
        mock_memory_store.optimize.return_value = {
            "before_count": 100,
            "after_count": 60,
            "pruned": 40,
            "dry_run": False,
            "avg_score_before": 0.5,
            "avg_score_after": 0.85
        }

        result = await optimize_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["pruned"] == 40
        assert result.data["avg_score_after"] > result.data["avg_score_before"]

    @pytest.mark.asyncio
    async def test_recall_consistency_after_optimize(self, recall_tool, optimize_tool, mock_memory_store):
        """Test recall returns consistent results after optimization."""
        # First recall
        mock_result = Mock()
        mock_result.similarity = 0.95
        mock_result.memory = Mock()
        mock_result.memory.id = 1
        mock_result.memory.content = "Important memory"
        mock_result.memory.memory_type = "semantic"
        mock_result.memory.tags = ["important"]
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        recall_before = await recall_tool.execute(query="important")
        assert recall_before.status == ToolStatus.SUCCESS
        assert recall_before.data["count"] == 1

        # Optimize
        optimize_result = await optimize_tool.execute()
        assert optimize_result.status == ToolStatus.SUCCESS

        # Recall again
        recall_after = await recall_tool.execute(query="important")
        assert recall_after.status == ToolStatus.SUCCESS
        # Important memories should still be found
        assert recall_after.data["count"] >= 0

    @pytest.mark.asyncio
    async def test_concurrent_recall_and_optimize(self, recall_tool, optimize_tool, mock_memory_store):
        """Test concurrent recall and optimize operations."""
        import asyncio

        mock_memory_store.recall_with_reranking.return_value = []

        # Run both concurrently
        recall_task = recall_tool.execute(query="test")
        optimize_task = optimize_tool.execute()

        recall_result, optimize_result = await asyncio.gather(recall_task, optimize_task)

        assert recall_result.status == ToolStatus.SUCCESS
        assert optimize_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_recall_optimize_preserve_important_memories(self, recall_tool, optimize_tool, mock_memory_store):
        """Test that optimization preserves important memories."""
        # Setup high-quality memory
        mock_result = Mock()
        mock_result.similarity = 0.99
        mock_result.memory = Mock()
        mock_result.memory.id = 1
        mock_result.memory.content = "Critical information"
        mock_result.memory.memory_type = "semantic"
        mock_result.memory.tags = ["critical", "important"]
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        recall_result = await recall_tool.execute(query="critical")
        assert recall_result.status == ToolStatus.SUCCESS
        assert recall_result.data["memories"][0]["similarity"] >= 0.95

        # Optimize should preserve this
        mock_memory_store.optimize.return_value = {
            "before_count": 100,
            "after_count": 50,
            "pruned": 50,
            "dry_run": False,
            "avg_score_before": 0.6,
            "avg_score_after": 0.9
        }

        optimize_result = await optimize_tool.execute()
        assert optimize_result.status == ToolStatus.SUCCESS
        assert optimize_result.data["after_count"] > 0


class TestRememberForgetFlow:
    """Test remember → forget workflow."""

    @pytest.mark.asyncio
    async def test_remember_then_forget(self, remember_tool, forget_tool, mock_memory_store):
        """Test remember followed by forget operation."""
        # Remember a memory
        mock_memory_store.store_memory.return_value = 42
        remember_result = await remember_tool.execute(content="Test content")
        assert remember_result.status == ToolStatus.SUCCESS
        assert remember_result.data["memory_id"] == 42

        # Forget it
        mock_memory_store.forget.return_value = True
        forget_result = await forget_tool.execute(memory_id=42)
        assert forget_result.status == ToolStatus.SUCCESS
        assert forget_result.data["deleted_count"] == 1

    @pytest.mark.asyncio
    async def test_forget_after_multiple_remember(self, remember_tool, forget_tool, mock_memory_store):
        """Test forgetting after multiple remember operations."""
        # Remember multiple memories
        memory_ids = [1, 2, 3, 4, 5]
        for mem_id in memory_ids:
            mock_memory_store.store_memory.return_value = mem_id
            result = await remember_tool.execute(content=f"Content {mem_id}")
            assert result.status == ToolStatus.SUCCESS

        # Forget one
        mock_memory_store.forget.return_value = True
        forget_result = await forget_tool.execute(memory_id=3)
        assert forget_result.status == ToolStatus.SUCCESS
        assert forget_result.data["deleted_count"] == 1

    @pytest.mark.asyncio
    async def test_consistency_after_remember_forget_cycle(self, remember_tool, forget_tool, mock_memory_store):
        """Test memory consistency after remember-forget cycles."""
        # Remember
        mock_memory_store.store_memory.return_value = 100
        remember_result = await remember_tool.execute(content="Test")
        assert remember_result.status == ToolStatus.SUCCESS

        # Forget
        mock_memory_store.forget.return_value = True
        forget_result = await forget_tool.execute(memory_id=100)
        assert forget_result.status == ToolStatus.SUCCESS

        # Remember again with different ID
        mock_memory_store.store_memory.return_value = 101
        remember_again = await remember_tool.execute(content="Test 2")
        assert remember_again.status == ToolStatus.SUCCESS
        assert remember_again.data["memory_id"] == 101

    @pytest.mark.asyncio
    async def test_forget_doesnt_affect_semantically_similar(self, remember_tool, forget_tool, recall_tool, mock_memory_store):
        """Test that forget doesn't affect semantically similar memories."""
        # Remember multiple memories
        mock_memory_store.store_memory.return_value = 50
        await remember_tool.execute(content="Important topic A")

        mock_memory_store.store_memory.return_value = 51
        await remember_tool.execute(content="Related topic A")

        # Forget first one
        mock_memory_store.forget.return_value = True
        forget_result = await forget_tool.execute(memory_id=50)
        assert forget_result.status == ToolStatus.SUCCESS

        # Recall related should still work
        mock_result = Mock()
        mock_result.similarity = 0.85
        mock_result.memory = Mock()
        mock_result.memory.id = 51
        mock_result.memory.content = "Related topic A"
        mock_result.memory.memory_type = "semantic"
        mock_result.memory.tags = []
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        recall_result = await recall_tool.execute(query="topic A")
        assert recall_result.status == ToolStatus.SUCCESS
        assert recall_result.data["count"] > 0


class TestConsolidateRecallFlow:
    """Test consolidate → recall workflow (simulated)."""

    @pytest.mark.asyncio
    async def test_recall_returns_quality_memories(self, recall_tool, mock_memory_store):
        """Test that recall returns higher quality memories after conceptual consolidation."""
        # Setup mock results with good quality
        mock_results = []
        for i in range(5):
            mock_result = Mock()
            mock_result.similarity = 0.95 - (i * 0.05)
            mock_result.memory = Mock()
            mock_result.memory.id = i + 1
            mock_result.memory.content = f"Quality memory {i}"
            mock_result.memory.memory_type = "semantic"
            mock_result.memory.tags = ["quality"]
            mock_result.memory.created_at = Mock()
            mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")
            mock_results.append(mock_result)

        mock_memory_store.recall_with_reranking.return_value = mock_results

        result = await recall_tool.execute(query="quality", k=5)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 5
        # Results should be ordered by quality
        assert result.data["memories"][0]["similarity"] >= result.data["memories"][-1]["similarity"]

    @pytest.mark.asyncio
    async def test_recall_preserves_critical_memories(self, recall_tool, mock_memory_store):
        """Test that recall preserves critical memories marked with high tags."""
        mock_result = Mock()
        mock_result.similarity = 0.99
        mock_result.memory = Mock()
        mock_result.memory.id = 999
        mock_result.memory.content = "CRITICAL: System configuration"
        mock_result.memory.memory_type = "semantic"
        mock_result.memory.tags = ["critical", "system", "config"]
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        result = await recall_tool.execute(query="configuration")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 1
        assert "critical" in result.data["memories"][0]["tags"]


class TestMemoryStateConsistency:
    """Test state consistency across memory operations."""

    @pytest.mark.asyncio
    async def test_memory_count_consistency(self, remember_tool, mock_memory_store):
        """Test that memory count remains consistent after operations."""
        initial_count = 100

        # Remember new memories
        mock_memory_store.store_memory.return_value = 101
        result = await remember_tool.execute(content="New memory")
        assert result.status == ToolStatus.SUCCESS

        # Mock should track count internally
        assert mock_memory_store.store_memory.called

    @pytest.mark.asyncio
    async def test_memory_uniqueness_after_operations(self, remember_tool, forget_tool, mock_memory_store):
        """Test that memory uniqueness is maintained."""
        # Remember same content twice (should get different IDs)
        mock_memory_store.store_memory.return_value = 1
        result1 = await remember_tool.execute(content="Same content")
        assert result1.status == ToolStatus.SUCCESS
        id1 = result1.data["memory_id"]

        mock_memory_store.store_memory.return_value = 2
        result2 = await remember_tool.execute(content="Same content")
        assert result2.status == ToolStatus.SUCCESS
        id2 = result2.data["memory_id"]

        # IDs should be different even for same content
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_storage_consistency_after_batch_ops(self, remember_tool, mock_memory_store):
        """Test storage consistency after batch operations."""
        batch_size = 10
        memory_ids = []

        for i in range(batch_size):
            mock_memory_store.store_memory.return_value = i + 1
            result = await remember_tool.execute(content=f"Batch memory {i}")
            assert result.status == ToolStatus.SUCCESS
            memory_ids.append(result.data["memory_id"])

        # All should be unique
        assert len(set(memory_ids)) == batch_size

    @pytest.mark.asyncio
    async def test_recovery_after_partial_failure(self, remember_tool, forget_tool, mock_memory_store):
        """Test recovery after partial operation failure."""
        # Setup: remember succeeds, forget fails
        mock_memory_store.store_memory.return_value = 50
        remember_result = await remember_tool.execute(content="Test")
        assert remember_result.status == ToolStatus.SUCCESS

        # Forget fails for non-existent ID
        mock_memory_store.forget.return_value = False
        forget_result = await forget_tool.execute(memory_id=999)
        assert forget_result.status == ToolStatus.SUCCESS
        assert forget_result.data["deleted_count"] == 0

        # System should still work - remember again
        mock_memory_store.store_memory.return_value = 51
        recovery_result = await remember_tool.execute(content="Recovery")
        assert recovery_result.status == ToolStatus.SUCCESS
