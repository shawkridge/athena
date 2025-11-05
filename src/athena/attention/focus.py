"""Attention focus management.

Manages what's currently being attended to:
- Primary focus (strongest attention)
- Secondary focuses (divided attention)
- Focus switching with context preservation
"""

from datetime import datetime, timedelta
from typing import List, Optional

from ..core.database import Database
from .models import AttentionType, FocusState, TransitionType


class AttentionFocus:
    """
    Manage attention focus and switching.

    Features:
    - Single primary focus (highest weight)
    - Multiple secondary focuses (divided attention)
    - Automatic focus decay over time
    - Context-preserving focus transitions
    """

    def __init__(self, db: Database):
        """Initialize attention focus manager.

        Args:
            db: Database connection
        """
        self.db = db

    def set_focus(
        self,
        project_id: int,
        memory_id: int,
        memory_layer: str,
        weight: float = 1.0,
        focus_type: AttentionType = AttentionType.PRIMARY,
        transition_type: TransitionType = TransitionType.VOLUNTARY
    ) -> int:
        """Set attention focus on a specific memory.

        If setting PRIMARY focus, ends current primary focus first.

        Args:
            project_id: Project ID
            memory_id: Memory to focus on
            memory_layer: Memory layer
            weight: Attention weight (0.0-1.0)
            focus_type: Type of focus
            transition_type: How focus was initiated

        Returns:
            Focus state ID
        """
        weight = max(0.0, min(1.0, weight))  # Clamp to valid range

        # If setting primary focus, end current primary
        previous_focus_id = None
        if focus_type == AttentionType.PRIMARY:
            current_primary = self.get_focus(project_id, AttentionType.PRIMARY)
            if current_primary:
                self._end_focus(current_primary.id)
                previous_focus_id = current_primary.id

        # Create new focus state
        started_at = datetime.now()
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO attention_state
                (project_id, focus_memory_id, focus_layer, attention_weight,
                 focus_type, started_at, updated_at, transition_type, previous_focus_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, memory_id, memory_layer, weight,
                  focus_type.value, started_at, started_at, transition_type.value,
                  previous_focus_id))
            conn.commit()
            return cursor.lastrowid

    def get_focus(
        self,
        project_id: int,
        focus_type: Optional[AttentionType] = None
    ) -> Optional[FocusState]:
        """Get current attention focus.

        Args:
            project_id: Project ID
            focus_type: Optional filter by focus type

        Returns:
            FocusState if found, None otherwise
        """
        query = """
            SELECT * FROM attention_state
            WHERE project_id = ? AND ended_at IS NULL
        """
        params = [project_id]

        if focus_type:
            query += " AND focus_type = ?"
            params.append(focus_type.value)

        query += " ORDER BY attention_weight DESC LIMIT 1"

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_focus_state(row)

    def get_all_focuses(self, project_id: int) -> List[FocusState]:
        """Get all active focuses (primary + secondary).

        Args:
            project_id: Project ID

        Returns:
            List of FocusState objects sorted by weight (descending)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM attention_state
                WHERE project_id = ? AND ended_at IS NULL
                ORDER BY attention_weight DESC
            """, (project_id,))
            rows = cursor.fetchall()

        return [self._row_to_focus_state(row) for row in rows]

    def shift_focus(
        self,
        project_id: int,
        new_memory_id: int,
        new_layer: str,
        transition_type: TransitionType = TransitionType.VOLUNTARY
    ) -> int:
        """Shift primary focus to a new memory.

        Args:
            project_id: Project ID
            new_memory_id: New memory to focus on
            new_layer: New memory layer
            transition_type: How the shift was initiated

        Returns:
            New focus state ID
        """
        return self.set_focus(
            project_id=project_id,
            memory_id=new_memory_id,
            memory_layer=new_layer,
            weight=1.0,
            focus_type=AttentionType.PRIMARY,
            transition_type=transition_type
        )

    def return_to_previous(self, project_id: int) -> Optional[int]:
        """Return focus to previous state (after interruption).

        Args:
            project_id: Project ID

        Returns:
            New focus state ID if previous focus found, None otherwise
        """
        # Get current focus
        current = self.get_focus(project_id, AttentionType.PRIMARY)
        if not current or not current.previous_focus_id:
            return None

        # Get previous focus details
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT focus_memory_id, focus_layer FROM attention_state
                WHERE id = ?
            """, (current.previous_focus_id,))
            row = cursor.fetchone()

        if not row:
            return None

        # Restore previous focus
        return self.shift_focus(
            project_id=project_id,
            new_memory_id=row['focus_memory_id'],
            new_layer=row['focus_layer'],
            transition_type=TransitionType.RETURN
        )

    def decay_focus(self, project_id: int, decay_rate: float = 0.1):
        """Decay attention weights for all active focuses.

        Args:
            project_id: Project ID
            decay_rate: Decay rate per call (0.0-1.0)
        """
        decay_rate = max(0.0, min(1.0, decay_rate))

        with self.db.get_connection() as conn:
            # Decay all active focuses
            conn.execute("""
                UPDATE attention_state
                SET attention_weight = attention_weight * (1.0 - ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ? AND ended_at IS NULL
            """, (decay_rate, project_id))

            # End focuses that have decayed below threshold
            conn.execute("""
                UPDATE attention_state
                SET ended_at = CURRENT_TIMESTAMP
                WHERE project_id = ? AND ended_at IS NULL AND attention_weight < 0.1
            """, (project_id,))

            conn.commit()

    def get_focus_history(
        self,
        project_id: int,
        limit: int = 10
    ) -> List[FocusState]:
        """Get recent focus history.

        Args:
            project_id: Project ID
            limit: Maximum number to return

        Returns:
            List of FocusState objects (most recent first)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM attention_state
                WHERE project_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (project_id, limit))
            rows = cursor.fetchall()

        return [self._row_to_focus_state(row) for row in rows]

    def get_focus_duration(self, focus_id: int) -> Optional[timedelta]:
        """Get duration of a focus state.

        Args:
            focus_id: Focus state ID

        Returns:
            timedelta of focus duration, None if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT started_at, ended_at FROM attention_state
                WHERE id = ?
            """, (focus_id,))
            row = cursor.fetchone()

        if not row:
            return None

        started = datetime.fromisoformat(row['started_at'])
        ended = datetime.fromisoformat(row['ended_at']) if row['ended_at'] else datetime.now()

        return ended - started

    def _end_focus(self, focus_id: int):
        """End a focus state.

        Args:
            focus_id: Focus state ID to end
        """
        with self.db.get_connection() as conn:
            conn.execute("""
                UPDATE attention_state
                SET ended_at = CURRENT_TIMESTAMP
                WHERE id = ? AND ended_at IS NULL
            """, (focus_id,))
            conn.commit()

    def _row_to_focus_state(self, row) -> FocusState:
        """Convert database row to FocusState object.

        Args:
            row: Database row

        Returns:
            FocusState object
        """
        return FocusState(
            id=row['id'],
            project_id=row['project_id'],
            focus_memory_id=row['focus_memory_id'],
            focus_layer=row['focus_layer'],
            attention_weight=row['attention_weight'],
            focus_type=AttentionType(row['focus_type']),
            started_at=datetime.fromisoformat(row['started_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
            transition_type=TransitionType(row['transition_type']) if row['transition_type'] else None,
            previous_focus_id=row['previous_focus_id']
        )
