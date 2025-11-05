"""Tests for symbol dependency resolver."""

import pytest
from pathlib import Path

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.dependency_resolver import (
    DependencyResolver,
    DependencyType,
    SymbolReference,
)


class TestDependencyResolverBasics:
    """Test basic dependency resolver functionality."""

    def test_resolver_initialization(self):
        """Test dependency resolver can be created."""
        resolver = DependencyResolver()
        assert resolver is not None
        assert len(resolver.symbols) == 0
        assert len(resolver.symbol_index) == 0

    def test_add_symbols(self):
        """Test adding symbols to resolver."""
        resolver = DependencyResolver()
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="module",
            signature="()",
            line_start=1,
            line_end=5,
            code="def test_func(): pass",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("test.py", [symbol])
        assert "test.py" in resolver.symbols
        assert len(resolver.symbols["test.py"]) == 1
        assert len(resolver.symbol_index) == 1

    def test_python_import_resolution(self):
        """Test Python import statement resolution."""
        resolver = DependencyResolver()
        code = '''from utils import helper
import os
from package.module import MyClass as MC
'''
        references = resolver.resolve_imports("test.py", code)
        assert len(references) >= 3

        # Check specific imports
        import_names = [ref.target_symbol for ref in references]
        assert "helper" in import_names
        assert "os" in import_names or any("os" in str(ref) for ref in references)

    def test_javascript_import_resolution(self):
        """Test JavaScript/TypeScript import statement resolution."""
        resolver = DependencyResolver()
        code = '''import { Component } from 'react';
import * as utils from './utils';
import { useState } from 'react';
const fs = require('fs');
'''
        references = resolver.resolve_imports("app.js", code)
        assert len(references) >= 3

        # Check module names
        modules = [ref.target_module for ref in references]
        assert "react" in modules
        assert "fs" in modules or any("fs" in str(ref) for ref in references)

    def test_java_import_resolution(self):
        """Test Java import statement resolution."""
        resolver = DependencyResolver()
        code = '''import java.util.ArrayList;
import java.io.File;
import com.example.MyClass;
'''
        references = resolver.resolve_imports("Test.java", code)
        assert len(references) >= 3

        # Check classes
        symbols = [ref.target_symbol for ref in references]
        assert "ArrayList" in symbols
        assert "MyClass" in symbols

    def test_go_import_resolution(self):
        """Test Go import statement resolution."""
        resolver = DependencyResolver()
        code = '''package main

import "fmt"
import "os"
import utils "myapp/utils"
'''
        references = resolver.resolve_imports("main.go", code)
        assert len(references) >= 2

        # Check modules
        modules = [ref.target_module for ref in references]
        assert "fmt" in modules
        assert "os" in modules

    def test_rust_import_resolution(self):
        """Test Rust import statement resolution."""
        resolver = DependencyResolver()
        code = '''use std::collections::HashMap;
use crate::utils::helper;
use serde::{Deserialize, Serialize};
'''
        references = resolver.resolve_imports("lib.rs", code)
        assert len(references) >= 2

        # Check modules
        modules = [ref.target_module for ref in references]
        assert "std" in modules
        assert "crate" in modules


class TestDependencyGraph:
    """Test dependency graph operations."""

    def test_symbol_dependencies(self):
        """Test finding symbol dependencies."""
        resolver = DependencyResolver()

        sym1 = create_symbol(
            file_path="a.py",
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
            file_path="b.py",
            symbol_type=SymbolType.FUNCTION,
            name="func_b",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("a.py", [sym1])
        resolver.add_symbols("b.py", [sym2])

        assert len(resolver.symbols) == 2
        assert len(resolver.symbol_index) == 2

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        resolver = DependencyResolver()

        # Create symbols in a circular dependency
        sym_a = create_symbol(
            file_path="a.py",
            symbol_type=SymbolType.CLASS,
            name="ClassA",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        sym_b = create_symbol(
            file_path="b.py",
            symbol_type=SymbolType.CLASS,
            name="ClassB",
            namespace="",
            signature="",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("a.py", [sym_a])
        resolver.add_symbols("b.py", [sym_b])

        # Note: Would need actual dependency edges to test circular detection
        # This is a structural test
        cycles = resolver.detect_circular_dependencies()
        assert isinstance(cycles, list)

    def test_impact_analysis(self):
        """Test impact analysis of symbol changes."""
        resolver = DependencyResolver()

        symbol = create_symbol(
            file_path="utils.py",
            symbol_type=SymbolType.FUNCTION,
            name="shared_util",
            namespace="",
            signature="()",
            line_start=1,
            line_end=1,
            code="",
            language="python",
            visibility="public"
        )

        resolver.add_symbols("utils.py", [symbol])

        impact = resolver.find_impact_of_change(symbol)
        assert "direct" in impact
        assert "indirect" in impact
        assert isinstance(impact["direct"], list)
        assert isinstance(impact["indirect"], list)

    def test_dependency_graph_stats(self):
        """Test dependency graph statistics."""
        resolver = DependencyResolver()

        # Add some symbols
        for i in range(3):
            symbol = create_symbol(
                file_path=f"module{i}.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=1,
                line_end=1,
                code="",
                language="python",
                visibility="public"
            )
            resolver.add_symbols(f"module{i}.py", [symbol])

        stats = resolver.get_dependency_graph_stats()
        assert "total_symbols" in stats
        assert "total_dependencies" in stats
        assert "circular_dependencies" in stats
        assert "max_dependency_depth" in stats
        assert stats["total_symbols"] == 3
        assert stats["files_with_symbols"] == 3


class TestImportPatterns:
    """Test various import patterns across languages."""

    def test_python_from_import(self):
        """Test Python from...import pattern."""
        resolver = DependencyResolver()
        code = "from module import func1, func2, func3"
        refs = resolver.resolve_imports("test.py", code)
        # Should capture all imports from module
        assert len(refs) >= 3
        symbols = {ref.target_symbol for ref in refs}
        assert "func1" in symbols
        assert "func2" in symbols
        assert "func3" in symbols

    def test_python_relative_import(self):
        """Test Python relative imports."""
        resolver = DependencyResolver()
        code = "from . import sibling\nfrom .. import parent"
        refs = resolver.resolve_imports("test.py", code)
        # Relative imports should be captured
        assert len(refs) >= 1

    def test_javascript_destructuring(self):
        """Test JavaScript destructured imports."""
        resolver = DependencyResolver()
        code = "import { useState, useEffect, useContext } from 'react';"
        refs = resolver.resolve_imports("app.js", code)
        assert len(refs) == 3
        symbols = {ref.target_symbol for ref in refs}
        assert "useState" in symbols
        assert "useEffect" in symbols
        assert "useContext" in symbols

    def test_javascript_default_import(self):
        """Test JavaScript default imports."""
        resolver = DependencyResolver()
        code = "import React from 'react';"
        refs = resolver.resolve_imports("app.js", code)
        assert len(refs) == 1
        assert refs[0].target_module == "react"

    def test_typescript_namespace_import(self):
        """Test TypeScript namespace imports."""
        resolver = DependencyResolver()
        code = "import * as fs from 'fs';"
        refs = resolver.resolve_imports("app.ts", code)
        assert len(refs) == 1
        assert refs[0].target_module == "fs"
        assert refs[0].target_symbol == "*"

    def test_java_wildcard_import(self):
        """Test Java wildcard imports (converted to module)."""
        resolver = DependencyResolver()
        code = "import java.util.*;\nimport com.example.util.*;"
        refs = resolver.resolve_imports("Test.java", code)
        # Wildcard imports captured
        assert len(refs) >= 1

    def test_go_multiple_imports(self):
        """Test Go multiple imports."""
        resolver = DependencyResolver()
        code = '''import (
    "fmt"
    "strings"
    "encoding/json"
)'''
        refs = resolver.resolve_imports("main.go", code)
        assert len(refs) == 3
        modules = {ref.target_module for ref in refs}
        assert "fmt" in modules
        assert "strings" in modules
        assert "encoding/json" in modules

    def test_rust_multiple_use_statements(self):
        """Test Rust multiple use statements."""
        resolver = DependencyResolver()
        code = '''use std::fs;
use std::io;
use serde_json::json;
'''
        refs = resolver.resolve_imports("lib.rs", code)
        assert len(refs) >= 2
        modules = {ref.target_module for ref in refs}
        assert "std" in modules


class TestSymbolReferences:
    """Test symbol reference tracking."""

    def test_symbol_reference_creation(self):
        """Test creating symbol references."""
        ref = SymbolReference(
            source_file="main.py",
            source_symbol=None,
            target_module="utils",
            target_symbol="helper",
            dependency_type=DependencyType.IMPORT,
            line_number=5
        )

        assert ref.source_file == "main.py"
        assert ref.target_module == "utils"
        assert ref.target_symbol == "helper"
        assert ref.dependency_type == DependencyType.IMPORT
        assert ref.line_number == 5

    def test_reference_dependency_types(self):
        """Test different dependency types."""
        types = [
            DependencyType.IMPORT,
            DependencyType.INHERIT,
            DependencyType.IMPLEMENT,
            DependencyType.CALL,
            DependencyType.TYPE,
            DependencyType.GENERIC
        ]

        assert len(types) == 6
        assert DependencyType.IMPORT.value == "import"
        assert DependencyType.CALL.value == "call"
