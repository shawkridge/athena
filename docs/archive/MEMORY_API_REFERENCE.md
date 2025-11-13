# Athena Memory API Reference

Complete documentation of all 70+ operations across 8 memory layers. Each operation is a direct import from `@athena/memory`.

**Quick Navigation:**
- [Episodic Memory (14 ops)](#episodic-memory-14-operations)
- [Semantic Memory (18 ops)](#semantic-memory-18-operations)
- [Procedural Memory (6 ops)](#procedural-memory-6-operations)
- [Prospective Memory (11 ops)](#prospective-memory-11-operations)
- [Knowledge Graph (8 ops)](#knowledge-graph-8-operations)
- [Meta-Memory (9 ops)](#meta-memory-9-operations)
- [Consolidation (7 ops)](#consolidation-7-operations)
- [RAG - Advanced Retrieval (10 ops)](#rag-advanced-retrieval-10-operations)

**Table Format:**
```
| Operation | Category | Parameters | Returns | Performance | Description |
```

---

## EPISODIC MEMORY (14 Operations)

Store and recall experiences, events, and temporal sequences with automatic temporal grounding.

### Core Operations

#### `remember(content: string, context?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 180ms |
| **Description** | Store a new experience or event with automatic timestamp |
| **Parameters** | `content` (string): Event content. `context` (optional): Additional context like location, project |
| **Returns** | Event ID (string) for later retrieval |
| **Example** | `const id = await remember('Debugged authentication bug in auth.ts')` |
| **Invalidates** | recall, getRecent, queryTemporal, listEvents |

#### `recall(query: string, limit?: number, options?: RecallOptions): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 85ms |
| **Description** | Search and recall similar experiences |
| **Parameters** | `query` (string): What to search for. `limit` (optional, default 10): Max results. `options` (optional): Advanced filters |
| **Returns** | Array of matching memories with scores |
| **Example** | `const memories = await recall('authentication issues', 10)` |
| **Cached** | 5 minutes (LRU, TTL-based) |
| **Cache Key** | `episodic/recall:{"query":"...","limit":...}` |

#### `forget(id: string): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 50ms |
| **Description** | Delete a specific memory |
| **Parameters** | `id` (string): Memory ID to delete |
| **Returns** | Success flag (boolean) |
| **Example** | `await forget('mem-123')` |
| **Invalidates** | listEvents, recall |

#### `bulkRemember(events: RememberInput[]): Promise<string[]>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 300ms |
| **Description** | Batch insert multiple events (optimized) |
| **Parameters** | `events`: Array of `{content, context?}` objects |
| **Returns** | Array of event IDs |
| **Example** | `const ids = await bulkRemember([{content: 'Event 1'}, {content: 'Event 2'}])` |
| **Performance** | 1500-2000 events/sec |
| **Invalidates** | recall, getRecent, queryTemporal, listEvents |

#### `queryTemporal(startTime: number, endTime: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 95ms |
| **Description** | Query events within a time range |
| **Parameters** | `startTime`, `endTime`: Unix timestamps (ms) |
| **Returns** | Events in temporal order |
| **Example** | `const today = await queryTemporal(startOfDay, endOfDay)` |
| **Cached** | 5 minutes |

#### `listEvents(limit?: number, offset?: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 80ms |
| **Description** | Get paginated list of all events (most recent first) |
| **Parameters** | `limit` (optional, default 10): Items per page. `offset` (optional): Pagination offset |
| **Returns** | Recent events in reverse chronological order |
| **Example** | `const recent = await listEvents(50)` |
| **Cached** | 5 minutes |

### Specialized Recall Operations

#### `getRecent(limit?: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 40ms |
| **Description** | Get most recent events (fast path, cached) |
| **Parameters** | `limit` (optional, default 10) |
| **Returns** | Last N events |
| **Example** | `const recent = await getRecent(5)` |
| **Cached** | 2 minutes (very frequently accessed) |
| **Cache Strategy** | LRU with 50K items max |

#### `recallWithMetrics(query: string, limit?: number): Promise<{memories: Memory[], metrics: RecallMetrics}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 120ms |
| **Description** | Recall with quality metrics (relevance, recency, frequency) |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Memories + scoring breakdown (relevance %, recency weight, hit frequency) |
| **Example** | `const {memories, metrics} = await recallWithMetrics('bug fixes')` |
| **Use Case** | Understand why certain memories were recalled |

#### `recallByTags(tags: string[], limit?: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 50ms |
| **Description** | Filter memories by tags |
| **Parameters** | `tags`: Array of tag names. `limit` (optional, default 10) |
| **Returns** | Matching events |
| **Example** | `const bugs = await recallByTags(['bug', 'critical'])` |
| **Cached** | 5 minutes |

### Specialized Remember Operations

#### `rememberDecision(decision: string, context?: string, rationale?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 200ms |
| **Description** | Store a decision with rationale (tagged for easy recall) |
| **Parameters** | `decision`: What was decided. `context`: Where/when. `rationale`: Why |
| **Returns** | Event ID |
| **Example** | `await rememberDecision('Use Postgres for this project', 'project:x', 'Better JSONB support')` |
| **Tags** | Automatically tagged with 'decision' |
| **Invalidates** | recall |

#### `rememberInsight(insight: string, context?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 180ms |
| **Description** | Store a learned insight or principle |
| **Parameters** | `insight`: The insight. `context`: Optional context |
| **Returns** | Event ID |
| **Example** | `await rememberInsight('Caching at the layer boundary is more effective than at query level')` |
| **Tags** | Automatically tagged with 'insight' |

#### `rememberError(error: string, solution?: string, context?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Episodic |
| **Latency P95** | 190ms |
| **Description** | Store an error and its solution for future reference |
| **Parameters** | `error`: Error description. `solution`: How it was fixed. `context`: Optional |
| **Returns** | Event ID |
| **Example** | `await rememberError('TypeError: null is not an object', 'Added null check in line 42')` |
| **Tags** | Automatically tagged with 'error', 'lesson-learned' |

### Query Helper Operations

#### `queryLastDays(days: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 90ms |
| **Description** | Query events from last N days |
| **Parameters** | `days`: Number of days to look back |
| **Returns** | Events in descending time order |
| **Example** | `const lastWeek = await queryLastDays(7)` |
| **Cached** | 1 minute |

#### `getOldest(limit?: number): Promise<Memory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Episodic |
| **Latency P95** | 70ms |
| **Description** | Get oldest events (useful for cleanup, archival) |
| **Parameters** | `limit` (optional, default 10) |
| **Returns** | Oldest N events |
| **Example** | `const old = await getOldest(100)` |
| **Use Case** | Identify candidates for consolidation or deletion |

---

## SEMANTIC MEMORY (18 Operations)

Store and search knowledge, facts, principles, and concepts using hybrid vector + keyword search.

### Search Operations (6)

#### `search(query: string, limit?: number, options?: SearchOptions): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 140ms |
| **Description** | Intelligent hybrid search (vector + keyword auto-blended) |
| **Parameters** | `query`: Search term. `limit` (optional, default 10). `options`: Advanced filters |
| **Returns** | Ranked semantic memories with relevance scores |
| **Example** | `const facts = await search('database optimization', 10)` |
| **Strategy** | Auto-selects vector/keyword/hybrid based on query type |
| **Cached** | 5 minutes |

#### `semanticSearch(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 160ms |
| **Description** | Vector embedding-based semantic search |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Results ranked by semantic similarity |
| **Example** | `const similar = await semanticSearch('optimization strategies')` |
| **Uses** | Semantic embeddings (Ollama/Anthropic) |

#### `keywordSearch(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 80ms |
| **Description** | BM25 keyword-based search (fast, good for exact terms) |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Results ranked by keyword relevance |
| **Example** | `const docs = await keywordSearch('PostgreSQL JSONB')` |
| **Performance** | Fastest search type (<100ms) |

#### `hybridSearch(query: string, limit?: number): Promise<HybridSearchResults>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 200ms |
| **Description** | Combined vector + BM25 search with reranking |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Object with `semantic`, `keyword`, `reranked` result arrays |
| **Example** | `const results = await hybridSearch('caching patterns')` |
| **Returns Structure** | `{semantic: [], keyword: [], reranked: []}` |
| **Best For** | Maximum quality recall (combined strengths of both) |

#### `searchByTopic(topic: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 130ms |
| **Description** | Search facts tagged with a specific topic |
| **Parameters** | `topic`: Topic name. `limit` (optional, default 10) |
| **Returns** | All facts in that topic area |
| **Example** | `const dbFacts = await searchByTopic('database')` |
| **Use Case** | Find all knowledge in a domain |

#### `searchRelated(id: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 150ms |
| **Description** | Find semantically related facts to a given memory |
| **Parameters** | `id`: Memory ID. `limit` (optional, default 10) |
| **Returns** | Related memories sorted by relevance |
| **Example** | `const related = await searchRelated('mem-456')` |
| **Uses** | Vector similarity + graph relationships |

### Storage Operations (5)

#### `store(content: string, topics?: string[]): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 250ms |
| **Description** | Store a fact or knowledge item |
| **Parameters** | `content`: The fact/knowledge. `topics` (optional): Category tags |
| **Returns** | Fact ID (string) |
| **Example** | `await store('PostgreSQL supports JSONB columns natively', ['database'])` |
| **Auto** | Generates embeddings, extracts entities, builds knowledge graph connections |
| **Invalidates** | search, semanticSearch, keywordSearch, hybridSearch |

#### `storeFact(fact: string, source?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 260ms |
| **Description** | Store a specific factual claim |
| **Parameters** | `fact`: The fact. `source`: Where it came from |
| **Returns** | Fact ID |
| **Example** | `await storeFact('React 18 introduced automatic batching', 'React docs v18')` |
| **Tagged** | Automatically tagged 'fact' |

#### `storePrinciple(principle: string, context?: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 260ms |
| **Description** | Store a design principle or pattern |
| **Parameters** | `principle`: The principle. `context` (optional): When to apply |
| **Returns** | Memory ID |
| **Example** | `await storePrinciple('Cache at layer boundaries for maximum impact')` |
| **Tagged** | Automatically tagged 'principle' |

#### `storeConcept(concept: string, definition: string): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 270ms |
| **Description** | Store a concept with definition |
| **Parameters** | `concept`: Concept name. `definition`: What it means |
| **Returns** | Concept ID |
| **Example** | `await storeConcept('Circuit Breaker', 'Pattern preventing cascading failures...')` |
| **Tagged** | Automatically tagged 'concept' |

#### `update(id: string, content: string): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 220ms |
| **Description** | Update an existing semantic memory |
| **Parameters** | `id`: Memory ID. `content`: Updated content |
| **Returns** | Success flag |
| **Example** | `await update('mem-789', 'Updated definition...')` |
| **Invalidates** | search, get, list, searchRelated |

### Retrieval Operations (4)

#### `get(id: string): Promise<SemanticMemory | null>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 15ms |
| **Description** | Get a specific memory by ID |
| **Parameters** | `id`: Memory ID |
| **Returns** | Full memory object or null |
| **Example** | `const fact = await get('mem-123')` |
| **Cached** | 10 minutes |
| **Performance** | Direct lookup, sub-20ms |

#### `list(limit?: number, offset?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 120ms |
| **Description** | List all semantic memories paginated |
| **Parameters** | `limit` (optional, default 10). `offset` (optional) |
| **Returns** | Memories most recent first |
| **Example** | `const all = await list(100)` |
| **Cached** | 5 minutes |

#### `listAll(): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 200ms |
| **Description** | Get all semantic memories (no pagination) |
| **Returns** | Complete set of all stored knowledge |
| **Example** | `const everything = await listAll()` |
| **Use Case** | Consolidation, export, analysis |

#### `getRecent(limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 50ms |
| **Description** | Get most recently added semantic memories |
| **Parameters** | `limit` (optional, default 10) |
| **Returns** | Recent additions |
| **Example** | `const new = await getRecent(5)` |
| **Cached** | 2 minutes |

### Management Operations (3)

#### `delete_memory(id: string): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 60ms |
| **Description** | Delete a semantic memory |
| **Parameters** | `id`: Memory ID |
| **Returns** | Success flag |
| **Example** | `await delete_memory('mem-123')` |
| **Invalidates** | search, list, get, searchRelated |

#### `deleteMultiple(ids: string[]): Promise<number>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 150ms |
| **Description** | Batch delete memories |
| **Parameters** | `ids`: Array of memory IDs |
| **Returns** | Count of deleted items |
| **Example** | `const deleted = await deleteMultiple(['mem-1', 'mem-2', 'mem-3'])` |
| **Invalidates** | search, list, get |

#### `deleteByTopics(topics: string[]): Promise<number>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic |
| **Latency P95** | 300ms |
| **Description** | Delete all memories in given topics |
| **Parameters** | `topics`: Topic names to delete |
| **Returns** | Count deleted |
| **Example** | `await deleteByTopics(['deprecated-pattern', 'outdated'])` |
| **Invalidates** | search, list, searchByTopic |

### Analysis Operations (4)

#### `analyzeTopics(): Promise<{topic: string, count: number}[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 100ms |
| **Description** | Get distribution of knowledge across topics |
| **Returns** | Array of topics with memory counts |
| **Example** | `const topics = await analyzeTopics()` |
| **Use Case** | Understand knowledge coverage and gaps |
| **Cached** | 10 minutes |

#### `getStats(): Promise<{total: number, byTopic: Record<string, number>, avgAge: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 80ms |
| **Description** | Get semantic memory statistics |
| **Returns** | Counts, topic breakdown, age statistics |
| **Example** | `const stats = await getStats()` |
| **Cached** | 15 minutes |

#### `getRelated(id: string): Promise<{direct: SemanticMemory[], graph: SemanticMemory[]}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Semantic |
| **Latency P95** | 180ms |
| **Description** | Get memories related via multiple methods |
| **Returns** | Direct relations + graph-based relations |
| **Example** | `const {direct, graph} = await getRelated('mem-456')` |
| **Uses** | Vector similarity + knowledge graph |

#### `consolidate(): Promise<{patternsExtracted: number, newFacts: number}>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Semantic (triggered by Consolidation) |
| **Latency P95** | 2000ms |
| **Description** | Extract patterns from episodic events into semantic knowledge |
| **Returns** | Statistics on extraction results |
| **Example** | `const result = await consolidate()` |
| **Runs Async** | Typically runs during off-peak (consolidation scheduler) |

---

## PROCEDURAL MEMORY (6 Operations)

Learn and execute reusable workflows and procedures.

#### `extract(fromEvents?: boolean): Promise<Procedure[]>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Procedural |
| **Latency P95** | 3000ms |
| **Description** | Extract procedures from episode patterns (automatic learning) |
| **Parameters** | `fromEvents` (optional, default true): Extract from episodic events |
| **Returns** | List of extracted procedures |
| **Example** | `const procedures = await extract()` |
| **Auto-triggers** | After consolidation of high-frequency patterns |
| **Learns** | Procedures that occur 3+ times with >70% success rate |

#### `list(): Promise<Procedure[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Procedural |
| **Latency P95** | 80ms |
| **Description** | List all learned procedures |
| **Returns** | All procedures with metadata |
| **Example** | `const procedures = await list()` |
| **Cached** | 10 minutes |
| **Current Count** | 101 procedures learned |

#### `get(name: string): Promise<Procedure | null>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Procedural |
| **Latency P95** | 30ms |
| **Description** | Get a specific procedure by name |
| **Parameters** | `name`: Procedure name |
| **Returns** | Procedure with steps |
| **Example** | `const proc = await get('debug-performance-issue')` |
| **Cached** | 15 minutes |

#### `execute(name: string, params?: Record<string, any>): Promise<any>`
| Property | Value |
|----------|-------|
| **Category** | Execute |
| **Layer** | Procedural |
| **Latency P95** | Variable (procedure dependent) |
| **Description** | Execute a learned procedure |
| **Parameters** | `name`: Procedure name. `params`: Optional parameters |
| **Returns** | Procedure result |
| **Example** | `const result = await execute('analyze-performance', {threshold: 100})` |
| **Logs** | Execution tracked and success rate updated |
| **Fallback** | Gracefully degrades if procedure fails |

#### `getEffectiveness(name: string): Promise<{successRate: number, timesRun: number, avgDuration: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Procedural |
| **Latency P95** | 30ms |
| **Description** | Get quality metrics for a procedure |
| **Parameters** | `name`: Procedure name |
| **Returns** | Effectiveness stats (success %, times run, avg time) |
| **Example** | `const effectiveness = await getEffectiveness('analyze-performance')` |
| **Use Case** | Decide whether to use procedure or try new approach |

#### `search(query: string, limit?: number): Promise<Procedure[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Procedural |
| **Latency P95** | 100ms |
| **Description** | Search procedures by name or description |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Matching procedures |
| **Example** | `const procs = await search('performance optimization')` |
| **Cached** | 10 minutes |

---

## PROSPECTIVE MEMORY (11 Operations)

Manage tasks, goals, and future-oriented planning.

### Task Operations (6)

#### `createTask(title: string, description: string, priority?: number): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Prospective |
| **Latency P95** | 120ms |
| **Description** | Create a new task |
| **Parameters** | `title`: Task name. `description`: Details. `priority` (optional, 1-10, default 5) |
| **Returns** | Task ID |
| **Example** | `const taskId = await createTask('Implement caching', 'Add LRU cache for queries', 8)` |
| **Auto** | Searches knowledge for related patterns, estimates effort |
| **Invalidates** | listTasks, getPendingTasks |

#### `listTasks(limit?: number): Promise<Task[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 100ms |
| **Description** | List all tasks |
| **Parameters** | `limit` (optional, default 20) |
| **Returns** | Tasks with status and priority |
| **Example** | `const tasks = await listTasks(50)` |
| **Cached** | 2 minutes |
| **Ordered** | By priority desc, then created date |

#### `getTask(id: string): Promise<Task | null>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 20ms |
| **Description** | Get a specific task |
| **Parameters** | `id`: Task ID |
| **Returns** | Full task object |
| **Example** | `const task = await getTask('task-123')` |
| **Cached** | 5 minutes |

#### `updateTask(id: string, updates: Partial<Task>): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Prospective |
| **Latency P95** | 80ms |
| **Description** | Update task details |
| **Parameters** | `id`: Task ID. `updates`: Fields to change (title, description, status, etc) |
| **Returns** | Success flag |
| **Example** | `await updateTask('task-123', {status: 'in-progress', priority: 9})` |
| **Invalidates** | listTasks, getTask, getPendingTasks |

#### `completeTask(id: string): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Prospective |
| **Latency P95** | 100ms |
| **Description** | Mark task as complete |
| **Parameters** | `id`: Task ID |
| **Returns** | Success flag |
| **Example** | `await completeTask('task-123')` |
| **Auto** | Records completion time, updates metrics |
| **Invalidates** | listTasks, getPendingTasks, getProgressMetrics |

#### `getPendingTasks(limit?: number): Promise<Task[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 60ms |
| **Description** | Get all active/pending tasks |
| **Parameters** | `limit` (optional, default 20) |
| **Returns** | Only incomplete tasks |
| **Example** | `const active = await getPendingTasks()` |
| **Cached** | 2 minutes |
| **Ordered** | By priority (highest first) |

### Goal Operations (5)

#### `createGoal(name: string, description: string, priority?: number): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Prospective |
| **Latency P95** | 140ms |
| **Description** | Create a high-level goal |
| **Parameters** | `name`: Goal name. `description`: Details. `priority` (optional, 1-10) |
| **Returns** | Goal ID |
| **Example** | `await createGoal('Optimize memory system for local-first', 'Eliminate HTTP overhead', 9)` |
| **Cascade** | Searches for related goals, suggests task breakdown |
| **Invalidates** | listGoals, getProgressMetrics |

#### `listGoals(limit?: number): Promise<Goal[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 90ms |
| **Description** | List all goals |
| **Parameters** | `limit` (optional, default 20) |
| **Returns** | Goals with progress and status |
| **Example** | `const goals = await listGoals()` |
| **Cached** | 5 minutes |
| **Ordered** | By priority desc, then by progress |

#### `getGoal(id: string): Promise<Goal | null>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 25ms |
| **Description** | Get a specific goal |
| **Parameters** | `id`: Goal ID |
| **Returns** | Full goal with related tasks |
| **Example** | `const goal = await getGoal('goal-456')` |
| **Cached** | 10 minutes |

#### `updateGoal(id: string, updates: Partial<Goal>): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Prospective |
| **Latency P95** | 100ms |
| **Description** | Update goal details |
| **Parameters** | `id`: Goal ID. `updates`: Fields to change |
| **Returns** | Success flag |
| **Example** | `await updateGoal('goal-456', {status: 'completed'})` |
| **Invalidates** | listGoals, getGoal, getProgressMetrics |

#### `getProgressMetrics(): Promise<{goals: GoalProgress[], overallCompletion: number, timeline: {goal: string, eta: number}[]}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Prospective |
| **Latency P95** | 150ms |
| **Description** | Get progress metrics across all goals |
| **Returns** | Completion %, ETAs, priority rankings |
| **Example** | `const metrics = await getProgressMetrics()` |
| **Includes** | Task completion rates, goal completion %, velocity metrics |
| **Cached** | 5 minutes |

---

## KNOWLEDGE GRAPH (8 Operations)

Explore entity relationships and semantic connections.

#### `searchEntities(query: string, limit?: number): Promise<Entity[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 120ms |
| **Description** | Search entities by name or type |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Matching entities with types |
| **Example** | `const entities = await searchEntities('PostgreSQL')` |
| **Cached** | 10 minutes |

#### `getEntity(id: string): Promise<Entity | null>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 40ms |
| **Description** | Get a specific entity |
| **Parameters** | `id`: Entity ID |
| **Returns** | Entity with all properties |
| **Example** | `const entity = await getEntity('entity-db-123')` |
| **Cached** | 15 minutes |
| **Includes** | Type, properties, relationship count |

#### `createEntity(name: string, type: string, properties?: Record<string, any>): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Graph |
| **Latency P95** | 100ms |
| **Description** | Create a new entity (concept, pattern, tool, person, etc) |
| **Parameters** | `name`: Entity name. `type`: Category (e.g., 'tool', 'pattern'). `properties`: Optional metadata |
| **Returns** | Entity ID |
| **Example** | `await createEntity('Circuit Breaker', 'pattern', {domain: 'resilience'})` |
| **Auto** | Links to related entities, finds similar concepts |
| **Invalidates** | searchEntities, getEntity |

#### `analyzeEntity(id: string): Promise<EntityAnalysis>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 300ms |
| **Description** | Deep analysis of an entity's role and connections |
| **Returns** | Relationships, influence, centrality, related entities |
| **Example** | `const analysis = await analyzeEntity('entity-pattern-456')` |
| **Metrics** | Degree centrality, betweenness, communities it belongs to |

#### `getRelationships(entityId: string, limit?: number): Promise<Relationship[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 100ms |
| **Description** | Get all relationships for an entity |
| **Parameters** | `entityId`: Entity ID. `limit` (optional, default 20) |
| **Returns** | Incoming and outgoing relationships |
| **Example** | `const rels = await getRelationships('entity-db-123')` |
| **Cached** | 10 minutes |

#### `createRelationship(fromId: string, toId: string, type: string, properties?: Record<string, any>): Promise<string>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Graph |
| **Latency P95** | 80ms |
| **Description** | Create a relationship between entities |
| **Parameters** | `fromId`, `toId`: Entity IDs. `type`: Relationship type (e.g., 'uses', 'solves'). `properties`: Optional metadata |
| **Returns** | Relationship ID |
| **Example** | `await createRelationship('entity-app', 'entity-db', 'uses', {since: 2024})` |
| **Auto** | Updates graph metrics, affects search rankings |
| **Invalidates** | getRelationships, analyzeEntity |

#### `searchRelationships(relationshipType: string, limit?: number): Promise<Relationship[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 110ms |
| **Description** | Find all relationships of a type |
| **Parameters** | `relationshipType`: Relationship type (e.g., 'depends-on'). `limit` (optional) |
| **Returns** | All relationships of that type |
| **Example** | `const deps = await searchRelationships('depends-on')` |
| **Cached** | 15 minutes |

#### `findPath(fromId: string, toId: string): Promise<Entity[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 250ms |
| **Description** | Find shortest path between two entities |
| **Parameters** | `fromId`, `toId`: Entity IDs |
| **Returns** | Ordered list of entities forming the path |
| **Example** | `const path = await findPath('entity-problem', 'entity-solution')` |
| **Uses** | BFS (breadth-first search) for optimal path |

#### `getCommunities(level?: number): Promise<CommunityInfo[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Graph |
| **Latency P95** | 500ms |
| **Description** | Detect communities in knowledge graph (Leiden algorithm) |
| **Parameters** | `level` (optional, 0=granular, 1=intermediate, 2=global) |
| **Returns** | Communities with entities and properties |
| **Example** | `const communities = await getCommunities(1)` |
| **Levels** | 0: 50+ small communities, 1: 10-15 medium, 2: 2-3 major themes |
| **Uses** | Community detection for topic analysis |

---

## META-MEMORY (9 Operations)

Monitor memory health, quality, and cognitive metrics.

#### `memoryHealth(): Promise<{overallScore: number, qualityMetrics: {...}, coverage: {...}, lastConsolidation: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 200ms |
| **Description** | Get overall memory system health |
| **Returns** | Health score (0-100), quality breakdown, coverage analysis |
| **Example** | `const health = await memoryHealth()` |
| **Metrics** | Compression ratio, recall accuracy, consistency, redundancy |
| **Cached** | 30 seconds (frequently checked) |

#### `getQualityMetrics(): Promise<{compression: number, accuracy: number, consistency: number, freshness: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 150ms |
| **Description** | Detailed quality metrics for memory |
| **Returns** | Four key quality dimensions |
| **Example** | `const quality = await getQualityMetrics()` |
| **Metrics** | Compression (2.5x typical), Accuracy (recall vs false positive ratio), Consistency (contradictions), Freshness (recency) |
| **Cached** | 1 minute |

#### `getExpertise(): Promise<{domain: string, level: number, size: number}[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 180ms |
| **Description** | Get expertise map (knowledge by domain) |
| **Returns** | Domains with expertise level (0-100) and knowledge size |
| **Example** | `const expertise = await getExpertise()` |
| **Tracks** | Depth of knowledge in each domain |
| **Cached** | 30 minutes |

#### `findGaps(): Promise<{domain: string, gapSize: number, relatedTopics: string[]}[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 250ms |
| **Description** | Identify knowledge gaps |
| **Returns** | Domains with insufficient knowledge |
| **Example** | `const gaps = await findGaps()` |
| **Suggests** | What to learn next based on related knowledge |

#### `getCognitiveLoad(): Promise<{workingMemoryUsage: number, saturation: number, recommendation: string}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 100ms |
| **Description** | Measure cognitive load (working memory) |
| **Returns** | Current load (0-7 items), saturation %, recommendation |
| **Example** | `const load = await getCognitiveLoad()` |
| **Based On** | Baddeley 7±2 working memory model |
| **Recommendation** | When approaching saturation, suggests consolidation |

#### `getAttentionMetrics(): Promise<{salience: Map<string, number>, focus: string[], distractions: string[]}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 120ms |
| **Description** | Get what's capturing attention |
| **Returns** | Salience scores, focused items, distractions |
| **Example** | `const attention = await getAttentionMetrics()` |
| **Tracks** | What's being thought about, what's novel/urgent |

#### `getMemoryStats(): Promise<{byLayer: Record<string, number>, total: number, density: number, averageAge: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 140ms |
| **Description** | Overall memory statistics |
| **Returns** | Counts by layer, total size, density, average age |
| **Example** | `const stats = await getMemoryStats()` |
| **Includes** | 8128 episodic events, 2341 facts, 101 procedures, etc. |
| **Cached** | 15 minutes |

#### `getRecommendations(): Promise<{consolidate: boolean, deleteOld: string[], learn: string[]}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 300ms |
| **Description** | Get AI recommendations for system improvement |
| **Returns** | Suggestions to consolidate, delete, or learn |
| **Example** | `const recs = await getRecommendations()` |
| **Smart** | Based on quality metrics and usage patterns |

#### `getProgressMetrics(): Promise<{goalsCompleted: number, tasksCompleted: number, patternsLearned: number, velocity: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Meta |
| **Latency P95** | 180ms |
| **Description** | Get progress across all domains |
| **Returns** | Completion stats, learning velocity |
| **Example** | `const progress = await getProgressMetrics()` |

---

## CONSOLIDATION (7 Operations)

Extract patterns, consolidate knowledge, and optimize storage.

#### `consolidate(strategy?: string): Promise<{patternsFound: number, newFacts: number, proceduresLearned: number}>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Consolidation |
| **Latency P95** | 3000-5000ms |
| **Description** | Run consolidation cycle (like sleep consolidation) |
| **Parameters** | `strategy` (optional): 'balanced' (default), 'speed', 'quality', 'minimal' |
| **Returns** | Statistics on patterns found and learned |
| **Example** | `const result = await consolidate('balanced')` |
| **Auto** | Runs hourly by default (scheduler) |
| **Process** | Statistical clustering → pattern extraction → LLM validation (uncertain patterns) |

#### `getStatus(): Promise<{lastRun: number, nextRun: number, patternsTotal: number, strategy: string}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Consolidation |
| **Latency P95** | 30ms |
| **Description** | Get consolidation scheduler status |
| **Returns** | Last run time, next scheduled, total patterns learned, active strategy |
| **Example** | `const status = await getStatus()` |
| **Cached** | 1 minute |

#### `analyzePatterns(): Promise<{pattern: string, frequency: number, confidence: number}[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Consolidation |
| **Latency P95** | 1000ms |
| **Description** | Analyze discovered patterns in episodic events |
| **Returns** | Patterns with frequency and confidence scores |
| **Example** | `const patterns = await analyzePatterns()` |
| **Doesn't consolidate** | Just analysis, doesn't persist results |

#### `extractPatterns(fromEvents: number): Promise<Pattern[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Consolidation |
| **Latency P95** | Variable (2-5s for 1000 events) |
| **Description** | Extract patterns from N most recent events |
| **Parameters** | `fromEvents`: How many recent events to analyze |
| **Returns** | Extracted patterns |
| **Example** | `const patterns = await extractPatterns(1000)` |
| **Method** | Temporal clustering → statistical feature extraction |

#### `getHistory(limit?: number): Promise<ConsolidationRun[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Consolidation |
| **Latency P95** | 100ms |
| **Description** | Get history of consolidation runs |
| **Parameters** | `limit` (optional, default 10) |
| **Returns** | Previous consolidation results |
| **Example** | `const history = await getHistory(20)` |
| **Cached** | 15 minutes |

#### `configureStrategy(strategy: string): Promise<boolean>`
| Property | Value |
|----------|-------|
| **Category** | Write |
| **Layer** | Consolidation |
| **Latency P95** | 50ms |
| **Description** | Change consolidation strategy |
| **Parameters** | `strategy`: 'balanced' | 'speed' | 'quality' | 'minimal' |
| **Returns** | Success flag |
| **Example** | `await configureStrategy('quality')` |
| **Strategies** | Speed (fast heuristics), Quality (LLM validation), Balanced (hybrid), Minimal (statistics only) |

#### `getRecommendations(): Promise<string[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | Consolidation |
| **Latency P95** | 200ms |
| **Description** | Get recommendations for consolidation tuning |
| **Returns** | List of suggested improvements |
| **Example** | `const recs = await getRecommendations()` |

---

## RAG - ADVANCED RETRIEVAL (10 Operations)

Advanced retrieval with synthesis and context enrichment.

#### `retrieve(query: string, limit?: number): Promise<{results: SemanticMemory[], context: string}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 200ms |
| **Description** | Retrieve with context synthesis |
| **Parameters** | `query`: Search query. `limit` (optional, default 10) |
| **Returns** | Results with synthesized context |
| **Example** | `const {results, context} = await retrieve('how to optimize database queries')` |
| **Strategy** | Auto-selects semantic/keyword/graph retrieval |

#### `search(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 150ms |
| **Description** | Basic RAG search |
| **Parameters** | `query`: Search term. `limit` (optional, default 10) |
| **Returns** | Ranked results |
| **Example** | `const results = await search('memory optimization')` |

#### `semanticSearch(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 160ms |
| **Description** | Semantic vector search |
| **Parameters** | `query`: Search term. `limit` (optional) |
| **Returns** | Vector-ranked results |
| **Example** | `const results = await semanticSearch('caching strategies')` |

#### `keywordSearch(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 80ms |
| **Description** | BM25 keyword search |
| **Parameters** | `query`: Search term. `limit` (optional) |
| **Returns** | BM25-ranked results |
| **Example** | `const results = await keywordSearch('PostgreSQL JSONB')` |
| **Performance** | Fastest retrieval strategy |

#### `hybridSearch(query: string, limit?: number): Promise<{semantic: [], keyword: [], reranked: []}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 200ms |
| **Description** | Combined semantic + keyword with reranking |
| **Parameters** | `query`: Search term. `limit` (optional) |
| **Returns** | Results from all three retrieval methods |
| **Example** | `const {reranked} = await hybridSearch('complex query')` |

#### `bm25Search(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 75ms |
| **Description** | BM25 probabilistic relevance ranking |
| **Parameters** | `query`: Search term. `limit` (optional) |
| **Returns** | BM25-scored results |
| **Example** | `const results = await bm25Search('exact phrase matching')` |

#### `reflectiveSearch(query: string, iterations?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 400ms |
| **Description** | Iterative search with query refinement |
| **Parameters** | `query`: Initial query. `iterations` (optional, default 2) |
| **Returns** | Improved results after refinement |
| **Example** | `const results = await reflectiveSearch('how to debug performance')` |
| **Process** | Initial query → analysis → refined query → search |

#### `retrieveWithReranking(query: string, limit?: number): Promise<SemanticMemory[]>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 250ms |
| **Description** | Retrieve and rerank by relevance |
| **Parameters** | `query`: Search query. `limit` (optional) |
| **Returns** | Reranked results (highest quality first) |
| **Example** | `const results = await retrieveWithReranking('advanced query')` |
| **Uses** | Multiple retrieval methods + cross-encoder reranking |

#### `queryExpansion(query: string): Promise<{original: string, expanded: string[], results: SemanticMemory[]}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 300ms |
| **Description** | Expand query with semantically similar terms |
| **Parameters** | `query`: Original search query |
| **Returns** | Expanded queries and combined results |
| **Example** | `const {expanded, results} = await queryExpansion('caching')` |
| **Generates** | Synonym queries, related concepts |

#### `getStats(): Promise<{queriesProcessed: number, avgLatency: number, hitRate: number}>`
| Property | Value |
|----------|-------|
| **Category** | Read |
| **Layer** | RAG |
| **Latency P95** | 80ms |
| **Description** | Get RAG system statistics |
| **Returns** | Usage and performance metrics |
| **Example** | `const stats = await getStats()` |
| **Cached** | 5 minutes |

---

## Performance Summary

| Layer | Total Ops | Typical Latency P95 | Cached |
|-------|-----------|-------------------|--------|
| Episodic | 14 | 85ms | 2-5 min |
| Semantic | 18 | 140ms | 5 min |
| Procedural | 6 | 800ms | 10-15 min |
| Prospective | 11 | 100ms | 2-5 min |
| Graph | 8 | 150ms | 10-15 min |
| Meta | 9 | 180ms | 30s-30min |
| Consolidation | 7 | 3000ms | N/A (write-heavy) |
| RAG | 10 | 200ms | 5 min |
| **TOTAL** | **70+** | **~150ms avg** | **Intelligent** |

---

## Common Patterns

### Pattern: Search-Store-Recall Workflow

```typescript
import { search, store, recall } from '@athena/memory';

// Search existing knowledge
const existing = await search('pattern name', 5);

// Store new knowledge if missing
if (existing.length === 0) {
  await store('New pattern description', ['category']);
}

// Recall it later
const memories = await recall('pattern', 10);
```

### Pattern: Task-Goal Tracking

```typescript
import { createTask, createGoal, getProgressMetrics } from '@athena/memory';

// Create goal
const goalId = await createGoal('Implement feature', 'Description', 8);

// Create related task
const taskId = await createTask('Start implementation', 'Begin coding', 9);

// Monitor progress
const metrics = await getProgressMetrics();
```

### Pattern: Consolidation Loop

```typescript
import { consolidate, getRecommendations, memoryHealth } from '@athena/memory';

// Check health
const health = await memoryHealth();
if (health.overallScore < 70) {
  // Run consolidation
  const result = await consolidate('quality');

  // Get recommendations
  const recs = await getRecommendations();
}
```

---

## Import Examples

```typescript
// Core operations
import {
  recall, remember, forget,
  search, store,
  createTask, createGoal,
  consolidate
} from '@athena/memory';

// Type definitions
import type {
  Memory,
  SemanticMemory,
  Task,
  Goal,
  Entity
} from '@athena/memory';

// Helper utilities
import {
  getSystemHealth,
  getPerformanceStats,
  getAvailableOperations
} from '@athena/memory';
```

---

**Total Operations**: 70+ across 8 layers
**Average Latency**: ~150ms (P95)
**Caching Strategy**: Intelligent LRU with operation-based invalidation
**Last Updated**: Phase 4 - Local Optimization
**Status**: Production-ready for local AI-first development
