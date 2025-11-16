"""Task learning handler methods for MCP server.

Exposes task pattern learning and execution history tools.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus
from ..prospective.task_learning_integration import TaskLearningIntegration
from ..prospective.task_pattern_store import TaskPatternStore
from ..core.database import get_database

logger = logging.getLogger(__name__)


class TaskLearningHandlersMixin:
    """Task learning handler methods for pattern extraction and history.

    Provides tools for:
    - Retrieving task execution history
    - Querying learned patterns
    - Analyzing task success factors
    - Getting execution metrics

    Methods:
    - _handle_get_task_history: Get recent task execution history
    - _handle_get_task_patterns: Get learned patterns by type/confidence
    - _handle_get_task_analytics: Get execution metrics and correlations
    - _handle_estimate_duration: Estimate task duration using historical patterns
    """

    async def _handle_get_task_history(self, args: dict) -> list[TextContent]:
        """Get recent task execution history for a project.

        Args:
            project_id: Optional project ID (uses current if not specified)
            limit: Maximum number of records (default 50, max 500)

        Returns:
            List of recent task executions with actual vs estimated times
        """
        try:
            project = self.project_manager.get_or_create_project()
            project_id = args.get("project_id", project.id)
            limit = min(args.get("limit", 50), 500)

            # Get learning integration
            db = get_database()
            integration = TaskLearningIntegration(db)

            # Get task history
            history = integration.get_task_history(project_id, limit=limit)

            if not history:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "data": [],
                        "message": "No task execution history found"
                    })
                )]

            # Format response
            formatted_history = []
            for record in history:
                formatted_history.append({
                    "task_id": record["task_id"],
                    "task": record["task_content"],
                    "priority": record["priority"],
                    "status": record["status"],
                    "estimated_minutes": record["estimated_minutes"],
                    "actual_minutes": round(record["actual_minutes"], 1),
                    "error_percent": round(record["error_percent"], 1) if record["error_percent"] else None,
                    "success": record["success"],
                    "failure_reason": record["failure_mode"],
                    "completed_at": record["completed_at"].isoformat() if record["completed_at"] else None,
                })

            response = {
                "status": "success",
                "data": formatted_history,
                "count": len(formatted_history),
                "project_id": project_id,
            }

            result = StructuredResult.success(
                data=response,
                metadata={"operation": "task_history_retrieval"}
            )
            return [result.as_optimized_content()]

        except Exception as e:
            logger.error(f"Error in _handle_get_task_history: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)})
            )]

    async def _handle_get_task_patterns(self, args: dict) -> list[TextContent]:
        """Get learned task patterns for a project.

        Args:
            project_id: Optional project ID (uses current if not specified)
            pattern_type: Optional filter by type (duration, success_rate, phase_correlation, property_correlation)
            min_confidence: Minimum confidence score (0.0-1.0, default 0.6)
            status: Optional status filter (active, deprecated, archived)

        Returns:
            List of learned patterns with confidence scores and predictions
        """
        try:
            project = self.project_manager.get_or_create_project()
            project_id = args.get("project_id", project.id)
            pattern_type = args.get("pattern_type")
            min_confidence = float(args.get("min_confidence", 0.6))
            status = args.get("status", "active")

            # Get pattern store
            db = get_database()
            store = TaskPatternStore(db)

            # Get patterns
            patterns = store.get_patterns_by_project(
                project_id,
                status=status,
                pattern_type=pattern_type,
                min_confidence=min_confidence
            )

            if not patterns:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "data": [],
                        "message": f"No patterns found (min_confidence={min_confidence})"
                    })
                )]

            # Format response
            formatted_patterns = []
            for pattern in patterns:
                try:
                    condition = json.loads(pattern.condition_json)
                except:
                    condition = pattern.condition_json

                formatted_patterns.append({
                    "id": pattern.id,
                    "name": pattern.pattern_name,
                    "type": pattern.pattern_type,
                    "description": pattern.description,
                    "prediction": pattern.prediction,
                    "conditions": condition,
                    "success_rate": round(pattern.success_rate, 3),
                    "confidence": round(pattern.confidence_score, 3),
                    "sample_size": pattern.sample_size,
                    "system_2_validated": pattern.system_2_validated,
                    "extraction_method": pattern.extraction_method,
                    "status": pattern.status,
                    "created_at": pattern.created_at.isoformat() if pattern.created_at else None,
                })

            response = {
                "status": "success",
                "data": formatted_patterns,
                "count": len(formatted_patterns),
                "project_id": project_id,
                "filters": {
                    "pattern_type": pattern_type,
                    "min_confidence": min_confidence,
                    "status": status
                }
            }

            result = StructuredResult.success(
                data=response,
                metadata={"operation": "pattern_retrieval"}
            )
            return [result.as_optimized_content()]

        except Exception as e:
            logger.error(f"Error in _handle_get_task_patterns: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)})
            )]

    async def _handle_get_task_analytics(self, args: dict) -> list[TextContent]:
        """Get task execution analytics and property correlations.

        Args:
            project_id: Optional project ID (uses current if not specified)
            property_name: Optional filter by property (priority, complexity, dependencies_count)

        Returns:
            Task execution statistics and property-success correlations
        """
        try:
            project = self.project_manager.get_or_create_project()
            project_id = args.get("project_id", project.id)
            property_name = args.get("property_name")

            db = get_database()
            store = TaskPatternStore(db)

            # Get correlations
            if property_name:
                correlations = store.get_correlations_for_property(project_id, property_name)
            else:
                # Get high confidence correlations
                correlations = store.get_high_confidence_correlations(project_id, min_confidence=0.7)

            # Format response
            formatted_correlations = []
            for corr in correlations:
                formatted_correlations.append({
                    "property": corr.property_name,
                    "value": corr.property_value,
                    "success_rate": round(corr.success_rate, 3),
                    "total_tasks": corr.total_tasks,
                    "successful": corr.successful_tasks,
                    "failed": corr.failed_tasks,
                    "confidence": round(corr.confidence_level, 3) if corr.confidence_level else None,
                    "avg_estimated_minutes": round(corr.avg_estimated_minutes, 1),
                    "avg_actual_minutes": round(corr.avg_actual_minutes, 1),
                    "estimation_accuracy_percent": round(corr.estimation_accuracy_percent, 1),
                })

            # Calculate overall statistics
            if formatted_correlations:
                avg_success = sum(c["success_rate"] for c in formatted_correlations) / len(formatted_correlations)
                overall_tasks = sum(c["total_tasks"] for c in formatted_correlations)
            else:
                avg_success = 0.0
                overall_tasks = 0

            response = {
                "status": "success",
                "data": formatted_correlations,
                "count": len(formatted_correlations),
                "project_id": project_id,
                "overall_stats": {
                    "average_success_rate": round(avg_success, 3),
                    "total_analyzed_tasks": overall_tasks,
                    "property_analyzed": property_name or "all"
                }
            }

            result = StructuredResult.success(
                data=response,
                metadata={"operation": "task_analytics"}
            )
            return [result.as_optimized_content()]

        except Exception as e:
            logger.error(f"Error in _handle_get_task_analytics: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)})
            )]

    async def _handle_estimate_duration(self, args: dict) -> list[TextContent]:
        """Estimate task duration using learned patterns.

        Args:
            task_description: Description of the task
            priority: Task priority (low, medium, high, critical)
            complexity: Estimated complexity (1-5)
            project_id: Optional project ID (uses current if not specified)

        Returns:
            Duration estimate with confidence level and reasoning
        """
        try:
            project = self.project_manager.get_or_create_project()
            project_id = args.get("project_id", project.id)
            priority = args.get("priority", "medium").lower()
            complexity = int(args.get("complexity", 3))

            db = get_database()
            store = TaskPatternStore(db)

            # Get relevant patterns
            patterns = store.get_patterns_by_project(
                project_id,
                min_confidence=0.6
            )

            # Find matching patterns
            matching_patterns = []
            for pattern in patterns:
                try:
                    conditions = json.loads(pattern.condition_json)

                    # Check if pattern applies
                    matches = True
                    if "priority" in conditions and conditions["priority"] != priority:
                        matches = False
                    if "complexity_estimate" in conditions and conditions["complexity_estimate"] != complexity:
                        matches = False

                    if matches:
                        matching_patterns.append(pattern)
                except:
                    pass

            # Estimate duration from matching patterns
            if matching_patterns:
                # Use pattern prediction to inform estimate
                high_confidence_patterns = [p for p in matching_patterns if p.confidence_score > 0.8]
                if high_confidence_patterns:
                    reasoning = f"Based on {len(high_confidence_patterns)} high-confidence patterns"
                    confidence = 0.8
                else:
                    reasoning = f"Based on {len(matching_patterns)} moderate-confidence patterns"
                    confidence = 0.6

                # Get historical durations for similar tasks
                from ..prospective.task_pattern_store import TaskPatternStore
                correlations = store.get_correlations_for_property(project_id, "priority")

                base_estimate = 60  # Default: 1 hour
                for corr in correlations:
                    if corr.property_value == priority:
                        base_estimate = int(corr.avg_actual_minutes)
                        break

                # Adjust for complexity
                complexity_multiplier = 1.0 + (complexity - 3) * 0.25  # Each complexity level adds 25%
                final_estimate = int(base_estimate * complexity_multiplier)

            else:
                reasoning = "No matching patterns found, using default estimate"
                base_estimate = 60
                complexity_multiplier = 1.0 + (complexity - 3) * 0.25
                final_estimate = int(base_estimate * complexity_multiplier)
                confidence = 0.4

            response = {
                "status": "success",
                "data": {
                    "estimated_minutes": final_estimate,
                    "estimated_hours": round(final_estimate / 60, 1),
                    "confidence": round(confidence, 2),
                    "reasoning": reasoning,
                    "factors": {
                        "priority": priority,
                        "complexity": complexity,
                        "base_estimate_minutes": base_estimate,
                        "complexity_multiplier": round(complexity_multiplier, 2)
                    },
                    "matching_patterns": len(matching_patterns),
                    "recommendation": f"Plan for {final_estimate} minutes with {int(confidence*100)}% confidence"
                }
            }

            result = StructuredResult.success(
                data=response,
                metadata={"operation": "duration_estimation"}
            )
            return [result.as_optimized_content()]

        except Exception as e:
            logger.error(f"Error in _handle_estimate_duration: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)})
            )]
