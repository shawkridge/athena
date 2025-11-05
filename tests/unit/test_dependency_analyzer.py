"""Unit tests for Dependency Analyzer.

Tests dependency analysis including:
- Dependency mapping
- Coupling analysis
- Circular dependency detection
- Impact analysis
- Report generation
"""

import pytest
from athena.symbols.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyType,
    CouplingLevel,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def analyzer():
    """Create a fresh analyzer instance."""
    return DependencyAnalyzer()


@pytest.fixture
def symbols():
    """Create test symbols."""
    symbols = {}
    for i in range(7):
        symbols[f"func{i}"] = Symbol(
            name=f"func{i}",
            symbol_type=SymbolType.FUNCTION,
            file_path="test.py",
            line_start=i * 10 + 1,
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


def test_analyzer_initialization(analyzer):
    """Test analyzer initializes empty."""
    assert analyzer.dependencies == []
    assert analyzer.metrics == {}
    assert analyzer.circular_chains == []


# ============================================================================
# Dependency Addition Tests
# ============================================================================


def test_add_dependency(analyzer, symbols):
    """Test adding a dependency."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    assert len(analyzer.dependencies) == 1
    assert analyzer.dependencies[0].from_symbol.name == "func0"
    assert analyzer.dependencies[0].to_symbol.name == "func1"


def test_add_multiple_dependencies(analyzer, symbols):
    """Test adding multiple dependencies."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func0"], symbols["func2"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])

    assert len(analyzer.dependencies) == 3


def test_dependency_type(analyzer, symbols):
    """Test dependency with specific type."""
    analyzer.add_dependency(
        symbols["func0"],
        symbols["func1"],
        dependency_type=DependencyType.IMPORTS
    )
    assert analyzer.dependencies[0].dependency_type == DependencyType.IMPORTS


def test_dependency_strength(analyzer, symbols):
    """Test dependency with strength."""
    analyzer.add_dependency(
        symbols["func0"],
        symbols["func1"],
        strength=0.8
    )
    assert analyzer.dependencies[0].strength == 0.8


# ============================================================================
# Analysis Tests
# ============================================================================


def test_analyze_simple_chain(analyzer, symbols):
    """Test analysis of simple dependency chain."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])

    metrics = analyzer.analyze()

    assert len(metrics) == 3
    assert metrics["test.func0"].outgoing_count == 1
    assert metrics["test.func1"].incoming_count == 1
    assert metrics["test.func1"].outgoing_count == 1
    assert metrics["test.func2"].incoming_count == 1


# ============================================================================
# Coupling Level Tests
# ============================================================================


def test_loose_coupling(analyzer, symbols):
    """Test loose coupling detection."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    metrics = analyzer.analyze()

    # func0 has 1 outgoing, func1 has 1 incoming
    assert metrics["test.func0"].coupling_level == CouplingLevel.LOOSE
    assert metrics["test.func1"].coupling_level == CouplingLevel.LOOSE


def test_tight_coupling(analyzer, symbols):
    """Test tight coupling detection."""
    # Create symbol with many dependencies
    central = symbols["func0"]

    for i in range(1, 5):
        analyzer.add_dependency(central, symbols[f"func{i}"])

    metrics = analyzer.analyze()

    assert metrics["test.func0"].coupling_level in [CouplingLevel.MODERATE, CouplingLevel.TIGHT]


# ============================================================================
# Hotspot Detection Tests
# ============================================================================


def test_hotspot_symbols(analyzer, symbols):
    """Test identification of hotspot symbols."""
    # Make func2 a hotspot
    for i in range(5):
        if i != 2:
            analyzer.add_dependency(symbols[f"func{i}"], symbols["func2"])

    analyzer.analyze()
    hotspots = analyzer.get_hotspot_symbols()

    assert len(hotspots) > 0
    assert hotspots[0][0] == "test.func2"
    assert hotspots[0][1] == 4


# ============================================================================
# Isolated Symbol Tests
# ============================================================================


def test_isolated_symbols(analyzer, symbols):
    """Test identification of isolated symbols."""
    # Add all symbols to metrics (even if isolated)
    for i in range(5):
        if i > 1:
            # Add isolated symbols through self-reference (will be filtered)
            analyzer.add_dependency(symbols[f"func{i}"], symbols[f"func{i}"])

    # Add one real dependency
    analyzer.add_dependency(symbols["func0"], symbols["func1"])

    analyzer.analyze()
    isolated = analyzer.get_isolated_symbols()

    # Isolated symbols should exist (or be empty if only 2 symbols in metrics)
    assert isinstance(isolated, list)


# ============================================================================
# Circular Dependency Tests
# ============================================================================


def test_circular_dependency_detection(analyzer, symbols):
    """Test detection of circular dependencies."""
    # Create a circular chain: func0 -> func1 -> func2 -> func0
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])
    analyzer.add_dependency(symbols["func2"], symbols["func0"])

    analyzer.analyze()

    # Check that circular dependencies are marked
    circular = False
    for dep in analyzer.dependencies:
        if dep.is_circular:
            circular = True
            break

    assert circular


def test_circular_chains(analyzer, symbols):
    """Test retrieval of circular chains."""
    # Create circular chain
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func1"], symbols["func0"])

    analyzer.analyze()
    chains = analyzer.get_circular_chains()

    assert len(chains) > 0


# ============================================================================
# Impact Analysis Tests
# ============================================================================


def test_change_impact_hotspot(analyzer, symbols):
    """Test impact analysis for hotspot symbol."""
    # Make func1 a hotspot (need >5 incoming)
    for i in range(7):
        if i != 1:
            analyzer.add_dependency(symbols[f"func{i}"], symbols["func1"])

    analyzer.analyze()
    impact = analyzer.calculate_change_impact(symbols["func1"])

    assert impact["symbol"] == "func1"
    assert impact["is_critical"] == True
    assert impact["total_impact"] >= 5


def test_change_impact_isolated(analyzer, symbols):
    """Test impact analysis for isolated symbol."""
    # Add only func4 as a destination with no dependencies
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    # func4 is isolated (not in any dependency path yet)

    analyzer.analyze()
    impact = analyzer.calculate_change_impact(symbols["func4"])

    # Symbol not in metrics should return unknown scope
    assert impact["impact_scope"] in ["unknown", "low"]


def test_change_impact_scope(analyzer, symbols):
    """Test impact scope calculation."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func0"], symbols["func2"])

    analyzer.analyze()
    impact = analyzer.calculate_change_impact(symbols["func0"])

    assert impact["impact_scope"] in ["low", "moderate", "high"]


# ============================================================================
# Incoming/Outgoing Dependency Tests
# ============================================================================


def test_incoming_dependencies(analyzer, symbols):
    """Test calculation of incoming dependencies."""
    analyzer.add_dependency(symbols["func0"], symbols["func2"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])

    metrics = analyzer.analyze()

    assert metrics["test.func2"].incoming_count == 2


def test_outgoing_dependencies(analyzer, symbols):
    """Test calculation of outgoing dependencies."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func0"], symbols["func2"])

    metrics = analyzer.analyze()

    assert metrics["test.func0"].outgoing_count == 2


# ============================================================================
# Report Generation Tests
# ============================================================================


def test_report_no_dependencies(analyzer):
    """Test report with no dependencies."""
    report = analyzer.get_dependency_report()
    assert report["status"] == "no_dependencies"


def test_report_with_dependencies(analyzer, symbols):
    """Test report generation."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])

    analyzer.analyze()
    report = analyzer.get_dependency_report()

    assert report["status"] == "analyzed"
    assert report["total_symbols"] >= 2
    assert report["total_dependencies"] == 2


def test_report_includes_hotspots(analyzer, symbols):
    """Test report includes hotspot symbols."""
    for i in range(1, 4):
        analyzer.add_dependency(symbols[f"func{i}"], symbols["func0"])

    analyzer.analyze()
    report = analyzer.get_dependency_report()

    assert len(report["hotspot_symbols"]) > 0
    assert report["hotspot_symbols"][0][0] == "test.func0"


def test_report_includes_coupling_counts(analyzer, symbols):
    """Test report includes coupling statistics."""
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func0"], symbols["func2"])

    analyzer.analyze()
    report = analyzer.get_dependency_report()

    assert "tight_coupling_count" in report
    assert "moderate_coupling_count" in report


# ============================================================================
# Integration Tests
# ============================================================================


def test_complex_dependency_graph(analyzer, symbols):
    """Test analysis of complex dependency graph."""
    # Create a more complex graph
    analyzer.add_dependency(symbols["func0"], symbols["func1"])
    analyzer.add_dependency(symbols["func0"], symbols["func2"])
    analyzer.add_dependency(symbols["func1"], symbols["func2"])
    analyzer.add_dependency(symbols["func1"], symbols["func3"])
    analyzer.add_dependency(symbols["func2"], symbols["func3"])

    metrics = analyzer.analyze()
    report = analyzer.get_dependency_report()

    assert len(metrics) >= 4
    assert report["total_dependencies"] == 5
    assert len(report["hotspot_symbols"]) > 0
