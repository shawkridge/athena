"""Temporal priming for memory activation.

Recently accessed memories have boosted activation for a short period,
modeling the psychological priming effect where recent exposure facilitates
subsequent retrieval.
"""

from datetime import datetime, timedelta, timezone
from typing import List

from ..core.database import Database
from .models import PrimedMemory


class TemporalPriming:
    """
    Manage temporal priming effects.

    Priming gives recently accessed memories a temporary activation boost:
    - Short-term (0-5 min): 2.0x boost
    - Medium-term (5-30 min): 1.5x boost
    - Long-term (30-60 min): 1.2x boost
    - After 60 min: No boost (priming expired)

    This models the psychological finding that recent exposure to a concept
    makes it more accessible in subsequent retrieval.
    """

    def __init__(self, db: Database):
        """Initialize temporal priming tracker.

        Args:
            db: Database connection
        """
        self.db = db

    def prime(
        self,
        memory_id: int,
        layer: str,
        project_id: int,
        duration_seconds: int = 300,
    ) -> int:
        """Prime a memory for temporary activation boost.

        If memory is already primed, refresh the priming duration.

        Args:
            memory_id: Memory ID to prime
            layer: Memory layer
            project_id: Project ID
            duration_seconds: Priming duration in seconds (default 300 = 5 min)

        Returns:
            Priming record ID
        """
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)

        with self.db.get_connection() as conn:
            # Check if already primed
            existing = conn.execute(
                """
                SELECT id FROM priming_state
                WHERE project_id = ? AND memory_id = ? AND memory_layer = ?
                AND expires_at > datetime('now', 'utc')
                """,
                (project_id, memory_id, layer),
            ).fetchone()

            if existing:
                # Refresh priming
                conn.execute(
                    """
                    UPDATE priming_state
                    SET priming_strength = 1.0,
                        primed_at = datetime('now', 'utc'),
                        expires_at = ?
                    WHERE id = ?
                    """,
                    (expires_at.isoformat().replace("T", " ").split("+")[0], existing["id"]),
                )
                conn.commit()
                return existing["id"]

            # Create new priming
            # Normalize timestamps to SQLite format (remove T and timezone)
            now_iso = datetime.now(timezone.utc).isoformat().replace("T", " ").split("+")[0]
            expires_iso = expires_at.isoformat().replace("T", " ").split("+")[0]

            cursor = conn.execute(
                """
                INSERT INTO priming_state (
                    project_id, memory_id, memory_layer,
                    priming_strength, primed_at, expires_at
                )
                VALUES (?, ?, ?, 1.0, ?, ?)
                """,
                (project_id, memory_id, layer, now_iso, expires_iso),
            )
            conn.commit()
            return cursor.lastrowid

    def get_priming_boost(self, memory_id: int, layer: str, project_id: int) -> float:
        """Get current priming boost multiplier for a memory.

        Boost depends on time since priming:
        - 0-5 min: 2.0x
        - 5-30 min: 1.5x
        - 30-60 min: 1.2x
        - >60 min: 1.0x (no boost)

        Args:
            memory_id: Memory ID
            layer: Memory layer
            project_id: Project ID

        Returns:
            Priming boost multiplier (1.0 = no boost, >1.0 = boosted)
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT primed_at, expires_at FROM priming_state
                WHERE project_id = ? AND memory_id = ? AND memory_layer = ?
                AND expires_at > datetime('now', 'utc')
                ORDER BY primed_at DESC
                LIMIT 1
                """,
                (project_id, memory_id, layer),
            ).fetchone()

            if not result:
                return 1.0  # No priming

            primed_at_str = result["primed_at"]
            # Handle various datetime formats from SQLite
            # Try parsing directly, then with timezone if needed
            try:
                # SQLite format: '2025-10-21 10:38:03.507276'
                primed_at = datetime.fromisoformat(primed_at_str)
                if primed_at.tzinfo is None:
                    primed_at = primed_at.replace(tzinfo=timezone.utc)
            except ValueError:
                # ISO format with timezone: '2025-10-21T10:38:03.507276+00:00'
                primed_at = datetime.fromisoformat(primed_at_str)

            elapsed = (datetime.now(timezone.utc) - primed_at).total_seconds() / 60.0  # minutes

            # Apply time-decay function
            if elapsed < 5:
                return 2.0  # Short-term: strong boost
            elif elapsed < 30:
                return 1.5  # Medium-term: moderate boost
            elif elapsed < 60:
                return 1.2  # Long-term: weak boost
            else:
                return 1.0  # Expired

    def decay_priming(self, project_id: int, decay_rate: float = 0.1) -> int:
        """Apply decay to all priming strengths.

        Gradually reduces priming over time. Priming below 0.1 is removed.

        Args:
            project_id: Project ID
            decay_rate: Amount to decrease priming strength (default 0.1)

        Returns:
            Number of priming records decayed
        """
        if not 0.0 < decay_rate < 1.0:
            raise ValueError("decay_rate must be between 0.0 and 1.0")

        with self.db.get_connection() as conn:
            # Decay priming
            conn.execute(
                """
                UPDATE priming_state
                SET priming_strength = MAX(0.0, priming_strength - ?)
                WHERE project_id = ?
                """,
                (decay_rate, project_id),
            )

            # Remove weak priming
            cursor = conn.execute(
                """
                DELETE FROM priming_state
                WHERE project_id = ? AND priming_strength < 0.1
                """,
                (project_id,),
            )
            conn.commit()
            return cursor.rowcount

    def expire_old_priming(self, project_id: int) -> int:
        """Remove expired priming records.

        Args:
            project_id: Project ID

        Returns:
            Number of priming records expired
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM priming_state
                WHERE project_id = ? AND expires_at <= datetime('now', 'utc')
                """,
                (project_id,),
            )
            conn.commit()
            return cursor.rowcount

    def get_primed_memories(self, project_id: int, min_boost: float = 1.2) -> List[PrimedMemory]:
        """Get all currently primed memories with boost >= threshold.

        Args:
            project_id: Project ID
            min_boost: Minimum boost threshold (default 1.2)

        Returns:
            List of primed memories sorted by priming strength (descending)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    memory_id, memory_layer, priming_strength,
                    primed_at, expires_at
                FROM priming_state
                WHERE project_id = ?
                AND expires_at > datetime('now', 'utc')
                ORDER BY priming_strength DESC
                """,
                (project_id,),
            )

            memories = []
            for row in cursor.fetchall():
                primed_at = datetime.fromisoformat(row["primed_at"])
                expires_at = datetime.fromisoformat(row["expires_at"])

                # Calculate actual boost
                memory_id = row["memory_id"]
                layer = row["memory_layer"]
                boost = self.get_priming_boost(memory_id, layer, project_id)

                # Only include if boost >= threshold
                if boost >= min_boost:
                    memories.append(
                        PrimedMemory(
                            memory_id=memory_id,
                            memory_layer=layer,
                            priming_strength=boost,
                            primed_at=primed_at,
                            expires_at=expires_at,
                        )
                    )

            return memories

    def clear_priming(self, project_id: int) -> int:
        """Clear all priming state for a project.

        Args:
            project_id: Project ID

        Returns:
            Number of priming records cleared
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM priming_state WHERE project_id = ?",
                (project_id,),
            )
            conn.commit()
            return cursor.rowcount

    def get_priming_count(self, project_id: int) -> int:
        """Get count of active priming records.

        Args:
            project_id: Project ID

        Returns:
            Number of active priming records
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT COUNT(*) as count FROM priming_state
                WHERE project_id = ? AND expires_at > CURRENT_TIMESTAMP
                """,
                (project_id,),
            ).fetchone()
            return result["count"] if result else 0
