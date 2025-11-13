"""
MCP tools for dream system control and monitoring.

Exposes:
- /dream - Trigger dream generation
- /dream_journal - View recent dreams
- /dream_health - System health metrics
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def setup_dream_tools(server):
    """
    Register dream system tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    async def dream(
        strategy: str = "balanced",
        focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger explicit dream generation during consolidation.

        Dreams are speculative procedure variants generated using
        multiple specialized models (DeepSeek, Qwen2.5-Coder, local).

        Args:
            strategy: Generation strategy
                - "light" (5 variants per procedure, ~1-2 min)
                - "balanced" (15 variants, ~2-3 min) [DEFAULT]
                - "deep" (30 variants, ~3-5 min)
            focus_area: Optional domain to focus on
                (e.g., "authentication", "deployment", "testing")

        Returns:
            Dream generation summary with counts by type

        Example:
            {"strategy": "balanced", "total_dreams": 87, "by_type": {
                "constraint_relaxation": 32,
                "cross_project_synthesis": 28,
                "parameter_exploration": 18,
                "conditional_variant": 9
            }, "generation_time": 145.3, "status": "complete"}
        """
        from ..core.database import Database
        from ..consolidation.dream_integration import integrate_dreams_into_consolidation

        try:
            logger.info(f"Manual dream generation triggered: strategy={strategy}")

            db = Database()
            result = await integrate_dreams_into_consolidation(
                db=db,
                strategy=strategy,
                project_id=None
            )

            return {
                "status": "success",
                "strategy": strategy,
                "total_dreams": result.get("total_dreams", 0),
                "by_type": result.get("by_type", {}),
                "generation_time": result.get("generation_time", 0),
                "procedures_processed": result.get("procedures_processed", 0),
                "run_id": result.get("run_id")
            }

        except Exception as e:
            logger.error(f"Error triggering dream generation: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @server.tool()
    async def dream_journal(
        limit: int = 10,
        tier: Optional[int] = None,
        days_back: Optional[int] = 7
    ) -> Dict[str, Any]:
        """
        View recent dream procedures.

        Access the journal of generated dreams, optionally filtered by
        tier (viability level) and time range.

        Args:
            limit: Maximum dreams to return (1-100) [DEFAULT: 10]
            tier: Optional filter
                - 1: Viable (confidence 0.6-1.0)
                - 2: Speculative (confidence 0.3-0.6)
                - 3: Archive (confidence <0.3)
            days_back: How many days of history (1-30) [DEFAULT: 7]

        Returns:
            List of recent dreams with metadata

        Example:
            {"dreams": [
                {
                    "name": "deploy_api_v_param_increased_timeout",
                    "tier": 1,
                    "viability": 0.82,
                    "novelty": 0.65,
                    "dream_type": "parameter_exploration",
                    "evaluated_at": "2025-11-13T10:23:45Z",
                    "reasoning": "Increased timeout from 5s to 10s for resilience"
                }
            ], "total_pending": 3, "total_evaluated": 42}
        """
        from ..core.database import Database
        from ..consolidation.dream_store import DreamStore, DreamTier, DreamStatus

        try:
            db = Database()
            store = DreamStore(db)

            # Get dreams based on filter
            if tier:
                dreams_list = await store.get_by_tier(DreamTier(tier), limit=limit)
            else:
                # Get recent evaluated dreams
                dreams_list = await store.get_by_status(DreamStatus.EVALUATED, limit=limit)

            # Format for display
            dreams = []
            for dream in dreams_list:
                dreams.append({
                    "id": dream.id,
                    "name": dream.name,
                    "base_procedure": dream.base_procedure_name,
                    "dream_type": dream.dream_type,
                    "tier": dream.tier.value if dream.tier else None,
                    "viability_score": dream.viability_score,
                    "novelty_score": dream.novelty_score,
                    "evaluated_at": dream.evaluated_at.isoformat() if dream.evaluated_at else None,
                    "reasoning": dream.claude_reasoning,
                    "cross_project_matches": dream.cross_project_matches
                })

            # Get statistics
            stats = await store.get_statistics()
            pending = await store.get_pending_evaluation(limit=1)

            return {
                "status": "success",
                "dreams": dreams,
                "count": len(dreams),
                "total_dreams": stats.get("total_dreams", 0),
                "tier_distribution": stats.get("by_tier", {}),
                "pending_evaluation": len(pending) if pending else 0
            }

        except Exception as e:
            logger.error(f"Error fetching dream journal: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @server.tool()
    async def dream_health() -> Dict[str, Any]:
        """
        Get dream system health report.

        Returns comprehensive metrics about dream system performance,
        including compound health score (0.0-1.0) and component scores.

        Returns:
            Health report with status, scores, and trends

        Example:
            {
                "status": "healthy",
                "compound_score": 0.74,
                "components": {
                    "novelty": 0.45,
                    "quality": 0.18,
                    "leverage": 0.08,
                    "efficiency": 0.04
                },
                "dream_counts": {
                    "tier_1_viable": 23,
                    "tier_2_speculative": 15,
                    "tier_3_archive": 8
                },
                "performance": {
                    "avg_viability_score": 0.72,
                    "tier1_test_success_rate": 0.78,
                    "cross_project_adoption_rate": 0.35
                },
                "trend": {
                    "trend_direction": "improving",
                    "change_percent": 12.5
                }
            }
        """
        from ..core.database import Database
        from ..consolidation.dream_metrics import calculate_dream_health

        try:
            logger.info("Dream health report requested")

            db = Database()
            health = await calculate_dream_health(db)

            return {
                "status": "success",
                "health": health
            }

        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @server.tool()
    async def dream_stats() -> Dict[str, Any]:
        """
        Get detailed dream system statistics.

        Returns detailed metrics about dream generation, testing,
        and effectiveness across all procedures.

        Returns:
            Detailed statistics dictionary

        Example:
            {
                "total_dreams": 142,
                "by_type": {
                    "constraint_relaxation": 58,
                    "cross_project_synthesis": 42,
                    "parameter_exploration": 28,
                    "conditional_variant": 14
                },
                "by_status": {
                    "pending_evaluation": 3,
                    "evaluated": 139
                },
                "by_tier": {
                    "1": 78,
                    "2": 51,
                    "3": 13
                },
                "quality_metrics": {
                    "average_viability": 0.68,
                    "average_novelty": 0.52,
                    "tier1_success_rate": 0.73
                }
            }
        """
        from ..core.database import Database
        from ..consolidation.dream_store import DreamStore

        try:
            db = Database()
            store = DreamStore(db)

            stats = await store.get_statistics()

            return {
                "status": "success",
                "statistics": stats
            }

        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
