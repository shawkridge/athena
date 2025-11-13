"""Slash Command Handlers - Extracted Domain Module

This module contains all slash command handler methods for Phase 5-6 slash
command operations (6 total handlers):
- _handle_consolidate_advanced
- _handle_plan_validate_advanced
- _handle_task_health
- _handle_estimate_resources
- _handle_stress_test_plan
- _handle_learning_effectiveness

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.database, self.manager, self.logger

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(SlashCommandHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class SlashCommandHandlersMixin:
    """Mixin class containing all slash command handler methods.

    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all slash command operations.
    """

    async def _handle_consolidate_advanced(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /consolidate-advanced command for advanced consolidation.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - strategy: Consolidation strategy (balanced, speed, quality, minimal)
                - measure_quality: Measure consolidation quality

        Returns:
            List with TextContent containing command result
        """
        try:
            project_id = args.get("project_id", 0)
            strategy = args.get("strategy", "balanced")
            measure_quality = args.get("measure_quality", False)

            # Import the command
            from ..integration.slash_commands import ConsolidateAdvancedCommand

            command = ConsolidateAdvancedCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                project_id=project_id,
                strategy=strategy,
                measure_quality=measure_quality
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing consolidate-advanced: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_plan_validate_advanced(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /plan-validate-advanced command for advanced plan validation.

        Args:
            args: Dictionary with keys:
                - task_description: Task to validate
                - include_scenarios: Include scenario testing

        Returns:
            List with TextContent containing command result
        """
        try:
            task_description = args.get("task_description", "")
            include_scenarios = args.get("include_scenarios", False)

            # Import the command
            from ..integration.slash_commands import PlanValidateAdvancedCommand

            command = PlanValidateAdvancedCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                task_description=task_description,
                include_scenarios=include_scenarios
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing plan-validate-advanced: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_task_health(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /task-health command for task health analysis.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - include_trends: Include trend analysis

        Returns:
            List with TextContent containing command result
        """
        try:
            project_id = args.get("project_id", 0)
            include_trends = args.get("include_trends", False)

            # Import the command
            from ..integration.slash_commands import TaskHealthCommand

            command = TaskHealthCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                project_id=project_id,
                include_trends=include_trends
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing task-health: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_estimate_resources(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /estimate-resources command for resource estimation.

        Args:
            args: Dictionary with keys:
                - task_description: Task description
                - include_breakdown: Include detailed breakdown

        Returns:
            List with TextContent containing command result
        """
        try:
            task_description = args.get("task_description", "")
            include_breakdown = args.get("include_breakdown", False)

            # Import the command
            from ..integration.slash_commands import EstimateResourcesCommand

            command = EstimateResourcesCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                task_description=task_description,
                include_breakdown=include_breakdown
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing estimate-resources: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_stress_test_plan(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /stress-test-plan command for scenario stress testing.

        Args:
            args: Dictionary with keys:
                - task_description: Task to stress test
                - confidence_level: Confidence level threshold

        Returns:
            List with TextContent containing command result
        """
        try:
            task_description = args.get("task_description", "")
            confidence_level = args.get("confidence_level", 0.8)

            # Import the command
            from ..integration.slash_commands import StressTestPlanCommand

            command = StressTestPlanCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                task_description=task_description,
                confidence_level=confidence_level
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing stress-test-plan: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_learning_effectiveness(
        self, args: dict
    ) -> list[TextContent]:
        """Handle /learning-effectiveness command for learning analysis.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - days_back: Days to analyze
                - include_recommendations: Include recommendations

        Returns:
            List with TextContent containing command result
        """
        try:
            project_id = args.get("project_id", 0)
            days_back = args.get("days_back", 7)
            include_recommendations = args.get("include_recommendations", False)

            # Import the command
            from ..integration.slash_commands import LearningEffectivenessCommand

            command = LearningEffectivenessCommand(self.database if hasattr(self, 'database') else None)
            result = await command.execute(
                project_id=project_id,
                days_back=days_back,
                include_recommendations=include_recommendations
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error executing learning-effectiveness: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]


# Module-level forwarding functions for test imports
async def handle_consolidate_advanced(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for consolidate_advanced handler."""
    return await server._handle_consolidate_advanced(args)


async def handle_plan_validate_advanced(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for plan_validate_advanced handler."""
    return await server._handle_plan_validate_advanced(args)


async def handle_task_health(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for task_health handler."""
    return await server._handle_task_health(args)


async def handle_estimate_resources(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for estimate_resources handler."""
    return await server._handle_estimate_resources(args)


async def handle_stress_test_plan(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for stress_test_plan handler."""
    return await server._handle_stress_test_plan(args)


async def handle_learning_effectiveness(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for learning_effectiveness handler."""
    return await server._handle_learning_effectiveness(args)
