"""Unit tests for Analysis Integrator.

Tests unified analysis including:
- Comprehensive symbol analysis
- Multi-analyzer coordination
- Result aggregation
- Summary generation
- End-to-end workflows
"""

import pytest
from athena.symbols.analysis_integrator import AnalysisIntegrator, AnalysisResult
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def integrator():
    """Create a fresh integrator."""
    return AnalysisIntegrator(project_name="Test Project")


@pytest.fixture
def test_symbols():
    """Create test symbols."""
    symbols = {}
    for i in range(1, 4):
        symbols[f"func{i}"] = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10,
            line_end=i * 10 + 10,
            namespace="",
            full_qualified_name=f"test.func{i}",
            signature=f"def func{i}():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        )
    return symbols


# ============================================================================
# Initialization Tests
# ============================================================================


def test_integrator_initialization(integrator):
    """Test integrator initializes correctly."""
    assert integrator.project_name == "Test Project"


# ============================================================================
# Analysis Tests
# ============================================================================


def test_basic_analysis(integrator, test_symbols):
    """Test basic analysis of symbols."""
    result = integrator.analyze(
        symbols=test_symbols,
        code_structures={},
        dependency_info={},
    )

    assert result is not None
    assert result.total_symbols == 3
    assert len(result.quality_scores) == 3
    assert result.total_issues >= 0
    assert result.pass_rate >= 0.0


def test_analysis_with_structures(integrator, test_symbols):
    """Test analysis with code structures."""
    code_structures = {
        "func1": {"branches": 1, "loops": 0, "nesting_depth": 0},
        "func2": {"branches": 3, "loops": 1, "nesting_depth": 1},
        "func3": {"branches": 5, "loops": 2, "nesting_depth": 2},
    }

    result = integrator.analyze(
        symbols=test_symbols,
        code_structures=code_structures,
        dependency_info={},
    )

    assert result.complexity_report is not None
    assert result.complexity_report.get("total_symbols", 0) == 3


def test_analysis_with_dependencies(integrator, test_symbols):
    """Test analysis with dependency information."""
    dependency_info = {
        "edges": [
            ("func1", "func2"),
            ("func2", "func3"),
        ]
    }

    result = integrator.analyze(
        symbols=test_symbols,
        code_structures={},
        dependency_info=dependency_info,
    )

    assert result.dependency_report is not None
    assert "status" in result.dependency_report


def test_full_analysis(integrator, test_symbols):
    """Test complete analysis with all inputs."""
    code_structures = {
        "func1": {"branches": 1, "loops": 0, "nesting_depth": 0},
    }
    dependency_info = {"edges": []}

    result = integrator.analyze(
        symbols=test_symbols,
        code_structures=code_structures,
        dependency_info=dependency_info,
        context={"func1.security": 0.8},
    )

    assert isinstance(result, AnalysisResult)
    assert result.quality_scores is not None
    assert result.metrics is not None
    assert result.dependency_report is not None
    assert result.complexity_report is not None


# ============================================================================
# Complexity Analysis Tests
# ============================================================================


def test_complexity_analysis(integrator, test_symbols):
    """Test complexity analysis integration."""
    code_structures = {
        "func1": {"branches": 1, "loops": 0, "nesting_depth": 0},
        "func2": {"branches": 3, "loops": 1, "nesting_depth": 1},
        "func3": {"branches": 5, "loops": 2, "nesting_depth": 2},
    }

    result = integrator.analyze(
        symbols=test_symbols,
        code_structures=code_structures,
    )

    assert result.complexity_report is not None
    assert result.complexity_report["total_symbols"] == 3


def test_complexity_refactoring_targets(integrator, test_symbols):
    """Test refactoring target identification."""
    code_structures = {
        "func1": {"branches": 1, "loops": 0, "nesting_depth": 0},
        "func2": {"branches": 3, "loops": 1, "nesting_depth": 1},
        "func3": {"branches": 5, "loops": 2, "nesting_depth": 2},
    }

    result = integrator.analyze(
        symbols=test_symbols,
        code_structures=code_structures,
    )

    assert isinstance(result.complexity_report, dict)


# ============================================================================
# Dependency Analysis Tests
# ============================================================================


def test_dependency_analysis(integrator, test_symbols):
    """Test dependency analysis integration."""
    dependency_info = {
        "edges": [
            ("func1", "func2"),
            ("func2", "func3"),
        ]
    }

    result = integrator.analyze(
        symbols=test_symbols,
        dependency_info=dependency_info,
    )

    assert result.dependency_report is not None
    assert result.dependency_report["status"] == "analyzed"


# ============================================================================
# Summary Generation Tests
# ============================================================================


def test_get_summary(integrator, test_symbols):
    """Test summary generation."""
    result = integrator.analyze(symbols=test_symbols)
    summary = integrator.get_summary(result)

    assert "Test Project" in summary
    assert "Quality Score" in summary
    assert "Health Score" in summary
    assert "Total Issues" in summary


def test_summary_contains_metrics(integrator, test_symbols):
    """Test that summary contains key metrics."""
    result = integrator.analyze(symbols=test_symbols)
    summary = integrator.get_summary(result)

    assert "Symbols Analyzed: 3" in summary
    assert "Pass Rate:" in summary


# ============================================================================
# Result Validation Tests
# ============================================================================


def test_result_structure(integrator, test_symbols):
    """Test AnalysisResult structure."""
    result = integrator.analyze(symbols=test_symbols)

    assert hasattr(result, "total_symbols")
    assert hasattr(result, "quality_scores")
    assert hasattr(result, "metrics")
    assert hasattr(result, "complexity_report")
    assert hasattr(result, "dependency_report")
    assert hasattr(result, "violations")
    assert hasattr(result, "total_issues")
    assert hasattr(result, "critical_count")
    assert hasattr(result, "pass_rate")


def test_result_types(integrator, test_symbols):
    """Test result data types."""
    result = integrator.analyze(symbols=test_symbols)

    assert isinstance(result.quality_scores, dict)
    assert isinstance(result.total_issues, int)
    assert isinstance(result.critical_count, int)
    assert isinstance(result.pass_rate, float)


def test_result_values(integrator, test_symbols):
    """Test result values are reasonable."""
    result = integrator.analyze(symbols=test_symbols)

    assert result.total_symbols == 3
    assert result.total_issues >= 0
    assert 0.0 <= result.pass_rate <= 1.0


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow(test_symbols):
    """Test complete end-to-end workflow."""
    integrator = AnalysisIntegrator("Full Workflow Test")

    # Execute analysis
    result = integrator.analyze(
        symbols=test_symbols,
        code_structures={},
        dependency_info={"edges": []},
        context={"func1.security": 0.85},
    )

    # Verify all components analyzed
    assert result.total_symbols == 3
    assert result.dependency_report["status"] == "analyzed"
    assert result.complexity_report["total_symbols"] == 3

    # Get summary
    summary = integrator.get_summary(result)
    assert len(summary) > 0


def test_empty_analysis(integrator):
    """Test analysis with empty symbols."""
    result = integrator.analyze(symbols={})

    assert result.quality_scores == {}
    assert result.total_symbols == 0
    assert result.dependency_report["status"] == "no_dependencies"


def test_large_analysis(integrator):
    """Test analysis with many symbols."""
    symbols = {}
    for i in range(1, 21):  # 20 symbols
        symbols[f"func{i}"] = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i,
            line_end=i + 1,
            namespace="",
            full_qualified_name=f"test.func{i}",
            signature=f"def func{i}():",
            code="",
            docstring="",
            metrics=SymbolMetrics(),
        )

    result = integrator.analyze(symbols=symbols)

    assert len(result.quality_scores) == 20
    assert result.total_symbols == 20


def test_analysis_with_context(integrator, test_symbols):
    """Test analysis with custom context."""
    context = {
        "func1.security": 0.9,
        "func1.performance": 0.8,
    }

    result = integrator.analyze(
        symbols=test_symbols,
        context=context,
    )

    assert result.total_symbols == 3
    assert result.metrics["overall_score"] > 0
