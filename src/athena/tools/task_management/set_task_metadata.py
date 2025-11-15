"""
SET_TASK_METADATA Tool - Phase 3a Task Management

Agents can discover and read this tool definition.

To use:
    from athena.prospective.metadata import MetadataStore
    from athena.core.database import Database

    db = Database()
    store = MetadataStore(db)
    success = store.set_metadata(project_id, task_id, ...)
"""


def set_task_metadata(
    project_id: int,
    task_id: int,
    effort_estimate: int = None,
    complexity_score: int = None,
    priority_score: int = None,
    tags: list = None,
) -> bool:
    """Set task metadata (effort, complexity, tags).

    Parameters:
        project_id: Project ID
        task_id: Task ID
        effort_estimate: Estimated time in minutes (optional)
        complexity_score: 1-10 complexity rating (optional)
        priority_score: 1-10 priority rating (optional)
        tags: List of tags like ['feature', 'urgent'] (optional)

    Returns:
        True if successful, False otherwise

    Example:
        >>> set_task_metadata(
        ...     project_id=1,
        ...     task_id=1,
        ...     effort_estimate=120,
        ...     complexity_score=7,
        ...     tags=['feature', 'urgent']
        ... )
        # Returns: True

    Implementation:
        from athena.prospective.metadata import MetadataStore
        from athena.core.database import Database

        db = Database()
        store = MetadataStore(db)
        return store.set_metadata(project_id, task_id, effort_estimate,
                                 complexity_score, priority_score, tags)
    """

    raise NotImplementedError(
        "Use MetadataStore directly:\n"
        "  from athena.prospective.metadata import MetadataStore\n"
        "  from athena.core.database import Database\n"
        "  db = Database()\n"
        "  store = MetadataStore(db)\n"
        "  store.set_metadata(project_id, task_id, effort_estimate, ...)"
    )
