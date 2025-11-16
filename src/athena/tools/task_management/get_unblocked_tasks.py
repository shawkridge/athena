"""
GET_UNBLOCKED_TASKS Tool - Phase 3a Task Management

Gets tasks that are ready to work on (not blocked by dependencies).

To use:
    from athena.prospective.dependencies import DependencyStore
    from athena.core.database import Database

    db = Database()
    store = DependencyStore(db)
    unblocked = store.get_unblocked_tasks(project_id, statuses, limit)
"""


def get_unblocked_tasks(
    project_id: int,
    statuses: list = None,
    limit: int = 10,
) -> list:
    """Get tasks that are ready to work on (unblocked by dependencies).

    Parameters:
        project_id: Project ID
        statuses: Filter by status (default: ['pending', 'in_progress'])
        limit: Max tasks to return (default: 10)

    Returns:
        List of unblocked tasks, each with:
        - id: Task ID
        - content: Task name
        - status: Task status
        - priority: Task priority
        - is_blocked: False (all are unblocked)

    Example:
        >>> unblocked = get_unblocked_tasks(project_id=1, limit=5)
        >>> next_task = max(unblocked, key=lambda t: t['priority'])
        >>> print(f"Next task: {next_task['content']}")
        Next task: Implement user authentication

    Usage Pattern:
        1. Filter to get only tasks ready to start
        2. Sort by priority to get highest priority next
        3. Suggest to user with confidence (no dependencies blocking)

    Implementation:
        from athena.prospective.dependencies import DependencyStore
        from athena.core.database import Database

        db = Database()
        store = DependencyStore(db)
        statuses = statuses or ['pending', 'in_progress']
        return store.get_unblocked_tasks(project_id, statuses, limit)
    """

    try:
        from athena.prospective.dependencies import DependencyStore
        from athena.core.database import Database

        db = Database()
        store = DependencyStore(db)
        statuses = statuses or ['pending', 'in_progress']
        tasks = store.get_unblocked_tasks(project_id, statuses, limit)
        return tasks
    except Exception as e:
        raise RuntimeError(f"Failed to get unblocked tasks: {str(e)}") from e
