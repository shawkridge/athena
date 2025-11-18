"""Example architecture fitness tests for Athena project.

These tests validate architectural properties and can be run via:
- pytest tests/architecture/
- Pre-commit hooks
- CI/CD pipelines

Add your own fitness functions following the patterns below.
"""

from pathlib import Path

import pytest

from athena.architecture.fitness import (
    Category,
    CodeAnalyzer,
    FitnessChecker,
    FitnessRegistry,
    FitnessResult,
    Severity,
    Violation,
    fitness_function,
)


# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before each test."""
    FitnessRegistry.clear()
    yield
    FitnessRegistry.clear()


@pytest.fixture
def analyzer():
    """Code analyzer fixture."""
    return CodeAnalyzer(PROJECT_ROOT)


@pytest.fixture
def checker():
    """Fitness checker fixture."""
    return FitnessChecker(PROJECT_ROOT)


# ============================================================================
# LAYERING FITNESS FUNCTIONS
# ============================================================================


@fitness_function(
    name="Core layer independence",
    severity=Severity.ERROR,
    category=Category.LAYERING,
    tags=["core", "layering"],
)
def test_core_layer_independence() -> FitnessResult:
    """Core layer (database, models, config) should not depend on higher layers.

    Rule: src/athena/core/ must not import from:
    - src/athena/mcp/
    - src/athena/episodic/
    - src/athena/semantic/
    - src/athena/procedural/
    """
    analyzer = CodeAnalyzer(PROJECT_ROOT)
    violations = []

    # Layers that core should not depend on
    forbidden_layers = ["mcp", "episodic", "semantic", "procedural", "prospective"]

    core_path = PROJECT_ROOT / "src" / "athena" / "core"
    if not core_path.exists():
        return FitnessResult(
            passed=True,
            message="Core layer not found (skipping check)",
            violations=[],
        )

    for file_path in core_path.rglob("*.py"):
        imports = analyzer.get_imports(file_path)

        for module, line_num in imports:
            for forbidden in forbidden_layers:
                if f"athena.{forbidden}" in module:
                    violations.append(
                        Violation(
                            file_path=str(file_path.relative_to(PROJECT_ROOT)),
                            line_number=line_num,
                            rule_name="Core layer independence",
                            description=f"Core layer imports from {forbidden} layer: {module}",
                            severity=Severity.ERROR,
                            suggested_fix=f"Move shared code to core or refactor to remove dependency",
                        )
                    )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} core layer violations" if violations else "Core layer is independent",
        violations=violations,
    )


@fitness_function(
    name="MCP handlers should not be imported by core layers",
    severity=Severity.WARNING,
    category=Category.LAYERING,
    tags=["mcp", "layering"],
)
def test_mcp_isolation() -> FitnessResult:
    """MCP handlers are top-level and should not be imported by core layers.

    Rule: Only hooks and CLI should import from src/athena/mcp/handlers*.py
    """
    analyzer = CodeAnalyzer(PROJECT_ROOT)
    violations = []

    # Check src/athena/ (excluding mcp itself)
    src_path = PROJECT_ROOT / "src" / "athena"
    if not src_path.exists():
        return FitnessResult(passed=True, message="Source not found", violations=[])

    for file_path in src_path.rglob("*.py"):
        # Skip MCP directory itself
        if "mcp" in str(file_path):
            continue

        imports = analyzer.get_imports(file_path)

        for module, line_num in imports:
            if "athena.mcp.handlers" in module:
                violations.append(
                    Violation(
                        file_path=str(file_path.relative_to(PROJECT_ROOT)),
                        line_number=line_num,
                        rule_name="MCP handler isolation",
                        description=f"Core layer imports MCP handlers: {module}",
                        severity=Severity.WARNING,
                        suggested_fix="Use manager classes or move logic out of handlers",
                    )
                )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} MCP isolation violations" if violations else "MCP is properly isolated",
        violations=violations,
    )


# ============================================================================
# PATTERN FITNESS FUNCTIONS
# ============================================================================


@fitness_function(
    name="Store classes extend BaseStore",
    severity=Severity.ERROR,
    category=Category.PATTERNS,
    tags=["patterns", "stores"],
)
def test_store_pattern() -> FitnessResult:
    """All *Store classes should extend BaseStore pattern."""
    analyzer = CodeAnalyzer(PROJECT_ROOT)
    violations = []

    src_path = PROJECT_ROOT / "src" / "athena"
    if not src_path.exists():
        return FitnessResult(passed=True, message="Source not found", violations=[])

    for file_path in src_path.rglob("*_store.py"):
        classes = analyzer.find_class_definitions(file_path)

        for class_name, line_num in classes:
            if class_name.endswith("Store"):
                # Check if extends BaseStore (simplified check)
                # In real implementation, would parse AST more thoroughly
                with open(file_path, "r") as f:
                    content = f.read()
                    if f"class {class_name}" in content and "BaseStore" not in content:
                        violations.append(
                            Violation(
                                file_path=str(file_path.relative_to(PROJECT_ROOT)),
                                line_number=line_num,
                                rule_name="Store pattern enforcement",
                                description=f"Store class {class_name} doesn't extend BaseStore",
                                severity=Severity.ERROR,
                                suggested_fix=f"class {class_name}(BaseStore): ...",
                            )
                        )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} store pattern violations" if violations else "All stores follow pattern",
        violations=violations,
    )


# ============================================================================
# NAMING CONVENTIONS
# ============================================================================


@fitness_function(
    name="Manager classes naming convention",
    severity=Severity.WARNING,
    category=Category.NAMING,
    tags=["naming", "conventions"],
)
def test_manager_naming() -> FitnessResult:
    """Classes managing layers should be named *Manager."""
    analyzer = CodeAnalyzer(PROJECT_ROOT)
    violations = []

    src_path = PROJECT_ROOT / "src" / "athena"
    if not src_path.exists():
        return FitnessResult(passed=True, message="Source not found", violations=[])

    # Files that should contain managers
    manager_files = list(src_path.rglob("manager.py"))

    for file_path in manager_files:
        classes = analyzer.find_class_definitions(file_path)

        for class_name, line_num in classes:
            # Main class in manager.py should end with Manager
            if not class_name.endswith("Manager") and not class_name.startswith("_"):
                violations.append(
                    Violation(
                        file_path=str(file_path.relative_to(PROJECT_ROOT)),
                        line_number=line_num,
                        rule_name="Manager naming convention",
                        description=f"Class {class_name} in manager.py should end with 'Manager'",
                        severity=Severity.WARNING,
                        suggested_fix=f"Rename to {class_name}Manager",
                    )
                )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} naming violations" if violations else "Naming conventions followed",
        violations=violations,
    )


# ============================================================================
# SECURITY CONSTRAINTS
# ============================================================================


@fitness_function(
    name="No hardcoded secrets",
    severity=Severity.ERROR,
    category=Category.SECURITY,
    tags=["security", "secrets"],
)
def test_no_hardcoded_secrets() -> FitnessResult:
    """No hardcoded API keys, passwords, or tokens in source code."""
    violations = []

    # Patterns to look for
    secret_patterns = [
        "api_key =",
        "password =",
        "secret =",
        "token =",
        "API_KEY =",
        "PASSWORD =",
    ]

    src_path = PROJECT_ROOT / "src" / "athena"
    if not src_path.exists():
        return FitnessResult(passed=True, message="Source not found", violations=[])

    for file_path in src_path.rglob("*.py"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                for pattern in secret_patterns:
                    if pattern in line and "os.environ" not in line and "config" not in line.lower():
                        # Likely hardcoded value
                        if "=" in line and '"' in line or "'" in line:
                            violations.append(
                                Violation(
                                    file_path=str(file_path.relative_to(PROJECT_ROOT)),
                                    line_number=line_num,
                                    rule_name="No hardcoded secrets",
                                    description=f"Possible hardcoded secret: {line.strip()[:50]}",
                                    severity=Severity.ERROR,
                                    suggested_fix="Use environment variables or config files",
                                )
                            )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} potential hardcoded secrets" if violations else "No hardcoded secrets found",
        violations=violations,
    )


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================


def test_run_all_fitness_functions(checker):
    """Run all registered fitness functions via pytest."""
    results = checker.run_all()

    # Print summary
    print("\n" + "=" * 70)
    print("ARCHITECTURE FITNESS CHECK RESULTS")
    print("=" * 70)
    print(f"Total functions: {results['summary']['total_functions']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Total violations: {results['summary']['total_violations']}")
    print()

    # Print failures
    for result in results["results"]:
        if not result["passed"]:
            print(f"\n❌ {result['name']} [{result['category']}] - {result['severity']}")
            print(f"   {result['message']}")
            for violation in result["violations"][:5]:  # Show first 5
                print(f"   • {violation['file']}:{violation['line']}")
                print(f"     {violation['description']}")
                if violation.get("suggested_fix"):
                    print(f"     → {violation['suggested_fix']}")

    print("\n" + "=" * 70)

    # Fail test if any ERROR severity failed
    if checker.check_should_block_commit(results):
        pytest.fail(
            f"Architecture fitness check failed: {results['summary']['failed']} functions with errors"
        )


def test_run_critical_only(checker):
    """Run only ERROR severity fitness functions (for faster CI)."""
    results = checker.run_all(severity_filter=Severity.ERROR)

    failed = results["summary"]["failed"]
    if failed > 0:
        pytest.fail(f"{failed} critical architecture fitness functions failed")


def test_layering_rules(checker):
    """Run only layering-related fitness functions."""
    results = checker.run_all(category_filter=Category.LAYERING)

    # Layering violations are always critical
    if results["summary"]["failed"] > 0:
        pytest.fail(f"Layering violations detected: {results['summary']['failed']}")
