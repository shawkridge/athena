"""Prospective Memory Operations - Direct Python API

This module provides clean async functions for prospective memory operations.
Prospective memory handles tasks, goals, and future-oriented thinking.

Functions can be imported and called directly by agents:
  from athena.prospective.operations import create_task, list_tasks
  task_id = await create_task("Implement feature X", due_date=...)
  tasks = await list_tasks(status="pending", limit=10)

No MCP protocol, no wrapper overhead. Just Python async functions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.database import Database
from .store import ProspectiveStore
from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


class ProspectiveOperations:
    """Encapsulates all prospective memory operations.

    This class is instantiated with a database and prospective store,
    providing all operations as methods.
    """

    def __init__(self, db: Database, store: ProspectiveStore):
        """Initialize with database and prospective store.

        Args:
            db: Database instance
            store: ProspectiveStore instance
        """
        self.db = db
        self.store = store
        self.logger = logger

    async def create_task(
        self,
        title: str,
        description: str = "",
        due_date: datetime | None = None,
        priority: int = 5,
        tags: List[str] | None = None,
        status: str = "pending",
    ) -> str:
        """Create a new task.

        Args:
            title: Task title
            description: Task description
            due_date: Optional due date
            priority: Priority (1-10, default 5)
            tags: Tags for categorization
            status: Task status (pending, in_progress, completed, cancelled)

        Returns:
            Task ID
        """
        if not title:
            raise ValueError("title is required")

        priority = max(1, min(10, priority))

        task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            tags=tags or [],
            status=TaskStatus(status),
            created_at=datetime.now(),
            completed_at=None,
            metadata={}
        )

        return await self.store.store(task)

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 20,
        sort_by: str = "priority",
    ) -> List[Task]:
        """List tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending, in_progress, completed, cancelled)
            limit: Maximum tasks to return
            sort_by: Sort field (priority, due_date, created_at)

        Returns:
            List of tasks
        """
        filters = {
            "limit": limit,
            "sort_by": sort_by,
        }

        if status:
            filters["status"] = status

        return await self.store.list(**filters)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found
        """
        return await self.store.get(task_id)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> bool:
        """Update task status.

        Args:
            task_id: Task ID
            status: New status (pending, in_progress, completed, cancelled)

        Returns:
            True if updated successfully
        """
        task = await self.store.get(task_id)
        if not task:
            return False

        task.status = TaskStatus(status)
        if status == "completed":
            task.completed_at = datetime.now()

        await self.store.update(task)
        return True

    async def get_active_tasks(self, limit: int = 10) -> List[Task]:
        """Get active (pending or in-progress) tasks.

        Args:
            limit: Maximum tasks to return

        Returns:
            Active tasks sorted by priority
        """
        pending = await self.store.list(status="pending", limit=limit // 2)
        in_progress = await self.store.list(status="in_progress", limit=limit // 2)

        all_tasks = pending + in_progress
        # Sort by priority descending
        return sorted(all_tasks, key=lambda t: t.priority, reverse=True)[:limit]

    async def get_overdue_tasks(self, limit: int = 10) -> List[Task]:
        """Get tasks that are overdue.

        Args:
            limit: Maximum tasks to return

        Returns:
            Overdue tasks
        """
        now = datetime.now()
        pending = await self.store.list(status="pending", limit=100)

        overdue = [t for t in pending if t.due_date and t.due_date < now]
        return sorted(overdue, key=lambda t: t.due_date)[:limit]

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about tasks.

        Returns:
            Dictionary with task statistics
        """
        pending = await self.store.list(status="pending", limit=10000)
        in_progress = await self.store.list(status="in_progress", limit=10000)
        completed = await self.store.list(status="completed", limit=10000)

        return {
            "total_pending": len(pending),
            "total_in_progress": len(in_progress),
            "total_completed": len(completed),
            "total_tasks": len(pending) + len(in_progress) + len(completed),
            "completion_rate": len(completed) / (len(pending) + len(in_progress) + len(completed))
            if (len(pending) + len(in_progress) + len(completed)) > 0
            else 0.0,
        }


# Global singleton instance (lazy-initialized by manager)
_operations: ProspectiveOperations | None = None


def initialize(db: Database, store: ProspectiveStore) -> None:
    """Initialize the global prospective operations instance.

    Called by UnifiedMemoryManager during setup.

    Args:
        db: Database instance
        store: ProspectiveStore instance
    """
    global _operations
    _operations = ProspectiveOperations(db, store)


def get_operations() -> ProspectiveOperations:
    """Get the global prospective operations instance.

    Returns:
        ProspectiveOperations instance

    Raises:
        RuntimeError: If not initialized
    """
    if _operations is None:
        raise RuntimeError(
            "Prospective operations not initialized. "
            "Call initialize(db, store) first."
        )
    return _operations


# Convenience functions that delegate to global instance
async def create_task(
    title: str,
    description: str = "",
    due_date: datetime | None = None,
    priority: int = 5,
    tags: List[str] | None = None,
    status: str = "pending",
) -> str:
    """Create a task. See ProspectiveOperations.create_task for details."""
    ops = get_operations()
    return await ops.create_task(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        tags=tags,
        status=status,
    )


async def list_tasks(
    status: str | None = None,
    limit: int = 20,
    sort_by: str = "priority",
) -> List[Task]:
    """List tasks. See ProspectiveOperations.list_tasks for details."""
    ops = get_operations()
    return await ops.list_tasks(status=status, limit=limit, sort_by=sort_by)


async def get_task(task_id: str) -> Optional[Task]:
    """Get a task. See ProspectiveOperations.get_task for details."""
    ops = get_operations()
    return await ops.get_task(task_id)


async def update_task_status(task_id: str, status: str) -> bool:
    """Update task status. See ProspectiveOperations.update_task_status for details."""
    ops = get_operations()
    return await ops.update_task_status(task_id=task_id, status=status)


async def get_active_tasks(limit: int = 10) -> List[Task]:
    """Get active tasks. See ProspectiveOperations.get_active_tasks for details."""
    ops = get_operations()
    return await ops.get_active_tasks(limit=limit)


async def get_overdue_tasks(limit: int = 10) -> List[Task]:
    """Get overdue tasks. See ProspectiveOperations.get_overdue_tasks for details."""
    ops = get_operations()
    return await ops.get_overdue_tasks(limit=limit)


async def get_statistics() -> Dict[str, Any]:
    """Get task statistics. See ProspectiveOperations.get_statistics for details."""
    ops = get_operations()
    return await ops.get_statistics()
