"""Architecture Fitness Functions - Automated architectural testing.

Inspired by ArchUnit (Java) and NetArchTest (.NET), this module provides
automated testing of architectural properties. Fitness functions are
executable tests that validate architectural constraints, patterns, and
design rules.

Usage:
    @fitness_function(
        name="Service Layer Independence",
        severity="error",
        category="layering"
    )
    def test_service_layer_independence():
        \"\"\"Services must not depend on UI components.\"\"\"
        violations = find_dependencies(from_layer="services", to_layer="ui")
        return FitnessResult(
            passed=len(violations) == 0,
            violations=violations,
            message=f"Found {len(violations)} service->UI dependencies"
        )

Integration:
    - Run via pytest: pytest tests/architecture/
    - Run via CLI: athena-fitness-check --project-id 1
    - Run via git hook: In pre-commit or pre-push
"""

import ast
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..core.database import Database


class Severity(str, Enum):
    """Severity levels for fitness function violations."""

    ERROR = "error"  # Blocks commit/build
    WARNING = "warning"  # Warns but allows
    INFO = "info"  # Informational only


class Category(str, Enum):
    """Categories of fitness functions."""

    LAYERING = "layering"  # Layer dependency rules
    PATTERNS = "patterns"  # Design pattern enforcement
    CONSTRAINTS = "constraints"  # Architectural constraints
    NAMING = "naming"  # Naming conventions
    DEPENDENCIES = "dependencies"  # Dependency management
    SECURITY = "security"  # Security requirements
    PERFORMANCE = "performance"  # Performance requirements


@dataclass
class Violation:
    """Represents a single architectural violation."""

    file_path: str
    line_number: int
    rule_name: str
    description: str
    severity: Severity
    suggested_fix: Optional[str] = None

    def __str__(self) -> str:
        fix = f"\n  → Suggested fix: {self.suggested_fix}" if self.suggested_fix else ""
        return (
            f"{self.file_path}:{self.line_number} - {self.description}{fix}"
        )


@dataclass
class FitnessResult:
    """Result of running a fitness function."""

    passed: bool
    message: str
    violations: List[Violation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)


@dataclass
class FitnessFunction:
    """Metadata and execution wrapper for a fitness function."""

    name: str
    func: Callable[[], FitnessResult]
    severity: Severity
    category: Category
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def execute(self) -> FitnessResult:
        """Execute the fitness function and return result."""
        try:
            result = self.func()
            if not isinstance(result, FitnessResult):
                return FitnessResult(
                    passed=False,
                    message=f"Fitness function {self.name} did not return FitnessResult",
                    violations=[],
                )
            return result
        except Exception as e:
            return FitnessResult(
                passed=False,
                message=f"Fitness function {self.name} raised exception: {str(e)}",
                violations=[],
            )


class FitnessRegistry:
    """Registry of all fitness functions."""

    _functions: List[FitnessFunction] = []

    @classmethod
    def register(cls, func: FitnessFunction) -> None:
        """Register a fitness function."""
        cls._functions.append(func)

    @classmethod
    def get_all(cls) -> List[FitnessFunction]:
        """Get all registered fitness functions."""
        return cls._functions.copy()

    @classmethod
    def get_by_category(cls, category: Category) -> List[FitnessFunction]:
        """Get fitness functions by category."""
        return [f for f in cls._functions if f.category == category]

    @classmethod
    def get_by_severity(cls, severity: Severity) -> List[FitnessFunction]:
        """Get fitness functions by severity."""
        return [f for f in cls._functions if f.severity == severity]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered functions (for testing)."""
        cls._functions = []


def fitness_function(
    name: str,
    severity: Severity = Severity.ERROR,
    category: Category = Category.LAYERING,
    tags: Optional[List[str]] = None,
):
    """Decorator to register a fitness function.

    Args:
        name: Human-readable name
        severity: ERROR, WARNING, or INFO
        category: Category of fitness function
        tags: Optional tags for filtering

    Example:
        @fitness_function(
            name="No UI dependencies in services",
            severity=Severity.ERROR,
            category=Category.LAYERING
        )
        def test_service_isolation():
            # Test implementation
            return FitnessResult(passed=True, message="All good")
    """

    def decorator(func: Callable[[], FitnessResult]):
        fitness_func = FitnessFunction(
            name=name,
            func=func,
            severity=severity,
            category=category,
            description=func.__doc__,
            tags=tags or [],
        )
        FitnessRegistry.register(fitness_func)
        return func

    return decorator


class CodeAnalyzer:
    """Analyze Python code for architectural properties."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def find_python_files(self, exclude_patterns: Optional[List[str]] = None) -> List[Path]:
        """Find all Python files in project."""
        exclude_patterns = exclude_patterns or ["tests/", "__pycache__/", ".venv/", "venv/"]
        files = []

        for path in self.project_root.rglob("*.py"):
            # Skip excluded patterns
            if any(pattern in str(path) for pattern in exclude_patterns):
                continue
            files.append(path)

        return files

    def get_imports(self, file_path: Path) -> List[Tuple[str, int]]:
        """Get all imports from a Python file.

        Returns:
            List of (module_name, line_number) tuples
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append((alias.name, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append((node.module, node.lineno))

            return imports
        except Exception:
            return []

    def find_class_definitions(self, file_path: Path) -> List[Tuple[str, int]]:
        """Find all class definitions in a file.

        Returns:
            List of (class_name, line_number) tuples
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append((node.name, node.lineno))

            return classes
        except Exception:
            return []

    def check_class_implements_interface(
        self, file_path: Path, class_name: str, interface_name: str
    ) -> bool:
        """Check if a class implements an interface (base class)."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Check base classes
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == interface_name:
                            return True
            return False
        except Exception:
            return False

    def find_dependencies_between_layers(
        self, from_layer: str, to_layer: str
    ) -> List[Violation]:
        """Find dependencies from one layer to another.

        Layers are identified by directory structure:
        - src/athena/ui/ (UI layer)
        - src/athena/services/ (Service layer)
        - src/athena/data/ (Data layer)
        """
        violations = []
        from_layer_path = self.project_root / "src" / "athena" / from_layer
        to_layer_module = f"athena.{to_layer}"

        if not from_layer_path.exists():
            return violations

        # Find all files in from_layer
        for file_path in from_layer_path.rglob("*.py"):
            imports = self.get_imports(file_path)

            for module, line_num in imports:
                if module.startswith(to_layer_module):
                    violations.append(
                        Violation(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            rule_name=f"No {from_layer} → {to_layer} dependencies",
                            description=f"Import of '{module}' violates layering",
                            severity=Severity.ERROR,
                            suggested_fix=f"Remove import or refactor {from_layer} to not depend on {to_layer}",
                        )
                    )

        return violations


class FitnessChecker:
    """Execute fitness functions and report results."""

    def __init__(self, project_root: Path, db: Optional[Database] = None):
        self.project_root = project_root
        self.db = db
        self.analyzer = CodeAnalyzer(project_root)

    def run_all(
        self,
        severity_filter: Optional[Severity] = None,
        category_filter: Optional[Category] = None,
    ) -> Dict[str, Any]:
        """Run all registered fitness functions.

        Args:
            severity_filter: Only run functions of this severity
            category_filter: Only run functions of this category

        Returns:
            Dict with results summary
        """
        functions = FitnessRegistry.get_all()

        # Apply filters
        if severity_filter:
            functions = [f for f in functions if f.severity == severity_filter]
        if category_filter:
            functions = [f for f in functions if f.category == category_filter]

        results = []
        for func in functions:
            result = func.execute()
            results.append(
                {
                    "name": func.name,
                    "category": func.category.value,
                    "severity": func.severity.value,
                    "passed": result.passed,
                    "message": result.message,
                    "violations": [
                        {
                            "file": v.file_path,
                            "line": v.line_number,
                            "description": v.description,
                            "suggested_fix": v.suggested_fix,
                        }
                        for v in result.violations
                    ],
                }
            )

        # Calculate summary
        total = len(results)
        passed = sum(1 for r in results if r["passed"])
        failed = total - passed
        total_violations = sum(len(r["violations"]) for r in results)

        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "summary": {
                "total_functions": total,
                "passed": passed,
                "failed": failed,
                "total_violations": total_violations,
            },
            "results": results,
        }

    def check_should_block_commit(self, results: Dict[str, Any]) -> bool:
        """Determine if results should block a commit/build.

        Blocks if any ERROR severity violations exist.
        """
        for result in results["results"]:
            if result["severity"] == Severity.ERROR.value and not result["passed"]:
                return True
        return False


# Example fitness functions that can be enabled

@fitness_function(
    name="Repository Pattern Enforcement",
    severity=Severity.ERROR,
    category=Category.PATTERNS,
    tags=["data-access", "patterns"],
)
def test_repository_pattern_enforcement() -> FitnessResult:
    """All *Repository classes must inherit from BaseRepository."""
    # This is an example - would need actual implementation
    return FitnessResult(
        passed=True,
        message="Repository pattern check passed (example)",
        violations=[],
    )


@fitness_function(
    name="No Circular Dependencies",
    severity=Severity.ERROR,
    category=Category.DEPENDENCIES,
    tags=["dependencies"],
)
def test_no_circular_dependencies() -> FitnessResult:
    """No circular dependencies between modules."""
    # This is an example - would need actual implementation
    return FitnessResult(
        passed=True,
        message="No circular dependencies detected (example)",
        violations=[],
    )
