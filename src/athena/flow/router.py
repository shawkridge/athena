"""Memory flow router - main orchestrator for information flow management.

Coordinates activation dynamics, tier management, consolidation, and search across
the 8-layer memory system using neuroscience-inspired principles.
"""

from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .activation import ActivationSystem
from .capacity import TierCapacityManager
from .consolidation import SelectiveConsolidationEngine, TemporalClusteringEngine
from .queries import QueryRouter
from .models import FlowStatistics, MemoryTier


class MemoryFlowRouter:
    """Orchestrates memory flow across episodic → session → semantic layers.

    Implements:
    1. Activation dynamics (temporal decay + RIF)
    2. Tier management (7±2 working, ~100 session, unlimited episodic)
    3. Selective consolidation (strong→semantic, weak→decay)
    4. Temporal clustering (group related items)
    5. Hot-first query routing
    """

    def __init__(self, db: Database):
        """Initialize memory flow router.

        Args:
            db: Database instance
        """
        self.db = db

        # Initialize subsystems
        self.activation = ActivationSystem(db)
        self.capacity = TierCapacityManager(db)
        self.consolidation = SelectiveConsolidationEngine(db)
        self.clustering = TemporalClusteringEngine(db)
        self.queries = QueryRouter(db)

    async def record_event_access(
        self, event_id: int, boost: float = 0.5
    ) -> None:
        """Record event access, triggering activation boost and RIF.

        When an event is accessed:
        1. Boost its activation
        2. Suppress similar items (RIF)
        3. Attempt promotion to working memory
        4. Enforce tier capacity limits

        Args:
            event_id: ID of event being accessed
            boost: Activation boost amount (0.0-1.0)
        """
        # Boost activation and apply RIF
        await self.activation.access_item(event_id, boost=boost)

        # Try to promote to working memory
        await self.capacity.promote_to_working_memory(event_id)

        # Enforce working memory limit
        await self.capacity.enforce_working_memory_limit()

    async def process_decay(self) -> dict[str, int]:
        """Apply temporal decay to all items and update activation levels.

        Called periodically (e.g., hourly) to update activation levels
        based on time elapsed since last access.

        Returns:
            Dict with stats: {'decayed': N, 'demoted': N, 'archived': N}
        """
        stats = {"decayed": 0, "demoted": 0, "archived": 0}

        # Apply temporal decay
        decayed = await self.activation.decay_all()
        stats["decayed"] = decayed

        # Enforce capacity limits
        demoted = await self.capacity.enforce_working_memory_limit()
        stats["demoted"] = demoted

        archived = await self.capacity.enforce_session_cache_limit()
        stats["archived"] = archived

        return stats

    async def run_consolidation_cycle(self) -> dict[str, int]:
        """Run selective consolidation based on activation.

        Consolidates strong items (activation > 0.7) to semantic memory
        and decays weak items (activation < 0.4).

        Returns:
            Dict with stats: {'promoted': N, 'maintained': N, 'decayed': N}
        """
        # Get strong items for consolidation
        candidates = await self.consolidation.get_consolidation_candidates()

        stats = {"promoted": 0, "maintained": 0, "decayed": 0}

        for event_id in candidates:
            if await self.consolidation.consolidate_event_to_semantic(event_id):
                stats["promoted"] += 1

        # Decay weak items
        decayed = await self.consolidation.decay_weak_items()
        stats["decayed"] = decayed

        return stats

    async def run_temporal_clustering(
        self, promote_all: bool = False
    ) -> dict[str, int]:
        """Run temporal clustering and consolidate related items together.

        Groups items by temporal proximity (default: 5-minute window) and
        consolidates them together to preserve temporal relationships.

        Args:
            promote_all: If True, promote all clusters. If False, only high-coherence.

        Returns:
            Dict with stats: {'clustered': N, 'consolidated': N}
        """
        # Cluster recent events
        clusters = await self.clustering.cluster_by_temporal_proximity()

        stats = {"clustered": len(clusters), "consolidated": 0}

        # Consolidate each cluster
        for cluster in clusters:
            consolidated = await self.clustering.consolidate_cluster(
                cluster, promote_all=promote_all
            )
            stats["consolidated"] += consolidated

        return stats

    async def get_working_memory(self, limit: int = 7) -> list[dict]:
        """Get current working memory items (active, high activation).

        Returns up to 7±2 most activated items currently in working memory.

        Args:
            limit: Maximum items to return (default: Baddeley's 7±2)

        Returns:
            List of working memory events
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, content, importance_score, actionability_score,
                       activation_count, last_activation
                FROM episodic_events
                WHERE lifecycle_status = 'active'
                ORDER BY (activation_count / NULLIF(EXTRACT(EPOCH FROM (NOW() - last_activation))/3600, 1)) DESC,
                         (importance_score * actionability_score) DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = await result.fetchall()

            items = []
            for row in rows:
                (
                    event_id,
                    content,
                    importance,
                    actionability,
                    access_count,
                    last_access,
                ) = row
                items.append(
                    {
                        "event_id": event_id,
                        "content": content[:200],
                        "importance": importance or 0.5,
                        "actionability": actionability or 0.5,
                        "access_count": access_count,
                        "last_access": last_access,
                    }
                )

            return items

    async def get_statistics(
        self, hours: int = 24
    ) -> Optional[FlowStatistics]:
        """Get flow system statistics for a time period.

        Args:
            hours: Time window for statistics

        Returns:
            FlowStatistics with detailed metrics
        """
        async with self.db.get_connection() as conn:
            # Get tier compositions
            result = await conn.execute(
                """
                SELECT
                  SUM(CASE WHEN lifecycle_status = 'active' THEN 1 ELSE 0 END) as working,
                  SUM(CASE WHEN lifecycle_status = 'session' THEN 1 ELSE 0 END) as session,
                  SUM(CASE WHEN consolidation_score > 0.7 THEN 1 ELSE 0 END) as promoted
                FROM episodic_events
                WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                """,
                (hours,),
            )
            row = await result.fetchone()
            working, session, promoted = (
                (row[0] or 0, row[1] or 0, row[2] or 0)
                if row
                else (0, 0, 0)
            )

            # Get activation statistics
            result = await conn.execute(
                """
                SELECT
                  AVG(activation_count) as mean_activation,
                  MAX(activation_count) as max_activation,
                  MIN(activation_count) as min_activation
                FROM episodic_events
                WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                """,
                (hours,),
            )
            row = await result.fetchone()
            mean_act, max_act, min_act = (
                (row[0] or 0, row[1] or 0, row[2] or 0)
                if row
                else (0, 0, 0)
            )

            return FlowStatistics(
                period_start=datetime.now() - timedelta(hours=hours),
                period_end=datetime.now(),
                working_memory_items=working,
                session_cache_items=session,
                promoted_to_semantic=promoted,
                decayed_items=0,  # Would need decay tracking table
                mean_activation=mean_act,
                max_interference=1.0,  # Would need RIF tracking
                consolidation_rate=promoted / (working + session + 1),
            )

    async def search_hot_first(
        self, query: str, limit: int = 10
    ) -> list[dict]:
        """Search memory hot-first: working → session → episodic.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching events ordered by tier and activation
        """
        return await self.queries.search_hot_first(query, limit=limit)

    async def get_consolidation_candidates(
        self, strength_threshold: float = 0.7
    ) -> list[dict]:
        """Get events ready for consolidation to semantic memory.

        Args:
            strength_threshold: Minimum activation for consolidation

        Returns:
            List of candidate events
        """
        candidates = await self.consolidation.get_consolidation_candidates(
            strength_threshold
        )

        # Get event details
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, content, importance_score, actionability_score,
                       consolidation_score, activation_count
                FROM episodic_events
                WHERE id = ANY(%s)
                ORDER BY consolidation_score DESC
                """,
                (candidates,),
            )
            rows = await result.fetchall()

            items = []
            for row in rows:
                (
                    event_id,
                    content,
                    importance,
                    actionability,
                    consol_score,
                    access_count,
                ) = row
                items.append(
                    {
                        "event_id": event_id,
                        "content": content[:200],
                        "importance": importance or 0.5,
                        "actionability": actionability or 0.5,
                        "consolidation_score": consol_score or 0.0,
                        "access_count": access_count,
                    }
                )

            return items

    async def get_flow_health(self) -> dict:
        """Get overall memory flow health metrics.

        Returns:
            Dict with health indicators and warnings
        """
        stats = await self.get_statistics(hours=1)
        tier_comp = await self.queries.get_tier_composition()

        health = {
            "working_memory_utilization": stats.working_memory_items / 7.0,
            "session_cache_utilization": stats.session_cache_items / 100.0,
            "consolidation_rate": stats.consolidation_rate,
            "tier_composition": tier_comp,
            "mean_activation": stats.mean_activation,
            "warnings": [],
        }

        # Check for warnings
        if health["working_memory_utilization"] > 0.95:
            health["warnings"].append("Working memory near capacity")
        if health["session_cache_utilization"] > 0.95:
            health["warnings"].append("Session cache near capacity")
        if health["consolidation_rate"] < 0.1:
            health["warnings"].append("Low consolidation rate")

        return health
