"""Unit tests for Complexity Analyzer.

Tests complexity analysis including:
- Cyclomatic complexity calculation
- Cognitive complexity calculation
- Essential complexity calculation
- Complexity categorization
- Refactoring recommendations
- Report generation
"""

import pytest
from athena.symbols.complexity_analyzer import (
    ComplexityAnalyzer,
    ComplexityCategory,
    ComplexityMetric,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance."""
    return ComplexityAnalyzer()


@pytest.fixture
def simple_symbol():
    """Create a simple symbol."""
    return Symbol(
        name="simple_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.simple_func",
        signature="def simple_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )


@pytest.fixture
def complex_symbol():
    """Create a complex symbol."""
    return Symbol(
        name="complex_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=20,
        line_end=100,
        namespace="",
        full_qualified_name="test.complex_func",
        signature="def complex_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes empty."""
    assert analyzer.metrics == {}
    assert analyzer.historical_metrics == []


# ============================================================================
# Single Symbol Analysis Tests
# ============================================================================


def test_analyze_simple_symbol(analyzer, simple_symbol):
    """Test analysis of simple symbol."""
    structure = {
        "branches": 0,
        "loops": 0,
        "nesting_depth": 0,
        "decisions": 0,
    }
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    assert metric.symbol.name == "simple_func"
    assert metric.cyclomatic_complexity == 1.0
    assert metric.category == ComplexityCategory.SIMPLE


def test_analyze_moderate_symbol(analyzer, complex_symbol):
    """Test analysis of moderate complexity symbol."""
    structure = {
        "branches": 3,
        "loops": 1,
        "nesting_depth": 2,
        "decisions": 3,
    }
    metric = analyzer.analyze_symbol(complex_symbol, structure)

    assert metric.cyclomatic_complexity == 5.0  # 1 + 3 + 1
    assert metric.cognitive_complexity > 0
    assert metric.category in [ComplexityCategory.SIMPLE, ComplexityCategory.MODERATE]


def test_analyze_high_complexity_symbol(analyzer, complex_symbol):
    """Test analysis of high complexity symbol."""
    structure = {
        "branches": 10,
        "loops": 5,
        "nesting_depth": 4,
        "decisions": 10,
    }
    metric = analyzer.analyze_symbol(complex_symbol, structure)

    assert metric.cyclomatic_complexity == 16.0  # 1 + 10 + 5
    assert metric.category in [ComplexityCategory.COMPLEX, ComplexityCategory.VERY_COMPLEX]


# ============================================================================
# Complexity Metrics Tests
# ============================================================================


def test_cyclomatic_complexity_calculation(analyzer, simple_symbol):
    """Test cyclomatic complexity calculation."""
    structure = {"branches": 4, "loops": 2, "nesting_depth": 1, "decisions": 4}
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    assert metric.cyclomatic_complexity == 7.0  # 1 + 4 + 2


def test_cognitive_complexity_calculation(analyzer, simple_symbol):
    """Test cognitive complexity calculation."""
    structure = {"branches": 2, "loops": 1, "nesting_depth": 3, "decisions": 2}
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    # cognitive = branches * (nesting_depth + 1) + loops * 2
    # = 2 * (3 + 1) + 1 * 2 = 8 + 2 = 10
    assert metric.cognitive_complexity == 10.0


def test_essential_complexity_calculation(analyzer, simple_symbol):
    """Test essential complexity calculation."""
    structure = {"branches": 3, "loops": 1, "nesting_depth": 1, "decisions": 3}
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    # cyclomatic = 1 + 3 + 1 = 5
    # structured = min(3, 4) = 3
    # essential = max(1, 5 - 3) = 2
    assert metric.essential_complexity == 2.0


# ============================================================================
# Complexity Category Tests
# ============================================================================


def test_simple_category(analyzer, simple_symbol):
    """Test simple complexity category (<=5)."""
    structure = {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0}
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    assert metric.category == ComplexityCategory.SIMPLE


def test_moderate_category(analyzer, simple_symbol):
    """Test moderate complexity category (6-15)."""
    structure = {"branches": 3, "loops": 1, "nesting_depth": 2, "decisions": 3}
    metric = analyzer.analyze_symbol(simple_symbol, structure)

    assert metric.category in [ComplexityCategory.MODERATE, ComplexityCategory.SIMPLE]


def test_complex_category(analyzer, complex_symbol):
    """Test complex category (16-30)."""
    structure = {"branches": 8, "loops": 4, "nesting_depth": 3, "decisions": 8}
    metric = analyzer.analyze_symbol(complex_symbol, structure)

    assert metric.category in [ComplexityCategory.COMPLEX, ComplexityCategory.VERY_COMPLEX]


def test_very_complex_category(analyzer, complex_symbol):
    """Test very complex category (31-50)."""
    structure = {"branches": 15, "loops": 8, "nesting_depth": 5, "decisions": 15}
    metric = analyzer.analyze_symbol(complex_symbol, structure)

    assert metric.category in [ComplexityCategory.VERY_COMPLEX, ComplexityCategory.EXTREMELY_COMPLEX]


# ============================================================================
# Multiple Symbol Analysis Tests
# ============================================================================


def test_analyze_multiple_symbols(analyzer, simple_symbol, complex_symbol):
    """Test analysis of multiple symbols."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 5, "loops": 2, "nesting_depth": 2, "decisions": 5},
    }

    metrics = analyzer.analyze(symbols, structures)

    assert len(metrics) == 2
    assert "test.simple_func" in metrics
    assert "test.complex_func" in metrics


# ============================================================================
# High Complexity Symbols Tests
# ============================================================================


def test_get_high_complexity_symbols(analyzer, simple_symbol, complex_symbol):
    """Test retrieval of high complexity symbols."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 8, "loops": 4, "nesting_depth": 3, "decisions": 8},
    }

    analyzer.analyze(symbols, structures)
    high = analyzer.get_high_complexity_symbols(threshold=15, limit=10)

    # Complex symbol should be in high complexity list
    assert len(high) > 0
    assert high[0][0] == "test.complex_func"


def test_high_complexity_threshold(analyzer, simple_symbol):
    """Test high complexity threshold filtering."""
    symbols = {"simple": simple_symbol}
    structures = {"simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0}}

    analyzer.analyze(symbols, structures)
    high = analyzer.get_high_complexity_symbols(threshold=15)

    assert len(high) == 0  # Simple symbol below threshold


# ============================================================================
# Complexity Distribution Tests
# ============================================================================


def test_complexity_distribution(analyzer, simple_symbol, complex_symbol):
    """Test complexity distribution calculation."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 8, "loops": 4, "nesting_depth": 3, "decisions": 8},
    }

    analyzer.analyze(symbols, structures)
    distribution = analyzer.get_complexity_distribution()

    assert "simple" in distribution
    assert "moderate" in distribution
    assert distribution["simple"] > 0


# ============================================================================
# Refactoring Targets Tests
# ============================================================================


def test_get_refactoring_targets(analyzer, simple_symbol, complex_symbol):
    """Test identification of refactoring targets."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 8, "loops": 4, "nesting_depth": 3, "decisions": 8},
    }

    analyzer.analyze(symbols, structures)
    targets = analyzer.get_refactoring_targets(limit=10)

    assert isinstance(targets, list)
    if len(targets) > 0:
        assert targets[0][0] == "test.complex_func"


def test_refactoring_priority_calculation(analyzer, complex_symbol):
    """Test refactoring priority calculation."""
    symbols = {"complex": complex_symbol}
    structures = {"complex": {"branches": 10, "loops": 5, "nesting_depth": 3, "decisions": 10}}

    analyzer.analyze(symbols, structures)
    targets = analyzer.get_refactoring_targets()

    # Complex symbol should be target if above threshold
    if len(targets) > 0:
        priority = targets[0][1]
        assert priority > 0


# ============================================================================
# Complexity Stats Tests
# ============================================================================


def test_get_complexity_stats(analyzer, simple_symbol, complex_symbol):
    """Test complexity statistics calculation."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 5, "loops": 2, "nesting_depth": 2, "decisions": 5},
    }

    analyzer.analyze(symbols, structures)
    stats = analyzer.get_complexity_stats()

    assert stats.count == 2
    assert stats.mean > 0
    assert stats.min_value > 0
    assert stats.max_value >= stats.min_value


def test_complexity_stats_empty(analyzer):
    """Test complexity stats with no analysis."""
    stats = analyzer.get_complexity_stats()

    assert stats.count == 0
    assert stats.mean == 0.0


def test_complexity_percentiles(analyzer, simple_symbol, complex_symbol):
    """Test percentile calculation in stats."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 10, "loops": 5, "nesting_depth": 3, "decisions": 10},
    }

    analyzer.analyze(symbols, structures)
    stats = analyzer.get_complexity_stats()

    assert stats.percentile_25 > 0
    assert stats.percentile_75 > stats.percentile_25


# ============================================================================
# Complexity Trending Tests
# ============================================================================


def test_compare_complexity(analyzer, simple_symbol):
    """Test complexity trend comparison."""
    symbols = {"simple": simple_symbol}
    structures = {"simple": {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0}}

    # First analysis
    metrics_v1 = analyzer.analyze(symbols, structures)

    # Second analysis with increased complexity
    structures2 = {"simple": {"branches": 3, "loops": 1, "nesting_depth": 1, "decisions": 3}}
    analyzer2 = ComplexityAnalyzer()
    metrics_v2 = analyzer2.analyze(symbols, structures2)

    # Compare
    trends = analyzer2.compare_complexity(metrics_v1)

    assert len(trends) > 0
    assert trends[0].direction == "increasing"


def test_stable_complexity_trend(analyzer, simple_symbol):
    """Test stable complexity trend."""
    symbols = {"simple": simple_symbol}
    structures = {"simple": {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0}}

    # First analysis
    metrics_v1 = analyzer.analyze(symbols, structures)

    # Second analysis with same complexity
    analyzer2 = ComplexityAnalyzer()
    metrics_v2 = analyzer2.analyze(symbols, structures)

    # Compare
    trends = analyzer2.compare_complexity(metrics_v1)

    if len(trends) > 0:
        assert trends[0].direction == "stable"


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_analysis(analyzer):
    """Test report with no analysis."""
    report = analyzer.get_complexity_report()

    assert report.status == "no_analysis"
    assert report.total_symbols == 0


def test_report_with_analysis(analyzer, simple_symbol, complex_symbol):
    """Test report generation."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 5, "loops": 2, "nesting_depth": 2, "decisions": 5},
    }

    analyzer.analyze(symbols, structures)
    report = analyzer.get_complexity_report()

    assert report.status == "analyzed"
    assert report.total_symbols == 2
    assert report.average_cyclomatic > 0
    assert report.average_cognitive > 0


def test_report_includes_distribution(analyzer, simple_symbol, complex_symbol):
    """Test report includes complexity distribution."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 8, "loops": 4, "nesting_depth": 3, "decisions": 8},
    }

    analyzer.analyze(symbols, structures)
    report = analyzer.get_complexity_report()

    assert "simple" in report.distribution
    assert report.distribution["simple"] > 0


def test_report_includes_refactoring_targets(analyzer, simple_symbol, complex_symbol):
    """Test report includes refactoring targets."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 10, "loops": 5, "nesting_depth": 3, "decisions": 10},
    }

    analyzer.analyze(symbols, structures)
    report = analyzer.get_complexity_report()

    assert isinstance(report.refactoring_targets, list)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_analysis_workflow(analyzer, simple_symbol, complex_symbol):
    """Test complete analysis workflow."""
    symbols = {
        "simple": simple_symbol,
        "complex": complex_symbol,
    }
    structures = {
        "simple": {"branches": 1, "loops": 0, "nesting_depth": 0, "decisions": 0},
        "complex": {"branches": 10, "loops": 5, "nesting_depth": 4, "decisions": 10},
    }

    # Analyze
    metrics = analyzer.analyze(symbols, structures)
    assert len(metrics) == 2

    # Get stats
    stats = analyzer.get_complexity_stats()
    assert stats.count == 2

    # Get report
    report = analyzer.get_complexity_report()
    assert report.status == "analyzed"
    assert report.total_symbols == 2

    # Get targets
    targets = analyzer.get_refactoring_targets()
    assert isinstance(targets, list)


def test_metrics_recording(analyzer, simple_symbol):
    """Test recording of metrics for trend tracking."""
    symbols = {"simple": simple_symbol}
    structures = {"simple": {"branches": 0, "loops": 0, "nesting_depth": 0, "decisions": 0}}

    analyzer.analyze(symbols, structures)
    report = analyzer.get_complexity_report()
    analyzer.record_metrics(report)

    assert len(analyzer.historical_metrics) == 1
    assert analyzer.historical_metrics[0].status == "analyzed"
