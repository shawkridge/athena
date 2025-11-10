"""Tests for tool base classes."""

import pytest
from datetime import datetime
from athena.mcp.tools.base import (
    BaseTool,
    ToolMetadata,
    ToolResult,
    ToolStatus,
    ToolDependency,
)


class MockTool(BaseTool):
    """Mock tool for testing."""

    async def execute(self, **params):
        """Mock execute method."""
        # Validate params if needed
        error = self.validate_params(params, ["query"])
        if error:
            return ToolResult.error(error)

        # Simulate execution
        result = ToolResult.success(
            data={"result": f"Executed with query: {params['query']}"},
            message="Mock execution successful"
        )
        self.log_execution(params, result)
        return result


@pytest.fixture
def tool_metadata():
    """Create test tool metadata."""
    return ToolMetadata(
        name="test_tool",
        description="Test tool for unit testing",
        category="test",
        version="1.0",
        parameters={
            "query": {"type": "string", "description": "Query string"}
        },
        tags=["test", "mock"]
    )


@pytest.fixture
def mock_tool(tool_metadata):
    """Create mock tool instance."""
    return MockTool(tool_metadata)


class TestToolMetadata:
    """Test ToolMetadata class."""

    def test_metadata_creation(self, tool_metadata):
        """Test creating tool metadata."""
        assert tool_metadata.name == "test_tool"
        assert tool_metadata.description == "Test tool for unit testing"
        assert tool_metadata.category == "test"
        assert "test" in tool_metadata.tags

    def test_metadata_to_dict(self, tool_metadata):
        """Test converting metadata to dictionary."""
        metadata_dict = tool_metadata.to_dict()
        assert metadata_dict["name"] == "test_tool"
        assert metadata_dict["category"] == "test"
        assert metadata_dict["deprecated"] is False


class TestToolResult:
    """Test ToolResult class."""

    def test_success_result(self):
        """Test creating success result."""
        result = ToolResult.success(data={"key": "value"})
        assert result.status == ToolStatus.SUCCESS
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_error_result(self):
        """Test creating error result."""
        result = ToolResult.error("Something went wrong")
        assert result.status == ToolStatus.ERROR
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ToolResult.success(data={"key": "value"}, message="Success")
        result_dict = result.to_dict()
        assert result_dict["status"] == "success"
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["message"] == "Success"
        assert "timestamp" in result_dict

    def test_result_with_metadata(self):
        """Test result with additional metadata."""
        result = ToolResult.success(
            data={"key": "value"},
            metadata={"processing_time_ms": 150, "version": "1.0"}
        )
        result_dict = result.to_dict()
        assert result_dict["metadata"]["processing_time_ms"] == 150


class TestBaseTool:
    """Test BaseTool class."""

    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_tool):
        """Test executing a tool."""
        result = await mock_tool.execute(query="test")
        assert result.status == ToolStatus.SUCCESS
        assert "test" in result.data["result"]

    @pytest.mark.asyncio
    async def test_tool_execution_missing_param(self, mock_tool):
        """Test tool execution with missing required param."""
        result = await mock_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    def test_validate_params_success(self, mock_tool):
        """Test parameter validation success."""
        error = mock_tool.validate_params(
            {"query": "test", "other": "value"},
            ["query"]
        )
        assert error is None

    def test_validate_params_missing(self, mock_tool):
        """Test parameter validation with missing param."""
        error = mock_tool.validate_params({}, ["query"])
        assert error is not None
        assert "Missing required parameter" in error

    def test_validate_params_none_value(self, mock_tool):
        """Test parameter validation with None value."""
        error = mock_tool.validate_params({"query": None}, ["query"])
        assert error is not None
        assert "cannot be None" in error

    def test_tool_metadata_access(self, mock_tool):
        """Test accessing tool metadata."""
        assert mock_tool.metadata.name == "test_tool"
        assert mock_tool.metadata.category == "test"


class TestToolDependency:
    """Test ToolDependency class."""

    def test_dependency_creation_required(self):
        """Test creating required dependency."""
        dep = ToolDependency("other_tool", required=True)
        assert dep.tool_name == "other_tool"
        assert dep.required is True

    def test_dependency_creation_optional(self):
        """Test creating optional dependency."""
        dep = ToolDependency("other_tool", required=False)
        assert dep.tool_name == "other_tool"
        assert dep.required is False
