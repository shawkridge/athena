"""Context recovery for conversation preservation across /clear boundaries."""

import json
from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType


class ContextSnapshot:
    """Snapshot and recover conversation context using episodic memory."""

    def __init__(self, db: Database, project_id: int = 1):
        """Initialize context snapshot manager.

        Args:
            db: Database instance
            project_id: Project ID for memory isolation
        """
        self.db = db
        self.project_id = project_id
        self.episodic_store = None  # Lazy-loaded

    def _get_episodic_store(self):
        """Get or create episodic store (lazy-loaded)."""
        if self.episodic_store is None:
            from ..episodic.store import EpisodicStore

            self.episodic_store = EpisodicStore(self.db)
        return self.episodic_store

    def snapshot_conversation(
        self,
        session_id: str,
        conversation_content: str,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> int:
        """Save conversation context before /clear.

        Args:
            session_id: Unique session identifier
            conversation_content: Full conversation text
            task: Optional current task description
            phase: Optional current execution phase

        Returns:
            Event ID of saved conversation
        """
        event = EpisodicEvent(
            project_id=self.project_id,
            session_id=session_id,
            timestamp=datetime.now(),
            event_type=EventType.CONVERSATION,
            content=conversation_content,
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                task=task,
                phase=phase,
            ),
            learned="Conversation snapshot for context recovery after /clear",
            confidence=1.0,
        )

        store = self._get_episodic_store()
        event_id = store.record_event(event)
        return event_id

    def snapshot_session_state(
        self,
        session_id: str,
        conversation_content: str,
        context_summary: str,
        active_goals: Optional[list[str]] = None,
        recent_files: Optional[list[str]] = None,
    ) -> int:
        """Save complete session state for resumption.

        Args:
            session_id: Unique session identifier
            conversation_content: Full conversation text
            context_summary: One-sentence summary of what you were doing
            active_goals: List of active goal descriptions
            recent_files: List of recently modified files

        Returns:
            Event ID of saved session state
        """
        state_data = {
            "conversation": conversation_content,
            "context_summary": context_summary,
            "active_goals": active_goals or [],
            "recent_files": recent_files or [],
            "snapshot_time": datetime.now().isoformat(),
        }

        event = EpisodicEvent(
            project_id=self.project_id,
            session_id=session_id,
            timestamp=datetime.now(),
            event_type=EventType.CONVERSATION,
            content=json.dumps(state_data, indent=2),
            outcome=EventOutcome.SUCCESS,
            context=EventContext(
                task=context_summary,
                phase="session_checkpoint",
            ),
            learned="Complete session state for resumption after context limit",
            confidence=1.0,
        )

        store = self._get_episodic_store()
        event_id = store.record_event(event)
        return event_id

    def recover_conversation(
        self, session_id: str, query: str = "conversation context", limit: int = 5
    ) -> list[dict]:
        """Recover conversation context from episodic memory.

        Args:
            session_id: Session identifier to search
            query: Search query for context retrieval
            limit: Maximum results to return

        Returns:
            List of recovered conversation events with content
        """
        store = self._get_episodic_store()
        cursor = self.db.get_cursor()

        # Search in specific session
        cursor.execute(
            """
            SELECT id, timestamp, content, context_task, context_phase, learned, confidence
            FROM episodic_events
            WHERE project_id = ?
              AND session_id = ?
              AND event_type = 'conversation'
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (self.project_id, session_id, limit),
        )

        results = []
        for row in cursor.fetchall():
            event_id, timestamp, content, task, phase, learned, confidence = row
            results.append(
                {
                    "event_id": event_id,
                    "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                    "content": content,
                    "task": task,
                    "phase": phase,
                    "learned": learned,
                    "confidence": confidence,
                }
            )

        return results

    def search_conversation_history(self, query: str, limit: int = 10) -> list[dict]:
        """Search conversation history across all sessions.

        Args:
            query: Search query (keywords or phrases)
            limit: Maximum results to return

        Returns:
            List of matching conversation events
        """
        store = self._get_episodic_store()
        cursor = self.db.get_cursor()

        # Full-text keyword search
        keywords = query.lower().split()
        where_conditions = []
        params = [self.project_id, "conversation"]

        for keyword in keywords:
            if len(keyword) >= 3:
                where_conditions.append("LOWER(content) LIKE ?")
                params.append(f"%{keyword}%")

        if not where_conditions:
            where_conditions = ["1=1"]

        where_clause = " AND ".join(where_conditions)

        sql = f"""
            SELECT id, session_id, timestamp, content, context_task, context_phase, learned, confidence
            FROM episodic_events
            WHERE project_id = ?
              AND event_type = ?
              AND {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """

        cursor.execute(sql, params + [limit])

        results = []
        for row in cursor.fetchall():
            event_id, session_id, timestamp, content, task, phase, learned, confidence = row
            results.append(
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                    "content": content[:500],  # Truncate for display
                    "task": task,
                    "phase": phase,
                    "learned": learned,
                    "confidence": confidence,
                }
            )

        return results

    def get_session_stats(self, session_id: str) -> dict:
        """Get statistics about a session's conversations.

        Args:
            session_id: Session identifier

        Returns:
            Statistics about conversation events in session
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT DATE(timestamp, 'unixepoch')) as days_active,
                MIN(timestamp) as first_event,
                MAX(timestamp) as last_event,
                SUM(LENGTH(content)) as total_content_size
            FROM episodic_events
            WHERE project_id = ? AND session_id = ? AND event_type = 'conversation'
        """,
            (self.project_id, session_id),
        )

        row = cursor.fetchone()
        if not row:
            return {
                "total_events": 0,
                "days_active": 0,
                "first_event": None,
                "last_event": None,
                "total_content_size": 0,
            }

        total_events, days_active, first_event, last_event, total_size = row
        return {
            "total_events": total_events or 0,
            "days_active": days_active or 0,
            "first_event": datetime.fromtimestamp(first_event).isoformat() if first_event else None,
            "last_event": datetime.fromtimestamp(last_event).isoformat() if last_event else None,
            "total_content_size": total_size or 0,
        }

    def get_recovery_recommendation(self, session_id: str) -> dict:
        """Generate a recovery recommendation for resuming work.

        Args:
            session_id: Session identifier

        Returns:
            Recommendation for context recovery
        """
        # Get recent conversations
        recent = self.recover_conversation(session_id, limit=3)

        if not recent:
            return {
                "status": "no_history",
                "message": "No conversation history found for this session",
            }

        # Get stats
        stats = self.get_session_stats(session_id)

        # Build recommendation
        latest_conversation = recent[0]["content"]
        context_summary = (
            latest_conversation[:200] + "..."
            if len(latest_conversation) > 200
            else latest_conversation
        )

        return {
            "status": "ready_to_recover",
            "message": f"Found {stats['total_events']} conversation events",
            "last_activity": recent[0]["timestamp"],
            "context_preview": context_summary,
            "recovery_steps": [
                "1. Check recovered conversation content below",
                "2. Use /memory-query to search for specific topics",
                "3. Review recent tasks and goals",
                "4. Continue from last point",
            ],
        }
