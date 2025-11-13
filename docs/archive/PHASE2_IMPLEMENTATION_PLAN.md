# Phase 2: Code Execution Engine - Implementation Plan

**Timeline**: Weeks 3-4 (November 14-27, 2025)
**Status**: Kickoff
**Lead**: Claude Code + Team
**Effort**: ~80 hours (2 weeks × 4 engineers)

---

## Phase 2 Overview

Transform security design into a functioning code execution engine. This phase implements:
1. **Task 2.1**: Deno runtime setup with worker pool (Week 3)
2. **Task 2.2**: Code execution engine and sandbox orchestration (Week 4)
3. **Task 2.3**: State management and session persistence (Week 4)

### Success Criteria
- [ ] Deno runtime initializes in <100ms with worker pool
- [ ] Can execute 100 sequential TypeScript operations without memory leaks
- [ ] Resource limits enforced (5s timeout, 100MB memory, 10MB disk)
- [ ] State persists correctly across multiple code executions
- [ ] All error cases handled gracefully with structured logging
- [ ] 50+ integration tests passing
- [ ] Performance benchmarks baseline established

### Deliverables
| Task | Deliverable | Lines | Type |
|------|-------------|-------|------|
| 2.1 | `src/runtime/deno_executor.ts` | 800+ | Core Runtime |
| 2.1 | `src/runtime/worker_pool.ts` | 600+ | Worker Management |
| 2.1 | `src/runtime/resource_monitor.ts` | 400+ | Monitoring |
| 2.2 | `src/execution/code_executor.ts` | 700+ | Execution Engine |
| 2.2 | `src/execution/code_validator.ts` | 500+ | Validation |
| 2.3 | `src/session/session_manager.ts` | 600+ | State Management |
| 2.3 | `src/session/session_store.ts` | 400+ | Persistence |
| Tests | `tests/integration/execution_*.ts` | 1000+ | Integration Tests |
| Docs | `docs/PHASE2_EXECUTION_GUIDE.md` | 1500+ | Documentation |
| **Total** | **9+ files** | **6,500+** | **Code + Docs** |

---

## Task 2.1: Deno Runtime Setup & Worker Pool

### Objective
Set up Deno runtime infrastructure with pre-warmed worker pool for parallel code execution.

### Design

```
┌─────────────────────────────────────────────────────────┐
│ DenoExecutor (Main Orchestrator)                        │
├─────────────────────────────────────────────────────────┤
│ - Manages worker pool lifecycle                         │
│ - Routes code to available workers                      │
│ - Monitors resource usage                              │
│ - Handles cleanup and shutdown                         │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    ┌───▼──────┐         ┌─────▼──────┐
    │ Worker 1 │  . . .  │ Worker N   │
    │          │         │            │
    │ Deno     │         │ Deno       │
    │ Runtime  │         │ Runtime    │
    ├──────────┤         ├────────────┤
    │ Code     │         │ Code       │
    │ Executor │         │ Executor   │
    │ (500ms   │         │ (500ms     │
    │ startup) │         │ startup)   │
    └──────────┘         └────────────┘
```

### Implementation Files

#### 1. `src/runtime/deno_executor.ts` (800+ lines)

Main orchestrator for Deno runtime execution:

```typescript
interface DenoExecutorConfig {
  workerCount: number;          // Number of pre-warmed workers (default: 10)
  workerTimeout: number;        // Worker startup timeout (ms)
  maxConcurrent: number;        // Max concurrent executions
  logLevel: "debug" | "info" | "warn" | "error";
  enableMetrics: boolean;       // Track performance metrics
}

interface ExecutionContext {
  sessionId: string;
  code: string;
  timeout: number;
  memoryLimit: number;
  maxResultSize: number;
  toolContext: ToolContext;
}

class DenoExecutor {
  private workerPool: WorkerPool;
  private resourceMonitor: ResourceMonitor;
  private executionQueue: ExecutionRequest[];
  private activeExecutions: Map<string, ExecutionState>;

  constructor(config: DenoExecutorConfig);

  // Initialize runtime and warm up workers
  async initialize(): Promise<void>;

  // Execute code in sandbox
  async execute(context: ExecutionContext): Promise<CodeExecutionResult>;

  // Get current metrics
  getMetrics(): ExecutorMetrics;

  // Graceful shutdown
  async shutdown(): Promise<void>;
}

// Worker pool management
interface ExecutorMetrics {
  activeWorkers: number;
  queuedExecutions: number;
  totalExecutions: number;
  averageLatencyMs: number;
  workerUtilization: number;
  memoryUsageMb: number;
}
```

Key methods:
- `initialize()`: Start worker pool, warm up workers
- `execute()`: Queue and execute code, wait for result
- `getMetrics()`: Return performance statistics
- `shutdown()`: Graceful shutdown with cleanup

#### 2. `src/runtime/worker_pool.ts` (600+ lines)

Worker pool lifecycle management:

```typescript
interface WorkerState {
  id: string;
  process: Deno.Process;
  available: boolean;
  lastUsed: number;
  executionCount: number;
  currentExecution?: ExecutionState;
}

interface WorkerPoolConfig {
  size: number;                 // Number of workers
  timeout: number;              // Startup timeout
  maxAge: number;               // Recycle after N executions
  idleTimeout: number;          // Kill if idle > N ms
}

class WorkerPool {
  private workers: WorkerState[];
  private available: WorkerState[];
  private config: WorkerPoolConfig;

  constructor(config: WorkerPoolConfig);

  // Get available worker or wait
  async acquire(timeout: number): Promise<WorkerState>;

  // Return worker to pool
  release(worker: WorkerState): void;

  // Warm up pool
  async warmup(): Promise<void>;

  // Get pool status
  getStatus(): PoolStatus;

  // Shutdown all workers
  async shutdown(): Promise<void>;
}

interface PoolStatus {
  total: number;
  available: number;
  busy: number;
  averageAge: number;
  memoryUsageMb: number;
}
```

Key methods:
- `acquire()`: Get available worker (wait if none available)
- `release()`: Return worker to available pool
- `warmup()`: Pre-start all workers before use
- `getStatus()`: Monitoring and debugging information

#### 3. `src/runtime/resource_monitor.ts` (400+ lines)

Monitor resource usage and enforce limits:

```typescript
interface ResourceLimits {
  timeout: number;              // 5000ms
  memory: number;               // 100MB
  disk: number;                 // 10MB
  fileDescriptors: number;      // 10
}

interface ResourceUsage {
  cpuTimeMs: number;
  memoryMb: number;
  diskMb: number;
  fileDescriptorCount: number;
  wallTimeMs: number;
}

class ResourceMonitor {
  private limits: ResourceLimits;
  private activeMonitors: Map<string, Timeout>;

  constructor(limits: ResourceLimits);

  // Start monitoring execution
  start(executionId: string): void;

  // Check if limits exceeded
  check(executionId: string): ResourceViolation | null;

  // Stop monitoring
  stop(executionId: string): ResourceUsage;

  // Get current usage
  getUsage(executionId: string): ResourceUsage;
}

// Resource violation types
interface ResourceViolation {
  type: "timeout" | "memory" | "disk" | "file_descriptor";
  limit: number;
  current: number;
  exceeded: boolean;
}
```

Key methods:
- `start()`: Begin tracking resource usage
- `check()`: Detect limit violations
- `stop()`: Stop tracking and return final usage
- `getUsage()`: Get current resource snapshot

---

## Task 2.2: Code Execution Engine

### Objective
Implement safe code execution with validation, error handling, and session state management.

### Implementation Files

#### 1. `src/execution/code_executor.ts` (700+ lines)

Main code execution orchestrator:

```typescript
interface ExecutionState {
  id: string;
  code: string;
  state: "queued" | "validating" | "executing" | "filtering" | "done" | "error";
  startTime: number;
  error?: ExecutionError;
  result?: unknown;
  metrics?: ExecutionMetrics;
}

class CodeExecutor {
  private validator: CodeValidator;
  private filterPipeline: FilterPipeline;
  private denoExecutor: DenoExecutor;

  constructor(config: ExecutorConfig);

  // Main execution pipeline
  async execute(request: CodeExecutionRequest, context: ToolContext): Promise<CodeExecutionResult>;

  // Execute with timeout
  private async executeWithTimeout(code: string, timeout: number): Promise<ExecutionResult>;

  // Apply output filtering
  private async applyOutputFiltering(result: unknown, context: FilterContext): Promise<FilteredResult>;
}

// Execution stages
interface ExecutionPipeline {
  1_validate: (code: string) => ValidationResult;
  2_prepare: (code: string) => string;          // Wrap with session context
  3_execute: (code: string) => Promise<unknown>;
  4_filter: (result: unknown) => Promise<FilteredResult>;
  5_validate_result: (result: unknown) => boolean;
  6_return: (result: unknown) => CodeExecutionResult;
}
```

Execution flow:
```
Code Input
  ↓
[1] Syntax Validation (prevents injection)
  ↓
[2] Code Preparation (inject session context, tools)
  ↓
[3] Sandbox Execution (Deno worker, enforce limits)
  ↓
[4] Output Filtering (remove secrets, tokenize PII)
  ↓
[5] Result Validation (check size, format)
  ↓
CodeExecutionResult
```

#### 2. `src/execution/code_validator.ts` (500+ lines)

Validate code before execution to prevent injection:

```typescript
interface ValidationConfig {
  maxCodeLength: number;        // 100KB default
  maxStringLength: number;      // 10KB
  maxDepth: number;             // AST depth limit
  forbiddenPatterns: RegExp[];  // e.g., /require\(/
}

class CodeValidator {
  private config: ValidationConfig;
  private forbiddenPatterns: Map<string, RegExp>;

  constructor(config: ValidationConfig);

  // Validate entire code
  validate(code: string): ValidationResult;

  // Check syntax
  private checkSyntax(code: string): SyntaxError | null;

  // Scan for dangerous patterns
  private scanPatterns(code: string): PatternViolation[];

  // Validate AST
  private validateAST(ast: any): ASTError | null;
}

interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  metrics: ValidationMetrics;
}

// Security checks
const FORBIDDEN_PATTERNS = [
  /require\s*\(/,               // No require
  /eval\s*\(/,                  // No eval
  /Function\s*\(/,              // No Function constructor
  /process\./,                  // No process access
  /globalThis\./,               // No globals
];
```

Validation checks:
1. **Syntax**: Valid TypeScript/JavaScript
2. **Patterns**: No forbidden keywords (eval, require, process, etc.)
3. **AST**: Check abstract syntax tree for dangerous constructs
4. **Size**: Code not exceeding 100KB
5. **Strings**: Individual strings not exceeding 10KB

---

## Task 2.3: State Management & Session Persistence

### Objective
Manage execution state across multiple code runs and persist to database.

### Implementation Files

#### 1. `src/session/session_manager.ts` (600+ lines)

Manage execution sessions and state:

```typescript
interface SessionConfig {
  ttl: number;                  // Session time-to-live (ms)
  maxSessions: number;          // Max concurrent sessions
  persistState: boolean;        // Save to database
}

interface Session {
  id: string;
  userId?: string;
  createdAt: number;
  lastActivity: number;
  variables: Map<string, unknown>;  // User variables
  toolState: Record<string, unknown>; // Tool-specific state
  executionHistory: ExecutionRecord[];
  metadata: Record<string, unknown>;
}

class SessionManager {
  private sessions: Map<string, Session>;
  private sessionStore: SessionStore;
  private config: SessionConfig;

  constructor(config: SessionConfig, store: SessionStore);

  // Create new session
  async createSession(userId?: string): Promise<string>;

  // Get session
  getSession(sessionId: string): Session | null;

  // Update session variable
  setVariable(sessionId: string, name: string, value: unknown): void;

  // Get session variable
  getVariable(sessionId: string, name: string): unknown;

  // Record execution
  recordExecution(sessionId: string, result: CodeExecutionResult): void;

  // Save session
  async saveSession(sessionId: string): Promise<void>;

  // Load session
  async loadSession(sessionId: string): Promise<Session | null>;

  // Cleanup expired sessions
  async cleanup(): Promise<void>;
}

// Execution record (stored in session history)
interface ExecutionRecord {
  timestamp: number;
  code: string;
  result: unknown;
  error?: ExecutionError;
  metrics: ExecutionMetrics;
}
```

Key features:
- Session creation and lifecycle
- Variable storage (accessible to subsequent code)
- Tool state tracking
- Execution history (debugging, auditing)
- Session persistence to database
- Automatic cleanup of expired sessions

#### 2. `src/session/session_store.ts` (400+ lines)

Persist sessions to database:

```typescript
interface SessionSchema {
  session_id: string;
  user_id?: string;
  created_at: number;
  last_activity: number;
  variables: string;            // JSON-serialized
  tool_state: string;           // JSON-serialized
  execution_count: number;
  execution_history: string;    // JSON-serialized (last N records)
  metadata: string;             // JSON-serialized
}

class SessionStore {
  private db: Database;

  constructor(db: Database);

  // Initialize schema
  async init(): Promise<void>;

  // Save session
  async save(session: Session): Promise<void>;

  // Load session
  async load(sessionId: string): Promise<Session | null>;

  // Delete session
  async delete(sessionId: string): Promise<void>;

  // Find sessions by user
  async findByUser(userId: string): Promise<Session[]>;

  // Get session history
  async getHistory(sessionId: string, limit?: number): Promise<ExecutionRecord[]>;

  // Cleanup old sessions
  async cleanup(olderThan: number): Promise<number>;
}

// Database schema
const SESSION_SCHEMA = `
  CREATE TABLE IF NOT EXISTS execution_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at INTEGER NOT NULL,
    last_activity INTEGER NOT NULL,
    variables TEXT,
    tool_state TEXT,
    execution_count INTEGER DEFAULT 0,
    execution_history TEXT,
    metadata TEXT,
    created_at_idx INTEGER NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_user_id ON execution_sessions(user_id);
  CREATE INDEX IF NOT EXISTS idx_last_activity ON execution_sessions(last_activity);
`;
```

Key methods:
- `save()`: Persist session to database
- `load()`: Retrieve session from database
- `getHistory()`: Get execution history for debugging
- `cleanup()`: Remove old/expired sessions

---

## Integration Tests

Location: `tests/integration/execution_*.ts`

### Test Suite

```typescript
// execution_runtime.test.ts - Deno runtime tests
describe("DenoExecutor", () => {
  describe("initialization", () => {
    test("should initialize worker pool in <100ms");
    test("should warm up all workers before returning");
    test("should handle worker startup failures gracefully");
  });

  describe("code execution", () => {
    test("should execute simple code and return result");
    test("should enforce 5s timeout on long-running code");
    test("should enforce 100MB memory limit");
    test("should catch and report errors");
  });

  describe("worker pool", () => {
    test("should recycle workers after N executions");
    test("should handle worker crashes and respawn");
    test("should queue executions when workers busy");
  });

  describe("resource monitoring", () => {
    test("should track CPU and memory usage");
    test("should detect timeout violations");
    test("should prevent memory exhaustion attacks");
  });
});

// execution_validator.test.ts - Code validation tests
describe("CodeValidator", () => {
  describe("syntax validation", () => {
    test("should accept valid TypeScript");
    test("should reject invalid syntax");
  });

  describe("pattern detection", () => {
    test("should forbid require() calls");
    test("should forbid eval() calls");
    test("should forbid process access");
  });

  describe("size limits", () => {
    test("should reject code >100KB");
    test("should reject strings >10KB");
  });
});

// execution_session.test.ts - Session management tests
describe("SessionManager", () => {
  describe("session lifecycle", () => {
    test("should create new sessions");
    test("should retrieve sessions by ID");
    test("should expire old sessions");
  });

  describe("state management", () => {
    test("should store and retrieve variables");
    test("should maintain tool state across executions");
    test("should track execution history");
  });

  describe("persistence", () => {
    test("should persist sessions to database");
    test("should recover sessions from database");
    test("should cleanup expired sessions");
  });
});
```

### Test Matrix
| Component | Unit Tests | Integration | Performance |
|-----------|------------|-------------|-------------|
| DenoExecutor | 15+ | 10+ | 5+ |
| WorkerPool | 12+ | 8+ | 4+ |
| CodeValidator | 20+ | 5+ | - |
| CodeExecutor | 15+ | 10+ | 5+ |
| SessionManager | 18+ | 12+ | - |
| **Total** | **80+** | **45+** | **14+** |

**Target**: 50+ integration tests passing by end of Phase 2

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Worker warmup | <100ms | Pre-started, ready to execute |
| Code execution | <500ms | Typical operation (50-100ms payload) |
| Timeout enforcement | 5s ± 100ms | Resource monitor accuracy |
| Memory limit | 100MB ± 5MB | Deno heap limit |
| Session lookup | <10ms | In-memory map |
| Session persistence | <50ms | SQLite write |
| Output filtering | <100ms | Even with compression |

---

## Documentation Deliverables

**File**: `docs/PHASE2_EXECUTION_GUIDE.md` (1500+ lines)

Contents:
1. Runtime architecture overview
2. Worker pool design and tuning
3. Code execution flow details
4. Error handling strategy
5. Session management patterns
6. Performance tuning guide
7. Troubleshooting guide
8. API reference for new components
9. Test setup and running instructions
10. Deployment considerations

---

## Rollout Plan

### Week 3 (Nov 14-20): Infrastructure
- [ ] Implement DenoExecutor and WorkerPool
- [ ] Setup ResourceMonitor
- [ ] Create unit tests (30+ tests)
- [ ] Performance baseline

### Week 4 (Nov 21-27): Integration
- [ ] Implement CodeValidator and CodeExecutor
- [ ] Implement SessionManager and SessionStore
- [ ] Create integration tests (45+ tests)
- [ ] Full end-to-end testing
- [ ] Documentation

### Exit Criteria
- [ ] All 50+ integration tests passing
- [ ] Performance benchmarks meeting targets
- [ ] Documentation complete
- [ ] Code review passed
- [ ] Ready for Phase 3 (Tool Adapters)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Deno startup slow | MEDIUM | Pre-warm workers, measure baseline |
| Worker crashes | MEDIUM | Auto-respawn, health checks |
| Memory leaks | HIGH | Resource monitoring, periodic recycling |
| Code validation evasion | CRITICAL | Multiple validation layers, AST analysis |
| State corruption | MEDIUM | Transaction semantics, atomic saves |

---

## Success Metrics

By end of Phase 2:
- ✅ 10-worker pool pre-warmed in <100ms
- ✅ Can execute 100+ sequential operations without crashes
- ✅ Memory usage stays within 100MB limit per worker
- ✅ Timeout enforcement accurate within ±100ms
- ✅ All 50+ integration tests passing
- ✅ Documentation complete and reviewed
- ✅ Ready to begin Phase 3 (Tool Adapters)

---

**Next Phase**: Phase 3 - Tool Adapters & Integration (Weeks 5-6)
