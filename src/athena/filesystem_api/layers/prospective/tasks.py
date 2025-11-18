"""
Task management and retrieval.

Returns task summaries, counts, and metrics.
Never returns full task data.
"""

from typing import Dict, Any, Optional

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def list_tasks(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    List tasks with filtering and summaries.

    Returns: Counts, distributions, top IDs.
    Never: Full task objects.

    Token cost: ~200 tokens vs 12,000 for full tasks.
    """
    try:
        conn = await AsyncConnection.connect(
            host, port=port, dbname=dbname, user=user, password=password
        )
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if status_filter:
            where_clauses.append("status = %s")
            params.append(status_filter)

        if priority_filter:
            where_clauses.append("priority = %s")
            params.append(priority_filter)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        await cursor.execute(
            f"""
            SELECT id, status, priority, estimated_effort
            FROM tasks
            WHERE {where_clause}
            LIMIT %s
            """,
            params + [limit],
        )

        tasks = [dict(row) for row in await cursor.fetchall()]
        await conn.close()

        if not tasks:
            return {"found_count": 0, "empty": True}

        # Calculate summaries
        status_dist = {}
        priority_dist = {}
        efforts = []

        for task in tasks:
            status = task.get("status", "unknown")
            status_dist[status] = status_dist.get(status, 0) + 1

            priority = task.get("priority", "medium")
            priority_dist[priority] = priority_dist.get(priority, 0) + 1

            if task.get("estimated_effort"):
                efforts.append(task.get("estimated_effort"))

        return {
            "found_count": len(tasks),
            "status_distribution": status_dist,
            "priority_distribution": priority_dist,
            "total_estimated_effort": sum(efforts) if efforts else 0,
            "top_task_ids": [t.get("id") for t in tasks[:5]],
        }

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


async def get_task_summary(
    host: str, port: int, dbname: str, user: str, password: str, task_id: str
) -> Dict[str, Any]:
    """Get task summary (not full data)."""
    try:
        conn = await AsyncConnection.connect(
            host, port=port, dbname=dbname, user=user, password=password
        )
        cursor = conn.cursor()

        await cursor.execute(
            """
            SELECT id, title, status, priority, estimated_effort, deadline
            FROM tasks
            WHERE id = %s
            """,
            (task_id,),
        )

        result = dict(await cursor.fetchone() or {})
        await conn.close()

        return result if result else {"error": f"Task not found: {task_id}"}

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


if __name__ == "__main__":
    print("Task management module - use via filesystem API")
