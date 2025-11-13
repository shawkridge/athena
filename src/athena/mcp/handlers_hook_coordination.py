"""Hook Coordination Handlers - Extracted Domain Module

This module contains all hook coordination handler methods for Phase 5-6 hook
optimization operations (5 total handlers):
- _handle_optimize_session_start
- _handle_optimize_session_end
- _handle_optimize_user_prompt_submit
- _handle_optimize_post_tool_use
- _handle_optimize_pre_execution

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.database, self.manager, self.logger

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(HookCoordinationHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class HookCoordinationHandlersMixin:
    """Mixin class containing all hook coordination handler methods.

    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all hook coordination operations.
    """

    async def _handle_optimize_session_start(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize session start hook for context initialization.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - validate_plans: Validate existing plans

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            validate_plans = args.get("validate_plans", False)

            # Import the optimizer
            from ..integration.hook_coordination import SessionStartOptimizer

            optimizer = SessionStartOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                validate_plans=validate_plans
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing session start: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_session_end(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize session end hook for consolidation.

        Args:
            args: Dictionary with keys:
                - session_id: Session identifier
                - extract_patterns: Extract patterns from session
                - measure_quality: Measure consolidation quality

        Returns:
            List with TextContent containing optimization result
        """
        try:
            session_id = args.get("session_id", "")
            extract_patterns = args.get("extract_patterns", False)
            measure_quality = args.get("measure_quality", False)

            # Import the optimizer
            from ..integration.hook_coordination import SessionEndOptimizer

            optimizer = SessionEndOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                session_id=session_id,
                extract_patterns=extract_patterns,
                measure_quality=measure_quality
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing session end: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_user_prompt_submit(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize user prompt submit hook for context grounding.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - monitor_health: Monitor system health

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            monitor_health = args.get("monitor_health", False)

            # Import the optimizer
            from ..integration.hook_coordination import UserPromptOptimizer

            optimizer = UserPromptOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                monitor_health=monitor_health
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing user prompt submit: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_post_tool_use(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize post tool use hook for event recording.

        Args:
            args: Dictionary with keys:
                - tool_name: Tool that was executed
                - execution_time_ms: Execution time in milliseconds
                - tool_result: Result status
                - task_id: Task identifier

        Returns:
            List with TextContent containing optimization result
        """
        try:
            tool_name = args.get("tool_name", "")
            execution_time_ms = args.get("execution_time_ms", 0)
            tool_result = args.get("tool_result", "")
            task_id = args.get("task_id", 0)

            # Import the optimizer
            from ..integration.hook_coordination import PostToolOptimizer

            optimizer = PostToolOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                tool_result=tool_result,
                task_id=task_id
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing post tool use: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_pre_execution(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize pre-execution hook for task validation.

        Args:
            args: Dictionary with keys:
                - task_id: Task identifier
                - strict_mode: Enforce strict validation
                - run_scenarios: Run scenario analysis

        Returns:
            List with TextContent containing optimization result
        """
        try:
            task_id = args.get("task_id", 0)
            strict_mode = args.get("strict_mode", False)
            run_scenarios = args.get("run_scenarios", "auto")

            # Import the optimizer
            from ..integration.hook_coordination import PreExecutionOptimizer

            optimizer = PreExecutionOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                task_id=task_id,
                strict_mode=strict_mode,
                run_scenarios=run_scenarios
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing pre-execution: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]


# Module-level forwarding functions for test imports
async def handle_optimize_session_start(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_session_start handler."""
    return await server._handle_optimize_session_start(args)


async def handle_optimize_session_end(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_session_end handler."""
    return await server._handle_optimize_session_end(args)


async def handle_optimize_user_prompt_submit(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_user_prompt_submit handler."""
    return await server._handle_optimize_user_prompt_submit(args)


async def handle_optimize_post_tool_use(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_post_tool_use handler."""
    return await server._handle_optimize_post_tool_use(args)


async def handle_optimize_pre_execution(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_pre_execution handler."""
    return await server._handle_optimize_pre_execution(args)
