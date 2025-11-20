"""Reconsolidation activation on memory retrieval.

Implements neuroscience-inspired reconsolidation: when a memory is retrieved,
it becomes labile (modifiable) for a time window, allowing updates and corrections.

Research: Nader & Hardt (2009), Nature Reviews Neuroscience
- Retrieved memories are temporarily unstable
- Can be updated with new information
- Window typically 5-6 hours, we use 60 minutes for AI
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database

logger = logging.getLogger(__name__)


class ReconsolidationActivator:
    """Manages reconsolidation windows for memories after retrieval."""

    RECONSOLIDATION_WINDOW_MINUTES = 60  # How long memory stays labile
    LABILITY_STATE = "labile"
    CONSOLIDATED_STATE = "consolidated"

    def __init__(self, db: Database):
        """Initialize activator.

        Args:
            db: Database instance
        """
        self.db = db

    async def mark_retrieved_memory_labile(
        self, event_id: int, window_minutes: int = RECONSOLIDATION_WINDOW_MINUTES
    ) -> bool:
        """Mark an episodic event as labile after retrieval.

        When a memory is retrieved and used, it becomes temporarily modifiable.
        This implements the neuroscience principle of reconsolidation.

        Args:
            event_id: ID of the retrieved event
            window_minutes: Duration of lability window (default 60 min)

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            async with self.db.get_connection() as conn:
                # Update lifecycle_status to indicate lability
                await conn.execute(
                    """
                    UPDATE episodic_events
                    SET lifecycle_status = %s,
                        last_activation = NOW()
                    WHERE id = %s
                    """,
                    (self.LABILITY_STATE, event_id),
                )
                logger.debug(f"Memory {event_id} marked labile (window: {window_minutes} min)")
                return True
        except Exception as e:
            logger.error(f"Error marking memory {event_id} labile: {e}")
            return False

    async def is_in_reconsolidation_window(self, event_id: int) -> bool:
        """Check if memory is still in reconsolidation window.

        Args:
            event_id: ID of the event to check

        Returns:
            True if memory is labile and within time window
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT lifecycle_status, last_activation
                    FROM episodic_events
                    WHERE id = %s
                    """,
                    (event_id,),
                )
                row = await result.fetchone()

                if not row:
                    return False

                status, last_activation = row
                if status != self.LABILITY_STATE:
                    return False

                # Check if still within window
                now = datetime.now()
                window_end = last_activation + timedelta(
                    minutes=self.RECONSOLIDATION_WINDOW_MINUTES
                )
                return now < window_end

        except Exception as e:
            logger.error(f"Error checking reconsolidation window for {event_id}: {e}")
            return False

    async def consolidate_labile_memories(self) -> int:
        """Consolidate all labile memories (move back to active state).

        Called during consolidation dream to close out lability windows
        and finalize any updates that occurred.

        Returns:
            Number of memories consolidated
        """
        try:
            async with self.db.get_connection() as conn:
                # Find labile memories outside their window
                result = await conn.execute(
                    f"""
                    SELECT id, last_activation
                    FROM episodic_events
                    WHERE lifecycle_status = %s
                    AND NOW() > last_activation + INTERVAL '{self.RECONSOLIDATION_WINDOW_MINUTES} minutes'
                    """,
                    (self.LABILITY_STATE,),
                )

                labile_rows = await result.fetchall()
                count = len(labile_rows)

                if count > 0:
                    # Move them back to consolidated
                    ids = [row[0] for row in labile_rows]
                    placeholders = ",".join(["%s"] * len(ids))

                    await conn.execute(
                        f"""
                        UPDATE episodic_events
                        SET lifecycle_status = %s
                        WHERE id IN ({placeholders})
                        """,
                        ([self.CONSOLIDATED_STATE] + ids),
                    )

                    logger.info(f"Consolidated {count} labile memories (window expired)")

                return count

        except Exception as e:
            logger.error(f"Error consolidating labile memories: {e}")
            return 0

    async def get_labile_memories(self, project_id: Optional[int] = None) -> list[dict]:
        """Get all currently labile memories.

        Useful for understanding what memories are pending update during dreams.

        Args:
            project_id: Optional filter by project

        Returns:
            List of labile event records
        """
        try:
            async with self.db.get_connection() as conn:
                if project_id:
                    result = await conn.execute(
                        """
                        SELECT id, content, event_type, last_activation, activation_count
                        FROM episodic_events
                        WHERE lifecycle_status = %s AND project_id = %s
                        ORDER BY last_activation DESC
                        """,
                        (self.LABILITY_STATE, project_id),
                    )
                else:
                    result = await conn.execute(
                        """
                        SELECT id, content, event_type, last_activation, activation_count
                        FROM episodic_events
                        WHERE lifecycle_status = %s
                        ORDER BY last_activation DESC
                        """,
                        (self.LABILITY_STATE,),
                    )

                rows = await result.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving labile memories: {e}")
            return []
