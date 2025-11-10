"""Tests for tool registry."""

import pytest
from athena.mcp.tools.base import BaseTool, ToolMetadata, ToolResult, ToolStatus
from athena.mcp.tools.registry import ToolRegistry


class SimpleTool(BaseTool):
    """Simple tool for testing registry."""

    async def execute(self, **params):
        """Execute tool."""
        return ToolResult.success(data={"executed": True})


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    tools = []
    for i in range(3):
        metadata = ToolMetadata(
            name=f"tool_{i}",
            description=f"Test tool {i}",
            category="test" if i < 2 else "memory",
        )
        tools.append(SimpleTool(metadata))
    return tools


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_register_tool(self, tool_registry, sample_tools):
        """Test registering a tool."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        assert len(tool_registry) == 1
        assert tool_registry.get("tool_0") == tool

    def test_register_duplicate_raises_error(self, tool_registry, sample_tools):
        """Test registering duplicate tool raises error."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        with pytest.raises(ValueError, match="already registered"):
            tool_registry.register(tool)

    def test_register_multiple_tools(self, tool_registry, sample_tools):
        """Test registering multiple tools."""
        for tool in sample_tools:
            tool_registry.register(tool)

        assert len(tool_registry) == 3

    def test_get_tool_exists(self, tool_registry, sample_tools):
        """Test getting an existing tool."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        retrieved = tool_registry.get("tool_0")
        assert retrieved == tool
        assert retrieved.metadata.name == "tool_0"

    def test_get_tool_not_found(self, tool_registry):
        """Test getting a non-existent tool."""
        result = tool_registry.get("nonexistent")
        assert result is None

    def test_unregister_tool(self, tool_registry, sample_tools):
        """Test unregistering a tool."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        success = tool_registry.unregister("tool_0")
        assert success is True
        assert len(tool_registry) == 0

    def test_unregister_nonexistent(self, tool_registry):
        """Test unregistering non-existent tool."""
        success = tool_registry.unregister("nonexistent")
        assert success is False

    def test_update_existing_tool(self, tool_registry, sample_tools):
        """Test updating an existing tool."""
        tool1 = sample_tools[0]
        tool_registry.register(tool1)

        # Update with new tool of same name
        new_metadata = ToolMetadata(
            name="tool_0",
            description="Updated tool 0",
            category="updated",
        )
        new_tool = SimpleTool(new_metadata)
        tool_registry.update(new_tool)

        assert len(tool_registry) == 1
        retrieved = tool_registry.get("tool_0")
        assert retrieved.metadata.description == "Updated tool 0"

    def test_list_tools(self, tool_registry, sample_tools):
        """Test listing all tools."""
        for tool in sample_tools:
            tool_registry.register(tool)

        tools = tool_registry.list_tools()
        assert len(tools) == 3

    def test_list_by_category(self, tool_registry, sample_tools):
        """Test listing tools by category."""
        for tool in sample_tools:
            tool_registry.register(tool)

        test_tools = tool_registry.list_by_category("test")
        assert len(test_tools) == 2

        memory_tools = tool_registry.list_by_category("memory")
        assert len(memory_tools) == 1

    def test_get_metadata(self, tool_registry, sample_tools):
        """Test getting tool metadata."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        metadata = tool_registry.get_metadata("tool_0")
        assert metadata is not None
        assert metadata.name == "tool_0"

    def test_get_metadata_not_found(self, tool_registry):
        """Test getting metadata for non-existent tool."""
        metadata = tool_registry.get_metadata("nonexistent")
        assert metadata is None

    def test_search_by_tag(self, tool_registry):
        """Test searching tools by tag."""
        # Create tools with tags
        metadata1 = ToolMetadata(
            name="tagged_tool_1",
            description="Tool with tags",
            category="test",
            tags=["important", "query"],
        )
        metadata2 = ToolMetadata(
            name="tagged_tool_2",
            description="Another tagged tool",
            category="test",
            tags=["important", "memory"],
        )

        tool_registry.register(SimpleTool(metadata1))
        tool_registry.register(SimpleTool(metadata2))

        important_tools = tool_registry.search_by_tag("important")
        assert len(important_tools) == 2

        query_tools = tool_registry.search_by_tag("query")
        assert len(query_tools) == 1

    def test_get_categories(self, tool_registry, sample_tools):
        """Test getting list of categories."""
        for tool in sample_tools:
            tool_registry.register(tool)

        categories = tool_registry.get_categories()
        assert "test" in categories
        assert "memory" in categories

    def test_get_stats(self, tool_registry, sample_tools):
        """Test getting registry statistics."""
        for tool in sample_tools:
            tool_registry.register(tool)

        stats = tool_registry.get_stats()
        assert stats["total_tools"] == 3
        assert stats["categories"] == 2
        assert stats["tools_by_category"]["test"] == 2
        assert stats["tools_by_category"]["memory"] == 1

    def test_contains_operator(self, tool_registry, sample_tools):
        """Test using 'in' operator to check tool existence."""
        tool = sample_tools[0]
        tool_registry.register(tool)

        assert "tool_0" in tool_registry
        assert "tool_999" not in tool_registry

    def test_iter_operator(self, tool_registry, sample_tools):
        """Test iterating over registry."""
        for tool in sample_tools:
            tool_registry.register(tool)

        tools = list(tool_registry)
        assert len(tools) == 3

    def test_len_operator(self, tool_registry, sample_tools):
        """Test getting registry length."""
        for tool in sample_tools:
            tool_registry.register(tool)

        assert len(tool_registry) == 3
