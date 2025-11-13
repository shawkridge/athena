# API Reference

Complete reference for Athena's 27 MCP tools and 228+ operations.

## Table of Contents

- [Core Memory Operations](#core-memory-operations)
- [Episodic Memory](#episodic-memory)
- [Semantic Memory](#semantic-memory)
- [Procedural Memory](#procedural-memory)
- [Prospective Memory](#prospective-memory)
- [Knowledge Graph](#knowledge-graph)
- [Meta-Memory](#meta-memory)
- [Consolidation](#consolidation)
- [Planning & Validation](#planning--validation)
- [System Operations](#system-operations)

---

## Core Memory Operations

### remember

Store a memory or event in the system.

```python
remember(
    content: str,
    domain: str = None,
    importance: float = 0.5,
    tags: List[str] = None,
) -> int
```

**Parameters:**
- `content` (str, required): Memory content
- `domain` (str): Topic/category for the memory
- `importance` (float, 0-1): Importance score
- `tags` (list): Tags for categorization

**Returns:**
- Memory ID (int)

**Example:**
```python
memory_id = remember(
    content="Athena has 8 memory layers",
    domain="architecture",
    importance=0.9,
    tags=["structure", "learning"]
)
```

### recall

Retrieve memories matching a query.

```python
recall(
    query: str,
    limit: int = 10,
    domain: str = None,
    min_importance: float = 0.0,
) -> List[Memory]
```

**Parameters:**
- `query` (str, required): Search query
- `limit` (int): Maximum results to return
- `domain` (str): Filter by domain
- `min_importance` (float): Minimum importance threshold

**Returns:**
- List of Memory objects

**Example:**
```python
memories = recall(
    query="memory layers",
    limit=5,
    domain="architecture"
)
```

### forget

Remove a memory from the system.

```python
forget(memory_id: int) -> bool
```

**Parameters:**
- `memory_id` (int, required): Memory to delete

**Returns:**
- True if successful, False otherwise

**Example:**
```python
success = forget(memory_id=123)
```

### list_memories

List all memories with optional filtering.

```python
list_memories(
    domain: str = None,
    min_importance: float = 0.0,
    limit: int = 100,
    offset: int = 0,
) -> List[Memory]
```

**Parameters:**
- `domain` (str): Filter by domain
- `min_importance` (float): Minimum importance
- `limit` (int): Maximum results
- `offset` (int): Pagination offset

**Returns:**
- List of Memory objects

---

## Episodic Memory

Layer 1: Events and experiences with timestamps.

### store_event

Store an episodic event.

```python
store_event(
    title: str,
    description: str = None,
    tags: List[str] = None,
    source_context: str = None,
) -> int
```

**Parameters:**
- `title` (str, required): Event title
- `description` (str): Detailed description
- `tags` (list): Event tags
- `source_context` (str): Where did this come from?

**Returns:**
- Event ID (int)

**Example:**
```python
event_id = store_event(
    title="Learned about consolidation",
    description="Studied sleep-like pattern extraction",
    tags=["learning", "consolidation"],
    source_context="Session 5"
)
```

### get_event

Retrieve a specific event by ID.

```python
get_event(event_id: int) -> Optional[Event]
```

**Parameters:**
- `event_id` (int, required): Event ID to retrieve

**Returns:**
- Event object or None if not found

### search_events_by_tag

Find events by tag.

```python
search_events_by_tag(
    tag: str,
    limit: int = 10,
) -> List[Event]
```

**Parameters:**
- `tag` (str, required): Tag to search for
- `limit` (int): Maximum results

**Returns:**
- List of Event objects

### search_events_by_time

Find events by time range.

```python
search_events_by_time(
    since: datetime = None,
    until: datetime = None,
    limit: int = 10,
) -> List[Event]
```

**Parameters:**
- `since` (datetime): Start of time range
- `until` (datetime): End of time range
- `limit` (int): Maximum results

**Returns:**
- List of Event objects in time range

---

## Semantic Memory

Layer 2: Facts and knowledge (vector + BM25 search).

### store_memory

Store semantic knowledge.

```python
store_memory(
    content: str,
    domain: str = None,
    importance: float = 0.5,
) -> int
```

**Parameters:**
- `content` (str, required): Knowledge content
- `domain` (str): Topic category
- `importance` (float, 0-1): Importance score

**Returns:**
- Memory ID (int)

### search_semantic

Search semantic memory with hybrid strategy.

```python
search_semantic(
    query: str,
    domain: str = None,
    limit: int = 10,
    strategy: str = "hybrid",  # hybrid, vector, keyword
) -> List[Memory]
```

**Parameters:**
- `query` (str, required): Search query
- `domain` (str): Filter by domain
- `limit` (int): Maximum results
- `strategy` (str): Search strategy

**Returns:**
- List of Memory objects ranked by relevance

**Example:**
```python
results = search_semantic(
    query="consolidation patterns",
    strategy="hybrid",
    limit=5
)
```

### update_importance

Update memory importance score.

```python
update_importance(
    memory_id: int,
    importance: float,
) -> bool
```

**Parameters:**
- `memory_id` (int, required): Memory to update
- `importance` (float, 0-1): New importance score

**Returns:**
- True if successful

---

## Procedural Memory

Layer 3: Skills, workflows, and procedures.

### store_procedure

Store a reusable workflow.

```python
store_procedure(
    name: str,
    steps: List[str],
    domain: str = None,
    effectiveness: float = 0.5,
) -> int
```

**Parameters:**
- `name` (str, required): Procedure name
- `steps` (list, required): Step-by-step instructions
- `domain` (str): Category
- `effectiveness` (float, 0-1): Success rate

**Returns:**
- Procedure ID (int)

### get_procedure

Retrieve a procedure by ID.

```python
get_procedure(procedure_id: int) -> Optional[Procedure]
```

**Parameters:**
- `procedure_id` (int, required): Procedure to retrieve

**Returns:**
- Procedure object or None

### search_procedures

Find procedures by name or domain.

```python
search_procedures(
    query: str,
    domain: str = None,
    limit: int = 10,
) -> List[Procedure]
```

**Parameters:**
- `query` (str, required): Search query
- `domain` (str): Filter by domain
- `limit` (int): Maximum results

**Returns:**
- List of Procedure objects

### execute_procedure

Execute a stored procedure.

```python
execute_procedure(
    procedure_id: int,
    context: Dict[str, Any] = None,
) -> Dict[str, Any]
```

**Parameters:**
- `procedure_id` (int, required): Procedure to execute
- `context` (dict): Variables for procedure

**Returns:**
- Execution result

---

## Prospective Memory

Layer 4: Goals, tasks, and planning.

### create_goal

Create a goal.

```python
create_goal(
    title: str,
    description: str = None,
    priority: float = 0.5,  # 0-1
    deadline: datetime = None,
) -> int
```

**Parameters:**
- `title` (str, required): Goal title
- `description` (str): Goal description
- `priority` (float, 0-1): Priority level
- `deadline` (datetime): Target deadline

**Returns:**
- Goal ID (int)

### create_task

Create a task for a goal.

```python
create_task(
    title: str,
    goal_id: int = None,
    priority: float = 0.5,
    due_date: datetime = None,
) -> int
```

**Parameters:**
- `title` (str, required): Task title
- `goal_id` (int): Parent goal ID
- `priority` (float, 0-1): Priority level
- `due_date` (datetime): Due date

**Returns:**
- Task ID (int)

### complete_task

Mark a task as complete.

```python
complete_task(task_id: int) -> bool
```

**Parameters:**
- `task_id` (int, required): Task to complete

**Returns:**
- True if successful

### list_tasks

List all tasks with filtering.

```python
list_tasks(
    goal_id: int = None,
    status: str = None,  # pending, in_progress, complete
    limit: int = 100,
) -> List[Task]
```

**Parameters:**
- `goal_id` (int): Filter by goal
- `status` (str): Filter by status
- `limit` (int): Maximum results

**Returns:**
- List of Task objects

---

## Knowledge Graph

Layer 5: Entities, relations, and communities.

### create_entity

Create an entity in the knowledge graph.

```python
create_entity(
    name: str,
    entity_type: str,
    metadata: Dict[str, Any] = None,
) -> int
```

**Parameters:**
- `name` (str, required): Entity name
- `entity_type` (str, required): Entity type
- `metadata` (dict): Additional information

**Returns:**
- Entity ID (int)

### create_relation

Create a relationship between entities.

```python
create_relation(
    source_id: int,
    target_id: int,
    relation_type: str,
    strength: float = 0.5,
) -> int
```

**Parameters:**
- `source_id` (int, required): Source entity
- `target_id` (int, required): Target entity
- `relation_type` (str, required): Relationship type
- `strength` (float, 0-1): Relationship strength

**Returns:**
- Relation ID (int)

### get_neighbors

Find related entities.

```python
get_neighbors(
    entity_id: int,
    max_distance: int = 1,
    limit: int = 10,
) -> List[Entity]
```

**Parameters:**
- `entity_id` (int, required): Starting entity
- `max_distance` (int): Hops to traverse
- `limit` (int): Maximum results

**Returns:**
- List of related Entity objects

### detect_communities

Detect natural groupings in the graph.

```python
detect_communities(
    resolution: float = 1.0,
) -> List[Community]
```

**Parameters:**
- `resolution` (float): Community size (higher = more communities)

**Returns:**
- List of Community objects

---

## Meta-Memory

Layer 6: Quality tracking and expertise.

### get_quality_metrics

Get quality metrics for a memory.

```python
get_quality_metrics(memory_id: int) -> Dict[str, float]
```

**Parameters:**
- `memory_id` (int, required): Memory to analyze

**Returns:**
- Dictionary with metrics:
  - `compression`: Compression ratio (0-1)
  - `recall`: Recall accuracy (0-1)
  - `consistency`: Contradiction-free score (0-1)
  - `relevance`: Relevance to domain (0-1)

### get_expertise

Get expertise map for domains.

```python
get_expertise(
    domain: str = None,
) -> Dict[str, float]
```

**Parameters:**
- `domain` (str): Filter to specific domain

**Returns:**
- Dictionary of domain → expertise level (0-1)

### get_cognitive_load

Get current cognitive load (7±2 model).

```python
get_cognitive_load() -> Dict[str, Any]
```

**Returns:**
- Dictionary with:
  - `current_items`: Number of items in focus (max 7)
  - `attention_budget`: Available attention (0-1)
  - `overload_risk`: Risk of overload (0-1)

---

## Consolidation

Layer 7: Sleep-like pattern extraction.

### consolidate

Run consolidation cycle.

```python
consolidate(
    strategy: str = "balanced",  # balanced, speed, quality
    days_back: int = 7,
    min_cluster_size: int = 2,
) -> List[SemanticMemory]
```

**Parameters:**
- `strategy` (str): Consolidation strategy
- `days_back` (int): How far back to look
- `min_cluster_size` (int): Minimum events per cluster

**Returns:**
- List of newly created semantic memories

**Example:**
```python
patterns = consolidate(
    strategy="quality",
    days_back=7,
)
```

### get_consolidation_stats

Get consolidation statistics.

```python
get_consolidation_stats() -> Dict[str, Any]
```

**Returns:**
- Dictionary with consolidation metrics

---

## Planning & Validation

### verify_plan

Verify a plan using Q* properties.

```python
verify_plan(
    plan: str,
    properties: List[str] = None,
) -> Dict[str, bool]
```

**Parameters:**
- `plan` (str, required): Plan description
- `properties` (list): Properties to check
  - Default: [optimality, completeness, consistency, soundness, minimality]

**Returns:**
- Dictionary of property → passes (bool)

### decompose_task

Break down a complex task.

```python
decompose_task(
    task: str,
    max_depth: int = 3,
) -> List[Dict[str, Any]]
```

**Parameters:**
- `task` (str, required): Task description
- `max_depth` (int): Maximum decomposition depth

**Returns:**
- List of subtasks with details

---

## System Operations

### get_health

Get system health status.

```python
get_health(detailed: bool = False) -> Dict[str, Any]
```

**Parameters:**
- `detailed` (bool): Include detailed diagnostics

**Returns:**
- Health status dictionary with:
  - `status`: overall status (healthy, warning, critical)
  - `memory_usage`: Current memory usage
  - `database_health`: Database status
  - `operation_latency`: Average operation time

### get_stats

Get system statistics.

```python
get_stats() -> Dict[str, Any]
```

**Returns:**
- System statistics including:
  - `total_memories`: Total stored memories
  - `total_events`: Total episodic events
  - `total_procedures`: Total procedures
  - `active_goals`: Active goals count
  - `total_entities`: Knowledge graph entities

### export_memory

Export memories to various formats.

```python
export_memory(
    memory_id: int,
    format: str = "json",  # json, csv, markdown
) -> str
```

**Parameters:**
- `memory_id` (int, required): Memory to export
- `format` (str): Export format

**Returns:**
- Exported memory as string

---

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Invalid parameters | Check parameter types and values |
| 404 | Not found | Verify ID exists |
| 409 | Conflict | Resource already exists or locked |
| 422 | Validation error | Check required fields |
| 500 | Server error | Check system health |
| 503 | Unavailable | Database connection issue |

---

## Rate Limiting

- **Default**: 1000 requests per minute per endpoint
- **Search**: 100 requests per minute
- **Consolidation**: 5 requests per minute (long-running)

---

## See Also

- [USAGE_GUIDE.md](./USAGE_GUIDE.md) - How to use memory operations
- [EXAMPLES.md](./EXAMPLES.md) - Code examples and use cases
- [tutorials/getting-started.md](./tutorials/getting-started.md) - Quick start
- [tutorials/advanced-features.md](./tutorials/advanced-features.md) - Advanced patterns

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Complete Reference
