# MCP Code Execution - API Contracts Reference

**Document Version**: 1.0
**Status**: Complete
**Last Updated**: 2025-11-07

---

## Overview

This document defines the API contracts for Athena's MCP code execution paradigm. These contracts specify how agents interact with the system through TypeScript code execution.

**Key Principle**: Contracts define clear boundaries between the Deno sandbox (untrusted agent code) and tool adapters (trusted Python handlers).

---

## Table of Contents

1. [Execution Flow Contracts](#execution-flow-contracts)
2. [Tool Adapter Contracts](#tool-adapter-contracts)
3. [Output Filtering Contracts](#output-filtering-contracts)
4. [Type System Contracts](#type-system-contracts)
5. [Error Handling Contracts](#error-handling-contracts)
6. [Session Management Contracts](#session-management-contracts)
7. [Examples & Usage Patterns](#examples--usage-patterns)

---

## Execution Flow Contracts

### Code Execution Request

**File**: `src/interfaces/execution.ts`

```typescript
interface CodeExecutionRequest {
  code: string;                          // TypeScript code to execute
  toolContext: ToolContext;              // Execution context
  timeout?: number;                      // Timeout (default: 5000ms)
  memoryLimit?: number;                  // Memory limit (default: 100MB)
  maxResultSize?: number;                // Max result size (default: 10MB)
  enableOutputFiltering?: boolean;       // Enable filtering (default: true)
  enableLogging?: boolean;               // Enable logging (default: true)
  metadata?: Record<string, unknown>;    // Optional metadata
}
```

**Contract Details**:

| Field | Type | Required | Constraints | Notes |
|-------|------|----------|-------------|-------|
| `code` | string | ✅ | Max 100KB, valid TypeScript | Agent-generated code to execute |
| `toolContext` | ToolContext | ✅ | See below | Provides session context |
| `timeout` | number | ❌ | 100-30000 | Override default timeout |
| `memoryLimit` | number | ❌ | 10-500 | Override default memory limit |
| `maxResultSize` | number | ❌ | 1-100 | Override default result size limit |
| `enableOutputFiltering` | boolean | ❌ | - | Whether to apply output filters |
| `enableLogging` | boolean | ❌ | - | Whether to log execution |
| `metadata` | object | ❌ | Flat structure | For tracing and debugging |

**Example Request**:

```typescript
const request: CodeExecutionRequest = {
  code: `
    const result = await athena.recall({ query: "memory" });
    return {
      found: result.length,
      firstItem: result[0]
    };
  `,
  toolContext: {
    sessionId: "sess_abc123",
    userId: "user_xyz",
    availableTools: ["episodic/recall", "semantic/search"],
    sessionState: { previousQuery: "test" },
    metadata: {
      startTime: Date.now(),
      timeout: 5000,
      memoryLimit: 100,
      requestId: "req_123"
    }
  },
  timeout: 5000,
  enableOutputFiltering: true
};
```

---

### Code Execution Result

**File**: `src/interfaces/execution.ts`

```typescript
interface CodeExecutionResult {
  success: boolean;                      // Whether execution succeeded
  output?: unknown;                      // Return value from code
  errors: ExecutionError[];              // Errors (if any)
  logs: string[];                        // Console output
  metrics: ExecutionMetrics;             // Performance metrics
  sessionState: Record<string, unknown>; // Updated session state
  wasFiltered: boolean;                  // Whether output was filtered
  originalSizeBytes: number;             // Original result size
  filteredSizeBytes: number;             // Filtered result size
}
```

**Contract Details**:

| Field | Type | Meaning |
|-------|------|---------|
| `success` | boolean | True if code executed without errors |
| `output` | unknown | Value returned from code (if successful) |
| `errors` | ExecutionError[] | Array of errors (empty if successful) |
| `logs` | string[] | Console.log() output during execution |
| `metrics` | ExecutionMetrics | Timing, memory, tool call statistics |
| `sessionState` | object | Updated session state after execution |
| `wasFiltered` | boolean | Whether sensitive data was removed |
| `originalSizeBytes` | number | Size before filtering |
| `filteredSizeBytes` | number | Size after filtering |

**Example Result** (Success):

```typescript
const result: CodeExecutionResult = {
  success: true,
  output: {
    found: 3,
    firstItem: { content: "...", timestamp: "2025-11-07T..." }
  },
  errors: [],
  logs: ["Query executed"],
  metrics: {
    executionTimeMs: 120,
    memoryPeakMb: 45,
    toolCallsCount: 1,
    avgToolLatencyMs: 115,
    timeoutCount: 0,
    errorCount: 0,
    resultSizeBytes: 1200,
    outputFiltered: true,
    custom: {}
  },
  sessionState: { previousQuery: "memory", queryCount: 1 },
  wasFiltered: true,
  originalSizeBytes: 2400,
  filteredSizeBytes: 1200
};
```

**Example Result** (Error):

```typescript
const result: CodeExecutionResult = {
  success: false,
  output: undefined,
  errors: [{
    type: "syntax_error",
    message: "Unexpected token }",
    line: 5,
    column: 10,
    snippet: "await athena.recall(}",
    suggestion: "Remove extra closing brace"
  }],
  logs: [],
  metrics: { /* ... */ },
  sessionState: { /* unchanged */ },
  wasFiltered: false,
  originalSizeBytes: 0,
  filteredSizeBytes: 0
};
```

---

### Tool Context

**File**: `src/interfaces/execution.ts`

```typescript
interface ToolContext {
  sessionId: string;                     // Unique session identifier
  userId?: string;                       // Optional user ID
  availableTools: string[];              // List of callable tools
  sessionState: Record<string, unknown>; // Persistent state
  metadata: {
    startTime: number;
    timeout: number;
    memoryLimit: number;
    requestId: string;
  };
}
```

**Contract**: Tool context MUST be provided by the server and is READ-ONLY to sandbox code.

**Example**:

```typescript
const context: ToolContext = {
  sessionId: "sess_abc123",
  userId: "user_xyz",
  availableTools: [
    "episodic/recall",
    "episodic/remember",
    "semantic/search",
    "consolidation/get_metrics"
  ],
  sessionState: {
    queryHistory: ["test", "search"],
    conversationId: "conv_456",
    customData: { theme: "dark" }
  },
  metadata: {
    startTime: 1730959200000,
    timeout: 5000,
    memoryLimit: 100,
    requestId: "req_abc123"
  }
};
```

---

## Tool Adapter Contracts

### ToolAdapter Interface

**File**: `src/interfaces/adapter.ts`

```typescript
interface ToolAdapter {
  name: string;                                        // Adapter name
  category: string;                                   // Category
  version: string;                                    // Version
  operations: ToolOperation[];                        // Available operations

  execute(operationName: string, parameters: Record<string, unknown>, context: ToolContext): Promise<unknown>;
  getOperation(operationName: string): ToolOperation | undefined;
  validateParameters(operationName: string, parameters: Record<string, unknown>): ValidationResult;
  hasOperation(operationName: string): boolean;
  getStatus(): AdapterStatus;
  dispose?(): Promise<void>;
}
```

**Contract Guarantees**:

1. ✅ Adapter is stateless (safe to call concurrently)
2. ✅ All operations validated before execution
3. ✅ Results are JSON-serializable
4. ✅ Errors thrown as ExecutionError type
5. ✅ Operations respect resource limits

**Example Implementation**:

```typescript
const episodicAdapter: ToolAdapter = {
  name: "episodic",
  category: "memory",
  version: "1.0.0",
  operations: [
    {
      name: "recall",
      id: "episodic/recall",
      category: "memory",
      description: "Retrieve episodic memories by query",
      parameters: [
        {
          name: "query",
          type: { name: "string" },
          required: true,
          description: "Search query"
        },
        {
          name: "limit",
          type: { name: "integer" },
          required: false,
          default: 10,
          description: "Max results"
        }
      ],
      returns: {
        name: "array",
        elementType: {
          name: "object",
          properties: {
            id: { name: "string" },
            content: { name: "string" },
            timestamp: { name: "string" }
          }
        }
      }
    }
  ],

  async execute(opName, params, context) {
    if (!this.hasOperation(opName)) {
      throw new Error(`Unknown operation: ${opName}`);
    }

    const validation = this.validateParameters(opName, params);
    if (!validation.valid) {
      throw new Error(`Invalid parameters: ${validation.errors[0].message}`);
    }

    // Execute actual operation (delegates to Python)
    return await callPythonHandler("episodic", opName, params, context);
  },

  getOperation(opName) {
    return this.operations.find(op => op.name === opName);
  },

  validateParameters(opName, params) {
    const op = this.getOperation(opName);
    if (!op) return { valid: false, errors: [{ parameter: "", message: "Unknown operation" }] };

    const errors: ValidationError[] = [];
    for (const param of op.parameters) {
      if (param.required && !(param.name in params)) {
        errors.push({
          parameter: param.name,
          message: `Required parameter missing: ${param.name}`,
          expected: param.type.name
        });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      parameters: params
    };
  },

  hasOperation(opName) {
    return this.operations.some(op => op.name === opName);
  },

  getStatus() {
    return {
      name: this.name,
      healthy: true,
      status: "ready",
      uptimeMs: 3600000,
      successCount: 1250,
      errorCount: 3,
      avgLatencyMs: 85,
      lastCheckTime: new Date().toISOString()
    };
  }
};
```

---

### Tool Operation

**File**: `src/interfaces/adapter.ts`

```typescript
interface ToolOperation {
  name: string;
  id: string;
  category: string;
  description: string;
  longDescription?: string;
  parameters: ToolParameter[];
  returns: ToolTypeSpec;
  example?: string;
  exampleResult?: unknown;
  deprecated?: boolean;
  replacedBy?: string;
  related?: string[];
  expectedDurationMs?: number;
  timeoutMs?: number;
  permissions?: string[];
  mutating?: boolean;
  readsSensitive?: boolean;
  writesSensitive?: boolean;
  cost?: number;
  since?: string;
  tags?: string[];
}
```

**Example**:

```typescript
const recallOperation: ToolOperation = {
  name: "recall",
  id: "episodic/recall",
  category: "episodic",
  description: "Retrieve episodic memories matching query",
  longDescription: `
    Search episodic memory for events matching the given query.
    Uses semantic similarity to find relevant events.
    Returns up to 'limit' most relevant events.
  `,
  parameters: [
    {
      name: "query",
      type: { name: "string", maxLength: 1000 },
      required: true,
      description: "Search query",
      examples: ["code review", "meeting notes"],
      position: 0
    },
    {
      name: "limit",
      type: { name: "integer", minimum: 1, maximum: 100 },
      required: false,
      default: 10,
      description: "Maximum results to return",
      position: 1
    }
  ],
  returns: {
    name: "array",
    elementType: {
      name: "object",
      properties: {
        id: { name: "string", description: "Event ID" },
        content: { name: "string", description: "Event content" },
        timestamp: { name: "string", format: "iso-date", description: "Event time" },
        confidence: { name: "number", minimum: 0, maximum: 1 }
      }
    }
  },
  example: `const memories = await athena.recall({ query: "meeting", limit: 5 });`,
  exampleResult: [
    {
      id: "evt_123",
      content: "Team standup meeting",
      timestamp: "2025-11-07T10:30:00Z",
      confidence: 0.95
    }
  ],
  expectedDurationMs: 100,
  timeoutMs: 5000,
  mutating: false,
  readsSensitive: false,
  cost: 1,
  since: "1.0.0",
  tags: ["read", "query", "episodic"]
};
```

---

## Output Filtering Contracts

### DataFilter Interface

**File**: `src/interfaces/filter.ts`

```typescript
interface DataFilter {
  filter(data: unknown, context: FilterContext): FilterResult;
  getMetadata(): FilterMetadata;
  needsFiltering(data: unknown): boolean;
}
```

**Contract Guarantees**:

1. ✅ Filters are idempotent (multiple applications = single application)
2. ✅ Original data is never modified
3. ✅ Filtering always completes (no infinite loops)
4. ✅ Result size < input size (unless no filtering needed)

**Example Filter Implementation**:

```typescript
const sensitiveFieldFilter: DataFilter = {
  filter(data, context) {
    const sensitiveFields = [
      "api_key", "token", "password", "secret",
      "auth", "credential", "apiKey", "accessToken"
    ];

    const result = {
      data: JSON.parse(JSON.stringify(data)), // Deep copy
      originalSize: JSON.stringify(data).length,
      sensitiveFieldsRemoved: [],
      filtersApplied: ["sensitive_field_redaction"]
    };

    for (const field of sensitiveFields) {
      this.redactField(result.data, field);
      if (fieldWasFound) result.sensitiveFieldsRemoved.push(field);
    }

    result.filteredSize = JSON.stringify(result.data).length;
    result.reductionPercent =
      ((result.originalSize - result.filteredSize) / result.originalSize) * 100;

    return result;
  },

  getMetadata() {
    return {
      name: "sensitive_field_redaction",
      type: "field_removal",
      version: "1.0",
      description: "Removes sensitive fields from results"
    };
  },

  needsFiltering(data) {
    // Check if data contains any sensitive fields
    return this.hasSensitiveFields(data);
  },

  private redactField(obj: any, fieldName: string) {
    // Recursive redaction
    if (typeof obj !== "object" || obj === null) return;

    for (const key in obj) {
      if (key.toLowerCase().includes(fieldName.toLowerCase())) {
        obj[key] = "[REDACTED]";
      } else if (typeof obj[key] === "object") {
        this.redactField(obj[key], fieldName);
      }
    }
  }
};
```

---

### Sensitive Field Detector

**File**: `src/interfaces/filter.ts`

```typescript
interface SensitiveFieldDetector {
  detect(data: unknown): SensitiveField[];
  isSensitiveField(fieldName: string): boolean;
  isSensitiveValue(value: string): boolean;
}
```

**Sensitive Field List**:

```
api_key, apiKey, API_KEY
token, TOKEN, auth_token, authToken, access_token, accessToken
secret, SECRET, password, PASSWORD
bearer, BEARER, authorization, AUTHORIZATION
credential, CREDENTIAL, private_key, privateKey
aws_secret, gcp_key, azure_key
```

**Sensitive Value Patterns**:

```regex
sk_[\w]{20,}                    // Stripe key
ghp_[\w]{36}                    // GitHub token
^[A-Za-z0-9+/]{40,}=*$          // Base64 secret
-----BEGIN PRIVATE KEY-----     // PEM key header
```

---

### Data Tokenizer

**File**: `src/interfaces/filter.ts`

```typescript
interface DataTokenizer {
  tokenize(value: string, context: TokenizationContext): string;
  isTokenized(value: string): boolean;
  getTokenMetadata(token: string): TokenMetadata | null;
}
```

**Tokenization Algorithm**:

```
1. Hash original value: hash = SHA-256(value)
2. Create token: token = "[REDACTED_" + dataType + "_" + hash.slice(0, 8) + "]"
3. Example: "sk_live_123abc" → "[REDACTED_api_key_a1b2c3d4]"
```

**Contract Guarantee**: Original value cannot be recovered from token (one-way hash).

---

### Filter Pipeline

**File**: `src/interfaces/filter.ts`

```typescript
interface FilterPipeline {
  addFilter(filter: DataFilter, position?: number): void;
  removeFilter(filterName: string): boolean;
  apply(data: unknown, context: FilterContext): FilterResult;
  getFilters(): DataFilter[];
  getMetadata(): PipelineMetadata;
}
```

**Example Pipeline**:

```typescript
const pipeline = new FilterPipeline();

// Add filters in order
pipeline.addFilter(sensitiveFieldFilter, 0);      // Redact fields
pipeline.addFilter(sensitiveValueFilter, 1);     // Tokenize values
pipeline.addFilter(sizeFilter, 2);               // Enforce size limits
pipeline.addFilter(compressionFilter, 3);        // Compress if needed

// Apply pipeline
const result = pipeline.apply(executionResult, filterContext);
// Result: data with sensitive fields removed, values tokenized, compressed if large
```

---

## Type System Contracts

### ToolTypeSpec

**File**: `src/interfaces/adapter.ts`

```typescript
interface ToolTypeSpec {
  name: "string" | "number" | "integer" | "boolean" | "object" | "array" | "any" | "null" | "undefined" | "union" | "intersection" | "enum";
  elementType?: ToolTypeSpec;      // For arrays
  properties?: Record<string, ToolTypeSpec>;  // For objects
  enum?: unknown[];                // For enums
  oneOf?: ToolTypeSpec[];          // For unions
  allOf?: ToolTypeSpec[];          // For intersections
  inner?: ToolTypeSpec;            // For optional
  nullable?: boolean;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  pattern?: string;
  format?: string;
}
```

**Examples**:

```typescript
// string type
const stringType: ToolTypeSpec = {
  name: "string",
  maxLength: 1000,
  pattern: "^[a-zA-Z0-9 ]+$"
};

// array of objects
const arrayType: ToolTypeSpec = {
  name: "array",
  elementType: {
    name: "object",
    properties: {
      id: { name: "string" },
      value: { name: "number" }
    }
  }
};

// union type
const unionType: ToolTypeSpec = {
  name: "union",
  oneOf: [
    { name: "string" },
    { name: "number" }
  ]
};

// optional type
const optionalType: ToolTypeSpec = {
  name: "string",
  nullable: true,
  inner: { name: "string" }
};
```

---

## Error Handling Contracts

### ExecutionError

**File**: `src/interfaces/execution.ts`

```typescript
interface ExecutionError {
  type: "syntax_error" | "runtime_error" | "timeout_error" | "resource_error" | "permission_error" | "validation_error";
  message: string;
  stack?: string;
  line?: number;
  column?: number;
  snippet?: string;
  suggestion?: string;
}
```

**Error Types**:

| Type | Cause | Action |
|------|-------|--------|
| `syntax_error` | Invalid TypeScript code | Fix code syntax |
| `runtime_error` | Exception during execution | Check logic and parameters |
| `timeout_error` | Execution exceeded timeout | Optimize or increase timeout |
| `resource_error` | Memory/disk limit exceeded | Reduce data size or increase limit |
| `permission_error` | Unauthorized operation | Use whitelisted operation |
| `validation_error` | Parameter validation failed | Fix parameters |

**Example Errors**:

```typescript
// Syntax error
const syntaxError: ExecutionError = {
  type: "syntax_error",
  message: "Expected '}', got EOF",
  line: 5,
  column: 0,
  snippet: "const x = {",
  suggestion: "Add closing brace: }"
};

// Timeout error
const timeoutError: ExecutionError = {
  type: "timeout_error",
  message: "Execution exceeded 5000ms timeout",
  stack: "at executeCode (runtime.ts:120)"
};

// Permission error
const permissionError: ExecutionError = {
  type: "permission_error",
  message: "Operation 'admin/reset_database' is not whitelisted",
  suggestion: "Use whitelisted operations from the discovery API"
};
```

---

## Session Management Contracts

### SessionState

**File**: `src/interfaces/execution.ts`

```typescript
interface SessionState {
  sessionId: string;
  userId?: string;
  executionCount: number;
  totalExecutionTimeMs: number;
  createdAt: string;
  lastExecutedAt: string;
  data: Record<string, unknown>;
  metadata: {
    active: boolean;
    timeout: number;
    maxResults: number;
  };
}
```

**Contract Guarantees**:

1. ✅ Session state persists across executions
2. ✅ State is isolated per session (no cross-session leaks)
3. ✅ State can be updated by agent code
4. ✅ State is automatically cleaned up after timeout
5. ✅ State size limited to prevent abuse

**Example**:

```typescript
// Initial state
const initialState: SessionState = {
  sessionId: "sess_abc123",
  userId: "user_xyz",
  executionCount: 0,
  totalExecutionTimeMs: 0,
  createdAt: "2025-11-07T10:00:00Z",
  lastExecutedAt: "2025-11-07T10:00:00Z",
  data: {},
  metadata: { active: true, timeout: 3600000, maxResults: 100 }
};

// After first execution
const updatedState: SessionState = {
  ...initialState,
  executionCount: 1,
  totalExecutionTimeMs: 120,
  lastExecutedAt: "2025-11-07T10:01:15Z",
  data: {
    queryHistory: ["test query"],
    conversationId: "conv_456"
  }
};
```

---

## Examples & Usage Patterns

### Pattern 1: Simple Query

```typescript
// Agent writes this code
const memories = await athena.recall({
  query: "code review",
  limit: 5
});

// Result returned to agent (1KB)
{
  found: 3,
  items: [
    { id: "...", content: "...", timestamp: "..." }
  ]
}
```

### Pattern 2: Multi-Step Composition

```typescript
// Step 1: Recall related memories
const memories = await athena.recall({ query: "architecture" });

// Step 2: Filter locally
const important = memories.filter(m => m.confidence > 0.8);

// Step 3: Search semantic memory
const semanticResults = await athena.search({ query: "design patterns" });

// Step 4: Return combined result
return {
  episodic: important,
  semantic: semanticResults.slice(0, 3)
};
```

### Pattern 3: Session State Persistence

```typescript
// Use session state across executions
globalThis.__session__.data.queryCount = (globalThis.__session__.data.queryCount || 0) + 1;

if (globalThis.__session__.data.queryCount > 10) {
  return { error: "Too many queries in session" };
}

const result = await athena.recall({ query: "..." });
return result;
```

### Pattern 4: Error Handling

```typescript
try {
  const result = await athena.recall({ query: "..." });
  return { success: true, data: result };
} catch (error) {
  // Error is ExecutionError type
  return {
    success: false,
    error: error.message,
    type: error.type
  };
}
```

---

## Contract Validation

### At Compile Time

- TypeScript compiler validates interface usage
- Code generator ensures types match Python signatures
- Type tests verify bidirectional compatibility

### At Runtime

- Parameter validation before tool execution
- Result validation after tool execution
- Size limits enforced on all results
- Sensitive data filtering applied

### Monitoring

- Execution metrics tracked per operation
- Contract violations logged
- Performance baseline established
- Anomalies alerted

---

## Versioning

**API Version**: 1.0
**Status**: Stable
**Release Date**: 2025-11-07

### Backwards Compatibility

- ✅ All contracts guaranteed stable for 1 year
- ✅ Breaking changes require major version bump
- ✅ Deprecated operations supported for 6 months
- ✅ Migration path provided for deprecations

---

## Further Reading

- **Security Model**: `docs/SECURITY_MODEL.md`
- **Configuration**: `src/runtime/deno_config.ts`
- **Test Suite**: `tests/security/sandbox_tests.ts`
- **Project Plan**: `MCP_CODE_EXECUTION_PLAN.md`

---

**Document Status**: COMPLETE ✅
**Last Review**: 2025-11-07
**Next Review**: 2026-02-07
