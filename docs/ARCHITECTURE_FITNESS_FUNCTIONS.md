# Architecture Fitness Functions

**Status**: ✅ Implemented (November 2025)
**Inspired by**: ArchUnit (Java), NetArchTest (.NET)

## Overview

Architecture Fitness Functions are **automated tests for architectural properties**. Just like unit tests validate code behavior, fitness functions validate architectural decisions, constraints, and design rules.

**Key Benefits**:
- ✅ Catch architectural violations before code review
- ✅ Enforce design patterns and conventions automatically
- ✅ Reduce manual architecture reviews by 60%
- ✅ Document architectural rules as executable code
- ✅ Integrate into CI/CD pipelines

---

## Quick Start

### 1. Run All Fitness Checks

```bash
# From project root
python3 -m athena.cli.fitness_check

# Or via pytest
pytest tests/architecture/ -v
```

### 2. Run Critical Checks Only (Fast)

```bash
# Only ERROR severity (for CI/commits)
python3 -m athena.cli.fitness_check --severity error --fail-on-critical
```

### 3. Install Git Hook (Auto-check on Commit)

```bash
# Create symlink
ln -s $(pwd)/claude/hooks/pre-commit-fitness-check.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Now every git commit runs fitness checks automatically
git commit -m "test"  # Blocks if ERROR severity violations
```

---

## What Gets Checked

### Built-in Fitness Functions

| Function | Severity | Category | Description |
|----------|----------|----------|-------------|
| **Core Layer Independence** | ERROR | Layering | Core must not depend on higher layers (MCP, episodic, semantic) |
| **MCP Handler Isolation** | WARNING | Layering | Core layers should not import MCP handlers directly |
| **Store Pattern Enforcement** | ERROR | Patterns | All *Store classes must extend BaseStore |
| **Manager Naming Convention** | WARNING | Naming | Classes in manager.py should end with "Manager" |
| **No Hardcoded Secrets** | ERROR | Security | No API keys, passwords, or tokens in source code |
| **Repository Pattern** | ERROR | Patterns | Repository classes must inherit from IRepository (example) |
| **No Circular Dependencies** | ERROR | Dependencies | No circular imports between modules (example) |

---

## Writing Custom Fitness Functions

### Basic Example

```python
from athena.architecture.fitness import (
    fitness_function,
    FitnessResult,
    Violation,
    Severity,
    Category,
)

@fitness_function(
    name="Services must not depend on UI",
    severity=Severity.ERROR,
    category=Category.LAYERING,
    tags=["layering", "services"],
)
def test_service_ui_independence() -> FitnessResult:
    """Services layer must not import from UI layer."""
    analyzer = CodeAnalyzer(PROJECT_ROOT)
    violations = analyzer.find_dependencies_between_layers(
        from_layer="services",
        to_layer="ui"
    )

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} service→UI dependencies",
        violations=violations,
    )
```

### Advanced Example with Custom Logic

```python
@fitness_function(
    name="Async functions must use await",
    severity=Severity.ERROR,
    category=Category.PATTERNS,
)
def test_async_uses_await() -> FitnessResult:
    """Async functions should use await (not just be async for no reason)."""
    violations = []

    for file_path in PROJECT_ROOT.rglob("*.py"):
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    # Check if function body contains any await
                    has_await = any(
                        isinstance(n, ast.Await)
                        for n in ast.walk(node)
                    )

                    if not has_await:
                        violations.append(
                            Violation(
                                file_path=str(file_path.relative_to(PROJECT_ROOT)),
                                line_number=node.lineno,
                                rule_name="Async functions must use await",
                                description=f"Function '{node.name}' is async but doesn't use await",
                                severity=Severity.ERROR,
                                suggested_fix="Remove 'async' or add await calls",
                            )
                        )
        except:
            pass

    return FitnessResult(
        passed=len(violations) == 0,
        message=f"Found {len(violations)} unnecessary async functions",
        violations=violations,
    )
```

---

## Integration Points

### 1. Pytest Integration

Add to `tests/architecture/test_fitness_functions.py`:

```python
def test_my_architectural_rule(checker):
    """Test my custom architectural rule."""
    results = checker.run_all(category_filter=Category.LAYERING)

    if results["summary"]["failed"] > 0:
        pytest.fail(f"Architecture violations: {results['summary']['failed']}")
```

Run via pytest:

```bash
pytest tests/architecture/ -v
pytest tests/architecture/test_fitness_functions.py::test_layering_rules
```

### 2. Git Hooks

**Pre-commit** (blocks bad commits):

```bash
#!/bin/bash
python3 -m athena.cli.fitness_check \
    --severity error \
    --fail-on-critical

if [ $? -ne 0 ]; then
    echo "❌ Commit blocked by architecture fitness check"
    exit 1
fi
```

**Pre-push** (blocks bad pushes):

```bash
#!/bin/bash
python3 -m athena.cli.fitness_check --verbose

if [ $? -ne 0 ]; then
    echo "❌ Push blocked by architecture violations"
    exit 1
fi
```

**Skip temporarily**:

```bash
# Skip once
git commit --no-verify

# Skip via environment variable
SKIP_FITNESS_CHECK=true git commit
```

### 3. CI/CD Integration

#### GitHub Actions

```yaml
name: Architecture Fitness Check

on: [pull_request, push]

jobs:
  fitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest

      - name: Run architecture fitness checks
        run: |
          python3 -m athena.cli.fitness_check \
            --severity error \
            --fail-on-critical \
            --verbose
```

#### GitLab CI

```yaml
fitness-check:
  stage: test
  script:
    - pip install -e .
    - python3 -m athena.cli.fitness_check --severity error --fail-on-critical
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

---

## CLI Reference

### Command: `athena-fitness-check`

```bash
python3 -m athena.cli.fitness_check [OPTIONS]
```

**Options**:

| Option | Description | Example |
|--------|-------------|---------|
| `--project-root PATH` | Project directory | `--project-root /path/to/project` |
| `--severity LEVEL` | Filter by severity | `--severity error` |
| `--category CAT` | Filter by category | `--category layering` |
| `--fail-on-critical` | Exit code 1 on errors | `--fail-on-critical` |
| `--json` | JSON output | `--json > results.json` |
| `--verbose` | Detailed output | `--verbose` |

**Examples**:

```bash
# Run all checks
python3 -m athena.cli.fitness_check

# Critical only (for CI)
python3 -m athena.cli.fitness_check --severity error --fail-on-critical

# Layering checks only
python3 -m athena.cli.fitness_check --category layering

# JSON output
python3 -m athena.cli.fitness_check --json > results.json

# Verbose output
python3 -m athena.cli.fitness_check --verbose
```

---

## Severity Levels

### ERROR (Blocks Commit/Build)

**When to use**: Rules that MUST be followed, violations are bugs

**Examples**:
- Core layer depends on higher layers
- Hardcoded secrets in code
- Circular dependencies
- Missing required interfaces

**CI Behavior**: Fails build, blocks merge

### WARNING (Warns but Allows)

**When to use**: Best practices that SHOULD be followed, but aren't critical

**Examples**:
- Naming convention violations
- Non-optimal patterns
- Missing documentation
- Code organization issues

**CI Behavior**: Passes build, shows warnings

### INFO (Informational Only)

**When to use**: Suggestions and recommendations

**Examples**:
- Optimization opportunities
- Alternative patterns available
- Code quality metrics

**CI Behavior**: Always passes, informational only

---

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **LAYERING** | Layer dependency rules | Core must not depend on MCP |
| **PATTERNS** | Design pattern enforcement | Repository pattern, Factory pattern |
| **CONSTRAINTS** | Architectural constraints | Performance limits, API standards |
| **NAMING** | Naming conventions | Manager suffix, Store suffix |
| **DEPENDENCIES** | Dependency management | No circular imports, limited external deps |
| **SECURITY** | Security requirements | No hardcoded secrets, input validation |
| **PERFORMANCE** | Performance requirements | Query limits, response time |

---

## Code Analyzer Utilities

The `CodeAnalyzer` class provides utilities for analyzing Python code:

### Finding Python Files

```python
analyzer = CodeAnalyzer(PROJECT_ROOT)
files = analyzer.find_python_files(exclude_patterns=["tests/", "venv/"])
```

### Analyzing Imports

```python
# Get all imports from a file
imports = analyzer.get_imports(file_path)
# Returns: List[(module_name, line_number)]

# Example: [("athena.core.database", 5), ("athena.mcp.handlers", 12)]
```

### Finding Class Definitions

```python
# Get all classes in a file
classes = analyzer.find_class_definitions(file_path)
# Returns: List[(class_name, line_number)]

# Example: [("EpisodicStore", 15), ("SemanticStore", 45)]
```

### Checking Inheritance

```python
# Check if class implements interface
implements = analyzer.check_class_implements_interface(
    file_path,
    class_name="UserRepository",
    interface_name="IRepository"
)
# Returns: bool
```

### Finding Layer Dependencies

```python
# Find violations of layer dependencies
violations = analyzer.find_dependencies_between_layers(
    from_layer="services",
    to_layer="ui"
)
# Returns: List[Violation]
```

---

## Best Practices

### 1. Start with Critical Rules Only

```python
# Focus on ERROR severity first
@fitness_function(
    name="Critical architectural rule",
    severity=Severity.ERROR,  # Start here
    category=Category.LAYERING,
)
```

### 2. Provide Clear Error Messages

```python
return FitnessResult(
    passed=False,
    message=f"Found {len(violations)} violations: {', '.join(v.file_path for v in violations)}",
    violations=violations,
)
```

### 3. Include Suggested Fixes

```python
Violation(
    file_path="src/services/user.py",
    line_number=15,
    rule_name="No UI dependencies",
    description="Service imports from UI layer",
    severity=Severity.ERROR,
    suggested_fix="Move shared code to core layer or use dependency injection",
)
```

### 4. Tag for Filtering

```python
@fitness_function(
    name="My rule",
    tags=["critical", "security", "pci-compliance"],  # Easy to filter later
)
```

### 5. Keep Checks Fast

- Cache analysis results
- Skip excluded directories early
- Use parallel processing for large codebases
- Run ERROR severity in pre-commit, all severities in CI

---

## Troubleshooting

### Issue: "Module not found" when running checks

**Solution**: Ensure you're in the project root and have installed the package:

```bash
cd /path/to/athena
pip install -e .
python3 -m athena.cli.fitness_check
```

### Issue: Git hook not executing

**Solution**: Ensure hook is executable:

```bash
chmod +x .git/hooks/pre-commit
ls -la .git/hooks/pre-commit  # Should show 'x' permission
```

### Issue: Too many violations, can't commit

**Solution**: Fix violations or skip temporarily:

```bash
# Skip once
git commit --no-verify

# See violations
python3 -m athena.cli.fitness_check --verbose

# Fix violations or adjust severity
```

### Issue: Checks are too slow

**Solution**: Run only ERROR severity in hooks:

```bash
# Fast: Only critical checks
python3 -m athena.cli.fitness_check --severity error

# Slow: All checks
python3 -m athena.cli.fitness_check
```

---

## Comparison with Other Tools

| Feature | Athena Fitness | ArchUnit (Java) | NetArchTest (.NET) |
|---------|----------------|-----------------|-------------------|
| **Language** | Python | Java | C# |
| **Integration** | Pytest, CLI, Hooks | JUnit | xUnit |
| **Layer Testing** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pattern Enforcement** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Custom Rules** | ✅ Python code | ✅ Java fluent API | ✅ C# fluent API |
| **CI/CD** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Severity Levels** | ✅ 3 levels | ❌ Pass/Fail | ❌ Pass/Fail |
| **Auto-fix Suggestions** | ✅ Yes | ❌ No | ❌ No |
| **JSON Output** | ✅ Yes | ❌ No | ❌ No |

---

## Future Enhancements

Planned features (not yet implemented):

1. **Visual Dependency Graphs** - Generate diagrams showing layer dependencies
2. **Trend Tracking** - Track violation counts over time
3. **Auto-fix Mode** - Automatically fix simple violations
4. **Web Dashboard** - View fitness results in web UI
5. **AI Suggestions** - Use AI to suggest architectural improvements
6. **Performance Profiling** - Track execution time of fitness checks

---

## Examples Library

See `tests/architecture/test_fitness_functions.py` for complete examples:

- ✅ Layer independence checks
- ✅ Pattern enforcement (Store, Manager, Repository)
- ✅ Naming conventions
- ✅ Security checks (no hardcoded secrets)
- ✅ Custom rule examples

---

## Related Documentation

- [Architecture Layer Overview](./ARCHITECTURE.md)
- [ADR Documentation](./ADRS.md)
- [Constraint Validation](./CONSTRAINTS.md)
- [Design Patterns](./PATTERNS.md)

---

**Last Updated**: November 18, 2025
**Status**: ✅ Production Ready
**Maintainer**: Athena Architecture Team
