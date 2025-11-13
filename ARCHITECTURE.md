# Athena Architecture

A comprehensive guide to the 8-layer memory system architecture.

## System Overview

Athena is built on a neuroscience-inspired 8-layer architecture where each layer handles a specific type of memory and reasoning:

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Interface                          │
│              (27 tools, 228+ operations)                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 8: Supporting Infrastructure                         │
│  • Advanced RAG (HyDE, reranking, reflective)               │
│  • Planning (Q* verification, scenario simulation)          │
│  • Zettelkasten (memory versioning, indexing)              │
│  • GraphRAG (community detection, synthesis)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 7: Consolidation (Sleep-like Pattern Extraction)    │
│  • Clustering: Events grouped by proximity                  │
│  • Extraction: Statistical pattern discovery                │
│  • Validation: LLM validation when uncertainty >0.5         │
│  • Integration: Patterns → semantic memories & procedures   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 6: Meta-Memory (Knowledge About Knowledge)           │
│  • Quality: Compression, recall, consistency metrics        │
│  • Expertise: Domain knowledge tracking                     │
│  • Attention: Salience & focus (7±2 working memory)        │
│  • Load: Cognitive load monitoring (Baddeley)              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Knowledge Graph (Semantic Structure)              │
│  • Entities: Concepts, agents, artifacts                    │
│  • Relations: Typed edges (causality, similarity, etc.)     │
│  • Observations: Contextual information                     │
│  • Communities: Leiden clustering for organization          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Prospective Memory (Goals & Tasks)               │
│  • Goals: Hierarchical objectives with milestones          │
│  • Tasks: Discrete work items with status tracking         │
│  • Triggers: Time-based, event-based, file-based          │
│  • Planning: Task decomposition and cost estimation        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Procedural Memory (Reusable Workflows)           │
│  • Procedures: 101 extracted from experience               │
│  • Versions: Semantic versioning & iteration tracking      │
│  • Effectiveness: Quality metrics per procedure            │
│  • Execution: Bind parameters and run with validation      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Semantic Memory (Knowledge Representation)        │
│  • Vector Search: Embeddings via Ollama or Claude         │
│  • BM25 Search: Keyword-based hybrid retrieval            │
│  • Compression: ~10:1 compression ratio                     │
│  • RAG: 4 strategies (HyDE, reranking, query transform)   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Episodic Memory (Event Storage)                  │
│  • Events: 8,128 timestamped incidents                     │
│  • Context: Spatial path + temporal window                 │
│  • Importance: Scoring for prioritization                  │
│  • Temporal Chains: Causality inference                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
           PostgreSQL Backend (Async Connection Pool)
```

## Layer Responsibilities

### Layer 1: Episodic Memory
**Purpose**: Store timestamped events with context

- **Event Types**: Decision, action, observation, outcome
- **Spatial Context**: File path hierarchy
- **Temporal Window**: Event causality links
- **Scoring**: Importance 0-1 based on surprise & relevance
- **Query**: Range queries, temporal chaining, context-based filtering

**Location**: `src/athena/episodic/`

### Layer 2: Semantic Memory
**Purpose**: Convert events into reusable knowledge

- **Representations**: Vector embeddings + BM25 indices
- **Search**: Hybrid semantic + keyword search
- **Compression**: ~10:1 reduction vs. raw events
- **RAG Strategies**:
  - HyDE (Hypothetical Document Embeddings)
  - Reranking (LLM-based result ranking)
  - Reflective (Query clarification)
  - Query Transform (Semantic expansion)

**Location**: `src/athena/semantic/`, `src/athena/memory/`

### Layer 3: Procedural Memory
**Purpose**: Learn and execute reusable workflows

- **Extraction**: Automatic workflow detection from event sequences
- **Storage**: 101 procedures with effectiveness tracking
- **Versioning**: Semantic versioning, iteration tracking
- **Execution**: Parameter binding, validation, error handling
- **Quality**: Usage frequency, success rate, learning rate

**Location**: `src/athena/procedural/`

### Layer 4: Prospective Memory
**Purpose**: Manage goals and tasks

- **Hierarchy**: Goals → sub-goals → tasks → milestones
- **Status**: Pending, in-progress, completed, blocked
- **Triggers**: Time-based (cron), event-based (file changes), manual
- **Planning**: Decomposition strategies, cost estimation, dependencies
- **Tracking**: Progress metrics, impediments, learnings

**Location**: `src/athena/prospective/`

### Layer 5: Knowledge Graph
**Purpose**: Semantic structure of entities and relations

- **Entities**: Concepts, agents, artifacts, code symbols
- **Relations**: Typed edges (causality, similarity, containment, etc.)
- **Observations**: Context snippets on entities
- **Communities**: Leiden algorithm for natural grouping
- **Synthesis**: GraphRAG for question answering

**Location**: `src/athena/graph/`

### Layer 6: Meta-Memory
**Purpose**: Knowledge about knowledge quality and attention

- **Quality Metrics**:
  - Compression ratio (size reduction)
  - Recall accuracy (how often remembered correctly)
  - Consistency (coherence across retrievals)

- **Expertise Tracking**: Domain-based knowledge levels

- **Attention Management**:
  - Working memory: 7±2 items in focus
  - Salience: Priority scoring
  - Focus: Active attention tracking

- **Cognitive Load**: Baddeley's model implementation

**Location**: `src/athena/meta/`

### Layer 7: Consolidation
**Purpose**: Sleep-like pattern extraction and integration

**Dual-Process Reasoning**:
- **System 1 (Fast)**: Statistical clustering <100ms
  - Event proximity clustering
  - Session boundaries
  - Temporal windows

- **System 2 (Slow)**: LLM validation when uncertainty >0.5
  - Pattern verification
  - Anomaly detection
  - Confidence refinement

**Output**:
- Semantic memories (knowledge units)
- Procedures (reusable workflows)
- Pattern facts (discovered rules)

**Location**: `src/athena/consolidation/`

### Layer 8: Supporting Infrastructure
**Purpose**: Advanced capabilities for retrieval and planning

- **RAG** (`src/athena/rag/`): Retrieval-augmented generation strategies
- **Planning** (`src/athena/planning/`): Formal verification, scenario simulation
- **Zettelkasten** (`src/athena/associations/`): Networked memory with backlinks
- **GraphRAG**: Knowledge graph-based synthesis

**Location**: `src/athena/rag/`, `src/athena/planning/`, `src/athena/associations/`

## Key Architectural Patterns

### Mixin Pattern for Handlers
The MCP server handlers are organized as domain-specific mixins for clean separation:

```python
class MemoryMCPServer(
    EpisodicHandlersMixin,
    MemoryCoreHandlersMixin,
    ProceduralHandlersMixin,
    ProspectiveHandlersMixin,
    GraphHandlersMixin,
    ConsolidationHandlersMixin,
    PlanningHandlersMixin,
    MetacognitionHandlersMixin,
    SystemHandlersMixin
):
    """MCP server with 148+ handler methods organized by domain."""
```

**Benefits**:
- 89.7% reduction in main file (12K → 1.3K lines)
- Clear responsibility boundaries
- Independent testing per domain
- Zero breaking changes (100% backward compatible)

### Layer Initialization Pattern
Each layer follows the same pattern for consistency:

```python
class [Layer]Store:
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()  # Create tables on first use

    def _init_schema(self):
        """Idempotent schema creation."""
        # CREATE TABLE IF NOT EXISTS
```

### Query Routing
The UnifiedMemoryManager routes queries to appropriate layers based on type:

```python
class QueryType:
    TEMPORAL = "temporal"      # → Episodic layer
    FACTUAL = "factual"        # → Semantic layer
    RELATIONAL = "relational"  # → Knowledge graph
    PROCEDURAL = "procedural"  # → Procedural layer
    PROSPECTIVE = "prospective"# → Prospective layer
    META = "meta"              # → Meta-memory
    PLANNING = "planning"      # → Planning layer
```

### Optional RAG Degradation
RAG components gracefully degrade if not available:

```python
try:
    from .rag import RAGManager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Later: fallback to semantic search if RAG unavailable
```

## Data Model

### Episodic Events
```python
class EpisodicEvent:
    id: int
    project_id: int
    content: str
    context: EventContext
    context_type: EventType
    session_id: str
    spatial_context: str  # File path
    importance: float     # 0-1
    tags: list[str]
    timestamp: datetime
    metadata: dict
```

### Semantic Memories
```python
class SemanticMemory:
    id: int
    project_id: int
    content: str
    embedding: vector  # Via sqlite-vec
    usefulness_score: float
    source_events: list[int]  # Episodic sources
    updated_at: datetime
    compression_ratio: float  # Size reduction
```

### Procedures
```python
class Procedure:
    id: int
    project_id: int
    name: str
    description: str
    steps: list[ProcedureStep]
    inputs: dict
    outputs: dict
    version: str  # Semantic versioning
    effectiveness: float  # Quality score
    last_used: datetime
    usage_count: int
```

### Knowledge Graph Entities
```python
class Entity:
    id: int
    project_id: int
    name: str
    entity_type: EntityType  # CONCEPT, AGENT, ARTIFACT, etc.
    observations: list[Observation]
    relations: list[Relation]
    created_at: datetime
    metadata: dict
```

## Performance Characteristics

| Operation | Target | Typical | Bottleneck |
|-----------|--------|---------|------------|
| Episodic store | 2000+/sec | 1500-2000 | PostgreSQL insert |
| Semantic search | <100ms | 50-80ms | Embedding similarity |
| Graph query | <50ms | 30-40ms | Relation traversal |
| Consolidation | 5s/1000 | 2-3s | LLM validation |
| Working memory | <10ms | 5ms | Cache hit |

## Database Schema

**Primary Tables**:
- `episodic_events` - Layer 1 raw events
- `semantic_memories` - Layer 2 knowledge units
- `procedures` - Layer 3 workflows
- `tasks` - Layer 4 task management
- `entities`, `entity_relations` - Layer 5 graph
- `meta_memories` - Layer 6 quality tracking
- `consolidation_runs` - Layer 7 integration logs

**Infrastructure**:
- PostgreSQL 12+ with async/await support
- Connection pool (2-10 connections)
- Parameterized queries (SQL injection safe)
- Transactions with rollback support

## Integration Points

### With Code Understanding
- File paths → spatial context
- Code symbols → entities in knowledge graph
- Dependencies → relations

### With Task Management
- Code changes → prospective triggers
- Completion → consolidation input

### With AI Agents
- Query → semantic search
- Recall → filtered by recency & importance
- Learn → consolidation + procedural extraction

## Future Enhancements

**Phase 9 (Optional)**:
- Attention budgets in Layer 6
- 7±2 working memory constraints
- Advanced reflection (metacognition)

**Beyond**:
- Multi-agent coordination
- Cross-project memory synthesis
- Temporal abstraction hierarchies

---

**Architecture Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Production-ready (95% complete)
