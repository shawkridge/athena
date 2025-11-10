"""Temporal chaining for AI Coordination to Memory-MCP integration.

Links ExecutionTraces into temporal chains based on timestamps and causal
relationships, enabling temporal-aware memory consolidation and sequence
understanding.

This is part of Phase 7.2 - enables Memory-MCP to understand event sequences
and build causal chains across AI Coordination executions.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database
    from athena.ai_coordination.execution_traces import ExecutionTrace


class TemporalChainer:
    """Links execution traces into temporal chains.

    Purpose:
    - Link ExecutionTraces by temporal proximity
    - Build temporal chains (immediately_after, shortly_after, later_after)
    - Calculate causal relationships between events
    - Identify execution sequences and patterns

    This enables queries like:
    - "What happened after this execution?"
    - "Are these two executions related?"
    - "What's the sequence of this task's executions?"
    """

    # Temporal relationship thresholds (in seconds)
    IMMEDIATELY_AFTER_THRESHOLD = 5 * 60  # 5 minutes
    SHORTLY_AFTER_THRESHOLD = 60 * 60  # 1 hour
    LATER_AFTER_THRESHOLD = 24 * 60 * 60  # 24 hours

    def __init__(self, db: "Database"):
        """Initialize TemporalChainer.

        Args:
            db: Database connection
        """
        self.db = db
    def _ensure_schema(self):
        """Create temporal_chains tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Table: Temporal chains linking events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_chains (
                id INTEGER PRIMARY KEY,
                from_event_id INTEGER NOT NULL,    -- episodic_event ID
                to_event_id INTEGER NOT NULL,      -- episodic_event ID
                relation_type TEXT NOT NULL,       -- immediately_after, shortly_after, later_after
                time_delta_seconds INTEGER,        -- seconds between events
                causal_strength REAL DEFAULT 0.5,  -- 0.0-1.0 strength of causal link
                metadata TEXT,                     -- JSON with chain details
                created_at INTEGER NOT NULL,
                FOREIGN KEY (from_event_id) REFERENCES episodic_events(id),
                FOREIGN KEY (to_event_id) REFERENCES episodic_events(id)
            )
        """)

        # Table: Execution sequences (ordered chains)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_sequences (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                goal_id TEXT,
                task_id TEXT,
                sequence_order INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                outcome TEXT,
                metadata TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (event_id) REFERENCES episodic_events(id)
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_chains_from
            ON temporal_chains(from_event_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_chains_to
            ON temporal_chains(to_event_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_chains_relation
            ON temporal_chains(relation_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_sequences_session
            ON execution_sequences(session_id, sequence_order)
        """)

        # commit handled by cursor context

    def link_temporal_events(
        self,
        from_event_id: int,
        to_event_id: int,
        from_timestamp: int,
        to_timestamp: int,
        session_continuity: bool = False,
        file_overlap: bool = False
    ) -> Optional[int]:
        """Link two events in temporal chain.

        Args:
            from_event_id: First event ID
            to_event_id: Second event ID
            from_timestamp: Timestamp of first event (milliseconds)
            to_timestamp: Timestamp of second event (milliseconds)
            session_continuity: Whether events are in same session
            file_overlap: Whether events modify same files

        Returns:
            Chain ID, or None if events too far apart
        """
        # Convert to seconds for comparison
        from_ts = from_timestamp / 1000
        to_ts = to_timestamp / 1000
        time_delta = to_ts - from_ts

        # Skip if events out of order
        if time_delta < 0:
            return None

        # Determine relation type based on time delta
        if time_delta <= self.IMMEDIATELY_AFTER_THRESHOLD:
            relation_type = "immediately_after"
            base_strength = 0.8
        elif time_delta <= self.SHORTLY_AFTER_THRESHOLD:
            relation_type = "shortly_after"
            base_strength = 0.6
        elif time_delta <= self.LATER_AFTER_THRESHOLD:
            relation_type = "later_after"
            base_strength = 0.4
        else:
            # Too far apart to link
            return None

        # Calculate causal strength
        causal_strength = base_strength
        if session_continuity:
            causal_strength += 0.15  # Same session = stronger causality
        if file_overlap:
            causal_strength += 0.10  # Same files = stronger causality

        causal_strength = min(causal_strength, 1.0)  # Cap at 1.0

        metadata = {
            "session_continuity": session_continuity,
            "file_overlap": file_overlap,
            "time_delta": int(time_delta),
        }

        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO temporal_chains
            (from_event_id, to_event_id, relation_type, time_delta_seconds,
             causal_strength, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            from_event_id,
            to_event_id,
            relation_type,
            int(time_delta),
            causal_strength,
            json.dumps(metadata),
            now
        ))

        chain_id = cursor.lastrowid
        # commit handled by cursor context
        return chain_id

    def build_session_sequence(
        self,
        session_id: str,
        goal_id: Optional[str],
        task_id: Optional[str]
    ) -> int:
        """Build execution sequence for a session.

        Args:
            session_id: Session identifier
            goal_id: Optional goal ID
            task_id: Optional task ID

        Returns:
            Number of sequences created
        """
        cursor = self.db.get_cursor()

        # Get all events for this session, ordered by timestamp
        cursor.execute("""
            SELECT id, timestamp, outcome, content
            FROM episodic_events
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))

        events = cursor.fetchall()
        sequence_count = 0

        for order, (event_id, timestamp, outcome, content) in enumerate(events):
            metadata = {
                "session_id": session_id,
                "goal_id": goal_id,
                "task_id": task_id,
                "content": content,
            }

            cursor.execute("""
                INSERT INTO execution_sequences
                (session_id, goal_id, task_id, sequence_order, event_id,
                 timestamp, outcome, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                goal_id,
                task_id,
                order,
                event_id,
                timestamp,
                outcome,
                json.dumps(metadata),
                int(datetime.now().timestamp() * 1000)
            ))

            sequence_count += 1

        # commit handled by cursor context
        return sequence_count

    def get_temporal_chain(self, event_id: int) -> dict:
        """Get temporal chain for an event (before and after).

        Args:
            event_id: Event ID

        Returns:
            Dict with before/after chains
        """
        cursor = self.db.get_cursor()

        # Get events that led to this one (predecessors)
        cursor.execute("""
            SELECT from_event_id, relation_type, causal_strength
            FROM temporal_chains
            WHERE to_event_id = ?
            ORDER BY causal_strength DESC
        """, (event_id,))

        predecessors = [
            {
                "event_id": row[0],
                "relation_type": row[1],
                "causal_strength": row[2]
            }
            for row in cursor.fetchall()
        ]

        # Get events that follow this one (successors)
        cursor.execute("""
            SELECT to_event_id, relation_type, causal_strength
            FROM temporal_chains
            WHERE from_event_id = ?
            ORDER BY causal_strength DESC
        """, (event_id,))

        successors = [
            {
                "event_id": row[0],
                "relation_type": row[1],
                "causal_strength": row[2]
            }
            for row in cursor.fetchall()
        ]

        return {
            "event_id": event_id,
            "predecessors": predecessors,
            "successors": successors,
        }

    def get_execution_sequence(
        self,
        session_id: str,
        limit: int = 50
    ) -> list[dict]:
        """Get execution sequence for a session.

        Args:
            session_id: Session identifier
            limit: Maximum events to return

        Returns:
            List of sequence events
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT sequence_order, event_id, timestamp, outcome, metadata
            FROM execution_sequences
            WHERE session_id = ?
            ORDER BY sequence_order ASC
            LIMIT ?
        """, (session_id, limit))

        sequence = []
        for order, event_id, timestamp, outcome, metadata_json in cursor.fetchall():
            try:
                metadata = json.loads(metadata_json)
            except json.JSONDecodeError:
                metadata = {}

            sequence.append({
                "order": order,
                "event_id": event_id,
                "timestamp": timestamp,
                "outcome": outcome,
                "metadata": metadata,
            })

        return sequence

    def get_causal_relationships(
        self,
        event_id: int,
        min_strength: float = 0.5
    ) -> list[dict]:
        """Get causally strong relationships for an event.

        Args:
            event_id: Event ID
            min_strength: Minimum causal strength (0.0-1.0)

        Returns:
            List of causal relationships
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT from_event_id, to_event_id, relation_type, causal_strength
            FROM temporal_chains
            WHERE (from_event_id = ? OR to_event_id = ?)
            AND causal_strength >= ?
            ORDER BY causal_strength DESC
        """, (event_id, event_id, min_strength))

        relationships = []
        for from_id, to_id, relation_type, strength in cursor.fetchall():
            relationships.append({
                "from_event_id": from_id,
                "to_event_id": to_id,
                "relation_type": relation_type,
                "causal_strength": strength,
                "direction": "forward" if from_id == event_id else "backward",
            })

        return relationships

    def detect_event_patterns(
        self,
        session_id: str,
        pattern_length: int = 3
    ) -> list[list[int]]:
        """Detect repeating patterns in event sequence.

        Args:
            session_id: Session identifier
            pattern_length: Length of patterns to detect

        Returns:
            List of repeating pattern sequences
        """
        cursor = self.db.get_cursor()

        # Get sequence for session
        cursor.execute("""
            SELECT event_id
            FROM execution_sequences
            WHERE session_id = ?
            ORDER BY sequence_order ASC
        """, (session_id,))

        event_ids = [row[0] for row in cursor.fetchall()]

        # Simple pattern detection: look for subsequences
        patterns = []
        if len(event_ids) >= pattern_length:
            for i in range(len(event_ids) - pattern_length + 1):
                pattern = event_ids[i:i + pattern_length]
                # Check if this pattern appears again later
                for j in range(i + pattern_length, len(event_ids) - pattern_length + 1):
                    if event_ids[j:j + pattern_length] == pattern:
                        if pattern not in patterns:
                            patterns.append(pattern)
                        break

        return patterns

    def calculate_sequence_metrics(self, session_id: str) -> dict:
        """Calculate metrics for a session's execution sequence.

        Args:
            session_id: Session identifier

        Returns:
            Dict with sequence metrics
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT COUNT(*), AVG(time_delta_seconds)
            FROM temporal_chains tc
            WHERE EXISTS (
                SELECT 1 FROM execution_sequences es
                WHERE es.session_id = ? AND (
                    es.event_id = tc.from_event_id OR
                    es.event_id = tc.to_event_id
                )
            )
        """, (session_id,))

        row = cursor.fetchone()
        link_count = row[0] or 0
        avg_time_delta = row[1] or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT outcome), outcome
            FROM execution_sequences
            WHERE session_id = ?
            GROUP BY outcome
        """, (session_id,))

        outcomes = {row[1]: row[0] for row in cursor.fetchall()}

        return {
            "session_id": session_id,
            "event_count": len(self.get_execution_sequence(session_id, limit=1000)),
            "temporal_link_count": link_count,
            "average_event_spacing_seconds": int(avg_time_delta),
            "outcomes": outcomes,
        }
