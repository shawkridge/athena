"""
GET_TASK_METADATA Tool - Phase 3a Task Management

Gets full metadata for a task including effort, complexity, and accuracy.

To use:
    from athena.prospective.metadata import MetadataStore
    from athena.core.database import Database

    db = Database()
    store = MetadataStore(db)
    metadata = store.get_task_metadata(project_id, task_id)
"""


def get_task_metadata(project_id: int, task_id: int) -> dict:
    """Get all metadata for a task.

    Parameters:
        project_id: Project ID
        task_id: Task ID

    Returns:
        Dictionary with:
        - id: Task ID
        - content: Task name
        - status: Task status
        - effort_estimate: Minutes estimated
        - effort_actual: Minutes actually spent
        - complexity_score: 1-10 complexity
        - priority_score: 1-10 priority
        - tags: List of tags
        - started_at: When task started
        - completed_at: When task completed
        - accuracy: Dict with accuracy_percent, variance, etc. (if available)

    Example:
        >>> metadata = get_task_metadata(project_id=1, task_id=1)
        >>> print(f"Accuracy: {metadata['accuracy']['accuracy_percent']}%")
        Accuracy: 80.0%

    Implementation:
        from athena.prospective.metadata import MetadataStore
        from athena.core.database import Database

        db = Database()
        store = MetadataStore(db)
        return store.get_task_metadata(project_id, task_id)
    """

    raise NotImplementedError(
        "Use MetadataStore directly:\n"
        "  from athena.prospective.metadata import MetadataStore\n"
        "  from athena.core.database import Database\n"
        "  db = Database()\n"
        "  store = MetadataStore(db)\n"
        "  return store.get_task_metadata(project_id, task_id)"
    )
