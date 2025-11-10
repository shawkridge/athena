"""Integration tests for Phase 7.5 Execution Analytics."""

import pytest
from datetime import datetime, timedelta

from athena.execution import (
    ExecutionMonitor,
    ExecutionLearner,
    ExecutionAnalytics,
    TaskOutcome,
)


@pytest.fixture
def analytics():
    """Create analytics engine for testing."""
    return ExecutionAnalytics()


@pytest.fixture
def sample_execution_records():
    """Create sample execution records."""
    monitor = ExecutionMonitor()
    monitor.initialize_plan(5, timedelta(hours=2))

    records = {}
    base_time = datetime.utcnow()

    for i in range(1, 6):
        task_id = f"task_{i}"
        planned_start = base_time + timedelta(minutes=(i-1)*20)
        monitor.record_task_start(
            task_id,
            planned_start,
            timedelta(minutes=20),
        )
        monitor.record_task_completion(
            task_id,
            TaskOutcome.SUCCESS,
            resources_used={"cpu": 2.0 + i*0.1, "memory": 4.0 + i*0.2},
        )
        records[task_id] = monitor.get_task_record(task_id)

    return records


class TestExecutionCostTracking:
    """Test suite for cost tracking."""

    def test_record_execution_metrics(self, analytics, sample_execution_records):
        """Test recording execution metrics."""
        analytics.record_execution_metrics(
            "exec_001",
            sample_execution_records,
            team_size=2,
        )

        assert "exec_001" in analytics.execution_history
        metrics = analytics.execution_history["exec_001"]
        assert metrics["task_count"] == 5
        assert metrics["team_size"] == 2

    def test_calculate_execution_cost(self, analytics, sample_execution_records):
        """Test cost calculation."""
        analytics.record_execution_metrics("exec_001", sample_execution_records)

        cost = analytics.calculate_execution_cost(
            "exec_001",
            labor_rate_per_hour=100.0,
            resource_cost_per_hour=50.0,
            team_size=2,
        )

        assert cost.execution_id == "exec_001"
        assert cost.labor_cost > 0
        assert cost.resource_cost > 0
        assert cost.overhead_cost > 0
        assert cost.total_cost > 0
        assert cost.cost_per_hour > 0

    def test_cost_breakdown(self, analytics, sample_execution_records):
        """Test cost breakdown components."""
        analytics.record_execution_metrics("exec_001", sample_execution_records, team_size=1)

        cost = analytics.calculate_execution_cost(
            "exec_001",
            labor_rate_per_hour=100.0,
            resource_cost_per_hour=50.0,
        )

        # Verify overhead is ~5% of subtotal
        subtotal = cost.labor_cost + cost.resource_cost
        expected_overhead = subtotal * 0.05
        assert abs(cost.overhead_cost - expected_overhead) < 1.0

    def test_cost_summary(self, analytics, sample_execution_records):
        """Test cost summary statistics."""
        for i in range(1, 4):
            analytics.record_execution_metrics(
                f"exec_{i:03d}",
                sample_execution_records,
            )
            analytics.calculate_execution_cost(f"exec_{i:03d}")

        summary = analytics.get_cost_summary()

        assert summary["count"] == 3
        assert summary["total"] > 0
        assert summary["average"] > 0
        assert summary["min"] > 0
        assert summary["max"] > 0
        assert summary["min"] <= summary["average"] <= summary["max"]


class TestTeamVelocity:
    """Test suite for team velocity metrics."""

    def test_calculate_team_velocity(self, analytics, sample_execution_records):
        """Test velocity calculation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)

        analytics.record_execution_metrics("exec_001", sample_execution_records, team_size=2)

        velocity = analytics.calculate_team_velocity(
            start_time,
            end_time,
            ["exec_001"],
            team_size=2,
        )

        assert velocity.tasks_completed == 5
        assert velocity.velocity > 0  # Tasks per hour
        assert 0.0 <= velocity.efficiency <= 1.0
        assert 0.0 <= velocity.productivity_index <= 1.0

    def test_velocity_efficiency(self, analytics, sample_execution_records):
        """Test efficiency calculation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)

        analytics.record_execution_metrics("exec_001", sample_execution_records)

        velocity = analytics.calculate_team_velocity(
            start_time,
            end_time,
            ["exec_001"],
            team_size=1,
            points_per_task=2.0,  # 2 story points per task
        )

        # All 5 tasks completed successfully
        # Estimated = 5 * 2 = 10
        # Actual = 5 * 2 = 10 (all successful)
        assert velocity.efficiency >= 0.9  # 90%+ efficiency

    def test_velocity_tracking(self, analytics, sample_execution_records):
        """Test velocity history tracking."""
        start_time = datetime.utcnow()

        for i in range(1, 4):
            analytics.record_execution_metrics(f"exec_{i:03d}", sample_execution_records)

        for i in range(1, 4):
            analytics.calculate_team_velocity(
                start_time + timedelta(hours=(i-1)*24),
                start_time + timedelta(hours=i*24),
                [f"exec_{i:03d}"],
            )

        assert len(analytics.velocity_history) == 3


class TestPerformanceTrending:
    """Test suite for performance trends."""

    def test_track_and_trend_metric(self, analytics):
        """Test metric tracking and trend calculation."""
        # Track metric values over time
        analytics.track_metric("task_duration", 60.0)
        analytics.track_metric("task_duration", 58.0)
        analytics.track_metric("task_duration", 55.0)
        analytics.track_metric("task_duration", 50.0)
        analytics.track_metric("task_duration", 48.0)

        trend = analytics.calculate_performance_trends("task_duration")

        assert trend is not None
        assert trend.metric_name == "task_duration"
        assert trend.current_value == 48.0
        assert trend.previous_value == 50.0
        assert trend.trend == "improving"  # Decreasing duration is improving

    def test_declining_trend(self, analytics):
        """Test detection of declining trend."""
        # Track increasing values (declining performance for error rate)
        analytics.track_metric("error_rate", 0.1)
        analytics.track_metric("error_rate", 0.12)
        analytics.track_metric("error_rate", 0.15)
        analytics.track_metric("error_rate", 0.18)
        analytics.track_metric("error_rate", 0.20)

        trend = analytics.calculate_performance_trends("error_rate")

        assert trend is not None
        # Values increasing = declining trend (worse performance)
        assert trend.trend == "declining"
        # Percentage change based on previous value (0.18 -> 0.20)
        assert trend.percentage_change > 0

    def test_stable_trend(self, analytics):
        """Test detection of stable trend."""
        # Track stable values
        analytics.track_metric("success_rate", 0.95)
        analytics.track_metric("success_rate", 0.95)
        analytics.track_metric("success_rate", 0.96)
        analytics.track_metric("success_rate", 0.95)
        analytics.track_metric("success_rate", 0.94)

        trend = analytics.calculate_performance_trends("success_rate")

        assert trend is not None
        assert trend.trend == "stable"
        assert abs(trend.percentage_change) < 10


class TestForecasting:
    """Test suite for forecasting."""

    def test_moving_average_forecast(self, analytics):
        """Test moving average forecasting."""
        # Track metric values
        values = [50.0, 52.0, 51.0, 53.0, 52.0, 54.0, 55.0]
        for v in values:
            analytics.track_metric("throughput", v)

        forecast = analytics.forecast_metric(
            "throughput",
            methodology="moving_average",
        )

        assert forecast is not None
        assert forecast.metric_name == "throughput"
        assert forecast.current_value == 55.0
        assert forecast.confidence > 0.6
        assert forecast.lower_bound <= forecast.forecasted_value <= forecast.upper_bound

    def test_exponential_forecast(self, analytics):
        """Test exponential smoothing forecast."""
        values = [10.0, 12.0, 15.0, 18.0, 20.0, 23.0]
        for v in values:
            analytics.track_metric("metric", v)

        forecast = analytics.forecast_metric(
            "metric",
            forecast_periods=3,
            methodology="exponential",
        )

        assert forecast is not None
        assert forecast.forecasted_value > 0
        assert forecast.confidence > 0.5

    def test_linear_forecast(self, analytics):
        """Test linear forecasting."""
        # Linear trend
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for v in values:
            analytics.track_metric("metric", v)

        forecast = analytics.forecast_metric(
            "metric",
            forecast_periods=2,
            methodology="linear",
        )

        assert forecast is not None
        # Should forecast upward continuation
        assert forecast.forecasted_value >= forecast.current_value


class TestAnalyticsReporting:
    """Test suite for analytics reporting."""

    def test_generate_analytics_report(self, analytics, sample_execution_records):
        """Test comprehensive analytics report generation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=3)

        # Record multiple executions
        for i in range(1, 4):
            analytics.record_execution_metrics(
                f"exec_{i:03d}",
                sample_execution_records,
                team_size=2,
            )
            analytics.calculate_execution_cost(f"exec_{i:03d}", team_size=2)

        # Track some metrics
        analytics.track_metric("velocity", 2.5)
        analytics.track_metric("velocity", 2.7)
        analytics.track_metric("velocity", 2.9)

        report = analytics.generate_analytics_report(
            "report_001",
            start_time,
            end_time,
            ["exec_001", "exec_002", "exec_003"],
            team_size=2,
        )

        assert report.execution_id == "report_001"
        assert report.total_executions == 3
        assert report.total_cost > 0
        assert report.average_cost_per_execution > 0
        assert report.team_velocity is not None
        assert isinstance(report.recommendations, list)

    def test_report_recommendations(self, analytics, sample_execution_records):
        """Test recommendation generation in report."""
        start_time = datetime.utcnow()

        # Record execution with low efficiency
        analytics.record_execution_metrics("exec_001", sample_execution_records)

        report = analytics.generate_analytics_report(
            "report_001",
            start_time,
            start_time + timedelta(hours=3),
            ["exec_001"],
        )

        # Should have at least some recommendations
        assert len(report.recommendations) > 0
        assert all(isinstance(rec, str) for rec in report.recommendations)


class TestAnalyticsIntegration:
    """Integration tests for analytics workflow."""

    def test_complete_analytics_workflow(self, sample_execution_records):
        """Test complete analytics workflow."""
        analytics = ExecutionAnalytics()
        monitor = ExecutionMonitor()

        # 1. Record multiple executions
        execution_ids = []
        for i in range(1, 4):
            exec_id = f"exec_{i:03d}"
            execution_ids.append(exec_id)

            analytics.record_execution_metrics(
                exec_id,
                sample_execution_records,
                team_size=2,
            )
            analytics.calculate_execution_cost(exec_id, team_size=2)

        # 2. Track performance metrics
        analytics.track_metric("success_rate", 0.95)
        analytics.track_metric("success_rate", 0.96)
        analytics.track_metric("success_rate", 0.95)

        analytics.track_metric("cost_per_task", 150.0)
        analytics.track_metric("cost_per_task", 145.0)
        analytics.track_metric("cost_per_task", 140.0)

        # 3. Generate report
        start_time = datetime.utcnow()
        report = analytics.generate_analytics_report(
            "report_001",
            start_time - timedelta(days=3),
            start_time,
            execution_ids,
            team_size=2,
        )

        # 4. Verify comprehensive reporting
        assert report.total_executions == 3
        assert report.total_cost > 0
        assert report.team_velocity.velocity > 0
        assert len(report.recommendations) > 0

        # 5. Verify trends calculated
        assert len(report.performance_trends) > 0

    def test_analytics_with_real_execution(self, analytics):
        """Test analytics with real execution monitoring."""
        monitor = ExecutionMonitor()
        learner = ExecutionLearner()

        # 1. Initialize and execute plan
        monitor.initialize_plan(3, timedelta(hours=1))

        for i in range(1, 4):
            task_id = f"task_{i}"
            monitor.record_task_start(
                task_id,
                datetime.utcnow(),
                timedelta(minutes=20),
            )
            monitor.record_task_completion(task_id, TaskOutcome.SUCCESS)

        # 2. Record analytics
        records = {r.task_id: r for r in monitor.get_all_task_records()}
        analytics.record_execution_metrics("exec_001", records)
        analytics.calculate_execution_cost("exec_001", team_size=1)

        # 3. Learn patterns
        patterns = learner.extract_execution_patterns(records)
        recommendations = learner.generate_recommendations(records)

        # 4. Generate analytics report
        report = analytics.generate_analytics_report(
            "report_001",
            datetime.utcnow() - timedelta(hours=2),
            datetime.utcnow(),
            ["exec_001"],
        )

        # Verify integration
        assert report.total_executions == 1
        assert len(report.recommendations) > 0
