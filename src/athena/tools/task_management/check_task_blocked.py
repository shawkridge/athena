"""
CHECK_TASK_BLOCKED Tool - Phase 3a Task Management

Agents can discover and read this tool definition to understand how it works.

To use this tool:
    from athena.prospective.dependencies import DependencyStore
    from athena.core.database import Database

    db = Database()
    store = DependencyStore(db)
    is_blocked, blocking_ids = store.is_task_blocked(project_id, task_id)
"""


def check_task_blocked(project_id: int, task_id: int):
    """Check if a task is blocked by incomplete dependencies.

    Parameters:
        project_id: Project ID
        task_id: Task ID to check

    Returns:
        (is_blocked, blocking_task_ids) tuple
        - is_blocked: bool - True if task is blocked
        - blocking_task_ids: list[int] - Task IDs that block this task

    Example:
        >>> check_task_blocked(project_id=1, task_id=2)
        # Returns: (True, [1])
        # Task 2 is blocked by Task 1
    """
    try:
        from athena.prospective.dependencies import DependencyStore
        from athena.core.database import Database

        db = Database()
        store = DependencyStore(db)
        is_blocked, blocking_ids = store.is_task_blocked(project_id, task_id)
        return (is_blocked, blocking_ids)
    except Exception as e:
        raise RuntimeError(f"Failed to check task blocked status: {str(e)}") from e
