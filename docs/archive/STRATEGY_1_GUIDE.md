# Strategy 1: Error Reproduction & Diagnosis

## Overview

**Strategy 1** teaches AI to learn from failures by systematically diagnosing errors, understanding their root causes, and preventing their recurrence. Rather than just catching exceptions, this strategy builds a knowledge base of failures to continuously improve system reliability.

**Core Philosophy**: *Every error is a learning opportunity.* By maintaining detailed error history and understanding patterns, we can predict and prevent failures before they occur.

---

## How It Works

### 1. Error Diagnosis Process

When an error occurs, the `ErrorDiagnostician` performs these steps:

```python
from athena.learning.error_diagnostician import ErrorDiagnostician

diagnostician = ErrorDiagnostician()

# Diagnose an error
diagnosed = diagnostician.diagnose(
    error_type="ValueError",
    message="invalid literal for int() with base 10: 'abc'",
    stack_trace="...",  # Full traceback
    context={"input": "abc", "expected_type": "int"}
)
```

The diagnosis includes:
- **Root Cause**: What fundamentally went wrong
- **Affected Component**: Which part of the system failed
- **Severity**: Critical, High, Medium, or Low
- **Reproduction Steps**: How to reliably reproduce the error
- **Solution**: Immediate fix for this instance
- **Prevention**: How to prevent this error in the future

### 2. Error History & Trends

The system tracks all diagnosed errors and detects patterns:

```python
# Get frequency information
frequency = diagnostician.get_error_frequency("ValueError")
# Returns: occurrences count, trend (increasing/stable/decreasing), first/last seen

# Get summary
summary = diagnostician.get_error_summary()
# Returns: error types, severity distribution, most common errors

# Get recommendations
recommendations = diagnostician.prevent_future_errors()
# Returns: list of prevention actions based on error patterns
```

### 3. Error Patterns

The system recognizes common error patterns:

| Error Type | Typical Cause | Prevention |
|-----------|--------------|-----------|
| **AttributeError** | Accessing non-existent attributes | Use `getattr()` with defaults or type hints |
| **TypeError** | Wrong type passed to function | Add type hints and use mypy |
| **ValueError** | Invalid value provided | Validate input at function entry |
| **KeyError** | Missing dictionary key | Use `.get()` with defaults |
| **IndexError** | Index out of range | Check length before indexing |
| **ConnectionError** | Network/service connection failed | Implement retry logic with backoff |
| **TimeoutError** | Operation exceeded time limit | Increase timeout or optimize operation |
| **ImportError** | Module not found | Verify installation and paths |
| **MemoryError** | Out of memory (CRITICAL) | Optimize memory usage, add limits |

---

## Core Classes

### ErrorDiagnostician

Main class for error diagnosis and learning:

```python
class ErrorDiagnostician:
    def diagnose(
        self,
        error_type: str,
        message: str,
        stack_trace: str,
        context: Dict[str, Any] = None,
    ) -> DiagnosedError:
        """Diagnose an error and determine root cause."""

    def analyze_traceback(self, traceback_str: str) -> Dict[str, Any]:
        """Parse Python traceback to extract key information."""

    def get_error_frequency(self, error_type: str) -> Optional[ErrorFrequency]:
        """Get frequency statistics for an error type."""

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all diagnosed errors."""

    def prevent_future_errors(self) -> List[str]:
        """Generate prevention recommendations based on error patterns."""
```

### DiagnosedError

Data class representing a fully diagnosed error:

```python
@dataclass
class DiagnosedError:
    error_id: str                      # Unique ID (e.g., "err_42")
    error_type: str                    # Python error type
    message: str                       # Error message
    stack_trace: str                   # Full traceback
    root_cause: str                    # What fundamentally went wrong
    affected_component: str            # Which part failed
    severity: str                      # critical|high|medium|low
    reproduction_steps: List[str]      # How to reproduce
    solution: str                      # How to fix it
    prevention: str                    # How to prevent it
    related_errors: List[str]          # IDs of similar errors
    timestamp: str                     # ISO timestamp
```

### ErrorPattern

Represents a recurring error pattern:

```python
@dataclass
class ErrorPattern:
    pattern_name: str                  # e.g., "Connection Timeout"
    description: str                   # What this pattern means
    regex: str                         # Pattern to match
    severity: str                      # critical|high|medium|low
    frequency: int                     # How many times seen
    last_seen: str                     # ISO timestamp
```

### ErrorFrequency

Statistical information about error occurrences:

```python
@dataclass
class ErrorFrequency:
    error_type: str                    # Type of error
    occurrences: int                   # Total count
    first_seen: str                    # ISO timestamp
    last_seen: str                     # ISO timestamp
    frequency_trend: str               # increasing|stable|decreasing
```

---

## Usage Examples

### Example 1: Diagnose a ValueError

```python
diagnostician = ErrorDiagnostician()

# When an error occurs in your system
try:
    int("not a number")
except ValueError as e:
    diagnosis = diagnostician.diagnose(
        error_type="ValueError",
        message=str(e),
        stack_trace=traceback.format_exc(),
        context={"input": "not a number", "expected": "integer"}
    )

    print(f"Root Cause: {diagnosis.root_cause}")
    # Output: "Invalid value provided"

    print(f"Solution: {diagnosis.solution}")
    # Output: "Validate input values before using them"

    print(f"Prevention: {diagnosis.prevention}")
    # Output: "Validate all inputs at function entry points"
```

### Example 2: Track Error Trends

```python
# Diagnose the same error type multiple times
for request in failed_requests:
    diagnostician.diagnose(
        error_type="ConnectionError",
        message=request.error_msg,
        stack_trace=request.traceback
    )

# Check if ConnectionError is becoming more frequent
frequency = diagnostician.get_error_frequency("ConnectionError")
if frequency.frequency_trend == "increasing":
    # Alert: ConnectionError is happening more often
    apply_circuit_breaker()
```

### Example 3: Learn from Error Patterns

```python
# Get summary to understand overall health
summary = diagnostician.get_error_summary()

if summary["critical"] > 0:
    # Critical errors need immediate attention
    alert_on_call_engineer()

if summary["total_errors"] > 10:
    # High error volume - comprehensive analysis needed
    recommendations = diagnostician.prevent_future_errors()
    for rec in recommendations:
        log_action_item(rec)
```

---

## Integration with Athena

### With Episodic Memory

Each diagnosed error becomes an episodic event:

```python
from athena.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()

# Diagnose error
diagnosis = diagnostician.diagnose(...)

# Store in memory for future learning
manager.remember({
    "type": "error_diagnosis",
    "error_type": diagnosis.error_type,
    "root_cause": diagnosis.root_cause,
    "severity": diagnosis.severity,
    "prevention": diagnosis.prevention,
})
```

### With Procedural Memory

Prevention steps become reusable procedures:

```python
# Extract error prevention as procedure
procedure = {
    "name": f"Handle {error_type}",
    "steps": diagnosis.reproduction_steps,
    "prevention": diagnosis.prevention,
}

manager.learn_procedure(procedure)
```

### With Consolidation

Error patterns are extracted during sleep-like consolidation:

```python
# During consolidation, patterns are identified
consolidator.consolidate()

# Result: "High frequency of ConnectionError - implement circuit breaker"
#         "ValueError pattern - add input validation layer"
```

---

## Best Practices

### 1. Always Capture Context

More context = better diagnosis:

```python
# ✅ Good
diagnosis = diagnostician.diagnose(
    error_type="ValueError",
    message=str(e),
    stack_trace=traceback.format_exc(),
    context={
        "input_value": user_input,
        "input_type": type(user_input).__name__,
        "expected_type": "int",
        "function": "process_payment",
        "user_id": 12345,
    }
)

# ❌ Avoid
diagnosis = diagnostician.diagnose(
    error_type="ValueError",
    message=str(e),
    stack_trace=""
)
```

### 2. Act on Trends

Use frequency trends to proactively improve:

```python
frequency = diagnostician.get_error_frequency("TimeoutError")

if frequency.frequency_trend == "increasing":
    # Proactively increase timeouts or optimize
    optimize_slow_queries()
    increase_timeout_threshold()
```

### 3. Review Recommendations Regularly

Use the prevention system as guidance:

```python
recommendations = diagnostician.prevent_future_errors()

# Schedule implementation of recommendations
for rec in recommendations:
    create_issue(
        title=f"Prevent: {rec}",
        priority="high" if "critical" in rec.lower() else "medium"
    )
```

### 4. Build Error-Handling Patterns

Use diagnosed errors to establish patterns:

```python
# If ValueError occurs repeatedly with validation-related inputs:
def robust_convert_to_int(value, default=None):
    """Based on diagnosed ValueError patterns."""
    try:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return default
    except (ValueError, TypeError):
        return default
```

---

## MCP Tool Integration

Strategy 1 is exposed via 3 MCP tools:

### 1. `diagnose_error`
Diagnose an error from stack trace and context:
```json
{
  "error_type": "ValueError",
  "message": "invalid input",
  "stack_trace": "...",
  "context": {"key": "value"}
}
```

### 2. `analyze_traceback`
Quick analysis of Python traceback:
```json
{
  "traceback_str": "Traceback (most recent call last)..."
}
```

### 3. `get_error_summary`
Get summary of all diagnosed errors:
```json
{
  "total_errors": 10,
  "error_types": {"ValueError": 5, "TypeError": 3},
  "critical": 1,
  "most_common": "ValueError"
}
```

---

## Performance Characteristics

| Operation | Time | Memory |
|-----------|------|--------|
| Diagnose error | <50ms | ~1KB per diagnosis |
| Get frequency | <10ms | O(n) where n = error count |
| Generate recommendations | <100ms | O(error_types) |
| Traceback analysis | <20ms | ~0.5KB |

---

## Testing

The strategy includes comprehensive tests:

```bash
# Run Strategy 1 tests
pytest tests/unit/test_learning_error_diagnosis.py -v

# Test coverage
# - Error diagnosis for all error types
# - Frequency tracking and trends
# - Error summary generation
# - Prevention recommendations
# - Traceback parsing
```

---

## Roadmap

### Phase 1 (Current)
- ✅ Error diagnosis from stack traces
- ✅ Error frequency tracking
- ✅ Trend detection (increasing/decreasing)
- ✅ Prevention recommendations

### Phase 2
- Root cause inference from code analysis
- ML-based error pattern classification
- Automatic error monitoring setup
- Integration with log analysis

### Phase 3
- Predictive error detection (before failure)
- Custom error handlers per component
- SLA impact calculation
- Automated remediation triggers

---

## References

- **Related Strategies**:
  - Strategy 3: Pattern Detection (find duplicate error handling)
  - Strategy 5: Git History (learn why errors occurred historically)
  - Strategy 7: Synthesis (evaluate error handling approaches)

- **Athena Layers**:
  - Episodic Memory: Stores error events with context
  - Procedural Memory: Stores error recovery procedures
  - Consolidation: Extracts error patterns

---

**Status**: Production-ready
**Test Coverage**: 23/23 tests passing
**Last Updated**: November 2024
