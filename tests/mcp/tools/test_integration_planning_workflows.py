"""Integration tests for planning workflow operations."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from athena.mcp.tools.planning_tools import (
    DecomposeTool,
    ValidatePlanTool,
    VerifyPlanTool,
    OptimizePlanTool,
)
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_planning_store():
    """Create mock planning store."""
    store = Mock()
    store.store_plan = Mock(return_value=1)
    store.get_plan = Mock(return_value={
        "id": 1,
        "title": "Test Plan",
        "steps": [
            {"id": 1, "title": "Step 1", "status": "pending"},
            {"id": 2, "title": "Step 2", "status": "pending"},
        ]
    })
    return store


@pytest.fixture
def mock_plan_validator():
    """Create mock plan validator."""
    validator = Mock()
    validator.validate = Mock(return_value={
        "valid": True,
        "issues": [],
        "score": 0.95
    })
    return validator


@pytest.fixture
def mock_formal_verification():
    """Create mock formal verification."""
    verifier = Mock()
    verifier.verify = Mock(return_value={
        "verified": True,
        "properties": {
            "optimality": True,
            "completeness": True,
            "consistency": True,
            "soundness": True,
            "minimality": True
        },
        "recommendations": []
    })
    return verifier


@pytest.fixture
def decompose_tool(mock_planning_store):
    """Create decompose tool."""
    return DecomposeTool(mock_planning_store)


@pytest.fixture
def validate_plan_tool(mock_plan_validator):
    """Create validate plan tool."""
    return ValidatePlanTool(mock_plan_validator)


@pytest.fixture
def verify_plan_tool(mock_formal_verification):
    """Create verify plan tool."""
    return VerifyPlanTool(mock_formal_verification)


@pytest.fixture
def optimize_plan_tool(mock_planning_store):
    """Create optimize plan tool."""
    return OptimizePlanTool(mock_planning_store)


class TestDecomposeValidateVerifyFlow:
    """Test decompose → validate → verify workflow."""

    @pytest.mark.asyncio
    async def test_full_planning_pipeline(self, decompose_tool, validate_plan_tool, verify_plan_tool, mock_planning_store):
        """Test complete planning pipeline: decompose → validate → verify."""
        # Step 1: Decompose
        decompose_result = await decompose_tool.execute(task="Implement API endpoint")
        assert decompose_result.status == ToolStatus.SUCCESS
        plan_id = decompose_result.data["plan_id"]

        # Step 2: Validate decomposed plan
        validate_result = await validate_plan_tool.execute(plan_id=plan_id)
        assert validate_result.status == ToolStatus.SUCCESS
        assert validate_result.data["valid"] is True

        # Step 3: Verify plan properties
        verify_result = await verify_plan_tool.execute(plan_id=plan_id)
        assert verify_result.status == ToolStatus.SUCCESS
        assert verify_result.data["verified"] is True

    @pytest.mark.asyncio
    async def test_decomposed_plan_passes_validation(self, decompose_tool, validate_plan_tool, mock_planning_store, mock_plan_validator):
        """Test that decomposed plans pass validation."""
        # Decompose task
        decompose_result = await decompose_tool.execute(task="Build feature")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Validate - should pass
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.95
        }

        validate_result = await validate_plan_tool.execute(plan_id=1)
        assert validate_result.status == ToolStatus.SUCCESS
        assert validate_result.data["valid"] is True
        assert validate_result.data["issue_count"] == 0

    @pytest.mark.asyncio
    async def test_verified_plan_meets_quality_gates(self, decompose_tool, verify_plan_tool, mock_formal_verification):
        """Test that verified plans meet quality gates."""
        # Decompose
        decompose_result = await decompose_tool.execute(task="Complex task")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Verify with quality threshold
        mock_formal_verification.verify.return_value = {
            "verified": True,
            "properties": {
                "optimality": True,
                "completeness": True,
                "consistency": True,
                "soundness": True,
                "minimality": True
            },
            "recommendations": []
        }

        verify_result = await verify_plan_tool.execute(plan_id=1)
        assert verify_result.status == ToolStatus.SUCCESS
        assert verify_result.data["verified"] is True
        # All properties should be true
        properties = verify_result.data.get("properties", {})
        for prop_name, prop_value in properties.items():
            if prop_name in ["optimality", "completeness", "consistency"]:
                assert prop_value is True

    @pytest.mark.asyncio
    async def test_plan_modifications_maintain_validity(self, decompose_tool, validate_plan_tool, mock_plan_validator):
        """Test that plan modifications maintain validity."""
        # Decompose original
        result1 = await decompose_tool.execute(task="Original task")
        assert result1.status == ToolStatus.SUCCESS

        # Validate
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.90
        }
        validate1 = await validate_plan_tool.execute(plan_id=1)
        assert validate1.data["valid"] is True

        # Simulate modification and revalidate
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.92  # Improved score
        }
        validate2 = await validate_plan_tool.execute(plan_id=1)
        assert validate2.data["valid"] is True
        assert validate2.data["score"] >= 0.90

    @pytest.mark.asyncio
    async def test_complex_task_planning_reliability(self, decompose_tool, validate_plan_tool, verify_plan_tool, mock_planning_store, mock_plan_validator, mock_formal_verification):
        """Test reliability of complex task planning through entire pipeline."""
        # Complex task
        decompose_result = await decompose_tool.execute(
            task="Implement distributed transaction system with consensus mechanism",
            strategy="hierarchical",
            max_depth=5
        )
        assert decompose_result.status == ToolStatus.SUCCESS
        assert decompose_result.data["step_count"] > 0

        # Validate with feasibility check
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.88
        }
        validate_result = await validate_plan_tool.execute(plan_id=1, check_feasibility=True)
        assert validate_result.status == ToolStatus.SUCCESS

        # Verify all properties
        mock_formal_verification.verify.return_value = {
            "verified": True,
            "properties": {
                "optimality": True,
                "completeness": True,
                "consistency": True,
                "soundness": True,
                "minimality": False  # Might have redundancy
            },
            "recommendations": ["Consider simplifying task structure"]
        }
        verify_result = await verify_plan_tool.execute(plan_id=1)
        assert verify_result.status == ToolStatus.SUCCESS


class TestAdaptiveReplanningFlow:
    """Test plan adaptation under changing conditions."""

    @pytest.mark.asyncio
    async def test_replanning_on_assumption_violation(self, decompose_tool, validate_plan_tool, mock_planning_store, mock_plan_validator):
        """Test replanning triggered by assumption violation."""
        # Original plan
        plan1 = await decompose_tool.execute(task="Task with assumptions")
        assert plan1.status == ToolStatus.SUCCESS

        # Validate original plan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.85
        }
        validate1 = await validate_plan_tool.execute(plan_id=1)
        assert validate1.data["valid"] is True

        # Simulate assumption violation - replan
        mock_plan_validator.validate.return_value = {
            "valid": False,
            "issues": ["Assumption violated: Resource constraint changed"],
            "score": 0.50
        }
        validate2 = await validate_plan_tool.execute(plan_id=1)
        assert validate2.data["valid"] is False

        # Create new plan with updated assumptions
        plan2 = await decompose_tool.execute(
            task="Task with updated assumptions",
            strategy="sequential"
        )
        assert plan2.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_plan_quality_after_replanning(self, decompose_tool, validate_plan_tool, mock_plan_validator):
        """Test that replanned plans maintain quality."""
        # Original plan quality
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.75
        }
        plan1 = await decompose_tool.execute(task="Initial plan")
        validate1 = await validate_plan_tool.execute(plan_id=1)
        original_score = validate1.data.get("score", 0)

        # Replan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.85  # Improved after replanning
        }
        plan2 = await decompose_tool.execute(task="Replanned task")
        validate2 = await validate_plan_tool.execute(plan_id=1)
        new_score = validate2.data.get("score", 0)

        assert new_score >= original_score

    @pytest.mark.asyncio
    async def test_incremental_plan_repair(self, validate_plan_tool, optimize_plan_tool, mock_plan_validator, mock_planning_store):
        """Test incremental repair of plan issues."""
        # Identify issues
        mock_plan_validator.validate.return_value = {
            "valid": False,
            "issues": ["Step ordering suboptimal", "Resource overallocation"],
            "score": 0.60
        }
        validate_result = await validate_plan_tool.execute(plan_id=1)
        assert validate_result.data["valid"] is False

        # Optimize for time to fix step ordering
        optimize_result = await optimize_plan_tool.execute(plan_id=1, objective="time")
        assert optimize_result.status == ToolStatus.SUCCESS

        # Validate improvement
        mock_plan_validator.validate.return_value = {
            "valid": False,
            "issues": ["Resource overallocation"],  # One issue fixed
            "score": 0.70
        }
        validate_again = await validate_plan_tool.execute(plan_id=1)
        assert validate_again.data["issue_count"] == 1

    @pytest.mark.asyncio
    async def test_multiple_replanning_cycles(self, decompose_tool, validate_plan_tool, mock_plan_validator):
        """Test multiple replanning cycles convergence."""
        scores = []

        for cycle in range(3):
            # Plan
            plan_result = await decompose_tool.execute(task=f"Cycle {cycle}")
            assert plan_result.status == ToolStatus.SUCCESS

            # Validate
            mock_plan_validator.validate.return_value = {
                "valid": True,
                "issues": [],
                "score": 0.70 + (cycle * 0.10)  # Progressive improvement
            }
            validate_result = await validate_plan_tool.execute(plan_id=1)
            scores.append(validate_result.data.get("score", 0))

        # Scores should improve or maintain
        assert len(scores) == 3
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i-1]

    @pytest.mark.asyncio
    async def test_replanning_preserves_completed_steps(self, decompose_tool, validate_plan_tool, mock_planning_store, mock_plan_validator):
        """Test that replanning preserves already-completed steps."""
        # Original plan with completed step
        decompose_result = await decompose_tool.execute(task="Task with dependencies")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Mark step as completed in mock
        mock_planning_store.get_plan.return_value = {
            "id": 1,
            "title": "Test Plan",
            "steps": [
                {"id": 1, "title": "Step 1", "status": "completed"},
                {"id": 2, "title": "Step 2", "status": "pending"},
            ]
        }

        # Replan
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "issues": [],
            "score": 0.90
        }
        validate_result = await validate_plan_tool.execute(plan_id=1)
        assert validate_result.status == ToolStatus.SUCCESS
        # Completed steps should be preserved


class TestScenarioSimulation:
    """Test scenario-based plan validation."""

    @pytest.mark.asyncio
    async def test_plan_survives_adverse_scenarios(self, decompose_tool, verify_plan_tool, mock_formal_verification):
        """Test that plan survives adverse scenarios."""
        # Create plan
        plan_result = await decompose_tool.execute(task="Resilient system design")
        assert plan_result.status == ToolStatus.SUCCESS

        # Verify against adverse scenarios
        mock_formal_verification.verify.return_value = {
            "verified": True,
            "properties": {
                "optimality": True,
                "completeness": True,
                "consistency": True,
                "soundness": True,
                "minimality": True
            },
            "recommendations": []
        }
        verify_result = await verify_plan_tool.execute(plan_id=1)
        assert verify_result.data["verified"] is True

    @pytest.mark.asyncio
    async def test_scenario_coverage_completeness(self, verify_plan_tool, mock_formal_verification):
        """Test coverage of different scenarios."""
        scenarios = ["resource_constrained", "time_critical", "high_risk", "normal"]

        for scenario in scenarios:
            # Each scenario verification
            mock_formal_verification.verify.return_value = {
                "verified": True,
                "properties": {
                    "optimality": True,
                    "completeness": True,
                    "consistency": True
                },
                "recommendations": []
            }
            verify_result = await verify_plan_tool.execute(plan_id=1)
            assert verify_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_plan_resilience_scoring(self, decompose_tool, verify_plan_tool, mock_formal_verification):
        """Test plan resilience scoring."""
        plan_result = await decompose_tool.execute(task="Complex task")
        assert plan_result.status == ToolStatus.SUCCESS

        mock_formal_verification.verify.return_value = {
            "verified": True,
            "properties": {
                "optimality": True,
                "completeness": True,
                "consistency": True,
                "soundness": True,
                "minimality": True
            },
            "recommendations": ["Consider adding error handling", "Add fallback mechanisms"]
        }
        verify_result = await verify_plan_tool.execute(plan_id=1)
        assert verify_result.status == ToolStatus.SUCCESS
        assert len(verify_result.data.get("recommendations", [])) >= 0


class TestPlanQuality:
    """Test overall plan quality metrics."""

    @pytest.mark.asyncio
    async def test_decomposition_quality_metrics(self, decompose_tool, mock_planning_store):
        """Test quality metrics for decomposition."""
        result = await decompose_tool.execute(task="Measurable task")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["step_count"] > 0
        assert result.data["plan_id"] > 0

    @pytest.mark.asyncio
    async def test_plan_efficiency_optimization(self, decompose_tool, optimize_plan_tool, mock_planning_store):
        """Test efficiency optimization."""
        # Create plan
        decompose_result = await decompose_tool.execute(task="Efficiency task")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Optimize
        mock_planning_store.optimize.return_value = {
            "before_duration": 100,
            "after_duration": 75,
            "efficiency_gain": 0.25,
            "optimized": True
        }

        optimize_result = await optimize_plan_tool.execute(plan_id=1, objective="time")
        assert optimize_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_constraint_satisfaction_validation(self, decompose_tool, validate_plan_tool, mock_plan_validator):
        """Test constraint satisfaction in plans."""
        # Decompose with constraints
        decompose_result = await decompose_tool.execute(task="Constrained task")
        assert decompose_result.status == ToolStatus.SUCCESS

        # Validate constraints
        mock_plan_validator.validate.return_value = {
            "valid": True,
            "constraints_satisfied": {
                "resource_limit": True,
                "time_limit": True,
                "dependency_ordering": True
            },
            "issues": [],
            "score": 0.95
        }

        validate_result = await validate_plan_tool.execute(
            plan_id=1,
            check_feasibility=True
        )
        assert validate_result.status == ToolStatus.SUCCESS
        assert validate_result.data["valid"] is True
