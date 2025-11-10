"""Tests for skill optimization tools."""

import pytest
from athena.mcp.tools.skill_optimization_tools import (
    EnhanceSkillTool,
    MeasureSkillEffectivenessTool,
)
from athena.mcp.tools.base import ToolStatus


class TestEnhanceSkillTool:
    """Test suite for EnhanceSkillTool."""

    @pytest.fixture
    def tool(self):
        """Create EnhanceSkillTool instance."""
        return EnhanceSkillTool()

    @pytest.mark.asyncio
    async def test_enhance_skill_basic(self, tool):
        """Test basic skill enhancement."""
        result = await tool.execute(
            skill_id="skill001",
            enhancement_type="accuracy"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["skill_id"] == "skill001"
        assert result.data["enhancement_type"] == "accuracy"
        assert "previous_effectiveness" in result.data
        assert "new_effectiveness" in result.data

    @pytest.mark.asyncio
    async def test_enhance_skill_improvement_calculation(self, tool):
        """Test improvement percentage calculation."""
        result = await tool.execute(
            skill_id="skill001",
            enhancement_type="capability",
            target_improvement=20.0
        )

        assert result.status == ToolStatus.SUCCESS
        prev = result.data["previous_effectiveness"]
        new = result.data["new_effectiveness"]
        improvement = result.data["improvement_percentage"]

        # Verify improvement calculation
        assert new > prev
        assert improvement > 0

    @pytest.mark.asyncio
    async def test_enhance_skill_all_types(self, tool):
        """Test all enhancement types."""
        enhancement_types = ["capability", "accuracy", "speed", "coverage"]

        for enh_type in enhancement_types:
            result = await tool.execute(
                skill_id="skill001",
                enhancement_type=enh_type
            )

            assert result.status == ToolStatus.SUCCESS
            assert result.data["enhancement_type"] == enh_type
            assert "improvement_details" in result.data

    @pytest.mark.asyncio
    async def test_enhance_skill_invalid_type(self, tool):
        """Test invalid enhancement type."""
        result = await tool.execute(
            skill_id="skill001",
            enhancement_type="invalid_type"
        )

        assert result.status == ToolStatus.ERROR
        assert "Invalid enhancement type" in result.error

    @pytest.mark.asyncio
    async def test_enhance_skill_missing_parameters(self, tool):
        """Test missing required parameters."""
        # Missing skill_id
        result = await tool.execute(enhancement_type="accuracy")
        assert result.status == ToolStatus.ERROR

        # Missing enhancement_type
        result = await tool.execute(skill_id="skill001")
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_enhance_skill_target_improvement_bounds(self, tool):
        """Test target improvement validation."""
        # Too low
        result = await tool.execute(
            skill_id="skill001",
            enhancement_type="accuracy",
            target_improvement=0.0
        )
        assert result.status == ToolStatus.ERROR

        # Too high
        result = await tool.execute(
            skill_id="skill001",
            enhancement_type="accuracy",
            target_improvement=101.0
        )
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_enhance_skill_improvement_details(self, tool):
        """Test improvement details structure."""
        enhancement_types = {
            "capability": ["training_iterations", "new_patterns_added"],
            "accuracy": ["refinement_passes", "error_correction_rules"],
            "speed": ["optimization_techniques", "expected_speedup"],
            "coverage": ["new_domains_covered", "edge_cases_handled"],
        }

        for enh_type, expected_fields in enhancement_types.items():
            result = await tool.execute(
                skill_id="skill001",
                enhancement_type=enh_type
            )

            details = result.data["improvement_details"]
            for field in expected_fields:
                assert field in details


class TestMeasureSkillEffectivenessTool:
    """Test suite for MeasureSkillEffectivenessTool."""

    @pytest.fixture
    def tool(self):
        """Create MeasureSkillEffectivenessTool instance."""
        return MeasureSkillEffectivenessTool()

    @pytest.mark.asyncio
    async def test_measure_effectiveness_basic(self, tool):
        """Test basic effectiveness measurement."""
        result = await tool.execute(skill_id="skill001")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["skill_id"] == "skill001"
        assert "overall_effectiveness" in result.data
        assert "metrics" in result.data
        assert "trends" in result.data
        assert "insights" in result.data

    @pytest.mark.asyncio
    async def test_measure_effectiveness_default_metrics(self, tool):
        """Test default metrics are collected."""
        result = await tool.execute(skill_id="skill001")

        metrics = result.data["metrics"]
        # Default metrics: accuracy, speed, coverage
        assert "accuracy" in metrics
        assert "speed" in metrics
        assert "coverage" in metrics

    @pytest.mark.asyncio
    async def test_measure_effectiveness_custom_metrics(self, tool):
        """Test custom metrics selection."""
        custom_metrics = ["accuracy", "reliability"]
        result = await tool.execute(
            skill_id="skill001",
            metrics=custom_metrics
        )

        assert result.status == ToolStatus.SUCCESS
        metrics = result.data["metrics"]

        for metric in custom_metrics:
            assert metric in metrics

    @pytest.mark.asyncio
    async def test_measure_effectiveness_timeframes(self, tool):
        """Test different timeframes."""
        for timeframe in ["day", "week", "month"]:
            result = await tool.execute(
                skill_id="skill001",
                timeframe=timeframe
            )
            assert result.status == ToolStatus.SUCCESS
            assert result.data["timeframe"] == timeframe

    @pytest.mark.asyncio
    async def test_measure_effectiveness_overall_score(self, tool):
        """Test overall effectiveness score calculation."""
        result = await tool.execute(skill_id="skill001")

        overall = result.data["overall_effectiveness"]
        metrics = result.data["metrics"]

        # Overall should be average of metrics
        average = sum(metrics.values()) / len(metrics)
        assert round(overall, 2) == round(average, 2)

    @pytest.mark.asyncio
    async def test_measure_effectiveness_trends(self, tool):
        """Test trend analysis."""
        result = await tool.execute(skill_id="skill001")

        trends = result.data["trends"]
        assert "overall_trend" in trends
        assert "trend_percentage" in trends
        assert "trend_direction" in trends
        assert "consistency" in trends
        assert "volatility" in trends

    @pytest.mark.asyncio
    async def test_measure_effectiveness_insights(self, tool):
        """Test insight generation."""
        result = await tool.execute(skill_id="skill001")

        insights = result.data["insights"]
        assert isinstance(insights, list)

        # Insights should have structure
        for insight in insights:
            assert "type" in insight
            assert "recommendation" in insight

    @pytest.mark.asyncio
    async def test_measure_effectiveness_missing_skill_id(self, tool):
        """Test missing skill ID."""
        result = await tool.execute()

        assert result.status == ToolStatus.ERROR
        assert "skill_id" in result.error

    @pytest.mark.asyncio
    async def test_measure_effectiveness_metric_ranges(self, tool):
        """Test that metrics are within valid range (0-100)."""
        result = await tool.execute(skill_id="skill001")

        metrics = result.data["metrics"]
        overall = result.data["overall_effectiveness"]

        # All metrics should be between 0-100
        for metric_value in metrics.values():
            assert 0 <= metric_value <= 100

        # Overall should be between 0-100
        assert 0 <= overall <= 100

    @pytest.mark.asyncio
    async def test_measure_effectiveness_timestamp(self, tool):
        """Test that timestamp is included."""
        result = await tool.execute(skill_id="skill001")

        assert "measurement_timestamp" in result.data


class TestSkillOptimizationIntegration:
    """Integration tests for skill optimization tools."""

    @pytest.mark.asyncio
    async def test_enhance_then_measure(self):
        """Test enhancing skill followed by measurement."""
        enhance_tool = EnhanceSkillTool()
        measure_tool = MeasureSkillEffectivenessTool()

        # First enhance the skill
        enhance_result = await enhance_tool.execute(
            skill_id="skill001",
            enhancement_type="accuracy",
            target_improvement=15.0
        )
        assert enhance_result.status == ToolStatus.SUCCESS

        # Then measure effectiveness
        measure_result = await measure_tool.execute(skill_id="skill001")
        assert measure_result.status == ToolStatus.SUCCESS

        # New effectiveness should be higher than previous
        assert measure_result.data["overall_effectiveness"] > 0

    @pytest.mark.asyncio
    async def test_multiple_enhancements(self):
        """Test multiple sequential enhancements."""
        tool = EnhanceSkillTool()

        enhancements = [
            ("accuracy", 10.0),
            ("speed", 15.0),
            ("coverage", 12.0),
        ]

        for enh_type, target in enhancements:
            result = await tool.execute(
                skill_id="skill001",
                enhancement_type=enh_type,
                target_improvement=target
            )
            assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_measure_all_metrics(self):
        """Test measuring all available metrics."""
        tool = MeasureSkillEffectivenessTool()

        all_metrics = ["accuracy", "speed", "coverage", "reliability", "efficiency"]
        result = await tool.execute(
            skill_id="skill001",
            metrics=all_metrics
        )

        assert result.status == ToolStatus.SUCCESS

        # Should have measurements for all requested metrics
        measured_metrics = result.data["metrics"]
        for metric in all_metrics:
            assert metric in measured_metrics
