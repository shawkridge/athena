# Hook System Quick Reference

## File Locations

```
src/athena/hooks/
├── dispatcher.py                    # Main HookDispatcher class (989 lines)
├── bridge.py                        # HookEventBridge + UnifiedHookSystem (250 lines)
├── mcp_wrapper.py                   # MCP operation fallbacks (172 lines)
├── __init__.py                      # Public exports
└── lib/
    ├── idempotency_tracker.py       # Deduplication (200+ lines)
    ├── rate_limiter.py              # Execution frequency limiting
    ├── cascade_monitor.py           # Cycle/depth/breadth detection (170+ lines)
    └── __init__.py

src/athena/integration/
└── hook_coordination.py             # Phase 5/6 optimized hooks (400 lines)
    ├── SessionStartOptimizer
    ├── SessionEndOptimizer
    ├── UserPromptOptimizer
    ├── PostToolOptimizer
    └── PreExecutionOptimizer

src/athena/mcp/
├── handlers_hook_coordination.py    # MCP handler stubs (200+ lines)
└── tools/hook_coordination_tools.py # Tool definitions (300+ lines)

src/athena/session/
└── context_manager.py               # SessionContextManager (NOT YET INTEGRATED)

src/athena/working_memory/
├── episodic_buffer.py               # Episodic buffer integration
├── phonological_loop.py
├── visuospatial_sketchpad.py
├── central_executive.py
└── capacity_enforcer.py
```

## The 13 Hooks

```
LIFECYCLE HOOKS:
1. fire_session_start()           → EventType.ACTION
2. fire_session_end()             → EventType.ACTION
3. fire_conversation_turn()       → EventType.CONVERSATION
4. fire_user_prompt_submit()      → EventType.CONVERSATION (+ context recovery)
5. fire_assistant_response()      → EventType.CONVERSATION

TASK HOOKS:
6. fire_task_started()            → EventType.ACTION
7. fire_task_completed()          → EventType.SUCCESS/ERROR
8. fire_error_occurred()          → EventType.ERROR

TOOL HOOKS:
9. fire_pre_tool_use()            → EventType.ACTION
10. fire_post_tool_use()          → EventType.SUCCESS/ERROR

CONSOLIDATION HOOKS:
11. fire_consolidation_start()    → EventType.ACTION
12. fire_consolidation_complete() → EventType.SUCCESS

MEMORY HOOKS:
13. dispatch_pre_clear_hook()     → EventType.ACTION
```

## 3-Layer Safety System

```
Layer 1: IDEMPOTENCY
├── SHA256 fingerprint of (hook_id + context)
├── 30-second execution window
├── Returns cached result if duplicate
└── Prevents accidental re-runs

Layer 2: RATE LIMITING
├── Per-hook execution frequency limit
├── Prevents execution storms
├── Configurable per hook
└── Raises RuntimeError if violated

Layer 3: CASCADE DETECTION
├── Max depth: 5 levels
├── Max breadth: 10 hooks per execution
├── Detects cycles: A → B → A
└── Prevents infinite loops
```

## Hook Execution Flow

```
fire_<hook_name>(params)
    ↓
_execute_with_safety("hook_id", context, _execute)
    ↓
    ├─ Check enabled? (from _hook_registry)
    ├─ Idempotency check (return if duplicate)
    ├─ Rate limit check (fail if exceeded)
    └─ Cascade check (fail if cycle/depth/breadth)
    ↓
_execute() function
    ├─ Auto-start session if needed
    ├─ Create EpisodicEvent
    ├─ Record to database
    └─ Return event_id
    ↓
Record execution stats
    ├─ idempotency_tracker.record_execution()
    ├─ _hook_registry[hook_id]["execution_count"] += 1
    └─ Update safety stats
    ↓
Return event_id (Integer)
```

## Data Flow

```
Hook fires
    ↓
EpisodicEvent created with:
├── event_type (ACTION, CONVERSATION, SUCCESS, ERROR)
├── content (formatted string)
├── outcome (SUCCESS, FAILURE, ONGOING, PARTIAL)
├── context (task, phase)
├── learned (summary of learning)
├── confidence (0.0-1.0)
└── duration_ms (for performance tracking)
    ↓
episodic_store.record_event(event)
    ↓
Database: episodic_events table
    ↓
Consolidation pipeline can query these events
    ↓
Patterns extracted and converted to semantic memory
```

## Integration Points

```
HookDispatcher (core)
    ├── → EpisodicStore (every hook records event)
    ├── → ConversationStore (session/turn tracking)
    ├── → ContextSnapshot (context recovery)
    ├── → AutoContextRecovery (context synthesis)
    └── ← Safety utilities (idempotency, rate limit, cascade)

HookEventBridge (router)
    ├── → EventHandlers (task automation events)
    └── Triggers: task_created, task_completed, task_status_changed, health_degraded

UnifiedHookSystem (coordinator)
    ├── HookDispatcher (lifecycle)
    ├── EventHandlers (automation)
    └── HookEventBridge (router)

Phase 5/6 Optimizers
    ├── SessionStartOptimizer (load context, validate plans)
    ├── SessionEndOptimizer (consolidate, extract patterns)
    ├── UserPromptOptimizer (monitor health, detect gaps)
    ├── PostToolOptimizer (track performance, update progress)
    └── PreExecutionOptimizer (validate, stress test, assess readiness)
```

## Key Methods

### HookDispatcher Core

```python
# Fire hooks (all return int event_id)
fire_session_start(session_id=None, context=None) -> str
fire_session_end(session_id=None) -> bool
fire_conversation_turn(user, assistant, task=None, phase=None) -> int
fire_user_prompt_submit(prompt, task=None, phase=None) -> int
fire_assistant_response(response, task=None, phase=None) -> int
fire_task_started(task_id, task_description, goal=None) -> int
fire_task_completed(task_id, outcome, summary=None) -> int
fire_error_occurred(error_type, error_message, context_str=None) -> int
fire_pre_tool_use(tool_name, tool_params, task=None) -> int
fire_post_tool_use(tool_name, tool_params, result, success=True, error=None) -> int
fire_consolidation_start(event_count, phase="consolidation") -> int
fire_consolidation_complete(patterns_found, duration_ms=0, quality_score=0.0) -> int
dispatch_pre_clear_hook(component="all") -> None

# Query hooks
get_hook_registry() -> Dict[str, Dict[str, Any]]
get_hook_stats(hook_id) -> Optional[Dict]
get_all_hook_stats() -> Dict[str, Dict]
is_hook_enabled(hook_id) -> bool

# Control hooks
enable_hook(hook_id) -> bool
disable_hook(hook_id) -> bool
reset_hook_stats(hook_id=None) -> None

# Session state
get_session_state(session_id=None) -> dict
get_active_session_id() -> Optional[str]
get_last_recovery_context() -> Optional[dict]

# Safety stats
get_safety_stats() -> Dict[str, Any]
```

### Safety Utilities

```python
# IdempotencyTracker
is_duplicate(hook_id, context, idempotency_key=None) -> bool
record_execution(hook_id, context, result=None, idempotency_key=None) -> None
get_last_execution(hook_id) -> Optional[IdempotencyRecord]
get_stats() -> dict

# RateLimiter
allow_execution(hook_id) -> bool
get_estimated_wait_time(hook_id) -> float
get_stats() -> dict

# CascadeMonitor
push_hook(hook_id) -> bool
pop_hook() -> Optional[str]
get_call_stack() -> List[str]
get_depth() -> int
is_at_depth_limit() -> bool
is_at_breadth_limit(hook_id) -> bool
get_stats() -> dict
```

### HookEventBridge

```python
async on_task_started(task_id, task_description, goal=None) -> None
async on_task_completed(task_id, outcome) -> None
async on_consolidation_start(event_count) -> None
async on_error_occurred(error_type, error_message, context_str=None) -> None

enable_bridging() -> None
disable_bridging() -> None
is_enabled() -> bool
get_bridge_stats() -> dict
reset_stats() -> None
```

### UnifiedHookSystem

```python
get_system_status() -> dict  # Hooks + events + bridge status
enable_all() -> None
disable_all() -> None
reset_all_stats() -> None
```

## Hook Registry Structure

```python
{
    "session_start": {
        "enabled": True,
        "execution_count": 42,
        "last_error": None
    },
    "task_completed": {
        "enabled": True,
        "execution_count": 7,
        "last_error": "Database connection timeout"
    },
    # ... one entry per hook ...
}
```

## Safety Stats Structure

```python
{
    "idempotency": {
        "duplicates_prevented": 3,
        "execution_history_size": 15,
        "max_history": 1000,
        # ...
    },
    "rate_limit": {
        "total_rate_limited": 0,
        "per_hook_limits": {...},
        # ...
    },
    "cascade": {
        "cycles_detected": 0,
        "max_depth": 5,
        "max_breadth": 10,
        # ...
    }
}
```

## Missing Integrations

### SessionContextManager
- Location: `src/athena/session/context_manager.py`
- Status: EXISTS but NOT INTEGRATED with HookDispatcher
- Integration gaps:
  1. No call to `session_context_mgr.start_session()` in `fire_session_start()`
  2. No event recording via `session_context_mgr.record_event()`
  3. No phase/task transition tracking
  4. No session state queries via hooks

### Working Memory API
- Location: `src/athena/working_memory/`
- Status: PARTIAL integration (only `dispatch_pre_clear_hook()`)
- Integration gaps:
  1. No hook for capacity threshold reached
  2. No hook for working memory cleared (only pre-clear)
  3. No working memory state snapshot in hooks
  4. No consolidation-triggered refresh

## Usage Example

```python
from athena.core.database import Database
from athena.hooks import HookDispatcher

# Initialize
db = Database("memory.db")
dispatcher = HookDispatcher(db, project_id=1, enable_safety=True)

# Session lifecycle
session_id = dispatcher.fire_session_start(
    session_id="session_001",
    context={"task": "Implement auth", "phase": "coding"}
)

# Task execution
event_id = dispatcher.fire_task_started("task_123", "Implement JWT")
event_id = dispatcher.fire_post_tool_use("semantic_search", {...}, result, success=True)
event_id = dispatcher.fire_task_completed("task_123", EventOutcome.SUCCESS, "JWT implemented")

# Consolidation
event_id = dispatcher.fire_consolidation_start(event_count=45)
event_id = dispatcher.fire_consolidation_complete(patterns_found=5, quality_score=0.82)

# End session
dispatcher.fire_session_end(session_id)

# Monitor
stats = dispatcher.get_all_hook_stats()
safety = dispatcher.get_safety_stats()
session_state = dispatcher.get_session_state(session_id)
```

## Testing

```bash
# Unit tests
pytest tests/unit/test_hook_dispatcher_safety_integration.py -v
pytest tests/unit/test_phase_3_hook_dispatcher.py -v

# Integration tests
pytest tests/integration/test_hook_system_integration.py -v
pytest tests/integration/test_hook_coordination.py -v
pytest tests/integration/test_hooks_smoke.py -v

# MCP tests
pytest tests/mcp/tools/test_hook_coordination_tools.py -v
```

## Design Principles

1. **Every hook is atomic** - All side effects happen within `_execute()`
2. **Every hook is recorded** - Every hook creates an EpisodicEvent
3. **Every hook is safe** - Three layers of protection against problems
4. **Every hook is observable** - Complete statistics in _hook_registry
5. **Every hook auto-sessions** - Hooks automatically create sessions if needed
6. **Every hook is contextual** - Includes task and phase for memory refinement

## Next Steps

### Phase 1: SessionContextManager Integration
- [ ] Modify HookDispatcher.__init__() to accept SessionContextManager
- [ ] Call session_context_mgr.start_session() in fire_session_start()
- [ ] Call session_context_mgr.end_session() in fire_session_end()
- [ ] Call session_context_mgr.record_event() for all hooks

### Phase 2: Working Memory Integration
- [ ] Add hook: fire_working_memory_capacity_threshold()
- [ ] Add hook: fire_working_memory_cleared()
- [ ] Snapshot working memory state in hooks
- [ ] Enable working memory recovery after clear

### Phase 3: Enhanced Monitoring
- [ ] Add hook performance metrics dashboard
- [ ] Export hook statistics to external monitoring
- [ ] Add alerting for cascade/rate limit violations
- [ ] Add hook execution timeline visualization
