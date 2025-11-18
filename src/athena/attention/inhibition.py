"""Attention inhibition for memory suppression.

Implements three types of cognitive inhibition:
- Proactive: Old memories suppressed by new learning
- Retroactive: New learning suppresses old memories
- Selective: User-directed suppression

Inhibition decays exponentially over time.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from ..core.database import Database
from .models import InhibitionRecord, InhibitionType


class AttentionInhibition:
    """
    Manage memory inhibition (suppression from retrieval).

    Features:
    - Three inhibition types (proactive, retroactive, selective)
    - Exponential decay over time
    - Strength-based filtering
    - Automatic cleanup of expired inhibitions
    """

    # Default inhibition decay half-life (30 minutes)
    DEFAULT_HALF_LIFE_SECONDS = 1800

    def __init__(self, db: Database):
        """Initialize attention inhibition manager.

        Args:
            db: Database connection
        """
        self.db = db

    def inhibit(
        self,
        project_id: int,
        memory_id: int,
        memory_layer: str,
        strength: float = 0.5,
        inhibition_type: InhibitionType = InhibitionType.SELECTIVE,
        reason: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> int:
        """Inhibit a memory from retrieval.

        Args:
            project_id: Project ID
            memory_id: Memory to inhibit
            memory_layer: Memory layer
            strength: Inhibition strength (0.0-1.0)
            inhibition_type: Type of inhibition
            reason: Optional reason for inhibition
            duration_seconds: Optional explicit expiration (None = no expiration)

        Returns:
            Inhibition record ID
        """
        strength = max(0.0, min(1.0, strength))  # Clamp to valid range

        expires_at = None
        if duration_seconds is not None:
            expires_at = datetime.now() + timedelta(seconds=duration_seconds)

        cursor = self.db.conn.execute(
            """
                INSERT INTO attention_inhibition
                (project_id, memory_id, memory_layer, inhibition_strength,
                 inhibition_type, reason, inhibited_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                project_id,
                memory_id,
                memory_layer,
                strength,
                inhibition_type.value,
                reason,
                datetime.now(),
                expires_at,
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def release_inhibition(self, inhibition_id: int) -> bool:
        """Release (remove) an inhibition.

        Args:
            inhibition_id: Inhibition record ID

        Returns:
            True if inhibition was removed, False if not found
        """
        cursor = self.db.conn.execute(
            "DELETE FROM attention_inhibition WHERE id = ?", (inhibition_id,)
        )
        # commit handled by cursor context
        return cursor.rowcount > 0

    def release_memory(self, project_id: int, memory_id: int, memory_layer: str) -> int:
        """Release all inhibitions for a specific memory.

        Args:
            project_id: Project ID
            memory_id: Memory ID
            memory_layer: Memory layer

        Returns:
            Number of inhibitions removed
        """
        cursor = self.db.conn.execute(
            """
            DELETE FROM attention_inhibition
            WHERE project_id = ? AND memory_id = ? AND memory_layer = ?
            """,
            (project_id, memory_id, memory_layer),
        )
        # commit handled by cursor context
        return cursor.rowcount

    def is_inhibited(
        self, memory_id: int, memory_layer: str, project_id: int, threshold: float = 0.3
    ) -> bool:
        """Check if a memory is currently inhibited.

        Memory is inhibited if effective inhibition strength >= threshold.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer
            project_id: Project ID
            threshold: Minimum strength to consider inhibited (default 0.3)

        Returns:
            True if memory is inhibited above threshold
        """
        strength = self.get_inhibition_strength(memory_id, memory_layer, project_id)
        return strength >= threshold

    def get_inhibition_strength(self, memory_id: int, memory_layer: str, project_id: int) -> float:
        """Get effective inhibition strength for a memory.

        Applies exponential decay based on time since inhibition.
        Returns sum of all active inhibitions (capped at 1.0).

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer
            project_id: Project ID

        Returns:
            Effective inhibition strength (0.0-1.0)
        """
        now = datetime.now()

        cursor = self.db.conn.execute(
            """
            SELECT inhibition_strength, inhibited_at, expires_at
            FROM attention_inhibition
            WHERE project_id = ?
              AND memory_id = ?
              AND memory_layer = ?
              AND (expires_at IS NULL OR expires_at > ?)
            """,
            (project_id, memory_id, memory_layer, now),
        )

        total_strength = 0.0
        for row in cursor.fetchall():
            base_strength = row[0]
            inhibited_at = datetime.fromisoformat(row[1])
            expires_at = row[2]

            # Check explicit expiration
            if expires_at is not None:
                expires_at = datetime.fromisoformat(expires_at)
                if now >= expires_at:
                    continue

            # Apply exponential decay
            elapsed_seconds = (now - inhibited_at).total_seconds()
            decay_factor = 0.5 ** (elapsed_seconds / self.DEFAULT_HALF_LIFE_SECONDS)
            effective_strength = base_strength * decay_factor

            total_strength += effective_strength

        return min(1.0, total_strength)  # Cap at 1.0

    def decay_inhibitions(self, project_id: int, min_strength: float = 0.01) -> int:
        """Remove inhibitions that have decayed below threshold.

        Args:
            project_id: Project ID
            min_strength: Minimum strength to keep (default 0.01)

        Returns:
            Number of inhibitions removed
        """
        now = datetime.now()
        removed_count = 0

        # Get all inhibitions for project
        cursor = self.db.conn.execute(
            """
            SELECT id, inhibition_strength, inhibited_at, expires_at
            FROM attention_inhibition
            WHERE project_id = ?
            """,
            (project_id,),
        )

        to_remove = []
        for row in cursor.fetchall():
            inhibition_id = row[0]
            base_strength = row[1]
            inhibited_at = datetime.fromisoformat(row[2])
            expires_at = row[3]

            # Remove if explicitly expired
            if expires_at is not None:
                expires_at = datetime.fromisoformat(expires_at)
                if now >= expires_at:
                    to_remove.append(inhibition_id)
                    continue

            # Remove if decayed below threshold
            elapsed_seconds = (now - inhibited_at).total_seconds()
            decay_factor = 0.5 ** (elapsed_seconds / self.DEFAULT_HALF_LIFE_SECONDS)
            effective_strength = base_strength * decay_factor

            if effective_strength < min_strength:
                to_remove.append(inhibition_id)

        # Remove decayed inhibitions
        for inhibition_id in to_remove:
            self.db.conn.execute("DELETE FROM attention_inhibition WHERE id = ?", (inhibition_id,))
            removed_count += 1

        # commit handled by cursor context
        return removed_count

    def get_inhibited_memories(
        self, project_id: int, min_strength: float = 0.3
    ) -> List[InhibitionRecord]:
        """Get all currently inhibited memories above threshold.

        Args:
            project_id: Project ID
            min_strength: Minimum effective strength to include

        Returns:
            List of inhibition records with effective strength >= threshold
        """
        now = datetime.now()
        inhibited = []

        cursor = self.db.conn.execute(
            """
            SELECT id, project_id, memory_id, memory_layer,
                   inhibition_strength, inhibition_type, reason,
                   inhibited_at, expires_at
            FROM attention_inhibition
            WHERE project_id = ?
              AND (expires_at IS NULL OR expires_at > ?)
            """,
            (project_id, now),
        )

        for row in cursor.fetchall():
            base_strength = row[4]
            inhibited_at = datetime.fromisoformat(row[7])
            expires_at = row[8]

            # Calculate effective strength with decay
            elapsed_seconds = (now - inhibited_at).total_seconds()
            decay_factor = 0.5 ** (elapsed_seconds / self.DEFAULT_HALF_LIFE_SECONDS)
            effective_strength = base_strength * decay_factor

            # Only include if above threshold
            if effective_strength >= min_strength:
                record = InhibitionRecord(
                    id=row[0],
                    project_id=row[1],
                    memory_id=row[2],
                    memory_layer=row[3],
                    inhibition_strength=effective_strength,  # Use effective strength
                    inhibition_type=InhibitionType(row[5]),
                    reason=row[6],
                    inhibited_at=inhibited_at,
                    expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
                )
                inhibited.append(record)

        return inhibited

    def get_all_inhibitions(self, project_id: int) -> List[InhibitionRecord]:
        """Get all inhibition records for a project (including expired).

        Args:
            project_id: Project ID

        Returns:
            List of all inhibition records
        """
        cursor = self.db.conn.execute(
            """
            SELECT id, project_id, memory_id, memory_layer,
                   inhibition_strength, inhibition_type, reason,
                   inhibited_at, expires_at
            FROM attention_inhibition
            WHERE project_id = ?
            ORDER BY inhibited_at DESC
            """,
            (project_id,),
        )

        records = []
        for row in cursor.fetchall():
            record = InhibitionRecord(
                id=row[0],
                project_id=row[1],
                memory_id=row[2],
                memory_layer=row[3],
                inhibition_strength=row[4],
                inhibition_type=InhibitionType(row[5]),
                reason=row[6],
                inhibited_at=datetime.fromisoformat(row[7]),
                expires_at=datetime.fromisoformat(row[8]) if row[8] else None,
            )
            records.append(record)

        return records
