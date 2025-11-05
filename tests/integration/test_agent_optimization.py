"""Integration tests for Agent Optimization handlers (5 operations).

Tests the optimized implementations of 5 key agents using Phase 5-6 tools.
"""

import pytest
import asyncio
from typing import Any, List

# Import handlers
from athena.mcp.handlers_agent_optimization import (
    handle_optimize_planning_orchestrator,
    handle_optimize_goal_orchestrator,
    handle_optimize_consolidation_trigger,
    handle_optimize_strategy_orchestrator,
    handle_optimize_attention_optimizer,
)
from athena.integration.agent_optimization import (
    PlanningOrchestratorOptimizer,
    GoalOrchestratorOptimizer,
    ConsolidationTriggerOptimizer,
    StrategyOrchestratorOptimizer,
    AttentionOptimizerOptimizer,
)


class MockStore:
    """Mock store with database reference."""

    def __init__(self, db: Any = None):
        self.db = db


class MockServer:
    """Mock server for testing."""

    def __init__(self, db: Any = None):
        self.db = db
        self.store = MockStore(db)


class TestAgentOptimizationHandlers:
    """Test Agent Optimization handler implementations."""

    @pytest.mark.asyncio
    async def test_optimize_planning_orchestrator_handler(self):
        """Test optimize_planning_orchestrator handler."""
        server = MockServer()
        args = {
            "task_description": "Implement user authentication",
            "include_scenarios": True,
            "strict_mode": False,
        }

        # Call handler
        result = await handle_optimize_planning_orchestrator(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0
        assert hasattr(result[0], "type")
        assert hasattr(result[0], "text")
        assert "planning" in result[0].text.lower() or "plan" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_optimize_goal_orchestrator_handler(self):
        """Test optimize_goal_orchestrator handler."""
        server = MockServer()
        args = {"goal_id": 1, "activate": True, "monitor_health": True}

        # Call handler
        result = await handle_optimize_goal_orchestrator(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0
        assert "goal" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_optimize_consolidation_trigger_handler(self):
        """Test optimize_consolidation_trigger handler."""
        server = MockServer()
        args = {
            "trigger_reason": "session_end",
            "strategy": "balanced",
            "measure_quality": True,
        }

        # Call handler
        result = await handle_optimize_consolidation_trigger(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_optimize_strategy_orchestrator_handler(self):
        """Test optimize_strategy_orchestrator handler."""
        server = MockServer()
        args = {
            "task_context": {"complexity": 5, "estimated_duration": 480},
            "analyze_effectiveness": True,
        }

        # Call handler
        result = await handle_optimize_strategy_orchestrator(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_optimize_attention_optimizer_handler(self):
        """Test optimize_attention_optimizer handler."""
        server = MockServer()
        args = {
            "project_id": 1,
            "weight_by_expertise": True,
            "analyze_patterns": True,
        }

        # Call handler
        result = await handle_optimize_attention_optimizer(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0


class TestPlanningOrchestratorOptimizer:
    """Test PlanningOrchestratorOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_planning_orchestrator_optimizer_execute(self, tmp_path):
        """Test planning orchestrator optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PlanningOrchestratorOptimizer(db)

        result = await optimizer.execute(
            task_description="Test task",
            include_scenarios=True,
            strict_mode=False
        )

        # Verify result structure
        assert "status" in result
        assert "plan_steps" in result
        assert "structure_valid" in result
        assert "feasibility_valid" in result
        assert "properties_score" in result
        assert "success_probability" in result
        assert "ready_for_execution" in result

        # Verify types
        assert isinstance(result["plan_steps"], int)
        assert isinstance(result["structure_valid"], bool)
        assert isinstance(result["properties_score"], float)
        assert 0.0 <= result["properties_score"] <= 1.0


class TestGoalOrchestratorOptimizer:
    """Test GoalOrchestratorOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_goal_orchestrator_optimizer_execute(self, tmp_path):
        """Test goal orchestrator optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = GoalOrchestratorOptimizer(db)

        result = await optimizer.execute(goal_id=1, activate=True, monitor_health=True)

        # Verify result structure
        assert "status" in result
        assert "activated" in result
        assert "plan_valid" in result
        assert "health_score" in result
        assert "health_status" in result
        assert "progress_percent" in result
        assert "replanning_triggered" in result

        # Verify types
        assert isinstance(result["activated"], bool)
        assert isinstance(result["health_score"], float)
        assert 0.0 <= result["health_score"] <= 1.0


class TestConsolidationTriggerOptimizer:
    """Test ConsolidationTriggerOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_consolidation_trigger_optimizer_execute(self, tmp_path):
        """Test consolidation trigger optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = ConsolidationTriggerOptimizer(db)

        result = await optimizer.execute(
            trigger_reason="session_end",
            strategy="balanced",
            measure_quality=True
        )

        # Verify result structure
        assert "status" in result
        assert "events_consolidated" in result
        assert "quality_score" in result
        assert "compression_ratio" in result
        assert "recall_score" in result
        assert "consistency_score" in result

        # Verify score ranges
        assert 0.0 <= result["quality_score"] <= 1.0
        assert 0.0 <= result["compression_ratio"] <= 1.0
        assert 0.0 <= result["recall_score"] <= 1.0


class TestStrategyOrchestratorOptimizer:
    """Test StrategyOrchestratorOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_strategy_orchestrator_optimizer_execute(self, tmp_path):
        """Test strategy orchestrator optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = StrategyOrchestratorOptimizer(db)

        result = await optimizer.execute(
            task_context={"complexity": 5},
            analyze_effectiveness=True,
            apply_refinements=True
        )

        # Verify result structure
        assert "status" in result
        assert "selected_strategy" in result
        assert "effectiveness_score" in result
        assert "strategies_evaluated" in result
        assert "refinements_applied" in result

        # Verify types
        assert isinstance(result["selected_strategy"], str)
        assert isinstance(result["effectiveness_score"], float)
        assert 0.0 <= result["effectiveness_score"] <= 1.0


class TestAttentionOptimizerOptimizer:
    """Test AttentionOptimizerOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_attention_optimizer_optimizer_execute(self, tmp_path):
        """Test attention optimizer optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = AttentionOptimizerOptimizer(db)

        result = await optimizer.execute(
            project_id=1,
            weight_by_expertise=True,
            analyze_patterns=True
        )

        # Verify result structure
        assert "status" in result
        assert "expertise_domains" in result
        assert "items_reordered" in result
        assert "wm_capacity_used" in result
        assert "top_item_1" in result
        assert "confidence_1" in result

        # Verify types
        assert isinstance(result["expertise_domains"], int)
        assert isinstance(result["wm_capacity_used"], int)
        assert 0.0 <= result["confidence_1"] <= 1.0


class TestAgentOptimizationIntegration:
    """Test Agent Optimization integration with operation router."""

    @pytest.mark.asyncio
    async def test_agent_optimization_operations_registered(self):
        """Test that agent optimization operations are registered in router."""
        from athena.mcp.operation_router import OperationRouter

        # Verify agent_optimization_tools is in operation maps
        assert "agent_optimization_tools" in OperationRouter.OPERATION_MAPS

        # Verify all 5 operations are registered
        agent_ops = OperationRouter.OPERATION_MAPS["agent_optimization_tools"]
        expected_ops = [
            "optimize_planning_orchestrator",
            "optimize_goal_orchestrator",
            "optimize_consolidation_trigger",
            "optimize_strategy_orchestrator",
            "optimize_attention_optimizer",
        ]

        for op in expected_ops:
            assert op in agent_ops, f"Operation {op} not registered"

    def test_agent_optimization_handler_forwarding(self):
        """Test that handlers properly forward to implementation."""
        from athena.mcp.handlers import MemoryMCPServer

        # Verify handler methods exist
        server_methods = [
            "_handle_optimize_planning_orchestrator",
            "_handle_optimize_goal_orchestrator",
            "_handle_optimize_consolidation_trigger",
            "_handle_optimize_strategy_orchestrator",
            "_handle_optimize_attention_optimizer",
        ]

        for method in server_methods:
            assert hasattr(MemoryMCPServer, method), f"Handler method {method} not found"


class TestAgentOptimizationErrorHandling:
    """Test error handling in agent optimization."""

    @pytest.mark.asyncio
    async def test_planning_orchestrator_error_handling(self, tmp_path):
        """Test error handling in planning orchestrator optimizer."""
        # Create optimizer with None database
        optimizer = PlanningOrchestratorOptimizer(None)

        result = await optimizer.execute(
            task_description="Test",
            include_scenarios=True
        )

        # Verify error handling
        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_goal_orchestrator_error_handling(self, tmp_path):
        """Test error handling in goal orchestrator optimizer."""
        optimizer = GoalOrchestratorOptimizer(None)

        result = await optimizer.execute(goal_id=1, activate=True)

        # Verify error handling
        assert result["status"] == "error"
        assert "error" in result


class TestAgentOptimizationPhase56Integration:
    """Test Phase 5-6 tool integration in agent optimization."""

    @pytest.mark.asyncio
    async def test_planning_orchestrator_phase6_tools(self, tmp_path):
        """Test Phase 6 tools used in planning orchestrator."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PlanningOrchestratorOptimizer(db)

        result = await optimizer.execute(task_description="Test")

        # Verify Phase 6 tool results are present
        assert "properties_score" in result  # Q* verification
        assert "success_probability" in result  # Scenario simulation
        assert "critical_path" in result  # Scenario analysis

    @pytest.mark.asyncio
    async def test_goal_orchestrator_phase6_tools(self, tmp_path):
        """Test Phase 6 tools used in goal orchestrator."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = GoalOrchestratorOptimizer(db)

        result = await optimizer.execute(goal_id=1)

        # Verify Phase 6 tool results
        assert "plan_valid" in result  # Plan validation
        assert "replanning_triggered" in result  # Adaptive replanning
        assert "patterns_extracted" in result  # Pattern extraction

    @pytest.mark.asyncio
    async def test_consolidation_trigger_phase5_tools(self, tmp_path):
        """Test Phase 5 tools used in consolidation trigger."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = ConsolidationTriggerOptimizer(db)

        result = await optimizer.execute(trigger_reason="session_end")

        # Verify Phase 5 tool results
        assert "quality_score" in result  # Consolidation quality
        assert "strategy_used" in result  # Strategy selection
        assert "compression_ratio" in result  # Consolidation metrics


class TestAgentOptimizationMetrics:
    """Test performance and quality metrics in agent optimization."""

    @pytest.mark.asyncio
    async def test_planning_orchestrator_quality_scores(self, tmp_path):
        """Test quality scores in planning orchestrator."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PlanningOrchestratorOptimizer(db)

        result = await optimizer.execute(task_description="Test")

        # Verify Q* properties
        assert 0.0 <= result["optimality"] <= 1.0
        assert 0.0 <= result["completeness"] <= 1.0
        assert 0.0 <= result["consistency"] <= 1.0
        assert 0.0 <= result["soundness"] <= 1.0
        assert 0.0 <= result["minimality"] <= 1.0

    @pytest.mark.asyncio
    async def test_consolidation_trigger_quality_metrics(self, tmp_path):
        """Test quality metrics in consolidation trigger."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = ConsolidationTriggerOptimizer(db)

        result = await optimizer.execute(trigger_reason="weekly_review")

        # Verify consolidation quality metrics
        assert 0.0 <= result["compression_ratio"] <= 1.0
        assert 0.0 <= result["recall_score"] <= 1.0
        assert 0.0 <= result["consistency_score"] <= 1.0
        assert 0.0 <= result["density_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_strategy_orchestrator_effectiveness(self, tmp_path):
        """Test strategy effectiveness metrics."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = StrategyOrchestratorOptimizer(db)

        result = await optimizer.execute(task_context={})

        # Verify effectiveness metrics
        assert 0.0 <= result["effectiveness_score"] <= 1.0
        assert result["strategies_evaluated"] >= 0


# ============================================================================
# Test Organization and Categorization
# ============================================================================

# These tests are organized into classes by optimizer/agent component
# Each class tests:
# 1. Handler implementation correctness
# 2. Optimizer execution and result structure
# 3. Error handling and edge cases
# 4. Integration with operation router
# 5. Phase 5-6 tool integration
# 6. Performance and quality metrics

# Run with: pytest tests/integration/test_agent_optimization.py -v
# Run specific test: pytest tests/integration/test_agent_optimization.py::TestPlanningOrchestratorOptimizer -v
