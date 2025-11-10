"""Unit tests for FeedbackMetricsCollector."""

import pytest
import time
from datetime import datetime, timedelta

from athena.verification import FeedbackMetricsCollector


class TestMetricRecording:
    """Test metric recording."""

    def test_record_single_metric(self):
        """Test recording a single metric."""
        collector = FeedbackMetricsCollector()
        collector.record_metric("decision_accuracy", 0.92)

        assert "decision_accuracy" in collector.metrics
        assert len(collector.metrics["decision_accuracy"]) == 1
        assert collector.metrics["decision_accuracy"][0].value == 0.92

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("decision_accuracy", 0.92)
        collector.record_metric("gate_pass_rate", 0.78)
        collector.record_metric("remediation_effectiveness", 0.85)

        assert len(collector.metrics) == 3


class TestMetricTrending:
    """Test metric trend analysis."""

    def test_improving_trend(self):
        """Test detection of improving trend."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record improving values
        for i in range(10):
            collector.record_metric("decision_accuracy", 0.5 + (i * 0.05))
            time.sleep(0.01)

        trend = collector.get_metric_trend("decision_accuracy")
        assert trend.trend == "improving"

    def test_degrading_trend(self):
        """Test detection of degrading trend."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record degrading values
        for i in range(10):
            collector.record_metric("decision_accuracy", 0.95 - (i * 0.05))
            time.sleep(0.01)

        trend = collector.get_metric_trend("decision_accuracy")
        assert trend.trend == "degrading"

    def test_flat_trend(self):
        """Test detection of flat trend."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record flat values
        for i in range(10):
            collector.record_metric("decision_accuracy", 0.75)
            time.sleep(0.01)

        trend = collector.get_metric_trend("decision_accuracy")
        assert trend.trend == "flat"

    def test_trend_magnitude(self):
        """Test trend magnitude calculation."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record strong improving trend
        for i in range(10):
            collector.record_metric("decision_accuracy", 0.1 + (i * 0.1))
            time.sleep(0.01)

        trend = collector.get_metric_trend("decision_accuracy")
        assert trend.trend_magnitude > 0  # Improving


class TestAnomalyDetection:
    """Test anomaly detection."""

    def test_anomaly_detection(self):
        """Test detecting anomalies."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record normal values
        for i in range(5):
            collector.record_metric("gate_pass_rate", 0.75)
            time.sleep(0.01)

        # Record outlier
        collector.record_metric("gate_pass_rate", 0.05)

        anomalies = collector.get_anomalies(sigma_threshold=1.0)
        assert len(anomalies) > 0
        assert any(a["metric_name"] == "gate_pass_rate" for a in anomalies)

    def test_anomaly_threshold(self):
        """Test anomaly threshold parameter."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record values with variance
        for i in range(5):
            collector.record_metric("metric", 50 + i)
            time.sleep(0.01)

        # Strict threshold should find anomalies
        strict_anomalies = collector.get_anomalies(sigma_threshold=1.0)

        # Loose threshold should find fewer
        loose_anomalies = collector.get_anomalies(sigma_threshold=3.0)

        assert len(strict_anomalies) >= len(loose_anomalies)


class TestSystemHealthScore:
    """Test system health score."""

    def test_health_score_good(self):
        """Test health score with good metrics."""
        collector = FeedbackMetricsCollector()

        # Record good metrics
        for i in range(5):
            collector.record_metric("gate_pass_rate", 0.85)
            collector.record_metric("decision_accuracy", 0.90)
            collector.record_metric("remediation_effectiveness", 0.88)

        health = collector.calculate_system_health_score()
        assert health > 0.7  # Should be good

    def test_health_score_poor(self):
        """Test health score with poor metrics."""
        collector = FeedbackMetricsCollector()

        # Record poor metrics
        for i in range(5):
            collector.record_metric("gate_pass_rate", 0.3)
            collector.record_metric("decision_accuracy", 0.4)
            collector.record_metric("remediation_effectiveness", 0.35)

        health = collector.calculate_system_health_score()
        assert health < 0.6  # Should be poor

    def test_health_score_range(self):
        """Test health score is in valid range."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("gate_pass_rate", 0.5)
        collector.record_metric("decision_accuracy", 0.5)
        collector.record_metric("remediation_effectiveness", 0.5)

        health = collector.calculate_system_health_score()
        assert 0.0 <= health <= 1.0


class TestMetricAlerts:
    """Test metric alerts."""

    def test_regression_alert(self):
        """Test alert on metric degradation."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record degrading metric
        for i in range(10):
            collector.record_metric("decision_accuracy", 0.9 - (i * 0.05))
            time.sleep(0.01)

        alerts = collector.get_metric_alerts()
        assert any("degrading" in alert.lower() or "regression" in alert.lower() for alert in alerts)

    def test_anomaly_alert(self):
        """Test alert on anomaly."""
        collector = FeedbackMetricsCollector(window_hours=1)

        # Record values with anomaly
        for i in range(5):
            collector.record_metric("metric", 75)
            time.sleep(0.01)

        # Add anomaly
        collector.record_metric("metric", 5)

        alerts = collector.get_metric_alerts()
        assert any("anomaly" in alert.lower() for alert in alerts)


class TestRecommendations:
    """Test recommendations."""

    def test_low_accuracy_recommendation(self):
        """Test recommendation for low accuracy."""
        collector = FeedbackMetricsCollector()

        # Record low accuracy
        for i in range(5):
            collector.record_metric("decision_accuracy", 0.6)

        recs = collector.get_recommendations()
        assert any("accuracy" in rec.lower() for rec in recs)

    def test_latency_recommendation(self):
        """Test recommendation for high latency."""
        collector = FeedbackMetricsCollector()

        # Record high latency
        for i in range(5):
            collector.record_metric("operation_latency_ms", 2000)

        recs = collector.get_recommendations()
        assert any("latency" in rec.lower() or "operations per second" in rec.lower() or "performance" in rec.lower() or "caching" in rec.lower() for rec in recs)


class TestCompositeScore:
    """Test composite score calculation."""

    def test_composite_score_equal_weights(self):
        """Test composite score with equal weights."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("metric1", 0.8)
        collector.record_metric("metric2", 0.8)
        collector.record_metric("metric3", 0.8)

        score = collector.calculate_composite_score(
            ["metric1", "metric2", "metric3"]
        )
        assert 0.7 <= score <= 0.9  # Should be around 0.8

    def test_composite_score_custom_weights(self):
        """Test composite score with custom weights."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("metric1", 1.0)
        collector.record_metric("metric2", 0.0)

        score = collector.calculate_composite_score(
            ["metric1", "metric2"],
            weights={"metric1": 0.9, "metric2": 0.1}
        )
        assert score > 0.8  # metric1 has high weight


class TestQualityMetricsSummary:
    """Test quality metrics summary."""

    def test_summary_structure(self):
        """Test summary has expected structure."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("decision_accuracy", 0.85)
        collector.record_metric("gate_pass_rate", 0.78)
        collector.record_metric("remediation_effectiveness", 0.80)
        collector.record_metric("operation_latency_ms", 250)
        collector.record_metric("violation_count", 5)

        summary = collector.get_quality_metrics_summary()

        assert "decision_accuracy" in summary
        assert "gate_pass_rate" in summary
        assert "remediation_effectiveness" in summary
        assert "operational_efficiency" in summary
        assert "violation_reduction" in summary

    def test_summary_values(self):
        """Test summary contains metric values."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("decision_accuracy", 0.92)

        summary = collector.get_quality_metrics_summary()
        assert summary["decision_accuracy"]["current"] == pytest.approx(0.92)


class TestMetricContext:
    """Test metric recording with context."""

    def test_metric_with_context(self):
        """Test recording metric with context."""
        collector = FeedbackMetricsCollector()

        collector.record_metric(
            "decision_accuracy",
            0.92,
            context={"operation_type": "consolidate", "sample_size": 100}
        )

        snapshots = collector.metrics["decision_accuracy"]
        assert snapshots[0].context["operation_type"] == "consolidate"


class TestMetricsExport:
    """Test metrics export."""

    def test_export_format(self):
        """Test metrics export format."""
        collector = FeedbackMetricsCollector()

        collector.record_metric("decision_accuracy", 0.92)

        report = collector.export_metrics_report()

        assert "timestamp" in report
        assert "summary" in report
        assert "trends" in report
        assert "anomalies" in report
        assert "alerts" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
