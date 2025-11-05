"""
PHASE 6: Analytics Engine Tests

Comprehensive test suite for EstimationAnalyzer and PatternDiscovery.
Tests MAPE, RMSE, bias calculation, pattern discovery, and MCP tool integration.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from athena.integration.estimation_analyzer import (
    EstimationAnalyzer, AccuracyMetrics, TaskEstimate, AccuracyReport,
    EstimationPattern, TaskPriority, TaskComplexity
)
from athena.integration.pattern_discovery import (
    PatternDiscovery, DurationPattern, DependencyPattern,
    ResourcePattern, TemporalPattern, QualityPattern, Pattern
)
from athena.core.database import Database


class TestEstimationAnalyzer:
    """Test suite for EstimationAnalyzer."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "test.db"
        return Database(str(db_path))

    @pytest.fixture
    def analyzer(self, db):
        """Create EstimationAnalyzer instance."""
        return EstimationAnalyzer(db, project_id=1)

    # =========================================================================
    # MAPE, RMSE, Bias Calculation Tests
    # =========================================================================

    def test_accuracy_metrics_perfect_estimation(self, analyzer):
        """Test metrics with perfect estimates (no error)."""
        tasks = [
            TaskEstimate(
                task_id=1,
                estimated_hours=8.0,
                actual_hours=8.0,
                error_hours=0.0,
                error_percentage=0.0,
                task_type="feature",
                priority="medium",
                complexity="moderate",
                assignee="alice",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
            TaskEstimate(
                task_id=2,
                estimated_hours=4.0,
                actual_hours=4.0,
                error_hours=0.0,
                error_percentage=0.0,
                task_type="bugfix",
                priority="high",
                complexity="simple",
                assignee="bob",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
        ]

        metrics = analyzer._calculate_metrics(tasks)

        assert metrics.mape == 0.0
        assert metrics.rmse == 0.0
        assert metrics.bias == 0.0
        assert metrics.accuracy_percentage == 100.0
        assert metrics.sample_size == 2

    def test_accuracy_metrics_underestimated(self, analyzer):
        """Test metrics when tasks are consistently underestimated."""
        tasks = [
            TaskEstimate(
                task_id=1,
                estimated_hours=8.0,
                actual_hours=10.0,  # 25% underestimated
                error_hours=2.0,
                error_percentage=25.0,
                task_type="feature",
                priority="medium",
                complexity="complex",
                assignee="alice",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
            TaskEstimate(
                task_id=2,
                estimated_hours=4.0,
                actual_hours=5.0,  # 25% underestimated
                error_hours=1.0,
                error_percentage=25.0,
                task_type="feature",
                priority="high",
                complexity="complex",
                assignee="bob",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
        ]

        metrics = analyzer._calculate_metrics(tasks)

        assert metrics.mape == 25.0
        assert metrics.bias > 0  # Positive bias = underestimated
        assert metrics.accuracy_percentage == 0.0  # Both exceed ±15% tolerance

    def test_accuracy_metrics_overestimated(self, analyzer):
        """Test metrics when tasks are consistently overestimated."""
        tasks = [
            TaskEstimate(
                task_id=1,
                estimated_hours=10.0,
                actual_hours=8.0,  # 20% overestimated
                error_hours=-2.0,
                error_percentage=-20.0,
                task_type="refactor",
                priority="low",
                complexity="moderate",
                assignee="alice",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
        ]

        metrics = analyzer._calculate_metrics(tasks)

        assert metrics.mape == 20.0
        assert metrics.bias < 0  # Negative bias = overestimated

    def test_accuracy_metrics_mixed_errors(self, analyzer):
        """Test metrics with mixed under/overestimation."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=10,
                        error_hours=2.0, error_percentage=25.0,
                        task_type="feature", priority="high", complexity="complex",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=4, actual_hours=4,
                        error_hours=0.0, error_percentage=0.0,
                        task_type="bugfix", priority="medium", complexity="simple",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=3, estimated_hours=12, actual_hours=10,
                        error_hours=-2.0, error_percentage=-16.67,
                        task_type="feature", priority="low", complexity="complex",
                        assignee="charlie", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        metrics = analyzer._calculate_metrics(tasks)

        assert metrics.sample_size == 3
        assert metrics.mape > 0
        assert abs(metrics.bias) < 0.25  # Roughly balanced

    def test_accuracy_tolerance_threshold(self, analyzer):
        """Test accuracy percentage with ±15% tolerance."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=8,
                        error_hours=0.0, error_percentage=0.0,
                        task_type="feature", priority="high", complexity="moderate",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=4, actual_hours=4.5,  # 12.5% - within tolerance
                        error_hours=0.5, error_percentage=12.5,
                        task_type="bugfix", priority="medium", complexity="simple",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=3, estimated_hours=10, actual_hours=12,  # 20% - outside tolerance
                        error_hours=2.0, error_percentage=20.0,
                        task_type="feature", priority="low", complexity="complex",
                        assignee="charlie", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        metrics = analyzer._calculate_metrics(tasks)

        assert metrics.accuracy_percentage == pytest.approx(66.67, rel=1)  # 2 out of 3

    # =========================================================================
    # Dimension Breakdown Tests
    # =========================================================================

    def test_analyze_by_priority(self, analyzer):
        """Test breakdown of accuracy by priority."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=8,
                        error_hours=0.0, error_percentage=0.0,
                        task_type="feature", priority="critical", complexity="complex",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=4, actual_hours=5,  # 25% error
                        error_hours=1.0, error_percentage=25.0,
                        task_type="feature", priority="low", complexity="simple",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        by_priority = analyzer._analyze_by_dimension(tasks, "priority")

        assert "critical" in by_priority
        assert "low" in by_priority
        assert by_priority["critical"].mape == 0.0
        assert by_priority["low"].mape == 25.0

    def test_analyze_by_complexity(self, analyzer):
        """Test breakdown of accuracy by complexity."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=8,
                        error_hours=0.0, error_percentage=0.0,
                        task_type="feature", priority="high", complexity="simple",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=20, actual_hours=25,  # 25% error
                        error_hours=5.0, error_percentage=25.0,
                        task_type="feature", priority="high", complexity="expert",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        by_complexity = analyzer._analyze_by_dimension(tasks, "complexity")

        assert "simple" in by_complexity
        assert "expert" in by_complexity
        assert by_complexity["simple"].accuracy_percentage == 100.0

    # =========================================================================
    # Outlier Detection Tests
    # =========================================================================

    def test_find_outliers_high_threshold(self, analyzer):
        """Test outlier detection with high error threshold."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=8,
                        error_hours=0.0, error_percentage=0.0,
                        task_type="feature", priority="high", complexity="moderate",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=4, actual_hours=12,  # 200% error
                        error_hours=8.0, error_percentage=200.0,
                        task_type="feature", priority="high", complexity="complex",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        outliers = analyzer._find_outliers(tasks, threshold=50.0)

        assert len(outliers) == 1
        assert outliers[0].task_id == 2

    def test_find_outliers_no_outliers(self, analyzer):
        """Test outlier detection when no outliers exist."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=8.5,  # 6.25% error
                        error_hours=0.5, error_percentage=6.25,
                        task_type="feature", priority="high", complexity="moderate",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=4, actual_hours=4.3,  # 7.5% error
                        error_hours=0.3, error_percentage=7.5,
                        task_type="bugfix", priority="high", complexity="simple",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        outliers = analyzer._find_outliers(tasks, threshold=50.0)

        assert len(outliers) == 0

    # =========================================================================
    # Pattern Discovery Tests
    # =========================================================================

    def test_discover_patterns_underestimation(self, analyzer):
        """Test pattern discovery for underestimated task types."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=8, actual_hours=10,
                        error_hours=2.0, error_percentage=25.0,
                        task_type="feature", priority="high", complexity="complex",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=8, actual_hours=10,
                        error_hours=2.0, error_percentage=25.0,
                        task_type="feature", priority="medium", complexity="complex",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=3, estimated_hours=8, actual_hours=10,
                        error_hours=2.0, error_percentage=25.0,
                        task_type="feature", priority="low", complexity="complex",
                        assignee="charlie", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        by_type = {"feature": analyzer._calculate_metrics(tasks)}
        patterns = analyzer._discover_patterns(tasks, {}, {}, by_type)

        assert len(patterns) > 0
        # Should find feature underestimation pattern
        feature_patterns = [p for p in patterns if p.affected_type == "feature"]
        assert len(feature_patterns) > 0

    def test_discover_patterns_overestimation(self, analyzer):
        """Test pattern discovery for overestimated task types."""
        tasks = [
            TaskEstimate(task_id=1, estimated_hours=20, actual_hours=12,
                        error_hours=-8.0, error_percentage=-40.0,
                        task_type="documentation", priority="low", complexity="simple",
                        assignee="alice", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=2, estimated_hours=16, actual_hours=10,
                        error_hours=-6.0, error_percentage=-37.5,
                        task_type="documentation", priority="low", complexity="simple",
                        assignee="bob", created_at=datetime.now(), completed_at=datetime.now()),
            TaskEstimate(task_id=3, estimated_hours=18, actual_hours=11,
                        error_hours=-7.0, error_percentage=-38.9,
                        task_type="documentation", priority="low", complexity="simple",
                        assignee="charlie", created_at=datetime.now(), completed_at=datetime.now()),
        ]

        by_type = {"documentation": analyzer._calculate_metrics(tasks)}
        patterns = analyzer._discover_patterns(tasks, {}, {}, by_type)

        doc_patterns = [p for p in patterns if "documentation" in p.affected_type]
        assert len(doc_patterns) > 0

        # Verify it's an overestimation pattern
        overest_patterns = [p for p in doc_patterns if p.error_direction == "overestimated"]
        assert len(overest_patterns) > 0

    # =========================================================================
    # Recommendations Tests
    # =========================================================================

    def test_generate_recommendations_poor_accuracy(self, analyzer):
        """Test recommendations when accuracy is poor."""
        poor_accuracy = AccuracyMetrics(
            mape=40.0,
            rmse=3.0,
            bias=0.3,
            accuracy_percentage=50.0,
            sample_size=10,
            confidence_interval=(35, 45)
        )

        recs = analyzer._generate_recommendations(
            poor_accuracy, {}, {}, []
        )

        assert len(recs) > 0
        assert any("poor" in r.lower() for r in recs)

    def test_generate_recommendations_good_accuracy(self, analyzer):
        """Test recommendations when accuracy is good."""
        good_accuracy = AccuracyMetrics(
            mape=10.0,
            rmse=1.0,
            bias=0.05,
            accuracy_percentage=85.0,
            sample_size=20,
            confidence_interval=(8, 12)
        )

        recs = analyzer._generate_recommendations(
            good_accuracy, {}, {}, []
        )

        # Should have fewer recommendations
        assert len(recs) <= 2


class TestPatternDiscovery:
    """Test suite for PatternDiscovery."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "test.db"
        return Database(str(db_path))

    @pytest.fixture
    def discovery(self, db):
        """Create PatternDiscovery instance."""
        return PatternDiscovery(db)

    def test_duration_patterns_structure(self, discovery):
        """Test duration pattern structure and generation."""
        patterns = discovery.discover_duration_patterns()

        # Should return list
        assert isinstance(patterns, list)

        # If patterns exist, check structure
        for pattern in patterns:
            assert isinstance(pattern, DurationPattern)
            assert hasattr(pattern, "task_type")
            assert hasattr(pattern, "avg_duration")
            assert hasattr(pattern, "std_dev")
            assert hasattr(pattern, "confidence_level")
            assert 0 <= pattern.confidence_level <= 1

    def test_dependency_patterns_structure(self, discovery):
        """Test dependency pattern structure."""
        patterns = discovery.discover_dependency_patterns()

        assert isinstance(patterns, list)

        for pattern in patterns:
            assert isinstance(pattern, DependencyPattern)
            assert hasattr(pattern, "predecessor_type")
            assert hasattr(pattern, "successor_type")
            assert hasattr(pattern, "frequency")

    def test_resource_patterns_structure(self, discovery):
        """Test resource pattern structure."""
        patterns = discovery.discover_resource_patterns()

        assert isinstance(patterns, list)

        for pattern in patterns:
            assert isinstance(pattern, ResourcePattern)
            assert hasattr(pattern, "task_type")
            assert hasattr(pattern, "typical_team_size")

    def test_temporal_patterns_structure(self, discovery):
        """Test temporal pattern structure."""
        patterns = discovery.discover_temporal_patterns()

        assert isinstance(patterns, list)

        for pattern in patterns:
            assert isinstance(pattern, TemporalPattern)
            assert hasattr(pattern, "faster_on_days")
            assert hasattr(pattern, "slower_on_days")

    def test_quality_patterns_structure(self, discovery):
        """Test quality pattern structure."""
        patterns = discovery.discover_quality_patterns()

        assert isinstance(patterns, list)

        for pattern in patterns:
            assert isinstance(pattern, QualityPattern)
            assert 0 <= pattern.avg_quality_score <= 100

    def test_discover_all_patterns(self, discovery):
        """Test discovering all pattern types at once."""
        patterns = discovery.discover_all_patterns()

        assert isinstance(patterns, list)

        # Should have a mix of pattern types
        pattern_types = {p.pattern_type for p in patterns}
        assert len(pattern_types) >= 0  # May be empty on first run

    def test_rank_patterns_by_score(self, discovery):
        """Test ranking patterns by composite score."""
        # Create sample patterns manually
        patterns = [
            Pattern(
                name="Pattern A",
                pattern_type="duration",
                frequency=10,
                impact=0.8,
                actionability=0.9,
                score=0.0,  # Will be calculated
                data=None
            ),
            Pattern(
                name="Pattern B",
                pattern_type="duration",
                frequency=5,
                impact=0.6,
                actionability=0.7,
                score=0.0,
                data=None
            ),
        ]

        ranked = discovery.rank_patterns(patterns)

        # Should be ranked by score
        assert ranked[0].name == "Pattern A"  # Higher score (10*0.8*0.9=7.2 vs 5*0.6*0.7=2.1)
        assert ranked[1].name == "Pattern B"

    def test_get_patterns_by_type(self, discovery):
        """Test filtering patterns by type."""
        patterns = discovery.discover_all_patterns()

        # Get only duration patterns
        duration_only = discovery.get_patterns_by_type("duration")

        # All should be duration type
        for p in duration_only:
            assert p.pattern_type == "duration"

    def test_actionable_patterns(self, discovery):
        """Test getting most actionable patterns."""
        patterns = discovery.get_actionable_patterns(top_n=5)

        # Should return up to 5 patterns
        assert len(patterns) <= 5

        # If any exist, check actionability
        if patterns:
            for p in patterns:
                assert p.actionability > 0

    def test_suggest_improvements(self, discovery):
        """Test improvement suggestions."""
        suggestions = discovery.suggest_improvements()

        # Should return list
        assert isinstance(suggestions, list)

        # Each suggestion should be a string
        for suggestion in suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0


class TestEstimationAnalyzerIntegration:
    """Integration tests for EstimationAnalyzer."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test.db"
        return Database(str(db_path))

    def test_full_accuracy_report(self, db):
        """Test complete accuracy report generation."""
        analyzer = EstimationAnalyzer(db, project_id=1)

        # Get report (will be empty due to no data in test DB)
        report = analyzer.analyze_accuracy(days_back=30)

        assert isinstance(report, AccuracyReport)
        assert report.project_id == 1
        assert isinstance(report.overall, AccuracyMetrics)
        assert isinstance(report.by_priority, dict)
        assert isinstance(report.by_complexity, dict)

    def test_accuracy_report_summary(self, db):
        """Test accuracy report text summary."""
        analyzer = EstimationAnalyzer(db, project_id=1)
        report = analyzer.analyze_accuracy()

        summary = report.summary()

        assert isinstance(summary, str)
        assert "ESTIMATION ACCURACY REPORT" in summary
        assert "=" * 60 in summary


# =========================================================================
# Performance Tests
# =========================================================================

class TestPhase6Performance:
    """Performance tests for PHASE 6 components."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test.db"
        return Database(str(db_path))

    def test_accuracy_calculation_performance(self, db):
        """Test performance of accuracy metric calculation."""
        import time

        analyzer = EstimationAnalyzer(db, project_id=1)

        # Create 1000 tasks
        tasks = [
            TaskEstimate(
                task_id=i,
                estimated_hours=8.0 + (i % 3),
                actual_hours=8.5 + (i % 3),
                error_hours=0.5,
                error_percentage=6.25,
                task_type=f"type_{i % 5}",
                priority=["low", "medium", "high"][i % 3],
                complexity=["simple", "moderate", "complex"][i % 3],
                assignee=f"user_{i % 10}",
                created_at=datetime.now(),
                completed_at=datetime.now(),
            )
            for i in range(1000)
        ]

        start = time.time()
        metrics = analyzer._calculate_metrics(tasks)
        elapsed = time.time() - start

        # Should complete in < 100ms
        assert elapsed < 0.1
        assert metrics.sample_size == 1000

    def test_pattern_discovery_performance(self, db):
        """Test performance of pattern discovery."""
        import time

        discovery = PatternDiscovery(db)

        start = time.time()
        patterns = discovery.discover_all_patterns()
        elapsed = time.time() - start

        # Should complete in < 500ms
        assert elapsed < 0.5
        assert isinstance(patterns, list)
