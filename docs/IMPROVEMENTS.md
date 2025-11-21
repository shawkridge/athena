# Athena Improvements Roadmap

**Last Updated**: 2025-11-21
**Status**: Active Development
**Version**: 1.0

This document outlines prioritized improvements for Athena's memory system, organized by impact and implementation effort.

---

## Table of Contents

1. [P0: Critical Fixes](#p0-critical-fixes)
2. [P1: High-Impact Improvements](#p1-high-impact-improvements)
3. [P2: Enhancements](#p2-enhancements)
4. [P3: Future Exploration](#p3-future-exploration)
5. [Implementation Guidelines](#implementation-guidelines)

---

## Priority Legend

- **P0**: Blockers - Must fix for production use
- **P1**: High Impact - Significant user/system value
- **P2**: Enhancements - Nice-to-have features
- **P3**: Exploration - Research/experimental features

**Effort Scale**: S (small, <1 day), M (medium, 1-3 days), L (large, 1-2 weeks), XL (very large, >2 weeks)

---

## P0: Critical Fixes

### 1. Complete Skipped Test Stubs

**Status**: 🔴 Blocking
**Effort**: M-L
**Impact**: High (testing coverage)

**Problem**: 6 integration tests are skipped due to incomplete stubs (see `README.md:126-135`):

1. `test_task_learning_with_llm.py` - LLM integration incomplete
2. `test_athena_cli.py` - CLI stubs missing
3. `test_tool_integration.py` - Tool registry incomplete
4. `test_meta_field_persistence.py` - Meta-field schema unfinished
5. `test_research_agents.py` - Research agents stub
6. `test_memory_tools.py` - Tool wrappers incomplete

**Solution**:
- Implement missing CLI commands in `src/athena/cli/`
- Complete tool registry in `src/athena/mcp/handlers.py:335`
- Finish meta-field schema in `src/athena/meta/models.py`
- Implement research agent stubs in `src/athena/agents/`
- Add tool wrappers in `src/athena/tools/`

**Files**:
- `tests/e2e/test_task_learning_with_llm.py.skip`
- `tests/integration/test_athena_cli.py.skip`
- `tests/unit/mcp/test_tool_integration.py.skip`
- `tests/unit/test_meta_field_persistence.py.skip`
- `tests/unit/test_research_agents.py.skip`
- `tests/unit/tools/test_memory_tools.py.skip`

**Acceptance Criteria**:
- All 6 skipped tests pass
- No regression in existing 8,705 passing tests
- Code coverage remains >85%

---

### 2. PostgreSQL Connection Pooling Optimization

**Status**: 🟡 Performance Issue
**Effort**: M
**Impact**: High (query latency)

**Problem**: Current implementation uses basic async connection pooling (`src/athena/core/database.py:52-67`), but doesn't implement:
- Connection health checks
- Idle connection timeout
- Connection retry with exponential backoff
- Pool size auto-tuning based on load

**Solution**:
```python
# src/athena/core/database.py
class Database:
    def __init__(self, ...):
        self.pool_config = {
            "min_size": int(os.environ.get("DB_MIN_POOL_SIZE", "2")),
            "max_size": int(os.environ.get("DB_MAX_POOL_SIZE", "10")),
            "max_idle": 300,  # 5 minutes
            "max_lifetime": 1800,  # 30 minutes
            "health_check_interval": 60,  # 1 minute
        }

    async def _health_check(self):
        """Periodic health check for pooled connections."""
        # SELECT 1 test, reconnect if failed
```

**Metrics to Track**:
- Query latency (p50, p95, p99)
- Connection acquisition time
- Pool exhaustion events
- Connection errors

**Acceptance Criteria**:
- No connection leaks after 1000+ queries
- p95 query latency < 50ms (local PostgreSQL)
- Pool exhaustion < 1% under normal load

---

## P1: High-Impact Improvements

### 3. User Profile Modeling (Meta-Memory Enhancement)

**Status**: 🟡 Partial Implementation
**Effort**: L
**Impact**: High (context personalization)

**Problem**: Current meta-memory tracks **agent expertise** (`src/athena/meta/operations.py:75-80`), not **user preferences/goals**. From "RAG is Dead" analysis:
> The article suggests "user profiles injected as default context." Athena has Layer 6 (Meta-Memory) tracking domain expertise, but this is agent-centric, not user-centric.

**Current State**:
```python
# src/athena/meta/operations.py:75
async def get_expertise(
    topic: str | None = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get expertise scores for a topic or all topics."""
```

**Proposed Enhancement**:
```python
# New: src/athena/meta/user_profile.py
class UserProfile(BaseModel):
    user_id: str
    preferences: dict  # {
        # "communication_style": "concise"|"detailed"|"technical",
        # "verbosity": 0.0-1.0,
        # "domain_expertise": {"python": 0.8, "kubernetes": 0.3}
    # }
    long_term_goals: list[str]
    interaction_history: dict  # {
        # "total_sessions": 142,
        # "avg_session_length_minutes": 45,
        # "most_used_operations": ["episodic/recall", "semantic/search"]
    # }
    created_at: datetime
    updated_at: datetime

async def get_user_profile(user_id: str) -> UserProfile:
    """Retrieve user profile for context injection."""

async def update_user_preference(user_id: str, key: str, value: Any):
    """Update user preference (communication style, verbosity, etc.)."""

async def infer_user_expertise(user_id: str, domain: str) -> float:
    """Infer user expertise from interaction patterns."""
```

**Integration**:
- Hook into working memory injection (`~/.claude/hooks/lib/session_context_manager.py`)
- Add user profile section to context: `## User Profile (verbosity: concise, expertise: python=0.8)`
- Use profile to filter/rank memories (prefer Python content for Python-expert users)

**Database Schema**:
```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    long_term_goals TEXT[] DEFAULT '{}',
    interaction_history JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_updated ON user_profiles(updated_at DESC);
```

**Acceptance Criteria**:
- User profiles persist across sessions
- Preferences affect memory ranking (verified via A/B test)
- Profile updates automatically from interaction patterns (every 10 sessions)

---

### 4. Automatic Background Consolidation

**Status**: 🔴 Missing
**Effort**: M
**Impact**: High (memory efficiency)

**Problem**: Consolidation currently requires manual invocation (`consolidate()` operation). From CLAUDE.md:
> **Current**: Batch consolidation via `consolidate()` operation.
> **Article's vision**: Continuous background consolidation.

With 8,128 episodic events, memory grows unbounded without automatic compression.

**Proposed Solution**:
```python
# New: src/athena/consolidation/background_scheduler.py
import asyncio
from datetime import datetime, timedelta

class BackgroundConsolidationScheduler:
    """Automatic consolidation scheduler (idle-time triggered)."""

    def __init__(self, db: Database, manager: UnifiedMemoryManager):
        self.db = db
        self.manager = manager
        self.is_running = False
        self.last_run = None

    async def start(self):
        """Start background consolidation loop."""
        self.is_running = True
        while self.is_running:
            # Wait for idle period (no queries for 5 minutes)
            if await self._is_idle(minutes=5):
                await self._run_consolidation()
            await asyncio.sleep(60)  # Check every minute

    async def _is_idle(self, minutes: int) -> bool:
        """Check if system has been idle for N minutes."""
        async with self.db.get_connection() as conn:
            result = await conn.execute("""
                SELECT MAX(timestamp) as last_activity
                FROM episodic_events
                WHERE timestamp > NOW() - INTERVAL '10 minutes'
            """)
            last_activity = result.fetchone()["last_activity"]
            if last_activity is None:
                return True
            return (datetime.now() - last_activity) > timedelta(minutes=minutes)

    async def _run_consolidation(self):
        """Run consolidation if threshold met."""
        # Consolidate if:
        # 1. >1000 unconsolidated events OR
        # 2. >24 hours since last consolidation

        stats = await self.manager.get_statistics()
        unconsolidated = stats["episodic"]["total"] - stats["procedural"]["total"] * 80  # ~80 events/procedure

        if unconsolidated > 1000 or (self.last_run and (datetime.now() - self.last_run) > timedelta(hours=24)):
            logger.info("Starting background consolidation...")
            result = await self.manager.consolidate(
                strategy="balanced",
                max_patterns=50,
            )
            self.last_run = datetime.now()
            logger.info(f"Consolidation complete: {result['patterns_extracted']} patterns extracted")
```

**Integration**:
- Start scheduler in MCP server: `src/athena/mcp/handlers.py:__init__`
- Add environment variable: `ATHENA_AUTO_CONSOLIDATE=true`
- Add CLI command: `athena consolidate --daemon`

**Configuration** (`src/athena/core/config.py`):
```python
# Background consolidation
AUTO_CONSOLIDATE_ENABLED = os.environ.get("ATHENA_AUTO_CONSOLIDATE", "false").lower() == "true"
AUTO_CONSOLIDATE_IDLE_MINUTES = int(os.environ.get("ATHENA_AUTO_CONSOLIDATE_IDLE", "5"))
AUTO_CONSOLIDATE_THRESHOLD = int(os.environ.get("ATHENA_AUTO_CONSOLIDATE_THRESHOLD", "1000"))
```

**Acceptance Criteria**:
- Consolidation runs automatically when idle
- No performance impact during active queries
- Consolidation reducesStorage by >90% (8,128 events → <1,000 patterns)
- Can be disabled via config

---

### 5. Direct Graph Query API

**Status**: 🟡 Partial (Graph Store Exists)
**Effort**: M
**Impact**: High (developer experience)

**Problem**: Knowledge graph exists (`src/athena/graph/store.py`) but not exposed directly for multi-hop queries. From "RAG is Dead" analysis:
> **Recommendation**: Expose graph queries - Make multi-hop traversal more accessible to end users

**Current State**:
```python
# src/athena/graph/operations.py:find_related
async def find_related(
    entity_id: int,
    relation_type: str | None = None,
    max_depth: int = 1,
) -> list[dict]:
    """Find related entities."""
```

Max depth = 1 means **no multi-hop traversal**.

**Proposed Enhancement**:
```python
# Enhanced: src/athena/graph/operations.py
async def traverse_graph(
    start_entity: str | int,  # Name or ID
    query: str,  # Natural language: "Find all people related to this project through dependencies"
    max_hops: int = 3,
    filters: dict | None = None,  # {"relation_type": "depends_on", "min_confidence": 0.7}
) -> dict:
    """Multi-hop graph traversal with natural language query.

    Returns:
        {
            "path": ["Entity A", "Entity B", "Entity C"],
            "relations": [
                {"from": "A", "to": "B", "type": "depends_on", "confidence": 0.9},
                {"from": "B", "to": "C", "type": "implements", "confidence": 0.8}
            ],
            "explanation": "Entity A depends on B, which implements C"
        }
    """

async def find_shortest_path(
    from_entity: str,
    to_entity: str,
    relation_types: list[str] | None = None,
) -> list[dict]:
    """Find shortest path between two entities (Dijkstra)."""

async def get_subgraph(
    entity_id: int,
    radius: int = 2,
    include_observations: bool = True,
) -> dict:
    """Get subgraph around entity (all nodes within N hops)."""
```

**Example Usage**:
```python
# Find how "authentication" relates to "user login"
path = await traverse_graph(
    start_entity="authentication",
    query="How does this relate to user login?",
    max_hops=3
)

# Returns:
# {
#     "path": ["Authentication", "OAuth", "User Session", "User Login"],
#     "relations": [
#         {"from": "Authentication", "to": "OAuth", "type": "implements"},
#         {"from": "OAuth", "to": "User Session", "type": "creates"},
#         {"from": "User Session", "to": "User Login", "type": "enables"}
#     ],
#     "explanation": "Authentication implements OAuth, which creates user sessions that enable user login"
# }
```

**TypeScript Stub** (`src/servers/athena/graph.ts`):
```typescript
export async function traverseGraph(
  startEntity: string,
  query: string,
  maxHops?: number,
  filters?: Record<string, any>
): Promise<{
  path: string[];
  relations: Array<{from: string; to: string; type: string; confidence: number}>;
  explanation: string;
}>;

// @implementation src/athena/graph/operations.py:traverse_graph
```

**Acceptance Criteria**:
- Multi-hop traversal (3+ hops) works correctly
- Natural language query routing (use LLM to interpret)
- Performance: <100ms for 3-hop queries on local graph
- Graph visualization support (return JSON for D3.js/Cytoscape)

---

### 6. Memory Compression & Archival

**Status**: 🔴 Missing
**Effort**: L
**Impact**: High (long-term scalability)

**Problem**: Current design keeps all memories in `episodic_events` table indefinitely. At scale (100K+ events), this impacts:
- Query performance (sequential scans)
- Storage costs (GB+ of data)
- Consolidation efficiency (processing old, irrelevant events)

**Proposed Solution**:
```python
# New: src/athena/archival/compressor.py
class MemoryCompressor:
    """Archive and compress old memories."""

    async def archive_old_events(
        self,
        project_id: int,
        age_days: int = 90,
        compression: str = "consolidation",  # "consolidation"|"summarization"|"deletion"
    ) -> dict:
        """Archive events older than N days.

        Strategies:
        - consolidation: Extract patterns, mark events as consolidated
        - summarization: Create high-level summaries, mark originals as archived
        - deletion: Permanently delete low-importance events
        """

        # 1. Find old events
        old_events = await self._find_old_events(project_id, age_days)

        # 2. Apply compression strategy
        if compression == "consolidation":
            patterns = await self._extract_patterns(old_events)
            await self._mark_as_consolidated(old_events)
            return {"archived": len(old_events), "patterns": len(patterns)}

        elif compression == "summarization":
            summary = await self._generate_summary(old_events)
            await self._store_summary(project_id, summary, old_events)
            await self._mark_as_archived(old_events)
            return {"archived": len(old_events), "summary_id": summary["id"]}

        elif compression == "deletion":
            # Only delete low-importance events
            deletable = [e for e in old_events if e["importance_score"] < 0.3]
            await self._delete_events([e["id"] for e in deletable])
            return {"deleted": len(deletable), "kept": len(old_events) - len(deletable)}

    async def restore_archived(self, archive_id: int) -> list[dict]:
        """Restore archived memories (if summarized, not if deleted)."""
```

**Database Schema**:
```sql
-- Archive table (stores compressed representations)
CREATE TABLE memory_archives (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    archive_type TEXT NOT NULL,  -- 'consolidation', 'summarization', 'deletion'
    summary TEXT,  -- For summarization type
    event_ids INTEGER[] NOT NULL,  -- Original event IDs
    patterns_extracted INTEGER DEFAULT 0,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_archives_project ON memory_archives(project_id);
CREATE INDEX idx_archives_type ON memory_archives(archive_type);

-- Update episodic_events with archival status
ALTER TABLE episodic_events ADD COLUMN archive_status TEXT DEFAULT 'active';
-- Values: 'active', 'consolidated', 'archived', 'deleted'
CREATE INDEX idx_episodic_archive_status ON episodic_events(archive_status);
```

**Configuration**:
```python
# src/athena/core/config.py
ARCHIVE_ENABLED = os.environ.get("ATHENA_ARCHIVE_ENABLED", "true").lower() == "true"
ARCHIVE_AGE_DAYS = int(os.environ.get("ATHENA_ARCHIVE_AGE_DAYS", "90"))
ARCHIVE_STRATEGY = os.environ.get("ATHENA_ARCHIVE_STRATEGY", "consolidation")
```

**Acceptance Criteria**:
- Archive process reduces table size by >80%
- Archived memories can be restored (if summarized)
- No loss of critical information (importance_score > 0.7 never deleted)
- Query performance improves after archival (verified via benchmarks)

---

### 7. Confidence Tracking & Uncertainty Quantification

**Status**: 🟡 Partial (Fields Exist)
**Effort**: M
**Impact**: High (trust calibration)

**Problem**: Confidence scores exist (`src/athena/episodic/models.py:102`) but aren't actively used for:
- Filtering low-confidence memories from retrieval
- Triggering re-validation when uncertainty is high
- Surfacing confidence to the user

**Current State**:
```python
# src/athena/episodic/models.py:102
class EpisodicEvent(BaseModel):
    confidence: float = 1.0  # Always defaults to 1.0
```

**Enhancement**:
```python
# src/athena/meta/confidence.py
class ConfidenceTracker:
    """Track and update memory confidence scores."""

    async def compute_confidence(self, event: EpisodicEvent) -> float:
        """Compute confidence based on evidence quality, source, validation.

        Factors:
        - Evidence type: OBSERVED (1.0), INFERRED (0.7), HYPOTHETICAL (0.3)
        - Source reliability: User (1.0), LLM (0.8), Heuristic (0.6)
        - Validation: Validated by user (1.0), No validation (0.5)
        - Age: Recent (1.0), >30 days (0.8), >90 days (0.6)
        """
        base_confidence = self._evidence_type_confidence(event.evidence_type)
        source_multiplier = self._source_reliability(event.source_id)
        age_decay = self._age_decay(event.timestamp)
        validation_boost = 1.0 if event.metadata.get("validated") else 0.8

        return min(1.0, base_confidence * source_multiplier * age_decay * validation_boost)

    async def flag_uncertain_memories(self, project_id: int, threshold: float = 0.5):
        """Flag memories with confidence < threshold for review."""
        # SELECT * FROM episodic_events WHERE confidence < threshold
        # AND lifecycle_status = 'active'

    async def request_validation(self, event_id: int) -> dict:
        """Request user validation for uncertain memory.

        Returns validation prompt for user:
        {
            "event_id": 123,
            "content": "User said Python is statically typed",
            "confidence": 0.3,
            "reason": "Conflicts with known fact (Python is dynamically typed)",
            "prompt": "Is this memory accurate? [Yes/No/Unsure]"
        }
        """
```

**Integration**:
- Display confidence in memory retrieval: `recall(query, min_confidence=0.7)`
- Working memory injection: Only inject memories with confidence > 0.6
- Consolidation: Re-validate low-confidence patterns before extraction

**Acceptance Criteria**:
- Confidence scores computed automatically for all new events
- Low-confidence memories (<0.5) flagged for review
- User can validate/reject memories via CLI/API
- Retrieval quality improves (measured via user feedback)

---

## P2: Enhancements

### 8. Query Performance Optimization

**Status**: 🟡 Acceptable (needs benchmarking)
**Effort**: M
**Impact**: Medium (user experience)

**Problem**: No comprehensive benchmarks exist for query performance. Need to establish baselines and optimize bottlenecks.

**Proposed Benchmark Suite**:
```python
# New: benchmarks/benchmark_query_performance.py
import asyncio
import time
from athena.manager import UnifiedMemoryManager

async def benchmark_recall(manager, n_queries=100):
    """Benchmark episodic recall performance."""
    queries = ["authentication", "user login", "database error", ...]

    start = time.time()
    for query in queries:
        results = await manager.recall(query, limit=5)
    elapsed = time.time() - start

    return {
        "total_queries": n_queries,
        "total_time_ms": elapsed * 1000,
        "avg_latency_ms": (elapsed / n_queries) * 1000,
        "queries_per_second": n_queries / elapsed
    }

# Benchmarks to implement:
# 1. Episodic recall (vector search)
# 2. Semantic search (hybrid BM25 + vector)
# 3. Graph traversal (multi-hop)
# 4. Consolidation (pattern extraction)
# 5. Working memory ranking (importance scoring)
```

**Optimization Targets**:
| Operation | Current (est.) | Target | Strategy |
|-----------|----------------|--------|----------|
| Episodic recall | ~50ms | <20ms | Add HNSW index to pgvector |
| Semantic search | ~80ms | <30ms | Cache frequent queries |
| Graph traversal (3-hop) | ~200ms | <100ms | Adjacency list pre-computation |
| Consolidation | ~5s | <2s | Parallel clustering |

**Specific Optimizations**:

1. **Add HNSW index** (`src/athena/episodic/store.py:_init_schema`):
```sql
-- Replace IVFlat with HNSW for faster vector search
CREATE INDEX episodic_embedding_hnsw ON episodic_events
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

2. **Query result caching** (`src/athena/rag/manager.py`):
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def cached_recall(query: str, k: int) -> list[MemorySearchResult]:
    """Cache frequent queries (cache invalidated on new writes)."""
```

3. **Graph adjacency pre-computation** (`src/athena/graph/store.py`):
```sql
-- Materialized view for fast graph traversal
CREATE MATERIALIZED VIEW entity_adjacency AS
SELECT
    from_entity_id,
    to_entity_id,
    relation_type,
    strength
FROM entity_relations
WHERE valid_until IS NULL OR valid_until > NOW();

CREATE INDEX idx_adjacency_from ON entity_adjacency(from_entity_id);
CREATE INDEX idx_adjacency_to ON entity_adjacency(to_entity_id);
```

**Acceptance Criteria**:
- All operations meet target latency (p95)
- Benchmark suite runs in CI/CD pipeline
- Performance regression alerts configured

---

### 9. Multi-Tenant Support (Project Isolation)

**Status**: 🟢 Exists (Needs Enhancement)
**Effort**: S
**Impact**: Medium (deployment flexibility)

**Problem**: Current design uses `project_id` for isolation, but lacks:
- Per-project resource limits (storage, query rate)
- Cross-project memory sharing (reusable patterns)
- Project archival/deletion

**Enhancements**:
```python
# src/athena/projects/manager.py
class ProjectManager:
    """Manage project isolation and resource limits."""

    async def create_project(
        self,
        name: str,
        owner_id: str,
        limits: dict | None = None,
    ) -> int:
        """Create project with resource limits.

        Limits:
        - max_events: 100000
        - max_patterns: 10000
        - max_storage_mb: 1000
        - query_rate_limit: 100/minute
        """

    async def get_project_usage(self, project_id: int) -> dict:
        """Get current resource usage vs limits."""

    async def share_pattern_across_projects(
        self,
        pattern_id: int,
        from_project: int,
        to_project: int,
    ):
        """Share reusable pattern across projects."""

    async def archive_project(self, project_id: int):
        """Archive all project data (mark as read-only)."""

    async def delete_project(self, project_id: int, confirm: bool = False):
        """Permanently delete project and all data."""
```

**Database Schema**:
```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'archived', 'deleted'
    limits JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    archived_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE project_usage (
    project_id INTEGER PRIMARY KEY REFERENCES projects(id),
    event_count INTEGER DEFAULT 0,
    pattern_count INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    last_query_at TIMESTAMP WITH TIME ZONE,
    query_count_last_hour INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Acceptance Criteria**:
- Resource limits enforced (reject writes when exceeded)
- Project usage tracked in real-time
- Cross-project pattern sharing works
- Project deletion cascades correctly

---

### 10. Natural Language Query Interface

**Status**: 🔴 Missing
**Effort**: M
**Impact**: Medium (user experience)

**Problem**: Current API requires structured calls:
```python
await recall("authentication", limit=5)
await find_related(entity_id=123, relation_type="depends_on")
```

Users want natural language: "Show me what I learned about authentication last week"

**Proposed Solution**:
```python
# New: src/athena/nlp/query_parser.py
class NaturalLanguageQueryParser:
    """Parse natural language queries into structured API calls."""

    async def parse(self, query: str) -> dict:
        """Parse natural language query.

        Examples:
        - "Show me what I learned about authentication last week"
          → {
              "operation": "episodic/recall",
              "params": {"query": "authentication", "time_range": "last_week"}
            }

        - "How does user login relate to OAuth?"
          → {
              "operation": "graph/traverse",
              "params": {"start": "user login", "target": "OAuth"}
            }

        - "What patterns did I extract from yesterday's work?"
          → {
              "operation": "procedural/list",
              "params": {"time_range": "yesterday"}
            }
        """

        # Use LLM to parse query
        parsed = await self.llm.generate(f"""
        Parse this natural language memory query into structured parameters:

        Query: {query}

        Available operations:
        - episodic/recall: Search events (params: query, limit, time_range)
        - semantic/search: Search knowledge (params: query, topics, limit)
        - graph/traverse: Traverse relationships (params: start, target, max_hops)
        - procedural/list: List procedures (params: time_range, tags)

        Return JSON: {{"operation": "...", "params": {{...}}}}
        """)

        return json.loads(parsed)
```

**CLI Integration**:
```bash
# Natural language CLI
$ athena ask "What did I learn about Python async/await?"
$ athena ask "Show me my goals for this week"
$ athena ask "How does authentication relate to user sessions?"
```

**Acceptance Criteria**:
- 90%+ accuracy on common query patterns
- Graceful fallback to keyword search if parsing fails
- Support for temporal queries (yesterday, last week, etc.)
- Support for relational queries (how X relates to Y)

---

### 11. Memory Visualization Dashboard

**Status**: 🔴 Missing
**Effort**: L
**Impact**: Medium (debugging, insights)

**Problem**: No visual interface to explore memory state. Users need:
- Timeline view of episodic events
- Graph visualization of knowledge graph
- Consolidation metrics dashboard
- Working memory inspection

**Proposed Solution**:
```python
# New: src/athena/web/dashboard.py (FastAPI + React)
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()

@app.get("/api/timeline")
async def get_timeline(project_id: int, days: int = 7):
    """Get episodic timeline for visualization."""
    # Returns: [{"timestamp": ..., "event_type": ..., "content": ...}, ...]

@app.get("/api/graph")
async def get_graph(project_id: int, entity_id: int | None = None):
    """Get knowledge graph for visualization."""
    # Returns: {"nodes": [...], "edges": [...]}

@app.get("/api/consolidation-metrics")
async def get_consolidation_metrics(project_id: int):
    """Get consolidation statistics."""
    # Returns: {"patterns_extracted": 101, "events_consolidated": 8128, ...}

@app.websocket("/ws/working-memory")
async def working_memory_stream(websocket: WebSocket):
    """Stream working memory updates in real-time."""
```

**Frontend Components** (React + D3.js):
1. Timeline view (episodic events over time)
2. Graph view (interactive knowledge graph with zoom/pan)
3. Metrics dashboard (consolidation stats, query performance)
4. Working memory inspector (live view of top-7 items)

**Acceptance Criteria**:
- Dashboard accessible at `http://localhost:8080`
- Graph rendering <2s for 1000+ nodes
- Real-time updates via WebSocket
- Mobile-responsive design

---

## P3: Future Exploration

### 12. Federated Memory Sync (Multi-Machine)

**Status**: 🔴 Research
**Effort**: XL
**Impact**: Low (niche use case)

**Problem**: Athena is single-machine by design (CLAUDE.md:76-91). For users with multiple machines (laptop + desktop), memories don't sync.

**Constraints**:
- Must preserve single-machine simplicity
- No cloud dependency (local-first)
- Conflict resolution required

**Proposed Approach**:
```python
# Federated sync via Git-like model
# 1. Each machine has local Athena instance
# 2. Sync via encrypted file export/import
# 3. Conflict resolution using vector clocks

class FederatedSync:
    async def export_snapshot(self, output_path: str):
        """Export encrypted snapshot of all memories."""

    async def import_snapshot(self, snapshot_path: str):
        """Import snapshot, merge with local state."""

    async def resolve_conflicts(self, conflicts: list[dict]):
        """Resolve conflicts using timestamps + vector clocks."""
```

**Status**: Deferred to v2.0 (adds significant complexity)

---

### 13. Multimodal Memory (Images, Audio)

**Status**: 🔴 Research
**Effort**: XL
**Impact**: Medium (niche use case)

**Problem**: Current design stores only text. Users may want:
- Screenshots of UI bugs
- Audio notes
- Code diagrams

**Technical Challenges**:
- Storage: Binary blobs vs external storage (S3, local filesystem)
- Embeddings: CLIP for images, Whisper for audio
- Retrieval: Cross-modal search (text query → image results)

**Status**: Deferred pending CLIP/Whisper integration

---

### 14. Memory Provenance Tracking

**Status**: 🟡 Partial (Evidence Type Exists)
**Effort**: M
**Impact**: Medium (trust, auditability)

**Problem**: Users want to know "Where did this memory come from?" for trust calibration.

**Current State**:
```python
# src/athena/episodic/models.py:104-109
class EpisodicEvent(BaseModel):
    evidence_type: EvidenceType = EvidenceType.OBSERVED
    source_id: Optional[str] = None
    evidence_quality: float = 1.0
```

**Enhancement**:
```python
# Add full provenance chain
class MemoryProvenance(BaseModel):
    memory_id: int
    source_chain: list[dict]  # [
        # {"source": "user_input", "timestamp": ...},
        # {"source": "llm_inference", "model": "claude-3", "confidence": 0.8},
        # {"source": "consolidation", "pattern_id": 42}
    # ]
    validation_history: list[dict]  # [
        # {"validated_by": "user", "timestamp": ..., "result": "confirmed"}
    # ]
```

**Use Cases**:
- "This fact came from an LLM (80% confidence), not direct observation"
- "This pattern was extracted from 47 events across 3 sessions"
- "This memory was validated by the user on 2025-11-20"

**Status**: Deferred to P2 (requires UI for visualization)

---

### 15. LLM-Free Mode (Pure Statistical)

**Status**: 🔴 Research
**Effort**: M
**Impact**: Low (privacy-focused users)

**Problem**: Some users want zero LLM dependency for privacy/cost.

**Proposed Approach**:
```python
# Disable all LLM features
export LLM_PROVIDER=none

# Fallbacks:
# - Consolidation: Statistical clustering only (no LLM validation)
# - Query parsing: Keyword-based only
# - Embeddings: TF-IDF instead of neural embeddings
```

**Status**: Deferred (most users want LLM features)

---

## Implementation Guidelines

### Development Workflow

1. **Create feature branch**: `git checkout -b feature/background-consolidation`
2. **Write tests first**: `tests/unit/test_background_consolidation.py`
3. **Implement feature**: `src/athena/consolidation/background_scheduler.py`
4. **Update documentation**: `CLAUDE.md`, operation stubs, docstrings
5. **Run test suite**: `pytest tests/ -v --timeout=300`
6. **Code quality**: `black src/ tests/ && ruff check --fix src/ tests/`
7. **Create PR**: Link to this improvement doc item

### Testing Requirements

- **Unit tests**: >90% coverage for new code
- **Integration tests**: Test end-to-end workflows
- **Performance tests**: Benchmark critical paths
- **Regression tests**: Ensure no impact on existing features

### Documentation Standards

- **Docstrings**: Google-style for all public functions
- **CLAUDE.md**: Update layer descriptions if architecture changes
- **API_REFERENCE.md**: Update if new operations added
- **Type hints**: All functions must have full type annotations

### Code Review Checklist

- [ ] Tests pass (all 8,705+ tests)
- [ ] No performance regression (run benchmarks)
- [ ] Documentation updated
- [ ] Type hints added
- [ ] No SQL injection vulnerabilities (parameterized queries only)
- [ ] Async/await used correctly (no blocking operations)
- [ ] Graceful error handling (no silent failures)

---

## Metrics & Success Criteria

### System Health Metrics

Track these metrics to measure improvement impact:

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Test coverage | 85% | >90% | P0 |
| Query latency (p95) | ~50ms | <20ms | P1 |
| Memory footprint | 8,128 events | <1,000 patterns | P1 |
| Consolidation ratio | 80:1 | 100:1 | P2 |
| User satisfaction | N/A | >4.5/5 | P1 |

### Performance Benchmarks

Run benchmarks before/after each improvement:

```bash
# Benchmark suite
pytest benchmarks/ -v --benchmark-only

# Expected output:
# - episodic_recall: 18ms (p95)
# - semantic_search: 25ms (p95)
# - graph_traversal_3hop: 85ms (p95)
# - consolidation_1000_events: 1.8s
```

### User Feedback Loop

Collect feedback via:
1. GitHub issues (feature requests, bug reports)
2. User surveys (quarterly)
3. Usage analytics (query patterns, feature adoption)
4. Performance monitoring (latency, error rates)

---

## Prioritization Matrix

Use this matrix to prioritize additional improvements:

```
High Impact + Low Effort = Do First (Quick Wins)
High Impact + High Effort = Plan Carefully (Strategic Bets)
Low Impact + Low Effort = Do Later (Maintenance)
Low Impact + High Effort = Avoid (Distractions)
```

Current roadmap focuses on **High Impact** items (P0, P1) regardless of effort, then adds **Quick Wins** from P2.

---

## Questions & Decisions

### Open Questions

1. **Background consolidation trigger**: Idle time vs fixed schedule vs event count threshold?
   - **Recommendation**: Hybrid (idle time OR event count >1000)

2. **User profiling storage**: PostgreSQL JSONB vs separate service?
   - **Recommendation**: PostgreSQL JSONB (simpler, fewer dependencies)

3. **Graph visualization library**: D3.js vs Cytoscape.js vs vis.js?
   - **Recommendation**: Cytoscape.js (better performance for large graphs)

4. **Memory archival default**: Consolidation vs summarization vs off?
   - **Recommendation**: Consolidation (preserves patterns, reduces storage)

### Decisions Made

1. ✅ **No distributed system**: Athena stays single-machine (CLAUDE.md design principle)
2. ✅ **PostgreSQL-only**: No SQLite/Qdrant (simplifies maintenance)
3. ✅ **Async-first**: All new code must use async/await
4. ✅ **LLM-optional**: Core features work without LLM (graceful degradation)

---

## Version History

- **v1.0** (2025-11-21): Initial improvements roadmap
- **v1.1** (TBD): Add benchmarks and metrics
- **v1.2** (TBD): Update based on user feedback

---

**Contributors**: Add your name when implementing improvements!

**Feedback**: Open a GitHub issue or comment on this doc.

---

*Last Updated: 2025-11-21 | Document Status: Active | Next Review: 2025-12-21*
