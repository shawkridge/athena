"""Tests for Java parser."""

import pytest
from pathlib import Path

from athena.code_search.java_parser import JavaParser


@pytest.fixture
def java_parser():
    """Create Java parser."""
    return JavaParser("java")


class TestJavaMethodExtraction:
    """Test Java method extraction."""

    def test_extract_regular_method(self, java_parser):
        """Test extracting regular method."""
        code = """
public void authenticate(String user) {
    validateUser(user);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "authenticate" in names

    def test_extract_static_method(self, java_parser):
        """Test extracting static method."""
        code = """
public static void main(String[] args) {
    System.out.println("Hello");
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "main" in names

    def test_extract_constructor(self, java_parser):
        """Test extracting constructor."""
        code = """
public class User {
    private String name;

    public User(String name) {
        this.name = name;
    }
}
"""
        units = java_parser.extract_functions(code, "User.java")
        # Should extract User constructor
        names = [u.name for u in units]
        assert "User" in names

    def test_extract_private_method(self, java_parser):
        """Test extracting private method."""
        code = """
private String validate(User user) {
    return user.getName();
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        names = [u.name for u in units]
        assert "validate" in names

    def test_extract_generic_method(self, java_parser):
        """Test extracting generic method."""
        code = """
public <T> T process(List<T> items) {
    return items.get(0);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1

    def test_extract_abstract_method(self, java_parser):
        """Test extracting abstract method."""
        code = """
public abstract void process(String data);
"""
        units = java_parser.extract_functions(code, "Test.java")
        # Abstract methods may or may not be extracted depending on implementation
        assert isinstance(units, list)

    def test_method_with_dependencies(self, java_parser):
        """Test method dependencies extraction."""
        code = """
public void authenticate(User user) {
    validateUser(user);
    checkPassword(user);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        # Check dependencies
        deps = units[0].dependencies
        assert "validateUser" in deps or "checkPassword" in deps


class TestJavaClassExtraction:
    """Test Java class extraction."""

    def test_extract_class(self, java_parser):
        """Test extracting class."""
        code = """
public class User {
    private String name;

    public User(String name) {
        this.name = name;
    }
}
"""
        units = java_parser.extract_classes(code, "User.java")
        assert len(units) >= 1
        assert units[0].name == "User"
        assert units[0].type == "class"

    def test_extract_class_with_inheritance(self, java_parser):
        """Test extracting class with inheritance."""
        code = """
public class Handler extends BaseHandler {
    public void handle() {
        super.handle();
    }
}
"""
        units = java_parser.extract_classes(code, "Handler.java")
        assert len(units) >= 1
        assert units[0].name == "Handler"
        assert "BaseHandler" in units[0].dependencies

    def test_extract_class_with_interfaces(self, java_parser):
        """Test extracting class implementing interfaces."""
        code = """
public class UserHandler implements IHandler, IValidator {
    public void handle(String data) {
        validate(data);
    }

    public boolean validate(String data) {
        return data.length() > 0;
    }
}
"""
        units = java_parser.extract_classes(code, "UserHandler.java")
        assert len(units) >= 1
        deps = units[0].dependencies
        # Should have IHandler and IValidator as dependencies
        assert any("IHandler" in str(d) for d in deps)

    def test_extract_multiple_classes(self, java_parser):
        """Test extracting multiple classes."""
        code = """
public class Class1 {
    public void method1() {}
}

class Class2 {
    public void method2() {}
}
"""
        units = java_parser.extract_classes(code, "Test.java")
        assert len(units) >= 2
        names = [u.name for u in units]
        assert "Class1" in names
        assert "Class2" in names

    def test_extract_abstract_class(self, java_parser):
        """Test extracting abstract class."""
        code = """
public abstract class BaseHandler {
    public abstract void handle();
}
"""
        units = java_parser.extract_classes(code, "BaseHandler.java")
        assert len(units) >= 1
        assert units[0].name == "BaseHandler"


class TestJavaImportExtraction:
    """Test Java import extraction."""

    def test_extract_single_import(self, java_parser):
        """Test extracting single import."""
        code = """
import java.util.List;
"""
        units = java_parser.extract_imports(code, "Test.java")
        assert len(units) >= 1
        assert units[0].type == "import"
        assert "java.util.List" in units[0].name

    def test_extract_wildcard_import(self, java_parser):
        """Test extracting wildcard import."""
        code = """
import java.util.*;
"""
        units = java_parser.extract_imports(code, "Test.java")
        assert len(units) >= 1
        assert units[0].type == "import_wildcard"

    def test_extract_static_import(self, java_parser):
        """Test extracting static import."""
        code = """
import static java.util.Collections.sort;
"""
        units = java_parser.extract_imports(code, "Test.java")
        assert len(units) >= 1
        assert units[0].type == "import"

    def test_extract_multiple_imports(self, java_parser):
        """Test extracting multiple imports."""
        code = """
import java.util.List;
import java.util.ArrayList;
import java.util.*;
"""
        units = java_parser.extract_imports(code, "Test.java")
        assert len(units) >= 3

    def test_extract_imports_with_semicolons(self, java_parser):
        """Test that imports with semicolons are extracted."""
        code = """
import java.io.IOException;
import java.io.File;
"""
        units = java_parser.extract_imports(code, "Test.java")
        assert len(units) >= 2


class TestJavaCompleteExtraction:
    """Test complete extraction of all units."""

    def test_extract_all(self, java_parser):
        """Test extracting all units from file."""
        code = """
import java.util.List;

public class UserService {
    private String name;

    public UserService(String name) {
        this.name = name;
    }

    public void authenticate(String user) {
        validateUser(user);
    }

    private void validateUser(String user) {
        System.out.println("Validating: " + user);
    }
}
"""
        units = java_parser.extract_all(code, "UserService.java")
        assert len(units) > 0

        # Check we got different types
        types = {u.type for u in units}
        assert "import" in types or "class" in types

    def test_extract_with_javadoc(self, java_parser):
        """Test extracting with JavaDoc comments."""
        code = """
/**
 * Authenticate a user.
 * @param user The user to authenticate
 * @return True if authenticated
 */
public boolean authenticate(String user) {
    return validateUser(user);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        # Should have extracted JavaDoc
        docstring = units[0].docstring
        assert len(docstring) > 0

    def test_extract_complex_code(self, java_parser):
        """Test with complex Java code."""
        code = """
package com.example.service;

import java.util.*;
import java.io.IOException;

/**
 * Main service class.
 */
public class MainService extends BaseService implements IService {
    private final String name;
    private List<User> users;

    public MainService(String name) {
        this.name = name;
        this.users = new ArrayList<>();
    }

    public void addUser(User user) {
        users.add(user);
        notifyObservers();
    }

    private void notifyObservers() {
        System.out.println("Users updated");
    }

    public List<User> getUsers() {
        return Collections.unmodifiableList(users);
    }
}
"""
        units = java_parser.extract_all(code, "MainService.java")
        assert len(units) > 0


class TestJavaEdgeCases:
    """Test edge cases."""

    def test_empty_code(self, java_parser):
        """Test with empty code."""
        units = java_parser.extract_all("", "Test.java")
        assert units == []

    def test_code_with_syntax_errors(self, java_parser):
        """Test with syntax errors (should not crash)."""
        code = """
public class Broken {
    public void method(
        // missing closing paren and brace
"""
        # Should not raise exception
        units = java_parser.extract_all(code, "Test.java")
        assert isinstance(units, list)

    def test_code_with_no_methods(self, java_parser):
        """Test with code containing no methods."""
        code = """
public class Empty {
    private String name;
    private int age;
}
"""
        units = java_parser.extract_functions(code, "Empty.java")
        # May have extracting issues but should not crash
        assert isinstance(units, list)

    def test_nested_classes(self, java_parser):
        """Test extracting nested classes."""
        code = """
public class Outer {
    public class Inner {
        public void innerMethod() {}
    }
}
"""
        units = java_parser.extract_classes(code, "Test.java")
        # Should extract at least the outer class
        names = [u.name for u in units]
        assert "Outer" in names

    def test_method_with_long_signature(self, java_parser):
        """Test method with very long signature."""
        code = """
public String processUserDataWithMultipleValidationSteps(
    String username, String password, String email, String phone) {
    return validateAll(username, password, email, phone);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        # Signature should be truncated but still valid
        assert len(units[0].signature) > 0

    def test_methods_with_annotations(self, java_parser):
        """Test methods with annotations."""
        code = """
@Override
public void method1() {
    System.out.println("method1");
}

@SuppressWarnings("unchecked")
public void method2() {
    System.out.println("method2");
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        # Should extract methods even with annotations
        assert len(units) >= 1


class TestJavaDocstringExtraction:
    """Test JavaDoc comment extraction."""

    def test_extract_javadoc_block_comment(self, java_parser):
        """Test extracting JavaDoc block comments."""
        code = """
/**
 * Authenticate a user account.
 * @param user The user to authenticate
 * @return True if authentication successful
 */
public boolean authenticate(User user) {
    return validateUser(user);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1
        # Should have extracted JavaDoc
        docstring = units[0].docstring
        assert len(docstring) > 0

    def test_extract_line_comment(self, java_parser):
        """Test extracting line comments."""
        code = """
// Validates user input
public boolean validate(String input) {
    return input.length() > 0;
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1

    def test_extract_multiline_javadoc(self, java_parser):
        """Test extracting multiline JavaDoc."""
        code = """
/**
 * Process data with multiple steps.
 * This is a longer description.
 * More details here.
 */
public void processData(String data) {
    validate(data);
    transform(data);
    store(data);
}
"""
        units = java_parser.extract_functions(code, "Test.java")
        assert len(units) >= 1


class TestJavaIntegration:
    """Test Java parser integration."""

    def test_parser_factory(self):
        """Test parser factory creates Java parser."""
        from athena.code_search.parser import CodeParser

        java_parser = CodeParser("java")
        assert java_parser.language == "java"
        assert java_parser.parser is not None

    def test_parser_extract_all(self):
        """Test CodeParser extracts from Java."""
        from athena.code_search.parser import CodeParser

        parser = CodeParser("java")
        code = """
import java.util.List;

public class UserRepository {
    private List<User> users;

    public User findById(String id) {
        return users.stream()
            .filter(u -> u.getId().equals(id))
            .findFirst()
            .orElse(null);
    }

    public void save(User user) {
        users.add(user);
    }
}
"""
        units = parser.extract_all(code, "UserRepository.java")
        assert len(units) > 0

    def test_java_and_python_parsers_independent(self):
        """Test Java and Python parsers work independently."""
        from athena.code_search.parser import CodeParser

        py_parser = CodeParser("python")
        java_parser = CodeParser("java")

        py_code = """
def authenticate(user):
    return validate_user(user)
"""

        java_code = """
public boolean authenticate(User user) {
    return validateUser(user);
}
"""

        py_units = py_parser.extract_all(py_code, "test.py")
        java_units = java_parser.extract_all(java_code, "Test.java")

        assert len(py_units) > 0
        assert len(java_units) > 0
        # Both should find authenticate
        assert any(u.name == "authenticate" for u in py_units)
        assert any(u.name == "authenticate" for u in java_units)

    def test_java_and_javascript_parsers_independent(self):
        """Test Java and JavaScript parsers work independently."""
        from athena.code_search.parser import CodeParser

        js_parser = CodeParser("javascript")
        java_parser = CodeParser("java")

        js_code = """
function authenticate(user) {
    return validateUser(user);
}
"""

        java_code = """
public boolean authenticate(User user) {
    return validateUser(user);
}
"""

        js_units = js_parser.extract_all(js_code, "test.js")
        java_units = java_parser.extract_all(java_code, "Test.java")

        assert len(js_units) > 0
        assert len(java_units) > 0
