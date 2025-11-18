"""Session context management for query-aware memory retrieval.

This module manages session contexts to enable intelligent memory retrieval
that adapts to the current task and phase.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict, dataclass, field

from ..core.async_utils import run_async
from ..core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """Structured session context for query-aware retrieval.

    Attributes:
        session_id: Unique session identifier
        project_id: Project ID
        current_task: Current task description (e.g., "Debug failing test")
        current_phase: Current phase (e.g., "debugging", "development", "testing")
        started_at: When session started
        ended_at: When session ended (None if active)
        recent_events: Recent events in this session
        active_items: Currently active working memory items
        consolidation_history: Record of consolidations in this session
    """

    session_id: str
    project_id: int
    current_task: Optional[str] = None
    current_phase: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None

    # Derived from recent events
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    active_items: List[Dict[str, Any]] = field(default_factory=list)
    consolidation_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dict for passing to retrieve().

        Returns:
            Dictionary representation with ISO format timestamps
        """
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        if self.ended_at:
            data["ended_at"] = self.ended_at.isoformat()
        return data

    def is_active(self) -> bool:
        """Check if session is still active.

        Returns:
            True if session is active, False otherwise
        """
        return self.ended_at is None


class SessionContextManager:
    """Manages session contexts for query-aware retrieval.

    Coordinates with UnifiedMemoryManager, HookDispatcher, and WorkingMemoryAPI
    to maintain structured session state and enable context-aware queries.

    The SessionContextManager:
    - Tracks session lifecycle (start, active events, end)
    - Records task and phase transitions
    - Maintains recent event history
    - Integrates with consolidation triggers
    - Enables context recovery from episodic memory
    - Provides session context to retrieve() for query refinement

    Usage:
        # Create manager
        session_mgr = SessionContextManager(db)

        # Start session with task and phase
        ctx = session_mgr.start_session(
            session_id="session_123",
            project_id=1,
            task="Debug failing test",
            phase="debugging"
        )

        # Record events during session
        session_mgr.record_event(
            session_id="session_123",
            event_type="conversation_turn",
            event_data={"turn_number": 1}
        )

        # Update task/phase as needed
        session_mgr.update_context(phase="refactoring")

        # Get current context for queries
        ctx = session_mgr.get_current_session()

        # End session
        session_mgr.end_session("session_123")
    """

    def __init__(self, db: Database):
        """Initialize session context manager.

        Args:
            db: Database instance

        Raises:
            ValueError: If database is None
        """
        if not db:
            raise ValueError("Database instance is required")

        self.db = db
        self._current_session: Optional[SessionContext] = None
        self._ensure_schema()

    def _ensure_schema(self):
        """Create session-related tables if they don't exist."""
        cursor = self.db.get_cursor()

        # Session contexts table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_contexts (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL UNIQUE,
                task TEXT,
                phase TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,

                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """
        )

        # Session context events table (audit trail)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_context_events (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES session_contexts(session_id)
                    ON DELETE CASCADE
            )
        """
        )

        self.db.commit()

    # ===== Core Session Operations =====

    def start_session(
        self,
        session_id: str,
        project_id: int,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> SessionContext:
        """Start a new session.

        Args:
            session_id: Unique session identifier
            project_id: Project ID
            task: Initial task description (e.g., "Debug failing test")
            phase: Initial phase (e.g., "debugging", "development")

        Returns:
            SessionContext instance

        Raises:
            ValueError: If session_id or project_id is missing
        """
        if not session_id or not project_id:
            raise ValueError("session_id and project_id are required")

        cursor = self.db.get_cursor()

        cursor.execute(
            """
            INSERT INTO session_contexts
            (project_id, session_id, task, phase)
            VALUES (?, ?, ?, ?)
        """,
            (project_id, session_id, task, phase),
        )

        self.db.commit()

        # Create and store context
        self._current_session = SessionContext(
            session_id=session_id,
            project_id=project_id,
            current_task=task,
            current_phase=phase,
        )

        logger.debug(
            f"Started session {session_id} (project={project_id}, " f"task={task}, phase={phase})"
        )
        return self._current_session

    def end_session(self, session_id: Optional[str] = None) -> bool:
        """End a session.

        Args:
            session_id: Session ID (uses current if not provided)

        Returns:
            True if ended successfully, False otherwise
        """
        end_id = session_id or (self._current_session.session_id if self._current_session else None)
        if not end_id:
            logger.warning("No session to end")
            return False

        cursor = self.db.get_cursor()
        cursor.execute(
            """
            UPDATE session_contexts
            SET ended_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """,
            (end_id,),
        )

        self.db.commit()

        if self._current_session and self._current_session.session_id == end_id:
            self._current_session.ended_at = datetime.now()

        logger.debug(f"Ended session {end_id}")
        return True

    def get_current_session(self) -> Optional[SessionContext]:
        """Get current active session.

        Returns:
            SessionContext instance if active, None otherwise
        """
        return self._current_session

    # ===== Event Recording =====

    def record_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> int:
        """Record an event in session context.

        Args:
            session_id: Session ID
            event_type: Type of event (conversation_turn, consolidation, etc.)
            event_data: Event data as dictionary

        Returns:
            Event ID in database

        Raises:
            ValueError: If session_id or event_type is missing
        """
        if not session_id or not event_type:
            raise ValueError("session_id and event_type are required")

        cursor = self.db.get_cursor()

        cursor.execute(
            """
            INSERT INTO session_context_events
            (session_id, event_type, event_data)
            VALUES (?, ?, ?)
        """,
            (session_id, event_type, json.dumps(event_data)),
        )

        event_id = cursor.lastrowid
        self.db.commit()

        logger.debug(f"Recorded {event_type} event in session {session_id} (id={event_id})")
        return event_id

    def record_consolidation(
        self,
        project_id: int,
        consolidation_type: Optional[str] = None,
        wm_size: int = 0,
        consolidation_run_id: Optional[int] = None,
        trigger_type: Optional[str] = None,
    ) -> None:
        """Record consolidation event in session.

        Called automatically when working memory triggers consolidation.

        Args:
            project_id: Project ID (for session lookup)
            consolidation_type: Type of consolidation (CAPACITY, PERIODIC, etc.)
            wm_size: Working memory size at consolidation
            consolidation_run_id: ID of consolidation run
            trigger_type: What triggered consolidation (CAPACITY, PERIODIC, MANUAL)
        """
        if not self._current_session:
            logger.debug("No active session for consolidation recording")
            return

        self.record_event(
            session_id=self._current_session.session_id,
            event_type="consolidation",
            event_data={
                "consolidation_type": consolidation_type,
                "wm_size": wm_size,
                "consolidation_run_id": consolidation_run_id,
                "trigger_type": trigger_type,
            },
        )

        # Track in memory for quick access
        self._current_session.consolidation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "wm_size": wm_size,
                "consolidation_run_id": consolidation_run_id,
                "trigger_type": trigger_type,
            }
        )

    # ===== Context Updates =====

    def update_context(
        self,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Update current session context.

        Args:
            task: New task description
            phase: New phase

        Example:
            session_mgr.update_context(phase="refactoring")
        """
        if not self._current_session:
            logger.warning("No active session to update")
            return

        if task:
            self._current_session.current_task = task
        if phase:
            self._current_session.current_phase = phase

        # Update database
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            UPDATE session_contexts
            SET task = COALESCE(?, task),
                phase = COALESCE(?, phase)
            WHERE session_id = ?
        """,
            (task, phase, self._current_session.session_id),
        )

        self.db.commit()
        logger.debug(f"Updated session context: task={task}, phase={phase}")

    # ===== Context Recovery =====

    def recover_context(
        self,
        recovery_patterns: Optional[List[str]] = None,
        source: str = "episodic_memory",
    ) -> Optional[SessionContext]:
        """Recover session context from episodic memory or session history.

        Attempts to reconstruct session context from recent episodic events or
        session context events when explicit context is unavailable.

        Args:
            recovery_patterns: Patterns to search for (e.g., ["task", "phase"])
            source: Source of recovery ("episodic_memory", "conversation_history")

        Returns:
            Recovered SessionContext or current session if recovery not needed
        """
        if not self._current_session:
            logger.debug(f"No session to recover from {source}")
            return None

        logger.debug(
            f"Recovering context from {source} for session {self._current_session.session_id}"
        )

        # Default recovery patterns if not provided
        if not recovery_patterns:
            recovery_patterns = [
                "task:",
                "phase:",
                "working on",
                "currently",
                "debugging",
                "testing",
                "developing",
            ]

        try:
            cursor = self.db.get_cursor()

            # Search session context events for recent task/phase info
            cursor.execute(
                """
                SELECT event_data FROM session_context_events
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (self._current_session.session_id,),
            )

            recent_events = cursor.fetchall()

            # Try to find task and phase from recent events
            recovered_task = self._current_session.current_task
            recovered_phase = self._current_session.current_phase

            for event_row in recent_events:
                if not event_row:
                    continue

                try:
                    event_data = (
                        json.loads(event_row[0]) if isinstance(event_row[0], str) else event_row[0]
                    )
                    event_content = json.dumps(event_data).lower()

                    # Search for patterns in event content
                    for pattern in recovery_patterns:
                        pattern_lower = pattern.lower()
                        if pattern_lower in event_content:
                            # Try to extract value after pattern
                            if "task" in pattern and not recovered_task:
                                if isinstance(event_data, dict) and "task" in event_data:
                                    recovered_task = str(event_data["task"])
                                    logger.debug(f"Recovered task from events: {recovered_task}")

                            if "phase" in pattern and not recovered_phase:
                                if isinstance(event_data, dict) and "phase" in event_data:
                                    recovered_phase = str(event_data["phase"])
                                    logger.debug(f"Recovered phase from events: {recovered_phase}")

                except (json.JSONDecodeError, TypeError):
                    continue

            # Update session with recovered values
            if recovered_task and recovered_task != self._current_session.current_task:
                self._current_session.current_task = recovered_task

            if recovered_phase and recovered_phase != self._current_session.current_phase:
                self._current_session.current_phase = recovered_phase

            if recovered_task or recovered_phase:
                logger.info(
                    f"Context recovery successful: task={recovered_task}, phase={recovered_phase}"
                )

        except Exception as e:
            logger.warning(f"Context recovery failed: {e}")
            # Continue with current session unchanged

        return self._current_session

    # ===== Query Integration =====

    def get_context_for_query(self) -> Dict[str, Any]:
        """Get session context formatted for query integration.

        Returns:
            Dictionary with session context for use in UnifiedMemoryManager.retrieve()

        Example:
            ctx = session_mgr.get_context_for_query()
            results = memory_manager.retrieve(query, context=ctx)
        """
        if not self._current_session:
            return {}

        return {
            "session_id": self._current_session.session_id,
            "task": self._current_session.current_task,
            "phase": self._current_session.current_phase,
            "recent_events": self._current_session.recent_events,
            "consolidation_count": len(self._current_session.consolidation_history),
        }

    # ===== Async/Sync Bridge Methods =====

    async def start_session_async(
        self,
        session_id: str,
        project_id: int,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> SessionContext:
        """Async version of start_session."""
        return await run_async(self.start_session, session_id, project_id, task, phase)

    async def end_session_async(self, session_id: Optional[str] = None) -> bool:
        """Async version of end_session."""
        return await run_async(self.end_session, session_id)

    async def record_event_async(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> int:
        """Async version of record_event."""
        return await run_async(self.record_event, session_id, event_type, event_data)

    async def update_context_async(
        self,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Async version of update_context."""
        return await run_async(self.update_context, task, phase)
