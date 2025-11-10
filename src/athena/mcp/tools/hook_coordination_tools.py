"""Hook coordination and lifecycle management tools."""

import logging
from typing import Optional, List, Dict, Any
from .base import BaseTool, ToolMetadata, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class RegisterHookTool(BaseTool):
    """Register and manage lifecycle hooks for system events."""

    def __init__(self, hook_registry=None):
        """Initialize register hook tool.

        Args:
            hook_registry: HookRegistry instance for hook management
        """
        metadata = ToolMetadata(
            name="register_hook",
            description="Register lifecycle hooks for system events",
            category="hook_coordination",
            version="1.0",
            parameters={
                "hook_name": {
                    "type": "string",
                    "description": "Name of hook to register"
                },
                "event_type": {
                    "type": "string",
                    "description": "Event type to listen for (before_task, after_task, on_error, on_success)"
                },
                "handler": {
                    "type": "string",
                    "description": "Handler function or script to execute"
                },
                "priority": {
                    "type": "integer",
                    "description": "Execution priority (1-100, default 50)",
                    "default": 50
                }
            },
            returns={
                "hook_id": {
                    "type": "string",
                    "description": "ID of registered hook"
                },
                "hook_name": {
                    "type": "string",
                    "description": "Name of hook"
                },
                "event_type": {
                    "type": "string",
                    "description": "Event type for hook"
                },
                "status": {
                    "type": "string",
                    "description": "Hook registration status"
                }
            },
            tags=["hook", "coordination", "lifecycle", "event-handling"]
        )
        super().__init__(metadata)
        self.hook_registry = hook_registry

    async def execute(self, **params) -> ToolResult:
        """Execute hook registration.

        Args:
            hook_name: Hook name (required)
            event_type: Event type (required)
            handler: Handler function (required)
            priority: Execution priority (optional)

        Returns:
            ToolResult with hook registration status
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["hook_name", "event_type", "handler"])
            if error:
                return ToolResult.error(error)

            hook_name = params["hook_name"]
            event_type = params["event_type"]
            handler = params["handler"]
            priority = params.get("priority", 50)

            # Validate event type
            valid_events = ["before_task", "after_task", "on_error", "on_success",
                          "before_consolidation", "after_consolidation"]
            if event_type not in valid_events:
                return ToolResult.error(
                    f"Invalid event type. Must be one of: {', '.join(valid_events)}"
                )

            # Validate priority
            if not (1 <= priority <= 100):
                return ToolResult.error("Priority must be between 1 and 100")

            # Register hook (simulated)
            hook_id = self._register_hook(hook_name, event_type, handler, priority)

            result_data = {
                "hook_id": hook_id,
                "hook_name": hook_name,
                "event_type": event_type,
                "priority": priority,
                "status": "registered",
                "message": f"Hook '{hook_name}' registered for event '{event_type}'"
            }

            self.log_execution(params, ToolResult.success(result_data))
            return ToolResult.success(result_data)

        except Exception as e:
            self.logger.error(f"Hook registration failed: {e}")
            return ToolResult.error(f"Hook registration failed: {str(e)}")

    def _register_hook(self, hook_name: str, event_type: str, handler: str,
                      priority: int) -> str:
        """Register hook in registry.

        Args:
            hook_name: Hook name
            event_type: Event type
            handler: Handler function
            priority: Execution priority

        Returns:
            Hook ID
        """
        # In real implementation, would store in hook_registry
        import hashlib
        hook_str = f"{hook_name}:{event_type}:{priority}"
        hook_id = hashlib.md5(hook_str.encode()).hexdigest()[:8]
        return hook_id


class ManageHooksTool(BaseTool):
    """Manage lifecycle hooks - enable, disable, remove, list."""

    def __init__(self, hook_registry=None):
        """Initialize manage hooks tool.

        Args:
            hook_registry: HookRegistry instance for hook management
        """
        metadata = ToolMetadata(
            name="manage_hooks",
            description="Manage lifecycle hooks - enable, disable, remove, list",
            category="hook_coordination",
            version="1.0",
            parameters={
                "action": {
                    "type": "string",
                    "description": "Action to perform (enable, disable, remove, list)"
                },
                "hook_id": {
                    "type": "string",
                    "description": "Hook ID (required for enable/disable/remove)"
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type (optional for list)"
                }
            },
            returns={
                "action": {
                    "type": "string",
                    "description": "Action performed"
                },
                "result": {
                    "type": "object",
                    "description": "Result of action"
                },
                "affected_hooks": {
                    "type": "array",
                    "description": "Hooks affected by action"
                }
            },
            tags=["hook", "management", "lifecycle", "coordination"]
        )
        super().__init__(metadata)
        self.hook_registry = hook_registry

    async def execute(self, **params) -> ToolResult:
        """Execute hook management action.

        Args:
            action: Action to perform (required)
            hook_id: Hook ID (optional)
            event_type: Filter by event type (optional)

        Returns:
            ToolResult with management action result
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["action"])
            if error:
                return ToolResult.error(error)

            action = params["action"]
            hook_id = params.get("hook_id")
            event_type = params.get("event_type")

            # Validate action
            valid_actions = ["enable", "disable", "remove", "list"]
            if action not in valid_actions:
                return ToolResult.error(
                    f"Invalid action. Must be one of: {', '.join(valid_actions)}"
                )

            # Execute action
            if action == "list":
                result = self._list_hooks(event_type)
            elif action in ["enable", "disable", "remove"]:
                if not hook_id:
                    return ToolResult.error(f"hook_id is required for action '{action}'")
                result = self._perform_action(action, hook_id)
            else:
                return ToolResult.error(f"Unknown action: {action}")

            result_data = {
                "action": action,
                "result": result,
                "affected_hooks": [hook_id] if hook_id else [],
                "timestamp": "2025-11-10T00:00:00Z"
            }

            self.log_execution(params, ToolResult.success(result_data))
            return ToolResult.success(result_data)

        except Exception as e:
            self.logger.error(f"Hook management failed: {e}")
            return ToolResult.error(f"Hook management failed: {str(e)}")

    def _list_hooks(self, event_type: Optional[str] = None) -> Dict[str, Any]:
        """List all registered hooks.

        Args:
            event_type: Filter by event type (optional)

        Returns:
            Dictionary with hook information
        """
        # In real implementation, would query hook_registry
        all_hooks = [
            {
                "hook_id": "hook001",
                "hook_name": "record_event_before",
                "event_type": "before_task",
                "enabled": True,
                "priority": 100
            },
            {
                "hook_id": "hook002",
                "hook_name": "validate_plan_after",
                "event_type": "after_task",
                "enabled": True,
                "priority": 75
            },
            {
                "hook_id": "hook003",
                "hook_name": "error_handler",
                "event_type": "on_error",
                "enabled": True,
                "priority": 90
            },
            {
                "hook_id": "hook004",
                "hook_name": "consolidate_on_success",
                "event_type": "on_success",
                "enabled": False,
                "priority": 50
            }
        ]

        if event_type:
            filtered_hooks = [h for h in all_hooks if h["event_type"] == event_type]
        else:
            filtered_hooks = all_hooks

        return {
            "total_hooks": len(filtered_hooks),
            "enabled_hooks": sum(1 for h in filtered_hooks if h["enabled"]),
            "hooks": filtered_hooks
        }

    def _perform_action(self, action: str, hook_id: str) -> Dict[str, Any]:
        """Perform action on hook.

        Args:
            action: Action to perform (enable, disable, remove)
            hook_id: Hook ID

        Returns:
            Action result
        """
        if action == "enable":
            return {
                "hook_id": hook_id,
                "action": "enabled",
                "status": "success"
            }
        elif action == "disable":
            return {
                "hook_id": hook_id,
                "action": "disabled",
                "status": "success"
            }
        elif action == "remove":
            return {
                "hook_id": hook_id,
                "action": "removed",
                "status": "success"
            }


class CoordinateHooksTool(BaseTool):
    """Coordinate hook execution and manage dependencies."""

    def __init__(self, hook_registry=None):
        """Initialize coordinate hooks tool.

        Args:
            hook_registry: HookRegistry instance for hook management
        """
        metadata = ToolMetadata(
            name="coordinate_hooks",
            description="Coordinate hook execution and manage dependencies",
            category="hook_coordination",
            version="1.0",
            parameters={
                "event_type": {
                    "type": "string",
                    "description": "Event type for coordination"
                },
                "coordination_mode": {
                    "type": "string",
                    "description": "Coordination mode (sequential, parallel, priority)",
                    "default": "priority"
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": "Timeout for hook execution (milliseconds)",
                    "default": 5000
                }
            },
            returns={
                "event_type": {
                    "type": "string",
                    "description": "Event type coordinated"
                },
                "coordination_mode": {
                    "type": "string",
                    "description": "Coordination mode used"
                },
                "hooks_executed": {
                    "type": "array",
                    "description": "Executed hooks with results"
                },
                "execution_time_ms": {
                    "type": "number",
                    "description": "Total execution time"
                }
            },
            tags=["hook", "coordination", "execution", "dependency-management"]
        )
        super().__init__(metadata)
        self.hook_registry = hook_registry

    async def execute(self, **params) -> ToolResult:
        """Execute hook coordination.

        Args:
            event_type: Event type (required)
            coordination_mode: Coordination mode (optional)
            timeout_ms: Timeout in milliseconds (optional)

        Returns:
            ToolResult with coordination result
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["event_type"])
            if error:
                return ToolResult.error(error)

            event_type = params["event_type"]
            coordination_mode = params.get("coordination_mode", "priority")
            timeout_ms = params.get("timeout_ms", 5000)

            # Validate coordination mode
            valid_modes = ["sequential", "parallel", "priority"]
            if coordination_mode not in valid_modes:
                return ToolResult.error(
                    f"Invalid coordination mode. Must be one of: {', '.join(valid_modes)}"
                )

            # Get hooks for event
            hooks_to_execute = self._get_hooks_for_event(event_type)

            # Execute hooks based on coordination mode
            if coordination_mode == "sequential":
                hooks_executed = self._execute_sequential(hooks_to_execute, timeout_ms)
            elif coordination_mode == "parallel":
                hooks_executed = self._execute_parallel(hooks_to_execute, timeout_ms)
            else:  # priority
                hooks_executed = self._execute_priority_order(hooks_to_execute, timeout_ms)

            execution_time_ms = sum(h.get("execution_time_ms", 0) for h in hooks_executed)

            result_data = {
                "event_type": event_type,
                "coordination_mode": coordination_mode,
                "hooks_executed": hooks_executed,
                "execution_time_ms": execution_time_ms,
                "success_count": sum(1 for h in hooks_executed if h["status"] == "success"),
                "total_hooks": len(hooks_executed)
            }

            self.log_execution(params, ToolResult.success(result_data))
            return ToolResult.success(result_data)

        except Exception as e:
            self.logger.error(f"Hook coordination failed: {e}")
            return ToolResult.error(f"Hook coordination failed: {str(e)}")

    def _get_hooks_for_event(self, event_type: str) -> List[Dict[str, Any]]:
        """Get hooks registered for event type.

        Args:
            event_type: Event type

        Returns:
            List of hooks for event
        """
        # In real implementation, would query hook_registry
        return [
            {"hook_id": "hook001", "hook_name": "record_event", "priority": 100},
            {"hook_id": "hook002", "hook_name": "validate_plan", "priority": 75},
        ]

    def _execute_sequential(self, hooks: List[Dict[str, Any]], timeout_ms: int) -> List[Dict[str, Any]]:
        """Execute hooks sequentially.

        Args:
            hooks: List of hooks to execute
            timeout_ms: Timeout for execution

        Returns:
            List of execution results
        """
        return [
            {
                "hook_id": h["hook_id"],
                "status": "success",
                "execution_time_ms": 50
            }
            for h in hooks
        ]

    def _execute_parallel(self, hooks: List[Dict[str, Any]], timeout_ms: int) -> List[Dict[str, Any]]:
        """Execute hooks in parallel.

        Args:
            hooks: List of hooks to execute
            timeout_ms: Timeout for execution

        Returns:
            List of execution results
        """
        return [
            {
                "hook_id": h["hook_id"],
                "status": "success",
                "execution_time_ms": 30
            }
            for h in hooks
        ]

    def _execute_priority_order(self, hooks: List[Dict[str, Any]], timeout_ms: int) -> List[Dict[str, Any]]:
        """Execute hooks in priority order.

        Args:
            hooks: List of hooks to execute
            timeout_ms: Timeout for execution

        Returns:
            List of execution results
        """
        # Sort by priority (highest first)
        sorted_hooks = sorted(hooks, key=lambda h: h.get("priority", 50), reverse=True)

        return [
            {
                "hook_id": h["hook_id"],
                "status": "success",
                "execution_time_ms": 40,
                "priority": h.get("priority", 50)
            }
            for h in sorted_hooks
        ]
