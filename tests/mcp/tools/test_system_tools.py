"""Tests for system monitoring and health check tools."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from athena.mcp.tools.system_tools import (
    SystemHealthCheckTool,
    HealthReportTool,
    ConsolidationStatusTool,
)
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_mcp_server():
    """Create mock MCP server."""
    server = Mock()
    server._health_checker = None
    return server


@pytest.fixture
def mock_consolidation_system():
    """Create mock consolidation system."""
    system = Mock()
    system.get_pending_count = Mock(return_value=5)
    system.get_last_consolidation_time = Mock(return_value=datetime.now())
    return system


@pytest.fixture
def health_check_tool(mock_mcp_server):
    """Create health check tool instance."""
    return SystemHealthCheckTool(mock_mcp_server)


@pytest.fixture
def health_report_tool(mock_mcp_server):
    """Create health report tool instance."""
    return HealthReportTool(mock_mcp_server)


@pytest.fixture
def consolidation_status_tool(mock_consolidation_system):
    """Create consolidation status tool instance."""
    return ConsolidationStatusTool(mock_consolidation_system)


class TestSystemHealthCheckTool:
    """Test SystemHealthCheckTool functionality."""

    @pytest.mark.asyncio
    async def test_health_check_basic(self, health_check_tool, mock_mcp_server):
        """Test basic health check."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value={
            "status": "healthy",
            "issues": []
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_check_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["status"] == "healthy"
        assert result.data["issue_count"] == 0

    @pytest.mark.asyncio
    async def test_health_check_with_issues(self, health_check_tool, mock_mcp_server):
        """Test health check with issues detected."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value={
            "status": "degraded",
            "issues": ["Memory usage high", "Cache hit rate low"]
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_check_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["status"] == "degraded"
        assert result.data["issue_count"] == 2
        assert len(result.data["issues"]) == 2

    @pytest.mark.asyncio
    async def test_health_check_specific_component(self, health_check_tool, mock_mcp_server):
        """Test health check for specific component."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(return_value={
            "status": "healthy",
            "issues": []
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_check_tool.execute(component="database")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["component"] == "database"

        # Verify component was passed to checker
        mock_health_checker.check.assert_called_with(component="database")

    @pytest.mark.asyncio
    async def test_health_check_error(self, health_check_tool, mock_mcp_server):
        """Test health check when checker fails."""
        # Mock the health checker to fail
        mock_health_checker = AsyncMock()
        mock_health_checker.check = AsyncMock(
            side_effect=Exception("Check failed")
        )
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_check_tool.execute()
        assert result.status == ToolStatus.SUCCESS  # Graceful degradation
        assert result.data["status"] == "unknown"
        assert len(result.data["issues"]) > 0


class TestHealthReportTool:
    """Test HealthReportTool functionality."""

    @pytest.mark.asyncio
    async def test_health_report_basic(self, health_report_tool, mock_mcp_server):
        """Test basic health report generation."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.generate_report = AsyncMock(return_value={
            "summary": "System is healthy",
            "metrics": {}
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_report_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert "System is healthy" in result.data["summary"]

    @pytest.mark.asyncio
    async def test_health_report_with_metrics(self, health_report_tool, mock_mcp_server):
        """Test health report with metrics."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.generate_report = AsyncMock(return_value={
            "summary": "System is healthy",
            "metrics": {
                "cpu_usage": "45%",
                "memory_usage": "62%",
                "disk_usage": "73%"
            }
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_report_tool.execute(include_metrics=True)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["has_metrics"] is True
        assert "cpu_usage" in result.data["metrics"]

    @pytest.mark.asyncio
    async def test_health_report_metrics_not_requested(self, health_report_tool, mock_mcp_server):
        """Test health report without requesting metrics."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.generate_report = AsyncMock(return_value={
            "summary": "System is healthy",
            "metrics": {}  # Empty metrics when not requested
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_report_tool.execute(include_metrics=False)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["metrics"] == {}
        assert result.data["has_metrics"] is False

    @pytest.mark.asyncio
    async def test_health_report_format_parameter(self, health_report_tool, mock_mcp_server):
        """Test health report with different formats."""
        # Mock the health checker
        mock_health_checker = AsyncMock()
        mock_health_checker.generate_report = AsyncMock(return_value={
            "summary": "Report",
            "metrics": {}
        })
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_report_tool.execute(format="detailed")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["format"] == "detailed"

    @pytest.mark.asyncio
    async def test_health_report_error(self, health_report_tool, mock_mcp_server):
        """Test health report when generation fails."""
        # Mock the health checker to fail
        mock_health_checker = AsyncMock()
        mock_health_checker.generate_report = AsyncMock(
            side_effect=Exception("Generation failed")
        )
        mock_mcp_server._health_checker = mock_health_checker

        result = await health_report_tool.execute()
        assert result.status == ToolStatus.SUCCESS  # Graceful degradation
        assert "error" in result.data["summary"].lower() or "Report generation error" in result.data["summary"]


class TestConsolidationStatusTool:
    """Test ConsolidationStatusTool functionality."""

    @pytest.mark.asyncio
    async def test_consolidation_status_basic(self, consolidation_status_tool):
        """Test basic consolidation status check."""
        result = await consolidation_status_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["status"] == "operational"

    @pytest.mark.asyncio
    async def test_consolidation_status_pending_events(self, consolidation_status_tool):
        """Test consolidation status with pending events."""
        result = await consolidation_status_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["pending_events"] == 5

    @pytest.mark.asyncio
    async def test_consolidation_status_last_time(self, consolidation_status_tool):
        """Test consolidation status includes last consolidation time."""
        result = await consolidation_status_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["last_consolidation"] is not None

    @pytest.mark.asyncio
    async def test_consolidation_status_no_methods(self, mock_consolidation_system):
        """Test consolidation status when system has no methods."""
        # Create system without methods
        simple_system = Mock(spec=[])
        tool = ConsolidationStatusTool(simple_system)

        result = await tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["status"] == "operational"
        assert result.data["pending_events"] == 0


class TestSystemToolsMetadata:
    """Test metadata for system tools."""

    def test_health_check_metadata(self, health_check_tool):
        """Test health check tool metadata."""
        assert health_check_tool.metadata.name == "check_system_health"
        assert "health" in health_check_tool.metadata.tags
        assert health_check_tool.metadata.category == "system"

    def test_health_report_metadata(self, health_report_tool):
        """Test health report tool metadata."""
        assert health_report_tool.metadata.name == "get_health_report"
        assert "reporting" in health_report_tool.metadata.tags
        assert health_report_tool.metadata.category == "system"

    def test_consolidation_status_metadata(self, consolidation_status_tool):
        """Test consolidation status tool metadata."""
        assert consolidation_status_tool.metadata.name == "get_consolidation_status"
        assert "consolidation" in consolidation_status_tool.metadata.tags
        assert consolidation_status_tool.metadata.category == "system"

    def test_health_check_parameters(self, health_check_tool):
        """Test health check tool parameters."""
        params = health_check_tool.metadata.parameters
        assert "component" in params

    def test_health_report_parameters(self, health_report_tool):
        """Test health report tool parameters."""
        params = health_report_tool.metadata.parameters
        assert "include_metrics" in params
        assert "format" in params
