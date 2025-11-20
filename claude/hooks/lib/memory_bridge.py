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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List

# Import connection pool and query cache for performance
from connection_pool import get_connection_pool, PooledConnection
from query_cache import get_query_cache, QueryCacheKey
# Import worktree helper for memory prioritization
from git_worktree_helper import GitWorktreeHelper
# Import diagnostics for monitoring
try:
    from memory_diagnostics import MemoryDiagnostics
    DIAGNOSTICS_AVAILABLE = True
except ImportError:
    DIAGNOSTICS_AVAILABLE = False

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
        """Get active working memory items (7±2 cognitive limit) ranked by ACT-R activation.

        Uses ACT-R activation decay model instead of simple importance scoring:
        Activation = base_level_decay + frequency_bonus + consolidation_boost
                   + importance_boost + actionability_boost + success_boost
                   + worktree_boost (prioritizes current worktree memories)

        Filters by lifecycle_status='active' to exclude consolidated events.

        WORKTREE AWARENESS: Memories from all worktrees are accessible (cross-worktree),
        but memories from the current worktree are boosted in activation ranking to
        prioritize relevant context.

        Returns summary only (300 tokens max).

        OPTIMIZATION (Phase 2): Results are cached with 5-minute L1 TTL and
        persistent L2 cache. Repeated calls within 5 minutes return from memory
        (5-10x faster).

        Args:
            project_id: Project ID
            limit: Maximum items to return (default 7±2)

        Returns:
            Dict with summary of active items ranked by activation (worktree-prioritized)
        """
        try:
            with PerformanceTimer("get_active_memories"):
                # Get current worktree context for prioritization
                worktree_helper = GitWorktreeHelper()
                current_worktree = worktree_helper.get_worktree_info().get("worktree_path")

                # Query for cache lookup
                # Uses ACT-R activation equation: base_level + frequency + consolidation + importance + actionability + success + worktree_boost
                query = """
                SELECT
                    id,
                    event_type,
                    content,
                    timestamp,
                    importance_score,
                    worktree_path,
                    (
                        -- Base level decay: -d * ln(time_since_access_hours) where d=0.5
                        (-0.5 * LN(GREATEST(EXTRACT(EPOCH FROM (NOW() - last_activation)) / 3600.0, 0.1)))
                        -- Frequency bonus: ln(activation_count)
                        + (LN(GREATEST(activation_count, 1)) * 0.1)
                        -- Consolidation boost
                        + (COALESCE(consolidation_score, 0) * 1.0)
                        -- Importance boost: +1.5 if importance > 0.7
                        + CASE WHEN importance_score > 0.7 THEN 1.5 ELSE 0 END
                        -- Actionability boost: +1.0 if has_next_step or actionability > 0.7
                        + CASE WHEN has_next_step = 1 OR actionability_score > 0.7 THEN 1.0 ELSE 0 END
                        -- Success boost: +0.5 if outcome='success'
                        + CASE WHEN outcome = 'success' THEN 0.5 ELSE 0 END
                        -- Worktree boost: +2.0 if memory is from current worktree (prioritizes local context)
                        + CASE WHEN worktree_path = %s THEN 2.0 ELSE 0 END
                    ) as activation
                FROM episodic_events
                WHERE project_id = %s AND lifecycle_status = 'active'
                ORDER BY activation DESC, timestamp DESC
                LIMIT %s
                """
                params = (current_worktree, project_id, limit)

                # Try cache first
                cached = self.cache.get(query, params)
                if cached is not None:
                    logger.debug(f"get_active_memories cache hit (project={project_id}, worktree={current_worktree})")
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
                        "worktree_path": row[5],
                        "activation": row[6] or 0.0,
                    }
                    for row in rows
                ]

                # Log prioritization analytics if diagnostics available
                if DIAGNOSTICS_AVAILABLE and os.environ.get("DEBUG"):
                    try:
                        analysis = MemoryDiagnostics.log_memory_prioritization(
                            project_id, items, current_worktree
                        )
                        logger.debug(f"Memory prioritization: {json.dumps(analysis)}")
                    except Exception as e:
                        logger.debug(f"Could not log memory diagnostics: {e}")

                return {
                    "count": len(items),
                    "items": items,
                    "activation_range": [
                        min(i["activation"] for i in items) if items else 0,
                        max(i["activation"] for i in items) if items else 1,
                    ],
                    "current_worktree": current_worktree,
                }
        except Exception as e:
            logger.warning(f"Error getting active memories: {e}")
            return {"count": 0, "items": [], "activation_range": [0, 1], "current_worktree": None}

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
        """Record an event in episodic memory with worktree context.

        OPTIMIZATION (Phase 2): Invalidates read cache since this is a write operation.
        Future reads will retrieve fresh data.

        WORKTREE AWARENESS: Automatically captures current worktree path and branch
        for proper memory prioritization and isolation.

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

                # Use UTC time for consistency with session-start.sh
                # timezone-aware UTC datetime (modern approach)
                timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)  # milliseconds
                session_id = str(uuid.uuid4())[:8]  # Generate short session ID

                # Get current worktree context for memory tagging
                worktree_helper = GitWorktreeHelper()
                worktree_info = worktree_helper.get_worktree_info()
                worktree_path = worktree_info.get("worktree_path")
                worktree_branch = worktree_info.get("worktree_branch")

                cursor.execute(
                    """
                    INSERT INTO episodic_events
                    (project_id, event_type, content, timestamp, outcome,
                     session_id, consolidation_status, importance_score,
                     worktree_path, worktree_branch)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        worktree_path,
                        worktree_branch,
                    ),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    # Invalidate caches on successful write
                    self.cache.invalidate()
                    logger.debug(f"Cache invalidated after event insert (worktree={worktree_path})")
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

    def get_last_session_time(self, project_id: int) -> Optional[datetime]:
        """Get the timestamp of the last session for a project.

        Args:
            project_id: Project ID

        Returns:
            datetime of last session (UTC), or None if no sessions recorded
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
                    # Convert milliseconds timestamp to UTC datetime
                    # CRITICAL: Must use UTC to match datetime.now(timezone.utc) in session-start.sh
                    timestamp_ms = row[0]
                    if isinstance(timestamp_ms, int):
                        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
                    return None

                return None
        except Exception as e:
            logger.warning(f"Error getting last session time: {e}")
            return None

    def get_memory_content(self, memory_id: int) -> Optional[str]:
        """Get full content of a memory by ID.

        Used by hooks to retrieve complete memory content (not truncated).

        Args:
            memory_id: Memory ID

        Returns:
            Full content string, or None if not found
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM episodic_events WHERE id = %s",
                    (memory_id,),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning(f"Error getting memory content: {e}")
            return None
