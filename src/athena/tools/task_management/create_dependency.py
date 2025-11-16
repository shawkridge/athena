"""
CREATE_DEPENDENCY Tool - Phase 3a Task Management

This file is discoverable by agents exploring the filesystem.
Agents can read this file to understand the tool, then import from the proper location.

To use this tool:
    from athena.prospective.dependencies import DependencyStore
    from athena.core.database import Database

    db = Database()
    store = DependencyStore(db)
    dep_id = store.create_dependency(project_id, from_task_id, to_task_id)
"""


def create_dependency(
    project_id: int,
    from_task_id: int,
    to_task_id: int,
    dependency_type: str = "blocks",
) -> int:
    """Create a task dependency (Task A blocks Task B).

    Parameters:
        project_id: Project ID
        from_task_id: Task that must complete first
        to_task_id: Task that is blocked
        dependency_type: Type of dependency (default: 'blocks')

    Returns:
        Dependency ID on success, None on error

    Example:
        >>> create_dependency(project_id=1, from_task_id=1, to_task_id=2)
        # Returns: dependency_id
        # Task 1 now blocks Task 2
    """
    try:
        from athena.prospective.dependencies import DependencyStore
        from athena.core.database import Database

        db = Database()
        store = DependencyStore(db)
        dep_id = store.create_dependency(project_id, from_task_id, to_task_id, dependency_type)
        return dep_id
    except Exception as e:
        raise RuntimeError(f"Failed to create task dependency: {str(e)}") from e
