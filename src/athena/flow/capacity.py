"""Tier capacity management for memory flow system.

Enforces Baddeley's working memory limit (7±2 items) and manages
movement between working memory → session cache → episodic archive.
"""


from ..core.database import Database


class TierCapacityManager:
    """Manages tier capacity limits and promotion/demotion."""

    # Baddeley's working memory limit: 7±2 items
    WORKING_MEMORY_HARD_LIMIT = 7
    WORKING_MEMORY_SOFT_LIMIT = 9

    # Session cache soft limit (warm items kept in memory)
    SESSION_CACHE_SOFT_LIMIT = 100

    def __init__(self, db: Database):
        """Initialize capacity manager.

        Args:
            db: Database instance
        """
        self.db = db

    async def get_tier_sizes(self) -> dict[str, int]:
        """Get current size of each tier.

        Returns:
            Dict with 'working', 'session', 'episodic' counts
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT
                  SUM(CASE WHEN lifecycle_status = 'active' THEN 1 ELSE 0 END) as working_count,
                  SUM(CASE WHEN lifecycle_status = 'session' THEN 1 ELSE 0 END) as session_count,
                  SUM(CASE WHEN lifecycle_status = 'archived' THEN 1 ELSE 0 END) as archived_count
                FROM episodic_events
                """,
            )
            row = await result.fetchone()
            if row:
                return {
                    "working": row[0] or 0,
                    "session": row[1] or 0,
                    "episodic": row[2] or 0,
                }
            return {"working": 0, "session": 0, "episodic": 0}

    async def enforce_working_memory_limit(self) -> int:
        """Enforce hard limit on working memory (7±2).

        If working memory exceeds hard limit, demote lowest-activation items
        to session cache.

        Returns:
            Number of items demoted
        """
        async with self.db.get_connection() as conn:
            # Get current working memory size
            result = await conn.execute(
                """
                SELECT COUNT(*) FROM episodic_events
                WHERE lifecycle_status = 'active'
                """,
            )
            current_size = (await result.fetchone())[0]

            if current_size <= self.WORKING_MEMORY_HARD_LIMIT:
                return 0

            # Need to demote: current - hard_limit items
            to_demote = current_size - self.WORKING_MEMORY_HARD_LIMIT

            # Demote lowest-activation items
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'session'
                WHERE id IN (
                  SELECT id FROM episodic_events
                  WHERE lifecycle_status = 'active'
                  ORDER BY (activation_count / NULLIF(EXTRACT(EPOCH FROM (NOW() - last_activation))/3600, 0))
                  LIMIT %s
                )
                RETURNING id
                """,
                (to_demote,),
            )
            rows = await result.fetchall()
            return len(rows) if rows else 0

    async def promote_to_working_memory(self, event_id: int) -> bool:
        """Try to promote item to working memory.

        May fail if working memory is at hard limit and item activation
        is not high enough to justify demotion of other items.

        Args:
            event_id: ID of event to promote

        Returns:
            True if promoted, False if unable
        """
        async with self.db.get_connection() as conn:
            # Check current size
            result = await conn.execute(
                """
                SELECT COUNT(*) FROM episodic_events
                WHERE lifecycle_status = 'active'
                """,
            )
            current_size = (await result.fetchone())[0]

            # If room available, promote directly
            if current_size < self.WORKING_MEMORY_SOFT_LIMIT:
                await conn.execute(
                    """
                    UPDATE episodic_events
                    SET lifecycle_status = 'active'
                    WHERE id = %s
                    """,
                    (event_id,),
                )
                return True

            # If at soft limit, check if new item's activation justifies demotion
            result = await conn.execute(
                """
                SELECT importance_score * actionability_score as score
                FROM episodic_events
                WHERE id = %s
                """,
                (event_id,),
            )
            new_item_score = (await result.fetchone())[0] if await result.fetchone() else 0

            # Find lowest-activation item currently in working memory
            result = await conn.execute(
                """
                SELECT id, importance_score * actionability_score as score
                FROM episodic_events
                WHERE lifecycle_status = 'active'
                ORDER BY score ASC
                LIMIT 1
                """,
            )
            row = await result.fetchone()
            lowest_id, lowest_score = row if row else (None, 0)

            # Only demote if new item is significantly better
            if new_item_score > lowest_score * 1.2:  # 20% threshold
                await conn.execute(
                    """
                    UPDATE episodic_events
                    SET lifecycle_status = 'session'
                    WHERE id = %s
                    """,
                    (lowest_id,),
                )
                await conn.execute(
                    """
                    UPDATE episodic_events
                    SET lifecycle_status = 'active'
                    WHERE id = %s
                    """,
                    (event_id,),
                )
                return True

            # Could not promote
            return False

    async def promote_to_session_cache(self, event_id: int) -> bool:
        """Promote item from episodic archive to session cache.

        Args:
            event_id: ID of event to promote

        Returns:
            True if promoted
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'session'
                WHERE id = %s AND lifecycle_status = 'archived'
                RETURNING id
                """,
                (event_id,),
            )
            return (await result.fetchone()) is not None

    async def demote_to_episodic_archive(self, event_id: int) -> bool:
        """Demote item from session cache to episodic archive.

        Args:
            event_id: ID of event to demote

        Returns:
            True if demoted
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'archived'
                WHERE id = %s AND lifecycle_status = 'session'
                RETURNING id
                """,
                (event_id,),
            )
            return (await result.fetchone()) is not None

    async def enforce_session_cache_limit(self) -> int:
        """Enforce soft limit on session cache (~100 items).

        Removes oldest items from session cache when limit exceeded.

        Returns:
            Number of items archived
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT COUNT(*) FROM episodic_events
                WHERE lifecycle_status = 'session'
                """,
            )
            current_size = (await result.fetchone())[0]

            if current_size <= self.SESSION_CACHE_SOFT_LIMIT:
                return 0

            to_archive = current_size - self.SESSION_CACHE_SOFT_LIMIT

            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'archived'
                WHERE id IN (
                  SELECT id FROM episodic_events
                  WHERE lifecycle_status = 'session'
                  ORDER BY last_activation ASC
                  LIMIT %s
                )
                RETURNING id
                """,
                (to_archive,),
            )
            rows = await result.fetchall()
            return len(rows) if rows else 0
