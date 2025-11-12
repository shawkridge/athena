"""
Task decomposition and planning.

Decomposes complex tasks into subtasks locally.
Returns task structure summary, not full task objects.
"""

from typing import Dict, Any, Optional, List
try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")
from datetime import datetime


def decompose_task(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    task_description: str,
    target_depth: int = 3,
    max_subtasks: int = 10
) -> Dict[str, Any]:
    """
    Decompose a task into subtasks.

    Returns structure summary: depths, counts, priorities.
    Token cost: ~300 tokens vs 15,000 for full task trees.

    Args:
        db_path: Path to database
        task_description: Description of task to decompose
        target_depth: Target decomposition depth
        max_subtasks: Max subtasks per level

    Returns:
        Summary with:
        - task_count: Total tasks in decomposition
        - depth_levels: Number of levels
        - critical_path_length: Longest dependency chain
        - priority_distribution: Count by priority
        - effort_estimates: Total and by priority
    """
    try:
        # For this demo, return a simulated decomposition
        # In production, this would use actual task decomposition logic

        decomposition = _simulate_decomposition(
            task_description,
            target_depth,
            max_subtasks
        )

        if not decomposition:
            return {
                "error": "Failed to decompose task",
                "task": task_description
            }

        return {
            "task": task_description,
            "total_tasks": len(decomposition),
            "decomposition_depth": _calc_depth(decomposition),
            "tasks_by_priority": _count_by_priority(decomposition),
            "tasks_by_status": {"pending": len(decomposition), "in_progress": 0, "completed": 0},
            "total_estimated_effort": _sum_effort(decomposition),
            "effort_by_priority": _effort_by_priority(decomposition),
            "critical_path_length": _critical_path(decomposition),
            "dependencies_count": _count_dependencies(decomposition),
            "top_level_tasks": min(max_subtasks, len([t for t in decomposition if t.get("depth", 0) == 0]))
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_task_structure(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    task_id: str,
    include_subtasks: bool = True
) -> Dict[str, Any]:
    """Get task structure summary."""
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        await cursor.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        )

        task = dict(await cursor.fetchone() or {})

        if include_subtasks:
            await cursor.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE parent_task_id = ?",
                (task_id,)
            )
            subtask_count = await cursor.fetchone()["count"]
            task["subtask_count"] = subtask_count

        await conn.close()

        return task if task else {"error": f"Task not found: {task_id}"}

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_dependency_graph(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    task_id: str
) -> Dict[str, Any]:
    """Get dependency graph summary."""
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        # Get dependencies
        await cursor.execute(
            """
            SELECT COUNT(*) as count FROM task_dependencies
            WHERE task_id = ? OR depends_on = ?
            """,
            (task_id, task_id)
        )

        dep_count = await cursor.fetchone()["count"]

        # Get blocking dependencies
        await cursor.execute(
            """
            SELECT COUNT(*) as count FROM task_dependencies
            WHERE task_id = ? AND dependency_type = 'blocks'
            """,
            (task_id,)
        )

        blocking_count = await cursor.fetchone()["count"]

        # Get blocked by
        await cursor.execute(
            """
            SELECT COUNT(*) as count FROM task_dependencies
            WHERE depends_on = ? AND dependency_type = 'blocks'
            """,
            (task_id,)
        )

        blocked_by_count = await cursor.fetchone()["count"]

        await conn.close()

        return {
            "task_id": task_id,
            "total_dependencies": dep_count,
            "blocking_count": blocking_count,
            "blocked_by_count": blocked_by_count,
            "critical_path_includes": blocked_by_count > 0
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def _simulate_decomposition(task_desc: str, depth: int, max_per_level: int) -> List[Dict]:
    """Simulate task decomposition."""
    # In production, use actual decomposition algorithm
    tasks = []

    # Level 0 - main task
    tasks.append({
        "id": f"task_0",
        "title": task_desc,
        "depth": 0,
        "priority": "high",
        "estimated_effort": 5.0
    })

    # Generate subtasks
    for level in range(1, min(depth, 3)):
        for i in range(min(max_per_level, 3)):
            tasks.append({
                "id": f"task_{level}_{i}",
                "title": f"Subtask {level}.{i}",
                "depth": level,
                "priority": ["high", "medium", "low"][i % 3],
                "estimated_effort": 2.0 - (level * 0.3)
            })

    return tasks


def _calc_depth(tasks: List[Dict]) -> int:
    """Calculate decomposition depth."""
    return max([t.get("depth", 0) for t in tasks]) if tasks else 0


def _count_by_priority(tasks: List[Dict]) -> Dict[str, int]:
    """Count tasks by priority."""
    counts = {}
    for task in tasks:
        priority = task.get("priority", "medium")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def _sum_effort(tasks: List[Dict]) -> float:
    """Sum estimated effort."""
    return sum(t.get("estimated_effort", 0) for t in tasks)


def _effort_by_priority(tasks: List[Dict]) -> Dict[str, float]:
    """Sum effort by priority."""
    efforts = {}
    for task in tasks:
        priority = task.get("priority", "medium")
        effort = task.get("estimated_effort", 0)
        efforts[priority] = efforts.get(priority, 0) + effort
    return efforts


def _critical_path(tasks: List[Dict]) -> int:
    """Calculate critical path length (simplified)."""
    return _calc_depth(tasks) + 1


def _count_dependencies(tasks: List[Dict]) -> int:
    """Count dependencies (simplified)."""
    return len([t for t in tasks if t.get("depth", 0) > 0])


if __name__ == "__main__":
    print("Task decomposition module - use via filesystem API")
