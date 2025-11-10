"""Tests for planning and task decomposition tools."""

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
            "consistency": True
        },
        "recommendations": []
    })
    return verifier


@pytest.fixture
def decompose_tool(mock_planning_store):
    """Create decompose tool instance."""
    return DecomposeTool(mock_planning_store)


@pytest.fixture
def validate_plan_tool(mock_plan_validator):
    """Create validate plan tool instance."""
    return ValidatePlanTool(mock_plan_validator)


@pytest.fixture
def verify_plan_tool(mock_formal_verification):
    """Create verify plan tool instance."""
    return VerifyPlanTool(mock_formal_verification)


@pytest.fixture
def optimize_plan_tool(mock_planning_store):
    """Create optimize plan tool instance."""
    return OptimizePlanTool(mock_planning_store)


class TestDecomposeTool:
    """Test DecomposeTool functionality."""

    @pytest.mark.asyncio
    async def test_decompose_missing_task(self, decompose_tool):
        """Test decompose with missing task parameter."""
        result = await decompose_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_decompose_basic(self, decompose_tool, mock_planning_store):
        """Test basic task decomposition."""
        result = await decompose_tool.execute(task="Implement feature X")
        assert result.status == ToolStatus.SUCCESS
        assert result.data["plan_id"] == 1
        assert result.data["step_count"] > 0

    @pytest.mark.asyncio
    async def test_decompose_with_strategy(self, decompose_tool, mock_planning_store):
        """Test decomposition with custom strategy."""
        result = await decompose_tool.execute(
            task="Complex task",
            strategy="parallel"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["strategy"] == "parallel"

    @pytest.mark.asyncio
    async def test_decompose_with_depth(self, decompose_tool, mock_planning_store):
        """Test decomposition with custom depth."""
        result = await decompose_tool.execute(
            task="Task",
            max_depth=5
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["max_depth"] == 5

    @pytest.mark.asyncio
    async def test_decompose_returns_steps(self, decompose_tool, mock_planning_store):
        """Test that decomposition returns steps."""
        result = await decompose_tool.execute(task="Task")
        assert result.status == ToolStatus.SUCCESS
        assert "steps" in result.data
        assert isinstance(result.data["steps"], list)
        assert len(result.data["steps"]) > 0

    @pytest.mark.asyncio
    async def test_decompose_step_structure(self, decompose_tool, mock_planning_store):
        """Test structure of returned steps."""
        result = await decompose_tool.execute(task="Task")
        steps = result.data["steps"]

        for step in steps:
            assert "id" in step
            assert "title" in step
            assert "description" in step
            assert "status" in step
            assert "order" in step


class TestValidatePlanTool:
    """Test ValidatePlanTool functionality."""

    @pytest.mark.asyncio
    async def test_validate_missing_parameters(self, validate_plan_tool):
        """Test validate with missing parameters."""
        result = await validate_plan_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Must provide either" in result.error

    @pytest.mark.asyncio
    async def test_validate_by_plan_id(self, validate_plan_tool, mock_plan_validator):
        """Test validation by plan ID."""
        result = await validate_plan_tool.execute(plan_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_by_description(self, validate_plan_tool):
        """Test validation by plan description."""
        result = await validate_plan_tool.execute(
            plan_description="Sample plan description"
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_validate_with_feasibility_check(self, validate_plan_tool, mock_plan_validator):
        """Test validation with feasibility check."""
        result = await validate_plan_tool.execute(
            plan_id=1,
            check_feasibility=True
        )
        assert result.status == ToolStatus.SUCCESS

        # Verify feasibility check was passed
        call_kwargs = mock_plan_validator.validate.call_args[1]
        assert call_kwargs["check_feasibility"] is True

    @pytest.mark.asyncio
    async def test_validate_with_issues(self, validate_plan_tool, mock_plan_validator):
        """Test validation result with issues."""
        mock_plan_validator.validate.return_value = {
            "valid": False,
            "issues": ["Missing resource", "Circular dependency"],
            "score": 0.5
        }

        result = await validate_plan_tool.execute(plan_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["valid"] is False
        assert result.data["issue_count"] == 2


class TestVerifyPlanTool:
    """Test VerifyPlanTool functionality."""

    @pytest.mark.asyncio
    async def test_verify_missing_plan_id(self, verify_plan_tool):
        """Test verify with missing plan ID."""
        result = await verify_plan_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_verify_basic(self, verify_plan_tool, mock_formal_verification):
        """Test basic plan verification."""
        result = await verify_plan_tool.execute(plan_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["verified"] is True

    @pytest.mark.asyncio
    async def test_verify_custom_properties(self, verify_plan_tool, mock_formal_verification):
        """Test verification with custom properties."""
        result = await verify_plan_tool.execute(
            plan_id=1,
            properties=["optimality", "soundness"]
        )
        assert result.status == ToolStatus.SUCCESS

        # Verify properties were passed
        call_kwargs = mock_formal_verification.verify.call_args[1]
        assert "optimality" in call_kwargs["properties"]
        assert "soundness" in call_kwargs["properties"]

    @pytest.mark.asyncio
    async def test_verify_with_recommendations(self, verify_plan_tool, mock_formal_verification):
        """Test verification result with recommendations."""
        mock_formal_verification.verify.return_value = {
            "verified": False,
            "properties": {"optimality": False},
            "recommendations": ["Reorder steps", "Add resource allocation"]
        }

        result = await verify_plan_tool.execute(plan_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["verified"] is False
        assert len(result.data["recommendations"]) > 0


class TestOptimizePlanTool:
    """Test OptimizePlanTool functionality."""

    @pytest.mark.asyncio
    async def test_optimize_missing_plan_id(self, optimize_plan_tool):
        """Test optimize with missing plan ID."""
        result = await optimize_plan_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_optimize_for_time(self, optimize_plan_tool, mock_planning_store):
        """Test optimization for time objective."""
        result = await optimize_plan_tool.execute(
            plan_id=1,
            objective="time"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["objective"] == "time"
        assert result.data["status"] == "optimized"

    @pytest.mark.asyncio
    async def test_optimize_for_resources(self, optimize_plan_tool, mock_planning_store):
        """Test optimization for resource objective."""
        result = await optimize_plan_tool.execute(
            plan_id=1,
            objective="resources"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["objective"] == "resources"

    @pytest.mark.asyncio
    async def test_optimize_for_quality(self, optimize_plan_tool, mock_planning_store):
        """Test optimization for quality objective."""
        result = await optimize_plan_tool.execute(
            plan_id=1,
            objective="quality"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["objective"] == "quality"

    @pytest.mark.asyncio
    async def test_optimize_returns_improvements(self, optimize_plan_tool, mock_planning_store):
        """Test that optimization returns improvements."""
        result = await optimize_plan_tool.execute(plan_id=1)
        assert result.status == ToolStatus.SUCCESS
        assert "improvements" in result.data
        assert isinstance(result.data["improvements"], dict)


class TestPlanningToolsMetadata:
    """Test metadata for planning tools."""

    def test_decompose_metadata(self, decompose_tool):
        """Test decompose tool metadata."""
        assert decompose_tool.metadata.name == "decompose_task"
        assert "planning" in decompose_tool.metadata.tags
        assert decompose_tool.metadata.category == "planning"

    def test_validate_plan_metadata(self, validate_plan_tool):
        """Test validate plan tool metadata."""
        assert validate_plan_tool.metadata.name == "validate_plan"
        assert "validation" in validate_plan_tool.metadata.tags
        assert validate_plan_tool.metadata.category == "planning"

    def test_verify_plan_metadata(self, verify_plan_tool):
        """Test verify plan tool metadata."""
        assert verify_plan_tool.metadata.name == "verify_plan"
        assert "verification" in verify_plan_tool.metadata.tags
        assert verify_plan_tool.metadata.category == "planning"

    def test_optimize_plan_metadata(self, optimize_plan_tool):
        """Test optimize plan tool metadata."""
        assert optimize_plan_tool.metadata.name == "optimize_plan"
        assert "optimization" in optimize_plan_tool.metadata.tags
        assert optimize_plan_tool.metadata.category == "planning"

    def test_decompose_parameters(self, decompose_tool):
        """Test decompose parameters."""
        params = decompose_tool.metadata.parameters
        assert "task" in params
        assert "strategy" in params
        assert "max_depth" in params

    def test_validate_plan_parameters(self, validate_plan_tool):
        """Test validate plan parameters."""
        params = validate_plan_tool.metadata.parameters
        assert "plan_id" in params
        assert "plan_description" in params
        assert "check_feasibility" in params

    def test_verify_plan_parameters(self, verify_plan_tool):
        """Test verify plan parameters."""
        params = verify_plan_tool.metadata.parameters
        assert "plan_id" in params
        assert "properties" in params

    def test_optimize_plan_parameters(self, optimize_plan_tool):
        """Test optimize plan parameters."""
        params = optimize_plan_tool.metadata.parameters
        assert "plan_id" in params
        assert "objective" in params
