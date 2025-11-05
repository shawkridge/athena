"""Health Trend Analyzer Skill - Analyze health metrics trends over time.

Analyzes task health scores over time to identify:
- Improving vs degrading trends
- Early warning signals
- Health pattern changes
- Intervention effectiveness
"""

from typing import Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..core.database import Database
from ..prospective.monitoring import TaskMonitor


@dataclass
class HealthTrend:
    """Health trend analysis result."""

    task_id: int
    time_period: str  # "7d", "30d", "90d"
    initial_score: float
    current_score: float
    trend: str  # "improving", "stable", "degrading"
    trend_strength: float  # 0.0-1.0, magnitude of change
    inflection_point: Optional[str]  # Date when trend changed
    early_warnings: List[str]
    intervention_needed: bool
    recommended_actions: List[str]


class HealthTrendAnalyzer:
    """Analyze health metrics trends over time."""

    def __init__(self, db: Database):
        """Initialize health trend analyzer.

        Args:
            db: Database connection
        """
        self.db = db
        self.monitor = TaskMonitor(db)

    async def analyze_task_trend(
        self, task_id: int, days: int = 30
    ) -> HealthTrend:
        """Analyze health trend for a specific task.

        Args:
            task_id: Task to analyze
            days: Number of days to look back

        Returns:
            HealthTrend with analysis and recommendations
        """
        # Get historical health scores
        health_history = self._get_health_history(task_id, days)

        if len(health_history) < 2:
            # Not enough data
            current_health = await self.monitor.get_task_health(task_id)
            return HealthTrend(
                task_id=task_id,
                time_period=f"{days}d",
                initial_score=(
                    current_health.health_score
                    if hasattr(current_health, "health_score")
                    else 0.5
                ),
                current_score=(
                    current_health.health_score
                    if hasattr(current_health, "health_score")
                    else 0.5
                ),
                trend="insufficient_data",
                trend_strength=0.0,
                inflection_point=None,
                early_warnings=["Insufficient historical data"],
                intervention_needed=False,
                recommended_actions=[
                    "Continue monitoring, trend analysis available after 3+ data points"
                ],
            )

        # Analyze trend
        initial_score = health_history[0]
        current_score = health_history[-1]
        trend, strength = self._calculate_trend(health_history)
        inflection_point = self._find_inflection_point(health_history)
        warnings = self._identify_early_warnings(health_history)
        actions = self._recommend_actions(
            trend, current_score, warnings
        )

        return HealthTrend(
            task_id=task_id,
            time_period=f"{days}d",
            initial_score=initial_score,
            current_score=current_score,
            trend=trend,
            trend_strength=strength,
            inflection_point=inflection_point,
            early_warnings=warnings,
            intervention_needed=current_score < 0.65 or trend == "degrading",
            recommended_actions=actions,
        )

    def _get_health_history(
        self, task_id: int, days: int
    ) -> List[float]:
        """Get historical health scores.

        Args:
            task_id: Task ID
            days: Number of days to look back

        Returns:
            List of health scores over time
        """
        try:
            cursor = self.db.conn.cursor()
            cutoff_time = int(
                (datetime.utcnow() - timedelta(days=days)).timestamp()
            )

            cursor.execute(
                """
                SELECT health_score FROM prospective_tasks
                WHERE id = ? AND updated_at > ?
                ORDER BY updated_at ASC
                """,
                (task_id, cutoff_time),
            )

            results = cursor.fetchall()
            # Try to extract numeric values
            scores = []
            for row in results:
                try:
                    score = float(row[0]) if row[0] else 0.5
                    scores.append(score)
                except (ValueError, TypeError):
                    scores.append(0.5)

            return scores if scores else [0.5]
        except Exception:
            return [0.5]

    def _calculate_trend(
        self, scores: List[float]
    ) -> tuple[str, float]:
        """Calculate trend from scores.

        Args:
            scores: Historical scores

        Returns:
            Tuple of (trend, strength)
        """
        if len(scores) < 2:
            return ("insufficient_data", 0.0)

        initial = scores[0]
        current = scores[-1]
        change = current - initial
        strength = abs(change)

        # Calculate slope for trend direction
        if len(scores) > 2:
            recent_scores = scores[-5:] if len(scores) >= 5 else scores
            avg_recent = sum(recent_scores) / len(recent_scores)
            older_scores = scores[: len(scores) - 5] if len(scores) > 5 else [scores[0]]
            avg_older = sum(older_scores) / len(older_scores)
            slope = avg_recent - avg_older
        else:
            slope = change

        # Determine trend
        if slope > 0.05:
            trend = "improving"
        elif slope < -0.05:
            trend = "degrading"
        else:
            trend = "stable"

        return (trend, min(strength, 1.0))

    def _find_inflection_point(
        self, scores: List[float]
    ) -> Optional[str]:
        """Find where trend changed.

        Args:
            scores: Historical scores

        Returns:
            Date when trend inflected, or None
        """
        if len(scores) < 3:
            return None

        # Find largest change point
        max_change = 0
        inflection_idx = 1
        for i in range(1, len(scores)):
            change = abs(scores[i] - scores[i - 1])
            if change > max_change:
                max_change = change
                inflection_idx = i

        if max_change > 0.1:
            # Return approximate date (7 days back for each index)
            days_back = (len(scores) - inflection_idx) * 7
            date = datetime.utcnow() - timedelta(days=days_back)
            return date.date().isoformat()

        return None

    def _identify_early_warnings(
        self, scores: List[float]
    ) -> List[str]:
        """Identify early warning signals.

        Args:
            scores: Historical scores

        Returns:
            List of warning descriptions
        """
        warnings = []

        current = scores[-1]
        recent_avg = (
            sum(scores[-3:]) / len(scores[-3:])
            if len(scores) >= 3
            else scores[-1]
        )

        # Check for degradation pattern
        if current < 0.65 and recent_avg < 0.70:
            warnings.append("Health dropping into warning zone (< 0.65)")

        # Check for volatility
        if len(scores) >= 3:
            recent_variance = max(scores[-3:]) - min(scores[-3:])
            if recent_variance > 0.3:
                warnings.append("High volatility in recent scores")

        # Check for low floor
        min_score = min(scores)
        if min_score < 0.3:
            warnings.append(f"Task reached critical state (score {min_score:.2f})")

        # Check for sustained low health
        if all(s < 0.6 for s in scores[-3:]):
            warnings.append("Sustained low health over recent period")

        if not warnings:
            warnings.append("No significant warning signals")

        return warnings

    def _recommend_actions(
        self, trend: str, current_score: float, warnings: List[str]
    ) -> List[str]:
        """Recommend actions based on analysis.

        Args:
            trend: Trend direction
            current_score: Current health score
            warnings: Identified warnings

        Returns:
            List of recommended actions
        """
        actions = []

        if trend == "degrading":
            actions.append("ACTION: Investigate cause of health degradation")
            if current_score < 0.65:
                actions.append(
                    "ACTION: Run /plan optimize to identify and fix issues"
                )
            if current_score < 0.5:
                actions.append(
                    "ACTION: CRITICAL - Consider halting and reassessing approach"
                )

        elif trend == "improving":
            actions.append("✓ Positive trend - maintain current approach")

        elif trend == "stable":
            if current_score < 0.65:
                actions.append(
                    "ACTION: Health is stable but low - needs improvement"
                )
            else:
                actions.append("✓ Health is stable and healthy")

        # Add warning-specific actions
        if "sustained low" in str(warnings).lower():
            actions.append(
                "ACTION: Schedule health review meeting to address root causes"
            )

        if "volatility" in str(warnings).lower():
            actions.append(
                "ACTION: Stabilize execution - identify what causes score swings"
            )

        return actions[:3]  # Top 3 actions

    async def analyze_project_trends(
        self, project_id: int, days: int = 30
    ) -> dict:
        """Analyze trends across all tasks in a project.

        Args:
            project_id: Project to analyze
            days: Number of days to look back

        Returns:
            Dictionary with project-wide trend analysis
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT id FROM prospective_tasks
                WHERE project_id = ? AND status != 'cancelled'
                """,
                (project_id,),
            )

            task_ids = [row[0] for row in cursor.fetchall()]

            trends = []
            improving_count = 0
            degrading_count = 0

            for task_id in task_ids[:10]:  # Sample top 10 tasks
                try:
                    trend = await self.analyze_task_trend(task_id, days)
                    trends.append(trend)

                    if trend.trend == "improving":
                        improving_count += 1
                    elif trend.trend == "degrading":
                        degrading_count += 1
                except Exception:
                    pass

            project_trend = (
                "improving"
                if improving_count > degrading_count
                else "degrading"
                if degrading_count > improving_count
                else "stable"
            )

            return {
                "project_id": project_id,
                "period_days": days,
                "tasks_analyzed": len(trends),
                "project_trend": project_trend,
                "improving_tasks": improving_count,
                "degrading_tasks": degrading_count,
                "warning_tasks": sum(
                    1 for t in trends if t.intervention_needed
                ),
                "recommendation": (
                    "Positive momentum - maintain current practices"
                    if project_trend == "improving"
                    else "Concerning trend - schedule intervention review"
                    if project_trend == "degrading"
                    else "Stable - monitor for changes"
                ),
            }
        except Exception:
            return {
                "error": "Unable to analyze project trends",
                "project_id": project_id,
            }
