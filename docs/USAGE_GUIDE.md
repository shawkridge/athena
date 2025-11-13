# Usage Guide

Complete guide to using Athena's memory operations and workflows.

## Quick Start

```python
from athena.manager import UnifiedMemoryManager

# Initialize
manager = UnifiedMemoryManager()

# Store an event
event_id = manager.store_event(
    title="Learned about memory",
    description="Studied memory system",
    tags=["learning"]
)

# Store a fact
memory_id = manager.store_memory(
    content="Athena has 8 layers",
    importance=0.9
)

# Search memories
results = manager.search_memories("memory layers", limit=5)

# Get a fact
memory = manager.get_memory(memory_id)
```

---

## Core Workflows

### Workflow 1: Learn and Store

Store learning experiences:

```python
# Step 1: Record what happened
event_id = manager.store_event(
    title="Debugging production issue",
    description="Found memory leak in cache layer",
    tags=["debugging", "production"],
    source_context="Incident #123"
)

# Step 2: Extract key learning
memory_id = manager.store_memory(
    content="Always check cache eviction policy to prevent memory leaks",
    domain="performance",
    importance=0.95  # Very important lesson
)

# Step 3: Link memory to original event
manager.link_memory_to_event(memory_id, event_id)
```

### Workflow 2: Build a Goal

Create and track goals:

```python
# Create goal
goal_id = manager.create_goal(
    title="Master distributed systems",
    description="Deep understanding of consensus algorithms",
    priority=0.9,  # High priority
)

# Add tasks to goal
task1 = manager.create_task(
    title="Study Raft consensus",
    goal_id=goal_id,
    priority=0.9,
)

task2 = manager.create_task(
    title="Implement Raft from scratch",
    goal_id=goal_id,
    priority=0.8,
)

# Track progress
manager.complete_task(task1)  # Mark task complete

# Get goal progress
progress = manager.get_goal_progress(goal_id)
print(f"Progress: {progress['completed']}/{progress['total']} tasks")
```

### Workflow 3: Consolidate Learning

Extract patterns from experiences:

```python
# Step 1: Store daily events
for day in range(7):
    manager.store_event(
        title=f"Daily standup day {day+1}",
        tags=["standup", "daily"],
    )

# Step 2: Consolidate (extract patterns)
patterns = manager.consolidate(
    strategy="quality",  # Better quality, slightly slower
    days_back=7,
)

# Step 3: Review extracted knowledge
for pattern in patterns:
    print(f"Pattern: {pattern.content}")
    print(f"Confidence: {pattern.confidence}")
```

### Workflow 4: Search and Recall

Find relevant knowledge:

```python
# Quick search (vector + keyword)
results = manager.search_memories(
    query="debugging techniques",
    limit=5
)

for memory in results:
    print(f"{memory.content} (importance: {memory.importance})")

# Advanced search with filters
results = manager.search_memories(
    query="performance",
    domain="optimization",
    min_importance=0.7,
    limit=10
)

# Search events by time
from datetime import datetime, timedelta
week_ago = datetime.now() - timedelta(days=7)
recent_events = manager.search_events_by_time(
    since=week_ago,
    tags=["learning"]
)
```

---

## Memory Operations by Layer

### Layer 1: Episodic (Events)

Store experiences as they happen:

```python
# Record an event
event_id = manager.store_event(
    title="Attended technical workshop",
    description="Learned about machine learning in production",
    tags=["workshop", "ml", "learning"],
    source_context="Company training program"
)

# Retrieve event
event = manager.get_event(event_id)

# List events by tag
events = manager.search_events_by_tag("learning", limit=10)

# Find events in time range
from datetime import datetime, timedelta
today = datetime.now()
month_ago = today - timedelta(days=30)
month_events = manager.search_events_by_time(
    since=month_ago,
    until=today
)
```

### Layer 2: Semantic (Knowledge)

Store facts and insights:

```python
# Store a fact
memory_id = manager.store_memory(
    content="Machine learning models require careful hyperparameter tuning",
    domain="ml",
    importance=0.8
)

# Update importance
manager.update_importance(memory_id, importance=0.95)

# Search for knowledge
results = manager.search_memories(
    query="hyperparameter tuning",
    domain="ml",
    limit=5
)

# Get memory details
memory = manager.get_memory(memory_id)
print(f"Memory: {memory.content}")
print(f"Importance: {memory.importance}")
print(f"Created: {memory.created_at}")
```

### Layer 3: Procedural (Workflows)

Save and reuse procedures:

```python
# Store a procedure
procedure_id = manager.store_procedure(
    name="Deploy to production",
    steps=[
        "Run full test suite",
        "Build Docker image",
        "Push to container registry",
        "Update Kubernetes deployment",
        "Monitor logs for errors",
        "Verify all services healthy"
    ],
    domain="devops",
    effectiveness=0.95  # Success rate
)

# Execute procedure
result = manager.execute_procedure(procedure_id)

# Search procedures
procedures = manager.search_procedures(
    query="deploy",
    domain="devops"
)

# Get procedure
procedure = manager.get_procedure(procedure_id)
print(f"Procedure: {procedure.name}")
print(f"Steps: {len(procedure.steps)}")
print(f"Effectiveness: {procedure.effectiveness}")
```

### Layer 4: Prospective (Goals & Tasks)

Plan future work:

```python
# Create goal
goal = manager.create_goal(
    title="Complete certification",
    description="AWS Solutions Architect certification",
    priority=0.8,
    deadline=None  # Optional deadline
)

# Create milestones (tasks under goal)
task1 = manager.create_task(
    title="Study core services",
    goal_id=goal,
    priority=0.9
)

task2 = manager.create_task(
    title="Practice exam questions",
    goal_id=goal,
    priority=0.8
)

# Mark progress
manager.complete_task(task1)

# List active tasks
tasks = manager.list_tasks(status="pending")
```

### Layer 5: Knowledge Graph

Map concept relationships:

```python
# Create entities
python = manager.create_entity(
    name="Python",
    entity_type="programming_language"
)

async_io = manager.create_entity(
    name="AsyncIO",
    entity_type="library"
)

# Link entities
manager.create_relation(
    source_id=python,
    target_id=async_io,
    relation_type="has_library",
    strength=0.95
)

# Find related concepts
neighbors = manager.get_neighbors(python, max_distance=2)

# Detect communities
communities = manager.detect_communities()
for community in communities:
    print(f"Community {community.id}: {len(community.entities)} entities")
```

### Layer 6: Meta-Memory

Monitor knowledge quality:

```python
# Get quality metrics
quality = manager.get_quality_metrics(memory_id)
print(f"Compression: {quality['compression']}")
print(f"Recall: {quality['recall']}")
print(f"Consistency: {quality['consistency']}")

# Get expertise map
expertise = manager.get_expertise(domain="python")
print(f"Python expertise: {expertise}")

# Check cognitive load
load = manager.get_cognitive_load()
print(f"Focus items: {load['current_items']}/{load['max_items']}")
print(f"Attention available: {load['attention_budget']}")
```

### Layer 7: Consolidation

Extract patterns:

```python
# Run consolidation
patterns = manager.consolidate(
    strategy="balanced",  # balanced, speed, quality
    days_back=30,  # Consolidate last 30 days
    min_cluster_size=2  # Minimum events per cluster
)

print(f"Extracted {len(patterns)} patterns")

# Get consolidation stats
stats = manager.get_consolidation_stats()
print(f"Last consolidation: {stats['last_run']}")
print(f"Total patterns extracted: {stats['total_patterns']}")
print(f"Average pattern quality: {stats['avg_quality']}")
```

---

## Advanced Operations

### Batch Operations

```python
# Store multiple events efficiently
events = [
    {"title": f"Event {i}", "tags": ["batch"]}
    for i in range(100)
]

event_ids = manager.bulk_store_events(events)
print(f"Stored {len(event_ids)} events")
```

### Complex Queries

```python
# Multi-criteria search
results = manager.search_memories(
    query="python async",
    domain="programming",
    min_importance=0.7,
    max_age_days=30,
    limit=10
)

# Time-based queries
from datetime import datetime, timedelta
last_week = datetime.now() - timedelta(days=7)
recent = manager.search_events_by_time(since=last_week)
```

### RAG (Retrieval-Augmented Generation)

```python
# Use advanced retrieval strategies
from athena.rag.manager import RAGManager

rag = RAGManager()

# HyDE (Hypothetical Document Embeddings)
results = rag.retrieve(
    query="How to optimize Python code?",
    strategy="hyde",
    limit=5
)

# Reranking for better relevance
results = rag.retrieve(
    query="debugging techniques",
    strategy="reranking",
    limit=5
)

# Reflective search (self-improving)
results = rag.retrieve(
    query="distributed systems",
    strategy="reflective",
    iterations=2,
    limit=5
)
```

### Graph Traversal

```python
# Find shortest path between concepts
path = manager.shortest_path(
    source_name="Python",
    target_name="Machine Learning"
)

print(f"Path: {' -> '.join(e.name for e in path)}")

# Get all paths
all_paths = manager.all_paths(
    source_name="Python",
    target_name="Machine Learning",
    max_distance=3
)
```

---

## Common Patterns

### Pattern 1: Daily Learning Log

```python
# Every day, record learning
event_id = manager.store_event(
    title="Today's learning",
    description="What did you learn today?",
    tags=["daily-log"]
)

# Weekly consolidation
if is_sunday():
    manager.consolidate(
        strategy="quality",
        days_back=7
    )
```

### Pattern 2: Project Tracking

```python
# Create goal for project
project = manager.create_goal(
    title="Build recommendation system",
    priority=0.9
)

# Track milestones
for milestone in ["Design", "Implementation", "Testing", "Deployment"]:
    manager.create_task(
        title=milestone,
        goal_id=project
    )

# Daily progress
manager.store_event(
    title="Project progress",
    tags=[f"project-{project}"]
)

# End of project
manager.complete_goal(project)
```

### Pattern 3: Knowledge Base Building

```python
# As you learn, save knowledge
for topic in ["Python", "Async", "FastAPI"]:
    manager.store_memory(
        content=f"Key insights about {topic}",
        domain="web-development",
        importance=0.8
    )

# Build knowledge graph
for topic1 in topics:
    for topic2 in topics:
        if related(topic1, topic2):
            manager.create_relation(
                source_name=topic1,
                target_name=topic2,
                relation_type="related"
            )
```

---

## Best Practices

### Do's ✅

- Store events frequently (daily or more)
- Consolidate regularly (weekly or after major work)
- Set importance scores accurately
- Link related memories
- Use meaningful tags for filtering
- Monitor quality metrics
- Review and clean up old memories periodically

### Don'ts ❌

- Don't store raw data without context
- Don't skip tagging (makes search harder)
- Don't consolidate without events to consolidate
- Don't ignore low-quality patterns
- Don't hoard memories (archiving works)
- Don't mix domains (keep organized)

---

## Performance Tips

1. **Use domains**: Filter search results by domain for faster queries
2. **Set limits**: Always specify `limit` in searches
3. **Cache results**: Store frequently used searches
4. **Batch operations**: Insert multiple events at once
5. **Index common fields**: Add database indexes for frequently searched tags
6. **Archive old data**: Move old events to archive

---

## See Also

- [API_REFERENCE.md](./API_REFERENCE.md) - Complete API documentation
- [EXAMPLES.md](./EXAMPLES.md) - Code examples
- [tutorials/getting-started.md](./tutorials/getting-started.md) - Quick start
- [tutorials/advanced-features.md](./tutorials/advanced-features.md) - Advanced patterns

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Complete User Guide
