"""Tests for BaseTool base class."""
import pytest
from athena.tools import BaseTool, ToolMetadata


class SimpleTool(BaseTool):
    """Simple tool implementation for testing."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="simple",
            category="test",
            description="A simple test tool",
            parameters={"input": {"type": "string"}},
            returns={"type": "object"}
        )

    async def execute(self, **kwargs):
        return {"result": kwargs.get("input", "no input")}


class ValidatingTool(BaseTool):
    """Tool with custom validation."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="validating",
            category="test",
            description="A tool with validation"
        )

    def validate_input(self, **kwargs):
        """Validate that required_param is present."""
        if "required_param" not in kwargs:
            raise ValueError("required_param is required")

    async def execute(self, **kwargs):
        return {"param": kwargs["required_param"]}


class TestBaseTool:
    """Test BaseTool abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseTool cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseTool()

    def test_simple_tool_instantiation(self):
        """Test creating a simple tool."""
        tool = SimpleTool()
        assert tool is not None

    def test_metadata_property(self):
        """Test accessing tool metadata."""
        tool = SimpleTool()
        metadata = tool.metadata

        assert isinstance(metadata, ToolMetadata)
        assert metadata.name == "simple"
        assert metadata.category == "test"
        assert metadata.description == "A simple test tool"

    def test_metadata_parameters(self):
        """Test metadata parameters."""
        tool = SimpleTool()
        metadata = tool.metadata

        assert "input" in metadata.parameters
        assert metadata.parameters["input"]["type"] == "string"

    def test_metadata_returns(self):
        """Test metadata returns."""
        tool = SimpleTool()
        metadata = tool.metadata

        assert metadata.returns["type"] == "object"

    @pytest.mark.asyncio
    async def test_execute_method(self):
        """Test executing a tool."""
        tool = SimpleTool()
        result = await tool.execute(input="test")

        assert result == {"result": "test"}

    @pytest.mark.asyncio
    async def test_execute_without_input(self):
        """Test executing tool without input."""
        tool = SimpleTool()
        result = await tool.execute()

        assert result == {"result": "no input"}

    def test_validate_input_default(self):
        """Test default validation does nothing."""
        tool = SimpleTool()
        # Should not raise
        tool.validate_input(anything="goes")

    def test_validate_input_custom(self):
        """Test custom validation."""
        tool = ValidatingTool()

        # Valid input should not raise
        tool.validate_input(required_param="value")

        # Invalid input should raise
        with pytest.raises(ValueError, match="required_param is required"):
            tool.validate_input()

    @pytest.mark.asyncio
    async def test_tool_with_validation_flow(self):
        """Test typical tool execution flow with validation."""
        tool = ValidatingTool()

        # Validate input first
        tool.validate_input(required_param="test_value")

        # Then execute
        result = await tool.execute(required_param="test_value")
        assert result == {"param": "test_value"}

    def test_tool_metadata_serializable(self):
        """Test that metadata is serializable to dict."""
        tool = SimpleTool()
        metadata = tool.metadata

        # Should be Pydantic model, serializable
        metadata_dict = metadata.model_dump()
        assert isinstance(metadata_dict, dict)
        assert metadata_dict["name"] == "simple"


class TestToolMetadata:
    """Test ToolMetadata model."""

    def test_create_metadata(self):
        """Test creating metadata."""
        metadata = ToolMetadata(
            name="test",
            category="general",
            description="Test tool"
        )

        assert metadata.name == "test"
        assert metadata.category == "general"

    def test_metadata_with_parameters(self):
        """Test metadata with parameters."""
        metadata = ToolMetadata(
            name="test",
            category="general",
            description="Test tool",
            parameters={
                "param1": {"type": "string", "required": True},
                "param2": {"type": "int", "required": False}
            }
        )

        assert len(metadata.parameters) == 2
        assert metadata.parameters["param1"]["type"] == "string"

    def test_metadata_with_returns(self):
        """Test metadata with return type."""
        metadata = ToolMetadata(
            name="test",
            category="general",
            description="Test tool",
            returns={
                "type": "object",
                "properties": {"status": {"type": "string"}}
            }
        )

        assert metadata.returns["type"] == "object"

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = ToolMetadata(
            name="test",
            category="general",
            description="Test tool"
        )

        assert metadata.parameters == {}
        assert metadata.returns == {}

    def test_metadata_model_dump(self):
        """Test serializing metadata to dict."""
        metadata = ToolMetadata(
            name="test",
            category="general",
            description="Test tool",
            parameters={"x": {"type": "string"}}
        )

        data = metadata.model_dump()
        assert data["name"] == "test"
        assert data["category"] == "general"
        assert "x" in data["parameters"]


class TestToolImplementationPatterns:
    """Test common tool implementation patterns."""

    def test_tool_with_required_kwargs(self):
        """Test tool that requires specific kwargs."""

        class QueryTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="query",
                    category="memory",
                    description="Query memory"
                )

            def validate_input(self, **kwargs):
                if "query" not in kwargs:
                    raise ValueError("query required")

            async def execute(self, **kwargs):
                query = kwargs["query"]
                return {"query": query, "results": []}

        tool = QueryTool()
        with pytest.raises(ValueError):
            tool.validate_input()

    @pytest.mark.asyncio
    async def test_tool_with_optional_parameters(self):
        """Test tool with optional parameters."""

        class SearchTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="search",
                    category="memory",
                    description="Search memory"
                )

            async def execute(self, **kwargs):
                query = kwargs.get("query", "")
                limit = kwargs.get("limit", 10)
                return {"query": query, "limit": limit, "results": []}

        tool = SearchTool()
        result = await tool.execute(query="test", limit=5)
        assert result["limit"] == 5

        result = await tool.execute(query="test")
        assert result["limit"] == 10

    @pytest.mark.asyncio
    async def test_tool_returning_structured_data(self):
        """Test tool returning structured results."""

        class StatsTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="stats",
                    category="system",
                    description="Get system stats"
                )

            async def execute(self, **kwargs):
                return {
                    "status": "ok",
                    "stats": {
                        "memory": {"used": 100, "total": 1000},
                        "tools": {"loaded": 5, "available": 20}
                    }
                }

        tool = StatsTool()
        result = await tool.execute()

        assert result["status"] == "ok"
        assert result["stats"]["memory"]["used"] == 100
        assert result["stats"]["tools"]["loaded"] == 5
