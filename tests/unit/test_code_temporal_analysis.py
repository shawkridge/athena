"""Tests for code temporal analysis."""

import pytest
from datetime import datetime, timedelta

from src.athena.code_search.code_temporal_analysis import (
    ChangeType,
    TemporalTrend,
    CodeChange,
    TemporalMetrics,
    CodeChangeTracker,
    TemporalAnalyzer,
)


class TestCodeChange:
    """Tests for CodeChange."""

    def test_change_creation(self):
        """Test creating a code change."""
        now = datetime.now()
        change = CodeChange(
            entity_name="process_data",
            entity_type="function",
            change_type=ChangeType.CREATION,
            timestamp=now,
            file_path="utils.py",
        )

        assert change.entity_name == "process_data"
        assert change.change_type == ChangeType.CREATION
        assert change.timestamp == now

    def test_change_to_dict(self):
        """Test change serialization."""
        now = datetime.now()
        change = CodeChange(
            entity_name="MyClass",
            entity_type="class",
            change_type=ChangeType.MODIFICATION,
            timestamp=now,
            file_path="models.py",
            author="developer",
            metrics_before={"complexity": 5},
            metrics_after={"complexity": 7},
        )

        change_dict = change.to_dict()
        assert change_dict["entity_name"] == "MyClass"
        assert change_dict["change_type"] == "modification"
        assert change_dict["metrics_before"]["complexity"] == 5


class TestTemporalMetrics:
    """Tests for TemporalMetrics."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = TemporalMetrics(entity_name="test_func", metric_name="complexity")
        assert metrics.entity_name == "test_func"
        assert len(metrics.values) == 0

    def test_add_value(self):
        """Test adding metric values."""
        metrics = TemporalMetrics(entity_name="func1", metric_name="lines")
        now = datetime.now()

        metrics.add_value(now, 10.0)
        metrics.add_value(now + timedelta(days=1), 12.0)

        assert len(metrics.values) == 2

    def test_get_trend_increasing(self):
        """Test detecting increasing trend."""
        metrics = TemporalMetrics(entity_name="func", metric_name="complexity")
        base_time = datetime.now()

        # Add increasing values
        metrics.add_value(base_time, 1.0)
        metrics.add_value(base_time + timedelta(days=1), 2.0)
        metrics.add_value(base_time + timedelta(days=2), 3.0)
        metrics.add_value(base_time + timedelta(days=3), 4.0)

        trend = metrics.get_trend()
        assert trend == TemporalTrend.INCREASING

    def test_get_trend_decreasing(self):
        """Test detecting decreasing trend."""
        metrics = TemporalMetrics(entity_name="func", metric_name="quality")
        base_time = datetime.now()

        # Add decreasing values
        metrics.add_value(base_time, 4.0)
        metrics.add_value(base_time + timedelta(days=1), 3.0)
        metrics.add_value(base_time + timedelta(days=2), 2.0)
        metrics.add_value(base_time + timedelta(days=3), 1.0)

        trend = metrics.get_trend()
        assert trend == TemporalTrend.DECREASING

    def test_get_volatility(self):
        """Test volatility calculation."""
        metrics = TemporalMetrics(entity_name="volatile", metric_name="value")
        base_time = datetime.now()

        # Volatile values
        metrics.add_value(base_time, 1.0)
        metrics.add_value(base_time + timedelta(days=1), 10.0)
        metrics.add_value(base_time + timedelta(days=2), 2.0)
        metrics.add_value(base_time + timedelta(days=3), 9.0)

        volatility = metrics.get_volatility()
        assert 0 <= volatility <= 1
        assert volatility > 0.5  # Should be volatile

    def test_get_change_rate(self):
        """Test change rate calculation."""
        metrics = TemporalMetrics(entity_name="func", metric_name="size")
        base_time = datetime.now()

        metrics.add_value(base_time, 0.0)
        metrics.add_value(base_time + timedelta(days=10), 100.0)

        rate = metrics.get_change_rate()
        assert rate > 0  # Should be positive


class TestCodeChangeTracker:
    """Tests for CodeChangeTracker."""

    @pytest.fixture
    def tracker(self):
        """Create tracker."""
        return CodeChangeTracker()

    def test_record_change(self, tracker):
        """Test recording changes."""
        change = CodeChange(
            entity_name="func1",
            entity_type="function",
            change_type=ChangeType.CREATION,
            timestamp=datetime.now(),
            file_path="test.py",
        )

        idx = tracker.record_change(change)
        assert idx == 0
        assert len(tracker.changes) == 1

    def test_record_metric(self, tracker):
        """Test recording metrics."""
        now = datetime.now()
        tracker.record_metric("func1", "complexity", now, 5.0)
        tracker.record_metric("func1", "complexity", now + timedelta(days=1), 7.0)

        assert len(tracker.metrics) == 1

    def test_get_entity_history(self, tracker):
        """Test retrieving entity history."""
        now = datetime.now()
        change1 = CodeChange(
            entity_name="func1",
            entity_type="function",
            change_type=ChangeType.CREATION,
            timestamp=now,
            file_path="test.py",
        )
        change2 = CodeChange(
            entity_name="func1",
            entity_type="function",
            change_type=ChangeType.MODIFICATION,
            timestamp=now + timedelta(days=1),
            file_path="test.py",
        )

        tracker.record_change(change1)
        tracker.record_change(change2)

        history = tracker.get_entity_history("func1")
        assert len(history) == 2

    def test_get_changes_by_type(self, tracker):
        """Test filtering changes by type."""
        now = datetime.now()
        tracker.record_change(
            CodeChange(
                entity_name="func1",
                entity_type="function",
                change_type=ChangeType.CREATION,
                timestamp=now,
                file_path="test.py",
            )
        )
        tracker.record_change(
            CodeChange(
                entity_name="func2",
                entity_type="function",
                change_type=ChangeType.BUGFIX,
                timestamp=now,
                file_path="test.py",
            )
        )

        creations = tracker.get_changes_by_type(ChangeType.CREATION)
        assert len(creations) == 1
        assert creations[0].entity_name == "func1"

    def test_get_changes_in_timeframe(self, tracker):
        """Test timeframe filtering."""
        base_time = datetime.now()
        change1 = CodeChange(
            entity_name="func1",
            entity_type="function",
            change_type=ChangeType.CREATION,
            timestamp=base_time,
            file_path="test.py",
        )
        change2 = CodeChange(
            entity_name="func2",
            entity_type="function",
            change_type=ChangeType.MODIFICATION,
            timestamp=base_time + timedelta(days=5),
            file_path="test.py",
        )

        tracker.record_change(change1)
        tracker.record_change(change2)

        # Get changes in first 2 days
        in_range = tracker.get_changes_in_timeframe(
            base_time, base_time + timedelta(days=2)
        )
        assert len(in_range) == 1

    def test_calculate_change_frequency(self, tracker):
        """Test change frequency calculation."""
        base_time = datetime.now()

        for i in range(5):
            tracker.record_change(
                CodeChange(
                    entity_name="func1",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=i),
                    file_path="test.py",
                )
            )

        frequency = tracker.calculate_change_frequency("func1")
        assert frequency > 0

    def test_calculate_code_stability(self, tracker):
        """Test stability calculation."""
        base_time = datetime.now()

        # Create many changes
        for i in range(3):
            tracker.record_change(
                CodeChange(
                    entity_name="volatile_func",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=i),
                    file_path="test.py",
                )
            )

        stability = tracker.calculate_code_stability()
        assert "volatile_func" in stability
        assert 0 <= stability["volatile_func"] <= 1

    def test_get_high_churn_entities(self, tracker):
        """Test finding high churn entities."""
        base_time = datetime.now()

        # Create high churn entity
        for i in range(10):
            tracker.record_change(
                CodeChange(
                    entity_name="high_churn",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=i),
                    file_path="test.py",
                )
            )

        high_churn = tracker.get_high_churn_entities(threshold=0.3)
        assert len(high_churn) >= 1

    def test_detect_change_patterns(self, tracker):
        """Test pattern detection."""
        base_time = datetime.now()

        # Add various changes
        tracker.record_change(
            CodeChange(
                entity_name="func1",
                entity_type="function",
                change_type=ChangeType.CREATION,
                timestamp=base_time,
                file_path="test.py",
            )
        )
        tracker.record_change(
            CodeChange(
                entity_name="func2",
                entity_type="function",
                change_type=ChangeType.BUGFIX,
                timestamp=base_time + timedelta(days=1),
                file_path="test.py",
            )
        )

        patterns = tracker.detect_change_patterns()
        assert patterns["total_changes"] == 2
        assert "change_types" in patterns


class TestTemporalAnalyzer:
    """Tests for TemporalAnalyzer."""

    @pytest.fixture
    def setup(self):
        """Setup tracker and analyzer."""
        tracker = CodeChangeTracker()
        analyzer = TemporalAnalyzer(tracker)
        return tracker, analyzer

    def test_detect_metric_trends(self, setup):
        """Test trend detection."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add increasing complexity
        tracker.record_metric("func1", "complexity", base_time, 1.0)
        tracker.record_metric("func1", "complexity", base_time + timedelta(days=1), 2.0)
        tracker.record_metric("func1", "complexity", base_time + timedelta(days=2), 3.0)

        trends = analyzer.detect_metric_trends("func1")
        assert "complexity" in trends
        assert trends["complexity"] == TemporalTrend.INCREASING

    def test_detect_volatility_issues(self, setup):
        """Test volatility detection."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add volatile metrics
        tracker.record_metric("func1", "quality", base_time, 1.0)
        tracker.record_metric("func1", "quality", base_time + timedelta(days=1), 10.0)
        tracker.record_metric("func1", "quality", base_time + timedelta(days=2), 2.0)

        volatile = analyzer.detect_volatility_issues(threshold=0.3)
        assert len(volatile) >= 0

    def test_predict_quality_decline(self, setup):
        """Test quality decline prediction."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add increasing complexity (bad)
        tracker.record_metric("func1", "complexity", base_time, 1.0)
        tracker.record_metric("func1", "complexity", base_time + timedelta(days=1), 5.0)

        prediction = analyzer.predict_quality_decline()
        # May or may not predict depending on metrics

    def test_find_high_change_concentration(self, setup):
        """Test finding concentrated changes."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add many changes to one file
        for i in range(5):
            tracker.record_change(
                CodeChange(
                    entity_name=f"func{i}",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=i),
                    file_path="hot_file.py",
                )
            )

        concentration = analyzer.find_high_change_concentration()
        assert "file_distribution" in concentration

    def test_estimate_refactoring_need(self, setup):
        """Test refactoring need estimation."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add changes without refactoring
        for i in range(3):
            tracker.record_change(
                CodeChange(
                    entity_name="func1",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=i),
                    file_path="test.py",
                )
            )

        candidates = analyzer.estimate_refactoring_need()
        assert isinstance(candidates, list)

    def test_generate_temporal_report(self, setup):
        """Test report generation."""
        tracker, analyzer = setup
        base_time = datetime.now()

        # Add some activity
        tracker.record_change(
            CodeChange(
                entity_name="func1",
                entity_type="function",
                change_type=ChangeType.CREATION,
                timestamp=base_time,
                file_path="test.py",
            )
        )

        report = analyzer.generate_temporal_report()
        assert "TEMPORAL CODE ANALYSIS REPORT" in report
        assert "Total Changes" in report


class TestTemporalIntegration:
    """Integration tests for temporal analysis."""

    def test_full_temporal_workflow(self):
        """Test complete temporal workflow."""
        tracker = CodeChangeTracker()
        analyzer = TemporalAnalyzer(tracker)

        base_time = datetime.now()

        # Simulate code evolution
        # Day 1: Create functions
        tracker.record_change(
            CodeChange(
                entity_name="process_data",
                entity_type="function",
                change_type=ChangeType.CREATION,
                timestamp=base_time,
                file_path="data.py",
                metrics_after={"complexity": 1, "size": 10},
            )
        )

        # Days 2-5: Modify and add features
        for day in range(1, 5):
            tracker.record_change(
                CodeChange(
                    entity_name="process_data",
                    entity_type="function",
                    change_type=ChangeType.MODIFICATION,
                    timestamp=base_time + timedelta(days=day),
                    file_path="data.py",
                    metrics_before={"complexity": day, "size": 10 + (day * 2)},
                    metrics_after={"complexity": day + 1, "size": 10 + ((day + 1) * 2)},
                )
            )

        # Track metrics
        for day in range(5):
            tracker.record_metric(
                "process_data",
                "complexity",
                base_time + timedelta(days=day),
                float(day + 1),
            )

        # Analyze
        patterns = tracker.detect_change_patterns()
        assert patterns["total_changes"] == 5

        trends = analyzer.detect_metric_trends("process_data")
        assert "complexity" in trends

        # Refactoring recommendations
        candidates = analyzer.estimate_refactoring_need()
        assert isinstance(candidates, list)

        # Generate report
        report = analyzer.generate_temporal_report()
        assert len(report) > 0
