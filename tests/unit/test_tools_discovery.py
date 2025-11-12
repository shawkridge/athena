"""Tests for tools discovery system.

Tests:
- Tool generation
- Filesystem structure
- Tool metadata
- Index creation
"""

import pytest
import tempfile
from pathlib import Path
from athena.tools_discovery import (
    ToolsGenerator, ToolMetadata, register_core_tools
)


class TestToolsGenerator:
    """Test tools generation."""

    @pytest.fixture
    def generator(self):
        """Create generator with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ToolsGenerator(output_dir=tmpdir)

    @pytest.fixture
    def generator_with_tools(self):
        """Create generator with core tools registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            yield gen

    def test_tool_metadata_creation(self):
        """Test creating tool metadata."""
        metadata = ToolMetadata(
            name="recall",
            category="memory",
            description="Search memories",
            parameters={
                "query": {"type": "str", "description": "Search query"},
                "limit": {"type": "int", "description": "Results limit", "default": 10},
            },
            returns="List[Memory]",
            example="recall('auth')",
            entry_point="recall",
            dependencies=["athena.manager"],
        )

        assert metadata.name == "recall"
        assert metadata.category == "memory"
        assert "query" in metadata.parameters
        assert metadata.parameters["limit"]["default"] == 10

    def test_register_tool(self, generator):
        """Test registering a tool."""
        metadata = ToolMetadata(
            name="test_tool",
            category="test",
            description="Test tool",
            parameters={},
            returns="str",
            example="test_tool()",
            entry_point="test_tool",
            dependencies=[],
        )

        generator.register_tool(metadata)

        assert "test/test_tool" in generator.tools
        assert generator.tools["test/test_tool"] == metadata

    def test_generate_creates_directories(self, generator_with_tools):
        """Test that generation creates proper directories."""
        generator_with_tools.generate_all()

        output_dir = Path(generator_with_tools.output_dir)
        assert output_dir.exists()
        assert (output_dir / "memory").exists()
        assert (output_dir / "planning").exists()
        assert (output_dir / "consolidation").exists()

    def test_generate_creates_tool_files(self, generator_with_tools):
        """Test that tool files are created."""
        generator_with_tools.generate_all()

        output_dir = Path(generator_with_tools.output_dir)
        assert (output_dir / "memory" / "recall.py").exists()
        assert (output_dir / "memory" / "remember.py").exists()
        assert (output_dir / "memory" / "forget.py").exists()
        assert (output_dir / "planning" / "plan_task.py").exists()

    def test_generate_creates_init_files(self, generator_with_tools):
        """Test that __init__.py files are created."""
        generator_with_tools.generate_all()

        output_dir = Path(generator_with_tools.output_dir)
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "memory" / "__init__.py").exists()
        assert (output_dir / "planning" / "__init__.py").exists()

    def test_generate_creates_indexes(self, generator_with_tools):
        """Test that INDEX.md files are created."""
        generator_with_tools.generate_all()

        output_dir = Path(generator_with_tools.output_dir)
        assert (output_dir / "INDEX.md").exists()
        assert (output_dir / "memory" / "INDEX.md").exists()
        assert (output_dir / "planning" / "INDEX.md").exists()

    def test_tool_file_content(self, generator_with_tools):
        """Test generated tool file has correct content."""
        generator_with_tools.generate_all()

        tool_file = Path(generator_with_tools.output_dir) / "memory" / "recall.py"
        content = tool_file.read_text()

        assert "def recall" in content
        assert "Search and retrieve memories" in content
        assert "query: str" in content
        assert "limit: int = 10" in content

    def test_index_file_content(self, generator_with_tools):
        """Test generated index has correct content."""
        generator_with_tools.generate_all()

        index_file = Path(generator_with_tools.output_dir) / "memory" / "INDEX.md"
        content = index_file.read_text()

        assert "# Memory Tools" in content or "memory" in content.lower()
        assert "recall" in content
        assert "remember" in content

    def test_root_index_content(self, generator_with_tools):
        """Test root INDEX.md has correct content."""
        generator_with_tools.generate_all()

        index_file = Path(generator_with_tools.output_dir) / "INDEX.md"
        content = index_file.read_text()

        assert "Athena Tools" in content
        # Check for category titles (case-insensitive)
        content_lower = content.lower()
        assert "memory" in content_lower
        assert "planning" in content_lower
        assert "consolidation" in content_lower

    def test_multiple_tools_same_category(self):
        """Test generating multiple tools in same category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)

            for i in range(3):
                gen.register_tool(ToolMetadata(
                    name=f"tool_{i}",
                    category="test",
                    description=f"Test tool {i}",
                    parameters={},
                    returns="str",
                    example="test()",
                    entry_point=f"tool_{i}",
                    dependencies=[],
                ))

            gen.generate_all()

            output_dir = Path(tmpdir)
            assert (output_dir / "test" / "tool_0.py").exists()
            assert (output_dir / "test" / "tool_1.py").exists()
            assert (output_dir / "test" / "tool_2.py").exists()

    def test_core_tools_registered(self):
        """Test that core tools are properly registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)

            # Check expected tools are registered
            assert "memory/recall" in gen.tools
            assert "memory/remember" in gen.tools
            assert "memory/forget" in gen.tools
            assert "planning/plan_task" in gen.tools
            assert "planning/validate_plan" in gen.tools
            assert "consolidation/consolidate" in gen.tools

    def test_tool_with_complex_parameters(self):
        """Test tool with complex parameter types."""
        metadata = ToolMetadata(
            name="complex_tool",
            category="test",
            description="Tool with complex params",
            parameters={
                "items": {"type": "List[str]", "description": "List of items"},
                "config": {"type": "Dict[str, Any]", "description": "Config"},
                "optional": {"type": "str", "description": "Optional param", "default": "None"},
            },
            returns="Dict[str, Any]",
            example="complex_tool(['a', 'b'])",
            entry_point="complex_tool",
            dependencies=[],
        )

        assert "List[str]" in metadata.parameters["items"]["type"]
        assert "Dict[str, Any]" in metadata.parameters["config"]["type"]


class TestRegisterCoreTools:
    """Test core tools registration."""

    def test_register_core_tools(self):
        """Test all core tools are registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)

            assert len(gen.tools) > 0
            assert len(gen.tools) >= 6  # At least 6 core tools

    def test_memory_tools(self):
        """Test memory tools are registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)

            memory_tools = {k: v for k, v in gen.tools.items() if v.category == "memory"}
            assert len(memory_tools) == 3  # recall, remember, forget
            assert any(t.name == "recall" for t in memory_tools.values())
            assert any(t.name == "remember" for t in memory_tools.values())
            assert any(t.name == "forget" for t in memory_tools.values())

    def test_planning_tools(self):
        """Test planning tools are registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)

            planning_tools = {k: v for k, v in gen.tools.items() if v.category == "planning"}
            assert len(planning_tools) == 2  # plan_task, validate_plan

    def test_consolidation_tools(self):
        """Test consolidation tools are registered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)

            consolidation_tools = {k: v for k, v in gen.tools.items() if v.category == "consolidation"}
            assert len(consolidation_tools) == 2  # consolidate, get_patterns


class TestFilesystemDiscovery:
    """Test filesystem discovery pattern."""

    def test_agents_can_list_tools(self):
        """Test that agents can discover tools via filesystem listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            output_dir = Path(tmpdir)

            # Agent can list categories
            categories = [d.name for d in output_dir.iterdir() if d.is_dir()]
            assert "memory" in categories
            assert "planning" in categories

            # Agent can list tools in category
            memory_tools = [f.stem for f in (output_dir / "memory").glob("*.py") if f.name != "__init__.py"]
            assert "recall" in memory_tools
            assert "remember" in memory_tools

    def test_agents_can_read_tool_files(self):
        """Test that agents can read tool definitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            tool_file = Path(tmpdir) / "memory" / "recall.py"

            # Agent can read the file
            content = tool_file.read_text()

            # File contains callable definition
            assert "def recall" in content
            # File contains docstring
            assert "Search and retrieve memories" in content
            # File contains parameters
            assert "query" in content

    def test_progressive_loading_pattern(self):
        """Test agents can progressively load only needed tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ToolsGenerator(output_dir=tmpdir)
            register_core_tools(gen)
            gen.generate_all()

            # Agent only needs memory tools initially
            memory_dir = Path(tmpdir) / "memory"
            recall_file = memory_dir / "recall.py"

            # Agent reads only what's needed
            content = recall_file.read_text()
            assert len(content) < 2000  # Tool files are small

            # Agent doesn't load planning/consolidation if not needed
            planning_file = Path(tmpdir) / "planning" / "plan_task.py"
            assert planning_file.exists()  # Available if needed
            # But agent doesn't read it unless required
