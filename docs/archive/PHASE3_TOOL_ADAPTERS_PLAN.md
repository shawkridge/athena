# Phase 3: Tool Adapters & Integration - Detailed Implementation Plan

**Timeline**: Weeks 5-6 (November 21 - December 4, 2025)
**Status**: Kickoff-ready with alignment adjustments
**Effort**: ~120 hours (3 weeks × 4 engineers)
**Blog Post Alignment**: 100% (with filesystem structure)

---

## Phase 3 Overview

Transform the code execution engine into a practical tool interface by:
1. Implementing tool adapters for all 8 memory layers
2. Creating filesystem-based tool discovery matching blog post
3. Integrating with MCP server
4. Building comprehensive integration tests

### Success Criteria
- [ ] All 8 memory layers exposed as tool adapters
- [ ] ./servers/ filesystem hierarchy fully functional
- [ ] Agents can discover tools via readdir/readFile
- [ ] 50+ end-to-end integration tests passing
- [ ] search_tools() utility working with detail levels
- [ ] Performance benchmarks: <300ms per tool call
- [ ] Full documentation with examples

### Deliverables
| Task | Deliverable | Files | Lines | Type |
|------|-------------|-------|-------|------|
| 3.1 | Tool Adapters (8 layers) | 80+ | 5,000+ | Implementation |
| 3.2 | MCP Server Integration | 10+ | 2,000+ | Integration |
| 3.3 | Filesystem Discovery | 20+ | 1,500+ | Infrastructure |
| 3.4 | Integration Tests | 30+ | 2,500+ | Testing |
| 3.5 | Documentation | 5+ | 1,500+ | Docs |
| **TOTAL** | **All layers exposed** | **145+ files** | **12,500+** | **Code + Docs** |

---

## Task 3.1: Tool Adapters for 8 Memory Layers

### Objective
Implement tool adapters for each memory layer following the blog post pattern.

### Directory Structure (Aligned with Blog Post)

```
src/servers/
├── episodic/
│   ├── recall.ts              # export async function recall()
│   ├── remember.ts            # export async function remember()
│   ├── forget.ts
│   ├── bulk_remember.ts
│   ├── query_temporal.ts
│   ├── list_events.ts
│   ├── index.ts               # Re-exports all operations
│   └── types.ts               # TypeScript interfaces
│
├── semantic/
│   ├── search.ts
│   ├── store.ts
│   ├── delete.ts
│   ├── update.ts
│   ├── list_memories.ts
│   ├── index.ts
│   └── types.ts
│
├── procedural/
│   ├── extract.ts
│   ├── execute.ts
│   ├── list.ts
│   ├── get_effectiveness.ts
│   ├── index.ts
│   └── types.ts
│
├── prospective/
│   ├── create_task.ts
│   ├── list_tasks.ts
│   ├── complete_task.ts
│   ├── update_task.ts
│   ├── get_task.ts
│   ├── create_goal.ts
│   ├── list_goals.ts
│   ├── index.ts
│   └── types.ts
│
├── graph/
│   ├── search_entities.ts
│   ├── get_entity.ts
│   ├── get_relationships.ts
│   ├── get_communities.ts
│   ├── search_relationships.ts
│   ├── analyze_entity.ts
│   ├── index.ts
│   └── types.ts
│
├── meta/
│   ├── memory_health.ts
│   ├── get_expertise.ts
│   ├── get_cognitive_load.ts
│   ├── get_quality_metrics.ts
│   ├── get_attention_metrics.ts
│   ├── index.ts
│   └── types.ts
│
├── consolidation/
│   ├── get_metrics.ts
│   ├── analyze_patterns.ts
│   ├── get_consolidation_status.ts
│   ├── get_consolidation_history.ts
│   ├── index.ts
│   └── types.ts
│
├── rag/
│   ├── retrieve.ts
│   ├── search.ts
│   ├── hybrid_search.ts
│   ├── semantic_search.ts
│   ├── bm25_search.ts
│   ├── index.ts
│   └── types.ts
│
└── search_tools.ts            # Tool discovery utility
```

### Implementation Pattern

Each operation file follows this pattern:

**File: src/servers/episodic/recall.ts**
```typescript
import type { Memory, RecallOptions } from './types';

/**
 * Recall memories matching a query
 *
 * @param query - Search query string
 * @param limit - Maximum results to return (default: 10)
 * @param minConfidence - Minimum confidence threshold (0-1)
 * @returns Matching memories with scores
 *
 * @example
 * const memories = await recall('important meetings', 5);
 * console.log(memories);
 */
export async function recall(
  query: string,
  limit?: number,
  minConfidence?: number
): Promise<Memory[]> {
  return await callMCPTool('episodic/recall', {
    query,
    limit: limit ?? 10,
    minConfidence: minConfidence ?? 0.5,
  });
}

/**
 * Get recent memories (simplified version for quick access)
 */
export async function getRecent(limit: number = 5): Promise<Memory[]> {
  return await callMCPTool('episodic/recall', {
    query: '*',  // Special: get recent
    limit,
    sort: 'timestamp',
    order: 'desc',
  });
}
```

**File: src/servers/episodic/types.ts**
```typescript
/**
 * Memory record from episodic layer
 */
export interface Memory {
  id: string;
  timestamp: number;
  content: string;
  context: Record<string, unknown>;
  confidence: number;
  source: string;
  tags: string[];
  relatedMemories: string[];
  expiresAt?: number;
}

/**
 * Options for recall operation
 */
export interface RecallOptions {
  query: string;
  limit?: number;
  minConfidence?: number;
  timeRange?: {
    start: number;
    end: number;
  };
  tags?: string[];
}

/**
 * Result from recall operation
 */
export interface RecallResult {
  memories: Memory[];
  totalMatches: number;
  executionTimeMs: number;
  confidence: number;
}
```

**File: src/servers/episodic/index.ts**
```typescript
/**
 * Episodic Memory Operations
 *
 * Functions for storing, retrieving, and managing episodic memories
 * (events and experiences with timestamps).
 */

export { recall, getRecent } from './recall';
export { remember } from './remember';
export { forget } from './forget';
export { bulkRemember } from './bulk_remember';
export { queryTemporal } from './query_temporal';
export { listEvents } from './list_events';

export type { Memory, RecallOptions, RecallResult } from './types';

/**
 * Episodic memory operations metadata
 */
export const operations = {
  recall: {
    name: 'recall',
    description: 'Recall memories matching a query',
    parameters: {
      query: { type: 'string', required: true },
      limit: { type: 'number', required: false, default: 10 },
      minConfidence: { type: 'number', required: false, default: 0.5 },
    },
  },
  remember: {
    name: 'remember',
    description: 'Store a new memory',
    parameters: {
      content: { type: 'string', required: true },
      context: { type: 'object', required: false },
      tags: { type: 'array', required: false },
    },
  },
  // ... more operations
};
```

### Tool Adapter Implementation

**File: src/adapters/episodic_adapter.ts**
```typescript
import { ToolAdapter, ToolOperation, ToolContext } from '../interfaces/adapter';
import * as episodic from '../servers/episodic';

export class EpisodicAdapter implements ToolAdapter {
  name = 'episodic';
  category = 'memory';
  version = '1.0.0';
  operations: ToolOperation[] = [];

  constructor() {
    this.initializeOperations();
  }

  private initializeOperations(): void {
    this.operations = [
      {
        name: 'recall',
        id: 'episodic/recall',
        category: 'memory',
        description: 'Recall memories matching a query',
        parameters: [
          {
            name: 'query',
            type: { name: 'string' },
            required: true,
            description: 'Search query string',
          },
          {
            name: 'limit',
            type: { name: 'number' },
            required: false,
            description: 'Maximum results to return',
            default: 10,
          },
        ],
        returns: {
          name: 'array',
          elementType: { name: 'object' },
          description: 'Array of matching memories',
        },
        example: `const memories = await recall('important', 5);`,
        exampleResult: [
          {
            id: 'mem-123',
            timestamp: 1699400000,
            content: 'Important meeting happened',
            confidence: 0.95,
          },
        ],
      },
      // ... more operations
    ];
  }

  async execute(
    operationName: string,
    parameters: Record<string, unknown>,
    context: ToolContext
  ): Promise<unknown> {
    switch (operationName) {
      case 'recall':
        return episodic.recall(
          parameters.query as string,
          parameters.limit as number | undefined
        );
      case 'remember':
        return episodic.remember(
          parameters.content as string,
          parameters.context as Record<string, unknown> | undefined
        );
      // ... more cases
      default:
        throw new Error(`Unknown operation: ${operationName}`);
    }
  }

  getOperation(operationName: string): ToolOperation | undefined {
    return this.operations.find((op) => op.name === operationName);
  }

  validateParameters(
    operationName: string,
    parameters: Record<string, unknown>
  ): ValidationResult {
    const operation = this.getOperation(operationName);
    if (!operation) {
      return { valid: false, errors: ['Unknown operation'] };
    }

    const errors: string[] = [];

    for (const param of operation.parameters) {
      if (param.required && !(param.name in parameters)) {
        errors.push(`Missing required parameter: ${param.name}`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  hasOperation(operationName: string): boolean {
    return this.operations.some((op) => op.name === operationName);
  }

  getStatus(): AdapterStatus {
    return {
      name: this.name,
      healthy: true,
      status: 'ready',
      uptimeMs: Date.now(),
      successCount: 0,
      errorCount: 0,
      avgLatencyMs: 0,
      lastCheckTime: new Date().toISOString(),
    };
  }
}
```

### Implementation for All 8 Layers

| Layer | Files | Operations | Status |
|-------|-------|-----------|--------|
| Episodic | 8 | recall, remember, forget, bulk_remember, query_temporal, list_events | Design above |
| Semantic | 8 | search, store, delete, update, list_memories, get_memory | Similar pattern |
| Procedural | 8 | extract, execute, list, get_effectiveness, get_procedure | Similar pattern |
| Prospective | 10 | create_task, list_tasks, complete_task, update_task, create_goal, list_goals | Similar pattern |
| Graph | 8 | search_entities, get_entity, get_relationships, get_communities | Similar pattern |
| Meta | 8 | memory_health, get_expertise, get_cognitive_load, get_quality_metrics | Similar pattern |
| Consolidation | 8 | get_metrics, analyze_patterns, get_status, get_history | Similar pattern |
| RAG | 8 | retrieve, search, hybrid_search, semantic_search, bm25_search | Similar pattern |
| **TOTAL** | **66+** | **70+ operations** | **All layers** |

---

## Task 3.2: Filesystem-Based Tool Discovery

### Objective
Enable agents to discover tools via filesystem exploration, matching blog post pattern.

### Implementation

**File: src/servers/search_tools.ts**
```typescript
/**
 * Tool Discovery Utility
 *
 * Enables agents to search for available tools with configurable detail levels.
 * Supports both filesystem-based and API-based discovery.
 */

export type DetailLevel = 'name' | 'name+description' | 'full-schema';

export interface SearchToolsOptions {
  detailLevel?: DetailLevel;  // Default: 'name+description'
  category?: string;           // e.g., 'episodic', 'semantic'
  pattern?: string;            // Search pattern (e.g., 'recall*')
}

/**
 * Search available tools with configurable detail level
 *
 * @example
 * // Get names only
 * const tools = await search_tools({ detailLevel: 'name' });
 *
 * // Get names + descriptions
 * const tools = await search_tools({ detailLevel: 'name+description' });
 *
 * // Get full schemas
 * const tools = await search_tools({ detailLevel: 'full-schema' });
 *
 * // Search specific category
 * const episodicTools = await search_tools({
 *   category: 'episodic',
 *   detailLevel: 'name+description'
 * });
 */
export async function search_tools(
  options?: SearchToolsOptions
): Promise<ToolInfo[]> {
  const detailLevel = options?.detailLevel ?? 'name+description';
  const category = options?.category;
  const pattern = options?.pattern;

  // Implementation: dynamically load tools and return at specified detail level
  // (See implementation below)
}

export interface ToolInfo {
  id: string;                    // e.g., 'episodic/recall'
  name: string;                  // e.g., 'recall'
  category: string;              // e.g., 'episodic'
  description?: string;          // Only if detail >= 'name+description'
  signature?: string;            // Only if detail >= 'full-schema'
  parameters?: Parameter[];      // Only if detail >= 'full-schema'
  returns?: string;              // Only if detail >= 'full-schema'
  example?: string;              // Only if detail >= 'full-schema'
}

export interface Parameter {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

/**
 * Internal: Load tool definitions dynamically
 */
async function loadToolDefinitions(detailLevel: DetailLevel) {
  const tools: ToolInfo[] = [];

  // Load each layer's operations
  const layers = [
    'episodic',
    'semantic',
    'procedural',
    'prospective',
    'graph',
    'meta',
    'consolidation',
    'rag',
  ];

  for (const layer of layers) {
    const module = await import(`./${layer}/index.ts`);

    if (module.operations) {
      for (const [opName, opMeta] of Object.entries(module.operations)) {
        const tool: ToolInfo = {
          id: `${layer}/${opName}`,
          name: opName,
          category: layer,
        };

        if (detailLevel !== 'name') {
          tool.description = (opMeta as any).description;
        }

        if (detailLevel === 'full-schema') {
          tool.parameters = (opMeta as any).parameters;
          tool.returns = (opMeta as any).returns;
          tool.example = (opMeta as any).example;
        }

        tools.push(tool);
      }
    }
  }

  return tools;
}
```

### Filesystem Access in Sandbox

Update Deno executor to allow read-only filesystem access:

**File: src/runtime/deno_executor.ts (modifications)**
```typescript
// Update permissions to allow reading tool files
const denoPermissions = {
  read: [
    '/tmp/athena/sandbox',        // Sandbox directory
    '/tmp/athena/servers',        // Tool files (NEW)
    '/tmp/athena/servers/*',      // Nested tool files
  ],
  write: ['/tmp/athena/sandbox'],
  env: ['ATHENA_SESSION_ID'],
  hrtime: true,
  // All dangerous permissions remain disabled
};
```

This enables agents to:

```typescript
// agents can now do:
const fs = require('fs');  // (blocked in sandbox)

// But they CAN do this via provided utilities:
const servers = readdir('./servers/');  // ['episodic', 'semantic', ...]
const recall = readFile('./servers/episodic/recall.ts', 'utf-8');
// TypeScript signature visible in file

// Or use search_tools utility:
const tools = await search_tools({ category: 'episodic' });
```

---

## Task 3.3: MCP Server Integration

### Objective
Update MCP server to route tool calls through code execution paradigm.

### Architecture Change

**Before (Traditional MCP)**:
```
Agent → MCP Tool Call → MCP Server → Athena Core
```

**After (Code Execution)**:
```
Agent → Code Execution → callMCPTool() → Athena Core
                ↓ (locally)
            Tool Adapters → MCP Server
```

### Implementation

**File: src/mcp/code_execution_handler.ts** (New)
```typescript
import { CodeExecutor } from '../execution/code_executor';
import { SessionManager } from '../session/session_manager';
import { DenoExecutor } from '../runtime/deno_executor';
import type { CodeExecutionRequest, CodeExecutionResult } from '../interfaces/execution';

export class CodeExecutionHandler {
  private codeExecutor: CodeExecutor;
  private sessionManager: SessionManager;
  private denoExecutor: DenoExecutor;
  private toolAdapters: Map<string, ToolAdapter> = new Map();

  constructor(denoExecutor: DenoExecutor, sessionManager: SessionManager) {
    this.denoExecutor = denoExecutor;
    this.sessionManager = sessionManager;
    this.codeExecutor = new CodeExecutor(denoExecutor);

    // Register all tool adapters
    this.registerAdapters();
  }

  private registerAdapters(): void {
    // Register all 8 layer adapters
    const adapters = [
      new EpisodicAdapter(),
      new SemanticAdapter(),
      new ProceduralAdapter(),
      new ProspectiveAdapter(),
      new GraphAdapter(),
      new MetaAdapter(),
      new ConsolidationAdapter(),
      new RAGAdapter(),
    ];

    for (const adapter of adapters) {
      this.toolAdapters.set(adapter.name, adapter);
    }
  }

  /**
   * Execute agent code (main entry point)
   */
  async executeCode(
    request: CodeExecutionRequest,
    sessionId?: string
  ): Promise<CodeExecutionResult> {
    // Create or get session
    if (!sessionId) {
      sessionId = this.sessionManager.createSession();
    }

    const session = this.sessionManager.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    // Create tool context
    const toolContext = {
      sessionId,
      userId: session.userId,
      availableTools: this.getAvailableTools(),
      sessionState: this.sessionManager.getVariables(sessionId),
    };

    // Execute code
    const result = await this.codeExecutor.execute(request, toolContext);

    // Record in session history
    if (result.success) {
      this.sessionManager.recordExecution(
        sessionId,
        request.code,
        result.output,
        result.metrics
      );
    }

    return result;
  }

  /**
   * Get available tools (for tool context)
   */
  private getAvailableTools() {
    const tools: ToolOperation[] = [];

    for (const adapter of this.toolAdapters.values()) {
      tools.push(...adapter.operations);
    }

    return tools;
  }

  /**
   * Tool call from within sandbox (called by agent code)
   */
  async callMCPTool(
    operationId: string,
    parameters: Record<string, unknown>,
    sessionId: string
  ): Promise<unknown> {
    const [category, operationName] = operationId.split('/');
    const adapter = this.toolAdapters.get(category);

    if (!adapter) {
      throw new Error(`Unknown tool category: ${category}`);
    }

    const toolContext: ToolContext = {
      sessionId,
      availableTools: this.getAvailableTools(),
      sessionState: this.sessionManager.getVariables(sessionId),
    };

    return await adapter.execute(operationName, parameters, toolContext);
  }
}
```

### MCP Server Modifications

**File: src/mcp/handlers.ts** (modifications)
```typescript
// Add code execution handler
private codeExecutionHandler: CodeExecutionHandler;

// Update server initialization
async initialize() {
  // Initialize execution infrastructure
  await this.denoExecutor.initialize();

  // Create handler
  this.codeExecutionHandler = new CodeExecutionHandler(
    this.denoExecutor,
    this.sessionManager
  );

  // Register MCP tools
  this.registerCodeExecutionTools();
}

// Register MCP tools for code execution
private registerCodeExecutionTools() {
  // Tool 1: Execute code
  this.server.tool('execute_code', 'Execute TypeScript code in sandbox', {
    code: { type: 'string', description: 'TypeScript code to execute' },
    session_id: { type: 'string', description: 'Optional: Session ID' },
  }, async ({ code, session_id }) => {
    const result = await this.codeExecutionHandler.executeCode(
      { code, timeout: 5000 },
      session_id
    );
    return JSON.stringify(result);
  });

  // Tool 2: Search tools
  this.server.tool('search_tools', 'Search available tools', {
    detail_level: {
      type: 'string',
      description: 'Detail level: name, name+description, or full-schema',
    },
    category: {
      type: 'string',
      description: 'Optional: Filter by category (episodic, semantic, etc)',
    },
  }, async ({ detail_level, category }) => {
    const tools = await this.searchTools({
      detailLevel: detail_level as DetailLevel,
      category,
    });
    return JSON.stringify(tools);
  });

  // Tool 3: Session management
  this.server.tool('create_session', 'Create a new execution session', {
    user_id: { type: 'string', description: 'Optional: User ID' },
  }, async ({ user_id }) => {
    const sessionId = this.sessionManager.createSession(user_id);
    return JSON.stringify({ sessionId });
  });

  this.server.tool('get_session_state', 'Get session state and variables', {
    session_id: { type: 'string', description: 'Session ID' },
  }, async ({ session_id }) => {
    const vars = this.sessionManager.getVariables(session_id);
    return JSON.stringify(vars);
  });

  this.server.tool('set_session_variable', 'Set a session variable', {
    session_id: { type: 'string' },
    name: { type: 'string' },
    value: { type: 'any' },
  }, async ({ session_id, name, value }) => {
    this.sessionManager.setVariable(session_id, name, value);
    return JSON.stringify({ ok: true });
  });
}

// Helper: search tools
private async searchTools(
  options?: SearchToolsOptions
): Promise<ToolInfo[]> {
  // Use the search_tools utility
  return await search_tools(options);
}
```

---

## Task 3.4: Integration Tests

### Test Coverage

**Test Suite Structure**:
```
tests/integration/
├── tool_discovery.test.ts        # Filesystem and API discovery
├── tool_adapters.test.ts         # All 8 layers
├── tool_execution.test.ts        # End-to-end execution
├── error_handling.test.ts        # Error scenarios
├── performance.test.ts           # Benchmarks
├── session_management.test.ts    # State persistence
├── large_results.test.ts         # Data filtering
└── composition_patterns.test.ts  # Complex workflows
```

**Example Test: Tool Discovery**
```typescript
describe('Tool Discovery', () => {
  describe('search_tools API', () => {
    test('should list all tools with name detail level', async () => {
      const tools = await search_tools({ detailLevel: 'name' });
      expect(tools.length).toBeGreaterThan(50);
      expect(tools.some((t) => t.id === 'episodic/recall')).toBe(true);
      expect(tools[0].description).toBeUndefined();
    });

    test('should include descriptions at name+description level', async () => {
      const tools = await search_tools({
        detailLevel: 'name+description',
      });
      expect(tools[0].description).toBeDefined();
      expect(tools[0].signature).toBeUndefined();
    });

    test('should include full schema at full-schema level', async () => {
      const tools = await search_tools({ detailLevel: 'full-schema' });
      expect(tools[0].parameters).toBeDefined();
      expect(tools[0].returns).toBeDefined();
    });

    test('should filter by category', async () => {
      const tools = await search_tools({ category: 'episodic' });
      expect(tools.every((t) => t.category === 'episodic')).toBe(true);
    });
  });

  describe('Filesystem discovery', () => {
    test('agents can readdir ./servers/', async () => {
      const code = `
        const Deno = require('deno');
        const servers = Deno.readDirSync('./servers/');
        return servers.map(s => s.name);
      `;

      const result = await codeExecutor.execute({ code });
      expect(result.success).toBe(true);
      expect(result.output).toContain('episodic');
      expect(result.output).toContain('semantic');
    });

    test('agents can readFile ./servers/episodic/index.ts', async () => {
      const code = `
        const Deno = require('deno');
        const content = Deno.readFileSync(
          './servers/episodic/index.ts',
          'utf-8'
        );
        return content.includes('recall');
      `;

      const result = await codeExecutor.execute({ code });
      expect(result.success).toBe(true);
      expect(result.output).toBe(true);
    });
  });
});
```

**Example Test: Tool Execution**
```typescript
describe('Tool Execution', () => {
  test('should execute episodic/recall and return memories', async () => {
    const code = `
      const memories = await recall('important', 5);
      return {
        count: memories.length,
        hasTimestamps: memories.every(m => m.timestamp)
      };
    `;

    const result = await codeExecutor.execute({ code });
    expect(result.success).toBe(true);
    expect(result.output.hasTimestamps).toBe(true);
  });

  test('should enable data filtering in code', async () => {
    const code = `
      const documents = await getDocuments({ limit: 1000 });
      const filtered = documents.filter(d => d.relevance > 0.8);
      return filtered.length;  // Only high-relevance docs returned
    `;

    const result = await codeExecutor.execute({ code });
    expect(result.success).toBe(true);
    expect(result.output).toBeLessThan(1000);  // Filtered down
  });

  test('should support parallel tool calls', async () => {
    const code = `
      const [memories, tasks, entities] = await Promise.all([
        recall('work'),
        listTasks(),
        searchEntities('project')
      ]);
      return { memories: memories.length, tasks: tasks.length };
    `;

    const start = Date.now();
    const result = await codeExecutor.execute({ code });
    const duration = Date.now() - start;

    expect(result.success).toBe(true);
    expect(duration).toBeLessThan(300);  // All parallel < 300ms
  });
});
```

### Test Targets
- ✅ 50+ integration tests total
- ✅ All 8 layers covered
- ✅ Error scenarios (10+ tests)
- ✅ Performance benchmarks (10+ tests)
- ✅ Complex workflows (10+ tests)
- ✅ Data filtering scenarios (5+ tests)

---

## Task 3.5: Documentation

### Documentation Deliverables

1. **PHASE3_EXECUTION_GUIDE.md** (1500+ lines)
   - Tool adapter architecture
   - Filesystem structure explanation
   - Discovery patterns (API vs. filesystem)
   - Implementation guide
   - API reference

2. **TOOLS_REFERENCE.md** (2000+ lines)
   - All 70+ operations documented
   - Parameters and return types
   - Usage examples
   - Error handling

3. **AGENT_GUIDE.md** (1000+ lines)
   - How to write agent code
   - Filesystem discovery examples
   - search_tools usage
   - Common patterns
   - Error handling

4. **PERFORMANCE_GUIDE.md** (500+ lines)
   - Optimization strategies
   - Benchmarks for each tool
   - Tips for efficient code
   - Caching strategies

---

## Timeline & Milestones

### Week 5 (Nov 21-27)

**Days 1-2**: Setup and planning
- Create directory structure
- Setup file templates
- Plan adapter implementation

**Days 3-5**: Implement adapters (Layers 1-4)
- Episodic adapter
- Semantic adapter
- Procedural adapter
- Prospective adapter

**Days 5-7**: Implement adapters (Layers 5-8) + Discovery
- Graph adapter
- Meta adapter
- Consolidation adapter
- RAG adapter
- search_tools utility
- Filesystem access setup

### Week 6 (Nov 28 - Dec 4)

**Days 1-2**: MCP server integration
- Update handlers
- Register new tools
- Session management

**Days 3-5**: Testing
- Unit tests for adapters
- Integration tests
- Performance benchmarks

**Days 6-7**: Documentation & Polish
- Complete documentation
- Code review
- Final testing

---

## Success Criteria

- [ ] All 8 layers have adapters
- [ ] ./servers/ directory structure in place
- [ ] Agents can discover tools via filesystem
- [ ] search_tools utility working
- [ ] 50+ integration tests passing
- [ ] Performance <300ms per tool call
- [ ] All operations documented
- [ ] Example workflows provided

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Filesystem permission issues | MEDIUM | Test carefully, document limits |
| Tool adapter complexity | MEDIUM | Use template pattern consistently |
| Integration test coverage | MEDIUM | Start with critical paths |
| Performance degradation | LOW | Monitor latency in tests |

---

## Success Metrics

By end of Phase 3:
- ✅ 100% blog post alignment (filesystem discovery)
- ✅ All 8 memory layers exposed as tools
- ✅ 70+ operations available to agents
- ✅ 50+ integration tests passing
- ✅ Full documentation
- ✅ Performance targets met (<300ms/call)
- ✅ Ready for Phase 4 (Testing & Optimization)

---

**Next Phase**: Phase 4 - Testing & Optimization (Weeks 7-10)
