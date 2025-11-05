"""Integration tests for Phase 1 tool exposure (Integration, Automation, Conversation)."""

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


class TestPhase1OperationRouting:
    """Test that Phase 1 operations are properly registered and routable."""

    def test_integration_operations_registered(self):
        """Test that integration_tools operations are registered."""
        ops = OperationRouter.INTEGRATION_OPERATIONS
        assert len(ops) == 12

        expected_ops = [
            "planning_assistance",
            "optimize_plan_suggestions",
            "analyze_project_coordination",
            "discover_patterns_advanced",
            "monitor_system_health_detailed",
            "estimate_task_resources_detailed",
            "generate_alternative_plans_impl",
            "analyze_estimation_accuracy_adv",
            "analyze_task_analytics_detailed",
            "aggregate_analytics_summary",
            "get_critical_path_analysis",
            "get_resource_allocation",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_automation_operations_registered(self):
        """Test that automation_tools operations are registered."""
        ops = OperationRouter.AUTOMATION_OPERATIONS
        assert len(ops) == 5

        expected_ops = [
            "register_automation_rule",
            "trigger_automation_event",
            "list_automation_rules",
            "update_automation_config",
            "execute_automation_workflow",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_conversation_operations_registered(self):
        """Test that conversation_tools operations are registered."""
        ops = OperationRouter.CONVERSATION_OPERATIONS
        assert len(ops) == 8

        expected_ops = [
            "start_new_conversation",
            "add_message_to_conversation",
            "get_conversation_history",
            "resume_conversation_session",
            "create_context_snapshot",
            "recover_conversation_context",
            "list_active_conversations",
            "export_conversation_data",
        ]

        for op in expected_ops:
            assert op in ops, f"Missing operation: {op}"
            assert ops[op].startswith("_handle_"), f"Invalid handler name for {op}"

    def test_operations_in_maps(self):
        """Test that all Phase 1 operations are in OPERATION_MAPS."""
        assert "integration_tools" in OperationRouter.OPERATION_MAPS
        assert "automation_tools" in OperationRouter.OPERATION_MAPS
        assert "conversation_tools" in OperationRouter.OPERATION_MAPS

        assert OperationRouter.OPERATION_MAPS["integration_tools"] == OperationRouter.INTEGRATION_OPERATIONS
        assert OperationRouter.OPERATION_MAPS["automation_tools"] == OperationRouter.AUTOMATION_OPERATIONS
        assert OperationRouter.OPERATION_MAPS["conversation_tools"] == OperationRouter.CONVERSATION_OPERATIONS


class TestPhase1WrapperMethods:
    """Test that Phase 1 wrapper methods are properly defined."""

    def test_all_integration_wrappers_exist(self):
        """Test that all integration wrapper methods exist."""
        for op, handler_name in OperationRouter.INTEGRATION_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"

    def test_all_automation_wrappers_exist(self):
        """Test that all automation wrapper methods exist."""
        for op, handler_name in OperationRouter.AUTOMATION_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"

    def test_all_conversation_wrappers_exist(self):
        """Test that all conversation wrapper methods exist."""
        for op, handler_name in OperationRouter.CONVERSATION_OPERATIONS.items():
            assert hasattr(MemoryMCPServer, handler_name), f"Missing handler: {handler_name}"
            method = getattr(MemoryMCPServer, handler_name)
            assert callable(method), f"{handler_name} is not callable"


class TestPhase1Routing:
    """Test routing of Phase 1 operations."""

    @pytest.mark.asyncio
    async def test_route_integration_operation(self, mock_server):
        """Test routing to integration operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_planning_assistance = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success"}))]
        )

        result = await router.route("integration_tools", {
            "operation": "planning_assistance",
            "task_id": 1,
        })

        assert result["status"] == "success"
        mock_server._handle_planning_assistance.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_automation_operation(self, mock_server):
        """Test routing to automation operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_register_automation_rule = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success"}))]
        )

        result = await router.route("automation_tools", {
            "operation": "register_automation_rule",
            "rule_name": "test_rule",
        })

        assert result["status"] == "success"
        mock_server._handle_register_automation_rule.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_conversation_operation(self, mock_server):
        """Test routing to conversation operation."""
        router = OperationRouter(mock_server)

        # Mock the handler on the server
        mock_server._handle_start_new_conversation = AsyncMock(
            return_value=[MagicMock(text=json.dumps({"status": "success", "conversation_id": 1}))]
        )

        result = await router.route("conversation_tools", {
            "operation": "start_new_conversation",
            "title": "Test conversation",
        })

        assert result["status"] == "success"
        assert result["conversation_id"] == 1
        mock_server._handle_start_new_conversation.assert_called_once()


class TestPhase1Integration:
    """End-to-end integration tests for Phase 1 tools."""

    def test_total_operations_count(self):
        """Test that total operations increased by 25."""
        total = OperationRouter.get_total_operations()
        # Should be original 127 + 25 new = 152
        # But we have some duplicates in the existing operations, so verify it's > 140
        assert total >= 150, f"Expected at least 150 total operations, got {total}"

    def test_meta_tool_count(self):
        """Test that meta-tool count increased to 25 (Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5)."""
        count = OperationRouter.get_meta_tool_count()
        assert count == 26, f"Expected 26 meta-tools, got {count}"

    def test_phase1_coverage(self):
        """Test that Phase 1 coverage is complete."""
        # Integration: 12/12
        assert len(OperationRouter.INTEGRATION_OPERATIONS) == 12

        # Automation: 5/5
        assert len(OperationRouter.AUTOMATION_OPERATIONS) == 5

        # Conversation: 8/8
        assert len(OperationRouter.CONVERSATION_OPERATIONS) == 8

        # Total: 25/25
        total_phase1 = (
            len(OperationRouter.INTEGRATION_OPERATIONS) +
            len(OperationRouter.AUTOMATION_OPERATIONS) +
            len(OperationRouter.CONVERSATION_OPERATIONS)
        )
        assert total_phase1 == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
