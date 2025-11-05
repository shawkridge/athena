"""Unit tests for Technical Debt Analyzer.

Tests technical debt analysis including:
- Debt scoring by category
- Debt item detection
- Priority calculation
- ROI analysis
- Comprehensive reporting
"""

import pytest
from athena.symbols.technical_debt_analyzer import (
    TechnicalDebtAnalyzer,
    DebtScore,
    DebtItem,
    DebtCategory,
    DebtSeverity,
    DebtPriority,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance."""
    return TechnicalDebtAnalyzer()


@pytest.fixture
def clean_symbol():
    """Create a clean symbol with no debt."""
    return Symbol(
        name="clean_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="test",
        full_qualified_name="test.clean_function",
        signature="def clean_function(x: int) -> int:",
        code="return x + 1",
        docstring="Simple function.",
        metrics=SymbolMetrics(),
        language="python",
    )


@pytest.fixture
def messy_symbol():
    """Create a symbol with significant debt."""
    return Symbol(
        name="messy_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=100,
        namespace="test",
        full_qualified_name="test.messy_function",
        signature="def messy_function():",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
        language="python",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes empty."""
    assert analyzer.scores == []
    assert analyzer.metrics is None


def test_analyzer_skips_non_callable_symbols(analyzer):
    """Test analyzer skips non-callable symbols."""
    var_symbol = Symbol(
        name="constant",
        symbol_type=SymbolType.CONSTANT,
        file_path="test.py",
        line_start=1,
        line_end=1,
        namespace="",
        full_qualified_name="constant",
        signature="",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(var_symbol)
    assert score is None


# ============================================================================
# Debt Scoring Tests
# ============================================================================


def test_clean_symbol_no_debt(analyzer, clean_symbol):
    """Test clean symbol has no debt."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        security_issues=0,
        performance_issues=0,
        code_smells=0,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )
    assert score.overall_debt_score < 20


def test_security_issues_increase_debt(analyzer, clean_symbol):
    """Test security issues produce debt items."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        security_issues=1,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )

    # Should have security debt items
    security_items = [i for i in score.debt_items if i.category == DebtCategory.SECURITY]
    assert len(security_items) > 0
    assert score.security_debt > 0


def test_performance_issues_increase_debt(analyzer, clean_symbol):
    """Test performance issues produce debt items."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        performance_issues=2,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )

    # Should have performance debt items
    perf_items = [i for i in score.debt_items if i.category == DebtCategory.PERFORMANCE]
    assert len(perf_items) > 0
    assert score.performance_debt > 0


def test_code_smells_increase_debt(analyzer, clean_symbol):
    """Test code smells produce debt items."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        code_smells=3,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )

    # Should have quality debt items
    quality_items = [i for i in score.debt_items if i.category == DebtCategory.QUALITY]
    assert len(quality_items) > 0
    assert score.quality_debt > 0


def test_low_maintainability_increases_debt(analyzer, clean_symbol):
    """Test low maintainability increases debt."""
    score1 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )
    
    score2 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=35.0,
        testability_score=85.0,
        has_docstring=True
    )
    
    assert score2.overall_debt_score > score1.overall_debt_score


def test_low_testability_increases_debt(analyzer, clean_symbol):
    """Test low testability increases debt."""
    score1 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )
    
    score2 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=85.0,
        testability_score=35.0,
        has_docstring=True
    )
    
    assert score2.overall_debt_score > score1.overall_debt_score


def test_missing_documentation_increases_debt(analyzer, clean_symbol):
    """Test missing documentation increases debt."""
    score1 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=True
    )
    
    score2 = analyzer.analyze_symbol(
        clean_symbol,
        maintainability_score=85.0,
        testability_score=85.0,
        has_docstring=False
    )
    
    assert score2.overall_debt_score > score1.overall_debt_score


# ============================================================================
# Debt Item Detection Tests
# ============================================================================


def test_security_debt_items_detected(analyzer, clean_symbol):
    """Test security debt items are created."""
    score = analyzer.analyze_symbol(clean_symbol, security_issues=2)
    assert len(score.debt_items) > 0
    security_items = [i for i in score.debt_items if i.category == DebtCategory.SECURITY]
    assert len(security_items) > 0


def test_performance_debt_items_detected(analyzer, clean_symbol):
    """Test performance debt items are created."""
    score = analyzer.analyze_symbol(clean_symbol, performance_issues=1)
    assert len(score.debt_items) > 0
    perf_items = [i for i in score.debt_items if i.category == DebtCategory.PERFORMANCE]
    assert len(perf_items) > 0


def test_quality_debt_items_detected(analyzer, clean_symbol):
    """Test code smell debt items are created."""
    score = analyzer.analyze_symbol(clean_symbol, code_smells=2)
    assert len(score.debt_items) > 0
    quality_items = [i for i in score.debt_items if i.category == DebtCategory.QUALITY]
    assert len(quality_items) > 0


def test_testing_debt_item_low_testability(analyzer, clean_symbol):
    """Test testing debt item detected with low testability."""
    score = analyzer.analyze_symbol(clean_symbol, testability_score=40.0)
    testing_items = [i for i in score.debt_items if i.category == DebtCategory.TESTING]
    assert len(testing_items) > 0


def test_documentation_debt_item_missing_doc(analyzer, clean_symbol):
    """Test documentation debt item without docstring."""
    score = analyzer.analyze_symbol(clean_symbol, has_docstring=False)
    doc_items = [i for i in score.debt_items if i.category == DebtCategory.DOCUMENTATION]
    assert len(doc_items) > 0


def test_maintainability_debt_item(analyzer, clean_symbol):
    """Test maintainability debt item with low score."""
    score = analyzer.analyze_symbol(clean_symbol, maintainability_score=35.0)
    maint_items = [i for i in score.debt_items if i.category == DebtCategory.MAINTAINABILITY]
    assert len(maint_items) > 0


# ============================================================================
# Multiple Symbol Analysis Tests
# ============================================================================


def test_analyze_all_symbols(analyzer, clean_symbol, messy_symbol):
    """Test analyzing multiple symbols."""
    scores = analyzer.analyze_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (messy_symbol, 2, 2, 3, 35.0, 35.0, False),
    ])
    assert len(scores) == 2
    assert scores[1].overall_debt_score > scores[0].overall_debt_score


# ============================================================================
# Query Methods Tests
# ============================================================================


def test_get_debt_by_category(analyzer, clean_symbol):
    """Test filtering by debt category."""
    analyzer.analyze_all([
        (clean_symbol, 2, 0, 0, 85.0, 85.0, True),
    ])
    
    security_debt = analyzer.get_debt_by_category(DebtCategory.SECURITY)
    assert len(security_debt) > 0


def test_get_critical_debt(analyzer, clean_symbol):
    """Test getting critical debt items."""
    analyzer.analyze_all([
        (clean_symbol, 2, 0, 0, 85.0, 85.0, True),
    ])
    
    critical = analyzer.get_critical_debt()
    assert len(critical) > 0
    assert all(item.severity == DebtSeverity.CRITICAL for item in critical)


def test_get_highest_debt_symbols(analyzer, clean_symbol, messy_symbol):
    """Test getting highest debt symbols."""
    analyzer.analyze_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (messy_symbol, 3, 3, 5, 35.0, 35.0, False),
    ])
    
    highest = analyzer.get_highest_debt_symbols(limit=1)
    assert len(highest) == 1
    assert highest[0].symbol.name == "messy_function"


def test_get_best_roi_debt_items(analyzer, clean_symbol):
    """Test getting highest ROI debt items."""
    analyzer.analyze_all([
        (clean_symbol, 1, 1, 1, 75.0, 75.0, False),
    ])
    
    best_roi = analyzer.get_best_roi_debt_items(limit=3)
    assert len(best_roi) > 0


# ============================================================================
# Metrics Calculation Tests
# ============================================================================


def test_metrics_after_analysis(analyzer, clean_symbol, messy_symbol):
    """Test metrics calculated after analysis."""
    analyzer.analyze_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (messy_symbol, 2, 2, 3, 35.0, 35.0, False),
    ])
    
    analyzer.get_debt_report()
    assert analyzer.metrics is not None
    assert analyzer.metrics.total_symbols == 2


def test_metrics_severity_breakdown(analyzer, clean_symbol):
    """Test severity breakdown in metrics."""
    analyzer.analyze_all([
        (clean_symbol, 2, 0, 0, 85.0, 85.0, True),
    ])
    
    analyzer.get_debt_report()
    assert analyzer.metrics.critical_count > 0


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_analysis(analyzer):
    """Test report with no analysis."""
    report = analyzer.get_debt_report()
    assert report["status"] == "no_analysis"


def test_report_with_analysis(analyzer, clean_symbol):
    """Test report generation."""
    analyzer.analyze_all([
        (clean_symbol, 1, 1, 1, 75.0, 75.0, True),
    ])
    report = analyzer.get_debt_report()
    
    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 1
    assert "severity_breakdown" in report
    assert "highest_debt_symbols" in report
    assert "best_roi_items" in report


def test_report_includes_highest_debt_symbols(analyzer, clean_symbol, messy_symbol):
    """Test report includes highest debt symbols."""
    analyzer.analyze_all([
        (clean_symbol, 0, 0, 0, 85.0, 85.0, True),
        (messy_symbol, 3, 3, 5, 35.0, 35.0, False),
    ])
    report = analyzer.get_debt_report()
    
    highest = report["highest_debt_symbols"]
    assert len(highest) > 0


def test_report_includes_best_roi_items(analyzer, clean_symbol):
    """Test report includes best ROI items."""
    analyzer.analyze_all([
        (clean_symbol, 1, 1, 1, 75.0, 75.0, False),
    ])
    report = analyzer.get_debt_report()
    
    best_roi = report["best_roi_items"]
    assert len(best_roi) > 0


# ============================================================================
# Edge Cases Tests
# ============================================================================


def test_symbol_with_max_issues(analyzer, clean_symbol):
    """Test symbol with maximum issues."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        security_issues=10,
        performance_issues=10,
        code_smells=10,
        maintainability_score=10.0,
        testability_score=10.0,
        has_docstring=False
    )
    assert score.overall_debt_score >= 80


def test_class_symbol_analysis(analyzer):
    """Test analyzing class symbol."""
    symbol = Symbol(
        name="TestClass",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=100,
        namespace="",
        full_qualified_name="TestClass",
        signature="class TestClass:",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol, security_issues=1)
    assert score is not None


def test_method_symbol_analysis(analyzer):
    """Test analyzing method symbol."""
    symbol = Symbol(
        name="method",
        symbol_type=SymbolType.METHOD,
        file_path="test.py",
        line_start=10,
        line_end=20,
        namespace="",
        full_qualified_name="Class.method",
        signature="def method(self):",
        code="pass",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol, performance_issues=1)
    assert score is not None


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(analyzer):
    """Test complete technical debt analysis workflow."""
    symbols = [
        Symbol(
            name="good_function",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=10,
            namespace="",
            full_qualified_name="good_function",
            signature="def good_function(x):",
            code="return x",
            docstring="Good.",
            metrics=SymbolMetrics(),
        ),
        Symbol(
            name="bad_function",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=100,
            namespace="",
            full_qualified_name="bad_function",
            signature="def bad_function():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    ]

    # Analyze with different issues
    scores = analyzer.analyze_all([
        (symbols[0], 0, 0, 0, 85.0, 85.0, True),
        (symbols[1], 2, 2, 3, 35.0, 35.0, False),
    ])
    assert len(scores) == 2

    # Query highest debt
    highest = analyzer.get_highest_debt_symbols(limit=1)
    assert highest[0].symbol.name == "bad_function"

    # Get best ROI
    best_roi = analyzer.get_best_roi_debt_items(limit=3)
    assert len(best_roi) > 0

    # Generate report
    report = analyzer.get_debt_report()
    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 2
    assert len(report["highest_debt_symbols"]) > 0


def test_debt_prioritization(analyzer, clean_symbol):
    """Test debt items are prioritized correctly."""
    score = analyzer.analyze_symbol(
        clean_symbol,
        security_issues=1,
        performance_issues=1,
        code_smells=1
    )
    
    # Security issues should be critical path
    security_items = [i for i in score.debt_items if i.category == DebtCategory.SECURITY]
    assert all(i.priority == DebtPriority.CRITICAL_PATH for i in security_items)
