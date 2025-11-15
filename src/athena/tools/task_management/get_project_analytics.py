"""
GET_PROJECT_ANALYTICS Tool - Phase 3a Task Management

Gets aggregate analytics for the project including effort and accuracy trends.

To use:
    from athena.prospective.metadata import MetadataStore
    from athena.core.database import Database

    db = Database()
    store = MetadataStore(db)
    analytics = store.get_project_analytics(project_id)
"""


def get_project_analytics(project_id: int) -> dict:
    """Get project-wide analytics on effort and accuracy.

    Parameters:
        project_id: Project ID

    Returns:
        Dictionary with:
        - total_tasks: Total number of tasks
        - estimated_tasks: Tasks with effort estimates
        - tracked_tasks: Tasks with actual effort recorded
        - avg_estimate_minutes: Average estimated effort
        - avg_actual_minutes: Average actual effort
        - avg_complexity: Average complexity score (1-10)
        - complexity_range: (min, max) complexity scores
        - overall_accuracy_percent: Aggregate estimate accuracy

    Example:
        >>> analytics = get_project_analytics(project_id=1)
        >>> print(f"Overall accuracy: {analytics['overall_accuracy_percent']}%")
        Overall accuracy: 82.5%
        >>> print(f"Avg complexity: {analytics['avg_complexity']}/10")
        Avg complexity: 6.2/10

    Insights:
        High accuracy (>85%): Good at estimating
        Low accuracy (<70%): Tend to underestimate
        High avg_actual vs avg_estimate: Tasks take longer than expected

    Implementation:
        from athena.prospective.metadata import MetadataStore
        from athena.core.database import Database

        db = Database()
        store = MetadataStore(db)
        return store.get_project_analytics(project_id)
    """

    raise NotImplementedError(
        "Use MetadataStore directly:\n"
        "  from athena.prospective.metadata import MetadataStore\n"
        "  from athena.core.database import Database\n"
        "  db = Database()\n"
        "  store = MetadataStore(db)\n"
        "  return store.get_project_analytics(project_id)"
    )
