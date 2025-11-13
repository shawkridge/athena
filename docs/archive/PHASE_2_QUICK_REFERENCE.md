# Phase 2 Quick Reference

## Files Created

```
src/athena/episodic/working_memory.py          (440 lines) - WorkingMemoryAPI
src/athena/working_memory/consolidation_router_v2.py  (480 lines) - Router V2
tests/unit/test_consolidation_router_v2.py    (390 lines) - Tests
```

## Key Classes

### WorkingMemoryAPI

```python
class WorkingMemoryAPI:
    """Baddeley's 7±2 working memory with auto-consolidation."""

    def __init__(self, db, episodic_store, consolidation_callback=None, capacity=7):
        """Initialize with optional consolidation callback."""

    # Async methods (primary)
    async def push_async(self, event, importance=0.5, distinctiveness=0.5) -> dict
    async def list_async(self, project_id, sort_by="recency") -> list[WorkingMemoryItem]
    async def pop_async(self, event_id, project_id) -> Optional[EpisodicEvent]
    async def clear_async(self, project_id) -> int
    async def update_scores_async(self, event_id, importance=None, distinctiveness=None) -> bool

    # Sync methods (wrappers via run_async)
    def push(self, event, importance=0.5, distinctiveness=0.5) -> dict
    def list(self, project_id, sort_by="recency") -> list[WorkingMemoryItem]
    def pop(self, event_id, project_id) -> Optional[EpisodicEvent]
    def clear(self, project_id) -> int
    def update_scores(self, event_id, importance=None, distinctiveness=None) -> bool
    def get_size(self) -> int
```

### ConsolidationRouterV2

```python
class ConsolidationRouterV2:
    """ML-based router using Store APIs for consolidation."""

    def __init__(self, db, memory_store, episodic_store, procedural_store, prospective_store):
        """Initialize with all memory stores."""

    # Routing (async/sync)
    async def route_async(self, item: WorkingMemoryItem, project_id: int, use_ml=True) -> tuple[TargetLayer, float]
    def route(self, item: WorkingMemoryItem, project_id: int, use_ml=True) -> tuple[TargetLayer, float]

    # Consolidation (async/sync)
    async def consolidate_item_async(self, item, project_id, target_layer=None) -> dict
    def consolidate_item(self, item, project_id, target_layer=None) -> dict

    # Statistics (async/sync)
    async def get_routing_statistics_async(self, project_id) -> dict
    def get_routing_statistics(self, project_id) -> dict

    # Helper methods
    def _extract_features(self, item) -> np.ndarray  # 11 features
    def _heuristic_route(self, item) -> TargetLayer  # Fallback routing
    def _ml_predict(self, features) -> tuple[TargetLayer, float]  # ML routing
```

## Database Schema

### working_memory
```sql
CREATE TABLE working_memory (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    event_id INTEGER UNIQUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recency_score REAL DEFAULT 1.0,
    importance_score REAL DEFAULT 0.5,
    distinctiveness_score REAL DEFAULT 0.5,

    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
)
```

### consolidation_triggers
```sql
CREATE TABLE consolidation_triggers (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trigger_type TEXT,
    working_memory_size INTEGER,
    capacity INTEGER,
    consolidation_type TEXT,
    consolidation_run_id INTEGER,

    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id)
)
```

## Usage Examples

### Basic Working Memory

```python
from athena.episodic.working_memory import WorkingMemoryAPI

api = WorkingMemoryAPI(db, episodic_store)

# Push event
result = api.push(event, importance=0.8)
# {
#   "event_id": 123,
#   "working_memory_size": 5,
#   "capacity": 7,
#   "consolidation_triggered": False
# }

# List items
items = api.list(project_id, sort_by="importance")

# Update scores
api.update_scores(event_id, importance=0.9, distinctiveness=0.7)

# Get size
size = api.get_size()  # Returns: 5
```

### Auto-Consolidation Callback

```python
async def consolidation_callback(project_id, consolidation_type, max_events):
    """Called when working memory capacity exceeded."""
    result = await consolidation_system.consolidate(
        project_id=project_id,
        consolidation_type=consolidation_type,
    )
    return result.id  # Return consolidation_run_id

api = WorkingMemoryAPI(
    db=db,
    episodic_store=episodic_store,
    consolidation_callback=consolidation_callback,
    capacity=7,  # Can customize
)

# Now when capacity exceeded:
result = api.push(event)
if result["consolidation_triggered"]:
    print(f"Auto-consolidated with run ID: {result['consolidation_run_id']}")
```

### Intelligent Consolidation Routing

```python
from athena.working_memory.consolidation_router_v2 import ConsolidationRouterV2

router = ConsolidationRouterV2(
    db=db,
    memory_store=memory_store,
    episodic_store=episodic_store,
    procedural_store=procedural_store,
    prospective_store=prospective_store,
)

# Route item to appropriate layer
target_layer, confidence = router.route(item, project_id)
# Returns: (TargetLayer.SEMANTIC, 0.85)

# Consolidate (auto-routes)
result = router.consolidate_item(item, project_id)
# {
#   "wm_item_id": 1,
#   "target_layer": "semantic",
#   "ltm_id": 42,
#   "confidence": 0.85
# }

# Or explicit target
result = router.consolidate_item(
    item, project_id,
    target_layer=TargetLayer.PROCEDURAL  # Override routing
)
```

## Routing Rules

### Heuristic Routing (when ML not trained)

| Content | Features | Target Layer |
|---------|----------|--------------|
| "Python lists..." | Factual, no markers | SEMANTIC |
| "Build a feature" | Action verbs | PROCEDURAL |
| "Complete tomorrow" | Future markers | PROSPECTIVE |
| "Yesterday tested" | Temporal markers | EPISODIC |
| "How do I...?" | Question words | PROSPECTIVE/PROCEDURAL |

### Feature Weights

1. **Future markers** (0.8) → PROSPECTIVE
2. **Action verbs** (0.7) → PROCEDURAL
3. **Temporal markers** (0.6) → EPISODIC
4. **Question words** (0.7) → PROSPECTIVE
5. **Default** → SEMANTIC

## Testing

### Run All Tests
```bash
pytest tests/unit/test_consolidation_router_v2.py -v
```

### Run Specific Test
```bash
pytest tests/unit/test_consolidation_router_v2.py::TestConsolidationRouterV2::test_heuristic_route_semantic -v
```

### Run with Coverage
```bash
pytest tests/unit/test_consolidation_router_v2.py --cov=src/athena/working_memory --cov-report=html
```

## Performance Notes

### Capacity Thresholds

- **Low**: 5/7 items (just informational)
- **High**: 7/7 items (triggers consolidation on next push)
- **Force**: 9/7 items (immediate consolidation)

### Typical Latencies

- Push: ~5-8ms
- List: ~20-30ms
- Pop: ~2-4ms
- Consolidation trigger: ~10-20ms

## Integration Points

### With ConsolidationSystem

```python
# ConsolidationSystem can trigger from working memory
system = ConsolidationSystem(db, memory_store, episodic_store, ...)

result = system.consolidate(
    project_id=1,
    consolidation_type=ConsolidationType.WORKING_MEMORY,
    max_events=7,  # From working memory
)
```

### With Hook System (Phase 3)

```python
# In hook handler
from athena.episodic.working_memory import WorkingMemoryAPI

api = WorkingMemoryAPI(db, episodic_store, consolidation_callback)

# On episode recorded
result = api.push(episode)
if result["consolidation_triggered"]:
    logger.info(f"Auto-consolidation triggered: {result}")
```

## Troubleshooting

### Consolidation Not Triggering

```python
# Check capacity setting
print(api.capacity)  # Should be 7 (default)

# Check working memory size
size = api.get_size()
print(f"Current size: {size}/{api.capacity}")

# Verify callback is set
if api.consolidation_callback is None:
    print("WARNING: No consolidation callback set!")
```

### Incorrect Routing

```python
# Check features extracted
item = WorkingMemoryItem(...)
features = router._extract_features(item)
print(f"Features: {features}")

# Check routing result
target, conf = router.route(item, project_id)
print(f"Routed to {target} with confidence {conf:.2f}")

# Check heuristic routing
target = router._heuristic_route(item)
print(f"Heuristic suggests: {target}")
```

### Database Schema Issues

```python
# Verify tables exist
cursor = db.get_cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print([t["name"] for t in tables])

# Check working_memory data
cursor.execute("SELECT * FROM working_memory LIMIT 10")
rows = cursor.fetchall()
print(f"Working memory has {len(rows)} items")
```

## Next Steps (Phase 3)

1. **SessionContextManager**: Auto-load/save working memory
2. **Cascading Recall**: Multi-tier search combining layers
3. **Hook Integration**: Auto-consolidation on save
4. **Performance Tuning**: Optimize thresholds and triggers
5. **Integration Tests**: Cross-layer scenarios

---

## References

- Full Documentation: `PHASE_2_COMPLETION_REPORT.md`
- Working Memory API: `src/athena/episodic/working_memory.py`
- Router V2: `src/athena/working_memory/consolidation_router_v2.py`
- Tests: `tests/unit/test_consolidation_router_v2.py`
- Async Utilities: `src/athena/core/async_utils.py`
