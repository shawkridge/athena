"""Consolidation engines for memory flow system.

Implements selective consolidation (based on activation) and temporal clustering
(grouping related items by proximity).
"""

from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .models import TemporalCluster, ConsolidationRule, MemoryTier


class SelectiveConsolidationEngine:
    """Selective consolidation based on activation strength.

    Rules:
    - Strong (activation > 0.7) → Promote to semantic
    - Medium (0.4-0.7) → Keep in session cache
    - Weak (< 0.4) → Decay/archive
    """

    # Consolidation thresholds
    STRONG_ACTIVATION_THRESHOLD = 0.7
    MEDIUM_ACTIVATION_THRESHOLD = 0.4

    def __init__(self, db: Database):
        """Initialize consolidation engine.

        Args:
            db: Database instance
        """
        self.db = db

    async def get_consolidation_candidates(
        self, activation_threshold: float = STRONG_ACTIVATION_THRESHOLD
    ) -> list[int]:
        """Get events ready for consolidation to semantic memory.

        Selects events with:
        - High activation (> threshold)
        - High importance and actionability
        - Recent activity

        Args:
            activation_threshold: Minimum activation for consolidation

        Returns:
            List of event IDs ready for consolidation
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id
                FROM episodic_events
                WHERE (activation_count / NULLIF(EXTRACT(EPOCH FROM (NOW() - last_activation))/3600, 1)) > %s
                  AND importance_score > 0.6
                  AND actionability_score > 0.5
                  AND lifecycle_status IN ('active', 'session')
                ORDER BY (importance_score * actionability_score) DESC
                LIMIT 50
                """,
                (activation_threshold,),
            )
            rows = await result.fetchall()
            return [row[0] for row in rows]

    async def consolidate_event_to_semantic(self, event_id: int) -> bool:
        """Consolidate a single event to semantic memory.

        Marks event as consolidated and updates consolidation score.

        Args:
            event_id: ID of event to consolidate

        Returns:
            True if successful
        """
        async with self.db.get_connection() as conn:
            now = datetime.now()
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'consolidated',
                    consolidation_score = 1.0,
                    last_activation = %s
                WHERE id = %s AND lifecycle_status IN ('active', 'session')
                RETURNING id
                """,
                (now, event_id),
            )
            return (await result.fetchone()) is not None

    async def decay_weak_items(
        self, activation_threshold: float = MEDIUM_ACTIVATION_THRESHOLD
    ) -> int:
        """Decay items with weak activation to archive.

        Args:
            activation_threshold: Maximum activation for decay

        Returns:
            Number of items decayed
        """
        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = 'archived'
                WHERE (activation_count / NULLIF(EXTRACT(EPOCH FROM (NOW() - last_activation))/3600, 1)) < %s
                  AND lifecycle_status = 'session'
                RETURNING id
                """,
                (activation_threshold,),
            )
            rows = await result.fetchall()
            return len(rows) if rows else 0

    async def apply_consolidation_rules(
        self, rules: list[ConsolidationRule]
    ) -> dict[str, int]:
        """Apply custom consolidation rules.

        Args:
            rules: List of consolidation rules to apply

        Returns:
            Dict with action counts: {'promoted': N, 'maintained': N, 'decayed': N}
        """
        stats = {"promoted": 0, "maintained": 0, "decayed": 0}

        for rule in rules:
            if rule.action == "promote":
                candidates = await self.get_consolidation_candidates(rule.min_activation)
                for event_id in candidates:
                    if await self.consolidate_event_to_semantic(event_id):
                        stats["promoted"] += 1
            elif rule.action == "decay":
                decayed = await self.decay_weak_items(rule.min_activation)
                stats["decayed"] += decayed
            elif rule.action == "maintain":
                stats["maintained"] += 1

        return stats


class TemporalClusteringEngine:
    """Groups temporally-related events for consolidated consolidation.

    Clusters events that occur within a time window (default: 300 seconds)
    and consolidates them together to preserve temporal relationships.
    """

    # Default time window for clustering (300 seconds = 5 minutes)
    DEFAULT_WINDOW_SECONDS = 300

    def __init__(self, db: Database, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        """Initialize clustering engine.

        Args:
            db: Database instance
            window_seconds: Time window for clustering
        """
        self.db = db
        self.window_seconds = window_seconds

    async def cluster_by_temporal_proximity(
        self, min_importance: float = 0.5
    ) -> list[TemporalCluster]:
        """Cluster events by temporal proximity.

        Algorithm:
        1. Sort events by timestamp
        2. Group consecutive events within time window
        3. Compute cluster coherence score
        4. Return clusters with high coherence

        Args:
            min_importance: Minimum importance for inclusion

        Returns:
            List of temporal clusters
        """
        async with self.db.get_connection() as conn:
            # Get recent events
            result = await conn.execute(
                """
                SELECT id, timestamp, importance_score, actionability_score
                FROM episodic_events
                WHERE importance_score >= %s
                  AND timestamp > NOW() - INTERVAL '24 hours'
                ORDER BY timestamp ASC
                """,
                (min_importance,),
            )
            rows = await result.fetchall()

            if not rows:
                return []

            clusters = []
            current_cluster = []
            cluster_start = None

            for event_id, timestamp, importance, actionability in rows:
                if not current_cluster:
                    # Start new cluster
                    cluster_start = timestamp
                    current_cluster.append(
                        {
                            "id": event_id,
                            "timestamp": timestamp,
                            "importance": importance,
                            "actionability": actionability,
                        }
                    )
                else:
                    # Check if within time window
                    time_diff = (timestamp - cluster_start).total_seconds()
                    if time_diff <= self.window_seconds:
                        # Add to current cluster
                        current_cluster.append(
                            {
                                "id": event_id,
                                "timestamp": timestamp,
                                "importance": importance,
                                "actionability": actionability,
                            }
                        )
                    else:
                        # Finalize current cluster and start new one
                        if current_cluster:
                            cluster = await self._finalize_cluster(
                                clusters, current_cluster, cluster_start
                            )
                            clusters.append(cluster)
                        cluster_start = timestamp
                        current_cluster = [
                            {
                                "id": event_id,
                                "timestamp": timestamp,
                                "importance": importance,
                                "actionability": actionability,
                            }
                        ]

            # Finalize last cluster
            if current_cluster:
                cluster = await self._finalize_cluster(
                    clusters, current_cluster, cluster_start
                )
                clusters.append(cluster)

            return clusters

    async def _finalize_cluster(
        self, clusters: list, items: list[dict], start_time: datetime
    ) -> TemporalCluster:
        """Finalize a cluster with computed statistics.

        Args:
            clusters: Existing clusters (for ID generation)
            items: Items in this cluster
            start_time: Start time of cluster

        Returns:
            TemporalCluster instance
        """
        importances = [item["importance"] for item in items]
        actionabilities = [item["actionability"] for item in items]
        timestamps = [item["timestamp"] for item in items]

        mean_importance = sum(importances) / len(importances)
        mean_actionability = sum(actionabilities) / len(actionabilities)
        coherence = mean_importance * mean_actionability  # Proxy for coherence

        return TemporalCluster(
            cluster_id=len(clusters),
            event_ids=[item["id"] for item in items],
            time_window_start=start_time,
            time_window_end=timestamps[-1] if timestamps else start_time,
            mean_importance=mean_importance,
            mean_actionability=mean_actionability,
            total_activation=sum(importances),
            cluster_coherence=coherence,
        )

    async def consolidate_cluster(
        self, cluster: TemporalCluster, promote_all: bool = True
    ) -> int:
        """Consolidate all items in a cluster together.

        Args:
            cluster: Cluster to consolidate
            promote_all: If True, promote all items to semantic. If False,
                        only promote high-coherence clusters.

        Returns:
            Number of items consolidated
        """
        async with self.db.get_connection() as conn:
            # Determine consolidation based on cluster coherence
            should_promote = promote_all or (cluster.cluster_coherence > 0.6)

            if should_promote:
                target_status = "consolidated"
            else:
                target_status = "session"

            result = await conn.execute(
                """
                UPDATE episodic_events
                SET lifecycle_status = %s,
                    consolidation_score = %s,
                    last_activation = NOW()
                WHERE id = ANY(%s)
                RETURNING id
                """,
                (target_status, cluster.cluster_coherence, cluster.event_ids),
            )
            rows = await result.fetchall()
            return len(rows) if rows else 0
