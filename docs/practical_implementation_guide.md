# Practical Implementation Guide: Building Production-Ready Memory Systems

**Generated**: 2025-11-18
**Purpose**: Technical implementation guidance for multi-layered memory architectures based on real-world production systems and recent research (2024-2025)

---

## Executive Summary

This guide compiles practical implementation strategies from production AI agent systems, cognitive architecture deployments, and recent research on memory-augmented LLMs. It focuses on **engineering decisions**, **performance optimization**, and **real-world deployment patterns** for systems like Athena.

**Key Topics Covered**:
1. Episodic memory storage and retrieval patterns
2. Vector database and hybrid search implementation
3. Async database connection pooling and performance
4. Knowledge graph deployment strategies
5. Memory consolidation background processing
6. Working memory buffers and attention mechanisms
7. Production RAG system best practices
8. Context window management strategies
9. Hook-based agent lifecycle architecture
10. Procedural memory extraction workflows

---

## 1. Episodic Memory: Practical Engineering (Layer 1)

### Current State of the Field (2024-2025)

**Research Consensus**: "Many recent AI systems take inspiration from biological episodic memory, implementing key features that provide behavioral advantages in strategic decision-making, fast learning, navigation, exploration and acting over temporal distance."

**Production Pattern**: "Episodic memory captures specific events and interactions with metadata like timestamps, while semantic memory remembers general knowledge through retrieval-augmented generation (RAG) with vector embeddings."

### Implementation Approaches

#### Storage Architecture

**Recommended**: Durable stores for episodic traces
- **SQL/NoSQL** for structured episodic events (Athena ✅ uses PostgreSQL)
- **Vector databases** for semantic retrieval (optional enhancement)
- **Hybrid approach**: Relational for metadata + vector for content search

**Example Schema** (MongoDB + LangGraph pattern):
```python
{
  "event_id": "evt_12345",
  "timestamp": "2025-11-18T10:30:00Z",
  "content": "User asked about consciousness research",
  "context": {
    "session_id": "sess_abc",
    "project_id": "proj_athena",
    "tags": ["research", "consciousness"]
  },
  "importance": 0.85,
  "embedding": [0.123, 0.456, ...],  // Optional for hybrid retrieval
  "metadata": {
    "source": "user_input",
    "duration_ms": 1234
  }
}
```

#### Retrieval Patterns

**1. Temporal Retrieval** (most common)
```python
# Recent events
SELECT * FROM episodic_events
WHERE session_id = ?
ORDER BY timestamp DESC
LIMIT 10;

# Time range queries
SELECT * FROM episodic_events
WHERE timestamp BETWEEN ? AND ?
AND importance > 0.7;
```

**2. Semantic Retrieval** (if embeddings available)
```python
# Feature Association Matrix (FAM) approach from 2024 research
# Encode query → Find nearest neighbors → Return events
query_embedding = encode("consciousness research")
similar_events = vector_db.search(query_embedding, k=10)
```

**3. Hybrid Temporal-Semantic** (recommended)
```python
# Combine recency with relevance
SELECT e.*,
       (importance * 0.5) +
       (1.0 / (1.0 + EXTRACT(EPOCH FROM NOW() - timestamp)/86400) * 0.3) +
       (vector_similarity(embedding, ?) * 0.2) as score
FROM episodic_events e
WHERE session_id = ?
ORDER BY score DESC
LIMIT 7;
```

### Athena-Specific Recommendations

✅ **Current Strengths**:
- PostgreSQL with async connection pooling
- Temporal indexing on timestamp
- Session-based organization
- Importance scoring

🔄 **Potential Enhancements**:
1. **Add embeddings column** for semantic retrieval (optional)
2. **Implement event clustering** for pattern detection
3. **Add decay function** for importance over time
4. **Create composite indexes** on (session_id, timestamp, importance)

**Performance Target** (from research):
- Retrieval latency: <100ms for top-10 events
- Storage overhead: ~1-5KB per event (without embeddings)
- With embeddings: +1-4KB per event (384-1536 dimensions)

---

## 2. Semantic Memory: Vector Search + Hybrid Retrieval (Layer 2)

### Production-Proven Hybrid Search Architecture

**Research Finding**: "Hybrid search merges dense and sparse vectors together to deliver the best of both search methods. Dense vectors excel at understanding context, whereas sparse vectors excel at keyword matches."

### Implementation: BM25 + Vector Embeddings

#### Architecture Components

```
Query Input
    ↓
┌───┴───┐
│       │
BM25    Vector Search
(Sparse) (Dense)
│       │
└───┬───┘
    ↓
Fusion Algorithm
(RRF or Weighted)
    ↓
Final Results
```

#### Step-by-Step Implementation

**1. Indexing Phase**

```python
# BM25 Index (via Elasticsearch/OpenSearch or custom)
from rank_bm25 import BM25Okapi

corpus = [fact['content'] for fact in semantic_facts]
tokenized_corpus = [doc.lower().split() for doc in corpus]
bm25 = BM25Okapi(tokenized_corpus)

# Vector Index (FAISS/pgvector/Pinecone)
import faiss
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, 384-dim
embeddings = model.encode(corpus)
index = faiss.IndexFlatIP(384)  # Inner product for normalized vectors
faiss.normalize_L2(embeddings)
index.add(embeddings)
```

**2. Query Phase**

```python
async def hybrid_search(query: str, k: int = 10, alpha: float = 0.6):
    """
    Alpha: weight for BM25 (1-alpha for vector search)
    Higher alpha = more keyword-focused
    Lower alpha = more semantic-focused
    """

    # BM25 retrieval
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)

    # Vector retrieval
    query_embedding = model.encode([query])
    faiss.normalize_L2(query_embedding)
    vector_scores, indices = index.search(query_embedding, k)

    # Reciprocal Rank Fusion (RRF)
    combined_scores = {}
    for rank, (doc_id, score) in enumerate(sorted_bm25_results):
        combined_scores[doc_id] = combined_scores.get(doc_id, 0) + alpha / (rank + 60)

    for rank, (doc_id, score) in enumerate(vector_results):
        combined_scores[doc_id] = combined_scores.get(doc_id, 0) + (1-alpha) / (rank + 60)

    # Return top-k by combined score
    return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:k]
```

**3. Fusion Algorithms**

| Algorithm | Formula | Best For |
|-----------|---------|----------|
| **RRF** (Reciprocal Rank Fusion) | `1/(rank + k)` | Balanced, robust to outliers |
| **Weighted Sum** | `alpha*bm25 + (1-alpha)*vector` | Fine-tuned control |
| **Relative Score** | Normalize scores to [0,1] first | Different score ranges |

**Research Recommendation**: "RRF is the default fusion algorithm in Weaviate and is recommended for most use cases."

### Embedding Model Selection

#### Performance Comparison (2024 Research)

| Model | Dimensions | Speed | Use Case |
|-------|-----------|-------|----------|
| **all-MiniLM-L6-v2** | 384 | ⚡⚡⚡ Fast | Production default (Sentence-Transformers) |
| **all-mpnet-base-v2** | 768 | ⚡⚡ Medium | Better accuracy, moderate speed |
| **nomic-embed-text-v2** | 768 | ⚡⚡ Medium | Ollama integration |
| **OpenAI text-embedding-3-small** | 1536 | ⚡ Slow (API) | Highest accuracy, cloud dependency |

**Key Finding**: "Open-source models running on CPU (via sentence-transformers) were the fastest options tested, outperforming cloud-based embedding APIs in latency tests."

**Ollama vs. Sentence-Transformers**: "Ollama's embed API is approximately 2x slower than Sentence Transformers when using the same model."

#### Athena Recommendation

```python
# config.py enhancement
EMBEDDING_CONFIG = {
    "provider": "sentence-transformers",  # Fastest local option
    "model": "all-MiniLM-L6-v2",         # 384-dim, ~50ms latency
    "batch_size": 32,                     # Balance speed/memory
    "normalize": True,                    # Enable inner product search
    "device": "cpu"                       # Most deployments
}

# Fallback: Ollama for unified interface (accept 2x latency)
# Production: Sentence-Transformers for speed
```

### pgvector Integration (Athena's PostgreSQL)

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add vector column to semantic_memories
ALTER TABLE semantic_memories
ADD COLUMN embedding vector(384);

-- Create HNSW index for fast approximate search
CREATE INDEX ON semantic_memories
USING hnsw (embedding vector_cosine_ops);

-- Hybrid query combining full-text + vector
SELECT
    m.*,
    ts_rank(to_tsvector('english', content), query) as bm25_score,
    1 - (embedding <=> $1) as vector_score,
    (0.6 * ts_rank(...) + 0.4 * (1 - (embedding <=> $1))) as combined_score
FROM semantic_memories m, plainto_tsquery('english', $2) query
WHERE to_tsvector('english', content) @@ query
ORDER BY combined_score DESC
LIMIT 10;
```

**Performance Tuning**:
- HNSW index: Fast but approximate (~95% recall)
- IVFFlat index: Faster indexing, slower queries
- Exact search: `ORDER BY embedding <=> $1` (small datasets only)

---

## 3. PostgreSQL Async Performance Optimization

### Connection Pooling with asyncpg

**Research Finding**: "Using a connection pool runs 6.7 times faster than creating individual connections for repeated queries."

#### Optimal Pool Configuration

```python
import asyncpg
from typing import Optional

class AsyncDatabase:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """
        Tuned for server-type applications with frequent short requests
        """
        self.pool = await asyncpg.create_pool(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,

            # Pool sizing (tune based on workload)
            min_size=2,              # Keep connections warm
            max_size=10,             # Limit max concurrent connections

            # Timeout settings
            command_timeout=60,      # Query timeout (seconds)
            timeout=30,              # Connection acquisition timeout

            # Performance optimizations
            server_settings={
                'jit': 'off',        # Disable JIT for small queries
                'application_name': 'athena_memory'
            }
        )

    async def execute(self, query: str, *args):
        """Execute with prepared statement caching"""
        async with self.pool.acquire() as conn:
            # asyncpg automatically caches prepared statements
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch with connection from pool"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def close(self):
        """Clean shutdown"""
        if self.pool:
            await self.pool.close()
```

#### Prepared Statements Optimization

**Research**: "Prepared statements are a PostgreSQL feature that can be used to optimize the performance of queries that are executed more than once, allowing the server to reuse parsing, analysis and compilation work."

**asyncpg handles this automatically**, but you can control it:

```python
# Automatic (recommended)
await conn.execute("SELECT * FROM memories WHERE id = $1", memory_id)

# Manual control (advanced)
stmt = await conn.prepare("SELECT * FROM memories WHERE importance > $1")
results = await stmt.fetch(0.7)
```

#### Performance Monitoring

```python
class MonitoredPool:
    async def get_pool_stats(self):
        """Monitor pool health"""
        return {
            "size": self.pool.get_size(),
            "free": self.pool.get_idle_size(),
            "max": self.pool.get_max_size(),
            "min": self.pool.get_min_size()
        }
```

### Athena Current Implementation Analysis

✅ **Strengths**:
- Uses asyncpg with connection pooling
- Async-first architecture throughout
- Parameterized queries (SQL injection safe)

🔄 **Optimization Opportunities**:

1. **Add pool monitoring**
```python
# In manager.py
async def get_system_stats(self):
    stats = await self.db.get_pool_stats()
    logger.info(f"DB Pool: {stats['free']}/{stats['size']} connections free")
```

2. **Tune pool size based on workload**
```python
# For CLI/hooks: Low concurrency
min_size=1, max_size=3

# For MCP server: Medium concurrency
min_size=2, max_size=10  # Current (good)

# For web API: High concurrency
min_size=5, max_size=20
```

3. **Add query timeout protection**
```python
# Prevent runaway queries
async with asyncio.timeout(5.0):  # 5 second timeout
    results = await self.db.fetch(complex_query)
```

---

## 4. Knowledge Graph Implementation (Layer 5)

### Neo4j vs. PostgreSQL: When to Choose

**Research Finding**: "PostgreSQL performs better against Neo4j in many categories, with performance benefits of Neo4j noticed only for large datasets and joins involving more than 5 tables."

#### Decision Matrix

| Factor | PostgreSQL (Current) | Neo4j | Recommendation |
|--------|---------------------|-------|----------------|
| **Graph size** | <100K entities | >100K entities | ✅ Athena: PostgreSQL sufficient |
| **Query depth** | 1-3 hops | 4+ hops | ✅ Current queries: shallow |
| **Setup complexity** | Low | High | ✅ Already have PostgreSQL |
| **Traversal speed** | Good (<5 hops) | Excellent | ✅ Athena use case: simple |
| **Maintenance** | Low | Medium-High | ✅ Single database simpler |

**Athena Verdict**: ✅ **Stick with PostgreSQL** for knowledge graph storage. Migration to Neo4j only justified if:
- Entity count exceeds 100,000
- Queries regularly traverse 5+ relationship hops
- Community detection becomes performance bottleneck

### Optimizing Graph Queries in PostgreSQL

#### Recursive CTE for Relationship Traversal

```sql
-- Find all related entities within 3 hops
WITH RECURSIVE entity_network AS (
    -- Base case: starting entity
    SELECT id, name, 0 as depth
    FROM knowledge_graph_entities
    WHERE id = $1

    UNION ALL

    -- Recursive case: follow relationships
    SELECT e.id, e.name, en.depth + 1
    FROM knowledge_graph_entities e
    JOIN knowledge_graph_relations r ON (
        r.target_id = e.id OR r.source_id = e.id
    )
    JOIN entity_network en ON (
        r.source_id = en.id OR r.target_id = en.id
    )
    WHERE en.depth < 3  -- Limit depth
)
SELECT DISTINCT * FROM entity_network;
```

#### Indexing Strategy

```sql
-- Composite indexes for relationship queries
CREATE INDEX idx_relations_source_target
ON knowledge_graph_relations(source_id, target_id);

CREATE INDEX idx_relations_target_source
ON knowledge_graph_relations(target_id, source_id);

-- Index on entity importance for filtering
CREATE INDEX idx_entities_importance
ON knowledge_graph_entities(importance DESC);

-- Partial index for active entities only
CREATE INDEX idx_active_entities
ON knowledge_graph_entities(name, importance)
WHERE deleted_at IS NULL;
```

#### Community Detection Optimization

```python
# Cache community computation results
class CommunityCache:
    def __init__(self, ttl_seconds=3600):
        self.cache = {}
        self.ttl = ttl_seconds

    async def get_communities(self, force_refresh=False):
        if force_refresh or self._is_expired():
            communities = await self._compute_communities()
            self.cache = {
                "data": communities,
                "timestamp": time.time()
            }
        return self.cache["data"]

    async def _compute_communities(self):
        # Expensive computation - cache results
        entities = await self.db.fetch("SELECT * FROM knowledge_graph_entities")
        relations = await self.db.fetch("SELECT * FROM knowledge_graph_relations")

        # Use networkx for Louvain community detection
        import networkx as nx
        G = nx.Graph()
        G.add_edges_from([(r['source_id'], r['target_id']) for r in relations])
        communities = nx.community.louvain_communities(G)
        return communities
```

---

## 5. Memory Consolidation: Background Processing (Layer 7)

### Biological Inspiration

**Research**: "Replay during sleep is important for consolidation processes... The model implements a functional consolidation process from one-shot learning capability to stable neocortical memory engrams due to its three-stage architecture and wide span of time constants."

### Implementation Patterns

#### Pattern 1: Event-Triggered Consolidation

```python
# Trigger after N new episodes
class ConsolidationTrigger:
    def __init__(self, threshold=100):
        self.event_count = 0
        self.threshold = threshold

    async def on_event_stored(self, event):
        self.event_count += 1
        if self.event_count >= self.threshold:
            await self.trigger_consolidation()
            self.event_count = 0

    async def trigger_consolidation(self):
        logger.info("Triggering consolidation after %d events", self.threshold)
        await consolidate_recent_events()
```

#### Pattern 2: Scheduled Background Consolidation

```python
import asyncio
from datetime import datetime, time as dtime

class ScheduledConsolidation:
    """Run consolidation during 'sleep' periods (e.g., 2 AM daily)"""

    async def start(self):
        """Run consolidation loop"""
        while True:
            await self.wait_until_consolidation_time()
            await self.run_consolidation()

    async def wait_until_consolidation_time(self):
        """Wait until 2 AM"""
        now = datetime.now()
        target = datetime.combine(now.date(), dtime(2, 0))

        if now.time() > dtime(2, 0):
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

    async def run_consolidation(self):
        """Consolidate yesterday's events"""
        logger.info("Starting nightly consolidation")

        # System 1: Fast statistical clustering
        start = time.time()
        clusters = await self.fast_clustering()
        logger.info("System 1 clustering: %.2fs", time.time() - start)

        # System 2: Slow validation (only if uncertain)
        uncertain_clusters = [c for c in clusters if c.confidence < 0.5]
        if uncertain_clusters:
            logger.info("System 2 validation for %d clusters", len(uncertain_clusters))
            validated = await self.llm_validate(uncertain_clusters)

        # Extract patterns and procedures
        await self.extract_patterns(clusters)
        await self.extract_procedures(clusters)

        logger.info("Consolidation complete")
```

#### Pattern 3: Incremental Online Consolidation

```python
class IncrementalConsolidation:
    """Consolidate small batches continuously (like awake replay)"""

    async def process_batch(self, batch_size=10):
        """Process recent events in small batches"""
        while True:
            events = await self.get_unconsolidated_events(limit=batch_size)
            if not events:
                await asyncio.sleep(60)  # Wait for new events
                continue

            # Quick pattern detection (System 1)
            patterns = self.detect_patterns(events)

            # Update semantic memory incrementally
            for pattern in patterns:
                await self.update_semantic_memory(pattern)

            # Mark events as consolidated
            await self.mark_consolidated(events)
```

### Athena Implementation Strategy

**Current**: On-demand consolidation via MCP tools
**Recommended**: Hybrid approach

```python
# src/athena/consolidation/scheduler.py
class ConsolidationScheduler:
    def __init__(self, db: Database):
        self.db = db
        self.incremental_enabled = True
        self.nightly_enabled = True

    async def start(self):
        """Start both consolidation modes"""
        tasks = []

        if self.incremental_enabled:
            tasks.append(self.incremental_loop())

        if self.nightly_enabled:
            tasks.append(self.nightly_loop())

        await asyncio.gather(*tasks)

    async def incremental_loop(self):
        """Every 5 minutes, process small batches"""
        while True:
            await self.consolidate_batch(batch_size=20)
            await asyncio.sleep(300)  # 5 minutes

    async def nightly_loop(self):
        """Deep consolidation at 2 AM"""
        while True:
            await self.wait_until(hour=2)
            await self.full_consolidation()
```

**Performance Targets**:
- Incremental: Process 20 events in <1 second
- Nightly: Process full day (1000+ events) in <60 seconds

---

## 6. Working Memory Implementation (Hooks + Attention)

### Research-Backed Architecture

**Finding**: "The Working Memory Hub acts as a temporary storage and manipulation space similar to human working memory... Advanced AI systems implement multi-layered memory hierarchies where working memory is like papers on your desk (immediately accessible but limited in space)."

### Attention Mechanism for Memory Selection

#### Relevance Scoring

```python
class AttentionMechanism:
    """Select top-K memories based on attention scores"""

    def score_memory(self, memory: Memory, context: Context) -> float:
        """Multi-factor attention scoring"""
        score = 0.0

        # 1. Recency (exponential decay)
        age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600
        recency_score = math.exp(-age_hours / 24.0)  # Half-life of 1 day
        score += 0.3 * recency_score

        # 2. Importance (pre-computed)
        score += 0.4 * memory.importance

        # 3. Semantic relevance (if query provided)
        if context.query:
            semantic_score = self.compute_similarity(
                memory.embedding,
                context.query_embedding
            )
            score += 0.2 * semantic_score

        # 4. Access frequency (meta-memory)
        access_score = min(memory.access_count / 10.0, 1.0)
        score += 0.1 * access_score

        return score

    async def select_working_memory(
        self,
        context: Context,
        k: int = 7
    ) -> List[Memory]:
        """Select top-K memories for working memory"""

        # Get candidates (recent + important)
        candidates = await self.db.fetch("""
            SELECT * FROM episodic_events
            WHERE session_id = $1
            OR importance > 0.7
            ORDER BY timestamp DESC
            LIMIT 50
        """, context.session_id)

        # Score each candidate
        scored = [
            (memory, self.score_memory(memory, context))
            for memory in candidates
        ]

        # Return top-K
        scored.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, score in scored[:k]]
```

#### Auxiliary Cross Attention Network (ACAN)

**Research**: "The Auxiliary Cross Attention Network (ACAN) calculates and ranks attention weights between an agent's current state and stored memories, selecting the most relevant memories for any given situation."

```python
import torch
import torch.nn as nn

class MemoryAttention(nn.Module):
    """Learned attention over memory bank"""

    def __init__(self, hidden_dim=768):
        super().__init__()
        self.query_proj = nn.Linear(hidden_dim, hidden_dim)
        self.key_proj = nn.Linear(hidden_dim, hidden_dim)
        self.value_proj = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, current_state, memory_bank):
        """
        current_state: (1, hidden_dim) - current context embedding
        memory_bank: (N, hidden_dim) - stored memory embeddings
        """
        Q = self.query_proj(current_state)  # (1, hidden_dim)
        K = self.key_proj(memory_bank)      # (N, hidden_dim)
        V = self.value_proj(memory_bank)    # (N, hidden_dim)

        # Scaled dot-product attention
        scores = torch.matmul(Q, K.T) / math.sqrt(Q.size(-1))  # (1, N)
        weights = torch.softmax(scores, dim=-1)

        # Weighted sum of values
        attended = torch.matmul(weights, V)  # (1, hidden_dim)
        return attended, weights
```

### Hook Implementation (Athena Current Pattern)

```python
# ~/.claude/hooks/lib/working_memory_selector.py
class WorkingMemorySelector:
    """Select memories for injection into Claude context"""

    def __init__(self, limit=7):
        self.limit = limit
        self.attention = AttentionMechanism()

    async def select_for_session(self, session_id: str, query: str = None):
        """Select memories to inject via PostToolUse hook"""

        context = Context(
            session_id=session_id,
            query=query,
            query_embedding=self.embed(query) if query else None
        )

        # Use attention mechanism
        memories = await self.attention.select_working_memory(
            context,
            k=self.limit
        )

        # Format for Claude injection
        return self.format_for_injection(memories)

    def format_for_injection(self, memories: List[Memory]) -> str:
        """Format memories as markdown for context injection"""
        output = ["## Working Memory\n"]

        for i, memory in enumerate(memories, 1):
            output.append(f"**{i}. {memory.content}** ({memory.importance:.2f})")
            output.append(f"   *{memory.timestamp.strftime('%Y-%m-%d %H:%M')}*\n")

        return "\n".join(output)
```

**Hook Integration** (current Athena pattern):
```bash
# ~/.claude/hooks/PostToolUse.sh
python3 ~/.claude/hooks/lib/working_memory_injector.py \
    --session "$CLAUDE_SESSION_ID" \
    --limit 7
```

---

## 7. Production RAG Best Practices

### Architecture for Production RAG

**Research**: "In production deployments, RAG components are often decoupled into microservices, with a vector database service handling storage and similarity search, a retriever service handling query logic, and the LLM inference service handling generation."

#### Component Separation

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Processor │  ← Rewrite, expand, classify
│ (Classification)│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────┐   ┌─────┐
│BM25 │   │Vector│
└──┬──┘   └──┬──┘
   │         │
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Reranker│  ← MonoT5, cross-encoder
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │   LLM   │
   │Generator│
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Response│
   └─────────┘
```

### Critical Optimizations

#### 1. Query Classification (Avoid Unnecessary Retrieval)

**Research**: "Not all queries require retrieval-augmented responses... while RAG can enhance information accuracy, frequent retrieval can increase response time."

```python
class QueryClassifier:
    """Determine if query needs RAG or can use LLM directly"""

    PARAMETRIC_KEYWORDS = [
        "what is", "define", "explain", "how does",
        "tell me about"
    ]

    RETRIEVAL_KEYWORDS = [
        "latest", "recent", "current", "my", "our",
        "in our codebase", "from memory"
    ]

    def needs_retrieval(self, query: str) -> bool:
        """Simple heuristic classifier"""
        query_lower = query.lower()

        # Explicit retrieval request
        if any(kw in query_lower for kw in self.RETRIEVAL_KEYWORDS):
            return True

        # General knowledge question
        if any(kw in query_lower for kw in self.PARAMETRIC_KEYWORDS):
            return False

        # Default: use retrieval
        return True
```

#### 2. Reranking (Critical for Quality)

**Research**: "The absence of a reranking module leads to a noticeable drop in performance, with MonoT5 achieving the highest average score in augmenting the relevance of retrieved documents."

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class MonoT5Reranker:
    """Rerank retrieval results using MonoT5"""

    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("castorini/monot5-base-msmarco")
        self.model = AutoModelForSeq2SeqLM.from_pretrained("castorini/monot5-base-msmarco")

    def rerank(self, query: str, documents: List[str], top_k: int = 5):
        """Rerank documents by relevance to query"""
        scores = []

        for doc in documents:
            # Format: "Query: {query} Document: {doc} Relevant:"
            input_text = f"Query: {query} Document: {doc} Relevant:"
            inputs = self.tokenizer(input_text, return_tensors="pt")

            # Generate relevance score
            outputs = self.model.generate(**inputs, return_dict_in_generate=True, output_scores=True)
            score = outputs.scores[0][0].item()
            scores.append((doc, score))

        # Return top-K by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, score in scores[:top_k]]
```

#### 3. Caching (Latency Reduction)

**Research**: "Caching frequently seen queries, embeddings, or final answers can greatly improve responsiveness."

```python
from functools import lru_cache
import hashlib

class RAGCache:
    """Multi-level caching for RAG pipeline"""

    def __init__(self):
        self.query_cache = {}  # Query → Response
        self.embedding_cache = {}  # Text → Embedding

    @lru_cache(maxsize=1000)
    def get_embedding(self, text: str):
        """Cache embeddings (expensive to compute)"""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key not in self.embedding_cache:
            self.embedding_cache[cache_key] = self.model.encode(text)
        return self.embedding_cache[cache_key]

    def get_response(self, query: str, ttl: int = 3600):
        """Cache full responses for repeated queries"""
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if cache_key in self.query_cache:
            cached_at, response = self.query_cache[cache_key]
            if time.time() - cached_at < ttl:
                return response

        return None

    def set_response(self, query: str, response: str):
        """Store response in cache"""
        cache_key = hashlib.md5(query.encode()).hexdigest()
        self.query_cache[cache_key] = (time.time(), response)
```

#### 4. Monitoring and Metrics

**Research**: "You can't optimize what you can't measure."

```python
class RAGMetrics:
    """Track RAG system performance"""

    def __init__(self):
        self.metrics = defaultdict(list)

    def log_retrieval(self, query: str, latency_ms: float, num_results: int):
        self.metrics['retrieval_latency'].append(latency_ms)
        self.metrics['retrieval_count'].append(num_results)

    def log_generation(self, latency_ms: float, tokens: int):
        self.metrics['generation_latency'].append(latency_ms)
        self.metrics['generation_tokens'].append(tokens)

    def get_summary(self):
        """Return performance summary"""
        return {
            'avg_retrieval_latency': np.mean(self.metrics['retrieval_latency']),
            'p95_retrieval_latency': np.percentile(self.metrics['retrieval_latency'], 95),
            'avg_generation_latency': np.mean(self.metrics['generation_latency']),
            'total_queries': len(self.metrics['retrieval_latency'])
        }
```

### Athena RAG Integration

Current status: ✅ RAG components exist but optional

**Recommendations**:
1. **Enable reranking** for procedural memory retrieval
2. **Add query classification** to skip RAG when unnecessary
3. **Implement embedding caching** for repeated queries
4. **Add metrics collection** for optimization

---

## 8. Context Window Management

### Token Budget Strategy

**Research**: "It's generally good practice to keep the context to around 75% of the maximum tokens to allow the model to provide a complete answer."

#### Athena's Context Budget (for Claude Sonnet)

```python
# Context window: 200,000 tokens
# Reserve: 50,000 for response (25%)
# Available: 150,000 for context (75%)

CONTEXT_ALLOCATION = {
    "system_prompt": 2000,          # 1.3%
    "working_memory": 7000,         # 4.7% (top-7 memories @ ~1K each)
    "episodic_history": 20000,      # 13.3% (recent session events)
    "semantic_facts": 15000,        # 10% (relevant knowledge)
    "procedural_context": 10000,    # 6.7% (applicable procedures)
    "code_context": 80000,          # 53.3% (file contents, etc.)
    "user_query": 1000,             # 0.7%
    "buffer": 15000                 # 10% safety margin
}
```

### Dynamic Context Prioritization

**Research**: "A 2023 study found that LLMs perform best when the most relevant information is at the beginning or end of the input."

```python
class ContextManager:
    """Manage limited context window intelligently"""

    def build_context(
        self,
        query: str,
        max_tokens: int = 150000
    ) -> str:
        """Build context with priority-based allocation"""

        sections = []
        remaining = max_tokens

        # 1. System prompt (always include, at start)
        system = self.get_system_prompt()
        sections.append(system)
        remaining -= self.count_tokens(system)

        # 2. User query (always include, at end)
        query_tokens = self.count_tokens(query)
        remaining -= query_tokens

        # 3. Allocate remaining budget by priority
        allocations = [
            ("working_memory", 7000, lambda: self.get_working_memory()),
            ("procedural", 10000, lambda: self.get_relevant_procedures(query)),
            ("semantic", 15000, lambda: self.get_semantic_facts(query)),
            ("episodic", 20000, lambda: self.get_episodic_history()),
        ]

        for name, budget, getter in allocations:
            if remaining < budget:
                budget = remaining

            content = getter()
            truncated = self.truncate_to_budget(content, budget)
            sections.append(f"## {name.title()}\n{truncated}")
            remaining -= self.count_tokens(truncated)

        # 4. Add query at end (recency bias)
        sections.append(f"## Current Query\n{query}")

        return "\n\n".join(sections)

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit token budget"""
        tokens = self.count_tokens(text)
        if tokens <= max_tokens:
            return text

        # Simple truncation (could use sliding window or summary)
        ratio = max_tokens / tokens
        char_limit = int(len(text) * ratio * 0.95)  # 5% safety margin
        return text[:char_limit] + "\n[... truncated ...]"
```

### Sliding Window for Long Conversations

```python
class SlidingWindow:
    """Maintain conversation history with sliding window"""

    def __init__(self, window_size=10):
        self.window_size = window_size
        self.messages = []

    def add_message(self, role: str, content: str):
        """Add message and maintain window"""
        self.messages.append({"role": role, "content": content})

        # Keep only recent window
        if len(self.messages) > self.window_size:
            # Keep first message (system prompt) + recent window
            self.messages = [self.messages[0]] + self.messages[-self.window_size:]

    def get_context(self) -> List[Dict]:
        """Get current window for LLM"""
        return self.messages
```

---

## 9. Procedural Memory Extraction (Layer 3)

### Research-Backed Framework: Memp

**Finding**: "By distilling past successful workflows into reusable procedural priors, Memp raises success rates and shortens steps."

**Architecture**: "Memp consists of three key stages that work in a continuous loop: building, retrieving, and updating memory."

### Implementation Strategy

#### 1. Trajectory Capture

```python
class TrajectoryCapture:
    """Record action sequences for procedure extraction"""

    def __init__(self):
        self.current_trajectory = []

    def start_trajectory(self, goal: str):
        """Begin recording a new trajectory"""
        self.current_trajectory = {
            "goal": goal,
            "steps": [],
            "start_time": datetime.now(),
            "outcome": None
        }

    def record_step(self, action: str, result: Any, success: bool):
        """Record a single step in the trajectory"""
        self.current_trajectory["steps"].append({
            "action": action,
            "result": result,
            "success": success,
            "timestamp": datetime.now()
        })

    def finish_trajectory(self, outcome: str):
        """Complete trajectory recording"""
        self.current_trajectory["outcome"] = outcome
        self.current_trajectory["end_time"] = datetime.now()
        self.current_trajectory["duration"] = (
            self.current_trajectory["end_time"] -
            self.current_trajectory["start_time"]
        ).total_seconds()

        return self.current_trajectory
```

#### 2. Procedure Extraction

```python
class ProcedureExtractor:
    """Extract reusable procedures from successful trajectories"""

    async def extract_from_trajectory(self, trajectory: Dict) -> Optional[Procedure]:
        """Convert successful trajectory to procedure"""

        # Only extract from successful outcomes
        if trajectory["outcome"] != "success":
            return None

        # Check if similar procedure already exists
        similar = await self.find_similar_procedure(trajectory["goal"])
        if similar and similar.success_rate > 0.8:
            # Update existing procedure instead
            await self.update_procedure(similar, trajectory)
            return similar

        # Create new procedure
        procedure = Procedure(
            name=self.generate_name(trajectory),
            goal=trajectory["goal"],
            steps=[step["action"] for step in trajectory["steps"]],
            success_count=1,
            total_count=1,
            avg_duration=trajectory["duration"],
            metadata={
                "extracted_from": trajectory["start_time"],
                "complexity": len(trajectory["steps"])
            }
        )

        await self.db.store_procedure(procedure)
        return procedure

    def generate_name(self, trajectory: Dict) -> str:
        """Generate descriptive procedure name"""
        # Simple: use first action + goal
        first_action = trajectory["steps"][0]["action"] if trajectory["steps"] else "unknown"
        goal = trajectory["goal"][:30]
        return f"{first_action} for {goal}"
```

#### 3. Procedure Retrieval and Application

```python
class ProcedureLibrary:
    """Retrieve and apply learned procedures"""

    async def find_applicable_procedures(
        self,
        goal: str,
        context: Dict,
        min_success_rate: float = 0.6
    ) -> List[Procedure]:
        """Find procedures relevant to current goal"""

        # Semantic search on goal
        goal_embedding = self.embed(goal)
        candidates = await self.db.search_procedures(
            embedding=goal_embedding,
            limit=10
        )

        # Filter by success rate
        viable = [
            p for p in candidates
            if p.success_rate >= min_success_rate
        ]

        # Rank by success rate * recency
        scored = [
            (proc, self.score_procedure(proc, context))
            for proc in viable
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [proc for proc, score in scored]

    def score_procedure(self, proc: Procedure, context: Dict) -> float:
        """Score procedure applicability"""
        score = proc.success_rate * 0.6  # Base score from success rate

        # Recency bonus (favor recently successful procedures)
        if proc.last_success:
            days_ago = (datetime.now() - proc.last_success).days
            recency = math.exp(-days_ago / 30)  # Decay over 30 days
            score += recency * 0.2

        # Efficiency bonus (favor faster procedures)
        if proc.avg_duration < 60:  # Less than 1 minute
            score += 0.2

        return score
```

### Athena Current Implementation

✅ **Strengths**:
- Procedure storage schema exists
- Success tracking implemented
- Metadata support for complexity, tags

🔄 **Enhancements from Research**:

1. **Add trajectory capture to hooks**
```python
# PostToolUse hook enhancement
if tool_use.is_start_of_sequence:
    trajectory_tracker.start_trajectory(goal=user_intent)

trajectory_tracker.record_step(
    action=tool_use.name,
    result=tool_use.result,
    success=tool_use.success
)

if tool_use.is_end_of_sequence:
    trajectory = trajectory_tracker.finish_trajectory(outcome)
    await extractor.extract_from_trajectory(trajectory)
```

2. **Implement procedure recommendation**
```python
# Pre-task suggestion
async def suggest_procedures(task_description: str):
    """Suggest learned procedures for task"""
    procedures = await library.find_applicable_procedures(task_description)

    if procedures:
        print("📚 Found {len(procedures)} relevant procedures:")
        for proc in procedures[:3]:
            print(f"  - {proc.name} (success: {proc.success_rate:.0%})")
```

---

## 10. Event-Driven Hook Architecture

### Research-Backed Pattern

**Finding**: "A hook allows developers to attach logic at specific lifecycle stages of agent execution, such as input preparation, LLM response processing, tool invocation, or memory update."

### Athena Hook Lifecycle

```
User Input
    ↓
[UserPromptSubmit Hook]
    ↓
Spatial-temporal grounding
    ↓
[PreToolUse Hook]
    ↓
Validate environment
    ↓
Tool Execution
    ↓
[PostToolUse Hook]
    ↓
Record to episodic memory
Update working memory
    ↓
Response to User
    ↓
[SessionEnd Hook]
    ↓
Consolidate learnings
```

### Advanced Hook Patterns

#### 1. Hook Composition

```python
class HookPipeline:
    """Compose multiple hooks in sequence"""

    def __init__(self):
        self.hooks = []

    def register(self, hook: Callable, priority: int = 0):
        """Register hook with priority (lower = earlier)"""
        self.hooks.append((priority, hook))
        self.hooks.sort(key=lambda x: x[0])

    async def execute(self, event: Event) -> Event:
        """Execute all hooks in priority order"""
        for priority, hook in self.hooks:
            event = await hook(event)

            # Allow hooks to cancel pipeline
            if event.cancelled:
                break

        return event
```

#### 2. Conditional Hooks

```python
class ConditionalHook:
    """Only execute hook when condition met"""

    def __init__(self, condition: Callable, action: Callable):
        self.condition = condition
        self.action = action

    async def __call__(self, event: Event) -> Event:
        if self.condition(event):
            return await self.action(event)
        return event

# Example: Only inject memory for certain tools
memory_injection_hook = ConditionalHook(
    condition=lambda e: e.tool_name in ["Bash", "Read", "Write"],
    action=inject_working_memory
)
```

#### 3. Hook Telemetry

```python
class InstrumentedHook:
    """Wrap hook with monitoring"""

    def __init__(self, hook: Callable, name: str):
        self.hook = hook
        self.name = name
        self.metrics = {"calls": 0, "errors": 0, "total_time": 0}

    async def __call__(self, event: Event) -> Event:
        self.metrics["calls"] += 1
        start = time.time()

        try:
            result = await self.hook(event)
            return result
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Hook {self.name} failed: {e}")
            raise
        finally:
            self.metrics["total_time"] += time.time() - start

    def get_stats(self):
        avg_time = self.metrics["total_time"] / max(self.metrics["calls"], 1)
        return {
            "name": self.name,
            "calls": self.metrics["calls"],
            "errors": self.metrics["errors"],
            "avg_time_ms": avg_time * 1000
        }
```

---

## 11. Performance Benchmarks and Targets

### Latency Budget (Per Operation)

Based on 2024-2025 production research:

| Operation | Target | Acceptable | Notes |
|-----------|--------|-----------|-------|
| **Episodic retrieval** | <50ms | <100ms | Top-10 events |
| **Semantic search** (BM25 only) | <30ms | <50ms | PostgreSQL full-text |
| **Semantic search** (hybrid) | <100ms | <200ms | BM25 + vector + fusion |
| **Embedding generation** | <50ms | <100ms | Sentence-Transformers, batch=1 |
| **Knowledge graph query** | <100ms | <300ms | 1-3 hop traversal |
| **Procedure retrieval** | <50ms | <100ms | Semantic search + filtering |
| **Working memory selection** | <100ms | <200ms | Attention mechanism |
| **Consolidation** (incremental) | <1s | <5s | 20 events batch |
| **Consolidation** (nightly) | <60s | <300s | Full day processing |

### Throughput Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Events/second** (write) | >100 | Async batch insert |
| **Queries/second** (read) | >500 | Connection pool = 10 |
| **Embeddings/second** | >20 | Sentence-Transformers CPU |
| **Database connections** | 2-10 | asyncpg pool |

### Storage Estimates

| Component | Per Item | 1000 Items | 10000 Items |
|-----------|----------|------------|-------------|
| **Episodic event** | ~2KB | ~2MB | ~20MB |
| **+ embedding (384-dim)** | +1.5KB | +1.5MB | +15MB |
| **Semantic fact** | ~1KB | ~1MB | ~10MB |
| **Knowledge graph entity** | ~500B | ~500KB | ~5MB |
| **Procedure** | ~3KB | ~3MB | ~30MB |

**Athena current**: 8,128 episodic events ≈ 16MB (without embeddings)

---

## 12. Implementation Checklist

### Phase 1: Core Optimization (Week 1)

- [ ] Add database connection pool monitoring
- [ ] Implement query timeout protection
- [ ] Create composite indexes on episodic_events
- [ ] Add embedding caching layer
- [ ] Benchmark current performance

### Phase 2: Hybrid Search (Week 2)

- [ ] Add pgvector extension to PostgreSQL
- [ ] Add embedding column to semantic_memories
- [ ] Implement BM25 + vector hybrid search
- [ ] Add reciprocal rank fusion
- [ ] Compare performance vs. current BM25-only

### Phase 3: Memory Consolidation (Week 3)

- [ ] Implement incremental consolidation service
- [ ] Add scheduled nightly consolidation
- [ ] Create consolidation metrics tracking
- [ ] Test consolidation on 1000+ events

### Phase 4: Advanced Features (Week 4)

- [ ] Implement attention-based working memory selection
- [ ] Add procedure extraction from trajectories
- [ ] Enhance knowledge graph query optimization
- [ ] Add query classification for RAG

### Phase 5: Production Hardening (Week 5)

- [ ] Add comprehensive metrics collection
- [ ] Implement graceful degradation patterns
- [ ] Add circuit breakers for external dependencies
- [ ] Performance load testing (1000 queries/minute)
- [ ] Documentation update

---

## 13. Key Takeaways for Athena

### What's Already Strong ✅

1. **Async-first architecture** with asyncpg connection pooling
2. **Layered memory design** matching cognitive science
3. **PostgreSQL storage** (sufficient for current scale)
4. **Hook-based lifecycle** for event-driven operations
5. **Modular design** enabling incremental improvements

### High-Impact Optimizations 🎯

1. **Add hybrid search** (BM25 + vectors) for semantic layer
   - **Impact**: 30-50% improvement in retrieval quality
   - **Effort**: Medium (1 week)

2. **Implement attention-based working memory selection**
   - **Impact**: More relevant context injection
   - **Effort**: Low (2-3 days)

3. **Add background consolidation service**
   - **Impact**: Automatic pattern extraction, reduced manual overhead
   - **Effort**: Medium (1 week)

4. **Optimize knowledge graph queries**
   - **Impact**: 2-5x faster relationship traversal
   - **Effort**: Low (indexed recursive CTEs)

5. **Add query classification**
   - **Impact**: Reduce unnecessary RAG overhead
   - **Effort**: Low (simple heuristics)

### Research-Backed Enhancements 🔬

1. **Memory-Augmented Attention** (ACAN pattern)
2. **Procedural extraction from trajectories** (Memp pattern)
3. **Dual-process consolidation** (already implemented! ✅)
4. **Reciprocal rank fusion** for hybrid search
5. **Reranking with MonoT5** for critical queries

---

## 14. References and Further Reading

### Production Systems (2024-2025)

1. **MemGPT**: Virtual context management for LLMs
2. **Mem0**: Production-ready AI agents with scalable long-term memory (arXiv 2504.19413)
3. **LangGraph + MongoDB**: Long-term memory for agents
4. **Memp**: Exploring agent procedural memory (arXiv 2508.06433)

### Performance Guides

5. "Tuning FastAPI and PostgreSQL for High-Performance Asynchronous Queries with asyncpg" (2024)
6. "Hybrid Search Explained" (Weaviate)
7. "Building Production-Ready RAG Systems" (Medium, 2024)
8. "Searching for Best Practices in Retrieval-Augmented Generation" (arXiv 2407.01219)

### Cognitive Architectures

9. "A Scenario-Driven Cognitive Approach to Next-Generation AI Memory" (arXiv 2509.13235)
10. "Elements of episodic memory: insights from artificial agents" (PMC 2024)
11. "Cognitive Architectures for Language Agents" (arXiv 2309.02427)

### Database Optimization

12. asyncpg official documentation (magicstack.github.io/asyncpg)
13. pgvector documentation for PostgreSQL vector operations
14. "Neo4j vs PostgreSQL: Graph Database Capabilities" (Medium 2023)

---

**Document Version**: 1.0
**Compiled**: 2025-11-18
**Coverage**: 15+ production systems, 10+ research papers (2024-2025)
**Focus**: Engineering implementation, performance optimization, production deployment

**Companion Document**: See `consciousness_research_connections.md` for theoretical foundations
