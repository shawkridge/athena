"""Pattern-Based Task Suggestions - Phase 3b.

Suggests next tasks based on historical workflow patterns.
Ranks suggestions by confidence and provides explanations.
"""

import logging
import json
from typing import Optional, Dict, Any, List

from ..core.database import Database
from .patterns import WorkflowPatternStore
from .analyzer import TaskTypeClassifier

logger = logging.getLogger(__name__)


class PatternSuggestionEngine:
    """Suggests next tasks based on workflow patterns."""

    def __init__(self, db: Database):
        """Initialize suggestion engine.

        Args:
            db: Database instance
        """
        self.db = db
        self.pattern_store = WorkflowPatternStore(db)

    def suggest_next_task_with_patterns(
        self,
        project_id: int,
        completed_task_id: int,
        limit: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """Suggest next tasks based on completed task and patterns.

        Args:
            project_id: Project ID
            completed_task_id: Task that was just completed
            limit: Max suggestions to return

        Returns:
            List of suggested task types with confidence scores
        """
        try:
            cursor = self.db.get_cursor()

            # Get the completed task
            cursor.execute(
                """
                SELECT content, tags FROM prospective_tasks
                WHERE id = %s AND project_id = %s
                """,
                (completed_task_id, project_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            content, tags_json = row
            tags = json.loads(tags_json) if tags_json else []

            # Classify the task type
            completed_type = TaskTypeClassifier.classify(content, tags)

            # Get successor patterns for this type
            suggestions = self.pattern_store.get_successor_patterns(
                project_id, completed_type, limit
            )

            if not suggestions:
                return None

            # Add explanations
            for suggestion in suggestions:
                suggestion["explanation"] = (
                    f"Based on {suggestion['frequency']} similar workflows "
                    f"({suggestion['confidence']:.0%} confidence)"
                )

            return suggestions

        except Exception as e:
            logger.error(f"Failed to suggest next task: {e}")
            return None

    def suggest_workflow_for_type(
        self,
        project_id: int,
        task_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the typical workflow for a task type.

        Args:
            project_id: Project ID
            task_type: Task type (e.g., 'feature', 'bugfix')

        Returns:
            Workflow dict with sequence and metrics
        """
        try:
            workflow = self.pattern_store.get_workflow_sequence(project_id, task_type)
            return workflow

        except Exception as e:
            logger.error(f"Failed to get workflow for type: {e}")
            return None

    def get_next_task_in_workflow(
        self,
        project_id: int,
        current_task_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the next task in a workflow for a given type.

        Args:
            project_id: Project ID
            current_task_type: Current task type

        Returns:
            Next task type suggestion or None
        """
        try:
            suggestions = self.pattern_store.get_successor_patterns(
                project_id, current_task_type, limit=1
            )

            if suggestions and len(suggestions) > 0:
                return suggestions[0]

            return None

        except Exception as e:
            logger.error(f"Failed to get next task in workflow: {e}")
            return None

    def get_typical_workflow_steps(
        self,
        project_id: int,
        task_type: str,
        confidence_threshold: float = 0.5,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get typical workflow steps for a task type.

        Builds a chain of most-likely successors starting from the task type.

        Args:
            project_id: Project ID
            task_type: Starting task type
            confidence_threshold: Min confidence for steps (0.0-1.0)

        Returns:
            List of workflow steps in order
        """
        try:
            steps = []
            current_type = task_type

            for step_num in range(1, 6):  # Max 5 steps
                # Get next task in chain
                suggestions = self.pattern_store.get_successor_patterns(
                    project_id, current_type, limit=1
                )

                if not suggestions:
                    break

                next_type = suggestions[0]
                confidence = next_type.get("confidence", 0.0)

                if confidence < confidence_threshold:
                    break

                steps.append(
                    {
                        "step": step_num,
                        "task_type": next_type["task_type"],
                        "confidence": confidence,
                        "frequency": next_type.get("frequency"),
                    }
                )

                current_type = next_type["task_type"]

            return steps if steps else None

        except Exception as e:
            logger.error(f"Failed to get typical workflow steps: {e}")
            return None

    def is_workflow_unusual(
        self,
        project_id: int,
        task_type: str,
        next_type: str,
        confidence_threshold: float = 0.1,
    ) -> bool:
        """Check if a task transition is unusual (low confidence).

        Args:
            project_id: Project ID
            task_type: Current task type
            next_type: Next task type
            confidence_threshold: Confidence threshold for "normal" (default: 0.1)

        Returns:
            True if transition is unusual
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT confidence FROM workflow_patterns
                WHERE project_id = %s AND from_task_type = %s AND to_task_type = %s
                """,
                (project_id, task_type, next_type),
            )

            row = cursor.fetchone()
            if not row:
                return True  # No pattern found = unusual

            confidence = row[0] or 0.0
            return confidence < confidence_threshold

        except Exception as e:
            logger.error(f"Failed to check if workflow unusual: {e}")
            return False

    def get_risk_assessment(
        self,
        project_id: int,
        task_type: str,
        next_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Assess risk of a task transition.

        Returns risk level and recommendations.

        Args:
            project_id: Project ID
            task_type: Current task type
            next_type: Next task type

        Returns:
            Risk assessment dict
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT confidence, frequency FROM workflow_patterns
                WHERE project_id = %s AND from_task_type = %s AND to_task_type = %s
                """,
                (project_id, task_type, next_type),
            )

            row = cursor.fetchone()

            if not row:
                return {
                    "risk_level": "high",
                    "confidence": 0.0,
                    "frequency": 0,
                    "message": f"No history of {task_type} → {next_type}",
                    "recommendation": "Verify this is the correct next step",
                }

            confidence = row[0] or 0.0
            frequency = row[1] or 0

            if confidence > 0.75:
                risk_level = "low"
                recommendation = "This is a standard workflow pattern"
            elif confidence > 0.5:
                risk_level = "medium"
                recommendation = "This is common but not guaranteed optimal"
            else:
                risk_level = "high"
                recommendation = "Consider if this is the right next step"

            return {
                "risk_level": risk_level,
                "confidence": round(confidence, 3),
                "frequency": frequency,
                "message": f"{task_type} → {next_type}: {confidence:.0%} confidence",
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error(f"Failed to get risk assessment: {e}")
            return None
