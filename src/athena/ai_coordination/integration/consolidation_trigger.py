"""Consolidation triggering for AI Coordination to Memory-MCP integration.

Detects when consolidation should occur (session end, threshold reached) and
triggers Memory-MCP consolidation, converting episodic events to semantic
patterns.

This is Phase 7.3 - enables automatic learning from AI Coordination executions
through Memory-MCP's consolidation pipeline.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class ConsolidationTriggerType(str, Enum):
    """Types of consolidation triggers."""

    SESSION_END = "session_end"
    EVENT_THRESHOLD = "event_threshold"
    TIME_BASED = "time_based"
    MANUAL = "manual"


class ConsolidationStatus(str, Enum):
    """Status of consolidation execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ConsolidationTrigger:
    """Detects and triggers consolidation of episodic to semantic memory.

    Purpose:
    - Monitor for consolidation conditions (session end, thresholds)
    - Collect execution events from sessions
    - Trigger Memory-MCP consolidation pipeline
    - Track consolidation results and metrics

    This enables the learning loop:
    ExecutionTrace → EpisodicEvent → Consolidation → SemanticPattern → Procedure
    """

    # Thresholds for consolidation
    MIN_EVENTS_FOR_CONSOLIDATION = 10
    TIME_THRESHOLD_HOURS = 1

    def __init__(self, db: "Database"):
        """Initialize ConsolidationTrigger.

        Args:
            db: Database connection
        """
        self.db = db

    def _ensure_schema(self):
        """Create consolidation trigger tables."""
        cursor = self.db.get_cursor()

        # Table: Consolidation trigger log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consolidation_triggers (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                trigger_type TEXT NOT NULL,  -- session_end, event_threshold, time_based, manual
                event_count INTEGER,         -- Number of events consolidated
                triggered_at INTEGER NOT NULL,
                started_at INTEGER,
                completed_at INTEGER,
                status TEXT NOT NULL,        -- pending, running, success, failed, partial
                error_message TEXT,
                consolidated_events INTEGER,
                patterns_extracted INTEGER,
                procedures_created INTEGER,
                metadata TEXT                -- JSON with trigger details
            )
        """
        )

        # Table: Pattern sources (links patterns back to original events)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pattern_sources (
                id INTEGER PRIMARY KEY,
                pattern_id INTEGER NOT NULL,
                source_event_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,  -- episodic, semantic, procedural
                strength REAL DEFAULT 0.5,  -- how strong is the link
                created_at INTEGER NOT NULL,
                FOREIGN KEY (source_event_id) REFERENCES episodic_events(id)
            )
        """
        )

        # Table: Consolidation metrics
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consolidation_metrics (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                unit TEXT,
                recorded_at INTEGER NOT NULL
            )
        """
        )

        # Indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consolidation_triggers_session
            ON consolidation_triggers(session_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_consolidation_triggers_status
            ON consolidation_triggers(status)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pattern_sources_pattern
            ON pattern_sources(pattern_id)
        """
        )

        # commit handled by cursor context

    def should_consolidate(self, session_id: str) -> dict:
        """Determine if consolidation should occur for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with consolidation recommendation
        """
        cursor = self.db.get_cursor()

        # Count events in session
        cursor.execute(
            """
            SELECT COUNT(*) FROM episodic_events
            WHERE session_id = ?
        """,
            (session_id,),
        )

        event_count = cursor.fetchone()[0]

        # Check if session has recent consolidation
        cursor.execute(
            """
            SELECT status FROM consolidation_triggers
            WHERE session_id = ? AND status IN ('running', 'success', 'partial')
            ORDER BY triggered_at DESC LIMIT 1
        """,
            (session_id,),
        )

        recent_consolidation = cursor.fetchone()

        # Determine if consolidation needed
        should_consolidate = event_count >= self.MIN_EVENTS_FOR_CONSOLIDATION
        reason = ""

        if should_consolidate and recent_consolidation:
            should_consolidate = False
            reason = "Recent consolidation already completed"

        if should_consolidate:
            reason = f"{event_count} events exceed threshold of {self.MIN_EVENTS_FOR_CONSOLIDATION}"

        return {
            "should_consolidate": should_consolidate,
            "event_count": event_count,
            "threshold": self.MIN_EVENTS_FOR_CONSOLIDATION,
            "reason": reason,
        }

    def trigger_consolidation(
        self,
        session_id: str,
        trigger_type: ConsolidationTriggerType,
        metadata: Optional[dict] = None,
    ) -> int:
        """Trigger consolidation for a session.

        Args:
            session_id: Session identifier
            trigger_type: Type of trigger
            metadata: Optional metadata

        Returns:
            Consolidation trigger ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)
        metadata_json = json.dumps(metadata) if metadata else None

        # Count events to be consolidated
        cursor.execute(
            """
            SELECT COUNT(*) FROM episodic_events
            WHERE session_id = ?
        """,
            (session_id,),
        )

        event_count = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO consolidation_triggers
            (session_id, trigger_type, event_count, triggered_at, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                session_id,
                trigger_type.value,
                event_count,
                now,
                ConsolidationStatus.PENDING.value,
                metadata_json,
            ),
        )

        trigger_id = cursor.lastrowid
        # commit handled by cursor context
        return trigger_id

    def mark_consolidation_started(self, trigger_id: int) -> bool:
        """Mark consolidation as started.

        Args:
            trigger_id: Consolidation trigger ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute(
            """
            UPDATE consolidation_triggers
            SET status = ?, started_at = ?
            WHERE id = ?
        """,
            (ConsolidationStatus.RUNNING.value, now, trigger_id),
        )

        # commit handled by cursor context
        return cursor.rowcount > 0

    def mark_consolidation_completed(
        self,
        trigger_id: int,
        status: ConsolidationStatus,
        consolidated_events: int,
        patterns_extracted: int,
        procedures_created: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """Mark consolidation as completed.

        Args:
            trigger_id: Consolidation trigger ID
            status: Final status (success, failed, partial)
            consolidated_events: Number of events consolidated
            patterns_extracted: Number of patterns extracted
            procedures_created: Number of procedures created
            error_message: Optional error message

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute(
            """
            UPDATE consolidation_triggers
            SET status = ?, completed_at = ?,
                consolidated_events = ?, patterns_extracted = ?,
                procedures_created = ?, error_message = ?
            WHERE id = ?
        """,
            (
                status.value,
                now,
                consolidated_events,
                patterns_extracted,
                procedures_created,
                error_message,
                trigger_id,
            ),
        )

        # commit handled by cursor context
        return cursor.rowcount > 0

    def link_pattern_to_source_events(
        self, pattern_id: int, source_event_ids: list[int], strength: float = 0.8
    ) -> int:
        """Link consolidated pattern back to source events.

        Args:
            pattern_id: ID of extracted pattern (in semantic memory)
            source_event_ids: List of episodic event IDs
            strength: Link strength (0.0-1.0)

        Returns:
            Number of links created
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)
        link_count = 0

        for event_id in source_event_ids:
            cursor.execute(
                """
                INSERT INTO pattern_sources
                (pattern_id, source_event_id, source_type, strength, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (pattern_id, event_id, "episodic", min(strength, 1.0), now),
            )
            link_count += 1

        # commit handled by cursor context
        return link_count

    def get_consolidation_status(self, trigger_id: int) -> Optional[dict]:
        """Get status of a consolidation.

        Args:
            trigger_id: Consolidation trigger ID

        Returns:
            Status dict or None
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT session_id, trigger_type, status, event_count,
                   triggered_at, started_at, completed_at,
                   consolidated_events, patterns_extracted, procedures_created,
                   error_message
            FROM consolidation_triggers
            WHERE id = ?
        """,
            (trigger_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": trigger_id,
            "session_id": row[0],
            "trigger_type": row[1],
            "status": row[2],
            "event_count": row[3],
            "triggered_at": row[4],
            "started_at": row[5],
            "completed_at": row[6],
            "consolidated_events": row[7],
            "patterns_extracted": row[8],
            "procedures_created": row[9],
            "error_message": row[10],
        }

    def get_session_consolidations(self, session_id: str) -> list[dict]:
        """Get all consolidations for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of consolidation dicts
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT id, trigger_type, status, event_count,
                   triggered_at, completed_at,
                   consolidated_events, patterns_extracted
            FROM consolidation_triggers
            WHERE session_id = ?
            ORDER BY triggered_at DESC
        """,
            (session_id,),
        )

        consolidations = []
        for row in cursor.fetchall():
            consolidations.append(
                {
                    "id": row[0],
                    "trigger_type": row[1],
                    "status": row[2],
                    "event_count": row[3],
                    "triggered_at": row[4],
                    "completed_at": row[5],
                    "consolidated_events": row[6],
                    "patterns_extracted": row[7],
                }
            )

        return consolidations

    def get_consolidation_metrics(self, session_id: str) -> dict:
        """Get consolidation metrics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Metrics dict
        """
        cursor = self.db.get_cursor()

        # Total consolidations
        cursor.execute(
            """
            SELECT COUNT(*), AVG(patterns_extracted), SUM(procedures_created)
            FROM consolidation_triggers
            WHERE session_id = ? AND status = 'success'
        """,
            (session_id,),
        )

        row = cursor.fetchone()
        consolidation_count = row[0] or 0
        avg_patterns = row[1] or 0
        total_procedures = row[2] or 0

        # Success rate
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM consolidation_triggers
            WHERE session_id = ?
        """,
            (session_id,),
        )

        total_triggers = cursor.fetchone()[0] or 1

        success_rate = (consolidation_count / total_triggers * 100) if total_triggers > 0 else 0

        return {
            "session_id": session_id,
            "consolidation_count": consolidation_count,
            "average_patterns_per_consolidation": avg_patterns,
            "total_procedures_created": total_procedures,
            "consolidation_success_rate": success_rate,
        }
