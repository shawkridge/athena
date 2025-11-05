# Athena API Reference

Complete reference for all 127+ MCP operations across the 8 memory layers.

## Table of Contents

- [Memory Management](#memory-management)
- [Graph Operations](#graph-operations)
- [Planning & Validation](#planning--validation)
- [RAG Operations](#rag-operations)
- [Zettelkasten Evolution](#zettelkasten-evolution)
- [GraphRAG Operations](#graphrag-operations)
- [Error Handling](#error-handling)

---

## Memory Management

### Core Memory Operations

#### `recall(query, project_id, k=5, min_similarity=0.3)`

**Purpose**: Search memories across all layers using semantic similarity.

**Parameters**:
- `query` (str): Search query text
- `project_id` (int): Project scope (0 = global)
- `k` (int, default=5): Number of results to return
- `min_similarity` (float, default=0.3): Minimum relevance threshold (0-1)

**Returns**: `list[MemorySearchResult]`

**Example**:
```python
results = memory.recall(
    "authentication patterns",
    project_id=1,
    k=10,
    min_similarity=0.4
)
```

**Performance**: <100ms typical (depends on database size)

---

#### `remember(content, memory_type, tags=[], context=None)`

**Purpose**: Store a new memory in the semantic layer.

**Parameters**:
- `content` (str): Memory content
- `memory_type` (str): Type of memory ("semantic", "procedural", "fact", "pattern")
- `tags` (list[str], optional): Searchable tags
- `context` (dict, optional): Contextual metadata

**Returns**: `int` (Memory ID)

**Example**:
```python
memory_id = memory.remember(
    "JWT tokens expire after 1 hour",
    memory_type="fact",
    tags=["authentication", "security"],
    context={"project": "auth-service", "discovered": "2025-11-05"}
)
```

---

#### `forget(memory_id)`

**Purpose**: Delete a memory.

**Parameters**:
- `memory_id` (int): ID of memory to delete

**Returns**: `bool` (Success)

**Example**:
```python
success = memory.forget(memory_id=42)
```

---

### Episodic Operations

#### `record_event(content, event_type, outcome="success", context=None)`

**Purpose**: Record a timestamped event (automatic via hooks, can be manual).

**Parameters**:
- `content` (str): Event description
- `event_type` (str): "action", "decision", "error", "test_run", "file_change"
- `outcome` (str): "success", "failure", "partial", "ongoing"
- `context` (dict, optional): Event context

**Returns**: `int` (Event ID)

**Example**:
```python
event_id = episodic.record_event(
    "Implemented JWT refresh token rotation",
    event_type="action",
    outcome="success",
    context={"file": "auth.py", "lines": 42}
)
```

---

#### `get_events(days=7, event_type=None, project_id=None)`

**Purpose**: Retrieve events from a time window.

**Parameters**:
- `days` (int, default=7): Days to look back
- `event_type` (str, optional): Filter by type
- `project_id` (int, optional): Filter by project

**Returns**: `list[EpisodicEvent]`

**Example**:
```python
recent_errors = episodic.get_events(
    days=1,
    event_type="error",
    project_id=1
)
```

---

### Semantic Operations

#### `create(content, memory_type="semantic", project_id=1)`

**Purpose**: Create semantic memory with vector embedding.

**Parameters**:
- `content` (str): Memory content to embed
- `memory_type` (str): Type of semantic memory
- `project_id` (int): Project scope

**Returns**: `int` (Memory ID)

**Example**:
```python
mem_id = semantic.create(
    "REST API design patterns: resource-oriented architecture",
    project_id=1
)
```

---

#### `retrieve(query, project_id=1, k=5)`

**Purpose**: Retrieve semantically similar memories using hybrid search.

**Parameters**:
- `query` (str): Search query
- `project_id` (int): Project scope
- `k` (int): Number of results

**Returns**: `list[MemorySearchResult]`

**Strategy**: Hybrid BM25 + vector search with recency weighting

**Example**:
```python
results = semantic.retrieve("database optimization", project_id=1, k=10)
for result in results:
    print(f"{result.memory.content} (score: {result.similarity:.2f})")
```

---

### Procedural Operations

#### `create_procedure(name, steps, category, description="")`

**Purpose**: Store reusable procedural workflow.

**Parameters**:
- `name` (str): Procedure identifier
- `steps` (list[dict]): Ordered execution steps
- `category` (str): Procedure category
- `description` (str): Human-readable description

**Returns**: `int` (Procedure ID)

**Example**:
```python
proc_id = procedural.create_procedure(
    name="setup-database",
    steps=[
        {"action": "install_postgres", "version": "15"},
        {"action": "create_database", "name": "app_db"},
        {"action": "run_migrations", "path": "migrations/"},
    ],
    category="devops",
    description="Initialize PostgreSQL database for new environment"
)
```

---

#### `execute_procedure(name, parameters=None)`

**Purpose**: Execute a stored procedure.

**Parameters**:
- `name` (str): Procedure name
- `parameters` (dict, optional): Variable bindings

**Returns**: `dict` (Execution result)

**Example**:
```python
result = procedural.execute_procedure(
    "setup-database",
    parameters={"version": "15"}
)
```

---

### Prospective Operations

#### `create_task(content, priority="medium", triggers=None, goal_id=None)`

**Purpose**: Create task with optional triggers and goal association.

**Parameters**:
- `content` (str): Task description
- `priority` (str): "low", "medium", "high", "urgent"
- `triggers` (dict, optional): Trigger conditions
- `goal_id` (int, optional): Associated goal

**Returns**: `int` (Task ID)

**Trigger Types**:
- `time`: Unix timestamp
- `event`: Event type matching
- `file`: File path matching
- `memory`: Memory recall threshold

**Example**:
```python
task_id = prospective.create_task(
    "Review code review comments",
    priority="high",
    triggers={
        "event": "pull_request_comment",
        "timeout_hours": 2
    },
    goal_id=5
)
```

---

#### `list_tasks(status="pending", goal_id=None)`

**Purpose**: List tasks by status.

**Parameters**:
- `status` (str): "pending", "in_progress", "completed", "blocked"
- `goal_id` (int, optional): Filter by goal

**Returns**: `list[Task]`

**Example**:
```python
active_tasks = prospective.list_tasks(status="in_progress")
```

---

## Graph Operations

### Entity Operations

#### `create_entity(name, entity_type, description="", project_id=1)`

**Purpose**: Create knowledge graph entity.

**Parameters**:
- `name` (str): Entity identifier
- `entity_type` (str): Type classification (Project, File, Function, etc.)
- `description` (str): Entity description
- `project_id` (int): Project scope

**Returns**: `int` (Entity ID)

**Example**:
```python
entity_id = graph.create_entity(
    name="AuthService",
    entity_type="Component",
    description="Service handling JWT authentication",
    project_id=1
)
```

---

#### `get_entity(entity_id)`

**Purpose**: Retrieve entity details.

**Parameters**:
- `entity_id` (int): Entity ID

**Returns**: `Entity`

**Example**:
```python
entity = graph.get_entity(42)
print(entity.name, entity.entity_type)
```

---

### Relation Operations

#### `create_relation(from_entity_id, to_entity_id, relation_type)`

**Purpose**: Create relationship between entities.

**Parameters**:
- `from_entity_id` (int): Source entity
- `to_entity_id` (int): Target entity
- `relation_type` (str): Relation type

**Relation Types**:
- `depends_on`: Dependency
- `implements`: Implementation
- `tests`: Test coverage
- `contains`: Composition
- `relates_to`: Association
- `caused_by`: Causality

**Returns**: `int` (Relation ID)

**Example**:
```python
rel_id = graph.create_relation(
    from_entity_id=1,  # AuthService
    to_entity_id=2,    # TokenValidator
    relation_type="depends_on"
)
```

---

#### `find_path(from_entity_id, to_entity_id, max_depth=5)`

**Purpose**: Find connection path between entities (graph traversal).

**Parameters**:
- `from_entity_id` (int): Start entity
- `to_entity_id` (int): End entity
- `max_depth` (int): Maximum traversal depth

**Returns**: `list[int]` (Entity IDs forming path, empty if none found)

**Example**:
```python
path = graph.find_path(
    from_entity_id=1,  # AuthService
    to_entity_id=10,   # Database
    max_depth=5
)
# Returns: [1, 3, 5, 8, 10] showing path through entities
```

---

### Observation Operations

#### `add_observation(entity_id, observation, context=None)`

**Purpose**: Add contextual observation to entity.

**Parameters**:
- `entity_id` (int): Target entity
- `observation` (str): Observation text
- `context` (dict, optional): Observation context

**Returns**: `int` (Observation ID)

**Example**:
```python
obs_id = graph.add_observation(
    entity_id=1,
    observation="Performance bottleneck in token validation at peak load",
    context={"date": "2025-11-05", "duration_ms": 850}
)
```

---

## Planning & Validation

### Validation Operations

#### `validate_plan(plan, strict=False)`

**Purpose**: Comprehensive 3-level plan validation.

**Parameters**:
- `plan` (dict): Plan structure with steps, resources, timeline
- `strict` (bool): Enable strict validation

**Validation Levels**:
1. **Structural**: Valid JSON, required fields present
2. **Feasibility**: Resource availability, timeline realism
3. **Rules**: Business logic, constraints, best practices

**Returns**: `dict` with validation results

**Example**:
```python
plan = {
    "steps": [
        {"action": "design", "duration_hours": 8},
        {"action": "implement", "duration_hours": 16},
        {"action": "test", "duration_hours": 4},
    ],
    "resources": {"developers": 2, "testers": 1},
    "deadline": "2025-11-15"
}

result = planning.validate_plan(plan, strict=True)
# Returns: {
#     "valid": True,
#     "score": 0.92,
#     "issues": [],
#     "warnings": ["tight timeline with 2 developers"]
# }
```

---

#### `verify_plan_properties(plan)`

**Purpose**: Formal property verification using Q* pattern.

**Parameters**:
- `plan` (dict): Plan to verify

**Properties Verified**:
1. **Optimality**: Resource minimization
2. **Completeness**: All requirements covered
3. **Consistency**: No conflicts or contradictions
4. **Soundness**: Valid assumptions and logic
5. **Minimality**: No redundant steps

**Returns**: `dict` with property scores

**Example**:
```python
properties = planning.verify_plan_properties(plan)
# Returns: {
#     "optimality": 0.85,
#     "completeness": 0.95,
#     "consistency": 1.0,
#     "soundness": 0.9,
#     "minimality": 0.88,
#     "overall_score": 0.916
# }
```

---

### Scenario Operations

#### `simulate_plan(plan, scenarios=None)`

**Purpose**: Stress-test plan under 5 execution scenarios.

**Parameters**:
- `plan` (dict): Plan to simulate
- `scenarios` (list[str], optional): Specific scenarios to run

**Scenario Types**:
- `best_case`: +25% speed, ideal conditions
- `worst_case`: -40% speed, multiple issues
- `likely_case`: -10% speed, typical challenges
- `critical_path`: Focus on bottlenecks
- `black_swan`: Unexpected events (variable)

**Returns**: `dict` with scenario results

**Example**:
```python
simulation = planning.simulate_plan(plan)
# Returns: {
#     "best_case": {"duration": "14h", "success_prob": 0.95},
#     "worst_case": {"duration": "35h", "success_prob": 0.65},
#     "likely_case": {"duration": "26h", "success_prob": 0.82},
#     "confidence_interval": "26h ±8h",
#     "recommendation": "Allocate 28 hours with 1 contingency developer"
# }
```

---

### Adaptive Replanning

#### `trigger_replanning(task_id, violation_type)`

**Purpose**: Auto-trigger replanning when assumptions violated.

**Parameters**:
- `task_id` (int): Task exceeding constraints
- `violation_type` (str): Type of violation

**Violation Types**:
- `DURATION_EXCEEDED`: >20% over estimated time
- `RESOURCE_CONSTRAINT`: Resources unavailable
- `BLOCKER_ENCOUNTERED`: Task blocked by dependency
- `ASSUMPTION_VIOLATED`: Initial assumption invalid

**Returns**: `dict` with new plan

**Replanning Strategies**:
- `parallelization`: Execute non-dependent tasks concurrently
- `compression`: Batch related tasks
- `reordering`: Topological sort optimization
- `escalation`: Add resources
- `deferral`: Move non-critical tasks

**Example**:
```python
new_plan = planning.trigger_replanning(
    task_id=5,
    violation_type="DURATION_EXCEEDED"
)
# Auto-selects strategy (e.g., parallelization)
# Returns revised plan with 15%+ improvement
```

---

## RAG Operations

### Retrieval Operations

#### `retrieve(query, project_id, strategy="auto", k=5)`

**Purpose**: Intelligent retrieval with auto-strategy selection.

**Parameters**:
- `query` (str): Search query
- `project_id` (int): Project scope
- `strategy` (str): "auto", "hyde", "reranking", "reflective", "transform"
- `k` (int): Results to return

**Strategies**:
- `auto`: Analyzes query and selects optimal strategy
- `hyde`: Hypothetical document embeddings (ambiguous queries)
- `reranking`: LLM-based result reranking (high accuracy)
- `reflective`: Iterative retrieval with critique loop
- `transform`: Query refinement for contextual references

**Returns**: `list[MemorySearchResult]`

**Example**:
```python
results = rag.retrieve(
    "What changes were made to error handling?",
    project_id=1,
    strategy="auto",  # Auto-selects "reflective" for temporal reasoning
    k=5
)
```

---

#### `retrieve_reflective(query, project_id, max_iterations=3, confidence_threshold=0.8)`

**Purpose**: Iterative retrieval with LLM critique and query refinement.

**Parameters**:
- `query` (str): Initial query
- `project_id` (int): Project scope
- `max_iterations` (int): Maximum refinement iterations
- `confidence_threshold` (float): Stop when confidence exceeds this

**Returns**: `list[MemorySearchResult]` with iteration metadata

**Example**:
```python
results = rag.retrieve_reflective(
    "JWT token expiry and refresh mechanisms",
    project_id=1,
    max_iterations=3,
    confidence_threshold=0.85
)

# Execution:
# Iteration 1: Retrieve on original query
# - LLM critique: "Query answers partially, missing refresh mechanism"
# Iteration 2: Refine query to "JWT refresh token rotation implementation"
# - LLM critique: "Complete answer found"
# Result: Returns best results after 2 iterations
```

---

### Query Transformation

#### `transform_query(query, context=None)`

**Purpose**: Refine query for better semantic matching.

**Parameters**:
- `query` (str): Original query
- `context` (dict, optional): Search context

**Returns**: `str` (Transformed query)

**Example**:
```python
transformed = rag.transform_query(
    "How did we solve the caching issue?",
    context={"recent_issues": ["performance", "caching"]}
)
# Returns: "caching performance optimization solution implementation"
```

---

## Zettelkasten Evolution

### Memory Versioning

#### `create_memory_version(memory_id, content)`

**Purpose**: Create timestamped version of memory with SHA256 hashing.

**Parameters**:
- `memory_id` (int): Memory to version
- `content` (str): New content

**Returns**: `dict` with version info

**Example**:
```python
version = zettel.create_memory_version(
    memory_id=42,
    content="Updated authentication pattern documentation"
)
# Returns: {
#     "version": 3,
#     "hash": "a7f4c2e9...",
#     "created_at": "2025-11-05T14:32:00Z",
#     "size_bytes": 245
# }
```

---

#### `get_memory_evolution_history(memory_id)`

**Purpose**: Retrieve complete version history.

**Parameters**:
- `memory_id` (int): Memory ID

**Returns**: `list[Version]`

**Example**:
```python
history = zettel.get_memory_evolution_history(42)
for version in history:
    print(f"v{version.version}: {version.created_at} (hash: {version.hash[:8]}...)")
```

---

### Attributes

#### `compute_memory_attributes(memory_id)`

**Purpose**: Compute auto-generated attributes.

**Returns**: `dict` with attributes

**Attributes**:
- `importance_score` (0-1): Based on access frequency + recency
- `evolution_stage`: nascent/developing/mature/stable
- `context_tags`: Auto-extracted topics
- `related_count`: Bidirectional links

**Example**:
```python
attrs = zettel.compute_memory_attributes(42)
# Returns: {
#     "importance_score": 0.82,
#     "evolution_stage": "mature",
#     "context_tags": ["authentication", "jwt", "security"],
#     "related_count": 7
# }
```

---

### Hierarchical Indexing

#### `create_hierarchical_index(project_id, parent_id=None, label="Untitled")`

**Purpose**: Create Luhmann-numbered index node.

**Parameters**:
- `project_id` (int): Project scope
- `parent_id` (str, optional): Parent index ID (e.g., "1.2")
- `label` (str): Human-readable label

**Returns**: `dict` with index info

**Example**:
```python
# Create root
root = zettel.create_hierarchical_index(project_id=1, label="Authentication")
# Returns: {"index_id": "1", "depth": 0}

# Create child
child = zettel.create_hierarchical_index(
    project_id=1,
    parent_id="1",
    label="JWT Tokens"
)
# Returns: {"index_id": "1.1", "depth": 1}

# Create grandchild
grandchild = zettel.create_hierarchical_index(
    project_id=1,
    parent_id="1.1",
    label="Refresh Token Rotation"
)
# Returns: {"index_id": "1.1.1", "depth": 2}
```

---

#### `assign_memory_to_index(memory_id, index_id)`

**Purpose**: Place memory in hierarchical index.

**Parameters**:
- `memory_id` (int): Memory to assign
- `index_id` (str): Target index (e.g., "1.2.3")

**Returns**: `bool` (Success)

**Example**:
```python
zettel.assign_memory_to_index(
    memory_id=42,
    index_id="1.1.1"
)
# Places memory 42 under "Refresh Token Rotation" section
```

---

## GraphRAG Operations

### Community Detection

#### `detect_graph_communities(project_id, min_community_size=2, max_iterations=100)`

**Purpose**: Detect communities using Leiden clustering algorithm.

**Parameters**:
- `project_id` (int): Project to analyze
- `min_community_size` (int): Minimum nodes per community
- `max_iterations` (int): Maximum algorithm iterations

**Returns**: `dict` with communities

**Example**:
```python
communities = graphrag.detect_graph_communities(
    project_id=1,
    min_community_size=3,
    max_iterations=100
)
# Returns: {
#     "1": {"size": 12, "density": 0.68, "entities": ["Entity1", "Entity2", ...]},
#     "2": {"size": 8, "density": 0.72, ...},
#     ...
# }
```

---

#### `query_communities_by_level(project_id, query, level=0)`

**Purpose**: Query communities at specific hierarchical level.

**Parameters**:
- `project_id` (int): Project scope
- `query` (str): Search query
- `level` (int): 0=granular, 1=intermediate, 2=global

**Returns**: `list[Community]`

**Example**:
```python
# Level 0: Granular (individual relationships)
granular = graphrag.query_communities_by_level(
    project_id=1,
    query="authentication services",
    level=0
)

# Level 1: Intermediate (subsystems)
intermediate = graphrag.query_communities_by_level(
    project_id=1,
    query="authentication services",
    level=1
)

# Level 2: Global (system overview)
global_view = graphrag.query_communities_by_level(
    project_id=1,
    query="authentication services",
    level=2
)
```

---

#### `find_bridge_entities(project_id, threshold=3)`

**Purpose**: Find entities connecting multiple communities (cross-cutting concerns).

**Parameters**:
- `project_id` (int): Project scope
- `threshold` (int): Minimum external connections

**Returns**: `list[Entity]`

**Example**:
```python
bridges = graphrag.find_bridge_entities(
    project_id=1,
    threshold=3
)
# Returns entities like "ErrorHandler" connecting
# authentication, database, and logging communities
```

---

## Error Handling

### Standard Error Response

All MCP operations return `TextContent` with standardized error format:

```
❌ Error: [Specific error message]
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `DatabaseError` | Connection failed | Check `/memory-health` |
| `EmbeddingError` | Vector embedding failed | Verify Ollama running |
| `ValidationError` | Invalid parameters | Check parameter types |
| `NotFoundError` | Resource not found | Verify resource ID exists |
| `PermissionError` | Access denied | Check project scope |

### Error Handling Pattern

```python
async def operation_handler(self, **kwargs) -> TextContent:
    try:
        # Main logic
        result = self._perform_operation(**kwargs)
        return TextContent(type="text", text=f"✓ Success: {result}")

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return TextContent(type="text", text=f"❌ Database error: {str(e)}")

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return TextContent(type="text", text=f"❌ Invalid input: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return TextContent(type="text", text=f"❌ Error: {str(e)}")
```

---

## Performance Characteristics

### Operation Latency Targets

| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| `recall()` | <100ms | 87ms | Hybrid search, 8K events |
| `retrieve()` | <100ms | 92ms | Semantic search only |
| `create_entity()` | <10ms | 3ms | Graph insert |
| `find_path()` | <50ms | 12ms | Traversal depth 5 |
| `validate_plan()` | <2s | 1.2s | 3-level validation |
| `simulate_plan()` | <5s | 3.8s | 5 scenarios |
| `detect_communities()` | <10s | 7.2s | Leiden algorithm |
| `retrieve_reflective()` | <3s | 2.1s | 2-3 iterations typical |

### Scalability

**Single Machine (Local Development)**:
- Records: Up to 1M episodic events
- Database: Up to 1GB
- QPS: 100-200 queries per second
- Consolidation: 10K events/hour

---

## Quick Reference

```python
# Memory operations
memory.recall(query, project_id=1, k=5)
memory.remember(content, memory_type="semantic")
memory.forget(memory_id)

# Graph operations
graph.create_entity(name, entity_type)
graph.create_relation(from_id, to_id, rel_type)
graph.find_path(from_id, to_id)

# Planning
planning.validate_plan(plan)
planning.verify_plan_properties(plan)
planning.simulate_plan(plan)

# RAG
rag.retrieve(query, strategy="auto")
rag.retrieve_reflective(query, max_iterations=3)

# Zettelkasten
zettel.create_memory_version(memory_id, content)
zettel.compute_memory_attributes(memory_id)

# GraphRAG
graphrag.detect_graph_communities(project_id)
graphrag.query_communities_by_level(project_id, query, level)
```

---

**Version**: 1.0
**Last Updated**: 2025-11-05
**Total Operations**: 127+
