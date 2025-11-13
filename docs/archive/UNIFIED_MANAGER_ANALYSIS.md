# UnifiedMemoryManager Architecture Analysis

## Executive Summary

The `UnifiedMemoryManager` is the central orchestration layer that routes queries across 7+ memory layers (Episodic, Semantic, Procedural, Prospective, Knowledge Graph, Meta, Planning, and optional RAG). It provides intelligent query classification, layer routing, result aggregation, and confidence scoring.

**Current Architecture Strengths:**
- Query classification based on linguistic patterns
- Intelligent multi-layer routing (7 query types → appropriate layers)
- Graceful RAG degradation (optional, falls back to basic search)
- Confidence scoring system for result quality
- Working memory integration via capacity triggers
- Hook dispatcher for conversation/session management

**Gap Analysis:**
- Session context is managed separately in HookDispatcher (not in UnifiedMemoryManager)
- No unified session/context loading at query time
- Limited cross-layer context awareness
- No explicit SessionContextManager integration points

---

## 1. Current Recall() Method Signature

### Primary Method: `retrieve()`
```python
def retrieve(
    self,
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    fields: Optional[list[str]] = None,
    conversation_history: Optional[list[dict]] = None,
    include_confidence_scores: bool = True,
    explain_reasoning: bool = False
) -> dict:
```

**Parameters:**
- `query`: Search query string
- `context`: Optional context dict (cwd, files, recent actions, task, phase)
- `k`: Number of results per layer (default 5)
- `fields`: Field projection for response optimization
- `conversation_history`: Recent conversation messages for context-aware queries
- `include_confidence_scores`: Add confidence metrics to results
- `explain_reasoning`: Include query routing explanation

**Return Value:**
```python
{
    "episodic": [list of event results],
    "semantic": [list of memory results],
    "procedural": [list of procedure results],
    # ... other layers
    "confidence": {...},  # If include_confidence_scores=True
    "_explanation": {...},  # If explain_reasoning=True
}
```

**Current Flow:**
```
1. Classify query type (TEMPORAL, FACTUAL, RELATIONAL, PROCEDURAL, PROSPECTIVE, META, PLANNING)
2. Route to appropriate layer(s) based on classification
3. Execute layer-specific queries
4. Track query for meta-memory
5. Apply confidence scores if requested
6. Project fields if requested
7. Return aggregated results
```

---

## 2. Query Routing Logic

### Classification System
```python
class QueryType:
    TEMPORAL = "temporal"        # when, what happened, recent
    FACTUAL = "factual"          # what is, facts, knowledge
    RELATIONAL = "relational"    # depends on, relationships
    PROCEDURAL = "procedural"    # how to, workflow, steps
    PROSPECTIVE = "prospective"  # tasks, reminders, pending
    META = "meta"                # coverage, expertise
    PLANNING = "planning"        # decompose, strategy, validation
```

### Routing Table
| Query Type | Target Layer | Method | Indicators |
|-----------|-------------|--------|-----------|
| TEMPORAL | Episodic | `_query_episodic()` | when, last, recent, yesterday, date, time |
| FACTUAL | Semantic + RAG | `_query_semantic()` | Default; facts, knowledge |
| RELATIONAL | Knowledge Graph | `_query_graph()` | depends, related, connection, uses |
| PROCEDURAL | Procedural | `_query_procedural()` | how to, workflow, process, steps |
| PROSPECTIVE | Prospective | `_query_prospective()` | task, todo, remind, pending |
| META | Meta-Memory | `_query_meta()` | what do we know, coverage, expertise |
| PLANNING | Planning RAG | `_query_planning()` | decompose, plan, strategy, validate |

### Layer-Specific Query Methods

#### `_query_episodic(query, context, k)`
- Checks for date-specific queries (yesterday, week)
- Falls back to general event search
- Returns: `[{event_id, content, timestamp, type}]`

#### `_query_semantic(query, context, k, conversation_history)`
- Uses advanced RAG if available (with conversation history)
- Falls back to reranking if RAG unavailable
- Returns: `[{content, type, similarity, tags}]`

#### `_query_graph(query, context, k)`
- Extracts entity name from query
- Searches entities, retrieves relations
- Returns: `[{entity, type, relations}]`

#### `_query_procedural(query, context, k)`
- Uses context tags (technologies) for filtering
- Returns: `[{name, category, template, success_rate}]`

#### `_query_prospective(query, context, k)`
- Filters by status (pending, ready) if indicated
- Returns: `[{content, status, priority, assignee}]`

#### `_query_meta(query, context, k)`
- Extracts domain from query
- Returns: `{domains: [{domain, memory_count, expertise}]}`

#### `_query_planning(query, context, k)`
- Routes through PlanningRAGRouter
- Returns: `[{type, content, confidence, pattern_type, rationale}]`

### Hybrid Search (`_hybrid_search()`)
When query doesn't match specific type:
1. Semantic search (vector + RAG)
2. Lexical search (BM25)
3. Reciprocal Rank Fusion (RRF) to combine rankings
4. Episodic search (recent 3 results)
5. Procedural search (if workflow-related)
6. Graph search (entity mentions)

---

## 3. Session Management (Current State)

### In HookDispatcher (NOT in UnifiedMemoryManager)
```python
class HookDispatcher:
    def __init__(self, db, project_id, enable_safety):
        # Active session tracking
        self._active_session_id: Optional[str] = None
        self._active_conversation_id: Optional[int] = None
        self._turn_count = 0
        self._last_recovery_context: Optional[dict] = None
```

### Session Lifecycle Hooks
1. **`fire_session_start(session_id, context)`** 
   - Creates session with optional context (task, phase)
   - Records episodic event
   - Returns: session_id

2. **`fire_session_end(session_id)`**
   - Closes session
   - Records end event
   - Clears active session tracking

3. **`fire_conversation_turn(user_content, assistant_content, ...)`**
   - Records turn in conversation store
   - Records episodic event
   - Tracks turn count

4. **`fire_user_prompt_submit(prompt, task, phase)`**
   - Checks for context recovery requests
   - Records episodic event
   - Can trigger auto-recovery

5. **`check_context_recovery_request(prompt)`**
   - Detects recovery patterns
   - Synthesizes context from episodic memory
   - Returns recovery context dict

### Session State Access
```python
def get_session_state(session_id) -> dict:
    return {
        "session_id": session_id,
        "is_active": bool,
        "conversation_count": int,
        "active_conversation_id": int,
        "turn_count": int,
        "conversations": [...]
    }
```

### CRITICAL GAP: Session context is NOT passed to `retrieve()`
**Current behavior:**
- HookDispatcher manages sessions independently
- UnifiedMemoryManager has optional `context` parameter but it's NOT automatically populated
- No integration between session tracking and query routing

---

## 4. Context Loading/Saving Patterns

### ContextSnapshot (in HookDispatcher)
```python
class ContextSnapshot:
    def snapshot_conversation(
        session_id: str,
        conversation_content: str,
        task: str
    ) -> int:  # Returns event_id
```

### AutoContextRecovery
```python
class AutoContextRecovery:
    def should_trigger_recovery(prompt: str) -> bool
    def auto_recover_context() -> dict:
        return {
            "status": "recovered",
            "session_id": str,
            "active_work": str,
            "current_phase": str,
            # ... more context fields
        }
```

### WorkingMemoryAPI (Phase 2)
```python
class WorkingMemoryAPI:
    def __init__(
        db: Database,
        episodic_store: EpisodicStore,
        consolidation_callback: Optional[Callable] = None,
        capacity: int = DEFAULT_CAPACITY
    )
    
    def push_async(event, importance, distinctiveness) -> dict:
        # Triggers consolidation if capacity exceeded
        return {
            "event_id": int,
            "working_memory_size": int,
            "capacity": int,
            "consolidation_triggered": bool,
            "consolidation_run_id": int | None
        }
```

### Consolidation Router V2
Routes working memory items to appropriate long-term memory layers:
- Uses ML-based routing (feature extraction)
- Falls back to heuristics
- Consolidates to: SEMANTIC, EPISODIC, PROCEDURAL, or PROSPECTIVE

---

## 5. Hook Integration Points

### Current Hook System (HookDispatcher)
**Registry of 13 hooks:**
```python
{
    "session_start": {...},
    "session_end": {...},
    "conversation_turn": {...},
    "user_prompt_submit": {...},
    "assistant_response": {...},
    "task_started": {...},
    "task_completed": {...},
    "error_occurred": {...},
    "pre_tool_use": {...},
    "post_tool_use": {...},
    "consolidation_start": {...},
    "consolidation_complete": {...},
    "pre_clear": {...}
}
```

### Hook Safety Mechanisms
1. **Idempotency Tracking** - Prevents duplicate executions
2. **Rate Limiting** - Prevents execution storms
3. **Cascade Monitoring** - Prevents cycles and deep nesting

### Hook Execution Pattern
```python
def _execute_with_safety(hook_id, context, func):
    # 1. Check idempotency (return cached if duplicate)
    # 2. Check rate limit (fail if exceeded)
    # 3. Check cascade (prevent nesting)
    # 4. Execute func()
    # 5. Record result
    # 6. Pop cascade stack
```

### INTEGRATION GAP: Hooks do NOT trigger query context updates
**Current behavior:**
- Hooks record events to episodic memory
- But they don't update UnifiedMemoryManager's query context
- No mechanism to "prime" retrieve() with session state

---

## 6. WorkingMemoryAPI Integration (Phase 2)

### MemoryAPI Class
```python
class MemoryAPI:
    def __init__(
        manager: UnifiedMemoryManager,
        project_manager: ProjectManager,
        database: Database
    )
    
    # Core methods
    def remember(content, memory_type, project_id, tags)
    def recall(query, limit, strategy)
    def forget(memory_id)
    def remember_event(event_type, content, context)
```

### Key Methods for Session Context
```python
# Store episodic event
api.remember_event(
    event_type="action",
    content="Session state snapshot",
    context={"task": task, "phase": phase}
)

# Recall recent events
api.recall(query="recent events in session", limit=5)
```

---

## 7. Current Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  UnifiedMemoryManager                        │
│  (Query Classification, Routing, Aggregation)               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  retrieve(query, context, k, ...)                            │
│      ↓                                                         │
│  _classify_query(query) → QueryType                          │
│      ↓                                                         │
│  ┌─────────────────────────────────────────────────┐        │
│  │  Route by Query Type                            │        │
│  ├─────────────────────────────────────────────────┤        │
│  │ TEMPORAL    → _query_episodic()                 │        │
│  │ FACTUAL     → _query_semantic()                 │        │
│  │ RELATIONAL  → _query_graph()                    │        │
│  │ PROCEDURAL  → _query_procedural()               │        │
│  │ PROSPECTIVE → _query_prospective()              │        │
│  │ META        → _query_meta()                     │        │
│  │ PLANNING    → _query_planning()                 │        │
│  │ DEFAULT     → _hybrid_search()                  │        │
│  └─────────────────────────────────────────────────┘        │
│      ↓                                                         │
│  _track_query() → Meta-memory                                │
│      ↓                                                         │
│  apply_confidence_scores()                                    │
│      ↓                                                         │
│  Return aggregated results                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         ↑                           ↑
         │                           │
    ┌────────────────────────────────────────┐
    │   Memory Layer Stores                   │
    ├────────────────────────────────────────┤
    │ • EpisodicStore (7±2 buffer)           │
    │ • MemoryStore (semantic)               │
    │ • ProceduralStore (workflows)          │
    │ • ProspectiveStore (tasks/goals)       │
    │ • GraphStore (entities/relations)      │
    │ • MetaMemoryStore (coverage/expertise) │
    │ • ConsolidationSystem (patterns)       │
    └────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   HookDispatcher                              │
│  (Session Management, Context Recovery)                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  _active_session_id                                           │
│  _active_conversation_id                                      │
│  _turn_count                                                  │
│                                                               │
│  fire_session_start() → Records episodic event              │
│  fire_conversation_turn() → Records turn + event            │
│  fire_user_prompt_submit() → Checks context recovery        │
│  check_context_recovery_request() → Auto-recover context    │
│  ...13 hooks total...                                         │
│                                                               │
│  Safety Mechanisms:                                           │
│  • IdempotencyTracker (no duplicates)                        │
│  • RateLimiter (prevents storms)                             │
│  • CascadeMonitor (prevents cycles)                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  WorkingMemoryAPI (Phase 2)                   │
│  (Event buffering, Consolidation triggering)                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  push_async(event) → Triggers consolidation if full         │
│  list_async(project_id) → List buffered items               │
│  pop_async(event_id) → Remove from buffer                   │
│  update_scores_async(event_id, importance, ...)            │
│                                                               │
│  ConsolidationRouterV2:                                       │
│  • route_async(wm_item) → TargetLayer + confidence          │
│  • consolidate_item_async(wm_item) → Store in target       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Integration Points for SessionContextManager

### A. Query-Time Integration Points

**1. Enhanced retrieve() signature**
```python
def retrieve(
    self,
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    session_context: Optional[SessionContext] = None,  # NEW
    auto_load_session: bool = True,  # NEW
    ...
) -> dict:
```

**2. Context loading at query start**
```python
if auto_load_session and session_context is None:
    session_context = self.session_manager.get_current_session()
    
# Merge session context into query context
if session_context:
    context = context or {}
    context.update({
        "session_id": session_context.session_id,
        "task": session_context.current_task,
        "phase": session_context.current_phase,
        "recent_events": session_context.recent_events,
        "working_memory": session_context.active_items,
    })
```

### B. Context-Aware Layer Routing

**Current:** Simple linguistic pattern matching
**Proposed:** Context + linguistics for routing

```python
def _classify_query(self, query: str, context: Optional[SessionContext] = None) -> str:
    # Current: linguistic patterns only
    # Proposed: Also consider session context
    
    if context:
        # If session is in debugging phase, bias toward error-related results
        if context.current_phase == "debugging":
            if "what went wrong" in query.lower():
                return QueryType.TEMPORAL  # Favor recent errors
        
        # If session has active task, bias toward task-related results
        if context.current_task:
            if "pending" in query.lower() or "remaining" in query.lower():
                return QueryType.PROSPECTIVE  # Favor tasks in this session
```

### C. Hook Integration Points

**Integration into HookDispatcher:**

```python
class HookDispatcher:
    def __init__(self, db, project_id, session_manager):
        self.session_manager = session_manager
    
    def fire_session_start(self, session_id, context):
        # Create SessionContext in addition to episodic event
        session_context = self.session_manager.start_session(
            session_id=session_id,
            task=context.get("task"),
            phase=context.get("phase")
        )
        
        # ... existing episodic event recording ...
    
    def fire_user_prompt_submit(self, prompt, task, phase):
        # Update session context before recording event
        self.session_manager.update_context(
            prompt_content=prompt,
            task=task,
            phase=phase
        )
        
        # Check for context recovery (existing)
        recovery_context = self.check_context_recovery_request(prompt)
        
        # ... rest of method ...
```

### D. Working Memory to Session Context Flow

```python
# Phase 2 consolidation cycle:
WorkingMemoryAPI.push_async(event)
    ↓
Check capacity → trigger consolidation if full
    ↓
ConsolidationRouterV2.route_async(wm_item, project_id)
    ↓
SessionContextManager.record_consolidation(
    wm_item=wm_item,
    target_layer=target_layer,
    confidence=confidence
)
    ↓
SessionContext.consolidation_history += [consolidation_record]
```

### E. Context Recovery Integration

**Existing flow:**
```python
HookDispatcher.fire_user_prompt_submit(prompt)
    ↓
check_context_recovery_request(prompt)
    ↓
if recovery needed:
    auto_recover_context() → recovery_dict
    return recovery_dict
```

**Enhanced with SessionContextManager:**
```python
HookDispatcher.fire_user_prompt_submit(prompt)
    ↓
check_context_recovery_request(prompt)
    ↓
if recovery needed:
    # Use SessionContextManager for more structured recovery
    session_context = self.session_manager.recover_context(
        recovery_patterns=recovery_patterns,
        source="episodic_memory"
    )
    return session_context.to_dict()
```

---

## 9. Store Classes and Their Roles

| Store | Responsibility | Key Methods | Stores In |
|-------|-----------------|-------------|-----------|
| `EpisodicStore` | Temporal events (7±2) | record_event(), get_events_by_date(), search_events() | episodic_events table |
| `MemoryStore` | Semantic facts | remember(), recall(), recall_with_reranking() | memories table |
| `ProceduralStore` | Workflows | search_procedures(), get_procedure() | procedures table |
| `ProspectiveStore` | Tasks/goals | create_task(), list_tasks(), get_ready_tasks() | prospective_tasks table |
| `GraphStore` | Entities/relations | search_entities(), get_entity_relations() | entities, relations tables |
| `MetaMemoryStore` | Coverage/expertise | get_domain(), list_domains() | domain_coverage table |
| `ConsolidationSystem` | Pattern extraction | consolidate(), run() | consolidation_runs table |
| `WorkingMemoryAPI` | Episodic buffering | push_async(), list_async(), pop_async() | working_memory table |

---

## 10. Suggested SessionContextManager Integration Points

### Priority 1: Query Priming (HIGH VALUE)
**Problem:** Session context not available at query time
**Solution:** 
- SessionContextManager accessible from UnifiedMemoryManager
- Auto-load session context if `auto_load_session=True`
- Merge session context into query `context` parameter

```python
# In UnifiedMemoryManager.__init__
def __init__(self, ..., session_manager: Optional[SessionContextManager] = None):
    self.session_manager = session_manager

# In UnifiedMemoryManager.retrieve()
def retrieve(self, query, context=None, auto_load_session=True, ...):
    if auto_load_session and self.session_manager:
        session_context = self.session_manager.get_current_session()
        context = self._merge_session_context(context, session_context)
```

### Priority 2: Context-Aware Routing (MEDIUM VALUE)
**Problem:** Query classification ignores session state
**Solution:**
- Pass SessionContext to _classify_query()
- Use context to bias routing decisions
- Example: In debugging phase, bias toward error-related queries

```python
def _classify_query(self, query, session_context=None):
    # Existing linguistic classification
    query_type = self._linguistic_classify(query)
    
    # Context-aware refinement
    if session_context:
        query_type = self._refine_query_type(
            query_type,
            session_context,
            query
        )
    
    return query_type
```

### Priority 3: Hook-Based Context Updates (MEDIUM VALUE)
**Problem:** Hooks record events but don't update query context
**Solution:**
- HookDispatcher notifies SessionContextManager of lifecycle events
- SessionContextManager updates context state
- Next retrieve() call has fresh context

```python
# In HookDispatcher
def fire_session_start(self, session_id, context):
    session_context = self.session_manager.start_session(...)
    # ... existing code ...

def fire_conversation_turn(self, user, assistant, ...):
    self.session_manager.record_turn(user, assistant, ...)
    # ... existing code ...
```

### Priority 4: Working Memory Integration (MEDIUM VALUE)
**Problem:** Consolidation events not visible to query context
**Solution:**
- WorkingMemoryAPI notifies SessionContextManager on consolidation
- SessionContextManager tracks what was consolidated
- retrieve() can use this for result ranking

```python
# In WorkingMemoryAPI._trigger_consolidation_async()
if session_manager:
    session_manager.record_consolidation(
        project_id=project_id,
        wm_size=size,
        consolidation_run_id=consolidation_run_id
    )
```

### Priority 5: Context Recovery Enhancement (LOW VALUE)
**Problem:** Context recovery uses episodic memory only
**Solution:**
- SessionContextManager coordinates recovery
- Combines episodic events with structured session metadata
- Provides richer context recovery results

```python
# In HookDispatcher.check_context_recovery_request()
if self.should_trigger_recovery(prompt):
    if self.session_manager:
        context = self.session_manager.recover_session_context()
    else:
        context = self.auto_recovery.auto_recover_context()
    
    return context
```

---

## 11. Critical Dependencies and Concerns

### PostgreSQL Migration
- Database converted from SQLite to PostgreSQL
- All Store classes use `db.get_cursor()` and transaction semantics
- SessionContextManager must use same Database abstraction

### Async/Sync Pattern
- WorkingMemoryAPI uses `run_async()` bridge for sync wrapper
- ConsolidationRouterV2 has async/sync dual interface
- SessionContextManager should follow same pattern

### Memory Layers Architecture
- 8 layers with distinct responsibilities
- Each layer has Store class with schema initialization
- SessionContextManager should NOT replicate this - only coordinate

### Query Context Propagation
- `context` parameter is dict-based, not strongly typed
- SessionContextManager should provide typed SessionContext
- But retrieve() should accept both dict and SessionContext for compatibility

### Hook Safety Mechanisms
- Three safety layers: idempotency, rate limiting, cascade detection
- SessionContextManager updates should use same safety mechanisms
- Prevent race conditions on context state

---

## 12. Key Files and Line Counts

| File | Lines | Key Classes | Purpose |
|------|-------|-----------|---------|
| src/athena/manager.py | 782 | UnifiedMemoryManager | Central routing engine |
| src/athena/mcp/memory_api.py | 1000+ | MemoryAPI | Direct Python API |
| src/athena/hooks/dispatcher.py | 893 | HookDispatcher | Session lifecycle |
| src/athena/episodic/working_memory.py | 494 | WorkingMemoryAPI | Episodic buffering |
| src/athena/working_memory/consolidation_router_v2.py | 300+ | ConsolidationRouterV2 | ML-based routing |
| src/athena/episodic/store.py | ~400 | EpisodicStore | Event persistence |
| src/athena/memory/store.py | ~400 | MemoryStore | Semantic persistence |
| src/athena/conversation/store.py | ~300 | ConversationStore | Conversation tracking |

---

## Summary: Where SessionContextManager Fits

The SessionContextManager should be:

1. **Peer to UnifiedMemoryManager** - not a child or wrapper
2. **Initialized in same factory** - alongside other managers
3. **Injected into HookDispatcher** - for lifecycle coordination
4. **Optional in UnifiedMemoryManager** - graceful degradation if not provided
5. **Query-context aware** - provides SessionContext to retrieve()
6. **Hook-coordinated** - receives notifications of session events
7. **Storage-backed** - uses Database abstraction for persistence

**Integration Summary:**
```
MemoryAPI
   ↓
UnifiedMemoryManager + SessionContextManager
   ↓
  / | \ \
 /  |  \ \
Hooks Stores Consolidation WorkingMemory
```

