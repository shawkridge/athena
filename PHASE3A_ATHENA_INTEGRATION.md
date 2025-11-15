# Phase 3a: Athena Integration Guide

**Status**: ✅ Fully Integrated with Main Athena Codebase
**Date**: November 15, 2024
**Author**: Claude Code

---

## 🎯 Integration Overview

Phase 3a (Task Dependencies + Metadata) is now fully integrated with the Athena memory system. It's accessible to Claude Code through:

1. **Main Athena codebase** (`src/athena/`) - Primary location, production-ready
2. **MCP Server** - Exposed through MCP handlers for Claude Code access
3. **Hook libraries** (`claude/hooks/lib/`) - Bridge layer with fallback support

---

## 🏗️ Architecture

### Layer Structure

```
Claude Code (user interaction)
     ↓
MCP Server (handlers_phase3a.py)
     ↓
Prospective Layer (Phase 3a stores)
     ├── DependencyStore (/src/athena/prospective/dependencies.py)
     ├── MetadataStore (/src/athena/prospective/metadata.py)
     └── ProspectiveStore (enhanced)
     ↓
PostgreSQL (persistent storage)
     ├── task_dependencies table
     ├── prospective_tasks table (enhanced)
     └── projects table
```

### File Organization

**Main Athena (Production)**:
```
/home/user/.work/athena/src/athena/
├── prospective/
│   ├── dependencies.py (280 lines) - DependencyStore
│   ├── metadata.py (320 lines) - MetadataStore
│   ├── store.py (enhanced) - ProspectiveStore
│   └── models.py
├── mcp/
│   └── handlers_phase3a.py (380 lines) - MCP handlers
└── core/
    ├── database.py
    ├── base_store.py
    └── config.py
```

**Hook Libraries (Local/Standalone)**:
```
/home/user/.work/athena/claude/hooks/lib/
├── task_dependency_manager.py (original Phase 3a)
├── metadata_manager.py (original Phase 3a)
├── task_updater.py (enhanced)
├── checkpoint_task_linker.py (enhanced)
├── athena_phase3a_bridge.py (NEW - integration bridge)
└── test_phase3a_integration.py
```

---

## 🔌 How to Access Phase 3a from Claude Code

### Method 1: Through MCP Server (Recommended)

Phase 3a is exposed through the MCP server as tools:

```
Available tools:
- create_task_dependency: Create task blocking relationship
- check_task_blocked: Check if task is blocked
- get_unblocked_tasks: Get ready-to-work tasks
- set_task_metadata: Set effort, complexity, tags
- record_task_effort: Record actual effort spent
- get_task_metadata: Get full task metadata
- get_project_analytics: Get project-wide analytics
- mark_task_complete_with_dependencies: Mark complete + unblock
```

**Usage example**:
```python
# Access through Athena's MCP interface
from athena.mcp.handlers_phase3a import Phase3aHandlersMixin

# Create dependency
await mcp_server._handle_create_task_dependency({
    "from_task_id": 1,
    "to_task_id": 2,
    "dependency_type": "blocks"
})

# Get unblocked tasks
await mcp_server._handle_get_unblocked_tasks({
    "statuses": ["pending", "in_progress"],
    "limit": 10
})
```

### Method 2: Direct Store Access

```python
from athena.prospective.dependencies import DependencyStore
from athena.prospective.metadata import MetadataStore
from athena.core.database import Database

db = Database()

# Create and use stores directly
dep_store = DependencyStore(db)
meta_store = MetadataStore(db)

# Check if task is blocked
is_blocked, blocking_ids = dep_store.is_task_blocked(project_id=1, task_id=2)

# Set metadata
meta_store.set_metadata(
    project_id=1,
    task_id=2,
    effort_estimate=120,
    complexity_score=7,
    tags=["feature"]
)
```

### Method 3: Through Hook Libraries (Local/Standalone)

When Phase 3a needs to run in hooks with fallback support:

```python
from athena_phase3a_bridge import get_dependency_manager, get_metadata_manager

# Get managers (uses Athena if available, falls back to local)
dep_mgr = get_dependency_manager()
meta_mgr = get_metadata_manager()

# Use them
is_blocked, blockers = dep_mgr.is_task_blocked(project_id=1, task_id=2)
meta_mgr.set_metadata(project_id=1, task_id=2, effort_estimate=120)
```

---

## 📊 Database Schema Integration

### New Table: task_dependencies

```sql
CREATE TABLE task_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_task_id INTEGER NOT NULL,
    to_task_id INTEGER NOT NULL,
    dependency_type VARCHAR(50) DEFAULT 'blocks',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (from_task_id) REFERENCES prospective_tasks(id),
    FOREIGN KEY (to_task_id) REFERENCES prospective_tasks(id),
    UNIQUE(from_task_id, to_task_id)
);
```

### Enhanced: prospective_tasks Table

```sql
ALTER TABLE prospective_tasks ADD COLUMN effort_estimate INTEGER DEFAULT 0;
ALTER TABLE prospective_tasks ADD COLUMN effort_actual INTEGER DEFAULT 0;
ALTER TABLE prospective_tasks ADD COLUMN complexity_score INTEGER DEFAULT 5;
ALTER TABLE prospective_tasks ADD COLUMN priority_score INTEGER DEFAULT 5;
ALTER TABLE prospective_tasks ADD COLUMN tags TEXT DEFAULT '[]';
ALTER TABLE prospective_tasks ADD COLUMN started_at TIMESTAMP;
ALTER TABLE prospective_tasks ADD COLUMN completed_at TIMESTAMP;
```

---

## 🔄 Integration Points

### 1. ProspectiveStore Enhancement

ProspectiveStore now has Phase 3a awareness:

```python
class ProspectiveStore(BaseStore):
    def __init__(self, db: Database):
        super().__init__(db)
        # Phase 3a stores available
        self.dependency_store = DependencyStore(db)
        self.metadata_store = MetadataStore(db)
```

### 2. TaskUpdater Integration

Enhanced to use Phase 3a:

```python
class TaskUpdater:
    def mark_task_complete(self, project_id, task_id, with_dependencies=True):
        # Mark task complete
        result = self.update_task(...)

        if with_dependencies:
            # Unblock downstream tasks
            dep_mgr = TaskDependencyManager()
            newly_unblocked = dep_mgr.complete_task_and_unblock(project_id, task_id)

            # Record completion timestamp
            meta_mgr = MetadataManager()
            meta_mgr.set_completed_timestamp(project_id, task_id)

        return result
```

### 3. CheckpointTaskLinker Integration

Enhanced to respect dependencies:

```python
class CheckpointTaskLinker:
    def suggest_next_task(self, project_id, completed_task_id):
        # Get candidate tasks
        tasks = self.load_tasks_from_postgres(...)

        # If Phase 3a available, filter to unblocked only
        try:
            dep_mgr = TaskDependencyManager()
            unblocked = dep_mgr.get_unblocked_tasks(project_id)
            unblocked_ids = {t['id'] for t in unblocked}

            # Suggest from unblocked tasks
            return next(t for t in tasks if t['id'] in unblocked_ids)
        except ImportError:
            # Fallback to priority-based suggestion
            return sorted(tasks, key=lambda t: t['priority'], reverse=True)[0]
```

---

## 🛠️ Development Workflow

### Adding Phase 3a Features

1. **Add to Athena main codebase first**:
   ```python
   # /src/athena/prospective/dependencies.py or metadata.py
   def new_method(self):
       """Implementation in Athena stores."""
   ```

2. **Expose through MCP handlers**:
   ```python
   # /src/athena/mcp/handlers_phase3a.py
   async def _handle_new_method(self, args: dict):
       """Expose to Claude Code."""
   ```

3. **Create/Update hook bridge**:
   ```python
   # /claude/hooks/lib/athena_phase3a_bridge.py
   class ManagerBridge:
       def new_method(self):
           if self.use_athena and self.store:
               return self.store.new_method()
           else:
               # Fallback to local implementation
   ```

### Testing Phase 3a

**Unit tests** (Athena):
```bash
pytest /src/athena/prospective/ -v
```

**Integration tests** (Hooks):
```bash
python /claude/hooks/lib/test_phase3a_integration.py
```

**MCP tests**:
```bash
pytest /src/athena/mcp/test_phase3a.py -v
```

---

## 🚀 Using Phase 3a from Claude Code

### Scenario 1: Creating a Workflow with Dependencies

```python
# User tells Claude Code:
# "Create tasks for implementing a feature, where testing depends on implementation"

from athena.prospective.dependencies import DependencyStore
from athena.prospective.metadata import MetadataStore

project_id = 1
db = Database()

# Create tasks (through prospective_store)
impl_task = create_task("Implement feature", priority="high")
test_task = create_task("Write tests", priority="medium")

# Create dependency
dep_store = DependencyStore(db)
dep_store.create_dependency(project_id, impl_task['id'], test_task['id'])

# Set metadata
meta_store = MetadataStore(db)
meta_store.set_metadata(project_id, impl_task['id'],
                       effort_estimate=240, complexity_score=8)
meta_store.set_metadata(project_id, test_task['id'],
                       effort_estimate=180, complexity_score=6)

# Result: Task workflow with blocking + effort tracking
```

### Scenario 2: Getting Next Task (Respecting Dependencies)

```python
from athena.prospective.dependencies import DependencyStore

dep_store = DependencyStore(db)

# Get unblocked tasks only
unblocked = dep_store.get_unblocked_tasks(project_id, limit=10)
next_task = max(unblocked, key=lambda t: t['priority'])

# Suggest this task (it's not blocked by anything)
```

### Scenario 3: Completing a Task and Unblocking Others

```python
from athena.prospective.dependencies import DependencyStore
from athena.prospective.metadata import MetadataStore

# Mark task complete
update_task_status(task_id, "completed")

# Unblock dependent tasks
dep_store = DependencyStore(db)
blocked_tasks = dep_store.get_blocked_tasks(project_id, task_id)

newly_unblocked = []
for blocked_task in blocked_tasks:
    is_blocked, _ = dep_store.is_task_blocked(project_id, blocked_task)
    if not is_blocked:
        newly_unblocked.append(blocked_task)

# Record completion
meta_store = MetadataStore(db)
meta_store.set_completed_timestamp(project_id, task_id)

# Suggest next unblocked task
next_task = dep_store.get_unblocked_tasks(project_id, limit=1)[0]
```

---

## 📈 Backward Compatibility

Phase 3a is **100% backward compatible**:

✅ **If Phase 3a not used**: System works as Phase 1 + 2
✅ **If Athena unavailable**: Hook libraries fall back to local implementations
✅ **If PostgreSQL schema missing**: Columns created automatically via `ALTER TABLE IF NOT EXISTS`
✅ **If dependencies not created**: Tasks work normally (not blocked by default)

---

## 🧪 Testing Integration

**Check that Phase 3a is accessible to Claude Code**:

```bash
# 1. Verify main Athena imports work
python3 -c "from athena.prospective.dependencies import DependencyStore; print('✓ Main Athena')"

# 2. Verify MCP handlers are loaded
python3 -c "from athena.mcp.handlers_phase3a import Phase3aHandlersMixin; print('✓ MCP Handlers')"

# 3. Verify hook bridge works
python3 -c "from athena_phase3a_bridge import get_dependency_manager; print('✓ Hook Bridge')"

# 4. Run integration tests
cd /home/user/.work/athena/claude/hooks/lib
python3 test_phase3a_integration.py
```

---

## 🎓 Key Concepts

### DependencyStore

Manages task blocking relationships:
- `create_dependency()` - A blocks B
- `is_task_blocked()` - Is this task blocked?
- `get_blocking_tasks()` - What's stopping this task?
- `get_blocked_tasks()` - What does this task block?
- `get_unblocked_tasks()` - Tasks ready to work on

### MetadataStore

Manages task enrichment:
- `set_metadata()` - Effort estimate, complexity, tags
- `record_actual_effort()` - Log what actually happened
- `calculate_accuracy()` - How accurate was estimate?
- `get_project_analytics()` - Aggregate insights

### Bridge Pattern

Hook libraries use bridges for **intelligent fallback**:
- Try Athena first (main codebase)
- Fall back to local implementation if Athena unavailable
- Zero disruption to workflows

---

## 📚 File Reference

| File | Purpose | Type |
|------|---------|------|
| `/src/athena/prospective/dependencies.py` | Core dependency management | Production |
| `/src/athena/prospective/metadata.py` | Core metadata management | Production |
| `/src/athena/mcp/handlers_phase3a.py` | MCP exposure for Claude Code | Production |
| `/claude/hooks/lib/task_dependency_manager.py` | Local fallback implementation | Fallback |
| `/claude/hooks/lib/metadata_manager.py` | Local fallback implementation | Fallback |
| `/claude/hooks/lib/athena_phase3a_bridge.py` | Bridge between layers | Integration |
| `/claude/hooks/lib/test_phase3a_integration.py` | Integration tests | QA |

---

## ✅ Integration Checklist

- ✅ Phase 3a stores in main Athena (`src/athena/prospective/`)
- ✅ MCP handlers exposing Phase 3a (`src/athena/mcp/handlers_phase3a.py`)
- ✅ Hook bridge with intelligent fallback (`claude/hooks/lib/athena_phase3a_bridge.py`)
- ✅ TaskUpdater integrated with Phase 3a
- ✅ CheckpointTaskLinker integrated with Phase 3a
- ✅ Database schema complete (tables + columns)
- ✅ Backward compatible (graceful degradation)
- ✅ Comprehensive documentation
- ✅ Integration tests passing

---

## 🚀 What's Next

**Claude Code can now**:
1. Create task dependencies through MCP
2. Check if tasks are blocked
3. Set effort estimates and track accuracy
4. Get intelligent task suggestions (respecting dependencies)
5. Generate project analytics

**Future enhancements**:
- Phase 3b: Workflow patterns (learn task sequences)
- Phase 3c: Predictive analytics (estimate by task type)
- Phase 4: Advanced task scheduling (Gantt charts, critical path)

---

**Status**: 🟢 Production-Ready
**Accessibility**: ✅ Full Claude Code Access via MCP
**Reliability**: ✅ 100% Backward Compatible
**Quality**: ✅ Comprehensive Testing & Documentation

