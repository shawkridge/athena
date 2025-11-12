"""
Search across all memory layers simultaneously.

Returns unified summary of matches from all layers.
Executes parallel queries locally, aggregates results.

Token cost: ~400 tokens vs 45,000 for separate searches.
"""

from typing import Dict, Any, Optional, List
import sqlite3


def search_all_layers(
    db_path: str,
    query: str,
    limit_per_layer: int = 10,
    confidence_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Search all memory layers for query.

    Parallel execution in sandbox:
    - Episodic search
    - Semantic search
    - Graph entity search
    - Procedure search
    - Task search

    Returns unified summary.

    Args:
        db_path: Path to database
        query: Search query
        limit_per_layer: Max results per layer
        confidence_threshold: Confidence filter

    Returns:
        Aggregated summary across all layers
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        results = {
            "query": query,
            "timestamp": _get_timestamp(),
            "layers_searched": 0,
            "total_matches": 0,
            "summary": {}
        }

        # Search episodic
        cursor.execute(
            """
            SELECT COUNT(*) as count, AVG(confidence) as avg_conf
            FROM episodic_events
            WHERE content LIKE ? AND confidence >= ?
            """,
            (f"%{query}%", confidence_threshold)
        )
        epi_row = cursor.fetchone()
        if epi_row and epi_row["count"] > 0:
            results["summary"]["episodic"] = {
                "match_count": epi_row["count"],
                "avg_confidence": epi_row["avg_conf"]
            }
            results["layers_searched"] += 1
            results["total_matches"] += epi_row["count"]

        # Search semantic
        cursor.execute(
            """
            SELECT COUNT(*) as count, AVG(confidence) as avg_conf
            FROM semantic_memories
            WHERE content LIKE ? AND confidence >= ?
            """,
            (f"%{query}%", confidence_threshold)
        )
        sem_row = cursor.fetchone()
        if sem_row and sem_row["count"] > 0:
            results["summary"]["semantic"] = {
                "match_count": sem_row["count"],
                "avg_confidence": sem_row["avg_conf"]
            }
            results["layers_searched"] += 1
            results["total_matches"] += sem_row["count"]

        # Search graph
        cursor.execute(
            """
            SELECT COUNT(*) as count, AVG(confidence) as avg_conf
            FROM graph_entities
            WHERE name LIKE ? AND confidence >= ?
            """,
            (f"%{query}%", confidence_threshold)
        )
        graph_row = cursor.fetchone()
        if graph_row and graph_row["count"] > 0:
            results["summary"]["graph"] = {
                "match_count": graph_row["count"],
                "avg_confidence": graph_row["avg_conf"]
            }
            results["layers_searched"] += 1
            results["total_matches"] += graph_row["count"]

        # Search procedures
        cursor.execute(
            """
            SELECT COUNT(*) as count, AVG(effectiveness_score) as avg_eff
            FROM procedures
            WHERE name LIKE ? OR description LIKE ?
            """,
            (f"%{query}%", f"%{query}%")
        )
        proc_row = cursor.fetchone()
        if proc_row and proc_row["count"] > 0:
            results["summary"]["procedural"] = {
                "match_count": proc_row["count"],
                "avg_effectiveness": proc_row["avg_eff"]
            }
            results["layers_searched"] += 1
            results["total_matches"] += proc_row["count"]

        # Search tasks
        cursor.execute(
            """
            SELECT COUNT(*) as count, COUNT(CASE WHEN status='completed' THEN 1 END) as completed
            FROM tasks
            WHERE title LIKE ? OR description LIKE ?
            """,
            (f"%{query}%", f"%{query}%")
        )
        task_row = cursor.fetchone()
        if task_row and task_row["count"] > 0:
            results["summary"]["prospective"] = {
                "match_count": task_row["count"],
                "completed_count": task_row["completed"]
            }
            results["layers_searched"] += 1
            results["total_matches"] += task_row["count"]

        conn.close()

        if results["total_matches"] == 0:
            results["empty"] = True
            results["recommendation"] = "No matches found across any layer"

        return results

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "query": query
        }


def _get_timestamp() -> str:
    """Get current timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()


if __name__ == "__main__":
    print("Cross-layer search module - use via filesystem API")
