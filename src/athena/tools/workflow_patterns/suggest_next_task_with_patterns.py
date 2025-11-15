"""
SUGGEST_NEXT_TASK_WITH_PATTERNS Tool - Phase 3b Workflow Analysis

Gets intelligent task suggestions based on historical workflow patterns.

To use:
    from athena.workflow.suggestions import PatternSuggestionEngine
    from athena.core.database import Database

    db = Database()
    engine = PatternSuggestionEngine(db)
    suggestions = engine.suggest_next_task_with_patterns(project_id, task_id, limit=5)
"""


def suggest_next_task_with_patterns(
    project_id: int,
    completed_task_id: int,
    limit: int = 5,
) -> list:
    """Suggest next tasks based on patterns from completed task.

    Analyzes the type of completed task and suggests what typically comes next
    based on historical workflow patterns.

    Parameters:
        project_id: Project ID
        completed_task_id: Task that was just completed
        limit: Max suggestions to return (default: 5)

    Returns:
        List of suggested task types with metrics:
        [
          {
            "task_type": "test",
            "confidence": 0.92,
            "frequency": 23,
            "avg_duration_hours": 48.5,
            "explanation": "Based on 23 similar workflows (92% confidence)"
          },
          ...
        ]

    Example:
        >>> suggestions = suggest_next_task_with_patterns(1, 42)
        >>> for s in suggestions:
        ...     print(f"{s['task_type']}: {s['confidence']:.0%} confidence")
        test: 92% confidence
        review: 45% confidence

    How it works:
        1. Get completed task type (from content + tags)
        2. Query workflow_patterns table
        3. Find tasks that typically follow this type
        4. Return sorted by confidence
        5. Include explanation with historical evidence

    Confidence interpretation:
        - 0.90+: Very reliable (do this next!)
        - 0.70-0.90: Likely (usually follows this pattern)
        - 0.50-0.70: Possible (sometimes follows this)
        - <0.50: Uncommon (rarely follows this)

    Implementation:
        from athena.workflow.suggestions import PatternSuggestionEngine
        from athena.core.database import Database

        db = Database()
        engine = PatternSuggestionEngine(db)
        return engine.suggest_next_task_with_patterns(project_id, completed_task_id, limit)
    """

    raise NotImplementedError(
        "Use PatternSuggestionEngine directly:\n"
        "  from athena.workflow.suggestions import PatternSuggestionEngine\n"
        "  from athena.core.database import Database\n"
        "  db = Database()\n"
        "  engine = PatternSuggestionEngine(db)\n"
        "  return engine.suggest_next_task_with_patterns(project_id, task_id, limit)"
    )
