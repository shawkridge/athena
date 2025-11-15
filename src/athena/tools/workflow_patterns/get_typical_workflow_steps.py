"""get_typical_workflow_steps - Get workflow step chain for a task type.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional, List


def get_typical_workflow_steps(
    project_id: int,
    task_type: str,
    max_steps: int = 10,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get complete workflow step chain for a task type.

    Builds sequence of most-likely successors starting from a task type.
    Each step shows confidence and frequency data.

    Args:
        project_id (int): Project ID
        task_type (str): Starting task type (e.g., 'feature')
        max_steps (int): Maximum steps to include (default: 10)
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with ordered workflow steps

    Examples:
        >>> get_typical_workflow_steps(project_id=1, task_type='feature', max_steps=6)
        {
            'task_type': 'feature',
            'steps': [
                {'step_num': 1, 'type': 'feature', 'confidence': 1.0, 'frequency': 25},
                {'step_num': 2, 'type': 'implement', 'confidence': 0.92, 'frequency': 23},
                {'step_num': 3, 'type': 'test', 'confidence': 0.94, 'frequency': 24},
                {'step_num': 4, 'type': 'review', 'confidence': 0.88, 'frequency': 22},
                {'step_num': 5, 'type': 'deploy', 'confidence': 0.85, 'frequency': 21}
            ],
            'completion_rate': 0.84,
            'average_duration_days': 14
        }

    Use this to:
        - See full workflow from start to finish
        - Understand typical task duration
        - Plan multi-step workflows
        - Identify standard completion rates
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.suggestions import PatternSuggestionEngine

        engine = PatternSuggestionEngine(db)

        # Get typical workflow steps
        steps = engine.get_typical_workflow_steps(
            project_id, task_type, max_steps
        )

        if not steps:
            return {
                "task_type": task_type,
                "steps": [],
                "message": "No workflow steps discovered",
                "recommendation": "Complete 5+ tasks of this type to build workflow",
            }

        return {
            "task_type": task_type,
            "steps": steps,
            "total_steps": len(steps),
        }

    except Exception as e:
        return {
            "error": f"Failed to get workflow steps: {str(e)}",
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "get_typical_workflow_steps"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Get workflow step chain for a task type"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "sequence", "steps", "chain", "planning"]
