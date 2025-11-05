"""Integration tests for PlanningStore CRUD and search operations."""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.planning.models import (
    DecompositionStrategy,
    DecompositionType,
    ExecutionFeedback,
    ExecutionOutcome,
    OrchestratorPattern,
    CoordinationType,
    PatternType,
    PlanningPattern,
    ValidationRule,
    ValidationRuleType,
)
from athena.planning.store import PlanningStore


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


@pytest.fixture
def planning_store(test_db):
    """Create planning store."""
    return PlanningStore(test_db)


class TestPlanningPatternStore:
    """Tests for planning pattern storage and retrieval."""

    def test_create_and_retrieve_planning_pattern(self, planning_store):
        """Test creating and retrieving a planning pattern."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="hierarchical-decomposition",
            description="Decomposes tasks hierarchically by depth",
            success_rate=0.85,
            applicable_domains=["backend", "frontend"],
            applicable_task_types=["refactoring", "feature"],
        )

        pattern_id = planning_store.create_planning_pattern(pattern)
        assert pattern_id > 0

        retrieved = planning_store.get_planning_pattern(pattern_id)
        assert retrieved is not None
        assert retrieved.name == "hierarchical-decomposition"
        assert retrieved.success_rate == 0.85
        assert "backend" in retrieved.applicable_domains

    def test_find_patterns_by_task_type(self, planning_store):
        """Test finding patterns by task type."""
        # Create multiple patterns
        patterns = [
            PlanningPattern(
                project_id=1,
                pattern_type=PatternType.HIERARCHICAL,
                name="hier-refactor",
                description="For refactoring",
                success_rate=0.90,
                applicable_task_types=["refactoring"],
                complexity_range=(3, 8),
            ),
            PlanningPattern(
                project_id=1,
                pattern_type=PatternType.RECURSIVE,
                name="recur-feature",
                description="For features",
                success_rate=0.80,
                applicable_task_types=["feature"],
                complexity_range=(1, 10),
            ),
        ]

        for pattern in patterns:
            planning_store.create_planning_pattern(pattern)

        # Find patterns for refactoring
        found = planning_store.find_patterns_by_task_type(1, "refactoring", complexity=5)
        assert len(found) >= 1
        assert found[0].name == "hier-refactor"

    def test_find_patterns_by_domain(self, planning_store):
        """Test finding patterns by domain."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HYBRID,
            name="hybrid-robotics",
            description="For robotics tasks",
            success_rate=0.92,
            applicable_domains=["robotics", "safety-critical"],
        )

        planning_store.create_planning_pattern(pattern)

        found = planning_store.find_patterns_by_domain(1, "robotics")
        assert len(found) >= 1
        assert found[0].applicable_domains == ["robotics", "safety-critical"]

    def test_update_pattern_metrics(self, planning_store):
        """Test updating pattern metrics after execution."""
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.GRAPH_BASED,
            name="graph-planning",
            description="Graph-based planning",
            success_rate=0.0,
            execution_count=0,
        )

        pattern_id = planning_store.create_planning_pattern(pattern)

        # Update metrics
        updated = planning_store.update_planning_pattern_metrics(
            pattern_id, success_rate=0.88, quality_score=0.90, execution_count=10
        )

        assert updated
        retrieved = planning_store.get_planning_pattern(pattern_id)
        assert retrieved.success_rate == 0.88
        assert retrieved.execution_count == 10

    def test_pattern_not_found(self, planning_store):
        """Test retrieving non-existent pattern."""
        retrieved = planning_store.get_planning_pattern(99999)
        assert retrieved is None


class TestDecompositionStrategyStore:
    """Tests for decomposition strategy storage."""

    def test_create_and_retrieve_strategy(self, planning_store):
        """Test creating and retrieving a decomposition strategy."""
        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="adaptive-30min",
            description="Adaptive decomposition with 30-minute chunks",
            decomposition_type=DecompositionType.ADAPTIVE,
            chunk_size_minutes=30,
            adaptive_depth=True,
            success_rate=0.88,
        )

        strategy_id = planning_store.create_decomposition_strategy(strategy)
        assert strategy_id > 0

        retrieved = planning_store.get_decomposition_strategy(strategy_id)
        assert retrieved is not None
        assert retrieved.strategy_name == "adaptive-30min"
        assert retrieved.chunk_size_minutes == 30
        assert retrieved.adaptive_depth is True

    def test_find_strategies_by_task_type(self, planning_store):
        """Test finding strategies by task type."""
        strategies = [
            DecompositionStrategy(
                project_id=1,
                strategy_name="refactor-strategy",
                description="For refactoring",
                decomposition_type=DecompositionType.HIERARCHICAL,
                applicable_task_types=["refactoring"],
                success_rate=0.92,
            ),
            DecompositionStrategy(
                project_id=1,
                strategy_name="feature-strategy",
                description="For features",
                decomposition_type=DecompositionType.RECURSIVE,
                applicable_task_types=["feature", "bugfix"],
                success_rate=0.85,
            ),
        ]

        for strategy in strategies:
            planning_store.create_decomposition_strategy(strategy)

        # Find refactoring strategies
        found = planning_store.find_strategies_by_type(1, "refactoring")
        assert len(found) >= 1
        assert "refactoring" in found[0].applicable_task_types

    def test_strategy_with_validation_gates(self, planning_store):
        """Test strategy with validation gates."""
        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="gated-strategy",
            description="With pre and post gates",
            decomposition_type=DecompositionType.HIERARCHICAL,
            validation_gates=["pre_execution", "post_phase", "milestone"],
        )

        strategy_id = planning_store.create_decomposition_strategy(strategy)
        retrieved = planning_store.get_decomposition_strategy(strategy_id)

        assert len(retrieved.validation_gates) == 3
        assert "pre_execution" in retrieved.validation_gates


class TestOrchestratorPatternStore:
    """Tests for orchestrator pattern storage."""

    def test_create_and_retrieve_orchestrator_pattern(self, planning_store):
        """Test creating and retrieving an orchestrator pattern."""
        pattern = OrchestratorPattern(
            project_id=1,
            pattern_name="parallel-specialists",
            description="Parallel specialist agents",
            coordination_type=CoordinationType.PARALLEL,
            agent_roles=["orchestrator", "frontend", "backend", "devops"],
            num_agents=4,
            speedup_factor=3.5,
            handoff_success_rate=0.95,
        )

        pattern_id = planning_store.create_orchestrator_pattern(pattern)
        assert pattern_id > 0

        retrieved = planning_store.get_orchestrator_pattern(pattern_id)
        assert retrieved is not None
        assert retrieved.pattern_name == "parallel-specialists"
        assert len(retrieved.agent_roles) == 4
        assert retrieved.speedup_factor == 3.5

    def test_find_orchestration_patterns_by_num_agents(self, planning_store):
        """Test finding orchestration patterns by number of agents."""
        patterns = [
            OrchestratorPattern(
                project_id=1,
                pattern_name="pair",
                description="Two agents",
                agent_roles=["coordinator", "executor"],
                coordination_type=CoordinationType.SEQUENTIAL,
                num_agents=2,
                speedup_factor=1.2,
            ),
            OrchestratorPattern(
                project_id=1,
                pattern_name="trio",
                description="Three agents",
                agent_roles=["coordinator", "executor", "validator"],
                coordination_type=CoordinationType.PARALLEL,
                num_agents=3,
                speedup_factor=2.5,
            ),
        ]

        for pattern in patterns:
            planning_store.create_orchestrator_pattern(pattern)

        # Find 3-agent patterns
        found = planning_store.find_orchestration_patterns(1, num_agents=3)
        assert len(found) >= 1
        assert found[0].num_agents == 3

    def test_find_orchestration_patterns_by_domain(self, planning_store):
        """Test finding orchestration patterns by domain."""
        pattern = OrchestratorPattern(
            project_id=1,
            pattern_name="deployment-team",
            description="For deployment tasks",
            agent_roles=["lead", "deployer", "monitor", "rollback"],
            coordination_type=CoordinationType.HIERARCHICAL,
            num_agents=4,
            applicable_domains=["deployment", "devops"],
        )

        planning_store.create_orchestrator_pattern(pattern)

        found = planning_store.find_orchestration_patterns(1, num_agents=4, domain="deployment")
        assert len(found) >= 1
        assert "deployment" in found[0].applicable_domains


class TestValidationRuleStore:
    """Tests for validation rule storage."""

    def test_create_and_retrieve_validation_rule(self, planning_store):
        """Test creating and retrieving a validation rule."""
        rule = ValidationRule(
            project_id=1,
            rule_name="check-task-duration",
            description="Ensures task duration is reasonable",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="validate_task_duration",
            risk_level="medium",
            accuracy_pct=85.5,
        )

        rule_id = planning_store.create_validation_rule(rule)
        assert rule_id > 0

        retrieved = planning_store.get_validation_rule(rule_id)
        assert retrieved is not None
        assert retrieved.rule_name == "check-task-duration"
        assert retrieved.accuracy_pct == 85.5

    def test_find_rules_by_task_type(self, planning_store):
        """Test finding rules by task type."""
        rules = [
            ValidationRule(
                project_id=1,
                rule_name="refactor-duration",
                description="Check refactoring duration",
                rule_type=ValidationRuleType.HEURISTIC,
                check_function="check_refactor",
                applicable_to_task_types=["refactoring"],
                f1_score=0.92,
            ),
            ValidationRule(
                project_id=1,
                rule_name="feature-scope",
                description="Check feature scope",
                rule_type=ValidationRuleType.LLM_BASED,
                check_function="check_feature",
                applicable_to_task_types=["feature"],
                f1_score=0.85,
            ),
        ]

        for rule in rules:
            planning_store.create_validation_rule(rule)

        # Find refactoring rules
        found = planning_store.find_validation_rules_by_task_type(1, "refactoring")
        assert len(found) >= 1
        assert "refactoring" in found[0].applicable_to_task_types

    def test_find_rules_by_risk_level(self, planning_store):
        """Test finding rules by risk level."""
        rules = [
            ValidationRule(
                project_id=1,
                rule_name="critical-check",
                description="Critical validation",
                rule_type=ValidationRuleType.FORMAL,
                check_function="verify",
                risk_level="critical",
                f1_score=0.98,
            ),
            ValidationRule(
                project_id=1,
                rule_name="low-check",
                description="Low risk check",
                rule_type=ValidationRuleType.HEURISTIC,
                check_function="simple_check",
                risk_level="low",
                f1_score=0.75,
            ),
        ]

        for rule in rules:
            planning_store.create_validation_rule(rule)

        # Find critical rules
        found = planning_store.find_validation_rules_by_risk(1, "critical")
        assert len(found) >= 1
        assert found[0].risk_level == "critical"

    def test_rule_with_dependencies(self, planning_store):
        """Test rule with dependencies on other rules."""
        rule = ValidationRule(
            project_id=1,
            rule_name="dependency-checker",
            description="Depends on other rules",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="check_deps",
            dependencies=["check-structure", "check-duration"],
        )

        rule_id = planning_store.create_validation_rule(rule)
        retrieved = planning_store.get_validation_rule(rule_id)

        assert len(retrieved.dependencies) == 2
        assert "check-structure" in retrieved.dependencies


class TestExecutionFeedbackStore:
    """Tests for execution feedback storage."""

    def test_record_and_retrieve_execution_feedback(self, planning_store):
        """Test recording and retrieving execution feedback."""
        feedback = ExecutionFeedback(
            project_id=1,
            pattern_id=1,
            task_id=10,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.92,
            planned_duration_minutes=120,
            actual_duration_minutes=138,
            learning_extracted="Include retry logic for external APIs",
        )

        feedback_id = planning_store.record_execution_feedback(feedback)
        assert feedback_id > 0

        retrieved = planning_store.get_execution_feedback(feedback_id)
        assert retrieved is not None
        assert retrieved.execution_outcome == ExecutionOutcome.SUCCESS
        assert retrieved.execution_quality_score == 0.92

    def test_duration_variance_calculation(self, planning_store):
        """Test that duration variance is calculated correctly."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            planned_duration_minutes=100,
            actual_duration_minutes=150,
        )

        feedback_id = planning_store.record_execution_feedback(feedback)
        retrieved = planning_store.get_execution_feedback(feedback_id)

        assert retrieved.duration_variance_pct == 50.0

    def test_get_feedback_for_pattern(self, planning_store):
        """Test retrieving all feedback for a pattern."""
        pattern_id = 1
        outcomes = [
            (ExecutionOutcome.SUCCESS, 0.95),
            (ExecutionOutcome.SUCCESS, 0.90),
            (ExecutionOutcome.PARTIAL, 0.75),
        ]

        for outcome, quality in outcomes:
            feedback = ExecutionFeedback(
                project_id=1,
                pattern_id=pattern_id,
                execution_outcome=outcome,
                execution_quality_score=quality,
            )
            planning_store.record_execution_feedback(feedback)

        feedback_list = planning_store.get_feedback_for_pattern(pattern_id)
        assert len(feedback_list) >= 3

    def test_feedback_with_blockers_and_adjustments(self, planning_store):
        """Test feedback with blockers and adjustments."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.PARTIAL,
            blockers_encountered=["API deprecation", "timeout on third-party"],
            adjustments_made=["Retried with backoff", "Updated API version"],
            assumption_violations=["Third-party latency higher than expected"],
        )

        feedback_id = planning_store.record_execution_feedback(feedback)
        retrieved = planning_store.get_execution_feedback(feedback_id)

        assert len(retrieved.blockers_encountered) == 2
        assert len(retrieved.adjustments_made) == 2
        assert len(retrieved.assumption_violations) == 1

    def test_feedback_with_quality_metrics(self, planning_store):
        """Test feedback with custom quality metrics."""
        feedback = ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            quality_metrics={
                "code_coverage": 0.92,
                "test_pass_rate": 1.0,
                "performance_improvement_pct": 15,
            },
        )

        feedback_id = planning_store.record_execution_feedback(feedback)
        retrieved = planning_store.get_execution_feedback(feedback_id)

        assert retrieved.quality_metrics["code_coverage"] == 0.92
        assert retrieved.quality_metrics["test_pass_rate"] == 1.0


class TestStorageIntegration:
    """Integration tests across multiple store operations."""

    def test_planning_workflow_full_cycle(self, planning_store):
        """Test a full planning workflow: pattern → strategy → execution → feedback."""
        # 1. Create a planning pattern
        pattern = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="workflow-pattern",
            description="Test workflow",
            success_rate=0.0,
            execution_count=0,
        )
        pattern_id = planning_store.create_planning_pattern(pattern)

        # 2. Create a decomposition strategy
        strategy = DecompositionStrategy(
            project_id=1,
            strategy_name="workflow-strategy",
            description="Test strategy",
            decomposition_type=DecompositionType.ADAPTIVE,
        )
        strategy_id = planning_store.create_decomposition_strategy(strategy)

        # 3. Create validation rules
        rule = ValidationRule(
            project_id=1,
            rule_name="workflow-rule",
            description="Test rule",
            rule_type=ValidationRuleType.HEURISTIC,
            check_function="test_check",
        )
        rule_id = planning_store.create_validation_rule(rule)

        # 4. Record execution feedback
        feedback = ExecutionFeedback(
            project_id=1,
            pattern_id=pattern_id,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.88,
            learning_extracted="Pattern worked well",
        )
        feedback_id = planning_store.record_execution_feedback(feedback)

        # 5. Verify all were created
        assert planning_store.get_planning_pattern(pattern_id) is not None
        assert planning_store.get_decomposition_strategy(strategy_id) is not None
        assert planning_store.get_validation_rule(rule_id) is not None
        assert planning_store.get_execution_feedback(feedback_id) is not None

        # 6. Update pattern metrics based on feedback
        planning_store.update_planning_pattern_metrics(
            pattern_id, success_rate=0.88, quality_score=0.90, execution_count=1
        )

        updated_pattern = planning_store.get_planning_pattern(pattern_id)
        assert updated_pattern.success_rate == 0.88

    def test_multiple_projects_isolation(self, planning_store):
        """Test that patterns from different projects are isolated."""
        # Create patterns for different projects
        pattern1 = PlanningPattern(
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="project1-pattern",
            description="For project 1",
        )

        pattern2 = PlanningPattern(
            project_id=2,
            pattern_type=PatternType.RECURSIVE,
            name="project2-pattern",
            description="For project 2",
        )

        planning_store.create_planning_pattern(pattern1)
        planning_store.create_planning_pattern(pattern2)

        # Find patterns for project 1 only
        found = planning_store.find_patterns_by_task_type(1, "any")
        # Should find only project 1 patterns
        assert all(p.project_id == 1 for p in found)
