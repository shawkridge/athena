"""Metrics tracking and analysis for memory flow system.

Tracks activation dynamics and consolidation metrics in activation_history
for analysis and visualization.
"""

import logging
from datetime import datetime

from ..core.database import Database

logger = logging.getLogger(__name__)


class FlowMetricsTracker:
    """Tracks and analyzes memory flow metrics."""

    def __init__(self, db: Database):
        """Initialize metrics tracker.

        Args:
            db: Database instance
        """
        self.db = db

    async def record_activation_change(
        self,
        event_id: int,
        activation_value: float,
        interference_factor: float = 1.0,
        access_count: int = 0,
        current_tier: str = "episodic",
        consolidation_strength: float = 0.0,
    ) -> bool:
        """Record activation state change in history for analysis.

        Args:
            event_id: ID of event
            activation_value: Current activation (0.0-1.0)
            interference_factor: RIF suppression factor
            access_count: Number of accesses
            current_tier: Current memory tier
            consolidation_strength: Consolidation score

        Returns:
            True if recorded successfully
        """
        try:
            async with self.db.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO activation_history
                    (event_id, timestamp, activation_value, interference_factor,
                     access_count, current_tier, consolidation_strength)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event_id,
                        datetime.now(),
                        activation_value,
                        interference_factor,
                        access_count,
                        current_tier,
                        consolidation_strength,
                    ),
                )
            return True
        except Exception as e:
            logger.error(f"Error recording activation change: {e}")
            return False

    async def get_activation_timeline(self, event_id: int, hours: int = 24) -> list[dict]:
        """Get activation history for an event over time.

        Args:
            event_id: ID of event
            hours: Time period to analyze

        Returns:
            List of activation history records
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT timestamp, activation_value, interference_factor,
                           access_count, current_tier, consolidation_strength
                    FROM activation_history
                    WHERE event_id = %s AND timestamp > NOW() - INTERVAL '1 hour' * %s
                    ORDER BY timestamp ASC
                    """,
                    (event_id, hours),
                )
                rows = await result.fetchall()

                return [
                    {
                        "timestamp": row[0],
                        "activation_value": row[1],
                        "interference_factor": row[2],
                        "access_count": row[3],
                        "tier": row[4],
                        "consolidation_strength": row[5],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error retrieving activation timeline: {e}")
            return []

    async def get_tier_distribution(self, hours: int = 24) -> dict[str, int]:
        """Get distribution of items across tiers.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with tier names and counts
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT current_tier, COUNT(DISTINCT event_id) as count
                    FROM activation_history
                    WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                    GROUP BY current_tier
                    """,
                    (hours,),
                )
                rows = await result.fetchall()

                return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Error calculating tier distribution: {e}")
            return {}

    async def get_consolidation_metrics(self, hours: int = 24) -> dict:
        """Get consolidation metrics for analysis.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with consolidation statistics
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT
                      COUNT(DISTINCT event_id) as total_events,
                      AVG(activation_value) as mean_activation,
                      MAX(activation_value) as max_activation,
                      MIN(activation_value) as min_activation,
                      AVG(consolidation_strength) as mean_consolidation,
                      SUM(CASE WHEN consolidation_strength > 0.7 THEN 1 ELSE 0 END) as promoted_count,
                      SUM(CASE WHEN consolidation_strength < 0.4 THEN 1 ELSE 0 END) as decayed_count
                    FROM activation_history
                    WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                    """,
                    (hours,),
                )
                row = await result.fetchone()

                if row:
                    return {
                        "total_events": row[0] or 0,
                        "mean_activation": float(row[1] or 0),
                        "max_activation": float(row[2] or 0),
                        "min_activation": float(row[3] or 0),
                        "mean_consolidation": float(row[4] or 0),
                        "promoted_to_semantic": row[5] or 0,
                        "decayed_items": row[6] or 0,
                    }
                return {}
        except Exception as e:
            logger.error(f"Error calculating consolidation metrics: {e}")
            return {}

    async def get_interference_analysis(self, hours: int = 24) -> dict:
        """Analyze RIF (Retrieval-Induced Forgetting) effects.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with RIF analysis
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT
                      AVG(interference_factor) as mean_interference,
                      MIN(interference_factor) as min_interference,
                      MAX(interference_factor) as max_interference,
                      COUNT(CASE WHEN interference_factor < 0.8 THEN 1 END) as suppressed_items
                    FROM activation_history
                    WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                    """,
                    (hours,),
                )
                row = await result.fetchone()

                if row:
                    return {
                        "mean_interference": float(row[0] or 1.0),
                        "min_interference": float(row[1] or 1.0),
                        "max_interference": float(row[2] or 1.0),
                        "suppressed_items": row[3] or 0,
                    }
                return {}
        except Exception as e:
            logger.error(f"Error analyzing interference: {e}")
            return {}

    async def get_access_patterns(self, hours: int = 24, top_n: int = 10) -> list[dict]:
        """Get most frequently accessed items.

        Args:
            hours: Time period to analyze
            top_n: Number of top items to return

        Returns:
            List of access pattern dicts
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT
                      event_id,
                      MAX(access_count) as max_accesses,
                      AVG(activation_value) as mean_activation,
                      MAX(consolidation_strength) as max_consolidation
                    FROM activation_history
                    WHERE timestamp > NOW() - INTERVAL '1 hour' * %s
                    GROUP BY event_id
                    ORDER BY max_accesses DESC
                    LIMIT %s
                    """,
                    (hours, top_n),
                )
                rows = await result.fetchall()

                return [
                    {
                        "event_id": row[0],
                        "access_count": row[1],
                        "mean_activation": float(row[2] or 0),
                        "consolidation_strength": float(row[3] or 0),
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting access patterns: {e}")
            return []
