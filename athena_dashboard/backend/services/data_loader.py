"""Data loader for querying Athena memory database."""

import psycopg
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from config import settings

logger = logging.getLogger(__name__)


class DataLoader:
    """Load data from Athena memory database (PostgreSQL-only)."""

    def __init__(self, connection_string: str = settings.DATABASE_URL):
        """Initialize data loader.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.conn: Optional[psycopg.Connection] = None

    def connect(self) -> None:
        """Connect to database."""
        try:
            self.conn = psycopg.connect(self.connection_string)
            logger.info(f"Connected to Athena database: PostgreSQL")
        except psycopg.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")

    def _query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute query and return results."""
        if not self.conn:
            self.connect()

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            # Convert psycopg rows to dicts
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            return []
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"Table not found, returning empty results: {e}")
            return []
        except psycopg.Error as e:
            logger.error(f"Database error: {e}")
            raise

    # ========================================================================
    # EPISODIC MEMORY QUERIES
    # ========================================================================

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent episodic events.

        Args:
            limit: Number of events to retrieve

        Returns:
            List of recent events
        """
        sql = """
            SELECT id, event_type, content, context, timestamp
            FROM episodic_events
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return self._query(sql, (limit,))

    def get_events_by_type(self, event_type: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get events of specific type in timeframe.

        Args:
            event_type: Type of event (tool_execution, error, consolidation, etc.)
            hours: Hours lookback

        Returns:
            List of matching events
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        sql = """
            SELECT id, event_type, content, timestamp
            FROM episodic_events
            WHERE event_type = %s AND timestamp > %s
            ORDER BY timestamp DESC
        """
        return self._query(sql, (event_type, cutoff.isoformat()))

    def count_events(self) -> int:
        """Count total episodic events."""
        sql = "SELECT COUNT(*) as count FROM episodic_events"
        result = self._query(sql)
        return result[0]["count"] if result else 0

    def get_event_count_by_type(self) -> Dict[str, int]:
        """Get event counts grouped by type."""
        sql = """
            SELECT event_type, COUNT(*) as count
            FROM episodic_events
            GROUP BY event_type
        """
        results = self._query(sql)
        return {row["event_type"]: row["count"] for row in results}

    # ========================================================================
    # SEMANTIC MEMORY QUERIES
    # ========================================================================

    def count_semantic_memories(self) -> int:
        """Count semantic memories."""
        sql = "SELECT COUNT(*) as count FROM semantic_memories"
        result = self._query(sql)
        return result[0]["count"] if result else 0

    def get_memory_quality_score(self) -> Optional[float]:
        """Get overall memory quality score.

        Returns:
            Quality score 0.0-1.0 or None if not available
        """
        sql = """
            SELECT quality_score
            FROM memory_quality
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self._query(sql)
        return result[0]["quality_score"] if result else None

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get latest memory metrics."""
        sql = """
            SELECT *
            FROM memory_quality
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self._query(sql)
        return dict(result[0]) if result else {}

    # ========================================================================
    # PROCEDURAL MEMORY QUERIES
    # ========================================================================

    def count_procedures(self) -> int:
        """Count stored procedures."""
        sql = "SELECT COUNT(*) as count FROM procedures"
        result = self._query(sql)
        return result[0]["count"] if result else 0

    def get_top_procedures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most effective procedures.

        Args:
            limit: Number of procedures to return

        Returns:
            List of top procedures
        """
        sql = """
            SELECT name, description, usage_count, success_rate, effectiveness_score
            FROM procedures
            ORDER BY effectiveness_score DESC
            LIMIT %s
        """
        return self._query(sql, (limit,))

    # ========================================================================
    # CONSOLIDATION QUERIES
    # ========================================================================

    def get_last_consolidation(self) -> Optional[Dict[str, Any]]:
        """Get last consolidation run details.

        Returns None if consolidation_runs table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT *
                FROM consolidation_runs
                ORDER BY started_at DESC
                LIMIT 1
            """
            result = self._query(sql)
            return dict(result[0]) if result else None
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"consolidation_runs table not available: {e}")
            return None

    def get_consolidation_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get consolidation history."""
        cutoff = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        sql = """
            SELECT id, started_at, completed_at, status, patterns_extracted,
                   avg_quality_before as quality_score
            FROM consolidation_runs
            WHERE started_at > %s
            ORDER BY started_at DESC
        """
        return self._query(sql, (cutoff,))

    # ========================================================================
    # WORKING MEMORY QUERIES
    # ========================================================================

    def get_working_memory_items(self) -> List[Dict[str, Any]]:
        """Get current working memory items.

        Returns empty list if working_memory table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT id, content, item_type, freshness, priority, timestamp_added
                FROM working_memory
                ORDER BY freshness DESC
            """
            return self._query(sql)
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"working_memory table not available: {e}")
            return []

    def get_working_memory_count(self) -> int:
        """Get count of current working memory items.

        Returns 0 if working_memory table doesn't exist (graceful fallback).
        """
        try:
            sql = "SELECT COUNT(*) as count FROM working_memory"
            result = self._query(sql)
            return result[0]["count"] if result else 0
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"working_memory table not available: {e}")
            return 0

    # ========================================================================
    # KNOWLEDGE GRAPH QUERIES
    # ========================================================================

    def get_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """Get identified knowledge gaps."""
        sql = """
            SELECT id, gap_type, domain, severity, description, discovered_at
            FROM knowledge_gaps
            ORDER BY severity DESC, discovered_at DESC
        """
        return self._query(sql)

    def count_knowledge_gaps(self, gap_type: Optional[str] = None) -> int:
        """Count knowledge gaps.

        Returns 0 if knowledge_gaps table doesn't exist (graceful fallback).
        """
        try:
            if gap_type:
                sql = "SELECT COUNT(*) as count FROM knowledge_gaps WHERE gap_type = %s"
                result = self._query(sql, (gap_type,))
            else:
                sql = "SELECT COUNT(*) as count FROM knowledge_gaps"
                result = self._query(sql)
            return result[0]["count"] if result else 0
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"knowledge_gaps table not available: {e}")
            return 0

    def get_domain_coverage(self) -> Dict[str, float]:
        """Get coverage percentage per domain.

        Returns empty dict if domain_coverage table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT domain, coverage_percent
                FROM domain_coverage
                ORDER BY coverage_percent DESC
            """
            results = self._query(sql)
            return {row["domain"]: row["coverage_percent"] for row in results}
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"domain_coverage table not available: {e}")
            return {}

    # ========================================================================
    # TASK & PROJECT QUERIES
    # ========================================================================

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get active goals.

        Returns empty list if goals table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT id, name, project_id, priority, progress, status, deadline
                FROM goals
                WHERE status IN ('pending', 'in_progress')
                ORDER BY priority DESC
            """
            return self._query(sql)
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"goals table not available: {e}")
            return []

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get active tasks.

        Returns empty list if tasks table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT id, name, goal_id, estimated_hours, actual_hours, progress, status
                FROM tasks
                WHERE status IN ('pending', 'in_progress')
                ORDER BY deadline ASC
            """
            return self._query(sql)
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"tasks table not available: {e}")
            return []

    def get_project_stats(self) -> Dict[str, Any]:
        """Get aggregate project statistics.

        Returns empty dict if projects table doesn't exist (graceful fallback).
        """
        try:
            sql = """
                SELECT
                    COUNT(DISTINCT id) as project_count,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    AVG(progress) as avg_progress
                FROM projects
            """
            result = self._query(sql)
            return dict(result[0]) if result else {}
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"projects table not available: {e}")
            return {}

    # ========================================================================
    # EXECUTION EVENT QUERIES
    # ========================================================================

    def get_tool_execution_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get tool execution statistics.

        Returns empty dict if tool_executions table doesn't exist (graceful fallback).
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            sql = """
                SELECT
                    COUNT(*) as execution_count,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                    AVG(duration_ms) as avg_latency
                FROM tool_executions
                WHERE timestamp > %s
            """
            result = self._query(sql, (cutoff.isoformat(),))
            return dict(result[0]) if result else {}
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"tool_executions table not available: {e}")
            return {}

    def get_hook_executions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hook executions in timeframe.

        Returns empty list if hook_executions table doesn't exist (graceful fallback).
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            sql = """
                SELECT hook_name, COUNT(*) as count, AVG(duration_ms) as avg_latency
                FROM hook_executions
                WHERE timestamp > %s
                GROUP BY hook_name
                ORDER BY count DESC
            """
            return self._query(sql, (cutoff.isoformat(),))
        except psycopg.errors.UndefinedTable as e:
            logger.warning(f"hook_executions table not available: {e}")
            return []

    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
