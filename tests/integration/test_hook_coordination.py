"""Integration tests for Hook Coordination handlers (5 operations).

Tests the optimized implementations of 5 key hooks using Phase 5-6 tools.
"""

import pytest
import asyncio
from typing import Any, List

# Import handlers
from athena.mcp.handlers_hook_coordination import (
    handle_optimize_session_start,
    handle_optimize_session_end,
    handle_optimize_user_prompt_submit,
    handle_optimize_post_tool_use,
    handle_optimize_pre_execution,
)
from athena.integration.hook_coordination import (
    SessionStartOptimizer,
    SessionEndOptimizer,
    UserPromptOptimizer,
    PostToolOptimizer,
    PreExecutionOptimizer,
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


class TestHookCoordinationHandlers:
    """Test Hook Coordination handler implementations."""

    @pytest.mark.asyncio
    async def test_optimize_session_start_handler(self):
        """Test optimize_session_start handler."""
        server = MockServer()
        args = {"project_id": 1, "validate_plans": True}

        # Call handler
        result = await handle_optimize_session_start(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0
        assert hasattr(result[0], "type")
        assert hasattr(result[0], "text")

    @pytest.mark.asyncio
    async def test_optimize_session_end_handler(self):
        """Test optimize_session_end handler."""
        server = MockServer()
        args = {
            "session_id": "test-session-123",
            "extract_patterns": True,
            "measure_quality": True,
        }

        # Call handler
        result = await handle_optimize_session_end(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0
        assert hasattr(result[0], "text")

    @pytest.mark.asyncio
    async def test_optimize_user_prompt_submit_handler(self):
        """Test optimize_user_prompt_submit handler."""
        server = MockServer()
        args = {"project_id": 1, "monitor_health": True}

        # Call handler
        result = await handle_optimize_user_prompt_submit(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_optimize_post_tool_use_handler(self):
        """Test optimize_post_tool_use handler."""
        server = MockServer()
        args = {
            "tool_name": "consolidation_tools:run_consolidation",
            "execution_time_ms": 250,
            "tool_result": "success",
            "task_id": 42,
        }

        # Call handler
        result = await handle_optimize_post_tool_use(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_optimize_pre_execution_handler(self):
        """Test optimize_pre_execution handler."""
        server = MockServer()
        args = {"task_id": 42, "strict_mode": False, "run_scenarios": "auto"}

        # Call handler
        result = await handle_optimize_pre_execution(server, args)

        # Verify result
        assert result is not None
        assert len(result) > 0
        # Check that response contains "ready_for_execution" info
        response_text = result[0].text
        assert "ready" in response_text.lower() or "execution" in response_text.lower()


class TestSessionStartOptimizer:
    """Test SessionStartOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_session_start_optimizer_execute(self, tmp_path):
        """Test session start optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = SessionStartOptimizer(db)

        result = await optimizer.execute(project_id=1, validate_plans=True)

        # Verify result structure
        assert "status" in result
        assert "context_loaded" in result
        assert "cognitive_load" in result
        assert "active_goals" in result
        assert "plan_validation_issues" in result

        # Verify types
        assert isinstance(result["context_loaded"], bool)
        assert isinstance(result["cognitive_load"], int)
        assert isinstance(result["active_goals"], list)
        assert isinstance(result["plan_validation_issues"], list)


class TestSessionEndOptimizer:
    """Test SessionEndOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_session_end_optimizer_execute(self, tmp_path):
        """Test session end optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = SessionEndOptimizer(db)

        result = await optimizer.execute(
            session_id="test-session", extract_patterns=True, measure_quality=True
        )

        # Verify result structure
        assert "status" in result
        assert "consolidation_events" in result
        assert "consolidation_strategy" in result
        assert "patterns_extracted" in result
        assert "quality_score" in result
        assert "compression_ratio" in result
        assert "recall_score" in result
        assert "consistency_score" in result

        # Verify types
        assert isinstance(result["consolidation_events"], int)
        assert isinstance(result["quality_score"], float)
        assert 0.0 <= result["quality_score"] <= 1.0


class TestUserPromptOptimizer:
    """Test UserPromptOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_user_prompt_optimizer_execute(self, tmp_path):
        """Test user prompt optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = UserPromptOptimizer(db)

        result = await optimizer.execute(project_id=1, monitor_health=True)

        # Verify result structure
        assert "status" in result
        assert "gaps_detected" in result
        assert "tasks_monitored" in result
        assert "health_warnings" in result
        assert "improvement_suggestions" in result

        # Verify types
        assert isinstance(result["gaps_detected"], list)
        assert isinstance(result["tasks_monitored"], int)
        assert isinstance(result["health_warnings"], list)
        assert isinstance(result["improvement_suggestions"], list)


class TestPostToolOptimizer:
    """Test PostToolOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_post_tool_optimizer_execute(self, tmp_path):
        """Test post-tool optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PostToolOptimizer(db)

        result = await optimizer.execute(
            tool_name="consolidation_tools:run_consolidation",
            execution_time_ms=250,
            tool_result="success",
            task_id=42,
        )

        # Verify result structure
        assert "status" in result
        assert "event_recorded" in result
        assert "performance_status" in result
        assert "task_updated" in result
        assert "target_met" in result

        # Verify types
        assert isinstance(result["event_recorded"], bool)
        assert isinstance(result["target_met"], bool)
        assert isinstance(result["task_updated"], bool)


class TestPreExecutionOptimizer:
    """Test PreExecutionOptimizer implementation."""

    @pytest.mark.asyncio
    async def test_pre_execution_optimizer_execute(self, tmp_path):
        """Test pre-execution optimizer execution."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PreExecutionOptimizer(db)

        result = await optimizer.execute(task_id=42, strict_mode=False, run_scenarios="auto")

        # Verify result structure
        assert "status" in result
        assert "ready_for_execution" in result
        assert "structure_valid" in result
        assert "feasibility_valid" in result
        assert "rules_valid" in result
        assert "issues" in result
        assert "properties_overall_score" in result
        assert "scenario_success_prob" in result

        # Verify types
        assert isinstance(result["ready_for_execution"], bool)
        assert isinstance(result["structure_valid"], bool)
        assert isinstance(result["properties_overall_score"], float)

        # Verify score ranges
        assert 0.0 <= result["properties_overall_score"] <= 1.0


class TestHookCoordinationIntegration:
    """Test Hook Coordination integration with operation router."""

    @pytest.mark.asyncio
    async def test_hook_coordination_operations_registered(self):
        """Test that hook coordination operations are registered in router."""
        from athena.mcp.operation_router import OperationRouter

        # Verify hook_coordination_tools is in operation maps
        assert "hook_coordination_tools" in OperationRouter.OPERATION_MAPS

        # Verify all 5 operations are registered
        hook_ops = OperationRouter.OPERATION_MAPS["hook_coordination_tools"]
        expected_ops = [
            "optimize_session_start",
            "optimize_session_end",
            "optimize_user_prompt_submit",
            "optimize_post_tool_use",
            "optimize_pre_execution",
        ]

        for op in expected_ops:
            assert op in hook_ops, f"Operation {op} not registered"

    def test_hook_coordination_handler_forwarding(self):
        """Test that handlers properly forward to implementation."""
        from athena.mcp.handlers import MemoryMCPServer

        # Verify handler methods exist
        server_methods = [
            "_handle_optimize_session_start",
            "_handle_optimize_session_end",
            "_handle_optimize_user_prompt_submit",
            "_handle_optimize_post_tool_use",
            "_handle_optimize_pre_execution",
        ]

        for method in server_methods:
            assert hasattr(MemoryMCPServer, method), f"Handler method {method} not found"


class TestHookCoordinationErrorHandling:
    """Test error handling in hook coordination."""

    @pytest.mark.asyncio
    async def test_session_start_optimizer_error_handling(self, tmp_path):
        """Test error handling in session start optimizer."""
        from athena.core.database import Database

        # Create optimizer with invalid database
        db = None
        optimizer = SessionStartOptimizer(db)

        result = await optimizer.execute(project_id=1, validate_plans=True)

        # Verify error handling
        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pre_execution_optimizer_error_handling(self, tmp_path):
        """Test error handling in pre-execution optimizer."""
        from athena.core.database import Database

        db = None
        optimizer = PreExecutionOptimizer(db)

        result = await optimizer.execute(task_id=42, strict_mode=False)

        # Verify error handling
        assert result["status"] == "error"
        assert "error" in result


class TestHookCoordinationMetrics:
    """Test performance metrics in hook coordination."""

    @pytest.mark.asyncio
    async def test_session_start_metrics(self, tmp_path):
        """Test that SessionStart returns useful metrics."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = SessionStartOptimizer(db)

        result = await optimizer.execute(project_id=1, validate_plans=True)

        # Verify consolidation age is reported
        assert "consolidation_age_hours" in result
        assert "consolidation_status" in result

    @pytest.mark.asyncio
    async def test_session_end_quality_metrics(self, tmp_path):
        """Test that SessionEnd returns quality metrics."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = SessionEndOptimizer(db)

        result = await optimizer.execute(
            session_id="test", extract_patterns=True, measure_quality=True
        )

        # Verify quality metrics are returned
        assert "compression_ratio" in result
        assert "recall_score" in result
        assert "consistency_score" in result

        # Verify metrics are reasonable
        assert 0.0 <= result["compression_ratio"] <= 1.0
        assert 0.0 <= result["recall_score"] <= 1.0
        assert 0.0 <= result["consistency_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_post_tool_performance_tracking(self, tmp_path):
        """Test that PostTool tracks performance metrics."""
        from athena.core.database import Database

        db = Database(str(tmp_path / "test.db"))
        optimizer = PostToolOptimizer(db)

        result = await optimizer.execute(
            tool_name="phase6_planning_tools:validate_plan",
            execution_time_ms=150,
            tool_result="success",
        )

        # Verify performance is tracked
        assert "performance_status" in result
        assert "target_met" in result
        # 150ms should be under 500ms target
        assert result["target_met"] is True


# ============================================================================
# Test Organization and Categorization
# ============================================================================

# These tests are organized into classes by optimizer/handler component
# Each class tests:
# 1. Handler implementation correctness
# 2. Optimizer execution and result structure
# 3. Error handling and edge cases
# 4. Integration with operation router
# 5. Performance and metric tracking

# Run with: pytest tests/integration/test_hook_coordination.py -v
# Run specific test: pytest tests/integration/test_hook_coordination.py::TestHookCoordinationHandlers::test_optimize_session_start_handler -v
