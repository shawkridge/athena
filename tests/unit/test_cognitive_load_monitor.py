"""Tests for CognitiveLoadMonitor component."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from athena.metacognition.load import CognitiveLoadMonitor
from athena.metacognition.models import SaturationLevel


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # Create cognitive load table
    cursor.execute(
        """
        CREATE TABLE metacognition_cognitive_load (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            metric_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active_memory_count INTEGER,
            max_capacity INTEGER,
            utilization_percent REAL,
            query_latency_ms REAL,
            saturation_level TEXT
        )
        """
    )

    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def monitor(db_path):
    """Create CognitiveLoadMonitor instance."""
    return CognitiveLoadMonitor(db_path, max_capacity=7)


class TestActiveMemoryTracking:
    """Test tracking active memory count."""

    def test_record_low_load(self, monitor, db_path):
        """Test recording low load conditions."""
        assert monitor.record_cognitive_load(
            project_id=1, active_memory_count=2, query_latency_ms=50.0
        )

        current = monitor.get_current_load(project_id=1)
        assert current is not None
        assert current["active_memory_count"] == 2
        assert current["query_latency_ms"] == 50.0

    def test_record_medium_load(self, monitor):
        """Test recording medium load conditions."""
        assert monitor.record_cognitive_load(
            project_id=1, active_memory_count=4, query_latency_ms=150.0
        )

        current = monitor.get_current_load(project_id=1)
        assert current["active_memory_count"] == 4

    def test_record_high_load(self, monitor):
        """Test recording high load conditions."""
        assert monitor.record_cognitive_load(
            project_id=1, active_memory_count=6, query_latency_ms=400.0
        )

        current = monitor.get_current_load(project_id=1)
        assert current["active_memory_count"] == 6


class TestCapacityUtilization:
    """Test capacity utilization calculation."""

    def test_calculate_utilization_empty(self, monitor):
        """Test utilization when memory is empty."""
        util = monitor.calculate_utilization(active_memory_count=0)
        assert util == 0.0

    def test_calculate_utilization_half_capacity(self, monitor):
        """Test utilization at half capacity (7/2 ≈ 3.5)."""
        util = monitor.calculate_utilization(active_memory_count=3)
        assert 40.0 <= util <= 50.0

    def test_calculate_utilization_full_capacity(self, monitor):
        """Test utilization at full capacity."""
        util = monitor.calculate_utilization(active_memory_count=7)
        assert util == 100.0

    def test_calculate_utilization_over_capacity(self, monitor):
        """Test utilization over capacity."""
        util = monitor.calculate_utilization(active_memory_count=10)
        assert util > 100.0


class TestQueryLatencyMonitoring:
    """Test query latency monitoring."""

    def test_low_latency(self, monitor):
        """Test with low latency."""
        monitor.record_cognitive_load(1, 2, 30.0)
        current = monitor.get_current_load(1)
        assert current["query_latency_ms"] == 30.0

    def test_high_latency(self, monitor):
        """Test with high latency."""
        monitor.record_cognitive_load(1, 6, 600.0)
        current = monitor.get_current_load(1)
        assert current["query_latency_ms"] == 600.0


class TestSaturationLevelDetection:
    """Test saturation level determination."""

    def test_saturation_low(self, monitor):
        """Test low saturation detection."""
        level = monitor.detect_saturation_level(
            utilization_percent=40.0, query_latency_ms=80.0
        )
        assert level == SaturationLevel.LOW

    def test_saturation_medium_by_utilization(self, monitor):
        """Test medium saturation by utilization."""
        level = monitor.detect_saturation_level(
            utilization_percent=60.0, query_latency_ms=50.0
        )
        assert level == SaturationLevel.MEDIUM

    def test_saturation_medium_by_latency(self, monitor):
        """Test medium saturation by latency."""
        level = monitor.detect_saturation_level(
            utilization_percent=40.0, query_latency_ms=200.0
        )
        assert level == SaturationLevel.MEDIUM

    def test_saturation_high(self, monitor):
        """Test high saturation detection."""
        level = monitor.detect_saturation_level(
            utilization_percent=80.0, query_latency_ms=350.0
        )
        assert level == SaturationLevel.HIGH

    def test_saturation_critical_by_utilization(self, monitor):
        """Test critical saturation by utilization."""
        level = monitor.detect_saturation_level(
            utilization_percent=95.0, query_latency_ms=200.0
        )
        assert level == SaturationLevel.CRITICAL

    def test_saturation_critical_by_latency(self, monitor):
        """Test critical saturation by latency."""
        level = monitor.detect_saturation_level(
            utilization_percent=50.0, query_latency_ms=600.0
        )
        assert level == SaturationLevel.CRITICAL


class TestCapacityPrediction:
    """Test saturation prediction."""

    def test_predict_saturation_no_data(self, monitor):
        """Test prediction with no data."""
        prediction = monitor.predict_saturation(project_id=999)

        assert prediction["will_saturate"] is False
        assert prediction["confidence"] == 0.0

    def test_predict_saturation_low_confidence(self, monitor):
        """Test prediction with single data point."""
        monitor.record_cognitive_load(1, 3, 100.0)
        prediction = monitor.predict_saturation(project_id=1)

        assert isinstance(prediction["will_saturate"], bool)
        assert prediction["confidence"] < 0.5

    def test_predict_saturation_with_increasing_load(self, monitor):
        """Test prediction detects increasing load."""
        # Simulate increasing load pattern
        for i in range(5):
            monitor.record_cognitive_load(1, 2 + i, 50.0 + (i * 50))

        prediction = monitor.predict_saturation(project_id=1, hours_ahead=1)

        assert isinstance(prediction["will_saturate"], bool)
        # With 5 data points, confidence should be 5/20 = 0.25
        assert prediction["confidence"] > 0.2


class TestOptimizationRecommendation:
    """Test optimization recommendations."""

    def test_recommend_low_load(self, monitor):
        """Test recommendations for low load."""
        monitor.record_cognitive_load(1, 2, 50.0)
        recommendations = monitor.recommend_optimization(project_id=1)

        # Should have few/no recommendations
        assert isinstance(recommendations, list)

    def test_recommend_high_load(self, monitor):
        """Test recommendations for high load."""
        monitor.record_cognitive_load(1, 6, 400.0)
        recommendations = monitor.recommend_optimization(project_id=1)

        # Should have recommendations
        assert len(recommendations) > 0
        actions = [r["action"] for r in recommendations]
        assert any("consolidation" in action.lower() for action in actions)

    def test_recommend_critical_load(self, monitor):
        """Test recommendations for critical load."""
        monitor.record_cognitive_load(1, 7, 600.0)
        recommendations = monitor.recommend_optimization(project_id=1)

        # Should have high-priority recommendations
        assert len(recommendations) > 0
        high_priority = [r for r in recommendations if r["priority"] == "high"]
        assert len(high_priority) > 0

    def test_recommendations_have_details(self, monitor):
        """Test recommendations include all required fields."""
        monitor.record_cognitive_load(1, 6, 500.0)
        recommendations = monitor.recommend_optimization(project_id=1)

        if recommendations:
            for rec in recommendations:
                assert "action" in rec
                assert "reason" in rec
                assert "priority" in rec
                assert "expected_improvement" in rec


class TestCognitiveLoadTrending:
    """Test load trending analysis."""

    def test_get_load_history_empty(self, monitor):
        """Test history with no data."""
        history = monitor.get_load_history(project_id=999)
        assert history == []

    def test_get_load_history_single_point(self, monitor):
        """Test history with single data point."""
        monitor.record_cognitive_load(1, 3, 100.0)
        history = monitor.get_load_history(project_id=1)

        assert len(history) == 1
        assert history[0]["active_memory_count"] == 3

    def test_get_load_history_multiple_points(self, monitor):
        """Test history with multiple data points."""
        for i in range(5):
            monitor.record_cognitive_load(1, 2 + i, 50.0 + (i * 50))

        history = monitor.get_load_history(project_id=1, hours=24)

        assert len(history) == 5
        # Verify ordering
        for i in range(len(history) - 1):
            assert (
                history[i]["timestamp"] <= history[i + 1]["timestamp"]
            )


class TestCognitiveLoadReport:
    """Test comprehensive load report generation."""

    def test_get_report_no_data(self, monitor):
        """Test report generation with no data."""
        report = monitor.get_cognitive_load_report(project_id=999)

        assert report["current_load"] is None
        assert report["saturation_risk"] == "UNKNOWN"

    def test_get_report_with_data(self, monitor):
        """Test report with actual data."""
        monitor.record_cognitive_load(1, 3, 100.0)
        report = monitor.get_cognitive_load_report(project_id=1)

        assert "current_load" in report
        assert "history" in report
        assert "trend" in report
        assert "prediction" in report
        assert "saturation_risk" in report
        assert "recommendations" in report
        assert "summary" in report

    def test_report_saturation_risk_levels(self, monitor):
        """Test report correctly identifies saturation risk levels."""
        # Low load
        monitor.record_cognitive_load(1, 2, 50.0)
        report_low = monitor.get_cognitive_load_report(project_id=1)
        assert report_low["saturation_risk"] == "LOW"

        # High load
        monitor.record_cognitive_load(2, 6, 400.0)
        report_high = monitor.get_cognitive_load_report(project_id=2)
        assert report_high["saturation_risk"] == "HIGH"

    def test_report_trend_analysis(self, monitor):
        """Test report includes trend analysis."""
        # Add multiple data points with varying load
        for i in range(3):
            monitor.record_cognitive_load(1, 2 + i, 50.0 + (i * 50))

        report = monitor.get_cognitive_load_report(project_id=1)

        assert "direction" in report["trend"]
        assert "avg_utilization" in report["trend"]
        assert report["trend"]["direction"] in [
            "increasing",
            "decreasing",
            "unknown",
        ]
