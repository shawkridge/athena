"""Tests for ToolLoader."""
import pytest
from pathlib import Path
from athena.tools import BaseTool, ToolMetadata, ToolRegistry, ToolLoader


class TestTool(BaseTool):
    """Test tool for loader testing."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="test_tool",
            category="test",
            description="A test tool"
        )

    async def execute(self, **kwargs):
        return {"status": "ok"}


class TestToolLoader:
    """Test ToolLoader functionality."""

    def test_create_loader(self):
        """Test creating a tool loader."""
        loader = ToolLoader()
        assert loader.registry is not None
        assert loader.tools_dir is not None

    def test_load_module_builtin(self):
        """Test loading a built-in module."""
        loader = ToolLoader()
        module = loader.load_module("json")
        assert module is not None
        assert hasattr(module, "dumps")

    def test_load_module_caching(self):
        """Test that loaded modules are cached."""
        loader = ToolLoader()
        module1 = loader.load_module("json")
        module2 = loader.load_module("json")
        assert module1 is module2

    def test_load_module_nonexistent(self):
        """Test loading nonexistent module raises ImportError."""
        loader = ToolLoader()
        with pytest.raises(ImportError):
            loader.load_module("nonexistent.module.that.does.not.exist")

    def test_load_tool_from_registry(self):
        """Test loading a registered tool."""
        registry = ToolRegistry()
        registry.register("test.tool", TestTool, category="test")
        loader = ToolLoader(registry=registry)

        tool = loader.load_tool("test.tool")
        assert isinstance(tool, TestTool)

    def test_key_to_module_name(self):
        """Test converting tool key to module name."""
        module_name = ToolLoader._key_to_module_name("memory.query")
        assert module_name == "athena.tools.memory.query"

        module_name = ToolLoader._key_to_module_name("consolidation.extract")
        assert module_name == "athena.tools.consolidation.extract"

    def test_module_name_to_class_name(self):
        """Test converting tool key to class name."""
        class_name = ToolLoader._module_name_to_class_name("memory.query")
        assert class_name == "MemoryQueryTool"

        class_name = ToolLoader._module_name_to_class_name("consolidation.extract")
        assert class_name == "ConsolidationExtractTool"

    def test_get_memory_usage(self):
        """Test getting memory usage stats."""
        registry = ToolRegistry()
        registry.register("test.tool", TestTool, category="test")
        loader = ToolLoader(registry=registry)

        # Load the tool
        _ = loader.load_tool("test.tool")

        stats = loader.get_memory_usage()
        assert "loaded_modules" in stats
        assert "registered_tools" in stats
        assert "unloaded_tools" in stats

    def test_global_loader(self):
        """Test global loader instance."""
        from athena.tools import get_loader

        loader = get_loader()
        assert isinstance(loader, ToolLoader)

        # Same instance returned on second call
        loader2 = get_loader()
        assert loader is loader2


class TestToolLoaderDiscovery:
    """Test tool discovery functionality."""

    def test_discover_tools_empty_directory(self, tmp_path):
        """Test discovering tools in empty directory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        loader = ToolLoader(tools_dir=tools_dir)
        discovered = loader.discover_tools()

        # Should be empty since no actual tools
        assert isinstance(discovered, dict)

    def test_discover_creates_categories(self, tmp_path):
        """Test that discovery creates category structure."""
        # Setup
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create a test category directory
        memory_dir = tools_dir / "memory"
        memory_dir.mkdir()

        # Create __init__.py files to make them packages
        (tools_dir / "__init__.py").touch()
        (memory_dir / "__init__.py").touch()

        # Discovery should work even with empty structure
        registry = ToolRegistry()
        loader = ToolLoader(registry=registry, tools_dir=tools_dir)
        discovered = loader.discover_tools()

        # No tools discovered yet, but should have run without error
        assert isinstance(discovered, dict)

    def test_discover_with_force_reload(self, tmp_path):
        """Test force reloading discovery."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "__init__.py").touch()

        registry = ToolRegistry()
        loader = ToolLoader(registry=registry, tools_dir=tools_dir)

        # First discovery
        loader.discover_tools()
        assert loader._auto_discovered

        # Force reload
        loader.discover_tools(force_reload=True)
        assert loader._auto_discovered


class TestToolLoaderIntegration:
    """Integration tests for loader with registry."""

    def test_load_category_empty(self):
        """Test loading empty category."""
        registry = ToolRegistry()
        loader = ToolLoader(registry=registry)

        tools = loader.load_category("nonexistent")
        assert isinstance(tools, dict)
        assert len(tools) == 0

    def test_load_category_with_tools(self):
        """Test loading category with tools."""
        registry = ToolRegistry()
        registry.register("test.tool1", TestTool, category="test")
        registry.register("test.tool2", TestTool, category="test")

        loader = ToolLoader(registry=registry)
        tools = loader.load_category("test")

        assert len(tools) == 2
        assert "test.tool1" in tools
        assert "test.tool2" in tools
        assert isinstance(tools["test.tool1"], TestTool)

    def test_preload_category(self):
        """Test preloading a category."""
        registry = ToolRegistry()
        registry.register("test.tool1", TestTool, category="test")

        loader = ToolLoader(registry=registry)
        loader.preload_category("test")

        # Should be in memory now
        stats = loader.get_memory_usage()
        assert stats["registered_tools"] > 0
