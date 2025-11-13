# Sandbox Setup & Configuration Guide

**Phase 3 Week 9 Deliverable**
**Status**: Production-Ready
**Last Updated**: December 30, 2025

This guide explains how to set up, configure, and use Athena's sandboxing system for safe code execution.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [SRT Configuration](#srt-configuration)
4. [Advanced Policies](#advanced-policies)
5. [Security Best Practices](#security-best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.10+
- Linux, macOS, or Windows with WSL2
- For SRT mode: OS-level package manager (apt, brew, etc.)

### 1. Install Athena

```bash
# Install with sandbox support
pip install -e ".[sandbox]"
```

### 2. Install SRT Binary

Anthropic's Sandbox Runtime is required for OS-level isolation:

```bash
# Linux (x86_64)
curl -fsSL https://github.com/anthropics/srt/releases/download/v0.1.0/srt-linux-x86_64 \
  -o /usr/local/bin/srt && chmod +x /usr/local/bin/srt

# macOS (Intel)
curl -fsSL https://github.com/anthropics/srt/releases/download/v0.1.0/srt-macos-x86_64 \
  -o /usr/local/bin/srt && chmod +x /usr/local/bin/srt

# macOS (Apple Silicon)
curl -fsSL https://github.com/anthropics/srt/releases/download/v0.1.0/srt-macos-arm64 \
  -o /usr/local/bin/srt && chmod +x /usr/local/bin/srt

# Verify installation
srt --version
```

### 3. Verify Installation

```bash
python -c "from athena.sandbox import SRTExecutor, SandboxConfig; print('✓ Sandbox installed')"
```

---

## Quick Start

### Execute Code in Default Sandbox

```python
from athena.sandbox import SRTExecutor, SandboxConfig

# Create executor with default config
config = SandboxConfig.default()
executor = SRTExecutor(config)

# Execute Python code
result = executor.execute("""
import json
data = {"name": "Alice", "age": 30}
print(json.dumps(data))
""")

print(f"Success: {result.success}")
print(f"Output: {result.stdout}")
print(f"Time: {result.execution_time_ms:.2f}ms")

# Always cleanup
executor.cleanup()
```

### Use Different Isolation Modes

```python
from athena.sandbox import SRTExecutor, SandboxConfig, SandboxMode

# Strict isolation (OS-level via SRT)
strict_executor = SRTExecutor(SandboxConfig.strict())

# Permissive mode (for development)
dev_executor = SRTExecutor(SandboxConfig.permissive())

# Mock mode (no actual sandboxing, for testing)
mock_executor = SRTExecutor(SandboxConfig(mode=SandboxMode.MOCK))
```

### Use Executor Pool for Efficiency

```python
from athena.sandbox import SRTExecutorPool, SandboxConfig

# Create pool of 4 reusable executors
with SRTExecutorPool(size=4, config=SandboxConfig.default()) as pool:
    for code in code_list:
        result = pool.execute(code)
        print(f"Executed: {result.success}")
```

---

## SRT Configuration

### Basic Configuration

```python
from athena.sandbox import SandboxConfig, ExecutionLanguage

config = SandboxConfig(
    mode=SandboxMode.SRT,                # OS-level isolation
    language=ExecutionLanguage.PYTHON,   # Code language
    timeout_seconds=30,                  # Max execution time
    max_memory_mb=256,                   # Memory limit
    allow_network=False,                 # Network access
    capture_output=True,                 # Capture stdout/stderr
)

is_valid, errors = config.validate()
if not is_valid:
    print(f"Config errors: {errors}")
```

### Preset Configurations

Athena provides three preset configurations:

```python
# 1. Strict (Maximum security, minimal access)
from athena.sandbox import SandboxConfig
config = SandboxConfig.strict()
# - Timeout: 10s
# - Memory: 128MB
# - Network: Disabled
# - Home: Blocked
# - Use case: Untrusted code

# 2. Permissive (Development mode)
config = SandboxConfig.permissive()
# - Timeout: 60s
# - Memory: 512MB
# - Network: Enabled
# - Use case: Development and testing

# 3. Default (Balanced)
config = SandboxConfig.default()
# - Timeout: 30s
# - Memory: 256MB
# - Network: Disabled
# - Use case: Most production scenarios
```

### Advanced Configuration

```python
from athena.sandbox import SandboxConfig, SandboxMode

config = SandboxConfig(
    # Resource limits
    timeout_seconds=45,
    max_memory_mb=512,
    max_cpu_percent=80.0,

    # File system limits
    max_file_size_mb=50,
    max_total_files=500,
    max_disk_space_mb=1000,

    # Network
    allow_network=True,
    allow_outbound_http=True,
    blocked_domains=["*.internal-company.com"],

    # Environment
    working_directory="/tmp/sandbox",
    environment_vars={
        "USER": "sandbox",
        "HOME": "/tmp/sandbox-home",
    },

    # Profiling
    enable_profiling=True,
    enable_tracing=False,
)
```

---

## Advanced Policies

### Using SRTConfigManager

For complex scenarios, use the policy builder:

```python
from athena.sandbox import SRTConfigManager, NetworkAccessMode

# Create manager
manager = SRTConfigManager(name="research-policy")

# Filesystem rules
manager.allow_read("/home/user/data", recursive=True,
                   description="Allow data directory")
manager.allow_write("/tmp", recursive=True,
                    description="Allow /tmp for temporary files")
manager.deny_path("/etc/passwd",
                  description="Block sensitive system files")

# Network rules
manager.allow_domain("api.github.com",
                     description="Allow GitHub API")
manager.allow_domain("*.pypi.org",
                     description="Allow PyPI access")
manager.deny_domain("*.internal-company.com",
                    description="Block internal network")

# Environment variables
manager.expose_env_var("GITHUB_TOKEN", "ghp_xxx", sensitive=True)
manager.expose_env_var("USER", "researcher", sensitive=False)

# Build policy
policy = manager.build()

# Save for reuse
policy.save("research_policy.json")
```

### Preset Policies

```python
from athena.sandbox import STRICT_POLICY, RESEARCH_POLICY, DEVELOPMENT_POLICY

# Strict: Zero external access
executor = SRTExecutor(config=SandboxConfig.strict())

# Research: GitHub/PyPI access
executor = SRTExecutor(config=SandboxConfig.research())

# Development: Full local+network access
executor = SRTExecutor(config=SandboxConfig.development())
```

### Creating Custom Policy Tiers

```python
from athena.sandbox import SRTConfigManager, NetworkAccessMode

def create_education_policy():
    """Policy for educational code execution."""
    return (
        SRTConfigManager("education")
        .allow_read("/home/student/assignments", recursive=True)
        .allow_write("/tmp", recursive=True)
        .allow_domain("api.github.com")
        .allow_domain("*.github.com")
        .allow_domain("*.stackexchange.com")
        .deny_domain("*.internal-university.com")
        .build()
    )

def create_api_policy():
    """Policy for API testing."""
    return (
        SRTConfigManager("api-testing")
        .allow_read("/etc/ssl/certs", recursive=True)
        .allow_write("/tmp", recursive=True)
        .set_network_mode(NetworkAccessMode.RESTRICTED)
        .allow_domain("*.example-api.com")
        .allow_domain("api.stripe.com")
        .allow_domain("api.github.com")
        .expose_env_var("API_KEY", "sk_test_xxx", sensitive=True)
        .expose_env_var("WEBHOOK_SECRET", "whsec_xxx", sensitive=True)
        .build()
    )
```

### Loading Policies from Files

```python
from athena.sandbox import SRTPolicy

# Load previously saved policy
policy = SRTPolicy.load("research_policy.json")

# Use in executor
config = SandboxConfig(policy=policy)
executor = SRTExecutor(config)
```

---

## Security Best Practices

### 1. Default-Deny Philosophy

Always default to the most restrictive policy:

```python
# ✅ Good: Start strict, add access as needed
manager = SRTConfigManager()  # Starts with sensible defaults
manager.allow_read("/home/user/data")
policy = manager.build()

# ❌ Avoid: Overly permissive
config = SandboxConfig(
    allow_network=True,
    allow_outbound_http=True,
    allow_eval=True,  # Never allow eval
)
```

### 2. Sensitive Data Management

```python
from athena.sandbox import SRTConfigManager

manager = SRTConfigManager()

# ✅ Mark credentials as sensitive (masked in logs)
manager.expose_env_var("API_KEY", "secret123", sensitive=True)

# ❌ Don't expose credentials
# manager.expose_env_var("PASSWORD", "secret", sensitive=False)
```

### 3. Network Isolation

```python
# ✅ Good: Explicit allowlist for domains
manager = SRTConfigManager()
manager.set_network_mode(NetworkAccessMode.RESTRICTED)
manager.allow_domain("api.github.com")  # Only what's needed
manager.allow_domain("pypi.org")

# ❌ Avoid: Blanket network access
config = SandboxConfig(allow_network=True)  # Too permissive
```

### 4. Filesystem Boundaries

```python
# ✅ Good: Explicit path boundaries
manager.allow_read("/home/user/data", recursive=True)
manager.allow_write("/tmp", recursive=True)  # Limited to /tmp

# ❌ Avoid: Overly broad paths
# manager.allow_write("/home", recursive=True)  # Too broad
```

### 5. Resource Limits

```python
# ✅ Good: Conservative limits prevent DoS
config = SandboxConfig(
    timeout_seconds=30,        # Max 30 seconds
    max_memory_mb=256,         # Max 256MB memory
    max_processes=5,           # Max 5 processes
)

# ❌ Avoid: Excessive resource limits
# config = SandboxConfig(
#     timeout_seconds=3600,      # 1 hour is too long
#     max_memory_mb=8192,        # 8GB is excessive
# )
```

### 6. Violation Monitoring

```python
result = executor.execute(untrusted_code)

if result.violations:
    print(f"Security violations detected: {result.violations}")
    # Log, alert, or quarantine
    for violation in result.violations:
        security_log.warning(f"Sandbox violation: {violation}")
```

---

## Troubleshooting

### SRT Binary Not Found

**Error**: `RuntimeError: SRT binary not found`

**Solution**:
```bash
# Install SRT
curl -fsSL https://github.com/anthropics/srt/releases/download/v0.1.0/srt-linux-x86_64 \
  -o /usr/local/bin/srt && chmod +x /usr/local/bin/srt

# Verify
srt --version
```

### RestrictedPython Not Installed

**Error**: `ImportError: RestrictedPython not installed`

**Solution**:
```bash
pip install RestrictedPython
```

### Execution Timeout

**Problem**: Code execution times out

**Solutions**:
```python
# Option 1: Increase timeout
config = SandboxConfig(timeout_seconds=60)

# Option 2: Optimize code
# - Remove infinite loops
# - Reduce nested loops
# - Use generators instead of lists

# Option 3: Use mock mode for testing
config = SandboxConfig(mode=SandboxMode.MOCK)
```

### Permission Denied Errors

**Problem**: `Permission denied` in stderr

**Solution**:
```python
# Check what paths are allowed
manager = SRTConfigManager()
print(manager.filesystem_rules)

# Add required permissions
manager.allow_read("/path/needed")
policy = manager.build()
```

### Memory Limit Exceeded

**Problem**: Out of memory error

**Solution**:
```python
# Increase memory limit
config = SandboxConfig(max_memory_mb=512)

# Or optimize code
# - Use generators instead of lists
# - Delete large objects when done
# - Process data in chunks
```

### Network Connection Refused

**Problem**: Network operations fail when allowed

**Solution**:
```python
# Verify network is allowed
config = SandboxConfig(allow_network=True)

# Allow specific domains
manager = SRTConfigManager()
manager.set_network_mode(NetworkAccessMode.RESTRICTED)
manager.allow_domain("example.com")
policy = manager.build()
```

### Cleanup Issues

**Problem**: Temporary files not cleaned up

**Solution**:
```python
# Always use context manager or explicit cleanup
try:
    executor = SRTExecutor(config)
    result = executor.execute(code)
finally:
    executor.cleanup()  # Ensures cleanup even if error

# Or use context manager
from athena.sandbox import SRTExecutorPool
with SRTExecutorPool(size=2) as pool:
    result = pool.execute(code)
# Auto-cleanup on exit
```

---

## Examples

### Example 1: Safe LLM-Generated Code Execution

```python
from athena.sandbox import SRTExecutor, SandboxConfig

def execute_llm_code(code: str) -> dict:
    """Execute LLM-generated code safely."""

    # Use strict config for untrusted code
    config = SandboxConfig.strict()
    executor = SRTExecutor(config)

    try:
        result = executor.execute(code)

        if result.violations:
            return {
                "success": False,
                "error": f"Security violations: {result.violations}"
            }

        if not result.success:
            return {
                "success": False,
                "error": result.stderr
            }

        return {
            "success": True,
            "output": result.stdout,
            "execution_time_ms": result.execution_time_ms
        }

    finally:
        executor.cleanup()

# Use it
code_from_llm = "print('Hello from LLM')"
result = execute_llm_code(code_from_llm)
print(result)
```

### Example 2: Data Processing Pipeline

```python
from athena.sandbox import SRTConfigManager, SRTExecutor, SandboxConfig

def create_data_pipeline():
    """Create secure data processing pipeline."""

    # Policy: Read from data dir, write to output dir
    policy = (
        SRTConfigManager("data-pipeline")
        .allow_read("/home/user/data", recursive=True)
        .allow_write("/home/user/output", recursive=True)
        .expose_env_var("INPUT_FILE", "/home/user/data/input.csv")
        .expose_env_var("OUTPUT_FILE", "/home/user/output/result.csv")
        .build()
    )

    code = """
import os
import csv

input_file = os.environ['INPUT_FILE']
output_file = os.environ['OUTPUT_FILE']

with open(input_file) as infile, open(output_file, 'w') as outfile:
    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()
    for row in reader:
        # Process row
        writer.writerow(row)
"""

    config = SandboxConfig(policy=policy)
    executor = SRTExecutor(config)

    try:
        result = executor.execute(code)
        return result.success
    finally:
        executor.cleanup()
```

### Example 3: Research Code Execution

```python
from athena.sandbox import RESEARCH_POLICY, SRTExecutor, SandboxConfig

def run_research_code(code: str):
    """Execute research code with GitHub/PyPI access."""

    config = SandboxConfig(policy=RESEARCH_POLICY)
    executor = SRTExecutor(config)

    try:
        result = executor.execute(code)

        if result.success:
            print("✓ Execution successful")
            print(f"Output:\n{result.stdout}")
        else:
            print(f"✗ Execution failed: {result.stderr}")

        if result.violations:
            print(f"⚠ Violations detected: {result.violations}")

        return result

    finally:
        executor.cleanup()
```

---

## Integration with MemoryAPI

The sandbox system integrates with Athena's MemoryAPI:

```python
from athena.mcp import MemoryAPI
from athena.sandbox import SRTExecutor, SandboxConfig

memory = MemoryAPI.create()

# Execute code and store result
config = SandboxConfig.default()
executor = SRTExecutor(config)

result = executor.execute(code)

# Remember execution in memory
memory.remember(
    memory_type="procedural",
    content=f"Executed: {code[:50]}...",
    tags=["execution", "sandbox"],
    context={"sandbox_id": result.sandbox_id}
)

executor.cleanup()
```

---

## Performance Considerations

- **SRT mode**: ~5-15ms overhead per execution
- **RestrictedPython**: ~1-3ms overhead per execution
- **Mock mode**: <1ms (for testing)

Use pooling for multiple executions:

```python
from athena.sandbox import SRTExecutorPool

# Pool size should match your concurrency needs
with SRTExecutorPool(size=4) as pool:
    for code in code_list:
        result = pool.execute(code)
        # Process result
```

---

## Next Steps

- **Week 10**: Code validator and execution context
- **Week 11**: Security test suite and performance benchmarking
- See [plan.md](../plan.md) for Phase 3 timeline

---

**Questions?** Check [SANDBOX_ANALYSIS_AND_INTEGRATION.md](SANDBOX_ANALYSIS_AND_INTEGRATION.md) for threat model and security analysis.
