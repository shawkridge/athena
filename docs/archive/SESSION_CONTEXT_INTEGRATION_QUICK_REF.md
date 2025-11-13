# SessionContextManager Integration - Quick Reference

## Current Architecture State

### UnifiedMemoryManager (src/athena/manager.py)
- **Role:** Central query routing engine across 7+ memory layers
- **Key Method:** `retrieve(query, context, k, ...)`
- **Query Types:** 7 linguistic patterns → routing logic
- **Current Gap:** No session context awareness at query time

### HookDispatcher (src/athena/hooks/dispatcher.py)
- **Role:** Session lifecycle management + context recovery
- **Session Tracking:** `_active_session_id`, `_active_conversation_id`, `_turn_count`
- **13 Hooks:** session_start, conversation_turn, user_prompt_submit, etc.
- **Integration Gap:** Sessions tracked independently; not shared with UnifiedMemoryManager

### WorkingMemoryAPI (src/athena/episodic/working_memory.py)
- **Role:** Episodic buffer (7±2 capacity) with consolidation triggers
- **Consolidation:** Routes to semantic/episodic/procedural/prospective layers via ConsolidationRouterV2
- **Integration Gap:** Consolidation events not visible to query context

---

## Key Method Signatures

### UnifiedMemoryManager.retrieve()
```python
def retrieve(
    self,
    query: str,
    context: Optional[dict] = None,      # Currently dict, not SessionContext
    k: int = 5,
    conversation_history: Optional[list[dict]] = None,
    include_confidence_scores: bool = True,
    explain_reasoning: bool = False
) -> dict
```

### HookDispatcher Session Methods
```python
def fire_session_start(session_id: Optional[str], context: Optional[dict]) -> str
def fire_session_end(session_id: Optional[str]) -> bool
def fire_conversation_turn(user_content, assistant_content, ...) -> int
def get_session_state(session_id: Optional[str]) -> dict
```

### WorkingMemoryAPI Push
```python
async def push_async(
    event: EpisodicEvent,
    importance: float = 0.5,
    distinctiveness: float = 0.5
) -> dict  # {event_id, working_memory_size, consolidation_triggered, ...}
```

---

## Integration Points (Priority Order)

### P1: Query Priming (HIGH VALUE)
**File:** `src/athena/manager.py`
**Method:** `retrieve()`
**Change:**
```python
def retrieve(self, query, context=None, session_context=None, auto_load_session=True, ...):
    if auto_load_session and session_context is None and self.session_manager:
        session_context = self.session_manager.get_current_session()
    
    if session_context:
        context = context or {}
        context.update(session_context.to_dict())
```

### P2: Context-Aware Routing (MEDIUM VALUE)
**File:** `src/athena/manager.py`
**Method:** `_classify_query()`
**Change:** Pass `session_context` to inform routing bias
```python
def _classify_query(self, query: str, session_context=None) -> str:
    query_type = self._linguistic_classify(query)
    if session_context:
        query_type = self._refine_query_type(query_type, session_context, query)
    return query_type
```

### P3: Hook-Based Updates (MEDIUM VALUE)
**File:** `src/athena/hooks/dispatcher.py`
**Methods:** `fire_session_start()`, `fire_conversation_turn()`, etc.
**Change:** Notify SessionContextManager of lifecycle events
```python
def fire_session_start(self, session_id, context):
    session_context = self.session_manager.start_session(...)
    # existing code...
```

### P4: Consolidation Tracking (MEDIUM VALUE)
**File:** `src/athena/episodic/working_memory.py`
**Method:** `_trigger_consolidation_async()`
**Change:** Record consolidation in SessionContextManager
```python
async def _trigger_consolidation_async(...):
    # existing code...
    if self.session_manager:
        self.session_manager.record_consolidation(
            wm_size=size,
            consolidation_run_id=consolidation_run_id
        )
```

### P5: Context Recovery (LOW VALUE)
**File:** `src/athena/hooks/dispatcher.py`
**Method:** `check_context_recovery_request()`
**Change:** Use SessionContextManager for structured recovery
```python
def check_context_recovery_request(self, prompt):
    if self.auto_recovery.should_trigger_recovery(prompt):
        if self.session_manager:
            return self.session_manager.recover_context(...)
        else:
            return self.auto_recovery.auto_recover_context()
```

---

## Data Flow Examples

### Current: Query Without Session Context
```
User Query
    ↓
retrieve(query="what was the last action?", context=None)
    ↓
_classify_query() → TEMPORAL
    ↓
_query_episodic() → searches all episodic events (no session filtering)
    ↓
Results (includes events from other sessions)
```

### Proposed: Query With Session Context
```
User Query
    ↓
retrieve(query="what was the last action?", auto_load_session=True)
    ↓
Load current session context → SessionContext(session_id="...", task="...", phase="...")
    ↓
_classify_query() → TEMPORAL (refined by context if in debugging phase)
    ↓
_query_episodic(context={"session_id": "..."}) → filters to current session only
    ↓
Results (only recent events in current session)
```

### Working Memory Consolidation Flow
```
WorkingMemoryAPI.push_async(event)
    ↓
Size check: if >= capacity:
    ↓
    HookDispatcher.fire_consolidation_start()
        ↓
        SessionContextManager.record_consolidation_start()
    ↓
    ConsolidationRouterV2.route_async() → target_layer
    ↓
    SessionContextManager.record_consolidation_complete()
        ↓
        Record: wm_item → target_layer + confidence
        ↓
        Update SessionContext.consolidation_history
    ↓
Next retrieve() call has consolidated_items in context
```

---

## Store Classes Affected

| Store | Integration Type | Impact |
|-------|------------------|--------|
| `EpisodicStore` | Query context filtering | Filter events by session_id |
| `MemoryStore` | Semantic search context | Bias results by task/phase |
| `ProceduralStore` | Task-aware procedures | Surface procedures matching current task |
| `ProspectiveStore` | Task visibility | Filter tasks by current session |
| `GraphStore` | Entity/relation context | Filter by relevant domain |
| `MetaMemoryStore` | Domain expertise tracking | Track expertise per session/phase |
| `ConsolidationSystem` | Consolidation events | Record what was consolidated in session |
| `WorkingMemoryAPI` | Consolidation triggers | Notify SessionContextManager |

---

## Files to Modify

### Core Changes
1. **src/athena/manager.py** (782 lines)
   - Add `session_manager` parameter to `__init__`
   - Modify `retrieve()` signature to accept `session_context` + `auto_load_session`
   - Update `_classify_query()` to accept `session_context`
   - Add `_merge_session_context()` helper
   - Add `_refine_query_type()` helper

2. **src/athena/hooks/dispatcher.py** (893 lines)
   - Add `session_manager` parameter to `__init__`
   - Update `fire_session_start()`, `fire_session_end()`, `fire_conversation_turn()` to notify manager
   - Update `check_context_recovery_request()` to use manager

3. **src/athena/episodic/working_memory.py** (494 lines)
   - Add `session_manager` parameter to `__init__`
   - Notify manager in `_trigger_consolidation_async()`

### New File
4. **src/athena/session/context_manager.py** (new file)
   - `SessionContextManager` class
   - `SessionContext` data class
   - Storage/retrieval in database

---

## Database Schema Additions

### session_contexts table
```sql
CREATE TABLE IF NOT EXISTS session_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    task TEXT,
    phase TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### session_context_events table
```sql
CREATE TABLE IF NOT EXISTS session_context_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT,  -- task_started, consolidation_complete, phase_changed, etc.
    event_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES session_contexts(session_id)
);
```

---

## Testing Strategy

### Unit Tests
- `test_session_context_manager.py` - Core CRUD operations
- `test_unified_manager_with_session.py` - Query priming
- `test_hook_dispatcher_integration.py` - Hook notifications

### Integration Tests
- Session creation → query context loading → retrieval
- Consolidation → SessionContext updates → query bias
- Context recovery with SessionContextManager

### E2E Test
- Full workflow: session start → queries → consolidation → context recovery

---

## Backward Compatibility

### Graceful Degradation
```python
# If SessionContextManager not provided:
if auto_load_session and self.session_manager:  # Only if manager exists
    session_context = self.session_manager.get_current_session()

# Query still works without session context (returns all results)
```

### Dict-Based Context Still Supported
```python
# Old code still works:
retrieve(query="...", context={"task": "...", "phase": "..."})

# New code:
retrieve(query="...", session_context=session_context)

# Both work simultaneously
```

---

## Expected Benefits

### Immediate (P1)
- Session-aware queries
- No context pollution across sessions
- Better recall for "what were we working on?"

### Short-term (P2-P3)
- Context-biased routing (phase awareness)
- Automatic context updates via hooks
- Better result ranking per session state

### Long-term (P4-P5)
- Consolidation visibility in queries
- Richer context recovery
- Session-based query analytics

