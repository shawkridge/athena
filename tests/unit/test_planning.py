"""Unit tests for planning memory models."""

import pytest
from datetime import datetime

from athena.planning.models import (
    PlanningPattern,
    PatternType,
    DecompositionStrategy,
    DecompositionType,
    OrchestratorPattern,
    CoordinationType,
    ValidationRule,
    ValidationRuleType,
    ExecutionFeedback,
    ExecutionOutcome,
)


class TestPlanningPattern:
    """Tests for PlanningPattern model."""

    def test_create_planning_pattern_minimal(self):
        """Test creating a planning pattern with minimal fields."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="hierarchical-decomposition",
            description="Decomposes tasks hierarchically by depth",
        )

        assert pattern.id is None  # Not saved yet
        assert pattern.project_id == 1
        assert pattern.pattern_type == PatternType.HIERARCHICAL
        assert pattern.name == "hierarchical-decomposition"
        assert pattern.success_rate == 0.0
        assert pattern.execution_count == 0
        assert isinstance(pattern.created_at, datetime)

    def test_create_planning_pattern_full(self):
        """Test creating a planning pattern with all fields."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HYBRID,
            name="hybrid-symbolic-llm",
            description="Combines symbolic planning with LLM approximation",
            success_rate=0.96,
            quality_score=0.93,
            execution_count=15,
            applicable_domains=["robotics", "safety-critical"],
            applicable_task_types=["planning", "decomposition"],
            complexity_range=(5, 10),
            conditions={"team_size": ">5", "risk_level": "high"},
            source="research",
            research_reference="arXiv:2505.11814",
        )

        assert pattern.success_rate == 0.96
        assert pattern.quality_score == 0.93
        assert "robotics" in pattern.applicable_domains
        assert pattern.research_reference == "arXiv:2505.11814"

    def test_planning_pattern_success_rate_validation(self):
        """Test that success rate is validated between 0 and 1."""
        with pytest.raises(ValueError):
            PlanningPattern(
                project_id=1,
                pattern_type=PatternType.RECURSIVE,
                name="test",
                description="test",
                success_rate=1.5,  # Invalid: > 1.0
            )

    def test_planning_pattern_quality_score_validation(self):
        """Test that quality score is validated between 0 and 1."""
        with pytest.raises(ValueError):
            PlanningPattern(
                project_id=1,
                pattern_type=PatternType.RECURSIVE,
                name="test",
                description="test",
                quality_score=-0.5,  # Invalid: < 0
            )

    def test_planning_pattern_enum_values(self):
        """Test that enum values are serialized correctly."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.GRAPH_BASED,
            name="graph-based",
            description="Uses knowledge graphs for planning",
        )

        data = pattern.model_dump()
        assert data["pattern_type"] == "graph_based"  # Enum is serialized to string


class TestDecompositionStrategy:
    """Tests for DecompositionStrategy model."""

    def test_create_decomposition_strategy_minimal(self):
        """Test creating decomposition strategy with minimal fields."""
        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="adaptive-30min",
            description="Adaptive decomposition with 30-minute chunks",
            decomposition_type=DecompositionType.ADAPTIVE,
        )

        assert strategy.chunk_size_minutes == 30
        assert strategy.decomposition_type == DecompositionType.ADAPTIVE
        assert strategy.success_rate == 0.0
        assert strategy.adaptive_depth is False

    def test_create_decomposition_strategy_full(self):
        """Test creating decomposition strategy with all fields."""
        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="hierarchical-with-gates",
            description="Hierarchical with validation gates",
            decomposition_type=DecompositionType.HIERARCHICAL,
            chunk_size_minutes=20,
            max_depth=4,
            adaptive_depth=True,
            validation_gates=["pre_execution", "post_phase"],
            applicable_task_types=["refactoring", "feature"],
            success_rate=0.88,
            avg_actual_vs_planned_ratio=1.15,
            quality_improvement_pct=28,
        )

        assert strategy.chunk_size_minutes == 20
        assert strategy.max_depth == 4
        assert strategy.adaptive_depth is True
        assert strategy.success_rate == 0.88
        assert "refactoring" in strategy.applicable_task_types

    def test_decomposition_strategy_chunk_size_validation(self):
        """Test that chunk size is validated between 5 and 480 minutes."""
        with pytest.raises(ValueError):
            DecompositionStrategy(
                project_id=1,
                strategy_name="invalid",
                description="invalid",
                decomposition_type=DecompositionType.FIXED,
                chunk_size_minutes=2,  # Invalid: < 5
            )

    def test_decomposition_strategy_avg_ratio_validation(self):
        """Test that avg_actual_vs_planned_ratio is reasonable."""
        with pytest.raises(ValueError):
            DecompositionStrategy(
                project_id=1,
                strategy_name="invalid",
                description="invalid",
                decomposition_type=DecompositionType.FIXED,
                avg_actual_vs_planned_ratio=4.0,  # Invalid: > 3.0
            )


class TestOrchestratorPattern:
    """Tests for OrchestratorPattern model."""

    def test_create_orchestrator_pattern_minimal(self):
        """Test creating orchestrator pattern with minimal fields."""
        pattern = OrchestratorPattern(
            project_id=1,
            pattern_name="orchestrator-worker",
            description="One orchestrator with worker agents",
            coordination_type=CoordinationType.HIERARCHICAL,
        )

        assert pattern.pattern_name == "orchestrator-worker"
        assert pattern.coordination_type == CoordinationType.HIERARCHICAL
        assert pattern.num_agents == 1
        assert pattern.speedup_factor == 1.0

    def test_create_orchestrator_pattern_full(self):
        """Test creating orchestrator pattern with all fields."""
        pattern = OrchestratorPattern(
            project_id=1,
            pattern_name="parallel-specialists",
            description="Parallel specialist agents with orchestrator",
            coordination_type=CoordinationType.PARALLEL,
            agent_roles=["orchestrator", "frontend", "backend", "devops"],
            num_agents=4,
            effectiveness_improvement_pct=90,
            handoff_success_rate=0.95,
            speedup_factor=3.5,
            token_overhead_multiplier=15.0,
            applicable_domains=["deployment", "refactoring"],
            applicable_task_types=["complex-system", "multi-phase"],
            execution_count=24,
            successful_executions=23,
        )

        assert pattern.num_agents == 4
        assert pattern.effectiveness_improvement_pct == 90
        assert pattern.handoff_success_rate == 0.95
        assert pattern.speedup_factor == 3.5
        assert pattern.token_overhead_multiplier == 15.0
        assert len(pattern.agent_roles) == 4

    def test_orchestrator_pattern_handoff_rate_validation(self):
        """Test that handoff success rate is validated between 0 and 1."""
        with pytest.raises(ValueError):
            OrchestratorPattern(
                project_id=1,
                pattern_name="invalid",
                description="invalid",
                coordination_type=CoordinationType.PARALLEL,
                handoff_success_rate=1.5,  # Invalid: > 1.0
            )

    def test_orchestrator_pattern_speedup_validation(self):
        """Test that speedup factor is at least 1.0."""
        with pytest.raises(ValueError):
            OrchestratorPattern(
                project_id=1,
                pattern_name="invalid",
                description="invalid",
                coordination_type=CoordinationType.PARALLEL,
                speedup_factor=0.5,  # Invalid: < 1.0
            )


class TestValidationRule:
    """Tests for ValidationRule model."""

    def test_create_validation_rule_minimal(self):
        """Test creating validation rule with minimal fields."""
        rule = ValidationRule(
            project_id=1,
            rule_name="check-task-duration",
            description="Ensures task duration is reasonable",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="validate_task_duration",
        )

        assert rule.rule_name == "check-task-duration"
        assert rule.rule_type == ValidationRuleType.HEURISTIC
        assert rule.risk_level == "medium"
        assert rule.accuracy_pct == 0.0

    def test_create_validation_rule_full(self):
        """Test creating validation rule with all fields."""
        rule = ValidationRule(
            project_id=1,
            rule_name="formal-plan-verification",
            description="Verifies plan using LTL and model checking",
            rule_type=ValidationRuleType.FORMAL,
            check_function="verify_plan_with_ltl",
            parameters={"model": "kripke_structure", "properties": ["safety", "liveness"]},
            applicable_to_task_types=["safety-critical", "planning"],
            applies_to_phases=["pre_execution"],
            risk_level="critical",
            accuracy_pct=96.3,
            precision=0.96,
            recall=0.97,
            f1_score=0.963,
            execution_count=50,
            violations_caught=48,
        )

        assert rule.rule_type == ValidationRuleType.FORMAL
        assert rule.accuracy_pct == 96.3
        assert rule.f1_score == 0.963
        assert rule.violations_caught == 48

    def test_validation_rule_accuracy_validation(self):
        """Test that accuracy percentage is validated between 0 and 100."""
        with pytest.raises(ValueError):
            ValidationRule(
                project_id=1,
                rule_name="invalid",
                description="invalid",
                rule_type=ValidationRuleType.LLM_BASED,
                check_function="test",
                accuracy_pct=150.0,  # Invalid: > 100
            )


class TestExecutionFeedback:
    """Tests for ExecutionFeedback model."""

    def test_create_execution_feedback_minimal(self):
        """Test creating execution feedback with minimal fields."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
        )

        assert feedback.execution_outcome == ExecutionOutcome.SUCCESS
        assert feedback.execution_quality_score == 0.0
        assert feedback.duration_variance_pct == 0.0
        assert isinstance(feedback.created_at, datetime)

    def test_create_execution_feedback_full(self):
        """Test creating execution feedback with all fields."""
        feedback = ExecutionFeedback(
            project_id=1,
            task_id=42,
            pattern_id=5,
            orchestration_pattern_id=3,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.94,
            planned_duration_minutes=120,
            actual_duration_minutes=138,
            blockers_encountered=["API deprecation", "timeout on third-party service"],
            adjustments_made=["Retried with exponential backoff", "Updated API version"],
            assumption_violations=["Third-party service latency higher than expected"],
            learning_extracted="Always include retry logic for external APIs",
            confidence_in_learning=0.85,
            quality_metrics={"code_coverage": 0.92, "test_pass_rate": 1.0},
            executor_agent="claude-3.5-sonnet",
            phase_number=2,
        )

        assert feedback.task_id == 42
        assert feedback.execution_outcome == ExecutionOutcome.SUCCESS
        assert feedback.actual_duration_minutes == 138
        assert len(feedback.blockers_encountered) == 2
        assert feedback.learning_extracted is not None

    def test_execution_feedback_calculate_variance(self):
        """Test duration variance calculation."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            planned_duration_minutes=100,
            actual_duration_minutes=150,
        )

        feedback.calculate_duration_variance()
        assert feedback.duration_variance_pct == 50.0

    def test_execution_feedback_variance_negative(self):
        """Test duration variance when actual is less than planned."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            planned_duration_minutes=100,
            actual_duration_minutes=75,
        )

        feedback.calculate_duration_variance()
        assert feedback.duration_variance_pct == -25.0

    def test_execution_feedback_quality_score_validation(self):
        """Test that execution quality score is validated between 0 and 1."""
        with pytest.raises(ValueError):
            ExecutionFeedback(
                project_id=1,
                execution_outcome=ExecutionOutcome.SUCCESS,
                execution_quality_score=1.5,  # Invalid: > 1.0
            )

    def test_execution_feedback_confidence_validation(self):
        """Test that confidence in learning is validated between 0 and 1."""
        with pytest.raises(ValueError):
            ExecutionFeedback(
                project_id=1,
                execution_outcome=ExecutionOutcome.SUCCESS,
                confidence_in_learning=-0.1,  # Invalid: < 0
            )

    def test_execution_feedback_partial_outcome(self):
        """Test execution feedback with partial outcome."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.PARTIAL,
            planned_duration_minutes=100,
            actual_duration_minutes=120,
            blockers_encountered=["Blocked on external dependency"],
        )

        assert feedback.execution_outcome == ExecutionOutcome.PARTIAL
        assert len(feedback.blockers_encountered) == 1

    def test_execution_feedback_blocked_outcome(self):
        """Test execution feedback with blocked outcome."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.BLOCKED,
            blockers_encountered=["Waiting for API credentials"],
            assumption_violations=["Credentials were not available as expected"],
        )

        assert feedback.execution_outcome == ExecutionOutcome.BLOCKED


class TestModelIntegration:
    """Integration tests between models."""

    def test_pattern_and_strategy_relationship(self):
        """Test that patterns and strategies can reference each other logically."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="hierarchical",
            description="Hierarchical decomposition",
        )

        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="adaptive-30min",
            description="30-minute chunks with adaptive depth",
            decomposition_type=DecompositionType.ADAPTIVE,
        )

        # Both can coexist for same project
        assert pattern.project_id == strategy.project_id

    def test_orchestration_pattern_with_multiple_agents(self):
        """Test orchestration pattern configuration with realistic team."""
        pattern = OrchestratorPattern(
            project_id=1,
            pattern_name="specialized-team",
            description="Team with specialized agents",
            coordination_type=CoordinationType.HIERARCHICAL,
            agent_roles=["project-manager", "frontend-expert", "backend-expert", "devops-expert"],
            num_agents=4,
        )

        assert len(pattern.agent_roles) == pattern.num_agents

    def test_validation_rules_with_dependencies(self):
        """Test validation rules that depend on other rules."""
        rule1 = ValidationRule(
            project_id=1,
            rule_name="check-dependencies",
            description="Verify all task dependencies",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="validate_dependencies",
        )

        rule2 = ValidationRule(
            project_id=1,
            rule_name="check-duration",
            description="Verify task duration",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="validate_duration",
            dependencies=["check-dependencies"],
        )

        assert "check-dependencies" in rule2.dependencies

    def test_feedback_links_pattern_to_execution(self):
        """Test execution feedback linking pattern and outcome."""
        feedback = ExecutionFeedback(
            project_id=1,
            pattern_id=10,
            execution_outcome=ExecutionOutcome.SUCCESS,
            learning_extracted="This pattern worked well for this task type",
        )

        assert feedback.pattern_id == 10
        assert feedback.execution_outcome == ExecutionOutcome.SUCCESS
        assert feedback.learning_extracted is not None


class TestEnumValues:
    """Tests for enum value serialization."""

    def test_pattern_type_enum_values(self):
        """Test all PatternType enum values."""
        assert PatternType.HIERARCHICAL == "hierarchical"
        assert PatternType.RECURSIVE == "recursive"
        assert PatternType.HYBRID == "hybrid"
        assert PatternType.GRAPH_BASED == "graph_based"
        assert PatternType.FLAT == "flat"

    def test_decomposition_type_enum_values(self):
        """Test all DecompositionType enum values."""
        assert DecompositionType.ADAPTIVE == "adaptive"
        assert DecompositionType.FIXED == "fixed"
        assert DecompositionType.HIERARCHICAL == "hierarchical"
        assert DecompositionType.RECURSIVE == "recursive"

    def test_validation_rule_type_enum_values(self):
        """Test all ValidationRuleType enum values."""
        assert ValidationRuleType.FORMAL == "formal"
        assert ValidationRuleType.HEURISTIC == "heuristic"
        assert ValidationRuleType.LLM_BASED == "llm_based"
        assert ValidationRuleType.SYMBOLIC == "symbolic"

    def test_execution_outcome_enum_values(self):
        """Test all ExecutionOutcome enum values."""
        assert ExecutionOutcome.SUCCESS == "success"
        assert ExecutionOutcome.FAILURE == "failure"
        assert ExecutionOutcome.PARTIAL == "partial"
        assert ExecutionOutcome.BLOCKED == "blocked"

    def test_coordination_type_enum_values(self):
        """Test all CoordinationType enum values."""
        assert CoordinationType.SEQUENTIAL == "sequential"
        assert CoordinationType.PARALLEL == "parallel"
        assert CoordinationType.HIERARCHICAL == "hierarchical"
        assert CoordinationType.HYBRID == "hybrid"
