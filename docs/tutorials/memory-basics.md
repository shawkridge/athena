# Understanding Athena's 8 Memory Layers

Deep dive into each layer of Athena's memory system.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│   MCP Interface (Tools & Operations)    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 8: Supporting Infrastructure      │
│ (RAG, Planning, Zettelkasten, GraphRAG) │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 7: Consolidation                  │
│ (Sleep-like pattern extraction)         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 6: Meta-Memory                    │
│ (Quality, expertise, attention, load)   │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 5: Knowledge Graph                │
│ (Entities, relations, communities)      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 4: Prospective Memory             │
│ (Goals, tasks, triggers, planning)      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 3: Procedural Memory              │
│ (Workflows, skills, effectiveness)      │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 2: Semantic Memory                │
│ (Facts, vector + BM25 hybrid search)    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Layer 1: Episodic Memory                │
│ (Events, spatial-temporal grounding)    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ PostgreSQL (Local, async, no cloud)     │
└─────────────────────────────────────────┘
```

## Layer 1: Episodic Memory

**What it stores**: Events and experiences with full context.

**Key characteristics**:
- Temporal: Includes timestamps and temporal relationships
- Spatial: Grounded in file paths and locations
- Contextual: Rich metadata and tags
- Complete: Nothing is summarized or lost

**When to use**:
- Recording what happened
- Learning from experience
- Temporal reasoning

**Example**:
```python
from athena.episodic.models import EpisodicEvent
from datetime import datetime

event = EpisodicEvent(
    title="Debugged authentication flow",
    description="Found race condition in token validation",
    timestamp=datetime.now(),
    file_path="src/auth/token.py",
    line_numbers="45-50",
    tags=["debugging", "auth", "bug-fix"],
    source_context="Session 23",
)
```

**Storage capacity**: 8,000+ events (currently 8,128 in production)

**Strengths**:
- Complete information preserved
- Temporal relationships captured
- Easy to drill down into details

**Limitations**:
- Raw data is redundant
- Doesn't scale to millions of events
- Hard to find patterns in raw events

---

## Layer 2: Semantic Memory

**What it stores**: Facts, knowledge, and concepts extracted from events.

**Key characteristics**:
- Vector embeddings (semantic similarity)
- BM25 indexing (keyword search)
- Importance scores
- Domain-tagged

**When to use**:
- Storing facts you've learned
- Finding related knowledge
- Building knowledge bases

**Example**:
```python
from athena.semantic.models import SemanticMemory

memory = SemanticMemory(
    content="Python GIL prevents true multithreading in CPU-bound tasks",
    domain="python_concurrency",
    importance=0.85,
    source_event_id=123,
    created_from="Session 23",
)
```

**Search mechanisms**:
- **Semantic search**: Find similar meaning (`similarity > 0.7`)
- **Keyword search**: Find exact matches (`BM25`)
- **Hybrid**: Combine both for best results

**Example search**:
```python
# Find all knowledge about Python concurrency
results = semantic_store.search(
    query="threading limitations",
    domain="python_concurrency",
    limit=5,
)
```

**Storage capacity**: Unlimited (vectors indexed efficiently)

**Strengths**:
- Efficient storage (facts, not events)
- Powerful search (semantic + keyword)
- Scales to millions of facts

**Limitations**:
- Information is summarized (some detail lost)
- Requires good embeddings
- Less temporal context

---

## Layer 3: Procedural Memory

**What it stores**: Skills, workflows, and techniques for accomplishing tasks.

**Key characteristics**:
- Step-by-step procedures
- Effectiveness metrics
- Reusable across contexts
- Learned from episodic events

**When to use**:
- Documenting workflows
- Building automation
- Teaching patterns

**Example**:
```python
from athena.procedural.models import Procedure

procedure = Procedure(
    name="Debug Python race condition",
    description="Steps to identify and fix threading bugs",
    steps=[
        "Enable concurrent.futures.ThreadPoolExecutor logging",
        "Reproduce the condition with stress test",
        "Add lock around critical section",
        "Validate with repeated test runs",
    ],
    domain="debugging",
    effectiveness_score=0.92,  # Success rate
    times_executed=15,
)
```

**How procedures are learned**:
1. Extract from episodic events (clustering similar events)
2. Validate that steps make sense
3. Track success rate
4. Update on new evidence

**Storage**: 101 procedures currently extracted

**Strengths**:
- Reusable knowledge
- Generalizable patterns
- Improves with practice

**Limitations**:
- Requires enough examples
- May not capture edge cases
- Needs validation

---

## Layer 4: Prospective Memory

**What it stores**: Goals, tasks, and intentions about the future.

**Key characteristics**:
- Hierarchical (goals contain tasks)
- Time-aware (deadlines, triggers)
- Status tracking
- Related to knowledge

**When to use**:
- Planning projects
- Tracking goals
- Creating reminders

**Example**:
```python
from athena.prospective.models import Goal, Task

goal = Goal(
    title="Become expert in distributed systems",
    description="Deep understanding of consensus, RPC, state machines",
    priority=1,  # 0-1, higher is more important
    deadline=None,  # Optional
)

task = Task(
    title="Study Raft consensus algorithm",
    goal_id=goal.id,
    priority=1,
    status="in_progress",
    due_date=None,
)
```

**Features**:
- **Time-based triggers**: "Check on this next Monday"
- **Event-based triggers**: "When you write documentation"
- **File-based triggers**: "When this file changes"

**Storage**: Currently 200+ active goals and tasks

**Strengths**:
- Supports planning
- Automated reminders
- Tracks progress

**Limitations**:
- Requires explicit creation
- Needs manual updates
- Can become cluttered

---

## Layer 5: Knowledge Graph

**What it stores**: Entities, relationships, and communities of concepts.

**Key characteristics**:
- Nodes: Entities (concepts, people, projects)
- Edges: Relationships between entities
- Communities: Natural groupings (Leiden algorithm)
- Observations: Context-specific information

**When to use**:
- Mapping concept relationships
- Finding related domains
- Building taxonomies

**Example**:
```python
from athena.graph.models import Entity, Relation

python = Entity(name="Python", type="programming_language")
concurrency = Entity(name="Concurrency", type="concept")

relation = Relation(
    source_entity=python,
    target_entity=concurrency,
    relation_type="has_feature",
    strength=0.9,
)

# Find all related concepts
python_concepts = graph_store.get_neighbors(python)
```

**Community Detection**:
```python
# Find natural groupings of concepts
communities = graph_store.detect_communities()
for community in communities:
    print(f"Community {community.id}: {community.entities}")
```

**Storage**: Growing as new entities discovered

**Strengths**:
- Captures relationships
- Finds natural clusters
- Enables inference

**Limitations**:
- Requires entity linking
- Maintenance overhead
- Graph queries slower than keyword search

---

## Layer 6: Meta-Memory

**What it stores**: Quality metrics about the memory system itself.

**Key characteristics**:
- Compression: How much data reduced
- Recall: Accuracy of retrieval
- Consistency: Contradiction detection
- Expertise: Domain knowledge tracking
- Attention: Salience management (7±2 focus items)
- Cognitive load: Working memory limits

**When to use**:
- System introspection
- Quality monitoring
- Resource allocation

**Example**:
```python
from athena.meta.quality import QualityMetrics

quality = QualityMetrics(
    memory_id=123,
    compression_ratio=0.85,  # Reduced by 85%
    recall_accuracy=0.92,    # Retrieved correctly 92% of time
    consistency_score=0.98,  # No contradictions
)
```

**Key metrics**:
| Metric | Purpose | Target |
|--------|---------|--------|
| Compression | How efficiently stored | >80% reduction |
| Recall | How often retrieved correctly | >90% accuracy |
| Consistency | Contradiction-free | >95% |
| Expertise | Domain mastery | Per-domain |
| Salience | Attention worthiness | Top 7±2 items |
| Cognitive load | Working memory usage | <7 items |

**Storage**: Metadata for all memories

**Strengths**:
- System introspection
- Quality monitoring
- Adaptive behavior

**Limitations**:
- Requires metrics collection
- Computation overhead
- Interpretation challenges

---

## Layer 7: Consolidation

**What it stores**: Nothing directly - it *transforms* episodic events into semantic knowledge.

**Key characteristics**:
- Dual-process: System 1 (fast) + System 2 (slow)
- Temporal clustering: Groups related events
- Pattern extraction: Identifies recurring patterns
- LLM validation: Quality assurance

**How it works**:

```
Episodic Events
    ↓
[System 1 - Fast, ~100ms]
- Statistical clustering (group similar events)
- Heuristic extraction (identify patterns)
    ↓
[Uncertainty check]
- High confidence? → Save to Semantic
- Low confidence? → Go to System 2
    ↓
[System 2 - Slow, ~1s per event]
- LLM validation and refinement
- Quality improvement
    ↓
Semantic Memories
```

**Example**:
```python
from athena.consolidation.consolidator import Consolidator

consolidator = Consolidator(db)

# Extract patterns from recent events
patterns = consolidator.consolidate(
    strategy="balanced",  # or "speed", "quality"
    days_back=7,
)

print(f"Consolidated {len(patterns)} new semantic memories")
```

**Strategies**:
- **Balanced**: 70% System 1, 30% System 2 (good for most cases)
- **Speed**: 100% System 1, no LLM (fast, lower quality)
- **Quality**: 50% System 1, 50% System 2 (slower, best quality)

**Storage**: Updates semantic memory layer

**Strengths**:
- Sleep-like learning
- Efficient compression
- Quality assurance via LLM

**Limitations**:
- Requires critical mass of events
- LLM validation is slow
- May miss subtle patterns

---

## Layer 8: Supporting Infrastructure

**What it stores**: Advanced retrieval and planning tools.

### 8a. RAG (Retrieval-Augmented Generation)

Advanced retrieval strategies:

- **HyDE** (Hypothetical Document Embeddings): Generate hypothetical answers first
- **Reranking**: Re-score results for relevance
- **Reflective search**: Self-improve queries
- **Query transformation**: Expand or rephrase queries

**Example**:
```python
from athena.rag.manager import RAGManager

rag = RAGManager(db)

# Use advanced retrieval
results = rag.retrieve(
    query="How do I optimize Python code?",
    strategy="hyde",  # Generate hypotheticals first
    limit=5,
)
```

### 8b. Planning

Advanced planning capabilities:

- **Decomposition**: Break goals into tasks
- **Formal verification**: Q* pattern validation
- **Scenario simulation**: 5-scenario stress testing
- **Adaptive replanning**: Auto-adjust on failure

**Example**:
```python
from athena.planning.validator import PlanValidator

validator = PlanValidator(db)

# Verify plan quality
is_valid = validator.verify(
    plan="Implement OAuth2 authentication",
    check_properties=[
        "optimality",
        "completeness",
        "consistency",
        "soundness",
        "minimality",
    ],
)
```

### 8c. Zettelkasten

Hierarchical note-taking and association:

- Bidirectional links between notes
- Hierarchical indexing (Luhmann method)
- Hebbian learning (reinforce frequently used connections)
- Version history

**Example**:
```python
from athena.associations.zettelkasten import Zettelkasten

zettel = Zettelkasten(db)

# Create interconnected notes
note1_id = zettel.create_note(
    title="Python GIL",
    content="Global Interpreter Lock prevents true multithreading",
    tags=["python", "concurrency"],
)

note2_id = zettel.create_note(
    title="Threading limitations",
    content="CPU-bound tasks can't parallelize",
    tags=["python", "threading"],
)

# Link them
zettel.link_notes(note1_id, note2_id, relation="explains")
```

---

## Layer Interactions

Layers don't work in isolation. Here's a typical workflow:

```
1. Experience something    → Layer 1 (Episodic)
2. Learn from it           → Layer 7 (Consolidation)
3. Extract as fact         → Layer 2 (Semantic)
4. Build a procedure       → Layer 3 (Procedural)
5. Track as goal/task      → Layer 4 (Prospective)
6. Update relationships    → Layer 5 (Knowledge Graph)
7. Assess quality          → Layer 6 (Meta-Memory)
8. Enhance with RAG/plan   → Layer 8 (Supporting)
```

**The key innovation**: **Layer 7 (Consolidation)** is the bridge that converts raw experience (Layer 1) into structured knowledge (Layers 2-5).

---

## Performance Characteristics

| Layer | Latency | Throughput | Storage | Indexing |
|-------|---------|-----------|---------|----------|
| Episodic | <10ms | 2000+ events/sec | ~1MB per 100 events | Timestamp, tags |
| Semantic | 50-80ms | Real-time | ~1KB per memory | Vector + BM25 |
| Procedural | <10ms | Real-time | ~2KB per procedure | Domain, name |
| Prospective | <10ms | Real-time | ~1KB per goal/task | Status, deadline |
| Knowledge Graph | 30-40ms | Real-time | Grows with entities | Entity ID, relation |
| Meta-Memory | <5ms | Real-time | ~100B per metric | Memory ID |
| Consolidation | 2-5s | Once per session | Variable | Time ranges |
| RAG/Planning | 500ms-2s | On-demand | Variable | Query-specific |

---

## Best Practices

1. **Record episodic events** frequently (daily at minimum)
2. **Consolidate regularly** (weekly or after major work)
3. **Review semantic knowledge** (monthly)
4. **Update procedures** based on effectiveness
5. **Set and track goals** explicitly
6. **Monitor quality metrics** and adjust

---

## Next Steps

- [Advanced Features](./advanced-features.md) - GraphRAG, query optimization, etc.
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Technical deep dive
- [API_REFERENCE.md](../API_REFERENCE.md) - Complete tool documentation

---

**Questions?** See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
