# Athena Architecture Guide

Deep dive into the 8-layer neuroscience-inspired memory system design.

## Table of Contents

1. [System Overview](#system-overview)
2. [8-Layer Architecture](#8-layer-architecture)
3. [Layer 1: Episodic Memory](#layer-1-episodic-memory)
4. [Layer 2: Semantic Memory](#layer-2-semantic-memory)
5. [Layer 3: Procedural Memory](#layer-3-procedural-memory)
6. [Layer 4: Prospective Memory](#layer-4-prospective-memory)
7. [Layer 5: Knowledge Graph](#layer-5-knowledge-graph)
8. [Layer 6: Meta-Memory](#layer-6-meta-memory)
9. [Layer 7: Consolidation](#layer-7-consolidation)
10. [Layer 8: Supporting Systems](#layer-8-supporting-systems)
11. [Data Flow](#data-flow)
12. [Performance Architecture](#performance-architecture)

---

## System Overview

Athena implements a **neuroscience-inspired 8-layer memory architecture** for AI agents based on human cognitive science:

```
┌─────────────────────────────────────────────────────────┐
│         MCP Interface (127+ Operations)                 │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 8: Supporting Systems                      │   │
│  │  - RAG (Reflective, HyDE, Reranking)             │   │
│  │  - Planning & Verification (Q*, Simulation)      │   │
│  │  - Zettelkasten (Versioning, Hierarchies)        │   │
│  │  - GraphRAG (Community Detection)                │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 7: Consolidation (Sleep-like Processing) │   │
│  │  - Dual-process reasoning (System 1+2)          │   │
│  │  - Pattern extraction & clustering              │   │
│  │  - Quality measurement & validation             │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 6: Meta-Memory (Knowledge about Knowledge)│   │
│  │  - Quality metrics & expertise tracking          │   │
│  │  - Attention & salience management              │   │
│  │  - Cognitive load monitoring                    │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 5: Knowledge Graph (Semantic Structure)  │   │
│  │  - Entities & relations                         │   │
│  │  - Community detection (Leiden)                 │   │
│  │  - Contextual observations                      │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 4: Prospective Memory (Future-oriented)  │   │
│  │  - Task management & triggers                   │   │
│  │  - Goal hierarchies                             │   │
│  │  - Deadline tracking                            │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 3: Procedural Memory (Skills/Workflows)  │   │
│  │  - Reusable procedures                          │   │
│  │  - Pattern-based learning                       │   │
│  │  - Effectiveness metrics                        │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 2: Semantic Memory (Knowledge)           │   │
│  │  - Vector embeddings                            │   │
│  │  - Hybrid BM25 + vector search                  │   │
│  │  - Semantic similarity (Ollama/Claude)          │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Layer 1: Episodic Memory (Temporal Events)     │   │
│  │  - Timestamped event storage                    │   │
│  │  - Bayesian surprise detection                  │   │
│  │  - Working memory buffer (7±2 items)            │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  SQLite + sqlite-vec (Local-first, no cloud)           │
│  Current: 8,128 episodic events, 101 procedures        │
│  Database: 5.5 MB                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 8-Layer Architecture

### Design Principles

1. **Layered Abstraction**: Each layer has specific cognitive function
2. **Local-First**: SQLite + sqlite-vec (no cloud dependencies)
3. **Neuroscience-Inspired**: Based on human memory research (Baddeley, Squire)
4. **Hierarchical**: Higher layers synthesize information from lower layers
5. **Bidirectional**: Consolidation feeds semantic back to episodic
6. **Performance-Optimized**: <100ms most operations, caching at every level

### Information Flow

```
New Event → Episodic (recorded) → Working Memory (7 items)
              ↓
         (consolidation trigger)
              ↓
         Semantic (extracted)
              ↓
         Procedural (patterns)
         Knowledge Graph (relations)
              ↓
         Meta-Memory (quality)
              ↓
         Consolidation Engine
              ↓
    (feeds back insights)
```

---

## Layer 1: Episodic Memory

### Purpose

Store timestamped events with full context. Forms the "sensory buffer" of the system.

### Implementation

**Key Components**:
- Event storage with timestamps
- Bayesian surprise detection
- Working memory buffer (7±2 items)
- Temporal reasoning

**Database Schema**:
```sql
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    event_type TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB,
    surprise_score REAL,
    importance REAL DEFAULT 0.5
);

CREATE INDEX idx_episodic_project ON episodic_events(project_id);
CREATE INDEX idx_episodic_timestamp ON episodic_events(timestamp);
```

### Operations

- `record_event()`: Record new event
- `get_events()`: Retrieve by time window
- `get_surprise_score()`: Bayesian surprise (0-1)

### Characteristics

| Aspect | Value |
|--------|-------|
| Capacity | ~50-100 items (human episodic buffer) |
| Decay Rate | ~4 hours (without consolidation) |
| Retrieval Speed | <5ms (direct database query) |
| Typical Latency | <10ms insert, <5ms retrieve |

### Example Usage

```python
# Record event (automatic via hooks)
event_id = episodic.record_event(
    content="Implemented JWT refresh token rotation",
    event_type="action",
    outcome="success",
    context={
        "file": "auth/tokens.py",
        "lines": 42,
        "duration_minutes": 45
    }
)

# Retrieve recent events
events = episodic.get_events(days=1, project_id=1)
for event in events:
    print(f"{event.timestamp}: {event.content}")
```

---

## Layer 2: Semantic Memory

### Purpose

Store general knowledge as searchable semantic memories with vector embeddings.

### Implementation

**Key Components**:
- Vector embeddings (1,536 dimensions via Ollama)
- Hybrid search (BM25 + vector similarity)
- Recency weighting (fresher memories score higher)
- Result caching (LRU, 1-hour TTL)

**Database Schema**:
```sql
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    content TEXT NOT NULL,
    memory_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    embedding VECTOR(1536) NOT NULL
);

-- Hybrid search indices
CREATE INDEX idx_semantic_bm25 ON semantic_memories(content);
CREATE INDEX idx_semantic_vector ON semantic_memories(embedding);
CREATE INDEX idx_semantic_recency ON semantic_memories(created_at);
```

### Search Strategy

**Hybrid BM25 + Vector**:
```
score = 0.6 * bm25_score + 0.4 * vector_similarity

bm25_score = Full-text relevance (Okapi BM25)
vector_similarity = Semantic similarity (cosine distance)

# Apply recency weighting
final_score = score * exp(-decay_rate * hours_since_created)
```

### Operations

- `create()`: Store semantic memory with embedding
- `retrieve()`: Hybrid search with ranking
- `delete()`: Remove memory

### Characteristics

| Aspect | Value |
|--------|-------|
| Typical Query | <100ms (87ms measured) |
| Embedding Latency | ~200ms per 256 tokens |
| Indexing | Automatic (sqlite-vec) |
| Storage | ~1.2 KB per memory |

### Example Usage

```python
# Create semantic memory
mem_id = semantic.create(
    "JWT tokens should expire after 1 hour. Refresh tokens last 7 days.",
    memory_type="fact",
    project_id=1
)

# Retrieve with hybrid search
results = semantic.retrieve(
    "token expiration configuration",
    project_id=1,
    k=5
)

for result in results:
    print(f"Relevance: {result.similarity:.2f}")
    print(f"Memory: {result.memory.content}")
```

---

## Layer 3: Procedural Memory

### Purpose

Store reusable procedures and workflows learned from patterns.

### Implementation

**Key Components**:
- Procedure storage (name, steps, category)
- Pattern extraction from episodic events
- Effectiveness tracking
- Parameter binding

**Database Schema**:
```sql
CREATE TABLE procedures (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    steps JSONB NOT NULL,
    category TEXT,
    created_at TIMESTAMP,
    last_executed TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    effectiveness_score REAL DEFAULT 0.5
);

CREATE INDEX idx_procedures_category ON procedures(category);
CREATE INDEX idx_procedures_name ON procedures(name);
```

**Procedure Format**:
```json
{
    "name": "setup-database",
    "category": "devops",
    "steps": [
        {
            "action": "install_postgres",
            "version": "15",
            "timeout_seconds": 300
        },
        {
            "action": "create_database",
            "name": "app_db",
            "encoding": "UTF-8"
        },
        {
            "action": "run_migrations",
            "path": "migrations/",
            "parallel": false
        }
    ],
    "parameters": ["version", "db_name"]
}
```

### Operations

- `create_procedure()`: Store new procedure
- `execute_procedure()`: Run procedure with parameters
- `update_effectiveness()`: Track success rates

### Characteristics

| Aspect | Value |
|--------|-------|
| Procedures | 101 current (from migration) |
| Avg Steps | 5-10 per procedure |
| Execution Speed | ~100-500ms depending on steps |
| Success Rate Tracking | Per-procedure metrics |

### Example Usage

```python
# Create procedure
proc_id = procedural.create_procedure(
    name="api-testing",
    steps=[
        {"action": "install_dependencies", "package": "pytest"},
        {"action": "run_tests", "path": "tests/", "verbosity": "v"},
        {"action": "generate_report", "format": "html"},
    ],
    category="testing"
)

# Execute procedure
result = procedural.execute_procedure(
    "api-testing",
    parameters={"package": "pytest", "verbosity": "vv"}
)
```

---

## Layer 4: Prospective Memory

### Purpose

Track future-oriented information: tasks, goals, and event triggers.

### Implementation

**Key Components**:
- Task management with status tracking
- Goal hierarchies (parent-child relationships)
- Event-based triggers (time, event, file, memory)
- Priority management (low, medium, high, urgent)

**Database Schema**:
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority TEXT,
    goal_id INTEGER,
    created_at TIMESTAMP,
    due_at TIMESTAMP,
    triggers JSONB,
    FOREIGN KEY(goal_id) REFERENCES goals(id)
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    priority INTEGER,
    parent_id INTEGER,
    created_at TIMESTAMP,
    FOREIGN KEY(parent_id) REFERENCES goals(id)
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_goals_status ON goals(status);
```

### Trigger System

**Trigger Types**:
```json
{
    "time": "2025-11-10T14:00:00Z",
    "event": "pull_request_comment",
    "event_timeout_hours": 2,
    "file": "src/auth/",
    "memory": {"query": "security", "threshold": 0.7}
}
```

### Operations

- `create_task()`: Store task with triggers
- `list_tasks()`: Filter by status/goal
- `complete_task()`: Mark task done
- `trigger_evaluation()`: Check if triggers fire

### Characteristics

| Aspect | Value |
|--------|-------|
| Active Tasks | Variable |
| Trigger Check | <50ms per task |
| Goal Depth | Up to 5 levels typical |
| Priority Levels | 4 (low, medium, high, urgent) |

### Example Usage

```python
# Create task with triggers
task_id = prospective.create_task(
    content="Review code review comments",
    priority="high",
    triggers={
        "event": "pull_request_comment",
        "timeout_hours": 2
    },
    goal_id=5
)

# List pending tasks
pending = prospective.list_tasks(status="pending", goal_id=5)

# Task fires automatically when trigger conditions met
```

---

## Layer 5: Knowledge Graph

### Purpose

Represent entities and their relationships as a directed graph.

### Implementation

**Key Components**:
- Entity storage (name, type, description)
- Relation storage (from, to, type)
- Graph traversal (BFS/DFS)
- Community detection (Leiden algorithm)
- Contextual observations

**Database Schema**:
```sql
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    name TEXT NOT NULL,
    entity_type TEXT,
    description TEXT,
    created_at TIMESTAMP
);

CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    from_entity_id INTEGER,
    to_entity_id INTEGER,
    relation_type TEXT,
    strength REAL DEFAULT 1.0,
    created_at TIMESTAMP,
    FOREIGN KEY(from_entity_id) REFERENCES entities(id),
    FOREIGN KEY(to_entity_id) REFERENCES entities(id)
);

CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER,
    observation TEXT,
    context JSONB,
    created_at TIMESTAMP,
    FOREIGN KEY(entity_id) REFERENCES entities(id)
);

CREATE INDEX idx_relation_from ON entity_relations(from_entity_id);
CREATE INDEX idx_relation_to ON entity_relations(to_entity_id);
```

### Relation Types

- `depends_on`: Dependency relationship
- `implements`: Implementation
- `tests`: Test coverage
- `contains`: Composition
- `relates_to`: Association
- `caused_by`: Causality

### Operations

- `create_entity()`: Add entity
- `create_relation()`: Link entities
- `find_path()`: Graph traversal
- `add_observation()`: Contextual note
- `detect_communities()`: Leiden clustering

### Characteristics

| Aspect | Value |
|--------|-------|
| Entities | Variable (0 current, init needed) |
| Relation Types | 6 standard types |
| Traversal Depth | <50ms for depth 5 |
| Community Detection | ~7s for 100+ entities |

### Example Usage

```python
# Create entities
auth_service = graph.create_entity("AuthService", "Component")
token_validator = graph.create_entity("TokenValidator", "Component")

# Create relations
graph.create_relation(auth_service, token_validator, "depends_on")

# Find paths
path = graph.find_path(from_entity_id=1, to_entity_id=10, max_depth=5)

# Add observations
graph.add_observation(
    entity_id=1,
    observation="Performance bottleneck under load >1000 RPS",
    context={"date": "2025-11-05"}
)

# Detect communities
communities = graph.detect_communities(project_id=1)
```

---

## Layer 6: Meta-Memory

### Purpose

Track knowledge about the memory system itself (quality, expertise, attention, load).

### Implementation

**Key Components**:
- Quality metrics (compression ratio, recall, consistency)
- Expertise tracking (domain-specific knowledge levels)
- Attention & salience (what's important now)
- Cognitive load monitoring (7±2 Baddeley model)

**Database Schema**:
```sql
CREATE TABLE memory_quality (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    layer TEXT,
    quality_score REAL,
    compression_ratio REAL,
    recall_rate REAL,
    consistency_rate REAL,
    measured_at TIMESTAMP
);

CREATE TABLE expertise (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    domain TEXT,
    expertise_level REAL,
    last_updated TIMESTAMP
);

CREATE TABLE attention_state (
    id INTEGER PRIMARY KEY,
    memory_id INTEGER,
    salience REAL,
    decay_rate REAL,
    active_since TIMESTAMP
);

CREATE TABLE cognitive_load (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    current_load INTEGER,
    capacity_limit INTEGER DEFAULT 7,
    measured_at TIMESTAMP
);
```

### Quality Metrics

**4-Core Metrics**:
- **Compression Ratio**: Episodic → Semantic (target 70-85%)
- **Recall Rate**: Can extract patterns correctly (target >80%)
- **Consistency**: No contradictions (target >75%)
- **Density**: Information density (meaningful vs noise)

**Cognitive Load Model** (Baddeley, 1994):
```
┌─────────────────────────────┐
│ Working Memory Capacity: 7±2│
├─────────────────────────────┤
│ 0-2 items:   Idle state    │
│ 2-4 items:   Optimal zone  │ ← Target operating range
│ 5-6 items:   Caution zone  │ → Trigger consolidation
│ 7+ items:    Overflow risk │ → Emergency consolidation
└─────────────────────────────┘
```

### Operations

- `measure_quality()`: Compute metrics
- `get_expertise()`: Domain knowledge levels
- `set_attention()`: Mark important items
- `check_cognitive_load()`: Current load + threshold
- `auto_consolidate()`: Trigger when >6 items

### Characteristics

| Aspect | Value |
|--------|-------|
| Quality Measurement | <100ms |
| Expertise Domains | Variable |
| Cognitive Load Capacity | 7 items (Baddeley) |
| Auto-Consolidation | Triggers at 6/7 items |

### Example Usage

```python
# Measure quality
quality = meta.measure_quality(project_id=1)
print(f"Quality: {quality['overall_score']:.2f}")

# Check expertise
expertise = meta.get_expertise(domain="authentication", project_id=1)
print(f"Auth expertise: {expertise:.2f}/1.0")

# Monitor cognitive load
load = meta.check_cognitive_load(project_id=1)
if load["current"] >= 6:
    print("WARNING: Consolidation needed")
```

---

## Layer 7: Consolidation

### Purpose

Sleep-like processing that transforms episodic events into semantic memories and discovers patterns.

### Implementation

**Key Components**:
- Dual-process reasoning (System 1 + System 2)
- Event clustering (temporal + semantic)
- Pattern extraction (statistical + LLM)
- Quality validation

**Dual-Process Model**:

```
System 1 (Fast - <100ms):
├─ Statistical clustering
├─ Frequency-based patterns
├─ Heuristic weighting
└─ Always runs (baseline)

System 2 (Slow - 1-5s):
├─ LLM extended thinking
├─ Semantic validation
├─ Confidence-based check
└─ Triggered when uncertainty >0.5
```

### Consolidation Strategies

1. **Speed** (100-200ms): System 1 only, optimized for throughput
2. **Balanced** (500-1000ms): 80% System 1 + 20% System 2
3. **Quality** (2-5s): Full System 2 validation
4. **Minimal** (<50ms): Basic clustering only
5. **Custom**: User-defined thresholds

### Operations

- `run_consolidation()`: Full cycle
- `extract_patterns()`: Find recurring patterns
- `cluster_events()`: Group similar events
- `measure_quality()`: Quality assessment

### Characteristics

| Aspect | Value |
|--------|-------|
| Events per Cycle | 100-1000 typical |
| Compression | 70-85% episodic → semantic |
| Duration | <5s target (5000 events) |
| Patterns Extracted | 5-20 per consolidation |

### Example Usage

```python
# Run consolidation with balanced strategy
result = consolidation.run_consolidation(
    project_id=1,
    strategy="balanced",
    max_events=500
)

# Extract patterns
patterns = consolidation.extract_patterns(
    min_frequency=3,
    confidence_threshold=0.7
)

# Measure consolidation quality
quality = consolidation.measure_quality()
print(f"Compression: {quality['compression_ratio']:.1%}")
print(f"Recall: {quality['recall_rate']:.1%}")
```

---

## Layer 8: Supporting Systems

### 8A: RAG (Retrieval Augmented Generation)

**Purpose**: Intelligent retrieval with multiple strategies.

**Components**:
- Reflective RAG: Iterative with LLM critique
- HyDE: Hypothetical document embeddings
- Reranking: LLM-based result ranking
- Query transformation: Refinement for context

**Strategy Auto-Selection**:
```
if ambiguous_query(query):           → HyDE
elif references_context(query):      → QueryTransform
elif temporal_reasoning(query):      → Reflective
else:                                → LLMReranking
```

**Example**:
```python
results = rag.retrieve(
    "What changed in error handling?",  # Temporal → Reflective
    project_id=1,
    strategy="auto"
)
```

### 8B: Planning & Verification

**Purpose**: Comprehensive plan validation and adaptive replanning.

**Components**:
- Validation (3 levels: structure, feasibility, rules)
- Q* Formal Verification (5 properties: safety, liveness, completeness, feasibility, correctness)
- Scenario Simulation (5 scenarios: best, worst, likely, critical path, black swan)
- Adaptive Replanning (5 strategies: parallelization, compression, reordering, escalation, deferral)

**Q* Properties**:
```
Hard Properties (SMT Solver):
├─ Optimality: Minimize resources
└─ Completeness: All requirements covered

Soft Properties (LLM):
├─ Consistency: No conflicts
├─ Soundness: Valid assumptions
└─ Minimality: No redundancy

Score = Hard (60%) + Soft (40%)
```

**Example**:
```python
result = planning.validate_plan(plan, strict=True)
props = planning.verify_plan_properties(plan)
sims = planning.simulate_plan(plan)
```

### 8C: Zettelkasten (Versioning & Evolution)

**Purpose**: Memory versioning with Luhmann numbering hierarchies.

**Components**:
- Version tracking (SHA256 hashing)
- Hierarchical indexing (Luhmann numbers: 1.2.3)
- Attribute computation (importance, evolution stage, tags)
- Evolution tracking (nascent → developing → mature → stable)

**Example**:
```python
# Create version
v = zettel.create_memory_version(memory_id=42, content="Updated")

# Create hierarchy
root = zettel.create_hierarchical_index(project_id=1, label="Auth")
child = zettel.create_hierarchical_index(
    project_id=1,
    parent_id="1",
    label="JWT"
)

# Compute attributes
attrs = zettel.compute_memory_attributes(42)
```

### 8D: GraphRAG (Community Detection)

**Purpose**: Multi-level knowledge graph analysis.

**Components**:
- Leiden clustering (better than Louvain)
- Multi-level queries (granular/intermediate/global)
- Bridge entity detection (cross-cutting concerns)
- Connectivity analysis

**Levels**:
```
Level 0 (Granular):   Individual relationships
Level 1 (Intermediate): Subsystem components
Level 2 (Global):      System-wide overview
```

**Example**:
```python
communities = graphrag.detect_graph_communities(project_id=1)
bridges = graphrag.find_bridge_entities(project_id=1, threshold=3)
query_result = graphrag.query_communities_by_level(
    project_id=1,
    query="authentication",
    level=0
)
```

---

## Data Flow

### Complete Memory Lifecycle

```
1. EVENT OCCURS
   ↓
2. EPISODIC RECORDING (Layer 1)
   - Timestamp added
   - Context captured
   - Bayesian surprise calculated
   - Working memory buffer updated
   ↓
3. WORKING MEMORY MANAGEMENT (Layers 1+6)
   - Item added to 7-item buffer
   - Oldest items decay (~4 hours)
   - If >6 items: Trigger consolidation
   ↓
4. SEMANTIC ENRICHMENT (Layers 2+5)
   - Embed event content (1,536 dims)
   - Auto-link to knowledge graph entities
   - Update relation strength
   ↓
5. CONSOLIDATION (Layer 7) [Every session or >100 events]
   - Cluster episodic events (temporal + semantic)
   - System 1: Fast heuristics (~100ms)
   - System 2: LLM validation if uncertainty >0.5 (~1-5s)
   - Extract patterns (frequency, causality)
   ↓
6. PATTERN EXTRACTION (Layers 3+5)
   - Convert patterns → Procedures
   - Update Knowledge Graph
   - Compute procedural effectiveness
   ↓
7. META-LEARNING (Layer 6)
   - Measure consolidation quality
   - Update domain expertise scores
   - Detect knowledge gaps
   ↓
8. RETRIEVAL (Layer 8: RAG)
   - User query arrives
   - Strategy auto-selected
   - Retrieve from all layers
   - Rank and return results
```

### Cross-Layer Queries

Example: "How do we handle JWT refresh tokens?"

```
1. RAG Strategy Selected: Reflective (iterative search)
   ↓
2. Iteration 1:
   - Query episodic events (Layer 1)
   - Query semantic (Layer 2) → "refresh tokens"
   - Query procedures (Layer 3) → "token rotation"
   - Query graph (Layer 5) → "JWT" entities
   ↓
3. LLM Critique: "Missing refresh mechanism details"
   ↓
4. Iteration 2 (Refined Query):
   - Search "JWT refresh token rotation implementation"
   - Find more specific procedures
   - Link related entities
   ↓
5. LLM Critique: "Complete answer found"
   ↓
6. Results Returned:
   - Top semantic memories
   - Applicable procedures
   - Related entities
   - Metadata on iterations (2 total)
```

---

## Performance Architecture

### Latency Targets

```
Operation                    Target    Typical   Architecture
────────────────────────────────────────────────────────────
Record event                 <5ms      2ms       Direct insert
Retrieve semantic             <100ms    87ms      Hybrid search
Graph traversal (depth 5)     <50ms     12ms      Indexed queries
Validate plan                 <2s       1.2s      3-level check
Simulate plan (5 scenarios)   <5s       3.8s      Parallel simulation
Consolidation (100 events)    <500ms    150ms     System 1 heuristics
Community detection (100 ents)<10s      7.2s      Leiden algorithm
Reflective RAG (3 iter)       <3s       2.1s      Iterative critique
```

### Caching Strategy

```
┌─────────────────────────────────────────────┐
│ Cache Hierarchy (TTL)                       │
├─────────────────────────────────────────────┤
│ L1: Memory Vectors (1 hour)                 │
│    - Pre-computed embeddings
│    - Hit rate: 70-80%
│
│ L2: Search Results (30 min)                 │
│    - Recent query results
│    - Hit rate: 40-60%
│
│ L3: Graph Traversal (5 min)                 │
│    - Path caches
│    - Hit rate: 20-40%
│
│ L4: Procedure Steps (1 hour)                │
│    - Compiled procedure bytecode
│    - Hit rate: 60-80%
│
│ Miss: Database query (5-100ms)              │
└─────────────────────────────────────────────┘
```

### Database Optimization

```
SQLite Configuration:
├─ journal_mode = WAL (Write-Ahead Logging)
├─ synchronous = NORMAL
├─ cache_size = 10000 pages (10MB)
├─ temp_store = MEMORY
├─ mmap_size = 30000000 (memory-mapped I/O)
└─ Indices on:
   ├─ episodic_events(project_id, created_at)
   ├─ semantic_memories(project_id, created_at)
   ├─ entity_relations(from_entity_id, to_entity_id)
   └─ procedures(category, name)
```

### Scaling Characteristics

**Single Machine (SQLite)**:
- Records: Up to 1M
- Database Size: Up to 1GB
- QPS: 100-200 per second
- Consolidation: 10K events/hour

**Distributed** (Future):
- Read replicas for search
- Centralized coordinator for consolidation
- Distributed graph processing (Spark/Dask)

---

## References

- **Performance Tuning**: [PERFORMANCE_TUNING.md](PERFORMANCE_TUNING.md)
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Development Guide**: [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **Scientific Papers**:
  - Baddeley, A. (1994). "Working Memory: The Interface between Memory and Cognition"
  - Squire, L. (2004). "Memory systems of the brain: A brief history and current perspective"
  - Tulving, E. (2002). "Episodic memory and common sense"

