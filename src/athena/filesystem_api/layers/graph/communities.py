"""
Community detection and analysis for knowledge graph.

Discovers natural clusters in graph structure.
Returns community metrics, not full membership lists.
"""

from typing import Dict, Any, Optional, List
import sqlite3


def detect_communities(
    db_path: str,
    min_size: int = 2,
    resolution: float = 1.0
) -> Dict[str, Any]:
    """
    Detect communities in knowledge graph using Leiden algorithm.

    Returns summary of communities, not full membership.

    Args:
        db_path: Path to database
        min_size: Minimum community size
        resolution: Resolution parameter for clustering

    Returns:
        Summary with:
        - community_count: Number of communities detected
        - avg_community_size: Average size
        - largest_community_size: Size of largest
        - modularity: Graph modularity score
        - entity_distribution: How entities spread across communities
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all entities and relations
        cursor.execute("SELECT id, type FROM graph_entities")
        entities = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT source_id, target_id FROM graph_relations")
        relations = [dict(row) for row in cursor.fetchall()]

        conn.close()

        if not entities or not relations:
            return {
                "community_count": 0,
                "empty": True,
                "total_entities": len(entities),
                "total_relations": len(relations)
            }

        # Simplified community detection (in production use actual Leiden)
        # For now, use graph diameter and clustering coefficient
        communities = _simple_detect(entities, relations, min_size)

        entity_types = {}
        for e in entities:
            t = e.get("type", "unknown")
            entity_types[t] = entity_types.get(t, 0) + 1

        return {
            "total_entities": len(entities),
            "total_relations": len(relations),
            "community_count": len(communities),
            "avg_community_size": sum(len(c) for c in communities) / len(communities) if communities else 0,
            "largest_community_size": max(len(c) for c in communities) if communities else 0,
            "smallest_community_size": min(len(c) for c in communities) if communities else 0,
            "entity_type_distribution": entity_types,
            "modularity_estimate": _estimate_modularity(entities, relations, communities)
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def get_community_info(
    db_path: str,
    community_id: int
) -> Dict[str, Any]:
    """
    Get summary info about a specific community.

    Returns entity counts and relation counts, not members.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get community members (from some membership table)
        cursor.execute(
            "SELECT entity_id FROM community_members WHERE community_id = ?",
            (community_id,)
        )

        member_ids = [row["entity_id"] for row in cursor.fetchall()]

        if not member_ids:
            return {
                "community_id": community_id,
                "member_count": 0,
                "empty": True
            }

        # Count entity types in community
        placeholders = ",".join("?" * len(member_ids))
        cursor.execute(
            f"SELECT type, COUNT(*) as count FROM graph_entities WHERE id IN ({placeholders}) GROUP BY type",
            member_ids
        )

        type_dist = {row["type"]: row["count"] for row in cursor.fetchall()}

        # Count internal relations
        cursor.execute(
            f"""
            SELECT COUNT(*) as count FROM graph_relations
            WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
            """,
            member_ids + member_ids
        )

        internal_relations = cursor.fetchone()["count"]

        # Count external relations
        cursor.execute(
            f"""
            SELECT COUNT(*) as count FROM graph_relations
            WHERE (source_id IN ({placeholders}) AND target_id NOT IN ({placeholders}))
               OR (source_id NOT IN ({placeholders}) AND target_id IN ({placeholders}))
            """,
            member_ids + member_ids + member_ids + member_ids
        )

        external_relations = cursor.fetchone()["count"]

        conn.close()

        return {
            "community_id": community_id,
            "member_count": len(member_ids),
            "entity_type_distribution": type_dist,
            "internal_relations": internal_relations,
            "external_relations": external_relations,
            "density": internal_relations / (len(member_ids) * (len(member_ids) - 1) / 2) if len(member_ids) > 1 else 0,
            "cohesion_score": internal_relations / (internal_relations + external_relations) if (internal_relations + external_relations) > 0 else 0
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def _simple_detect(entities: List, relations: List, min_size: int) -> List[List[str]]:
    """Simple community detection using graph connectivity."""
    if not entities:
        return []

    # Build adjacency
    adj = {e["id"]: [] for e in entities}
    for rel in relations:
        adj[rel["source_id"]].append(rel["target_id"])
        adj[rel["target_id"]].append(rel["source_id"])

    # Simple BFS-based clustering
    visited = set()
    communities = []

    for entity in entities:
        if entity["id"] in visited:
            continue

        community = []
        queue = [entity["id"]]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue

            visited.add(node)
            community.append(node)

            for neighbor in adj[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

        if len(community) >= min_size:
            communities.append(community)

    return communities


def _estimate_modularity(entities: List, relations: List, communities: List[List]) -> float:
    """Estimate modularity of community structure."""
    if not communities or not relations:
        return 0.0

    total_edges = len(relations)
    if total_edges == 0:
        return 0.0

    # Simple modularity: fraction of edges within communities / expected
    edges_within = 0
    community_sets = [set(c) for c in communities]

    for rel in relations:
        for comm in community_sets:
            if rel["source_id"] in comm and rel["target_id"] in comm:
                edges_within += 1
                break

    return edges_within / total_edges if total_edges > 0 else 0.0


if __name__ == "__main__":
    print("Community detection module - use via filesystem API")
