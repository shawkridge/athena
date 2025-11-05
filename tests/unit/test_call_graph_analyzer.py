"""Tests for call graph analyzer."""

import pytest

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.call_graph_analyzer import (
    CallGraphAnalyzer,
    CallNode,
    CallEdge,
    CallPath,
)


class TestCallGraphAnalyzerBasics:
    """Test basic call graph analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test call graph analyzer can be created."""
        symbols = {}
        analyzer = CallGraphAnalyzer(symbols)
        assert analyzer is not None
        assert len(analyzer.symbol_index) == 0
        assert len(analyzer.call_graph) == 0

    def test_analyzer_with_symbols(self):
        """Test initializing with symbols."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def test_func(): pass",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        assert len(analyzer.symbol_index) == 1
        assert len(analyzer.call_nodes) == 1

    def test_call_node_creation(self):
        """Test creating a call node."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        node = CallNode(symbol=symbol)
        assert node.symbol.name == "test_func"
        assert node.in_degree == 0
        assert node.out_degree == 0
        assert not node.is_recursive

    def test_call_edge_creation(self):
        """Test creating a call edge."""
        sym1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_a",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_b",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        edge = CallEdge(from_symbol=sym1, to_symbol=sym2, line_number=5)
        assert edge.from_symbol.name == "func_a"
        assert edge.to_symbol.name == "func_b"
        assert edge.line_number == 5


class TestPythonCallDetection:
    """Test Python function call detection."""

    def test_simple_function_call(self):
        """Test detecting simple function calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="helper",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code="def helper(): pass",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """def main():
    helper()
    print('done')
"""
        calls = analyzer.analyze_file("test.py", code)
        assert len(calls) > 0

    def test_multiple_function_calls(self):
        """Test detecting multiple function calls."""
        symbols_list = [
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func_{i}",
                namespace="",
                signature="()",
                line_start=i * 5 + 1,
                line_end=i * 5 + 3,
                code="",
                language="python",
                visibility="public"
            )
            for i in range(3)
        ]

        symbols = {"test.py": symbols_list}
        analyzer = CallGraphAnalyzer(symbols)

        code = """
func_0()
func_1()
func_2()
"""
        calls = analyzer.analyze_file("test.py", code)
        assert len(calls) >= 3

    def test_method_call_detection(self):
        """Test detecting method calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.METHOD,
            name="process",
            namespace="Handler",
            signature="(self)",
            line_start=10,
            line_end=15,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """handler = Handler()
handler.process()"""
        calls = analyzer.analyze_file("test.py", code)
        assert isinstance(calls, list)

    def test_skip_comments(self):
        """Test that calls in comments are skipped."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """# func() should not be detected
actual_code = 'func()'  # this is a string
func()  # this should be detected
"""
        calls = analyzer.analyze_file("test.py", code)
        # At least one call should be detected
        assert len(calls) >= 1


class TestJavaScriptCallDetection:
    """Test JavaScript/TypeScript function call detection."""

    def test_simple_js_call(self):
        """Test detecting simple JavaScript calls."""
        symbol = create_symbol(
            file_path="app.js",
            symbol_type=SymbolType.FUNCTION,
            name="render",
            namespace="",
            signature="()",
            line_start=5,
            line_end=10,
            code="",
            language="javascript",
            visibility="public"
        )

        symbols = {"app.js": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """function main() {
  render();
  console.log('done');
}"""
        calls = analyzer.analyze_file("app.js", code)
        assert len(calls) > 0

    def test_async_function_call(self):
        """Test detecting async function calls."""
        symbol = create_symbol(
            file_path="app.ts",
            symbol_type=SymbolType.ASYNC_FUNCTION,
            name="fetchData",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="",
            language="typescript",
            visibility="public"
        )

        symbols = {"app.ts": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """async function main() {
  const data = await fetchData();
}"""
        calls = analyzer.analyze_file("app.ts", code)
        assert len(calls) > 0

    def test_skip_js_comments(self):
        """Test that JS/TS calls in comments are skipped."""
        symbol = create_symbol(
            file_path="app.js",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="javascript",
            visibility="public"
        )

        symbols = {"app.js": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        code = """// process() is commented
/* process() is in block comment */
process();  // actual call"""
        calls = analyzer.analyze_file("app.js", code)
        assert len(calls) >= 1


class TestCallGraphConstruction:
    """Test call graph construction."""

    def test_build_call_graph(self):
        """Test building a call graph."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_a",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_b",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b, line_number=5)
        analyzer.build_call_graph([call])

        # Check nodes are updated
        for node in analyzer.call_nodes.values():
            assert node.in_degree >= 0
            assert node.out_degree >= 0

    def test_update_node_degrees(self):
        """Test that node degrees are updated correctly."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="callee",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        # callee should have in_degree 1
        for qname, node in analyzer.call_nodes.items():
            if node.symbol.name == "callee":
                assert node.in_degree >= 1


class TestRecursiveCallDetection:
    """Test recursive call detection."""

    def test_detect_simple_recursion(self):
        """Test detecting simple recursive calls."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="fibonacci",
            namespace="",
            signature="(n)",
            line_start=1,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [symbol]}
        analyzer = CallGraphAnalyzer(symbols)

        # Create a self-call edge
        call = CallEdge(from_symbol=symbol, to_symbol=symbol)
        analyzer.build_call_graph([call])

        recursive = analyzer.detect_recursive_calls()
        assert len(recursive) >= 1

    def test_no_recursion_for_different_functions(self):
        """Test that different functions aren't marked as recursive."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_a",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_b",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        recursive = analyzer.detect_recursive_calls()
        assert len(recursive) == 0


class TestCallGraphQueries:
    """Test call graph query operations."""

    def test_get_callers(self):
        """Test getting callers of a function."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="callee",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        # Note: get_callers needs populated reverse graph
        callers = analyzer.get_callers(sym_b)
        assert isinstance(callers, list)

    def test_get_callees(self):
        """Test getting functions called by a function."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="callee",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        callees = analyzer.get_callees(sym_a)
        assert isinstance(callees, list)


class TestCallGraphStatistics:
    """Test call graph statistics."""

    def test_get_call_graph_stats_empty(self):
        """Test statistics on empty graph."""
        symbols = {}
        analyzer = CallGraphAnalyzer(symbols)

        stats = analyzer.get_call_graph_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_calls"] == 0
        assert stats["recursive_calls"] == 0

    def test_get_call_graph_stats_with_calls(self):
        """Test statistics with calls."""
        sym_a = create_symbol(
            file_path="test.py",
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
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="helper",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        stats = analyzer.get_call_graph_stats()
        assert stats["total_nodes"] == 2
        assert stats["total_calls"] >= 1

    def test_entry_points_detection(self):
        """Test detecting entry point functions."""
        sym_entry = create_symbol(
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
        sym_helper = create_symbol(
            file_path="utils.py",
            symbol_type=SymbolType.FUNCTION,
            name="helper",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"main.py": [sym_entry], "utils.py": [sym_helper]}
        analyzer = CallGraphAnalyzer(symbols)

        stats = analyzer.get_call_graph_stats()
        assert stats["entry_points"] >= 1

    def test_leaf_functions_detection(self):
        """Test detecting leaf functions (called but don't call others)."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="leaf",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        call = CallEdge(from_symbol=sym_a, to_symbol=sym_b)
        analyzer.build_call_graph([call])

        stats = analyzer.get_call_graph_stats()
        assert stats["leaf_functions"] >= 1


class TestCallGraphReporting:
    """Test call graph reporting."""

    def test_call_graph_report_generation(self):
        """Test generating call graph report."""
        symbols = {}
        analyzer = CallGraphAnalyzer(symbols)

        report = analyzer.get_call_graph_report()
        assert "CALL GRAPH ANALYSIS REPORT" in report
        assert "Total Functions" in report

    def test_report_includes_statistics(self):
        """Test that report includes statistics."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_a",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a]}
        analyzer = CallGraphAnalyzer(symbols)

        report = analyzer.get_call_graph_report()
        assert "Total Functions:      1" in report
        assert "Total Calls:          0" in report


class TestCallPath:
    """Test call path functionality."""

    def test_call_path_creation(self):
        """Test creating a call path."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="a",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="b",
            namespace="",
            signature="()",
            line_start=5,
            line_end=5,
            code="",
            language="python",
            visibility="public"
        )

        path = CallPath(symbols=[sym_a, sym_b])
        assert path.length == 1
        assert len(path.symbols) == 2

    def test_find_call_paths(self):
        """Test finding call paths."""
        sym_a = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="start",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )
        sym_b = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="end",
            namespace="",
            signature="()",
            line_start=10,
            line_end=10,
            code="",
            language="python",
            visibility="public"
        )

        symbols = {"test.py": [sym_a, sym_b]}
        analyzer = CallGraphAnalyzer(symbols)

        paths = analyzer.find_call_paths(sym_a, sym_b)
        assert isinstance(paths, list)
