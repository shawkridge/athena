# Vector Database Architecture Evaluation

**Context:** Fresh database initialization - opportunity to pick optimal solution

## Requirements

1. **Local-first** - Privacy, no cloud dependencies
2. **Docker-ready** - Easy deployment
3. **Scale** - Handle 10K → 1M+ documents
4. **Performance** - Sub-100ms semantic search
5. **Features** - Hybrid search, metadata filtering, reranking
6. **Backup/Restore** - Simple data management
7. **Multi-modal** - Support text + code embeddings

---

## Option 1: SQLite + sqlite-vec (Current)

### Pros
✅ Single file database - trivial backup
✅ Zero configuration
✅ Unified storage (vectors + structured data)
✅ Already implemented and working
✅ No network calls
✅ Perfect for <10K documents

### Cons
❌ Poor performance at scale (>50K vectors)
❌ No native HNSW/IVF indexing
❌ Limited advanced RAG features
❌ No distributed support
❌ BM25 implemented in Python (slow)

### Verdict
**Good for:** Prototypes, small deployments, single-user
**Bad for:** Production scale, multi-user, advanced RAG

---

## Option 2: PostgreSQL + pgvector

### Pros
✅ Production-grade RDBMS
✅ pgvector extension for embeddings
✅ HNSW indexing support
✅ Full SQL features (joins, transactions, etc.)
✅ pg_trgm for full-text search
✅ Mature backup/restore tools
✅ Single database for everything

### Cons
❌ More complex setup vs SQLite
❌ Slower than specialized vector DBs
❌ No built-in reranking/MMR
❌ Still limited at 1M+ vectors

### Docker Setup
```yaml
postgres:
  image: ankane/pgvector:latest
  environment:
    POSTGRES_DB: athena
    POSTGRES_PASSWORD: athena
  volumes:
    - postgres-data:/var/lib/postgresql/data
```

### Verdict
**Good for:** Unified data model, moderate scale, SQL familiarity
**Bad for:** Massive scale, bleeding-edge RAG features

---

## Option 3: ChromaDB

### Pros
✅ Purpose-built for embeddings
✅ Simple API (add/query)
✅ Built-in metadata filtering
✅ Multi-modal (text, images)
✅ Local + server modes
✅ Active development
✅ Python-native

### Cons
❌ Still young (stability concerns)
❌ No production hardening at scale
❌ Limited advanced RAG features
❌ SQLite backend (same scaling issues)

### Docker Setup
```yaml
chromadb:
  image: chromadb/chroma:latest
  ports:
    - "8001:8000"
  volumes:
    - chroma-data:/chroma/chroma
```

### Verdict
**Good for:** Quick prototypes, ML experiments, small teams
**Bad for:** Production systems, large scale

---

## Option 4: Qdrant

### Pros
✅ **Best-in-class performance**
✅ Native HNSW indexing
✅ Rich filtering (metadata, geo, range)
✅ Quantization for efficiency
✅ Snapshot backup/restore
✅ Multi-tenancy support
✅ Production-ready
✅ Horizontal scaling
✅ REST + gRPC APIs

### Cons
❌ Separate service (not embedded)
❌ Requires structured data in SQLite still
❌ More moving parts

### Docker Setup
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
    - "6334:6334"  # gRPC
  volumes:
    - qdrant-data:/qdrant/storage
```

### Verdict
⭐ **STRONG CONTENDER** - Best performance + production-ready
**Good for:** Production systems, scale, advanced RAG
**Bad for:** Simple prototypes, embedded needs

---

## Option 5: Weaviate

### Pros
✅ GraphQL API
✅ Built-in vectorization modules
✅ Multi-tenancy
✅ Hybrid search (BM25 + vector)
✅ Generative search integration
✅ Production-ready

### Cons
❌ Heavy (JVM-based)
❌ Complex configuration
❌ Overkill for most use cases
❌ Resource hungry

### Verdict
**Good for:** Enterprise, complex schemas, GraphQL fans
**Bad for:** Lightweight deployments, resource-constrained

---

## Option 6: Milvus

### Pros
✅ Highest performance at massive scale
✅ GPU support
✅ Multiple index types
✅ Production-ready
✅ Used by major companies

### Cons
❌ **Complex deployment** (Kafka, etcd, MinIO)
❌ Overkill for <10M vectors
❌ Steep learning curve
❌ Resource intensive

### Verdict
**Good for:** Billion-scale vectors, GPU acceleration
**Bad for:** Everything else

---

## Option 7: Hybrid Architecture (RECOMMENDED)

### Architecture
```
┌─────────────────────────────────────┐
│   Application Layer (Manager)       │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐        ┌─────▼──────┐
│ SQLite │        │  Qdrant    │
│        │        │            │
├────────┤        ├────────────┤
│Tasks   │        │Embeddings  │
│Events  │        │Semantic    │
│Goals   │        │Search      │
│Entities│        │Reranking   │
│Relations│       │            │
└────────┘        └────────────┘
```

### Rationale
✅ **Best of both worlds**
✅ SQLite for structured data (tasks, events, relations)
✅ Qdrant for semantic search (fast, scalable)
✅ Clear separation of concerns
✅ Can backup/migrate each independently
✅ Gradual migration path

### Implementation
- Keep all non-embedding tables in SQLite
- Move `semantic_memories.embedding` → Qdrant
- Implement adapter in `rag/vector_store.py`
- Environment variable: `VECTOR_STORE=sqlite|qdrant`

---

## Recommendation Matrix

| Use Case | Recommendation | Why |
|----------|---------------|-----|
| **Prototype/Demo** | SQLite + sqlite-vec | Simplicity |
| **Single User/Local** | SQLite + sqlite-vec | No complexity |
| **Production (<100K docs)** | PostgreSQL + pgvector | Unified, reliable |
| **Production (>100K docs)** | SQLite + Qdrant | Best performance |
| **Advanced RAG** | SQLite + Qdrant | Reranking, filtering |
| **Enterprise/Scale** | PostgreSQL + Qdrant | Both production-grade |

---

## Final Recommendation: **SQLite + Qdrant Hybrid**

### Why?
1. **Best performance** for semantic search (Qdrant)
2. **Simplicity** for structured data (SQLite)
3. **Docker-ready** - add one service
4. **Future-proof** - scales to millions
5. **Local-first** - both run locally
6. **Clear migration** - move embeddings only

### Migration Plan
```python
# Phase 1: Add Qdrant container (today)
# Phase 2: Implement QdrantAdapter
# Phase 3: Migrate semantic_memories embeddings
# Phase 4: A/B test performance
# Phase 5: Switch default
```

### Cost
- **Development time:** 4-6 hours
- **Runtime overhead:** Minimal (<50MB RAM)
- **Complexity:** Low (one extra service)

---

## Implementation Checklist

- [ ] Add Qdrant to docker-compose.yml
- [ ] Create `src/athena/rag/vector_stores/qdrant_adapter.py`
- [ ] Update `UnifiedMemoryManager` to use adapter
- [ ] Add env var: `VECTOR_STORE=qdrant`
- [ ] Migrate embeddings from SQLite → Qdrant
- [ ] Update backup scripts
- [ ] Benchmark performance
- [ ] Document new architecture

**Estimated time:** 4-6 hours
**Performance gain:** 5-10x on semantic search
**Scale ceiling:** 10M+ documents
