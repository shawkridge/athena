"""Tests for ToolRegistry."""
import pytest
from athena.tools import BaseTool, ToolMetadata, ToolRegistry, get_registry, register_tool


class DummyTool(BaseTool):
    """Dummy tool for testing."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="dummy",
            category="test",
            description="A dummy tool for testing"
        )

    async def execute(self, **kwargs):
        return {"result": "success"}


class AnotherTool(BaseTool):
    """Another dummy tool."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="another",
            category="test",
            description="Another tool"
        )

    async def execute(self, **kwargs):
        return {"result": "another"}


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")

        assert registry.has_tool("test.dummy")
        assert registry.get("test.dummy") == DummyTool

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate key raises ValueError."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")

        with pytest.raises(ValueError, match="already registered"):
            registry.register("test.dummy", AnotherTool, category="test")

    def test_register_invalid_class_raises_error(self):
        """Test that registering non-BaseTool class raises TypeError."""
        registry = ToolRegistry()

        class NotATool:
            pass

        with pytest.raises(TypeError, match="must inherit from BaseTool"):
            registry.register("test.invalid", NotATool, category="test")

    def test_get_nonexistent_tool(self):
        """Test getting nonexistent tool returns None."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_instantiate_tool(self):
        """Test instantiating a tool."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")

        tool = registry.instantiate("test.dummy")
        assert isinstance(tool, DummyTool)

    def test_instantiate_nonexistent_tool(self):
        """Test instantiating nonexistent tool returns None."""
        registry = ToolRegistry()
        assert registry.instantiate("nonexistent") is None

    def test_list_all_tools(self):
        """Test listing all registered tools."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("test.another", AnotherTool, category="test")

        tools = registry.list_tools()
        assert len(tools) == 2
        assert "test.dummy" in tools
        assert "test.another" in tools

    def test_list_tools_by_category(self):
        """Test listing tools filtered by category."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("other.another", AnotherTool, category="other")

        test_tools = registry.list_tools(category="test")
        assert len(test_tools) == 1
        assert "test.dummy" in test_tools

        other_tools = registry.list_tools(category="other")
        assert len(other_tools) == 1
        assert "other.another" in other_tools

    def test_list_tools_with_metadata(self):
        """Test listing tools with metadata."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")

        tools = registry.list_tools(include_metadata=True)
        assert len(tools) == 1
        key, metadata = tools[0]
        assert key == "test.dummy"
        assert metadata.name == "dummy"

    def test_get_categories(self):
        """Test getting all categories."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("memory.another", AnotherTool, category="memory")

        categories = registry.get_categories()
        assert "test" in categories
        assert "memory" in categories

    def test_get_category_tools(self):
        """Test getting tools in a category."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("test.another", AnotherTool, category="test")

        tools = registry.get_category_tools("test")
        assert len(tools) == 2
        assert "test.dummy" in tools
        assert "test.another" in tools

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")

        assert registry.has_tool("test.dummy")
        success = registry.unregister("test.dummy")
        assert success
        assert not registry.has_tool("test.dummy")

    def test_unregister_nonexistent_tool(self):
        """Test unregistering nonexistent tool returns False."""
        registry = ToolRegistry()
        success = registry.unregister("nonexistent")
        assert not success

    def test_clear_registry(self):
        """Test clearing all tools from registry."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("test.another", AnotherTool, category="test")

        registry.clear()
        assert len(registry.list_tools()) == 0
        assert len(registry.get_categories()) == 0

    def test_get_stats(self):
        """Test getting registry statistics."""
        registry = ToolRegistry()
        registry.register("test.dummy", DummyTool, category="test")
        registry.register("memory.another", AnotherTool, category="memory")

        stats = registry.get_stats()
        assert stats["total_tools"] == 2
        assert stats["total_categories"] == 2
        assert stats["categories_breakdown"]["test"] == 1
        assert stats["categories_breakdown"]["memory"] == 1

    def test_global_registry(self):
        """Test global registry functions."""
        registry = get_registry()
        assert isinstance(registry, ToolRegistry)

        # Same instance returned on second call
        registry2 = get_registry()
        assert registry is registry2

    def test_register_tool_global(self):
        """Test global register_tool function."""
        registry = get_registry()
        registry.clear()  # Clear for clean test

        register_tool("test.dummy", DummyTool, category="test")
        assert registry.has_tool("test.dummy")
