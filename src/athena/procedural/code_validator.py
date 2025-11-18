"""Validate and analyze generated code for safety and quality.

This module provides CodeValidator to check:
- Syntax correctness (AST parsing)
- Security concerns (forbidden imports, patterns)
- Code quality (completeness, error handling)
- Type hints coverage
- Documentation completeness
"""

import ast
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a code validation issue."""

    severity: str  # "error", "warning", "info"
    message: str
    line: Optional[int] = None
    category: str = "general"  # syntax, security, style, completeness

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    issues: List[ValidationIssue]
    warnings: int
    errors: int
    quality_score: float  # 0.0-1.0
    has_docstring: bool
    has_error_handling: bool
    type_hints_coverage: float  # 0.0-1.0
    imports: Set[str]
    functions: Set[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": self.warnings,
            "errors": self.errors,
            "quality_score": self.quality_score,
            "has_docstring": self.has_docstring,
            "has_error_handling": self.has_error_handling,
            "type_hints_coverage": self.type_hints_coverage,
            "imports": list(self.imports),
            "functions": list(self.functions),
        }


class SyntaxValidator:
    """Validates Python syntax using AST."""

    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python code syntax.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            return False, error_msg
        except Exception as e:
            return False, f"Parse error: {str(e)}"


class SecurityValidator:
    """Validates code for security concerns."""

    # Forbidden imports for sandboxed execution
    FORBIDDEN_IMPORTS = {
        "os",
        "sys",
        "subprocess",
        "pickle",
        "eval",
        "exec",
        "__import__",
        "importlib",
        "socket",
        "httpx",
        "requests",
        "paramiko",
        "ftplib",
    }

    # Dangerous patterns
    DANGEROUS_PATTERNS = {
        "eval(",
        "exec(",
        "__import__(",
        "compile(",
        "open(",
        "file(",
        "input(",
        "raw_input(",
    }

    # Warning patterns
    WARNING_PATTERNS = {
        "global ",
        "globals(",
        "locals(",
        "vars(",
        "__dict__",
        "setattr(",
        "getattr(",
        "delattr(",
        "hasattr(",
    }

    @staticmethod
    def validate_security(code: str, allow_file_ops: bool = False) -> List[ValidationIssue]:
        """Validate code for security concerns.

        Args:
            code: Python code to check
            allow_file_ops: Allow file operations (open, read, write)

        Returns:
            List of security issues found
        """
        issues = []

        # Check imports
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in SecurityValidator.FORBIDDEN_IMPORTS:
                        issues.append(
                            ValidationIssue(
                                severity="error",
                                message=f"Forbidden import: {module_name}",
                                category="security",
                            )
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in SecurityValidator.FORBIDDEN_IMPORTS:
                        issues.append(
                            ValidationIssue(
                                severity="error",
                                message=f"Forbidden import: {node.module}",
                                category="security",
                            )
                        )

        # Check dangerous patterns
        for pattern in SecurityValidator.DANGEROUS_PATTERNS:
            if allow_file_ops and pattern in ("open(", "file("):
                continue

            if pattern in code:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Dangerous pattern detected: {pattern}",
                        category="security",
                    )
                )

        # Check warning patterns
        for pattern in SecurityValidator.WARNING_PATTERNS:
            if pattern in code:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"Potentially unsafe pattern: {pattern}",
                        category="security",
                    )
                )

        return issues


class CodeQualityValidator:
    """Validates code quality and completeness."""

    @staticmethod
    def check_docstring(tree: ast.AST) -> bool:
        """Check if code has docstring."""
        if isinstance(tree, ast.Module):
            return (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            )
        elif isinstance(tree, (ast.FunctionDef, ast.ClassDef)):
            return (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            )
        return False

    @staticmethod
    def check_error_handling(code: str) -> bool:
        """Check if code has try/except blocks."""
        return "try:" in code and "except" in code

    @staticmethod
    def check_type_hints(tree: ast.AST) -> float:
        """Calculate type hints coverage (0.0-1.0)."""
        total_args = 0
        typed_args = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Count parameters
                for arg in node.args.args:
                    total_args += 1
                    if arg.annotation:
                        typed_args += 1

                # Check return annotation
                if node.returns:
                    typed_args += 1
                total_args += 1

        if total_args == 0:
            return 1.0
        return typed_args / total_args

    @staticmethod
    def check_imports(tree: ast.AST) -> Set[str]:
        """Extract all imports from code."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        return imports

    @staticmethod
    def check_functions(tree: ast.AST) -> Set[str]:
        """Extract all function definitions from code."""
        functions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.add(node.name)
        return functions

    @staticmethod
    def calculate_quality_score(
        has_docstring: bool,
        has_error_handling: bool,
        type_hints_coverage: float,
        issues_count: int,
    ) -> float:
        """Calculate overall code quality score (0.0-1.0)."""
        score = 0.5  # Base score

        if has_docstring:
            score += 0.2
        if has_error_handling:
            score += 0.15
        score += type_hints_coverage * 0.15

        # Deduct for issues
        issues_penalty = min(issues_count * 0.05, 0.25)
        score -= issues_penalty

        return max(0.0, min(1.0, score))


class CodeValidator:
    """Comprehensive code validator."""

    def validate(self, code: str, allow_file_ops: bool = False) -> ValidationResult:
        """Validate generated code.

        Args:
            code: Python code to validate
            allow_file_ops: Allow file operations (open, read, write)

        Returns:
            ValidationResult with detailed analysis
        """
        issues = []
        errors = 0
        warnings = 0

        # 1. Syntax validation
        is_valid, syntax_error = SyntaxValidator.validate_syntax(code)
        if not is_valid:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=syntax_error or "Syntax error",
                    category="syntax",
                )
            )
            errors += 1
            return ValidationResult(
                is_valid=False,
                issues=issues,
                warnings=0,
                errors=1,
                quality_score=0.0,
                has_docstring=False,
                has_error_handling=False,
                type_hints_coverage=0.0,
                imports=set(),
                functions=set(),
            )

        # Parse for detailed analysis
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError, TypeError):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="Failed to parse code",
                    category="syntax",
                )
            )
            return ValidationResult(
                is_valid=False,
                issues=issues,
                warnings=0,
                errors=1,
                quality_score=0.0,
                has_docstring=False,
                has_error_handling=False,
                type_hints_coverage=0.0,
                imports=set(),
                functions=set(),
            )

        # 2. Security validation
        security_issues = SecurityValidator.validate_security(code, allow_file_ops)
        for issue in security_issues:
            issues.append(issue)
            if issue.severity == "error":
                errors += 1
            elif issue.severity == "warning":
                warnings += 1

        # 3. Quality checks
        has_docstring = CodeQualityValidator.check_docstring(tree)
        has_error_handling = CodeQualityValidator.check_error_handling(code)
        type_hints_coverage = CodeQualityValidator.check_type_hints(tree)
        imports = CodeQualityValidator.check_imports(tree)
        functions = CodeQualityValidator.check_functions(tree)

        # 4. Additional quality checks
        if not has_docstring:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="Missing module/function docstring",
                    category="completeness",
                )
            )
            warnings += 1

        if not has_error_handling:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="No try/except error handling found",
                    category="completeness",
                )
            )
            warnings += 1

        if type_hints_coverage < 0.5:
            issues.append(
                ValidationIssue(
                    severity="info",
                    message=f"Low type hints coverage: {type_hints_coverage:.1%}",
                    category="style",
                )
            )

        # 5. Calculate quality score
        quality_score = CodeQualityValidator.calculate_quality_score(
            has_docstring, has_error_handling, type_hints_coverage, errors + warnings
        )

        return ValidationResult(
            is_valid=errors == 0,
            issues=issues,
            warnings=warnings,
            errors=errors,
            quality_score=quality_score,
            has_docstring=has_docstring,
            has_error_handling=has_error_handling,
            type_hints_coverage=type_hints_coverage,
            imports=imports,
            functions=functions,
        )

    def validate_and_report(self, code: str) -> Dict:
        """Validate code and return JSON report.

        Args:
            code: Python code to validate

        Returns:
            Dictionary with validation results
        """
        result = self.validate(code)
        return result.to_dict()
