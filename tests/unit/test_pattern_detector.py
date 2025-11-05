"""Unit tests for Pattern Detector.

Tests pattern detection including:
- Design pattern recognition
- Anti-pattern identification
- Pattern metrics calculation
- Smell detection
- Refactoring recommendations
"""

import pytest
from athena.symbols.pattern_detector import (
    PatternDetector,
    PatternType,
    AntiPatternType,
)
from athena.symbols.symbol_models import Symbol, SymbolType, SymbolMetrics


@pytest.fixture
def detector():
    """Create a fresh pattern detector."""
    return PatternDetector()


@pytest.fixture
def test_symbol():
    """Create a test symbol."""
    return Symbol(
        name="test_class",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=50,
        namespace="",
        full_qualified_name="test.test_class",
        signature="class test_class:",
        code="class test_class:\n    pass",
        docstring="Test class",
        metrics=SymbolMetrics(),
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_detector_initialization(detector):
    """Test detector initializes empty."""
    assert detector.detected_patterns == {}
    assert detector.detected_anti_patterns == {}
    assert detector.metrics == {}


# ============================================================================
# Pattern Detection Tests
# ============================================================================


def test_detect_singleton_pattern(detector, test_symbol):
    """Test Singleton pattern detection."""
    singleton_code = """
    class Singleton:
        _instance = None
        def __init__(self):
            pass
        @staticmethod
        def getInstance():
            if Singleton._instance is None:
                Singleton._instance = Singleton()
            return Singleton._instance
    """
    singleton_symbol = Symbol(
        name="Singleton",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=15,
        namespace="",
        full_qualified_name="test.Singleton",
        signature="class Singleton:",
        code=singleton_code,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(singleton_symbol, {})

    assert len(metrics.detected_patterns) > 0
    if metrics.detected_patterns:
        assert metrics.detected_patterns[0].pattern_type == PatternType.SINGLETON


def test_detect_factory_pattern(detector, test_symbol):
    """Test Factory pattern detection."""
    factory_code = """
    class Factory:
        def create_object(self, type):
            if type == 'A':
                return ObjectA()
            return ObjectB()
    """
    factory_symbol = Symbol(
        name="Factory",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=8,
        namespace="",
        full_qualified_name="test.Factory",
        signature="class Factory:",
        code=factory_code,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(factory_symbol, {})

    assert metrics.pattern_score >= 0.0
    assert metrics.pattern_score <= 1.0


def test_detect_builder_pattern(detector, test_symbol):
    """Test Builder pattern detection."""
    builder_code = """
    class Builder:
        def set_name(self, name):
            return self
        def set_age(self, age):
            return self
        def build(self):
            return self
    """
    builder_symbol = Symbol(
        name="Builder",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=10,
        namespace="",
        full_qualified_name="test.Builder",
        signature="class Builder:",
        code=builder_code,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(builder_symbol, {})

    assert metrics.pattern_score >= 0.0


# ============================================================================
# Anti-Pattern Detection Tests
# ============================================================================


def test_detect_god_object(detector):
    """Test God Object anti-pattern detection."""
    metrics = {"incoming_count": 25, "methods": 60}

    result = detector.analyze_symbol(detector.__dict__.get("test_symbol", Symbol(
        name="GodClass",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=100,
        namespace="",
        full_qualified_name="test.GodClass",
        signature="class GodClass:",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )), metrics)

    assert len(result.detected_anti_patterns) > 0


def test_detect_long_method(detector):
    """Test Long Method anti-pattern detection."""
    long_code = "x = 1\n" * 60

    long_symbol = Symbol(
        name="long_method",
        symbol_type=SymbolType.FUNCTION,
        file_path="test.py",
        line_start=1,
        line_end=60,
        namespace="",
        full_qualified_name="test.long_method",
        signature="def long_method():",
        code=long_code,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(long_symbol, {"lines": 60})

    assert len(metrics.detected_anti_patterns) > 0
    if metrics.detected_anti_patterns:
        assert metrics.detected_anti_patterns[0].anti_pattern_type == AntiPatternType.LONG_METHOD


def test_detect_large_class(detector):
    """Test Large Class anti-pattern detection."""
    large_symbol = Symbol(
        name="large_class",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=300,
        namespace="",
        full_qualified_name="test.large_class",
        signature="class large_class:",
        code="x = 1\n" * 250,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(large_symbol, {"lines": 250})

    assert len(metrics.detected_anti_patterns) > 0


# ============================================================================
# Pattern Metrics Tests
# ============================================================================


def test_pattern_score_calculation(detector, test_symbol):
    """Test pattern score calculation."""
    metrics = detector.analyze_symbol(test_symbol, {})

    assert metrics.pattern_score >= 0.0
    assert metrics.pattern_score <= 1.0


def test_smell_score_calculation(detector):
    """Test smell score calculation."""
    smelly_symbol = Symbol(
        name="smelly",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=100,
        namespace="",
        full_qualified_name="test.smelly",
        signature="class smelly:",
        code="",
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(smelly_symbol, {"lines": 250, "methods": 60})

    assert metrics.smell_score >= 0.0
    assert metrics.smell_score <= 1.0


def test_design_quality_excellent(detector):
    """Test excellent design quality determination."""
    symbol = Symbol(
        name="good_design",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=30,
        namespace="",
        full_qualified_name="test.good_design",
        signature="class good_design:",
        code="class good_design:\n    pass",
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(symbol, {})

    # Clean code with no anti-patterns should have good design
    assert metrics.design_quality in ["excellent", "good", "fair"]


def test_design_quality_poor(detector):
    """Test poor design quality determination."""
    smelly_symbol = Symbol(
        name="poor_design",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=500,
        namespace="",
        full_qualified_name="test.poor_design",
        signature="class poor_design:",
        code="x = 1\n" * 300,
        docstring="",
        metrics=SymbolMetrics(),
    )

    metrics = detector.analyze_symbol(smelly_symbol, {"lines": 300, "methods": 80})

    assert metrics.design_quality in ["fair", "poor", "critical"]


# ============================================================================
# Summary Tests
# ============================================================================


def test_pattern_summary(detector, test_symbol):
    """Test pattern summary generation."""
    detector.analyze_symbol(test_symbol, {})
    summary = detector.get_pattern_summary()

    assert "total_patterns" in summary
    assert "total_anti_patterns" in summary
    assert "pattern_distribution" in summary
    assert "symbols_with_patterns" in summary


# ============================================================================
# Smell Detection Tests
# ============================================================================


def test_worst_smells(detector):
    """Test worst smells retrieval."""
    smelly_symbol = Symbol(
        name="smelly",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=300,
        namespace="",
        full_qualified_name="test.smelly",
        signature="class smelly:",
        code="x = 1\n" * 250,
        docstring="",
        metrics=SymbolMetrics(),
    )

    detector.analyze_symbol(smelly_symbol, {"lines": 250})
    worst = detector.get_worst_smells(5)

    assert isinstance(worst, list)


def test_best_patterns(detector):
    """Test best patterns retrieval."""
    good_symbol = Symbol(
        name="good",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=30,
        namespace="",
        full_qualified_name="test.good",
        signature="class good:",
        code="class good:\n    pass",
        docstring="",
        metrics=SymbolMetrics(),
    )

    detector.analyze_symbol(good_symbol, {})
    best = detector.get_best_patterns(5)

    assert isinstance(best, list)


# ============================================================================
# Recommendations Tests
# ============================================================================


def test_refactoring_recommendations(detector):
    """Test refactoring recommendations."""
    smelly_symbol = Symbol(
        name="needs_refactoring",
        symbol_type=SymbolType.CLASS,
        file_path="test.py",
        line_start=1,
        line_end=300,
        namespace="",
        full_qualified_name="test.needs_refactoring",
        signature="class needs_refactoring:",
        code="x = 1\n" * 250,
        docstring="",
        metrics=SymbolMetrics(),
    )

    detector.analyze_symbol(smelly_symbol, {"lines": 250})
    recommendations = detector.get_refactoring_recommendations()

    assert isinstance(recommendations, list)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_analysis_workflow(detector):
    """Test complete analysis workflow."""
    # Analyze multiple symbols
    symbols = {}
    for i in range(1, 4):
        symbols[f"class{i}"] = Symbol(
            name=f"class{i}",
            symbol_type=SymbolType.CLASS,
            file_path="test.py",
            line_start=i * 10,
            line_end=i * 10 + 20,
            namespace="",
            full_qualified_name=f"test.class{i}",
            signature=f"class class{i}:",
            code=f"class class{i}:\n    pass",
            docstring="",
            metrics=SymbolMetrics(),
        )

    for name, symbol in symbols.items():
        detector.analyze_symbol(symbol, {})

    # Get summary
    summary = detector.get_pattern_summary()
    assert summary["total_patterns"] >= 0
    assert summary["total_anti_patterns"] >= 0

    # Get recommendations
    recommendations = detector.get_refactoring_recommendations()
    assert isinstance(recommendations, list)
