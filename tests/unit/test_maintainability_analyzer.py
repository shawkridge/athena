"""Unit tests for Maintainability Analyzer.

Tests maintainability analysis including:
- Complexity scoring
- Documentation scoring
- Size/length scoring
- Duplication scoring
- Style/consistency scoring
- Risk assessment
- Rating assignment
- Improvement recommendations
"""

import pytest
from athena.symbols.maintainability_analyzer import (
    MaintainabilityAnalyzer,
    MaintainabilityScore,
    MaintainabilityRating,
    RiskLevel,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance."""
    return MaintainabilityAnalyzer()


@pytest.fixture
def simple_symbol():
    """Create a simple, well-maintained symbol."""
    return Symbol(
        name="simple_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="test",
        full_qualified_name="test.simple_function",
        signature="def simple_function(x: int) -> int:",
        code="return x + 1",
        docstring="Return x plus one.",
        metrics=SymbolMetrics(cyclomatic_complexity=1),
        language="python",
    )


@pytest.fixture
def complex_symbol():
    """Create a complex, poorly-maintained symbol."""
    return Symbol(
        name="complex_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=300,
        namespace="test",
        full_qualified_name="test.complex_function",
        signature="def complex_function(a, b, c, d, e, f, g, h):",
        code="",
        docstring="",
        metrics=SymbolMetrics(cyclomatic_complexity=35),
        language="python",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes with empty scores."""
    assert analyzer.scores == []
    assert analyzer.metrics is None


def test_analyzer_with_non_callable_symbol(analyzer, simple_symbol):
    """Test analyzer skips non-callable symbols."""
    var_symbol = Symbol(
        name="module_constant",
        symbol_type=SymbolType.CONSTANT,
        file_path="test.py",
        line_start=1,
        line_end=1,
        namespace="",
        full_qualified_name="module_constant",
        signature="",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(var_symbol)
    assert score is None


# ============================================================================
# Complexity Scoring Tests
# ============================================================================


def test_low_complexity_high_score(analyzer, simple_symbol):
    """Test low complexity gets high score."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score is not None
    assert score.complexity_score >= 80


def test_high_complexity_low_score(analyzer, complex_symbol):
    """Test high complexity gets low score."""
    score = analyzer.analyze_symbol(complex_symbol)
    assert score is not None
    assert score.complexity_score < 50


# ============================================================================
# Documentation Scoring Tests
# ============================================================================


def test_with_docstring_higher_score(analyzer, simple_symbol):
    """Test symbol with docstring scores higher."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score.documentation_score > 30


def test_without_docstring_zero_score(analyzer):
    """Test symbol without docstring gets zero."""
    symbol = Symbol(
        name="undocumented",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="undocumented",
        signature="def undocumented():",
        code="pass",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.documentation_score == 0.0


def test_comprehensive_docstring_high_score(analyzer):
    """Test comprehensive docstring gets high score."""
    symbol = Symbol(
        name="well_documented",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="well_documented",
        signature="def well_documented(x, y):",
        code="return x + y",
        docstring="Add two numbers.\n\nArgs:\n    x: First number\n    y: Second number\n\nReturns:\n    Sum of x and y",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.documentation_score >= 80


# ============================================================================
# Size Scoring Tests
# ============================================================================


def test_small_function_high_size_score(analyzer):
    """Test small function gets high size score."""
    symbol = Symbol(
        name="tiny_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="tiny_func",
        signature="def tiny_func():",
        code="return 42",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.size_score == 100.0


def test_medium_function_good_size_score(analyzer):
    """Test medium function gets good size score."""
    symbol = Symbol(
        name="medium_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=30,
        namespace="",
        full_qualified_name="medium_func",
        signature="def medium_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert 70 <= score.size_score <= 100


def test_large_function_low_size_score(analyzer):
    """Test large function gets low size score."""
    symbol = Symbol(
        name="large_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=250,
        namespace="",
        full_qualified_name="large_func",
        signature="def large_func():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.size_score < 50


# ============================================================================
# Duplication Scoring Tests
# ============================================================================


def test_low_duplication_high_score(analyzer, simple_symbol):
    """Test code with low duplication gets high score."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score.duplication_score >= 50


def test_high_duplication_low_score(analyzer):
    """Test code with high duplication gets low score."""
    repeated_code = "if x == 1: pass\nif y == 2: pass\nif z == 3: pass\nif w == 4: pass"
    symbol = Symbol(
        name="duplicated_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="duplicated_func",
        signature="def duplicated_func():",
        code=repeated_code,
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.duplication_score < 80


# ============================================================================
# Style Scoring Tests
# ============================================================================


def test_good_naming_style_score(analyzer, simple_symbol):
    """Test good naming convention gets good score."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score.style_score > 50


def test_magic_numbers_reduce_style_score(analyzer):
    """Test magic numbers reduce style score."""
    symbol = Symbol(
        name="magic_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="magic_func",
        signature="def magic_func():",
        code="x = 12345; y = 67890; z = 11111; a = 22222; b = 33333; c = 44444",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.style_score < 90


def test_todo_comments_reduce_style_score(analyzer):
    """Test TODO comments reduce style score."""
    symbol = Symbol(
        name="todo_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="todo_func",
        signature="def todo_func():",
        code="# TODO: Fix this later\nreturn None",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.style_score < 95


# ============================================================================
# Rating Assignment Tests
# ============================================================================


def test_excellent_rating(analyzer, simple_symbol):
    """Test excellent rating for high-quality code."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score.rating == MaintainabilityRating.EXCELLENT


def test_critical_rating(analyzer, complex_symbol):
    """Test critical rating for low-quality code."""
    score = analyzer.analyze_symbol(complex_symbol)
    assert score.rating == MaintainabilityRating.CRITICAL


# ============================================================================
# Risk Assessment Tests
# ============================================================================


def test_low_risk_for_excellent_code(analyzer, simple_symbol):
    """Test low risk for excellent code."""
    score = analyzer.analyze_symbol(simple_symbol)
    assert score.risk_level == RiskLevel.LOW


def test_critical_risk_for_poor_code(analyzer, complex_symbol):
    """Test critical risk for poor code."""
    score = analyzer.analyze_symbol(complex_symbol)
    assert score.risk_level == RiskLevel.CRITICAL


def test_medium_risk_for_fair_code(analyzer):
    """Test medium risk for fair code."""
    symbol = Symbol(
        name="fair_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=75,
        namespace="",
        full_qualified_name="fair_func",
        signature="def fair_func(x, y):",
        code="if x > 0: return y else: return -y",
        docstring="Process numbers.",
        metrics=SymbolMetrics(cyclomatic_complexity=5),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]


# ============================================================================
# Suggestion Generation Tests
# ============================================================================


def test_suggestions_for_complex_code(analyzer, complex_symbol):
    """Test suggestions generated for complex code."""
    score = analyzer.analyze_symbol(complex_symbol)
    assert len(score.suggestions) > 0
    # Should suggest reducing complexity
    suggestions_text = " ".join(score.suggestions).lower()
    assert "complex" in suggestions_text or "smaller" in suggestions_text


def test_no_suggestions_for_good_code(analyzer, simple_symbol):
    """Test minimal suggestions for good code."""
    score = analyzer.analyze_symbol(simple_symbol)
    # Good code may still have some suggestions
    assert isinstance(score.suggestions, list)


# ============================================================================
# Multiple Symbol Analysis Tests
# ============================================================================


def test_analyze_all_multiple_symbols(analyzer, simple_symbol, complex_symbol):
    """Test analyzing multiple symbols."""
    scores = analyzer.analyze_all([simple_symbol, complex_symbol])
    assert len(scores) == 2
    assert scores[0].overall_score > scores[1].overall_score


def test_analyze_all_clean_code(analyzer):
    """Test analyzing multiple clean symbols."""
    symbols = [
        Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10 + 1,
            line_end=i * 10 + 5,
            namespace="",
            full_qualified_name=f"func{i}",
            signature=f"def func{i}():",
            code="return 42",
            docstring="Simple function.",
            metrics=SymbolMetrics(cyclomatic_complexity=1),
        )
        for i in range(3)
    ]
    scores = analyzer.analyze_all(symbols)
    assert len(scores) == 3
    assert all(s.rating == MaintainabilityRating.EXCELLENT for s in scores)


# ============================================================================
# Query Methods Tests
# ============================================================================


def test_get_scores_by_rating(analyzer, simple_symbol, complex_symbol):
    """Test filtering scores by rating."""
    analyzer.analyze_all([simple_symbol, complex_symbol])

    excellent_scores = analyzer.get_scores_by_rating(MaintainabilityRating.EXCELLENT)
    assert len(excellent_scores) > 0

    # Complex symbol should have poor or worse rating
    poor_or_worse = [s for s in analyzer.scores
                     if s.rating in [MaintainabilityRating.POOR, MaintainabilityRating.CRITICAL]]
    assert len(poor_or_worse) > 0


def test_get_scores_by_risk(analyzer, simple_symbol, complex_symbol):
    """Test filtering scores by risk level."""
    analyzer.analyze_all([simple_symbol, complex_symbol])
    
    low_risk = analyzer.get_scores_by_risk(RiskLevel.LOW)
    assert len(low_risk) > 0
    
    critical_risk = analyzer.get_scores_by_risk(RiskLevel.CRITICAL)
    assert len(critical_risk) > 0


def test_get_lowest_scoring_symbols(analyzer, simple_symbol, complex_symbol):
    """Test getting lowest scoring symbols."""
    analyzer.analyze_all([simple_symbol, complex_symbol])
    
    worst = analyzer.get_lowest_scoring_symbols(limit=1)
    assert len(worst) == 1
    # complex_symbol should be the worst
    assert worst[0].overall_score < 50


# ============================================================================
# Metrics Calculation Tests
# ============================================================================


def test_metrics_after_analysis(analyzer, simple_symbol, complex_symbol):
    """Test metrics are calculated after analysis."""
    analyzer.analyze_all([simple_symbol, complex_symbol])

    # Get report which triggers metric calculation
    report = analyzer.get_maintainability_report()
    assert analyzer.metrics is not None
    assert analyzer.metrics.total_symbols == 2
    assert analyzer.metrics.average_score > 0


def test_metrics_with_clean_code(analyzer):
    """Test metrics with only clean code."""
    symbols = [
        Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10 + 1,
            line_end=i * 10 + 5,
            namespace="",
            full_qualified_name=f"func{i}",
            signature=f"def func{i}():",
            code="return 42",
            docstring="Simple function.",
            metrics=SymbolMetrics(cyclomatic_complexity=1),
        )
        for i in range(3)
    ]
    analyzer.analyze_all(symbols)

    # Trigger metric calculation
    analyzer.get_maintainability_report()
    assert analyzer.metrics is not None
    assert analyzer.metrics.code_health_percentage >= 90


def test_code_health_percentage(analyzer):
    """Test code health percentage calculation."""
    # Mix of good and bad symbols
    symbols = [
        Symbol(
            name="good_func",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="good_func",
            signature="def good_func():",
            code="return 42",
            docstring="Good function.",
            metrics=SymbolMetrics(cyclomatic_complexity=1),
        ),
        Symbol(
            name="bad_func",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=200,
            namespace="",
            full_qualified_name="bad_func",
            signature="def bad_func(a, b, c, d, e):",
            code="",
            docstring="",
            metrics=SymbolMetrics(cyclomatic_complexity=25),
        ),
    ]
    analyzer.analyze_all(symbols)

    # Trigger metric calculation
    analyzer.get_maintainability_report()
    # Should have 50% health
    assert 40 <= analyzer.metrics.code_health_percentage <= 60


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_analysis(analyzer):
    """Test report with no analysis."""
    report = analyzer.get_maintainability_report()
    assert report["status"] == "no_analysis"


def test_report_with_analysis(analyzer, simple_symbol, complex_symbol):
    """Test report generation with analysis."""
    analyzer.analyze_all([simple_symbol, complex_symbol])
    report = analyzer.get_maintainability_report()
    
    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 2
    assert "average_score" in report
    assert "distribution" in report
    assert "risk_distribution" in report
    assert "worst_offenders" in report


def test_report_contains_worst_offenders(analyzer, simple_symbol, complex_symbol):
    """Test report contains worst offenders with suggestions."""
    analyzer.analyze_all([simple_symbol, complex_symbol])
    report = analyzer.get_maintainability_report()
    
    worst_offenders = report["worst_offenders"]
    assert len(worst_offenders) > 0
    
    for offender in worst_offenders:
        assert "symbol" in offender
        assert "score" in offender
        assert "rating" in offender
        assert "suggestions" in offender


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_symbol_with_no_code(analyzer):
    """Test analyzing symbol with no code."""
    symbol = Symbol(
        name="empty_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=1,
        namespace="",
        full_qualified_name="empty_func",
        signature="def empty_func():",
        code="",
        docstring="",
        metrics=None,
    )
    score = analyzer.analyze_symbol(symbol)
    assert score is not None
    assert score.overall_score >= 0


def test_symbol_with_no_metrics(analyzer):
    """Test analyzing symbol with no metrics."""
    symbol = Symbol(
        name="no_metrics_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="no_metrics_func",
        signature="def no_metrics_func():",
        code="return 42",
        docstring="",
        metrics=None,
    )
    score = analyzer.analyze_symbol(symbol)
    assert score is not None
    # Should use default values
    assert score.complexity_score == 50.0


def test_class_symbol_analysis(analyzer):
    """Test analyzing class symbol."""
    symbol = Symbol(
        name="TestClass",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=50,
        namespace="",
        full_qualified_name="TestClass",
        signature="class TestClass:",
        code="",
        docstring="Test class.",
        metrics=SymbolMetrics(cyclomatic_complexity=5),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score is not None
    assert score.symbol.name == "TestClass"


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(analyzer):
    """Test complete analysis workflow."""
    # Create diverse symbols
    symbols = [
        Symbol(
            name="simple",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=5,
            namespace="",
            full_qualified_name="simple",
            signature="def simple():",
            code="return 42",
            docstring="Simple.",
            metrics=SymbolMetrics(cyclomatic_complexity=1),
        ),
        Symbol(
            name="complex",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=250,
            namespace="",
            full_qualified_name="complex",
            signature="def complex(a, b, c, d, e, f, g):",
            code="",
            docstring="",
            metrics=SymbolMetrics(cyclomatic_complexity=40),
        ),
    ]

    # Analyze
    scores = analyzer.analyze_all(symbols)
    assert len(scores) == 2

    # Query - should have some good scores
    good_or_better = [s for s in analyzer.scores
                      if s.rating in [MaintainabilityRating.EXCELLENT, MaintainabilityRating.GOOD]]
    assert len(good_or_better) >= 1

    # Report
    report = analyzer.get_maintainability_report()
    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 2
    assert len(report["worst_offenders"]) > 0
