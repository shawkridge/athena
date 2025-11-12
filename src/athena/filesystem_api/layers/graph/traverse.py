"""
Knowledge graph traversal with local processing.

Returns summaries: entity counts, relation counts, community metrics.
Never returns full entity/relation objects.
"""

from typing import Dict, Any, Optional, List
try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def search_entities(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    query: str,
    limit: int = 100,
    max_depth: int = 2
) -> Dict[str, Any]:
    """
    Search entities in knowledge graph with summary results.

    Args:
        db_path: Path to database
        query: Entity search query
        limit: Max entities to return
        max_depth: Max depth for relationship traversal

    Returns:
        Summary with entity counts, relation counts, connectivity metrics
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        # Search entities
        await cursor.execute(
            """
            SELECT id, type, name, confidence
            FROM graph_entities
            WHERE name ILIKE ? OR description ILIKE ?
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit)
        )

        entities = [dict(row) for row in await cursor.fetchall()]

        if not entities:
            return {
                "query": query,
                "total_entities": 0,
                "empty": True
            }

        entity_ids = [e["id"] for e in entities]

        # Count relations for these entities
        placeholders = ",".join("?" * len(entity_ids))
        await cursor.execute(
            f"""
            SELECT COUNT(*) as relation_count
            FROM graph_relations
            WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
            """,
            entity_ids + entity_ids
        )

        relation_count = await cursor.fetchone()["relation_count"]

        # Get relation type distribution
        await cursor.execute(
            f"""
            SELECT relation_type, COUNT(*) as count
            FROM graph_relations
            WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
            GROUP BY relation_type
            """,
            entity_ids + entity_ids
        )

        rel_dist = {row["relation_type"]: row["count"] for row in await cursor.fetchall()}

        # Entity type distribution
        type_dist = {}
        for entity in entities:
            etype = entity.get("type", "unknown")
            type_dist[etype] = type_dist.get(etype, 0) + 1

        await conn.close()

        return {
            "query": query,
            "total_entities": len(entities),
            "entity_type_distribution": type_dist,
            "total_relations": relation_count,
            "relation_type_distribution": rel_dist,
            "avg_relations_per_entity": relation_count / len(entities) if entities else 0,
            "avg_confidence": sum(e.get("confidence", 0) for e in entities) / len(entities) if entities else 0,
            "top_entity_ids": [e["id"] for e in entities[:5]]
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_entity_neighbors(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    entity_id: str,
    relation_type: Optional[str] = None,
    depth: int = 1
) -> Dict[str, Any]:
    """
    Get neighbor entities and relation summary.

    Returns counts and types, not full entities.
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        where_clause = "(source_id = ? OR target_id = %s)"
        params = [entity_id, entity_id]

        if relation_type:
            where_clause += " AND relation_type = ?"
            params.append(relation_type)

        await cursor.execute(
            f"SELECT COUNT(*) as count FROM graph_relations WHERE {where_clause}",
            params
        )

        total_relations = await cursor.fetchone()["count"]

        # Get relation type distribution
        await cursor.execute(
            f"""
            SELECT relation_type, COUNT(*) as count
            FROM graph_relations
            WHERE {where_clause}
            GROUP BY relation_type
            """,
            params
        )

        rel_dist = {row["relation_type"]: row["count"] for row in await cursor.fetchall()}

        # Get neighbor entity types
        await cursor.execute(
            f"""
            SELECT DISTINCT e.type, COUNT(*) as count
            FROM graph_entities e
            JOIN graph_relations r ON (r.target_id = e.id OR r.source_id = e.id)
            WHERE {where_clause}
            GROUP BY e.type
            """,
            params
        )

        neighbor_types = {row["type"]: row["count"] for row in await cursor.fetchall()}

        await conn.close()

        return {
            "entity_id": entity_id,
            "total_neighbors": total_relations,
            "relation_type_distribution": rel_dist,
            "neighbor_type_distribution": neighbor_types,
            "connectivity_score": min(1.0, total_relations / 10.0)  # 10+ relations = 1.0
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


if __name__ == "__main__":
    print("Graph traversal module - use via filesystem API")
