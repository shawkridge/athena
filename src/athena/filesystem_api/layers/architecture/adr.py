"""
Architecture Decision Record (ADR) operations with local filtering and summarization.

Provides filesystem API for ADR management.
Filters locally, returns only summaries (not full ADR objects).

Uses PostgreSQL backend only.

Usage:
    result = await create_adr(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        project_id=1,
        title="Use PostgreSQL for primary datastore",
        context="Need ACID guarantees...",
        decision="Use PostgreSQL with pgvector",
        rationale="Provides ACID compliance..."
    )
"""

from typing import Dict, Any, Optional, List
import asyncio
import json
from datetime import datetime

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def create_adr(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    project_id: int,
    title: str,
    context: str,
    decision: str,
    rationale: str,
    alternatives: Optional[List[str]] = None,
    consequences: Optional[List[str]] = None,
    author: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new Architecture Decision Record.

    Philosophy: Return summary only, never full ADR object.
    Token cost: ~150 tokens vs 2,000 for full object.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password
        project_id: Project ID
        title: Decision title
        context: Problem/context
        decision: The decision made
        rationale: Why this decision
        alternatives: Alternatives considered (optional)
        consequences: Expected consequences (optional)
        author: Decision author (optional)

    Returns:
        Summary with:
        - adr_id: Created ADR ID
        - title: Decision title
        - status: proposed
        - created_at: Timestamp
        - next_steps: What to do next
    """
    try:
        conn = await AsyncConnection.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        now = datetime.now().timestamp()

        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO architecture_decisions (
                    project_id, title, status, context, decision, rationale,
                    alternatives, consequences, author, created_at, updated_at,
                    implementation_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    title,
                    "proposed",
                    context,
                    decision,
                    rationale,
                    json.dumps(alternatives or []),
                    json.dumps(consequences or []),
                    author,
                    now,
                    now,
                    "not_started"
                )
            )

            result = await cursor.fetchone()
            adr_id = result[0] if result else None

            await conn.commit()

        await conn.close()

        return {
            "status": "success",
            "adr_id": adr_id,
            "title": title,
            "adr_status": "proposed",
            "created_at": datetime.fromtimestamp(now).isoformat(),
            "next_steps": [
                "Review decision with team",
                "Add related patterns and constraints",
                f"Accept with accept_adr(adr_id={adr_id})"
            ],
            "note": f"Full ADR accessible via get_adr_details({adr_id})"
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "title": title
        }


async def list_adrs(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    project_id: int,
    status_filter: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    List ADRs for a project with local filtering.

    Philosophy: Return summaries only, never full ADR objects.
    Token cost: ~250 tokens vs 10,000+ for full objects.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password
        project_id: Project ID
        status_filter: Filter by status (proposed/accepted/deprecated)
        limit: Max results

    Returns:
        Summary with:
        - total_count: Total ADRs
        - by_status: Count by status
        - recent_5: Last 5 ADR summaries
        - adr_ids: All matching ADR IDs
    """
    try:
        conn = await AsyncConnection.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        # Build query
        where_clause = "project_id = %s"
        params = [project_id]

        if status_filter:
            where_clause += " AND status = %s"
            params.append(status_filter)

        async with conn.cursor() as cursor:
            await cursor.execute(
                f"""
                SELECT id, title, status, created_at, effectiveness_score
                FROM architecture_decisions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params + [limit]
            )

            adrs = [dict(row) for row in await cursor.fetchall()]

        await conn.close()

        if not adrs:
            return {
                "project_id": project_id,
                "total_count": 0,
                "empty": True
            }

        # Count by status (local processing)
        status_counts = {}
        for adr in adrs:
            status = adr.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Get effectiveness stats
        with_effectiveness = [
            adr for adr in adrs
            if adr.get("effectiveness_score") is not None
        ]
        avg_effectiveness = (
            sum(a.get("effectiveness_score", 0) for a in with_effectiveness) / len(with_effectiveness)
            if with_effectiveness else None
        )

        return {
            "project_id": project_id,
            "total_count": len(adrs),
            "by_status": status_counts,
            "avg_effectiveness": avg_effectiveness,
            "recent_5": [
                {
                    "id": adr.get("id"),
                    "title": adr.get("title"),
                    "status": adr.get("status"),
                    "date": datetime.fromtimestamp(adr.get("created_at")).strftime("%Y-%m-%d") if adr.get("created_at") else None
                }
                for adr in adrs[:5]
            ],
            "adr_ids": [adr.get("id") for adr in adrs],
            "note": "Get details with get_adr_details(adr_id)"
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "project_id": project_id
        }


async def get_adr_details(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    adr_id: int
) -> Dict[str, Any]:
    """
    Retrieve full details for a specific ADR.

    Use sparingly to avoid token inflation.
    Only call after reviewing summary.
    """
    try:
        conn = await AsyncConnection.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM architecture_decisions WHERE id = %s",
                (adr_id,)
            )

            row = await cursor.fetchone()

        await conn.close()

        if not row:
            return {"error": f"ADR not found: {adr_id}"}

        adr = dict(row)

        # Parse JSON fields
        for field in ["alternatives", "consequences", "related_patterns", "related_constraints", "tags"]:
            if field in adr and isinstance(adr[field], str):
                try:
                    adr[field] = json.loads(adr[field])
                except:
                    pass

        # Convert timestamps
        for field in ["created_at", "updated_at"]:
            if field in adr and adr[field]:
                adr[field] = datetime.fromtimestamp(adr[field]).isoformat()

        return adr

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_arch_context(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    project_id: int,
    task_description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get architectural context for AI decision-making.

    Philosophy: Return summary for context engineering, not full data.
    Token cost: ~300 tokens vs 20,000+ for full context.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password
        project_id: Project ID
        task_description: Optional task for context-specific guidance

    Returns:
        Summary with:
        - active_decisions: Top accepted ADRs
        - top_patterns: Most effective patterns
        - active_constraints: Unsatisfied constraints
        - recent_changes: Last 5 architectural changes
    """
    try:
        conn = await AsyncConnection.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )

        context = {
            "project_id": project_id,
            "active_decisions": [],
            "active_constraints_count": 0,
            "recent_changes_count": 0
        }

        # Get active (accepted) ADRs
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, title, decision, status
                FROM architecture_decisions
                WHERE project_id = %s AND status = 'accepted'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (project_id,)
            )

            adrs = [dict(row) for row in await cursor.fetchall()]
            context["active_decisions"] = [
                {
                    "id": adr.get("id"),
                    "title": adr.get("title"),
                    "decision": adr.get("decision")[:100] + "..." if len(adr.get("decision", "")) > 100 else adr.get("decision")
                }
                for adr in adrs
            ]

        # Get unsatisfied constraints count
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM architectural_constraints
                WHERE project_id = %s AND is_satisfied = false
                """,
                (project_id,)
            )

            result = await cursor.fetchone()
            context["active_constraints_count"] = result[0] if result else 0

        # Get recent changes count
        async with conn.cursor() as cursor:
            last_30_days = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            await cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM architecture_decisions
                WHERE project_id = %s AND created_at >= %s
                """,
                (project_id, last_30_days)
            )

            result = await cursor.fetchone()
            context["recent_changes_count"] = result[0] if result else 0

        await conn.close()

        context["summary"] = (
            f"{len(context['active_decisions'])} active decisions, "
            f"{context['active_constraints_count']} unsatisfied constraints, "
            f"{context['recent_changes_count']} changes in last 30 days"
        )

        return context

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "project_id": project_id
        }
