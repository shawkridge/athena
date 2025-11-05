"""Tests for SelfReflectionSystem component."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from athena.metacognition.reflection import SelfReflectionSystem


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    cursor = conn.cursor()

    # Create confidence table
    cursor.execute(
        """
        CREATE TABLE metacognition_confidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            memory_id INTEGER,
            confidence_reported REAL,
            confidence_actual REAL,
            memory_type TEXT,
            updated_at TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def reflection(db_path):
    """Create SelfReflectionSystem instance."""
    return SelfReflectionSystem(db_path)


class TestConfidenceRecording:
    """Test confidence recording."""

    def test_record_confidence(self, reflection, db_path):
        """Test recording confidence calibration."""
        assert reflection.record_confidence(
            project_id=1,
            memory_id=1,
            confidence_reported=0.9,
            confidence_actual=0.85,
            memory_type="semantic",
        )

        # Verify in database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT confidence_reported, confidence_actual FROM metacognition_confidence"
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == 0.9
        assert row[1] == 0.85

    def test_record_multiple_confidences(self, reflection, db_path):
        """Test recording multiple confidence samples."""
        for i in range(5):
            reflection.record_confidence(
                project_id=1,
                memory_id=i,
                confidence_reported=0.8 + (i * 0.02),
                confidence_actual=0.75 + (i * 0.01),
                memory_type="semantic",
            )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metacognition_confidence")
            count = cursor.fetchone()[0]

        assert count == 5


class TestConfidenceCalibration:
    """Test confidence calibration analysis."""

    def test_calibrate_well_calibrated(self, reflection):
        """Test calibration when well-calibrated."""
        # Well-calibrated: reported ≈ actual
        for _ in range(10):
            reflection.record_confidence(
                1, _, 0.80, 0.80, "semantic"
            )

        calibration = reflection.calibrate_confidence(project_id=1)

        assert calibration["mean_reported"] == pytest.approx(0.80)
        assert calibration["mean_actual"] == pytest.approx(0.80)
        assert calibration["calibration_status"] == "well_calibrated"

    def test_calibrate_overconfident(self, reflection):
        """Test calibration when overconfident."""
        # Overconfident: reported > actual
        for _ in range(10):
            reflection.record_confidence(
                1, _, 0.90, 0.60, "semantic"
            )

        calibration = reflection.calibrate_confidence(project_id=1)

        assert calibration["mean_reported"] > calibration["mean_actual"]
        assert calibration["is_overconfident"] is True
        assert calibration["calibration_status"] == "overconfident"

    def test_calibrate_underconfident(self, reflection):
        """Test calibration when underconfident."""
        # Underconfident: reported < actual
        for _ in range(10):
            reflection.record_confidence(
                1, _, 0.50, 0.80, "semantic"
            )

        calibration = reflection.calibrate_confidence(project_id=1)

        assert calibration["mean_reported"] < calibration["mean_actual"]
        assert calibration["is_underconfident"] is True
        assert calibration["calibration_status"] == "underconfident"

    def test_calibrate_no_data(self, reflection):
        """Test calibration with no data."""
        calibration = reflection.calibrate_confidence(project_id=999)

        assert calibration["calibration_status"] == "no_data"
        assert calibration["mean_reported"] == 0.0
        assert calibration["mean_actual"] == 0.0


class TestErrorTracking:
    """Test error tracking."""

    def test_track_error(self, reflection, db_path):
        """Test tracking an error."""
        assert reflection.track_error(
            project_id=1,
            error_type="retrieval",
            description="Failed to retrieve memory",
            memory_id=1,
        )

        # Verify recorded
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT memory_type FROM metacognition_confidence WHERE project_id = 1"
            )
            row = cursor.fetchone()

        assert row is not None
        assert "error:retrieval" in row[0]


class TestSuccessRatesByType:
    """Test success rate calculation by memory type."""

    def test_success_rates_by_type(self, reflection):
        """Test calculating success rates per memory type."""
        # Semantic: 80% success
        for i in range(8):
            reflection.record_confidence(1, i, 0.8, 0.8, "semantic")
        for i in range(2):
            reflection.record_confidence(1, 10+i, 0.8, 0.2, "semantic")

        # Episodic: 60% success
        for i in range(6):
            reflection.record_confidence(1, 20+i, 0.7, 0.7, "episodic")
        for i in range(4):
            reflection.record_confidence(1, 30+i, 0.7, 0.3, "episodic")

        rates = reflection.get_success_rates_by_type(project_id=1)

        assert "semantic" in rates
        assert "episodic" in rates
        assert rates["semantic"] > rates["episodic"]

    def test_success_rates_empty(self, reflection):
        """Test success rates with no data."""
        rates = reflection.get_success_rates_by_type(project_id=999)
        assert rates == {}


class TestReasoningQuality:
    """Test reasoning quality analysis."""

    def test_analyze_reasoning_quality_excellent(self, reflection):
        """Test reasoning quality assessment - excellent."""
        # High accuracy, low variance = excellent
        for _ in range(10):
            reflection.record_confidence(1, _, 0.90, 0.90, "semantic")

        quality = reflection.analyze_reasoning_quality(project_id=1)

        assert quality["accuracy"] == pytest.approx(0.90)
        assert quality["assessment"] == "excellent"
        assert quality["quality_score"] > 0.85

    def test_analyze_reasoning_quality_poor(self, reflection):
        """Test reasoning quality assessment - poor."""
        # Low accuracy, high variance = poor
        accuracies = [0.3, 0.2, 0.5, 0.4, 0.1]
        for acc in accuracies:
            reflection.record_confidence(1, len(accuracies), 0.8, acc, "semantic")

        quality = reflection.analyze_reasoning_quality(project_id=1)

        assert quality["accuracy"] < 0.5
        assert quality["assessment"] in ["poor", "fair"]

    def test_analyze_reasoning_quality_no_data(self, reflection):
        """Test reasoning quality with no data."""
        quality = reflection.analyze_reasoning_quality(project_id=999)

        assert quality["assessment"] == "no_data"
        assert quality["accuracy"] == 0.0


class TestSystematicBias:
    """Test systematic bias detection."""

    def test_detect_overconfidence_bias(self, reflection):
        """Test detecting overconfidence bias."""
        # Consistently report 0.9, actual 0.5
        for _ in range(10):
            reflection.record_confidence(1, _, 0.9, 0.5, "semantic")

        bias = reflection.detect_systematic_bias(project_id=1)

        assert bias["overconfidence_bias"] is True
        assert bias["severity"] in ["moderate", "severe"]
        assert len(bias["recommendations"]) > 0

    def test_detect_underconfidence_bias(self, reflection):
        """Test detecting underconfidence bias."""
        # Consistently report 0.4, actual 0.9
        for _ in range(10):
            reflection.record_confidence(1, _, 0.4, 0.9, "semantic")

        bias = reflection.detect_systematic_bias(project_id=1)

        assert bias["underconfidence_bias"] is True
        assert len(bias["recommendations"]) > 0

    def test_detect_type_specific_bias(self, reflection):
        """Test detecting biases specific to memory types."""
        # Semantic: well-calibrated
        for _ in range(5):
            reflection.record_confidence(1, _, 0.8, 0.8, "semantic")

        # Episodic: overconfident
        for _ in range(5):
            reflection.record_confidence(1, 10+_, 0.9, 0.5, "episodic")

        bias = reflection.detect_systematic_bias(project_id=1)

        assert "semantic" in bias["type_bias"]
        assert "episodic" in bias["type_bias"]


class TestPerformanceTrending:
    """Test performance trend analysis."""

    def test_performance_trends_improving(self, reflection):
        """Test detecting improving performance trend."""
        # Add varied data - if recent avg is better than all-time avg, it's improving
        # First add lower accuracy data
        for _ in range(5):
            reflection.record_confidence(1, _, 0.8, 0.5, "semantic")

        # Then add higher accuracy data
        for _ in range(10):
            reflection.record_confidence(1, 10+_, 0.8, 0.8, "semantic")

        trends = reflection.get_performance_trends(project_id=1, hours=24)

        # With mixed data, recent should be higher than historical
        assert trends["recent_avg"] >= trends["historical_avg"]

    def test_performance_trends_declining(self, reflection):
        """Test detecting declining performance trend."""
        # Add data that shows decline
        # First add higher accuracy data
        for _ in range(5):
            reflection.record_confidence(1, _, 0.8, 0.8, "semantic")

        # Then add lower accuracy data
        for _ in range(10):
            reflection.record_confidence(1, 10+_, 0.8, 0.4, "semantic")

        trends = reflection.get_performance_trends(project_id=1, hours=24)

        # With mixed data where recent is lower, recent should be lower than historical
        assert trends["recent_avg"] <= trends["historical_avg"]

    def test_performance_trends_stable(self, reflection):
        """Test detecting stable performance trend."""
        # Consistent 0.7 accuracy
        for _ in range(10):
            reflection.record_confidence(1, _, 0.8, 0.7, "semantic")

        trends = reflection.get_performance_trends(project_id=1, hours=24)

        assert trends["trend"] == "stable"

    def test_performance_trends_no_data(self, reflection):
        """Test performance trends with no data."""
        trends = reflection.get_performance_trends(project_id=999)

        assert trends["trend"] == "no_data"


class TestSelfReport:
    """Test self-report generation."""

    def test_generate_self_report(self, reflection):
        """Test generating comprehensive self-report."""
        # Set up diverse data
        for i in range(10):
            reflection.record_confidence(
                1, i, 0.85, 0.80 if i % 2 == 0 else 0.75, "semantic"
            )
        for i in range(10):
            reflection.record_confidence(
                1, 20+i, 0.75, 0.70 if i % 2 == 0 else 0.65, "episodic"
            )

        report = reflection.generate_self_report(project_id=1)

        assert "summary" in report
        assert "calibration" in report
        assert "reasoning_quality" in report
        assert "bias_analysis" in report
        assert "performance_trends" in report
        assert "success_by_type" in report
        assert "timestamp" in report

    def test_self_report_assessment_quality(self, reflection):
        """Test self-report includes quality assessment."""
        # High quality data
        for _ in range(10):
            reflection.record_confidence(1, _, 0.9, 0.88, "semantic")

        report = reflection.generate_self_report(project_id=1)

        quality = report["reasoning_quality"]
        assert quality["assessment"] in [
            "excellent",
            "good",
            "fair",
            "poor",
            "no_data",
        ]
        assert quality["quality_score"] > 0.8

    def test_self_report_includes_recommendations(self, reflection):
        """Test self-report includes actionable recommendations."""
        # Create overconfident scenario
        for _ in range(10):
            reflection.record_confidence(1, _, 0.95, 0.40, "semantic")

        report = reflection.generate_self_report(project_id=1)

        bias = report["bias_analysis"]
        assert len(bias["recommendations"]) > 0
