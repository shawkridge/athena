# Code Examples & Use Cases

Practical examples for common Athena use cases.

## Table of Contents

- [Basic Operations](#basic-operations)
- [Learning & Development](#learning--development)
- [Project Management](#project-management)
- [Knowledge Base](#knowledge-base)
- [Advanced Patterns](#advanced-patterns)

---

## Basic Operations

### Store and Retrieve a Memory

```python
from athena.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()

# Store a memory
memory_id = manager.store_memory(
    content="Python uses reference counting for garbage collection",
    domain="python",
    importance=0.8,
    tags=["garbage-collection", "memory"]
)

# Retrieve it back
memory = manager.get_memory(memory_id)
print(f"Stored: {memory.content}")
print(f"Importance: {memory.importance}")
```

### Search Memories

```python
# Simple search
results = manager.search_memories("garbage collection", limit=5)
print(f"Found {len(results)} results")

# Search by domain
python_memories = manager.search_memories(
    "memory management",
    domain="python",
    limit=10
)

# Advanced filtering
important = manager.search_memories(
    "optimization",
    min_importance=0.8,
    limit=5
)
```

### Record an Event

```python
# Record what happened
event_id = manager.store_event(
    title="Fixed memory leak in cache",
    description="Cache was holding references to deleted objects",
    tags=["bug-fix", "performance", "cache"],
    source_context="Production incident"
)

# Later, find events by tag
cache_events = manager.search_events_by_tag("cache")
```

---

## Learning & Development

### Track Daily Learning

```python
from datetime import datetime

# Every day, log what you learned
daily_lessons = [
    "Understood Python async/await patterns",
    "Learned about fastAPI middleware",
    "Practiced writing unit tests"
]

for lesson in daily_lessons:
    manager.store_event(
        title=f"Daily learning - {datetime.now().strftime('%Y-%m-%d')}",
        description=lesson,
        tags=["learning", "daily"]
    )

# At week end, consolidate learning
if datetime.now().weekday() == 6:  # Sunday
    patterns = manager.consolidate(
        strategy="quality",
        days_back=7,
        min_cluster_size=2
    )
    print(f"Extracted {len(patterns)} learning patterns this week")
```

### Create Learning Path

```python
# Define learning goal
goal = manager.create_goal(
    title="Learn FastAPI",
    description="Master FastAPI for building APIs",
    priority=0.9,
)

# Break into tasks
tasks = [
    "Install FastAPI and dependencies",
    "Create first API endpoint",
    "Learn about request/response models",
    "Implement error handling",
    "Build realistic API project"
]

task_ids = []
for i, task_title in enumerate(tasks):
    task = manager.create_task(
        title=task_title,
        goal_id=goal,
        priority=0.9 - (i * 0.1)  # Decreasing priority
    )
    task_ids.append(task)

# Track progress
print(f"Total tasks: {len(task_ids)}")

# As you complete tasks
manager.complete_task(task_ids[0])
manager.complete_task(task_ids[1])

# Check progress
progress = manager.get_goal_progress(goal)
print(f"Progress: {progress['completed']}/{progress['total']}")
```

### Build Personal Knowledge Base

```python
# As you learn topics, create structured knowledge
topics = {
    "Asyncio": {
        "description": "Python's async I/O library",
        "uses": ["Web servers", "Database clients"],
        "importance": 0.9
    },
    "FastAPI": {
        "description": "Modern web framework",
        "uses": ["REST APIs", "Real-time APIs"],
        "importance": 0.95
    },
    "PostgreSQL": {
        "description": "Relational database",
        "uses": ["Data storage", "Transactions"],
        "importance": 0.9
    }
}

for topic, info in topics.items():
    # Store each concept
    memory_id = manager.store_memory(
        content=f"{topic}: {info['description']}",
        domain="programming",
        importance=info['importance']
    )

    # Create entity in knowledge graph
    entity = manager.create_entity(
        name=topic,
        entity_type="technology"
    )

# Create relationships
manager.create_relation(
    source_name="FastAPI",
    target_name="Asyncio",
    relation_type="uses",
    strength=0.95
)

manager.create_relation(
    source_name="FastAPI",
    target_name="PostgreSQL",
    relation_type="often_paired_with",
    strength=0.8
)
```

---

## Project Management

### Sprint Tracking

```python
# Create sprint goal
sprint = manager.create_goal(
    title="Sprint 23 - Authentication",
    description="Implement OAuth2 authentication",
    priority=0.95
)

# Add user stories as tasks
stories = [
    ("Implement JWT token generation", 0.95),
    ("Add password hashing", 0.9),
    ("Create login endpoint", 0.95),
    ("Add refresh token logic", 0.8),
    ("Write security tests", 0.85)
]

story_ids = []
for story_title, priority in stories:
    task = manager.create_task(
        title=story_title,
        goal_id=sprint,
        priority=priority
    )
    story_ids.append(task)

# Daily standup - log progress
from datetime import datetime

status_update = manager.store_event(
    title="Sprint 23 - Daily standup",
    description="Completed JWT token generation, working on password hashing",
    tags=["standup", "sprint-23"],
    source_context="Scrum meeting"
)

# Mark stories as complete
manager.complete_task(story_ids[0])  # JWT done

# Sprint retrospective
manager.store_event(
    title="Sprint 23 - Retrospective",
    description="Completed all user stories. Need better testing procedures.",
    tags=["retrospective", "sprint-23"]
)

# Extract learnings
learnings = manager.consolidate(
    strategy="quality",
    days_back=14  # Sprint period
)
```

### Bug Tracking

```python
# Report bug as event
bug_id = manager.store_event(
    title="BUG: Cache invalidation timeout",
    description="Cache not invalidating after 1 hour in some cases",
    tags=["bug", "critical", "cache"],
    source_context="Production alert"
)

# Store debugging notes as memories
manager.store_memory(
    content="Cache timeout bug likely caused by clock skew in distributed system",
    domain="debugging",
    importance=0.9
)

# Create fix task
fix_task = manager.create_task(
    title="Fix cache invalidation timeout",
    priority=0.99  # Critical
)

# When fixed, consolidate the knowledge
manager.store_event(
    title="Bug fix: Cache invalidation",
    description="Solution: Use centralized time source, increased timeout buffer",
    tags=["bug-fix", "cache"],
    source_context="Bug #456"
)

# Extract solution as procedure
procedure = manager.store_procedure(
    name="Fix cache timeout issues",
    steps=[
        "Check system clock synchronization",
        "Review timeout calculation logic",
        "Add safety buffer to timeout value",
        "Test with simulated clock skew",
        "Deploy and monitor"
    ],
    domain="debugging",
    effectiveness=0.9
)
```

---

## Knowledge Base

### Build Technical Documentation

```python
# Store architectural decisions
arch_decisions = [
    {
        "title": "Use async/await for I/O",
        "rationale": "Non-blocking I/O improves throughput",
        "domain": "architecture"
    },
    {
        "title": "PostgreSQL for persistence",
        "rationale": "ACID compliance and reliability",
        "domain": "database"
    }
]

for decision in arch_decisions:
    manager.store_memory(
        content=f"ADR: {decision['title']} - {decision['rationale']}",
        domain=decision['domain'],
        importance=0.95
    )

# Search architectural decisions
arch_docs = manager.search_memories(
    "async",
    domain="architecture"
)

print("Architectural decisions about async:")
for doc in arch_docs:
    print(f"- {doc.content}")
```

### API Reference Generation

```python
# Document API endpoints
endpoints = [
    {
        "path": "/users/{id}",
        "method": "GET",
        "description": "Get user by ID",
        "params": ["id: int"],
        "returns": "User object"
    },
    {
        "path": "/users",
        "method": "POST",
        "description": "Create new user",
        "params": ["name: str", "email: str"],
        "returns": "Created user with ID"
    }
]

for endpoint in endpoints:
    doc = f"""
    {endpoint['method']} {endpoint['path']}
    {endpoint['description']}
    Params: {', '.join(endpoint['params'])}
    Returns: {endpoint['returns']}
    """

    manager.store_memory(
        content=doc,
        domain="api",
        importance=0.9
    )

# Later, search for endpoint
api_docs = manager.search_memories("GET /users", domain="api")
```

---

## Advanced Patterns

### Problem Solving Workflow

```python
# Record the problem
problem = manager.store_event(
    title="Performance degradation under load",
    description="API response time increases from 100ms to 1s under 100+ concurrent requests",
    tags=["performance", "production"],
    source_context="Production incident"
)

# Capture investigation steps
investigation_steps = [
    "Check CPU utilization - normal",
    "Check memory usage - normal",
    "Check database query time - HIGH",
    "Identified: N+1 query problem in user loading"
]

for i, step in enumerate(investigation_steps):
    manager.store_event(
        title=f"Investigation step {i+1}",
        description=step,
        tags=["investigation", "performance"]
    )

# Store solution
solution = manager.store_memory(
    content="N+1 query problem solved with proper JOIN and eager loading",
    domain="performance",
    importance=0.95
)

# Extract as procedure for future reference
manager.store_procedure(
    name="Debug N+1 query performance issue",
    steps=[
        "Enable query logging to see all queries",
        "Run load test and capture queries",
        "Identify repeated single queries inside loops",
        "Use JOIN or eager loading instead",
        "Verify query count reduced with load test",
        "Monitor production performance"
    ],
    domain="debugging",
    effectiveness=0.9
)

# Link the knowledge together
# (This creates a searchable learning experience)
```

### Cross-Domain Pattern Discovery

```python
# Consolidate across multiple domains
all_patterns = manager.consolidate(
    strategy="quality",
    days_back=30
)

# Filter by patterns that span domains
# (This requires custom analysis, but shows power of consolidation)
cross_domain_patterns = [
    p for p in all_patterns
    if spans_multiple_domains(p)
]

print(f"Found {len(cross_domain_patterns)} cross-domain patterns")

# Example: Performance lesson applies to multiple systems
# - Database optimization (layer 2)
# - Cache implementation (layer 3)
# - API design (layer 4)
```

### Research & Learning Synthesis

```python
# Store research from multiple sources
research_papers = [
    "Raft Consensus Algorithm",
    "CRDT for Distributed Systems",
    "Memory Management in Go"
]

for paper in research_papers:
    manager.store_event(
        title=f"Read research: {paper}",
        tags=["research", "reading"],
        source_context=f"arxiv: {paper}"
    )

    # Store key takeaways
    manager.store_memory(
        content=f"Key insights from {paper}",
        domain="research",
        importance=0.9
    )

# Weekly research consolidation
insights = manager.consolidate(
    strategy="quality",
    days_back=7,
    tags=["research"]
)

print(f"This week's research synthesis: {len(insights)} insights")

# Build knowledge graph from research
topics = {
    "Raft Consensus": "distributed-systems",
    "CRDT": "distributed-systems",
    "Memory Management": "systems-programming"
}

for topic, domain in topics.items():
    entity = manager.create_entity(
        name=topic,
        entity_type="research_topic"
    )
```

---

## Real-World Scenarios

### Onboarding New Team Member

```python
# Create onboarding plan
onboarding_goal = manager.create_goal(
    title="Onboard new engineer",
    description="Team member familiar with codebase and practices",
    priority=0.9
)

# Create onboarding tasks
onboarding_tasks = [
    "Set up development environment",
    "Complete security training",
    "Review architecture documentation",
    "Read code standards guide",
    "Submit first code review",
    "Lead architecture discussion"
]

for task in onboarding_tasks:
    manager.create_task(
        title=task,
        goal_id=onboarding_goal
    )

# Daily check-ins
manager.store_event(
    title="Onboarding check-in - Day 1",
    description="Environment setup complete, ready to code",
    tags=["onboarding"]
)

# When complete, extract procedures
if is_all_complete(onboarding_goal):
    manager.consolidate(
        strategy="quality",
        days_back=30
    )
    # Results can be used to improve onboarding process
```

### Knowledge Transfer

```python
# Before senior leaves team, document expertise
expertise_areas = ["authentication", "database-optimization", "kubernetes-deployment"]

for area in expertise_areas:
    manager.store_memory(
        content=f"Expert knowledge transfer session on {area}",
        domain=area,
        importance=0.99
    )

# Record knowledge transfer session
manager.store_event(
    title="Knowledge transfer session",
    description="Senior engineer shared 10 years of database optimization expertise",
    tags=["knowledge-transfer", "database"],
    source_context="Team meeting"
)

# Create procedures from shared knowledge
manager.store_procedure(
    name="Database optimization best practices",
    steps=[
        "Index on frequently filtered columns",
        "Use EXPLAIN ANALYZE for query planning",
        "Monitor slow query log",
        "Batch operations when possible",
        "Use connection pooling"
    ],
    domain="database",
    effectiveness=0.95
)
```

---

## Running Examples

### Save and run examples

```bash
# Save as example_learning.py
python example_learning.py

# Or run interactively
python3
from athena.manager import UnifiedMemoryManager
manager = UnifiedMemoryManager()
# ... run examples above
```

---

## See Also

- [USAGE_GUIDE.md](./USAGE_GUIDE.md) - Complete usage guide
- [API_REFERENCE.md](./API_REFERENCE.md) - API reference
- [tutorials/getting-started.md](./tutorials/getting-started.md) - Quick start
- [tutorials/advanced-features.md](./tutorials/advanced-features.md) - Advanced patterns

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Comprehensive Examples
