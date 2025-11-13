"""Agent Optimization Handlers - Extracted Domain Module

This module contains all agent optimization handler methods for Phase 5-6 agent
optimization operations (5 total handlers):
- _handle_optimize_planning_orchestrator
- _handle_optimize_goal_orchestrator
- _handle_optimize_consolidation_trigger
- _handle_optimize_strategy_orchestrator
- _handle_optimize_attention_optimizer

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.database, self.manager, self.logger

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(AgentOptimizationHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class AgentOptimizationHandlersMixin:
    """Mixin class containing all agent optimization handler methods.

    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all agent optimization operations.
    """

    async def _handle_optimize_planning_orchestrator(
        self, args: Dict[str, Any]
    ) -> List[TextContent]:
        """Optimize planning orchestrator for task decomposition.

        Args:
            args: Dictionary with keys:
                - task_description: Task to plan
                - include_scenarios: Include scenario simulation
                - strict_mode: Enforce all constraints

        Returns:
            List with TextContent containing optimization result
        """
        try:
            task_description = args.get("task_description", "")
            include_scenarios = args.get("include_scenarios", False)
            strict_mode = args.get("strict_mode", False)

            if not task_description:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "task_description is required"})
                )]

            # Import the optimizer
            from ..integration.agent_optimization import PlanningOrchestratorOptimizer

            optimizer = PlanningOrchestratorOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                task_description=task_description,
                include_scenarios=include_scenarios,
                strict_mode=strict_mode
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing planning orchestrator: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_goal_orchestrator(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize goal orchestrator for goal management.

        Args:
            args: Dictionary with keys:
                - goal_id: Goal identifier
                - activate: Activate the goal
                - monitor_health: Monitor goal health

        Returns:
            List with TextContent containing optimization result
        """
        try:
            goal_id = args.get("goal_id", 0)
            activate = args.get("activate", False)
            monitor_health = args.get("monitor_health", False)

            # Import the optimizer
            from ..integration.agent_optimization import GoalOrchestratorOptimizer

            optimizer = GoalOrchestratorOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                goal_id=goal_id,
                activate=activate,
                monitor_health=monitor_health
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing goal orchestrator: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_consolidation_trigger(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize consolidation trigger for memory consolidation.

        Args:
            args: Dictionary with keys:
                - trigger_reason: Reason for consolidation
                - strategy: Consolidation strategy
                - measure_quality: Measure consolidation quality

        Returns:
            List with TextContent containing optimization result
        """
        try:
            trigger_reason = args.get("trigger_reason", "manual")
            strategy = args.get("strategy", "balanced")
            measure_quality = args.get("measure_quality", False)

            # Import the optimizer
            from ..integration.agent_optimization import ConsolidationTriggerOptimizer

            optimizer = ConsolidationTriggerOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                trigger_reason=trigger_reason,
                strategy=strategy,
                measure_quality=measure_quality
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing consolidation trigger: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_strategy_orchestrator(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize strategy orchestrator for strategy selection.

        Args:
            args: Dictionary with keys:
                - task_context: Task context information
                - analyze_effectiveness: Analyze strategy effectiveness
                - apply_refinements: Apply refinements

        Returns:
            List with TextContent containing optimization result
        """
        try:
            task_context = args.get("task_context", {})
            analyze_effectiveness = args.get("analyze_effectiveness", False)
            apply_refinements = args.get("apply_refinements", False)

            # Import the optimizer
            from ..integration.agent_optimization import StrategyOrchestratorOptimizer

            optimizer = StrategyOrchestratorOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                task_context=task_context,
                analyze_effectiveness=analyze_effectiveness,
                apply_refinements=apply_refinements
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing strategy orchestrator: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_attention_optimizer(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize attention optimizer for working memory management.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - weight_by_expertise: Weight items by expertise
                - analyze_patterns: Analyze attention patterns

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            weight_by_expertise = args.get("weight_by_expertise", False)
            analyze_patterns = args.get("analyze_patterns", False)

            # Import the optimizer
            from ..integration.agent_optimization import AttentionOptimizerOptimizer

            optimizer = AttentionOptimizerOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                weight_by_expertise=weight_by_expertise,
                analyze_patterns=analyze_patterns
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing attention optimizer: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]


# Module-level forwarding functions for test imports
async def handle_optimize_planning_orchestrator(
    server: Any, args: Dict[str, Any]
) -> List[TextContent]:
    """Forwarding function for optimize_planning_orchestrator handler."""
    return await server._handle_optimize_planning_orchestrator(args)


async def handle_optimize_goal_orchestrator(
    server: Any, args: Dict[str, Any]
) -> List[TextContent]:
    """Forwarding function for optimize_goal_orchestrator handler."""
    return await server._handle_optimize_goal_orchestrator(args)


async def handle_optimize_consolidation_trigger(
    server: Any, args: Dict[str, Any]
) -> List[TextContent]:
    """Forwarding function for optimize_consolidation_trigger handler."""
    return await server._handle_optimize_consolidation_trigger(args)


async def handle_optimize_strategy_orchestrator(
    server: Any, args: Dict[str, Any]
) -> List[TextContent]:
    """Forwarding function for optimize_strategy_orchestrator handler."""
    return await server._handle_optimize_strategy_orchestrator(args)


async def handle_optimize_attention_optimizer(
    server: Any, args: Dict[str, Any]
) -> List[TextContent]:
    """Forwarding function for optimize_attention_optimizer handler."""
    return await server._handle_optimize_attention_optimizer(args)
