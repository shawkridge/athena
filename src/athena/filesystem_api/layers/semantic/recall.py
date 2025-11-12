"""
Recall semantic memories with local filtering and summarization.

Provides filesystem API for semantic memory retrieval.
Filters locally, returns only summaries (not full memory objects).

Usage:
    result = search_memories(
        db_path="~/.athena/memory.db",
        query="authentication",
        limit=100,
        confidence_threshold=0.7
    )
"""

from typing import Dict, Any, Optional, List
import sqlite3
import json


def search_memories(
    db_path: str,
    query: str,
    limit: int = 100,
    confidence_threshold: float = 0.7,
    domain_filter: Optional[str] = None,
    memory_type_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search semantic memories with local filtering.

    Philosophy: Return summaries only, never full memory objects.
    Token cost: ~200 tokens vs 15,000 for full objects.

    Args:
        db_path: Path to memory database
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
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query
        where_clauses = ["1=1"]
        params = []

        # Search in content (would use FTS in production)
        where_clauses.append("(content LIKE ? OR tags LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

        if domain_filter:
            where_clauses.append("domain = ?")
            params.append(domain_filter)

        if memory_type_filter:
            where_clauses.append("type = ?")
            params.append(memory_type_filter)

        where_clause = " AND ".join(where_clauses)

        # Get all matches (will filter locally)
        cursor.execute(
            f"""
            SELECT id, type, domain, confidence, usefulness_score
            FROM semantic_memories
            WHERE {where_clause}
            LIMIT ?
            """,
            params + [limit]
        )

        all_memories = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not all_memories:
            return {
                "query": query,
                "total_results": 0,
                "high_confidence_count": 0,
                "empty": True
            }

        # Filter by confidence (local processing)
        high_conf = [
            m for m in all_memories
            if m.get("confidence", 0) >= confidence_threshold
        ]

        # Get statistics
        confidences = [m.get("confidence", 0) for m in all_memories]
        usefulness_scores = [m.get("usefulness_score", 0) for m in all_memories]

        # Count by domain
        domain_dist = {}
        for mem in high_conf:
            domain = mem.get("domain", "unknown")
            domain_dist[domain] = domain_dist.get(domain, 0) + 1

        # Count by type
        type_dist = {}
        for mem in high_conf:
            mtype = mem.get("type", "unknown")
            type_dist[mtype] = type_dist.get(mtype, 0) + 1

        return {
            "query": query,
            "total_results": len(all_memories),
            "high_confidence_count": len(high_conf),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "confidence_range": (min(confidences), max(confidences)) if confidences else (None, None),
            "avg_usefulness": sum(usefulness_scores) / len(usefulness_scores) if usefulness_scores else 0,
            "domain_distribution": domain_dist,
            "type_distribution": type_dist,
            "top_5_ids": [m.get("id") for m in high_conf[:5]],
            "percentiles": {
                "p10": sorted(confidences)[len(confidences)//10] if confidences else None,
                "p50": sorted(confidences)[len(confidences)//2] if confidences else None,
                "p90": sorted(confidences)[len(confidences)*9//10] if confidences else None
            }
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "query": query
        }


def get_memory_details(
    db_path: str,
    memory_id: str
) -> Dict[str, Any]:
    """
    Retrieve full details for a specific memory.

    Use sparingly to avoid token inflation.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM semantic_memories WHERE id = ?",
            (memory_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"error": f"Memory not found: {memory_id}"}

        memory = dict(row)

        # Parse JSON fields
        for field in ["tags", "relationships"]:
            if field in memory and isinstance(memory[field], str):
                try:
                    memory[field] = json.loads(memory[field])
                except:
                    pass

        return memory

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def get_related_memories(
    db_path: str,
    memory_id: str,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Get summaries of memories related to a specific one.

    Returns relationship graph, not full memory objects.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get relationships for this memory
        cursor.execute(
            """
            SELECT target_id, relationship_type
            FROM memory_relationships
            WHERE source_id = ? OR target_id = ?
            LIMIT ?
            """,
            (memory_id, memory_id, limit)
        )

        relationships = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not relationships:
            return {
                "memory_id": memory_id,
                "related_count": 0,
                "relationships": []
            }

        return {
            "memory_id": memory_id,
            "related_count": len(relationships),
            "relationship_types": _count_rel_types(relationships),
            "related_ids": [r.get("target_id") for r in relationships],
            "relationships": relationships
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def _count_rel_types(rels: List[Dict]) -> Dict[str, int]:
    """Count relationship types."""
    counts = {}
    for rel in rels:
        rtype = rel.get("relationship_type", "unknown")
        counts[rtype] = counts.get(rtype, 0) + 1
    return counts
