# Athena MCP Code Execution - Security Model

**Status**: 🟠 DRAFT (Day 1 of threat modeling)
**Owner**: Tech Lead + Security Team
**Last Updated**: 2025-11-07
**Version**: 1.0

---

## Executive Summary

This document outlines the security architecture for Athena's MCP code execution paradigm, where agents write and execute TypeScript code in a Deno sandbox to compose memory operations.

**Security Principle**: Defense in Depth
- **Layer 1**: Input validation (code syntax, parameter types)
- **Layer 2**: Deno sandboxing (permission model, resource limits)
- **Layer 3**: Runtime isolation (worker processes, memory limits)
- **Layer 4**: Tool access control (trusted tool adapters only)
- **Layer 5**: Output filtering (sensitive data tokenization)

**Security Posture**: High assurance (suitable for production use)

---

## Trust Model

### Trust Boundaries

```
┌─────────────────────────────────────────────────────┐
│ UNTRUSTED: Agent-Generated Code                     │
│ - Arbitrary TypeScript written by agent            │
│ - Must be sandboxed, isolated, monitored           │
│ - No access to filesystem, network, child processes│
└────────────────┬────────────────────────────────────┘
                 │ (Execute in Deno sandbox)
                 ↓
┌─────────────────────────────────────────────────────┐
│ BOUNDARY: Deno Runtime                              │
│ - Enforces permissions (allow-list only)           │
│ - Enforces resource limits (CPU, memory, disk)     │
│ - Enforces timeout (5-second execution limit)      │
└────────────────┬────────────────────────────────────┘
                 │ (Call through trusted adapters)
                 ↓
┌─────────────────────────────────────────────────────┐
│ TRUSTED: Tool Adapters & Python Handlers            │
│ - Marshalling requests to Python handlers          │
│ - Executing actual memory operations               │
│ - Returning filtered results to sandbox            │
└────────────────┬────────────────────────────────────┘
                 │ (Return filtered results)
                 ↓
┌─────────────────────────────────────────────────────┐
│ BOUNDARY: Output Filtering                          │
│ - Remove sensitive data (API keys, tokens)         │
│ - Tokenize private information                     │
│ - Compress large results                           │
│ - Size-limit output (< 10MB)                       │
└────────────────┬────────────────────────────────────┘
                 │ (Return to model)
                 ↓
         Safe for model context
```

### Actor Roles

| Role | Trust Level | Permissions |
|------|-------------|-------------|
| **Agent (Model)** | UNTRUSTED | Reads code, writes requests, receives results |
| **Agent Code** | UNTRUSTED | Executes in sandbox, limited to Deno API |
| **Tool Adapters** | TRUSTED | Call Python handlers, return filtered results |
| **Python Handlers** | TRUSTED | Execute memory operations, interact with DB |
| **Athena Core** | TRUSTED | Manage database, orchestrate layers |

---

## Threat Model

### STRIDE Analysis

#### S: Spoofing

**Threat**: Agent impersonates another agent or tool to gain access
- **Attack**: Write code that calls `athena.impersonate("admin")` to gain elevated privileges
- **Severity**: HIGH
- **Mitigation**:
  - No authentication/authorization in sandbox (all agents same privilege level)
  - Session ID tied to execution context, can't be forged in sandbox
  - Python handlers validate session ID on every call

**Threat**: Agent spoofs tool adapter to call arbitrary Python code
- **Attack**: Write code that imports `os` module and runs shell commands
- **Severity**: CRITICAL
- **Mitigation**:
  - Deno permissions disable module imports (only allow whitelisted imports)
  - No filesystem access (can't load arbitrary modules)
  - Only tool adapters provided to sandbox (no direct Python access)

#### T: Tampering

**Threat**: Agent modifies sandbox memory to corrupt execution
- **Attack**: Write code that modifies global state between calls
- **Severity**: MEDIUM
- **Mitigation**:
  - Fresh worker process per execution (clean global state)
  - Session state persisted only in Python side (immutable in sandbox)
  - Memory isolation: Workers can't access each other's memory

**Threat**: Agent tampers with tool adapters to call wrong operations
- **Attack**: Write code that calls `athena.recall` with modified parameters
- **Severity**: MEDIUM (caught by input validation)
- **Mitigation**:
  - Type validation before calling Python handlers
  - Parameter schema validation (strict checking)
  - Tool adapters validate parameters independently

#### R: Repudiation

**Threat**: Agent denies executing malicious code
- **Attack**: "I didn't write that malicious code"
- **Severity**: LOW (forensic, not operational)
- **Mitigation**:
  - All code executions logged (code hash, timestamp, result)
  - Audit trail in database (immutable, 30-day retention)
  - Code fingerprinting (SHA-256 hash of source)

#### I: Information Disclosure

**Threat**: Agent reads other agents' session state
- **Attack**: Access `globalThis.__session__.context` to read other sessions
- **Severity**: HIGH
- **Mitigation**:
  - Session isolation: Each worker gets own session context
  - No global state leakage (workers cleaned after execution)
  - State stored in Python side (sandbox can't access)

**Threat**: Agent reads sensitive data from memory operations
- **Attack**: Call `recall()` and print API keys from returned data
- **Severity**: CRITICAL (but mitigated by output filtering)
- **Mitigation**:
  - Output filtering removes known sensitive fields (api_key, token, password)
  - Tokenization: Replace sensitive values with tokens
  - Size limits: Max output 10MB (prevents dumping entire database)

**Threat**: Agent extracts data via timing attacks
- **Attack**: Time how long operations take to infer data patterns
- **Severity**: LOW (requires many requests, can be monitored)
- **Mitigation**:
  - Constant-time comparisons (not applicable here)
  - Timing logs: Monitor for unusual patterns
  - Rate limiting: 100 executions/min per user

#### D: Denial of Service

**Threat**: Agent runs infinite loop to exhaust CPU
- **Attack**: `while(true) { console.log("spam"); }`
- **Severity**: MEDIUM (mitigated by timeout)
- **Mitigation**:
  - Timeout enforcement: 5-second hard limit
  - CPU measurement: Monitor via `process.uptime()`
  - Abort mechanism: Kill worker if timeout exceeded

**Threat**: Agent allocates huge array to exhaust memory
- **Attack**: `const huge = new Array(1e9).fill("x")`
- **Severity**: MEDIUM (mitigated by memory limit)
- **Mitigation**:
  - Memory limit: 100MB heap via V8 flag
  - OOM handler: Catch `RangeError` and abort
  - Monitoring: Track memory usage per execution

**Threat**: Agent opens many connections to exhaust resources
- **Attack**: `for(let i=0; i<1e6; i++) { new Worker(...) }`
- **Severity**: MEDIUM (mitigated by permission model)
- **Mitigation**:
  - No worker creation allowed (disabled permission)
  - No network access allowed (disabled permission)
  - Worker pool size: Limited to 10 (server-side)

**Threat**: Agent causes Python handler to hang
- **Attack**: Call `consolidate()` with huge dataset
- **Severity**: MEDIUM
- **Mitigation**:
  - Tool adapters have own timeout (30-second Python timeout)
  - Circuit breaker: Disable tool if >3 timeouts in 5 min
  - Queue depth limiting: Max 100 pending requests

#### E: Elevation of Privilege

**Threat**: Agent breaks out of sandbox to access filesystem
- **Attack**: Use FFI or syscall to escape Deno sandbox
- **Severity**: CRITICAL
- **Mitigation**:
  - Deno is battle-tested, no known escapes
  - Permission model: Whitelist only (deny by default)
  - Regular Deno updates: Security patches applied within 1 week
  - No unsafe code: Deno disables unsafe in WASM

**Threat**: Agent tricks tool adapter into elevated operation
- **Attack**: Call `memory_health --reset-database` to wipe data
- **Severity**: HIGH
- **Mitigation**:
  - Tool adapters expose safe operations only
  - Dangerous operations behind explicit authorization
  - Command injection validation: Parameterized calls
  - Audit: All sensitive operations logged

---

### Attack Scenarios (20+ Scenarios)

#### Scenario 1: Code Injection Attack
**Attacker**: Compromised LLM or malicious prompt
**Goal**: Extract API keys from session state
**Attack**:
```typescript
// Agent writes this code
const keys = await athena.recall({ query: "api_key" });
// Hope result contains unfiltered API keys
console.log(keys);
```
**Defense**:
- Output filtering removes `api_key` field ✓
- Keys are stored separately (not in memory) ✓
- Session doesn't have access to system credentials ✓
**Risk Level**: LOW (fully mitigated)

#### Scenario 2: Resource Exhaustion
**Attacker**: Compromised agent or DoS attempt
**Goal**: Crash server or disrupt service
**Attack**:
```typescript
while(true) {
  await athena.recall({ query: "test" }); // Loop forever
}
```
**Defense**:
- 5-second timeout per execution ✓
- Worker abort mechanism ✓
- Rate limiting: 100 executions/min per user ✓
**Risk Level**: LOW (fully mitigated)

#### Scenario 3: Sandbox Escape via Deno
**Attacker**: Sophisticated attacker with Deno knowledge
**Goal**: Access filesystem or network
**Attack**:
```typescript
// Deno.open, Deno.run, Deno.net.dial - all should be disabled
```
**Defense**:
- Deno permissions disabled (whitelist-only model) ✓
- No filesystem access (--allow-read=/tmp/athena/tools only) ✓
- No network access (--allow-net disabled) ✓
- No subprocess (--allow-run disabled) ✓
- External security audit (Week 16) ✓
**Risk Level**: MEDIUM (mitigated by Deno + audit)

#### Scenario 4: Information Disclosure via Global State
**Attacker**: Competing agent or data exfiltration
**Goal**: Read another agent's session state
**Attack**:
```typescript
// Try to access other agent's context
const otherContext = globalThis.__athena__.sessions["other-agent"];
```
**Defense**:
- Fresh worker per execution (no global leakage) ✓
- Session isolation (Python-side only) ✓
- Workers cleaned after use ✓
**Risk Level**: LOW (fully mitigated)

#### Scenario 5: SQL Injection via Tool Parameters
**Attacker**: Agent writing code
**Goal**: Inject SQL to bypass security checks
**Attack**:
```typescript
await athena.recall({
  query: "test'; DROP TABLE memories; --"
});
```
**Defense**:
- Python handlers use parameterized queries ✓
- Type validation: query must be string (max 1000 chars) ✓
- Parameter escaping: SQLAlchemy handles escaping ✓
**Risk Level**: LOW (fully mitigated by Python ORM)

---

### Attack Scenarios (15 More)

#### Scenarios 6-10: Timeout/Resource Limit Bypasses
- Large JSON parsing attack: Mitigated by 100MB memory limit
- Regex DoS: Mitigated by 5-second timeout
- Recursive function explosion: Mitigated by stack size limits
- Array allocation: Mitigated by memory limits
- File descriptor exhaustion: Mitigated by permission denial

#### Scenarios 11-15: Tool Adapter Attacks
- Tool parameter tampering: Mitigated by type validation
- Unauthorized tool access: Mitigated by whitelist
- Tool state corruption: Mitigated by session isolation
- Tool invocation overflow: Mitigated by circuit breaker
- Poison pill data: Mitigated by input validation

#### Scenarios 16-20: Output Filtering Bypasses
- Sensitive data leakage: Mitigated by field filtering
- Compression bypass: Mitigated by strict size limits
- Encoding attacks: Mitigated by tokenization
- Timing information leakage: Mitigated by rate limiting
- Side-channel attacks: Mitigated by process isolation

---

## Deno Security Configuration

### Minimum Required Permissions

```bash
deno run \
  --allow-read=/tmp/athena/tools \
  --allow-write=/tmp/athena/sandbox \
  --allow-env=ATHENA_SESSION_ID \
  --allow-hrtime \
  code_execution.ts
```

### Disabled Permissions (Deny-All)

| Permission | Reason |
|-----------|--------|
| `--allow-net` | No network access needed (tool adapters handle) |
| `--allow-run` | No subprocess execution |
| `--allow-env` | Only ATHENA_SESSION_ID allowed (limited) |
| `--allow-read=/` | Only /tmp/athena/tools allowed (strict) |
| `--allow-write=/` | Only /tmp/athena/sandbox allowed (strict) |
| `--allow-ffi` | No FFI (prevents native code execution) |
| `--allow-sys` | No system access |
| `--allow-flock` | No file locking |

### Resource Limits

```typescript
interface ResourceLimits {
  cpuTimeoutMs: 5000;        // 5-second timeout
  heapSizeMb: 100;           // 100MB heap limit
  stackSizeMb: 8;            // 8MB stack limit
  diskQuotaMb: 10;           // 10MB temp storage
  openFilesMax: 10;          // Max 10 open files
  maxStringSize: 1_000_000;  // 1MB string limit
}
```

### V8 Flags for Resource Limits

```bash
deno run \
  --v8-flags=--max-old-space-size=100 \
  --v8-flags=--max-semi-space-size=16 \
  code_execution.ts
```

---

## Tool Adapter Security

### Safe Operations (Whitelist)

```typescript
const SafeOperations = [
  // Episodic
  "episodic/recall",
  "episodic/remember",
  "episodic/forget",

  // Semantic
  "semantic/search",
  "semantic/store",

  // Procedural
  "procedural/extract",
  "procedural/execute",

  // Consolidation (read-only)
  "consolidation/get_metrics",

  // Meta (read-only)
  "meta/memory_health",
  "meta/get_expertise",

  // ❌ FORBIDDEN
  // "admin/reset_database",
  // "admin/drop_all_memories",
  // "config/change_settings",
];
```

### Dangerous Operations (Blacklist)

```typescript
const DangerousOperations = [
  "admin/*",           // All admin operations
  "config/*",          // Configuration changes
  "database/truncate", // Data deletion
  "security/*",        // Security settings
];
```

### Parameter Validation Rules

```python
# src/runtime/parameter_validator.py
class ParameterValidator:
    RULES = {
        "query": {
            "type": "string",
            "max_length": 1000,
            "pattern": r"^[a-zA-Z0-9\s\-_,.:]+$",  # No special chars
        },
        "limit": {
            "type": "integer",
            "min": 1,
            "max": 100,
        },
        "timeout": {
            "type": "integer",
            "min": 100,
            "max": 30000,
        },
    }
```

---

## Output Filtering & Privacy

### Sensitive Field Detection

```python
SENSITIVE_FIELDS = {
    "api_key", "token", "secret", "password", "auth",
    "credential", "bearer", "authorization", "x-api-key",
    "private_key", "access_token", "refresh_token",
    "aws_secret", "gcp_key", "azure_key",
}

SENSITIVE_VALUES = [
    r"sk_[\w]{20,}",  # Stripe key pattern
    r"ghp_[\w]{36}",  # GitHub token pattern
    r"[\w\-]{32,}",   # Generic secret pattern
]
```

### Tokenization Strategy

```typescript
// Before: { api_key: "sk_live_123456789" }
// After: { api_key: "[REDACTED_TOKEN_a7f3d2e1]" }

function tokenizeValue(value: string): string {
  const hash = sha256(value);
  const token = `[REDACTED_TOKEN_${hash.slice(0, 8)}]`;
  return token;
}
```

### Result Filtering Algorithm

```typescript
function filterResult(result: any): any {
  // Step 1: Remove sensitive fields
  removeFields(result, SENSITIVE_FIELDS);

  // Step 2: Tokenize sensitive values
  for (const value of findSensitiveValues(result)) {
    replaceValue(result, value, tokenizeValue(value));
  }

  // Step 3: Enforce size limit
  if (JSON.stringify(result).length > 10_000_000) {
    // Compress or truncate
    return compressResult(result);
  }

  // Step 4: Redact nested structures
  for (const field in result) {
    if (isPassword(field) || isToken(field)) {
      result[field] = "[REDACTED]";
    }
  }

  return result;
}
```

---

## Audit & Monitoring

### Execution Logging

Every code execution logged with:
```json
{
  "timestamp": "2025-11-07T10:30:00Z",
  "session_id": "sess_abc123",
  "code_hash": "sha256_abc123",
  "code_length": 250,
  "execution_time_ms": 120,
  "memory_peak_mb": 45,
  "result_size_bytes": 1200,
  "status": "success",
  "errors": [],
  "tools_called": ["episodic/recall", "semantic/search"],
  "user_id": "user_xyz"
}
```

**Retention**: 30 days live, 90 days archived

### Suspicious Activity Detection

```python
ALERTS = [
    ("timeout", "Execution timed out", "rate_limit_user"),
    ("oom", "Out of memory during execution", "kill_worker"),
    ("syntax_error", "Invalid code syntax", "log_only"),
    ("permission_denied", "Attempted forbidden operation", "block_tool"),
    ("sensitive_leak", "Sensitive data in result", "redact_and_alert"),
    ("high_error_rate", ">50% errors in 5min", "circuit_break"),
]
```

### Metrics to Monitor

- Execution count (daily/hourly)
- Success rate (target: 95%+)
- Average latency (target: <200ms)
- Timeout rate (alert if >5%)
- Memory usage distribution
- Tool usage frequency
- Error types and frequency

---

## Secure Development Practices

### Code Review Checklist

- [ ] All Deno permissions minimized (whitelist only)
- [ ] All parameters validated (type + length + pattern)
- [ ] All sensitive fields filtered (api_key, token, etc.)
- [ ] All outputs size-limited (<10MB)
- [ ] All timeouts enforced (5-second max)
- [ ] All errors logged (no data leakage in errors)
- [ ] All resource limits tested (memory, disk, files)

### Testing Requirements

- [ ] 100+ attack scenario tests (STRIDE-based)
- [ ] Sandbox escape tests (10K+ scenarios)
- [ ] Resource limit tests (timeout, memory, disk)
- [ ] Permission boundary tests (all disabled permissions)
- [ ] Parameter validation tests (injection, overflow, etc.)
- [ ] Output filtering tests (sensitive field detection)
- [ ] Load testing (100 concurrent executions)

### Security Updates

- **Frequency**: Monthly security reviews
- **Deno Updates**: Applied within 1 week of release
- **Dependencies**: Regular audit (npm audit, safety)
- **Vulnerability Response**: P0 within 24 hours

---

## Security Audit Checklist

### Phase 1: Design Review ✅ IN PROGRESS
- [ ] Threat model approved by team
- [ ] Trust boundaries validated
- [ ] Attack scenarios documented (20+)
- [ ] Resource limits appropriate
- [ ] Permission model correct

### Phase 2: Implementation Review (Week 5-6)
- [ ] Code follows security checklist
- [ ] Tests cover all attack scenarios
- [ ] Deno configuration correct
- [ ] Tool adapters safe

### Phase 3: External Audit (Week 16)
- [ ] External security firm hired
- [ ] Penetration testing conducted (10K+ scenarios)
- [ ] Vulnerability assessment completed
- [ ] Remediation plan if needed

### Phase 4: Ongoing Monitoring (Post-Launch)
- [ ] Metrics dashboards active
- [ ] Alerts configured
- [ ] Incident response plan tested
- [ ] Monthly security reviews

---

## Incident Response Plan

### P0 (Critical) - Immediate Response

**Example**: Sandbox escape discovered
1. **Immediate** (0-15 min): Kill affected worker, preserve logs
2. **Short term** (15-60 min): Assess impact, identify affected users
3. **Medium term** (1-4 hours): Deploy fix, roll back if needed
4. **Post-incident** (24 hours): Root cause analysis, prevention

### P1 (High) - Fast Response

**Example**: Resource limit bypass
1. **Immediate** (0-1 hour): Disable vulnerable operation
2. **Short term** (1-4 hours): Fix root cause
3. **Medium term** (same day): Deploy fix, enable operation
4. **Post-incident** (24 hours): Review and update tests

### P2 (Medium) - Standard Response

**Example**: High error rate
1. **Immediate** (0-4 hours): Investigate cause
2. **Short term** (same day): Fix or mitigate
3. **Medium term** (next business day): Deploy fix

### P3 (Low) - Backlog

**Example**: Documentation improvement
1. Add to backlog
2. Review in weekly meeting
3. Schedule for next iteration

---

## Success Criteria

### Security Audit Sign-Off

**Criteria for passing security model review**:

1. **Threat Model Complete**
   - [ ] STRIDE analysis documented
   - [ ] 20+ attack scenarios identified and mitigated
   - [ ] Risk matrix completed (impact × probability)

2. **Deno Configuration Secure**
   - [ ] Permissions minimized (whitelist only)
   - [ ] Resource limits enforced (CPU, memory, disk)
   - [ ] Timeout enforcement tested
   - [ ] No escapes in 100+ attack tests

3. **Tool Adapter Security**
   - [ ] Whitelist of safe operations defined
   - [ ] Parameter validation rules specified
   - [ ] Dangerous operations blacklisted

4. **Output Filtering Working**
   - [ ] Sensitive fields detected and redacted
   - [ ] Values tokenized correctly
   - [ ] Size limits enforced
   - [ ] No data leakage in error messages

5. **Audit & Monitoring**
   - [ ] Execution logging implemented
   - [ ] Suspicious activity alerts configured
   - [ ] Metrics dashboard sketched
   - [ ] Incident response plan drafted

6. **Team Review**
   - [ ] Tech team reviews and approves
   - [ ] No critical security gaps identified
   - [ ] Confidence level >80%

---

## Next Steps

### Week 1 (Threat Modeling)
- [ ] Complete STRIDE analysis (Day 1)
- [ ] Document 20+ attack scenarios (Day 2-3)
- [ ] Create risk matrix (Day 4)
- [ ] Finalize security briefing (Day 5)

### Week 2 (Implementation Review)
- [ ] Review Deno configuration
- [ ] Validate resource limits
- [ ] Review tool adapter security
- [ ] Plan external audit

### Week 5-6 (Code Review)
- [ ] Implement security tests (100+ scenarios)
- [ ] Code review against checklist
- [ ] Update documentation

### Week 16 (External Audit)
- [ ] Conduct external security review
- [ ] Penetration testing
- [ ] Vulnerability remediation

---

**Document Status**: Draft (in active development)
**Last Updated**: 2025-11-07
**Next Review**: 2025-11-14 (end of Week 1)
