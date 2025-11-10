"""Tests for agent optimization tools."""

import pytest
from athena.mcp.tools.agent_optimization_tools import (
    TuneAgentTool,
    AnalyzeAgentPerformanceTool,
)
from athena.mcp.tools.base import ToolStatus


class TestTuneAgentTool:
    """Test suite for TuneAgentTool."""

    @pytest.fixture
    def tool(self):
        """Create TuneAgentTool instance."""
        return TuneAgentTool()

    @pytest.mark.asyncio
    async def test_tune_agent_basic(self, tool):
        """Test basic agent tuning."""
        result = await tool.execute(
            agent_id="agent001",
            parameter="learning_rate",
            value=0.01
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["agent_id"] == "agent001"
        assert result.data["parameter"] == "learning_rate"
        assert result.data["new_value"] == 0.01
        assert result.data["validated"] is True

    @pytest.mark.asyncio
    async def test_tune_agent_missing_agent_id(self, tool):
        """Test missing required parameter."""
        result = await tool.execute(
            parameter="learning_rate",
            value=0.01
        )

        assert result.status == ToolStatus.ERROR
        assert "agent_id" in result.error

    @pytest.mark.asyncio
    async def test_tune_agent_invalid_parameter(self, tool):
        """Test invalid parameter name."""
        result = await tool.execute(
            agent_id="agent001",
            parameter="invalid_param",
            value=0.5,
            validation=True
        )

        assert result.status == ToolStatus.ERROR
        assert "Unknown parameter" in result.error

    @pytest.mark.asyncio
    async def test_tune_agent_out_of_range(self, tool):
        """Test parameter value out of valid range."""
        result = await tool.execute(
            agent_id="agent001",
            parameter="learning_rate",
            value=2.0,  # Out of range (0.0001-1.0)
            validation=True
        )

        assert result.status == ToolStatus.ERROR
        assert "must be between" in result.error

    @pytest.mark.asyncio
    async def test_tune_agent_all_parameters(self, tool):
        """Test tuning various parameters."""
        params_to_test = [
            ("learning_rate", 0.001),
            ("temperature", 0.5),
            ("max_depth", 10),
            ("batch_size", 64),
            ("timeout", 600),
            ("retry_limit", 5),
        ]

        for param_name, param_value in params_to_test:
            result = await tool.execute(
                agent_id="agent001",
                parameter=param_name,
                value=param_value
            )
            assert result.status == ToolStatus.SUCCESS
            assert result.data["parameter"] == param_name
            assert result.data["new_value"] == param_value

    @pytest.mark.asyncio
    async def test_tune_agent_skip_validation(self, tool):
        """Test tuning without validation."""
        result = await tool.execute(
            agent_id="agent001",
            parameter="unknown_param",
            value=0.5,
            validation=False
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["validated"] is False

    @pytest.mark.asyncio
    async def test_tune_agent_boundary_values(self, tool):
        """Test parameter boundary values."""
        # Test minimum value
        result = await tool.execute(
            agent_id="agent001",
            parameter="learning_rate",
            value=0.0001
        )
        assert result.status == ToolStatus.SUCCESS

        # Test maximum value
        result = await tool.execute(
            agent_id="agent001",
            parameter="temperature",
            value=2.0
        )
        assert result.status == ToolStatus.SUCCESS


class TestAnalyzeAgentPerformanceTool:
    """Test suite for AnalyzeAgentPerformanceTool."""

    @pytest.fixture
    def tool(self):
        """Create AnalyzeAgentPerformanceTool instance."""
        return AnalyzeAgentPerformanceTool()

    @pytest.mark.asyncio
    async def test_analyze_performance_basic(self, tool):
        """Test basic performance analysis."""
        result = await tool.execute(agent_id="agent001")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["agent_id"] == "agent001"
        assert "metrics" in result.data
        assert "bottlenecks" in result.data
        assert "recommendations" in result.data

    @pytest.mark.asyncio
    async def test_analyze_performance_metrics_present(self, tool):
        """Test that metrics are properly collected."""
        result = await tool.execute(agent_id="agent001")

        metrics = result.data["metrics"]
        assert "success_rate" in metrics
        assert "average_latency_ms" in metrics
        assert "error_rate" in metrics
        assert "total_executions" in metrics

    @pytest.mark.asyncio
    async def test_analyze_performance_detailed(self, tool):
        """Test detailed performance analysis."""
        result = await tool.execute(
            agent_id="agent001",
            detailed=True
        )

        assert result.status == ToolStatus.SUCCESS
        metrics = result.data["metrics"]

        # Check for detailed metrics
        assert "p50_latency_ms" in metrics
        assert "p95_latency_ms" in metrics
        assert "p99_latency_ms" in metrics
        assert "memory_usage_mb" in metrics
        assert "cpu_usage_percent" in metrics

    @pytest.mark.asyncio
    async def test_analyze_performance_timeframes(self, tool):
        """Test different timeframes."""
        for timeframe in ["hour", "day", "week"]:
            result = await tool.execute(
                agent_id="agent001",
                timeframe=timeframe
            )
            assert result.status == ToolStatus.SUCCESS
            assert result.data["timeframe"] == timeframe

    @pytest.mark.asyncio
    async def test_analyze_performance_bottleneck_detection(self, tool):
        """Test bottleneck identification."""
        result = await tool.execute(agent_id="agent001")

        bottlenecks = result.data["bottlenecks"]
        # Check that bottlenecks have proper structure
        for bottleneck in bottlenecks:
            assert "type" in bottleneck
            assert "severity" in bottleneck
            assert "description" in bottleneck

    @pytest.mark.asyncio
    async def test_analyze_performance_recommendations(self, tool):
        """Test recommendation generation."""
        result = await tool.execute(agent_id="agent001")

        recommendations = result.data["recommendations"]
        # Check that recommendations have proper structure
        for rec in recommendations:
            assert "priority" in rec
            assert "action" in rec
            assert "description" in rec

    @pytest.mark.asyncio
    async def test_analyze_performance_missing_agent_id(self, tool):
        """Test missing required parameter."""
        result = await tool.execute()

        assert result.status == ToolStatus.ERROR
        assert "agent_id" in result.error

    @pytest.mark.asyncio
    async def test_analyze_performance_empty_id(self, tool):
        """Test with empty agent ID."""
        result = await tool.execute(agent_id="")

        # Empty string should still be treated as valid parameter
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_analyze_performance_special_characters(self, tool):
        """Test with special characters in agent ID."""
        result = await tool.execute(agent_id="agent_001-special#chars")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["agent_id"] == "agent_001-special#chars"

    @pytest.mark.asyncio
    async def test_analyze_performance_timestamp(self, tool):
        """Test that timestamp is included."""
        result = await tool.execute(agent_id="agent001")

        assert "analysis_timestamp" in result.data
        assert "2025-11-10" in result.data["analysis_timestamp"]


class TestAgentOptimizationIntegration:
    """Integration tests for agent optimization tools."""

    @pytest.mark.asyncio
    async def test_tune_then_analyze(self):
        """Test tuning followed by analysis."""
        tune_tool = TuneAgentTool()
        analyze_tool = AnalyzeAgentPerformanceTool()

        # First tune the agent
        tune_result = await tune_tool.execute(
            agent_id="agent001",
            parameter="learning_rate",
            value=0.01
        )
        assert tune_result.status == ToolStatus.SUCCESS

        # Then analyze performance
        analyze_result = await analyze_tool.execute(agent_id="agent001")
        assert analyze_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_multiple_tuning_operations(self):
        """Test multiple sequential tuning operations."""
        tool = TuneAgentTool()

        operations = [
            ("learning_rate", 0.005),
            ("temperature", 0.8),
            ("max_depth", 8),
        ]

        for param, value in operations:
            result = await tool.execute(
                agent_id="agent001",
                parameter=param,
                value=value
            )
            assert result.status == ToolStatus.SUCCESS
            assert result.data["new_value"] == value
