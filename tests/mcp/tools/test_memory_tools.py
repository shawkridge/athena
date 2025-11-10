"""Tests for core memory tools (recall, remember, forget, optimize)."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
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
    mock_project.name = "test_project"
    manager.require_project = Mock(return_value=mock_project)
    manager.detect_current_project = Mock(return_value=mock_project)
    return manager


@pytest.fixture
def recall_tool(mock_memory_store, mock_project_manager):
    """Create recall tool instance."""
    return RecallTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def remember_tool(mock_memory_store, mock_project_manager):
    """Create remember tool instance."""
    return RememberTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def forget_tool(mock_memory_store, mock_project_manager):
    """Create forget tool instance."""
    return ForgetTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def optimize_tool(mock_memory_store, mock_project_manager):
    """Create optimize tool instance."""
    return OptimizeTool(mock_memory_store, mock_project_manager)


class TestRecallTool:
    """Test RecallTool functionality."""

    @pytest.mark.asyncio
    async def test_recall_missing_query(self, recall_tool):
        """Test recall with missing query parameter."""
        result = await recall_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_recall_no_results(self, recall_tool, mock_memory_store):
        """Test recall when no results found."""
        mock_memory_store.recall_with_reranking.return_value = []

        result = await recall_tool.execute(query="test query")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 0
        assert result.data["memories"] == []

    @pytest.mark.asyncio
    async def test_recall_with_results(self, recall_tool, mock_memory_store):
        """Test recall with successful results."""
        # Mock search results
        mock_result = Mock()
        mock_result.similarity = 0.95
        mock_result.memory = Mock()
        mock_result.memory.id = 1
        mock_result.memory.content = "Test memory content"
        mock_result.memory.memory_type = "semantic"
        mock_result.memory.tags = ["test", "important"]
        mock_result.memory.created_at = Mock()
        mock_result.memory.created_at.isoformat = Mock(return_value="2025-01-01T00:00:00")

        mock_memory_store.recall_with_reranking.return_value = [mock_result]

        result = await recall_tool.execute(query="test query", k=5)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 1
        assert len(result.data["memories"]) == 1
        assert result.data["memories"][0]["content"] == "Test memory content"
        assert result.data["memories"][0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_recall_with_k_parameter(self, recall_tool, mock_memory_store):
        """Test recall respects k parameter."""
        mock_memory_store.recall_with_reranking.return_value = []

        await recall_tool.execute(query="test", k=10)

        # Verify k was passed to store
        call_args = mock_memory_store.recall_with_reranking.call_args
        assert call_args[1]["k"] == 10

    @pytest.mark.asyncio
    async def test_recall_project_error(self, recall_tool, mock_project_manager):
        """Test recall when project lookup fails."""
        mock_project_manager.require_project.side_effect = Exception("Project not found")

        result = await recall_tool.execute(query="test")
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error

    @pytest.mark.asyncio
    async def test_recall_search_error(self, recall_tool, mock_memory_store):
        """Test recall when search fails."""
        mock_memory_store.recall_with_reranking.side_effect = Exception("Search error")

        result = await recall_tool.execute(query="test")
        assert result.status == ToolStatus.ERROR
        assert "Search failed" in result.error


class TestRememberTool:
    """Test RememberTool functionality."""

    @pytest.mark.asyncio
    async def test_remember_missing_content(self, remember_tool):
        """Test remember with missing content parameter."""
        result = await remember_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_remember_basic(self, remember_tool, mock_memory_store):
        """Test basic remember operation."""
        mock_memory_store.store_memory.return_value = 42

        result = await remember_tool.execute(content="Test memory content")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["memory_id"] == 42
        assert result.data["content"] == "Test memory content"

    @pytest.mark.asyncio
    async def test_remember_with_tags(self, remember_tool, mock_memory_store):
        """Test remember with tags."""
        mock_memory_store.store_memory.return_value = 42

        result = await remember_tool.execute(
            content="Test",
            tags=["tag1", "tag2"]
        )
        assert result.status == ToolStatus.SUCCESS

        # Verify tags were passed
        call_args = mock_memory_store.store_memory.call_args
        assert call_args[1]["tags"] == ["tag1", "tag2"]

    @pytest.mark.asyncio
    async def test_remember_with_memory_type(self, remember_tool, mock_memory_store):
        """Test remember with memory type."""
        mock_memory_store.store_memory.return_value = 42

        result = await remember_tool.execute(
            content="Test",
            memory_type="episodic"
        )
        assert result.status == ToolStatus.SUCCESS

        # Verify memory type was passed
        call_args = mock_memory_store.store_memory.call_args
        assert call_args[1]["memory_type"] == "episodic"

    @pytest.mark.asyncio
    async def test_remember_project_error(self, remember_tool, mock_project_manager):
        """Test remember when project lookup fails."""
        mock_project_manager.require_project.side_effect = Exception("No project")

        result = await remember_tool.execute(content="Test")
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error

    @pytest.mark.asyncio
    async def test_remember_storage_error(self, remember_tool, mock_memory_store):
        """Test remember when storage fails."""
        mock_memory_store.store_memory.side_effect = Exception("Storage error")

        result = await remember_tool.execute(content="Test")
        assert result.status == ToolStatus.ERROR
        assert "Storage failed" in result.error


class TestForgetTool:
    """Test ForgetTool functionality."""

    @pytest.mark.asyncio
    async def test_forget_missing_parameters(self, forget_tool):
        """Test forget with missing both parameters."""
        result = await forget_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Must provide either 'memory_id' or 'query'" in result.error

    @pytest.mark.asyncio
    async def test_forget_by_id(self, forget_tool, mock_memory_store):
        """Test forget by memory ID."""
        mock_memory_store.forget.return_value = True

        result = await forget_tool.execute(memory_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["deleted_count"] == 1
        assert result.data["memory_id"] == 1

    @pytest.mark.asyncio
    async def test_forget_by_id_not_found(self, forget_tool, mock_memory_store):
        """Test forget when memory not found."""
        mock_memory_store.forget.return_value = False

        result = await forget_tool.execute(memory_id=999)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_forget_by_query_not_supported(self, forget_tool):
        """Test forget by query returns appropriate error."""
        result = await forget_tool.execute(query="test query")
        assert result.status == ToolStatus.ERROR
        assert "Query-based forget not yet supported" in result.error

    @pytest.mark.asyncio
    async def test_forget_delete_error(self, forget_tool, mock_memory_store):
        """Test forget when delete fails."""
        mock_memory_store.forget.side_effect = Exception("Delete error")

        result = await forget_tool.execute(memory_id=1)
        assert result.status == ToolStatus.ERROR
        assert "Delete failed" in result.error


class TestOptimizeTool:
    """Test OptimizeTool functionality."""

    @pytest.mark.asyncio
    async def test_optimize_dry_run(self, optimize_tool, mock_memory_store):
        """Test optimize in dry-run mode."""
        result = await optimize_tool.execute(dry_run=True)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["dry_run"] is True
        assert result.data["pruned"] == 20

    @pytest.mark.asyncio
    async def test_optimize_actual(self, optimize_tool, mock_memory_store):
        """Test optimize actual run."""
        result = await optimize_tool.execute(dry_run=False)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["dry_run"] is False
        assert result.data["before_count"] == 100
        assert result.data["after_count"] == 80

    @pytest.mark.asyncio
    async def test_optimize_default_dry_run(self, optimize_tool, mock_memory_store):
        """Test optimize defaults to dry-run."""
        result = await optimize_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["dry_run"] is True

    @pytest.mark.asyncio
    async def test_optimize_project_error(self, optimize_tool, mock_project_manager):
        """Test optimize when project lookup fails."""
        mock_project_manager.require_project.side_effect = Exception("No project")

        result = await optimize_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error

    @pytest.mark.asyncio
    async def test_optimize_operation_error(self, optimize_tool, mock_memory_store):
        """Test optimize when operation fails."""
        mock_memory_store.optimize.side_effect = Exception("Optimization error")

        result = await optimize_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Optimization failed" in result.error


class TestMemoryToolsMetadata:
    """Test metadata for memory tools."""

    def test_recall_metadata(self, recall_tool):
        """Test recall tool metadata."""
        assert recall_tool.metadata.name == "recall"
        assert "search" in recall_tool.metadata.tags
        assert recall_tool.metadata.category == "memory"

    def test_remember_metadata(self, remember_tool):
        """Test remember tool metadata."""
        assert remember_tool.metadata.name == "remember"
        assert "store" in remember_tool.metadata.tags
        assert remember_tool.metadata.category == "memory"

    def test_forget_metadata(self, forget_tool):
        """Test forget tool metadata."""
        assert forget_tool.metadata.name == "forget"
        assert "delete" in forget_tool.metadata.tags
        assert forget_tool.metadata.category == "memory"

    def test_optimize_metadata(self, optimize_tool):
        """Test optimize tool metadata."""
        assert optimize_tool.metadata.name == "optimize"
        assert "maintenance" in optimize_tool.metadata.tags
        assert optimize_tool.metadata.category == "memory"
