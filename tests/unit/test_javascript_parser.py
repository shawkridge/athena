"""Tests for JavaScript/TypeScript parser."""

import pytest
from pathlib import Path

from athena.code_search.javascript_parser import JavaScriptParser


@pytest.fixture
def js_parser():
    """Create JavaScript parser."""
    return JavaScriptParser("javascript")


@pytest.fixture
def ts_parser():
    """Create TypeScript parser."""
    return JavaScriptParser("typescript")


class TestJavaScriptFunctionExtraction:
    """Test JavaScript function extraction."""

    def test_extract_regular_function(self, js_parser):
        """Test extracting regular function."""
        code = """
function authenticate(user) {
    return validateUser(user);
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) == 1
        assert units[0].name == "authenticate"
        assert units[0].type == "function"

    def test_extract_async_function(self, js_parser):
        """Test extracting async function."""
        code = """
async function fetchData() {
    return await getData();
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) == 1
        assert units[0].name == "fetchData"

    def test_extract_arrow_function(self, js_parser):
        """Test extracting arrow function."""
        code = """
const validate = (user) => {
    return user.length > 0;
};
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1
        # Check if validate function is extracted
        names = [u.name for u in units]
        assert "validate" in names

    def test_extract_async_arrow_function(self, js_parser):
        """Test extracting async arrow function."""
        code = """
const fetchUser = async (id) => {
    return await getUser(id);
};
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1

    def test_extract_multiple_functions(self, js_parser):
        """Test extracting multiple functions."""
        code = """
function func1() {
    return 1;
}

function func2() {
    return 2;
}

const func3 = () => 3;
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 2

    def test_function_with_dependencies(self, js_parser):
        """Test function dependencies extraction."""
        code = """
function authenticate(user) {
    return validateUser(user) && checkPassword(user);
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1
        # Check dependencies
        deps = units[0].dependencies
        assert "validateUser" in deps or "checkPassword" in deps


class TestJavaScriptClassExtraction:
    """Test JavaScript class extraction."""

    def test_extract_class(self, js_parser):
        """Test extracting class."""
        code = """
class AuthHandler {
    constructor() {
        this.state = null;
    }

    login(user) {
        return authenticate(user);
    }
}
"""
        units = js_parser.extract_classes(code, "test.js")
        assert len(units) >= 1
        assert units[0].name == "AuthHandler"
        assert units[0].type == "class"

    def test_extract_class_with_inheritance(self, js_parser):
        """Test extracting class with inheritance."""
        code = """
class Handler extends BaseHandler {
    handle() {
        return super.handle();
    }
}
"""
        units = js_parser.extract_classes(code, "test.js")
        assert len(units) >= 1
        assert units[0].name == "Handler"
        assert "BaseHandler" in units[0].dependencies

    def test_extract_multiple_classes(self, js_parser):
        """Test extracting multiple classes."""
        code = """
class Class1 {
    method1() {}
}

class Class2 {
    method2() {}
}
"""
        units = js_parser.extract_classes(code, "test.js")
        assert len(units) >= 2


class TestTypeScriptExtraction:
    """Test TypeScript-specific extraction."""

    def test_extract_class_with_type_annotations(self, ts_parser):
        """Test extracting TypeScript class with type annotations."""
        code = """
class User {
    id: number;
    name: string;

    constructor(id: number, name: string) {
        this.id = id;
        this.name = name;
    }

    validate(): boolean {
        return this.id > 0 && this.name.length > 0;
    }
}
"""
        units = ts_parser.extract_classes(code, "test.ts")
        assert len(units) >= 1
        assert units[0].name == "User"

    def test_extract_class_with_implements(self, ts_parser):
        """Test extracting class implementing interface."""
        code = """
class Handler implements IHandler {
    execute(): void {
        console.log('executing');
    }
}
"""
        units = ts_parser.extract_classes(code, "test.ts")
        assert len(units) >= 1
        # Interface should be in dependencies
        deps = units[0].dependencies
        assert any("IHandler" in str(d) for d in deps)

    def test_extract_interface(self, ts_parser):
        """Test that interfaces are attempted to be extracted."""
        code = """
interface IUser {
    id: number;
    name: string;
    validate(): boolean;
}
"""
        # TypeScript parser should handle interfaces gracefully
        units = ts_parser.extract_all(code, "test.ts")
        assert isinstance(units, list)


class TestJavaScriptImportExtraction:
    """Test JavaScript import extraction."""

    def test_extract_es6_default_import(self, js_parser):
        """Test extracting ES6 default import."""
        code = """
import React from 'react';
"""
        units = js_parser.extract_imports(code, "test.js")
        assert len(units) >= 1
        assert units[0].type == "import_es6"
        assert "react" in units[0].name

    def test_extract_es6_named_imports(self, js_parser):
        """Test extracting ES6 named imports."""
        code = """
import { useState, useEffect } from 'react';
"""
        units = js_parser.extract_imports(code, "test.js")
        assert len(units) >= 1

    def test_extract_commonjs_require(self, js_parser):
        """Test extracting CommonJS require."""
        code = """
const express = require('express');
"""
        units = js_parser.extract_imports(code, "test.js")
        assert len(units) >= 1
        assert units[0].type == "import_cjs"

    def test_extract_multiple_imports(self, js_parser):
        """Test extracting multiple imports."""
        code = """
import React from 'react';
import { Component } from 'react';
const express = require('express');
"""
        units = js_parser.extract_imports(code, "test.js")
        assert len(units) >= 2

    def test_extract_import_with_alias(self, js_parser):
        """Test extracting import with alias."""
        code = """
import * as utils from './utils';
"""
        units = js_parser.extract_imports(code, "test.js")
        assert len(units) >= 1


class TestJavaScriptCompleteExtraction:
    """Test complete extraction of all units."""

    def test_extract_all(self, js_parser):
        """Test extracting all units from file."""
        code = """
import React from 'react';

function greet(name) {
    console.log(`Hello, ${name}`);
}

class Component {
    render() {
        return greet('World');
    }
}

const App = () => <Component />;
"""
        units = js_parser.extract_all(code, "test.js")

        # Should extract functions, classes, and imports
        types = {u.type for u in units}
        assert len(units) > 0

    def test_extract_with_real_world_code(self, js_parser):
        """Test with realistic React component."""
        code = """
import React, { useState } from 'react';

function Counter() {
    const [count, setCount] = useState(0);

    const increment = () => {
        setCount(count + 1);
    };

    const decrement = () => {
        setCount(count - 1);
    };

    return (
        <div>
            <button onClick={increment}>+</button>
            <span>{count}</span>
            <button onClick={decrement}>-</button>
        </div>
    );
}

export default Counter;
"""
        units = js_parser.extract_all(code, "Counter.js")
        assert len(units) > 0


class TestJavaScriptEdgeCases:
    """Test edge cases."""

    def test_empty_code(self, js_parser):
        """Test with empty code."""
        units = js_parser.extract_all("", "test.js")
        assert units == []

    def test_code_with_syntax_errors(self, js_parser):
        """Test with syntax errors (should not crash)."""
        code = """
function broken(
    // missing closing paren and brace
"""
        # Should not raise exception
        units = js_parser.extract_all(code, "test.js")
        assert isinstance(units, list)

    def test_code_with_no_functions(self, js_parser):
        """Test with code containing no functions."""
        code = """
const x = 5;
const y = 10;
const z = x + y;
"""
        units = js_parser.extract_all(code, "test.js")
        # May have some imports/declarations but not functions
        functions = [u for u in units if u.type == "function"]
        assert len(functions) == 0

    def test_nested_functions(self, js_parser):
        """Test extracting nested functions (top-level only)."""
        code = """
function outer() {
    function inner() {
        return 42;
    }
    return inner();
}
"""
        units = js_parser.extract_functions(code, "test.js")
        # Should extract at least the outer function
        names = [u.name for u in units]
        assert "outer" in names

    def test_function_with_long_signature(self, js_parser):
        """Test function with very long signature."""
        code = """
function veryLongFunctionNameWithManyParameters(param1, param2, param3, param4, param5) {
    return param1 + param2 + param3 + param4 + param5;
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1
        # Signature should be truncated but still valid
        assert len(units[0].signature) > 0


class TestJavaScriptDocstringExtraction:
    """Test JSDoc/comment extraction."""

    def test_extract_jsdoc_comment(self, js_parser):
        """Test extracting JSDoc comments."""
        code = """
/**
 * Authenticate a user.
 * @param {string} user - The user to authenticate
 * @returns {boolean} True if authenticated
 */
function authenticate(user) {
    return validateUser(user);
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1
        # Should have extracted some docstring
        docstring = units[0].docstring
        assert len(docstring) > 0

    def test_extract_line_comment(self, js_parser):
        """Test extracting line comments."""
        code = """
// Validates user input
function validate(input) {
    return input.length > 0;
}
"""
        units = js_parser.extract_functions(code, "test.js")
        assert len(units) >= 1


class TestJavaScriptIntegration:
    """Test JavaScript parser integration."""

    def test_parser_factory(self):
        """Test parser factory creates correct parser."""
        from athena.code_search.parser import CodeParser

        # Test JavaScript
        js_parser = CodeParser("javascript")
        assert js_parser.language == "javascript"
        assert js_parser.parser is not None

        # Test TypeScript
        ts_parser = CodeParser("typescript")
        assert ts_parser.language == "typescript"
        assert ts_parser.parser is not None

    def test_parser_extract_all(self):
        """Test CodeParser extracts from JavaScript."""
        from athena.code_search.parser import CodeParser

        parser = CodeParser("javascript")
        code = """
import axios from 'axios';

function fetchUser(id) {
    return axios.get(`/api/users/${id}`);
}

class UserService {
    getUser(id) {
        return fetchUser(id);
    }
}
"""
        units = parser.extract_all(code, "service.js")
        assert len(units) > 0

    def test_python_and_js_parsers_work_independently(self):
        """Test Python and JavaScript parsers work independently."""
        from athena.code_search.parser import CodeParser

        py_parser = CodeParser("python")
        js_parser = CodeParser("javascript")

        py_code = """
def authenticate(user):
    return validate_user(user)
"""

        js_code = """
function authenticate(user) {
    return validateUser(user);
}
"""

        py_units = py_parser.extract_all(py_code, "test.py")
        js_units = js_parser.extract_all(js_code, "test.js")

        assert len(py_units) > 0
        assert len(js_units) > 0
        # Both should find authenticate function
        assert any(u.name == "authenticate" for u in py_units)
        assert any(u.name == "authenticate" for u in js_units)
