"""Tests for ToolManager and tool integration."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from athena.mcp.tools.manager import ToolManager
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server with required components."""
    server = Mock()

    # Mock stores and managers
    server.store = Mock()
    server.project_manager = Mock()
    server.episodic_store = Mock()
    server.consolidation_system = Mock()

    # Mock project for convenience
    mock_project = Mock()
    mock_project.id = 1
    mock_project.name = "test_project"
    server.project_manager.require_project = Mock(return_value=mock_project)
    server.project_manager.get_or_create_project = Mock(return_value=mock_project)

    return server


@pytest.fixture
def tool_manager(mock_mcp_server):
    """Create ToolManager instance."""
    return ToolManager(mock_mcp_server)


class TestToolManagerInitialization:
    """Test ToolManager initialization."""

    def test_initialization(self, tool_manager):
        """Test basic initialization."""
        assert not tool_manager.tools_initialized
        assert tool_manager.registry is not None
        assert len(tool_manager.registry) == 0

    def test_initialize_tools(self, tool_manager):
        """Test tool initialization."""
        tool_manager.initialize_tools()
        assert tool_manager.tools_initialized
        assert len(tool_manager.registry) > 0

    def test_initialize_tools_twice(self, tool_manager):
        """Test that initializing twice is idempotent."""
        tool_manager.initialize_tools()
        first_count = len(tool_manager.registry)

        tool_manager.initialize_tools()
        second_count = len(tool_manager.registry)

        assert first_count == second_count

    def test_initialize_creates_expected_tools(self, tool_manager):
        """Test that initialization creates all expected tools."""
        tool_manager.initialize_tools()

        stats = tool_manager.get_stats()
        # Should have 25 tools: 4 memory + 3 system + 3 episodic + 4 planning + 2 retrieval + 2 integration + 2 agent_optimization + 2 skill_optimization + 3 hook_coordination
        assert stats['total_tools'] == 25


class TestToolManagerExecution:
    """Test tool execution."""

    @pytest.mark.asyncio
    async def test_execute_missing_tool(self, tool_manager):
        """Test executing non-existent tool."""
        tool_manager.initialize_tools()

        result = await tool_manager.execute_tool("nonexistent_tool")
        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_recall_tool(self, tool_manager, mock_mcp_server):
        """Test executing recall tool."""
        # Mock store response
        mock_mcp_server.store.recall_with_reranking.return_value = []

        tool_manager.initialize_tools()

        result = await tool_manager.execute_tool(
            "recall",
            query="test query"
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_with_missing_param(self, tool_manager):
        """Test executing tool with missing required parameter."""
        tool_manager.initialize_tools()

        result = await tool_manager.execute_tool("recall")  # Missing query param
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error


class TestToolManagerQuerying:
    """Test tool discovery and querying."""

    def test_get_tool(self, tool_manager):
        """Test getting a tool by name."""
        tool_manager.initialize_tools()

        recall_tool = tool_manager.get_tool("recall")
        assert recall_tool is not None
        assert recall_tool.metadata.name == "recall"

    def test_get_nonexistent_tool(self, tool_manager):
        """Test getting non-existent tool."""
        tool_manager.initialize_tools()

        tool = tool_manager.get_tool("nonexistent")
        assert tool is None

    def test_list_tools(self, tool_manager):
        """Test listing all tools."""
        tool_manager.initialize_tools()

        tools = tool_manager.list_tools()
        assert len(tools) > 0
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)
        assert all("category" in t for t in tools)

    def test_list_tools_before_init(self, tool_manager):
        """Test listing tools before initialization."""
        tools = tool_manager.list_tools()
        assert len(tools) == 0

    def test_get_tools_by_category(self, tool_manager):
        """Test getting tools by category."""
        tool_manager.initialize_tools()

        memory_tools = tool_manager.get_tools_by_category("memory")
        assert len(memory_tools) == 4

        system_tools = tool_manager.get_tools_by_category("system")
        assert len(system_tools) == 3

        episodic_tools = tool_manager.get_tools_by_category("episodic")
        assert len(episodic_tools) == 3

    def test_get_tool_metadata(self, tool_manager):
        """Test getting tool metadata."""
        tool_manager.initialize_tools()

        metadata = tool_manager.get_tool_metadata("recall")
        assert metadata is not None
        assert metadata["name"] == "recall"
        assert "parameters" in metadata
        assert "description" in metadata

    def test_get_tool_metadata_not_found(self, tool_manager):
        """Test getting metadata for non-existent tool."""
        tool_manager.initialize_tools()

        metadata = tool_manager.get_tool_metadata("nonexistent")
        assert metadata is None

    def test_get_categories(self, tool_manager):
        """Test getting list of categories."""
        tool_manager.initialize_tools()

        categories = tool_manager.get_categories()
        assert "memory" in categories
        assert "system" in categories
        assert "episodic" in categories
        assert "planning" in categories
        assert "retrieval" in categories
        assert "integration" in categories
        assert "agent_optimization" in categories
        assert "skill_optimization" in categories
        assert "hook_coordination" in categories

    def test_get_stats(self, tool_manager):
        """Test getting registry statistics."""
        tool_manager.initialize_tools()

        stats = tool_manager.get_stats()
        assert "total_tools" in stats
        assert "categories" in stats
        assert "tools_by_category" in stats
        assert stats["total_tools"] == 25


class TestToolManagerCategories:
    """Test category management."""

    def test_memory_tools_present(self, tool_manager):
        """Test that all memory tools are present."""
        tool_manager.initialize_tools()
        memory_tools = tool_manager.get_tools_by_category("memory")
        assert len(memory_tools) == 4

    def test_system_tools_present(self, tool_manager):
        """Test that all system tools are present."""
        tool_manager.initialize_tools()
        system_tools = tool_manager.get_tools_by_category("system")
        assert len(system_tools) == 3

    def test_episodic_tools_present(self, tool_manager):
        """Test that all episodic tools are present."""
        tool_manager.initialize_tools()
        episodic_tools = tool_manager.get_tools_by_category("episodic")
        assert len(episodic_tools) == 3

    def test_planning_tools_present(self, tool_manager):
        """Test that all planning tools are present."""
        tool_manager.initialize_tools()
        planning_tools = tool_manager.get_tools_by_category("planning")
        assert len(planning_tools) == 4

    def test_retrieval_tools_present(self, tool_manager):
        """Test that all retrieval tools are present."""
        tool_manager.initialize_tools()
        retrieval_tools = tool_manager.get_tools_by_category("retrieval")
        assert len(retrieval_tools) == 2

    def test_integration_tools_present(self, tool_manager):
        """Test that all integration tools are present."""
        tool_manager.initialize_tools()
        integration_tools = tool_manager.get_tools_by_category("integration")
        assert len(integration_tools) == 2
