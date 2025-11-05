---
category: skill
name: profile-performance
description: Profile and optimize performance bottlenecks in Memory MCP operations
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.83
trigger: Performance degraded, queries slow, "slow" or "optimize" mentioned, benchmarks show regression
---

# Profile Performance Skill

Guides systematic profiling and optimization of Memory MCP performance bottlenecks.

## When I Invoke This

You have:
- Performance regression (queries >100ms instead of <100ms)
- Memory footprint too large
- Insertion rate too slow
- Need to optimize specific operations
- Want baseline performance metrics

## What I Do

I guide performance optimization in these phases:

```
1. MEASURE Phase: Establish baseline
   → Run benchmark scripts
   → Capture current metrics
   → Identify slowest operations
   → Document baseline numbers

2. PROFILE Phase: Find bottlenecks
   → Use Python cProfile
   → Analyze call stacks
   → Identify slow functions
   → Check database query performance

3. ANALYZE Phase: Understand issues
   → Missing indexes?
   → N+1 query problems?
   → Inefficient algorithms?
   → Memory leaks?

4. OPTIMIZE Phase: Implement fixes
   → Add database indexes
   → Optimize queries
   → Refactor algorithms
   → Improve memory usage

5. VALIDATE Phase: Verify improvements
   → Re-run benchmarks
   → Compare metrics
   → Ensure no regressions
   → Document improvements
```

## Performance Metrics

### Target Performance
```
Metric                    Target        Current (if slow)
────────────────────────────────────────────────────────
Memory query latency      <100ms        >200ms?
Semantic search           <50ms         >100ms?
Event insertion           ~10 events/s  <5 events/s?
Consolidation            <1s baseline   >3s?
Graph traversal          <50ms         >200ms?
Working memory decay     Minimal ops    Expensive?
────────────────────────────────────────────────────────
```

## Profiling Commands

### Command 1: Benchmark Suite
```bash
# Run full benchmark
python scripts/run_benchmark.py

# Expected output:
# - Event insertion rate (target: 10/sec)
# - Query latency (target: <100ms)
# - Consolidation time (target: <1s)
# - Memory footprint (baseline comparison)
```

### Command 2: CPU Profiling
```bash
# Profile a slow operation
python -m cProfile -o profile.stats scripts/run_benchmark.py

# Analyze results
python -m pstats profile.stats
# Shows: cumulative time, number of calls, per-call time
```

### Command 3: Memory Profiling
```bash
# Track memory usage
pip install memory-profiler

python -m memory_profiler slow_operation.py
# Shows: line-by-line memory usage
```

### Command 4: Query Analysis
```bash
# Check database size and query plans
sqlite3 ~/.athena/memory.db

# Check size
SELECT COUNT(*) FROM semantic_memories;
SELECT COUNT(*) FROM episodic_events;

# Check query plan
EXPLAIN QUERY PLAN SELECT * FROM semantic_memories WHERE id = ?;
# Look for "SCAN" (bad) vs "SEARCH" (good)
```

## Common Performance Issues

### Issue 1: Missing Indexes

**Symptom**: Queries take >100ms, query plan shows "SCAN"

```bash
# Check what indexes exist
sqlite3 ~/.athena/memory.db ".indices"

# Add missing index
sqlite3 ~/.athena/memory.db "CREATE INDEX idx_semantic_layer ON semantic_memories(layer)"

# Verify improvement
EXPLAIN QUERY PLAN SELECT * FROM semantic_memories WHERE layer = 'episodic';
# Should show "SEARCH" now
```

**Fix**: Add indexes on commonly filtered columns
**Impact**: 10-100x faster queries
**Time**: 2-5 min per index

---

### Issue 2: N+1 Queries

**Symptom**: Operation slow, but profiling shows many queries

```python
# ❌ Before (N+1 problem)
def get_memories_with_details(ids):
    results = []
    for memory_id in ids:
        memory = query("SELECT * FROM semantic_memories WHERE id = ?", memory_id)
        details = query("SELECT * FROM memory_details WHERE memory_id = ?", memory_id)
        results.append((memory, details))
    return results

# ✓ After (batch query)
def get_memories_with_details(ids):
    memories = query("SELECT * FROM semantic_memories WHERE id IN (?)", ids)
    details = query("SELECT * FROM memory_details WHERE memory_id IN (?)", ids)
    # Merge results
    return combined_results
```

**Fix**: Use batch queries instead of loops
**Impact**: 10-1000x faster
**Time**: 5-10 min per N+1

---

### Issue 3: Inefficient Algorithms

**Symptom**: Algorithm takes O(n²) when O(n) is possible

```python
# ❌ Before (inefficient sort in consolidation)
def consolidate(events):
    # Sorts events multiple times? Re-groups repeatedly?
    for event in events:
        for other_event in events:
            if should_cluster(event, other_event):
                # ...
    # O(n²) or worse!

# ✓ After (efficient clustering)
def consolidate(events):
    # Pre-compute features, use efficient algorithm
    clusters = cluster_events_efficient(events)
    # O(n log n) or O(n)
```

**Fix**: Analyze algorithm complexity, optimize
**Impact**: Variable (2-100x)
**Time**: 10-30 min per algorithm

---

### Issue 4: Memory Leaks

**Symptom**: Memory grows over time without being freed

```python
# ❌ Before (circular references prevent garbage collection)
class MemoryStore:
    def __init__(self):
        self.cache = {}
        self.reverse_cache = {}  # Points back to cache items

    def add(self, item):
        self.cache[item.id] = item
        self.reverse_cache[item] = item.id  # Circular ref!

# ✓ After (proper cleanup)
class MemoryStore:
    def __init__(self):
        self.cache = {}

    def clear_stale(self):
        # Remove old items
        threshold = time.time() - 86400
        for id, item in list(self.cache.items()):
            if item.created_at < threshold:
                del self.cache[id]
```

**Fix**: Fix circular references, add cleanup
**Impact**: Prevents memory bloat
**Time**: 5-15 min per leak

---

## Step-by-Step Optimization Process

### Step 1: Measure Baseline
```bash
# Run benchmarks and capture output
python scripts/run_benchmark.py > baseline.txt

# Key metrics to note:
# - Event insertion: ___ events/sec
# - Query latency: ___ms
# - Consolidation: ___s
# - Memory: ___MB
```

### Step 2: Identify Slow Part
```bash
# Run with profiling
python -m cProfile -o profile.stats scripts/run_benchmark.py

# Analyze - look for high cumtime
python3 << 'EOF'
import pstats
s = pstats.Stats('profile.stats')
s.sort_stats('cumulative').print_stats(20)
EOF
```

### Step 3: Profile Specific Function
```bash
# If consolidation is slow:
python -m cProfile -o consolidate.stats -c "from memory_mcp.consolidation import system; system.run_consolidation()"

# Analyze
python -m pstats consolidate.stats
```

### Step 4: Check Database
```bash
# Query plan analysis
sqlite3 ~/.athena/memory.db

# For slow queries
EXPLAIN QUERY PLAN SELECT * FROM semantic_memories
WHERE project_id = ? AND layer = ?;

# If SCAN instead of SEARCH, add index
CREATE INDEX idx_semantic_project_layer
ON semantic_memories(project_id, layer);
```

### Step 5: Implement Fix
```python
# Example: Add index
import sqlite3
conn = sqlite3.connect('~/.athena/memory.db')
conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_episodic_session_time
    ON episodic_events(session_id, timestamp)
""")
conn.commit()
```

### Step 6: Validate Improvement
```bash
# Re-run benchmarks
python scripts/run_benchmark.py > after.txt

# Compare
diff baseline.txt after.txt

# Expected: Query latency reduced 5-10x, event insertion maintained
```

### Step 7: Commit & Document
```bash
git add -A
git commit -m "perf: add indexes to improve query latency

Before: query latency 200ms+
After: query latency <50ms (4x improvement)

Added indexes on:
- semantic_memories(project_id, layer)
- episodic_events(session_id, timestamp)"
```

## Performance Optimization Checklist

- [ ] Baseline metrics captured
- [ ] Bottleneck identified
- [ ] Root cause understood
- [ ] Fix implemented and tested
- [ ] Performance improved (measured)
- [ ] No regressions (benchmarks pass)
- [ ] Code reviewed
- [ ] Committed with clear message

## Related Skills

- **refactor-code** - Often needed alongside performance optimization
- **fix-failing-tests** - Performance regressions can break tests
- **debug-integration-issue** - Performance problems can indicate bugs

## Success Criteria

✓ Baseline metrics established
✓ Bottleneck identified and profiled
✓ Root cause understood
✓ Fix implemented safely
✓ Performance metrics improved (target: 5-10x)
✓ No regressions
✓ All benchmarks pass
