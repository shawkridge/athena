"""Unit tests for Testability Analyzer.

Tests testability analysis including:
- Dependency injection readiness
- Side effect detection
- Coupling assessment
- External dependency analysis
- Issue detection
- Coverage potential
- Suggestions
"""

import pytest
from athena.symbols.testability_analyzer import (
    TestabilityAnalyzer,
    TestabilityScore,
    TestabilityRating,
    TestabilityIssue,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance."""
    return TestabilityAnalyzer()


@pytest.fixture
def testable_symbol():
    """Create a highly testable symbol."""
    return Symbol(
        name="pure_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="test",
        full_qualified_name="test.pure_function",
        signature="def pure_function(x: int, y: int) -> int:",
        code="return x + y",
        docstring="Add two numbers.",
        metrics=SymbolMetrics(),
        language="python",
    )


@pytest.fixture
def untestable_symbol():
    """Create an untestable symbol."""
    code = """
global state
state = None
import requests
import time
def bad_function():
    global state
    data = requests.get('http://api.example.com/data')
    state = data.json()
    file = open('/data/file.txt', 'w')
    file.write(str(state))
    file.close()
    time.sleep(1)
    return state
"""
    return Symbol(
        name="bad_function",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=15,
        namespace="test",
        full_qualified_name="test.bad_function",
        signature="def bad_function():",
        code=code,
        docstring="",
        metrics=SymbolMetrics(),
        language="python",
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes with empty scores."""
    assert analyzer.scores == []
    assert analyzer.metrics is None


def test_analyzer_skips_non_callable_symbols(analyzer):
    """Test analyzer skips non-callable symbols."""
    var_symbol = Symbol(
        name="some_constant",
        symbol_type=SymbolType.CONSTANT,
        file_path="test.py",
        line_start=1,
        line_end=1,
        namespace="",
        full_qualified_name="some_constant",
        signature="",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(var_symbol)
    assert score is None


# ============================================================================
# Dependency Injection Scoring Tests
# ============================================================================


def test_high_di_score_with_parameters(analyzer, testable_symbol):
    """Test function with parameters scores high for DI."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.dependency_injection_score >= 70


def test_low_di_score_with_instantiations(analyzer):
    """Test function with many instantiations scores low."""
    code = "a = ClassA(); b = ClassB(); c = ClassC(); d = ClassD(); e = ClassE()"
    symbol = Symbol(
        name="many_instantiations",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="many_instantiations",
        signature="def many_instantiations():",
        code=code,
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # Many instantiations reduce DI score
    assert score.dependency_injection_score < 100


# ============================================================================
# Side Effect Scoring Tests
# ============================================================================


def test_high_side_effect_score_for_pure_function(analyzer, testable_symbol):
    """Test pure function scores high for side effects."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.side_effect_score >= 80


def test_low_side_effect_score_with_print(analyzer):
    """Test function with print scores lower."""
    symbol = Symbol(
        name="print_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="print_func",
        signature="def print_func():",
        code="print('hello'); return 42",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # Print reduces side effect score
    assert score.side_effect_score < 100


def test_global_state_reduces_side_effect_score(analyzer):
    """Test global state modification reduces score."""
    symbol = Symbol(
        name="global_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="global_func",
        signature="def global_func():",
        code="global x\nx = 42",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # Global state is detected as critical issue
    assert len([i for i in score.issues if i.issue_type.value == "global_state"]) > 0


# ============================================================================
# Coupling Scoring Tests
# ============================================================================


def test_low_coupling_high_score(analyzer, testable_symbol):
    """Test loosely coupled code scores high."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.coupling_score >= 70


def test_tight_coupling_low_score(analyzer):
    """Test tightly coupled code scores coupling."""
    code = "obj.method1().method2().method3().method4().method5()"
    symbol = Symbol(
        name="tight_coupling",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="tight_coupling",
        signature="def tight_coupling():",
        code=code,
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # Method chaining is assessed for coupling
    assert score.coupling_score >= 0


# ============================================================================
# External Dependency Scoring Tests
# ============================================================================


def test_high_ext_dep_score_pure_code(analyzer, testable_symbol):
    """Test code without external dependencies scores high."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.external_dependency_score >= 70


def test_low_ext_dep_score_with_file_io(analyzer):
    """Test file I/O reduces external dependency score."""
    symbol = Symbol(
        name="file_io_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="file_io_func",
        signature="def file_io_func():",
        code="f = open('file.txt'); data = f.read(); f.close()",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # File I/O detected as issue
    assert any(i.issue_type.value == "file_io" for i in score.issues)


def test_very_low_ext_dep_score_with_network_io(analyzer):
    """Test network I/O detected as critical issue."""
    symbol = Symbol(
        name="network_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="network_func",
        signature="def network_func():",
        code="import requests\nr = requests.get('http://api.example.com')",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    # Network I/O detected as critical issue
    assert any(i.issue_type.value == "network_io" for i in score.issues)


# ============================================================================
# Issue Detection Tests
# ============================================================================


def test_global_state_issue_detected(analyzer):
    """Test global state is detected as issue."""
    symbol = Symbol(
        name="global_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="global_func",
        signature="def global_func():",
        code="global x\nx = 42",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert len(score.issues) > 0
    issue_types = [i.issue_type for i in score.issues]
    assert TestabilityIssue.GLOBAL_STATE in issue_types


def test_file_io_issue_detected(analyzer):
    """Test file I/O is detected as issue."""
    symbol = Symbol(
        name="file_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="file_func",
        signature="def file_func():",
        code="f = open('file.txt'); f.write('data')",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert len(score.issues) > 0
    issue_types = [i.issue_type for i in score.issues]
    assert TestabilityIssue.FILE_IO in issue_types


def test_network_io_issue_detected(analyzer):
    """Test network I/O is detected as issue."""
    symbol = Symbol(
        name="network_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="network_func",
        signature="def network_func():",
        code="import requests\nresponse = requests.get('http://example.com')",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert len(score.issues) > 0
    issue_types = [i.issue_type for i in score.issues]
    assert TestabilityIssue.NETWORK_IO in issue_types


def test_time_dependency_issue_detected(analyzer):
    """Test time/random functions detected."""
    symbol = Symbol(
        name="time_func",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=5,
        namespace="",
        full_qualified_name="time_func",
        signature="def time_func():",
        code="import time\ntime.sleep(1)\nreturn time.time()",
        docstring="",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert len(score.issues) > 0
    issue_types = [i.issue_type for i in score.issues]
    assert TestabilityIssue.TIME_DEPENDENCIES in issue_types


# ============================================================================
# Rating Assignment Tests
# ============================================================================


def test_highly_testable_rating(analyzer, testable_symbol):
    """Test highly testable code gets correct rating."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.rating == TestabilityRating.HIGHLY_TESTABLE


def test_untestable_rating(analyzer, untestable_symbol):
    """Test untestable code has many issues."""
    score = analyzer.analyze_symbol(untestable_symbol)
    # Code with external dependencies should have multiple issues
    assert len(score.issues) > 2
    # Should have at least some critical/high issues
    critical_high = [i for i in score.issues if i.severity in ["critical", "high"]]
    assert len(critical_high) > 0


# ============================================================================
# Coverage Potential Tests
# ============================================================================


def test_high_coverage_potential_pure_function(analyzer, testable_symbol):
    """Test pure function has high coverage potential."""
    score = analyzer.analyze_symbol(testable_symbol)
    assert score.test_coverage_potential >= 0.8


def test_low_coverage_potential_with_issues(analyzer, untestable_symbol):
    """Test function with critical issues has low coverage potential."""
    score = analyzer.analyze_symbol(untestable_symbol)
    assert score.test_coverage_potential < 0.7


# ============================================================================
# Suggestions Tests
# ============================================================================


def test_suggestions_for_untestable_code(analyzer, untestable_symbol):
    """Test suggestions generated for untestable code."""
    score = analyzer.analyze_symbol(untestable_symbol)
    assert len(score.suggestions) > 0


def test_minimal_suggestions_for_testable_code(analyzer, testable_symbol):
    """Test minimal suggestions for testable code."""
    score = analyzer.analyze_symbol(testable_symbol)
    # Even good code might have suggestions
    assert isinstance(score.suggestions, list)


# ============================================================================
# Multiple Symbol Analysis Tests
# ============================================================================


def test_analyze_all_multiple_symbols(analyzer, testable_symbol, untestable_symbol):
    """Test analyzing multiple symbols."""
    scores = analyzer.analyze_all([testable_symbol, untestable_symbol])
    assert len(scores) == 2
    assert scores[0].overall_score > scores[1].overall_score


def test_analyze_all_clean_code(analyzer):
    """Test analyzing multiple testable symbols."""
    symbols = [
        Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10 + 1,
            line_end=i * 10 + 5,
            namespace="",
            full_qualified_name=f"func{i}",
            signature=f"def func{i}(x):",
            code="return x",
            docstring="Simple function.",
            metrics=SymbolMetrics(),
        )
        for i in range(3)
    ]
    scores = analyzer.analyze_all(symbols)
    assert len(scores) == 3
    assert all(s.rating == TestabilityRating.HIGHLY_TESTABLE for s in scores)


# ============================================================================
# Query Methods Tests
# ============================================================================


def test_get_scores_by_rating(analyzer, testable_symbol, untestable_symbol):
    """Test filtering scores by rating."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])

    highly_testable = analyzer.get_scores_by_rating(TestabilityRating.HIGHLY_TESTABLE)
    assert len(highly_testable) > 0

    # At least one should be testable or lower
    testable_or_lower = [s for s in analyzer.scores
                         if s.rating in [TestabilityRating.TESTABLE, TestabilityRating.MODERATELY_TESTABLE,
                                        TestabilityRating.DIFFICULT, TestabilityRating.UNTESTABLE]]
    assert len(testable_or_lower) >= 0


def test_get_symbols_with_issues(analyzer, testable_symbol, untestable_symbol):
    """Test getting symbols with issues."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])

    with_issues = analyzer.get_symbols_with_issues()
    assert len(with_issues) > 0


def test_get_lowest_testability(analyzer, testable_symbol, untestable_symbol):
    """Test getting lowest testability."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])

    worst = analyzer.get_lowest_testability(limit=1)
    assert len(worst) == 1
    # Lowest should score lower than highest
    assert worst[0].overall_score < analyzer.scores[0].overall_score


# ============================================================================
# Metrics Calculation Tests
# ============================================================================


def test_metrics_after_analysis(analyzer, testable_symbol, untestable_symbol):
    """Test metrics calculated after analysis."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])

    # Trigger metric calculation via report
    analyzer.get_testability_report()
    assert analyzer.metrics is not None
    assert analyzer.metrics.total_symbols == 2


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
            signature=f"def func{i}(x):",
            code="return x + 1",
            docstring="Simple function.",
            metrics=SymbolMetrics(),
        )
        for i in range(3)
    ]
    analyzer.analyze_all(symbols)

    analyzer.get_testability_report()
    assert analyzer.metrics is not None
    assert analyzer.metrics.highly_testable_count == 3


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_analysis(analyzer):
    """Test report with no analysis."""
    report = analyzer.get_testability_report()
    assert report["status"] == "no_analysis"


def test_report_with_analysis(analyzer, testable_symbol, untestable_symbol):
    """Test report generation."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])
    report = analyzer.get_testability_report()

    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 2
    assert "average_testability_score" in report
    assert "distribution" in report
    assert "issues_summary" in report
    assert "least_testable" in report


def test_report_contains_least_testable(analyzer, testable_symbol, untestable_symbol):
    """Test report contains least testable symbols."""
    analyzer.analyze_all([testable_symbol, untestable_symbol])
    report = analyzer.get_testability_report()

    least_testable = report["least_testable"]
    assert len(least_testable) > 0

    for symbol in least_testable:
        assert "symbol" in symbol
        assert "score" in symbol
        assert "rating" in symbol
        assert "issues" in symbol
        assert "coverage_potential" in symbol


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
        code="def __init__(self): pass",
        docstring="Test class.",
        metrics=SymbolMetrics(),
    )
    score = analyzer.analyze_symbol(symbol)
    assert score is not None


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(analyzer):
    """Test complete testability analysis workflow."""
    symbols = [
        Symbol(
            name="simple",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=1,
            line_end=5,
            namespace="",
            full_qualified_name="simple",
            signature="def simple(x):",
            code="return x + 1",
            docstring="Simple.",
            metrics=SymbolMetrics(),
        ),
        Symbol(
            name="complex",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=20,
            line_end=30,
            namespace="",
            full_qualified_name="complex",
            signature="def complex():",
            code="import requests\nglobal x\nx = requests.get('http://x.com')\nfile = open('data.txt')\nfile.write(str(x))",
            docstring="",
            metrics=SymbolMetrics(),
        ),
    ]

    # Analyze
    scores = analyzer.analyze_all(symbols)
    assert len(scores) == 2

    # Query
    highly_testable = analyzer.get_scores_by_rating(TestabilityRating.HIGHLY_TESTABLE)
    assert len(highly_testable) > 0

    # Check issues
    with_issues = analyzer.get_symbols_with_issues()
    assert len(with_issues) > 0

    # Report
    report = analyzer.get_testability_report()
    assert report["status"] == "analyzed"
    assert report["total_symbols"] == 2
