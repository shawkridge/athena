"""Execution Analytics - Cost tracking, performance trending, and forecasting."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import logging

from .models import TaskExecutionRecord

logger = logging.getLogger(__name__)


@dataclass
class ExecutionCost:
    """Cost metrics for an execution."""

    execution_id: str
    labor_cost: float  # Estimated labor cost
    resource_cost: float  # Resource consumption cost
    overhead_cost: float  # System overhead cost
    total_cost: float
    cost_per_hour: float
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TeamVelocity:
    """Team velocity metrics."""

    period_start: datetime
    period_end: datetime
    tasks_completed: int
    estimated_story_points: float
    actual_story_points: float
    velocity: float  # tasks per hour
    efficiency: float  # actual/estimated
    team_size: int
    productivity_index: float  # 0.0-1.0


@dataclass
class PerformanceTrend:
    """Performance trend data."""

    metric_name: str
    current_value: float
    previous_value: Optional[float]
    trend: str  # "improving", "declining", "stable"
    trend_strength: float  # -1.0 to 1.0
    percentage_change: float
    samples: int
    period: timedelta


@dataclass
class ExecutionForecast:
    """Forecast for future executions."""

    metric_name: str
    current_value: float
    forecasted_value: float
    confidence: float  # 0.0-1.0
    lower_bound: float
    upper_bound: float
    forecast_period: timedelta
    methodology: str  # "linear", "exponential", "moving_average"


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""

    execution_id: str
    period_start: datetime
    period_end: datetime
    total_executions: int
    total_cost: float
    average_cost_per_execution: float
    team_velocity: TeamVelocity
    performance_trends: List[PerformanceTrend]
    forecasts: List[ExecutionForecast]
    recommendations: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


class ExecutionAnalytics:
    """Analyze execution metrics, costs, and performance."""

    def __init__(self):
        """Initialize analytics engine."""
        self.execution_history: Dict[str, Dict] = {}
        self.cost_history: Dict[str, ExecutionCost] = {}
        self.velocity_history: List[TeamVelocity] = []
        self.trends: Dict[str, List[float]] = {}  # metric -> values
        self.forecasts: Dict[str, ExecutionForecast] = {}

    def record_execution_metrics(
        self,
        execution_id: str,
        execution_records: Dict[str, TaskExecutionRecord],
        team_size: int = 1,
    ) -> None:
        """Record execution metrics for analytics.

        Args:
            execution_id: Unique execution ID
            execution_records: Dictionary of task execution records
            team_size: Number of team members
        """
        total_duration = timedelta(0)
        task_count = 0
        failed_count = 0

        for record in execution_records.values():
            task_count += 1
            if record.actual_duration:
                total_duration += record.actual_duration
            if record.outcome and record.outcome.value == "failure":
                failed_count += 1

        success_rate = (task_count - failed_count) / task_count if task_count > 0 else 0.0

        self.execution_history[execution_id] = {
            "total_duration": total_duration,
            "task_count": task_count,
            "success_rate": success_rate,
            "failed_count": failed_count,
            "team_size": team_size,
            "timestamp": datetime.utcnow(),
        }

        logger.info(f"Recorded execution metrics for {execution_id}")

    def calculate_execution_cost(
        self,
        execution_id: str,
        labor_rate_per_hour: float = 150.0,  # $ per hour
        resource_cost_per_hour: float = 50.0,  # $ per hour
        team_size: int = 1,
    ) -> ExecutionCost:
        """Calculate cost metrics for an execution.

        Args:
            execution_id: Execution ID
            labor_rate_per_hour: Labor cost per hour
            resource_cost_per_hour: Resource cost per hour
            team_size: Number of team members

        Returns:
            ExecutionCost with breakdown
        """
        if execution_id not in self.execution_history:
            logger.warning(f"Execution {execution_id} not found in history")
            return ExecutionCost(
                execution_id=execution_id,
                labor_cost=0.0,
                resource_cost=0.0,
                overhead_cost=0.0,
                total_cost=0.0,
                cost_per_hour=0.0,
            )

        metrics = self.execution_history[execution_id]
        duration_hours = metrics["total_duration"].total_seconds() / 3600

        # Calculate labor cost (team_size * labor_rate * hours)
        labor_cost = labor_rate_per_hour * team_size * duration_hours

        # Calculate resource cost
        resource_cost = resource_cost_per_hour * duration_hours

        # Calculate overhead (5% of total)
        total_before_overhead = labor_cost + resource_cost
        overhead_cost = total_before_overhead * 0.05

        total_cost = total_before_overhead + overhead_cost
        cost_per_hour = total_cost / duration_hours if duration_hours > 0 else 0.0

        cost = ExecutionCost(
            execution_id=execution_id,
            labor_cost=labor_cost,
            resource_cost=resource_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost,
            cost_per_hour=cost_per_hour,
        )

        self.cost_history[execution_id] = cost
        logger.info(f"Calculated cost for {execution_id}: ${total_cost:.2f}")

        return cost

    def calculate_team_velocity(
        self,
        period_start: datetime,
        period_end: datetime,
        executions: List[str],
        team_size: int = 1,
        points_per_task: float = 1.0,
    ) -> TeamVelocity:
        """Calculate team velocity for a period.

        Args:
            period_start: Start of period
            period_end: End of period
            executions: List of execution IDs in period
            team_size: Number of team members
            points_per_task: Story points per task (default 1.0)

        Returns:
            TeamVelocity metrics
        """
        total_tasks = 0
        total_duration = timedelta(0)
        total_estimated_points = 0.0
        total_actual_points = 0.0

        for exec_id in executions:
            if exec_id in self.execution_history:
                metrics = self.execution_history[exec_id]
                completed_tasks = metrics["task_count"] - metrics["failed_count"]
                total_tasks += completed_tasks
                total_duration += metrics["total_duration"]

                # Estimated points = all tasks * points_per_task
                total_estimated_points += metrics["task_count"] * points_per_task

                # Actual points = completed tasks * points_per_task
                total_actual_points += completed_tasks * points_per_task

        # Calculate velocity (tasks per hour)
        duration_hours = total_duration.total_seconds() / 3600
        velocity = total_tasks / duration_hours if duration_hours > 0 else 0.0

        # Calculate efficiency (actual/estimated)
        efficiency = (
            (total_actual_points / total_estimated_points) if total_estimated_points > 0 else 0.0
        )

        # Productivity index (0-1 scale)
        productivity_index = min(1.0, efficiency * velocity / 5.0)  # Normalize to 5 tasks/hr

        team_velocity = TeamVelocity(
            period_start=period_start,
            period_end=period_end,
            tasks_completed=total_tasks,
            estimated_story_points=total_estimated_points,
            actual_story_points=total_actual_points,
            velocity=velocity,
            efficiency=efficiency,
            team_size=team_size,
            productivity_index=productivity_index,
        )

        self.velocity_history.append(team_velocity)
        logger.info(
            f"Calculated velocity: {velocity:.2f} tasks/hr, " f"efficiency: {efficiency:.1%}"
        )

        return team_velocity

    def calculate_performance_trends(
        self, metric_name: str, window_size: int = 5
    ) -> Optional[PerformanceTrend]:
        """Calculate performance trend for a metric.

        Args:
            metric_name: Name of metric to analyze
            window_size: Number of recent samples to use

        Returns:
            PerformanceTrend or None
        """
        if metric_name not in self.trends or len(self.trends[metric_name]) < 2:
            return None

        values = self.trends[metric_name][-window_size:]
        if len(values) < 2:
            return None

        current_value = values[-1]
        previous_value = values[-2] if len(values) > 1 else None

        # Calculate trend
        if len(values) > 2:
            # Linear regression to determine trend
            avg_change = (values[-1] - values[0]) / (len(values) - 1)
        else:
            avg_change = (values[-1] - values[0]) if previous_value else 0.0

        # Determine if change is "improving" or "declining"
        # This is context-dependent, but we'll use absolute change here
        abs_change = abs(avg_change)
        threshold = 0.02  # 2% change threshold (more sensitive)

        if avg_change < -threshold:  # Significant negative change
            trend = "improving"  # Decreasing is better for most metrics
            trend_strength = min(1.0, abs_change / current_value if current_value != 0 else 0)
        elif avg_change > threshold:  # Significant positive change
            trend = "declining"  # Increasing is worse for most metrics
            trend_strength = min(1.0, abs_change / current_value if current_value != 0 else 0)
        else:
            trend = "stable"
            trend_strength = 0.0

        # Calculate percentage change
        if previous_value and previous_value != 0:
            percentage_change = ((current_value - previous_value) / previous_value) * 100
        else:
            percentage_change = 0.0

        period = timedelta(days=len(values))

        perf_trend = PerformanceTrend(
            metric_name=metric_name,
            current_value=current_value,
            previous_value=previous_value,
            trend=trend,
            trend_strength=trend_strength,
            percentage_change=percentage_change,
            samples=len(values),
            period=period,
        )

        logger.info(
            f"Trend for {metric_name}: {trend} "
            f"({percentage_change:+.1f}%, strength={trend_strength:.2f})"
        )

        return perf_trend

    def forecast_metric(
        self,
        metric_name: str,
        forecast_periods: int = 5,
        methodology: str = "moving_average",
    ) -> Optional[ExecutionForecast]:
        """Forecast future value of a metric.

        Args:
            metric_name: Metric to forecast
            forecast_periods: Number of periods to forecast
            methodology: Forecasting method

        Returns:
            ExecutionForecast or None
        """
        if metric_name not in self.trends or len(self.trends[metric_name]) < 3:
            return None

        values = self.trends[metric_name]
        current_value = values[-1]

        # Select forecasting method
        if methodology == "moving_average":
            window = min(3, len(values))
            recent_values = values[-window:]
            forecasted_value = statistics.mean(recent_values)
            confidence = 0.7

        elif methodology == "exponential":
            # Simple exponential smoothing
            alpha = 0.3
            forecast = current_value
            for _ in range(forecast_periods):
                forecast = alpha * current_value + (1 - alpha) * forecast
            forecasted_value = forecast
            confidence = 0.6

        elif methodology == "linear":
            # Linear extrapolation
            if len(values) > 1:
                slope = values[-1] - values[-2]
                forecasted_value = current_value + (slope * forecast_periods)
            else:
                forecasted_value = current_value
            confidence = 0.65

        else:
            forecasted_value = current_value
            confidence = 0.5

        # Calculate confidence bounds (80% confidence interval)
        if len(values) > 2:
            stdev = statistics.stdev(values)
            margin = 1.28 * stdev  # 80% confidence
        else:
            margin = current_value * 0.1

        lower_bound = max(0, forecasted_value - margin)
        upper_bound = forecasted_value + margin

        forecast = ExecutionForecast(
            metric_name=metric_name,
            current_value=current_value,
            forecasted_value=forecasted_value,
            confidence=confidence,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            forecast_period=timedelta(days=forecast_periods),
            methodology=methodology,
        )

        self.forecasts[metric_name] = forecast
        logger.info(
            f"Forecast {metric_name}: {forecasted_value:.2f} "
            f"(±{margin:.2f}, confidence={confidence:.1%})"
        )

        return forecast

    def track_metric(self, metric_name: str, value: float) -> None:
        """Track a metric value over time.

        Args:
            metric_name: Name of metric
            value: Current value
        """
        if metric_name not in self.trends:
            self.trends[metric_name] = []

        self.trends[metric_name].append(value)
        logger.debug(f"Tracked {metric_name}: {value}")

    def generate_analytics_report(
        self,
        execution_id: str,
        period_start: datetime,
        period_end: datetime,
        executions: List[str],
        team_size: int = 1,
    ) -> AnalyticsReport:
        """Generate comprehensive analytics report.

        Args:
            execution_id: Report ID
            period_start: Period start
            period_end: Period end
            executions: List of execution IDs
            team_size: Team size

        Returns:
            AnalyticsReport with all metrics
        """
        # Calculate metrics
        total_cost = sum(
            self.cost_history.get(exec_id, ExecutionCost("", 0, 0, 0, 0, 0)).total_cost
            for exec_id in executions
        )
        avg_cost = total_cost / len(executions) if executions else 0.0

        # Get velocity
        velocity = self.calculate_team_velocity(period_start, period_end, executions, team_size)

        # Calculate trends
        trends = []
        for metric_name in self.trends.keys():
            trend = self.calculate_performance_trends(metric_name)
            if trend:
                trends.append(trend)

        # Generate forecasts
        forecasts = []
        for metric_name in self.trends.keys():
            forecast = self.forecast_metric(metric_name)
            if forecast:
                forecasts.append(forecast)

        # Generate recommendations
        recommendations = self._generate_recommendations(velocity, trends, forecasts)

        report = AnalyticsReport(
            execution_id=execution_id,
            period_start=period_start,
            period_end=period_end,
            total_executions=len(executions),
            total_cost=total_cost,
            average_cost_per_execution=avg_cost,
            team_velocity=velocity,
            performance_trends=trends,
            forecasts=forecasts,
            recommendations=recommendations,
        )

        logger.info(f"Generated analytics report {execution_id}")
        return report

    def _generate_recommendations(
        self,
        velocity: TeamVelocity,
        trends: List[PerformanceTrend],
        forecasts: List[ExecutionForecast],
    ) -> List[str]:
        """Generate recommendations based on analytics.

        Args:
            velocity: Team velocity metrics
            trends: Performance trends
            forecasts: Forecasted metrics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Velocity-based recommendations
        if velocity.efficiency < 0.8:
            recommendations.append(
                f"Team efficiency is {velocity.efficiency:.0%}. "
                f"Consider improving task estimation or reducing scope."
            )

        if velocity.productivity_index < 0.6:
            recommendations.append(
                "Productivity is below target. Review task allocation and dependencies."
            )

        # Trend-based recommendations
        for trend in trends:
            if trend.trend == "declining" and trend.trend_strength > 0.5:
                recommendations.append(
                    f"⚠️ {trend.metric_name} is declining ({trend.percentage_change:+.1f}%). "
                    f"Investigate root cause."
                )
            elif trend.trend == "improving" and trend.trend_strength > 0.5:
                recommendations.append(
                    f"✅ {trend.metric_name} is improving ({trend.percentage_change:+.1f}%). "
                    f"Continue current approach."
                )

        # Forecast-based recommendations
        for forecast in forecasts:
            if forecast.forecasted_value > forecast.current_value * 1.2:
                recommendations.append(
                    f"⚠️ {forecast.metric_name} is forecasted to increase {(forecast.forecasted_value - forecast.current_value):.1f}. "
                    f"Plan accordingly."
                )

        if not recommendations:
            recommendations.append("✅ All metrics are performing well. Continue current strategy.")

        return recommendations

    def get_cost_summary(self) -> Dict[str, float]:
        """Get cost summary statistics.

        Returns:
            Dictionary with cost metrics
        """
        if not self.cost_history:
            return {"total": 0.0, "average": 0.0, "min": 0.0, "max": 0.0}

        costs = [c.total_cost for c in self.cost_history.values()]
        return {
            "total": sum(costs),
            "average": statistics.mean(costs),
            "min": min(costs),
            "max": max(costs),
            "count": len(costs),
        }

    def reset(self) -> None:
        """Reset analytics for new analysis period."""
        self.execution_history.clear()
        self.cost_history.clear()
        self.velocity_history.clear()
        self.trends.clear()
        self.forecasts.clear()
        logger.info("Analytics reset")
