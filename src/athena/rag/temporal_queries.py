"""
Temporal/Timeline Queries for Memory Retrieval.

Implements causal reasoning over episodic timeline to understand
event sequences, dependencies, and temporal patterns.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from athena.core.database import Database

logger = logging.getLogger(__name__)


class TemporalRelation(str, Enum):
    """Temporal relationship types."""
    IMMEDIATELY_AFTER = "immediately_after"  # <5 min
    SHORTLY_AFTER = "shortly_after"  # 5-60 min
    LATER_AFTER = "later_after"  # 1-24 hours
    SAME_SESSION = "same_session"  # Same session
    RELATED_BY_CONTEXT = "related_by_context"  # Similar context


@dataclass
class TemporalEvent:
    """Event with temporal information."""
    event_id: int
    content: str
    event_type: str
    timestamp: datetime
    session_id: str
    outcome: str


@dataclass
class EventSequence:
    """Sequence of causally-related events."""
    events: List[TemporalEvent]
    causal_strength: float  # 0.0-1.0 confidence of causality
    time_span: timedelta
    summary: str


class TemporalQueries:
    """Temporal reasoning over episodic events."""

    def __init__(self, db: Database):
        """Initialize temporal queries.

        Args:
            db: Database connection
        """
        self.db = db

    async def find_causal_sequence(
        self,
        event_description: str,
        direction: str = "forward",
        max_events: int = 10,
    ) -> Optional[EventSequence]:
        """Find causal event sequence starting from or leading to event.

        Args:
            event_description: Description of event to find
            direction: "forward" (effects) or "backward" (causes)
            max_events: Maximum events in sequence

        Returns:
            EventSequence if found
        """
        try:
            # Find the focal event
            focal_event = self._find_event(event_description)
            if not focal_event:
                logger.debug(f"Event not found: {event_description}")
                return None

            # Find related events
            if direction == "forward":
                related = self._find_forward_chain(focal_event, max_events)
            else:
                related = self._find_backward_chain(focal_event, max_events)

            if not related:
                return None

            # Build sequence with causal strength
            events = [focal_event] + related
            causal_strength = self._calculate_causal_strength(events)
            time_span = events[-1].timestamp - events[0].timestamp
            summary = self._build_event_summary(events)

            return EventSequence(
                events=events,
                causal_strength=causal_strength,
                time_span=time_span,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"Causal sequence search failed: {e}")
            return None

    def _find_event(self, description: str) -> Optional[TemporalEvent]:
        """Find event by description.

        Args:
            description: Event description

        Returns:
            TemporalEvent if found
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, content, event_type, timestamp, session_id, outcome
                FROM episodic_events
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (f"%{description}%",),
            )
            row = cursor.fetchone()

            if not row:
                return None

            event_id, content, event_type, timestamp, session_id, outcome = row
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            return TemporalEvent(
                event_id=event_id,
                content=content,
                event_type=event_type,
                timestamp=timestamp,
                session_id=session_id,
                outcome=outcome or "unknown",
            )

        except Exception as e:
            logger.debug(f"Event lookup failed: {e}")
            return None

    def _find_forward_chain(
        self,
        event: TemporalEvent,
        max_events: int,
    ) -> List[TemporalEvent]:
        """Find events that follow and may be causally related.

        Args:
            event: Starting event
            max_events: Maximum events to find

        Returns:
            List of related events in temporal order
        """
        related = []

        try:
            cursor = self.db.get_cursor()

            # Find events within 24 hours after
            end_time = event.timestamp + timedelta(hours=24)

            cursor.execute(
                """
                SELECT id, content, event_type, timestamp, session_id, outcome
                FROM episodic_events
                WHERE timestamp > ? AND timestamp <= ?
                AND session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (
                    event.timestamp.isoformat(),
                    end_time.isoformat(),
                    event.session_id,
                    max_events,
                ),
            )

            for row in cursor.fetchall():
                event_id, content, event_type, timestamp, session_id, outcome = row
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                related.append(
                    TemporalEvent(
                        event_id=event_id,
                        content=content,
                        event_type=event_type,
                        timestamp=timestamp,
                        session_id=session_id,
                        outcome=outcome or "unknown",
                    )
                )

        except Exception as e:
            logger.debug(f"Forward chain search failed: {e}")

        return related

    def _find_backward_chain(
        self,
        event: TemporalEvent,
        max_events: int,
    ) -> List[TemporalEvent]:
        """Find events that precede and may have caused this event.

        Args:
            event: Target event
            max_events: Maximum events to find

        Returns:
            List of preceding events in reverse temporal order
        """
        related = []

        try:
            cursor = self.db.get_cursor()

            # Find events within 24 hours before
            start_time = event.timestamp - timedelta(hours=24)

            cursor.execute(
                """
                SELECT id, content, event_type, timestamp, session_id, outcome
                FROM episodic_events
                WHERE timestamp >= ? AND timestamp < ?
                AND session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (
                    start_time.isoformat(),
                    event.timestamp.isoformat(),
                    event.session_id,
                    max_events,
                ),
            )

            for row in cursor.fetchall():
                event_id, content, event_type, timestamp, session_id, outcome = row
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                related.append(
                    TemporalEvent(
                        event_id=event_id,
                        content=content,
                        event_type=event_type,
                        timestamp=timestamp,
                        session_id=session_id,
                        outcome=outcome or "unknown",
                    )
                )

            # Reverse to get chronological order
            related.reverse()

        except Exception as e:
            logger.debug(f"Backward chain search failed: {e}")

        return related

    def _calculate_causal_strength(self, events: List[TemporalEvent]) -> float:
        """Calculate confidence of causal relationship between events.

        Uses temporal proximity and outcome continuity.

        Args:
            events: Sequence of events

        Returns:
            Causal strength (0.0-1.0)
        """
        if len(events) < 2:
            return 0.0

        strengths = []

        for i in range(len(events) - 1):
            curr = events[i]
            next_ev = events[i + 1]

            # Time proximity score
            time_diff = (next_ev.timestamp - curr.timestamp).total_seconds()
            if time_diff < 300:  # <5 min
                time_score = 1.0
            elif time_diff < 3600:  # <1 hour
                time_score = 0.8
            elif time_diff < 86400:  # <1 day
                time_score = 0.5
            else:
                time_score = 0.0

            # Outcome continuity score
            outcome_score = 1.0 if curr.outcome == "success" else 0.5

            # Event type relevance
            type_score = 1.0 if curr.event_type == next_ev.event_type else 0.7

            # Combined strength
            strength = (0.4 * time_score + 0.3 * outcome_score + 0.3 * type_score)
            strengths.append(strength)

        # Return average strength
        return sum(strengths) / len(strengths) if strengths else 0.0

    def _build_event_summary(self, events: List[TemporalEvent]) -> str:
        """Build timeline narrative.

        Args:
            events: List of events

        Returns:
            Timeline summary string
        """
        if not events:
            return ""

        lines = ["📅 Timeline:"]

        for i, event in enumerate(events):
            time_str = event.timestamp.strftime("%H:%M:%S")
            status = "✓" if event.outcome == "success" else "✗" if event.outcome == "failure" else "○"

            # Format event
            event_line = f"{time_str} {status} {event.event_type}: {event.content}"
            if len(event_line) > 100:
                event_line = event_line[:97] + "..."

            lines.append(event_line)

            # Add time delta
            if i < len(events) - 1:
                delta = events[i + 1].timestamp - event.timestamp
                if delta.total_seconds() < 300:
                    lines.append("    ↓ immediately after")
                elif delta.total_seconds() < 3600:
                    mins = int(delta.total_seconds() / 60)
                    lines.append(f"    ↓ {mins} min later")
                else:
                    hours = int(delta.total_seconds() / 3600)
                    lines.append(f"    ↓ {hours}h later")

        return "\n".join(lines)

    async def find_temporal_pattern(
        self,
        pattern_description: str,
        time_window: timedelta = timedelta(days=7),
    ) -> Dict[str, Any]:
        """Find repeating temporal patterns in events.

        Identifies recurring event sequences.

        Args:
            pattern_description: Description of pattern
            time_window: Time window to search

        Returns:
            Dict with pattern occurrences and statistics
        """
        try:
            cursor = self.db.get_cursor()

            # Find all matching events in window
            start_time = datetime.utcnow() - time_window
            cursor.execute(
                """
                SELECT id, content, event_type, timestamp, session_id, outcome
                FROM episodic_events
                WHERE content LIKE ? AND timestamp > ?
                ORDER BY timestamp ASC
                """,
                (f"%{pattern_description}%", start_time.isoformat()),
            )
            rows = cursor.fetchall()

            if not rows:
                return {
                    "pattern": pattern_description,
                    "occurrences": 0,
                    "frequency": "never",
                    "latest": None,
                }

            # Build statistics
            occurrences = len(rows)
            success_rate = sum(1 for r in rows if r[5] == "success") / occurrences

            # Calculate frequency
            if occurrences > 1:
                time_diffs = []
                for i in range(len(rows) - 1):
                    t1 = datetime.fromisoformat(rows[i][3].replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(rows[i + 1][3].replace("Z", "+00:00"))
                    time_diffs.append((t2 - t1).total_seconds())

                avg_interval = sum(time_diffs) / len(time_diffs)
                if avg_interval < 3600:
                    frequency = "hourly"
                elif avg_interval < 86400:
                    frequency = "daily"
                else:
                    frequency = "weekly"
            else:
                frequency = "once"

            latest_time = datetime.fromisoformat(rows[-1][3].replace("Z", "+00:00"))

            return {
                "pattern": pattern_description,
                "occurrences": occurrences,
                "frequency": frequency,
                "success_rate": f"{success_rate:.0%}",
                "latest": latest_time.isoformat(),
                "time_window_days": time_window.days,
            }

        except Exception as e:
            logger.error(f"Pattern search failed: {e}")
            return {
                "pattern": pattern_description,
                "occurrences": 0,
                "error": str(e),
            }
