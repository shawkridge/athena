# Agent Code Execution Guide

## Overview

Phase 3 Week 10 introduces **direct code execution** capabilities to Athena's MemoryAPI. Agents can now:

1. **Execute Python code** directly in a sandbox environment
2. **Track execution context** with full I/O capture and violation detection
3. **Monitor security** with pre-execution validation and runtime checks
4. **Store execution records** in episodic memory for analysis and learning

This enables agents to:
- Run analysis code on data
- Execute procedures with parameters
- Test hypotheses programmatically
- Generate and run code dynamically
- Learn from execution outcomes

## Architecture

### Three-Layer Security Model

```
Layer 1: Pre-Execution (CodeValidator)
  ↓
Layer 2: Sandbox Execution (SRTExecutor or RestrictedPython)
  ↓
Layer 3: Post-Execution (ExecutionContext & Violation Logging)
```

### Execution Modes (Graceful Degradation)

1. **SRT Mode** (Most Secure): OS-level isolation with Anthropic's Sandbox Runtime
   - Full filesystem & network control
   - Process isolation
   - Resource limits

2. **RestrictedPython Mode**: Runtime code restrictions
   - Compiled code execution with restricted globals
   - Forbidden import detection
   - Safe built-ins only

3. **Plain Exec Mode** (Least Secure, Fallback): Basic Python execution
   - Used when SRT and RestrictedPython unavailable
   - Still captures I/O and tracks violations

## API Reference

### `api.execute_code()`

Execute Python, JavaScript, or Bash code in a sandbox.

**Signature:**
```python
def execute_code(
    code: str,
    language: str = "python",
    parameters: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 30,
    sandbox_policy: Optional[str] = None,
) -> Dict[str, Any]:
```

**Parameters:**
- `code` (str): Code to execute
- `language` (str): Programming language - `python`, `javascript`, or `bash`
- `parameters` (dict): Parameters passed to code as `parameters` variable
- `timeout_seconds` (int): Execution timeout (default 30s)
- `sandbox_policy` (str): Security policy - `strict`, `research`, or `development`

**Returns:**
```python
{
    "success": bool,              # Whether execution succeeded
    "execution_id": str,          # Unique execution ID
    "stdout": str,                # Captured standard output
    "stderr": str,                # Captured standard error
    "exit_code": int,             # Process exit code (0 = success)
    "execution_time_ms": float,   # Time taken to execute
    "violations": List[str],      # Security violations detected
    "sandbox_id": str,            # Sandbox execution ID
    "language": str,              # Language executed
    "timestamp": str,             # ISO timestamp
}
```

## Agent Code Examples

### Example 1: Simple Code Execution

```python
from athena.mcp.memory_api import MemoryAPI

api = MemoryAPI.create()

# Execute simple Python code
result = api.execute_code(
    code='''
result = 2 + 2
print(f"2 + 2 = {result}")
output = result
''',
    language="python"
)

print(f"Success: {result['success']}")
print(f"Output: {result['stdout']}")
# Output:
# Success: True
# Output: 2 + 2 = 4
```

### Example 2: Code with Parameters

```python
# Pass parameters to executed code
result = api.execute_code(
    code='''
names = parameters.get('names', [])
for name in names:
    print(f"Hello, {name}!")
''',
    language="python",
    parameters={"names": ["Alice", "Bob", "Charlie"]}
)

print(result['stdout'])
# Output:
# Hello, Alice!
# Hello, Bob!
# Hello, Charlie!
```

### Example 3: Error Handling

```python
# Code that raises an exception
result = api.execute_code(
    code='''
x = 10
y = 0
result = x / y  # Division by zero
''',
    language="python"
)

if not result['success']:
    print(f"Execution failed: {result['stderr']}")
    # Output: division by zero
else:
    print("Execution succeeded")
```

### Example 4: Data Analysis Workflow

```python
# Analyze code metrics
import json

analysis_code = '''
metrics = {
    "files_analyzed": 42,
    "lines_of_code": 1250,
    "test_coverage": 0.87,
    "cyclomatic_complexity": 3.2,
}
print(json.dumps(metrics))
'''

result = api.execute_code(
    code=analysis_code,
    language="python"
)

if result['success']:
    metrics = json.loads(result['stdout'])
    memory_id = api.remember(
        content=f"Code metrics: {metrics}",
        memory_type="semantic",
        tags=["code_metrics", "analysis"]
    )
    print(f"Stored analysis results in memory ID: {memory_id}")
```

### Example 5: Procedure Execution

```python
# Create and execute a procedure
proc_id = api.remember_procedure(
    name="analyze_code_quality",
    steps=[
        "Read source files",
        "Calculate metrics (LOC, cyclomatic complexity)",
        "Check test coverage",
        "Generate report"
    ],
    category="analysis"
)

# Generate code for procedure
code_result = api.generate_procedure_code(proc_id)

if code_result['success']:
    # Execute the generated code
    exec_result = api.execute_code(
        code=code_result['code'],
        language="python"
    )

    if exec_result['success']:
        print("Procedure executed successfully")
        print(f"Output: {exec_result['stdout']}")
```

### Example 6: Learning from Execution

```python
# Execute code and record the outcome
code = '''
import math
radius = parameters['radius']
area = math.pi * radius ** 2
print(f"Circle area: {area}")
'''

result = api.execute_code(
    code=code,
    language="python",
    parameters={"radius": 5.0}
)

# Record execution in episodic memory
event_id = api.remember_event(
    event_type="action",
    content="Executed geometry calculation",
    outcome="success" if result['success'] else "failure",
    context={
        "execution_id": result['execution_id'],
        "language": result['language'],
        "execution_time_ms": result['execution_time_ms'],
        "stdout_length": len(result['stdout']),
    }
)

# Consolidate learnings
api.consolidate(strategy="balanced", days_back=7)
```

### Example 7: Multi-Language Execution

```python
# JavaScript example
js_result = api.execute_code(
    code='''
const nums = [1, 2, 3, 4, 5];
const sum = nums.reduce((a, b) => a + b, 0);
console.log(`Sum: ${sum}`);
''',
    language="javascript"
)

# Bash example
bash_result = api.execute_code(
    code='''
echo "Current directory: $(pwd)"
echo "Files: $(ls -1 | wc -l)"
''',
    language="bash"
)

for name, result in [("JavaScript", js_result), ("Bash", bash_result)]:
    print(f"{name}: {result['success']} - {result['stdout']}")
```

### Example 8: Security Policy Control

```python
# Use STRICT policy for untrusted code
result = api.execute_code(
    code='print("Hello")',
    language="python",
    sandbox_policy="strict"  # Most restrictive
)

# Use RESEARCH policy for data analysis
result = api.execute_code(
    code='import numpy as np; print(np.__version__)',
    language="python",
    sandbox_policy="research"  # Allow common libraries
)

# Use DEVELOPMENT policy for testing
result = api.execute_code(
    code='import os; print(os.getcwd())',
    language="python",
    sandbox_policy="development"  # Most permissive
)
```

## ExecutionContext for Advanced Tracking

For fine-grained control over execution, use `ExecutionContext` directly:

```python
from athena.sandbox.execution_context import ExecutionContext

# Create execution context
context = ExecutionContext(
    execution_id="my_execution",
    language="python",
    timeout_seconds=30,
    track_resources=True,
    capture_io=True
)

# Start tracking
context.start()

try:
    # Execute code
    exec(your_code, context.exec_globals)

except Exception as e:
    context.set_exception(e)

finally:
    # Stop and get results
    context.stop()

    # Access captured output
    print(f"Output: {context.get_stdout()}")
    print(f"Errors: {context.get_stderr()}")

    # Check for violations
    if context.violations:
        print(f"Security violations: {context.violations}")

    # Get full execution record
    record = context.to_dict()
    print(f"Execution record: {record}")
```

## Security Considerations

### Sandbox Policies

**STRICT_POLICY:**
- Filesystem: read-only access to specific directories
- Network: all outbound blocked
- Best for: untrusted user code, security-sensitive operations

**RESEARCH_POLICY:**
- Filesystem: read/write to temp directory, read to project
- Network: restricted outbound (no credential services)
- Best for: data analysis, experiments, research workflows

**DEVELOPMENT_POLICY:**
- Filesystem: read/write to project directories
- Network: outbound allowed to developer services
- Best for: development, testing, trusted code

### Pre-Execution Validation

Code is automatically validated for:
- **Syntax errors**: Caught before execution
- **Forbidden imports**: os, subprocess, eval, etc.
- **Dangerous functions**: exec, compile, etc.
- **Type safety**: Function signatures checked

### Runtime Monitoring

Violations are logged for:
- **File operations**: Unauthorized reads/writes
- **Network operations**: Blocked connections
- **Resource exhaustion**: Memory/CPU limits exceeded
- **Timeout violations**: Execution exceeded time limit

### Best Practices

1. **Always check `success` flag** before using results
2. **Capture stderr** for error messages
3. **Use appropriate policies** for code sensitivity
4. **Set reasonable timeouts** for long operations
5. **Log execution results** for auditability
6. **Test code locally** before executing via API
7. **Use parameters** instead of hardcoding values

## Troubleshooting

### Code execution fails with "Code validation failed"

```python
# Check what validation errors occurred
result = api.execute_code(code=your_code)
if not result['success']:
    print(result.get('issues', []))
```

### SRT executor not available

The system will automatically fall back to RestrictedPython or plain exec:

```python
# Log shows: "SRT execution failed, falling back to restricted mode"
# Execution still succeeds with less isolation
result = api.execute_code(code=your_code)
assert result['success']  # Still works, different sandbox
```

### Code runs slowly

Check execution time and optimize:

```python
result = api.execute_code(code=your_code)
print(f"Execution time: {result['execution_time_ms']:.1f}ms")

# Consider:
# - Using algorithms with better complexity
# - Caching results
# - Breaking into smaller operations
```

### Violations detected

Review and address security issues:

```python
result = api.execute_code(code=your_code)
if result['violations']:
    print(f"Security violations: {result['violations']}")
    # Refactor code to not trigger violations
    # Or use less restrictive policy if appropriate
```

## Integration with MemoryAPI

Code execution integrates with all memory layers:

```python
# Execute → Remember → Recall workflow
result = api.execute_code(code)

# Store execution result
memory_id = api.remember(
    content=f"Executed code, output: {result['stdout']}",
    memory_type="semantic"
)

# Recall related code later
similar = api.recall("code execution analysis results")

# Build knowledge graph of executions
entity_id = api.remember_entity(
    name="analysis_execution",
    entity_type="process"
)
```

## Advanced Patterns

### Pattern 1: Code Generation → Validation → Execution

```python
# Generate code for a procedure
gen_result = api.generate_procedure_code(proc_id)

# Validate the generated code
val_result = api.validate_procedure_code(gen_result['code'])

# Execute if validation passes
if val_result['success'] and val_result['quality_score'] > 0.7:
    exec_result = api.execute_code(code=gen_result['code'])
```

### Pattern 2: Incremental Execution with Learning

```python
for iteration in range(5):
    # Execute analysis
    result = api.execute_code(
        code=analysis_code,
        parameters={"iteration": iteration}
    )

    # Learn from results
    api.remember(
        content=f"Iteration {iteration}: {result['stdout']}",
        memory_type="semantic",
        tags=[f"iteration_{iteration}"]
    )

    # Consolidate learning
    if iteration % 2 == 0:
        api.consolidate(strategy="quality")
```

### Pattern 3: Error Recovery with Fallback

```python
try:
    result = api.execute_code(
        code=preferred_code,
        language="python"
    )

    if not result['success']:
        # Try fallback code
        result = api.execute_code(
            code=fallback_code,
            language="python"
        )

        api.remember_event(
            event_type="decision",
            content="Fell back to alternative code",
            outcome="success" if result['success'] else "failure"
        )

except Exception as e:
    api.remember_event(
        event_type="error",
        content=f"Code execution error: {e}",
        outcome="failure"
    )
```

## Performance Characteristics

| Operation | Time | Memory |
|-----------|------|--------|
| Simple Python code | 50-100ms | 5-10MB |
| With I/O capture | +10ms | +2MB |
| SRT sandbox overhead | +20ms | +15MB |
| Code validation | 10-30ms | 1-5MB |

## Future Enhancements

- **Streaming execution**: Process results as they generate
- **Multi-process execution**: Parallel code execution
- **Persistent execution state**: Maintain state across calls
- **Resource profiling**: Detailed CPU/memory analysis
- **Execution replay**: Deterministic re-execution for debugging

## Related Documentation

- [SANDBOX_SETUP.md](SANDBOX_SETUP.md) - Sandbox configuration and installation
- [PROCEDURE_GUIDE.md](PROCEDURE_GUIDE.md) - Working with executable procedures
- [ARCHITECTURE_REPORT.md](ATHENA_ARCHITECTURE_REPORT.md) - System architecture
- [Phase 3 Plan](../plan.md#week-9-11-phase-3---sandboxed-code-execution) - Implementation timeline

## Quick Reference

```python
# Import
from athena.mcp.memory_api import MemoryAPI

# Create API
api = MemoryAPI.create()

# Execute code
result = api.execute_code(
    code="print('Hello, World!')",
    language="python"
)

# Check result
assert result['success']
print(result['stdout'])

# Store execution record
api.remember_event(
    event_type="action",
    content="Executed analysis code",
    outcome="success",
    context={
        "execution_id": result['execution_id'],
        "execution_time_ms": result['execution_time_ms']
    }
)
```

---

**Document Version**: 1.0 (Phase 3 Week 10)
**Status**: Complete
**Last Updated**: January 15, 2026
