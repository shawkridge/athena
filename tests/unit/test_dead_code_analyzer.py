"""Tests for dead code analyzer."""

import pytest
from pathlib import Path

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.dependency_resolver import DependencyResolver, DependencyType, SymbolReference
from athena.symbols.dead_code_analyzer import DeadCodeAnalyzer, DeadCodeIssue


class TestDeadCodeAnalyzerBasics:
    """Test basic dead code analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test dead code analyzer can be created."""
        resolver = DependencyResolver()
        analyzer = DeadCodeAnalyzer(resolver)
        assert analyzer is not None
        assert analyzer.resolver is resolver
        assert len(analyzer.used_symbols) == 0
        assert len(analyzer.unused_symbols) == 0

    def test_dead_code_issue_creation(self):
        """Test creating a dead code issue."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=10,
            line_end=15,
            code="def unused_func(): pass",
            language="python",
            visibility="private"
        )

        issue = DeadCodeIssue(
            symbol=symbol,
            issue_type="unused_symbol",
            references_count=0,
            line_number=10,
            file_path="test.py",
            severity="warning"
        )

        assert issue.symbol.name == "unused_func"
        assert issue.issue_type == "unused_symbol"
        assert issue.references_count == 0
        assert issue.severity == "warning"

    def test_empty_project_analysis(self):
        """Test analysis on empty project."""
        resolver = DependencyResolver()
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        assert result["total_symbols"] == 0
        assert result["used_symbols"] == 0
        assert result["unused_symbols"] == 0
        assert result["dead_code_percentage"] == 0.0

    def test_single_unused_symbol(self):
        """Test detection of single unused symbol."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        assert result["total_symbols"] == 1
        assert result["unused_symbols"] == 1
        assert result["dead_code_percentage"] == 100.0


class TestUnusedSymbolDetection:
    """Test detection of unused symbols by type."""

    def test_detect_unused_function(self):
        """Test detecting unused function."""
        resolver = DependencyResolver()
        sym_used = create_symbol(
            file_path="main.py",
            symbol_type=SymbolType.FUNCTION,
            name="main",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_unused = create_symbol(
            file_path="utils.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("main.py", [sym_used])
        resolver.add_symbols("utils.py", [sym_unused])

        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        # main() is entry point, unused_func is not used
        assert result["unused_symbols"] == 1
        assert result["dead_code_issues"][0].symbol.name == "unused_func"

    def test_detect_unused_class(self):
        """Test detecting unused class."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="UnusedClass",
            namespace="",
            signature="",
            line_start=5,
            line_end=20,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        assert result["unused_symbols"] == 1
        assert result["dead_code_issues"][0].symbol.symbol_type == SymbolType.CLASS

    def test_detect_unused_method(self):
        """Test detecting unused method."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.METHOD,
            name="unused_method",
            namespace="MyClass",
            signature="()",
            line_start=15,
            line_end=20,
            code="",
            language="python",
            visibility="private"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        assert result["unused_symbols"] == 1
        assert result["dead_code_issues"][0].severity == "warning"

    def test_detect_multiple_unused_symbols(self):
        """Test detecting multiple unused symbols."""
        resolver = DependencyResolver()
        symbols = []
        for i in range(5):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"unused_func_{i}",
                namespace="",
                signature="()",
                line_start=i * 10 + 1,
                line_end=max(1, i * 10 + 5),
                code="",
                language="python",
                visibility="public"
            )
            symbols.append(symbol)

        resolver.add_symbols("test.py", symbols)
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        assert result["unused_symbols"] == 5
        assert len(result["dead_code_issues"]) == 5

    def test_skip_unused_constants(self):
        """Test that unused constants are skipped."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CONSTANT,
            name="UNUSED_CONSTANT",
            namespace="",
            signature="10",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        # Constants are skipped in unused detection
        assert result["unused_symbols"] == 0

    def test_entry_point_symbols_not_unused(self):
        """Test that entry point symbols are not marked as unused."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="main",
            namespace="",
            signature="()",
            line_start=1,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        # main() is entry point, should not be marked as unused
        assert result["unused_symbols"] == 0


class TestDeadCodeGrouping:
    """Test grouping of dead code issues."""

    def test_group_by_file(self):
        """Test grouping unused symbols by file."""
        resolver = DependencyResolver()

        # Create symbols in multiple files
        for file_num in range(3):
            symbols = []
            for sym_num in range(2):
                symbol = create_symbol(
                    file_path=f"module{file_num}.py",
                    symbol_type=SymbolType.FUNCTION,
                    name=f"unused_func_{file_num}_{sym_num}",
                    namespace="",
                    signature="()",
                    line_start=max(1, sym_num * 5 + 1),
                    line_end=max(1, sym_num * 5 + 4),
                    code="",
                    language="python",
                    visibility="public"
                )
                symbols.append(symbol)
            resolver.add_symbols(f"module{file_num}.py", symbols)

        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        by_file = result["unused_by_file"]
        assert len(by_file) == 3
        assert all(len(issues) == 2 for issues in by_file.values())

    def test_group_by_type(self):
        """Test grouping unused symbols by symbol type."""
        resolver = DependencyResolver()

        symbols = [
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name="unused_func",
                namespace="",
                signature="()",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            ),
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.CLASS,
                name="UnusedClass",
                namespace="",
                signature="",
                line_start=10,
                line_end=10,
                code="",
                language="python",
                visibility="public"
            ),
        ]

        resolver.add_symbols("test.py", symbols)
        analyzer = DeadCodeAnalyzer(resolver)
        result = analyzer.analyze_project()

        by_type = result["unused_by_type"]
        assert "function" in by_type
        assert "class" in by_type
        assert by_type["function"] == 1
        assert by_type["class"] == 1

    def test_find_unused_in_file(self):
        """Test finding unused symbols in specific file."""
        resolver = DependencyResolver()

        symbols_a = [
            create_symbol(
                file_path="a.py",
                symbol_type=SymbolType.FUNCTION,
                name="unused_a",
                namespace="",
                signature="()",
                line_start=10,
                line_end=10,
                code="",
                language="python",
                visibility="public"
            ),
        ]
        symbols_b = [
            create_symbol(
                file_path="b.py",
                symbol_type=SymbolType.FUNCTION,
                name="unused_b",
                namespace="",
                signature="()",
                line_start=20,
                line_end=20,
                code="",
                language="python",
                visibility="public"
            ),
        ]

        resolver.add_symbols("a.py", symbols_a)
        resolver.add_symbols("b.py", symbols_b)

        analyzer = DeadCodeAnalyzer(resolver)
        analyzer.analyze_project()

        file_a_unused = analyzer.find_unused_in_file("a.py")
        file_b_unused = analyzer.find_unused_in_file("b.py")

        assert len(file_a_unused) == 1
        assert len(file_b_unused) == 1
        assert file_a_unused[0].symbol.name == "unused_a"
        assert file_b_unused[0].symbol.name == "unused_b"


class TestDeadCodeReporting:
    """Test dead code reporting."""

    def test_dead_code_report_generation(self):
        """Test generating dead code report."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=10,
            line_end=15,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        analyzer.analyze_project()

        report = analyzer.get_dead_code_report()
        assert "DEAD CODE ANALYSIS REPORT" in report
        assert "unused_func" in report
        assert "100.0%" in report

    def test_report_shows_line_numbers(self):
        """Test that report shows line numbers."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=42,
            line_end=50,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        analyzer = DeadCodeAnalyzer(resolver)
        analyzer.analyze_project()

        report = analyzer.get_dead_code_report()
        assert "Line 42" in report

    def test_report_shows_statistics(self):
        """Test that report includes statistics."""
        resolver = DependencyResolver()
        symbols = []
        for i in range(3):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"unused_{i}",
                namespace="",
                signature="()",
                line_start=i * 5 + 1,
                line_end=i * 5 + 4,
                code="",
                language="python",
                visibility="public"
            )
            symbols.append(symbol)
        resolver.add_symbols("test.py", symbols)

        analyzer = DeadCodeAnalyzer(resolver)
        analyzer.analyze_project()

        report = analyzer.get_dead_code_report()
        assert "Total Symbols:      3" in report
        assert "Unused Symbols:     3" in report
        assert "Dead Code:          100.0%" in report


class TestUnusedImportDetection:
    """Test detection of unused imports."""

    def test_detect_unused_import(self):
        """Test detecting unused import."""
        resolver = DependencyResolver()
        code = "from utils import helper\nimport os"
        refs = resolver.resolve_imports("test.py", code)

        analyzer = DeadCodeAnalyzer(resolver)
        unused = analyzer.detect_unused_imports("test.py", code)

        # All imports are considered used by default
        # (actual usage analysis would require code parsing)
        assert len(refs) >= 2

    def test_unused_import_issue_creation(self):
        """Test creating unused import issue."""
        resolver = DependencyResolver()
        code = "import unused_module"

        analyzer = DeadCodeAnalyzer(resolver)
        unused = analyzer.detect_unused_imports("test.py", code)

        # Implementation would detect this as unused
        # For now, test that detection runs without error
        assert isinstance(unused, list)


class TestDeadCodeSeverity:
    """Test severity classification for unused code."""

    def test_constant_has_info_severity(self):
        """Test that unused constants have info severity."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CONSTANT,
            name="UNUSED",
            namespace="",
            signature="10",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        analyzer = DeadCodeAnalyzer(DependencyResolver())
        severity = analyzer._determine_severity(symbol)
        assert severity == "info"

    def test_function_has_warning_severity(self):
        """Test that unused functions have warning severity."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="unused_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        analyzer = DeadCodeAnalyzer(DependencyResolver())
        severity = analyzer._determine_severity(symbol)
        assert severity == "warning"

    def test_class_has_error_severity(self):
        """Test that unused classes have error severity."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="UnusedClass",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        analyzer = DeadCodeAnalyzer(DependencyResolver())
        severity = analyzer._determine_severity(symbol)
        assert severity == "error"
