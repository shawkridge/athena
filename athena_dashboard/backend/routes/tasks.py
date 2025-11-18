"""
Tasks endpoint - Prospective memory task operations.

Uses real data from Athena's prospective memory layer.
"""

from fastapi import APIRouter
import logging
import athena

logger = logging.getLogger(__name__)
router = APIRouter()


async def ensure_initialized():
    """Ensure Athena is initialized."""
    try:
        await athena.initialize_athena()
    except Exception as e:
        logger.warning(f"Athena initialization warning: {e}")


@router.get("/")
async def list_tasks():
    """List all tasks - active, completed, and overdue."""
    await ensure_initialized()

    try:
        active = await athena.get_active_tasks(limit=10)
        overdue = await athena.get_overdue_tasks(limit=10)

        return {
            "active": [
                {
                    "id": t.get("id", ""),
                    "title": t.get("name", ""),
                    "status": "in_progress",
                    "priority": t.get("priority", "medium"),
                    "dueDate": t.get("due_date", ""),
                    "progress": t.get("progress", 0),
                }
                for t in (active or [])
            ],
            "completed": [],
            "overdue": [
                {
                    "id": t.get("id", ""),
                    "title": t.get("name", ""),
                    "status": "overdue",
                    "priority": t.get("priority", "medium"),
                }
                for t in (overdue or [])
            ],
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return {"active": [], "completed": [], "overdue": []}


@router.get("/active")
async def get_active_tasks_endpoint():
    """Get only active/in-progress tasks."""
    await ensure_initialized()

    try:
        tasks = await athena.get_active_tasks(limit=10)

        return {
            "count": len(tasks) if tasks else 0,
            "tasks": [
                {
                    "id": t.get("id", ""),
                    "title": t.get("name", ""),
                    "progress": t.get("progress", 0),
                    "blockers": t.get("blockers", []),
                }
                for t in (tasks or [])
            ],
        }
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return {"count": 0, "tasks": []}


@router.get("/statistics")
async def get_task_statistics():
    """Task statistics and trends."""
    await ensure_initialized()

    try:
        stats = await athena.prospective_get_statistics()

        return {
            "totalTasks": stats.get("total_tasks", 0),
            "activeTasks": stats.get("active_tasks", 0),
            "completedTasks": stats.get("completed_tasks", 0),
            "overdueTasks": stats.get("overdue_tasks", 0),
            "completionRate": stats.get("completion_rate", 0),
            "averageCompletionTime": stats.get("avg_completion_time", "0 hours"),
            "trends": {
                "completionVelocity": stats.get("trend", "stable"),
                "averageEstimationAccuracy": stats.get("estimation_accuracy", 0),
            },
        }
    except Exception as e:
        logger.error(f"Error getting task statistics: {e}")
        return {
            "totalTasks": 0,
            "activeTasks": 0,
            "completedTasks": 0,
            "overdueTasks": 0,
            "completionRate": 0,
            "averageCompletionTime": "0 hours",
            "trends": {"completionVelocity": "unknown", "averageEstimationAccuracy": 0},
        }
