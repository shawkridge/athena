"""get_typical_workflow - Get standard workflow sequence for a task type.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional


def get_typical_workflow(
    project_id: int,
    task_type: str,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get typical workflow sequence for a task type.

    Returns the standard workflow steps that typically follow a task type.
    Each step includes confidence score and frequency data.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix', 'refactor')
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with workflow steps and confidence scores

    Examples:
        >>> get_typical_workflow(project_id=1, task_type='feature')
        {
            'task_type': 'feature',
            'steps': [
                {'step': 'design', 'confidence': 0.95, 'frequency': 25},
                {'step': 'implement', 'confidence': 0.92, 'frequency': 23},
                {'step': 'test', 'confidence': 0.94, 'frequency': 24},
                {'step': 'review', 'confidence': 0.88, 'frequency': 22},
                {'step': 'deploy', 'confidence': 0.85, 'frequency': 21}
            ],
            'average_duration_days': 14,
            'completion_rate': 0.84
        }

    Use this to:
        - Understand standard workflow for a task type
        - See which steps are most reliable
        - Plan realistic task sequences
        - Identify when to deviate from standard
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.suggestions import PatternSuggestionEngine

        engine = PatternSuggestionEngine(db)
        workflow = engine.suggest_workflow_for_type(project_id, task_type)

        if not workflow:
            return {
                "message": f"No workflow data for task type: {task_type}",
                "task_type": task_type,
                "recommendation": "Complete 5+ tasks of this type to discover workflow",
            }

        return workflow

    except Exception as e:
        return {
            "error": f"Failed to get typical workflow: {str(e)}",
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_typical_workflow"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Get standard workflow sequence for a task type"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "sequence", "patterns", "planning"]
