"""Phase 3b handlers: Workflow Pattern Management.

Exposes Phase 3b workflow pattern tools through MCP server.
Allows agents to discover and suggest optimal task workflows.
"""

import logging
from typing import Any, Dict, List
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus

logger = logging.getLogger(__name__)


class Phase3bHandlersMixin:
    """Phase 3b handler methods for workflow pattern management.

    Methods exposed to Claude Code through MCP:
    - _handle_analyze_workflow_patterns: Mine patterns from completed tasks
    - _handle_get_typical_workflow: Get standard workflow for task type
    - _handle_suggest_next_task_with_patterns: Smart suggestions based on patterns
    - _handle_find_workflow_anomalies: Find unusual task sequences
    - _handle_get_pattern_metrics: Get detailed pattern metrics
    - _handle_assess_workflow_risk: Risk assessment for task transitions
    """

    async def _handle_analyze_workflow_patterns(self, args: dict) -> list[TextContent]:
        """Analyze completed task sequences to discover patterns.

        Args:
            None (uses current project)

        Returns:
            Analysis results including patterns found and statistics
        """
        try:
            project = self.project_manager.get_or_create_project()

            from ..workflow.analyzer import TaskSequenceAnalyzer

            analyzer = TaskSequenceAnalyzer(self.db)
            result = analyzer.analyze_completed_sequences(project.id)

            if "error" in result:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data=result,
                ).to_mcp()

            # Add statistics
            stats = analyzer.get_pattern_statistics(project.id)
            if stats:
                result["statistics"] = stats

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=result,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error analyzing workflow patterns: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_typical_workflow(self, args: dict) -> list[TextContent]:
        """Get typical workflow sequence for a task type.

        Args:
            task_type: Task type (e.g., 'feature', 'bugfix')

        Returns:
            Workflow sequence with steps and confidence scores
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..workflow.suggestions import PatternSuggestionEngine

            engine = PatternSuggestionEngine(self.db)
            workflow = engine.suggest_workflow_for_type(project.id, task_type)

            if not workflow:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": f"No workflow data for task type: {task_type}"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=workflow,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting typical workflow: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_suggest_next_task_with_patterns(self, args: dict) -> list[TextContent]:
        """Suggest next task based on completed task and patterns.

        Args:
            completed_task_id: Task that was just completed

        Returns:
            List of suggested task types ranked by confidence
        """
        try:
            project = self.project_manager.get_or_create_project()
            completed_task_id = args.get("completed_task_id")

            if not completed_task_id:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "completed_task_id required"},
                ).to_mcp()

            from ..workflow.suggestions import PatternSuggestionEngine

            engine = PatternSuggestionEngine(self.db)
            suggestions = engine.suggest_next_task_with_patterns(
                project.id, completed_task_id, limit=5
            )

            if not suggestions:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": "No pattern-based suggestions available"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={"suggestions": suggestions},
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error suggesting next task: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_find_workflow_anomalies(self, args: dict) -> list[TextContent]:
        """Find unusual workflow patterns.

        Args:
            confidence_threshold: Threshold for "anomaly" (default: 0.1 = 10%)

        Returns:
            List of unusual patterns
        """
        try:
            project = self.project_manager.get_or_create_project()
            confidence_threshold = args.get("confidence_threshold", 0.1)

            from ..workflow.patterns import WorkflowPatternStore

            store = WorkflowPatternStore(self.db)
            anomalies = store.find_anomalies(project.id, confidence_threshold)

            if not anomalies:
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data={"anomalies": [], "message": "No unusual patterns detected"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "anomalies": anomalies,
                    "count": len(anomalies),
                    "message": f"Found {len(anomalies)} unusual workflow patterns",
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error finding anomalies: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_pattern_metrics(self, args: dict) -> list[TextContent]:
        """Get metrics for workflow patterns.

        Args:
            None (uses current project)

        Returns:
            Statistics on discovered patterns
        """
        try:
            project = self.project_manager.get_or_create_project()

            from ..workflow.analyzer import TaskSequenceAnalyzer

            analyzer = TaskSequenceAnalyzer(self.db)
            stats = analyzer.get_pattern_statistics(project.id)

            if not stats:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": "No pattern metrics available"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=stats,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_assess_workflow_risk(self, args: dict) -> list[TextContent]:
        """Assess risk of a task transition.

        Args:
            current_task_type: Current task type
            next_task_type: Proposed next task type

        Returns:
            Risk assessment with recommendations
        """
        try:
            project = self.project_manager.get_or_create_project()
            current_type = args.get("current_task_type")
            next_type = args.get("next_task_type")

            if not current_type or not next_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "current_task_type and next_task_type required"},
                ).to_mcp()

            from ..workflow.suggestions import PatternSuggestionEngine

            engine = PatternSuggestionEngine(self.db)
            assessment = engine.get_risk_assessment(project.id, current_type, next_type)

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=assessment,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_typical_workflow_steps(self, args: dict) -> list[TextContent]:
        """Get typical workflow steps for a task type.

        Builds a chain of most-likely successors.

        Args:
            task_type: Starting task type
            confidence_threshold: Min confidence for steps (default: 0.5)

        Returns:
            Ordered list of workflow steps
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")
            confidence_threshold = args.get("confidence_threshold", 0.5)

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..workflow.suggestions import PatternSuggestionEngine

            engine = PatternSuggestionEngine(self.db)
            steps = engine.get_typical_workflow_steps(
                project.id, task_type, confidence_threshold
            )

            if not steps:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={"message": f"No workflow steps for task type: {task_type}"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={"workflow_steps": steps},
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting workflow steps: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()
