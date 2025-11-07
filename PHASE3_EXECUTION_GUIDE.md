# Phase 3 Execution Guide: Tool Adapters & Code Execution

**Date**: November 8, 2025
**Version**: 1.0
**Status**: Complete

This guide covers how to use the Athena code execution paradigm to write agent code that leverages all 8 memory layers.

---

## Quick Start

### 1. Agent Code Execution Pattern

```typescript
// Agents write TypeScript code that gets executed in a secure sandbox
const code = `
  // Recall recent memories
  const recentMemories = await recall('project meeting', 10);
  console.log('Found memories:', recentMemories.length);

  // Store a new memory
  const memoryId = await remember('Budget approved for Q2', ['decision', 'budget']);
  console.log('Stored:', memoryId);

  // Discover available tools
  const tools = await search_tools({ layer: 'episodic', detailLevel: 'name' });
  console.log('Episodic operations:', tools.length);

  return { success: true, memories: recentMemories };
`;

// Execute in context
const result = await codeExecutionHandler.executeWithTools(code, {
  sessionId: 'agent_123',
  userId: 'user_456'
});
```

### 2. Tool Discovery Pattern

```typescript
// Agents can discover tools at runtime
const tools = await search_tools({
  detailLevel: 'name+description',
  layer: 'episodic'
});

for (const tool of tools) {
  console.log(`${tool.name}: ${tool.description}`);
}

// Output:
// recall: Recall memories matching a query
// remember: Store a new memory
// forget: Delete memories
// ...
```

### 3. Progressive Disclosure Pattern

```typescript
// Start with minimal context (1 KB)
const namesList = await search_tools({ detailLevel: 'name' });

// Expand as needed (5 KB)
const withDescriptions = await search_tools({ detailLevel: 'name+description' });

// Get full schemas when needed (50 KB)
const fullDetails = await search_tools({ detailLevel: 'full-schema' });
```

---

## 8 Memory Layers Overview

### Layer 1: Episodic Memory

**Purpose**: Store events and experiences with timestamps and context.

```typescript
// Store an event
const id = await remember('User asked about deployment process', {
  context: 'support conversation',
  timestamp: Date.now()
}, ['support', 'deployment']);

// Recall events
const events = await recall('deployment', 5);

// Query by time
const weekEvents = await queryLastDays(7);

// List with pagination
const page1 = await listEvents(20, 0);

// Delete old memories
await forget(oldMemoryIds);
```

**Key Operations**: recall, remember, forget, bulkRemember, queryTemporal, listEvents (6 core operations)

**Use Cases**:
- Track conversation history
- Store decisions and their context
- Remember agent interactions
- Temporal reasoning

---

### Layer 2: Semantic Memory

**Purpose**: Store general knowledge, facts, and principles.

```typescript
// Store knowledge
const id = await store('PostgreSQL VACUUM prevents table bloat', ['database', 'maintenance']);

// Search knowledge
const results = await semanticSearch('database optimization');

// Keyword search
const exact = await keywordSearch('VACUUM');

// Hybrid search
const hybrid = await hybridSearch('performance tuning', 10, 0.6);

// Analyze knowledge
const topics = await analyzeTopics();
const stats = await getStats();

// Update knowledge
await update(id, 'PostgreSQL VACUUM must run regularly...', ['database']);

// Delete knowledge
await delete_memory(id);
```

**Key Operations**: search (9 variants), store, update, delete, list, analyzeTopics, getStats (14+ operations)

**Use Cases**:
- Store learned facts and principles
- Semantic knowledge base
- Domain expertise tracking
- Learning from consolidation

---

### Layer 3: Procedural Memory

**Purpose**: Store reusable procedures and workflows.

```typescript
// Extract procedures from past experiences
const newProcedures = await extract(3, 0.7); // min 3 occurrences, 70% success

// List all procedures
const procedures = await list(50);

// Execute a procedure
const result = await execute('proc_123', {
  inputParam: 'value'
});

// Check effectiveness
const metrics = await getEffectiveness('proc_123');
console.log('Success rate:', metrics.successRate);

// Search procedures
const relevant = await search('database backup', 10);
```

**Key Operations**: extract, list, get, execute, getEffectiveness, search (6 operations)

**Use Cases**:
- Automate repeated workflows
- Improve execution through learning
- Share procedures across sessions
- Measure procedure quality

---

### Layer 4: Prospective Memory

**Purpose**: Manage tasks, goals, and event-based triggers.

```typescript
// Create a task
const taskId = await createTask('Implement feature X', 'Review requirements first', 8);

// List tasks
const pending = await listTasks('pending');
const completed = await listTasks('completed');

// Update task status
await updateTask(taskId, { status: 'in_progress' });

// Complete task
await completeTask(taskId);

// Create a goal
const goalId = await createGoal('Launch product', 'By end of Q4');

// Update goal progress
await updateGoal(goalId, 75); // 75% complete

// Register event triggers
const triggerId = await registerTrigger('task_completed', 'notify_team', {
  taskType: 'critical'
});

// Get pending tasks
const overdue = await getPendingTasks();
```

**Key Operations**: createTask, listTasks, updateTask, completeTask, createGoal, updateGoal, registerTrigger, getPendingTasks (11 operations)

**Use Cases**:
- Track work items and deadlines
- Goal hierarchy and progress
- Event-driven automation
- Deadline management

---

### Layer 5: Knowledge Graph

**Purpose**: Store entities, relationships, and community structures.

```typescript
// Search for entities
const entities = await searchEntities('database optimization');

// Get specific entity
const entity = await getEntity('entity_123');

// Get relationships
const relations = await getRelationships('entity_123', 'relates_to');

// Find communities
const communities = await getCommunities(1); // level 1

// Analyze connections
const analysis = await analyzeEntity('entity_123');
// Returns: entity, relatedEntities, relationshipCount, communityId, centrality

// Find path between entities
const path = await findPath('source_123', 'target_456');

// Create entity and relationship
const newEntity = await createEntity('PostgreSQL', 'Database', 'Open source relational DB');
const newRelation = await createRelationship(newEntity, 'existing_123', 'similar_to');
```

**Key Operations**: searchEntities, getEntity, getRelationships, getCommunities, analyzeEntity, findPath, createEntity, createRelationship (8 operations)

**Use Cases**:
- Semantic relationships between concepts
- Finding related knowledge
- Community detection
- Path reasoning

---

### Layer 6: Meta-Memory

**Purpose**: Quality metrics, expertise, and cognitive load.

```typescript
// Memory health check
const health = await memoryHealth();
console.log('Average confidence:', health.averageConfidence);
console.log('Issues:', health.issues);

// Expertise tracking
const expertise = await getExpertise(); // All domains
const dbExpertise = await getExpertise('database');

// Cognitive load
const load = await getCognitiveLoad();
console.log('Working memory:', load.workingMemory); // 0-1
console.log('Stress level:', load.stress);

// Quality metrics
const quality = await getQualityMetrics();

// Attention metrics
const attention = await getAttentionMetrics();

// Memory statistics
const stats = await getMemoryStats();

// Find knowledge gaps
const gaps = await findGaps();

// Get recommendations
const recommendations = await getRecommendations();

// Progress tracking
const progress = await getProgressMetrics();
```

**Key Operations**: memoryHealth, getExpertise, getCognitiveLoad, getQualityMetrics, getAttentionMetrics, getMemoryStats, findGaps, getRecommendations, getProgressMetrics (9 operations)

**Use Cases**:
- Monitor memory system health
- Track learning progress
- Identify knowledge gaps
- Assess cognitive load
- Domain expertise tracking

---

### Layer 7: Consolidation

**Purpose**: Sleep-like pattern extraction and learning.

```typescript
// Run consolidation cycle
const metrics = await consolidate('balanced'); // strategy: balanced|speed|quality|minimal
console.log('Processed:', metrics.processedEvents);
console.log('Patterns:', metrics.extractedPatterns);

// Analyze patterns
const patterns = await analyzePatterns(20, 0.7); // limit, minConfidence

// Check status
const status = await getStatus();
console.log('Progress:', status.progress); // 0-1

// Get history
const history = await getHistory(10);

// Configure strategy
await configureStrategy('quality', {
  llmValidationThreshold: 0.7,
  clusteringDistance: 0.85
});

// Get recommendations
const recs = await getRecommendations();
```

**Key Operations**: consolidate, getMetrics, analyzePatterns, getStatus, getHistory, configureStrategy, getRecommendations (7 operations)

**Use Cases**:
- Extract patterns from experiences
- Convert episodic → semantic knowledge
- Improve memory efficiency
- Sleep-like consolidation cycles

---

### Layer 8: RAG (Retrieval-Augmented Generation)

**Purpose**: Advanced semantic search and context retrieval.

```typescript
// Flexible retrieval
const context = await retrieve('How do we deploy services?', 5, 'hybrid');

// Semantic search
const semantic = await semanticSearch('deployment process');

// Keyword search
const keywords = await bm25Search('docker kubernetes');

// Hybrid search (best of both)
const hybrid = await hybridSearch('CI/CD pipeline', 10, {
  episodic: 0.2,
  semantic: 0.5,
  graph: 0.3
});

// Reflective search (iterative refinement)
const refined = await reflectiveSearch('testing strategy', 2);

// Query expansion
const expanded = await queryExpansion('performance optimization');
// Returns: ['performance tuning', 'optimization', 'efficiency', ...]

// Get synthesis prompt
const synthPrompt = await getSynthesisPrompt('deployment', context);

// Retrieval statistics
const stats = await getStats();
```

**Key Operations**: retrieve, search, hybridSearch, semanticSearch, bm25Search, reflectiveSearch, queryExpansion, getSynthesisPrompt, retrieveWithReranking, getStats (10 operations)

**Use Cases**:
- Context retrieval for agent reasoning
- Multi-strategy search
- Query refinement
- Hybrid search across layers

---

## Tool Discovery: search_tools()

### Basic Discovery

```typescript
// Get all tools
const all = await search_tools();

// Get tools by layer
const episodic = await search_tools({ layer: 'episodic' });

// Get by category
const readOps = await search_tools({ category: 'read' });
const writeOps = await search_tools({ category: 'write' });

// Query by name
const recall = await search_tools({ query: 'recall' });

// Detail levels
const namesOnly = await search_tools({ detailLevel: 'name' });
const withDesc = await search_tools({ detailLevel: 'name+description' });
const fullSchema = await search_tools({ detailLevel: 'full-schema' });
```

### Advanced Discovery

```typescript
// Find tools for a task
const toolsFor = await findToolsFor('store conversation history');

// Get tool complexity
const complexity = await getToolComplexity('consolidate');
// Returns: { complexity: 'complex', estimatedTime: '300-1000ms', requiredContext: [...] }

// Get all categories
const categories = await getCategories();
// Returns: [{ layer, displayName, toolCount, readOps, writeOps }, ...]

// Get quick reference
const ref = await getQuickReference();
// Returns: markdown reference with tool counts
```

---

## Session Management

### Creating and Managing Sessions

```typescript
// Create context for agent session
const context = codeExecutionHandler.createToolContext('agent_session_123', 'user_456');

// Context includes:
// - sessionId: unique session identifier
// - userId: optional user identifier
// - allowedTools: set of accessible operations
// - callMCPTool: function to invoke operations
// - search_tools: function to discover tools

// Check if tool is accessible
const hasAccess = codeExecutionHandler.canAccess('episodic/recall', 'session_123');

// Close session when done
codeExecutionHandler.closeSession('session_123');
```

---

## Complete Workflow Examples

### Example 1: Learn from a Support Conversation

```typescript
const code = `
  // Step 1: Store conversation events
  const eventIds = await bulkRemember([
    { content: 'Customer asked about database scaling' },
    { content: 'Provided solution using read replicas' },
    { content: 'Customer satisfied with approach' }
  ], { tags: ['support', 'database'] });

  // Step 2: Extract knowledge to semantic memory
  const knowledge = await store(
    'For database scaling issues, read replicas provide good solution',
    ['database', 'scaling', 'solution']
  );

  // Step 3: Check if procedure can be extracted
  const procedures = await extract(2, 0.6);

  // Step 4: Check memory health
  const health = await memoryHealth();

  return {
    eventsStored: eventIds.length,
    knowledgeId: knowledge,
    procedures: procedures.length,
    systemHealth: health.averageConfidence
  };
`;

const result = await codeExecutionHandler.executeWithTools(code, {
  sessionId: 'support_session',
  userId: 'support_agent'
});
```

### Example 2: Complex Query with Multiple Strategies

```typescript
const code = `
  // Discover available search strategies
  const searchOps = await search_tools({
    layer: 'rag',
    detailLevel: 'name'
  });

  const query = 'How do we handle payment processing';

  // Try semantic search first
  const semantic = await semanticSearch(query, 5);

  // Try keyword search
  const keyword = await bm25Search('payment processing', 5);

  // Use hybrid for best results
  const hybrid = await hybridSearch(query, 10, {
    semantic: 0.6,
    episodic: 0.3,
    graph: 0.1
  });

  // Check which found most relevant
  const best = hybrid.length > 0 ? hybrid : semantic;

  return {
    queryStrategies: searchOps.length,
    semanticResults: semantic.length,
    keywordResults: keyword.length,
    hybridResults: hybrid.length,
    bestResults: best
  };
`;
```

### Example 3: Task Management with Consolidation

```typescript
const code = `
  // Create task
  const taskId = await createTask(
    'Implement caching layer',
    'Improve API performance',
    9
  );

  // Remember context
  const contextId = await remember(
    'Implementing Redis cache for API endpoints',
    { taskId, estimatedHours: 8 }
  );

  // Update as work progresses
  await updateTask(taskId, { status: 'in_progress' });

  // Record insights during work
  const insightId = await rememberInsight(
    'Redis pub/sub better than polling',
    'caching',
    0.95
  );

  // Complete task
  await completeTask(taskId);

  // Trigger consolidation
  const consolidation = await consolidate('balanced');

  // Check if procedures were extracted
  const procs = await extract(2, 0.7);

  return {
    task: taskId,
    insights: insightId,
    consolidation,
    extractedProcedures: procs.length
  };
`;
```

---

## Common Patterns

### Pattern 1: Store and Retrieve

```typescript
// Store
const id = await remember(content, context, tags);

// Retrieve
const memories = await recall(query, limit);

// Delete
await forget([id]);
```

### Pattern 2: Search and Analyze

```typescript
// Semantic search
const results = await semanticSearch(query);

// Get entity info
const entity = await getEntity(results[0].id);

// Analyze connections
const analysis = await analyzeEntity(entity.id);
```

### Pattern 3: Batch Operations

```typescript
// Multiple stores
const ids = await bulkRemember(memories);

// Session-based
const sessionIds = await bulkRememberSession('session_123', messages);

// With deduplication
const dedupIds = await bulkRememberDedup(memories, 0.9);
```

### Pattern 4: Monitor and Improve

```typescript
// Check health
const health = await memoryHealth();

// Find issues
const gaps = await findGaps();

// Get recommendations
const recs = await getRecommendations();

// Take action based on recommendations
if (health.averageConfidence < 0.7) {
  await purgeLowConfidence(0.5);
}
```

---

## Best Practices

### 1. Use Progressive Disclosure

Start with minimal tool discovery and expand only when needed:

```typescript
// Minimal context discovery
const names = await search_tools({ detailLevel: 'name' });

// Later, if needed
const schemas = await search_tools({ detailLevel: 'full-schema' });
```

### 2. Leverage Specialized Functions

Use typed, specialized functions instead of generic operations:

```typescript
// Good: Use specialized functions
const decision = await rememberDecision('Chose approach B', 'Better performance');
const fact = await storeFact('PostgreSQL is ACID compliant', 'Wikipedia', 0.99);

// Less ideal: Using generic functions
await remember('Decision: Chose approach B'); // Loses structure
await store('PostgreSQL is ACID compliant'); // Loses metadata
```

### 3. Chain Operations Efficiently

```typescript
// Efficient: Multiple operations in single code execution
const code = `
  const recent = await getRecent(10);
  const keywords = await semanticSearch('performance');
  const related = await getRelated(recent[0].id);
  return { recent, keywords, related };
`;

// Less efficient: Multiple code executions
await recall(...);  // First execution
await search(...);  // Second execution
await getRelated(...); // Third execution
```

### 4. Use Appropriate Detail Levels

```typescript
// For UI: name-only discovery (light)
const tools = await search_tools({ detailLevel: 'name' });

// For planning: name + description (medium)
const tools = await search_tools({ detailLevel: 'name+description' });

// For implementation: full schema (heavy)
const tools = await search_tools({ detailLevel: 'full-schema' });
```

### 5. Handle Errors Gracefully

```typescript
try {
  const result = await recall(query);
  if (result.length === 0) {
    // No results found
    const broader = await recall(query.substring(0, query.length - 3));
  }
} catch (error) {
  // Operation failed
  const fallback = await getRecent(5);
}
```

---

## Performance Considerations

### Discovery Latency

- Name-only: ~1 KB, <50ms
- Name + description: ~5 KB, <100ms
- Full schema: ~50 KB, <500ms

### Operation Latency

- Read operations: 50-200ms
- Write operations: 100-300ms
- Complex operations (consolidate): 1-5s

### Optimization Tips

1. Cache tool discovery results
2. Batch write operations with `bulkRemember()`
3. Use detail levels strategically
4. Close sessions when done
5. Run consolidation during low-activity periods

---

## Troubleshooting

### Tools Not Found

```typescript
// Check if tools are registered
const allTools = await search_tools();
if (allTools.length === 0) {
  // Initialize layers
  await initializeAllLayers();
}
```

### Session Access Denied

```typescript
// Verify session exists
const hasAccess = codeExecutionHandler.canAccess('episodic/recall', sessionId);
if (!hasAccess) {
  // Create new session
  const context = codeExecutionHandler.createToolContext(sessionId);
}
```

### Memory Full

```typescript
// Check health
const health = await memoryHealth();

// Clean up
await forgetOlderThan(Date.now() - 90 * 24 * 60 * 60 * 1000); // 90 days
await purgeLowConfidence(0.4);
```

---

## Summary

Phase 3 enables agents to:
- ✅ Write TypeScript code using memory operations
- ✅ Access all 8 memory layers through 70+ operations
- ✅ Discover tools dynamically with progressive disclosure
- ✅ Manage sessions and access control
- ✅ Build complex workflows across layers
- ✅ Monitor and improve memory quality

All operations follow consistent patterns and are fully typed with TypeScript.

