"""Query routing for memory flow system.

Implements hot-first search: searches working memory → session cache → episodic
archive to optimize for recency and activation.
"""


from ..core.database import Database


class QueryRouter:
    """Routes queries through memory tiers in hot-first order."""

    def __init__(self, db: Database):
        """Initialize query router.

        Args:
            db: Database instance
        """
        self.db = db

    async def search_hot_first(
        self, query: str, limit: int = 10, similarity_threshold: float = 0.7
    ) -> list[dict]:
        """Search memory tiers in hot-first order: working → session → episodic.

        Implements progressive search:
        1. First search working memory (most active, ~7 items)
        2. If insufficient results, search session cache (~100 items)
        3. If still insufficient, search episodic archive (unlimited)

        Each tier search is fast (indexed on lifecycle_status + timestamp).

        Args:
            query: Search query/content
            limit: Maximum results to return
            similarity_threshold: Minimum relevance score (0.0-1.0)

        Returns:
            List of matching events with scores, ordered by tier then activation
        """
        results = []

        # Search working memory first (most active, hot items)
        working_results = await self._search_tier("active", query, limit, similarity_threshold)
        results.extend(working_results)

        # If working memory didn't provide enough results, search session cache
        if len(results) < limit:
            session_results = await self._search_tier(
                "session", query, limit - len(results), similarity_threshold
            )
            results.extend(session_results)

        # If session cache also insufficient, search episodic archive
        if len(results) < limit:
            episodic_results = await self._search_tier(
                "archived", query, limit - len(results), similarity_threshold
            )
            results.extend(episodic_results)

        return results[:limit]

    async def _search_tier(self, tier: str, query: str, limit: int, threshold: float) -> list[dict]:
        """Search a single memory tier.

        Args:
            tier: Lifecycle status ('active', 'session', 'archived')
            query: Search query
            limit: Results limit
            threshold: Similarity threshold

        Returns:
            List of matching events with tier and activation info
        """
        async with self.db.get_connection() as conn:
            # Search by content match and activation
            result = await conn.execute(
                """
                SELECT
                  id, content, importance_score, actionability_score,
                  activation_count, last_activation, lifecycle_status,
                  CASE
                    WHEN content ILIKE %s THEN 1.0
                    WHEN content ILIKE %s THEN 0.8
                    ELSE 0.5
                  END as relevance_score,
                  (activation_count / NULLIF(EXTRACT(EPOCH FROM (NOW() - last_activation))/3600, 1))
                    as activation_strength
                FROM episodic_events
                WHERE lifecycle_status = %s
                  AND (content ILIKE %s OR content ILIKE %s)
                ORDER BY activation_strength DESC, last_activation DESC
                LIMIT %s
                """,
                (
                    f"%{query}%",
                    f"%{query.split()[0]}%",
                    tier,
                    f"%{query}%",
                    f"%{query.split()[0]}%",
                    limit,
                ),
            )
            rows = await result.fetchall()

            results = []
            for row in rows:
                (
                    event_id,
                    content,
                    importance,
                    actionability,
                    access_count,
                    last_access,
                    lifecycle_status,
                    relevance,
                    activation_strength,
                ) = row

                # Only include if above threshold
                if relevance >= threshold:
                    results.append(
                        {
                            "event_id": event_id,
                            "content": content[:200],  # Summary
                            "importance": importance or 0.5,
                            "actionability": actionability or 0.5,
                            "access_count": access_count,
                            "last_access": last_access,
                            "tier": lifecycle_status,
                            "relevance_score": relevance,
                            "activation_strength": activation_strength or 0.0,
                        }
                    )

            return results

    async def search_by_importance(
        self, min_importance: float = 0.5, limit: int = 20
    ) -> list[dict]:
        """Search for high-importance items across all tiers.

        Useful for extracting important findings for consolidation.

        Args:
            min_importance: Minimum importance score (0.0-1.0)
            limit: Maximum results

        Returns:
            List of important events
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, content, importance_score, actionability_score,
                       lifecycle_status, last_activation,
                       (importance_score * actionability_score) as combined_score
                FROM episodic_events
                WHERE importance_score >= %s
                ORDER BY combined_score DESC, last_activation DESC
                LIMIT %s
                """,
                (min_importance, limit),
            )
            rows = await result.fetchall()

            results = []
            for row in rows:
                (
                    event_id,
                    content,
                    importance,
                    actionability,
                    tier,
                    last_access,
                    combined_score,
                ) = row
                results.append(
                    {
                        "event_id": event_id,
                        "content": content[:200],
                        "importance": importance,
                        "actionability": actionability,
                        "tier": tier,
                        "last_access": last_access,
                        "combined_score": combined_score,
                    }
                )

            return results

    async def search_by_recency(self, hours: int = 1, limit: int = 20) -> list[dict]:
        """Search for recent items (high activation).

        Args:
            hours: Time window (hours)
            limit: Maximum results

        Returns:
            List of recent events
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, content, importance_score, actionability_score,
                       lifecycle_status, last_activation,
                       EXTRACT(EPOCH FROM (NOW() - last_activation))/3600 as hours_ago
                FROM episodic_events
                WHERE last_activation > NOW() - INTERVAL '1 hour' * %s
                ORDER BY last_activation DESC
                LIMIT %s
                """,
                (hours, limit),
            )
            rows = await result.fetchall()

            results = []
            for row in rows:
                (
                    event_id,
                    content,
                    importance,
                    actionability,
                    tier,
                    last_access,
                    hours_ago,
                ) = row
                results.append(
                    {
                        "event_id": event_id,
                        "content": content[:200],
                        "importance": importance,
                        "actionability": actionability,
                        "tier": tier,
                        "hours_ago": hours_ago,
                    }
                )

            return results

    async def get_tier_composition(self) -> dict[str, int]:
        """Get count of items in each tier.

        Returns:
            Dict with tier names and item counts
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT lifecycle_status, COUNT(*) as count
                FROM episodic_events
                GROUP BY lifecycle_status
                """,
            )
            rows = await result.fetchall()

            composition = {}
            for tier, count in rows:
                composition[tier or "unknown"] = count

            return composition
