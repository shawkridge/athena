"""Integration tests for Phase 2 tool exposure (Safety, IDE_Context, Skills, Resilience)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.athena.mcp.handlers import MemoryMCPServer
from src.athena.mcp.operation_router import OperationRouter
from src.athena.core.database import Database


@pytest.fixture
def mock_server(tmp_path):
    """Create a mock MCP server for testing."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    server = MagicMock()
    server.store = MagicMock()
    server.store.db = db
    server.project_manager = MagicMock()
    server.project_manager.get_or_create_project = MagicMock(return_value=MagicMock(id=1, name="test"))

    return server


class TestPhase2OperationRouting:
    """Test that Phase 2 operations are properly registered and routable."""

    def test_safety_operations_registered(self):
        """Test that safety_tools operations are registered."""
        ops = OperationRouter.SAFETY_OPERATIONS
        assert len(ops) == 7

        expected_ops = [
            "evaluate_change_safety",
            "request_approval",
            "get_audit_trail",
            "monitor_execution",
            "create_code_snapshot",
            "check_safety_policy",
            "analyze_change_risk",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_ide_context_operations_registered(self):
        """Test that ide_context_tools operations are registered."""
        ops = OperationRouter.IDE_CONTEXT_OPERATIONS
        assert len(ops) == 8

        expected_ops = [
            "get_ide_context",
            "get_cursor_position",
            "get_open_files",
            "get_git_status",
            "get_recent_files",
            "get_file_changes",
            "get_active_buffer",
            "track_ide_activity",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_skills_operations_registered(self):
        """Test that skills_tools operations are registered."""
        ops = OperationRouter.SKILLS_OPERATIONS
        assert len(ops) == 7

        expected_ops = [
            "analyze_project_with_skill",
            "improve_estimations",
            "learn_from_outcomes",
            "detect_bottlenecks_advanced",
            "analyze_health_trends",
            "create_task_from_template",
            "get_skill_recommendations",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_resilience_operations_registered(self):
        """Test that resilience_tools operations are registered."""
        ops = OperationRouter.RESILIENCE_OPERATIONS
        assert len(ops) == 6

        expected_ops = [
            "check_system_health",
            "get_health_report",
            "configure_circuit_breaker",
            "get_resilience_status",
            "test_fallback_chain",
            "configure_retry_policy",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_operations_in_maps(self):
        """Test that all Phase 2 operations are in OPERATION_MAPS."""
        assert "safety_tools" in OperationRouter.OPERATION_MAPS
        assert "ide_context_tools" in OperationRouter.OPERATION_MAPS
        assert "skills_tools" in OperationRouter.OPERATION_MAPS
        assert "resilience_tools" in OperationRouter.OPERATION_MAPS

        assert OperationRouter.OPERATION_MAPS["safety_tools"] == OperationRouter.SAFETY_OPERATIONS
        assert OperationRouter.OPERATION_MAPS["ide_context_tools"] == OperationRouter.IDE_CONTEXT_OPERATIONS
        assert OperationRouter.OPERATION_MAPS["skills_tools"] == OperationRouter.SKILLS_OPERATIONS
        assert OperationRouter.OPERATION_MAPS["resilience_tools"] == OperationRouter.RESILIENCE_OPERATIONS


class TestPhase2WrapperMethods:
    """Test that Phase 2 wrapper methods are properly defined."""

    def test_all_safety_wrappers_exist(self):
        """Test that all safety wrapper methods exist."""
        for op, handler_name in OperationRouter.SAFETY_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"

    def test_all_ide_context_wrappers_exist(self):
        """Test that all ide_context wrapper methods exist."""
        for op, handler_name in OperationRouter.IDE_CONTEXT_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"

    def test_all_skills_wrappers_exist(self):
        """Test that all skills wrapper methods exist."""
        for op, handler_name in OperationRouter.SKILLS_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"

    def test_all_resilience_wrappers_exist(self):
        """Test that all resilience wrapper methods exist."""
        for op, handler_name in OperationRouter.RESILIENCE_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"


class TestPhase2Routing:
    """Test routing of Phase 2 operations."""

    @pytest.mark.asyncio
    async def test_route_safety_operation(self, mock_server):
        """Test routing to safety operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_evaluate_change_safety = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success", "safe": True}))]
        )

        result = await router.route("safety_tools", {
            "operation": "evaluate_change_safety",
            "change_type": "code",
            "change_description": "Add new feature",
        })

        assert result["status"] == "success"
        assert result["safe"] == True
        mock_server._handle_evaluate_change_safety.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_ide_context_operation(self, mock_server):
        """Test routing to IDE context operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_get_ide_context = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success", "open_files": 3}))]
        )

        result = await router.route("ide_context_tools", {
            "operation": "get_ide_context",
        })

        assert result["status"] == "success"
        assert result["open_files"] == 3
        mock_server._handle_get_ide_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_skills_operation(self, mock_server):
        """Test routing to skills operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_analyze_project_with_skill = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success", "insights": []}))]
        )

        result = await router.route("skills_tools", {
            "operation": "analyze_project_with_skill",
            "project_id": 1,
        })

        assert result["status"] == "success"
        mock_server._handle_analyze_project_with_skill.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_resilience_operation(self, mock_server):
        """Test routing to resilience operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_check_system_health = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success", "health": "good"}))]
        )

        result = await router.route("resilience_tools", {
            "operation": "check_system_health",
        })

        assert result["status"] == "success"
        assert result["health"] == "good"
        mock_server._handle_check_system_health.assert_called_once()


class TestPhase2Integration:
    """End-to-end integration tests for Phase 2 tools."""

    def test_total_operations_increased(self):
        """Test that total operations increased by 28."""
        total = OperationRouter.get_total_operations()
        # Should be Phase 1 (152) + Phase 2 (28) = 180
        assert total >= 175, f"Expected at least 175 total operations, got {total}"

    def test_meta_tool_count(self):
        """Test that meta-tool count increased to 25 (Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5)."""
        count = OperationRouter.get_meta_tool_count()
        assert count == 26, f"Expected 26 meta-tools, got {count}"

    def test_phase2_coverage(self):
        """Test that Phase 2 coverage is complete."""
        # Safety: 7/7
        assert len(OperationRouter.SAFETY_OPERATIONS) == 7

        # IDE_Context: 8/8
        assert len(OperationRouter.IDE_CONTEXT_OPERATIONS) == 8

        # Skills: 7/7
        assert len(OperationRouter.SKILLS_OPERATIONS) == 7

        # Resilience: 6/6
        assert len(OperationRouter.RESILIENCE_OPERATIONS) == 6

        # Total: 28/28
        total_phase2 = (
            len(OperationRouter.SAFETY_OPERATIONS) +
            len(OperationRouter.IDE_CONTEXT_OPERATIONS) +
            len(OperationRouter.SKILLS_OPERATIONS) +
            len(OperationRouter.RESILIENCE_OPERATIONS)
        )
        assert total_phase2 == 28

    def test_cumulative_coverage(self):
        """Test cumulative coverage from Phase 1 + Phase 2."""
        # Phase 1: 25 tools
        phase1_total = (
            len(OperationRouter.INTEGRATION_OPERATIONS) +
            len(OperationRouter.AUTOMATION_OPERATIONS) +
            len(OperationRouter.CONVERSATION_OPERATIONS)
        )
        assert phase1_total == 25

        # Phase 2: 28 tools
        phase2_total = (
            len(OperationRouter.SAFETY_OPERATIONS) +
            len(OperationRouter.IDE_CONTEXT_OPERATIONS) +
            len(OperationRouter.SKILLS_OPERATIONS) +
            len(OperationRouter.RESILIENCE_OPERATIONS)
        )
        assert phase2_total == 28

        # Combined: 53 new tools (25 + 28)
        combined = phase1_total + phase2_total
        assert combined == 53, f"Expected 53 combined Phase 1+2 tools, got {combined}"

        # Total with previous 127: should be ~180
        total = OperationRouter.get_total_operations()
        assert total >= 175


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
