"""Tests for tool migration framework."""
import pytest
from pathlib import Path
from athena.tools.migration import ToolExtractor, ToolMigrator, BackwardCompatibilityLayer


@pytest.fixture
def sample_handlers_file(tmp_path):
    """Create a sample handlers.py file for testing."""
    handlers_py = tmp_path / "handlers.py"
    content = '''"""Sample MCP handlers for testing."""


class SampleHandler:
    """Sample handler class."""

    @server.tool()
    def memory_recall(self, query: str, limit: int = 10) -> dict:
        """Recall memories from the system.

        Args:
            query: Search query
            limit: Max results

        Returns:
            Dictionary with results
        """
        return {"results": []}

    @server.tool()
    def memory_store(self, content: str, metadata: dict = None) -> str:
        """Store a memory.

        Args:
            content: Memory content
            metadata: Optional metadata

        Returns:
            Memory ID
        """
        return "memory_123"

    @server.tool()
    def consolidation_start(self, strategy: str = "balanced") -> dict:
        """Start consolidation process.

        Args:
            strategy: Consolidation strategy

        Returns:
            Consolidation status
        """
        return {"status": "started"}

    def regular_method(self):
        """This is not a tool."""
        pass
'''
    handlers_py.write_text(content)
    return handlers_py


class TestToolExtractor:
    """Test ToolExtractor functionality."""

    def test_extract_tools(self, sample_handlers_file):
        """Test extracting tools from handlers."""
        extractor = ToolExtractor(sample_handlers_file)
        tools = extractor.find_tools()

        assert len(tools) == 3
        assert "memory_recall" in tools
        assert "memory_store" in tools
        assert "consolidation_start" in tools

    def test_extract_tool_metadata(self, sample_handlers_file):
        """Test extracting tool metadata."""
        extractor = ToolExtractor(sample_handlers_file)
        tools = extractor.find_tools()

        tool_info = tools["memory_recall"]
        assert tool_info["name"] == "memory_recall"
        assert tool_info["lineno"] > 0
        assert "query" in tool_info["args"]
        assert "limit" in tool_info["args"]

    def test_extract_tool_docstring(self, sample_handlers_file):
        """Test extracting tool docstring."""
        extractor = ToolExtractor(sample_handlers_file)
        tools = extractor.find_tools()

        docstring = tools["memory_recall"]["docstring"]
        assert docstring is not None
        assert "Recall memories" in docstring

    def test_get_tool_categories(self, sample_handlers_file):
        """Test categorizing tools."""
        extractor = ToolExtractor(sample_handlers_file)
        categories = extractor.get_tool_categories()

        assert "memory" in categories
        assert "consolidation" in categories
        assert len(categories["memory"]) == 2
        assert "memory_recall" in categories["memory"]
        assert "memory_store" in categories["memory"]

    def test_extract_tool_method(self, sample_handlers_file):
        """Test extracting complete tool method source."""
        extractor = ToolExtractor(sample_handlers_file)
        source = extractor.extract_tool_method("memory_recall")

        assert source is not None
        assert "def memory_recall" in source
        assert "query: str" in source


class TestToolMigrator:
    """Test ToolMigrator functionality."""

    def test_create_tool_file(self, sample_handlers_file, tmp_path):
        """Test creating a new tool file."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        tool_file = migrator.create_tool_file("memory_recall", "memory")

        assert tool_file.exists()
        assert tool_file.parent.name == "memory"
        assert tool_file.name == "recall.py"

        # Check content
        content = tool_file.read_text()
        assert "class RecallTool" in content
        assert "memory" in content

    def test_create_tool_file_structure(self, sample_handlers_file, tmp_path):
        """Test that tool file has correct structure."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        tool_file = migrator.create_tool_file("memory_recall", "memory")
        content = tool_file.read_text()

        # Check for required components
        assert "from athena.tools import BaseTool, ToolMetadata" in content
        assert "class RecallTool(BaseTool):" in content
        assert "def metadata(self)" in content
        assert "async def execute(self" in content
        assert "def validate_input(self" in content

    def test_migrate_tools(self, sample_handlers_file, tmp_path):
        """Test migrating multiple tools."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        migrated = migrator.migrate_tools(["memory_recall", "memory_store"])

        assert len(migrated) == 2
        assert "memory_recall" in migrated
        assert "memory_store" in migrated

        # Check files exist
        assert migrated["memory_recall"].exists()
        assert migrated["memory_store"].exists()

    def test_migrate_all_tools(self, sample_handlers_file, tmp_path):
        """Test migrating all tools."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        migrated = migrator.migrate_tools()

        # Should migrate 3 tools
        assert len(migrated) == 3

    def test_migrate_nonexistent_tool(self, sample_handlers_file, tmp_path):
        """Test migrating nonexistent tool."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        migrated = migrator.migrate_tools(["nonexistent_tool"])

        assert len(migrated) == 0

    def test_get_migration_status(self, sample_handlers_file, tmp_path):
        """Test getting migration status."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        # Before migration
        status = migrator.get_migration_status()
        assert status["total_tools_in_handlers"] == 3
        assert status["migrated_tools"] == 0
        assert status["migration_percentage"] == 0.0

        # After migrating some
        migrator.migrate_tools(["memory_recall"])
        status = migrator.get_migration_status()
        assert status["migrated_tools"] == 1
        assert status["remaining_tools"] == 2
        assert 0 < status["migration_percentage"] < 100

    def test_migration_status_all_migrated(self, sample_handlers_file, tmp_path):
        """Test migration status when all tools migrated."""
        tools_dir = tmp_path / "tools"
        migrator = ToolMigrator(sample_handlers_file, tools_dir)

        # Migrate all
        migrator.migrate_tools()

        status = migrator.get_migration_status()
        assert status["migrated_tools"] == 3
        assert status["remaining_tools"] == 0
        assert status["migration_percentage"] == 100.0


class TestBackwardCompatibilityLayer:
    """Test backward compatibility layer."""

    def test_create_wrapper(self, tmp_path):
        """Test creating compatibility wrapper."""
        mcp_dir = tmp_path / "mcp"
        tools_dir = tmp_path / "tools"
        mcp_dir.mkdir()

        compat = BackwardCompatibilityLayer(mcp_dir, tools_dir)
        wrapper_file = compat.create_wrapper("memory_recall", "memory.recall")

        assert wrapper_file.exists()
        assert wrapper_file.parent.name == "compat"

        content = wrapper_file.read_text()
        assert "handle_memory_recall" in content
        assert "memory.recall" in content

    def test_create_all_wrappers(self, tmp_path):
        """Test creating multiple wrappers."""
        mcp_dir = tmp_path / "mcp"
        tools_dir = tmp_path / "tools"
        mcp_dir.mkdir()

        compat = BackwardCompatibilityLayer(mcp_dir, tools_dir)

        mappings = {
            "memory_recall": "memory.recall",
            "memory_store": "memory.store",
            "consolidation_start": "consolidation.start"
        }

        wrappers = compat.create_all_wrappers(mappings)

        assert len(wrappers) == 3
        for wrapper_file in wrappers.values():
            assert wrapper_file.exists()

    def test_wrapper_structure(self, tmp_path):
        """Test wrapper has correct structure."""
        mcp_dir = tmp_path / "mcp"
        tools_dir = tmp_path / "tools"
        mcp_dir.mkdir()

        compat = BackwardCompatibilityLayer(mcp_dir, tools_dir)
        wrapper_file = compat.create_wrapper("memory_recall", "memory.recall")

        content = wrapper_file.read_text()

        # Check for required components
        assert "from athena.tools import get_loader" in content
        assert "def handle_memory_recall" in content
        assert "_loader.load_tool" in content
        assert "asyncio.run" in content
