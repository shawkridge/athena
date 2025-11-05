#!/usr/bin/env python3
"""
Temporal Chains - Phase 5 Implementation

Automatically links episodic events by time windows for temporal reasoning.

Time Windows (from CLAUDE.md):
- < 5 minutes (300s): "immediately_after" - Same focus/task
- 5-60 minutes (300-3600s): "shortly_after" - Same session, different tasks
- 1-24 hours (3600-86400s): "later_after" - Same day, different sessions
- 24+ hours: No link (different context)

Example chain:
    Event 1: "Started task X"         (timestamp: 10:00:00)
    ↓ immediately_after (4 min 59 sec)
    Event 2: "Added feature Y"        (timestamp: 10:04:59)
    ↓ shortly_after (45 min)
    Event 3: "Code review feedback"   (timestamp: 10:49:59)

Session Continuity:
- Events in same session are more likely to be linked
- Different sessions are linked only if <24 hours apart
- Causal strength computed from: time_delta + session_continuity + file_overlap
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("temporal_chains")


class TemporalLinkType(str, Enum):
    """Types of temporal links between events."""
    IMMEDIATELY_AFTER = "immediately_after"  # < 5 min (300s)
    SHORTLY_AFTER = "shortly_after"          # 5-60 min (300-3600s)
    LATER_AFTER = "later_after"              # 1-24 hours (3600-86400s)


@dataclass
class TemporalLink:
    """
    Represents a temporal link between two events.

    Attributes:
        from_event_id: Source event
        to_event_id: Target event
        time_delta_seconds: Time elapsed
        link_type: Type of temporal link
        confidence: Confidence score (0.0-1.0)
        causal_strength: Estimated causal relationship strength
    """
    id: Optional[int] = None
    from_event_id: int = 0
    to_event_id: int = 0
    time_delta_seconds: int = 0
    link_type: str = TemporalLinkType.IMMEDIATELY_AFTER
    confidence: float = 0.0
    causal_strength: float = 0.0

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


class TemporalChain:
    """
    Manages temporal relationships between events.

    Features:
    - Automatic linking by time windows
    - Chain traversal (forward/backward)
    - Causal inference
    - Session continuity tracking
    """

    # Time window boundaries (in seconds)
    IMMEDIATELY_AFTER_MAX = 300  # 5 minutes
    SHORTLY_AFTER_MAX = 3600     # 1 hour
    LATER_AFTER_MAX = 86400      # 24 hours

    def __init__(self):
        """Initialize temporal chain processor."""
        pass

    def compute_link_type(self, time_delta_seconds: int) -> str:
        """
        Determine link type based on time delta.

        Args:
            time_delta_seconds: Seconds between events

        Returns:
            Link type as string
        """
        if time_delta_seconds < self.IMMEDIATELY_AFTER_MAX:
            return TemporalLinkType.IMMEDIATELY_AFTER
        elif time_delta_seconds < self.SHORTLY_AFTER_MAX:
            return TemporalLinkType.SHORTLY_AFTER
        elif time_delta_seconds < self.LATER_AFTER_MAX:
            return TemporalLinkType.LATER_AFTER
        else:
            return None  # Too far apart

    def compute_confidence(self, time_delta: int, session_same: bool = True,
                          file_overlap: bool = False) -> float:
        """
        Compute confidence score for a temporal link.

        Factors:
        - Time delta (closer = higher confidence)
        - Session continuity (same session = higher)
        - File overlap (related files = higher)

        Args:
            time_delta: Seconds between events
            session_same: True if in same session
            file_overlap: True if in same directory/file

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence from time proximity
        if time_delta < self.IMMEDIATELY_AFTER_MAX:
            base = 0.9
        elif time_delta < self.SHORTLY_AFTER_MAX:
            base = 0.7
        elif time_delta < self.LATER_AFTER_MAX:
            base = 0.4
        else:
            base = 0.0

        # Boost for session continuity
        if session_same:
            base += 0.1

        # Boost for file overlap
        if file_overlap:
            base += 0.1

        return min(base, 1.0)

    def compute_causal_strength(self, time_delta: int, file_overlap: bool = False) -> float:
        """
        Estimate causal relationship strength between events.

        Args:
            time_delta: Seconds between events
            file_overlap: True if events in same file/directory

        Returns:
            Causal strength score (0.0-1.0)
        """
        # Temporal proximity = causality
        if time_delta < self.IMMEDIATELY_AFTER_MAX:
            base = 0.8
        elif time_delta < self.SHORTLY_AFTER_MAX:
            base = 0.5
        else:
            base = 0.2

        # File overlap increases causal likelihood
        if file_overlap:
            base += 0.2

        return min(base, 1.0)


class TemporalStore:
    """
    Stores and queries temporal links between events.

    Provides:
    - Persistent storage of temporal chains
    - Forward/backward traversal
    - Causal reasoning queries
    - Chain analysis and metrics
    """

    def __init__(self, db_path: str):
        """
        Initialize temporal store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.chain = TemporalChain()
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()

        # Temporal links table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_links (
                id INTEGER PRIMARY KEY,
                from_event_id INTEGER NOT NULL,
                to_event_id INTEGER NOT NULL,
                time_delta_seconds INTEGER NOT NULL,
                link_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                causal_strength REAL DEFAULT 0.5,
                created_at INTEGER NOT NULL,
                UNIQUE(from_event_id, to_event_id),
                FOREIGN KEY(from_event_id) REFERENCES episodic_events(id),
                FOREIGN KEY(to_event_id) REFERENCES episodic_events(id)
            )
        """)

        # Indices for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_from_event
            ON temporal_links(from_event_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_to_event
            ON temporal_links(to_event_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temporal_link_type
            ON temporal_links(link_type)
        """)

        self.conn.commit()

    def create_link(self, from_event_id: int, to_event_id: int,
                   time_delta_seconds: int, session_same: bool = True,
                   file_overlap: bool = False) -> Optional[TemporalLink]:
        """
        Create a temporal link between two events.

        Args:
            from_event_id: Source event ID
            to_event_id: Target event ID
            time_delta_seconds: Time elapsed (seconds)
            session_same: True if events in same session
            file_overlap: True if events in same file/directory

        Returns:
            Created TemporalLink, or None if too far apart
        """
        link_type = self.chain.compute_link_type(time_delta_seconds)
        if not link_type:
            return None  # Too far apart

        confidence = self.chain.compute_confidence(
            time_delta_seconds, session_same, file_overlap
        )
        causal_strength = self.chain.compute_causal_strength(
            time_delta_seconds, file_overlap
        )

        import time
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO temporal_links
                (from_event_id, to_event_id, time_delta_seconds, link_type,
                 confidence, causal_strength, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                from_event_id, to_event_id, time_delta_seconds,
                link_type, confidence, causal_strength, int(time.time())
            ))

            cursor.execute(
                "SELECT id FROM temporal_links WHERE from_event_id = ? AND to_event_id = ?",
                (from_event_id, to_event_id)
            )
            result = cursor.fetchone()

            self.conn.commit()

            if result:
                return TemporalLink(
                    id=result[0],
                    from_event_id=from_event_id,
                    to_event_id=to_event_id,
                    time_delta_seconds=time_delta_seconds,
                    link_type=link_type,
                    confidence=confidence,
                    causal_strength=causal_strength
                )
        except sqlite3.IntegrityError as e:
            logger.warning(f"Failed to create link: {e}")

        return None

    def get_forward_chain(self, event_id: int,
                         link_type: Optional[str] = None,
                         max_depth: int = 5) -> List[Tuple[int, TemporalLink]]:
        """
        Get all events that follow an event (temporal forward chain).

        Args:
            event_id: Source event ID
            link_type: Filter by link type (None = all)
            max_depth: Maximum chain depth

        Returns:
            List of (event_id, TemporalLink) tuples
        """
        cursor = self.conn.cursor()

        if link_type:
            cursor.execute("""
                SELECT id, to_event_id, time_delta_seconds, link_type,
                       confidence, causal_strength
                FROM temporal_links
                WHERE from_event_id = ? AND link_type = ?
                ORDER BY time_delta_seconds
            """, (event_id, link_type))
        else:
            cursor.execute("""
                SELECT id, to_event_id, time_delta_seconds, link_type,
                       confidence, causal_strength
                FROM temporal_links
                WHERE from_event_id = ?
                ORDER BY time_delta_seconds
            """, (event_id,))

        chain = []
        for row in cursor.fetchall():
            link = TemporalLink(
                id=row[0],
                from_event_id=event_id,
                to_event_id=row[1],
                time_delta_seconds=row[2],
                link_type=row[3],
                confidence=row[4],
                causal_strength=row[5]
            )
            chain.append((row[1], link))

        return chain

    def get_backward_chain(self, event_id: int,
                          link_type: Optional[str] = None,
                          max_depth: int = 5) -> List[Tuple[int, TemporalLink]]:
        """
        Get all events that precede an event (temporal backward chain).

        Args:
            event_id: Target event ID
            link_type: Filter by link type (None = all)
            max_depth: Maximum chain depth

        Returns:
            List of (event_id, TemporalLink) tuples
        """
        cursor = self.conn.cursor()

        if link_type:
            cursor.execute("""
                SELECT id, from_event_id, time_delta_seconds, link_type,
                       confidence, causal_strength
                FROM temporal_links
                WHERE to_event_id = ? AND link_type = ?
                ORDER BY time_delta_seconds DESC
            """, (event_id, link_type))
        else:
            cursor.execute("""
                SELECT id, from_event_id, time_delta_seconds, link_type,
                       confidence, causal_strength
                FROM temporal_links
                WHERE to_event_id = ?
                ORDER BY time_delta_seconds DESC
            """, (event_id,))

        chain = []
        for row in cursor.fetchall():
            link = TemporalLink(
                id=row[0],
                from_event_id=row[1],
                to_event_id=event_id,
                time_delta_seconds=row[2],
                link_type=row[3],
                confidence=row[4],
                causal_strength=row[5]
            )
            chain.append((row[1], link))

        return chain

    def get_events_by_link_type(self, link_type: str,
                               confidence_min: float = 0.5) -> List[TemporalLink]:
        """
        Get all links of a specific type above confidence threshold.

        Args:
            link_type: Type of link to retrieve
            confidence_min: Minimum confidence score

        Returns:
            List of TemporalLink objects
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, from_event_id, to_event_id, time_delta_seconds,
                   link_type, confidence, causal_strength
            FROM temporal_links
            WHERE link_type = ? AND confidence >= ?
            ORDER BY confidence DESC
        """, (link_type, confidence_min))

        links = []
        for row in cursor.fetchall():
            links.append(TemporalLink(
                id=row[0],
                from_event_id=row[1],
                to_event_id=row[2],
                time_delta_seconds=row[3],
                link_type=row[4],
                confidence=row[5],
                causal_strength=row[6]
            ))

        return links

    def get_chain_stats(self) -> Dict:
        """
        Get statistics about temporal chains.

        Returns:
            Dict with chain statistics
        """
        cursor = self.conn.cursor()

        # Count by link type
        cursor.execute("""
            SELECT link_type, COUNT(*) as count
            FROM temporal_links
            GROUP BY link_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Average confidence
        cursor.execute("""
            SELECT AVG(confidence), AVG(causal_strength)
            FROM temporal_links
        """)
        row = cursor.fetchone()
        avg_confidence = row[0] or 0.0
        avg_causal = row[1] or 0.0

        # Total links
        cursor.execute("SELECT COUNT(*) FROM temporal_links")
        total = cursor.fetchone()[0]

        return {
            "total_links": total,
            "by_link_type": by_type,
            "avg_confidence": avg_confidence,
            "avg_causal_strength": avg_causal
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """CLI interface for temporal chains."""
    import argparse

    parser = argparse.ArgumentParser(description="Temporal Chains Tool")
    parser.add_argument("--link-type", help="Get link type for time delta")
    parser.add_argument("--time-delta", type=int, help="Time delta in seconds")

    args = parser.parse_args()

    chain = TemporalChain()

    if args.time_delta is not None:
        link_type = chain.compute_link_type(args.time_delta)
        confidence = chain.compute_confidence(args.time_delta)

        print(f"Time delta: {args.time_delta} seconds")
        print(f"Link type: {link_type}")
        print(f"Confidence: {confidence:.2f}")


if __name__ == "__main__":
    main()
