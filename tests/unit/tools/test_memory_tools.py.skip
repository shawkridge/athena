"""Tests for memory tools (recall, store, health)."""
import pytest
from athena.tools.memory.recall import RecallMemoryTool


class TestRecallMemoryTool:
    """Test RecallMemoryTool functionality."""

    def test_metadata(self):
        """Test tool metadata structure."""
        tool = RecallMemoryTool()
        metadata = tool.metadata

        assert metadata.name == "recall"
        assert metadata.category == "memory"
        assert "query" in metadata.parameters
        assert "results" in metadata.returns["properties"]

    def test_metadata_required_parameters(self):
        """Test that metadata lists required parameters."""
        tool = RecallMemoryTool()
        metadata = tool.metadata

        # query is required
        assert metadata.parameters["query"].get("required") is True
        # Others are optional
        assert metadata.parameters.get("limit", {}).get("required") is not True

    def test_validate_empty_query(self):
        """Test validation rejects empty query."""
        tool = RecallMemoryTool()

        with pytest.raises(ValueError, match="required"):
            tool.validate_input(query="")

        with pytest.raises(ValueError, match="required"):
            tool.validate_input(query="   ")

    def test_validate_missing_query(self):
        """Test validation requires query parameter."""
        tool = RecallMemoryTool()

        with pytest.raises(ValueError, match="required"):
            tool.validate_input()

    def test_validate_query_too_long(self):
        """Test validation rejects overly long queries."""
        tool = RecallMemoryTool()

        long_query = "x" * 10001
        with pytest.raises(ValueError, match="less than 10,000"):
            tool.validate_input(query=long_query)

    def test_validate_invalid_limit(self):
        """Test validation validates limit parameter."""
        tool = RecallMemoryTool()

        # Negative limit
        with pytest.raises(ValueError, match="between 1 and 100"):
            tool.validate_input(query="test", limit=-1)

        # Zero limit
        with pytest.raises(ValueError, match="between 1 and 100"):
            tool.validate_input(query="test", limit=0)

        # Limit too high
        with pytest.raises(ValueError, match="between 1 and 100"):
            tool.validate_input(query="test", limit=101)

        # Non-integer limit
        with pytest.raises(ValueError, match="between 1 and 100"):
            tool.validate_input(query="test", limit=5.5)

    def test_validate_valid_limit(self):
        """Test validation accepts valid limit values."""
        tool = RecallMemoryTool()

        # Should not raise
        tool.validate_input(query="test", limit=1)
        tool.validate_input(query="test", limit=50)
        tool.validate_input(query="test", limit=100)

    def test_validate_invalid_query_type(self):
        """Test validation validates query_type parameter."""
        tool = RecallMemoryTool()

        with pytest.raises(ValueError, match="query_type must be one of"):
            tool.validate_input(query="test", query_type="invalid_type")

    def test_validate_valid_query_types(self):
        """Test validation accepts valid query types."""
        tool = RecallMemoryTool()
        valid_types = ["temporal", "factual", "relational", "procedural", "prospective", "meta", "planning", "auto"]

        for query_type in valid_types:
            # Should not raise
            tool.validate_input(query="test", query_type=query_type)

    def test_validate_invalid_relevance(self):
        """Test validation validates min_relevance parameter."""
        tool = RecallMemoryTool()

        # Below range
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            tool.validate_input(query="test", min_relevance=-0.5)

        # Above range
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            tool.validate_input(query="test", min_relevance=1.5)

        # Non-numeric
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            tool.validate_input(query="test", min_relevance="0.5")

    def test_validate_valid_relevance(self):
        """Test validation accepts valid relevance scores."""
        tool = RecallMemoryTool()

        # Should not raise
        tool.validate_input(query="test", min_relevance=0.0)
        tool.validate_input(query="test", min_relevance=0.5)
        tool.validate_input(query="test", min_relevance=1.0)

    @pytest.mark.asyncio
    async def test_execute_basic(self):
        """Test basic tool execution."""
        tool = RecallMemoryTool()
        result = await tool.execute(query="test query")

        assert isinstance(result, dict)
        assert "query" in result
        assert "results" in result
        assert "search_time_ms" in result
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_with_all_parameters(self):
        """Test execution with all parameters."""
        tool = RecallMemoryTool()
        result = await tool.execute(
            query="test query",
            query_type="factual",
            limit=5,
            include_metadata=True,
            min_relevance=0.5
        )

        assert result["status"] == "success"
        assert result["query"] == "test query"
        assert result["query_type"] == "factual"

    @pytest.mark.asyncio
    async def test_execute_defaults(self):
        """Test execution uses correct defaults."""
        tool = RecallMemoryTool()
        result = await tool.execute(query="test")

        assert result["query_type"] == "auto"
        assert result["total_results"] == 0
        assert result["returned_results"] == 0

    @pytest.mark.asyncio
    async def test_execute_invalid_input_returns_error(self):
        """Test that invalid input returns error response."""
        tool = RecallMemoryTool()

        # Missing query
        result = await tool.execute()
        assert result.get("status") == "error"
        assert "error" in result

        # Invalid query type
        result = await tool.execute(query="test", query_type="invalid")
        assert result.get("status") == "error"

    @pytest.mark.asyncio
    async def test_execute_timing(self):
        """Test that execution timing is recorded."""
        tool = RecallMemoryTool()
        result = await tool.execute(query="test")

        assert "search_time_ms" in result
        assert isinstance(result["search_time_ms"], (int, float))
        assert result["search_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_empty_results(self):
        """Test execution returns proper structure for empty results."""
        tool = RecallMemoryTool()
        result = await tool.execute(query="no results")

        assert isinstance(result["results"], list)
        assert len(result["results"]) == 0
        assert result["total_results"] == 0
        assert result["returned_results"] == 0

    def test_instantiation(self):
        """Test tool can be instantiated."""
        tool = RecallMemoryTool()
        assert tool is not None
        assert hasattr(tool, "metadata")
        assert hasattr(tool, "execute")
        assert hasattr(tool, "validate_input")
