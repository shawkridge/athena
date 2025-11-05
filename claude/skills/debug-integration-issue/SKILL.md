---
category: skill
name: debug-integration-issue
description: Systematically debug complex multi-layer integration issues
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.82
trigger: Multi-layer system issue, cross-layer data flow problem, integration test fails, "integration" mentioned
---

# Debug Integration Issue Skill

Guides systematic debugging of complex issues across multiple Memory MCP layers.

## When I Invoke This

You have:
- Integration test failing mysteriously
- Data not flowing between layers correctly
- Consolidation not working as expected
- Multi-layer workflow broken
- Issue difficult to isolate

## What I Do

I guide integration debugging in these phases:

```
1. UNDERSTAND Phase: Map the flow
   → What layers involved?
   → What's the happy path?
   → What should happen step-by-step?

2. TRACE Phase: Follow the data
   → Add logging at layer boundaries
   → Trace data flow end-to-end
   → Identify where it breaks
   → Check intermediate state

3. ISOLATE Phase: Narrow scope
   → Is it Layer A or Layer B?
   → Is it the connection or the layer?
   → Can you reproduce in isolation?
   → What's the minimal example?

4. ANALYZE Phase: Find root cause
   → Check contracts (input/output types)
   → Verify assumptions
   → Check error handling
   → Review recent changes

5. FIX Phase: Implement solution
   → Fix root cause (not symptom)
   → Update contract if needed
   → Add safeguards
   → Test isolation + integration
```

## Integration Architecture

### Layer Communication Patterns

```python
# Pattern 1: Direct call between layers
episodic_layer.record_event(event)
consolidation_layer.process_episodic_events()

# Pattern 2: Event-driven via hooks
hook.trigger('on_event_recorded', event)

# Pattern 3: Query-based
episodic_events = episodic_layer.query(time_range)
consolidation_layer.consolidate(episodic_events)

# Pattern 4: Manager-orchestrated (preferred)
manager.record_event(event)  # Propagates to all layers
results = manager.consolidate()  # Coordinates across layers
```

## Common Integration Issues

### Issue 1: Data Not Flowing to Next Layer

**Symptom**: Event recorded in episodic, not appearing in semantic after consolidation

```python
# Debug flow
def debug_consolidation_flow():
    # 1. Check episodic has events
    episodic_count = episodic_store.count()
    print(f"Episodic events: {episodic_count}")

    # 2. Trigger consolidation
    results = consolidation_system.run()
    print(f"Consolidation results: {results}")

    # 3. Check semantic was updated
    semantic_count = semantic_store.count()
    print(f"Semantic after consolidation: {semantic_count}")

    # 4. If not updated, check consolidation output
    if semantic_count == 0:
        print(f"Consolidation succeeded but semantic empty!")
        # Check: is consolidation output being used?
        # Check: is semantic_store.create() being called?
        # Check: error handling in consolidation
```

**Common causes**:
- Consolidation output not used
- Store not getting called with results
- Exception swallowed (try/except issue)
- Data type mismatch

**Fix**: Add logging, verify each step executes

---

### Issue 2: Stale Data from Previous Layer

**Symptom**: Old data still showing after update

```python
# Debug caching issue
def debug_stale_data():
    # 1. Get directly from source
    direct = layer_a.get_by_id(id)
    print(f"Direct from layer A: {direct}")

    # 2. Get through manager (might cache)
    via_manager = manager.get_by_id(id)
    print(f"Via manager: {via_manager}")

    # 3. Check if they match
    if direct != via_manager:
        print("Stale cache detected!")
        # Solution: invalidate cache after updates
```

**Common causes**:
- Cache not invalidated after update
- Query using old timestamp range
- Stale reference to object

**Fix**: Clear caches, use fresh queries

---

### Issue 3: Type Mismatch Between Layers

**Symptom**: Integration test fails with type error

```python
# Episodic layer returns EpisodicEvent
event: EpisodicEvent = episodic_store.get(id)

# But consolidation expects dict?
consolidation.process(event)  # Fails if consolidation expects dict

# Fix: Check types match
assert isinstance(event, EpisodicEvent)
# Or convert: consolidation.process(event.dict())
```

**Common causes**:
- Model mismatch between layers
- Serialization issue
- API change not propagated

**Fix**: Check and convert types at boundaries

---

### Issue 4: Missing Integration Glue

**Symptom**: Two layers work in isolation but not together

```python
# Pattern: Each layer works
episodic_store.create(event)  # ✓ Works
consolidation_system.run()     # ✓ Works alone

# But together they fail
# Missing: glue code that connects them!

# Solution: Integration layer
def full_workflow():
    # 1. Record event
    event = episodic_store.create(event)

    # 2. Maybe trigger consolidation
    if should_consolidate():
        consolidation_system.run()

    # 3. Use results
    # ...
```

**Common causes**:
- No integration test
- Integration code not in right place
- Layers assume some external orchestration

**Fix**: Add integration code and tests

---

## Debugging Techniques

### Technique 1: Add Strategic Logging

```python
# Add before/after each layer
logger.info(f"Before consolidation: {episodic_store.count()} events")
results = consolidation_system.run()
logger.info(f"Consolidation results: {results}")
logger.info(f"After consolidation: {semantic_store.count()} memories")

# Check: do counts change?
# If not, something didn't execute
```

### Technique 2: Create Minimal Reproduction

```python
def test_minimal_consolidation():
    # Minimal: just what's needed
    event = EpisodicEvent(content="test", event_type="action")
    episodic_store.create(event)

    results = consolidation_system.run()

    assert semantic_store.count() > 0, "Consolidation didn't create semantic memory"
```

### Technique 3: Check Layer Contracts

```python
# Episodic layer contract
episodic_output = episodic_store.get_unconsolidated()
# Returns: List[EpisodicEvent] with these fields: id, content, timestamp, ...

# Consolidation input contract
consolidation_input = consolidation_system.consolidate(episodic_output)
# Expects: List[dict] with fields: content, session_id, timestamp, ...
# MISMATCH! Episodic returns objects, consolidation expects dicts

# Fix: Convert at boundary
episodic_dicts = [e.dict() for e in episodic_output]
consolidation_system.consolidate(episodic_dicts)
```

### Technique 4: Verify Assumptions

```python
# When debugging, check assumptions:
assert db is not None, "Database not initialized"
assert episodic_store is not None, "Episodic store not created"
assert episodic_store.count() > 0, "No episodic events to consolidate"
assert consolidation_enabled, "Consolidation disabled"

# If any fail, that's your bug!
```

## Step-by-Step Integration Debugging

### Step 1: Understand Expected Flow
```
# For consolidation integration:
Event recorded → Episodic layer stores → Consolidation triggered → Patterns extracted → Semantic layer stores → Query returns results

# For task sync:
Task created → Episodic event recorded → Patterns detected (2+ matches) → Workflow suggested → Consolidation triggered
```

### Step 2: Add Logging at Each Boundary
```python
# episodic/store.py
def create(self, event):
    result = super().create(event)
    logger.info(f"Created episodic event: {event.id}")
    return result

# consolidation/system.py
def run(self):
    logger.info(f"Starting consolidation...")
    results = self.extract_patterns()
    logger.info(f"Extracted {len(results)} patterns")
    return results

# semantic/store.py
def create(self, memory):
    result = super().create(memory)
    logger.info(f"Created semantic memory: {memory.id}")
    return result
```

### Step 3: Run & Check Logs
```bash
# Run integration test with logging
pytest tests/integration/test_consolidation.py -v -s --log-cli-level=INFO

# Look for: do all log lines appear in order?
# Missing line = that code didn't execute
```

### Step 4: Isolate Each Layer
```bash
# Test episodic in isolation
pytest tests/unit/test_episodic_store.py -v

# Test consolidation in isolation
pytest tests/unit/test_consolidation_system.py -v

# Test semantic in isolation
pytest tests/unit/test_semantic_store.py -v

# All pass? Then issue is in integration
```

### Step 5: Test Integration Piece by Piece
```python
def test_integration_step_by_step():
    # Step 1: Can record event?
    event = episodic_store.create(test_event)
    assert event.id is not None

    # Step 2: Can consolidation see it?
    unconsolidated = episodic_store.get_unconsolidated()
    assert len(unconsolidated) > 0

    # Step 3: Can consolidation process it?
    results = consolidation_system.run(unconsolidated)
    assert results is not None

    # Step 4: Was semantic memory created?
    semantic_count = semantic_store.count()
    assert semantic_count > 0, "Consolidation didn't create semantic memory"
```

### Step 6: Check Error Handling
```python
# Add try/except logging to find swallowed exceptions
try:
    consolidation_system.run()
except Exception as e:
    logger.error(f"Consolidation failed: {e}", exc_info=True)
    raise  # Re-raise so test fails (don't hide errors!)
```

## Integration Checklist

- [ ] Expected flow documented
- [ ] Logging added at layer boundaries
- [ ] Each layer tested in isolation (passes)
- [ ] Integration test failing (reproducible)
- [ ] Data flow traced (where does it break?)
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Integration test now passes
- [ ] No regressions (full suite passes)
- [ ] Committed with clear message

## Related Skills

- **fix-failing-tests** - Integration tests often fail first
- **refactor-code** - Integration issues often need refactoring
- **profile-performance** - Integration layers can be slow

## Success Criteria

✓ Root cause identified
✓ Data flow traced end-to-end
✓ Each layer works in isolation
✓ Layers communicate correctly
✓ Integration test passes
✓ No regressions
✓ Code is maintainable
