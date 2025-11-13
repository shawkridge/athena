# Cascading Recall Implementation Analysis

## Executive Summary

The Athena codebase implements a sophisticated **multi-tier cascading recall system** that retrieves information across 8 memory layers with progressive enrichment. The implementation spans 3 tiers with increasing complexity: fast direct queries (Tier 1), cross-layer enrichment (Tier 2), and LLM-synthesized synthesis (Tier 3).

**Key Finding**: The system is well-structured but has several optimization opportunities at each tier level, particularly around caching, batch operations, and intelligent depth selection.

---

## 1. FILE LOCATIONS & MODULE STRUCTURE

### Core Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `/src/athena/manager.py` | 1,073 | Main UnifiedMemoryManager with `recall()` method (lines 751-863) |
| `/src/athena/rag/manager.py` | 547 | RAGManager for Tier 3 LLM synthesis |
| `/src/athena/session/context_manager.py` | 480 | SessionContextManager for context-aware retrieval |
| `/src/athena/performance/cache.py` | 368 | LRUCache & QueryCache implementations |
| `/src/athena/performance/monitor.py` | 348 | Performance monitoring metrics |
| `/src/athena/hooks/lib/cascade_monitor.py` | 193 | Cascade depth & breadth limit enforcement |

### Supporting Recall Components

```
src/athena/
├── manager.py                          # recall() entry point
├── session/context_manager.py          # Session context loading
├── rag/manager.py                      # Tier 3 synthesis
├── memory/store.py                     # Tier 1 semantic queries
├── episodic/store.py                   # Tier 1 episodic queries
├── procedural/store.py                 # Tier 1 procedural queries
├── prospective/store.py                # Tier 1 prospective queries
├── graph/store.py                      # Tier 1 graph queries
├── meta/store.py                       # Tier 2 meta queries
├── performance/cache.py                # Query result caching
├── performance/monitor.py              # Performance metrics
└── hooks/lib/cascade_monitor.py        # Cascade safety
```

---

## 2. CURRENT ARCHITECTURE & DEPTH LEVELS

### Tier Structure

```
Cascading Recall Pyramid
═════════════════════════════════════════════════════════════════

TIER 3: LLM-Synthesized Results (if cascade_depth >= 3 AND rag_manager available)
├── RAG synthesis across all tier 1 results
├── Planning-aware synthesis for complex queries
└── Cost: ~500-2000ms per query (depends on LLM)

TIER 2: Enriched Cross-Layer Context (if cascade_depth >= 2)
├── Hybrid multi-layer search
├── Session context enrichment
├── Meta-memory queries
└── Cost: ~100-300ms

TIER 1: Fast Layer-Specific Searches (always executed)
├── Episodic: Recent events, temporal queries
├── Semantic: Factual knowledge, embeddings
├── Procedural: Workflows, how-to queries
├── Prospective: Tasks, goals, reminders
├── Graph: Relationships, dependencies
└── Cost: ~50-150ms

═════════════════════════════════════════════════════════════════
```

### Depth Configuration

```python
# From manager.py:751-863

def recall(
    self,
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    cascade_depth: int = 3,              # Default: all 3 tiers
    include_scores: bool = True,
    explain_reasoning: bool = False,
) -> dict:
    """
    cascade_depth: int (1-3, auto-clamped)
    - 1: Tier 1 only (fast, 50-150ms)
    - 2: Tier 1 + Tier 2 (enriched, 150-450ms)
    - 3: All tiers (full synthesis, 650-2450ms)
    """
    cascade_depth = min(max(1, cascade_depth), 3)  # Clamp to 1-3
```

### Query Routing at Each Tier

**Tier 1 Routing Logic** (_recall_tier_1, lines 865-906):
```python
# Intelligent layer selection based on keywords
- "when", "last", "recent", "error", "failed" → Episodic
- Always included → Semantic (factual queries)
- "how", "do", "build", "implement" → Procedural
- "task", "goal", "todo", "should" → Prospective
- "relates", "depends", "connected" → Graph
- Phase == "debugging" → Episodic (context-aware)
```

**Tier 2 Enrichment** (_recall_tier_2, lines 908-951):
```python
- Hybrid search across selected layers from Tier 1
- Meta-queries about phase context
- Session context injection (recent_events, task, phase)
```

**Tier 3 Synthesis** (_recall_tier_3, lines 953-994):
```python
- RAG.retrieve() with auto-strategy selection
- Planning-aware synthesis if phase in ["planning", "refactoring"]
- Graceful degradation if RAG unavailable
```

---

## 3. QUERY TYPES HANDLED

### Primary Query Type Classification

From `manager.py:_classify_query()` (lines 291-331):

| Query Type | Keywords | Routed to Layer |
|-----------|----------|-----------------|
| **TEMPORAL** | when, last, recent, yesterday, week, month, date, time | Episodic (Tier 1) |
| **FACTUAL** | (default) | Semantic (Tier 1) |
| **RELATIONAL** | depends, related, connection, linked, uses, implements | Graph (Tier 1) |
| **PROCEDURAL** | how to, how do, workflow, process, steps, procedure | Procedural (Tier 1) |
| **PROSPECTIVE** | task, todo, remind, remember to, pending, need to | Prospective (Tier 1) |
| **META** | what do we know, what have we learned, coverage, expertise | Meta (Tier 2) |
| **PLANNING** | decompose, plan, strategy, orchestration, validate, project status | Planning RAG (Tier 3) |

### Session Context Integration

From `session/context_manager.py`:
```python
# Automatically loaded if session active
context.update({
    "session_id": session_context.session_id,
    "task": session_context.current_task,      # e.g., "Debug failing test"
    "phase": session_context.current_phase,    # e.g., "debugging", "refactoring"
    "recent_events": session_context.recent_events,  # Last N events in session
})
```

**Impact on Tier 1**: Context-aware layer selection
- `phase == "debugging"` → Include episodic layer
- `task` → Influences prospective layer inclusion

**Impact on Tier 2**: Session context enrichment
- Recent events from session injected directly
- Phase-aware meta queries

---

## 4. CACHING & OPTIMIZATION STATUS

### Current Caching Implementation

From `performance/cache.py`:

**LRUCache (Lines 46-157)**
- Max size: 1,000 entries (configurable)
- TTL: 1 hour default (3,600 seconds)
- Hit tracking: `hits` / `misses` counters
- Eviction: LRU on capacity exceeded

**QueryCache (Lines 159-229)**
- Specialized for SQL query results
- Hash-based keying: `MD5(query + params)`
- TTL: 5 minutes default (300 seconds)
- Pattern-based invalidation: `invalidate_pattern(table_name)`

**EntityCache (Lines 232-324)**
- 5,000 entity limit
- Indexed by: file_path, entity_type
- Invalidation by file: `invalidate_file(file_path)`

### Current Cache Usage

```python
# In manager.py, NO explicit caching at recall level
# Caching happens at individual layer level:
- semantic.search() → May use internal embeddings cache
- episodic.search_events() → May use temporal indexes
- graph._query_graph() → Uses pathfinding cache

# Performance/monitoring.py provides metrics but NOT used in recall path
```

### Cache Warmup Capability

From `performance/cache.py:148-156`:
```python
def warmup(self, data: dict[str, Any], ttl_seconds: Optional[int] = None):
    """Pre-load cache with data."""
    for key, value in data.items():
        self.set(key, value, ttl_seconds)
```

**Current Status**: Cache warmup available but NOT integrated into recall path.

---

## 5. PERFORMANCE CHARACTERISTICS

### Measured Performance Metrics

From `performance/monitor.py`:
```python
# Tracking available for:
- Operation timing (PerformanceMetric: count, avg, min, max, p50, p95, p99)
- Operation counting
- Error counting
- System stats (CPU%, memory, threads)
```

### Estimated Latency per Tier

| Tier | Operation | Est. Time | Bottleneck |
|------|-----------|-----------|-----------|
| **1** | Semantic search | 50-80ms | Embeddings generation |
| **1** | Episodic search | 30-50ms | Temporal index lookup |
| **1** | Graph query | 20-40ms | Index traversal |
| **2** | Hybrid search | 100-200ms | Multiple layer coordination |
| **2** | Session enrichment | 10-20ms | Context merging |
| **3** | RAG synthesis | 500-2000ms | LLM API call |
| **3** | Planning synthesis | 300-1000ms | Complex reasoning |

### Critical Path Analysis

```
Cascade Depth 3 Timeline (worst case):
├─ Load session context: 5-10ms
├─ Tier 1 queries (parallel): 50-150ms
│  ├─ Episodic: 30-50ms
│  ├─ Semantic: 50-80ms (includes embedding lookup)
│  ├─ Procedural: 40-60ms
│  ├─ Prospective: 30-50ms
│  └─ Graph: 20-40ms
├─ Tier 2 enrichment: 100-300ms
│  ├─ Hybrid search: 100-200ms
│  ├─ Meta query: 20-50ms
│  └─ Session context: 10-20ms
├─ Tier 3 synthesis: 500-2000ms
│  ├─ RAG retrieval: 300-1500ms
│  └─ Planning synthesis: 200-500ms
└─ Total: 655-2460ms

OPTIMIZATION TARGETS:
1. Tier 1: Parallelize layer queries (currently sequential)
2. Tier 2: Cache hybrid search results (5min TTL)
3. Tier 3: Depth-based LLM cost optimization
```

### Memory Usage

From cascade_monitor.py:
```python
# Tracks call stack depth & breadth
- max_depth: 5 (for hooks)
- max_breadth: 10 (concurrent triggers)

# Estimated memory per recall:
- Tier 1 results: ~10-50KB
- Tier 2 enrichment: ~5-20KB
- Tier 3 synthesis: ~20-100KB
- Session context: ~5-10KB
```

---

## 6. PERFORMANCE BOTTLENECKS IDENTIFIED

### Critical Bottleneck #1: Sequential Tier 1 Queries

**Location**: `manager.py:865-906` (_recall_tier_1)

```python
# CURRENT: Sequential execution
tier_1["episodic"] = self._query_episodic(query, context, k)   # waits
tier_1["semantic"] = self._query_semantic(query, context, k)   # then this
tier_1["procedural"] = self._query_procedural(...)             # then this
```

**Impact**: 50-150ms total when could be ~80-150ms with parallelization

**Fix**: Use `asyncio.gather()` for independent layer queries

---

### Critical Bottleneck #2: No Caching at Recall Level

**Location**: `manager.py:751-863` (recall method)

**Current State**:
- Each recall() calls _recall_tier_1, _recall_tier_2, _recall_tier_3
- No deduplication of repeated queries
- No result caching across sessions

**Impact**: Repeated queries cost 650-2450ms each

**Example**: Two users asking "What was the error?" in same session
- Query 1: 650-2450ms (full execution)
- Query 2: 650-2450ms (full recomputation)
- Could be: Query 2: ~50ms with 5-minute cache TTL

---

### Critical Bottleneck #3: Tier 3 Always Uses Full RAG

**Location**: `manager.py:835-839` (_recall_tier_3)

```python
if cascade_depth >= 3 and self.rag_manager:
    rag_results = self.rag_manager.retrieve(query, context=context, k=k)
    # Always auto-selects strategy; expensive for simple queries
```

**Impact**: LLM synthesis even for simple factual queries

**Example Costs**:
- Query: "What is a list in Python?" 
  - Optimal: Semantic search only (50-80ms)
  - Current: Full RAG synthesis (500-2000ms)
  - Overhead: 10-25x slowdown

---

### Critical Bottleneck #4: No Query-to-Depth Mapping

**Location**: `manager.py:756` (cascade_depth parameter)

**Current State**:
```python
# Users must manually specify depth
manager.recall("What is X?", cascade_depth=3)  # Overkill for simple fact
manager.recall("Should I...?", cascade_depth=3)  # Correct complexity

# No automatic depth selection based on query complexity
```

**Impact**: Users use max depth for all queries, wasting resources

**Analysis**:
- "What is Python?" → Depth 1 ideal (semantic only)
- "What should I do about the failing test?" → Depth 2 ideal (context enrichment)
- "Decompose this complex system" → Depth 3 ideal (planning synthesis)

---

### Critical Bottleneck #5: Session Context Load Overhead

**Location**: `manager.py:806-817` (session context loading)

```python
if self.session_manager:
    session_context = self.session_manager.get_current_session()
    # Single database query per recall, even if no session active
```

**Impact**: 5-10ms per recall when session exists

**Opportunity**: Cache session context reference in memory

---

### Critical Bottleneck #6: No Tier 1 Result Batching

**Location**: `manager.py:889` (_recall_tier_1)

```python
tier_1["semantic"] = self._query_semantic(query, context, k)

# _query_semantic calls:
# 1. Get project
# 2. Classify query type  
# 3. Run RAG or basic search
# 4. Apply scores (if enabled)
# 5. Project fields (if specified)
```

**Impact**: 4-6 database round-trips per layer query

**Opportunity**: Batch semantic embeddings lookup, project fields once

---

## 7. CALLING PATTERNS & DEPTH USAGE

### Test Suite Analysis

From `tests/unit/test_cascading_recall.py`:

```python
# Tier 1 focus (depth=1): 36% of tests
def test_recall_basic_single_tier(...)
def test_recall_empty_query(...)
def test_recall_with_zero_k(...)

# Tier 1-2 (depth=2): 28% of tests  
def test_recall_two_tiers(...)
def test_tier_2_enrichment(...)
def test_recall_with_different_contexts(...)

# All tiers (depth=3): 24% of tests
def test_recall_three_tiers(...)
def test_recall_full_workflow(...)

# Error handling: 12% of tests
def test_recall_handles_tier_1_error(...)
def test_recall_handles_session_context_error(...)
```

### Likely Production Patterns

Based on implementation design:

```python
# Quick fact retrieval (estimated 40% of calls)
manager.recall("What is X?", cascade_depth=1)  # 50-150ms

# Context-aware queries (estimated 35% of calls)
manager.recall("What were we working on?", cascade_depth=2)  # 150-450ms

# Complex reasoning (estimated 20% of calls)
manager.recall("What should we do?", cascade_depth=3)  # 650-2450ms

# Session-based queries (estimated 40% of all calls use session context)
session_mgr.start_session(...)
manager.recall(...)  # Auto-loads context, biases layer selection
```

**Depth Distribution Hypothesis**:
- Depth 1: 40% of calls (5-10ms cost saved vs depth 2)
- Depth 2: 35% of calls  
- Depth 3: 20% of calls (5-10% use RAG, most fail to RAG)
- Mixed: 5% (edge cases, experiments)

---

## 8. TIER SELECTION OPTIMIZATION OPPORTUNITIES

### Opportunity #1: Query Complexity Classification

```python
# Add to manager.py

class QueryComplexity:
    SIMPLE = 1      # "What is...?"
    CONTEXTUAL = 2  # "What should...?" (needs context)
    REASONING = 3   # "Decompose..." (needs LLM)

def _select_cascade_depth(query: str, context: dict) -> int:
    """Recommend cascade depth based on query characteristics."""
    
    # Check for planning indicators
    if any(kw in query.lower() for kw in 
           ["decompose", "plan", "strategy", "validate", "recommend"]):
        return QueryComplexity.REASONING
    
    # Check for contextual indicators
    if context.get("phase") or context.get("recent_events"):
        return QueryComplexity.CONTEXTUAL
    
    # Default to simple
    return QueryComplexity.SIMPLE
```

**Expected Impact**:
- 25-30% reduction in average latency
- 40% reduction in LLM synthesis calls
- Better UX (queries complete faster)

---

### Opportunity #2: Tier 1 Query Parallelization

```python
# Replace sequential execution with async parallelization
async def _recall_tier_1_async(self, query: str, context: dict, k: int) -> dict:
    """Parallel execution of layer-specific searches."""
    
    # All independent queries run concurrently
    tasks = {
        "episodic": self._query_episodic_async(query, context, k),
        "semantic": self._query_semantic_async(query, context, k),
        "procedural": self._query_procedural_async(query, context, k),
        # ...
    }
    
    # Gather all results
    return await asyncio.gather(*tasks.values())
```

**Expected Impact**:
- Tier 1: 50-150ms → 50-80ms (30-50% faster)
- Overall depth 1: 100-200ms → 70-130ms
- Overall depth 2: 200-450ms → 150-380ms

---

### Opportunity #3: Cascade Result Caching

```python
# Add to manager.py

from performance.cache import LRUCache

class CascadingRecallCache:
    def __init__(self, max_size: int = 500):
        self.results = LRUCache(max_size=max_size, default_ttl_seconds=300)  # 5 min
        self.session_caches = {}  # Per-session caches
    
    def get_cache_key(query: str, context: dict, depth: int) -> str:
        """Hash query + context + depth."""
        return hashlib.md5(
            f"{query}:{sorted(context.items())}:{depth}".encode()
        ).hexdigest()
    
    def get(self, query: str, context: dict, depth: int) -> Optional[dict]:
        """Retrieve cached cascade results."""
        key = self.get_cache_key(query, context, depth)
        return self.results.get(key)
    
    def set(self, query: str, context: dict, depth: int, results: dict):
        """Cache cascade results."""
        key = self.get_cache_key(query, context, depth)
        self.results.set(key, results, ttl_seconds=300)
```

**Expected Impact**:
- Repeated queries: 650-2450ms → 50-100ms (10-30x faster)
- Memory: ~5-10MB for 500 cached results
- Hit rate: ~30-40% for typical session (based on repeat questions)

---

### Opportunity #4: Intelligent Tier 3 Dispatch

```python
def _should_use_tier_3_rag(self, query: str, tier_1_results: dict) -> bool:
    """Determine if Tier 3 RAG synthesis adds value."""
    
    # Skip Tier 3 if Tier 1 has high-quality results
    if tier_1_results.get("semantic", []):
        top_score = tier_1_results["semantic"][0].get("relevance", 0)
        if top_score > 0.85:  # Already high-quality
            return False
    
    # Skip Tier 3 for simple factual queries
    if self._is_simple_factual_query(query):
        return False
    
    # Use Tier 3 for complex reasoning
    if any(kw in query.lower() for kw in ["decompose", "recommend", "strategy"]):
        return True
    
    return False  # Default: no RAG
```

**Expected Impact**:
- 30-50% fewer RAG calls
- 200-1000ms savings per avoided synthesis
- 10-20% reduction in overall latency

---

### Opportunity #5: Session Context Caching

```python
class SessionContextCache:
    def __init__(self):
        self.sessions = {}  # session_id -> cached context + timestamp
        self.cache_ttl = 10  # seconds
    
    def get_context(self, session_id: str) -> Optional[dict]:
        """Get cached session context."""
        if session_id in self.sessions:
            cached, timestamp = self.sessions[session_id]
            if time.time() - timestamp < self.cache_ttl:
                return cached
        return None
    
    def invalidate_session(self, session_id: str):
        """Invalidate session cache (called on update_context)."""
        if session_id in self.sessions:
            del self.sessions[session_id]
```

**Expected Impact**:
- Session context load: 5-10ms → <1ms (cache hit)
- Recall overhead: 5-10% reduction
- Memory: <1MB for 1000 sessions

---

## 9. CACHE-FRIENDLY DATA ACCESS PATTERNS

### Current Patterns

**Pattern 1: Layer-by-layer sequential access**
```python
# From manager.py:889-901
tier_1["episodic"] = self._query_episodic(...)
tier_1["semantic"] = self._query_semantic(...)
tier_1["procedural"] = self._query_procedural(...)
```

**Cache Impact**: 
- L1 cache: Layer filter predicates evicted between queries
- SQLite query cache: Unused (separate queries, different tables)
- Embedding cache: Cold hit rate (different queries)

---

**Pattern 2: Context-aware layer selection**
```python
# From manager.py:882-885
if context.get("phase") == "debugging" or any(
    word in query.lower()
    for word in ["when", "last", "recent", "error", "failed"]
):
    tier_1["episodic"] = self._query_episodic(...)
```

**Cache Impact**:
- Good: Reduces query branching (fewer executed paths)
- Bad: Context reads (database) for every recall call

---

### Recommended Access Patterns for Optimization

**Pattern A: Batch Similar Layer Queries**
```python
# Group queries to same table for cache locality
# Before: [episodic, semantic, procedural] (3 tables)
# After: [episodic+episodic_relations, semantic+semantic_vectors, procedural]
```

**Pattern B: Pre-load Common Projections**
```python
# Cache query with all projection fields
# Instead of: SELECT id, content FROM semantic_memory
#           SELECT id, content, relevance, tags, ...
# (Projects once, reuse cache)
```

**Pattern C: Session Context Pinning**
```python
# Keep session context in memory (SessionContext object)
# Instead of: Database query per recall() call
# (Invalidate on update_context() only)
```

**Pattern D: Temporal Locality in Episodic Queries**
```python
# Access recent events → already in warm cache
# Query: SELECT * FROM episodic_events 
#        WHERE timestamp > now() - 1 hour
# ORDER BY timestamp DESC
# (Leverages index on timestamp + sequential disk I/O)
```

---

## 10. KEY RECOMMENDATIONS

### High Priority (20-30% latency improvement)

1. **Implement Cascade Result Caching** (5 min TTL)
   - Location: `manager.py` before recall() returns
   - Impact: 10-30x faster for repeated queries
   - Complexity: Low (use existing LRUCache)

2. **Parallelize Tier 1 Queries** (asyncio.gather)
   - Location: `manager.py:_recall_tier_1()`
   - Impact: 30-50% faster for tier 1
   - Complexity: Medium (async refactor)

3. **Add Query Complexity Classification** (depth auto-selection)
   - Location: New method in manager.py
   - Impact: 25-30% average latency reduction
   - Complexity: Low (keyword-based heuristics)

---

### Medium Priority (10-15% latency improvement)

4. **Cache Session Context Reference** (in-memory)
   - Location: `manager.py` + `session/context_manager.py`
   - Impact: 5-10ms savings per recall with active session
   - Complexity: Low

5. **Intelligent Tier 3 Dispatch** (skip when unnecessary)
   - Location: `manager.py:_recall_tier_3()`
   - Impact: 30-50% fewer LLM calls
   - Complexity: Medium

---

### Lower Priority (5-10% latency improvement)

6. **Batch Database Queries** (combine projections)
   - Location: Individual layer query methods
   - Impact: 10-15% reduction in query latency
   - Complexity: High (refactor layer logic)

7. **Implement Cache Warmup** (session start)
   - Location: `session/context_manager.py`
   - Impact: 5-10% faster initial queries
   - Complexity: Low

---

## 11. IMPLEMENTATION ROADMAP

### Phase 1 (Week 1-2): Quick Wins
- [ ] Add cascade result caching (QueryCache.set/get wrapper)
- [ ] Add query complexity classification (heuristics)
- [ ] Cache session context reference in memory

### Phase 2 (Week 3-4): Medium Complexity
- [ ] Parallelize Tier 1 queries (asyncio refactor)
- [ ] Add intelligent Tier 3 dispatch (quality checks)
- [ ] Implement cache hit metrics

### Phase 3 (Week 5-6): Advanced Optimization
- [ ] Batch database queries (layer refactor)
- [ ] Temporal locality optimization (episodic indexing)
- [ ] Per-session cache isolation (memory isolation)

---

## 12. METRICS TO TRACK

### Performance Baselines (Pre-Optimization)

```python
# Record with performance/monitor.py

# Tier 1 latency by layer
manager.timer("tier_1_episodic").record()
manager.timer("tier_1_semantic").record()
manager.timer("tier_1_procedural").record()

# Tier 2/3 latency
manager.timer("tier_2_hybrid").record()
manager.timer("tier_3_rag").record()

# Cache metrics
cache.get_stats()  # {hits, misses, hit_rate, size}

# Session context metrics
session_context_cache.get_stats()

# Query complexity distribution
{
    "depth_1": count,
    "depth_2": count,
    "depth_3": count,
}
```

### Optimization Success Metrics

After implementing recommendations:

| Metric | Target |
|--------|--------|
| P50 latency (all depths) | -25% |
| P95 latency (depth 3) | -40% |
| Cache hit rate | >30% |
| LLM call reduction | -40% |
| Repeated query speedup | 10-30x |

---

## 13. CONCLUSION

The cascading recall system is well-architected with three distinct tiers providing progressive enrichment. The main opportunities lie in:

1. **Caching** - Most impactful, easiest to implement
2. **Parallelization** - Good ROI, requires async refactor
3. **Intelligent Dispatch** - Reduces unnecessary computation

Combined, these optimizations could achieve:
- **25-30% average latency reduction**
- **10-30x speedup for repeated queries**
- **40-50% fewer LLM synthesis calls**
- **Overall system 40-50% more responsive**

The infrastructure for these optimizations exists (caching, monitoring); implementation requires integration into the recall critical path.

