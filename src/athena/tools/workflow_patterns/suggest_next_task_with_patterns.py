"""suggest_next_task_with_patterns - Get next task suggestions based on patterns.

Part of Phase 3b: Workflow Pattern Mining
"""

from typing import Dict, Any, Optional, List


def suggest_next_task_with_patterns(
    project_id: int,
    completed_task_id: int,
    limit: int = 5,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Suggest next tasks based on patterns from completed task.

    Analyzes the type of completed task and suggests what typically comes next
    based on historical workflow patterns. Provides confidence scores and explanations.

    Args:
        project_id (int): Project ID
        completed_task_id (int): Task that was just completed
        limit (int): Max suggestions to return (default: 5)
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with task suggestions and explanations

    Examples:
        >>> suggest_next_task_with_patterns(project_id=1, completed_task_id=42, limit=5)
        {
            'suggestions': [
                {
                    'task_type': 'test',
                    'confidence': 0.92,
                    'frequency': 23,
                    'explanation': 'Based on 23 similar workflows (92% confidence)'
                },
                {
                    'task_type': 'review',
                    'confidence': 0.45,
                    'frequency': 9,
                    'explanation': 'Based on 9 similar workflows (45% confidence)'
                }
            ],
            'completed_task_type': 'implement'
        }

    Confidence interpretation:
        - 0.90+: Very reliable (do this next!)
        - 0.70-0.90: Likely (usually follows this pattern)
        - 0.50-0.70: Possible (sometimes follows this)
        - <0.50: Uncommon (rarely follows this)

    Use this to:
        - Get intelligent next task suggestions
        - Understand typical workflow patterns
        - Stay on expected path
        - Discover alternative paths
    """

    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..workflow.suggestions import PatternSuggestionEngine

        engine = PatternSuggestionEngine(db)
        suggestions = engine.suggest_next_task_with_patterns(
            project_id, completed_task_id, limit
        )

        if not suggestions:
            return {
                "suggestions": [],
                "message": "No suggestions available",
                "reason": "Not enough pattern data; complete more tasks first",
            }

        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "limit": limit,
        }

    except Exception as e:
        return {
            "error": f"Failed to suggest next task: {str(e)}",
            "project_id": project_id,
            "task_id": completed_task_id,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "suggest_next_task_with_patterns"
__tool_category__ = "workflow_patterns"
__tool_summary__ = "Get next task suggestions based on patterns"
__tool_version__ = "1.0.0"
__tool_tags__ = ["workflow", "suggestion", "patterns", "recommendation", "next-task"]
