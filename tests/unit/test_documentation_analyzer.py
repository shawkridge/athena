"""Tests for documentation analyzer."""

import pytest

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.documentation_analyzer import (
    DocumentationAnalyzer,
    DocumentationMetrics,
    DocumentationQuality,
    DocumentationViolation,
)


class TestDocumentationAnalyzerBasics:
    """Test basic documentation analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test documentation analyzer can be created."""
        analyzer = DocumentationAnalyzer()
        assert analyzer is not None
        assert len(analyzer.metrics) == 0
        assert len(analyzer.violations) == 0

    def test_analyze_undocumented_symbol(self):
        """Test analyzing symbol without docstring."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="no_doc",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def no_doc():\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert not metrics.has_docstring
        assert metrics.quality_grade == DocumentationQuality.MISSING
        assert metrics.quality_score == 0.0


class TestDocstringDetection:
    """Test docstring presence detection."""

    def test_detect_simple_docstring(self):
        """Test detecting simple docstring."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="documented",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code='def documented():\n    """Simple docstring."""\n    pass',
            language="python",
            visibility="public",
            docstring="Simple docstring."
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_docstring
        assert metrics.has_summary

    def test_detect_multiline_docstring(self):
        """Test detecting multi-line docstring."""
        docstring = """Process data.

        This function processes the input data and returns results.
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(data)",
            line_start=1,
            line_end=10,
            code="def process(data):\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_docstring
        assert metrics.has_summary
        assert metrics.has_description


class TestParameterDocumentation:
    """Test parameter documentation detection."""

    def test_detect_parameter_documentation(self):
        """Test detecting parameter documentation."""
        docstring = """Process values.

        Args:
            x: First value
            y: Second value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="add",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=10,
            code="def add(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_parameters
        assert metrics.total_parameters == 2
        assert metrics.documented_parameters == 2
        assert metrics.parameter_coverage == 1.0

    def test_partial_parameter_documentation(self):
        """Test detecting partial parameter documentation."""
        docstring = """Process values.

        Args:
            x: First value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="add",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=10,
            code="def add(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.total_parameters == 2
        assert metrics.documented_parameters == 1
        assert metrics.parameter_coverage == 0.5

    def test_no_parameters_no_documentation_needed(self):
        """Test function with no parameters needs no parameter docs."""
        docstring = """Get constant value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_constant",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_constant():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.total_parameters == 0
        assert metrics.parameter_coverage == 1.0

    def test_exclude_self_from_parameters(self):
        """Test that 'self' is excluded from parameter count."""
        docstring = """Get value.

        Args:
            x: Input value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.METHOD,
            name="get_value",
            namespace="TestClass",
            signature="(self, x)",
            line_start=10,
            line_end=15,
            code="def get_value(self, x):\n    return x",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        # self should be excluded, so only x is counted
        assert metrics.total_parameters == 1
        assert metrics.documented_parameters == 1


class TestReturnDocumentation:
    """Test return type documentation detection."""

    def test_detect_return_documentation(self):
        """Test detecting return documentation."""
        docstring = """Get value.

        Returns:
            int: The computed value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_value",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_value():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_return_type
        assert metrics.has_return_description

    def test_missing_return_documentation(self):
        """Test detecting missing return documentation."""
        docstring = """Get value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="get_value",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def get_value():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert not metrics.has_return_type


class TestExampleDetection:
    """Test code example detection."""

    def test_detect_doctest_examples(self):
        """Test detecting doctest examples with >>>."""
        docstring = """Process value.

        Examples:
            >>> process(5)
            10
            >>> process(3)
            6
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=10,
            code="def process(x):\n    return x * 2",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_examples
        assert metrics.example_count > 0

    def test_detect_code_block_examples(self):
        """Test detecting code block examples with ```."""
        docstring = """Process value.

        Examples:
            ```python
            result = process(5)
            print(result)
            ```
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=10,
            code="def process(x):\n    return x * 2",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_examples

    def test_missing_examples(self):
        """Test detecting missing examples."""
        docstring = """Process value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def process(x):\n    return x",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert not metrics.has_examples
        assert metrics.example_count == 0


class TestRaisesDocumentation:
    """Test exception documentation detection."""

    def test_detect_raises_documentation(self):
        """Test detecting raises documentation."""
        docstring = """Process value.

        Args:
            x: Input value

        Returns:
            Processed value

        Raises:
            ValueError: If x is negative
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=10,
            code="def process(x):\n    if x < 0:\n        raise ValueError()",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_raises

    def test_missing_raises_documentation(self):
        """Test detecting missing raises documentation."""
        docstring = """Process value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code="def process(x):\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert not metrics.has_raises


class TestQualityScoring:
    """Test documentation quality scoring."""

    def test_minimal_docstring_low_score(self):
        """Test minimal docstring gets low score."""
        docstring = """Do something."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="do_something",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=5,
            code="def do_something(x, y):\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.quality_score < 50

    def test_comprehensive_docstring_high_score(self):
        """Test comprehensive docstring gets high score."""
        docstring = """Process values and return result.

        This function takes two values and processes them through several
        computational steps before returning the result.

        Args:
            x: First numerical value
            y: Second numerical value

        Returns:
            int: The processed result

        Raises:
            ValueError: If inputs are negative

        Examples:
            >>> process(5, 10)
            15
            >>> process(3, 7)
            10
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=20,
            code="def process(x, y):\n    if x < 0 or y < 0:\n        raise ValueError()\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.quality_score > 80

    def test_quality_grade_assignment(self):
        """Test quality grade assignment."""
        analyzer = DocumentationAnalyzer()

        # Excellent (>=85)
        assert analyzer._grade_quality(90.0, True) == DocumentationQuality.EXCELLENT

        # Good (70-84)
        assert analyzer._grade_quality(75.0, True) == DocumentationQuality.GOOD

        # Adequate (50-69)
        assert analyzer._grade_quality(60.0, True) == DocumentationQuality.ADEQUATE

        # Incomplete (<50)
        assert analyzer._grade_quality(30.0, True) == DocumentationQuality.INCOMPLETE

        # Missing (no docstring)
        assert analyzer._grade_quality(0.0, False) == DocumentationQuality.MISSING


class TestViolationDetection:
    """Test documentation violation detection."""

    def test_public_undocumented_function_violation(self):
        """Test undocumented public function is critical violation."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="public_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def public_func():\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        violations = analyzer.get_violations(severity="critical")
        assert len(violations) > 0

    def test_private_undocumented_no_violation(self):
        """Test undocumented private function has no violation."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="_private_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def _private_func():\n    pass",
            language="python",
            visibility="private"
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        violations = analyzer.get_violations(severity="critical")
        assert len(violations) == 0


class TestDocumentationQueries:
    """Test querying documentation results."""

    def test_get_undocumented_symbols(self):
        """Test getting undocumented symbols."""
        analyzer = DocumentationAnalyzer()

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="documented",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def documented():\n    pass",
            language="python",
            visibility="public",
            docstring="Documented function."
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="undocumented",
            namespace="",
            signature="()",
            line_start=10,
            line_end=15,
            code="def undocumented():\n    pass",
            language="python",
            visibility="public"
        )

        analyzer.analyze_symbol(symbol1)
        analyzer.analyze_symbol(symbol2)

        undocumented = analyzer.get_undocumented_symbols()
        assert len(undocumented) >= 1

    def test_get_incomplete_documentation(self):
        """Test getting symbols with incomplete documentation."""
        docstring = """Do something."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="incomplete",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=5,
            code="def incomplete(x, y):\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        incomplete = analyzer.get_incomplete_documentation(quality_threshold=70.0)
        assert len(incomplete) > 0

    def test_get_well_documented_symbols(self):
        """Test getting well documented symbols."""
        docstring = """Process values and return result.

        Args:
            x: First value
            y: Second value

        Returns:
            int: The result

        Examples:
            >>> process(1, 2)
            3
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="well_documented",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=15,
            code="def well_documented(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        well_doc = analyzer.get_well_documented_symbols(quality_threshold=70.0)
        assert len(well_doc) > 0

    def test_get_missing_parameter_docs(self):
        """Test getting symbols with missing parameter docs."""
        docstring = """Add values.

        Args:
            x: First value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="add",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=5,
            code="def add(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        missing = analyzer.get_missing_parameter_docs()
        assert len(missing) > 0

    def test_get_missing_return_docs(self):
        """Test getting functions with missing return docs."""
        docstring = """Compute value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="compute",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def compute():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        missing = analyzer.get_missing_return_docs()
        assert len(missing) > 0


class TestCoverageStats:
    """Test coverage statistics calculation."""

    def test_coverage_stats(self):
        """Test calculating coverage statistics."""
        analyzer = DocumentationAnalyzer()

        symbols = [
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name="f1",
                namespace="",
                signature="()",
                line_start=1,
                line_end=5,
                code="def f1():\n    pass",
                language="python",
                visibility="public",
                docstring="First function."
            ),
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name="f2",
                namespace="",
                signature="()",
                line_start=10,
                line_end=15,
                code="def f2():\n    pass",
                language="python",
                visibility="public"
            ),
        ]

        for symbol in symbols:
            analyzer.analyze_symbol(symbol)

        stats = analyzer.get_coverage_stats()

        assert stats["total_symbols"] == 2
        assert stats["documented"] == 1
        assert stats["undocumented"] == 1
        assert stats["coverage"] == 0.5


class TestDocumentationReport:
    """Test report generation."""

    def test_generate_documentation_report(self):
        """Test generating documentation report."""
        analyzer = DocumentationAnalyzer()

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def test():\n    pass",
            language="python",
            visibility="public",
            docstring="Test function."
        )

        analyzer.analyze_symbol(symbol)

        report = analyzer.get_documentation_report()

        assert isinstance(report, str)
        assert len(report) > 0
        assert "DOCUMENTATION COVERAGE REPORT" in report


class TestImprovementSuggestions:
    """Test improvement suggestions."""

    def test_suggest_improvements_no_docstring(self):
        """Test suggestions for undocumented function."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="no_doc",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=5,
            code="def no_doc(x, y):\n    pass",
            language="python",
            visibility="public"
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        suggestions = analyzer.suggest_improvements(symbol)

        assert len(suggestions) > 0
        assert any("docstring" in s.lower() for s in suggestions)

    def test_suggest_improvements_missing_params(self):
        """Test suggestions for missing parameter docs."""
        docstring = """Add values.

        Args:
            x: First value
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="add",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=5,
            code="def add(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        suggestions = analyzer.suggest_improvements(symbol)

        assert len(suggestions) > 0
        assert any("parameter" in s.lower() for s in suggestions)

    def test_suggest_improvements_missing_return(self):
        """Test suggestions for missing return docs."""
        docstring = """Compute value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="compute",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def compute():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        suggestions = analyzer.suggest_improvements(symbol)

        assert len(suggestions) > 0
        assert any("return" in s.lower() for s in suggestions)

    def test_suggest_improvements_missing_examples(self):
        """Test suggestions for missing examples."""
        docstring = """Compute value."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="compute",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def compute():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        analyzer.analyze_symbol(symbol)

        suggestions = analyzer.suggest_improvements(symbol)

        assert len(suggestions) > 0


class TestSpecialCases:
    """Test special cases and edge conditions."""

    def test_analyze_class_with_docstring(self):
        """Test analyzing class with docstring."""
        docstring = """Test class for demonstration."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="TestClass",
            namespace="",
            signature="",
            line_start=1,
            line_end=10,
            code="class TestClass:\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_docstring

    def test_analyze_async_function(self):
        """Test analyzing async function."""
        docstring = """Async operation.

        Returns:
            Result of async operation
        """
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.ASYNC_FUNCTION,
            name="async_op",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="async def async_op():\n    return 42",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_docstring

    def test_docstring_with_special_characters(self):
        """Test docstring with special characters."""
        docstring = """Process @values with #special $chars."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="special",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def special():\n    pass",
            language="python",
            visibility="public",
            docstring=docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics = analyzer.analyze_symbol(symbol)

        assert metrics.has_docstring
        assert metrics.has_summary

    def test_long_docstring_bonus(self):
        """Test that longer comprehensive docstrings get bonus points."""
        short_docstring = """Short."""
        long_docstring = """Process values with comprehensive documentation.

        This function takes input values and processes them through multiple
        computational steps to produce the final result. It includes detailed
        descriptions of all parameters, return values, and potential exceptions.

        Args:
            x: First value to process
            y: Second value to process

        Returns:
            The processed result

        Raises:
            ValueError: If inputs are invalid

        Examples:
            >>> compute(1, 2)
            3
        """

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="short",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def short():\n    pass",
            language="python",
            visibility="public",
            docstring=short_docstring
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="long",
            namespace="",
            signature="(x, y)",
            line_start=10,
            line_end=25,
            code="def long(x, y):\n    return x + y",
            language="python",
            visibility="public",
            docstring=long_docstring
        )

        analyzer = DocumentationAnalyzer()
        metrics1 = analyzer.analyze_symbol(symbol1)
        metrics2 = analyzer.analyze_symbol(symbol2)

        # Longer docstring should have higher score
        assert metrics2.quality_score > metrics1.quality_score
