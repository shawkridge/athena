"""
RECORD_TASK_EFFORT Tool - Phase 3a Task Management

Records actual effort spent and calculates accuracy vs estimate.

To use:
    from athena.prospective.metadata import MetadataStore
    from athena.core.database import Database

    db = Database()
    store = MetadataStore(db)
    success = store.record_actual_effort(project_id, task_id, actual_minutes)
"""


def record_task_effort(
    project_id: int,
    task_id: int,
    actual_minutes: int,
) -> bool:
    """Record actual effort spent on a task.

    Parameters:
        project_id: Project ID
        task_id: Task ID
        actual_minutes: Actual time spent in minutes

    Returns:
        True if successful, False otherwise

    Example:
        >>> record_task_effort(project_id=1, task_id=1, actual_minutes=150)
        # Task 1 took 150 minutes
        # If estimate was 120, accuracy = 80% (120/150)

    Implementation:
        from athena.prospective.metadata import MetadataStore
        from athena.core.database import Database

        db = Database()
        store = MetadataStore(db)
        return store.record_actual_effort(project_id, task_id, actual_minutes)
    """

    raise NotImplementedError(
        "Use MetadataStore directly:\n"
        "  from athena.prospective.metadata import MetadataStore\n"
        "  from athena.core.database import Database\n"
        "  db = Database()\n"
        "  store = MetadataStore(db)\n"
        "  store.record_actual_effort(project_id, task_id, actual_minutes)"
    )
