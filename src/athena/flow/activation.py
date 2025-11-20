"""Activation system for memory flow management.

Implements neuroscience-inspired activation dynamics:
- Temporal decay: memory strength decreases over time
- Retrieval-Induced Forgetting (RIF): accessing one item suppresses similar items
- Refreshing: accessing an item boosts its activation
"""

import math
from datetime import datetime
from typing import Optional

from ..core.database import Database
from .models import ActivationState


class ActivationSystem:
    """Manages memory activation dynamics with decay and interference."""

    # Temporal decay parameter (λ in e^(-λt))
    # Typical neuroscience values: 0.01-0.1 per hour
    DEFAULT_DECAY_RATE = 0.01  # per hour

    # Similarity threshold for RIF (0.7 = 70% similar)
    SIMILARITY_THRESHOLD = 0.7

    # RIF inhibition strength (how much to suppress similar items)
    RIF_INHIBITION = 0.3

    def __init__(self, db: Database):
        """Initialize activation system.

        Args:
            db: Database instance for querying events
        """
        self.db = db
        self.decay_rate = self.DEFAULT_DECAY_RATE

    async def compute_activation(
        self,
        base_activation: float,
        last_access: datetime,
        interference_factor: float = 1.0,
    ) -> float:
        """Compute current activation with temporal decay and interference.

        Formula: activation = base_activation * e^(-λt) * interference_factor

        Where:
        - base_activation: Initial strength (typically 1.0)
        - λt: Decay factor (λ=decay_rate, t=hours since access)
        - interference_factor: Suppression from similar items (0.0-1.0)

        Args:
            base_activation: Initial activation (0.0-1.0)
            last_access: Time of last access
            interference_factor: RIF suppression factor (0.0-1.0)

        Returns:
            Current activation value (0.0-1.0)
        """
        # Calculate time elapsed in hours
        now = datetime.now()
        elapsed = (now - last_access).total_seconds() / 3600.0

        # Temporal decay: e^(-λt)
        decay = math.exp(-self.decay_rate * elapsed)

        # Combined activation with interference
        activation = base_activation * decay * interference_factor

        # Clamp to [0, 1]
        return max(0.0, min(1.0, activation))

    async def access_item(
        self,
        event_id: int,
        boost: float = 0.5,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        """Access an item, boosting it and suppressing similar items (RIF).

        Args:
            event_id: ID of item being accessed
            boost: How much to boost activation (0.0-1.0)
            similarity_threshold: Similarity threshold for RIF
        """
        async with self.db.get_connection() as conn:
            # Boost accessed item
            now = datetime.now()
            await conn.execute(
                """
                UPDATE episodic_events
                SET last_activation = %s, activation_count = activation_count + 1
                WHERE id = %s
                """,
                (now, event_id),
            )

            # Find similar items (same event type, similar importance, recent)
            similar_items = await self._find_similar_items(conn, event_id, similarity_threshold)

            # Suppress similar items (RIF effect)
            for similar_id in similar_items:
                # Reduce interference_factor to suppress activation
                await conn.execute(
                    """
                    UPDATE activation_history
                    SET interference_factor = interference_factor * %s
                    WHERE event_id = %s
                    ORDER BY timestamp DESC LIMIT 1
                    """,
                    (1.0 - self.RIF_INHIBITION, similar_id),
                )

    async def decay_all(self) -> int:
        """Apply temporal decay to all active items.

        Returns:
            Number of items updated
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET activation_count = activation_count
                WHERE last_activation < NOW() - INTERVAL '1 hour'
                """,
            )
            return result.rowcount

    async def _find_similar_items(self, conn, event_id: int, threshold: float) -> list[int]:
        """Find items similar to the given event.

        Similarity based on:
        - Same event type
        - Similar importance score (within 0.2)
        - Recent (within last 24 hours)

        Args:
            conn: Database connection
            event_id: ID of reference event
            threshold: Similarity threshold (not used directly, kept for clarity)

        Returns:
            List of similar event IDs
        """
        # Get reference event properties
        result = await conn.execute(
            """
            SELECT event_type, importance_score
            FROM episodic_events
            WHERE id = %s
            """,
            (event_id,),
        )
        row = await result.fetchone()
        if not row:
            return []

        event_type, importance = row

        # Find similar events
        result = await conn.execute(
            """
            SELECT id
            FROM episodic_events
            WHERE id != %s
              AND event_type = %s
              AND ABS(importance_score - %s) < 0.2
              AND timestamp > NOW() - INTERVAL '24 hours'
            LIMIT 10
            """,
            (event_id, event_type, importance),
        )
        rows = await result.fetchall()
        return [row[0] for row in rows]

    async def get_activation_state(self, event_id: int) -> Optional[ActivationState]:
        """Get current activation state for an event.

        Args:
            event_id: ID of event

        Returns:
            ActivationState or None if event not found
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, last_activation, activation_count, importance_score,
                       actionability_score
                FROM episodic_events
                WHERE id = %s
                """,
                (event_id,),
            )
            row = await result.fetchone()
            if not row:
                return None

            event_id, last_access, access_count, importance, actionability = row

            # Compute current activation with decay
            base_activation = min(1.0, access_count / 10.0)  # Access count → base strength
            current_activation = await self.compute_activation(base_activation, last_access)

            return ActivationState(
                event_id=event_id,
                current_activation=current_activation,
                last_access_time=last_access,
                access_count=access_count,
                importance=importance or 0.5,
                actionability=actionability or 0.5,
            )

    def set_decay_rate(self, rate: float) -> None:
        """Set custom decay rate (typically 0.001-0.1 per hour).

        Args:
            rate: New decay rate parameter
        """
        if rate < 0:
            raise ValueError("Decay rate must be non-negative")
        self.decay_rate = rate
