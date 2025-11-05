"""Integration tests for Slash Command handlers (6 commands).

Tests the implementations of 6 new slash commands providing access to Phase 5-6 tools.
"""

import pytest
import asyncio
from typing import Any, List

# Import handlers
from athena.mcp.handlers_slash_commands import (
    handle_consolidate_advanced,
    handle_plan_validate_advanced,
    handle_task_health,
    handle_estimate_resources,
    handle_stress_test_plan,
    handle_learning_effectiveness,
)
from athena.integration.slash_commands import (
    ConsolidateAdvancedCommand,
    PlanValidateAdvancedCommand,
    TaskHealthCommand,
    EstimateResourcesCommand,
    StressTestPlanCommand,
    LearningEffectivenessCommand,
)


class MockServer:
    """Mock server for testing."""

    def __init__(self, db: Any = None):
        self.db = db
        self.store = MockStore(db)


class MockStore:
    """Mock store with database reference."""

    def __init__(self, db: Any = None):
        self.db = db


class TestSlashCommandHandlers:
    """Test slash command handler implementations."""

    @pytest.mark.asyncio
    async def test_consolidate_advanced_handler(self):
        """Test /consolidate-advanced handler."""
        server = MockServer()
        args = {"project_id": 1, "strategy": "balanced", "measure_quality": True}

        result = await handle_consolidate_advanced(server, args)

        assert result is not None
        assert len(result) > 0
        assert "consolidate" in result[0].text.lower() or "quality" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_plan_validate_advanced_handler(self):
        """Test /plan-validate-advanced handler."""
        server = MockServer()
        args = {"task_description": "Test task", "include_scenarios": True}

        result = await handle_plan_validate_advanced(server, args)

        assert result is not None
        assert len(result) > 0
        assert "validation" in result[0].text.lower() or "plan" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_task_health_handler(self):
        """Test /task-health handler."""
        server = MockServer()
        args = {"project_id": 1, "include_trends": True}

        result = await handle_task_health(server, args)

        assert result is not None
        assert len(result) > 0
        assert "health" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_estimate_resources_handler(self):
        """Test /estimate-resources handler."""
        server = MockServer()
        args = {"task_description": "Test task", "include_breakdown": True}

        result = await handle_estimate_resources(server, args)

        assert result is not None
        assert len(result) > 0
        assert "resource" in result[0].text.lower() or "estimate" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_stress_test_plan_handler(self):
        """Test /stress-test-plan handler."""
        server = MockServer()
        args = {"task_description": "Test task", "confidence_level": 0.80}

        result = await handle_stress_test_plan(server, args)

        assert result is not None
        assert len(result) > 0
        assert "stress" in result[0].text.lower() or "scenario" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_learning_effectiveness_handler(self):
        """Test /learning-effectiveness handler."""
        server = MockServer()
        args = {"project_id": 1, "days_back": 7, "include_recommendations": True}

        result = await handle_learning_effectiveness(server, args)

        assert result is not None
        assert len(result) > 0
        assert "learning" in result[0].text.lower() or "effectiveness" in result[0].text.lower()


class TestConsolidateAdvancedCommand:
    """Test ConsolidateAdvancedCommand implementation."""

    @pytest.mark.asyncio
    async def test_consolidate_advanced_execute(self):
        """Test consolidate advanced command execution."""
        command = ConsolidateAdvancedCommand(None)

        result = await command.execute(project_id=1, strategy="balanced", measure_quality=True)

        # Verify result structure
        assert "status" in result
        assert "strategy_used" in result
        assert "events_consolidated" in result
        assert "quality_score" in result
        assert "compression_ratio" in result
        assert "recall_score" in result

        # Verify types
        assert result["status"] == "success"
        assert isinstance(result["quality_score"], float)
        assert 0.0 <= result["quality_score"] <= 1.0


class TestPlanValidateAdvancedCommand:
    """Test PlanValidateAdvancedCommand implementation."""

    @pytest.mark.asyncio
    async def test_plan_validate_advanced_execute(self):
        """Test plan validation command execution."""
        command = PlanValidateAdvancedCommand(None)

        result = await command.execute(task_description="Test", include_scenarios=True)

        # Verify result structure
        assert "status" in result
        assert "plan_steps" in result
        assert "estimated_duration" in result
        assert "structure_valid" in result
        assert "feasibility_valid" in result
        assert "properties_score" in result

        # Verify types
        assert result["status"] == "success"
        assert isinstance(result["structure_valid"], bool)
        assert 0.0 <= result["properties_score"] <= 1.0


class TestTaskHealthCommand:
    """Test TaskHealthCommand implementation."""

    @pytest.mark.asyncio
    async def test_task_health_execute(self):
        """Test task health command execution."""
        command = TaskHealthCommand(None)

        result = await command.execute(project_id=1, include_trends=True)

        # Verify result structure
        assert "status" in result
        assert "health_score" in result
        assert "health_status" in result
        assert "progress_percent" in result
        assert "completed_tasks" in result
        assert "error_count" in result

        # Verify types
        assert result["status"] == "success"
        assert 0.0 <= result["health_score"] <= 1.0
        assert 0.0 <= result["progress_percent"] <= 100.0


class TestEstimateResourcesCommand:
    """Test EstimateResourcesCommand implementation."""

    @pytest.mark.asyncio
    async def test_estimate_resources_execute(self):
        """Test resource estimation command execution."""
        command = EstimateResourcesCommand(None)

        result = await command.execute(task_description="Test", include_breakdown=True)

        # Verify result structure
        assert "status" in result
        assert "complexity_level" in result
        assert "duration_estimate" in result
        assert "confidence_percent" in result
        assert "expertise_required" in result
        assert "tools_required" in result

        # Verify types
        assert result["status"] == "success"
        assert isinstance(result["complexity_level"], int)
        assert 1 <= result["complexity_level"] <= 10


class TestStressTestPlanCommand:
    """Test StressTestPlanCommand implementation."""

    @pytest.mark.asyncio
    async def test_stress_test_plan_execute(self):
        """Test stress test plan command execution."""
        command = StressTestPlanCommand(None)

        result = await command.execute(task_description="Test", confidence_level=0.80)

        # Verify result structure
        assert "status" in result
        assert "scenarios_analyzed" in result
        assert "best_case_duration" in result
        assert "likely_case_duration" in result
        assert "worst_case_duration" in result
        assert "success_probability" in result

        # Verify types
        assert result["status"] == "success"
        assert isinstance(result["scenarios_analyzed"], int)
        assert 0.0 <= result["success_probability"] <= 1.0


class TestLearningEffectivenessCommand:
    """Test LearningEffectivenessCommand implementation."""

    @pytest.mark.asyncio
    async def test_learning_effectiveness_execute(self):
        """Test learning effectiveness command execution."""
        command = LearningEffectivenessCommand(None)

        result = await command.execute(project_id=1, days_back=7, include_recommendations=True)

        # Verify result structure
        assert "status" in result
        assert "consolidation_runs" in result
        assert "patterns_extracted" in result
        assert "best_strategy" in result
        assert "best_strategy_score" in result
        assert "domain_expertise" in result

        # Verify types
        assert result["status"] == "success"
        assert isinstance(result["consolidation_runs"], int)
        assert 0.0 <= result["best_strategy_score"] <= 1.0


class TestSlashCommandQuality:
    """Test quality assurance for slash commands."""

    @pytest.mark.asyncio
    async def test_consolidate_advanced_metrics(self):
        """Test consolidation command quality metrics."""
        command = ConsolidateAdvancedCommand(None)

        result = await command.execute()

        # Verify metric values
        assert 0.0 <= result["quality_score"] <= 1.0
        assert 0.0 <= result["compression_ratio"] <= 1.0
        assert 0.0 <= result["recall_score"] <= 1.0
        assert 0.0 <= result["consistency_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_plan_validate_advanced_properties(self):
        """Test plan validation properties scoring."""
        command = PlanValidateAdvancedCommand(None)

        result = await command.execute()

        # Verify property scores
        assert "optimality" in result
        assert "completeness" in result
        assert "consistency" in result
        assert "soundness" in result
        assert all(0.0 <= result[p] <= 1.0 for p in ["optimality", "completeness", "consistency", "soundness"])

    @pytest.mark.asyncio
    async def test_task_health_status_mapping(self):
        """Test task health status mapping."""
        command = TaskHealthCommand(None)

        result = await command.execute()

        # Verify health status is valid
        assert result["health_status"] in ["healthy", "warning", "critical"]
        # Verify consistency with score
        health_score = result["health_score"]
        if health_score >= 0.75:
            assert result["health_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_estimate_resources_risk_distribution(self):
        """Test resource estimation risk distribution."""
        command = EstimateResourcesCommand(None)

        result = await command.execute()

        # Verify risk percentages sum to 100
        risk_total = (
            result["low_risk_percentage"] +
            result["medium_risk_percentage"] +
            result["high_risk_percentage"]
        )
        assert risk_total == 100

    @pytest.mark.asyncio
    async def test_stress_test_plan_scenario_probabilities(self):
        """Test stress test scenario probabilities."""
        command = StressTestPlanCommand(None)

        result = await command.execute()

        # Verify scenario probabilities sum reasonably
        scenario_probs = (
            result["best_case_probability"] +
            result["likely_case_probability"] +
            result["worst_case_probability"]
        )
        assert 0.8 < scenario_probs <= 1.0  # Allow rounding

    @pytest.mark.asyncio
    async def test_learning_effectiveness_strategy_scores(self):
        """Test learning effectiveness strategy scores."""
        command = LearningEffectivenessCommand(None)

        result = await command.execute()

        # Verify all strategy scores are valid
        strategies = ["balanced", "speed", "quality", "minimal"]
        for strategy in strategies:
            key = f"{strategy}_effectiveness"
            assert key in result
            assert 0.0 <= result[key] <= 1.0

        # Verify best strategy score matches
        best = result["best_strategy"]
        best_key = f"{best}_effectiveness"
        assert result["best_strategy_score"] == result[best_key]


class TestSlashCommandRecommendations:
    """Test recommendation generation in slash commands."""

    @pytest.mark.asyncio
    async def test_consolidate_advanced_recommendations(self):
        """Test consolidation command provides recommendations."""
        command = ConsolidateAdvancedCommand(None)

        result = await command.execute()

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_task_health_recommendations(self):
        """Test task health command provides recommendations."""
        command = TaskHealthCommand(None)

        result = await command.execute()

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_stress_test_plan_mitigations(self):
        """Test stress test provides mitigation strategies."""
        command = StressTestPlanCommand(None)

        result = await command.execute()

        assert "mitigation_strategies" in result
        assert isinstance(result["mitigation_strategies"], list)
        assert len(result["mitigation_strategies"]) > 0

    @pytest.mark.asyncio
    async def test_learning_effectiveness_recommendations(self):
        """Test learning command provides recommendations."""
        command = LearningEffectivenessCommand(None)

        result = await command.execute()

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0


class TestSlashCommandErrorHandling:
    """Test error handling in slash commands."""

    @pytest.mark.asyncio
    async def test_consolidate_advanced_error_handling(self):
        """Test consolidation command error handling."""
        command = ConsolidateAdvancedCommand(None)

        result = await command.execute()

        assert "status" in result

    @pytest.mark.asyncio
    async def test_all_commands_error_resilience(self):
        """Test all commands handle errors gracefully."""
        commands = [
            ConsolidateAdvancedCommand(None),
            PlanValidateAdvancedCommand(None),
            TaskHealthCommand(None),
            EstimateResourcesCommand(None),
            StressTestPlanCommand(None),
            LearningEffectivenessCommand(None),
        ]

        for command in commands:
            result = await command.execute()
            assert "status" in result
            assert result["status"] in ["success", "error"]


# ============================================================================
# Test Organization
# ============================================================================

# These tests are organized by:
# 1. Handler tests (6 handlers)
# 2. Command unit tests (6 commands)
# 3. Quality assurance tests
# 4. Recommendation generation tests
# 5. Error handling tests

# Run with: pytest tests/integration/test_slash_commands.py -v
# Run specific test: pytest tests/integration/test_slash_commands.py::TestConsolidateAdvancedCommand -v
