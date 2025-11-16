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
        Dictionary with task metadata including effort, complexity, priority, etc.

    Example:
        >>> metadata = get_task_metadata(project_id=1, task_id=1)
        >>> print(f"Accuracy: {metadata['accuracy']['accuracy_percent']}%")
        Accuracy: 80.0%
    """
    try:
        from athena.prospective.metadata import MetadataStore
        from athena.core.database import Database

        db = Database()
        store = MetadataStore(db)
        metadata = store.get_task_metadata(project_id, task_id)
        return metadata
    except Exception as e:
        raise RuntimeError(f"Failed to get task metadata: {str(e)}") from e
