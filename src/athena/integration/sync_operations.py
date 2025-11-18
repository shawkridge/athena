"""Bidirectional Sync Operations for TodoWrite ↔ Athena

High-level operations for syncing todos with the Athena database.
Coordinates between todowrite_sync (mapping) and database_sync (persistence).

Functions handle:
- Creating plans from todos and storing to database
- Updating plans based on todo changes
- Resolving conflicts with database
- Extracting completed todos for learning
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .todowrite_sync import (
    convert_todo_to_plan,
    convert_plan_to_todo,
    resolve_sync_conflict,
    get_sync_metadata,
)
from .database_sync import get_store

logger = logging.getLogger(__name__)


async def sync_todo_to_database(
    todo: Dict[str, Any],
    project_id: int = 1,
) -> Tuple[bool, str]:
    """Sync a TodoWrite todo to the database as a plan.

    Creates or updates a plan in the todowrite_plans table based on the todo.

    Args:
        todo: TodoWrite todo {content, status, activeForm}
        project_id: Project ID

    Returns:
        (success, plan_id or error_message)
    """
    try:
        # Convert todo to plan
        plan = await convert_todo_to_plan(todo, project_id=project_id)

        # Get database store
        store = get_store()

        # Check if plan already exists
        todo_id = todo.get("id", str(hash(todo.get("content", ""))))
        existing = await store.get_plan_by_todo_id(todo_id)

        if existing:
            # Update existing plan
            success = await store.update_plan_status(
                existing["plan_id"],
                plan["status"],
                plan["phase"],
            )
            if success:
                await store.update_sync_status(existing["plan_id"], "synced")
                logger.info(f"Updated plan {existing['plan_id']} from todo {todo_id}")
                return True, existing["plan_id"]
            else:
                return False, "Failed to update plan"
        else:
            # Store new plan
            success, result = await store.store_plan_from_todo(todo_id, plan, project_id)
            if success:
                # Record mapping
                metadata = get_sync_metadata()
                metadata.map_todo_to_plan(todo_id, result)
                logger.info(f"Stored new plan {result} from todo {todo_id}")
                return True, result
            else:
                return False, result

    except Exception as e:
        logger.error(f"Failed to sync todo to database: {e}")
        return False, str(e)


async def sync_todo_status_change(
    todo_id: str,
    new_status: str,
    project_id: int = 1,
) -> Tuple[bool, str]:
    """Sync a todo status change to its corresponding plan.

    Args:
        todo_id: TodoWrite todo ID
        new_status: New TodoWrite status
        project_id: Project ID

    Returns:
        (success, message or error)
    """
    try:
        store = get_store()

        # Get existing plan
        plan = await store.get_plan_by_todo_id(todo_id)
        if not plan:
            return False, f"No plan found for todo {todo_id}"

        # Map TodoWrite status to Athena status and phase
        from .todowrite_sync import (
            _map_todowrite_to_athena_status,
            _determine_phase_from_todo_status,
        )

        athena_status = _map_todowrite_to_athena_status(new_status)
        phase = _determine_phase_from_todo_status(new_status)

        # Update plan in database
        success = await store.update_plan_status(
            plan["plan_id"],
            athena_status,
            phase,
        )

        if success:
            await store.update_sync_status(plan["plan_id"], "synced")
            logger.info(f"Synced todo {todo_id} status change to plan")
            return True, f"Updated plan status to {athena_status}"
        else:
            return False, "Failed to update plan status"

    except Exception as e:
        logger.error(f"Failed to sync status change: {e}")
        return False, str(e)


async def detect_database_conflicts(
    project_id: int = 1,
) -> List[Dict[str, Any]]:
    """Detect conflicts between todos and plans in the database.

    Checks all plans with conflict status.

    Args:
        project_id: Project ID

    Returns:
        List of conflicted plan dicts with conflict details
    """
    try:
        store = get_store()

        # Get all conflicted plans
        conflicts = await store.get_sync_conflicts(project_id)

        logger.info(f"Found {len(conflicts)} sync conflicts")

        return conflicts

    except Exception as e:
        logger.error(f"Failed to detect conflicts: {e}")
        return []


async def resolve_database_conflict(
    plan_id: str,
    preference: str = "plan",  # "todo" or "plan"
) -> Tuple[bool, Dict[str, Any]]:
    """Resolve a conflict between todo and plan in the database.

    Args:
        plan_id: Athena plan ID
        preference: Which source to prefer ("todo" or "plan")

    Returns:
        (success, resolved_plan dict or error info)
    """
    try:
        store = get_store()

        # Get the conflicted plan
        plan = await store.get_plan_by_plan_id(plan_id)
        if not plan:
            return False, {"error": f"Plan {plan_id} not found"}

        # Reconstruct todo from plan
        todo = convert_plan_to_todo(plan)

        # Resolve conflict
        resolved = await resolve_sync_conflict(
            todo,
            plan,
            prefer=preference,
        )

        # Update plan in database
        success = await store.update_plan_status(
            plan_id,
            resolved["plan"]["status"],
            resolved["plan"].get("phase"),
        )

        if success:
            await store.update_sync_status(plan_id, "synced", None)
            logger.info(f"Resolved conflict for plan {plan_id} with preference {preference}")
            return True, resolved["plan"]
        else:
            return False, {"error": "Failed to update plan"}

    except Exception as e:
        logger.error(f"Failed to resolve conflict: {e}")
        return False, {"error": str(e)}


async def get_completed_plans(
    project_id: int = 1,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get all completed plans for learning/consolidation.

    Args:
        project_id: Project ID
        limit: Maximum results

    Returns:
        List of completed plan dicts
    """
    try:
        store = get_store()

        plans = await store.list_plans_by_status("completed", project_id, limit)

        logger.info(f"Retrieved {len(plans)} completed plans")

        return plans

    except Exception as e:
        logger.error(f"Failed to get completed plans: {e}")
        return []


async def get_active_plans(
    project_id: int = 1,
    limit: int = 7,  # Baddeley's 7±2
) -> List[Dict[str, Any]]:
    """Get active plans for working memory injection.

    Returns only the most recently updated plans (for working memory context).

    Args:
        project_id: Project ID
        limit: Maximum results (default 7 for Baddeley's limit)

    Returns:
        List of active plan dicts
    """
    try:
        store = get_store()

        # Get in_progress and pending plans, ordered by updated_at
        cursor = store.db.get_cursor()

        cursor.execute(
            """
            SELECT * FROM todowrite_plans
            WHERE project_id = %s AND status IN ('in_progress', 'ready', 'planning')
            ORDER BY updated_at DESC
            LIMIT %s
        """,
            (project_id, limit),
        )

        rows = cursor.fetchall()
        cursor.close()

        plans = [store._row_to_dict(row) for row in rows]

        logger.info(f"Retrieved {len(plans)} active plans for working memory")

        return plans

    except Exception as e:
        logger.error(f"Failed to get active plans: {e}")
        return []


async def get_sync_summary(
    project_id: int = 1,
) -> Dict[str, Any]:
    """Get summary of TodoWrite ↔ Athena sync state.

    Args:
        project_id: Project ID

    Returns:
        Summary dict with stats and insights
    """
    try:
        store = get_store()

        # Get statistics
        stats = await store.get_statistics(project_id)

        # Get pending syncs
        pending = await store.get_pending_syncs(project_id, limit=10)

        # Get conflicts
        conflicts = await store.get_sync_conflicts(project_id, limit=10)

        # Get sync metadata
        metadata = get_sync_metadata()

        summary = {
            "statistics": stats,
            "pending_syncs": len(pending),
            "pending_plans": [p["plan_id"] for p in pending[:5]],
            "conflicts": len(conflicts),
            "conflict_plans": [c["plan_id"] for c in conflicts[:5]],
            "total_mappings": len(metadata.todo_to_plan_mapping),
            "last_sync": metadata.last_sync.isoformat() if metadata.last_sync else None,
        }

        return summary

    except Exception as e:
        logger.error(f"Failed to get sync summary: {e}")
        return {
            "error": str(e),
            "statistics": {},
            "pending_syncs": 0,
            "conflicts": 0,
        }


async def cleanup_completed_plans(
    project_id: int = 1,
    days_old: int = 30,
) -> int:
    """Clean up old completed plans from the database.

    Useful for removing completed plans after consolidation to learning system.

    Args:
        project_id: Project ID
        days_old: Delete completed plans older than this many days

    Returns:
        Number of plans deleted
    """
    try:
        store = get_store()
        cursor = store.db.get_cursor()

        # Calculate cutoff timestamp
        import time

        now = int(time.time())
        cutoff = now - (days_old * 24 * 60 * 60)

        cursor.execute(
            """
            DELETE FROM todowrite_plans
            WHERE project_id = %s AND status = 'completed' AND created_at < %s
        """,
            (project_id, cutoff),
        )

        deleted = cursor.rowcount
        cursor.close()

        logger.info(f"Cleaned up {deleted} completed plans older than {days_old} days")

        return deleted

    except Exception as e:
        logger.error(f"Failed to cleanup completed plans: {e}")
        return 0


async def export_plans_as_todos(
    project_id: int = 1,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Export all plans as TodoWrite todos.

    Useful for exporting back to external systems or for visualization.

    Args:
        project_id: Project ID
        status_filter: Optional status filter

    Returns:
        List of TodoWrite todo dicts
    """
    try:
        store = get_store()
        cursor = store.db.get_cursor()

        if status_filter:
            cursor.execute(
                """
                SELECT * FROM todowrite_plans
                WHERE project_id = %s AND status = %s
                ORDER BY created_at DESC
            """,
                (project_id, status_filter),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM todowrite_plans
                WHERE project_id = %s
                ORDER BY created_at DESC
            """,
                (project_id,),
            )

        rows = cursor.fetchall()
        cursor.close()

        todos = []
        for row in rows:
            plan = store._row_to_dict(row)
            todo = convert_plan_to_todo(plan)
            todos.append(todo)

        logger.info(f"Exported {len(todos)} plans as todos")

        return todos

    except Exception as e:
        logger.error(f"Failed to export plans as todos: {e}")
        return []
