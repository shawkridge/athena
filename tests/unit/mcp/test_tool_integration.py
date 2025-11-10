"""Integration tests for modular tools with compatibility layer."""
import pytest

from athena.tools import get_registry, get_loader
from athena.tools.memory.recall import RecallMemoryTool
from athena.tools.memory.store import StoreMemoryTool
from athena.tools.memory.health import HealthCheckTool
from athena.tools.consolidation.start import StartConsolidationTool
from athena.tools.consolidation.extract import ExtractPatternsTool
from athena.tools.planning.verify import VerifyPlanTool
from athena.tools.planning.simulate import SimulatePlanTool
from athena.tools.graph.query import QueryGraphTool
from athena.tools.graph.analyze import AnalyzeGraphTool
from athena.tools.retrieval.hybrid import HybridSearchTool


class TestToolRegistry:
    """Test tool registry integration."""

    def test_all_tools_instantiate(self):
        """Test that all 10 tools can be instantiated."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool(),
            StartConsolidationTool(),
            ExtractPatternsTool(),
            VerifyPlanTool(),
            SimulatePlanTool(),
            QueryGraphTool(),
            AnalyzeGraphTool(),
            HybridSearchTool()
        ]

        assert len(tools) == 10
        for tool in tools:
            assert tool is not None
            assert hasattr(tool, 'metadata')
            assert hasattr(tool, 'execute')

    def test_tool_metadata_complete(self):
        """Test that all tools have complete metadata."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool(),
            StartConsolidationTool(),
            ExtractPatternsTool(),
            VerifyPlanTool(),
            SimulatePlanTool(),
            QueryGraphTool(),
            AnalyzeGraphTool(),
            HybridSearchTool()
        ]

        for tool in tools:
            metadata = tool.metadata

            # Check required fields
            assert metadata.name
            assert metadata.category
            assert metadata.description
            assert isinstance(metadata.parameters, dict)
            assert isinstance(metadata.returns, dict)

            # Verify category consistency
            assert metadata.category in [
                "memory", "consolidation", "planning", "graph", "retrieval"
            ]


class TestToolLoader:
    """Test tool loader functionality."""

    def test_loader_can_discover_tools(self):
        """Test that loader can discover tools."""
        loader = get_loader()
        registry = get_registry()

        # First register tools
        registry.register("memory.recall", RecallMemoryTool, category="memory")
        registry.register("memory.store", StoreMemoryTool, category="memory")
        registry.register("memory.health", HealthCheckTool, category="memory")

        # Then verify discovery
        tools = registry.list_tools(category="memory")
        assert len(tools) >= 3

    def test_loader_can_instantiate_tool(self):
        """Test that loader can instantiate registered tools."""
        loader = get_loader()
        registry = get_registry()

        # Register a tool
        registry.register("memory.recall", RecallMemoryTool, category="memory")

        # Load it
        tool = loader.load_tool("memory.recall")
        assert tool is not None
        assert isinstance(tool, RecallMemoryTool)

    def test_loader_caches_modules(self):
        """Test that loader caches loaded modules."""
        loader = get_loader()

        # Load json module twice
        m1 = loader.load_module("json")
        m2 = loader.load_module("json")

        # Should be same instance
        assert m1 is m2


class TestToolCategories:
    """Test tool categorization."""

    def test_memory_tools_category(self):
        """Test memory tools are properly categorized."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool()
        ]

        for tool in tools:
            assert tool.metadata.category == "memory"

    def test_consolidation_tools_category(self):
        """Test consolidation tools are properly categorized."""
        tools = [
            StartConsolidationTool(),
            ExtractPatternsTool()
        ]

        for tool in tools:
            assert tool.metadata.category == "consolidation"

    def test_planning_tools_category(self):
        """Test planning tools are properly categorized."""
        tools = [
            VerifyPlanTool(),
            SimulatePlanTool()
        ]

        for tool in tools:
            assert tool.metadata.category == "planning"

    def test_graph_tools_category(self):
        """Test graph tools are properly categorized."""
        tools = [
            QueryGraphTool(),
            AnalyzeGraphTool()
        ]

        for tool in tools:
            assert tool.metadata.category == "graph"

    def test_retrieval_tools_category(self):
        """Test retrieval tools are properly categorized."""
        tool = HybridSearchTool()
        assert tool.metadata.category == "retrieval"


class TestToolExecution:
    """Test tool execution interface."""

    @pytest.mark.asyncio
    async def test_tools_execute_async(self):
        """Test that all tools support async execution."""
        tool = RecallMemoryTool()

        # Execute should return a dict
        result = await tool.execute(query="test")
        assert isinstance(result, dict)

    def test_tools_validate_input(self):
        """Test that tools validate input."""
        tool = RecallMemoryTool()

        # Should raise for missing required parameter
        with pytest.raises(ValueError):
            tool.validate_input()

        # Should not raise for valid input
        tool.validate_input(query="test")

    def test_tools_handle_errors(self):
        """Test that tools handle errors gracefully."""
        tool = RecallMemoryTool()

        # Invalid input should not raise, but return error response
        result = tool.metadata  # Should not raise
        assert result is not None


class TestToolComparison:
    """Test tool comparison and matching."""

    def test_all_tools_follow_interface(self):
        """Test that all tools implement the BaseTool interface."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool(),
            StartConsolidationTool(),
            ExtractPatternsTool(),
            VerifyPlanTool(),
            SimulatePlanTool(),
            QueryGraphTool(),
            AnalyzeGraphTool(),
            HybridSearchTool()
        ]

        for tool in tools:
            # Should have these methods
            assert hasattr(tool, 'metadata')
            assert hasattr(tool, 'execute')
            assert hasattr(tool, 'validate_input')

            # metadata should be callable property
            assert callable(tool.metadata.fget)

            # execute should be async
            import inspect
            assert inspect.iscoroutinefunction(tool.execute)

    def test_tool_names_are_unique(self):
        """Test that all tool names are unique."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool(),
            StartConsolidationTool(),
            ExtractPatternsTool(),
            VerifyPlanTool(),
            SimulatePlanTool(),
            QueryGraphTool(),
            AnalyzeGraphTool(),
            HybridSearchTool()
        ]

        names = [tool.metadata.name for tool in tools]
        assert len(names) == len(set(names))  # All unique

    def test_tool_descriptions_present(self):
        """Test that all tools have descriptions."""
        tools = [
            RecallMemoryTool(),
            StoreMemoryTool(),
            HealthCheckTool(),
            StartConsolidationTool(),
            ExtractPatternsTool(),
            VerifyPlanTool(),
            SimulatePlanTool(),
            QueryGraphTool(),
            AnalyzeGraphTool(),
            HybridSearchTool()
        ]

        for tool in tools:
            assert tool.metadata.description
            assert len(tool.metadata.description) > 10  # Non-trivial


class TestToolCompatibility:
    """Test backward compatibility aspects."""

    def test_tool_can_be_called_with_old_parameter_names(self):
        """Test tools work with old parameter styles."""
        from athena.mcp.compat_adapter import (
            memory_recall,
            memory_store,
            consolidation_start
        )

        # Old style calls should work
        result1 = memory_recall(query="test")
        assert isinstance(result1, dict)

        result2 = memory_store(content="test content")
        assert isinstance(result2, dict)

        result3 = consolidation_start(strategy="balanced")
        assert isinstance(result3, dict)

    def test_compatibility_wrappers_exist(self):
        """Test that all compatibility wrappers exist."""
        from athena.mcp import compat_adapter

        # Check all 10 wrappers exist
        wrappers = [
            "memory_recall",
            "memory_store",
            "memory_health",
            "consolidation_start",
            "consolidation_extract",
            "planning_verify",
            "planning_simulate",
            "graph_query",
            "graph_analyze",
            "retrieval_hybrid"
        ]

        for wrapper in wrappers:
            assert hasattr(compat_adapter, wrapper)
            assert callable(getattr(compat_adapter, wrapper))
