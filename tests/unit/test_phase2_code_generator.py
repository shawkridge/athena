"""Tests for Phase 2 code generation (Week 7).

Tests for:
- ProcedureCodeGenerator with fallback and mock LLM
- CodeValidator with syntax, security, and quality checks
- ConfidenceScorer for code quality assessment
- Integration of all three components
"""

import ast
import json
import pytest
from datetime import datetime
from typing import Optional, Dict, Any

from athena.procedural.code_generator import (
    ProcedureCodeGenerator,
    CodeGenerationPrompt,
    ConfidenceScorer,
)
from athena.procedural.code_validator import (
    CodeValidator,
    ValidationIssue,
    SyntaxValidator,
    SecurityValidator,
    CodeQualityValidator,
)
from athena.procedural.models import Procedure, ProcedureCategory


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def simple_procedure():
    """Simple procedure for testing."""
    return Procedure(
        id=1,
        name="Run Unit Tests",
        category=ProcedureCategory.TESTING,
        description="Execute unit tests for a Python project",
        template="pytest {{test_path}} -v",
        steps=[
            {"description": "Navigate to project directory"},
            {"description": "Run pytest with verbose output"},
            {"description": "Report results"},
        ],
        examples=[
            {"input": "tests/", "expected": "All tests pass"},
        ],
    )


@pytest.fixture
def complex_procedure():
    """Complex procedure with multiple steps."""
    return Procedure(
        id=2,
        name="Refactor TypeScript Module",
        category=ProcedureCategory.REFACTORING,
        description="Refactor a TypeScript module for improved type safety",
        template="Refactor {{module}} with {{improvements}}",
        steps=[
            {"description": "Analyze current module structure"},
            {"description": "Identify type issues"},
            {"description": "Update type annotations"},
            {"description": "Test with strict mode"},
            {"description": "Document changes"},
        ],
        applicable_contexts=["typescript", "react"],
        examples=[
            {
                "module": "UserService",
                "improvements": "strict null checks",
                "expected": "Module passes strict TypeScript check",
            },
        ],
    )


@pytest.fixture
def code_generator():
    """Code generator without LLM (uses fallback)."""
    return ProcedureCodeGenerator(llm_client=None)


@pytest.fixture
def code_validator():
    """Code validator instance."""
    return CodeValidator()


# ============================================================================
# TESTS: CodeGenerationPrompt
# ============================================================================


class TestCodeGenerationPrompt:
    """Tests for prompt generation."""

    def test_sanitize_name(self):
        """Test name sanitization."""
        assert CodeGenerationPrompt._sanitize_name("Run Unit Tests") == "run_unit_tests"
        assert CodeGenerationPrompt._sanitize_name("test-123") == "test_123"
        assert CodeGenerationPrompt._sanitize_name("123_test") == "test"
        # Special chars become underscores, trailing underscores kept (they're valid in Python)
        result = CodeGenerationPrompt._sanitize_name("test!@#$")
        assert result.startswith("test")

    def test_build_procedure_context(self, simple_procedure):
        """Test building procedure context."""
        context = CodeGenerationPrompt.build_procedure_context(simple_procedure)

        assert "Run Unit Tests" in context
        assert "testing" in context  # Enum converts to lowercase
        assert "Execute unit tests" in context
        assert "pytest {{test_path}} -v" in context
        assert "1. Navigate to project directory" in context

    def test_build_code_generation_prompt(self, simple_procedure):
        """Test code generation prompt building."""
        prompt = CodeGenerationPrompt.build_code_generation_prompt(simple_procedure)

        assert "Python code generation expert" in prompt
        assert "run_unit_tests" in prompt
        assert "REQUIREMENTS" in prompt
        assert "syntactically valid Python" in prompt
        assert "docstring" in prompt

    def test_build_refinement_prompt(self):
        """Test refinement prompt building."""
        code = "def test(): pass"
        feedback = "Add error handling"

        prompt = CodeGenerationPrompt.build_refinement_prompt(code, feedback)

        assert code in prompt
        assert feedback in prompt
        assert "improved" in prompt.lower()

    def test_build_validation_prompt(self):
        """Test validation prompt building."""
        code = "def test(): pass"
        prompt = CodeGenerationPrompt.build_validation_prompt(code)

        assert code in prompt
        assert "JSON" in prompt
        assert "is_valid" in prompt
        assert "issues" in prompt


# ============================================================================
# TESTS: SyntaxValidator
# ============================================================================


class TestSyntaxValidator:
    """Tests for syntax validation."""

    def test_valid_syntax(self):
        """Test validation of valid code."""
        code = """
def hello():
    return "world"
"""
        is_valid, error = SyntaxValidator.validate_syntax(code)
        assert is_valid is True
        assert error is None

    def test_invalid_syntax(self):
        """Test validation of invalid code."""
        code = """
def hello(
    return "world"
"""
        is_valid, error = SyntaxValidator.validate_syntax(code)
        assert is_valid is False
        assert error is not None

    def test_complex_valid_code(self):
        """Test complex valid code."""
        code = """
class MyClass:
    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}"

def process(items: list) -> dict:
    try:
        result = [item.upper() for item in items]
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
"""
        is_valid, error = SyntaxValidator.validate_syntax(code)
        assert is_valid is True
        assert error is None


# ============================================================================
# TESTS: SecurityValidator
# ============================================================================


class TestSecurityValidator:
    """Tests for security validation."""

    def test_forbidden_imports(self):
        """Test detection of forbidden imports."""
        code = """
import os
import subprocess

os.system("rm -rf /")
"""
        issues = SecurityValidator.validate_security(code)
        assert len(issues) >= 2
        assert any("os" in issue.message for issue in issues)
        assert any("subprocess" in issue.message for issue in issues)

    def test_dangerous_patterns(self):
        """Test detection of dangerous patterns."""
        code = """
code = "print('hello')"
exec(code)
"""
        issues = SecurityValidator.validate_security(code)
        assert any("exec(" in issue.message for issue in issues)

    def test_allowed_code(self):
        """Test code that should pass security check."""
        code = """
import json
import logging

def safe_process(data: dict) -> dict:
    try:
        result = json.dumps(data)
        return {"success": True, "result": result}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"success": False, "error": str(e)}
"""
        issues = SecurityValidator.validate_security(code)
        # Should have no errors, maybe some warnings
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_file_operations(self):
        """Test file operation handling."""
        code = """
with open("test.txt") as f:
    content = f.read()
"""
        # Should warn about open() by default
        issues = SecurityValidator.validate_security(code, allow_file_ops=False)
        assert any("open(" in issue.message for issue in issues)

        # Should allow with flag
        issues = SecurityValidator.validate_security(code, allow_file_ops=True)
        assert not any("open(" in issue.message for issue in issues)


# ============================================================================
# TESTS: CodeQualityValidator
# ============================================================================


class TestCodeQualityValidator:
    """Tests for code quality validation."""

    def test_check_docstring_present(self):
        """Test docstring detection."""
        code = '''
def test():
    """This is a docstring."""
    return 42
'''
        tree = ast.parse(code)
        # Check function definition (first non-import statement)
        func_node = tree.body[0]
        has_doc = CodeQualityValidator.check_docstring(func_node)
        assert has_doc is True

    def test_check_docstring_missing(self):
        """Test missing docstring detection."""
        code = """
def test():
    return 42
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        has_doc = CodeQualityValidator.check_docstring(func_node)
        assert has_doc is False

    def test_check_error_handling(self):
        """Test error handling detection."""
        with_handling = """
try:
    result = 1 / 0
except ZeroDivisionError:
    result = None
"""
        without_handling = "result = 1 + 1"

        assert CodeQualityValidator.check_error_handling(with_handling) is True
        assert CodeQualityValidator.check_error_handling(without_handling) is False

    def test_check_type_hints(self):
        """Test type hints coverage calculation."""
        code = """
def func1(a: int, b: str) -> bool:
    return True

def func2(a, b):
    return a + b
"""
        tree = ast.parse(code)
        coverage = CodeQualityValidator.check_type_hints(tree)
        # func1: 2 typed args + 1 return type, func2: 2 untyped
        # Total: 7 args, 3 typed = 3/7 ≈ 0.43
        assert 0.3 < coverage < 0.6

    def test_check_imports(self):
        """Test import extraction."""
        code = """
import json
from typing import Dict
import os.path
from collections import defaultdict
"""
        tree = ast.parse(code)
        imports = CodeQualityValidator.check_imports(tree)

        assert "json" in imports
        assert "typing" in imports
        assert "os" in imports
        assert "collections" in imports

    def test_check_functions(self):
        """Test function extraction."""
        code = """
def func1():
    pass

def func2(a, b):
    return a + b

class MyClass:
    def method(self):
        pass
"""
        tree = ast.parse(code)
        functions = CodeQualityValidator.check_functions(tree)

        assert "func1" in functions
        assert "func2" in functions
        assert "method" in functions

    def test_calculate_quality_score(self):
        """Test quality score calculation."""
        # Perfect code
        score1 = CodeQualityValidator.calculate_quality_score(
            has_docstring=True,
            has_error_handling=True,
            type_hints_coverage=1.0,
            issues_count=0,
        )
        assert score1 > 0.9

        # Poor code
        score2 = CodeQualityValidator.calculate_quality_score(
            has_docstring=False,
            has_error_handling=False,
            type_hints_coverage=0.0,
            issues_count=5,
        )
        assert score2 < 0.5


# ============================================================================
# TESTS: CodeValidator (Integrated)
# ============================================================================


class TestCodeValidator:
    """Tests for integrated code validator."""

    def test_validate_good_code(self, code_validator):
        """Test validation of well-written code."""
        code = '''
"""Module for testing."""

import json
import logging

logger = logging.getLogger(__name__)


def process_data(data: dict) -> dict:
    """Process input data.

    Args:
        data: Input dictionary

    Returns:
        Processed result
    """
    try:
        result = json.dumps(data)
        logger.info("Processing complete")
        return {
            "success": True,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
        }
'''
        result = code_validator.validate(code)

        assert result.is_valid is True
        assert result.errors == 0
        assert result.has_docstring is True
        assert result.has_error_handling is True
        assert result.quality_score > 0.7

    def test_validate_bad_syntax(self, code_validator):
        """Test validation of code with syntax errors."""
        code = """
def test(
    return "bad"
"""
        result = code_validator.validate(code)

        assert result.is_valid is False
        assert result.errors > 0
        assert any("Syntax" in i.message for i in result.issues)

    def test_validate_security_issues(self, code_validator):
        """Test validation of code with security issues."""
        code = """
import os
os.system("rm -rf /")
"""
        result = code_validator.validate(code)

        assert result.is_valid is False
        assert result.errors > 0

    def test_validate_and_report(self, code_validator):
        """Test JSON reporting."""
        code = 'def test(): pass'
        report = code_validator.validate_and_report(code)

        assert isinstance(report, dict)
        assert "is_valid" in report
        assert "issues" in report
        assert "quality_score" in report
        assert "functions" in report


# ============================================================================
# TESTS: ConfidenceScorer
# ============================================================================


class TestConfidenceScorer:
    """Tests for confidence scoring."""

    def test_confidence_good_code(self, simple_procedure):
        """Test confidence of well-written code."""
        code = '''
def run_unit_tests(**kwargs):
    """Execute unit tests."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        test_path = kwargs.get("test_path", "tests/")
        logger.info(f"Running tests in {test_path}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"success": False, "error": str(e)}
'''
        confidence = ConfidenceScorer.calculate_confidence(code, simple_procedure)
        assert confidence > 0.6

    def test_confidence_bad_syntax(self, simple_procedure):
        """Test confidence of code with syntax errors."""
        code = "def test(: pass"
        confidence = ConfidenceScorer.calculate_confidence(code, simple_procedure)
        assert confidence == 0.0

    def test_confidence_minimal_code(self, simple_procedure):
        """Test confidence of minimal code."""
        code = "def test(): pass"
        confidence = ConfidenceScorer.calculate_confidence(code, simple_procedure)
        assert 0.3 < confidence < 0.7


# ============================================================================
# TESTS: ProcedureCodeGenerator
# ============================================================================


class TestProcedureCodeGenerator:
    """Tests for code generator."""

    def test_generator_exists(self, code_generator):
        """Test generator initialization."""
        assert code_generator is not None
        assert code_generator._use_llm is False

    def test_generate_fallback(self, code_generator, simple_procedure):
        """Test fallback code generation."""
        code, confidence = code_generator.generate(simple_procedure)

        assert code is not None
        assert "def run_unit_tests" in code
        assert confidence > 0.0
        assert isinstance(confidence, float)

    def test_generate_with_extraction(self, code_generator, simple_procedure):
        """Test code can be extracted from response."""
        response = """```python
def hello():
    return "world"
```"""
        extracted = code_generator._extract_code(response)
        assert extracted is not None
        assert "def hello" in extracted

    def test_generate_without_markdown(self, code_generator):
        """Test extraction without markdown blocks."""
        response = """def hello():
    return "world"
"""
        extracted = code_generator._extract_code(response)
        assert extracted is not None
        assert "def hello" in extracted

    def test_generate_fallback_git(self, code_generator):
        """Test fallback for git procedure."""
        procedure = Procedure(
            name="Git Status",
            category=ProcedureCategory.GIT,
            description="Check git status",
            template="git status",
        )
        code, confidence = code_generator.generate(procedure)

        assert code is not None
        assert "subprocess" in code
        assert "git" in code.lower()

    def test_generate_fallback_testing(self, code_generator):
        """Test fallback for testing procedure."""
        procedure = Procedure(
            name="Run Tests",
            category=ProcedureCategory.TESTING,
            description="Run all tests",
            template="pytest",
        )
        code, confidence = code_generator.generate(procedure)

        assert code is not None
        assert "def run_tests" in code


# ============================================================================
# TESTS: Integration
# ============================================================================


class TestCodeGenerationIntegration:
    """Integration tests for code generation pipeline."""

    def test_generation_to_validation_pipeline(self, code_generator, code_validator):
        """Test full pipeline: generate -> validate -> score."""
        procedure = Procedure(
            name="Validate JSON",
            category=ProcedureCategory.TESTING,
            description="Validate JSON data structure",
            template="validate_json({{data}})",
            steps=[
                {"description": "Parse JSON"},
                {"description": "Check structure"},
            ],
        )

        # Generate
        code, gen_confidence = code_generator.generate(procedure)
        assert code is not None

        # Validate
        validation_result = code_validator.validate(code)
        assert validation_result.is_valid is True

        # Score
        confidence = ConfidenceScorer.calculate_confidence(code, procedure, validation_result.to_dict())
        assert 0.0 <= confidence <= 1.0

    def test_multiple_generation_attempts(self, code_generator):
        """Test that generator can handle multiple procedures."""
        procedures = [
            Procedure(
                name="Test A",
                category=ProcedureCategory.TESTING,
                description="First test",
                template="pytest",
            ),
            Procedure(
                name="Test B",
                category=ProcedureCategory.REFACTORING,
                description="Second test",
                template="refactor code",
            ),
            Procedure(
                name="Test C",
                category=ProcedureCategory.GIT,
                description="Third test",
                template="git commit",
            ),
        ]

        codes = []
        for procedure in procedures:
            code, confidence = code_generator.generate(procedure)
            assert code is not None
            codes.append(code)

        # All codes should be different (different function names)
        assert len(set(codes)) == len(codes)


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


class TestCodeGenerationEdgeCases:
    """Tests for edge cases and error handling."""

    def test_generate_empty_procedure(self, code_generator):
        """Test generation with minimal procedure."""
        procedure = Procedure(
            name="",
            category=ProcedureCategory.TESTING,
            template="",
        )
        code, confidence = code_generator.generate(procedure)
        # Should still generate fallback code
        assert code is not None

    def test_generator_error_handling(self, code_generator):
        """Test error handling during generation."""
        procedure = Procedure(
            name="Test",
            category=ProcedureCategory.TESTING,
            template="test",
        )
        # This should not crash
        try:
            code, confidence = code_generator.generate(procedure)
            assert code is not None
        except Exception as e:
            pytest.fail(f"Generator should handle errors gracefully: {e}")

    def test_validator_error_handling(self, code_validator):
        """Test validator error handling."""
        # Try to validate various inputs
        invalid_inputs = [
            "",
            "   ",
            "\n\n",
            "def test(\n",  # Syntax error
        ]

        for invalid in invalid_inputs:
            result = code_validator.validate(invalid)
            # Should not crash
            assert result is not None
