# Task/Project Management System Analysis

## Current State: Two Separate Systems

### System 1: Athena (PostgreSQL-backed)
**Location:** `~/.work/athena/src/athena/prospective/`, `/migrations/003_*`

**Components:**
- `prospective_tasks` table - Core task storage
- `executive_goals` table - Hierarchical goal system
- `phase_plans` - Task phase tracking
- `planning_patterns` - Reusable strategies
- `execution_feedback` - Learning from execution
- ProspectiveStore - Data access layer
- Session-start hook loads top 5 "active goals" from PostgreSQL

**Characteristics:**
- ✅ Persistent across sessions (PostgreSQL)
- ✅ Rich metadata (priority, status, phases, metrics)
- ✅ Hierarchical (parent/child goals)
- ✅ Learnings from execution captured
- ✅ Already integrated with session-start hooks
- ❌ Not bidirectionally synced with Claude's context
- ❌ Read-only in current session (can't update from Claude)
- ❌ Not accessible to TodoWrite tool

### System 2: Claude Code TodoWrite (JSON-backed)
**Location:** `~/.claude/todos/` (session-scoped files)

**Structure:**
```json
[
  {
    "content": "string",           // Task description
    "status": "pending|in_progress|completed",
    "activeForm": "string"         // Present continuous form
  }
]
```

**Characteristics:**
- ✅ Lives in Claude's context during session
- ✅ I can see and update tasks in real-time
- ✅ Simple, clean API
- ❌ Session-scoped only (dies at context clear)
- ❌ Not persistent (no PostgreSQL)
- ❌ No metadata (priority, dependencies, etc.)
- ❌ Not linked to code, tests, or memory
- ❌ No phase tracking or execution feedback
- ❌ Separate from Athena

---

## The Integration Opportunity

### Problem Statement
**Current behavior:**
- User creates tasks in Claude Code (TodoWrite)
- Session ends → tasks disappear
- User returns to work → "what were we doing?"
- Checkpoint system helps, but tasks are lost

**Desired behavior:**
- Tasks persist across context clears
- Tasks integrate with checkpoints
- Tasks link to code, tests, and memory
- TodoWrite becomes bidirectional (read/write to persistent store)

---

## Integration Architecture: TodoWrite ↔ Prospective Tasks

### Design: Hybrid Dual-Write System

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Context                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TodoWrite (active in session)                       │  │
│  │  [content, status, activeForm]                       │  │
│  └──────────────────────────────────────────────────────┘  │
│           ↑                                    ↑             │
│       (read)                               (write)          │
│           │                                    │             │
└───────────┼────────────────────────────────────┼─────────────┘
            │                                    │
    ┌───────┴────────────────────────────────────┴──────┐
    │                                                    │
    │     Bidirectional Sync Layer (New)               │
    │     - Translate TodoWrite ↔ ProspectiveTask      │
    │     - Merge metadata intelligently               │
    │     - Maintain reference IDs                     │
    │                                                    │
    └───────┬────────────────────────────────────────┬──────┘
            │                                        │
            ↓                                        ↓
┌───────────────────────────────────┐   ┌──────────────────────┐
│  PostgreSQL: prospective_tasks    │   │  Session Checkpoint  │
│                                   │   │  (task references)   │
│  - id (primary key)              │   │                      │
│  - content                        │   │  CHECKPOINT_TASK_ID  │
│  - status                         │   │  points to task      │
│  - priority                       │   │                      │
│  - phase                          │   └──────────────────────┘
│  - active_form                    │
│  - created_at, updated_at        │
│  - project_id                     │
│  - related_checkpoint_id (NEW)   │
│  - related_test_name (NEW)       │
│  - related_file_path (NEW)       │
└───────────────────────────────────┘
```

### Implementation Steps

#### 1. Extend prospective_tasks Schema
```sql
ALTER TABLE prospective_tasks ADD COLUMN (
    claude_session_id VARCHAR(255),      -- Current session
    sync_status VARCHAR(50),             -- synced|pending|conflict
    checkpoint_id INTEGER,               -- Links to checkpoint
    related_test_name VARCHAR(500),      -- Test that validates task
    related_file_path VARCHAR(1000),     -- Primary file being edited
    last_claude_sync_at INTEGER          -- Last sync timestamp
);

CREATE INDEX idx_task_checkpoint ON prospective_tasks(checkpoint_id);
CREATE INDEX idx_task_test ON prospective_tasks(related_test_name);
```

#### 2. Create TodoWrite Sync Module
**Location:** `/home/user/.claude/hooks/lib/todowrite_sync.py`

```python
class TodoWriteSync:
    """Bidirectional sync between TodoWrite and prospective_tasks."""

    def __init__(self):
        self.bridge = MemoryBridge()

    def load_tasks_from_postgres(self, project_id):
        """Load active tasks from PostgreSQL → Convert to TodoWrite format."""
        # Query prospective_tasks WHERE project_id = ? AND status IN ('pending', 'active', 'in_progress')
        # Convert to: [{"content": ..., "status": ..., "activeForm": ...}]

    def save_todowrite_to_postgres(self, project_id, tasks):
        """Save TodoWrite updates → Write back to PostgreSQL."""
        # For each task:
        #   - Find or create prospective_task record
        #   - Update status, content, timestamp
        #   - Set sync_status = 'synced'

    def sync_checkpoint_to_task(self, checkpoint, task_id):
        """Link checkpoint to task."""
        # UPDATE prospective_tasks SET checkpoint_id = ? WHERE id = ?

    def get_task_context(self, task_id):
        """Get full context: test, file, checkpoint, memory."""
        # SELECT * FROM prospective_tasks WHERE id = task_id
        # Join with checkpoint, memory, related tests
```

#### 3. Modify session-start.sh

```bash
# Phase: Load active tasks
print(f"✓ Loading active tasks...", file=sys.stderr)

from todowrite_sync import TodoWriteSync
sync = TodoWriteSync()

# Load tasks from PostgreSQL
active_tasks = sync.load_tasks_from_postgres(project_id, limit=10)

# Convert to TodoWrite JSON
todowrite_tasks = convert_to_todowrite_format(active_tasks)

# Write to session file
session_todo_file = f"/home/user/.claude/todos/{session_id}.json"
with open(session_todo_file, 'w') as f:
    json.dump(todowrite_tasks, f)

# Also inject into working memory (with links)
for task in active_tasks[:3]:
    active_items.insert(0, {
        'id': f'task_{task["id"]}',
        'type': 'task',
        'content': f"Task: {task['content']} [Status: {task['status']}]",
        'importance': 0.85,
        ...
    })
```

#### 4. Modify session-end.sh

```bash
# Phase: Sync TodoWrite changes back to PostgreSQL
print(f"✓ Syncing tasks back to persistent storage...", file=sys.stderr)

from todowrite_sync import TodoWriteSync
sync = TodoWriteSync()

# Load current TodoWrite state
session_todo_file = f"/home/user/.claude/todos/{session_id}.json"
if os.path.exists(session_todo_file):
    with open(session_todo_file, 'r') as f:
        current_tasks = json.load(f)

    # Sync back to PostgreSQL
    sync.save_todowrite_to_postgres(project_id, current_tasks)

    # Link checkpoint if exists
    if os.environ.get('CHECKPOINT_TASK_ID'):
        checkpoint_task_id = int(os.environ['CHECKPOINT_TASK_ID'])
        # UPDATE checkpoint SET related_task_id = ?
```

#### 5. Extend checkpoint_manager.py

```python
class CheckpointSchema:
    @staticmethod
    def create(
        task_name: str,
        file_path: str,
        test_name: str,
        next_action: str,
        task_id: Optional[int] = None,  # NEW: Link to persistent task
        ...
    ):
        checkpoint = {
            ...
            "task_id": task_id,  # Reference to prospective_tasks.id
        }
```

---

## Benefits of Integration

### For Session Continuity
| Scenario | Before | After |
|----------|--------|-------|
| Create task, context clears | ❌ Task lost | ✅ Task persists in PostgreSQL |
| Load next session | ❌ No tasks shown | ✅ Tasks loaded from DB into TodoWrite |
| Multiple sessions on same project | ❌ Tasks isolated | ✅ Tasks shared across sessions |

### For Checkpoint System
```
Current: Checkpoint → File, Test, Next Action
Enhanced: Checkpoint ← Task ← Full context (priority, blockers, related tasks)

When loading checkpoint:
  1. Load checkpoint from DB
  2. Load associated task from DB
  3. Load related tasks and blockers
  4. Show full project context
  5. Auto-run test and update task status
```

### For Memory Integration
```
Task ↔ Checkpoint ↔ Memory

When consolidating session:
  - Completed tasks → Extract as learning
  - Blockers → Linked to execution feedback
  - Failed tasks → Analyze failure reason
  - Next task → Checkpoint ready for next session
```

### For Work Continuity
```
Session 1: User creates 5 tasks, works on task #3, completes it
  ↓ (context clear)
Session 2: TodoWrite loads all 5 tasks, highlights task #4 as next
           Checkpoint links task #4 to test and file
           User continues immediately
```

---

## Data Flow: Example

**Session 1: Creating Tasks**
```
Claude Code:
  TodoWrite: [
    {content: "Implement JWT refresh", status: "in_progress"},
    {content: "Add error handling", status: "pending"},
    {content: "Write tests", status: "pending"}
  ]

Session-end:
  → TodoWriteSync.save_todowrite_to_postgres()
  → Create prospective_tasks records
  → IDs: [101, 102, 103]
  → PostgreSQL updated
  → Checkpoint saved: task_id=101
```

**Session 2: Resuming Work**
```
Session-start:
  → TodoWriteSync.load_tasks_from_postgres()
  → Query: SELECT * WHERE project_id=1 AND status IN ('pending', 'in_progress')
  → Get: [Task 101, 102, 103]
  → Convert to TodoWrite JSON
  → Load checkpoint with task_id=101
  → Show task 101 as "next up"
  → User continues

Claude Code:
  TodoWrite: [
    {content: "Implement JWT refresh", status: "in_progress"},  ← from DB
    {content: "Add error handling", status: "pending"},          ← from DB
    {content: "Write tests", status: "pending"}                  ← from DB
  ]

  Checkpoint shows: Task 101, File: src/auth.ts, Test: test_jwt_refresh
```

---

## Implementation Strategy

### Phase 1: Minimal Integration (1-2 hours)
- Create TodoWriteSync module
- Add task_id to checkpoint schema
- Load tasks from PostgreSQL on session-start
- Save tasks back on session-end
- **Result:** Tasks persist, sync one-way

### Phase 2: Bidirectional Sync (2-3 hours)
- Add task metadata to prospective_tasks
- Handle merges when task updated in both places
- Link checkpoint to task
- Show task context in working memory
- **Result:** Full read/write sync

### Phase 3: Advanced Features (3-4 hours)
- Task dependencies (block on other tasks)
- Task priorities (affect working memory ranking)
- Task completion triggers (auto-create new checkpoints)
- Task history and analytics
- **Result:** Rich task management system

---

## Questions Before Building

1. **Priority Weighting**: Should active tasks appear before regular working memory?
   - Current: 7 items of working memory (7±2 capacity)
   - Proposed: 1-2 active tasks + 5-6 memories
   - Or: Mix by importance?

2. **Task Metadata**: What fields matter?
   - Min: content, status, activeForm
   - Good: + priority, due_date, tags
   - Rich: + dependencies, blockers, related_test, related_file

3. **Sync Conflicts**: If task edited in both places?
   - Last-write-wins?
   - Merge intelligently (status takes PostgreSQL, content takes Claude)?
   - Manual conflict resolution?

4. **Archive Strategy**: When are old tasks removed?
   - Delete after 30 days?
   - Archive when completed?
   - Keep forever?

5. **Scope**: Per-project or global?
   - Should tasks from Project A show when working on Project B?
   - Or only active-project tasks?

---

## Constraints & Risks

### Token Cost
- Loading 10 tasks: ~500 tokens
- Syncing 10 tasks: ~500 tokens
- **Total impact:** ~1K tokens per session (negligible, <1% budget)

### Complexity
- Adds TodoWriteSync module (~200 lines)
- Modifies 2 hooks (session-start, session-end)
- Extends checkpoint schema
- **Risk:** Sync bugs could corrupt tasks

### Data Consistency
- PostgreSQL source of truth
- TodoWrite is ephemeral per-session
- Conflicts possible if network issues
- **Mitigation:** Implement conflict detection + logging

---

## Summary

**Current state:** Two isolated systems (TodoWrite for sessions, Athena for persistence)

**Proposed:** Bidirectional sync layer making TodoWrite the **interface** to persistent PostgreSQL tasks

**Effort:** 6-10 hours implementation (phases 1-3)

**Value:** Tasks survive context clears, link to code/tests/memory, enable work continuity

**Starting point:** Create TodoWriteSync module + modify hooks

Would you like me to:
1. Build Phase 1 (basic persistence + sync)?
2. Design the full schema first?
3. Explore specific edge cases?
