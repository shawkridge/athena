"""
Dream system metrics tracking and compound health scoring.

Implements:
- Quality metrics collection
- Compound health score calculation
- Trend analysis over time
- Performance tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.database import Database
from .dream_store import DreamStore
from .dream_models import DreamStatus, DreamTier, DreamMetrics

logger = logging.getLogger(__name__)


class DreamMetricsCalculator:
    """
    Calculate dream system metrics and health scores.

    Metrics include:
    - Quality metrics: viability scores, tier distributions, test success rates
    - Novelty metrics: high-novelty dream counts, cross-project leverage
    - Efficiency metrics: generation time, API request efficiency
    - Compound health score: weighted combination of metrics
    """

    def __init__(self, db: Database):
        """Initialize metrics calculator.

        Args:
            db: Database instance
        """
        self.db = db
        self.dream_store = DreamStore(db)

    async def calculate_current_metrics(self) -> DreamMetrics:
        """
        Calculate current dream system metrics.

        Returns:
            DreamMetrics object with all calculations
        """
        logger.info("Calculating dream system metrics...")

        try:
            # Get statistics
            stats = await self.dream_store.get_statistics()

            # Calculate quality metrics
            avg_viability = stats.get("average_viability", 0.0)
            tier_counts = stats.get("by_tier", {})
            tier1_count = tier_counts.get(1, 0)
            tier2_count = tier_counts.get(2, 0)
            tier3_count = tier_counts.get(3, 0)

            # Calculate test success rate for tier 1
            tier1_success_rate = await self._calculate_tier1_success_rate()

            # Calculate novelty metrics
            avg_novelty = await self._calculate_average_novelty()
            high_novelty_count = await self._count_high_novelty_dreams()

            # Calculate cross-project metrics
            cross_project_rate, adopted_count = await self._calculate_cross_project_adoption()

            # Calculate efficiency metrics
            avg_gen_time, avg_api_cost = await self._calculate_efficiency_metrics()

            # Calculate component scores (each 0.0-1.0)
            novelty_component = self._score_novelty(avg_novelty, high_novelty_count)
            quality_component = self._score_quality(
                avg_viability, tier1_success_rate, tier1_count, tier2_count, tier3_count
            )
            leverage_component = self._score_cross_project_leverage(cross_project_rate)
            efficiency_component = self._score_efficiency(avg_gen_time)

            # Apply weights for compound score
            # 60% novelty, 15% quality evolution, 15% cross-project, 10% efficiency
            compound_score = (
                0.60 * novelty_component +
                0.15 * quality_component +
                0.15 * leverage_component +
                0.10 * efficiency_component
            )

            # Create metrics object
            metrics = DreamMetrics(
                timestamp=datetime.now(),
                average_viability_score=avg_viability,
                tier1_count=tier1_count,
                tier2_count=tier2_count,
                tier3_count=tier3_count,
                tier1_test_success_rate=tier1_success_rate,
                tier1_test_count=await self._count_tier1_tested(),
                average_novelty_score=avg_novelty,
                high_novelty_count=high_novelty_count,
                cross_project_adoption_rate=cross_project_rate,
                dreams_adopted_count=adopted_count,
                average_generation_time_seconds=avg_gen_time,
                api_requests_per_dream=avg_api_cost,
                novelty_score_weighted=novelty_component * 0.60,
                quality_evolution_weighted=quality_component * 0.15,
                cross_project_leverage_weighted=leverage_component * 0.15,
                efficiency_weighted=efficiency_component * 0.10,
                compound_health_score=compound_score
            )

            # Store metrics
            await self.dream_store.store_metrics(metrics)

            logger.info(
                f"Metrics calculated: "
                f"novelty={novelty_component:.2f}, "
                f"quality={quality_component:.2f}, "
                f"leverage={leverage_component:.2f}, "
                f"efficiency={efficiency_component:.2f}, "
                f"compound={compound_score:.2f}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}", exc_info=True)
            # Return minimal metrics on error
            return DreamMetrics()

    async def _calculate_tier1_success_rate(self) -> float:
        """Calculate percentage of Tier 1 dreams that passed testing."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN test_outcome = 'success' THEN 1 ELSE 0 END) as successes
            FROM dream_procedures
            WHERE tier = 1 AND test_outcome IS NOT NULL
        """
        )

        result = cursor.fetchone()
        if result["total"] == 0:
            return 0.0

        return float(result["successes"]) / float(result["total"])

    async def _calculate_average_novelty(self) -> float:
        """Calculate average novelty score of evaluated dreams."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT AVG(novelty_score) as avg_novelty
            FROM dream_procedures
            WHERE novelty_score IS NOT NULL AND status = 'evaluated'
        """
        )

        result = cursor.fetchone()
        return result["avg_novelty"] or 0.0

    async def _count_high_novelty_dreams(self) -> int:
        """Count dreams with novelty score > 0.7."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM dream_procedures
            WHERE novelty_score >= 0.7 AND status = 'evaluated'
        """
        )

        return cursor.fetchone()["count"]

    async def _calculate_cross_project_adoption(self) -> tuple:
        """Calculate cross-project adoption rate and count."""
        cursor = self.db.get_cursor()

        # Count dreams with cross-project matches
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN cross_project_matches >= 2 THEN 1 ELSE 0 END) as adopted
            FROM dream_procedures
            WHERE tier = 1 AND status = 'evaluated'
        """
        )

        result = cursor.fetchone()
        if result["total"] == 0:
            return 0.0, 0

        adoption_rate = float(result["adopted"]) / float(result["total"]) if result["adopted"] else 0.0
        return adoption_rate, result["adopted"]

    async def _calculate_efficiency_metrics(self) -> tuple:
        """Calculate generation efficiency metrics."""
        cursor = self.db.get_cursor()

        # Average generation time from runs
        cursor.execute(
            """
            SELECT AVG(duration_seconds) as avg_time
            FROM dream_generation_runs
            WHERE timestamp > datetime('now', '-7 days')
        """
        )

        avg_time = cursor.fetchone()["avg_time"] or 0.0

        # Estimate API cost (roughly 25-30 requests per consolidation)
        avg_api_cost = 30.0

        return avg_time, avg_api_cost

    async def _count_tier1_tested(self) -> int:
        """Count Tier 1 dreams that have been tested."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM dream_procedures
            WHERE tier = 1 AND test_outcome IS NOT NULL
        """
        )

        return cursor.fetchone()["count"]

    def _score_novelty(self, avg_novelty: float, high_novelty_count: int) -> float:
        """Score novelty component (0.0-1.0)."""
        # Weight: 70% average novelty, 30% high-novelty count
        avg_score = min(avg_novelty, 1.0)
        high_score = min(high_novelty_count / 10.0, 1.0)  # Target: 10+ high-novelty dreams

        return (0.7 * avg_score) + (0.3 * high_score)

    def _score_quality(
        self,
        avg_viability: float,
        tier1_success: float,
        tier1_count: int,
        tier2_count: int,
        tier3_count: int
    ) -> float:
        """Score quality component (0.0-1.0)."""
        total = tier1_count + tier2_count + tier3_count

        if total == 0:
            return 0.0

        # Distribution score: prefer Tier 1 > Tier 2 > Tier 3
        distribution_score = (
            (0.5 * tier1_count + 0.3 * tier2_count + 0.1 * tier3_count) / total
        )

        # Combine with viability and test success
        return (
            (0.5 * min(avg_viability, 1.0)) +
            (0.3 * distribution_score) +
            (0.2 * tier1_success)  # Only if we have test data
        )

    def _score_cross_project_leverage(self, adoption_rate: float) -> float:
        """Score cross-project leverage component (0.0-1.0)."""
        # Target: 25%+ of tier 1 dreams are reusable
        return min(adoption_rate / 0.25, 1.0)

    def _score_efficiency(self, avg_gen_time: float) -> float:
        """Score efficiency component (0.0-1.0)."""
        # Target: 30 seconds for full consolidation
        # Score decreases if slower than target
        target_time = 30.0

        if avg_gen_time <= target_time:
            return 1.0
        else:
            # Penalize: score = target / actual
            return max(target_time / avg_gen_time, 0.1)

    async def get_trend_analysis(self, days: int = 30) -> Dict:
        """
        Analyze metrics trend over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend information
        """
        cursor = self.db.get_cursor()

        # Get metrics from past N days
        cursor.execute(
            """
            SELECT
                timestamp,
                compound_health_score,
                novelty_score_weighted,
                quality_evolution_weighted,
                cross_project_leverage_weighted,
                efficiency_weighted
            FROM dream_metrics
            WHERE timestamp > datetime('now', ? || ' days')
            ORDER BY timestamp ASC
        """,
            (f"-{days}",)
        )

        metrics_history = cursor.fetchall()

        if not metrics_history:
            return {"message": "No metrics data available"}

        # Calculate trends
        compound_scores = [m["compound_health_score"] for m in metrics_history]
        first_score = compound_scores[0]
        last_score = compound_scores[-1]

        trend = {
            "days_analyzed": days,
            "data_points": len(metrics_history),
            "initial_score": first_score,
            "latest_score": last_score,
            "trend_direction": "improving" if last_score > first_score else "declining" if last_score < first_score else "stable",
            "change_amount": last_score - first_score,
            "change_percent": ((last_score - first_score) / first_score * 100) if first_score > 0 else 0,
            "average_score": sum(compound_scores) / len(compound_scores),
            "max_score": max(compound_scores),
            "min_score": min(compound_scores),
        }

        return trend

    async def get_health_report(self) -> Dict:
        """
        Get comprehensive health report.

        Returns:
            Dictionary with complete health status
        """
        latest_metrics = await self.dream_store.get_latest_metrics()

        if not latest_metrics:
            return {"status": "no_data"}

        trend = await self.get_trend_analysis(days=30)

        return {
            "status": "healthy" if latest_metrics.compound_health_score > 0.6 else "needs_improvement",
            "compound_score": latest_metrics.compound_health_score,
            "components": {
                "novelty": latest_metrics.novelty_score_weighted,
                "quality": latest_metrics.quality_evolution_weighted,
                "leverage": latest_metrics.cross_project_leverage_weighted,
                "efficiency": latest_metrics.efficiency_weighted,
            },
            "dream_counts": {
                "tier_1_viable": latest_metrics.tier1_count,
                "tier_2_speculative": latest_metrics.tier2_count,
                "tier_3_archive": latest_metrics.tier3_count,
            },
            "performance": {
                "avg_viability_score": latest_metrics.average_viability_score,
                "avg_novelty_score": latest_metrics.average_novelty_score,
                "tier1_test_success_rate": latest_metrics.tier1_test_success_rate,
                "cross_project_adoption_rate": latest_metrics.cross_project_adoption_rate,
            },
            "efficiency": {
                "avg_generation_time_seconds": latest_metrics.average_generation_time_seconds,
                "api_requests_per_dream": latest_metrics.api_requests_per_dream,
            },
            "trend": trend,
            "timestamp": latest_metrics.timestamp.isoformat() if latest_metrics.timestamp else None,
        }


# Convenience function
async def calculate_dream_health(db: Database) -> Dict:
    """
    Calculate and return dream system health report.

    Usage:
        health = await calculate_dream_health(db)
        print(f"Health: {health['compound_score']:.2f}")

    Args:
        db: Database instance

    Returns:
        Health report dictionary
    """
    calculator = DreamMetricsCalculator(db)
    return await calculator.get_health_report()
