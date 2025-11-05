"""
PHASE 6 MCP Tools

Exposes PHASE 6 Analytics Engine tools via MCP protocol.
- analyze_estimation_accuracy: Track estimation accuracy trends
- discover_patterns: Find reusable patterns from task history
"""

import json
import logging
from typing import List
from mcp.types import TextContent

from ..integration.estimation_analyzer import EstimationAnalyzer, AccuracyReport
from ..integration.pattern_discovery import PatternDiscovery
from ..core.database import Database

logger = logging.getLogger(__name__)


class Phase6MCP:
    """MCP handlers for PHASE 6 Analytics Engine tools."""

    def __init__(self, db: Database):
        """Initialize Phase 6 MCP handlers.

        Args:
            db: Database instance
        """
        self.db = db

    # =========================================================================
    # PHASE 6 Tool: analyze_estimation_accuracy
    # =========================================================================

    async def handle_analyze_estimation_accuracy(
        self, arguments: dict
    ) -> List[TextContent]:
        """Handle analyze_estimation_accuracy tool call.

        Analyzes task estimation accuracy over time.

        Args:
            arguments: {"project_id": int, "days_back": int (optional, default 30)}

        Returns:
            List with accuracy report
        """
        try:
            project_id = arguments.get("project_id")
            days_back = arguments.get("days_back", 30)

            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]

            # Create analyzer and generate report
            analyzer = EstimationAnalyzer(self.db, project_id)
            report = analyzer.analyze_accuracy(days_back)

            # Format response
            response = report.summary()

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in analyze_estimation_accuracy: {e}", exc_info=True)
            error_response = json.dumps({
                "error": str(e),
                "tool": "analyze_estimation_accuracy"
            })
            return [TextContent(type="text", text=error_response)]

    # =========================================================================
    # PHASE 6 Tool: discover_patterns
    # =========================================================================

    async def handle_discover_patterns(
        self, arguments: dict
    ) -> List[TextContent]:
        """Handle discover_patterns tool call.

        Discovers reusable patterns from task execution history.

        Args:
            arguments: {
                "project_id": int,
                "pattern_type": str (optional: "all" | "duration" | "dependency" | "resource" | "temporal" | "quality")
            }

        Returns:
            List with discovered patterns
        """
        try:
            project_id = arguments.get("project_id")
            pattern_type = arguments.get("pattern_type", "all")

            if not project_id:
                return [TextContent(
                    type="text",
                    text="Error: project_id is required"
                )]

            # Create discovery engine
            discovery = PatternDiscovery(self.db)

            # Get patterns
            if pattern_type == "all":
                patterns = discovery.discover_all_patterns()
            else:
                patterns = discovery.get_patterns_by_type(pattern_type)

            # Format response
            lines = [
                "=" * 70,
                f"PATTERN DISCOVERY RESULTS (Pattern Type: {pattern_type})",
                "=" * 70,
                f"\nTotal Patterns Found: {len(patterns)}\n",
            ]

            if patterns:
                for i, pattern in enumerate(patterns[:10], 1):
                    lines.append(f"{i}. {pattern.name}")
                    lines.append(f"   Type: {pattern.pattern_type}")
                    lines.append(f"   Frequency: {pattern.frequency}")
                    lines.append(f"   Impact: {pattern.impact:.1f}/1.0")
                    lines.append(f"   Actionability: {pattern.actionability:.1f}/1.0")
                    lines.append(f"   Score: {pattern.score:.2f}")
                    lines.append(f"   Details: {pattern.data}")
                    lines.append("")
            else:
                lines.append("No patterns discovered yet. Need more task history data.")

            # Get suggestions
            suggestions = discovery.suggest_improvements()
            if suggestions:
                lines.append("\nACTIONABLE SUGGESTIONS:")
                lines.append("-" * 70)
                for suggestion in suggestions[:5]:
                    lines.append(f"✓ {suggestion}")

            lines.append("\n" + "=" * 70)

            response = "\n".join(lines)
            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in discover_patterns: {e}", exc_info=True)
            error_response = json.dumps({
                "error": str(e),
                "tool": "discover_patterns"
            })
            return [TextContent(type="text", text=error_response)]


def get_phase6_tool_definitions() -> List[dict]:
    """Get PHASE 6 tool definitions for MCP server.

    Returns:
        List of tool definitions
    """
    return [
        {
            "name": "analyze_estimation_accuracy",
            "description": (
                "PHASE 6: Analyze task estimation accuracy over time. "
                "Returns MAPE, RMSE, bias, and accuracy metrics broken down by priority, complexity, and task type."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to analyze (default: 30)",
                        "default": 30
                    }
                },
                "required": ["project_id"]
            }
        },
        {
            "name": "discover_patterns",
            "description": (
                "PHASE 6: Discover reusable patterns from task execution history. "
                "Finds duration, dependency, resource, temporal, and quality patterns."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "Project ID to analyze"
                    },
                    "pattern_type": {
                        "type": "string",
                        "enum": ["all", "duration", "dependency", "resource", "temporal", "quality"],
                        "description": "Type of patterns to discover (default: all)",
                        "default": "all"
                    }
                },
                "required": ["project_id"]
            }
        }
    ]
