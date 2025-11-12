# Phase 3 Quick Reference: SessionContextManager & Cascading Recall

## Quick Start

### 1. SessionContextManager

```python
from athena.session.context_manager import SessionContextManager

# Create manager
session_mgr = SessionContextManager(db)

# Start session
ctx = session_mgr.start_session(
    session_id="session_123",
    project_id=1,
    task="Debug failing test",
    phase="debugging"
)

# Record events
session_mgr.record_event(
    session_id="session_123",
    event_type="conversation_turn",
    event_data={"turn": 1}
)

# Update context
session_mgr.update_context(phase="refactoring")

# Record consolidation (auto from WorkingMemoryAPI)
session_mgr.record_consolidation(
    project_id=1,
    consolidation_type="CAPACITY",
    wm_size=8,
    consolidation_run_id=42
)

# Get context for queries
query_ctx = session_mgr.get_context_for_query()

# End session
session_mgr.end_session()
```

### 2. Cascading Recall

```python
# Basic recall (single tier, fast)
results = manager.recall(
    query="What was the failing test?",
    k=5,
    cascade_depth=1
)
# Returns: { tier_1: { episodic, semantic, procedural, ... }, ... }

# Enriched recall (two tiers)
results = manager.recall(
    query="What happened?",
    context={"phase": "debugging"},
    cascade_depth=2
)
# Returns: { tier_1: {...}, tier_2: { hybrid, meta, session_context } }

# Full recall (three tiers, LLM synthesis)
results = manager.recall(
    query="What should we do?",
    cascade_depth=3,
    include_scores=True,
    explain_reasoning=True
)
# Returns: { tier_1, tier_2, tier_3, _scores, _explanation }
```

---

## API Reference

### SessionContextManager

#### Core Methods

```python
# Start a session
ctx = session_mgr.start_session(
    session_id: str,
    project_id: int,
    task: Optional[str] = None,
    phase: Optional[str] = None
) → SessionContext

# End a session
success = session_mgr.end_session(
    session_id: Optional[str] = None
) → bool

# Get current active session
ctx = session_mgr.get_current_session() → Optional[SessionContext]

# Record an event
event_id = session_mgr.record_event(
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any]
) → int

# Record consolidation (called from WorkingMemoryAPI)
session_mgr.record_consolidation(
    project_id: int,
    consolidation_type: Optional[str] = None,
    wm_size: int = 0,
    consolidation_run_id: Optional[int] = None,
    trigger_type: Optional[str] = None
) → None

# Update context
session_mgr.update_context(
    task: Optional[str] = None,
    phase: Optional[str] = None
) → None

# Recover context from episodic memory
ctx = session_mgr.recover_context(
    recovery_patterns: Optional[List[str]] = None,
    source: str = "episodic_memory"
) → Optional[SessionContext]

# Get context formatted for queries
ctx_dict = session_mgr.get_context_for_query() → Dict[str, Any]
```

#### Async Variants

All methods have `*_async()` versions:
- `start_session_async()`
- `end_session_async()`
- `record_event_async()`
- `update_context_async()`

### UnifiedMemoryManager.recall()

```python
results = manager.recall(
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    cascade_depth: int = 3,
    include_scores: bool = True,
    explain_reasoning: bool = False
) → dict
```

**Parameters**:
- `query`: Search query (e.g., "What was the error?")
- `context`: Optional context dict (session context auto-loaded)
- `k`: Number of results per tier (default 5)
- `cascade_depth`: 1 (fast), 2 (enriched), 3 (synthesized) - default 3
- `include_scores`: Include confidence scores (default True)
- `explain_reasoning`: Include tier explanation (default False)

**Returns**: Dictionary with tiers and metadata
```python
{
    "_cascade_depth": 3,
    "tier_1": {
        "episodic": [...],
        "semantic": [...],
        "procedural": [...],
        ...
    },
    "tier_2": {
        "hybrid": [...],
        "meta": [...],
        "session_context": {...}
    },
    "tier_3": {
        "synthesized": [...],
        "planning": [...]
    },
    "_cascade_explanation": {...}  # if explain_reasoning=True
}
```

---

## Database Schema

### session_contexts

```sql
CREATE TABLE session_contexts (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    task TEXT,
    phase TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
)
```

### session_context_events

```sql
CREATE TABLE session_context_events (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT,  -- JSON
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## Usage Patterns

### Pattern 1: Session-aware Queries

```python
# Start debugging session
hooks.fire_session_start(context={
    "task": "Debug failing test",
    "phase": "debugging"
})

# Query automatically includes session context
# Results biased toward error-related memories
results = manager.recall("What went wrong?")
```

### Pattern 2: Multi-depth Queries

```python
# Fast check (tier 1 only)
quick_results = manager.recall(query, cascade_depth=1, k=3)

# If quick results insufficient, try enriched
if not quick_results["tier_1"]:
    enriched = manager.recall(query, cascade_depth=2, k=5)

# For complex questions, use full synthesis
if len(enriched["tier_2"]["meta"]) == 0:
    full = manager.recall(query, cascade_depth=3)
```

### Pattern 3: Context Recovery

```python
# User asks: "What were we working on?"
recovered = session_mgr.recover_context(
    recovery_patterns=["task", "phase"]
)

if recovered:
    print(f"Task: {recovered.current_task}")
    print(f"Phase: {recovered.current_phase}")
```

### Pattern 4: Consolidation Tracking

```python
# During working memory consolidation
await working_memory.push_async(event)  # Triggers consolidation if full

# SessionContextManager auto-records:
session_mgr.record_consolidation(
    project_id=1,
    consolidation_type="CAPACITY",
    wm_size=7,
    consolidation_run_id=run_id,
    trigger_type="CAPACITY"
)

# Next recall includes consolidation history in context
results = manager.recall(query, cascade_depth=2)
```

---

## Tier Selection Heuristics

### Tier 1 Layer Selection

| Layer | Triggered By |
|-------|---|
| Episodic | "when", "last", "recent", "error", "failed", phase="debugging" |
| Semantic | Always (baseline) |
| Procedural | "how", "do", "build", "implement" |
| Prospective | "task", "goal", "todo", "should" |
| Graph | "relates", "depends", "connected" |

### Tier 2 Enrichment

| Source | Trigger |
|--------|---------|
| Hybrid | If tier 1 has results |
| Meta | If phase is set |
| Session Context | If recent_events available |

### Tier 3 Synthesis

| Feature | Requirement |
|---------|-------------|
| RAG Synthesis | RAG manager available |
| Planning | phase in ["planning", "refactoring"] |

---

## Performance Tips

### 1. Use Appropriate Depth

```python
# Fast path (typical)
manager.recall(query, cascade_depth=1)  # 50-100ms

# Enriched (when needed)
manager.recall(query, cascade_depth=2)  # 100-300ms

# Synthesis (complex questions only)
manager.recall(query, cascade_depth=3)  # 500-2000ms
```

### 2. Cache Session Context

```python
# Session context auto-loaded from manager
# Cached during active session
# Invalidated on session end
```

### 3. Batch Events

```python
# Record multiple events efficiently
for event_data in events:
    session_mgr.record_event(
        session_id=sid,
        event_type="batch_event",
        event_data=event_data
    )
```

---

## Integration Points

### With UnifiedMemoryManager

```python
# Initialize with session manager
manager = UnifiedMemoryManager(
    semantic=semantic_store,
    # ... other stores ...
    session_manager=session_manager,
    # All queries auto-load context
)
```

### With WorkingMemoryAPI

```python
# Working memory auto-records consolidations
working_memory = WorkingMemoryAPI(
    db=db,
    episodic_store=episodic_store,
    consolidation_callback=callback,
    session_manager=session_manager,  # NEW
)

# Consolidation events auto-recorded
```

### With HookDispatcher

```python
# Hook dispatcher notifies session manager
hooks = HookDispatcher(
    db=db,
    project_id=1,
    session_manager=session_manager,  # NEW
)

# Session lifecycle events auto-tracked
```

---

## Testing

### SessionContextManager Tests

```bash
pytest tests/unit/test_session_context_manager.py -v
# 31 tests covering all functionality
```

### Cascading Recall Tests

```bash
pytest tests/unit/test_cascading_recall.py -v
# 31 tests covering all tiers and edge cases
```

### All Phase 3 Tests

```bash
pytest tests/unit/test_session_context_manager.py tests/unit/test_cascading_recall.py -v
# 62 total tests
```

---

## Troubleshooting

### Session context not loading?

```python
# Check if session_manager is initialized
if manager.session_manager is None:
    print("SessionContextManager not initialized")

# Check if active session
ctx = session_manager.get_current_session()
if ctx is None:
    print("No active session")
```

### Recall returning empty results?

```python
# Check tier 1 (fast) first
results = manager.recall(query, cascade_depth=1)
if not results["tier_1"]:
    # Try tier 2 (enriched)
    results = manager.recall(query, cascade_depth=2)
```

### Consolidation not recorded?

```python
# Ensure session is active
session_mgr.start_session(sid, pid, task, phase)

# Then record consolidation
session_mgr.record_consolidation(...)

# Verify it was recorded
ctx = session_mgr.get_current_session()
print(len(ctx.consolidation_history))
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/athena/session/__init__.py` | Module exports |
| `src/athena/session/context_manager.py` | Implementation |
| `src/athena/manager.py` | Integration (retrieve + recall) |
| `tests/unit/test_session_context_manager.py` | Unit tests |
| `tests/unit/test_cascading_recall.py` | Integration tests |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| SessionContextManager code | 480 lines |
| Test coverage | 62 tests |
| Database tables | 2 |
| API methods | 13 core + async |
| Cascade tiers | 3 |
| Performance (tier 1) | 50-100ms |
| Performance (tier 3) | 500-2000ms |

---

**Status**: Phase 3 implementation complete. Ready for hook integration and optimization.
