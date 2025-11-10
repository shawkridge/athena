"""Tests for retrieval and integration tools."""

import pytest
from unittest.mock import Mock, AsyncMock
from athena.mcp.tools.retrieval_tools import SmartRetrieveTool, AnalyzeCoverageTool
from athena.mcp.tools.integration_tools import ConsolidateTool, RunConsolidationTool
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_memory_store():
    """Create mock memory store."""
    store = Mock()
    store.recall_with_reranking = Mock(return_value=[])
    return store


@pytest.fixture
def mock_project_manager():
    """Create mock project manager."""
    manager = Mock()
    mock_project = Mock()
    mock_project.id = 1
    manager.require_project = Mock(return_value=mock_project)
    return manager


@pytest.fixture
def mock_consolidation_system():
    """Create mock consolidation system."""
    return Mock()


@pytest.fixture
def smart_retrieve_tool(mock_memory_store, mock_project_manager):
    """Create smart retrieve tool."""
    return SmartRetrieveTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def analyze_coverage_tool(mock_memory_store, mock_project_manager):
    """Create analyze coverage tool."""
    return AnalyzeCoverageTool(mock_memory_store, mock_project_manager)


@pytest.fixture
def consolidate_tool(mock_consolidation_system, mock_project_manager):
    """Create consolidate tool."""
    return ConsolidateTool(mock_consolidation_system, mock_project_manager)


@pytest.fixture
def run_consolidation_tool(mock_consolidation_system, mock_project_manager):
    """Create run consolidation tool."""
    return RunConsolidationTool(mock_consolidation_system, mock_project_manager)


class TestSmartRetrieveTool:
    """Test SmartRetrieveTool functionality."""

    @pytest.mark.asyncio
    async def test_smart_retrieve_missing_query(self, smart_retrieve_tool):
        """Test smart retrieve with missing query."""
        result = await smart_retrieve_tool.execute()
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_smart_retrieve_basic(self, smart_retrieve_tool, mock_memory_store):
        """Test basic smart retrieval."""
        mock_memory_store.recall_with_reranking.return_value = []
        result = await smart_retrieve_tool.execute(query="test")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 0

    @pytest.mark.asyncio
    async def test_smart_retrieve_with_strategy(self, smart_retrieve_tool, mock_memory_store):
        """Test smart retrieve with custom strategy."""
        mock_memory_store.recall_with_reranking.return_value = []
        result = await smart_retrieve_tool.execute(query="test", strategy="hyde")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["strategy"] == "hyde"

    @pytest.mark.asyncio
    async def test_smart_retrieve_with_threshold(self, smart_retrieve_tool, mock_memory_store):
        """Test smart retrieve with threshold filter."""
        mock_memory_store.recall_with_reranking.return_value = []
        result = await smart_retrieve_tool.execute(query="test", threshold=0.8)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["threshold"] == 0.8


class TestAnalyzeCoverageTool:
    """Test AnalyzeCoverageTool functionality."""

    @pytest.mark.asyncio
    async def test_analyze_coverage_basic(self, analyze_coverage_tool):
        """Test basic coverage analysis."""
        result = await analyze_coverage_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "coverage_score" in result.data
        assert "gaps" in result.data

    @pytest.mark.asyncio
    async def test_analyze_coverage_with_domain(self, analyze_coverage_tool):
        """Test coverage analysis with domain."""
        result = await analyze_coverage_tool.execute(domain="programming")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["domain"] == "programming"

    @pytest.mark.asyncio
    async def test_analyze_coverage_detail_levels(self, analyze_coverage_tool):
        """Test coverage analysis with different detail levels."""
        for level in ["summary", "detailed", "comprehensive"]:
            result = await analyze_coverage_tool.execute(detail_level=level)
            assert result.status == ToolStatus.SUCCESS
            assert result.data["detail_level"] == level

    @pytest.mark.asyncio
    async def test_analyze_coverage_returns_recommendations(self, analyze_coverage_tool):
        """Test that coverage analysis returns recommendations."""
        result = await analyze_coverage_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "recommendations" in result.data
        assert len(result.data["recommendations"]) > 0


class TestConsolidateTool:
    """Test ConsolidateTool functionality."""

    @pytest.mark.asyncio
    async def test_consolidate_basic(self, consolidate_tool):
        """Test basic consolidation."""
        result = await consolidate_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "consolidation_id" in result.data
        assert "status" in result.data

    @pytest.mark.asyncio
    async def test_consolidate_with_strategy(self, consolidate_tool):
        """Test consolidation with strategy."""
        for strategy in ["balanced", "speed", "quality"]:
            result = await consolidate_tool.execute(strategy=strategy)
            assert result.status == ToolStatus.SUCCESS
            assert result.data["strategy"] == strategy

    @pytest.mark.asyncio
    async def test_consolidate_with_hours(self, consolidate_tool):
        """Test consolidation with custom hours."""
        result = await consolidate_tool.execute(hours=48)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["hours"] == 48

    @pytest.mark.asyncio
    async def test_consolidate_returns_stats(self, consolidate_tool):
        """Test that consolidation returns statistics."""
        result = await consolidate_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "events_processed" in result.data
        assert "memories_created" in result.data


class TestRunConsolidationTool:
    """Test RunConsolidationTool functionality."""

    @pytest.mark.asyncio
    async def test_run_consolidation_basic(self, run_consolidation_tool):
        """Test basic consolidation run."""
        result = await run_consolidation_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "run_id" in result.data

    @pytest.mark.asyncio
    async def test_run_consolidation_with_strategy(self, run_consolidation_tool):
        """Test consolidation run with strategy."""
        for strategy in ["balanced", "speed", "quality", "minimal"]:
            result = await run_consolidation_tool.execute(strategy=strategy)
            assert result.status == ToolStatus.SUCCESS
            assert result.data["strategy"] == strategy

    @pytest.mark.asyncio
    async def test_run_consolidation_with_batch_size(self, run_consolidation_tool):
        """Test consolidation run with custom batch size."""
        result = await run_consolidation_tool.execute(batch_size=50)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["batch_size"] == 50

    @pytest.mark.asyncio
    async def test_run_consolidation_with_validation(self, run_consolidation_tool):
        """Test consolidation run with validation."""
        result = await run_consolidation_tool.execute(validate=True)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["validate"] is True

    @pytest.mark.asyncio
    async def test_run_consolidation_without_validation(self, run_consolidation_tool):
        """Test consolidation run without validation."""
        result = await run_consolidation_tool.execute(validate=False)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["validate"] is False


class TestRetrievalToolsMetadata:
    """Test metadata for retrieval tools."""

    def test_smart_retrieve_metadata(self, smart_retrieve_tool):
        """Test smart retrieve metadata."""
        assert smart_retrieve_tool.metadata.name == "smart_retrieve"
        assert "retrieval" in smart_retrieve_tool.metadata.tags
        assert smart_retrieve_tool.metadata.category == "retrieval"

    def test_analyze_coverage_metadata(self, analyze_coverage_tool):
        """Test analyze coverage metadata."""
        assert analyze_coverage_tool.metadata.name == "analyze_coverage"
        assert "analysis" in analyze_coverage_tool.metadata.tags
        assert analyze_coverage_tool.metadata.category == "retrieval"


class TestIntegrationToolsMetadata:
    """Test metadata for integration tools."""

    def test_consolidate_metadata(self, consolidate_tool):
        """Test consolidate metadata."""
        assert consolidate_tool.metadata.name == "consolidate"
        assert "consolidation" in consolidate_tool.metadata.tags
        assert consolidate_tool.metadata.category == "integration"

    def test_run_consolidation_metadata(self, run_consolidation_tool):
        """Test run consolidation metadata."""
        assert run_consolidation_tool.metadata.name == "run_consolidation"
        assert "consolidation" in run_consolidation_tool.metadata.tags
        assert run_consolidation_tool.metadata.category == "integration"
