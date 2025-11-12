"""
Find and retrieve procedures from procedural memory.

Returns procedure summaries and effectiveness metrics.
Never returns full procedure code.
"""

from typing import Dict, Any, Optional, List
try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def find_procedures(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    query: str,
    limit: int = 10,
    effectiveness_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Find applicable procedures by query.

    Returns: Procedure IDs, effectiveness scores, usage counts.
    Never: Full procedure code.

    Token cost: ~200 tokens vs 5,000 for full procedures.
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        await cursor.execute(
            """
            SELECT id, name, effectiveness_score, success_count, execution_count
            FROM procedures
            WHERE name ILIKE ? OR description ILIKE ?
            AND effectiveness_score >= ?
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", effectiveness_threshold, limit)
        )

        procedures = [dict(row) for row in await cursor.fetchall()]
        await conn.close()

        if not procedures:
            return {
                "query": query,
                "found_count": 0,
                "empty": True
            }

        effectiveness_scores = [p.get("effectiveness_score", 0) for p in procedures]

        return {
            "query": query,
            "found_count": len(procedures),
            "avg_effectiveness": sum(effectiveness_scores) / len(effectiveness_scores),
            "effectiveness_range": (min(effectiveness_scores), max(effectiveness_scores)),
            "total_executions": sum(p.get("execution_count", 0) for p in procedures),
            "total_successes": sum(p.get("success_count", 0) for p in procedures),
            "top_procedure_ids": [p.get("id") for p in procedures[:5]]
        }

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


async def get_procedure_summary(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    procedure_id: str
) -> Dict[str, Any]:
    """Get procedure summary (not full code)."""
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        await cursor.execute(
            """
            SELECT id, name, description, effectiveness_score,
                   execution_count, success_count, last_used
            FROM procedures
            WHERE id = ?
            """,
            (procedure_id,)
        )

        result = dict(await cursor.fetchone() or {})
        await conn.close()

        return result if result else {"error": f"Procedure not found: {procedure_id}"}

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


if __name__ == "__main__":
    print("Procedure find module - use via filesystem API")
