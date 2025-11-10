"""Tests for hook coordination tools."""

import pytest
from athena.mcp.tools.hook_coordination_tools import (
    RegisterHookTool,
    ManageHooksTool,
    CoordinateHooksTool,
)
from athena.mcp.tools.base import ToolStatus


class TestRegisterHookTool:
    """Test suite for RegisterHookTool."""

    @pytest.fixture
    def tool(self):
        """Create RegisterHookTool instance."""
        return RegisterHookTool()

    @pytest.mark.asyncio
    async def test_register_hook_basic(self, tool):
        """Test basic hook registration."""
        result = await tool.execute(
            hook_name="test_hook",
            event_type="before_task",
            handler="def handler(): pass"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["hook_name"] == "test_hook"
        assert result.data["event_type"] == "before_task"
        assert result.data["status"] == "registered"
        assert "hook_id" in result.data

    @pytest.mark.asyncio
    async def test_register_hook_all_event_types(self, tool):
        """Test registration with all event types."""
        event_types = [
            "before_task",
            "after_task",
            "on_error",
            "on_success",
            "before_consolidation",
            "after_consolidation",
        ]

        for event_type in event_types:
            result = await tool.execute(
                hook_name=f"hook_{event_type}",
                event_type=event_type,
                handler="def handler(): pass"
            )

            assert result.status == ToolStatus.SUCCESS
            assert result.data["event_type"] == event_type

    @pytest.mark.asyncio
    async def test_register_hook_with_priority(self, tool):
        """Test hook registration with priority."""
        result = await tool.execute(
            hook_name="priority_hook",
            event_type="before_task",
            handler="def handler(): pass",
            priority=75
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["priority"] == 75

    @pytest.mark.asyncio
    async def test_register_hook_invalid_event_type(self, tool):
        """Test registration with invalid event type."""
        result = await tool.execute(
            hook_name="test_hook",
            event_type="invalid_event",
            handler="def handler(): pass"
        )

        assert result.status == ToolStatus.ERROR
        assert "Invalid event type" in result.error

    @pytest.mark.asyncio
    async def test_register_hook_missing_parameters(self, tool):
        """Test registration with missing parameters."""
        # Missing hook_name
        result = await tool.execute(
            event_type="before_task",
            handler="def handler(): pass"
        )
        assert result.status == ToolStatus.ERROR

        # Missing event_type
        result = await tool.execute(
            hook_name="test_hook",
            handler="def handler(): pass"
        )
        assert result.status == ToolStatus.ERROR

        # Missing handler
        result = await tool.execute(
            hook_name="test_hook",
            event_type="before_task"
        )
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_register_hook_priority_bounds(self, tool):
        """Test priority validation."""
        # Too low
        result = await tool.execute(
            hook_name="test_hook",
            event_type="before_task",
            handler="def handler(): pass",
            priority=0
        )
        assert result.status == ToolStatus.ERROR

        # Too high
        result = await tool.execute(
            hook_name="test_hook",
            event_type="before_task",
            handler="def handler(): pass",
            priority=101
        )
        assert result.status == ToolStatus.ERROR

    @pytest.mark.asyncio
    async def test_register_hook_boundary_priority(self, tool):
        """Test boundary priority values."""
        # Minimum
        result = await tool.execute(
            hook_name="min_hook",
            event_type="before_task",
            handler="def handler(): pass",
            priority=1
        )
        assert result.status == ToolStatus.SUCCESS

        # Maximum
        result = await tool.execute(
            hook_name="max_hook",
            event_type="before_task",
            handler="def handler(): pass",
            priority=100
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_register_hook_default_priority(self, tool):
        """Test default priority is applied."""
        result = await tool.execute(
            hook_name="default_hook",
            event_type="before_task",
            handler="def handler(): pass"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["priority"] == 50  # Default


class TestManageHooksTool:
    """Test suite for ManageHooksTool."""

    @pytest.fixture
    def tool(self):
        """Create ManageHooksTool instance."""
        return ManageHooksTool()

    @pytest.mark.asyncio
    async def test_list_all_hooks(self, tool):
        """Test listing all hooks."""
        result = await tool.execute(action="list")

        assert result.status == ToolStatus.SUCCESS
        assert "result" in result.data
        assert "total_hooks" in result.data["result"]
        assert "hooks" in result.data["result"]

    @pytest.mark.asyncio
    async def test_list_hooks_by_event_type(self, tool):
        """Test listing hooks filtered by event type."""
        result = await tool.execute(
            action="list",
            event_type="before_task"
        )

        assert result.status == ToolStatus.SUCCESS
        hooks = result.data["result"]["hooks"]

        # All hooks should be for the specified event type
        for hook in hooks:
            assert hook["event_type"] == "before_task"

    @pytest.mark.asyncio
    async def test_enable_hook(self, tool):
        """Test enabling a hook."""
        result = await tool.execute(
            action="enable",
            hook_id="hook001"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["result"]["action"] == "enabled"

    @pytest.mark.asyncio
    async def test_disable_hook(self, tool):
        """Test disabling a hook."""
        result = await tool.execute(
            action="disable",
            hook_id="hook001"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["result"]["action"] == "disabled"

    @pytest.mark.asyncio
    async def test_remove_hook(self, tool):
        """Test removing a hook."""
        result = await tool.execute(
            action="remove",
            hook_id="hook001"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["result"]["action"] == "removed"

    @pytest.mark.asyncio
    async def test_invalid_action(self, tool):
        """Test invalid action."""
        result = await tool.execute(action="invalid_action")

        assert result.status == ToolStatus.ERROR
        assert "Invalid action" in result.error

    @pytest.mark.asyncio
    async def test_action_missing_hook_id(self, tool):
        """Test action that requires hook_id without providing it."""
        for action in ["enable", "disable", "remove"]:
            result = await tool.execute(action=action)
            assert result.status == ToolStatus.ERROR
            assert "hook_id is required" in result.error

    @pytest.mark.asyncio
    async def test_list_hooks_count(self, tool):
        """Test hooks list includes count information."""
        result = await tool.execute(action="list")

        result_data = result.data["result"]
        assert "total_hooks" in result_data
        assert "enabled_hooks" in result_data
        assert result_data["total_hooks"] >= result_data["enabled_hooks"]


class TestCoordinateHooksTool:
    """Test suite for CoordinateHooksTool."""

    @pytest.fixture
    def tool(self):
        """Create CoordinateHooksTool instance."""
        return CoordinateHooksTool()

    @pytest.mark.asyncio
    async def test_coordinate_hooks_basic(self, tool):
        """Test basic hook coordination."""
        result = await tool.execute(event_type="before_task")

        assert result.status == ToolStatus.SUCCESS
        assert result.data["event_type"] == "before_task"
        assert "hooks_executed" in result.data
        assert "execution_time_ms" in result.data

    @pytest.mark.asyncio
    async def test_coordinate_hooks_sequential(self, tool):
        """Test sequential hook coordination."""
        result = await tool.execute(
            event_type="before_task",
            coordination_mode="sequential"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["coordination_mode"] == "sequential"

    @pytest.mark.asyncio
    async def test_coordinate_hooks_parallel(self, tool):
        """Test parallel hook coordination."""
        result = await tool.execute(
            event_type="before_task",
            coordination_mode="parallel"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["coordination_mode"] == "parallel"

    @pytest.mark.asyncio
    async def test_coordinate_hooks_priority(self, tool):
        """Test priority-based hook coordination."""
        result = await tool.execute(
            event_type="before_task",
            coordination_mode="priority"
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.data["coordination_mode"] == "priority"

    @pytest.mark.asyncio
    async def test_coordinate_hooks_invalid_mode(self, tool):
        """Test invalid coordination mode."""
        result = await tool.execute(
            event_type="before_task",
            coordination_mode="invalid_mode"
        )

        assert result.status == ToolStatus.ERROR
        assert "Invalid coordination mode" in result.error

    @pytest.mark.asyncio
    async def test_coordinate_hooks_missing_event_type(self, tool):
        """Test missing event type."""
        result = await tool.execute(coordination_mode="sequential")

        assert result.status == ToolStatus.ERROR
        assert "event_type" in result.error

    @pytest.mark.asyncio
    async def test_coordinate_hooks_with_timeout(self, tool):
        """Test hook coordination with custom timeout."""
        result = await tool.execute(
            event_type="before_task",
            timeout_ms=10000
        )

        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_coordinate_hooks_execution_stats(self, tool):
        """Test execution statistics."""
        result = await tool.execute(event_type="before_task")

        assert "success_count" in result.data
        assert "total_hooks" in result.data
        assert result.data["success_count"] <= result.data["total_hooks"]

    @pytest.mark.asyncio
    async def test_coordinate_hooks_all_event_types(self, tool):
        """Test coordination for all event types."""
        event_types = [
            "before_task",
            "after_task",
            "on_error",
            "on_success",
        ]

        for event_type in event_types:
            result = await tool.execute(event_type=event_type)
            assert result.status == ToolStatus.SUCCESS
            assert result.data["event_type"] == event_type


class TestHookCoordinationIntegration:
    """Integration tests for hook coordination tools."""

    @pytest.mark.asyncio
    async def test_register_then_coordinate(self):
        """Test registering hook then coordinating execution."""
        register_tool = RegisterHookTool()
        coordinate_tool = CoordinateHooksTool()

        # Register a hook
        reg_result = await register_tool.execute(
            hook_name="test_hook",
            event_type="before_task",
            handler="def handler(): pass"
        )
        assert reg_result.status == ToolStatus.SUCCESS

        # Coordinate hooks for the event
        coord_result = await coordinate_tool.execute(event_type="before_task")
        assert coord_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_register_manage_coordinate_workflow(self):
        """Test full workflow: register, manage, coordinate."""
        register_tool = RegisterHookTool()
        manage_tool = ManageHooksTool()
        coordinate_tool = CoordinateHooksTool()

        # Register hook
        reg_result = await register_tool.execute(
            hook_name="workflow_hook",
            event_type="before_task",
            handler="def handler(): pass"
        )
        hook_id = reg_result.data["hook_id"]

        # List hooks
        list_result = await manage_tool.execute(action="list")
        assert list_result.status == ToolStatus.SUCCESS

        # Disable hook
        disable_result = await manage_tool.execute(
            action="disable",
            hook_id=hook_id
        )
        assert disable_result.status == ToolStatus.SUCCESS

        # Coordinate execution
        coord_result = await coordinate_tool.execute(event_type="before_task")
        assert coord_result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_multiple_hook_registration(self):
        """Test registering multiple hooks for same event."""
        tool = RegisterHookTool()

        hooks = []
        for i in range(3):
            result = await tool.execute(
                hook_name=f"hook_{i}",
                event_type="before_task",
                handler=f"def handler_{i}(): pass",
                priority=50 + (i * 10)
            )
            assert result.status == ToolStatus.SUCCESS
            hooks.append(result.data["hook_id"])

        assert len(hooks) == 3
