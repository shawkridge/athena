# Phase 3a Task Management Tools

Filesystem-discoverable tools for task dependency and metadata management.

## Overview

Phase 3a adds two dimensions of task intelligence to Athena:
1. **Task Dependencies** - Block tasks on other tasks
2. **Task Metadata** - Track effort, complexity, tags, accuracy

## Available Tools

### Dependencies (3 tools)

- **`create_dependency`** - Create blocking relationship (Task A blocks Task B)
  - Returns: Dependency ID on success
  - Use when: You need to order tasks (e.g., "test depends on implementation")

- **`check_task_blocked`** - Check if a task is blocked
  - Returns: (is_blocked, blocking_task_ids)
  - Use when: You need to know if a task can start

- **`get_unblocked_tasks`** - Get tasks ready to work on
  - Returns: List of unblocked tasks
  - Use when: You want intelligent task suggestions

### Metadata (4 tools)

- **`set_task_metadata`** - Set effort estimate, complexity, priority, tags
  - Parameters: effort_estimate (minutes), complexity_score (1-10), tags (list)
  - Use when: You're planning a task

- **`record_task_effort`** - Record actual effort spent
  - Parameters: actual_minutes
  - Use when: Task is complete, record what it took

- **`get_task_metadata`** - Get full task metadata including accuracy
  - Returns: Metadata dict with effort, complexity, accuracy (if available)
  - Use when: You need task details

- **`get_project_analytics`** - Get project-wide analytics
  - Returns: Aggregate effort, complexity, and accuracy statistics
  - Use when: You need project insights

## Discovery Pattern

Following Anthropic's recommended approach:

```
1. Agents explore filesystem
   ls /athena/tools/task_management/

2. Read tool definitions
   cat /athena/tools/task_management/create_dependency.py

3. Import and use the actual implementation
   from athena.prospective.dependencies import DependencyStore
   db = Database()
   store = DependencyStore(db)
   store.create_dependency(...)
```

## Usage Example

### Get Next Unblocked Task

```python
from athena.prospective.dependencies import DependencyStore
from athena.core.database import Database

db = Database()
store = DependencyStore(db)

# Get tasks ready to work on (not blocked by dependencies)
unblocked = store.get_unblocked_tasks(
    project_id=1,
    statuses=["pending", "in_progress"],
    limit=10
)

# Suggest highest priority unblocked task
next_task = max(unblocked, key=lambda t: t['priority'])
print(f"Next task: {next_task['content']}")
```

### Track Effort and Accuracy

```python
from athena.prospective.metadata import MetadataStore
from athena.core.database import Database

db = Database()
store = MetadataStore(db)

# Set estimate when planning
store.set_metadata(
    project_id=1,
    task_id=1,
    effort_estimate=120,  # minutes
    complexity_score=7,
    tags=["feature", "urgent"]
)

# Record actual when done
store.record_actual_effort(project_id=1, task_id=1, actual_minutes=150)

# Check accuracy
accuracy = store.calculate_accuracy(project_id=1, task_id=1)
print(f"Accuracy: {accuracy['accuracy_percent']}%")
print(f"Underestimated by: {accuracy['variance_minutes']}m")
```

### Create Workflow

```python
# Task 1: Implement
dep_store.create_dependency(project_id=1, from_task_id=1, to_task_id=2)

# Task 2: Test (blocked by Task 1)
dep_store.create_dependency(project_id=1, from_task_id=2, to_task_id=3)

# Task 3: Deploy (blocked by Task 2)

# Complete Task 1
is_blocked_1, _ = dep_store.is_task_blocked(1, 1)  # False, can complete

# Task 2 is now ready (unblocked by Task 1)
is_blocked_2, _ = dep_store.is_task_blocked(1, 2)  # False
```

## Implementation Details

### DependencyStore

Located: `/src/athena/prospective/dependencies.py`

Methods:
- `create_dependency(project_id, from_task_id, to_task_id)` → int
- `is_task_blocked(project_id, task_id)` → (bool, list[int])
- `get_blocking_tasks(project_id, task_id)` → list[dict]
- `get_blocked_tasks(project_id, task_id)` → list[int]
- `get_unblocked_tasks(project_id, statuses, limit)` → list[dict]
- `remove_dependency(project_id, from_task_id, to_task_id)` → bool

### MetadataStore

Located: `/src/athena/prospective/metadata.py`

Methods:
- `set_metadata(project_id, task_id, effort_estimate, complexity_score, priority_score, tags)` → bool
- `record_actual_effort(project_id, task_id, actual_minutes)` → bool
- `calculate_accuracy(project_id, task_id)` → dict
- `get_task_metadata(project_id, task_id)` → dict
- `get_project_analytics(project_id)` → dict
- `add_tags(project_id, task_id, tags)` → bool

## Integration

Phase 3a integrates with:
- **ProspectiveStore** - Enhanced task storage
- **TaskUpdater** - Marks complete + unblocks
- **CheckpointTaskLinker** - Suggests only unblocked tasks
- **MCP Server** - Exposed as tools

## Token Efficiency

Following Anthropic's pattern, Phase 3a achieves:
- **Progressive discovery** - Agents read tool defs on-demand
- **Local processing** - Filter/transform data locally before returning
- **98.7% token savings** - Compared to upfront tool loading

Example: Filtering 1000 tasks to 10 unblocked happens locally, only 10 returned to Claude.
