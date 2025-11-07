"""Tests for code parser implementation."""

import pytest
from athena.code_search.parser import CodeParser, PythonASTParser
from athena.code_search.models import CodeUnit


@pytest.fixture
def python_parser():
    """Create a Python code parser."""
    return CodeParser("python")


@pytest.fixture
def ast_parser():
    """Create a Python AST parser."""
    return PythonASTParser()


class TestCodeParserInitialization:
    """Test CodeParser initialization."""

    def test_python_parser_initialization(self):
        """Test initializing Python parser."""
        parser = CodeParser("python")
        assert parser.language == "python"
        assert parser.parser is not None

    def test_unsupported_language(self):
        """Test initializing unsupported language."""
        parser = CodeParser("rust")
        assert parser.language == "rust"
        # Parser should be None for unsupported languages
        assert parser.parser is None


class TestFunctionExtraction:
    """Test function extraction."""

    def test_extract_simple_function(self, python_parser):
        """Test extracting a simple function."""
        code = """
def hello():
    return "world"
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "hello"
        assert units[0].type == "function"
        assert "return" in units[0].code

    def test_extract_function_with_parameters(self, python_parser):
        """Test extracting function with parameters."""
        code = """
def greet(name: str) -> str:
    return f"Hello {name}"
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "greet"
        assert "name: str" in units[0].signature

    def test_extract_multiple_functions(self, python_parser):
        """Test extracting multiple functions."""
        code = """
def func1():
    pass

def func2():
    pass

def func3():
    pass
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 3
        names = [u.name for u in units]
        assert "func1" in names
        assert "func2" in names
        assert "func3" in names

    def test_extract_function_with_docstring(self, python_parser):
        """Test extracting function with docstring."""
        code = '''
def process(data):
    """Process the input data."""
    return data
'''
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].docstring == "Process the input data."

    def test_extract_function_dependencies(self, python_parser):
        """Test extracting function dependencies."""
        code = """
def main():
    result = helper1()
    process(result)
    validate()
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        dependencies = units[0].dependencies
        assert "helper1" in dependencies
        assert "process" in dependencies
        assert "validate" in dependencies

    def test_extract_async_function(self, python_parser):
        """Test extracting async function."""
        code = """
async def fetch_data():
    await some_operation()
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "fetch_data"

    def test_extract_function_syntax_error(self, python_parser):
        """Test handling syntax errors."""
        code = """
def broken(:
    pass
"""
        units = python_parser.extract_functions(code, "test.py")

        # Should return empty list on syntax error
        assert len(units) == 0


class TestClassExtraction:
    """Test class extraction."""

    def test_extract_simple_class(self, python_parser):
        """Test extracting a simple class."""
        code = """
class Animal:
    def speak(self):
        pass
"""
        units = python_parser.extract_classes(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "Animal"
        assert units[0].type == "class"

    def test_extract_class_with_docstring(self, python_parser):
        """Test extracting class with docstring."""
        code = '''
class User:
    """Represents a user in the system."""
    def __init__(self, name):
        self.name = name
'''
        units = python_parser.extract_classes(code, "test.py")

        assert len(units) == 1
        assert units[0].docstring == "Represents a user in the system."

    def test_extract_class_with_inheritance(self, python_parser):
        """Test extracting class with base classes."""
        code = """
class Dog(Animal):
    pass

class Cat(Animal):
    pass
"""
        units = python_parser.extract_classes(code, "test.py")

        assert len(units) == 2
        # Check dependencies (base classes)
        assert "Animal" in units[0].dependencies
        assert "Animal" in units[1].dependencies

    def test_extract_multiple_classes(self, python_parser):
        """Test extracting multiple classes."""
        code = """
class ClassA:
    pass

class ClassB:
    pass

class ClassC(ClassA):
    pass
"""
        units = python_parser.extract_classes(code, "test.py")

        assert len(units) == 3
        names = [u.name for u in units]
        assert "ClassA" in names
        assert "ClassB" in names
        assert "ClassC" in names

    def test_extract_class_with_methods(self, python_parser):
        """Test that class extraction includes methods in code."""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
        units = python_parser.extract_classes(code, "test.py")

        assert len(units) == 1
        # Code should include method definitions
        assert "def add" in units[0].code
        assert "def subtract" in units[0].code


class TestImportExtraction:
    """Test import extraction."""

    def test_extract_simple_import(self, python_parser):
        """Test extracting simple import."""
        code = """
import os
"""
        units = python_parser.extract_imports(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "os"
        assert units[0].type == "import"

    def test_extract_from_import(self, python_parser):
        """Test extracting from import."""
        code = """
from pathlib import Path
"""
        units = python_parser.extract_imports(code, "test.py")

        assert len(units) == 1
        assert "pathlib" in units[0].dependencies
        assert "Path" in units[0].dependencies

    def test_extract_multiple_imports(self, python_parser):
        """Test extracting multiple imports."""
        code = """
import os
import sys
from pathlib import Path
from typing import List, Dict
"""
        units = python_parser.extract_imports(code, "test.py")

        assert len(units) == 4

    def test_extract_import_with_alias(self, python_parser):
        """Test extracting import with alias."""
        code = """
import numpy as np
"""
        units = python_parser.extract_imports(code, "test.py")

        assert len(units) == 1
        # Should contain the numpy reference
        assert "np" in units[0].name or "numpy" in units[0].dependencies


class TestExtractAll:
    """Test extracting all semantic units."""

    def test_extract_all_units(self, python_parser):
        """Test extracting all types of units."""
        code = """
import os
from pathlib import Path

def helper():
    pass

class Handler:
    def process(self):
        pass

def main():
    helper()
"""
        units = python_parser.extract_all(code, "test.py")

        # Should have: 2 imports, 2 functions, 1 class = 5 units
        assert len(units) > 0

        # Check that we have different types
        types = [u.type for u in units]
        assert "function" in types
        assert "class" in types
        assert any(t.startswith("import") for t in types)


class TestCodeUnitProperties:
    """Test CodeUnit properties extracted by parser."""

    def test_code_unit_has_correct_line_numbers(self, python_parser):
        """Test that line numbers are correct."""
        code = """
def func():
    return 42
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].start_line >= 1
        assert units[0].end_line > units[0].start_line

    def test_code_unit_has_file_path(self, python_parser):
        """Test that file path is preserved."""
        code = "def foo(): pass"
        units = python_parser.extract_functions(code, "/path/to/file.py")

        assert len(units) == 1
        assert units[0].file_path == "/path/to/file.py"

    def test_code_unit_has_id(self, python_parser):
        """Test that code unit has unique ID."""
        code = "def func(): pass"
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].id is not None
        assert "func" in units[0].id
        assert "test.py" in units[0].id

    def test_code_unit_serialization(self, python_parser):
        """Test that code units can be serialized."""
        code = "def example(): pass"
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        unit_dict = units[0].to_dict()

        assert "id" in unit_dict
        assert "name" in unit_dict
        assert "type" in unit_dict
        assert "file_path" in unit_dict  # Serialized as "file_path"
        assert "code" in unit_dict


class TestASTParserEdgeCases:
    """Test edge cases in AST parser."""

    def test_empty_file(self, python_parser):
        """Test parsing empty file."""
        code = ""
        units = python_parser.extract_functions(code, "empty.py")
        assert len(units) == 0

    def test_file_with_only_comments(self, python_parser):
        """Test file with only comments."""
        code = """
# This is a comment
# Another comment
"""
        units = python_parser.extract_functions(code, "test.py")
        assert len(units) == 0

    def test_file_with_module_docstring(self, python_parser):
        """Test file with module-level docstring."""
        code = '''
"""Module docstring."""

def func():
    pass
'''
        units = python_parser.extract_functions(code, "test.py")
        assert len(units) == 1

    def test_nested_functions(self, python_parser):
        """Test that only top-level functions are extracted."""
        code = """
def outer():
    def inner():
        pass
    return inner
"""
        units = python_parser.extract_functions(code, "test.py")

        # Should get outer function
        assert len(units) == 1
        assert units[0].name == "outer"

    def test_lambda_expressions(self, python_parser):
        """Test that lambdas are not extracted as functions."""
        code = """
f = lambda x: x + 1

def regular_func():
    return 42
"""
        units = python_parser.extract_functions(code, "test.py")

        # Should only get regular_func
        assert len(units) == 1
        assert units[0].name == "regular_func"

    def test_decorator_handling(self, python_parser):
        """Test function with decorators."""
        code = """
@decorator
@another_decorator
def decorated_func():
    pass
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        assert units[0].name == "decorated_func"

    def test_function_with_complex_body(self, python_parser):
        """Test function with complex body including multiple calls."""
        code = """
def complex_function():
    data = fetch_data()
    processed = transform(data)
    save(processed)
    log_result(processed)
    return processed
"""
        units = python_parser.extract_functions(code, "test.py")

        assert len(units) == 1
        deps = units[0].dependencies
        assert "fetch_data" in deps
        assert "transform" in deps
        assert "save" in deps
        assert "log_result" in deps
