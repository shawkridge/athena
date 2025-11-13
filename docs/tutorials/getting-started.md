# Getting Started with Athena

Learn the basics of using Athena's 8-layer memory system in 15 minutes.

## What is Athena?

Athena is a neuroscience-inspired memory system for AI agents with 8 layers:

1. **Episodic** - Events and experiences (what happened)
2. **Semantic** - Facts and knowledge (what you know)
3. **Procedural** - Skills and workflows (how to do things)
4. **Prospective** - Goals and tasks (what's planned)
5. **Knowledge Graph** - Relationships between concepts
6. **Meta-Memory** - Quality tracking and expertise
7. **Consolidation** - Sleep-like pattern extraction
8. **Supporting Systems** - RAG, planning, retrieval

## Installation

```bash
# Clone the repository
git clone https://github.com/anthropics/athena.git
cd athena

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Athena
pip install -e ".[dev]"
```

See [INSTALLATION.md](../INSTALLATION.md) for detailed setup instructions.

## Quick Test

Verify your installation works:

```bash
# Run a simple test
pytest tests/unit/test_episodic_store.py -v

# You should see: PASSED ✓
```

## Basic Usage

### 1. Store an Event (Episodic Memory)

Events are experiences with context:

```python
from athena.episodic.store import EpisodicStore
from athena.core.database import Database

# Create database and store
db = Database()  # Uses PostgreSQL connection from env
episodic_store = EpisodicStore(db)

# Store an event
event_id = episodic_store.store_event(
    title="Learned about memory layers",
    description="Studied the 8 layers of Athena",
    tags=["learning", "athena"],
    source_context="Athena tutorial",
)

print(f"Stored event: {event_id}")
```

### 2. Retrieve an Event

```python
# Get the event back
event = episodic_store.get_event(event_id)
print(f"Event: {event.title}")
print(f"Tags: {event.tags}")
```

### 3. Search Events

```python
# Find events by tag
recent_events = episodic_store.search_by_tag("learning", limit=5)
print(f"Found {len(recent_events)} learning events")

# Find events by time range
from datetime import datetime, timedelta
yesterday = datetime.now() - timedelta(days=1)
daily_events = episodic_store.search_by_time(since=yesterday)
print(f"Found {len(daily_events)} events since yesterday")
```

### 4. Store Knowledge (Semantic Memory)

When you discover facts, save them to semantic memory:

```python
from athena.semantic.store import SemanticStore

semantic_store = SemanticStore(db)

# Store a fact
memory_id = semantic_store.store_memory(
    content="Athena has 8 memory layers for intelligent retention",
    domain="memory_systems",
    importance=0.8,
)

print(f"Stored memory: {memory_id}")
```

### 5. Search Knowledge

```python
# Search for related memories
results = semantic_store.search("memory layers", limit=3)
for memory in results:
    print(f"- {memory.content}")
    print(f"  Importance: {memory.importance}")
```

### 6. Extract Procedures (Learn Workflows)

After completing tasks, extract reusable workflows:

```python
from athena.procedural.extraction import ProcedureExtractor

# If you've stored episodic events describing a workflow
extractor = ProcedureExtractor(db)

# Extract procedures from events in the last session
procedures = extractor.extract_from_session(
    session_id="my-session-123",
    threshold=0.7,  # Confidence threshold
)

print(f"Extracted {len(procedures)} procedures")
for proc in procedures:
    print(f"- {proc.name}: {proc.description}")
```

### 7. Set Goals (Prospective Memory)

```python
from athena.prospective.goals import GoalStore

goal_store = GoalStore(db)

# Create a goal
goal_id = goal_store.create_goal(
    title="Master Athena",
    description="Understand all 8 memory layers",
    priority=1,  # 0 = lowest, 1 = highest
    deadline=None,  # Optional deadline
)

print(f"Created goal: {goal_id}")
```

### 8. Track Tasks

```python
from athena.prospective.tasks import TaskStore

task_store = TaskStore(db)

# Create a task for the goal
task_id = task_store.create_task(
    title="Read Athena architecture",
    description="Study the 8-layer design",
    goal_id=goal_id,
    priority=1,
)

print(f"Created task: {task_id}")

# Mark task as complete
task_store.complete_task(task_id)
```

## Understanding the Layers

### Layer 1: Episodic (What Happened?)

Stores experiences with full context - when, where, what, how.

```python
# Best for: Recording events, learning from experience
event = episodic_store.store_event(
    title="Learned Python loops",
    description="Spent 2 hours practicing for/while loops",
    timestamp=datetime.now(),
    tags=["python", "learning"],
)
```

### Layer 2: Semantic (What Do I Know?)

Stores facts, concepts, and knowledge extracted from events.

```python
# Best for: Knowledge facts, extracted insights
memory = semantic_store.store_memory(
    content="Python for loops iterate over sequences",
    domain="python",
    importance=0.9,
)
```

### Layer 3: Procedural (How Do I Do It?)

Stores reusable workflows and skills learned from repeated experiences.

```python
# Best for: Techniques, workflows, recurring tasks
procedure = procedural_store.store_procedure(
    name="Write Python loop",
    steps=[
        "Choose sequence to iterate",
        "Write for variable in sequence:",
        "Indent loop body",
        "Use variable inside loop",
    ],
    domain="python",
)
```

### Layer 4: Prospective (What's Planned?)

Stores goals, tasks, and future intentions.

```python
# Best for: Planning, goal tracking, task management
goal = goal_store.create_goal(
    title="Become Python expert",
    priority=1,
)

task = task_store.create_task(
    title="Complete 10 Python projects",
    goal_id=goal,
)
```

## Consolidation: The Key Innovation

Athena's killer feature is **consolidation** - converting episodic events into semantic knowledge:

```python
from athena.consolidation.consolidator import Consolidator

consolidator = Consolidator(db)

# Extract patterns from recent events
consolidated = consolidator.consolidate(
    strategy="balanced",  # balanced, speed, or quality
    days_back=7,  # Look at last 7 days
)

print(f"Consolidated {len(consolidated)} new memories")
```

This works like your brain during sleep:
1. **System 1 (Fast)** - Group similar events automatically
2. **System 2 (Slow)** - Use AI to validate and refine patterns

## Full Example: Learn a Skill

Here's a complete example of learning a new skill:

```python
from datetime import datetime
from athena.episodic.store import EpisodicStore
from athena.semantic.store import SemanticStore
from athena.consolidation.consolidator import Consolidator

# Setup
db = Database()
episodic = EpisodicStore(db)
semantic = SemanticStore(db)
consolidator = Consolidator(db)

# Step 1: Store learning experiences
for day in range(3):
    event_id = episodic.store_event(
        title=f"Python practice day {day+1}",
        description="Practiced Python for 1 hour",
        tags=["python", "learning"],
    )
    print(f"Day {day+1}: Stored event {event_id}")

# Step 2: Consolidate (extract knowledge)
consolidated = consolidator.consolidate(strategy="balanced")
print(f"\nExtracted {len(consolidated)} pieces of knowledge")

# Step 3: Search consolidated knowledge
results = semantic.search("python", limit=5)
print(f"\nFound {len(results)} relevant memories")
for memory in results:
    print(f"- {memory.content} (importance: {memory.importance})")
```

## Common Tasks

### Find Related Events

```python
# Search by tag
events = episodic.search_by_tag("python")

# Search by time
from datetime import datetime, timedelta
week_ago = datetime.now() - timedelta(days=7)
week_events = episodic.search_by_time(since=week_ago)
```

### Update Knowledge

```python
# Update memory importance
semantic.update_memory(
    memory_id=123,
    importance=0.95,  # Mark as very important
)
```

### Find Similar Events

```python
# Search for similar episodic events
similar = episodic.search_similar(event_id, limit=5)
print(f"Found {len(similar)} similar events")
```

## Next Steps

1. **Read the tutorials**:
   - [Memory Basics](./memory-basics.md) - Deep dive into each layer
   - [Advanced Features](./advanced-features.md) - Knowledge graphs, RAG, planning

2. **Explore the architecture**:
   - Read [ARCHITECTURE.md](../ARCHITECTURE.md)
   - Review [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md)

3. **Start coding**:
   - Try the examples above in a Python notebook
   - Run the test suite: `pytest tests/unit/ -v`
   - Check out working tests in `tests/unit/test_episodic_store.py`

4. **Get help**:
   - See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for common issues
   - Check [INSTALLATION.md](../INSTALLATION.md) for setup help
   - Read [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidance

## Key Concepts

| Concept | Purpose | When to Use |
|---------|---------|------------|
| **Event** | Record an experience | As it happens |
| **Memory** | Store a fact | After learning |
| **Procedure** | Save a workflow | After completing a task |
| **Goal** | Define objective | At start of project |
| **Task** | Track action item | Before doing work |
| **Consolidation** | Extract patterns | End of session/day |

---

**Ready to dive deeper?** Go to [memory-basics.md](./memory-basics.md)
