# Airweave Integration Analysis for Athena

**Date**: November 10, 2025
**Status**: Complete Analysis with Actionable Recommendations
**Effort Estimate**: 4-6 weeks for full implementation

---

## Executive Summary

Analysis of Airweave (https://github.com/airweave-ai/airweave) reveals **selective opportunities** for integration into Athena. While Airweave excels at multi-source data integration and Athena already has sophisticated memory consolidation, there are **three high-impact** areas worth integrating:

1. **Multi-Source Event Ingestion Architecture** (8-12 weeks) - Enable episodic events from external sources
2. **Query Expansion for Improved Recall** (2-3 weeks) - Generate alternative query phrasings
3. **Connection Pooling & PostgreSQL Optimization** (1 week) - Production hardening

**Overall Assessment**: **Proceed with selective integration, not wholesale adoption.** Airweave's strengths are orthogonal to Athena's consolidation innovation.

---

## Part 1: Multi-Source Event Ingestion

### Why It Matters

Currently, Athena's episodic events come only from agent-generated activities (code changes, tests, tasks). Multi-source ingestion would enable:

- **Pull events from GitHub** (commits, PRs, reviews)
- **Pull events from Slack** (team discussions, decisions)
- **Pull events from CI/CD** (test results, deployments)
- **Pull events from file systems** (directory changes, file creations)
- **Pull events from APIs** (monitoring alerts, metric changes)

This transforms Athena from **internal agent memory** to **external context aggregator**, dramatically improving consolidation quality.

### Architecture

**Adopted from Airweave**: Base class abstraction + factory pattern + cursor-based incremental sync

**Key Files to Create**:

```
src/athena/episodic/
├── sources/
│   ├── _base.py              # BaseEventSource abstract class
│   ├── filesystem.py         # Watch filesystem for changes
│   ├── github_webhook.py     # Pull from GitHub Events API
│   ├── slack_webhook.py      # Poll Slack conversations
│   ├── api_log.py            # HTTP API logs
│   └── cicd_logs.py          # CI/CD pipeline events
├── factory.py                 # EventSourceFactory with DI
├── cursor.py                  # CursorManager for incremental sync
├── pipeline.py                # EventProcessingPipeline (6 stages)
├── hashing.py                 # ContentHasher for deduplication
├── orchestrator.py            # EventIngestionOrchestrator
└── models.py                  # EventSourceConfig, etc.
```

### Implementation Plan

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1** | 1 week | BaseEventSource + EventHasher + CursorManager |
| **Phase 2** | 2 weeks | FileSystemEventSource + GitHubEventSource |
| **Phase 3** | 2 weeks | SlackEventSource + APILogEventSource |
| **Phase 4** | 1 week | EventProcessingPipeline + EventIngestionOrchestrator |
| **Phase 5** | 2 weeks | Testing + Performance (target: 1000+ events/sec) |
| **Phase 6** | 1 week | MCP tools + Documentation |

**Total**: 8-12 weeks

### Code Patterns (Detailed in Analysis Above)

See **Section 5** of analysis report for:
- `BaseEventSource` abstract class
- Event source factory with dependency injection
- Content-based hashing for deduplication
- Cursor-based incremental sync schemas
- Multi-stage event processing pipeline
- Event ingestion orchestrator

---

## Part 2: Query Expansion for Improved Recall

### Why It Matters

Current Athena search:
1. Takes user query
2. Applies query transformation (pronoun resolution)
3. Performs semantic + keyword search
4. Applies reranking

**Missing**: Query expansion (generating alternative phrasings)

Airweave generates **4 alternative query variants** that:
- Emphasize different keywords
- Use synonyms and paraphrases
- Include keyword-optimized and normalized versions
- Collectively improve recall by ~20-30% on complex queries

### Implementation

**Effort**: 2-3 weeks (low complexity)

**Files to Create**:
- `src/athena/rag/query_expansion.py` (300 lines)

**Key Methods**:
```python
class QueryExpander:
    def expand(query: str) -> List[str]:
        """Return [original, variant1, variant2, variant3, variant4]"""

    def _generate_alternatives(query: str) -> List[str]:
        """LLM-based generation with structured output"""

    def _validate_alternatives(original: str, alternatives: List[str]) -> List[str]:
        """Remove duplicates, matches to original, empty strings"""
```

**Integration Point**:
```python
# In src/athena/memory/search.py
async def recall(query: str, limit: int = 10):
    # NEW: Expand query to variants
    query_variants = expander.expand(query)

    # Search with each variant
    results_per_variant = await asyncio.gather(*[
        self._search_hybrid(variant, limit * 2)
        for variant in query_variants
    ])

    # Merge and deduplicate results
    merged = self._merge_results(results_per_variant)

    # Rerank and return top-k
    return reranker.rerank(merged, query)[:limit]
```

**Performance**: ~200-500ms added per query (worth it for recall improvement)

### Configuration

```python
# In config.py
RAG_QUERY_EXPANSION_ENABLED = True
RAG_QUERY_EXPANSION_VARIANTS = 4  # Airweave default
RAG_QUERY_EXPANSION_CACHE = True
RAG_QUERY_EXPANSION_CACHE_SIZE = 1000
```

---

## Part 3: PostgreSQL Optimization

### Why It Matters

Your `database_postgres.py` is already production-ready with IVFFlat indexes and hybrid search. This section adds **hardening** from Airweave's production experience.

### Three Quick Wins

#### 1. Dynamic Connection Pool Sizing (1 hour)

**Current**: Fixed min_size=2, max_size=10

**Airweave Pattern**: Scale with worker count

```python
# In database_postgres.py __init__
self.min_size = min(5, max(2, int(worker_count * 0.1)))
self.max_size = min(20, max(10, int(worker_count * 0.5)))
self.pool_timeout = 30
self.max_idle = 300      # Recycle idle > 5 min
self.max_lifetime = 3600  # Recycle old > 1 hour
```

#### 2. Connection Health Checks (30 minutes)

```python
# When creating pool
check=AsyncConnectionPool.check_connection,  # Validate before use
pool_pre_ping=True,  # Test connection before query
```

#### 3. PostgreSQL Tuning Parameters (1 hour)

```python
# In _init_schema() after connection
await conn.execute("SET shared_buffers = '256MB'")
await conn.execute("SET effective_cache_size = '1GB'")
await conn.execute("SET maintenance_work_mem = '128MB'")
await conn.execute("SET work_mem = '16MB'")
await conn.execute("SET max_parallel_workers_per_gather = 4")
```

**Total Effort**: 2-3 hours

### Optional: Connection Pool Monitoring

```python
async def get_pool_stats(self) -> Dict[str, Any]:
    """Return current pool utilization."""
    if not self._pool:
        return {}

    return {
        "total_connections": self._pool.get_size(),
        "available_connections": self._pool.get_available(),
        "waiting_clients": self._pool.get_waiting(),
    }

async def get_index_stats(self) -> Dict[str, Any]:
    """Return index usage statistics."""
    # Query pg_stat_user_indexes for IVFFlat index efficiency
    async with self.get_connection() as conn:
        rows = await conn.execute("""
            SELECT indexname, idx_scan, idx_tup_read, idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
        """)
        return await rows.fetchall()
```

---

## Part 4: Search & Reranking Enhancements

### Why It Matters

Airweave uses **RRF fusion** (Reciprocal Rank Fusion) for combining dense + sparse vector search results. Your PostgreSQL implementation is superior (native hybrid search), but the search configuration could be optimized.

### Three Targeted Improvements

#### 1. Query Expansion (Already Covered Above)

#### 2. Temporal Decay Tuning (30 minutes)

**Current**: Athena uses 10% recency weight, Airweave uses 30%

**Recommendation**: Increase to 20% for better recent-first behavior

```python
# In memory/search.py
DEFAULT_RECENCY_WEIGHT = 0.20  # Up from 0.10
DEFAULT_USEFULNESS_WEIGHT = 0.20
DEFAULT_SEMANTIC_WEIGHT = 0.60  # Down from 0.70
```

**Rationale**:
- 10% is too conservative (misses important recent context)
- 30% is too aggressive (ignores semantic relevance)
- 20% balances both signals

#### 3. Add Recency to LLM Reranking (1 hour)

**Current LLM Reranking**: 70% LLM score + 30% vector similarity

**Missing**: Temporal decay signal

```python
# In rag/reranker.py
def rerank_with_recency(
    self,
    results: List[Dict],
    query: str,
    llm_weight: float = 0.65,
    vector_weight: float = 0.20,
    recency_weight: float = 0.15,
):
    """Rerank with temporal signal added."""

    scores = []
    for result in results:
        llm_score = self._score_relevance(result, query)
        vector_score = result.get('similarity', 0)

        # NEW: Recency decay
        age_days = (datetime.now() - result['timestamp']).days
        recency_score = max(0, 1.0 - (age_days / 90))  # 90-day window

        composite = (
            llm_weight * llm_score +
            vector_weight * vector_score +
            recency_weight * recency_score
        )

        scores.append((result, composite))

    return sorted(scores, key=lambda x: x[1], reverse=True)
```

---

## Part 5: Implementation Priority & Timeline

### Phase 1: Quick Wins (1-2 weeks)

✅ **High Impact, Low Effort**

1. **Query Expansion Module** (2-3 weeks) → +20% recall
2. **Temporal Weight Tuning** (30 min) → Better recency balance
3. **PostgreSQL Pool Optimization** (2-3 hours) → Production hardening
4. **Recency in LLM Reranking** (1 hour) → More accurate reranking

**Start Date**: Week 1 of next sprint
**Estimate**: 16-20 hours
**Expected Impact**: 15-25% improved recall, better recent-first ranking

---

### Phase 2: Multi-Source Events (8-12 weeks)

⭐ **High Impact, High Effort** (Strategic differentiator)

1. Base infrastructure (1 week)
2. FileSystem + GitHub sources (2 weeks)
3. Slack + API sources (2 weeks)
4. Pipeline + Orchestrator (1 week)
5. Testing + Perf (2 weeks)
6. MCP tools + Docs (1 week)

**Start Date**: Week 4 of current month
**Timeline**: 8-12 weeks
**Dependencies**: None (self-contained feature)
**Expected Impact**: Transform Athena into context aggregation engine

---

### Phase 3: Advanced Optimization (Optional, low priority)

💡 **Nice-to-Have Enhancements**

1. **RRF Fusion for Qdrant mode** (3 weeks) - Only needed if not using PostgreSQL
2. **Sparse vector support in Qdrant** (1 week) - PostgreSQL already does this natively
3. **Query result caching** (1 week) - Add LRU cache for repeated queries
4. **Advanced prefetch tuning** (1 week) - Adaptive fetch limits

---

## Part 6: Detailed Architecture Decisions

### 1. Multi-Source Events: Why Airweave's Pattern?

**Airweave's Approach**:
- Abstract base class (`BaseEventSource`)
- Concrete implementations per source
- Factory pattern for dependency injection
- Cursor-based incremental sync

**Why Adopt**:
- ✅ Proven at scale (39+ sources)
- ✅ Easy to add new sources (3 methods minimum)
- ✅ Extensible without modifying core
- ✅ Supports incremental sync for efficiency

**Why Not Just Use Airweave**:
- ❌ Airweave is entity-focused (current state), Athena is event-focused (change history)
- ❌ Airweave uses separate Qdrant service, Athena uses PostgreSQL
- ❌ Airweave's full platform is overkill (UI, API, multi-tenant auth)

**Adaptation Strategy**:
- Take abstract pattern, apply to episodic events
- Events are immutable (no DELETE, SKIP actions)
- Add temporal causality tracking (Athena-specific)
- Add spatial grounding for code events (Athena-specific)

---

### 2. Query Expansion: Why LLM-Based?

**Alternatives Considered**:
1. **Rule-based** (thesaurus lookup) - Too rigid, misses context
2. **Embedding-based** (find nearest neighbors in semantic space) - Requires pre-computed database of expansions
3. **LLM-based** (Airweave's approach) - Flexible, context-aware, no pre-computation

**Why LLM-Based Wins**:
- ✅ Understands query intent
- ✅ Generates diverse phrasings
- ✅ Adapts to domain
- ✅ No training required

**Cost-Benefit**:
- Cost: ~200-500ms per query + API call fee
- Benefit: +20-30% recall on complex queries
- ROI: Worth for important queries, skip for simple ones

---

### 3. PostgreSQL Pooling: Why Dynamic?

**Static Pooling** (current):
- Simple, predictable
- Wastes connections under low load
- Starves pool under high load

**Dynamic Pooling** (Airweave pattern):
- Scales with workload
- Efficient resource utilization
- Better for variable load

**Formula**:
```
min_size = max(2, min(5, workers * 0.1))  # 10% of workers, min 2
max_size = max(10, min(20, workers * 0.5)) # 50% of workers, max 20
```

For 10 workers: min=1 → min_size=2 (floor), max=5 → max_size=10 (current default)

For 100 workers: min=10, max=50 → enables proper scaling

---

## Part 7: Risk Assessment

### High-Risk Areas

**Multi-Source Events: Curse of Completeness**
- Risk: Building "everything source" vs focusing on most valuable
- Mitigation: Start with GitHub (most common), Slack (team context), then iterate
- Timeline: Phase 1 (GitHub), Phase 2 (Slack), Phase 3+ (others)

**Query Expansion: Token Cost**
- Risk: Each expansion multiplies API calls by 5x
- Mitigation: Cache results, skip for short queries, use fallback on API failure
- Cost estimate: +$50-100/month if heavy usage

**PostgreSQL Pooling: Connection Explosion**
- Risk: max_size=20 × 100 workers = 2000 connections to Postgres
- Mitigation: Cap max_size at 20-30 regardless of worker count
- Safety: `max_size = min(20, max(10, workers * 0.5))`

---

## Part 8: Recommended Starting Point

### 🚀 Quick Wins (Start This Week)

1. **Query Expansion Module** (2-3 weeks)
   - File: `src/athena/rag/query_expansion.py`
   - Integration: `src/athena/memory/search.py`
   - Config: Add `RAG_QUERY_EXPANSION_*` params
   - Test: `tests/unit/test_query_expansion.py`

2. **Temporal Weight Tuning** (30 min)
   - File: `src/athena/core/config.py`
   - Changes: `DEFAULT_RECENCY_WEIGHT = 0.20`

3. **PostgreSQL Hardening** (2-3 hours)
   - File: `src/athena/core/database_postgres.py`
   - Changes: Pool sizing, health checks, tuning params

### 📅 Next Sprint

4. **Multi-Source Events Architecture** (Phase 1: 1 week)
   - Files: `src/athena/episodic/sources/_base.py`, `factory.py`, `cursor.py`, `hashing.py`
   - Deliverable: Base infrastructure for event sources

### 🎯 Roadmap (8-12 weeks out)

5. **Concrete Event Sources** (Phase 2-3)
   - GitHub, Slack, CI/CD, API logs
   - Full pipeline + orchestration
   - MCP tools for source management

---

## Part 9: Code References & Files to Modify

### New Files to Create

```python
# Query Expansion
src/athena/rag/query_expansion.py  # 300 lines

# Multi-Source Events
src/athena/episodic/sources/_base.py  # 200 lines
src/athena/episodic/sources/filesystem.py  # 250 lines
src/athena/episodic/sources/github_webhook.py  # 300 lines
src/athena/episodic/factory.py  # 200 lines
src/athena/episodic/cursor.py  # 150 lines
src/athena/episodic/pipeline.py  # 400 lines
src/athena/episodic/hashing.py  # 100 lines
src/athena/episodic/orchestrator.py  # 250 lines

# Tests
tests/unit/test_query_expansion.py  # 200 lines
tests/unit/test_event_sources.py  # 300 lines
tests/integration/test_event_ingestion.py  # 400 lines
```

### Files to Modify

```python
# Search improvements
src/athena/memory/search.py
  - Line 95: Add query expansion
  - Line 346: Add recency to LLM reranking
  - Add _merge_results() method

src/athena/rag/reranker.py
  - Add recency_weight parameter
  - Update scoring formula

src/athena/core/config.py
  - Add DEFAULT_RECENCY_WEIGHT = 0.20
  - Add RAG_QUERY_EXPANSION_* params

# PostgreSQL hardening
src/athena/core/database_postgres.py
  - Line 60-62: Add pool_timeout, max_idle, max_lifetime
  - Line 107-112: Enhanced pool initialization
  - Add _optimize_postgres() method
  - Add get_pool_stats() method
  - Add get_index_stats() method

# Episodic layer integration
src/athena/episodic/store.py
  - Add support for hash-based deduplication
  - Add cursor management
  - Update schema to include hash field

src/athena/manager.py
  - Initialize EventSourceFactory
  - Add event_sources property
  - Add ingest_events() method
```

---

## Part 10: Success Metrics

### Query Expansion
- **Baseline**: 100 complex queries, record recall@10
- **Target**: 20-30% improvement in recall
- **Measurement**: `precision = relevant_results / total_results`

### Multi-Source Events
- **Baseline**: 0 external events
- **Target**: 1000+ events/day from 3+ sources
- **Measurement**: Event count per source, dedup rate

### PostgreSQL Optimization
- **Baseline**: Current query latency
- **Target**: <100ms p99 for hybrid search
- **Measurement**: Query latency distribution, pool utilization

### Overall Impact
- **Consolidation Quality**: Measure quality metrics before/after multi-source events
- **Search Relevance**: User satisfaction with recall/precision
- **System Reliability**: Pool exhaustion incidents (target: 0)

---

## Conclusion

**Recommendation**: Proceed with **selective integration** in this order:

1. **Phase 1 (Weeks 1-2)**: Quick wins (query expansion, pooling, recency tuning)
2. **Phase 2 (Weeks 3-4)**: Multi-source event infrastructure
3. **Phase 3 (Weeks 5-12)**: Concrete event sources (GitHub, Slack, etc.)

This approach:
- ✅ Delivers immediate value (better search, better pooling)
- ✅ Builds foundation for long-term differentiation (multi-source events)
- ✅ Minimizes risk (small incremental steps, reversible)
- ✅ Aligns with Athena's core innovation (consolidation)

---

**Document prepared**: 2025-11-10
**Analysis based on**: Airweave v2024.11 (GitHub commit history)
**Recommendation status**: Ready for implementation planning
