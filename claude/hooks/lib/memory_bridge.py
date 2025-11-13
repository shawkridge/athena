"""Simple synchronous bridge for hooks to access PostgreSQL memory.

This implements Anthropic's code-execution-with-MCP pattern:
- Direct database access (no MCP complexity)
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

# Configure logging (check environment for DEBUG)
import os
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
    """Direct PostgreSQL bridge for memory access in hooks."""

    def __init__(self):
        """Initialize connection to PostgreSQL."""
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to PostgreSQL database."""
        import psycopg

        try:
            self.conn = psycopg.connect(
                host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
                dbname=os.environ.get("ATHENA_POSTGRES_DB", "athena"),
                user=os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
                password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
            )
            logger.debug("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

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
                cursor = self.conn.cursor()
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

        Args:
            project_id: Project ID
            limit: Maximum items to return (default 7±2)

        Returns:
            Dict with summary of active items
        """
        try:
            with PerformanceTimer("get_active_memories"):
                cursor = self.conn.cursor()

                # Get recent, high-importance events
                cursor.execute(
                    """
                    SELECT id, event_type, content, timestamp, importance_score
                    FROM episodic_events
                    WHERE project_id = %s
                    ORDER BY timestamp DESC, importance_score DESC
                    LIMIT %s
                    """,
                    (project_id, limit),
                )

                rows = cursor.fetchall()

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

        Args:
            project_id: Project ID
            limit: Maximum goals to return

        Returns:
            Dict with summary of active goals
        """
        try:
            with PerformanceTimer("get_active_goals"):
                cursor = self.conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, status, priority
                    FROM prospective_tasks
                    WHERE project_id = %s AND status IN ('active', 'in_progress')
                    ORDER BY priority DESC
                    LIMIT %s
                    """,
                    (project_id, limit),
                )

                rows = cursor.fetchall()

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
            cursor = self.conn.cursor()

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
            self.conn.commit()

            if result:
                return result[0]
            return None
        except Exception as e:
            logger.warning(f"Error recording event: {e}")
            self.conn.rollback()
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
            cursor = self.conn.cursor()

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
