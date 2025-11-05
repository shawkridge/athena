"""Metrics Aggregator for project-wide metrics consolidation and analysis.

Provides:
- Project-wide metrics aggregation
- Trend tracking and progression
- Benchmark comparisons
- Statistical analysis across symbols
- Quality trends over time
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

from .symbol_models import Symbol
from .code_quality_scorer import CodeQualityScore, QualityRating


class TrendDirection(str, Enum):
    """Direction of metric trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class MetricStats:
    """Statistical metrics for a quality metric."""
    metric_name: str
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_75: float


@dataclass
class QualityTrend:
    """Quality metric trend over time."""
    metric_name: str
    previous_value: float
    current_value: float
    change: float  # Positive = improvement
    percent_change: float
    direction: TrendDirection
    is_significant: bool  # Change > threshold


@dataclass
class ProjectMetrics:
    """Aggregated project metrics."""
    total_symbols: int
    analyzed_symbols: int
    overall_quality_score: float
    overall_quality_rating: str

    # Rating distribution
    excellent_count: int
    good_count: int
    fair_count: int
    poor_count: int
    critical_count: int

    # Issues summary
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int

    # Component statistics
    security_stats: MetricStats
    performance_stats: MetricStats
    quality_stats: MetricStats
    maintainability_stats: MetricStats
    testability_stats: MetricStats
    documentation_stats: MetricStats

    # Trends
    trends: List[QualityTrend] = field(default_factory=list)

    # Top performers and worst performers
    top_performers: List[Tuple[str, float]] = field(default_factory=list)
    worst_performers: List[Tuple[str, float]] = field(default_factory=list)

    # Health metrics
    health_score: float = 0.0  # Overall project health (0-1)
    code_churn_risk: float = 0.0  # Risk based on issue concentration


class MetricsAggregator:
    """Aggregates metrics across multiple symbols and tracks trends."""

    def __init__(self):
        """Initialize aggregator."""
        self.scores: List[CodeQualityScore] = []
        self.historical_metrics: List[ProjectMetrics] = []
        self.current_metrics: Optional[ProjectMetrics] = None

    def add_scores(self, scores: List[CodeQualityScore]) -> None:
        """Add quality scores to aggregate.

        Args:
            scores: List of CodeQualityScore objects
        """
        self.scores = scores

    def aggregate(self) -> ProjectMetrics:
        """Aggregate all scores into project metrics.

        Returns:
            ProjectMetrics with aggregated data
        """
        if not self.scores:
            return self._create_empty_metrics()

        # Count ratings
        excellent = sum(1 for s in self.scores if s.overall_rating == QualityRating.EXCELLENT)
        good = sum(1 for s in self.scores if s.overall_rating == QualityRating.GOOD)
        fair = sum(1 for s in self.scores if s.overall_rating == QualityRating.FAIR)
        poor = sum(1 for s in self.scores if s.overall_rating == QualityRating.POOR)
        critical = sum(1 for s in self.scores if s.overall_rating == QualityRating.CRITICAL)

        # Overall quality
        overall_quality_score = statistics.mean(s.overall_score for s in self.scores)
        overall_rating = self._score_to_rating(overall_quality_score)

        # Issues
        total_issues = sum(s.total_issues for s in self.scores)
        critical_issues = sum(s.critical_issues for s in self.scores)
        high_issues = sum(s.high_issues for s in self.scores)
        medium_issues = sum(s.medium_issues for s in self.scores)
        low_issues = sum(s.low_issues for s in self.scores)

        # Component statistics
        security_stats = self._calculate_component_stats("security")
        performance_stats = self._calculate_component_stats("performance")
        quality_stats = self._calculate_component_stats("quality")
        maintainability_stats = self._calculate_component_stats("maintainability")
        testability_stats = self._calculate_component_stats("testability")
        documentation_stats = self._calculate_component_stats("documentation")

        # Top/worst performers
        top_performers = self._get_top_performers(5)
        worst_performers = self._get_worst_performers(5)

        # Health score
        health_score = self._calculate_health_score(
            excellent, critical, total_issues, len(self.scores)
        )

        # Code churn risk
        code_churn_risk = self._calculate_code_churn_risk(critical_issues, len(self.scores))

        metrics = ProjectMetrics(
            total_symbols=len(self.scores),
            analyzed_symbols=len(self.scores),
            overall_quality_score=overall_quality_score,
            overall_quality_rating=overall_rating.value,
            excellent_count=excellent,
            good_count=good,
            fair_count=fair,
            poor_count=poor,
            critical_count=critical,
            total_issues=total_issues,
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            security_stats=security_stats,
            performance_stats=performance_stats,
            quality_stats=quality_stats,
            maintainability_stats=maintainability_stats,
            testability_stats=testability_stats,
            documentation_stats=documentation_stats,
            top_performers=top_performers,
            worst_performers=worst_performers,
            health_score=health_score,
            code_churn_risk=code_churn_risk,
        )

        # Calculate trends if we have historical data
        if self.historical_metrics:
            metrics.trends = self._calculate_trends(metrics)

        self.current_metrics = metrics
        return metrics

    def _calculate_component_stats(self, component_name: str) -> MetricStats:
        """Calculate statistics for a component."""
        values = []
        for score in self.scores:
            for cs in score.component_scores:
                if cs.metric.value == component_name:
                    values.append(cs.score)
                    break

        if not values:
            return MetricStats(
                metric_name=component_name,
                count=0,
                mean=0.0,
                median=0.0,
                std_dev=0.0,
                min_value=0.0,
                max_value=0.0,
                percentile_25=0.0,
                percentile_75=0.0,
            )

        sorted_values = sorted(values)
        return MetricStats(
            metric_name=component_name,
            count=len(values),
            mean=statistics.mean(values),
            median=statistics.median(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min_value=min(values),
            max_value=max(values),
            percentile_25=sorted_values[len(sorted_values) // 4],
            percentile_75=sorted_values[3 * len(sorted_values) // 4],
        )

    def _get_top_performers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get top performing symbols."""
        sorted_scores = sorted(self.scores, key=lambda s: s.overall_score, reverse=True)
        return [(s.symbol.name, s.overall_score) for s in sorted_scores[:limit]]

    def _get_worst_performers(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get worst performing symbols."""
        sorted_scores = sorted(self.scores, key=lambda s: s.overall_score)
        return [(s.symbol.name, s.overall_score) for s in sorted_scores[:limit]]

    def _calculate_health_score(self, excellent: int, critical: int, total_issues: int, total: int) -> float:
        """Calculate overall project health score (0-1)."""
        if total == 0:
            return 0.0

        excellent_ratio = excellent / total
        critical_ratio = critical / total
        issues_ratio = min(1.0, total_issues / max(1, total * 5))  # Expected ~5 issues per symbol

        health = (excellent_ratio * 0.4) - (critical_ratio * 0.4) - (issues_ratio * 0.2)
        return max(0.0, min(1.0, health))

    def _calculate_code_churn_risk(self, critical_issues: int, total: int) -> float:
        """Calculate code churn risk (0-1)."""
        if total == 0:
            return 0.0
        risk = min(1.0, critical_issues / max(1, total))
        return risk

    def _calculate_trends(self, current: ProjectMetrics) -> List[QualityTrend]:
        """Calculate trends from historical data."""
        if not self.historical_metrics:
            return []

        previous = self.historical_metrics[-1]
        trends = []

        # Overall quality trend
        change = current.overall_quality_score - previous.overall_quality_score
        percent_change = (change / max(0.1, previous.overall_quality_score)) * 100
        direction = TrendDirection.IMPROVING if change > 0 else TrendDirection.DECLINING if change < 0 else TrendDirection.STABLE
        is_significant = abs(change) > 5.0

        trends.append(QualityTrend(
            metric_name="overall_quality",
            previous_value=previous.overall_quality_score,
            current_value=current.overall_quality_score,
            change=change,
            percent_change=percent_change,
            direction=direction,
            is_significant=is_significant,
        ))

        # Issues trend
        issues_change = current.total_issues - previous.total_issues
        issues_percent = (issues_change / max(1, previous.total_issues)) * 100
        issues_direction = TrendDirection.DECLINING if issues_change < 0 else TrendDirection.IMPROVING if issues_change > 0 else TrendDirection.STABLE
        trends.append(QualityTrend(
            metric_name="total_issues",
            previous_value=float(previous.total_issues),
            current_value=float(current.total_issues),
            change=float(issues_change),
            percent_change=issues_percent,
            direction=issues_direction,
            is_significant=abs(issues_change) > 3,
        ))

        # Health trend
        health_change = current.health_score - previous.health_score
        health_direction = TrendDirection.IMPROVING if health_change > 0 else TrendDirection.DECLINING if health_change < 0 else TrendDirection.STABLE
        trends.append(QualityTrend(
            metric_name="health_score",
            previous_value=previous.health_score,
            current_value=current.health_score,
            change=health_change,
            percent_change=(health_change / max(0.1, previous.health_score)) * 100,
            direction=health_direction,
            is_significant=abs(health_change) > 0.1,
        ))

        return trends

    def _score_to_rating(self, score: float) -> QualityRating:
        """Convert score to rating."""
        if score >= 85:
            return QualityRating.EXCELLENT
        elif score >= 70:
            return QualityRating.GOOD
        elif score >= 55:
            return QualityRating.FAIR
        elif score >= 40:
            return QualityRating.POOR
        else:
            return QualityRating.CRITICAL

    def _create_empty_metrics(self) -> ProjectMetrics:
        """Create empty metrics."""
        empty_stats = MetricStats(
            metric_name="",
            count=0,
            mean=0.0,
            median=0.0,
            std_dev=0.0,
            min_value=0.0,
            max_value=0.0,
            percentile_25=0.0,
            percentile_75=0.0,
        )
        return ProjectMetrics(
            total_symbols=0,
            analyzed_symbols=0,
            overall_quality_score=0.0,
            overall_quality_rating=QualityRating.CRITICAL.value,
            excellent_count=0,
            good_count=0,
            fair_count=0,
            poor_count=0,
            critical_count=0,
            total_issues=0,
            critical_issues=0,
            high_issues=0,
            medium_issues=0,
            low_issues=0,
            security_stats=empty_stats,
            performance_stats=empty_stats,
            quality_stats=empty_stats,
            maintainability_stats=empty_stats,
            testability_stats=empty_stats,
            documentation_stats=empty_stats,
        )

    def record_metrics(self, metrics: ProjectMetrics) -> None:
        """Record metrics for trend tracking.

        Args:
            metrics: ProjectMetrics to record
        """
        self.historical_metrics.append(metrics)

    def get_aggregate_report(self) -> Dict:
        """Generate aggregate metrics report."""
        if self.current_metrics is None:
            return {
                "status": "no_data",
                "message": "No metrics aggregated yet"
            }

        metrics = self.current_metrics
        return {
            "status": "complete",
            "total_symbols": metrics.total_symbols,
            "overall_quality_score": round(metrics.overall_quality_score, 2),
            "overall_quality_rating": metrics.overall_quality_rating,
            "health_score": round(metrics.health_score, 2),
            "code_churn_risk": round(metrics.code_churn_risk, 2),
            "rating_distribution": {
                "excellent": metrics.excellent_count,
                "good": metrics.good_count,
                "fair": metrics.fair_count,
                "poor": metrics.poor_count,
                "critical": metrics.critical_count,
            },
            "issues_summary": {
                "total": metrics.total_issues,
                "critical": metrics.critical_issues,
                "high": metrics.high_issues,
                "medium": metrics.medium_issues,
                "low": metrics.low_issues,
            },
            "component_averages": {
                "security": round(metrics.security_stats.mean, 2),
                "performance": round(metrics.performance_stats.mean, 2),
                "quality": round(metrics.quality_stats.mean, 2),
                "maintainability": round(metrics.maintainability_stats.mean, 2),
                "testability": round(metrics.testability_stats.mean, 2),
                "documentation": round(metrics.documentation_stats.mean, 2),
            },
            "top_performers": metrics.top_performers[:5],
            "worst_performers": metrics.worst_performers[:5],
            "trends": [
                {
                    "metric": t.metric_name,
                    "direction": t.direction.value,
                    "change": round(t.change, 2),
                    "percent_change": round(t.percent_change, 1),
                    "is_significant": t.is_significant,
                }
                for t in metrics.trends
            ] if metrics.trends else [],
        }
