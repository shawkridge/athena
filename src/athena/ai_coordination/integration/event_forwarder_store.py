"""Store for managing forwarding log and status

Handles database operations for the forwarding audit trail,
tracking what AI Coordination events have been forwarded to Memory-MCP.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from athena.core.database import Database
from athena.core.base_store import BaseStore


class ForwardingLogEntry(BaseModel):
    """Model for a forwarding log entry."""

    id: Optional[int] = None
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    status: str = "complete"
    timestamp: int
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: Optional[int] = None


class EventForwarderStore(BaseStore[ForwardingLogEntry]):
    """Database store for event forwarding operations

    Maintains audit trail of forwarded events (AI Coordination → Memory-MCP).
    Enables validation, debugging, and reconciliation.
    """

    table_name = "forwarding_log"
    model_class = ForwardingLogEntry

    def __init__(self, db: Database):
        """Initialize EventForwarderStore

        Args:
            db: Database connection
        """
        super().__init__(db)
        self._ensure_schema()

    def _row_to_model(self, row: Dict[str, Any]) -> ForwardingLogEntry:
        """Convert database row to ForwardingLogEntry model.

        Args:
            row: Database row as dict

        Returns:
            ForwardingLogEntry instance
        """
        return ForwardingLogEntry(
            id=row.get("id"),
            source_type=row.get("source_type"),
            source_id=row.get("source_id"),
            target_type=row.get("target_type"),
            target_id=row.get("target_id"),
            status=row.get("status", "complete"),
            timestamp=row.get("timestamp"),
            metadata=self.deserialize_json(row.get("metadata_json"), {}) if row.get("metadata_json") else {},
            created_at=row.get("created_at"),
        )

    def _ensure_schema(self):
        """Create forwarding log tables if they don't exist"""
        cursor = self.db.get_cursor()

        # Forwarding log table - tracks all forwards
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forwarding_log (
                id INTEGER PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                status TEXT DEFAULT 'complete',
                timestamp INTEGER NOT NULL,
                metadata_json TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE(source_type, source_id, target_type)
            )
        """)

        # Forwarding statistics table - pre-computed stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forwarding_stats (
                id INTEGER PRIMARY KEY,
                source_type TEXT UNIQUE,
                forward_count INTEGER,
                last_forward_time INTEGER,
                updated_at INTEGER
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_forwarding_source
            ON forwarding_log(source_type, source_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_forwarding_target
            ON forwarding_log(target_type, target_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_forwarding_time
            ON forwarding_log(timestamp)
        """)

        # commit handled by cursor context

    def log_forwarding(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        status: str = "complete",
        metadata: Optional[dict] = None,
    ) -> int:
        """Log a forwarding operation

        Args:
            source_type: Type in coordination system (ExecutionTrace, etc)
            source_id: ID in coordination system
            target_type: Type in memory-mcp (EpisodicEvent, etc)
            target_id: ID in memory-mcp
            status: Status of forwarding (complete, pending, failed)
            metadata: Additional context about the forward

        Returns:
            log_id: ID of the log entry
        """
        timestamp = self.now_timestamp()

        self.execute(
            """
            INSERT INTO forwarding_log
            (source_type, source_id, target_type, target_id, status, timestamp, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_type,
                source_id,
                target_type,
                target_id,
                status,
                timestamp,
                self.serialize_json(metadata or {}),
                timestamp,
            ),
        )

        self.commit()

        # Get the last inserted ID
        result = self.execute("SELECT last_insert_rowid()", fetch_one=True)
        last_id = result[0] if result else None

        # Update statistics
        self._update_stats(source_type)

        return last_id

    def get_forwarding_status(self):
        """Get overall forwarding status

        Returns:
            Object with total_forwarded, by_source_type, pending_forwarding
        """
        # Get total forwarded
        result = self.execute("SELECT COUNT(*) FROM forwarding_log WHERE status = 'complete'", fetch_one=True)
        total = result[0] if result else 0

        # Get by source type
        rows = self.execute("""
            SELECT source_type, COUNT(*) as count
            FROM forwarding_log
            WHERE status = 'complete'
            GROUP BY source_type
        """, fetch_all=True)

        by_type = {row[0]: row[1] for row in rows} if rows else {}

        # Get pending count
        result = self.execute("SELECT COUNT(*) FROM forwarding_log WHERE status = 'pending'", fetch_one=True)
        pending = result[0] if result else 0

        # Get last forward time
        result = self.execute("SELECT MAX(timestamp) FROM forwarding_log", fetch_one=True)
        last_time = result[0] if result else None

        class Status:
            total_forwarded = total
            by_source_type = by_type
            pending_forwarding = pending
            last_forward_time = last_time

        return Status()

    def get_forwarding_log_by_source(
        self,
        source_type: str,
        source_id: Optional[str] = None,
    ) -> List[ForwardingLogEntry]:
        """Get forwarding log entries for a source

        Args:
            source_type: Type to filter by
            source_id: Optional specific source to filter by

        Returns:
            List of ForwardingLogEntry objects
        """
        if source_id:
            rows = self.execute(
                """
                SELECT id, source_type, source_id, target_type, target_id,
                       status, timestamp, metadata_json, created_at
                FROM forwarding_log
                WHERE source_type = ? AND source_id = ?
                ORDER BY timestamp DESC
                """,
                (source_type, source_id),
                fetch_all=True,
            )
        else:
            rows = self.execute(
                """
                SELECT id, source_type, source_id, target_type, target_id,
                       status, timestamp, metadata_json, created_at
                FROM forwarding_log
                WHERE source_type = ?
                ORDER BY timestamp DESC
                """,
                (source_type,),
                fetch_all=True,
            )

        return [self._row_to_model(dict(zip(
            ["id", "source_type", "source_id", "target_type", "target_id", "status", "timestamp", "metadata_json", "created_at"],
            row
        ))) for row in (rows or [])]

    def get_all_forwarding_logs(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ForwardingLogEntry]:
        """Get all forwarding log entries

        Args:
            limit: Maximum number to return
            offset: Offset for pagination

        Returns:
            List of ForwardingLogEntry objects
        """
        rows = self.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id,
                   status, timestamp, metadata_json, created_at
            FROM forwarding_log
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
            fetch_all=True,
        )

        return [self._row_to_model(dict(zip(
            ["id", "source_type", "source_id", "target_type", "target_id", "status", "timestamp", "metadata_json", "created_at"],
            row
        ))) for row in (rows or [])]

    def mark_forwarding_complete(self, log_id: int) -> bool:
        """Mark a forwarding as complete

        Args:
            log_id: ID of log entry

        Returns:
            True if successful
        """
        self.execute(
            "UPDATE forwarding_log SET status = 'complete' WHERE id = ?",
            (log_id,),
        )

        self.commit()
        return True

    def mark_forwarding_failed(self, log_id: int, error: str) -> bool:
        """Mark a forwarding as failed

        Args:
            log_id: ID of log entry
            error: Error message

        Returns:
            True if successful
        """
        self.execute(
            """
            UPDATE forwarding_log
            SET status = 'failed', metadata_json = ?
            WHERE id = ?
            """,
            (self.serialize_json({"error": error}), log_id),
        )

        self.commit()
        return True

    def get_forwarding_by_target(
        self,
        target_type: str,
        target_id: str,
    ) -> Optional[ForwardingLogEntry]:
        """Get the forwarding entry for a specific target

        Useful for finding original source of a memory-mcp event.

        Args:
            target_type: Target type (EpisodicEvent, etc)
            target_id: Target ID in memory-mcp

        Returns:
            ForwardingLogEntry or None
        """
        row = self.execute(
            """
            SELECT id, source_type, source_id, target_type, target_id,
                   status, timestamp, metadata_json, created_at
            FROM forwarding_log
            WHERE target_type = ? AND target_id = ?
            LIMIT 1
            """,
            (target_type, target_id),
            fetch_one=True,
        )

        if not row:
            return None

        return self._row_to_model(dict(zip(
            ["id", "source_type", "source_id", "target_type", "target_id", "status", "timestamp", "metadata_json", "created_at"],
            row
        )))

    def _update_stats(self, source_type: str):
        """Update forwarding statistics for a source type

        Args:
            source_type: Type to update stats for
        """
        # Get current count for this type
        result = self.execute(
            """
            SELECT COUNT(*) FROM forwarding_log
            WHERE source_type = ? AND status = 'complete'
            """,
            (source_type,),
            fetch_one=True,
        )

        count = result[0] if result else 0
        timestamp = self.now_timestamp()

        # Update or insert stats
        self.execute(
            """
            INSERT OR REPLACE INTO forwarding_stats
            (source_type, forward_count, last_forward_time, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (source_type, count, timestamp, timestamp),
        )

        self.commit()

    def get_forwarding_stats(self) -> Dict[str, Dict]:
        """Get statistics by source type

        Returns:
            Dict mapping source_type to {count, last_forward_time}
        """
        rows = self.execute("""
            SELECT source_type, forward_count, last_forward_time
            FROM forwarding_stats
            ORDER BY source_type
        """, fetch_all=True)

        return {
            row[0]: {
                "count": row[1],
                "last_forward_time": row[2],
            }
            for row in (rows or [])
        }
