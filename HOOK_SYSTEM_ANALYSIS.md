# Athena Hook System Architecture - Comprehensive Analysis

## Executive Summary

The Athena hook system is a sophisticated event-driven architecture that captures the complete lifecycle of sessions, conversations, tasks, and memory operations. It consists of three main components:

1. **HookDispatcher** - Core session/conversation/task lifecycle hooks
2. **HookEventBridge** - Bridges hooks with task automation events
3. **UnifiedHookSystem** - High-level interface combining both

The system integrates deeply with episodic memory recording, consolidation pipelines, and includes advanced safety mechanisms (idempotency, rate limiting, cascade detection).

---

## 1. HookDispatcher - Main Hook System

**Location**: `/home/user/.work/athena/src/athena/hooks/dispatcher.py`

### Class Structure

```python
class HookDispatcher:
    def __init__(self, db: Database, project_id: int = 1, enable_safety: bool = True)
```

### Key Attributes

- `db`: Database instance (SQLite)
- `project_id`: For memory isolation across projects
- `episodic_store`: Records hook events to episodic memory
- `conversation_store`: Tracks session/conversation state
- `context_snapshot`: Snapshots context for recovery
- `auto_recovery`: Automatic context recovery from episodic memory
- `enable_safety`: Enable/disable safety utilities
- `_active_session_id`: Tracks current session
- `_active_conversation_id`: Tracks current conversation
- `_turn_count`: Conversation turn counter
- `_hook_registry`: Metadata about all hooks

### Supported Hooks (13 Total)

| Hook ID | Method | Purpose | Records Event |
|---------|--------|---------|----------------|
| `session_start` | `fire_session_start()` | Session lifecycle starts | ✓ ACTION |
| `session_end` | `fire_session_end()` | Session lifecycle ends | ✓ ACTION |
| `conversation_turn` | `fire_conversation_turn()` | After user-assistant exchange | ✓ CONVERSATION |
| `user_prompt_submit` | `fire_user_prompt_submit()` | User submits prompt (+ context recovery) | ✓ CONVERSATION |
| `assistant_response` | `fire_assistant_response()` | Assistant generates response | ✓ CONVERSATION |
| `task_started` | `fire_task_started()` | Task begins execution | ✓ ACTION |
| `task_completed` | `fire_task_completed()` | Task finishes (success/failure) | ✓ SUCCESS/ERROR |
| `error_occurred` | `fire_error_occurred()` | Error is caught | ✓ ERROR |
| `pre_tool_use` | `fire_pre_tool_use()` | Before tool execution | ✓ ACTION |
| `post_tool_use` | `fire_post_tool_use()` | After tool execution | ✓ SUCCESS/ERROR |
| `consolidation_start` | `fire_consolidation_start()` | Consolidation begins | ✓ ACTION |
| `consolidation_complete` | `fire_consolidation_complete()` | Consolidation finishes | ✓ SUCCESS |
| `pre_clear` | `dispatch_pre_clear_hook()` | Before clearing working memory | ✓ ACTION |

### Hook Method Signature Pattern

All fire_* methods follow this pattern:

```python
def fire_<hook_name>(self, param1: str, param2: Optional[str] = None) -> int:
    """Called when <event> occurs.
    
    Args:
        param1: Description
        param2: Optional description
    
    Returns:
        Event ID (integer) that was recorded to episodic memory
    """
    def _execute():
        # Auto-start session if needed
        if not self._active_session_id:
            self.fire_session_start()
        
        # Create and record episodic event
        event = EpisodicEvent(
            project_id=self.project_id,
            session_id=self._active_session_id,
            event_type=EventType.ACTION,  # or CONVERSATION, SUCCESS, ERROR
            content=formatted_content,
            outcome=EventOutcome.SUCCESS,  # or FAILURE, ONGOING
            context=EventContext(task=task, phase=phase),
            learned=learning_summary,
            confidence=1.0,
        )
        
        return self.episodic_store.record_event(event)
    
    context = {hash_based_identifiers}
    return self._execute_with_safety("hook_id", context, _execute)
```

---

## 2. Safety System - Three Protection Layers

The `_execute_with_safety()` method applies three mechanisms:

### Layer 1: Idempotency Tracker

**Location**: `/home/user/.work/athena/src/athena/hooks/lib/idempotency_tracker.py`

```python
class IdempotencyTracker:
    def __init__(self, execution_window_seconds: int = 30, max_history: int = 1000)
```

**Mechanism**:
- Computes SHA256 fingerprint of hook_id + context
- Prevents re-execution within 30-second grace period
- Supports explicit idempotency keys
- Returns cached result if duplicate detected

**Example**:
```python
if self.idempotency_tracker.is_duplicate(hook_id, context):
    last_exec = self.idempotency_tracker.get_last_execution(hook_id)
    return last_exec.result  # Return cached result silently
```

### Layer 2: Rate Limiter

**Location**: `/home/user/.work/athena/src/athena/hooks/lib/rate_limiter.py`

**Mechanism**:
- Limits hook execution frequency per hook
- Prevents execution storms
- Tracks execution history with timestamps
- Raises RuntimeError if rate limit exceeded

**Example**:
```python
if not self.rate_limiter.allow_execution(hook_id):
    wait_time = self.rate_limiter.get_estimated_wait_time(hook_id)
    raise RuntimeError(f"Hook {hook_id} rate limited. Wait {wait_time:.2f}s")
```

### Layer 3: Cascade Monitor

**Location**: `/home/user/.work/athena/src/athena/hooks/lib/cascade_monitor.py`

```python
class CascadeMonitor:
    def __init__(self, max_depth: int = 5, max_breadth: int = 10)
```

**Detects**:
- **Cycles**: Hook A triggers B which triggers A (circular)
- **Deep nesting**: Call depth exceeds 5 levels
- **Breadth explosion**: One hook triggers >10 other hooks

**Mechanism**:
```python
def push_hook(self, hook_id: str) -> bool:
    # Check for cycle in call stack
    if self._call_stack.contains(hook_id):
        raise ValueError(f"Hook cycle detected: {' -> '.join(cycle_path)}")
    
    # Check depth limit
    if self._call_stack.depth >= self.max_depth:
        raise ValueError(f"Hook depth limit exceeded")
    
    # Check breadth limit
    if self._triggered_hooks[hook_id] > self.max_breadth:
        raise ValueError(f"Hook breadth limit exceeded")
```

---

## 3. HookEventBridge - Event System Integration

**Location**: `/home/user/.work/athena/src/athena/hooks/bridge.py`

### Architecture

```
HookDispatcher (Session/Conversation lifecycle)
         ↓
    HookEventBridge (Router)
         ↓
EventHandlers (Task automation events)
         ↓
Automation Rules (Triggered actions)
         ↓
Episodic Memory (Consolidation feedback)
```

### Bridge Methods

| Method | Maps Hook To | Event Type |
|--------|--------------|-----------|
| `on_task_started()` | `fire_task_started()` | `task_created` |
| `on_task_completed()` | `fire_task_completed()` | `task_completed` |
| `on_consolidation_start()` | `fire_consolidation_start()` | `task_status_changed` |
| `on_error_occurred()` | `fire_error_occurred()` | `health_degraded` |

**Example Bridge Method**:
```python
async def on_task_started(
    self, task_id: str, task_description: str, goal: Optional[str] = None
) -> None:
    if not self._is_enabled:
        return
    
    try:
        # Route hook event to automation event system
        await self.event_handlers.trigger_event(
            event_type="task_created",
            entity_id=task_id,
            entity_type="task",
            metadata={
                "description": task_description,
                "goal": goal,
                "session_id": self.hook_dispatcher.get_active_session_id(),
            },
        )
        self._event_mapping_count += 1
    except Exception as e:
        logger.error(f"Error triggering task_created event: {e}")
```

### Bridge Statistics

```python
def get_bridge_stats(self) -> dict:
    return {
        "enabled": self._is_enabled,
        "events_routed": self._event_mapping_count,
        "hook_dispatcher_stats": self.hook_dispatcher.get_all_hook_stats(),
        "listener_info": self.event_handlers.get_listener_info(),
    }
```

---

## 4. UnifiedHookSystem - High-Level Interface

**Location**: `/home/user/.work/athena/src/athena/hooks/bridge.py`

```python
class UnifiedHookSystem:
    def __init__(self, hook_dispatcher: HookDispatcher, event_handlers: EventHandlers)
```

### Unified Pipeline

```
Hook -> Event -> Automation -> Episodic Memory -> Consolidation -> Semantic Memory
```

### Methods

```python
def get_system_status() -> dict:
    # Returns comprehensive status including hooks, events, bridge

def enable_all() -> None:
    # Enable all hooks and events

def disable_all() -> None:
    # Disable all hooks and events

def reset_all_stats() -> None:
    # Reset all statistics
```

---

## 5. Current Integration Points

### With Episodic Memory

Every hook call records an EpisodicEvent:

```python
event = EpisodicEvent(
    project_id=self.project_id,
    session_id=self._active_session_id,
    event_type=EventType.ACTION,      # or CONVERSATION, SUCCESS, ERROR
    content=content_string,
    outcome=EventOutcome.SUCCESS,     # or FAILURE, ONGOING, PARTIAL
    context=EventContext(task=..., phase=...),
    learned=learning_summary,
    confidence=confidence_score,
    duration_ms=duration_milliseconds,  # For performance tracking
)

self.episodic_store.record_event(event)
```

### With Consolidation System

**Hooks that trigger consolidation**:
- `fire_consolidation_start(event_count, phase)` - Recorded when consolidation begins
- `fire_consolidation_complete(patterns_found, duration_ms, quality_score)` - Recorded when consolidation finishes

These events feed back into episodic memory:
```python
event = EpisodicEvent(
    content=f"Consolidation completed: extracted {patterns_found} patterns",
    outcome=EventOutcome.SUCCESS,
    learned=f"Consolidation quality: {quality_score:.2%}",
    duration_ms=consolidation_time_ms,
)
```

### With Auto-Recovery (Context Recovery)

The `fire_user_prompt_submit()` hook includes automatic context recovery:

```python
def fire_user_prompt_submit(self, prompt: str, task: Optional[str] = None) -> int:
    # Check if prompt is asking for context recovery
    self._last_recovery_context = self.check_context_recovery_request(prompt)
    
    # If recovery triggered, synthesize context from episodic memory
    recovery_context = self.auto_recovery.auto_recover_context()
    # Returns: {"status": "recovered", "active_work": "...", "current_phase": "..."}
```

Access recovered context via:
```python
recovery_ctx = dispatcher.get_last_recovery_context()
```

---

## 6. Missing Integrations - SessionContextManager

**Location**: `/home/user/.work/athena/src/athena/session/context_manager.py`

### Current State

The SessionContextManager exists but is NOT integrated with HookDispatcher:

```python
class SessionContextManager:
    """Manages session contexts for query-aware retrieval."""
    
    def __init__(self, db: Database)
    def start_session(session_id, project_id, task, phase) -> SessionContext
    def record_event(session_id, event_type, event_data)
    def update_context(phase=None, task=None)
    def get_current_session() -> SessionContext
    def end_session(session_id) -> bool
```

### Integration Gaps

**MISSING**:
1. No coordination between HookDispatcher.fire_session_start() and SessionContextManager.start_session()
2. No automatic event recording via SessionContextManager.record_event()
3. No phase/task transition tracking when hook fires
4. No session state queries via hooks

---

## 7. Missing Integrations - Working Memory API

**Location**: `/home/user/.work/athena/src/athena/working_memory/` (multiple files)

### Current State

Working Memory has multiple layers:
- `central_executive.py` - Manages working memory coordination
- `episodic_buffer.py` - Binds information from phonological loop + visuospatial
- `phonological_loop.py` - Verbal information (7±2 items)
- `visuospatial_sketchpad.py` - Spatial information
- `capacity_enforcer.py` - Enforces Baddeley's 7±2 limit

### Integration Gaps

**MISSING**:
1. No hook fired when working memory capacity threshold reached
2. No hook fired when working memory cleared (partial integration via `dispatch_pre_clear_hook()`)
3. No working memory state snapshot in hooks
4. No consolidation-triggered working memory refresh

---

## 8. Integration Points for SessionContextManager

### Option 1: Tight Integration (Recommended)

```python
class HookDispatcher:
    def __init__(self, db: Database, project_id: int = 1, 
                 session_context_manager: Optional[SessionContextManager] = None):
        self.session_context_mgr = session_context_manager or SessionContextManager(db)
    
    def fire_session_start(self, session_id: Optional[str] = None, context: Optional[dict] = None) -> str:
        def _execute():
            # 1. Create session in conversation store (existing)
            self.conversation_store.create_session(session_id, self.project_id)
            
            # 2. ALSO create in session context manager (NEW)
            self.session_context_mgr.start_session(
                session_id=session_id,
                project_id=self.project_id,
                task=context.get("task") if context else None,
                phase=context.get("phase") if context else None,
            )
            
            # 3. Record episodic event (existing)
            event = EpisodicEvent(...)
            self.episodic_store.record_event(event)
            
            return session_id
```

### Option 2: Event-Based Integration

```python
class HookDispatcher:
    def fire_session_start(self, ...):
        # After recording episodic event, notify SessionContextManager
        self.session_context_mgr.record_event(
            session_id=session_id,
            event_type="hook_session_start",
            event_data={
                "task": context.get("task"),
                "phase": context.get("phase"),
                "timestamp": datetime.now().isoformat(),
            }
        )

class SessionContextManager:
    async def on_hook_event(self, hook_id: str, event_data: dict):
        """Called by HookDispatcher when hook fires."""
        if hook_id == "session_start":
            self.start_session(...)
        elif hook_id == "session_end":
            self.end_session(...)
```

### Option 3: Shared State

```python
class HookDispatcher:
    def __init__(self, db: Database, ...):
        self.session_context_mgr = SessionContextManager(db)
        # Share reference to active session
        self._session_context: Optional[SessionContext] = None
    
    def fire_session_start(self, ...):
        session_ctx = self.session_context_mgr.start_session(...)
        self._session_context = session_ctx
        
    def get_session_context(self) -> Optional[SessionContext]:
        return self._session_context
```

---

## 9. Hook Coordination - Phase 5/6 Integration

**Location**: `/home/user/.work/athena/src/athena/integration/hook_coordination.py`

### Five Optimized Hooks

1. **SessionStartOptimizer**
   - Loads context via smart_retrieve
   - Checks cognitive load
   - Loads active goals
   - Validates goal plans (Phase 6)
   - Checks consolidation status

2. **SessionEndOptimizer**
   - Runs consolidation cycle
   - Extracts planning patterns (Phase 6)
   - Measures consolidation quality
   - Strengthens associations
   - Records execution progress

3. **UserPromptOptimizer**
   - Detects knowledge gaps
   - Monitors task health (Phase 5)
   - Suggests improvements
   - Analyzes project patterns

4. **PostToolOptimizer**
   - Tracks tool performance
   - Updates task progress
   - Monitors consolidation throughput
   - Validates planning duration

5. **PreExecutionOptimizer**
   - Validates plan structure
   - Verifies formal properties (Phase 6)
   - Runs scenario stress tests
   - Assesses execution readiness

**MCP Handlers**: `/home/user/.work/athena/src/athena/mcp/handlers_hook_coordination.py`

---

## 10. Test Coverage

### Unit Tests

- `tests/unit/test_hook_dispatcher_safety_integration.py` - Safety mechanisms
- `tests/unit/test_phase_3_hook_dispatcher.py` - Core dispatcher

### Integration Tests

- `tests/integration/test_hook_system_integration.py` - End-to-end hooks
- `tests/integration/test_hook_coordination.py` - Optimized hooks
- `tests/integration/test_hooks_smoke.py` - Smoke tests
- `tests/integration/test_phase5_hooks_simple.py` - Phase 5 hooks
- `tests/integration/test_phase_2_hooks.py` - Phase 2 hooks

### MCP Tests

- `tests/mcp/tools/test_hook_coordination_tools.py` - MCP tool tests

---

## 11. Hook Registry & Introspection

### Get Hook Statistics

```python
# Get all hook stats
all_stats = dispatcher.get_all_hook_stats()
# Returns: {hook_id: {enabled, execution_count, last_error, ...}}

# Get single hook stats
hook_stats = dispatcher.get_hook_stats("session_start")

# Get safety statistics
safety_stats = dispatcher.get_safety_stats()
# Returns: {idempotency: {...}, rate_limit: {...}, cascade: {...}}

# Check if hook is enabled
is_enabled = dispatcher.is_hook_enabled("consolidation_start")

# Enable/disable hooks
dispatcher.enable_hook("consolidation_start")
dispatcher.disable_hook("task_completed")

# Reset statistics
dispatcher.reset_hook_stats("session_start")  # Single hook
dispatcher.reset_hook_stats()  # All hooks
```

### Hook Registry Structure

```python
{
    "session_start": {
        "enabled": True,
        "execution_count": 42,
        "last_error": None
    },
    "consolidation_complete": {
        "enabled": True,
        "execution_count": 3,
        "last_error": "Consolidation timeout"
    },
    ...
}
```

---

## 12. Error Handling & Recovery

### Graceful Degradation

The `_execute_with_safety()` method ensures:
1. **Idempotency failures** → Return cached result
2. **Rate limit violations** → Raise RuntimeError (caller handles)
3. **Cascade violations** → Raise RuntimeError (caller handles)
4. **Hook execution errors** → Record in registry, propagate

### Exception Handling Pattern

```python
def _execute_with_safety(self, hook_id, context, func):
    try:
        result = func()
        self.idempotency_tracker.record_execution(hook_id, context, result)
        self._hook_registry[hook_id]["execution_count"] += 1
        return result
    except Exception as e:
        self._hook_registry[hook_id]["last_error"] = str(e)
        raise  # Always propagate after recording
    finally:
        self.cascade_monitor.pop_hook()  # Always pop from stack
```

---

## 13. Key Design Patterns

### Pattern 1: Hook Lifecycle

```
Hook fired (fire_*) 
  ↓
Check enabled status
  ↓
Apply safety checks (idempotency, rate limit, cascade)
  ↓
Execute hook function
  ↓
Create EpisodicEvent
  ↓
Record to database
  ↓
Update hook registry stats
  ↓
Return event ID
```

### Pattern 2: Auto-Session Creation

Most hooks auto-start a session if none active:

```python
if not self._active_session_id:
    self.fire_session_start()
```

This ensures every hook is tied to a session automatically.

### Pattern 3: Context Passing

Context includes task and phase for memory refinement:

```python
event = EpisodicEvent(
    context=EventContext(
        task="Implement authentication",
        phase="coding"
    )
)
```

This allows consolidation to understand task context.

---

## 14. Next Steps for SessionContextManager Integration

### Phase 1: Basic Sync
1. Pass SessionContextManager to HookDispatcher
2. Call `session_context_mgr.start_session()` in `fire_session_start()`
3. Call `session_context_mgr.end_session()` in `fire_session_end()`
4. Call `session_context_mgr.record_event()` for each hook

### Phase 2: Phase/Task Transitions
1. Fire hook when `update_context(phase=...)` called
2. Add new hook type: `phase_changed`, `task_changed`
3. Update SessionContext automatically

### Phase 3: Consolidation Feedback
1. Pass consolidation quality metrics to SessionContext
2. Track consolidation history in session
3. Enable query refinement based on session history

### Phase 4: Working Memory Sync
1. Snapshot working memory state in SessionContext
2. Fire hook when capacity threshold reached
3. Enable working memory recovery after clear

---

## Summary

The Athena hook system is production-ready and comprehensive, providing:

- **13 lifecycle hooks** capturing complete session/task/memory lifecycle
- **3-layer safety system** preventing duplicates, storms, and cycles
- **Event bridge** connecting hooks to task automation
- **Deep episodic integration** - every hook records to long-term memory
- **Introspection & monitoring** - complete statistics on all hooks
- **Phase 5/6 optimization** - advanced planning and consolidation hooks

**Key missing piece**: Integration with SessionContextManager for query-aware session tracking.

The analysis shows exactly where and how to integrate SessionContextManager for maximum benefit.

