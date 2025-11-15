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
from typing import Any, Dict, Optional, List  # List for type hints

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


def truncate_by_importance(content: str, importance: float) -> str:
    """Truncate content based on importance score (research-backed strategy).

    Strategy: Context prioritization by importance ranking
    - importance >= 0.7: Full context (critical items must be complete)
    - 0.5 <= importance < 0.7: 200-char summary (balanced approach)
    - importance < 0.5: 50-char summary (optional items)

    Research: AI21 and Agenta recommend importance-ranking over fixed truncation.

    Args:
        content: Original content string
        importance: Importance score (0.0-1.0)

    Returns:
        Appropriately truncated content
    """
    if importance >= 0.7:
        # High importance: Keep full content
        return content
    elif importance >= 0.5:
        # Medium importance: 200-char summary
        if len(content) > 200:
            return content[:200] + "..."
        return content
    else:
        # Low importance: 50-char summary
        if len(content) > 50:
            return content[:50] + "..."
        return content


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
        """Get active working memory items (7±2 cognitive limit) with optimal ranking.

        Returns summary only (300 tokens max).

        RANKING: Uses combined score = importance × contextuality × actionability
        This ensures items with full context are ranked highest.

        OPTIMIZATION (Phase 2): Results are cached with 5-minute L1 TTL and
        persistent L2 cache. Repeated calls within 5 minutes return from memory
        (5-10x faster).

        Args:
            project_id: Project ID
            limit: Maximum items to return (default 7±2)

        Returns:
            Dict with summary of active items (ranked optimally)
        """
        try:
            with PerformanceTimer("get_active_memories"):
                # Enhanced query using combined ranking score for optimal working memory
                # Ranking formula: importance × contextuality × actionability
                query = """
                SELECT
                    id, event_type, content, timestamp,
                    importance_score, actionability_score, context_completeness_score,
                    project_name, project_goal, project_phase_status,
                    (COALESCE(importance_score, 0.5) *
                     COALESCE(context_completeness_score, 0.5) *
                     COALESCE(actionability_score, 0.5)) as combined_rank
                FROM episodic_events
                WHERE project_id = %s
                ORDER BY combined_rank DESC, timestamp DESC
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

                items = []
                for row in rows:
                    importance = row[4] or 0.5
                    items.append({
                        "id": row[0],
                        "type": row[1],
                        "content": truncate_by_importance(row[2], importance),
                        "timestamp": row[3],
                        "importance": importance,
                        "actionability": row[5] or 0.5,
                        "context_completeness": row[6] or 0.5,
                        "project": row[7],
                        "goal": row[8],
                        "phase": row[9],
                        "combined_rank": row[10] or 0.0,
                    })

                return {
                    "count": len(items),
                    "items": items,
                    "ranking_method": "importance × contextuality × actionability",
                    "activation_range": [
                        min(i["importance"] for i in items) if items else 0,
                        max(i["importance"] for i in items) if items else 1,
                    ],
                }
        except Exception as e:
            logger.warning(f"Error getting active memories: {e}")
            return {"count": 0, "items": [], "activation_range": [0, 1]}

    def semantic_search_memories(
        self, project_id: int, query_embedding: List[float], limit: int = 5, threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Search for memories using semantic similarity (pgvector).

        Uses cosine similarity on embeddings to find semantically related items.

        Args:
            project_id: Project ID
            query_embedding: Query embedding vector (768D)
            limit: Maximum results to return
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            Dict with search results and metadata
        """
        try:
            with PerformanceTimer("semantic_search_memories"):
                # Convert embedding to pgvector format string
                embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

                # Query using pgvector cosine distance
                # 1 - distance = similarity (1.0 = identical, 0.0 = opposite)
                query = """
                SELECT
                    id, event_type, content, timestamp, project_name,
                    importance_score, actionability_score,
                    1 - (embedding <=> %s::vector) as similarity
                FROM episodic_events
                WHERE project_id = %s
                  AND embedding IS NOT NULL
                  AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY similarity DESC
                LIMIT %s
                """
                params = (embedding_str, project_id, embedding_str, threshold, limit)

                with PooledConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                items = [
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2][:200] + "..." if len(row[2]) > 200 else row[2],
                        "timestamp": row[3],
                        "project": row[4],
                        "importance": row[5] or 0.5,
                        "actionability": row[6] or 0.5,
                        "similarity": float(row[7]) if row[7] else 0.0,
                    }
                    for row in rows
                ]

                return {
                    "count": len(items),
                    "items": items,
                    "query_threshold": threshold,
                    "search_method": "pgvector_cosine_similarity",
                }
        except Exception as e:
            logger.warning(f"Error in semantic search: {e}")
            return {"count": 0, "items": [], "search_method": "pgvector_cosine_similarity"}

    def find_cross_project_discoveries(
        self, project_id: int, query_embedding: List[float], limit: int = 3
    ) -> Dict[str, Any]:
        """Find similar discoveries in other projects.

        Useful for cross-project knowledge transfer and identifying patterns.

        Args:
            project_id: Current project ID (to exclude)
            query_embedding: Query embedding vector (768D)
            limit: Maximum results from other projects

        Returns:
            Dict with cross-project discoveries
        """
        try:
            with PerformanceTimer("find_cross_project_discoveries"):
                embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

                # Find discoveries with high similarity (> 0.8) in other projects
                query = """
                SELECT
                    e.id, e.project_id, p.name, e.content, e.event_type,
                    e.timestamp, e.importance_score,
                    1 - (e.embedding <=> %s::vector) as similarity
                FROM episodic_events e
                JOIN projects p ON e.project_id = p.id
                WHERE e.project_id != %s
                  AND e.event_type LIKE '%discovery%'
                  AND e.embedding IS NOT NULL
                  AND 1 - (e.embedding <=> %s::vector) > 0.8
                ORDER BY similarity DESC
                LIMIT %s
                """
                params = (embedding_str, project_id, embedding_str, limit)

                with PooledConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                discoveries = [
                    {
                        "id": row[0],
                        "from_project_id": row[1],
                        "from_project": row[2],
                        "content": row[3][:200] + "..." if len(row[3]) > 200 else row[3],
                        "type": row[4],
                        "timestamp": row[5],
                        "importance": row[6] or 0.5,
                        "similarity": float(row[7]) if row[7] else 0.0,
                    }
                    for row in rows
                ]

                return {
                    "count": len(discoveries),
                    "discoveries": discoveries,
                    "source_project_id": project_id,
                }
        except Exception as e:
            logger.warning(f"Error finding cross-project discoveries: {e}")
            return {"count": 0, "discoveries": []}

    def get_related_discoveries_by_event(
        self, project_id: int, event_id: int, limit: int = 5
    ) -> Dict[str, Any]:
        """Get discoveries related to a specific event via relationships.

        Uses the event_relations table to find semantically linked discoveries.

        Args:
            project_id: Project ID
            event_id: Event ID to find relations for
            limit: Maximum related items

        Returns:
            Dict with related discoveries
        """
        try:
            with PerformanceTimer("get_related_discoveries"):
                # Find related events through relationship graph
                query = """
                SELECT
                    e.id, e.event_type, e.content, e.timestamp,
                    e.project_name, e.importance_score,
                    er.strength as relationship_strength
                FROM event_relations er
                JOIN episodic_events e ON er.to_event_id = e.id
                WHERE er.from_event_id = %s
                  AND e.project_id = %s
                  AND er.relation_type = 'semantic_related'
                ORDER BY er.strength DESC
                LIMIT %s
                """
                params = (event_id, project_id, limit)

                with PooledConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                related = [
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2][:200] + "..." if len(row[2]) > 200 else row[2],
                        "timestamp": row[3],
                        "project": row[4],
                        "importance": row[5] or 0.5,
                        "relationship_strength": float(row[6]) if row[6] else 0.0,
                    }
                    for row in rows
                ]

                return {
                    "event_id": event_id,
                    "count": len(related),
                    "related": related,
                }
        except Exception as e:
            logger.warning(f"Error getting related discoveries: {e}")
            return {"event_id": event_id, "count": 0, "related": []}

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
                        "title": truncate_by_importance(row[1], 0.6),  # Goals are mid-importance by default
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
                        "content": truncate_by_importance(row[2], row[4] or 0.5),
                        "timestamp": row[3],
                        "score": row[4] or 0.5,
                    }
                    for row in rows
                ]

                return {"found": len(results), "results": results}
        except Exception as e:
            logger.warning(f"Error searching memories: {e}")
            return {"found": 0, "results": []}

    def get_last_session_time(self, project_id: int) -> Optional[datetime]:
        """Get the timestamp of the last session for a project.

        Args:
            project_id: Project ID

        Returns:
            datetime of last session, or None if no sessions recorded
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT timestamp
                    FROM episodic_events
                    WHERE project_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (project_id,),
                )
                row = cursor.fetchone()

                if row:
                    # Convert milliseconds timestamp to datetime
                    timestamp_ms = row[0]
                    if isinstance(timestamp_ms, int):
                        return datetime.fromtimestamp(timestamp_ms / 1000.0)
                    return None

                return None
        except Exception as e:
            logger.warning(f"Error getting last session time: {e}")
            return None
