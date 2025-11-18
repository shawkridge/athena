"""
PHASE 6: Estimation Analyzer

Analyzes task estimation accuracy and provides insights into estimation patterns.
Tracks MAPE, RMSE, bias, and identifies systematic over/underestimation patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

from ..core.database import Database


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskComplexity(str, Enum):
    """Task complexity levels."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class AccuracyMetrics:
    """Metrics for estimation accuracy."""

    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    bias: float  # Over/underestimation bias (-1 to 1)
    accuracy_percentage: float  # % of estimates within ±15%
    sample_size: int
    confidence_interval: Tuple[float, float]  # (lower, upper) bounds at 95%

    def __str__(self) -> str:
        """Human-readable representation."""
        accuracy_emoji = (
            "✓"
            if self.accuracy_percentage >= 80
            else "⚠" if self.accuracy_percentage >= 60 else "✗"
        )
        return (
            f"{accuracy_emoji} MAPE: {self.mape:.1f}% | "
            f"RMSE: {self.rmse:.1f}h | "
            f"Bias: {self.bias:+.1f} | "
            f"Accuracy: {self.accuracy_percentage:.0f}% | "
            f"n={self.sample_size}"
        )


@dataclass
class Trend:
    """A trend in estimation accuracy."""

    period: str  # "week" | "month"
    start_date: datetime
    end_date: datetime
    metrics: AccuracyMetrics
    direction: str  # "improving" | "degrading" | "stable"
    change_percentage: float  # % change from previous period


@dataclass
class EstimationPattern:
    """A discovered pattern in estimation."""

    name: str
    description: str
    affected_type: str  # Task type this pattern affects
    frequency: int  # How many tasks match this pattern
    avg_error: float  # Average error in this pattern (percentage)
    error_direction: str  # "underestimated" | "overestimated"
    suggested_action: str  # Recommended action
    confidence: float  # 0-1 confidence in pattern


@dataclass
class TaskEstimate:
    """A task estimation record."""

    task_id: int
    estimated_hours: float
    actual_hours: float
    error_hours: float  # actual - estimated
    error_percentage: float  # (actual - estimated) / estimated * 100
    task_type: str
    priority: str
    complexity: str
    assignee: Optional[str]
    created_at: datetime
    completed_at: datetime


@dataclass
class AccuracyReport:
    """Complete accuracy analysis report."""

    project_id: int
    overall: AccuracyMetrics
    by_priority: Dict[str, AccuracyMetrics]
    by_complexity: Dict[str, AccuracyMetrics]
    by_assignee: Dict[str, AccuracyMetrics]
    by_task_type: Dict[str, AccuracyMetrics]
    trends: List[Trend] = field(default_factory=list)
    outliers: List[TaskEstimate] = field(default_factory=list)
    patterns: List[EstimationPattern] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return summary text."""
        lines = [
            "=" * 60,
            "ESTIMATION ACCURACY REPORT",
            "=" * 60,
            f"\nOverall Accuracy: {self.overall}",
            "\nBy Priority:",
        ]
        for priority, metrics in sorted(self.by_priority.items()):
            lines.append(f"  {priority:10s}: {metrics}")

        lines.extend(
            [
                "\nBy Complexity:",
            ]
        )
        for complexity, metrics in sorted(self.by_complexity.items()):
            lines.append(f"  {complexity:10s}: {metrics}")

        if self.trends:
            lines.append("\nTrends:")
            for trend in self.trends[:3]:  # Top 3 trends
                direction_emoji = (
                    "📈"
                    if trend.direction == "improving"
                    else "📉" if trend.direction == "degrading" else "➡️"
                )
                lines.append(
                    f"  {direction_emoji} {trend.period}: {trend.direction} ({trend.change_percentage:+.1f}%)"
                )

        if self.patterns:
            lines.append("\nKey Patterns:")
            for pattern in self.patterns[:5]:  # Top 5 patterns
                lines.append(f"  • {pattern.name}: {pattern.description}")
                lines.append(f"    Action: {pattern.suggested_action}")

        if self.recommendations:
            lines.append("\nRecommendations:")
            for rec in self.recommendations[:5]:
                lines.append(f"  ✓ {rec}")

        lines.append("=" * 60)
        return "\n".join(lines)


class EstimationAnalyzer:
    """Analyzes task estimation accuracy and provides insights."""

    def __init__(self, db: Database, project_id: int):
        """Initialize EstimationAnalyzer.

        Args:
            db: Database instance
            project_id: Project to analyze
        """
        self.db = db
        self.project_id = project_id
        self.cursor = db.conn.cursor()

    def analyze_accuracy(self, days_back: int = 30) -> AccuracyReport:
        """Analyze estimation vs actual for past N days.

        Args:
            days_back: Number of days to analyze

        Returns:
            AccuracyReport with comprehensive metrics
        """
        # Query completed tasks from past N days
        tasks = self._get_completed_tasks(days_back)

        if not tasks:
            # Return empty report
            return AccuracyReport(
                project_id=self.project_id,
                overall=AccuracyMetrics(0, 0, 0, 0, 0, (0, 0)),
                by_priority={},
                by_complexity={},
                by_assignee={},
                by_task_type={},
            )

        # Calculate overall metrics
        overall = self._calculate_metrics(tasks)

        # Break down by dimensions
        by_priority = self._analyze_by_dimension(tasks, "priority")
        by_complexity = self._analyze_by_dimension(tasks, "complexity")
        by_assignee = self._analyze_by_dimension(tasks, "assignee")
        by_task_type = self._analyze_by_dimension(tasks, "task_type")

        # Find trends
        trends = self._analyze_trends(days_back)

        # Find outliers
        outliers = self._find_outliers(tasks)

        # Discover patterns
        patterns = self._discover_patterns(tasks, by_priority, by_complexity, by_task_type)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall, by_priority, by_complexity, patterns
        )

        return AccuracyReport(
            project_id=self.project_id,
            overall=overall,
            by_priority=by_priority,
            by_complexity=by_complexity,
            by_assignee=by_assignee,
            by_task_type=by_task_type,
            trends=trends,
            outliers=outliers,
            patterns=patterns,
            recommendations=recommendations,
        )

    def _get_completed_tasks(self, days_back: int) -> List[TaskEstimate]:
        """Get completed tasks from past N days."""
        # This would query the prospective_tasks + execution history
        # For now, return empty list (would be implemented with real DB queries)
        return []

    def _calculate_metrics(self, tasks: List[TaskEstimate]) -> AccuracyMetrics:
        """Calculate MAPE, RMSE, bias, and confidence interval."""
        if not tasks:
            return AccuracyMetrics(0, 0, 0, 0, 0, (0, 0))

        n = len(tasks)
        errors = []
        error_percentages = []
        within_tolerance = 0

        for task in tasks:
            error_pct = task.error_percentage
            error_percentages.append(abs(error_pct))

            # Check if within ±15%
            if abs(error_pct) <= 15:
                within_tolerance += 1

            errors.append(task.error_hours)

        # MAPE: Mean Absolute Percentage Error
        mape = sum(error_percentages) / n

        # RMSE: Root Mean Square Error
        rmse = math.sqrt(sum(e**2 for e in errors) / n)

        # Bias: Average error (positive = underestimated, negative = overestimated)
        bias = sum(task.error_percentage for task in tasks) / n / 100

        # Accuracy percentage: % within ±15%
        accuracy_pct = (within_tolerance / n) * 100

        # Confidence interval (95%) using standard error
        std_error = math.sqrt(sum((abs(e) - mape) ** 2 for e in error_percentages) / n) / math.sqrt(
            n
        )
        ci_lower = max(0, mape - 1.96 * std_error)
        ci_upper = mape + 1.96 * std_error

        return AccuracyMetrics(
            mape=mape,
            rmse=rmse,
            bias=bias,
            accuracy_percentage=accuracy_pct,
            sample_size=n,
            confidence_interval=(ci_lower, ci_upper),
        )

    def _analyze_by_dimension(
        self, tasks: List[TaskEstimate], dimension: str
    ) -> Dict[str, AccuracyMetrics]:
        """Break down accuracy by priority, complexity, assignee, etc."""
        grouped: Dict[str, List[TaskEstimate]] = {}

        for task in tasks:
            key = getattr(task, dimension, "unknown")
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(task)

        result = {}
        for key, group_tasks in grouped.items():
            result[key] = self._calculate_metrics(group_tasks)

        return result

    def _analyze_trends(self, days_back: int) -> List[Trend]:
        """Analyze trends over time."""
        # Would analyze weekly/monthly trends
        return []

    def _find_outliers(
        self, tasks: List[TaskEstimate], threshold: float = 50.0
    ) -> List[TaskEstimate]:
        """Find tasks with extreme estimation errors."""
        return [t for t in tasks if abs(t.error_percentage) > threshold]

    def _discover_patterns(
        self,
        tasks: List[TaskEstimate],
        by_priority: Dict[str, AccuracyMetrics],
        by_complexity: Dict[str, AccuracyMetrics],
        by_task_type: Dict[str, AccuracyMetrics],
    ) -> List[EstimationPattern]:
        """Discover patterns in estimation errors."""
        patterns: List[EstimationPattern] = []

        # Find systematically over/underestimated types
        for task_type, metrics in by_task_type.items():
            if metrics.sample_size >= 3:  # Minimum sample size
                if metrics.bias > 0.15:  # Consistently underestimated
                    patterns.append(
                        EstimationPattern(
                            name=f"{task_type} underestimated",
                            description=f"{task_type} tasks are consistently underestimated by {metrics.mape:.0f}%",
                            affected_type=task_type,
                            frequency=metrics.sample_size,
                            avg_error=metrics.mape,
                            error_direction="underestimated",
                            suggested_action=f"Add {metrics.mape:.0f}% buffer to {task_type} estimates",
                            confidence=min(1.0, metrics.sample_size / 10),
                        )
                    )
                elif metrics.bias < -0.15:  # Consistently overestimated
                    patterns.append(
                        EstimationPattern(
                            name=f"{task_type} overestimated",
                            description=f"{task_type} tasks are consistently overestimated by {abs(metrics.mape):.0f}%",
                            affected_type=task_type,
                            frequency=metrics.sample_size,
                            avg_error=metrics.mape,
                            error_direction="overestimated",
                            suggested_action=f"Reduce {task_type} estimates by {abs(metrics.mape):.0f}%",
                            confidence=min(1.0, metrics.sample_size / 10),
                        )
                    )

        # Sort by frequency
        patterns.sort(key=lambda p: p.frequency, reverse=True)
        return patterns[:10]  # Return top 10 patterns

    def _generate_recommendations(
        self,
        overall: AccuracyMetrics,
        by_priority: Dict[str, AccuracyMetrics],
        by_complexity: Dict[str, AccuracyMetrics],
        patterns: List[EstimationPattern],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Overall accuracy recommendations
        if overall.accuracy_percentage < 60:
            recommendations.append(
                "Overall estimation accuracy is poor - review estimation process"
            )
        elif overall.accuracy_percentage < 80:
            recommendations.append(
                "Estimation accuracy is below target - apply identified patterns"
            )

        # Priority-specific recommendations
        for priority, metrics in by_priority.items():
            if priority == "critical" and metrics.accuracy_percentage < 80:
                recommendations.append(
                    f"Critical tasks have {metrics.accuracy_percentage:.0f}% accuracy - prioritize estimation for these"
                )

        # Pattern-based recommendations
        for pattern in patterns[:3]:
            recommendations.append(pattern.suggested_action)

        return recommendations

    def accuracy_by_dimension(
        self, dimension: str = "priority", days_back: int = 30
    ) -> Dict[str, AccuracyMetrics]:
        """Get accuracy metrics broken down by dimension."""
        tasks = self._get_completed_tasks(days_back)
        return self._analyze_by_dimension(tasks, dimension)

    def identify_estimation_patterns(self, top_n: int = 10) -> List[EstimationPattern]:
        """Identify patterns in estimation errors."""
        tasks = self._get_completed_tasks(30)
        by_type = self._analyze_by_dimension(tasks, "task_type")
        return self._discover_patterns(tasks, {}, {}, by_type)[:top_n]

    def recommend_adjustments(self) -> List[str]:
        """Recommend process changes based on analysis."""
        report = self.analyze_accuracy()
        return report.recommendations
