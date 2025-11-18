"""Estimation Improver Skill - Calibrate estimates from historical patterns.

Uses accuracy data and patterns to improve future task estimates by:
- Calculating adjustment multipliers by task type
- Tracking confidence scores
- Identifying variance sources
- Providing estimation heuristics
"""

from typing import Dict, List
from dataclasses import dataclass
from ..integration.analytics import TaskAnalytics
from ..core.database import Database


@dataclass
class EstimationMultiplier:
    """Adjustment multiplier for task type estimates."""

    task_type: str
    base_multiplier: float  # 1.0 = no adjustment
    confidence: float  # 0.0-1.0
    sample_count: int
    underestimate_rate: float
    overestimate_rate: float
    variance: float
    recommendations: List[str]


class EstimationImprover:
    """Improve task estimates using historical data."""

    def __init__(self, db: Database):
        """Initialize estimation improver.

        Args:
            db: Database connection
        """
        self.db = db
        self.analytics = TaskAnalytics(db)

    async def get_multipliers_by_task_type(
        self, project_id: int, days: int = 30
    ) -> Dict[str, EstimationMultiplier]:
        """Get estimation multipliers by task type.

        Args:
            project_id: Project to analyze
            days: Number of days of history to use

        Returns:
            Dictionary of task_type -> EstimationMultiplier
        """
        # Analyze estimation accuracy
        accuracy_data = await self.analytics.analyze_estimation_accuracy(project_id, days_back=days)

        # Discover patterns
        patterns_data = await self.analytics.discover_patterns(project_id)

        multipliers = {}

        # Extract task types from patterns
        task_types = self._extract_task_types(patterns_data)

        for task_type in task_types:
            multiplier = self._calculate_multiplier_for_type(
                task_type, accuracy_data, patterns_data
            )
            multipliers[task_type] = multiplier

        return multipliers

    def _extract_task_types(self, patterns_data) -> List[str]:
        """Extract task types from pattern data.

        Args:
            patterns_data: Pattern discovery results

        Returns:
            List of task type names
        """
        task_types = [
            "implementation",
            "bug_fix",
            "refactoring",
            "documentation",
            "research",
            "testing",
        ]

        # Try to extract from patterns if available
        if isinstance(patterns_data, dict):
            if "task_types" in patterns_data:
                extracted = patterns_data["task_types"]
                if extracted:
                    return extracted

        return task_types

    def _calculate_multiplier_for_type(
        self, task_type: str, accuracy_data, patterns_data
    ) -> EstimationMultiplier:
        """Calculate adjustment multiplier for task type.

        Args:
            task_type: Type of task
            accuracy_data: Accuracy analysis
            patterns_data: Pattern data

        Returns:
            EstimationMultiplier with adjustment factor
        """
        # Default multipliers based on common patterns
        default_multipliers = {
            "implementation": 1.2,  # Often underestimated
            "bug_fix": 1.5,  # High variance
            "refactoring": 1.1,  # Moderate variance
            "documentation": 0.8,  # Usually faster
            "research": 1.8,  # Highly uncertain
            "testing": 1.3,  # Often underestimated
        }

        base_multiplier = default_multipliers.get(task_type, 1.0)

        # Try to extract actual accuracy for this type
        accuracy_score = (
            accuracy_data.accuracy_rate
            if hasattr(accuracy_data, "accuracy_rate")
            else accuracy_data.get("accuracy_rate", 75) if isinstance(accuracy_data, dict) else 75
        )

        # Calculate confidence based on accuracy
        confidence = min(accuracy_score / 100.0, 1.0)

        # Extract underestimate/overestimate rates
        under_rate = (
            accuracy_data.underestimate_count
            / max(
                accuracy_data.underestimate_count + accuracy_data.overestimate_count,
                1,
            )
            if hasattr(accuracy_data, "underestimate_count")
            else 0.5
        )
        over_rate = 1.0 - under_rate

        # Calculate variance
        variance = (
            accuracy_data.average_variance if hasattr(accuracy_data, "average_variance") else 0.25
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            task_type, confidence, under_rate, over_rate
        )

        return EstimationMultiplier(
            task_type=task_type,
            base_multiplier=base_multiplier,
            confidence=confidence,
            sample_count=self._get_sample_count_for_type(task_type),
            underestimate_rate=under_rate,
            overestimate_rate=over_rate,
            variance=variance,
            recommendations=recommendations,
        )

    def _get_sample_count_for_type(self, task_type: str) -> int:
        """Get sample count for task type.

        Args:
            task_type: Task type

        Returns:
            Number of historical tasks of this type
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM prospective_tasks
                WHERE content LIKE ? AND status = 'completed'
                """,
                (f"%{task_type}%",),
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            return 0

    def _generate_recommendations(
        self,
        task_type: str,
        confidence: float,
        under_rate: float,
        over_rate: float,
    ) -> List[str]:
        """Generate recommendations for estimation.

        Args:
            task_type: Task type
            confidence: Confidence score
            under_rate: Underestimate rate
            over_rate: Overestimate rate

        Returns:
            List of recommendations
        """
        recommendations = []

        if confidence < 0.5:
            recommendations.append(f"Low confidence in {task_type} estimates - gather more data")
        elif confidence < 0.7:
            recommendations.append(f"Moderate confidence in {task_type} estimates")
        else:
            recommendations.append(f"High confidence in {task_type} estimates")

        if under_rate > 0.6:
            recommendations.append(f"Tendency to underestimate {task_type} - add 20-30% buffer")
        elif over_rate > 0.6:
            recommendations.append(
                f"Tendency to overestimate {task_type} - reduce estimates by 10-15%"
            )

        if confidence >= 0.8:
            recommendations.append(f"Use multiplier adjustments for {task_type} estimates")

        return recommendations[:2]

    async def adjust_estimate(
        self,
        project_id: int,
        task_type: str,
        base_estimate_minutes: int,
    ) -> int:
        """Adjust task estimate based on historical data.

        Args:
            project_id: Project for context
            task_type: Type of task
            base_estimate_minutes: Initial estimate in minutes

        Returns:
            Adjusted estimate in minutes
        """
        multipliers = await self.get_multipliers_by_task_type(project_id)

        if task_type in multipliers:
            multiplier = multipliers[task_type]
            adjusted = int(base_estimate_minutes * multiplier.base_multiplier)
            return max(adjusted, 15)  # Minimum 15 minutes
        else:
            return base_estimate_minutes

    def estimate_confidence_interval(
        self,
        project_id: int,
        task_type: str,
        estimate_minutes: int,
    ) -> tuple[int, int]:
        """Get confidence interval for estimate.

        Args:
            project_id: Project
            task_type: Task type
            estimate_minutes: Central estimate

        Returns:
            Tuple of (lower_bound, upper_bound) in minutes
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT
                    AVG(actual_duration_minutes) as avg,
                    MAX(actual_duration_minutes) as max_dur,
                    MIN(actual_duration_minutes) as min_dur
                FROM prospective_tasks
                WHERE project_id = ? AND content LIKE ?
                AND status = 'completed' AND actual_duration_minutes IS NOT NULL
                """,
                (project_id, f"%{task_type}%"),
            )
            result = cursor.fetchone()

            if result and result[0]:
                avg = result[0]
                variance = (result[1] - result[2]) / 2 if result[1] and result[2] else avg * 0.5
                lower = max(int(estimate_minutes * 0.7), 15)
                upper = int(estimate_minutes * 1.3)
                return (lower, upper)
            else:
                # Default confidence interval
                lower = max(int(estimate_minutes * 0.7), 15)
                upper = int(estimate_minutes * 1.5)
                return (lower, upper)
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            # Fallback
            lower = max(int(estimate_minutes * 0.7), 15)
            upper = int(estimate_minutes * 1.5)
            return (lower, upper)

    async def suggest_estimate_improvement(self, project_id: int, days: int = 30) -> Dict[str, any]:
        """Suggest overall estimation improvements.

        Args:
            project_id: Project to analyze
            days: Days of history to consider

        Returns:
            Dictionary with improvement suggestions
        """
        accuracy_data = await self.analytics.analyze_estimation_accuracy(project_id, days_back=days)

        accuracy_score = (
            accuracy_data.accuracy_rate
            if hasattr(accuracy_data, "accuracy_rate")
            else accuracy_data.get("accuracy_rate", 0) if isinstance(accuracy_data, dict) else 0
        )

        suggestions = []

        if accuracy_score < 60:
            suggestions.append(
                "CRITICAL: Estimation accuracy very low - systematic recalibration needed"
            )
            suggestions.append("Action: Review recent failed estimates for patterns")
        elif accuracy_score < 75:
            suggestions.append("Estimation accuracy below target - apply type-specific multipliers")
            suggestions.append("Action: Use multiplier adjustments for common task types")
        elif accuracy_score < 85:
            suggestions.append("Estimation accuracy is good - fine-tune with variance data")
            suggestions.append("Action: Use confidence intervals for planning")
        else:
            suggestions.append("Excellent estimation accuracy - maintain approach")

        return {
            "current_accuracy": accuracy_score,
            "target_accuracy": 85,
            "suggestions": suggestions,
            "next_review_date": "7 days",
        }
