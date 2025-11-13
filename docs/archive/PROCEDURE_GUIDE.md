# Procedure Guide: Working with Executable Procedures in Athena

## Overview

This guide covers how to use Athena's procedural memory system, which converts reusable workflows into executable Python code. Phase 2 of the MCP alignment project introduced code generation, validation, versioning, and execution capabilities.

**Status**: Phase 2 Week 8 Complete - 100% of core functionality implemented

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Working with MemoryAPI](#working-with-memoryapi)
4. [Code Generation](#code-generation)
5. [Code Validation](#code-validation)
6. [Version Management](#version-management)
7. [Execution and Statistics](#execution-and-statistics)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Initialize MemoryAPI

```python
from athena.mcp.memory_api import MemoryAPI

# Create MemoryAPI instance
api = MemoryAPI.create()

# Or with custom database
api = MemoryAPI.create(db_path="/path/to/memory.db")
```

### Basic Workflow

```python
# 1. Generate executable code for a procedure
result = api.generate_procedure_code(
    procedure_id=42,
    use_llm=True,
    refine_on_low_confidence=True
)

# 2. Validate the generated code
validation = api.validate_procedure_code(
    code=result["code"],
    procedure_id=42
)

# 3. Execute the procedure
execution = api.execute_procedure(
    procedure_id=42,
    parameters={"target": "src/main.py"}
)

# 4. Get statistics
stats = api.get_procedure_stats(procedure_id=42)
print(f"Success rate: {stats['success_rate']:.0%}")
```

---

## Core Concepts

### What are Executable Procedures?

Procedures are reusable workflows that have been converted from metadata definitions into executable Python code. They:

- Are versioned in git with full history
- Have confidence scores (0.0-1.0) indicating code quality
- Can be executed directly via MemoryAPI
- Track execution metrics (success rate, performance, etc.)
- Support rollback to previous versions

### Procedure Lifecycle

```
Define Procedure (steps, template)
    ↓
Generate Code (LLM-powered)
    ↓
Validate Code (syntax, security, quality)
    ↓
Store in Git (versioning)
    ↓
Execute Procedure
    ↓
Track Metrics (success, duration)
    ↓
Refine or Rollback
```

---

## Working with MemoryAPI

### 8 Procedure-Related Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `generate_procedure_code()` | Generate code using LLM | Dict with code, confidence, validation results |
| `validate_procedure_code()` | Check syntax, security, quality | Dict with quality score, issues, checks |
| `get_procedure_versions()` | Retrieve version history | Dict with list of versions |
| `rollback_procedure_code()` | Revert to previous version | Dict with rollback result |
| `execute_procedure()` | Run procedure code | Dict with outcome and metrics |
| `get_procedure_stats()` | Retrieve execution statistics | Dict with stats (usage, success rate, etc.) |
| `search_procedures_by_confidence()` | Find high-quality procedures | Dict with filtered procedure list |
| `remember_procedure()` | Store a new procedure | Procedure ID |

---

## Code Generation

### Generating Code for a Procedure

```python
result = api.generate_procedure_code(
    procedure_id=42,
    use_llm=True,           # Use Claude or local LLM
    refine_on_low_confidence=True  # Auto-refine if confidence <0.7
)

if result["success"]:
    print(f"Generated code:")
    print(result["code"])
    print(f"Confidence: {result['confidence']:.0%}")
    print(f"Issues: {result['issues']}")
else:
    print(f"Generation failed: {result['error']}")
```

### Return Structure

```python
{
    "success": bool,
    "procedure_id": int,
    "code": str,                          # Generated Python code
    "confidence": float,                  # 0.0-1.0 quality score
    "validation": {...},                  # Validation results
    "issues": [...],                      # Any issues or warnings
    "duration_seconds": float,            # How long generation took
    "timestamp": "ISO8601 string"
}
```

### Code Generation Options

#### LLM-Powered (Recommended)

```python
result = api.generate_procedure_code(
    procedure_id=42,
    use_llm=True  # Uses Claude API or local LLM
)
# Pros: High quality, handles complex procedures
# Cons: Requires API key or local model
```

#### Heuristic Fallback

```python
result = api.generate_procedure_code(
    procedure_id=42,
    use_llm=False  # Uses rule-based generation
)
# Pros: Always works, no dependencies
# Cons: Lower quality for complex procedures
```

#### Auto-Refinement

```python
result = api.generate_procedure_code(
    procedure_id=42,
    refine_on_low_confidence=True  # Automatically refine low-confidence code
)
# If confidence <0.7, LLM refines the code automatically
```

---

## Code Validation

### Validating Procedure Code

```python
result = api.validate_procedure_code(
    code="def my_procedure():\n    return 42",
    procedure_id=42  # Optional, for context
)

print(f"Quality score: {result['quality_score']:.0%}")
print(f"Checks: {result['checks']}")
for issue in result['issues']:
    print(f"  - {issue}")
```

### Validation Checks

The validator checks for:

1. **Syntax**: Valid Python code (AST parsing)
2. **Security**: No forbidden imports (os, subprocess, etc.)
3. **Quality**:
   - Docstrings present and complete
   - Error handling with try/except
   - Type hints on parameters and returns

### Return Structure

```python
{
    "success": bool,
    "procedure_id": int or None,
    "quality_score": float,              # 0.0-1.0
    "issues": [                          # List of issues found
        {
            "severity": "error|warning|info",
            "message": str,
            "line": int or None,
            "category": "syntax|security|style|completeness"
        }
    ],
    "checks": {
        "syntax": bool,                  # Valid Python syntax
        "security": bool,                # No forbidden imports
        "docstring": bool,               # Has docstring
        "error_handling": bool,          # Has try/except
        "type_hints": float              # Coverage % (0.0-1.0)
    },
    "duration_seconds": float,
    "timestamp": "ISO8601 string"
}
```

---

## Version Management

### Viewing Version History

```python
versions = api.get_procedure_versions(
    procedure_id=42,
    limit=10  # Last 10 versions
)

if versions["success"]:
    for v in versions["versions"]:
        print(f"{v['version']}: {v['message']} ({v['timestamp']})")
```

### Rolling Back to a Previous Version

```python
result = api.rollback_procedure_code(
    procedure_id=42,
    target_version="abc123def456",  # Git commit hash or version tag
    reason="Performance issue in current version"
)

if result["success"]:
    print(f"Rolled back to {result['target_version']}")
```

### Return Structure

```python
{
    "success": bool,
    "procedure_id": int,
    "target_version": str,  # Version rolled back to
    "procedure": {
        "name": str,
        "code_version": str
    },
    "timestamp": "ISO8601 string"
}
```

---

## Execution and Statistics

### Executing a Procedure

```python
result = api.execute_procedure(
    procedure_id=42,
    parameters={
        "target_file": "src/main.py",
        "debug": True
    }
)

if result["success"]:
    print(f"Outcome: {result['outcome']}")  # success, failure, skipped
    print(f"Duration: {result['duration_seconds']:.2f}s")
else:
    print(f"Error: {result['error']}")
```

### Execution Outcomes

| Outcome | Meaning |
|---------|---------|
| `success` | Code executed without errors |
| `failure` | Code raised an exception |
| `skipped` | No executable code available |

### Retrieving Procedure Statistics

```python
stats = api.get_procedure_stats(procedure_id=42)

if stats["success"]:
    print(f"Name: {stats['name']}")
    print(f"Usage count: {stats['usage_count']}")
    print(f"Success rate: {stats['success_rate']:.0%}")
    print(f"Avg time: {stats['avg_completion_time_ms']}ms")
    print(f"Code confidence: {stats['code_confidence']:.0%}")
```

### Return Structure

```python
{
    "success": bool,
    "procedure_id": int,
    "name": str,
    "usage_count": int,
    "success_rate": float,           # 0.0-1.0
    "avg_completion_time_ms": int,
    "code_confidence": float,        # 0.0-1.0
    "execution_stats": {...},        # Detailed execution metrics
    "timestamp": "ISO8601 string"
}
```

---

## Examples

### Example 1: Testing Workflow

```python
# Create or retrieve a testing procedure
procedure = api.remember_procedure(
    name="run_unit_tests",
    steps=[
        "Change to project directory",
        "Run pytest with coverage",
        "Report results"
    ],
    category="testing"
)

# Generate executable code
code_result = api.generate_procedure_code(
    procedure_id=procedure,
    use_llm=True
)

# Validate the code
val_result = api.validate_procedure_code(
    code=code_result["code"],
    procedure_id=procedure
)

if val_result["success"] and val_result["checks"]["syntax"]:
    # Execute the testing workflow
    exec_result = api.execute_procedure(procedure_id=procedure)

    # Get statistics
    stats = api.get_procedure_stats(procedure_id=procedure)
    print(f"Tests passed {stats['success_rate']:.0%} of the time")
```

### Example 2: Git Workflow

```python
# Create a git procedure
procedure = api.remember_procedure(
    name="commit_changes",
    steps=[
        "Stage all changes",
        "Commit with message",
        "Push to remote"
    ],
    category="git"
)

# Generate code
result = api.generate_procedure_code(procedure_id=procedure, use_llm=True)

# Find procedures with high confidence codes
high_quality = api.search_procedures_by_confidence(
    min_confidence=0.8,
    limit=10
)

print(f"Found {high_quality['count']} high-quality procedures")
```

### Example 3: Refactoring Workflow

```python
# Find refactoring procedures
refactoring_procs = api.recall_procedures("refactoring", limit=5)

for proc in refactoring_procs:
    # Check for issues with current code
    val = api.validate_procedure_code(
        code=proc["code"],
        procedure_id=proc["id"]
    )

    if val["checks"]["error_handling"] is False:
        # Regenerate with focus on error handling
        new_code = api.generate_procedure_code(
            procedure_id=proc["id"],
            use_llm=True
        )
        print(f"Updated {proc['name']} with better error handling")
```

---

## Troubleshooting

### Code Generation Fails

**Problem**: `generate_procedure_code()` returns `success=False`

**Solutions**:
1. Verify procedure exists: `api.recall_procedures()`
2. Check LLM availability (API key, local model)
3. Fall back to heuristic: `use_llm=False`
4. Check logs: `DEBUG=1 python script.py`

### Low Confidence Score

**Problem**: Generated code has confidence <0.5

**Solutions**:
1. Enable auto-refinement: `refine_on_low_confidence=True`
2. Validate and improve: use `validate_procedure_code()`
3. Manually review and edit the procedure definition
4. Add more examples to procedure template

### Validation Errors

**Problem**: Code fails validation

**Common Issues**:
- **Syntax errors**: Use Python formatter (black, ruff)
- **Security warnings**: Replace forbidden imports (os, subprocess, etc.)
- **Missing docstring**: Add docstring to function
- **No error handling**: Wrap logic in try/except

### Execution Fails

**Problem**: `execute_procedure()` returns `outcome=failure`

**Solutions**:
1. Review error message in result["error"]
2. Test code independently with `validate_procedure_code()`
3. Check execution parameters
4. Verify procedure has executable code (`code` field not empty)

### Version Issues

**Problem**: Can't find previous version

**Solutions**:
1. List all versions: `api.get_procedure_versions(procedure_id, limit=100)`
2. Check git history directly: `git log procedures/[id]`
3. Use most recent version if rollback fails

---

## Best Practices

### 1. Always Validate Before Executing

```python
# Good
val = api.validate_procedure_code(code)
if val["success"] and val["quality_score"] > 0.7:
    api.execute_procedure(procedure_id)

# Avoid
api.execute_procedure(procedure_id)  # No validation
```

### 2. Store Confidence for High-Value Procedures

```python
# Track only high-confidence procedures
high_conf = api.search_procedures_by_confidence(min_confidence=0.8)
for proc in high_conf["procedures"]:
    api.execute_procedure(proc["id"])
```

### 3. Handle Errors Gracefully

```python
result = api.execute_procedure(procedure_id)
if result["success"]:
    print("Execution successful")
else:
    # Log failure, don't crash
    print(f"Execution failed: {result.get('error', 'Unknown error')}")
    # Optionally rollback
    api.rollback_procedure_code(procedure_id, last_known_good_version)
```

### 4. Monitor Performance

```python
stats = api.get_procedure_stats(procedure_id)
if stats["success_rate"] < 0.7:
    # Regenerate with LLM
    new_code = api.generate_procedure_code(
        procedure_id,
        use_llm=True,
        refine_on_low_confidence=True
    )
```

---

## API Reference Summary

| Operation | Method | Returns |
|-----------|--------|---------|
| Generate code | `generate_procedure_code(id, use_llm, refine)` | {code, confidence, ...} |
| Validate code | `validate_procedure_code(code, id)` | {quality_score, checks, ...} |
| Get versions | `get_procedure_versions(id, limit)` | {versions, count, ...} |
| Rollback | `rollback_procedure_code(id, version, reason)` | {success, target_version, ...} |
| Execute | `execute_procedure(id, parameters)` | {success, outcome, duration, ...} |
| Get stats | `get_procedure_stats(id)` | {usage_count, success_rate, ...} |
| Search | `search_procedures_by_confidence(min, limit)` | {procedures, count, ...} |
| Store | `remember_procedure(name, steps, category)` | procedure_id |

---

## See Also

- [PHASE_2_IMPLEMENTATION_PLAN.md](PHASE_2_IMPLEMENTATION_PLAN.md) - Week 5-8 overview
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Converting 101 procedures to executable code
- [API_REFERENCE.md](API_REFERENCE.md) - Complete MCP tools reference

---

**Last Updated**: Week 8, Phase 2 MCP Alignment
**Status**: Complete & Production-Ready
