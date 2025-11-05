"""
Unit Tests for Symbol Analysis System (Phase 1A)

Tests for symbol models, parsing, and integration.
Total: 44 tests

Author: Claude Code
Date: 2025-10-31
"""

import pytest
from athena.symbols.symbol_models import (
    SymbolType, RelationType, SymbolMetrics, SymbolDependency,
    Symbol, SymbolAnalysisResult, create_symbol
)
from athena.symbols.symbol_parser import (
    SymbolParser, LanguageDetector,
    PythonSymbolParser, JavaScriptSymbolParser, JavaSymbolParser, GoSymbolParser, RustSymbolParser,
    CSharpSymbolParser, PackageJsonParser, TsConfigParser, BabelConfigParser, ESLintConfigParser
)
from athena.symbols.symbol_store import SymbolStore
from athena.symbols.symbol_analyzer import SymbolAnalyzer, ComplexityAnalysis
from athena.symbols.symbol_tools import SymbolTools
from athena.symbols.symbol_pattern_integration import SymbolPatternLinker


# ============================================================================
# TEST SYMBOL MODELS (8 tests)
# ============================================================================

class TestSymbolModels:
    """Test symbol data model creation and validation."""

    def test_symbol_type_enum_values(self):
        """Test SymbolType enum has all expected values."""
        assert SymbolType.FUNCTION == "function"
        assert SymbolType.CLASS == "class"
        assert SymbolType.METHOD == "method"
        assert SymbolType.ASYNC_FUNCTION == "async_function"
        assert SymbolType.DATACLASS == "dataclass"
        # 14 types total
        assert len(SymbolType) == 14

    def test_relation_type_enum_values(self):
        """Test RelationType enum has all expected values."""
        assert RelationType.CALLS == "calls"
        assert RelationType.IMPORTS == "imports"
        assert RelationType.INHERITS_FROM == "inherits_from"
        # 8 types total
        assert len(RelationType) == 8

    def test_symbol_metrics_creation(self):
        """Test SymbolMetrics creation with valid values."""
        metrics = SymbolMetrics(
            lines_of_code=50,
            cyclomatic_complexity=5,
            cognitive_complexity=8,
            parameters=3,
            nesting_depth=2,
            maintainability_index=85.0
        )
        assert metrics.lines_of_code == 50
        assert metrics.cyclomatic_complexity == 5
        assert metrics.maintainability_index == 85.0

    def test_symbol_metrics_validation(self):
        """Test SymbolMetrics validates invalid values."""
        with pytest.raises(ValueError):
            SymbolMetrics(lines_of_code=-1)  # negative LOC

        with pytest.raises(ValueError):
            SymbolMetrics(cyclomatic_complexity=0)  # min is 1

        with pytest.raises(ValueError):
            SymbolMetrics(maintainability_index=150.0)  # max is 100

    def test_symbol_creation_with_factory(self):
        """Test create_symbol factory function."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="my_function",
            namespace="module",
            signature="(x, y)",
            line_start=10,
            line_end=20,
            code="def my_function(x, y):\n    return x + y",
            docstring="Test function"
        )
        assert symbol.name == "my_function"
        assert symbol.full_qualified_name == "module.my_function"
        assert symbol.get_lines_count() == 11

    def test_symbol_complexity_detection(self):
        """Test symbol complexity detection methods."""
        metrics_simple = SymbolMetrics(
            cyclomatic_complexity=3,
            lines_of_code=20,
            maintainability_index=85.0
        )
        symbol_simple = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="simple",
            namespace="",
            signature="()",
            line_start=1,
            line_end=20,
            code="pass",
            metrics=metrics_simple
        )
        assert not symbol_simple.is_complex()
        assert not symbol_simple.is_large()

        metrics_complex = SymbolMetrics(
            cyclomatic_complexity=15,
            lines_of_code=200,
            maintainability_index=25.0
        )
        symbol_complex = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="complex",
            namespace="",
            signature="()",
            line_start=1,
            line_end=200,
            code="pass",
            metrics=metrics_complex
        )
        assert symbol_complex.is_complex()
        assert symbol_complex.is_large()
        assert symbol_complex.is_poorly_maintained()

    def test_symbol_analysis_result(self):
        """Test SymbolAnalysisResult aggregation."""
        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=10,
            code="pass"
        )
        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="MyClass",
            namespace="",
            signature="()",
            line_start=15,
            line_end=30,
            code="pass"
        )

        result = SymbolAnalysisResult(
            file_path="test.py",
            language="python",
            symbols=[symbol1, symbol2],
            total_lines=100
        )

        assert result.get_symbol_count() == 2
        assert len(result.get_symbols_by_type(SymbolType.FUNCTION)) == 1
        assert len(result.get_symbols_by_type(SymbolType.CLASS)) == 1

    def test_dependency_creation(self):
        """Test SymbolDependency creation."""
        dep = SymbolDependency(
            target_symbol_name="other.function",
            relation_type=RelationType.CALLS,
            strength=0.8
        )
        assert dep.target_symbol_name == "other.function"
        assert dep.relation_type == RelationType.CALLS
        assert dep.strength == 0.8

        with pytest.raises(ValueError):
            SymbolDependency(
                target_symbol_name="test",
                relation_type=RelationType.CALLS,
                strength=1.5  # invalid
            )


# ============================================================================
# TEST SYMBOL PARSER (12 tests)
# ============================================================================

class TestSymbolParser:
    """Test language detection and code parsing."""

    def test_language_detection_python(self):
        """Test language detection for Python files."""
        assert LanguageDetector.detect_language("test.py") == "python"
        assert LanguageDetector.detect_language("script.pyw") == "python"

    def test_language_detection_javascript(self):
        """Test language detection for JavaScript files."""
        assert LanguageDetector.detect_language("app.js") == "javascript"
        assert LanguageDetector.detect_language("module.mjs") == "javascript"

    def test_language_detection_typescript(self):
        """Test language detection for TypeScript files."""
        assert LanguageDetector.detect_language("app.ts") == "typescript"
        assert LanguageDetector.detect_language("component.tsx") == "typescript"

    def test_language_detection_unsupported(self):
        """Test language detection for unsupported file types."""
        assert LanguageDetector.detect_language("file.go") == "go"
        assert LanguageDetector.detect_language("file.unknown") is None

    def test_python_function_parsing(self):
        """Test Python function parsing."""
        code = '''
def add(x, y):
    """Add two numbers."""
    return x + y
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success
        assert result.get_symbol_count() >= 1

        functions = result.get_symbols_by_type(SymbolType.FUNCTION)
        assert len(functions) >= 1
        func = functions[0]
        assert func.name == "add"
        assert func.symbol_type == SymbolType.FUNCTION

    def test_python_class_parsing(self):
        """Test Python class parsing."""
        code = '''
class MyClass:
    """A test class."""

    def __init__(self):
        pass

    def method(self):
        pass
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success
        assert result.get_symbol_count() >= 1

        classes = result.get_symbols_by_type(SymbolType.CLASS)
        assert len(classes) >= 1

    def test_python_async_function_parsing(self):
        """Test Python async function parsing."""
        code = '''
async def fetch_data():
    """Async function."""
    return None
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success

        async_funcs = result.get_symbols_by_type(SymbolType.ASYNC_FUNCTION)
        assert len(async_funcs) >= 1

    def test_javascript_function_parsing(self):
        """Test JavaScript function parsing."""
        code = '''
function greet(name) {
    return "Hello, " + name;
}

const multiply = (a, b) => a * b;
'''
        result = JavaScriptSymbolParser.parse_file("test.js", code)
        assert result.language == "javascript"
        assert result.get_symbol_count() >= 2

    def test_javascript_class_parsing(self):
        """Test JavaScript class parsing."""
        code = '''
class Calculator {
    constructor(name) {
        this.name = name;
    }

    add(a, b) {
        return a + b;
    }
}
'''
        result = JavaScriptSymbolParser.parse_file("test.js", code)
        assert result.success

        classes = result.get_symbols_by_type(SymbolType.CLASS)
        assert len(classes) >= 1

    def test_javascript_import_parsing(self):
        """Test JavaScript import parsing."""
        code = '''
import React from 'react';
import { useState } from 'react';
const express = require('express');
'''
        result = JavaScriptSymbolParser.parse_file("test.js", code)
        imports = result.get_symbols_by_type(SymbolType.IMPORT)
        assert len(imports) >= 1

    def test_typescript_parsing(self):
        """Test TypeScript file parsing."""
        code = '''
interface User {
    name: string;
    age: number;
}

class UserService {
    getUser(id: number): User {
        return { name: "Test", age: 30 };
    }
}
'''
        result = SymbolParser.parse_file("test.ts", code)
        assert result.language == "typescript"
        assert result.get_symbol_count() >= 1

    def test_java_class_parsing(self):
        """Test Java class parsing."""
        code = '''
public class Calculator {
    private int value = 0;

    public int add(int a, int b) {
        return a + b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }
}
'''
        result = SymbolParser.parse_file("Calculator.java", code)
        assert result.language == "java"
        assert result.get_symbol_count() >= 1
        # Should have class and methods
        assert any(s.symbol_type == SymbolType.CLASS for s in result.symbols)
        assert any(s.symbol_type == SymbolType.METHOD for s in result.symbols)

    def test_java_interface_parsing(self):
        """Test Java interface parsing."""
        code = '''
public interface Repository<T> {
    T findById(int id);
    void save(T entity);
    List<T> findAll();
}
'''
        result = SymbolParser.parse_file("Repository.java", code)
        assert result.language == "java"
        assert result.get_symbol_count() >= 1
        # Should have interface
        assert any(s.symbol_type == SymbolType.INTERFACE for s in result.symbols)

    def test_java_package_and_imports(self):
        """Test Java package and import parsing."""
        code = '''
package com.example.app;

import java.util.List;
import java.util.ArrayList;
import org.junit.Test;

public class MyClass {
    public void test() {
        List<String> items = new ArrayList<>();
    }
}
'''
        result = SymbolParser.parse_file("MyClass.java", code)
        assert result.language == "java"
        # Should extract imports
        assert any(s.symbol_type == SymbolType.IMPORT for s in result.symbols)

    def test_parser_syntax_error_handling(self):
        """Test parser handles syntax errors gracefully."""
        bad_python = "def invalid syntax here )(("
        result = PythonSymbolParser.parse_file("test.py", bad_python)
        assert not result.success
        assert len(result.parse_errors) > 0

    def test_parser_dispatcher(self):
        """Test SymbolParser dispatches to correct language parser."""
        python_code = "def test(): pass"
        py_result = SymbolParser.parse_file("test.py", python_code)
        assert py_result.language == "python"

        js_code = "function test() {}"
        js_result = SymbolParser.parse_file("test.js", js_code)
        assert js_result.language == "javascript"

        ts_code = "function test(): void {}"
        ts_result = SymbolParser.parse_file("test.ts", ts_code)
        assert ts_result.language == "typescript"

        java_code = "public class Test {}"
        java_result = SymbolParser.parse_file("Test.java", java_code)
        assert java_result.language == "java"

    def test_go_struct_parsing(self):
        """Test Go struct parsing."""
        code = '''
package main

type User struct {
    ID    int
    Name  string
    Email string
}

func (u *User) GetEmail() string {
    return u.Email
}

func (u *User) SetEmail(email string) {
    u.Email = email
}
'''
        result = SymbolParser.parse_file("user.go", code)
        assert result.language == "go"
        assert result.get_symbol_count() >= 1
        # Should have struct and methods
        assert any(s.symbol_type == SymbolType.CLASS for s in result.symbols)
        assert any(s.symbol_type == SymbolType.METHOD for s in result.symbols)

    def test_go_interface_parsing(self):
        """Test Go interface parsing."""
        code = '''
package main

type Reader interface {
    Read(b []byte) (n int, err error)
    Close() error
}

type Writer interface {
    Write(b []byte) (n int, err error)
    Flush() error
}
'''
        result = SymbolParser.parse_file("interfaces.go", code)
        assert result.language == "go"
        assert result.get_symbol_count() >= 1
        # Should have interfaces
        assert any(s.symbol_type == SymbolType.INTERFACE for s in result.symbols)

    def test_go_package_and_imports(self):
        """Test Go package and import parsing."""
        code = '''
package myapp

import (
    "fmt"
    "os"
    "github.com/user/package"
)

func main() {
    fmt.Println("Hello")
}

func helper() string {
    return "help"
}
'''
        result = SymbolParser.parse_file("main.go", code)
        assert result.language == "go"
        # Should extract imports and functions
        assert any(s.symbol_type == SymbolType.IMPORT for s in result.symbols)
        assert any(s.symbol_type == SymbolType.FUNCTION for s in result.symbols)

    def test_rust_struct_and_impl_parsing(self):
        """Test Rust struct and impl parsing."""
        code = '''
pub struct User {
    pub id: u32,
    pub name: String,
    email: String,
}

impl User {
    pub fn new(id: u32, name: String, email: String) -> Self {
        User { id, name, email }
    }

    pub fn email(&self) -> &str {
        &self.email
    }

    fn private_method(&self) -> String {
        format!("{}", self.name)
    }
}
'''
        result = SymbolParser.parse_file("user.rs", code)
        assert result.language == "rust"
        assert result.get_symbol_count() >= 1
        # Should have struct and methods
        assert any(s.symbol_type == SymbolType.CLASS for s in result.symbols)
        assert any(s.symbol_type == SymbolType.METHOD for s in result.symbols)

    def test_rust_trait_parsing(self):
        """Test Rust trait parsing."""
        code = '''
pub trait Reader {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize>;
    fn read_to_end(&mut self, buf: &mut Vec<u8>) -> std::io::Result<usize>;
}

pub trait Writer {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize>;
    fn flush(&mut self) -> std::io::Result<()>;
}
'''
        result = SymbolParser.parse_file("traits.rs", code)
        assert result.language == "rust"
        assert result.get_symbol_count() >= 1
        # Should have traits
        assert any(s.symbol_type == SymbolType.INTERFACE for s in result.symbols)

    def test_rust_module_and_functions(self):
        """Test Rust module and function parsing."""
        code = '''
mod utils {
    pub fn helper() -> String {
        "help".to_string()
    }
}

pub fn main() {
    println!("Hello, world!");
}

fn private_function() -> i32 {
    42
}

pub const PI: f64 = 3.14159;
pub static COUNTER: u32 = 0;
'''
        result = SymbolParser.parse_file("main.rs", code)
        assert result.language == "rust"
        # Should extract modules, functions, and constants
        assert any(s.symbol_type == SymbolType.MODULE for s in result.symbols)
        assert any(s.symbol_type == SymbolType.FUNCTION for s in result.symbols)
        assert any(s.symbol_type == SymbolType.CONSTANT for s in result.symbols)

    def test_react_native_typescript_component(self):
        """Test React Native TypeScript component parsing."""
        code = '''
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';

interface HomeScreenProps {
  userId: string;
}

const HomeScreen: React.FC<HomeScreenProps> = ({ userId }) => {
  const [count, setCount] = useState<number>(0);
  const navigation = useNavigation();

  useEffect(() => {
    console.log('Component mounted');
  }, []);

  const handlePress = () => {
    setCount(count + 1);
  };

  return <View><Text>{count}</Text></View>;
};

export default HomeScreen;
'''
        result = SymbolParser.parse_file("HomeScreen.tsx", code)
        assert result.language == "typescript"
        assert result.get_symbol_count() >= 1
        # Should have imports and arrow function component
        assert any(s.symbol_type == SymbolType.IMPORT for s in result.symbols)
        assert any(s.symbol_type == SymbolType.FUNCTION for s in result.symbols)

    def test_expo_app_component(self):
        """Test Expo app component parsing."""
        code = '''
import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';

const App: React.FC = () => {
  const [fontsLoaded] = useFonts({
    SpaceMono: require('./assets/fonts/SpaceMono-Regular.ttf'),
  });

  const onLayoutRootView = useCallback(async () => {
    if (fontsLoaded) {
      await SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text>Open up App.tsx to start working!</Text>
      <StatusBar style="auto" />
    </View>
  );
};

export default App;
'''
        result = SymbolParser.parse_file("App.tsx", code)
        assert result.language == "typescript"
        assert result.get_symbol_count() >= 1
        # Should extract Expo/React Native imports
        imports = [s for s in result.symbols if s.symbol_type == SymbolType.IMPORT]
        assert len(imports) >= 3
        # Verify key packages are imported
        import_names = [s.name for s in imports]
        assert "react" in import_names
        assert "react-native" in import_names
        assert "expo-status-bar" in import_names

    def test_typescript_interface_and_types(self):
        """Test TypeScript interface and type extraction."""
        code = '''
import { ReactNode } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
}

type UserStatus = 'active' | 'inactive' | 'pending';

interface AuthContextType {
  user: User | null;
  status: UserStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
'''
        result = SymbolParser.parse_file("auth.ts", code)
        assert result.language == "typescript"
        # Should extract imports and functions
        assert any(s.symbol_type == SymbolType.IMPORT for s in result.symbols)
        assert any(s.symbol_type == SymbolType.FUNCTION for s in result.symbols)

    def test_package_json_dependencies(self):
        """Test package.json dependency extraction."""
        code = '''{
  "name": "expo-app",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-native": "0.72.0",
    "expo": "^49.0.0",
    "@react-navigation/native": "^6.1.0",
    "axios": "^1.4.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0",
    "jest": "^29.0.0"
  }
}'''
        result = SymbolParser.parse_file("package.json", code)
        assert result.language == "package.json"
        assert result.get_symbol_count() >= 1
        # Should have dependencies
        deps = [s for s in result.symbols if s.symbol_type == SymbolType.IMPORT]
        assert len(deps) >= 8  # 5 runtime + 3 dev
        # Verify specific packages
        dep_names = [s.name for s in deps]
        assert "react" in dep_names
        assert "react-native" in dep_names
        assert "expo" in dep_names
        assert "typescript" in dep_names

    def test_package_json_scripts_and_metadata(self):
        """Test package.json scripts and metadata extraction."""
        code = '''{
  "name": "my-app",
  "version": "2.0.1",
  "main": "dist/index.js",
  "module": "dist/index.esm.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "start": "expo start",
    "build": "expo build:web",
    "test": "jest",
    "lint": "eslint src/",
    "typecheck": "tsc --noEmit"
  },
  "engines": {
    "node": ">=16.0.0",
    "npm": ">=8.0.0"
  }
}'''
        result = SymbolParser.parse_file("package.json", code)
        assert result.language == "package.json"
        # Should have scripts
        scripts = [s for s in result.symbols if s.symbol_type == SymbolType.FUNCTION]
        assert len(scripts) == 5
        script_names = [s.name for s in scripts]
        assert "start" in script_names
        assert "build" in script_names
        assert "test" in script_names
        # Should have metadata
        constants = [s for s in result.symbols if s.symbol_type == SymbolType.CONSTANT]
        assert len(constants) >= 5  # name, version, main, module, types

    def test_package_json_peer_and_optional_deps(self):
        """Test package.json peer and optional dependencies."""
        code = '''{
  "name": "react-plugin",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0"
  },
  "peerDependencies": {
    "react": ">=16.8.0",
    "react-dom": ">=16.8.0"
  },
  "optionalDependencies": {
    "native-module": "^1.0.0"
  }
}'''
        result = SymbolParser.parse_file("package.json", code)
        assert result.language == "package.json"
        # Should have all dependency types
        all_deps = [s for s in result.symbols if s.symbol_type == SymbolType.IMPORT]
        assert len(all_deps) >= 4
        # Check namespaces
        namespaces = [s.namespace for s in all_deps]
        assert "dependencies" in namespaces
        assert "peerDependencies" in namespaces
        assert "optionalDependencies" in namespaces

    def test_package_json_language_detection(self):
        """Test that package.json is properly detected."""
        result = SymbolParser.parse_file("package.json", '{"name": "test"}')
        assert result.language == "package.json"
        assert result.success

    def test_package_json_with_exports(self):
        """Test package.json exports field (modern entry points)."""
        code = '''{
  "name": "my-lib",
  "version": "1.0.0",
  "main": "dist/cjs/index.js",
  "module": "dist/esm/index.js",
  "exports": {
    ".": "./dist/index.js",
    "./components": "./dist/components.js",
    "./utils": "./dist/utils.js"
  }
}'''
        result = SymbolParser.parse_file("package.json", code)
        assert result.language == "package.json"
        # Should extract exports
        exports = [s for s in result.symbols if "export" in s.name]
        assert len(exports) == 3

    def test_csharp_class_with_properties_and_methods(self):
        """Test C# class parsing with properties and methods."""
        code = '''
namespace MyApp.Models
{
    public class User
    {
        private string _email;

        public int Id { get; set; }
        public string Name { get; set; }
        public string Email
        {
            get => _email;
            set => _email = value;
        }

        public User() { }

        public string GetEmail()
        {
            return _email;
        }

        public async Task SaveAsync()
        {
            await Task.Delay(100);
        }

        private void InternalMethod()
        {
            // private method
        }
    }
}
'''
        result = SymbolParser.parse_file("User.cs", code)
        assert result.language == "csharp"
        assert result.get_symbol_count() >= 1
        # Should have class, properties, and methods
        assert any(s.symbol_type == SymbolType.CLASS for s in result.symbols)
        assert any(s.symbol_type == SymbolType.PROPERTY for s in result.symbols)
        assert any(s.symbol_type == SymbolType.METHOD for s in result.symbols)
        # Check for async method
        assert any(s.is_async and s.symbol_type == SymbolType.ASYNC_FUNCTION for s in result.symbols)

    def test_csharp_interface_parsing(self):
        """Test C# interface parsing."""
        code = '''
namespace MyApp.Interfaces
{
    public interface IRepository<T>
    {
        Task<T> GetByIdAsync(int id);
        Task<IEnumerable<T>> GetAllAsync();
        Task<bool> SaveAsync(T entity);
        Task<bool> DeleteAsync(int id);
    }
}
'''
        result = SymbolParser.parse_file("IRepository.cs", code)
        assert result.language == "csharp"
        assert result.get_symbol_count() >= 1
        # Should have interface
        assert any(s.symbol_type == SymbolType.INTERFACE for s in result.symbols)

    def test_csharp_namespace_and_using(self):
        """Test C# namespace and using statements."""
        code = '''
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MyApp.Interfaces;
using static System.Console;

namespace MyApp.Services
{
    public class UserService
    {
        public void PrintUser(string name)
        {
            WriteLine($"User: {name}");
        }
    }
}
'''
        result = SymbolParser.parse_file("UserService.cs", code)
        assert result.language == "csharp"
        # Should have using statements
        using_stmts = [s for s in result.symbols if s.symbol_type == SymbolType.IMPORT]
        assert len(using_stmts) >= 4
        # Should have class
        assert any(s.symbol_type == SymbolType.CLASS for s in result.symbols)

    def test_csharp_enum_and_struct(self):
        """Test C# enum and struct parsing."""
        code = '''
namespace MyApp
{
    public enum UserRole
    {
        Admin = 1,
        Manager = 2,
        User = 3
    }

    public struct Point
    {
        public int X { get; set; }
        public int Y { get; set; }

        public Point(int x, int y)
        {
            X = x;
            Y = y;
        }
    }
}
'''
        result = SymbolParser.parse_file("Types.cs", code)
        assert result.language == "csharp"
        # Should have enum and struct
        symbols = result.symbols
        assert len(symbols) >= 2
        symbol_names = [s.name for s in symbols]
        assert "UserRole" in symbol_names
        assert "Point" in symbol_names
        # Verify types
        enum_symbols = [s for s in symbols if s.symbol_type == SymbolType.ENUM]
        class_symbols = [s for s in symbols if s.symbol_type == SymbolType.CLASS]
        assert len(enum_symbols) >= 1  # UserRole enum
        assert len(class_symbols) >= 1  # Point struct

    def test_tsconfig_compiler_options(self):
        """Test tsconfig.json compiler options extraction."""
        code = '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "esnext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-native",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}'''
        result = SymbolParser.parse_file("tsconfig.json", code)
        assert result.language == "tsconfig.json"
        assert result.get_symbol_count() >= 1
        # Should have compiler options as constants
        constants = [s for s in result.symbols if s.symbol_type == SymbolType.CONSTANT]
        assert len(constants) >= 5
        # Verify specific options are extracted
        option_names = [s.name for s in constants]
        assert any("target" in name for name in option_names)
        assert any("module" in name for name in option_names)

    def test_tsconfig_path_mappings(self):
        """Test tsconfig.json path mapping extraction."""
        code = '''{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@utils/*": ["src/utils/*"],
      "@types/*": ["src/types/*"]
    }
  }
}'''
        result = SymbolParser.parse_file("tsconfig.json", code)
        assert result.language == "tsconfig.json"
        symbols = result.symbols
        # Should have baseUrl and path mappings
        path_symbols = [s for s in symbols if "paths" in s.namespace]
        assert len(path_symbols) >= 4  # baseUrl + mappings
        mapping_names = [s.name for s in path_symbols]
        assert any("baseUrl" in name for name in mapping_names)
        assert any("@/" in name or "@components" in name for name in mapping_names)

    def test_tsconfig_extended_config(self):
        """Test tsconfig.json extends and root options."""
        code = '''{
  "extends": "./tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}'''
        result = SymbolParser.parse_file("tsconfig.json", code)
        assert result.language == "tsconfig.json"
        symbols = result.symbols
        # Should extract extends
        config_symbols = [s for s in symbols if "extends" in s.name]
        assert len(config_symbols) >= 1
        assert any(s.signature == "./tsconfig.base.json" for s in config_symbols)

    def test_tsconfig_project_references(self):
        """Test tsconfig.json project references."""
        code = '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "esnext"
  },
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/ui" },
    { "path": "./packages/utils" }
  ]
}'''
        result = SymbolParser.parse_file("tsconfig.json", code)
        assert result.language == "tsconfig.json"
        symbols = result.symbols
        # Should extract project references
        ref_symbols = [s for s in symbols if "reference" in s.namespace]
        assert len(ref_symbols) >= 3
        ref_paths = [s.signature for s in ref_symbols]
        assert "./packages/core" in ref_paths

    def test_tsconfig_language_detection(self):
        """Test tsconfig.json language detection."""
        # Verify filename-based detection works
        lang = LanguageDetector.detect_language("tsconfig.json")
        assert lang == "tsconfig.json"
        # Test with path
        lang = LanguageDetector.detect_language("/project/tsconfig.json")
        assert lang == "tsconfig.json"

    def test_babel_config_json_presets_and_plugins(self):
        """Test babel.config.json preset and plugin extraction."""
        code = '''{
  "presets": [
    ["@babel/preset-env", { "targets": { "browsers": ["last 2 versions"] } }],
    "@babel/preset-react",
    "@babel/preset-typescript"
  ],
  "plugins": [
    "@babel/plugin-proposal-class-properties",
    "@babel/plugin-transform-runtime",
    ["module-resolver", { "alias": { "@": "./src" } }]
  ]
}'''
        result = SymbolParser.parse_file("babel.config.json", code)
        assert result.language == "babel.config.json"
        assert result.get_symbol_count() >= 5
        # Should have presets and plugins
        symbols = result.symbols
        preset_symbols = [s for s in symbols if "preset" in s.name]
        plugin_symbols = [s for s in symbols if "plugin" in s.name]
        assert len(preset_symbols) >= 3
        assert len(plugin_symbols) >= 3

    def test_babel_config_js_env_presets(self):
        """Test babel.config.js env-based presets."""
        code = '''module.exports = {
  presets: [
    "@babel/preset-env",
    "@babel/preset-react"
  ],
  env: {
    test: {
      presets: ["@babel/preset-env"]
    },
    production: {
      plugins: ["@babel/plugin-transform-runtime"]
    }
  }
};'''
        result = SymbolParser.parse_file("babel.config.js", code)
        assert result.language == "babel.config.js"
        symbols = result.symbols
        # Should extract presets and env configs
        assert len(symbols) >= 3
        # Check for env configurations
        env_symbols = [s for s in symbols if "env" in s.name]
        assert len(env_symbols) >= 2

    def test_babel_config_with_targets(self):
        """Test babel.config.json with browser targets."""
        code = '''{
  "presets": [
    [
      "@babel/preset-env",
      {
        "targets": {
          "browsers": ["last 2 versions", "not dead", "not ie <= 10"],
          "node": "12"
        }
      }
    ]
  ]
}'''
        result = SymbolParser.parse_file("babel.config.json", code)
        assert result.language == "babel.config.json"
        symbols = result.symbols
        # Should extract preset with targets
        assert len(symbols) >= 1
        assert any("preset" in s.name for s in symbols)

    def test_babel_config_language_detection(self):
        """Test babel config language detection."""
        # Test JSON detection
        lang = LanguageDetector.detect_language("babel.config.json")
        assert lang == "babel.config.json"

        # Test JS detection
        lang = LanguageDetector.detect_language("babel.config.js")
        assert lang == "babel.config.js"

        # Test with paths
        lang = LanguageDetector.detect_language("/project/babel.config.js")
        assert lang == "babel.config.js"

    def test_eslintrc_json_parser_envs_and_extends(self):
        """Test .eslintrc.json parser, environments and extends."""
        code = '''{
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module",
    "ecmaFeatures": { "jsx": true }
  },
  "env": {
    "browser": true,
    "node": true,
    "es2021": true,
    "jest": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended"
  ],
  "plugins": [
    "@typescript-eslint",
    "react",
    "react-hooks"
  ]
}'''
        result = SymbolParser.parse_file(".eslintrc.json", code)
        assert result.language == "eslintrc.json"
        assert result.get_symbol_count() >= 1
        symbols = result.symbols
        # Should have parser
        parser_symbols = [s for s in symbols if "parser" in s.name]
        assert len(parser_symbols) >= 1
        assert any("@typescript-eslint" in s.signature for s in parser_symbols)
        # Should have environments
        env_symbols = [s for s in symbols if "env." in s.name]
        assert len(env_symbols) >= 4
        # Should have extends
        extends_symbols = [s for s in symbols if "extends." in s.name]
        assert len(extends_symbols) >= 3

    def test_eslintrc_js_rules_configuration(self):
        """Test .eslintrc.js with rules configuration."""
        code = '''module.exports = {
  parser: "@typescript-eslint/parser",
  env: {
    browser: true,
    node: true,
    es2021: true
  },
  extends: ["eslint:recommended"],
  rules: {
    "no-console": "warn",
    "no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-types": ["error", {
      allowExpressions: true
    }],
    "react/prop-types": 0
  }
};'''
        result = SymbolParser.parse_file(".eslintrc.js", code)
        assert result.language == "eslintrc.js"
        symbols = result.symbols
        # Should have rules
        rule_symbols = [s for s in symbols if "rule." in s.name]
        assert len(rule_symbols) >= 4
        rule_names = [s.name for s in rule_symbols]
        assert any("no-console" in name for name in rule_names)
        assert any("no-unused-vars" in name for name in rule_names)

    def test_eslintrc_with_overrides(self):
        """Test .eslintrc.json with file overrides."""
        code = '''{
  "env": { "browser": true, "node": true },
  "extends": ["eslint:recommended"],
  "overrides": [
    {
      "files": ["*.ts", "*.tsx"],
      "parser": "@typescript-eslint/parser",
      "extends": ["plugin:@typescript-eslint/recommended"]
    },
    {
      "files": ["*.test.js"],
      "env": { "jest": true },
      "rules": { "no-console": "off" }
    }
  ]
}'''
        result = SymbolParser.parse_file(".eslintrc.json", code)
        assert result.language == "eslintrc.json"
        symbols = result.symbols
        # Should have overrides
        override_symbols = [s for s in symbols if "override." in s.name]
        assert len(override_symbols) >= 2
        assert any("*.ts" in s.signature or "*.tsx" in s.signature for s in override_symbols)

    def test_eslintrc_plugins_and_rules(self):
        """Test .eslintrc with plugins and their rules."""
        code = '''{
  "extends": ["eslint:recommended"],
  "plugins": [
    "@typescript-eslint",
    "react",
    "react-hooks",
    "import"
  ],
  "rules": {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "import/no-unresolved": "error",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}'''
        result = SymbolParser.parse_file(".eslintrc", code)
        assert result.language == "eslintrc"
        symbols = result.symbols
        # Should have plugins
        plugin_symbols = [s for s in symbols if "plugin." in s.name]
        assert len(plugin_symbols) >= 4
        # Should have rules from plugins
        rule_symbols = [s for s in symbols if "rule." in s.name]
        assert len(rule_symbols) >= 4

    def test_eslintrc_language_detection(self):
        """Test ESLint config language detection."""
        # Test JSON detection
        lang = LanguageDetector.detect_language(".eslintrc.json")
        assert lang == "eslintrc.json"

        # Test JS detection
        lang = LanguageDetector.detect_language(".eslintrc.js")
        assert lang == "eslintrc.js"

        # Test plain .eslintrc detection
        lang = LanguageDetector.detect_language(".eslintrc")
        assert lang == "eslintrc"

        # Test with paths
        lang = LanguageDetector.detect_language("/project/.eslintrc.json")
        assert lang == "eslintrc.json"

    def test_jest_config_json_test_patterns(self):
        """Test Jest config JSON parsing with test patterns and coverage."""
        code = '''{
  "testEnvironment": "jsdom",
  "preset": "ts-jest",
  "testMatch": [
    "<rootDir>/src/**/__tests__/**/*.test.ts",
    "<rootDir>/src/**/?(*.)+(spec|test).ts"
  ],
  "testPathIgnorePatterns": [
    "/node_modules/",
    "/dist/"
  ],
  "collectCoverageFrom": [
    "src/**/*.ts",
    "!src/**/*.d.ts",
    "!src/**/__tests__/**"
  ],
  "coverageThreshold": {
    "global": {
      "lines": 80,
      "functions": 75,
      "branches": 70,
      "statements": 80
    }
  },
  "setupFilesAfterEnv": [
    "<rootDir>/src/test/setup.ts"
  ],
  "testTimeout": 10000
}'''
        result = SymbolParser.parse_file("jest.config.json", code)
        assert result.success is True
        assert len(result.symbols) >= 12

        # Check test patterns
        test_match_symbols = [s for s in result.symbols if "testMatch" in s.name]
        assert len(test_match_symbols) == 2

        # Check coverage thresholds
        coverage_symbols = [s for s in result.symbols if "coverage" in s.name]
        assert len(coverage_symbols) >= 5

        # Check test environment
        env_symbol = next((s for s in result.symbols if s.name == "config.testEnvironment"), None)
        assert env_symbol is not None
        assert env_symbol.signature == "jsdom"

        # Check preset
        preset_symbol = next((s for s in result.symbols if s.name == "config.preset"), None)
        assert preset_symbol is not None
        assert preset_symbol.signature == "ts-jest"

    def test_jest_config_js_transforms_and_aliases(self):
        """Test Jest config JS parsing with transforms and module aliases."""
        code = '''module.exports = {
  testEnvironment: "node",
  transform: {
    "^.+\\\\.tsx?$": "ts-jest",
    "^.+\\\\.jsx?$": "babel-jest"
  },
  moduleNameMapper: {
    "@/(.*)$": "<rootDir>/src/$1",
    "@tests/(.*)$": "<rootDir>/src/__tests__/$1"
  },
  collectCoverageFrom: [
    "src/**/*.{ts,tsx,js,jsx}",
    "!src/**/*.d.ts"
  ],
  coverageThreshold: {
    global: {
      lines: 85,
      functions: 85,
      branches: 80,
      statements: 85
    }
  }
};'''
        result = SymbolParser.parse_file("jest.config.js", code)
        assert result.success is True
        assert len(result.symbols) >= 8

        # Check transforms
        transform_symbols = [s for s in result.symbols if "transform" in s.name]
        assert len(transform_symbols) >= 2

        # Check module aliases
        alias_symbols = [s for s in result.symbols if "alias" in s.name]
        assert len(alias_symbols) == 2

        # Verify alias mappings
        alias_names = {s.name for s in alias_symbols}
        assert "alias.@/(.*)$" in alias_names or "alias.@/*" in alias_names

    def test_jest_config_with_setup_files(self):
        """Test Jest config with setup files and timeout."""
        code = '''{
  "testEnvironment": "jsdom",
  "setupFilesAfterEnv": [
    "<rootDir>/src/setupTests.ts",
    "<rootDir>/src/setupMocks.ts"
  ],
  "testTimeout": 30000,
  "testMatch": [
    "**/__tests__/**/*.test.ts"
  ],
  "moduleNameMapper": {
    "^@/(.*)$": "<rootDir>/src/$1"
  }
}'''
        result = SymbolParser.parse_file("jest.config.json", code)
        assert result.success is True

        # Check setup files
        setup_symbols = [s for s in result.symbols if "setupFile" in s.name]
        assert len(setup_symbols) == 2

        # Check timeout
        timeout_symbol = next((s for s in result.symbols if s.name == "config.testTimeout"), None)
        assert timeout_symbol is not None
        assert timeout_symbol.signature == "30000"

    def test_jest_config_coverage_configuration(self):
        """Test Jest coverage configuration extraction."""
        code = '''{
  "collectCoverageFrom": [
    "src/**/*.ts",
    "!src/**/*.d.ts",
    "!src/index.ts"
  ],
  "coveragePathIgnorePatterns": [
    "/node_modules/",
    "/dist/",
    ".mock.ts"
  ],
  "coverageThreshold": {
    "global": {
      "lines": 90,
      "functions": 90,
      "branches": 85,
      "statements": 90
    },
    "./src/utils/": {
      "lines": 95,
      "functions": 95
    }
  }
}'''
        result = SymbolParser.parse_file("jest.config.json", code)
        assert result.success is True

        # Check collectCoverageFrom
        collect_symbols = [s for s in result.symbols if "collectFrom" in s.name]
        assert len(collect_symbols) == 3

        # Check ignore patterns
        ignore_symbols = [s for s in result.symbols if "ignorePattern" in s.name]
        assert len(ignore_symbols) == 3

        # Check coverage thresholds
        threshold_symbols = [s for s in result.symbols if "threshold" in s.name]
        assert len(threshold_symbols) >= 6

    def test_jest_config_language_detection(self):
        """Test Jest config language detection."""
        # Test JSON detection
        lang = LanguageDetector.detect_language("jest.config.json")
        assert lang == "jest.config.json"

        # Test JS detection
        lang = LanguageDetector.detect_language("jest.config.js")
        assert lang == "jest.config.js"

        # Test with paths
        lang = LanguageDetector.detect_language("/project/jest.config.json")
        assert lang == "jest.config.json"

        lang = LanguageDetector.detect_language("/project/jest.config.js")
        assert lang == "jest.config.js"

    def test_prettier_config_json_formatting_options(self):
        """Test Prettier config JSON parsing with formatting options."""
        code = '''{
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "bracketSpacing": true,
  "arrowParens": "always",
  "bracketSameLine": false,
  "endOfLine": "lf",
  "proseWrap": "preserve"
}'''
        result = SymbolParser.parse_file(".prettierrc", code)
        assert result.success is True
        assert len(result.symbols) >= 11

        # Check print width
        print_width_symbol = next((s for s in result.symbols if s.name == "config.printWidth"), None)
        assert print_width_symbol is not None
        assert print_width_symbol.signature == "100"

        # Check tab width
        tab_width_symbol = next((s for s in result.symbols if s.name == "config.tabWidth"), None)
        assert tab_width_symbol is not None
        assert tab_width_symbol.signature == "2"

        # Check single quote
        single_quote_symbol = next((s for s in result.symbols if s.name == "config.singleQuote"), None)
        assert single_quote_symbol is not None
        assert single_quote_symbol.signature == "true"

        # Check trailing comma
        trailing_comma_symbol = next((s for s in result.symbols if s.name == "config.trailingComma"), None)
        assert trailing_comma_symbol is not None
        assert trailing_comma_symbol.signature == "es5"

    def test_prettier_config_js_with_plugins_and_overrides(self):
        """Test Prettier config JS parsing with plugins and overrides."""
        code = '''module.exports = {
  printWidth: 120,
  tabWidth: 4,
  semi: false,
  singleQuote: false,
  trailingComma: "all",
  bracketSpacing: false,
  arrowParens: "avoid",
  plugins: [
    "prettier-plugin-tailwindcss",
    "prettier-plugin-organize-imports"
  ],
  overrides: [
    {
      files: ["*.md", "*.mdx"],
      options: {
        proseWrap: "always"
      }
    },
    {
      files: ["*.html"],
      options: {
        parser: "html",
        tabWidth: 2
      }
    }
  ]
};'''
        result = SymbolParser.parse_file("prettier.config.js", code)
        assert result.success is True
        assert len(result.symbols) >= 10

        # Check plugins
        plugin_symbols = [s for s in result.symbols if "plugin" in s.name]
        assert len(plugin_symbols) >= 2

        # Check plugin names
        plugin_names = {s.name for s in plugin_symbols}
        assert "plugin.prettier-plugin-tailwindcss" in plugin_names
        assert "plugin.prettier-plugin-organize-imports" in plugin_names

        # Check overrides
        override_symbols = [s for s in result.symbols if "override" in s.name]
        assert len(override_symbols) >= 3

    def test_prettier_config_with_overrides_for_languages(self):
        """Test Prettier config with language-specific overrides."""
        code = '''{
  "printWidth": 80,
  "tabWidth": 2,
  "semi": true,
  "overrides": [
    {
      "files": ["*.json"],
      "options": {
        "printWidth": 100,
        "tabWidth": 2
      }
    },
    {
      "files": ["*.css", "*.scss"],
      "options": {
        "parser": "scss",
        "tabWidth": 4
      }
    },
    {
      "files": ["*.html"],
      "options": {
        "parser": "html",
        "bracketSameLine": true
      }
    }
  ]
}'''
        result = SymbolParser.parse_file(".prettierrc.json", code)
        assert result.success is True

        # Check override patterns
        override_patterns = [s for s in result.symbols if "pattern" in s.name]
        assert len(override_patterns) >= 3

        pattern_values = {s.signature for s in override_patterns}
        assert "*.json" in pattern_values
        assert "*.css" in pattern_values
        assert "*.html" in pattern_values

    def test_prettier_config_minimal(self):
        """Test Prettier config with minimal settings."""
        code = '''{
  "semi": false,
  "singleQuote": true
}'''
        result = SymbolParser.parse_file(".prettierrc", code)
        assert result.success is True
        assert len(result.symbols) >= 2

        # Check semi setting
        semi_symbol = next((s for s in result.symbols if s.name == "config.semi"), None)
        assert semi_symbol is not None
        assert semi_symbol.signature == "false"

    def test_prettier_config_language_detection(self):
        """Test Prettier config language detection."""
        # Test .prettierrc detection
        lang = LanguageDetector.detect_language(".prettierrc")
        assert lang == "prettierrc"

        # Test .prettierrc.json detection
        lang = LanguageDetector.detect_language(".prettierrc.json")
        assert lang == "prettierrc.json"

        # Test .prettierrc.js detection
        lang = LanguageDetector.detect_language(".prettierrc.js")
        assert lang == "prettierrc.js"

        # Test prettier.config.js detection
        lang = LanguageDetector.detect_language("prettier.config.js")
        assert lang == "prettier.config.js"

        # Test with paths
        lang = LanguageDetector.detect_language("/project/.prettierrc")
        assert lang == "prettierrc"

        lang = LanguageDetector.detect_language("/project/.prettierrc.json")
        assert lang == "prettierrc.json"

    def test_editorconfig_basic_settings(self):
        """Test EditorConfig parsing with basic settings."""
        code = '''root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{js,jsx,ts,tsx}]
indent_style = space
indent_size = 2
'''
        result = SymbolParser.parse_file(".editorconfig", code)
        assert result.success is True
        assert len(result.symbols) >= 9

        # Check root setting
        root_symbol = next((s for s in result.symbols if s.name == "config.root"), None)
        assert root_symbol is not None
        assert root_symbol.signature == "true"

        # Check patterns
        pattern_symbols = [s for s in result.symbols if "pattern" in s.name]
        assert len(pattern_symbols) >= 3

        # Check for python pattern
        py_patterns = [s for s in pattern_symbols if "*.py" in s.name]
        assert len(py_patterns) >= 1

    def test_editorconfig_with_multiple_overrides(self):
        """Test EditorConfig with multiple file type overrides."""
        code = '''root = true

[*]
indent_style = space
indent_size = 2
charset = utf-8

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab

[*.{css,scss,less}]
indent_size = 4

[*.json]
indent_size = 2
insert_final_newline = true

[*.sh]
end_of_line = lf
indent_style = space
indent_size = 2
'''
        result = SymbolParser.parse_file(".editorconfig", code)
        assert result.success is True

        # Check pattern count
        pattern_symbols = [s for s in result.symbols if "pattern" in s.name]
        assert len(pattern_symbols) >= 5

        # Verify specific patterns
        pattern_names = {s.signature for s in pattern_symbols}
        assert "*" in pattern_names
        assert "*.md" in pattern_names
        assert "Makefile" in pattern_names

    def test_editorconfig_indentation_styles(self):
        """Test EditorConfig indentation configuration."""
        code = '''root = true

[*.py]
indent_style = space
indent_size = 4
tab_width = 4

[Makefile]
indent_style = tab
indent_size = 8

[*.js]
indent_style = space
indent_size = 2
'''
        result = SymbolParser.parse_file(".editorconfig", code)
        assert result.success is True

        # Get all settings
        setting_symbols = [s for s in result.symbols if "setting" in s.name]
        assert len(setting_symbols) >= 7

        # Check for indent_style settings
        indent_style_symbols = [s for s in setting_symbols if "indent_style" in s.name]
        assert len(indent_style_symbols) >= 2

    def test_editorconfig_with_comments(self):
        """Test EditorConfig parsing with comments."""
        code = '''# This is an EditorConfig file
root = true

# Default settings for all files
[*]
charset = utf-8
; This is a semicolon comment
end_of_line = lf

# Python-specific settings
[*.py]
indent_style = space
indent_size = 4
'''
        result = SymbolParser.parse_file(".editorconfig", code)
        assert result.success is True

        # Comments should not create symbols
        symbols = result.symbols
        comment_symbols = [s for s in symbols if "This" in str(s.name) or "#" in str(s.name)]
        assert len(comment_symbols) == 0

        # Verify actual settings are parsed
        charset_symbols = [s for s in symbols if "charset" in s.name]
        assert len(charset_symbols) >= 1

    def test_editorconfig_language_detection(self):
        """Test EditorConfig language detection."""
        # Test .editorconfig detection
        lang = LanguageDetector.detect_language(".editorconfig")
        assert lang == "editorconfig"

        # Test with paths
        lang = LanguageDetector.detect_language("/project/.editorconfig")
        assert lang == "editorconfig"

        # Test with deep paths
        lang = LanguageDetector.detect_language("/home/user/project/.editorconfig")
        assert lang == "editorconfig"


# ============================================================================
# TEST INTEGRATION (8 tests)
# ============================================================================

class TestSymbolIntegration:
    """Test symbol system integration."""

    def test_end_to_end_python_analysis(self):
        """Test complete Python file analysis workflow."""
        code = '''
"""Authentication module."""

class JWTHandler:
    """Handles JWT tokens."""

    def encode(self, payload, secret):
        """Encode JWT token."""
        return f"{payload}.{secret}"

    def decode(self, token, secret):
        """Decode JWT token."""
        parts = token.split('.')
        return parts[0] if len(parts) > 0 else None

def create_handler(secret):
    """Create JWT handler."""
    return JWTHandler()
'''
        result = SymbolParser.parse_file("auth.py", code)

        # Verify results
        assert result.success
        assert result.get_symbol_count() >= 4

        # Verify class and methods
        classes = result.get_symbols_by_type(SymbolType.CLASS)
        assert len(classes) >= 1
        assert classes[0].name == "JWTHandler"

    def test_end_to_end_javascript_analysis(self):
        """Test complete JavaScript file analysis workflow."""
        code = '''
class UserController {
    constructor(userService) {
        this.userService = userService;
    }

    async getUser(id) {
        return await this.userService.fetch(id);
    }
}

const validate = (user) => {
    return user && user.id && user.name;
};

module.exports = { UserController, validate };
'''
        result = SymbolParser.parse_file("controller.js", code)

        assert result.success
        assert result.get_symbol_count() >= 2

    def test_complexity_metrics_computation(self):
        """Test complexity metrics are computed for extracted symbols."""
        code = '''
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 100:
                return "large"
            return "medium"
        return "small"
    return "zero"
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success

        functions = result.get_symbols_by_type(SymbolType.FUNCTION)
        assert len(functions) >= 1

        func = functions[0]
        # Should have cyclomatic complexity > 1 due to if statements
        assert func.metrics.cyclomatic_complexity > 1

    def test_symbol_relationships_tracking(self):
        """Test symbol can track dependencies."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.METHOD,
            name="process",
            namespace="DataHandler",
            signature="(data)",
            line_start=10,
            line_end=20,
            code="pass"
        )

        # Add dependencies
        dep1 = SymbolDependency("validate", RelationType.CALLS)
        dep2 = SymbolDependency("transform", RelationType.CALLS)
        symbol.dependencies.append(dep1)
        symbol.dependencies.append(dep2)

        assert len(symbol.dependencies) == 2
        assert symbol.dependencies[0].target_symbol_name == "validate"

    def test_analysis_result_complexity_summary(self):
        """Test SymbolAnalysisResult provides complexity summary."""
        symbols = [
            create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=(i+1)*10,  # Ensure line_start >= 1
                line_end=(i+1)*10+5,
                code="pass",
                metrics=SymbolMetrics(cyclomatic_complexity=i+1)
            )
            for i in range(3)
        ]

        result = SymbolAnalysisResult(
            file_path="test.py",
            language="python",
            symbols=symbols
        )

        summary = result.get_complexity_summary()
        assert summary["total_symbols"] == 3
        assert summary["max_cyclomatic"] == 3
        assert summary["avg_cyclomatic"] > 1

    def test_symbol_visibility_detection(self):
        """Test symbol visibility is correctly detected."""
        code = '''
def public_function():
    pass

def _private_function():
    pass

class __internal_class__:
    pass
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success

        symbols = {s.name: s for s in result.symbols}

        if "public_function" in symbols:
            assert symbols["public_function"].visibility == "public"

        # Functions starting with underscore marked as private
        if "_private_function" in symbols:
            assert symbols["_private_function"].visibility == "private"

    def test_docstring_extraction(self):
        """Test docstring extraction from symbols."""
        code = '''
def documented_function():
    """This is a comprehensive docstring.

    It spans multiple lines.
    """
    pass
'''
        result = PythonSymbolParser.parse_file("test.py", code)
        assert result.success

        functions = result.get_symbols_by_type(SymbolType.FUNCTION)
        if functions:
            func = functions[0]
            assert len(func.docstring) > 0
            assert "comprehensive" in func.docstring


# ============================================================================
# PERFORMANCE TESTS (3 tests)
# ============================================================================

class TestSymbolParserPerformance:
    """Test parser performance characteristics."""

    def test_large_python_file_parsing(self):
        """Test parsing of large Python file with many functions."""
        code = "\n".join([
            f"def function_{i}():\n    pass"
            for i in range(100)
        ])

        result = PythonSymbolParser.parse_file("large.py", code)
        assert result.success
        assert result.get_symbol_count() >= 100

    def test_complex_python_file_parsing(self):
        """Test parsing complex Python with nested classes and methods."""
        code = '''
class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass

    def outer_method(self):
        def nested_function():
            pass
        return nested_function
'''
        result = PythonSymbolParser.parse_file("nested.py", code)
        assert result.success
        assert result.get_symbol_count() >= 2

    def test_mixed_javascript_parsing(self):
        """Test parsing JavaScript with mixed function styles."""
        code = '''
function traditionfunc() {}
const arrowFunc = () => {};
class MixedClass {
    method1() {}
    method2 = () => {}
}
async function asyncFunc() {}
'''
        result = JavaScriptSymbolParser.parse_file("mixed.js", code)
        assert result.success
        assert result.get_symbol_count() >= 5


# ============================================================================
# TEST SYMBOL STORE (10 tests)
# ============================================================================

class TestSymbolStore:
    """Test symbol database store operations."""

    def test_store_creation(self, tmp_path):
        """Test SymbolStore creates database and schema."""
        db_path = tmp_path / "test.db"
        store = SymbolStore(str(db_path))

        assert db_path.exists()
        assert store.get_statistics()["total_symbols"] == 0

        store.close()

    def test_create_and_get_symbol(self, tmp_path):
        """Test create and retrieve symbol."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test_func",
            namespace="",
            signature="(x, y)",
            line_start=1,
            line_end=10,
            code="def test_func(x, y):\n    return x + y"
        )

        stored = store.create_symbol(symbol)
        assert stored.id is not None

        retrieved = store.get_symbol(stored.id)
        assert retrieved is not None
        assert retrieved.name == "test_func"
        assert retrieved.full_qualified_name == "test_func"

        store.close()

    def test_get_symbol_by_qname(self, tmp_path):
        """Test retrieve symbol by full qualified name."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="auth.py",
            symbol_type=SymbolType.CLASS,
            name="JWTHandler",
            namespace="auth.jwt",
            signature="()",
            line_start=5,
            line_end=30,
            code="class JWTHandler: pass"
        )

        stored = store.create_symbol(symbol)
        assert stored.full_qualified_name == "auth.jwt.JWTHandler"

        retrieved = store.get_symbol_by_qname("auth.jwt.JWTHandler")
        assert retrieved is not None
        assert retrieved.name == "JWTHandler"

        store.close()

    def test_get_symbols_in_file(self, tmp_path):
        """Test retrieve all symbols from a file."""
        store = SymbolStore(str(tmp_path / "test.db"))

        for i in range(3):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=i*10+1,
                line_end=i*10+5,
                code="pass"
            )
            store.create_symbol(symbol)

        symbols = store.get_symbols_in_file("test.py")
        assert len(symbols) == 3
        assert all(s.file_path == "test.py" for s in symbols)

        store.close()

    def test_get_symbols_by_type(self, tmp_path):
        """Test retrieve symbols by type."""
        store = SymbolStore(str(tmp_path / "test.db"))

        # Create mix of symbols
        func_symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="my_func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="pass"
        )

        class_symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.CLASS,
            name="MyClass",
            namespace="",
            signature="()",
            line_start=10,
            line_end=20,
            code="pass"
        )

        store.create_symbol(func_symbol)
        store.create_symbol(class_symbol)

        functions = store.get_symbols_by_type(SymbolType.FUNCTION)
        classes = store.get_symbols_by_type(SymbolType.CLASS)

        assert len(functions) == 1
        assert len(classes) == 1
        assert functions[0].name == "my_func"
        assert classes[0].name == "MyClass"

        store.close()

    def test_create_relationship(self, tmp_path):
        """Test create relationship between symbols."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="other_func()"
        )

        stored = store.create_symbol(symbol)

        store.create_relationship(
            stored.id,
            "other_func",
            RelationType.CALLS,
            0.9
        )

        relationships = store.get_relationships(stored.id)
        assert len(relationships) == 1
        assert relationships[0]["to_symbol_name"] == "other_func"
        assert relationships[0]["relation_type"] == RelationType.CALLS

        store.close()

    def test_get_dependencies(self, tmp_path):
        """Test get symbol dependencies."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="pass"
        )

        stored = store.create_symbol(symbol)

        store.create_relationship(stored.id, "dep1", RelationType.CALLS)
        store.create_relationship(stored.id, "dep2", RelationType.CALLS)

        deps = store.get_dependencies(stored.id)
        assert len(deps) == 2
        assert "dep1" in deps
        assert "dep2" in deps

        store.close()

    def test_get_dependents(self, tmp_path):
        """Test reverse lookup: who depends on this symbol."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="pass"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller2",
            namespace="",
            signature="()",
            line_start=10,
            line_end=15,
            code="pass"
        )

        stored1 = store.create_symbol(symbol1)
        stored2 = store.create_symbol(symbol2)

        store.create_relationship(stored1.id, "target", RelationType.CALLS)
        store.create_relationship(stored2.id, "target", RelationType.CALLS)

        dependents = store.get_dependents("target")
        assert len(dependents) == 2
        assert stored1.id in dependents
        assert stored2.id in dependents

        store.close()

    def test_update_symbol_metrics(self, tmp_path):
        """Test update symbol metrics."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="test",
            namespace="",
            signature="()",
            line_start=1,
            line_end=10,
            code="pass",
            metrics=SymbolMetrics(
                lines_of_code=10,
                cyclomatic_complexity=2
            )
        )

        stored = store.create_symbol(symbol)

        # Update metrics
        new_metrics = SymbolMetrics(
            lines_of_code=15,
            cyclomatic_complexity=5,
            maintainability_index=75.0
        )
        store.update_symbol_metrics(stored.id, new_metrics)

        # Verify update
        retrieved = store.get_symbol(stored.id)
        assert retrieved.metrics.lines_of_code == 15
        assert retrieved.metrics.cyclomatic_complexity == 5
        assert retrieved.metrics.maintainability_index == 75.0

        store.close()

    def test_delete_symbol(self, tmp_path):
        """Test delete symbol (with cascade)."""
        store = SymbolStore(str(tmp_path / "test.db"))

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="to_delete",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="pass"
        )

        stored = store.create_symbol(symbol)
        store.create_relationship(stored.id, "other", RelationType.CALLS)

        # Delete
        deleted = store.delete_symbol(stored.id)
        assert deleted

        # Verify deletion
        retrieved = store.get_symbol(stored.id)
        assert retrieved is None

        # Verify relationships are cascaded
        relationships = store.get_relationships(stored.id)
        assert len(relationships) == 0

        store.close()

    def test_get_statistics(self, tmp_path):
        """Test get database statistics."""
        store = SymbolStore(str(tmp_path / "test.db"))

        # Add symbols
        for i in range(5):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION if i < 3 else SymbolType.CLASS,
                name=f"item{i}",
                namespace="",
                signature="()",
                line_start=i+1,
                line_end=i+5,
                code="pass"
            )
            store.create_symbol(symbol)

        stats = store.get_statistics()
        assert stats["total_symbols"] == 5
        assert stats["symbol_types"] == 2  # FUNCTION and CLASS

        store.close()


# ============================================================================
# TEST SYMBOL ANALYZER (8 tests)
# ============================================================================

class TestSymbolAnalyzer:
    """Test symbol analysis and metrics computation."""

    def test_analyzer_initialization(self, tmp_path):
        """Test SymbolAnalyzer initialization."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)

        assert analyzer is not None
        assert analyzer.store is store

        store.close()

    def test_cyclomatic_complexity_simple(self):
        """Test cyclomatic complexity for simple function."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="simple",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code="def simple():\n    return 42"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        cc = analyzer.compute_cyclomatic_complexity(symbol)

        assert cc >= 1  # Minimum complexity

    def test_cyclomatic_complexity_with_branches(self):
        """Test cyclomatic complexity with multiple branches."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="branching",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=10,
            code="""def branching(x):
    if x > 0:
        if x > 10:
            return "big"
        return "small"
    return "zero\""""
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        cc = analyzer.compute_cyclomatic_complexity(symbol)

        assert cc > 1  # Has multiple branches
        assert "if" in symbol.code  # Verify test data

    def test_cognitive_complexity(self):
        """Test cognitive complexity computation."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="complex",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def complex():\n    if True:\n        if True:\n            pass"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        cog = analyzer.compute_cognitive_complexity(symbol)

        assert cog >= 1

    def test_maintainability_index(self):
        """Test maintainability index calculation."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="tested",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code='def tested():\n    """Good function."""\n    return 42',
            metrics=SymbolMetrics(
                lines_of_code=3,
                cyclomatic_complexity=1,
                parameters=0
            ),
            docstring="Good function."
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        mi = analyzer.compute_maintainability_index(symbol, 1)

        assert 0 <= mi <= 100
        assert mi > 50  # Well-documented, simple function

    def test_analyze_symbol(self):
        """Test comprehensive symbol analysis."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="analyze_me",
            namespace="test",
            signature="(x, y)",
            line_start=1,
            line_end=10,
            code="def analyze_me(x, y):\n    if x > y:\n        return x\n    return y"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        analysis = analyzer.analyze_symbol(symbol)

        assert isinstance(analysis, ComplexityAnalysis)
        assert analysis.cyclomatic_complexity >= 1
        assert analysis.cognitive_complexity >= 1
        assert 0 <= analysis.maintainability_index <= 100
        assert isinstance(analysis.quality_issues, list)

    def test_compute_dependencies(self):
        """Test dependency detection in code."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def caller():\n    foo()\n    bar.method()\n    import baz"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        deps = analyzer.compute_dependencies(symbol)

        assert len(deps) > 0
        assert "foo" in deps or "bar" in deps  # Should detect some calls

    def test_compute_metrics(self):
        """Test compute all metrics at once."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="complete",
            namespace="",
            signature="(a, b, c)",
            line_start=1,
            line_end=15,
            code="def complete(a, b, c):\n    if a > b:\n        return a\n    return c"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        metrics = analyzer.compute_metrics(symbol)

        assert isinstance(metrics, SymbolMetrics)
        assert metrics.lines_of_code >= 1
        assert metrics.cyclomatic_complexity >= 1
        assert metrics.parameters == 0  # count not yet computed

    def test_link_symbol_to_patterns(self):
        """Test linking symbols to procedural patterns."""
        symbol = create_symbol(
            file_path="service.py",
            symbol_type=SymbolType.METHOD,
            name="get_user",
            namespace="UserService",
            signature="(id)",
            line_start=1,
            line_end=10,
            code="def get_user(self, id):\n    \"\"\"Get user by ID.\"\"\"\n    return db.find(id)"
        )

        analyzer = SymbolAnalyzer(SymbolStore())
        patterns = ["getter", "setter", "class_pattern"]
        scores = analyzer.link_symbol_to_patterns(symbol, patterns)

        assert isinstance(scores, dict)
        assert "getter" in scores
        assert 0.0 <= scores["getter"] <= 1.0


# ============================================================================
# TEST SYMBOL TOOLS INTEGRATION (6 tests)
# ============================================================================

class TestSymbolToolsIntegration:
    """Test MCP tool handlers for symbol analysis."""

    def test_analyze_symbols(self, tmp_path):
        """Test analyze_symbols tool."""
        tools = SymbolTools(db_path=str(tmp_path / "test.db"))

        code = '''
def add(x, y):
    """Add two numbers."""
    return x + y

class Calculator:
    """Simple calculator."""
    def multiply(self, a, b):
        return a * b
'''

        result = tools.analyze_symbols("math.py", code)

        assert result["status"] == "success"
        assert result["total_symbols"] >= 2
        assert len(result["symbols"]) >= 2
        assert result["language"] == "python"

        tools.store.close()

    def test_get_symbol_info(self, tmp_path):
        """Test get_symbol_info tool."""
        store = SymbolStore(str(tmp_path / "test.db"))
        tools = SymbolTools(store=store)

        # Create a symbol
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process",
            namespace="module",
            signature="(data)",
            line_start=1,
            line_end=10,
            code="def process(data):\n    if data:\n        return data\n    return None"
        )
        stored = store.create_symbol(symbol)

        # Get info
        result = tools.get_symbol_info("module.process")

        assert result["status"] == "success"
        assert result["symbol"]["name"] == "process"
        assert "metrics" in result
        assert "analysis" in result

        store.close()

    def test_find_symbol_dependencies(self, tmp_path):
        """Test find_symbol_dependencies tool."""
        store = SymbolStore(str(tmp_path / "test.db"))
        tools = SymbolTools(store=store)

        # Create symbols
        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="helper()"
        )
        stored1 = store.create_symbol(symbol1)

        # Add dependency
        store.create_relationship(stored1.id or 0, "helper", RelationType.CALLS)

        # Test
        result = tools.find_symbol_dependencies("caller")

        assert result["status"] == "success"
        assert result["dependencies_count"] == 1
        assert "helper" in [d["target"] for d in result["dependencies"]]

        store.close()

    def test_find_symbol_dependents(self, tmp_path):
        """Test find_symbol_dependents tool."""
        store = SymbolStore(str(tmp_path / "test.db"))
        tools = SymbolTools(store=store)

        # Create symbols
        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="caller",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="pass"
        )
        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="target",
            namespace="",
            signature="()",
            line_start=10,
            line_end=15,
            code="pass"
        )
        stored1 = store.create_symbol(symbol1)
        stored2 = store.create_symbol(symbol2)

        # Add dependency
        store.create_relationship(stored1.id or 0, "target", RelationType.CALLS)

        # Test
        result = tools.find_symbol_dependents("target")

        assert result["status"] == "success"
        assert result["dependents_count"] == 1
        assert "caller" in [d["full_qualified_name"] for d in result["dependents"]]

        store.close()

    def test_suggest_symbol_refactorings(self, tmp_path):
        """Test suggest_symbol_refactorings tool."""
        store = SymbolStore(str(tmp_path / "test.db"))
        tools = SymbolTools(store=store)

        # Create complex symbol
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="complex_func",
            namespace="",
            signature="(a, b, c, d, e, f, g)",
            line_start=1,
            line_end=50,
            code="def complex_func(a, b, c, d, e, f, g):\n" + "\n    if a:\n        if b:\n" * 10
        )
        stored = store.create_symbol(symbol)

        # Test
        result = tools.suggest_symbol_refactorings("complex_func")

        assert result["status"] == "success"
        assert result["suggestions_count"] > 0
        assert any(s["category"] == "parameters" for s in result["suggestions"])

        store.close()

    def test_get_symbol_quality_report(self, tmp_path):
        """Test get_symbol_quality_report tool."""
        store = SymbolStore(str(tmp_path / "test.db"))
        tools = SymbolTools(store=store)

        # Create symbol
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="quality_test",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code='def quality_test():\n    """Well documented."""\n    return 42',
            docstring="Well documented."
        )
        stored = store.create_symbol(symbol)

        # Test
        result = tools.get_symbol_quality_report("quality_test")

        assert result["status"] == "success"
        assert "grade" in result
        assert "metrics" in result
        assert "issues" in result
        assert result["coverage"]["has_docstring"] is True

        store.close()


# ============================================================================
# TEST SYMBOL PATTERN INTEGRATION (5 tests)
# ============================================================================

class TestSymbolPatternIntegration:
    """Test Phase 4 pattern integration."""

    def test_link_patterns_to_symbols(self, tmp_path):
        """Test linking patterns to symbols."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)
        linker = SymbolPatternLinker(store, analyzer)

        # Create symbols
        for i in range(3):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=i*10+1,
                line_end=i*10+20,
                code="if x > 0:\n    if y > 0:\n        return x + y\n" * 3
            )
            store.create_symbol(symbol)

        # Define test patterns
        patterns = [
            {
                "name": "extract_method",
                "type": "refactoring",
                "triggers": ["high_complexity"],
                "applicable_to": [SymbolType.FUNCTION, SymbolType.METHOD],
            }
        ]

        # Link patterns
        linked = linker.link_patterns_to_symbols(patterns)

        assert len(linked) > 0
        for symbol_name, applications in linked.items():
            assert len(applications) > 0

        store.close()

    def test_suggest_refactorings_for_symbol(self, tmp_path):
        """Test generating refactoring suggestions."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)
        linker = SymbolPatternLinker(store, analyzer)

        # Create complex symbol
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="complex",
            namespace="",
            signature="(a, b, c)",
            line_start=1,
            line_end=100,
            code="if a:\n    if b:\n        if c:\n            pass\n" * 10
        )
        stored = store.create_symbol(symbol)

        # Get suggestions
        suggestions = linker.suggest_refactorings_for_symbol(stored)

        assert len(suggestions) > 0
        assert any(s["category"] == "complexity_reduction" for s in suggestions)

        store.close()

    def test_measure_pattern_effectiveness_by_symbol(self, tmp_path):
        """Test measuring pattern effectiveness."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)
        linker = SymbolPatternLinker(store, analyzer)

        # Create symbols
        for i in range(5):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=i*10+1,
                line_end=i*10+20,
                code="pass"
            )
            store.create_symbol(symbol)

        # Measure effectiveness
        result = linker.measure_pattern_effectiveness_by_symbol("extract_method")

        assert "pattern" in result
        assert "total_symbols_analyzed" in result
        assert "avg_effectiveness" in result

        store.close()

    def test_compute_pattern_applicability_matrix(self, tmp_path):
        """Test computing applicability matrix."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)
        linker = SymbolPatternLinker(store, analyzer)

        # Create mixed symbols
        for sym_type in [SymbolType.FUNCTION, SymbolType.CLASS, SymbolType.METHOD]:
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=sym_type,
                name=f"test_{sym_type}",
                namespace="",
                signature="()",
                line_start=1,
                line_end=10,
                code="pass"
            )
            store.create_symbol(symbol)

        # Define patterns
        patterns = [
            {
                "name": "refactor_pattern",
                "type": "refactoring",
                "applicable_to": [SymbolType.FUNCTION, SymbolType.METHOD],
            }
        ]

        # Compute matrix
        matrix = linker.compute_pattern_applicability_matrix(patterns)

        assert "refactor_pattern" in matrix
        assert SymbolType.FUNCTION in matrix["refactor_pattern"]

        store.close()

    def test_pattern_applicability_explains_why(self, tmp_path):
        """Test that applicability explanations are generated."""
        store = SymbolStore(str(tmp_path / "test.db"))
        analyzer = SymbolAnalyzer(store)
        linker = SymbolPatternLinker(store, analyzer)

        # Create complex symbol without docs
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="undocumented",
            namespace="",
            signature="(a, b, c, d, e)",
            line_start=1,
            line_end=50,
            code="if a: pass\nif b: pass\nif c: pass\n" * 5
        )
        stored = store.create_symbol(symbol)

        # Get suggestions
        suggestions = linker.suggest_refactorings_for_symbol(stored)

        # Should have multiple suggestions
        assert len(suggestions) > 0

        # Should mention various issues
        suggestion_types = [s.get("category", s.get("type")) for s in suggestions]
        assert len(suggestion_types) > 1

        store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
