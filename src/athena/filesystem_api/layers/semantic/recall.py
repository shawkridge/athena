"""
Recall semantic memories with local filtering and summarization.

Provides filesystem API for semantic memory retrieval.
Filters locally, returns only summaries (not full memory objects).

Uses PostgreSQL backend only.

Usage:
    result = await search_memories(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
        query="authentication",
        limit=100,
        confidence_threshold=0.7
    )
"""

from typing import Dict, Any, Optional, List

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def search_memories(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    query: str,
    limit: int = 100,
    confidence_threshold: float = 0.7,
    domain_filter: Optional[str] = None,
    memory_type_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search semantic memories with local filtering.

    Philosophy: Return summaries only, never full memory objects.
    Token cost: ~200 tokens vs 15,000 for full objects.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: Database user
        password: Database password
        query: Search query
        limit: Max results
        confidence_threshold: Filter by confidence >= this
        domain_filter: Filter by domain (e.g., "authentication", "architecture")
        memory_type_filter: Filter by type (fact, concept, procedure, etc)

    Returns:
        Summary with:
        - total_results: Total matching memories
        - high_confidence_count: Above threshold
        - avg_confidence: Average confidence
        - domain_distribution: Count by domain
        - top_5_ids: Best matching memory IDs
    """
    try:
        conn = await AsyncConnection.connect(
            f"dbname={dbname} user={user} password={password} host={host} port={port}"
        )

        # Build query using semantic_memories table (replacement for semantic_memories)
        where_clauses = ["1=1"]
        params = []

        # Search in content using text search
        where_clauses.append("(content ILIKE %s OR tags::text ILIKE %s)")
        params.extend([f"%{query}%", f"%{query}%"])

        if domain_filter:
            where_clauses.append("domain = %s")
            params.append(domain_filter)

        if memory_type_filter:
            where_clauses.append("memory_type = %s")
            params.append(memory_type_filter)

        where_clause = " AND ".join(where_clauses)

        # Get all matches (will filter locally)
        async with conn.cursor() as cursor:
            await cursor.execute(
                f"""
                SELECT id, memory_type, domain, confidence, usefulness_score
                FROM semantic_memories
                WHERE {where_clause}
                LIMIT %s
                """,
                params + [limit],
            )

            all_memories = [dict(row) for row in await cursor.fetchall()]

        await conn.close()

        if not all_memories:
            return {"query": query, "total_results": 0, "high_confidence_count": 0, "empty": True}

        # Filter by confidence (local processing)
        high_conf = [m for m in all_memories if m.get("confidence", 0) >= confidence_threshold]

        # Get statistics
        confidences = [m.get("confidence", 0) for m in all_memories]
        usefulness_scores = [m.get("usefulness_score", 0) for m in all_memories]

        # Count by domain
        domain_dist = {}
        for mem in high_conf:
            domain = mem.get("domain", "unknown")
            domain_dist[domain] = domain_dist.get(domain, 0) + 1

        # Count by type (memory_type in semantic_memories table)
        type_dist = {}
        for mem in high_conf:
            mtype = mem.get("memory_type", "unknown")
            type_dist[mtype] = type_dist.get(mtype, 0) + 1

        return {
            "query": query,
            "total_results": len(all_memories),
            "high_confidence_count": len(high_conf),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "confidence_range": (
                (min(confidences), max(confidences)) if confidences else (None, None)
            ),
            "avg_usefulness": (
                sum(usefulness_scores) / len(usefulness_scores) if usefulness_scores else 0
            ),
            "domain_distribution": domain_dist,
            "memory_type_distribution": type_dist,
            "top_5_ids": [m.get("id") for m in high_conf[:5]],
            "percentiles": {
                "p10": sorted(confidences)[len(confidences) // 10] if confidences else None,
                "p50": sorted(confidences)[len(confidences) // 2] if confidences else None,
                "p90": sorted(confidences)[len(confidences) * 9 // 10] if confidences else None,
            },
        }

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__, "query": query}


def _count_rel_types(rels: List[Dict]) -> Dict[str, int]:
    """Count relationship types."""
    counts = {}
    for rel in rels:
        rtype = rel.get("relationship_type", "unknown")
        counts[rtype] = counts.get(rtype, 0) + 1
    return counts
