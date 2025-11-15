# TodoWrite Integration: Fit with Existing Project Planning

## The Short Answer

**TodoWrite doesn't replace anything. It becomes the session-scoped interface layer for prospective_tasks.**

The existing project planning system stays exactly as-is. TodoWrite is an addition that makes tasks accessible in Claude's context.

---

## Current Architecture (What Exists)

```
┌─────────────────────────────────────────────────────────┐
│           PROJECT-LEVEL PLANNING (in Athena)            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ProjectPlan (top-level)                               │
│    ├─ Phases[PhasePlan]                                │
│    ├─ Milestones[Milestone]                            │
│    ├─ Dependencies[ProjectDependency]                  │
│    └─ Validation Rules[ValidationRule]                 │
│                                                          │
│  Planning Patterns (reusable strategies)               │
│    ├─ PlanningPattern (hierarchical, recursive, etc.)  │
│    ├─ DecompositionStrategy (how to break tasks down)  │
│    └─ OrchestratorPattern (multi-agent coordination)   │
│                                                          │
│  Execution Feedback (learning)                         │
│    └─ ExecutionFeedback (track what worked/didn't)     │
│                                                          │
└─────────────────────────────────────────────────────────┘
           (stored in PostgreSQL, complex, rich)

┌─────────────────────────────────────────────────────────┐
│         PROSPECTIVE MEMORY (Layer 4 in Athena)          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  prospective_tasks table                               │
│    ├─ id, content, status (pending|in_progress|...)   │
│    ├─ priority, phase, deadline                        │
│    ├─ active_form (present continuous)                │
│    ├─ created_at, updated_at                          │
│    ├─ project_id, assignee                            │
│    └─ blocked_reason, failure_reason                  │
│                                                          │
│  executive_goals table (hierarchical)                  │
│    ├─ goal_text, goal_type                            │
│    ├─ priority (1-10), progress (0-1.0)               │
│    ├─ deadline, completed_at                          │
│    └─ parent_goal_id (for hierarchy)                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
           (stored in PostgreSQL, persistent)
```

**Status quo:**
- Project planning exists (sophisticated, rarely updated in session)
- Prospective tasks exist (persistent, currently one-way read-only into Claude)
- TodoWrite exists (session-scoped, ephemeral, not linked to anything)

---

## After TodoWrite Integration (What Changes)

```
┌──────────────────────────────────────────────────────────────────┐
│                    Claude Code Context                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  TodoWrite (session-scoped, in-memory)                          │
│    [{"content": "...", "status": "...", "activeForm": "..."}]   │
│                                                                   │
│  ↑ Loaded from DB at session-start                              │
│  ↓ Synced back to DB at session-end                             │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
                          ↕ (NEW SYNC LAYER)
                    TodoWriteSync (new module)
                    ├─ load_tasks_from_postgres()
                    ├─ save_todowrite_to_postgres()
                    └─ sync_checkpoint_to_task()
                          ↕
┌──────────────────────────────────────────────────────────────────┐
│         PROSPECTIVE MEMORY (Layer 4, ENHANCED)                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  prospective_tasks table (EXTENDED COLUMNS)                     │
│    ├─ id, content, status                                        │
│    ├─ priority, phase, deadline                                  │
│    ├─ active_form                                                │
│    ├─ created_at, updated_at                                    │
│    ├─ project_id, assignee                                      │
│    ├─ blocked_reason, failure_reason                            │
│    │                                                              │
│    ├─ [NEW] checkpoint_id → Links to checkpoint                 │
│    ├─ [NEW] related_test_name → Test that validates task        │
│    ├─ [NEW] related_file_path → Primary file being edited       │
│    └─ [NEW] last_claude_sync_at → Last sync timestamp           │
│                                                                   │
│  executive_goals table (UNCHANGED)                              │
│    └─ Still works exactly as before                             │
│                                                                   │
│  ProjectPlan, PhasePlan, etc. (UNCHANGED)                       │
│    └─ Still works exactly as before                             │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
               (same PostgreSQL, enhanced rows)
```

**What changes:**
- ✅ Add 4 columns to prospective_tasks (checkpoint_id, test_name, file_path, sync_timestamp)
- ✅ Create TodoWriteSync module (~200 lines)
- ✅ Modify session-start.sh to load and inject tasks
- ✅ Modify session-end.sh to save updated tasks
- ❌ Don't touch ProjectPlan, PhasePlan, planning patterns, or any existing logic
- ❌ Don't change executive_goals table

---

## Layering: What Talks to What

### Before Integration

```
Session-Start Hook
  └─ MemoryBridge.get_active_goals()
     └─ SELECT * FROM prospective_tasks WHERE status IN (...)
     └─ Inject into Claude's context
     └─ Claude can read but NOT write back

TodoWrite
  └─ Session-scoped JSON files
  └─ Ephemeral (dies at context clear)
  └─ Not linked to anything
```

### After Integration

```
Session-Start Hook
  ├─ MemoryBridge.get_active_goals()  [UNCHANGED]
  │  └─ SELECT * FROM prospective_tasks
  │
  └─ TodoWriteSync.load_tasks_from_postgres()  [NEW]
     ├─ SELECT * FROM prospective_tasks WHERE status IN (pending, in_progress)
     ├─ Convert to TodoWrite format [{content, status, activeForm}]
     ├─ Write to ~/.claude/todos/{session_id}.json
     └─ Claude sees tasks in TodoWrite
           ↓
Claude edits tasks (mark complete, change priority, update content)
           ↓
Session-End Hook
  ├─ Load ~/. claude/todos/{session_id}.json
  ├─ TodoWriteSync.save_todowrite_to_postgres()  [NEW]
  │  ├─ For each task:
  │  │  ├─ Find existing prospective_task record
  │  │  ├─ Update status, content, timestamp
  │  │  └─ Merge with checkpoint if linked
  │  └─ Write back to prospective_tasks
  │
  ├─ Record executive session end  [UNCHANGED]
  ├─ Consolidate learnings  [UNCHANGED]
  └─ Extract planning patterns  [UNCHANGED]
```

---

## Why This Is "Addition Not Replacement"

### What You Keep (Untouched)

1. **ProjectPlan system**
   - Still for long-term project architecture
   - Still has phases, milestones, dependencies
   - Use case: "Break down a 6-month project into phases"

2. **executive_goals**
   - Hierarchical goal system (parent/child)
   - Strategic goals vs tactical tasks
   - Use case: "What are our Q4 objectives?"

3. **planning_patterns**
   - Reusable strategies (hierarchical, recursive, etc.)
   - Learning from past executions
   - Use case: "Which decomposition strategy worked best last time?"

4. **execution_feedback**
   - Captures learnings from completion
   - Tracks blockers, assumptions violated, etc.
   - Use case: "What did we learn from the last project?"

### What TodoWrite Adds (New Layer)

1. **Session-scoped task management**
   - What am I working on right now?
   - Small, tactical, in-progress items
   - Use case: "Show me 5 tasks I'm actively working on"

2. **Checkpoint linking**
   - Task ↔ Test ↔ File
   - Context for what's being worked on
   - Use case: "What test validates this task?"

3. **In-context editability**
   - I can see and modify tasks during session
   - Changes persist across context clears
   - Use case: "Mark task complete, move to next"

4. **Bidirectional sync**
   - TodoWrite is just the **view** of prospective_tasks
   - Same underlying PostgreSQL data
   - Use case: "Keep session-level work in sync with persistent storage"

---

## Example: How They Work Together

### Scenario: Implementing JWT Refresh

**Week 1: Project Planning (uses ProjectPlan)**
```
Milestone: Authentication System
  ├─ Phase 1: Design API (1 week)
  ├─ Phase 2: Implement JWT (2 weeks)
  │   └─ Task: Implement token refresh
  ├─ Phase 3: Testing (1 week)
  └─ Phase 4: Documentation (1 week)
```

**Day 5: Session Start (uses TodoWrite + Checkpoint)**
```
## Working Memory
[checkpoint] Resume: Implement JWT refresh in src/auth.ts
             Next: Add token refresh handler in AuthService

## Active Goals
[task]       Implement token refresh (in_progress)
[task]       Write refresh tests (pending)
[memory]     Pattern: JWT best practices (refresh before expiry)
```

**During Session: I work (TodoWrite updates)**
```
TodoWrite:
  [✓] Implement token refresh (completed)
  [ ] Write refresh tests (in_progress)
  [ ] Add error handling (pending)

Checkpoint:
  task_id: 101 (links to prospective_tasks.id)
  test_status: failing → passing (auto-run test)
```

**Session End: Changes Persist (TodoWriteSync)**
```
prospective_tasks table:
  id=101: status=completed, updated_at=now()
  id=102: status=in_progress, updated_at=now()
  id=103: status=pending, updated_at=now()
```

**Week End: Analysis (uses execution_feedback)**
```
ExecutionFeedback:
  task_id: 101
  actual_duration_hours: 3.5  (estimated was 4)
  blockers: ["cors_headers_required"]
  lessons_learned: "Always check CORS early"
  success: true
```

---

## Architecture Summary

| Layer | Purpose | Scope | Persistence | Interface |
|-------|---------|-------|-------------|-----------|
| **ProjectPlan** | Long-term structure | Strategic | PostgreSQL | Planning tools |
| **executive_goals** | Hierarchical goals | Strategic | PostgreSQL | Goal manager |
| **prospective_tasks** | All task records | Tactical | PostgreSQL | MemoryBridge |
| **TodoWrite** (NEW) | Session workspace | In-session | JSON → PostgreSQL | Claude context |
| **Checkpoint** (NEW) | Resume point | Per-session | PostgreSQL | Checkpoint mgr |

**Flow**:
```
Long-term planning (ProjectPlan)
  ↓
Creates initial tasks (prospective_tasks)
  ↓
Session loads tasks (TodoWrite via TodoWriteSync)
  ↓
Work on tasks, mark complete (in TodoWrite)
  ↓
Session ends, sync back (TodoWriteSync.save)
  ↓
Consolidate & extract patterns (execution_feedback + planning_patterns)
  ↓
Next planning cycle learns from feedback
```

---

## Schema Changes (Minimal)

**Current prospective_tasks**:
```sql
CREATE TABLE prospective_tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    content TEXT,
    active_form TEXT,
    status VARCHAR(50),
    priority VARCHAR(20),
    created_at INTEGER,
    updated_at INTEGER,
    -- ... 15 more columns
);
```

**After Enhancement**:
```sql
-- ADD these 4 columns (non-breaking):
ALTER TABLE prospective_tasks ADD COLUMN (
    checkpoint_id INTEGER REFERENCES checkpoints(id),      -- NEW
    related_test_name VARCHAR(500),                        -- NEW
    related_file_path VARCHAR(1000),                       -- NEW
    last_claude_sync_at INTEGER                            -- NEW
);

-- Create indexes for faster queries
CREATE INDEX idx_task_checkpoint ON prospective_tasks(checkpoint_id);
CREATE INDEX idx_task_test ON prospective_tasks(related_test_name);
```

**Impact**: Zero breaking changes. Optional columns, existing queries unaffected.

---

## Why This Works

1. **Minimal changes to existing code**
   - ProjectPlan system: untouched ✓
   - planning_patterns: untouched ✓
   - execution_feedback: untouched ✓
   - Just add 4 columns to prospective_tasks ✓

2. **Leverages existing infrastructure**
   - Uses MemoryBridge (already exists) ✓
   - Uses PostgreSQL (already in use) ✓
   - Uses checkpoint system (just built) ✓
   - Uses prospective_tasks (already there) ✓

3. **Clear separation of concerns**
   - ProjectPlan = architecture (weeks/months)
   - prospective_tasks = all tasks (persistent)
   - TodoWrite = active tasks (session view)
   - Checkpoint = resume point (session state)

4. **Graceful degradation**
   - TodoWrite optional (if sync fails, tasks still in DB)
   - Checkpoint optional (tasks work without it)
   - ProjectPlan unchanged (works as before)

---

## Decision Tree: Does It Fit?

```
Q: Does TodoWrite integration replace ProjectPlan?
A: No. ProjectPlan is untouched. TodoWrite is a new layer above.

Q: Does it change how planning patterns work?
A: No. Patterns are in planning module, separate from tasks.

Q: Does it break existing execution feedback?
A: No. ExecutionFeedback works the same way, just on updated tasks.

Q: Do I need to refactor anything?
A: No. Just add 4 columns, create TodoWriteSync module, modify 2 hooks.

Q: Will this mess up my existing project plans?
A: No. ProjectPlan system continues unchanged.

Q: Can I still use planning patterns?
A: Yes. They're separate and untouched.
```

---

## Conclusion

**TodoWrite integration is a **clean addition**, not a replacement.**

```
                    EXISTING                    ADDITIONS
┌──────────────────────────────────┬──────────────────────────┐
│  ProjectPlan (architecture)      │  TodoWrite (interface)    │
│  PhasePlan (phases)              │  TodoWriteSync (sync)     │
│  prospective_tasks (records)     │  +4 columns to table      │
│  executive_goals (hierarchy)     │  Checkpoint links         │
│  planning_patterns (strategies)  │                          │
│  execution_feedback (learning)   │                          │
│                                  │                          │
│  ✓ Unchanged                     │  ✓ New layer              │
│  ✓ Still working                 │  ✓ Builds on top          │
│  ✓ All dependencies intact       │  ✓ No rework needed       │
└──────────────────────────────────┴──────────────────────────┘
```

Ready to implement Phase 1?
