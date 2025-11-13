"""Skill Optimization Handlers - Extracted Domain Module

This module contains all skill optimization handler methods for Phase 5 skill
optimization operations (4 total handlers):
- _handle_optimize_learning_tracker
- _handle_optimize_procedure_suggester
- _handle_optimize_gap_detector
- _handle_optimize_quality_monitor

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.database, self.manager, self.logger

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(SkillOptimizationHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class SkillOptimizationHandlersMixin:
    """Mixin class containing all skill optimization handler methods.

    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all skill optimization operations.
    """

    async def _handle_optimize_learning_tracker(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize learning tracker for strategy effectiveness.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - analyze_effectiveness: Analyze strategy effectiveness
                - track_patterns: Track learning patterns

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            analyze_effectiveness = args.get("analyze_effectiveness", False)
            track_patterns = args.get("track_patterns", False)

            # Import the optimizer
            from ..integration.skill_optimization import LearningTrackerOptimizer

            optimizer = LearningTrackerOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                analyze_effectiveness=analyze_effectiveness,
                track_patterns=track_patterns
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing learning tracker: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_procedure_suggester(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize procedure suggester for workflow discovery.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - analyze_patterns: Analyze workflow patterns
                - discovery_depth: Depth of pattern discovery

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            analyze_patterns = args.get("analyze_patterns", False)
            discovery_depth = args.get("discovery_depth", 3)

            # Import the optimizer
            from ..integration.skill_optimization import ProcedureSuggesterOptimizer

            optimizer = ProcedureSuggesterOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                analyze_patterns=analyze_patterns,
                discovery_depth=discovery_depth
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing procedure suggester: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_gap_detector(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize gap detector for knowledge gap analysis.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - stability_window: Time window for stability analysis
                - analyze_contradictions: Analyze contradictions

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            stability_window = args.get("stability_window", 7)
            analyze_contradictions = args.get("analyze_contradictions", False)

            # Import the optimizer
            from ..integration.skill_optimization import GapDetectorOptimizer

            optimizer = GapDetectorOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                stability_window=stability_window,
                analyze_contradictions=analyze_contradictions
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing gap detector: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]

    async def _handle_optimize_quality_monitor(
        self, args: dict
    ) -> list[TextContent]:
        """Optimize quality monitor for memory quality analysis.

        Args:
            args: Dictionary with keys:
                - project_id: Project identifier
                - measure_layers: Measure all memory layers
                - domain_analysis: Analyze by domain

        Returns:
            List with TextContent containing optimization result
        """
        try:
            project_id = args.get("project_id", 0)
            measure_layers = args.get("measure_layers", False)
            domain_analysis = args.get("domain_analysis", False)

            # Import the optimizer
            from ..integration.skill_optimization import QualityMonitorOptimizer

            optimizer = QualityMonitorOptimizer(self.database if hasattr(self, 'database') else None)
            result = await optimizer.execute(
                project_id=project_id,
                measure_layers=measure_layers,
                domain_analysis=domain_analysis
            )

            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error optimizing quality monitor: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e), "status": "error"})
            )]


# Module-level forwarding functions for test imports
async def handle_optimize_learning_tracker(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_learning_tracker handler."""
    return await server._handle_optimize_learning_tracker(args)


async def handle_optimize_procedure_suggester(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_procedure_suggester handler."""
    return await server._handle_optimize_procedure_suggester(args)


async def handle_optimize_gap_detector(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_gap_detector handler."""
    return await server._handle_optimize_gap_detector(args)


async def handle_optimize_quality_monitor(
    server: Any, args: Dict[str, Any]
) -> list[TextContent]:
    """Forwarding function for optimize_quality_monitor handler."""
    return await server._handle_optimize_quality_monitor(args)
