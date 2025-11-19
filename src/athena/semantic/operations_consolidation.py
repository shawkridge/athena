"""Consolidation and reconsolidation operations for semantic store."""

from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConsolidationOperations:
    """Memory consolidation and reconsolidation operations."""

    def __init__(self, db):
        """Initialize consolidation operations.

        Args:
            db: Database instance
        """
        self.db = db

    def mark_memory_labile(self, memory_id: int, window_minutes: int = 5):
        """Mark memory as labile (retrieved, open for modification).

        Opens a reconsolidation window for the specified duration.

        Args:
            memory_id: Memory ID to mark as labile
            window_minutes: Duration of reconsolidation window in minutes
        """
        now = datetime.now()
        self.db.execute(
            """
            UPDATE semantic_memories
            SET consolidation_state = 'labile',
                last_retrieved = %s
            WHERE id = %s
        """,
            (now, memory_id),
        )
        self.db.conn.commit()

    def is_in_reconsolidation_window(
        self, memory_id: int, window_minutes: int = 5
    ) -> bool:
        """Check if memory is within reconsolidation window.

        Returns True if memory was retrieved within the specified window.

        Args:
            memory_id: Memory ID to check
            window_minutes: Window duration in minutes

        Returns:
            True if in reconsolidation window, False otherwise
        """
        memory = self.db.get_memory(memory_id)
        if not memory or not memory.last_retrieved:
            return False

        now = datetime.now()
        elapsed = (now - memory.last_retrieved).total_seconds() / 60
        return elapsed < window_minutes

    def get_memory_history(self, memory_id: int) -> list[dict]:
        """Get version history for a memory (superseded_by chain).

        Args:
            memory_id: Memory ID to get history for

        Returns:
            List of memory versions in order
        """
        from ..core.models import Memory

        history = []
        current_id = memory_id

        # Follow the superseded_by chain
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            memory = self.db.get_memory(current_id)
            if not memory:
                break

            history.append(
                {
                    "id": memory.id,
                    "version": memory.version,
                    "content": memory.content,
                    "updated_at": memory.updated_at,
                    "consolidation_state": memory.consolidation_state,
                    "superseded_by": memory.superseded_by,
                }
            )

            if not memory.superseded_by:
                break
            current_id = memory.superseded_by

        return history
