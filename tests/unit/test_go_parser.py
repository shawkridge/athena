"""Tests for Go parser."""

import pytest
from pathlib import Path

from athena.code_search.go_parser import GoParser


@pytest.fixture
def go_parser():
    """Create Go parser."""
    return GoParser("go")


class TestGoFunctionExtraction:
    """Test Go function extraction."""

    def test_extract_regular_function(self, go_parser):
        """Test extracting regular function."""
        code = """
func Authenticate(user string) bool {
    return ValidateUser(user)
}
"""
        units = go_parser.extract_functions(code, "auth.go")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "Authenticate" in names

    def test_extract_method_with_receiver(self, go_parser):
        """Test extracting method with receiver."""
        code = """
func (s *Server) Start() error {
    return s.listen()
}
"""
        units = go_parser.extract_functions(code, "server.go")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "Start" in names

    def test_extract_function_with_multiple_returns(self, go_parser):
        """Test extracting function with multiple return values."""
        code = """
func GetUser(id string) (*User, error) {
    user, err := findUser(id)
    return user, err
}
"""
        units = go_parser.extract_functions(code, "user.go")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "GetUser" in names

    def test_extract_function_with_variadic_params(self, go_parser):
        """Test extracting function with variadic parameters."""
        code = """
func PrintLines(lines ...string) {
    for _, line := range lines {
        fmt.Println(line)
    }
}
"""
        units = go_parser.extract_functions(code, "print.go")
        assert len(units) >= 1

    def test_extract_init_function(self, go_parser):
        """Test extracting init function."""
        code = """
func init() {
    setupLogging()
}
"""
        units = go_parser.extract_functions(code, "main.go")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "init" in names

    def test_extract_multiple_functions(self, go_parser):
        """Test extracting multiple functions."""
        code = """
func Function1() string {
    return "one"
}

func (r *Receiver) Method1() {
    doSomething()
}

func Function2() int {
    return 2
}
"""
        units = go_parser.extract_functions(code, "test.go")
        assert len(units) >= 2

    def test_function_with_dependencies(self, go_parser):
        """Test function dependencies extraction."""
        code = """
func Process(data string) error {
    if err := validate(data); err != nil {
        return handleError(err)
    }
    return save(data)
}
"""
        units = go_parser.extract_functions(code, "process.go")
        assert len(units) >= 1
        # Check dependencies
        deps = units[0].dependencies
        assert "validate" in deps or "save" in deps


class TestGoStructExtraction:
    """Test Go struct extraction."""

    def test_extract_struct(self, go_parser):
        """Test extracting struct."""
        code = """
type User struct {
    ID   string
    Name string
}
"""
        units = go_parser.extract_classes(code, "user.go")
        assert len(units) >= 1
        assert units[0].name == "User"
        assert units[0].type == "struct"

    def test_extract_struct_with_embedded_types(self, go_parser):
        """Test extracting struct with embedded types."""
        code = """
type Handler struct {
    Reader
    Writer
    Logger
}
"""
        units = go_parser.extract_classes(code, "handler.go")
        assert len(units) >= 1
        assert units[0].name == "Handler"
        # Check embedded types are dependencies
        deps = units[0].dependencies
        assert "Reader" in deps or "Writer" in deps

    def test_extract_interface(self, go_parser):
        """Test extracting interface."""
        code = """
type Reader interface {
    Read(p []byte) (n int, err error)
    Close() error
}
"""
        units = go_parser.extract_classes(code, "io.go")
        assert len(units) >= 1
        assert units[0].name == "Reader"
        assert units[0].type == "interface"

    def test_extract_interface_with_embedding(self, go_parser):
        """Test extracting interface with embedded interfaces."""
        code = """
type ReadWriter interface {
    Reader
    Writer
}
"""
        units = go_parser.extract_classes(code, "io.go")
        assert len(units) >= 1
        assert units[0].name == "ReadWriter"
        deps = units[0].dependencies
        assert "Reader" in deps or "Writer" in deps

    def test_extract_multiple_types(self, go_parser):
        """Test extracting multiple type definitions."""
        code = """
type User struct {
    ID string
}

type UserHandler struct {
    User
}

type UserService interface {
    GetUser(id string) (*User, error)
}
"""
        units = go_parser.extract_classes(code, "types.go")
        assert len(units) >= 2
        names = [u.name for u in units]
        assert "User" in names or "UserHandler" in names


class TestGoImportExtraction:
    """Test Go import extraction."""

    def test_extract_single_import(self, go_parser):
        """Test extracting single import."""
        code = """
import "fmt"
"""
        units = go_parser.extract_imports(code, "test.go")
        assert len(units) >= 1
        assert units[0].type == "import"
        assert "fmt" in units[0].name

    def test_extract_grouped_imports(self, go_parser):
        """Test extracting grouped imports."""
        code = """
import (
    "fmt"
    "os"
    "strings"
)
"""
        units = go_parser.extract_imports(code, "test.go")
        assert len(units) >= 3
        names = {u.name for u in units}
        assert "fmt" in names
        assert "os" in names

    def test_extract_import_with_alias(self, go_parser):
        """Test extracting import with alias."""
        code = """
import . "fmt"
import alias "mypackage"
"""
        units = go_parser.extract_imports(code, "test.go")
        # Should extract at least the aliased import
        assert len(units) >= 1
        # Check that mypackage is in the imports
        names = {u.name for u in units}
        assert "mypackage" in names

    def test_extract_mixed_imports(self, go_parser):
        """Test extracting mixed single and grouped imports."""
        code = """
import "fmt"

import (
    "os"
    "io"
)

import . "path/filepath"
"""
        units = go_parser.extract_imports(code, "test.go")
        # Should extract at least the main imports (fmt, os, io)
        assert len(units) >= 3
        # Check that key imports are present
        names = {u.name for u in units}
        assert "fmt" in names
        assert "os" in names or "io" in names


class TestGoCompleteExtraction:
    """Test complete extraction of all units."""

    def test_extract_all(self, go_parser):
        """Test extracting all units from file."""
        code = """
package main

import (
    "fmt"
    "log"
)

type Server struct {
    Port int
    Handler Handler
}

func (s *Server) Start() error {
    return s.listen()
}

func main() {
    server := &Server{Port: 8080}
    if err := server.Start(); err != nil {
        log.Fatal(err)
    }
}
"""
        units = go_parser.extract_all(code, "main.go")
        assert len(units) > 0

        # Check we got different types
        types = {u.type for u in units}
        assert "import" in types or "struct" in types

    def test_extract_with_comments(self, go_parser):
        """Test extracting with comments."""
        code = """
// Start the server
func (s *Server) Start() error {
    return s.listen()
}
"""
        units = go_parser.extract_functions(code, "server.go")
        assert len(units) >= 1
        # Should have extracted comment
        docstring = units[0].docstring
        assert len(docstring) > 0

    def test_extract_complex_package(self, go_parser):
        """Test with complex Go package code."""
        code = """
package user

import (
    "context"
    "database/sql"
    "errors"
)

type User struct {
    ID    int
    Name  string
    Email string
}

type Repository interface {
    GetUser(ctx context.Context, id int) (*User, error)
    SaveUser(ctx context.Context, user *User) error
    DeleteUser(ctx context.Context, id int) error
}

type userRepository struct {
    db *sql.DB
}

func (r *userRepository) GetUser(ctx context.Context, id int) (*User, error) {
    user := &User{}
    err := r.db.QueryRowContext(ctx, "SELECT id, name, email FROM users WHERE id = $1", id).
        Scan(&user.ID, &user.Name, &user.Email)
    if err != nil {
        if err == sql.ErrNoRows {
            return nil, errors.New("user not found")
        }
        return nil, err
    }
    return user, nil
}

func NewRepository(db *sql.DB) Repository {
    return &userRepository{db: db}
}
"""
        units = go_parser.extract_all(code, "user.go")
        assert len(units) > 0


class TestGoEdgeCases:
    """Test edge cases."""

    def test_empty_code(self, go_parser):
        """Test with empty code."""
        units = go_parser.extract_all("", "test.go")
        assert units == []

    def test_code_with_syntax_errors(self, go_parser):
        """Test with syntax errors (should not crash)."""
        code = """
func Broken(
    // missing closing paren and brace
"""
        # Should not raise exception
        units = go_parser.extract_all(code, "test.go")
        assert isinstance(units, list)

    def test_code_with_no_functions(self, go_parser):
        """Test with code containing no functions."""
        code = """
package main

import "fmt"

const Version = "1.0"
"""
        units = go_parser.extract_functions(code, "constants.go")
        # Should extract no functions
        assert len(units) == 0

    def test_nested_functions(self, go_parser):
        """Test extracting nested functions."""
        code = """
func Outer() {
    var inner func() = func() {
        doSomething()
    }
    inner()
}
"""
        units = go_parser.extract_functions(code, "nested.go")
        # Should extract outer at minimum
        names = [u.name for u in units]
        assert "Outer" in names

    def test_function_with_long_signature(self, go_parser):
        """Test function with very long signature."""
        code = """
func ProcessDataWithMultipleSteps(
    ctx context.Context,
    data string,
    options ProcessOptions,
    callback func(result string) error,
) (string, error) {
    return handleData(data), nil
}
"""
        units = go_parser.extract_functions(code, "processor.go")
        assert len(units) >= 1
        # Signature should be truncated but still valid
        assert len(units[0].signature) > 0


class TestGoDocstringExtraction:
    """Test comment extraction."""

    def test_extract_function_comment(self, go_parser):
        """Test extracting function comments."""
        code = """
// Start starts the server on the specified port
func (s *Server) Start() error {
    return s.listen()
}
"""
        units = go_parser.extract_functions(code, "server.go")
        assert len(units) >= 1
        # Should have extracted comment
        docstring = units[0].docstring
        assert len(docstring) > 0

    def test_extract_struct_comment(self, go_parser):
        """Test extracting struct comments."""
        code = """
// User represents a user in the system
type User struct {
    ID   string
    Name string
}
"""
        units = go_parser.extract_classes(code, "user.go")
        assert len(units) >= 1

    def test_extract_multiline_comment(self, go_parser):
        """Test extracting multiline comments."""
        code = """
// Process handles data processing
// It validates and transforms the input
// Returns the processed result or an error
func Process(data string) (string, error) {
    return transform(data), nil
}
"""
        units = go_parser.extract_functions(code, "process.go")
        assert len(units) >= 1


class TestGoIntegration:
    """Test Go parser integration."""

    def test_parser_factory(self):
        """Test parser factory creates Go parser."""
        from athena.code_search.parser import CodeParser

        go_parser = CodeParser("go")
        assert go_parser.language == "go"
        assert go_parser.parser is not None

    def test_parser_extract_all(self):
        """Test CodeParser extracts from Go."""
        from athena.code_search.parser import CodeParser

        parser = CodeParser("go")
        code = """
package main

import "fmt"

type Logger interface {
    Log(message string)
}

func main() {
    logger := NewLogger()
    logger.Log("Hello, World!")
}

func NewLogger() Logger {
    return &simpleLogger{}
}

type simpleLogger struct{}

func (l *simpleLogger) Log(message string) {
    fmt.Println(message)
}
"""
        units = parser.extract_all(code, "main.go")
        assert len(units) > 0

    def test_go_and_python_parsers_independent(self):
        """Test Go and Python parsers work independently."""
        from athena.code_search.parser import CodeParser

        py_parser = CodeParser("python")
        go_parser = CodeParser("go")

        py_code = """
def authenticate(user):
    return validate_user(user)
"""

        go_code = """
func Authenticate(user string) bool {
    return ValidateUser(user)
}
"""

        py_units = py_parser.extract_all(py_code, "auth.py")
        go_units = go_parser.extract_all(go_code, "auth.go")

        assert len(py_units) > 0
        assert len(go_units) > 0
        # Both should find authenticate
        assert any(u.name == "authenticate" for u in py_units)
        assert any(u.name == "Authenticate" for u in go_units)

    def test_all_parsers_work_together(self):
        """Test all language parsers work independently."""
        from athena.code_search.parser import CodeParser

        py_parser = CodeParser("python")
        js_parser = CodeParser("javascript")
        java_parser = CodeParser("java")
        go_parser = CodeParser("go")

        # All parsers should be initialized
        assert py_parser.parser is not None
        assert js_parser.parser is not None
        assert java_parser.parser is not None
        assert go_parser.parser is not None

        # Test basic extraction works for all
        py_code = "def test(): pass"
        js_code = "function test() {}"
        java_code = "public void test() {}"
        go_code = "func Test() {}"

        py_units = py_parser.extract_all(py_code, "test.py")
        js_units = js_parser.extract_all(js_code, "test.js")
        java_units = java_parser.extract_all(java_code, "Test.java")
        go_units = go_parser.extract_all(go_code, "test.go")

        assert len(py_units) > 0
        assert len(js_units) > 0
        assert len(java_units) > 0
        assert len(go_units) > 0
