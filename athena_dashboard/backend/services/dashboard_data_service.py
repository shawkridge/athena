"""
Dashboard Data Service

Provides unified data access for all dashboard endpoints.
Queries the Athena memory database and aggregates information.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DashboardDataService:
    """Service for dashboard data access."""

    def __init__(self, data_loader):
        """Initialize with data loader."""
        self.data_loader = data_loader

    # ========================================================================
    # EPISODIC MEMORY
    # ========================================================================

    async def get_episodic_events(
        self,
        limit: int = 100,
        offset: int = 0,
        sort: str = "timestamp",
        order: str = "desc",
    ) -> Dict[str, Any]:
        """Get episodic events with pagination."""
        try:
            # Query episodic_events table
            query = f"""
                SELECT * FROM episodic_events
                ORDER BY {sort} {order.upper()}
                LIMIT {limit} OFFSET {offset}
            """
            events = self.data_loader._query(text(query))

            # Get total count
            count_query = "SELECT COUNT(*) as count FROM episodic_events"
            count_result = self.data_loader._query(text(count_query))
            total = count_result[0]['count'] if count_result else 0

            return {
                "events": [dict(e) for e in events],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"Error fetching episodic events: {e}")
            return {"events": [], "total": 0, "limit": limit, "offset": offset}

    async def get_episodic_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        try:
            query = """
                SELECT
                    COUNT(*) as total_events,
                    MIN(created_at) as oldest_event,
                    MAX(created_at) as newest_event
                FROM episodic_events
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "total_events": stats.get("total_events", 0),
                "oldest_event": stats.get("oldest_event"),
                "newest_event": stats.get("newest_event"),
                "events_per_hour": 0,  # TODO: Calculate from timeline
                "event_types": {},  # TODO: Aggregate by type
            }
        except Exception as e:
            logger.error(f"Error fetching episodic stats: {e}")
            return {
                "total_events": 0,
                "events_per_hour": 0,
                "event_types": {},
            }

    # ========================================================================
    # SEMANTIC MEMORY
    # ========================================================================

    async def get_semantic_memories(
        self,
        limit: int = 50,
        offset: int = 0,
        sort: str = "relevance",
    ) -> Dict[str, Any]:
        """Get semantic memories."""
        try:
            query = f"""
                SELECT * FROM semantic_memories
                ORDER BY {sort} DESC
                LIMIT {limit} OFFSET {offset}
            """
            memories = self.data_loader._query(text(query))

            count_query = "SELECT COUNT(*) as count FROM semantic_memories"
            count_result = self.data_loader._query(text(count_query))
            total = count_result[0]['count'] if count_result else 0

            return {
                "memories": [dict(m) for m in memories],
                "total": total,
            }
        except Exception as e:
            logger.error(f"Error fetching semantic memories: {e}")
            return {"memories": [], "total": 0}

    async def get_semantic_stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics."""
        try:
            query = """
                SELECT
                    COUNT(*) as total_memories,
                    AVG(quality_score) as avg_quality
                FROM semantic_memories
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "total_memories": stats.get("total_memories", 0),
                "domains": 0,  # TODO: Count distinct domains
                "avg_quality": float(stats.get("avg_quality", 0.0)),
                "search_hit_rate": 0.0,  # TODO: Calculate
            }
        except Exception as e:
            logger.error(f"Error fetching semantic stats: {e}")
            return {
                "total_memories": 0,
                "domains": 0,
                "avg_quality": 0.0,
                "search_hit_rate": 0.0,
            }

    # ========================================================================
    # PROCEDURAL MEMORY
    # ========================================================================

    async def get_procedural_skills(
        self,
        limit: int = 100,
        offset: int = 0,
        sort: str = "effectiveness",
    ) -> Dict[str, Any]:
        """Get procedural skills."""
        try:
            query = f"""
                SELECT * FROM procedural_skills
                ORDER BY {sort} DESC
                LIMIT {limit} OFFSET {offset}
            """
            skills = self.data_loader._query(text(query))

            count_query = "SELECT COUNT(*) as count FROM procedural_skills"
            count_result = self.data_loader._query(text(count_query))
            total = count_result[0]['count'] if count_result else 0

            return {
                "skills": [dict(s) for s in skills],
                "total": total,
            }
        except Exception as e:
            logger.error(f"Error fetching procedural skills: {e}")
            return {"skills": [], "total": 0}

    async def get_procedural_stats(self) -> Dict[str, Any]:
        """Get procedural memory statistics."""
        try:
            query = """
                SELECT
                    COUNT(*) as total_skills,
                    AVG(effectiveness_score) as avg_effectiveness,
                    AVG(success_rate) as avg_success
                FROM procedural_skills
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "total_skills": stats.get("total_skills", 0),
                "avg_effectiveness": float(stats.get("avg_effectiveness", 0.0)),
                "usage_trend": [],  # TODO: Calculate trend
                "success_rate": float(stats.get("avg_success", 0.0)),
            }
        except Exception as e:
            logger.error(f"Error fetching procedural stats: {e}")
            return {
                "total_skills": 0,
                "avg_effectiveness": 0.0,
                "usage_trend": [],
                "success_rate": 0.0,
            }

    # ========================================================================
    # PROSPECTIVE MEMORY
    # ========================================================================

    async def get_prospective_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get prospective tasks."""
        try:
            query = "SELECT * FROM prospective_tasks"
            params = []

            if status:
                query += " WHERE status = %s"
                params.append(status)

            query += f" LIMIT {limit}"

            tasks = self.data_loader._query(text(query), params) if params else self.data_loader._query(text(query))

            return {
                "tasks": [dict(t) for t in tasks],
                "total": len(tasks),
            }
        except Exception as e:
            logger.error(f"Error fetching prospective tasks: {e}")
            return {"tasks": [], "total": 0}

    async def get_prospective_stats(self) -> Dict[str, Any]:
        """Get prospective memory statistics."""
        try:
            query = """
                SELECT
                    COUNT(CASE WHEN type='goal' THEN 1 END) as active_goals,
                    COUNT(CASE WHEN type='task' THEN 1 END) as total_tasks,
                    COUNT(CASE WHEN status='completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN due_date < NOW() AND status != 'completed' THEN 1 END) as overdue
                FROM prospective_tasks
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            total_tasks = stats.get("total_tasks", 0)
            completed = stats.get("completed", 0)

            return {
                "active_goals": stats.get("active_goals", 0),
                "total_tasks": total_tasks,
                "completion_rate": (completed / total_tasks * 100) if total_tasks > 0 else 0.0,
                "overdue_tasks": stats.get("overdue", 0),
            }
        except Exception as e:
            logger.error(f"Error fetching prospective stats: {e}")
            return {
                "active_goals": 0,
                "total_tasks": 0,
                "completion_rate": 0.0,
                "overdue_tasks": 0,
            }

    # ========================================================================
    # KNOWLEDGE GRAPH
    # ========================================================================

    async def get_graph_entities(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get knowledge graph entities."""
        try:
            query = f"""
                SELECT * FROM knowledge_graph_entities
                LIMIT {limit} OFFSET {offset}
            """
            entities = self.data_loader._query(text(query))

            count_query = "SELECT COUNT(*) as count FROM knowledge_graph_entities"
            count_result = self.data_loader._query(text(count_query))
            total = count_result[0]['count'] if count_result else 0

            return {
                "entities": [dict(e) for e in entities],
                "total": total,
            }
        except Exception as e:
            logger.error(f"Error fetching graph entities: {e}")
            return {"entities": [], "total": 0}

    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        try:
            query = """
                SELECT
                    (SELECT COUNT(*) FROM knowledge_graph_entities) as total_entities,
                    (SELECT COUNT(*) FROM knowledge_graph_relationships) as total_relationships
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "total_entities": stats.get("total_entities", 0),
                "total_relationships": stats.get("total_relationships", 0),
                "communities": 0,  # TODO: Query community detection results
                "density": 0.0,  # TODO: Calculate
            }
        except Exception as e:
            logger.error(f"Error fetching graph stats: {e}")
            return {
                "total_entities": 0,
                "total_relationships": 0,
                "communities": 0,
                "density": 0.0,
            }

    # ========================================================================
    # CONSOLIDATION
    # ========================================================================

    async def get_consolidation_runs(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get consolidation run history."""
        try:
            query = f"""
                SELECT * FROM consolidation_runs
                ORDER BY timestamp DESC
                LIMIT {limit} OFFSET {offset}
            """
            runs = self.data_loader._query(text(query))

            count_query = "SELECT COUNT(*) as count FROM consolidation_runs"
            count_result = self.data_loader._query(text(count_query))
            total = count_result[0]['count'] if count_result else 0

            return {
                "runs": [dict(r) for r in runs],
                "total": total,
            }
        except Exception as e:
            logger.error(f"Error fetching consolidation runs: {e}")
            return {"runs": [], "total": 0}

    async def get_consolidation_progress(self) -> Dict[str, Any]:
        """Get current consolidation progress."""
        try:
            query = """
                SELECT
                    events_processed,
                    patterns_extracted,
                    quality_score
                FROM consolidation_runs
                ORDER BY timestamp DESC
                LIMIT 1
            """
            result = self.data_loader._query(text(query))
            latest = result[0] if result else {}

            return {
                "percentage": min(int(latest.get("quality_score", 0) * 100), 100),
                "events_processed": latest.get("events_processed", 0),
                "patterns_extracted": latest.get("patterns_extracted", 0),
            }
        except Exception as e:
            logger.error(f"Error fetching consolidation progress: {e}")
            return {
                "percentage": 0,
                "events_processed": 0,
                "patterns_extracted": 0,
            }

    async def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get consolidation statistics."""
        try:
            query = """
                SELECT
                    COUNT(*) as total_runs,
                    SUM(patterns_extracted) as patterns_found,
                    AVG(quality_score) as avg_quality
                FROM consolidation_runs
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "total_runs": stats.get("total_runs", 0),
                "patterns_found": stats.get("patterns_found", 0),
                "avg_quality": float(stats.get("avg_quality", 0.0)),
                "compression_ratio": 0.0,  # TODO: Calculate
            }
        except Exception as e:
            logger.error(f"Error fetching consolidation stats: {e}")
            return {
                "total_runs": 0,
                "patterns_found": 0,
                "avg_quality": 0.0,
                "compression_ratio": 0.0,
            }

    # ========================================================================
    # SYSTEM HEALTH
    # ========================================================================

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            # Check all critical tables
            tables = [
                "episodic_events",
                "semantic_memories",
                "procedural_skills",
                "prospective_tasks",
                "knowledge_graph_entities",
            ]

            health_status = {}
            for table in tables:
                try:
                    query = f"SELECT COUNT(*) as count FROM {table}"
                    result = self.data_loader._query(text(query))
                    count = result[0]['count'] if result else 0
                    health_status[table] = "healthy" if count > 0 else "warning"
                except:
                    health_status[table] = "unhealthy"

            return {
                "status": "healthy" if all(
                    v == "healthy" for v in health_status.values()
                ) else "warning",
                "layers": health_status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                "status": "unhealthy",
                "layers": {},
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide statistics."""
        try:
            query = """
                SELECT
                    (SELECT COUNT(*) FROM episodic_events) as episodic_count,
                    (SELECT COUNT(*) FROM semantic_memories) as semantic_count,
                    (SELECT COUNT(*) FROM procedural_skills) as procedural_count,
                    (SELECT COUNT(*) FROM knowledge_graph_entities) as graph_count
            """
            result = self.data_loader._query(text(query))
            stats = result[0] if result else {}

            return {
                "uptime": 0,  # TODO: Calculate from startup time
                "total_requests": 0,  # TODO: Track requests
                "error_rate": 0.0,
                "memory_summary": {
                    "episodic": stats.get("episodic_count", 0),
                    "semantic": stats.get("semantic_count", 0),
                    "procedural": stats.get("procedural_count", 0),
                    "graph": stats.get("graph_count", 0),
                },
            }
        except Exception as e:
            logger.error(f"Error fetching system stats: {e}")
            return {
                "uptime": 0,
                "total_requests": 0,
                "error_rate": 0.0,
                "memory_summary": {},
            }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def search_episodic(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Full-text search in episodic events."""
        try:
            # Simple implementation - can be enhanced with FTS
            search_query = f"""
                SELECT * FROM episodic_events
                WHERE content ILIKE %s OR metadata ILIKE %s
                LIMIT {limit}
            """
            pattern = f"%{query}%"
            results = self.data_loader._query(text(search_query), [pattern, pattern])

            return {
                "results": [dict(r) for r in results],
                "query": query,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Error searching episodic: {e}")
            return {"results": [], "query": query, "count": 0}

    async def get_working_memory(self) -> Dict[str, Any]:
        """Get current working memory."""
        try:
            query = """
                SELECT * FROM working_memory
                ORDER BY freshness DESC
                LIMIT 7
            """
            items = self.data_loader._query(text(query))

            return {
                "items": [dict(i) for i in items],
                "count": len(items),
                "capacity": 7,
            }
        except Exception as e:
            logger.warning(f"Working memory table not available: {e}")
            return {"items": [], "count": 0, "capacity": 7}
