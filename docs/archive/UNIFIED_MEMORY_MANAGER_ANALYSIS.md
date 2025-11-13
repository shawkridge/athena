# UnifiedMemoryManager Analysis - Phase 3 Cascading Recall Design

## Executive Summary

The `UnifiedMemoryManager` in `src/athena/manager.py` (800 lines) provides intelligent multi-layer retrieval with query type classification, layer-specific routing, hybrid search combining multiple retrieval strategies, and confidence scoring.

**Key Finding**: There is **NO existing `recall()` method** in UnifiedMemoryManager itself - only in underlying stores (`MemoryStore`, `SemanticSearch`). The manager has a **`retrieve()` method** that orchestrates multi-layer queries and is ready for Phase 3 cascading recall implementation.

---

## 1. Current Method Signatures

### UnifiedMemoryManager Methods

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
    """Multi-layer retrieval with optional confidence scoring and explanation."""
```

### MemoryStore Methods (called by manager)

```python
async def remember(
    self,
    content: str,
    memory_type: MemoryType | str,
    project_id: int,
    tags: Optional[list[str]] = None,
) -> int:
    """Store a new memory with embedding (PostgreSQL pgvector)."""

def recall(
    self,
    query: str,
    project_id: int,
    k: int = 5,
    memory_types: Optional[list[MemoryType]] = None,
) -> list[MemorySearchResult]:
    """Search for relevant memories semantically (delegates to SemanticSearch)."""

def recall_with_reranking(
    self, 
    query: str, 
    project_id: int, 
    k: int = 5
) -> list[MemorySearchResult]:
    """Search with composite scoring (similarity + recency + usefulness)."""
```

### SemanticSearch.recall_with_reranking Pattern

```python
def recall_with_reranking(
    self,
    query: str,
    project_id: int,
    k: int = 5,
    memory_types: Optional[list[MemoryType]] = None,
    recency_weight: float = 0.1,
    usefulness_weight: float = 0.2,
) -> list[MemorySearchResult]:
    """
    Two-stage reranking:
    1. Retrieve 3*k candidates (k=5 → 15 candidates)
    2. Composite score: similarity_weight*sim + recency_weight*recency + usefulness_weight*usefulness
    3. Sort and return top-k
    """
```

---

## 2. Layer-Specific Query Methods

The UnifiedMemoryManager has **7 layer-specific query methods**:

| Method | Layer | Returns |
|--------|-------|---------|
| `_query_episodic()` | Layer 1 (Events) | `list` of `{event_id, content, timestamp, type}` |
| `_query_semantic()` | Layer 2 (Facts) | `list` of `{content, type, similarity, tags}` |
| `_query_procedural()` | Layer 3 (Workflows) | `list` of `{name, category, template, success_rate}` |
| `_query_prospective()` | Layer 4 (Tasks) | `list` of `{content, status, priority, assignee}` |
| `_query_graph()` | Layer 5 (Knowledge Graph) | `list` of `{entity, type, relations:[{relation, to}]}` |
| `_query_meta()` | Layer 6 (Meta-Memory) | `dict` of domain metadata or `list` of domains |
| `_query_planning()` | Layer 7.5 (Planning) | `list` of `{type, content, confidence, pattern_type, rationale}` |

### Query Routing Logic (_classify_query)

```python
TEMPORAL        → "when", "last", "recent", "week", "date"
RELATIONAL      → "depends", "related", "connection", "uses"
PLANNING        → "decompose", "plan", "strategy", "orchestration" (checked BEFORE procedural)
PROCEDURAL      → "how to", "workflow", "process", "steps"
PROSPECTIVE     → "task", "todo", "remind", "pending"
META            → "what do we know", "coverage", "expertise"
DEFAULT (FACTUAL) → Everything else → HYBRID search
```

---

## 3. Hybrid Search Implementation

The `_hybrid_search()` method orchestrates **6 retrieval sources**:

```python
def _hybrid_search(
    self,
    query: str,
    context: dict,
    k: int,
    conversation_history: Optional[list[dict]] = None
) -> dict:
    """Combines:
    1. Vector search (semantic with advanced RAG)
    2. Lexical search (BM25)
    3. Reciprocal Rank Fusion (RRF) to merge semantic+lexical
    4. Episodic search (recent relevant events, k=3)
    5. Procedural search (if query suggests workflow)
    6. Graph search (entity relationships, k=3)
    """
```

### Result Fusion Pattern (RRF)

```python
# Convert results to (index, score) tuples
semantic_tuples = [(i, r.get('similarity', 0.5)) for i, r in enumerate(semantic_results)]
lexical_tuples = [(i, r.get('score', 0.5)) for i, r in enumerate(lexical_results)]

# Fuse using reciprocal rank fusion
from .memory.lexical import reciprocal_rank_fusion
fused = reciprocal_rank_fusion([semantic_tuples, lexical_tuples])

# Map back to content and add fused_score
results["semantic"] = [merged_results_with_fused_score]
```

---

## 4. Confidence Scoring Architecture

### apply_confidence_scores() Method

```python
def apply_confidence_scores(self, results: dict) -> dict:
    """For each layer in results dict:
    1. Create ConfidenceScorer.score(memory, source_layer, semantic_score)
    2. Compute 5 confidence factors (see below)
    3. Add confidence dict to each result with all factors + overall score
    """
```

### ConfidenceScores (5 Factors)

```python
class ConfidenceScores(BaseModel):
    semantic_relevance: float      # From vector similarity (0-1)
    source_quality: float          # From layer quality + meta-memory (0-1)
    recency: float                 # Exponential decay over 30 days (0-1)
    consistency: float             # Consistency with other memories (0-1)
    completeness: float            # Information richness (0-1)
    
    def average() -> float         # Simple mean of 5 factors
    def level() -> ConfidenceLevel # VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW
```

### Layer Quality Baselines (from ConfidenceScorer)

```python
layer_quality = {
    "episodic": 0.85,      # Well-grounded in time
    "semantic": 0.80,      # Well-verified
    "procedural": 0.75,    # Learned from experience
    "graph": 0.70,         # Synthesized
    "prospective": 0.65,   # Forward-looking
    "meta": 0.70,          # Meta-knowledge
}
```

### Recency Decay Function

```python
# Applied in ConfidenceScorer._compute_recency()
age_in_days = (now - created_at).total_seconds() / 86400

if days_old < 1:     return 0.95
elif days_old < 7:   return max(0.3, 0.95 - (days_old / 7) * 0.65)  # 7-day window
else:                return max(0.0, 0.3 - (days_old - 7) / 30 * 0.3)  # 30-day tail
```

### Aggregation Weights (aggregate_confidence)

```python
weights = {
    "semantic_relevance": 0.35,   # 35% - most important
    "source_quality": 0.25,       # 25% - source matters
    "recency": 0.15,              # 15% - favor recent
    "consistency": 0.15,          # 15% - favor consistent
    "completeness": 0.10,         # 10% - rich metadata
}

overall = sum(score * weight for score, weight in zip(scores, weights))
```

---

## 5. Result Structure

### MemorySearchResult (Base Unit)

```python
class MemorySearchResult(BaseModel):
    memory: Memory                    # Full memory object
    similarity: float                 # Semantic similarity (0-1)
    rank: int                         # Position in result set
    metadata: Optional[dict] = None   # Optional context (e.g., reranking scores)
```

### Memory (Stored Object)

```python
class Memory(BaseModel):
    id: Optional[int]
    project_id: int
    content: str
    memory_type: MemoryType           # FACT, PATTERN, DECISION, CONTEXT
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]
    access_count: int
    usefulness_score: float           # 0-1, used in reranking
    embedding: Optional[list[float]]
    consolidation_state: ConsolidationState
    superseded_by: Optional[int]      # For versioning
    version: int
```

### Full Result with Confidence

```python
{
    "semantic": [
        {
            "content": str,
            "type": str,
            "similarity": 0.87,
            "tags": [...],
            "confidence": {
                "semantic_relevance": 0.87,
                "source_quality": 0.80,
                "recency": 0.95,
                "consistency": 0.75,
                "completeness": 0.85,
                "overall": 0.84,         # Weighted average
                "level": "high"
            }
        }
    ],
    "episodic": [...],
    "procedural": [...],
    "_explanation": {
        "query": str,
        "query_type": str,
        "reasoning": str,
        "layers_searched": [...],
        "result_count": int
    }
}
```

---

## 6. Advanced RAG Integration

### RAGManager Usage in _query_semantic

```python
if use_advanced_rag and self.rag_manager:
    # Use RAG manager for advanced retrieval
    results = self.rag_manager.retrieve(
        query=query,
        project_id=project.id,
        k=k,
        strategy="auto",              # Let RAG decide best strategy
        conversation_history=conversation_history
    )
else:
    # Fallback to basic reranking
    results = self.semantic.recall_with_reranking(query, project_id, k)
```

### RAGManager Strategies
- **auto**: RAGManager selects best approach
- **hyde**: Hypothetical Document Embeddings (if available)
- **reranking**: Multi-stage reranking
- **reflective**: Reflective question generation
- **query_transform**: Query augmentation

---

## 7. Key Design Patterns

### Pattern 1: Graceful Degradation

```python
# Try RAG first, fallback to basic search
try:
    if RAG_AVAILABLE and self.rag_manager:
        results = self.rag_manager.retrieve(...)
except Exception as e:
    logger.warning(f"RAG failed, fallback: {e}")
    results = self.semantic.recall_with_reranking(...)
```

### Pattern 2: Multi-Stage Confidence Scoring

```python
# Stage 1: Per-result confidence (apply_confidence_scores)
result["confidence"] = {
    "semantic_relevance": ...,
    "source_quality": ...,
    "recency": ...,
    "consistency": ...,
    "completeness": ...,
    "overall": confidence_scorer.aggregate_confidence(scores),
    "level": scores.level()
}

# Stage 2: Optional filtering/ranking
from core.confidence_scoring import ConfidenceFilter
filtered = ConfidenceFilter.filter_by_confidence(results, min_confidence=0.6)
ranked = ConfidenceFilter.rank_by_confidence(filtered)
```

### Pattern 3: Query Context Enrichment

```python
# Load session context if available
if self.session_manager:
    session_context = self.session_manager.get_current_session()
    if session_context:
        context.update({
            "session_id": session_context.session_id,
            "task": session_context.current_task,
            "phase": session_context.current_phase,
            "recent_events": session_context.recent_events,
        })
```

---

## 8. Phase 3 Cascading Recall Design Implications

### Cascading Architecture Will:

1. **Extend retrieve()** with a `recall()` method that wraps retrieve with phase 3 semantics
2. **Add cascade parameter** to control fallback strategy (e.g., `cascade_on_low_confidence=True`)
3. **Implement fallback layers** based on confidence scores:
   - If semantic confidence < 0.5 → expand to episodic
   - If still < 0.5 → expand to graph/procedural
   - If still < 0.5 → expand to meta-memory analysis
4. **Track cascade path** in explanation (which layers were consulted, confidence at each stage)
5. **Reuse existing**: confidence scoring, layer routing, RRF fusion, result formatting

### Implementation Hook Points:

```python
# In retrieve() or new recall() method:
results = {}

# Primary layer query (based on query type)
results = self._query_[layer](query, context, k)
results = self.apply_confidence_scores(results)

# Phase 3: Cascading fallback
if results and results['confidence']['overall'] < confidence_threshold:
    # Try secondary layers
    secondary_results = self._cascade_to_[secondary_layer](...)
    results = self._merge_cascade_results(results, secondary_results)

# Track cascade path
results['_cascade_path'] = {
    'primary_layer': primary_layer,
    'primary_confidence': results['confidence']['overall'],
    'cascaded_to': [secondary_layers],
    'final_confidence': final_confidence
}
```

---

## 9. Key Files for Phase 3 Implementation

| File | Purpose | Key Classes/Methods |
|------|---------|-------------------|
| `src/athena/manager.py` | Main orchestration | `retrieve()`, `_hybrid_search()`, `apply_confidence_scores()` |
| `src/athena/memory/store.py` | Semantic layer | `recall()`, `recall_with_reranking()` |
| `src/athena/memory/search.py` | Search engine | `recall()` with query expansion, `recall_with_reranking()` |
| `src/athena/core/confidence_scoring.py` | Scoring engine | `ConfidenceScorer`, `ConfidenceFilter` |
| `src/athena/core/models.py` | Data models | `Memory`, `MemorySearchResult`, `MemoryType` |
| `src/athena/core/result_models.py` | Result models | `ConfidenceScores`, `ConfidenceLevel` |

---

## 10. Current Limitations & Opportunities

### Limitations
1. **No native recall()** - only retrieve() in manager (easy to add wrapper)
2. **No cascading logic** - each query targets single layer (Phase 3 will fix)
3. **Cascade path not tracked** - explanation doesn't show which layers were consulted (Phase 3 will add)
4. **No confidence-based fallback** - all results returned regardless of confidence (Phase 3 will implement)

### Opportunities for Phase 3
1. Add `recall()` method wrapper with cascading semantics
2. Implement `_cascade_to_[layer]()` methods for fallback
3. Add cascade depth/breadth control parameters
4. Track and explain cascade path in `_explanation`
5. Implement confidence-threshold-triggered cascades
6. Reuse existing reranking infrastructure for merged results

---

## Summary Table

| Aspect | Current State | Phase 3 Addition |
|--------|---------------|-----------------|
| Query Methods | 7 layer-specific methods | 7 + cascade methods |
| Confidence Scoring | Per-result factors | Cascade-aware factors |
| Result Merging | RRF for semantic+lexical | Cascade merger with confidence tracking |
| Fallback Strategy | None | Confidence-triggered layers |
| Explanation | Query routing only | Query routing + cascade path |

