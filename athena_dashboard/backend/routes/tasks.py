"""
Tasks endpoint - Prospective memory task operations.
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_tasks():
    """List all active tasks."""
    return {
        "active": [
            {
                "id": "task_1",
                "title": "Implement remaining memory layer pages",
                "status": "in_progress",
                "priority": "high",
                "dueDate": "2025-11-19T00:00:00Z",
                "progress": 35,
            },
            {
                "id": "task_2",
                "title": "Add real-time WebSocket updates",
                "status": "pending",
                "priority": "medium",
                "dueDate": "2025-11-20T00:00:00Z",
                "progress": 0,
            },
        ],
        "completed": [
            {
                "id": "task_0",
                "title": "Dashboard clean restart",
                "status": "completed",
                "completedDate": "2025-11-18T07:41:00Z",
            },
        ],
        "overdue": [],
    }


@router.get("/active")
async def get_active_tasks():
    """Get only active/in-progress tasks."""
    return {
        "count": 2,
        "tasks": [
            {
                "id": "task_1",
                "title": "Implement remaining memory layer pages",
                "progress": 35,
                "blockers": [],
            },
            {
                "id": "task_2",
                "title": "Add real-time WebSocket updates",
                "progress": 0,
                "blockers": ["task_1"],
            },
        ],
    }


@router.get("/statistics")
async def get_task_statistics():
    """Task statistics and trends."""
    return {
        "totalTasks": 5,
        "activeTasks": 2,
        "completedTasks": 3,
        "overdueTasks": 0,
        "completionRate": 0.60,
        "averageCompletionTime": "2.3 hours",
        "trends": {
            "completionVelocity": "increasing",
            "averageEstimationAccuracy": 0.82,
        },
    }
