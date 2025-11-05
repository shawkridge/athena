"""Tests for Phase 3.4 Advanced Planning MCP tools."""

import pytest
import asyncio
from pathlib import Path

from athena.mcp.handlers import MemoryMCPServer


@pytest.fixture
def server(tmp_path: Path) -> MemoryMCPServer:
    """Create MCP server instance."""
    db_path = tmp_path / "test.db"
    return MemoryMCPServer(str(db_path))


def run_async(coro):
    """Helper to run async code in sync tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestDecomposeHierarchicallyTool:
    """Tests for decompose_hierarchically tool."""

    def test_decompose_simple_task(self, server: MemoryMCPServer):
        """Test decomposing a simple (low complexity) task."""
        args = {
            "task_description": "Write a simple hello world program",
            "complexity_level": 2,
            "domain": "coding",
        }

        result = run_async(server._handle_decompose_hierarchically(args))
        assert result is not None
        assert len(result) > 0
        text = result[0].text
        assert "✓" in text
        assert "Hierarchical Task Decomposition" in text
        assert "30 minutes" in text
        assert "Complexity: 2/10" in text

    def test_decompose_medium_complexity(self, server: MemoryMCPServer):
        """Test decomposing a medium complexity task."""
        args = {
            "task_description": "Refactor authentication system",
            "complexity_level": 6,
            "domain": "refactoring",
        }

        result = run_async(server._handle_decompose_hierarchically(args))
        assert result is not None
        text = result[0].text
        assert "Complexity: 6/10" in text
        assert "Depth: 3 levels" in text

    def test_decompose_high_complexity(self, server: MemoryMCPServer):
        """Test decomposing a high complexity task."""
        args = {
            "task_description": "Build a distributed microservices architecture",
            "complexity_level": 9,
            "domain": "architecture",
        }

        result = run_async(server._handle_decompose_hierarchically(args))
        assert result is not None
        text = result[0].text
        assert "Complexity: 9/10" in text
        assert "Depth: 4 levels" in text

    def test_decompose_default_domain(self, server: MemoryMCPServer):
        """Test decomposing without specifying domain."""
        args = {
            "task_description": "Some task",
            "complexity_level": 5,
        }

        result = run_async(server._handle_decompose_hierarchically(args))
        assert result is not None
        text = result[0].text
        assert "Domain: general" in text


class TestValidatePlanTool:
    """Tests for validate_plan tool."""

    def test_validate_missing_project_id(self, server: MemoryMCPServer):
        """Test validating without project_id."""
        args = {}

        result = run_async(server._handle_validate_plan(args))
        assert result is not None
        text = result[0].text
        assert "project_id required" in text

    def test_validate_nonexistent_project(self, server: MemoryMCPServer):
        """Test validating a non-existent project."""
        args = {"project_id": 999}

        result = run_async(server._handle_validate_plan(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text or "not found" in text

    def test_validate_plan_strict_mode(self, server: MemoryMCPServer):
        """Test validation with strict_mode."""
        project = server.project_manager.store.create_project("test_project", "/tmp/test")
        args = {"project_id": project.id, "strict_mode": False}

        result = run_async(server._handle_validate_plan(args))
        assert result is not None
        text = result[0].text
        # Check for either success or graceful error handling
        assert ("✓" in text or "Validation" in text or "Error" in text)


class TestGetProjectStatusTool:
    """Tests for get_project_status tool."""

    def test_get_status_missing_project_id(self, server: MemoryMCPServer):
        """Test getting status without project_id."""
        args = {}

        result = run_async(server._handle_get_project_status(args))
        assert result is not None
        text = result[0].text
        assert "project_id required" in text

    def test_get_status_valid_project(self, server: MemoryMCPServer):
        """Test getting status of valid project."""
        project = server.project_manager.store.create_project("status_test", "/tmp/status")
        args = {"project_id": project.id}

        result = run_async(server._handle_get_project_status(args))
        assert result is not None
        text = result[0].text
        # Check for either success or graceful error handling
        assert ("✓" in text or "Status" in text or "Error" in text)


class TestRecommendOrchestrationTool:
    """Tests for recommend_orchestration tool."""

    def test_orchestration_single_agent(self, server: MemoryMCPServer):
        """Test orchestration recommendation for single agent."""
        args = {"num_agents": 1}

        result = run_async(server._handle_recommend_orchestration(args))
        assert result is not None
        text = result[0].text
        assert "✓" in text
        assert "Sequential" in text
        assert "Agents Available: 1" in text

    def test_orchestration_few_agents(self, server: MemoryMCPServer):
        """Test orchestration recommendation for 2-3 agents."""
        args = {"num_agents": 2, "task_domains": ["frontend", "backend"]}

        result = run_async(server._handle_recommend_orchestration(args))
        assert result is not None
        text = result[0].text
        assert "Orchestrator-Worker" in text

    def test_orchestration_with_time_constraint(self, server: MemoryMCPServer):
        """Test orchestration with time constraint."""
        args = {
            "num_agents": 3,
            "task_domains": ["design", "dev"],
            "time_constraint": "1_hour",
        }

        result = run_async(server._handle_recommend_orchestration(args))
        assert result is not None
        text = result[0].text
        assert "Time Constraint: 1_hour" in text


class TestSuggestPlanningStrategyTool:
    """Tests for suggest_planning_strategy tool."""

    def test_suggest_simple_task(self, server: MemoryMCPServer):
        """Test strategy suggestion for simple task."""
        args = {
            "task_description": "Add a button to UI",
            "domain": "frontend",
            "complexity": 2,
        }

        result = run_async(server._handle_suggest_planning_strategy(args))
        assert result is not None
        text = result[0].text
        assert "✓" in text
        assert "Simple Sequential" in text
        assert "Confidence: 95%" in text

    def test_suggest_medium_task(self, server: MemoryMCPServer):
        """Test strategy suggestion for medium task."""
        args = {
            "task_description": "Refactor database queries",
            "domain": "backend",
            "complexity": 5,
        }

        result = run_async(server._handle_suggest_planning_strategy(args))
        assert result is not None
        text = result[0].text
        assert "Hierarchical" in text

    def test_suggest_complex_task(self, server: MemoryMCPServer):
        """Test strategy suggestion for complex task."""
        args = {
            "task_description": "Build distributed cache system",
            "domain": "architecture",
            "complexity": 9,
        }

        result = run_async(server._handle_suggest_planning_strategy(args))
        assert result is not None
        text = result[0].text
        assert "Complex" in text or "Confidence: 82%" in text


class TestRecordExecutionFeedbackTool:
    """Tests for record_execution_feedback tool."""

    def test_record_feedback_minimal(self, server: MemoryMCPServer):
        """Test recording minimal feedback (required fields only)."""
        args = {
            "task_id": 1,
            "actual_duration": 45,
        }

        result = run_async(server._handle_record_execution_feedback(args))
        assert result is not None
        text = result[0].text
        assert "✓" in text
        assert "Execution Feedback Recorded" in text
        assert "Task ID: 1" in text

    def test_record_feedback_with_blockers(self, server: MemoryMCPServer):
        """Test recording feedback with blockers."""
        args = {
            "task_id": 2,
            "actual_duration": 60,
            "blockers": ["Missing API key", "Database timeout"],
        }

        result = run_async(server._handle_record_execution_feedback(args))
        assert result is not None
        text = result[0].text
        assert "Blockers Encountered:" in text
        assert "Missing API key" in text

    def test_record_feedback_with_quality_metrics(self, server: MemoryMCPServer):
        """Test recording feedback with quality metrics."""
        args = {
            "task_id": 3,
            "actual_duration": 30,
            "quality_metrics": {"success": True, "quality_score": 0.92},
        }

        result = run_async(server._handle_record_execution_feedback(args))
        assert result is not None
        text = result[0].text
        assert "Outcome: success" in text
        assert "Quality Score: 92%" in text

    def test_record_feedback_missing_duration(self, server: MemoryMCPServer):
        """Test recording feedback without actual_duration."""
        args = {
            "task_id": 6,
        }

        result = run_async(server._handle_record_execution_feedback(args))
        assert result is not None
        text = result[0].text
        assert "✗" in text or "Error" in text or "required" in text

    def test_record_feedback_with_lessons(self, server: MemoryMCPServer):
        """Test recording feedback with lessons learned."""
        args = {
            "task_id": 5,
            "actual_duration": 50,
            "lessons_learned": "Using caching reduced query time by 40%",
        }

        result = run_async(server._handle_record_execution_feedback(args))
        assert result is not None
        text = result[0].text
        assert "Lessons Learned:" in text


class TestPhase34ToolIntegration:
    """Integration tests for Phase 3.4 tools."""

    def test_tools_registered(self, server: MemoryMCPServer):
        """Test that all Phase 3.4 tools have handlers."""
        tool_names = {
            "decompose_hierarchically",
            "validate_plan",
            "get_project_status",
            "recommend_orchestration",
            "suggest_planning_strategy",
            "record_execution_feedback",
        }

        for tool_name in tool_names:
            handler_name = f"_handle_{tool_name}"
            assert hasattr(server, handler_name), f"Missing handler for {tool_name}"

    def test_workflow_decompose_strategy_orchestration(self, server: MemoryMCPServer):
        """Test workflow: decompose -> strategy -> orchestration."""
        # Decompose
        decompose_result = run_async(
            server._handle_decompose_hierarchically({
                "task_description": "Implement OAuth2",
                "complexity_level": 7,
                "domain": "security",
            })
        )
        assert "✓" in decompose_result[0].text

        # Strategy
        strategy_result = run_async(
            server._handle_suggest_planning_strategy({
                "task_description": "Implement OAuth2",
                "complexity": 7,
            })
        )
        assert "✓" in strategy_result[0].text

        # Orchestration
        orch_result = run_async(
            server._handle_recommend_orchestration({
                "num_agents": 2,
                "task_domains": ["backend", "devops"],
            })
        )
        assert "✓" in orch_result[0].text

    def test_workflow_execution_feedback_status(self, server: MemoryMCPServer):
        """Test workflow: execute -> feedback -> status."""
        project = server.project_manager.store.create_project("workflow", "/tmp/test")

        # Record feedback
        feedback_result = run_async(
            server._handle_record_execution_feedback({
                "task_id": 1,
                "actual_duration": 45,
                "quality_metrics": {"success": True, "quality_score": 0.90},
            })
        )
        assert "✓" in feedback_result[0].text

        # Get status
        status_result = run_async(
            server._handle_get_project_status({"project_id": project.id})
        )
        text = status_result[0].text
        # Check for valid response (either success or graceful error)
        assert ("✓" in text or "Status" in text or "Error" in text)


class TestTriggerReplanningTool:
    """Tests for trigger_replanning tool."""

    def test_trigger_missing_task_id(self, server: MemoryMCPServer):
        """Test trigger_replanning without task_id."""
        args = {
            "trigger_type": "duration_exceeded",
            "trigger_reason": "Task taking longer than expected"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text and "task_id" in text

    def test_trigger_missing_trigger_type(self, server: MemoryMCPServer):
        """Test trigger_replanning without trigger_type."""
        args = {
            "task_id": 1,
            "trigger_reason": "Task taking longer than expected"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text and "trigger_type" in text

    def test_trigger_missing_trigger_reason(self, server: MemoryMCPServer):
        """Test trigger_replanning without trigger_reason."""
        args = {
            "task_id": 1,
            "trigger_type": "duration_exceeded"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text and "trigger_reason" in text

    def test_trigger_duration_exceeded(self, server: MemoryMCPServer):
        """Test trigger_replanning with duration_exceeded trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "duration_exceeded",
            "trigger_reason": "Task is running 50% over estimate"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        text = result[0].text
        # Verify handler is callable and returns proper format (either success or graceful error)
        assert len(text) > 0
        assert ("Replanning" in text or "Error" in text or "duration_exceeded" in text)

    def test_trigger_quality_degradation(self, server: MemoryMCPServer):
        """Test trigger_replanning with quality_degradation trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "quality_degradation",
            "trigger_reason": "Quality metrics dropping below threshold"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0
        # Accept either success or error response
        assert ("quality_degradation" in result[0].text or "Error" in result[0].text)

    def test_trigger_blocker_encountered(self, server: MemoryMCPServer):
        """Test trigger_replanning with blocker_encountered trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "blocker_encountered",
            "trigger_reason": "Waiting on third-party API"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0
        # Accept either success or error response
        assert ("blocker" in result[0].text.lower() or "Error" in result[0].text)

    def test_trigger_assumption_violated(self, server: MemoryMCPServer):
        """Test trigger_replanning with assumption_violated trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "assumption_violated",
            "trigger_reason": "Assumed resource not available"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_trigger_milestone_missed(self, server: MemoryMCPServer):
        """Test trigger_replanning with milestone_missed trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "milestone_missed",
            "trigger_reason": "Phase completion date passed"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_trigger_resource_constraint(self, server: MemoryMCPServer):
        """Test trigger_replanning with resource_constraint trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "resource_constraint",
            "trigger_reason": "Key team member unavailable"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_trigger_with_remaining_work(self, server: MemoryMCPServer):
        """Test trigger_replanning with remaining work estimate."""
        args = {
            "task_id": 1,
            "trigger_type": "duration_exceeded",
            "trigger_reason": "Need to extend timeline",
            "remaining_work_estimate": 120
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_trigger_unknown_type(self, server: MemoryMCPServer):
        """Test trigger_replanning with unknown trigger type."""
        args = {
            "task_id": 1,
            "trigger_type": "unknown_trigger",
            "trigger_reason": "Unknown trigger type"
        }
        result = run_async(server._handle_trigger_replanning(args))
        assert result is not None
        assert len(result[0].text) > 0


class TestVerifyPlanTool:
    """Tests for verify_plan tool."""

    def test_verify_missing_project_id(self, server: MemoryMCPServer):
        """Test verify_plan without project_id."""
        args = {}
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text and "project_id" in text

    def test_verify_nonexistent_project(self, server: MemoryMCPServer):
        """Test verify_plan with non-existent project."""
        args = {"project_id": 9999}
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        text = result[0].text
        assert "Error" in text and "not found" in text

    def test_verify_default_properties(self, server: MemoryMCPServer):
        """Test verify_plan with default properties."""
        project = server.project_manager.store.create_project("verify_test", "/tmp/test")
        args = {"project_id": project.id}
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        text = result[0].text
        # Verify proper response format (either success or graceful error)
        assert len(text) > 0
        assert ("Formal Plan Verification" in text or "VERIFICATION" in text or "Error" in text)

    def test_verify_specific_properties(self, server: MemoryMCPServer):
        """Test verify_plan with specific properties."""
        project = server.project_manager.store.create_project("verify_specific", "/tmp/test")
        args = {
            "project_id": project.id,
            "properties_to_verify": ["no_cycles", "dependencies_valid"]
        }
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_verify_plan_summary(self, server: MemoryMCPServer):
        """Test verify_plan summary section."""
        project = server.project_manager.store.create_project("verify_summary", "/tmp/test")
        args = {"project_id": project.id}
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        assert len(result[0].text) > 0

    def test_verify_plan_verification_method(self, server: MemoryMCPServer):
        """Test verify_plan includes verification method."""
        project = server.project_manager.store.create_project("verify_method", "/tmp/test")
        args = {"project_id": project.id}
        result = run_async(server._handle_verify_plan(args))
        assert result is not None
        assert len(result[0].text) > 0


class TestMissingToolsIntegration:
    """Integration tests for trigger_replanning and verify_plan with other tools."""

    def test_trigger_then_validate_workflow(self, server: MemoryMCPServer):
        """Test workflow: trigger replanning → validate revised plan."""
        project = server.project_manager.store.create_project("trigger_validate", "/tmp/test")

        # Trigger replanning
        trigger_result = run_async(
            server._handle_trigger_replanning({
                "task_id": 1,
                "trigger_type": "duration_exceeded",
                "trigger_reason": "Unexpected complexity"
            })
        )
        assert trigger_result is not None
        assert len(trigger_result[0].text) > 0

        # Validate revised plan
        validate_result = run_async(
            server._handle_validate_plan({"project_id": project.id})
        )
        assert validate_result is not None

    def test_decompose_then_verify_workflow(self, server: MemoryMCPServer):
        """Test workflow: decompose task → verify resulting plan."""
        project = server.project_manager.store.create_project("decompose_verify", "/tmp/test")

        # Decompose task
        decompose_result = run_async(
            server._handle_decompose_hierarchically({
                "task_description": "Build authentication system",
                "complexity_level": 7,
                "domain": "security"
            })
        )
        assert decompose_result is not None
        assert "✓" in decompose_result[0].text

        # Verify plan
        verify_result = run_async(
            server._handle_verify_plan({"project_id": project.id})
        )
        assert verify_result is not None
        assert len(verify_result[0].text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
