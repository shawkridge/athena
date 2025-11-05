"""Unit tests for Metrics Aggregator.

Tests metrics aggregation including:
- Project-wide metrics consolidation
- Trend tracking
- Statistical analysis
- Health score calculation
- Report generation
"""

import pytest
from athena.symbols.metrics_aggregator import MetricsAggregator, TrendDirection
from athena.symbols.code_quality_scorer import CodeQualityScore, QualityRating, ComponentScore, QualityMetric
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def aggregator():
    """Create a fresh aggregator instance."""
    return MetricsAggregator()


@pytest.fixture
def quality_scores():
    """Create sample quality scores."""
    scores = []

    # Excellent quality symbol
    symbol1 = Symbol(
        name="excellent_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="excellent_func",
        signature="def excellent_func():",
        code="",
        docstring="Good",
        metrics=SymbolMetrics(),
    )
    score1 = CodeQualityScore(
        symbol=symbol1,
        overall_score=92.0,
        overall_rating=QualityRating.EXCELLENT,
        component_scores=[
            ComponentScore(QualityMetric.SECURITY, 95.0, QualityRating.EXCELLENT, 0.25, 0, 0, "healthy"),
            ComponentScore(QualityMetric.PERFORMANCE, 90.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
            ComponentScore(QualityMetric.QUALITY, 90.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
            ComponentScore(QualityMetric.DOCUMENTATION, 90.0, QualityRating.EXCELLENT, 0.10, 0, 0, "healthy"),
            ComponentScore(QualityMetric.MAINTAINABILITY, 92.0, QualityRating.EXCELLENT, 0.20, 0, 0, "healthy"),
            ComponentScore(QualityMetric.TESTABILITY, 90.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
        ],
        total_issues=0,
        critical_issues=0,
        high_issues=0,
        medium_issues=0,
        low_issues=0,
        health_checks=[],
        improvements=[],
    )
    scores.append(score1)

    # Good quality symbol
    symbol2 = Symbol(
        name="good_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=20,
        line_end=40,
        namespace="",
        full_qualified_name="good_func",
        signature="def good_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score2 = CodeQualityScore(
        symbol=symbol2,
        overall_score=75.0,
        overall_rating=QualityRating.GOOD,
        component_scores=[
            ComponentScore(QualityMetric.SECURITY, 80.0, QualityRating.GOOD, 0.25, 1, 0, "healthy"),
            ComponentScore(QualityMetric.PERFORMANCE, 70.0, QualityRating.GOOD, 0.15, 1, 0, "warning"),
            ComponentScore(QualityMetric.QUALITY, 75.0, QualityRating.GOOD, 0.15, 1, 0, "healthy"),
            ComponentScore(QualityMetric.DOCUMENTATION, 50.0, QualityRating.POOR, 0.10, 1, 0, "warning"),
            ComponentScore(QualityMetric.MAINTAINABILITY, 78.0, QualityRating.GOOD, 0.20, 0, 0, "healthy"),
            ComponentScore(QualityMetric.TESTABILITY, 72.0, QualityRating.GOOD, 0.15, 0, 0, "healthy"),
        ],
        total_issues=4,
        critical_issues=0,
        high_issues=0,
        medium_issues=2,
        low_issues=2,
        health_checks=[],
        improvements=[],
    )
    scores.append(score2)

    # Poor quality symbol
    symbol3 = Symbol(
        name="poor_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=60,
        line_end=150,
        namespace="",
        full_qualified_name="poor_func",
        signature="def poor_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score3 = CodeQualityScore(
        symbol=symbol3,
        overall_score=35.0,
        overall_rating=QualityRating.CRITICAL,
        component_scores=[
            ComponentScore(QualityMetric.SECURITY, 50.0, QualityRating.FAIR, 0.25, 3, 2, "critical"),
            ComponentScore(QualityMetric.PERFORMANCE, 40.0, QualityRating.POOR, 0.15, 2, 1, "critical"),
            ComponentScore(QualityMetric.QUALITY, 30.0, QualityRating.POOR, 0.15, 5, 2, "critical"),
            ComponentScore(QualityMetric.DOCUMENTATION, 20.0, QualityRating.POOR, 0.10, 1, 0, "critical"),
            ComponentScore(QualityMetric.MAINTAINABILITY, 35.0, QualityRating.POOR, 0.20, 1, 1, "critical"),
            ComponentScore(QualityMetric.TESTABILITY, 30.0, QualityRating.POOR, 0.15, 2, 1, "critical"),
        ],
        total_issues=14,
        critical_issues=7,
        high_issues=4,
        medium_issues=2,
        low_issues=1,
        health_checks=[],
        improvements=[],
    )
    scores.append(score3)

    return scores


# ============================================================================
# Initialization Tests
# ============================================================================


def test_aggregator_initialization(aggregator):
    """Test aggregator initializes empty."""
    assert aggregator.scores == []
    assert aggregator.historical_metrics == []
    assert aggregator.current_metrics is None


# ============================================================================
# Score Addition Tests
# ============================================================================


def test_add_scores(aggregator, quality_scores):
    """Test adding scores to aggregator."""
    aggregator.add_scores(quality_scores)
    assert len(aggregator.scores) == 3
    assert aggregator.scores[0].overall_score == 92.0


# ============================================================================
# Aggregation Tests
# ============================================================================


def test_aggregate_empty(aggregator):
    """Test aggregation with no scores."""
    metrics = aggregator.aggregate()
    assert metrics.total_symbols == 0
    assert metrics.overall_quality_score == 0.0


def test_aggregate_scores(aggregator, quality_scores):
    """Test aggregation of scores."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert metrics.total_symbols == 3
    assert metrics.analyzed_symbols == 3
    assert 40 < metrics.overall_quality_score < 90  # Between poor and excellent


def test_aggregate_rating_distribution(aggregator, quality_scores):
    """Test rating distribution in aggregation."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert metrics.excellent_count == 1
    assert metrics.good_count == 1
    assert metrics.critical_count == 1
    assert metrics.excellent_count + metrics.good_count + metrics.critical_count == 3


def test_aggregate_issue_counting(aggregator, quality_scores):
    """Test issue counting in aggregation."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    # Scores have: 0 + 4 + 14 = 18 issues
    assert metrics.total_issues == 18
    assert metrics.critical_issues == 7


# ============================================================================
# Statistics Tests
# ============================================================================


def test_component_statistics(aggregator, quality_scores):
    """Test component statistics calculation."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    # Security stats should exist
    assert metrics.security_stats.count == 3
    assert metrics.security_stats.mean > 0
    assert metrics.security_stats.min_value <= metrics.security_stats.max_value


def test_component_stats_have_percentiles(aggregator, quality_scores):
    """Test component stats include percentile values."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    for stats in [metrics.security_stats, metrics.performance_stats, metrics.quality_stats]:
        assert stats.percentile_25 > 0
        assert stats.percentile_75 > 0


# ============================================================================
# Top/Worst Performers Tests
# ============================================================================


def test_top_performers(aggregator, quality_scores):
    """Test identification of top performers."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert len(metrics.top_performers) > 0
    assert metrics.top_performers[0][0] == "excellent_func"
    assert metrics.top_performers[0][1] == 92.0


def test_worst_performers(aggregator, quality_scores):
    """Test identification of worst performers."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert len(metrics.worst_performers) > 0
    assert metrics.worst_performers[0][0] == "poor_func"
    assert metrics.worst_performers[0][1] == 35.0


# ============================================================================
# Health Score Tests
# ============================================================================


def test_health_score_range(aggregator, quality_scores):
    """Test health score is between 0 and 1."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert 0.0 <= metrics.health_score <= 1.0


def test_excellent_health_score(aggregator):
    """Test health score for all excellent symbols."""
    # Create all excellent symbols
    scores = []
    for i in range(3):
        symbol = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i*10 + 1,
            line_end=i*10 + 10,
            namespace="",
            full_qualified_name=f"func{i}",
            signature="def func():",
            code="",
            docstring="Good",
            metrics=SymbolMetrics(),
        )
        score = CodeQualityScore(
            symbol=symbol,
            overall_score=95.0,
            overall_rating=QualityRating.EXCELLENT,
            component_scores=[
                ComponentScore(QualityMetric.SECURITY, 95.0, QualityRating.EXCELLENT, 0.25, 0, 0, "healthy"),
                ComponentScore(QualityMetric.PERFORMANCE, 95.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
                ComponentScore(QualityMetric.QUALITY, 95.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
                ComponentScore(QualityMetric.DOCUMENTATION, 95.0, QualityRating.EXCELLENT, 0.10, 0, 0, "healthy"),
                ComponentScore(QualityMetric.MAINTAINABILITY, 95.0, QualityRating.EXCELLENT, 0.20, 0, 0, "healthy"),
                ComponentScore(QualityMetric.TESTABILITY, 95.0, QualityRating.EXCELLENT, 0.15, 0, 0, "healthy"),
            ],
            total_issues=0,
            critical_issues=0,
            high_issues=0,
            medium_issues=0,
            low_issues=0,
            health_checks=[],
            improvements=[],
        )
        scores.append(score)

    aggregator.add_scores(scores)
    metrics = aggregator.aggregate()

    # All excellent should have good health
    assert metrics.health_score > 0.3


def test_poor_health_score(aggregator):
    """Test health score for all poor symbols."""
    # Create all critical symbols
    scores = []
    for i in range(3):
        symbol = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i*10 + 1,
            line_end=i*10 + 10,
            namespace="",
            full_qualified_name=f"func{i}",
            signature="def func():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        )
        score = CodeQualityScore(
            symbol=symbol,
            overall_score=25.0,
            overall_rating=QualityRating.CRITICAL,
            component_scores=[
                ComponentScore(QualityMetric.SECURITY, 25.0, QualityRating.CRITICAL, 0.25, 5, 3, "critical"),
                ComponentScore(QualityMetric.PERFORMANCE, 25.0, QualityRating.CRITICAL, 0.15, 3, 2, "critical"),
                ComponentScore(QualityMetric.QUALITY, 25.0, QualityRating.CRITICAL, 0.15, 5, 2, "critical"),
                ComponentScore(QualityMetric.DOCUMENTATION, 25.0, QualityRating.CRITICAL, 0.10, 1, 1, "critical"),
                ComponentScore(QualityMetric.MAINTAINABILITY, 25.0, QualityRating.CRITICAL, 0.20, 2, 1, "critical"),
                ComponentScore(QualityMetric.TESTABILITY, 25.0, QualityRating.CRITICAL, 0.15, 3, 2, "critical"),
            ],
            total_issues=20,
            critical_issues=11,
            high_issues=5,
            medium_issues=3,
            low_issues=1,
            health_checks=[],
            improvements=[],
        )
        scores.append(score)

    aggregator.add_scores(scores)
    metrics = aggregator.aggregate()

    # All critical should have poor health (clamped to 0.0 or lower)
    assert metrics.health_score <= 0.0


# ============================================================================
# Code Churn Risk Tests
# ============================================================================


def test_code_churn_risk_range(aggregator, quality_scores):
    """Test code churn risk is between 0 and 1."""
    aggregator.add_scores(quality_scores)
    metrics = aggregator.aggregate()

    assert 0.0 <= metrics.code_churn_risk <= 1.0


def test_high_critical_issues_increase_risk(aggregator):
    """Test that critical issues increase code churn risk."""
    # Create low-risk scores
    low_risk_scores = []
    for i in range(3):
        symbol = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i*10 + 1,
            line_end=i*10 + 10,
            namespace="",
            full_qualified_name=f"func{i}",
            signature="def func():",
            code="",
            docstring="Good",
            metrics=SymbolMetrics(),
        )
        score = CodeQualityScore(
            symbol=symbol,
            overall_score=85.0,
            overall_rating=QualityRating.GOOD,
            component_scores=[ComponentScore(QualityMetric.SECURITY, 85.0, QualityRating.GOOD, 1.0, 0, 0, "healthy")],
            total_issues=0,
            critical_issues=0,
            high_issues=0,
            medium_issues=0,
            low_issues=0,
            health_checks=[],
            improvements=[],
        )
        low_risk_scores.append(score)

    # Create high-risk scores
    high_risk_scores = []
    for i in range(3):
        symbol = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i*10 + 1,
            line_end=i*10 + 10,
            namespace="",
            full_qualified_name=f"func{i}",
            signature="def func():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        )
        score = CodeQualityScore(
            symbol=symbol,
            overall_score=25.0,
            overall_rating=QualityRating.CRITICAL,
            component_scores=[ComponentScore(QualityMetric.SECURITY, 25.0, QualityRating.CRITICAL, 1.0, 5, 3, "critical")],
            total_issues=15,
            critical_issues=9,
            high_issues=4,
            medium_issues=1,
            low_issues=1,
            health_checks=[],
            improvements=[],
        )
        high_risk_scores.append(score)

    aggregator.add_scores(low_risk_scores)
    low_metrics = aggregator.aggregate()

    aggregator.add_scores(high_risk_scores)
    high_metrics = aggregator.aggregate()

    assert high_metrics.code_churn_risk > low_metrics.code_churn_risk


# ============================================================================
# Trend Tracking Tests
# ============================================================================


def test_record_historical_metrics(aggregator, quality_scores):
    """Test recording historical metrics."""
    aggregator.add_scores(quality_scores)
    metrics1 = aggregator.aggregate()
    aggregator.record_metrics(metrics1)

    assert len(aggregator.historical_metrics) == 1


def test_calculate_trends(aggregator, quality_scores):
    """Test trend calculation."""
    # First aggregation
    aggregator.add_scores(quality_scores)
    metrics1 = aggregator.aggregate()
    aggregator.record_metrics(metrics1)

    # Create improved scores
    improved_scores = []
    for score in quality_scores:
        # Improve each score by 10 points
        improved_score = CodeQualityScore(
            symbol=score.symbol,
            overall_score=min(100.0, score.overall_score + 10),
            overall_rating=score.overall_rating,
            component_scores=score.component_scores,
            total_issues=max(0, score.total_issues - 2),
            critical_issues=max(0, score.critical_issues - 1),
            high_issues=max(0, score.high_issues - 1),
            medium_issues=score.medium_issues,
            low_issues=score.low_issues,
            health_checks=score.health_checks,
            improvements=score.improvements,
        )
        improved_scores.append(improved_score)

    # Second aggregation
    aggregator.add_scores(improved_scores)
    metrics2 = aggregator.aggregate()

    # Check trends
    assert len(metrics2.trends) > 0
    overall_trend = [t for t in metrics2.trends if t.metric_name == "overall_quality"][0]
    assert overall_trend.direction == TrendDirection.IMPROVING
    assert overall_trend.change > 0


def test_trend_detection_significant(aggregator, quality_scores):
    """Test significant trend detection."""
    aggregator.add_scores(quality_scores)
    metrics1 = aggregator.aggregate()
    aggregator.record_metrics(metrics1)

    # Create significantly improved scores
    improved_scores = []
    for score in quality_scores:
        improved_score = CodeQualityScore(
            symbol=score.symbol,
            overall_score=min(100.0, score.overall_score + 20),
            overall_rating=score.overall_rating,
            component_scores=score.component_scores,
            total_issues=max(0, score.total_issues - 5),
            critical_issues=max(0, score.critical_issues - 2),
            high_issues=max(0, score.high_issues - 2),
            medium_issues=score.medium_issues,
            low_issues=score.low_issues,
            health_checks=score.health_checks,
            improvements=score.improvements,
        )
        improved_scores.append(improved_score)

    aggregator.add_scores(improved_scores)
    metrics2 = aggregator.aggregate()

    overall_trend = [t for t in metrics2.trends if t.metric_name == "overall_quality"][0]
    assert overall_trend.is_significant == True


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_data(aggregator):
    """Test report with no data."""
    report = aggregator.get_aggregate_report()
    assert report["status"] == "no_data"


def test_report_with_data(aggregator, quality_scores):
    """Test report generation."""
    aggregator.add_scores(quality_scores)
    aggregator.aggregate()
    report = aggregator.get_aggregate_report()

    assert report["status"] == "complete"
    assert report["total_symbols"] == 3
    assert "overall_quality_score" in report
    assert "rating_distribution" in report
    assert "issues_summary" in report
    assert "component_averages" in report


def test_report_includes_ratings(aggregator, quality_scores):
    """Test report includes rating distribution."""
    aggregator.add_scores(quality_scores)
    aggregator.aggregate()
    report = aggregator.get_aggregate_report()

    assert report["rating_distribution"]["excellent"] == 1
    assert report["rating_distribution"]["good"] == 1
    assert report["rating_distribution"]["critical"] == 1


def test_report_includes_performers(aggregator, quality_scores):
    """Test report includes top/worst performers."""
    aggregator.add_scores(quality_scores)
    aggregator.aggregate()
    report = aggregator.get_aggregate_report()

    assert len(report["top_performers"]) > 0
    assert len(report["worst_performers"]) > 0
    assert report["top_performers"][0][0] == "excellent_func"
    assert report["worst_performers"][0][0] == "poor_func"
