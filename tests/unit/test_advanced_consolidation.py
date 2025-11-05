"""Tests for advanced consolidation modules."""

import pytest
from datetime import datetime

from athena.consolidation.strategy_learning import StrategyLearningEngine, StrategyPerformance
from athena.consolidation.orchestration_learning import (
    OrchestrationLearningEngine,
    DiscoveredPattern,
)
from athena.consolidation.validation_learning import (
    ValidationLearningEngine,
    RuleExecution,
    RuleMetrics,
)


class TestStrategyLearningEngine:
    """Tests for strategy learning."""

    def test_initialize_engine(self):
        """Test initializing strategy learning engine."""
        engine = StrategyLearningEngine()
        assert engine is not None

    def test_analyze_task_type_cluster(self):
        """Test analyzing performance of a task cluster."""
        engine = StrategyLearningEngine()

        execution_records = [
            {"strategy_id": 1, "success": True, "quality_score": 0.95, "duration_variance_pct": 10.0},
            {"strategy_id": 1, "success": True, "quality_score": 0.92, "duration_variance_pct": 5.0},
            {"strategy_id": 1, "success": False, "quality_score": 0.60, "duration_variance_pct": -15.0},
        ]

        performance = engine.analyze_task_type_cluster(
            task_type="refactoring",
            complexity=5,
            domain="backend",
            execution_records=execution_records,
        )

        assert performance.task_type == "refactoring"
        assert performance.complexity == 5
        assert performance.execution_count == 3
        assert performance.success_rate > 0.5

    def test_get_best_strategy_for_cluster(self):
        """Test retrieving best strategy for a cluster."""
        engine = StrategyLearningEngine()

        # Record multiple clusters
        for i in range(3):
            records = [
                {"strategy_id": 1 + i, "success": True, "quality_score": 0.9 + 0.01*i, "duration_variance_pct": 5.0}
                for _ in range(5)
            ]
            engine.analyze_task_type_cluster(
                "refactoring", 5, "backend", records
            )

        best = engine.get_best_strategy_for_cluster("refactoring", 5, "backend")
        assert best is not None
        assert best.success_rate > 0.8

    def test_identify_optimal_strategies(self):
        """Test identifying optimal strategies."""
        engine = StrategyLearningEngine()

        records = [
            {"strategy_id": 1, "success": True, "quality_score": 0.95, "duration_variance_pct": 0.0}
            for _ in range(5)
        ]

        engine.analyze_task_type_cluster("refactoring", 5, "backend", records)
        optimal = engine.identify_optimal_strategies()

        assert len(optimal) > 0

    def test_extract_strategy_insights(self):
        """Test extracting strategy insights."""
        engine = StrategyLearningEngine()

        records_success = [
            {"strategy_id": 1, "success": True, "quality_score": 0.95, "duration_variance_pct": 5.0}
            for _ in range(10)
        ]

        engine.analyze_task_type_cluster("feature", 8, "frontend", records_success)
        engine.identify_optimal_strategies()

        insights = engine.extract_strategy_insights()
        assert len(insights) > 0

    def test_get_strategy_conditions(self):
        """Test getting optimal conditions for a strategy."""
        engine = StrategyLearningEngine()

        records = [
            {"strategy_id": 1, "success": True, "quality_score": 0.95, "duration_variance_pct": 5.0}
            for _ in range(5)
        ]

        engine.analyze_task_type_cluster("refactoring", 3, "backend", records)
        conditions = engine.get_strategy_conditions(1)

        assert "strategy_id" in conditions
        assert "best_for_task_types" in conditions

    def test_compare_strategies_for_task_type(self):
        """Test comparing strategies for a task type."""
        engine = StrategyLearningEngine()

        for strategy_id in [1, 2, 3]:
            records = [
                {"strategy_id": strategy_id, "success": strategy_id == 1, "quality_score": 0.8 + 0.05*strategy_id, "duration_variance_pct": 0.0}
                for _ in range(5)
            ]
            engine.analyze_task_type_cluster("refactoring", 5, "backend", records)

        comparison = engine.compare_strategies_for_task_type("refactoring")
        assert len(comparison) > 0
        # Strategy 1 should be more effective (all successes)
        assert comparison[0][0] == 1


class TestOrchestrationLearningEngine:
    """Tests for orchestration learning."""

    def test_initialize_engine(self):
        """Test initializing orchestration learning engine."""
        engine = OrchestrationLearningEngine()
        assert engine is not None

    def test_record_execution_trace(self):
        """Test recording execution trace."""
        engine = OrchestrationLearningEngine()

        delegations = [
            {"from_agent": "orchestrator", "to_agent": "frontend", "success": True},
            {"from_agent": "frontend", "to_agent": "backend", "success": True},
        ]

        engine.record_execution_trace(
            delegations=delegations,
            total_time_ms=5000,
            success=True,
            task_type="feature",
            domains=["frontend", "backend"],
            task_complexity=5,
        )

        assert len(engine._execution_traces) == 1

    def test_discover_patterns(self):
        """Test discovering orchestration patterns."""
        engine = OrchestrationLearningEngine()

        # Record multiple successful traces
        for _ in range(5):
            delegations = [
                {"from_agent": "orchestrator", "to_agent": "backend", "success": True},
                {"from_agent": "backend", "to_agent": "database", "success": True},
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=4000,
                success=True,
                task_type="data-migration",
                domains=["backend", "database"],
                task_complexity=7,
            )

        patterns = engine.discover_patterns()
        assert len(patterns) > 0

    def test_get_best_pattern_for_task(self):
        """Test getting best pattern for task."""
        engine = OrchestrationLearningEngine()

        # Record successful traces
        for _ in range(5):
            delegations = [
                {"from_agent": "orchestrator", "to_agent": "agent_a", "success": True},
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=3000,
                success=True,
                task_type="simple",
                domains=["backend"],
                task_complexity=2,
            )

        patterns = engine.discover_patterns()
        if patterns:
            best = engine.get_best_pattern_for_task("simple", 2)
            assert best is not None

    def test_get_successful_agent_teams(self):
        """Test getting successful agent teams."""
        engine = OrchestrationLearningEngine()

        # Record traces
        for _ in range(5):
            delegations = [
                {"from_agent": "orchestrator", "to_agent": "agent_a", "success": True},
                {"from_agent": "agent_a", "to_agent": "agent_b", "success": True},
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=5000,
                success=True,
                task_type="complex",
                domains=["domain1", "domain2"],
                task_complexity=8,
            )

        patterns = engine.discover_patterns()
        teams = engine.get_successful_agent_teams()

        assert isinstance(teams, list)

    def test_get_handoff_bottlenecks(self):
        """Test identifying handoff bottlenecks."""
        engine = OrchestrationLearningEngine()

        # Record traces with some failures
        for i in range(5):
            delegations = [
                {"from_agent": "agent_a", "to_agent": "agent_b", "success": i < 2},  # 40% success
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=3000,
                success=i < 2,
                task_type="task",
                domains=["domain"],
                task_complexity=5,
            )

        bottlenecks = engine.get_handoff_bottlenecks()
        assert isinstance(bottlenecks, list)

    def test_estimate_speedup_for_pattern(self):
        """Test estimating speedup."""
        engine = OrchestrationLearningEngine()

        speedup_single = engine.estimate_speedup_for_pattern(1, "sequential")
        assert speedup_single == 1.0

        speedup_multi = engine.estimate_speedup_for_pattern(3, "parallel")
        assert speedup_multi > 1.0

    def test_extract_orchestration_insights(self):
        """Test extracting insights."""
        engine = OrchestrationLearningEngine()

        # Record successful patterns
        for _ in range(5):
            delegations = [
                {"from_agent": "orchestrator", "to_agent": "worker", "success": True},
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=2000,
                success=True,
                task_type="work",
                domains=["domain"],
                task_complexity=3,
            )

        patterns = engine.discover_patterns()
        insights = engine.extract_orchestration_insights()

        assert isinstance(insights, list)


class TestValidationLearningEngine:
    """Tests for validation rule learning."""

    def test_initialize_engine(self):
        """Test initializing validation learning engine."""
        engine = ValidationLearningEngine()
        assert engine is not None

    def test_record_rule_execution(self):
        """Test recording rule execution."""
        engine = ValidationLearningEngine()

        execution = engine.record_rule_execution(
            rule_id=1,
            rule_name="Check duration",
            issue_present=True,
            rule_flagged_issue=True,
        )

        assert execution.rule_id == 1
        assert not execution.false_positive
        assert not execution.false_negative

    def test_record_false_positive(self):
        """Test recording false positive."""
        engine = ValidationLearningEngine()

        execution = engine.record_rule_execution(
            rule_id=1,
            rule_name="Check duration",
            issue_present=False,
            rule_flagged_issue=True,
        )

        assert execution.false_positive is True

    def test_record_false_negative(self):
        """Test recording false negative."""
        engine = ValidationLearningEngine()

        execution = engine.record_rule_execution(
            rule_id=1,
            rule_name="Check duration",
            issue_present=True,
            rule_flagged_issue=False,
        )

        assert execution.false_negative is True

    def test_calculate_rule_metrics(self):
        """Test calculating rule metrics."""
        engine = ValidationLearningEngine()

        # Record executions: 3 TP, 1 FP, 1 FN, 5 TN = 10 total
        for _ in range(3):
            engine.record_rule_execution(1, "Rule1", True, True)  # TP

        engine.record_rule_execution(1, "Rule1", False, True)  # FP

        engine.record_rule_execution(1, "Rule1", True, False)  # FN

        for _ in range(5):
            engine.record_rule_execution(1, "Rule1", False, False)  # TN

        metrics = engine.calculate_rule_metrics(1)

        assert metrics.true_positives == 3
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1
        assert metrics.true_negatives == 5
        assert metrics.precision == 0.75  # 3 / (3 + 1)
        assert metrics.recall == 0.75  # 3 / (3 + 1)

    def test_rank_rules_by_effectiveness(self):
        """Test ranking rules."""
        engine = ValidationLearningEngine()

        # Rule 1: excellent (3 TP, 0 FP, 0 FN, 7 TN)
        for _ in range(3):
            engine.record_rule_execution(1, "Rule1", True, True)
        for _ in range(7):
            engine.record_rule_execution(1, "Rule1", False, False)

        # Rule 2: poor (1 TP, 3 FP, 2 FN, 4 TN)
        engine.record_rule_execution(2, "Rule2", True, True)
        for _ in range(3):
            engine.record_rule_execution(2, "Rule2", False, True)
        for _ in range(2):
            engine.record_rule_execution(2, "Rule2", True, False)
        for _ in range(4):
            engine.record_rule_execution(2, "Rule2", False, False)

        ranked = engine.rank_rules_by_effectiveness()
        assert ranked[0].rule_id == 1  # Rule 1 should be first

    def test_identify_low_value_rules(self):
        """Test identifying low-value rules."""
        engine = ValidationLearningEngine()

        # Record a low-effectiveness rule with enough executions
        for _ in range(11):
            engine.record_rule_execution(1, "BadRule", False, True)  # All FP

        low_value = engine.identify_low_value_rules(effectiveness_threshold=0.5)
        assert len(low_value) > 0

    def test_identify_high_value_rules(self):
        """Test identifying high-value rules."""
        engine = ValidationLearningEngine()

        # Record a high-effectiveness rule
        for _ in range(10):
            engine.record_rule_execution(1, "GoodRule", True, True)  # All TP

        high_value = engine.identify_high_value_rules(effectiveness_threshold=0.75)
        assert len(high_value) > 0

    def test_get_complementary_rules(self):
        """Test finding complementary rules."""
        engine = ValidationLearningEngine()

        # Record executions for rule 1
        for _ in range(5):
            engine.record_rule_execution(1, "Rule1", True, True)

        complementary = engine.get_complementary_rules(1)
        assert isinstance(complementary, list)

    def test_extract_validation_insights(self):
        """Test extracting validation insights."""
        engine = ValidationLearningEngine()

        # Record some rule executions
        for _ in range(5):
            engine.record_rule_execution(1, "Rule1", True, True)

        insights = engine.extract_validation_insights()
        assert isinstance(insights, list)

    def test_recommend_rule_set_for_plan(self):
        """Test recommending rules for plan."""
        engine = ValidationLearningEngine()

        # Record good rule
        for _ in range(10):
            engine.record_rule_execution(1, "GoodRule", True, True)

        recommended = engine.recommend_rule_set_for_plan("refactoring", max_rules=3)
        assert isinstance(recommended, list)


class TestConsolidationIntegration:
    """End-to-end tests for advanced consolidation."""

    def test_strategy_learning_workflow(self):
        """Test complete strategy learning workflow."""
        engine = StrategyLearningEngine()

        # Simulate 3 different task complexities
        for complexity in [3, 5, 8]:
            records = [
                {"strategy_id": 1, "success": True, "quality_score": 0.9, "duration_variance_pct": 5.0}
                for _ in range(5)
            ]
            engine.analyze_task_type_cluster("refactoring", complexity, "backend", records)

        # Get optimal strategies
        optimal = engine.identify_optimal_strategies()
        assert len(optimal) >= 3

        # Extract insights
        insights = engine.extract_strategy_insights()
        assert len(insights) > 0

    def test_orchestration_discovery_workflow(self):
        """Test complete orchestration discovery workflow."""
        engine = OrchestrationLearningEngine()

        # Simulate multiple successful executions
        for _ in range(5):
            delegations = [
                {"from_agent": "orch", "to_agent": "specialist1", "success": True},
                {"from_agent": "specialist1", "to_agent": "specialist2", "success": True},
            ]

            engine.record_execution_trace(
                delegations=delegations,
                total_time_ms=3000,
                success=True,
                task_type="complex-task",
                domains=["domain1", "domain2"],
                task_complexity=7,
            )

        # Discover patterns
        patterns = engine.discover_patterns()
        assert len(patterns) > 0

        # Get best pattern for task
        best = engine.get_best_pattern_for_task("complex-task", 7)
        if patterns:
            assert best is not None

    def test_validation_rule_optimization_workflow(self):
        """Test complete validation rule optimization workflow."""
        engine = ValidationLearningEngine()

        # Record executions for multiple rules
        # Rule 1: excellent
        for _ in range(20):
            engine.record_rule_execution(1, "ExcellentRule", True, True)

        # Rule 2: poor
        for _ in range(15):
            engine.record_rule_execution(2, "PoorRule", False, True)

        # Get rankings
        ranked = engine.rank_rules_by_effectiveness()
        assert ranked[0].rule_id == 1

        # Get recommendations
        recommended = engine.recommend_rule_set_for_plan("planning", max_rules=5)
        assert 1 in recommended
