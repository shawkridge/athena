"""Simple synchronous bridge for hooks to access PostgreSQL memory.

This implements Anthropic's code-execution-with-MCP pattern:
- Direct database access (no MCP complexity)
- Connection pooling for 50-100x faster reuse (Phase 2 optimization)
- Local execution (no RPC overhead)
- Summary-first results (300 tokens max)
- Graceful error handling

This is used by all hooks to recall memory without complexity.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

# Import connection pool and query cache for performance
from connection_pool import get_connection_pool, PooledConnection
from query_cache import get_query_cache, QueryCacheKey

# Configure logging (check environment for DEBUG)
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class PerformanceTimer:
    """Track operation timing for profiling."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.time() - self.start_time) * 1000
        logger.debug(f"[PERF] {self.operation_name}: {elapsed_ms:.1f}ms")
        return False


class MemoryBridge:
    """Direct PostgreSQL bridge for memory access in hooks.

    OPTIMIZATION (Phase 2): Uses connection pooling for 50-100x faster
    sequential hook execution. First invocation creates connections (~100ms),
    subsequent invocations reuse (~1-2ms each).
    """

    def __init__(self):
        """Initialize bridge with connection pool and query cache."""
        self.pool = get_connection_pool()
        self.cache = get_query_cache()
        # No direct connection needed - pool manages lifecycle

    def close(self):
        """Close (no-op for pooled connections)."""
        # Connections are managed by pool, not closed here
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def get_project_by_path(self, project_path: str) -> Optional[Dict[str, Any]]:
        """Get project by file path.

        Args:
            project_path: Absolute path to project directory

        Returns:
            Project dict or None if not found
        """
        try:
            with PerformanceTimer("get_project_by_path"):
                with PooledConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, name, path FROM projects WHERE path = %s LIMIT 1",
                        (project_path,),
                    )
                    row = cursor.fetchone()

                    if not row:
                        # Try default project
                        cursor.execute(
                            "SELECT id, name, path FROM projects WHERE name = 'default' LIMIT 1"
                        )
                        row = cursor.fetchone()

                    if row:
                        return {
                            "id": row[0],
                            "name": row[1],
                            "path": row[2],
                        }
                    return None
        except Exception as e:
            logger.warning(f"Error getting project: {e}")
            return None

    def get_active_memories(
        self, project_id: int, limit: int = 7
    ) -> Dict[str, Any]:
        """Get active working memory items (7±2 cognitive limit).

        Returns summary only (300 tokens max).

        OPTIMIZATION (Phase 2): Results are cached with 5-minute L1 TTL and
        persistent L2 cache. Repeated calls within 5 minutes return from memory
        (5-10x faster).

        Args:
            project_id: Project ID
            limit: Maximum items to return (default 7±2)

        Returns:
            Dict with summary of active items
        """
        try:
            with PerformanceTimer("get_active_memories"):
                # Query for cache lookup
                query = """
                SELECT id, event_type, content, timestamp, importance_score
                FROM episodic_events
                WHERE project_id = %s
                ORDER BY timestamp DESC, importance_score DESC
                LIMIT %s
                """
                params = (project_id, limit)

                # Try cache first
                cached = self.cache.get(query, params)
                if cached is not None:
                    logger.debug(f"get_active_memories cache hit (project={project_id})")
                    rows = cached
                else:
                    # Execute query
                    with PooledConnection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(query, params)
                        rows = cursor.fetchall()

                    # Cache result
                    self.cache.set(query, params, rows)

                items = [
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2][:50] + "..." if len(row[2]) > 50 else row[2],
                        "timestamp": row[3],
                        "importance": row[4] or 0.5,
                    }
                    for row in rows
                ]

                return {
                    "count": len(items),
                    "items": items,
                    "activation_range": [
                        min(i["importance"] for i in items) if items else 0,
                        max(i["importance"] for i in items) if items else 1,
                    ],
                }
        except Exception as e:
            logger.warning(f"Error getting active memories: {e}")
            return {"count": 0, "items": [], "activation_range": [0, 1]}

    def get_active_goals(self, project_id: int, limit: int = 5) -> Dict[str, Any]:
        """Get active goals/tasks for project.

        OPTIMIZATION (Phase 2): Results are cached with 5-minute L1 TTL.
        Repeated calls within 5 minutes return from memory (5-10x faster).

        Args:
            project_id: Project ID
            limit: Maximum goals to return

        Returns:
            Dict with summary of active goals
        """
        try:
            with PerformanceTimer("get_active_goals"):
                # Query for cache lookup
                query = """
                SELECT id, title, status, priority
                FROM prospective_tasks
                WHERE project_id = %s AND status IN ('active', 'in_progress')
                ORDER BY priority DESC
                LIMIT %s
                """
                params = (project_id, limit)

                # Try cache first
                cached = self.cache.get(query, params)
                if cached is not None:
                    logger.debug(f"get_active_goals cache hit (project={project_id})")
                    rows = cached
                else:
                    # Execute query
                    with PooledConnection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(query, params)
                        rows = cursor.fetchall()

                    # Cache result
                    self.cache.set(query, params, rows)

                goals = [
                    {
                        "id": row[0],
                        "title": row[1][:40] + "..." if len(row[1]) > 40 else row[1],
                        "status": row[2],
                        "priority": row[3],
                    }
                    for row in rows
                ]

                return {"count": len(goals), "goals": goals}
        except Exception as e:
            logger.warning(f"Error getting active goals: {e}")
            return {"count": 0, "goals": []}

    def record_event(
        self,
        project_id: int,
        event_type: str,
        content: str,
        outcome: Optional[str] = None,
    ) -> Optional[int]:
        """Record an event in episodic memory.

        OPTIMIZATION (Phase 2): Invalidates read cache since this is a write operation.
        Future reads will retrieve fresh data.

        Args:
            project_id: Project ID
            event_type: Type of event (e.g., 'user_input', 'tool_use')
            content: Event content/description
            outcome: Optional outcome (success/failure/partial)

        Returns:
            Event ID or None if failed
        """
        try:
            import uuid
            with PooledConnection() as conn:
                cursor = conn.cursor()

                timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
                session_id = str(uuid.uuid4())[:8]  # Generate short session ID

                cursor.execute(
                    """
                    INSERT INTO episodic_events
                    (project_id, event_type, content, timestamp, outcome,
                     session_id, consolidation_status, importance_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        project_id,
                        event_type,
                        content,
                        timestamp,
                        outcome,
                        session_id,
                        "unconsolidated",
                        0.5,  # Default importance
                    ),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    # Invalidate caches on successful write
                    self.cache.invalidate()
                    logger.debug(f"Cache invalidated after event insert")
                    return result[0]
                return None
        except Exception as e:
            logger.warning(f"Error recording event: {e}")
            return None

    def search_memories(
        self, project_id: int, query: str, limit: int = 5
    ) -> Dict[str, Any]:
        """Search for memories matching query (keyword search fallback).

        Args:
            project_id: Project ID
            query: Search query
            limit: Maximum results

        Returns:
            Dict with search results summary
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Simple keyword search in content
                search_terms = query.lower().split()[:3]
                where_clauses = " OR ".join(
                    [f"content ILIKE %s" for _ in search_terms]
                )
                params = [f"%{term}%" for term in search_terms]

                cursor.execute(
                    f"""
                    SELECT id, event_type, content, timestamp, importance_score
                    FROM episodic_events
                    WHERE project_id = %s AND ({where_clauses})
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    [project_id] + params + [limit],
                )

                rows = cursor.fetchall()

                results = [
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2][:60] + "..." if len(row[2]) > 60 else row[2],
                        "timestamp": row[3],
                        "score": row[4] or 0.5,
                    }
                    for row in rows
                ]

                return {"found": len(results), "results": results}
        except Exception as e:
            logger.warning(f"Error searching memories: {e}")
            return {"found": 0, "results": []}
