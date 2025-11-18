"""
System health check and diagnostics.

Returns comprehensive health metrics across all layers.
No sensitive data exposed, only metrics and anomaly flags.
"""

from typing import Dict, Any

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")
from datetime import datetime


async def get_system_health(
    host: str, port: int, dbname: str, user: str, password: str, include_anomalies: bool = True
) -> Dict[str, Any]:
    """
    Get comprehensive system health check.

    Returns metrics on:
    - Memory layer status
    - Data quality indicators
    - Anomalies detected
    - Performance indicators
    - Capacity usage

    Token cost: ~300 tokens vs 15,000 for detailed diagnostics.

    Args:
        db_path: Path to database
        include_anomalies: Include anomaly detection

    Returns:
        Health dashboard summary
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "layers": {},
            "metrics": {},
            "anomalies": [] if include_anomalies else None,
        }

        # Episodic health
        await cursor.execute(
            """
            SELECT COUNT(*) as count,
                   AVG(confidence) as avg_conf,
                   COUNT(CASE WHEN confidence < 0.5 THEN 1 END) as low_conf_count
            FROM episodic_events
        """
        )
        epi = await cursor.fetchone()
        health["layers"]["episodic"] = {
            "event_count": epi["count"],
            "avg_confidence": epi["avg_conf"],
            "low_confidence_count": epi["low_conf_count"],
            "status": "good" if epi["avg_conf"] and epi["avg_conf"] > 0.7 else "warning",
        }

        # Semantic health
        await cursor.execute(
            """
            SELECT COUNT(*) as count,
                   AVG(confidence) as avg_conf,
                   AVG(usefulness_score) as avg_usefulness
            FROM semantic_memories
        """
        )
        sem = await cursor.fetchone()
        health["layers"]["semantic"] = {
            "memory_count": sem["count"],
            "avg_confidence": sem["avg_conf"],
            "avg_usefulness": sem["avg_usefulness"],
            "status": "good" if sem["avg_conf"] and sem["avg_conf"] > 0.7 else "warning",
        }

        # Graph health
        await cursor.execute(
            """
            SELECT COUNT(*) as entity_count FROM graph_entities
        """
        )
        await cursor.execute(
            """
            SELECT COUNT(*) as relation_count FROM graph_relations
        """
        )
        graph_entities = await cursor.fetchone()["entity_count"]
        graph_relations = await cursor.fetchone()["relation_count"]

        health["layers"]["graph"] = {
            "entity_count": graph_entities,
            "relation_count": graph_relations,
            "connectivity": graph_relations / max(1, graph_entities) if graph_entities > 0 else 0,
        }

        # Task health
        await cursor.execute(
            """
            SELECT status, COUNT(*) as count
            FROM tasks
            GROUP BY status
        """
        )
        task_dist = {row["status"]: row["count"] for row in await cursor.fetchall()}
        health["layers"]["prospective"] = {
            "status_distribution": task_dist,
            "total_tasks": sum(task_dist.values()),
        }

        # Procedure health
        await cursor.execute(
            """
            SELECT COUNT(*) as count,
                   AVG(effectiveness_score) as avg_eff
            FROM procedures
        """
        )
        proc = await cursor.fetchone()
        health["layers"]["procedural"] = {
            "procedure_count": proc["count"],
            "avg_effectiveness": proc["avg_eff"],
            "status": "good" if proc["avg_eff"] and proc["avg_eff"] > 0.7 else "fair",
        }

        # Metrics
        await cursor.execute(
            "SELECT COUNT(*) as count FROM episodic_events WHERE timestamp > datetime('now', '-24 hours')"
        )
        recent_events = await cursor.fetchone()["count"]

        health["metrics"] = {
            "total_data_points": (epi["count"] or 0) + (sem["count"] or 0),
            "recent_activity_24h": recent_events,
            "total_procedures": proc["count"],
            "graph_density": health["layers"]["graph"]["connectivity"],
        }

        # Anomalies
        if include_anomalies:
            anomalies = []

            if epi["low_conf_count"] and epi["low_conf_count"] > (epi["count"] * 0.3):
                anomalies.append(
                    {
                        "type": "low_episodic_confidence",
                        "severity": "warning",
                        "description": f"{epi['low_conf_count']} events with low confidence",
                    }
                )

            if task_dist.get("blocked", 0) > (sum(task_dist.values()) * 0.2):
                anomalies.append(
                    {
                        "type": "high_blocked_tasks",
                        "severity": "warning",
                        "description": "High number of blocked tasks",
                    }
                )

            if health["metrics"]["graph_density"] < 0.1:
                anomalies.append(
                    {
                        "type": "low_graph_connectivity",
                        "severity": "info",
                        "description": "Knowledge graph connectivity is low",
                    }
                )

            health["anomalies"] = anomalies

        # Overall status
        warning_count = len([l for l in health["layers"].values() if l.get("status") == "warning"])
        if warning_count > 2:
            health["status"] = "warning"
        elif any(l.get("status") == "critical" for l in health["layers"].values()):
            health["status"] = "critical"

        await conn.close()

        return health

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__, "status": "error"}


if __name__ == "__main__":
    print("Health check module - use via filesystem API")
