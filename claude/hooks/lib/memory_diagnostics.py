"""Memory System Diagnostics

Monitors and analyzes memory boost effectiveness, activation distribution,
and worktree-specific memory patterns.
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from connection_pool import PooledConnection

logger = logging.getLogger(__name__)


class MemoryDiagnostics:
    """Analyze memory system performance and worktree prioritization."""

    @staticmethod
    def analyze_memory_distribution(
        project_id: int,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Analyze how memories are distributed across worktrees.

        Shows:
        - Total memories per worktree
        - Average activation scores
        - Boost impact (with vs. without worktree boost)

        Args:
            project_id: Project ID to analyze
            limit: Maximum memories to analyze

        Returns:
            Dict with distribution statistics
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get memories grouped by worktree
                cursor.execute(
                    """
                    SELECT
                        COALESCE(worktree_path, 'non_git') as worktree,
                        COUNT(*) as count,
                        AVG(importance_score) as avg_importance,
                        COUNT(DISTINCT event_type) as event_types,
                        MIN(timestamp) as oldest_memory,
                        MAX(timestamp) as newest_memory
                    FROM episodic_events
                    WHERE project_id = %s AND lifecycle_status = 'active'
                    GROUP BY worktree_path
                    ORDER BY count DESC
                    LIMIT %s
                    """,
                    (project_id, limit),
                )

                rows = cursor.fetchall()

                distribution = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project_id": project_id,
                    "total_worktrees": len(rows),
                    "worktrees": [],
                    "summary": {
                        "total_memories": 0,
                        "avg_importance": 0.0,
                    },
                }

                total_memories = 0
                total_importance = 0

                for row in rows:
                    worktree, count, avg_importance, event_types, oldest, newest = row

                    worktree_data = {
                        "worktree": worktree or "non_git",
                        "memory_count": count,
                        "avg_importance": float(avg_importance or 0.5),
                        "event_types": event_types,
                        "oldest_memory": oldest,
                        "newest_memory": newest,
                    }

                    distribution["worktrees"].append(worktree_data)

                    total_memories += count
                    total_importance += (avg_importance or 0.5) * count

                # Calculate summary
                if total_memories > 0:
                    distribution["summary"]["total_memories"] = total_memories
                    distribution["summary"]["avg_importance"] = total_importance / total_memories

                logger.info(f"Memory distribution: {total_memories} memories across {len(rows)} worktrees")
                return distribution

        except Exception as e:
            logger.error(f"Error analyzing memory distribution: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def get_memory_boost_stats(
        project_id: int,
        current_worktree: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Measure the impact of worktree boost on memory activation.

        Compares activation scores with and without worktree boost.

        Args:
            project_id: Project ID to analyze
            current_worktree: Optional current worktree for simulation

        Returns:
            Dict with boost statistics
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get memory activation stats
                cursor.execute(
                    """
                    SELECT
                        CASE WHEN worktree_path = %s THEN 'current_worktree' ELSE 'other_worktrees' END as category,
                        COUNT(*) as count,
                        AVG(
                            (-0.5 * LN(GREATEST(EXTRACT(EPOCH FROM (NOW() - last_activation)) / 3600.0, 0.1)))
                            + (LN(GREATEST(activation_count, 1)) * 0.1)
                            + (COALESCE(consolidation_score, 0) * 1.0)
                            + CASE WHEN importance_score > 0.7 THEN 1.5 ELSE 0 END
                            + CASE WHEN has_next_step = 1 OR actionability_score > 0.7 THEN 1.0 ELSE 0 END
                            + CASE WHEN outcome = 'success' THEN 0.5 ELSE 0 END
                        ) as base_activation,
                        AVG(
                            (-0.5 * LN(GREATEST(EXTRACT(EPOCH FROM (NOW() - last_activation)) / 3600.0, 0.1)))
                            + (LN(GREATEST(activation_count, 1)) * 0.1)
                            + (COALESCE(consolidation_score, 0) * 1.0)
                            + CASE WHEN importance_score > 0.7 THEN 1.5 ELSE 0 END
                            + CASE WHEN has_next_step = 1 OR actionability_score > 0.7 THEN 1.0 ELSE 0 END
                            + CASE WHEN outcome = 'success' THEN 0.5 ELSE 0 END
                            + CASE WHEN worktree_path = %s THEN 2.0 ELSE 0 END
                        ) as boosted_activation
                    FROM episodic_events
                    WHERE project_id = %s AND lifecycle_status = 'active'
                    GROUP BY category
                    """,
                    (current_worktree, current_worktree, project_id),
                )

                rows = cursor.fetchall()

                stats = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project_id": project_id,
                    "current_worktree": current_worktree,
                    "boost_effect": {
                        "current_worktree_memories": None,
                        "other_worktrees_memories": None,
                        "boost_delta": None,
                        "boost_percentage": None,
                    },
                }

                for row in rows:
                    category, count, base_activation, boosted_activation = row

                    boost_delta = (boosted_activation or 0) - (base_activation or 0)
                    boost_percent = (
                        (boost_delta / (base_activation or 1)) * 100
                        if base_activation and base_activation > 0
                        else 0
                    )

                    if category == "current_worktree":
                        stats["boost_effect"]["current_worktree_memories"] = {
                            "count": count,
                            "base_activation": float(base_activation or 0),
                            "boosted_activation": float(boosted_activation or 0),
                            "boost_delta": float(boost_delta),
                            "boost_percentage": float(boost_percent),
                        }
                    else:
                        stats["boost_effect"]["other_worktrees_memories"] = {
                            "count": count,
                            "base_activation": float(base_activation or 0),
                            "boosted_activation": float(boosted_activation or 0),
                            "boost_delta": 0.0,
                            "boost_percentage": 0.0,
                        }

                logger.info(
                    f"Memory boost stats: current_worktree +{stats['boost_effect']['current_worktree_memories'].get('boost_percentage', 0):.1f}% boost"
                    if stats["boost_effect"]["current_worktree_memories"]
                    else "No current worktree memories"
                )
                return stats

        except Exception as e:
            logger.error(f"Error calculating boost stats: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def log_memory_prioritization(
        project_id: int,
        memory_items: List[Dict[str, Any]],
        current_worktree: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log which memories are prioritized and why.

        Useful for debugging memory ranking.

        Args:
            project_id: Project ID
            memory_items: List of memory dicts from get_active_memories()
            current_worktree: Current worktree for context

        Returns:
            Dict with prioritization analysis
        """
        analysis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "current_worktree": current_worktree,
            "total_items": len(memory_items),
            "priority_tiers": {
                "current_worktree": [],
                "other_worktrees": [],
            },
            "summary": {
                "current_worktree_count": 0,
                "other_worktree_count": 0,
                "current_worktree_percentage": 0.0,
            },
        }

        for i, item in enumerate(memory_items, 1):
            is_current = item.get("worktree_path") == current_worktree
            tier = "current_worktree" if is_current else "other_worktrees"

            memory_info = {
                "rank": i,
                "type": item.get("type", "unknown"),
                "content": item.get("content", "")[:50],
                "activation": float(item.get("activation", 0)),
                "importance": float(item.get("importance", 0.5)),
                "worktree_path": item.get("worktree_path"),
            }

            analysis["priority_tiers"][tier].append(memory_info)

            if is_current:
                analysis["summary"]["current_worktree_count"] += 1
            else:
                analysis["summary"]["other_worktree_count"] += 1

        # Calculate percentage
        if memory_items:
            analysis["summary"]["current_worktree_percentage"] = (
                (analysis["summary"]["current_worktree_count"] / len(memory_items)) * 100
            )

        logger.info(
            f"Memory prioritization: {analysis['summary']['current_worktree_count']}/{len(memory_items)} "
            f"({analysis['summary']['current_worktree_percentage']:.1f}%) from current worktree"
        )

        return analysis

    @staticmethod
    def get_memory_health_report(project_id: int) -> Dict[str, Any]:
        """Generate a comprehensive memory system health report.

        Args:
            project_id: Project ID

        Returns:
            Dict with full health analysis
        """
        try:
            report = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "sections": {},
            }

            # Section 1: Distribution
            report["sections"]["distribution"] = MemoryDiagnostics.analyze_memory_distribution(project_id)

            # Section 2: Boost stats (without current worktree for overview)
            report["sections"]["boost_stats"] = MemoryDiagnostics.get_memory_boost_stats(project_id, None)

            # Section 3: Overall metrics
            with PooledConnection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(DISTINCT project_id) as projects,
                        COUNT(DISTINCT COALESCE(worktree_path, 'non_git')) as worktrees,
                        COUNT(CASE WHEN consolidation_status = 'consolidated' THEN 1 END) as consolidated_count,
                        AVG(importance_score) as avg_importance
                    FROM episodic_events
                    WHERE project_id = %s
                    """,
                    (project_id,),
                )

                row = cursor.fetchone()
                if row:
                    total, projects, worktrees, consolidated, avg_imp = row
                    report["sections"]["metrics"] = {
                        "total_memories": total,
                        "consolidated_memories": consolidated,
                        "consolidated_percentage": (consolidated / total * 100) if total > 0 else 0,
                        "distinct_worktrees": worktrees,
                        "avg_importance": float(avg_imp or 0.5),
                    }

            report["status"] = "healthy"
            logger.info(f"Memory health report generated for project {project_id}")
            return report

        except Exception as e:
            logger.error(f"Error generating memory health report: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
            }
