# Agent Guide: Writing Code with Athena Memory

**Target Audience**: AI agents executing code in the Athena sandbox
**Status**: Complete
**Version**: 1.0

This guide teaches agents how to write effective TypeScript code that leverages Athena's memory system.

---

## Your Superpowers

As an agent executing code in Athena's sandbox, you have access to:

1. **callMCPTool(operation, params)** - Invoke any of 70+ memory operations
2. **search_tools(options)** - Discover available tools at runtime
3. **Persistent sessions** - Your state persists across multiple executions
4. **90%+ token efficiency** - Code execution reduces tokens vs traditional tool calls

---

## Getting Started

### Your Execution Environment

```typescript
// These are available to you automatically:

// Access to any operation
const result = await callMCPTool('episodic/recall', {
  query: 'my search query',
  limit: 10
});

// Tool discovery
const tools = await search_tools({
  detailLevel: 'name+description'
});

// Logging
console.log('Debug output');

// Async/await support
const data = await someAsyncOperation();
```

### Simple Example

```typescript
// 1. Store a memory
const id = await remember('User asked about pricing');

// 2. Search for memories
const results = await recall('pricing', 5);

// 3. Log results
console.log('Found:', results.length, 'memories');

// 4. Return value
return { success: true, memories: results };
```

---

## Pattern 1: Remember What Happened

### Store Conversation Events

```typescript
// Store a single event
const id = await remember(
  'User expressed frustration with deployment process',
  { tone: 'frustrated', topic: 'deployment' },
  ['user-feedback', 'deployment']
);

// Store multiple events from a conversation
const eventIds = await bulkRemember([
  { content: 'User said: "Deployments are too slow"' },
  { content: 'I suggested: Use blue-green deployment' },
  { content: 'User: "That sounds promising"' }
], { tags: ['conversation', 'deployment'] });
```

### Store Decisions

```typescript
// Record a decision
const decisionId = await rememberDecision(
  'Use Redis for session storage',
  'Faster than database, supports TTL',
  { alternatives: ['Database', 'Memcached'] }
);
```

### Store Insights

```typescript
// Record what you learned
const insightId = await rememberInsight(
  'Users prefer simpler interfaces over feature-rich ones',
  'UX',
  0.85  // confidence
);
```

---

## Pattern 2: Learn from Experience

### Recall What You Know

```typescript
// Simple recall
const memories = await recall('how do we deploy', 10);

// With confidence filter
const highConfidence = await recall('deployment strategy', 5, 0.8);

// Recent memories only
const recent = await getRecent(20);

// Specific time period
const weekAgo = await queryLastDays(7);

// By tags
const deploymentKnowledge = await recallByTags(['deployment', 'production']);
```

### Search Your Knowledge Base

```typescript
// Semantic search (conceptual)
const related = await semanticSearch('how do we scale databases');

// Keyword search (exact)
const exact = await keywordSearch('PostgreSQL configuration');

// Best of both
const comprehensive = await hybridSearch('API performance optimization');

// Task-based discovery
const tools = await findToolsFor('improve system performance');
```

---

## Pattern 3: Organize Knowledge

### Store Facts and Principles

```typescript
// Store a fact
const factId = await storeFact(
  'PostgreSQL supports JSONB columns',
  'PostgreSQL documentation',
  0.99
);

// Store a principle
const principleId = await storePrinciple(
  'Always validate user input before processing',
  'security',
  ['SQL injection prevention', 'XSS prevention']
);

// Store a concept
const conceptId = await storeConcept(
  'Blue-Green Deployment',
  'Technique where two identical environments exist: Blue (current) and Green (new)',
  ['CI/CD', 'deployment', 'zero-downtime']
);
```

### Search Your Knowledge

```typescript
// Find related facts
const facts = await list(20, 0, 'usefulness', 'desc');

// Analyze topics
const topicAnalysis = await analyzeTopics();
console.log('Dominant topics:', topicAnalysis.dominantTopics);

// Get statistics
const stats = await getStats();
console.log('Total knowledge items:', stats.totalMemories);
```

---

## Pattern 4: Plan and Execute

### Create Tasks

```typescript
// Create a task
const taskId = await createTask(
  'Implement caching layer',
  'Reduce API latency by 50%',
  8  // priority (1-10)
);

// Create related tasks
const subtasks = await Promise.all([
  createTask('Design cache strategy', 'Plan Redis topology', 9),
  createTask('Implement Redis client', 'Add caching wrapper', 8),
  createTask('Add cache invalidation', 'Automatic TTL management', 7)
]);

// Mark as you progress
await updateTask(taskId, { status: 'in_progress' });

// Record insights as you work
await rememberInsight('Redis cluster better for high availability', 'infrastructure', 0.9);

// Complete when done
await completeTask(taskId);
```

### Track Goals

```typescript
// Define a goal
const goalId = await createGoal(
  'Improve system performance',
  'Reduce P95 latency to <100ms'
);

// Update progress
await updateGoal(goalId, 25);  // 25% done
await updateGoal(goalId, 50);  // 50% done
await updateGoal(goalId, 100); // Complete

// Check pending work
const pending = await getPendingTasks();
console.log('Overdue tasks:', pending.length);
```

---

## Pattern 5: Explore Relationships

### Understand Entity Connections

```typescript
// Find entities
const entities = await searchEntities('database optimization', 5);

// Get details
const entity = await getEntity(entities[0].id);

// Find relationships
const related = await getRelationships(entity.id, 'relates_to');

// Analyze connections
const analysis = await analyzeEntity(entity.id);
console.log('Centrality:', analysis.centrality);
console.log('Community:', analysis.communityId);

// Find path between concepts
const path = await findPath('source_concept', 'target_concept');
console.log('Connection path:', path);
```

---

## Pattern 6: Monitor System Health

### Check Memory Status

```typescript
// Overall health
const health = await memoryHealth();
console.log('Average confidence:', health.averageConfidence);
if (health.issues.length > 0) {
  console.log('Issues:', health.issues);
}

// Your expertise
const expertise = await getExpertise();
console.log('Expertise levels:', expertise);

// Cognitive load
const load = await getCognitiveLoad();
console.log('Working memory usage:', load.workingMemory);
console.log('Stress level:', load.stress);

// Knowledge gaps
const gaps = await findGaps();
if (gaps.length > 0) {
  console.log('Areas to learn:', gaps);
}

// Recommendations
const recommendations = await getRecommendations();
```

### Improve Quality

```typescript
// Analyze patterns
const patterns = await analyzePatterns(10, 0.7);
console.log('Found patterns:', patterns.patterns.length);

// Clean low-confidence memories
const deleted = await purgeLowConfidence(0.3);

// Consolidate knowledge
const consolidated = await consolidate('balanced');

// Schedule next consolidation
const status = await getStatus();
console.log('Consolidation status:', status.status);
```

---

## Pattern 7: Discover Available Tools

### Progressive Discovery

```typescript
// Start light (1 KB context)
const minimal = await search_tools({ detailLevel: 'name' });
console.log('Available operations:', minimal.length);

// Expand when needed (5 KB context)
const withDesc = await search_tools({ detailLevel: 'name+description' });

// Deep dive if required (50 KB context)
const fullSchema = await search_tools({ detailLevel: 'full-schema' });
```

### Filtered Discovery

```typescript
// Tools in specific layer
const episodicOps = await search_tools({ layer: 'episodic' });

// Only safe read operations
const readOps = await search_tools({ category: 'read' });

// State-modifying operations
const writeOps = await search_tools({ category: 'write' });

// Search by name
const recallOps = await search_tools({ query: 'recall' });

// Task-based recommendations
const storeTools = await findToolsFor('save user preferences');
```

---

## Pattern 8: Complex Workflows

### Learn and Extract Procedures

```typescript
// 1. Store experience
const eventId = await remember('Successfully deployed to production');

// 2. Extract procedures
const procedures = await extract(3, 0.7);
console.log('Extracted procedures:', procedures.length);

// 3. Execute procedure next time
if (procedures.length > 0) {
  const result = await execute(procedures[0], {
    service: 'api-service',
    version: '2.0.0'
  });
  console.log('Procedure executed:', result);
}
```

### Multi-Layer Analysis

```typescript
// 1. Find relevant experiences
const memories = await recall('API design patterns', 10);

// 2. Search for related knowledge
const knowledge = await semanticSearch('REST API best practices');

// 3. Analyze entity relationships
const entities = await searchEntities('API design');

// 4. Retrieve comprehensive context
const context = await retrieve('How should we design this API?', 10);

// 5. Synthesize answer
return {
  memories: memories.length,
  knowledge: knowledge.length,
  entities: entities.length,
  context: context
};
```

---

## Code Patterns and Examples

### Pattern: Error Handling

```typescript
try {
  const result = await recall('something');
  if (result.length === 0) {
    // Try broader search
    const broader = await recall(query.split(' ')[0]);
    return broader;
  }
  return result;
} catch (error) {
  console.error('Recall failed:', error);
  // Fallback
  return await getRecent(5);
}
```

### Pattern: Batch Operations

```typescript
// Store multiple memories efficiently
const events = [
  'First event happened',
  'Second event happened',
  'Third event happened'
];

const ids = await bulkRemember(
  events.map(e => ({ content: e })),
  { parallel: true }
);

console.log(`Stored ${ids.length} events`);
```

### Pattern: Conditional Logic

```typescript
// Check health and take action
const health = await memoryHealth();

if (health.averageConfidence < 0.7) {
  // Confidence is low, clean up
  await purgeLowConfidence(0.5);

  // Run consolidation
  const metrics = await consolidate('quality');
  console.log('Consolidated:', metrics.extractedPatterns, 'patterns');
}

if (health.issues.length > 0) {
  // Report issues
  return { success: false, issues: health.issues };
}

return { success: true, confidence: health.averageConfidence };
```

### Pattern: Pagination

```typescript
// Process all memories
let offset = 0;
const batchSize = 50;

while (true) {
  const batch = await list(batchSize, offset);
  if (batch.length === 0) break;

  // Process batch
  for (const memory of batch) {
    // Do something with memory
  }

  offset += batch.length;
}
```

---

## Best Practices for Agents

### 1. Use Meaningful Tags

```typescript
// ✅ Good: Specific, hierarchical tags
await remember(content, { tags: ['user-feedback', 'feature-request', 'ui'] });

// ❌ Poor: Vague tags
await remember(content, { tags: ['data', 'info'] });
```

### 2. Record Context

```typescript
// ✅ Good: Store rich context
const id = await remember(content, {
  source: 'user-conversation',
  urgency: 'high',
  category: 'bug-report',
  relatedTask: taskId
});

// ❌ Poor: Minimal context
const id = await remember(content);
```

### 3. Chain Related Operations

```typescript
// ✅ Good: Single execution with multiple operations
const code = `
  const event = await remember(...);
  const insights = await analyzePatterns();
  const health = await memoryHealth();
  return { event, insights, health };
`;
// Result: 1 HTTP call, efficient

// ❌ Poor: Multiple separate executions
await remember(...);  // HTTP call 1
await analyzePatterns();  // HTTP call 2
await memoryHealth();  // HTTP call 3
// Result: 3 HTTP calls, inefficient
```

### 4. Use Detail Levels Strategically

```typescript
// ✅ Good: Start light, expand as needed
const tools = await search_tools({ detailLevel: 'name' });
if (tools.length > 0) {
  const detailed = await search_tools({ detailLevel: 'name+description' });
}

// ❌ Poor: Always use full schema
const tools = await search_tools({ detailLevel: 'full-schema' });
// Wastes context (50KB when 1KB would suffice)
```

### 5. Handle Empty Results

```typescript
// ✅ Good: Graceful fallback
const memories = await recall(query, 10);
if (memories.length === 0) {
  const recent = await getRecent(10);
  return recent;
}
return memories;

// ❌ Poor: Assume results exist
const memories = await recall(query, 10);
return memories[0];  // May crash if empty
```

### 6. Track Confidence

```typescript
// ✅ Good: Use confidence levels
const highConfidence = await recall(query, 5, 0.8);
if (highConfidence.length === 0) {
  const lowConfidence = await recall(query, 5, 0.5);
}

// ❌ Poor: Ignore confidence
const results = await recall(query);
// May include low-confidence false positives
```

---

## Common Agent Tasks

### Task: Analyze User Request

```typescript
// Remember the request
const requestId = await remember(userMessage, { type: 'user-request' });

// Search for similar past requests
const similar = await semanticSearch(userMessage, 5);

// Get relevant procedures
const tools = await findToolsFor(userMessage);

// Analyze knowledge needed
const gaps = await findGaps();

return {
  requestId,
  similarRequests: similar,
  applicableTools: tools,
  knowledgeGaps: gaps
};
```

### Task: Extract Learnings

```typescript
// Record the interaction
const eventId = await remember(interaction);

// Extract patterns
const patterns = await analyzePatterns(20);

// Store insights
const insightId = await rememberInsight(
  'Users prefer direct answers over explanations',
  'UX',
  0.85
);

// Try to extract new procedures
const procs = await extract(3, 0.7);

return { eventId, patterns, insightId, newProcedures: procs };
```

### Task: Check System Status

```typescript
// Health check
const health = await memoryHealth();

// Expertise analysis
const expertise = await getExpertise();

// Cognitive load
const load = await getCognitiveLoad();

// Issues and recommendations
const gaps = await findGaps();
const recs = await getRecommendations();

return {
  healthy: health.averageConfidence > 0.7,
  expertise,
  stressed: load.stress > 0.7,
  issues: gaps,
  improvements: recs
};
```

---

## Token Efficiency Tips

### ✅ Efficient Execution

```typescript
// Single execution with multiple operations
const code = `
  const recent = await getRecent(10);
  const related = await searchRelated(recent[0].id);
  const analysis = await analyzeEntity(recent[0].id);
  return { recent, related, analysis };
`;

// Result: 1 HTTP call, ~2KB tokens
```

### ❌ Inefficient Execution

```typescript
// Multiple separate executions
await getRecent(10);  // 1 HTTP call, 500+ tokens
await searchRelated(...);  // 1 HTTP call, 500+ tokens
await analyzeEntity(...);  // 1 HTTP call, 500+ tokens

// Result: 3 HTTP calls, ~1500+ tokens (3x worse)
```

---

## Next Steps

1. **Start simple**: Use `remember()` and `recall()` to get familiar
2. **Add storage**: Use `store()` for knowledge base
3. **Explore**: Use `search_tools()` to discover available operations
4. **Analyze**: Use `analyzePatterns()` and health checks
5. **Optimize**: Use batching and workflow chaining

---

## Summary

As an agent, you can:
- ✅ Remember experiences with `remember()`
- ✅ Recall memories with `recall()`
- ✅ Store knowledge with `store()`
- ✅ Search knowledge with `semanticSearch()`, `keywordSearch()`, `hybridSearch()`
- ✅ Manage tasks with `createTask()`, `completeTask()`
- ✅ Track goals with `createGoal()`, `updateGoal()`
- ✅ Analyze relationships with `analyzeEntity()`, `findPath()`
- ✅ Monitor health with `memoryHealth()`, `getExpertise()`
- ✅ Discover tools with `search_tools()`
- ✅ Extract procedures with `extract()`
- ✅ Get 90%+ token efficiency with code execution

All in one secure sandbox with persistent state!

