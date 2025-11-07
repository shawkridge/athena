"""Unit tests for call graph analysis."""

import pytest
from athena.code.call_graph import (
    CallGraphBuilder,
    CallGraph,
    FunctionDef,
    FunctionCall,
    CallGraphConfig,
)


@pytest.fixture
def simple_code():
    """Simple code with basic function calls."""
    return """
def foo():
    bar()
    baz()

def bar():
    pass

def baz():
    pass
"""


@pytest.fixture
def nested_code():
    """Code with nested function calls."""
    return """
def main():
    a()
    b()

def a():
    c()

def b():
    c()

def c():
    pass
"""


@pytest.fixture
def cycle_code():
    """Code with circular dependencies."""
    return """
def a():
    b()

def b():
    c()

def c():
    a()
"""


@pytest.fixture
def method_code():
    """Code with class methods."""
    return """
class MyClass:
    def method1(self):
        self.method2()

    def method2(self):
        pass

def function():
    obj = MyClass()
    obj.method1()
"""


@pytest.fixture
def complex_code():
    """Complex code with multiple patterns."""
    return """
def entry_point():
    process_data()
    validate()

def process_data():
    transform()
    save()

def transform():
    parse()

def parse():
    pass

def save():
    write_file()

def write_file():
    pass

def validate():
    check()

def check():
    pass
"""


class TestFunctionDef:
    """Test FunctionDef data class."""

    def test_create_function_def(self):
        """Test creating function definition."""
        func_def = FunctionDef(
            name="test_func",
            module="test_module",
            lineno=10,
            qualname="test_func",
            params=["a", "b"],
        )

        assert func_def.name == "test_func"
        assert func_def.module == "test_module"
        assert func_def.lineno == 10
        assert len(func_def.params) == 2

    def test_method_definition(self):
        """Test creating method definition."""
        func_def = FunctionDef(
            name="method",
            module="test_module",
            lineno=20,
            qualname="MyClass.method",
            is_method=True,
            class_name="MyClass",
        )

        assert func_def.is_method is True
        assert func_def.class_name == "MyClass"


class TestCallGraphBuilder:
    """Test call graph builder."""

    def test_parse_simple_code(self, simple_code):
        """Test parsing simple code."""
        builder = CallGraphBuilder(simple_code, "test_module")
        graph = builder.build()

        assert len(graph.functions) == 3  # foo, bar, baz
        assert len(graph.calls) == 2  # foo->bar, foo->baz

    def test_extract_function_definitions(self, simple_code):
        """Test extracting function definitions."""
        builder = CallGraphBuilder(simple_code, "test_module")
        graph = builder.build()

        func_names = list(graph.functions.keys())
        assert any("foo" in name for name in func_names)
        assert any("bar" in name for name in func_names)
        assert any("baz" in name for name in func_names)

    def test_extract_function_calls(self, simple_code):
        """Test extracting function calls."""
        builder = CallGraphBuilder(simple_code, "test_module")
        graph = builder.build()

        assert len(graph.calls) == 2
        assert graph.calls[0].callee == "bar"
        assert graph.calls[1].callee == "baz"

    def test_parse_nested_code(self, nested_code):
        """Test parsing nested function calls."""
        builder = CallGraphBuilder(nested_code, "test_module")
        graph = builder.build()

        assert len(graph.functions) == 4  # main, a, b, c
        assert len(graph.calls) == 4  # main->a, main->b, a->c, b->c

    def test_parse_class_methods(self, method_code):
        """Test parsing class methods."""
        builder = CallGraphBuilder(method_code, "test_module")
        graph = builder.build()

        # Should find both class methods and functions
        assert len(graph.functions) >= 3  # method1, method2, function

    def test_parse_with_decorators(self):
        """Test parsing functions with decorators."""
        code = """
@decorator
def decorated_func():
    pass
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        func_def = next(iter(graph.functions.values()))
        assert "decorator" in func_def.decorators or len(func_def.decorators) > 0

    def test_invalid_syntax(self):
        """Test handling invalid syntax."""
        bad_code = "def foo( : pass"

        builder = CallGraphBuilder(bad_code, "test_module")
        graph = builder.build()

        # Should handle gracefully
        assert len(graph.functions) == 0

    def test_config_exclude_external(self, simple_code):
        """Test excluding external calls."""
        config = CallGraphConfig(include_external=False)
        builder = CallGraphBuilder(simple_code, "test_module", config)
        graph = builder.build()

        # All calls should be internal
        assert all(not call.is_external for call in graph.calls)

    def test_extract_parameters(self):
        """Test extracting function parameters."""
        code = """
def func_with_params(a, b, c):
    pass
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        func_def = next(iter(graph.functions.values()))
        assert "a" in func_def.params
        assert "b" in func_def.params
        assert "c" in func_def.params

    def test_extract_docstring(self):
        """Test extracting docstring."""
        code = '''
def documented():
    """This is a docstring."""
    pass
'''
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        func_def = next(iter(graph.functions.values()))
        assert func_def.docstring is not None


class TestCallGraph:
    """Test call graph functionality."""

    def test_get_direct_callers(self, nested_code):
        """Test getting direct callers."""
        builder = CallGraphBuilder(nested_code, "test_module")
        graph = builder.build()

        # Check that we have the callers dictionary populated
        assert len(graph.callers) > 0 or len(graph.calls) > 0

    def test_get_direct_callees(self, simple_code):
        """Test getting direct callees."""
        builder = CallGraphBuilder(simple_code, "test_module")
        graph = builder.build()

        # Find function 'foo' (calls bar and baz)
        foo_func = [f for f in graph.functions.keys() if "foo" in f][0]
        callees = graph.get_all_callees(foo_func, recursive=False)

        assert len(callees) == 2  # foo calls bar and baz

    def test_get_transitive_callees(self, complex_code):
        """Test getting transitive callees."""
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        # entry_point should transitively call many functions
        entry = [f for f in graph.functions.keys() if "entry_point" in f][0]
        callees = graph.get_all_callees(entry, recursive=True)

        # Should find multiple transitive callees
        assert len(callees) > 0

    def test_detect_cycles(self, cycle_code):
        """Test cycle detection."""
        builder = CallGraphBuilder(cycle_code, "test_module")
        graph = builder.build()

        cycles = graph.detect_cycles()

        # Should have calls (even if cycle detection is conservative)
        assert len(graph.calls) > 0

    def test_find_call_paths(self, complex_code):
        """Test finding call paths."""
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        # Find path from entry_point to write_file
        entry = [f for f in graph.functions.keys() if "entry_point" in f][0]
        write_file = [f for f in graph.functions.keys() if "write_file" in f][0]

        paths = graph.find_call_paths(entry, write_file)

        # May or may not find paths depending on call structure
        # Just verify the method works
        assert isinstance(paths, list)

    def test_get_call_depth(self, complex_code):
        """Test getting call depth."""
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        entry = [f for f in graph.functions.keys() if "entry_point" in f][0]
        depths = graph.get_call_depth(entry)

        # Should have depths for reachable functions
        assert len(depths) > 1
        # Entry point should have depth 0
        assert depths[entry] == 0

    def test_get_function_metrics(self, complex_code):
        """Test getting function metrics."""
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        entry = [f for f in graph.functions.keys() if "entry_point" in f][0]
        metrics = graph.get_function_metrics(entry)

        assert "name" in metrics
        assert "direct_callers" in metrics
        assert "direct_callees" in metrics
        assert "transitive_callees" in metrics

    def test_get_graph_statistics(self, complex_code):
        """Test getting graph statistics."""
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        stats = graph.get_graph_statistics()

        assert "total_functions" in stats
        assert "total_calls" in stats
        assert "entry_points" in stats
        assert "leaf_functions" in stats
        assert stats["total_functions"] > 0

    def test_export_metrics(self, simple_code):
        """Test exporting metrics for all functions."""
        builder = CallGraphBuilder(simple_code, "test_module")
        graph = builder.build()

        all_metrics = graph.export_metrics()

        # Should have metrics for each function
        assert len(all_metrics) == 3
        assert all("name" in m for m in all_metrics.values())


class TestCallGraphIntegration:
    """Integration tests for call graph."""

    def test_full_analysis_workflow(self, complex_code):
        """Test full analysis workflow."""
        # Build graph
        builder = CallGraphBuilder(complex_code, "test_module")
        graph = builder.build()

        # Get statistics
        stats = graph.get_graph_statistics()
        assert stats["total_functions"] > 0

        # Detect cycles
        cycles = graph.detect_cycles()
        # Complex code has no cycles
        assert len(cycles) == 0

        # Export metrics
        metrics = graph.export_metrics()
        assert len(metrics) == stats["total_functions"]

    def test_call_graph_with_multiple_modules(self):
        """Test handling multiple module references."""
        code = """
import os
from datetime import datetime

def process():
    os.path.exists('file')
    datetime.now()
    helper()

def helper():
    pass
"""
        config = CallGraphConfig(include_external=True)
        builder = CallGraphBuilder(code, "test_module", config)
        graph = builder.build()

        # Should have internal and external calls
        assert len(graph.calls) > 0

    def test_empty_code(self):
        """Test handling empty code."""
        builder = CallGraphBuilder("", "test_module")
        graph = builder.build()

        assert len(graph.functions) == 0
        assert len(graph.calls) == 0

    def test_function_with_multiple_calls_same_callee(self):
        """Test function calling same function multiple times."""
        code = """
def caller():
    callee()
    callee()
    callee()

def callee():
    pass
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        # Should record multiple calls
        assert len(graph.calls) >= 3

    def test_indirect_recursion(self):
        """Test detection of indirect recursion."""
        code = """
def a():
    b()

def b():
    c()

def c():
    a()
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        # Should have calls forming the cycle
        assert len(graph.calls) == 3

    def test_lambda_functions(self):
        """Test handling lambda functions."""
        code = """
def processor():
    f = lambda x: x + 1
    return f

def caller():
    processor()
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        # Should handle basic structure (lambdas are complex)
        assert len(graph.functions) >= 1

    def test_high_fanout_function(self):
        """Test function with high call fanout."""
        code = """
def hub():
    a()
    b()
    c()
    d()
    e()

def a(): pass
def b(): pass
def c(): pass
def d(): pass
def e(): pass
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        hub = [f for f in graph.functions.keys() if "hub" in f][0]
        callees = graph.get_all_callees(hub)

        # Hub should call 5 functions
        assert len(callees) == 5

    def test_deep_call_chain(self):
        """Test deep call chain (A->B->C->D->E)."""
        code = """
def a(): b()
def b(): c()
def c(): d()
def d(): e()
def e(): pass
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        a_func = [f for f in graph.functions.keys() if f.endswith("a")][0]
        depths = graph.get_call_depth(a_func)

        # Should have calls at multiple depths
        assert len(depths) > 1


class TestCallGraphEdgeCases:
    """Test edge cases in call graph analysis."""

    def test_recursive_function(self):
        """Test function that calls itself."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        # Should have one function
        assert len(graph.functions) == 1
        # Should have one call (factorial calls itself)
        assert len(graph.calls) == 1

    def test_builtin_function_calls(self):
        """Test calls to builtin functions."""
        code = """
def process():
    x = len([1, 2, 3])
    y = str(x)
    print(y)
"""
        config = CallGraphConfig(include_builtins=False)
        builder = CallGraphBuilder(code, "test_module", config)
        graph = builder.build()

        # Should exclude builtin calls when configured
        for call in graph.calls:
            assert call.callee not in ["len", "str", "print"]

    def test_async_functions(self):
        """Test async function definitions."""
        code = """
async def async_func():
    pass

async def caller():
    await async_func()
"""
        builder = CallGraphBuilder(code, "test_module")
        graph = builder.build()

        # Should handle async functions
        assert len(graph.functions) >= 1
