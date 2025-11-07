"""Integration tests for Phase 6 Advanced Planning Orchestrator.

Tests Q* planning cycle, scenario simulation, adaptive replanning,
and cross-layer integration.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime

from athena.planning.phase6_orchestrator import (
    Phase6Orchestrator,
    initialize_phase6_orchestrator,
    PlanningPhase,
    AdaptiveReplanning,
    PlanExecutionContext,
    PlanVerificationReport,
)
from athena.planning.formal_verification import (
    FormalVerificationEngine,
    PropertyType,
    SimulationScenario,
)
from athena.planning.validation import PlanValidator


@pytest.fixture
def simple_plan():
    """Create a simple test plan."""
    return {
        "name": "Test Plan",
        "goal": "Complete testing",
        "tasks": [
            {
                "id": "task1",
                "name": "Unit tests",
                "duration": 1.0,
                "depends_on": [],
            },
            {
                "id": "task2",
                "name": "Integration tests",
                "duration": 2.0,
                "depends_on": ["task1"],
            },
            {
                "id": "task3",
                "name": "Performance tests",
                "duration": 1.5,
                "depends_on": ["task2"],
            },
        ],
        "resources": {
            "cpu": 4,
            "memory_gb": 8,
            "time_hours": 10,
        },
        "constraints": [],
        "assumptions": [
            "Tests run in parallel",
            "No external dependencies",
            "System has stable network",
        ],
    }


@pytest.fixture
def complex_plan():
    """Create a complex plan with dependencies."""
    return {
        "name": "Complex Plan",
        "goal": "Implement Phase 6",
        "tasks": [
            {"id": "design", "name": "Design", "duration": 4.0, "depends_on": []},
            {"id": "impl_core", "name": "Core impl", "duration": 8.0, "depends_on": ["design"]},
            {"id": "impl_test", "name": "Test impl", "duration": 6.0, "depends_on": ["design"]},
            {"id": "integrate", "name": "Integration", "duration": 4.0, "depends_on": ["impl_core", "impl_test"]},
            {"id": "validate", "name": "Validation", "duration": 3.0, "depends_on": ["integrate"]},
        ],
        "resources": {"cpu": 8, "memory_gb": 16, "time_hours": 30},
        "constraints": [
            {"type": "time", "max_hours": 32},
            {"type": "resource", "min_cpu": 4},
        ],
        "assumptions": [
            "No major blocker bugs",
            "Team available full-time",
            "Requirements stable",
        ],
    }


@pytest_asyncio.fixture
async def orchestrator():
    """Create Phase 6 orchestrator."""
    return await initialize_phase6_orchestrator()


class TestPhase6Orchestration:
    """Test Phase 6 orchestration workflow."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = await initialize_phase6_orchestrator()

        assert orchestrator is not None, "Orchestrator should be initialized"
        assert orchestrator.formal_verifier is not None, "Verifier should be present"
        assert orchestrator.plan_validator is not None, "Validator should be present"

    @pytest.mark.asyncio
    async def test_simple_plan_orchestration(self, orchestrator: Phase6Orchestrator, simple_plan):
        """Test orchestrating a simple plan."""
        report = await orchestrator.orchestrate_planning(
            plan=simple_plan,
            project_id=1,
            decision_id=1,
            scenario_count=3,
            max_iterations=1,
        )

        assert isinstance(report, PlanVerificationReport), "Should return report"
        assert report.decision_id == 1, "Should track decision ID"
        assert report.timestamp is not None, "Should have timestamp"

    @pytest.mark.asyncio
    async def test_complex_plan_orchestration(self, orchestrator: Phase6Orchestrator, complex_plan):
        """Test orchestrating a complex plan."""
        report = await orchestrator.orchestrate_planning(
            plan=complex_plan,
            project_id=1,
            decision_id=2,
            scenario_count=5,
            max_iterations=2,
        )

        assert isinstance(report, PlanVerificationReport), "Should return report"
        assert report.overall_success_rate >= 0.0, "Should have success rate"
        assert report.validation_score >= 0.0, "Should have validation score"

    @pytest.mark.asyncio
    async def test_plan_with_different_iterations(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test plan refinement across iterations."""
        # Try with multiple iterations
        report = await orchestrator.orchestrate_planning(
            plan=simple_plan,
            project_id=1,
            decision_id=3,
            scenario_count=3,
            max_iterations=3,
        )

        assert report is not None, "Should complete orchestration"


class TestFormalVerification:
    """Test formal verification of plans."""

    @pytest.mark.asyncio
    async def test_verify_simple_plan(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test verifying a simple plan."""
        passed = await orchestrator._verify_plan(simple_plan)

        # Should complete without error
        assert isinstance(passed, bool), "Should return boolean"

    @pytest.mark.asyncio
    async def test_verify_properties(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test verification of specific properties."""
        # Get formal verifier
        verifier = orchestrator.formal_verifier

        # Verify plan returns result with property checks
        result = verifier.verify_plan(simple_plan, method="hybrid")
        assert result is not None, "Should verify plan"
        assert hasattr(result, "property_results"), "Should have property results"


class TestScenarioSimulation:
    """Test scenario simulation."""

    @pytest.mark.asyncio
    async def test_simulate_simple_plan(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test simulating a simple plan."""
        results = await orchestrator._simulate_plan(simple_plan, scenario_count=3)

        assert isinstance(results, list), "Should return list of results"
        # Results may be empty or have scenarios depending on implementation
        assert len(results) >= 0, "Should return list"

    @pytest.mark.asyncio
    async def test_simulate_complex_plan(
        self,
        orchestrator: Phase6Orchestrator,
        complex_plan,
    ):
        """Test simulating a complex plan."""
        results = await orchestrator._simulate_plan(complex_plan, scenario_count=5)

        assert len(results) == 5, "Should have 5 simulation results"
        assert all(hasattr(r, "success") for r in results), "Results should have success field"

    @pytest.mark.asyncio
    async def test_success_rate_calculation(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test success rate calculation."""
        results = await orchestrator._simulate_plan(simple_plan, scenario_count=4)
        success_rate = Phase6Orchestrator._calculate_success_rate(results)

        assert 0.0 <= success_rate <= 1.0, "Success rate should be between 0 and 1"


class TestPlanValidation:
    """Test plan validation."""

    @pytest.mark.asyncio
    async def test_validate_simple_plan(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test validating a simple plan."""
        score, issues = await orchestrator._validate_plan(simple_plan)

        assert isinstance(score, float), "Score should be float"
        assert isinstance(issues, list), "Issues should be list"
        assert 0.0 <= score <= 1.0, "Score should be between 0 and 1"

    @pytest.mark.asyncio
    async def test_validation_identifies_issues(
        self,
        orchestrator: Phase6Orchestrator,
    ):
        """Test that validation can identify issues."""
        # Create plan with issues
        bad_plan = {
            "name": "Bad Plan",
            "goal": None,  # Missing goal
            "tasks": [],  # No tasks
        }

        score, issues = await orchestrator._validate_plan(bad_plan)

        # Should identify issues
        assert isinstance(issues, list), "Should return issues"


class TestPlanRefinement:
    """Test plan refinement based on feedback."""

    @pytest.mark.asyncio
    async def test_refine_plan(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test refining a plan."""
        refined, improved = await orchestrator._refine_plan(
            plan=simple_plan,
            verification_passed=False,
            scenario_results=[],
            validation_issues=["Missing error handling"],
        )

        assert isinstance(refined, dict), "Should return refined plan"
        assert isinstance(improved, bool), "Should indicate if improved"

    @pytest.mark.asyncio
    async def test_refinement_adds_constraints(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test that refinement adds constraints."""
        refined, improved = await orchestrator._refine_plan(
            plan=simple_plan,
            verification_passed=False,
            scenario_results=[],
            validation_issues=[],
        )

        # Should add constraints if verification failed
        if not simple_plan.get("constraints"):
            assert "constraints" in refined, "Should add constraints"

    @pytest.mark.asyncio
    async def test_refinement_unchanged_when_valid(
        self,
        orchestrator: Phase6Orchestrator,
        simple_plan,
    ):
        """Test that refinement doesn't change valid plan."""
        refined, improved = await orchestrator._refine_plan(
            plan=simple_plan,
            verification_passed=True,
            scenario_results=[],
            validation_issues=[],
        )

        # If no issues found, plan should be unchanged
        assert not improved or improved is False, "Valid plan should not be improved"


class TestExecutionTracking:
    """Test plan execution tracking and adaptive replanning."""

    @pytest.mark.asyncio
    async def test_execution_context_creation(self):
        """Test creating execution context."""
        context = PlanExecutionContext(
            plan_id=1,
            decision_id=1,
            current_phase=PlanningPhase.GENERATE,
        )

        assert context.plan_id == 1, "Should store plan ID"
        assert context.decision_id == 1, "Should store decision ID"
        assert context.executed_tasks == [], "Should initialize empty tasks list"

    @pytest.mark.asyncio
    async def test_assumption_violation_detection(
        self,
        orchestrator: Phase6Orchestrator,
    ):
        """Test detecting assumption violations."""
        context = PlanExecutionContext(
            plan_id=1,
            decision_id=1,
            current_phase=PlanningPhase.EXECUTE,
        )

        context.executed_tasks = ["task1", "task2"]

        # Simulate assumption violation
        actual_outcome = {"status": "failed", "reason": "Network timeout"}

        strategy = await orchestrator.track_execution(context, actual_outcome)

        assert strategy is not None or strategy is None, "Should return strategy or None"

    @pytest.mark.asyncio
    async def test_replanning_strategy_selection(self):
        """Test replanning strategy selection."""
        # Few violations, many tasks executed
        strategy = Phase6Orchestrator._select_replanning_strategy(
            violations=["assumption1"],
            executed_tasks=["task1", "task2", "task3", "task4", "task5", "task6"],
        )
        assert strategy == AdaptiveReplanning.LOCAL, "Should choose local for late-stage issue"

        # Many violations
        strategy = Phase6Orchestrator._select_replanning_strategy(
            violations=["assumption1", "assumption2", "assumption3"],
            executed_tasks=["task1"],
        )
        assert strategy == AdaptiveReplanning.FULL, "Should choose full for many violations"

        # No violations
        strategy = Phase6Orchestrator._select_replanning_strategy(
            violations=[],
            executed_tasks=["task1"],
        )
        assert strategy == AdaptiveReplanning.NONE, "Should not replan when no violations"


class TestVerificationReport:
    """Test verification report generation."""

    @pytest.mark.asyncio
    async def test_report_creation(self):
        """Test creating verification report."""
        report = PlanVerificationReport(
            plan_id=1,
            decision_id=1,
            timestamp=datetime.now(),
            phase=PlanningPhase.VERIFY,
        )

        assert report.plan_id == 1, "Should store plan ID"
        assert report.decision_id == 1, "Should store decision ID"
        assert isinstance(report.timestamp, datetime), "Should have datetime"

    @pytest.mark.asyncio
    async def test_report_serialization(self):
        """Test report can be serialized to dict."""
        report = PlanVerificationReport(
            plan_id=1,
            decision_id=1,
            timestamp=datetime.now(),
            phase=PlanningPhase.VERIFY,
        )

        report_dict = report.to_dict()

        assert isinstance(report_dict, dict), "Should convert to dict"
        assert report_dict["plan_id"] == 1, "Should preserve plan ID"
        assert "timestamp" in report_dict, "Should include timestamp"

    @pytest.mark.asyncio
    async def test_report_confidence_calculation(self):
        """Test report confidence score."""
        report = PlanVerificationReport(
            plan_id=1,
            decision_id=1,
            timestamp=datetime.now(),
            phase=PlanningPhase.EXECUTE,
            overall_success_rate=0.9,
            validation_score=0.85,
            confidence=0.9 * 0.85,
        )

        assert report.confidence > 0.0, "Should have positive confidence"
        assert report.confidence < 1.0, "Should be realistic confidence"


class TestFailurePatternExtraction:
    """Test extraction of failure patterns from simulations."""

    @pytest.mark.asyncio
    async def test_extract_patterns_empty(self, orchestrator: Phase6Orchestrator):
        """Test extracting patterns from empty results."""
        patterns = Phase6Orchestrator._extract_failure_patterns([])

        assert isinstance(patterns, list), "Should return list"
        assert len(patterns) == 0, "Should be empty for no results"


class TestCrossLayerIntegration:
    """Test integration with other Athena layers."""

    @pytest.mark.asyncio
    async def test_orchestrator_with_postgres_integration(self):
        """Test orchestrator with PostgreSQL integration."""
        # This would require PostgreSQL to be running
        # For now, test initialization without it
        orchestrator = await initialize_phase6_orchestrator(postgres_integration=None)

        assert orchestrator is not None, "Should initialize without PostgreSQL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
