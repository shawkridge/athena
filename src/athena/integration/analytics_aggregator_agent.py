"""Analytics Aggregator Agent - Weekly/monthly analytics synthesis.

Phase 5-8 Agent: Analyzes estimation accuracy, discovers task patterns,
and generates optimization recommendations for weekly/monthly reviews.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..integration.analytics import TaskAnalytics
from ..prospective.store import ProspectiveStore
from ..prospective.monitoring import TaskMonitor
from ..core.database import Database


@dataclass
class AnalyticsSummary:
    """Weekly/monthly analytics summary."""

    period: str  # "weekly" or "monthly"
    start_date: str
    end_date: str
    completed_tasks: int
    estimation_accuracy: float
    average_health_score: float
    patterns_identified: list[str]
    improvement_areas: list[str]
    recommendations: list[str]


class AnalyticsAggregatorAgent:
    """Autonomous agent for weekly/monthly analytics synthesis.

    Analyzes estimation accuracy, discovers patterns from completed tasks,
    and generates optimization recommendations for continuous improvement.
    """

    def __init__(self, db: Database):
        """Initialize analytics aggregator agent.

        Args:
            db: Database connection for accessing task data
        """
        self.db = db
        self.analytics = TaskAnalytics(db)
        self.store = ProspectiveStore(db)
        self.monitor = TaskMonitor(db)

    async def analyze_project(
        self, project_id: int, period: str = "weekly"
    ) -> AnalyticsSummary:
        """Analyze project with weekly/monthly metrics.

        Args:
            project_id: Project to analyze
            period: "weekly" or "monthly"

        Returns:
            AnalyticsSummary with comprehensive analytics
        """
        # Calculate lookback days
        days_back = 7 if period == "weekly" else 30

        # Analyze estimation accuracy
        accuracy_data = await self.analytics.analyze_estimation_accuracy(
            project_id, days_back=days_back
        )

        # Discover patterns
        patterns_data = await self.analytics.discover_patterns(project_id)

        # Get project dashboard for health metrics
        dashboard = await self.monitor.get_project_dashboard(project_id)

        # Extract accuracy metrics
        accuracy_score = (
            accuracy_data.accuracy_rate
            if hasattr(accuracy_data, "accuracy_rate")
            else accuracy_data.get("accuracy_rate", 0)
            if isinstance(accuracy_data, dict)
            else 0
        )

        # Extract patterns
        patterns_list = self._extract_patterns(patterns_data)

        # Identify improvement areas
        improvement_areas = self._identify_improvements(
            accuracy_data, patterns_data, dashboard
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            improvement_areas, accuracy_score, patterns_list
        )

        # Calculate dates
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        return AnalyticsSummary(
            period=period,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            completed_tasks=self._count_completed_tasks(project_id, days_back),
            estimation_accuracy=accuracy_score,
            average_health_score=dashboard.average_health_score
            if hasattr(dashboard, "average_health_score")
            else 0,
            patterns_identified=patterns_list[:5],  # Top 5 patterns
            improvement_areas=improvement_areas[:3],  # Top 3 areas
            recommendations=recommendations[:5],  # Top 5 recommendations
        )

    def _count_completed_tasks(
        self, project_id: int, days_back: int
    ) -> int:
        """Count completed tasks in timeframe.

        Args:
            project_id: Project ID
            days_back: Number of days to look back

        Returns:
            Count of completed tasks
        """
        try:
            cursor = self.db.get_cursor()
            cutoff_time = (
                int(
                    (
                        datetime.utcnow()
                        - timedelta(days=days_back)
                    ).timestamp()
                )
                if days_back > 0
                else 0
            )

            cursor.execute(
                """
                SELECT COUNT(*) FROM prospective_tasks
                WHERE project_id = ? AND status = 'completed'
                AND updated_at > ?
                """,
                (project_id, cutoff_time),
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def _extract_patterns(self, patterns_data) -> list[str]:
        """Extract readable pattern descriptions.

        Args:
            patterns_data: Pattern discovery result

        Returns:
            List of pattern descriptions
        """
        patterns = []

        if isinstance(patterns_data, dict):
            if "most_common_priority" in patterns_data:
                patterns.append(
                    f"Most tasks are {patterns_data['most_common_priority']} priority"
                )
            if "failure_reason_distribution" in patterns_data:
                patterns.append(
                    f"Common failure reasons: {patterns_data['failure_reason_distribution']}"
                )
            if "average_duration_hours" in patterns_data:
                patterns.append(
                    f"Average task duration: {patterns_data['average_duration_hours']:.1f} hours"
                )
        elif hasattr(patterns_data, "most_common_priority"):
            patterns.append(
                f"Most tasks are {patterns_data.most_common_priority} priority"
            )
            if hasattr(patterns_data, "average_duration_hours"):
                patterns.append(
                    f"Average task duration: {patterns_data.average_duration_hours:.1f} hours"
                )

        return patterns if patterns else ["No clear patterns identified yet"]

    def _identify_improvements(
        self, accuracy_data, patterns_data, dashboard
    ) -> list[str]:
        """Identify areas for improvement.

        Args:
            accuracy_data: Estimation accuracy results
            patterns_data: Pattern discovery results
            dashboard: Project dashboard

        Returns:
            List of improvement area descriptions
        """
        improvements = []

        # Check estimation accuracy
        accuracy_score = (
            accuracy_data.accuracy_rate
            if hasattr(accuracy_data, "accuracy_rate")
            else accuracy_data.get("accuracy_rate", 100)
            if isinstance(accuracy_data, dict)
            else 100
        )

        if accuracy_score < 70:
            improvements.append("Estimation accuracy is low - need calibration")
        elif accuracy_score < 85:
            improvements.append("Estimation accuracy could be improved")

        # Check health score
        avg_health = (
            dashboard.average_health_score
            if hasattr(dashboard, "average_health_score")
            else 0
        )
        if avg_health < 0.65:
            improvements.append("Average task health declining - more blockers")
        elif avg_health < 0.75:
            improvements.append("Some tasks experiencing quality issues")

        # Check task distribution
        if isinstance(patterns_data, dict):
            if patterns_data.get("failure_count", 0) > 2:
                improvements.append("Multiple task failures - review approaches")
            if patterns_data.get("blocked_count", 0) > 1:
                improvements.append("Tasks frequently blocked - resolve dependencies")

        return improvements if improvements else ["Process running smoothly"]

    def _generate_recommendations(
        self, improvements: list[str], accuracy: float, patterns: list[str]
    ) -> list[str]:
        """Generate specific recommendations.

        Args:
            improvements: Identified improvement areas
            accuracy: Estimation accuracy score
            patterns: Discovered patterns

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # Estimation recommendations
        if accuracy < 70:
            recommendations.append(
                "ACTION: Review estimation methodology - consider using historical averages"
            )
        elif accuracy < 85:
            recommendations.append(
                "ACTION: Refine estimates using recent completion data"
            )
        else:
            recommendations.append("✓ Estimation accuracy is good - maintain approach")

        # Quality recommendations
        if "declining" in str(improvements):
            recommendations.append(
                "ACTION: Schedule health reviews every 30 min during execution"
            )
        if "blocked" in str(improvements):
            recommendations.append(
                "ACTION: Identify and resolve top blocker categories"
            )
        if "failures" in str(improvements):
            recommendations.append(
                "ACTION: Post-mortem on failed tasks to identify systemic issues"
            )

        # Pattern-based recommendations
        if patterns and "Average task duration" in patterns[0]:
            recommendations.append(
                "ACTION: Use average duration for future similar tasks"
            )

        # Default recommendation
        if not recommendations:
            recommendations.append(
                "✓ Continue current practices - metrics are positive"
            )

        return recommendations

    async def should_trigger_review(
        self, project_id: int
    ) -> tuple[bool, str]:
        """Check if analytics review should be triggered.

        Args:
            project_id: Project to check

        Returns:
            Tuple of (should_trigger, reason)
        """
        try:
            # Check if >10 completed tasks in past 7 days
            completed_count = self._count_completed_tasks(project_id, 7)
            if completed_count >= 10:
                return (True, "10+ tasks completed this week")

            # Check if any critical health issues
            dashboard = await self.monitor.get_project_dashboard(project_id)
            if (
                hasattr(dashboard, "average_health_score")
                and dashboard.average_health_score < 0.5
            ):
                return (True, "Critical health issues detected")

            # Check if estimation accuracy is degrading
            accuracy_data = await self.analytics.analyze_estimation_accuracy(
                project_id, days_back=7
            )
            accuracy_score = (
                accuracy_data.accuracy_rate
                if hasattr(accuracy_data, "accuracy_rate")
                else accuracy_data.get("accuracy_rate", 100)
                if isinstance(accuracy_data, dict)
                else 100
            )
            if accuracy_score < 65:
                return (True, "Estimation accuracy below threshold")

            return (False, "No trigger conditions met")
        except Exception as e:
            return (False, f"Error checking trigger: {e}")

    async def get_project_forecast(self, project_id: int) -> dict:
        """Generate project forecast based on recent analytics.

        Args:
            project_id: Project to forecast

        Returns:
            Dictionary with forecast metrics
        """
        try:
            # Get recent analytics
            summary = await self.analyze_project(project_id, "weekly")

            # Get active tasks count
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM prospective_tasks
                WHERE project_id = ? AND status IN ('active', 'pending')
                """,
                (project_id,),
            )
            active_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            # Estimate completion date based on velocity
            velocity = (
                summary.completed_tasks / 7
            )  # tasks per day
            estimated_days = active_count / velocity if velocity > 0 else 0

            return {
                "active_tasks": active_count,
                "weekly_velocity": velocity,
                "estimated_completion_days": estimated_days,
                "completion_confidence": "high"
                if summary.estimation_accuracy > 80
                else "medium"
                if summary.estimation_accuracy > 70
                else "low",
                "risk_level": "low"
                if summary.average_health_score > 0.75
                else "medium"
                if summary.average_health_score > 0.5
                else "high",
            }
        except Exception:
            return {
                "error": "Unable to generate forecast",
                "active_tasks": 0,
                "weekly_velocity": 0,
                "estimated_completion_days": 0,
            }
