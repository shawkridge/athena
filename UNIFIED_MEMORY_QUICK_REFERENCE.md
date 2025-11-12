# UnifiedMemoryManager Quick Reference - Phase 3

## Current State: NO recall() method yet

The manager has `retrieve()` (multi-layer intelligent query) but no dedicated `recall()` method. This is the entry point for Phase 3.

---

## All Query Layer Methods (7 Total)

```python
# Primary retrieval methods in UnifiedMemoryManager

_query_episodic(query, context, k)      # Layer 1: Events - returns {event_id, content, timestamp, type}
_query_semantic(query, context, k)      # Layer 2: Facts - returns {content, type, similarity, tags}
_query_procedural(query, context, k)    # Layer 3: Workflows - returns {name, category, template, success_rate}
_query_prospective(query, context, k)   # Layer 4: Tasks - returns {content, status, priority, assignee}
_query_graph(query, context, k)         # Layer 5: KG - returns {entity, type, relations:[...]}
_query_meta(query, context)             # Layer 6: Meta - returns domain metadata dict
_query_planning(query, context, k)      # Layer 7.5: Planning - returns {type, content, confidence, pattern_type}

# Hybrid orchestration
_hybrid_search(query, context, k)       # Combines 6 sources: semantic + lexical + RRF + episodic + procedural + graph
```

---

## Confidence Scoring (5 Factors)

Applied by `apply_confidence_scores()`:

```python
"confidence": {
    "semantic_relevance": 0.87,  # Vector similarity
    "source_quality": 0.80,       # Layer base (episodic=0.85, semantic=0.80, etc)
    "recency": 0.95,              # Exponential decay (1 day ago=0.95, 7 days=0.3, 30+ days=0)
    "consistency": 0.75,          # Flags from memory
    "completeness": 0.85,         # Metadata richness
    "overall": 0.84,              # Weighted average (35% relevance, 25% quality, 15% recency, 15% consistency, 10% completeness)
    "level": "high"               # VERY_HIGH (0.9+), HIGH (0.7+), MEDIUM (0.5+), LOW (0.3+), VERY_LOW
}
```

---

## Query Classification Rules

What determines which layer to query:

```python
IF "when", "last", "recent", "week", "date" 
   → TEMPORAL → _query_episodic()

IF "depends", "related", "connection", "uses"
   → RELATIONAL → _query_graph()

IF "decompose", "plan", "strategy", "orchestration", "validate"
   → PLANNING → _query_planning()  [checked BEFORE procedural!]

IF "how to", "workflow", "process", "steps", "procedure"
   → PROCEDURAL → _query_procedural()

IF "task", "todo", "remind", "pending"
   → PROSPECTIVE → _query_prospective()

IF "what do we know", "coverage", "expertise"
   → META → _query_meta()

ELSE
   → FACTUAL → _hybrid_search()
```

---

## Result Structures (What Each Layer Returns)

### Semantic (from _query_semantic via _query_semantic results):
```python
[
    {
        "content": str,
        "type": str,  # FACT, PATTERN, DECISION, CONTEXT
        "similarity": 0.87,
        "tags": [...],
        "confidence": {...}
    }
]
```

### Episodic (from _query_episodic):
```python
[
    {
        "event_id": int,
        "content": str,
        "timestamp": datetime,
        "type": str,  # action, observation, decision
        "confidence": {...}
    }
]
```

### Procedural (from _query_procedural):
```python
[
    {
        "name": str,
        "category": str,
        "template": str,
        "success_rate": float,
        "confidence": {...}
    }
]
```

### Full retrieve() Response:
```python
{
    "semantic": [...],
    "episodic": [...],
    "procedural": [...],
    "prospective": [...],
    "graph": [...],
    "meta": {...},
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

## Key Methods for Phase 3 Extension

### Methods to Hook Into:

| Method | Purpose | Input | Output | Use in Phase 3 |
|--------|---------|-------|--------|----------------|
| `apply_confidence_scores()` | Add confidence to each result | `{layer: [results]}` | `{layer: [results_with_confidence]}` | Extract confidence before cascade decision |
| `_hybrid_search()` | Multi-source fusion | query, context, k | merged results | Template for cascade merger |
| `_merge_results()` (in search.py) | RRF fusion | `[result_set1, result_set2]` | merged results | Reuse for cascade merging |
| `_explain_query_routing()` | Explain result selection | query, query_type, results | explanation dict | Extend to track cascade path |

---

## Reranking Pattern (Existing, Reusable for Phase 3)

From `SemanticSearch.recall_with_reranking()`:

```python
# 1. Retrieve 3*k candidates (over-fetch)
results = self.recall(query, project_id, k=k*3, memory_types=memory_types, min_similarity=0.2)

# 2. Composite reranking
for result in results:
    sim_score = result.similarity                                    # 0-1
    recency_score = max(0, 1.0 - (days_since_access / 90))          # 0-1, 90-day decay
    useful_score = memory.usefulness_score                          # 0-1
    
    composite = (
        similarity_weight * sim_score +                      # similarity_weight = 1 - recency_weight - usefulness_weight
        recency_weight * recency_score +                     # default: 0.1
        usefulness_weight * useful_score                     # default: 0.2
    )

# 3. Sort and return top-k
rescored.sort(key=lambda x: x[1], reverse=True)
return rescored[:k]
```

This exact pattern can be applied to merged cascade results!

---

## Entry Point for Phase 3: recall() Method

Should implement:

```python
def recall(
    self,
    query: str,
    context: Optional[dict] = None,
    k: int = 5,
    cascade: bool = True,                    # NEW: enable cascading
    confidence_threshold: float = 0.5,       # NEW: fallback if below this
    max_cascade_depth: int = 2,             # NEW: max layers to cascade through
    include_confidence_scores: bool = True,
    explain_reasoning: bool = True,
    **kwargs
) -> dict:
    """
    Intelligent cascading recall with confidence-based fallback.
    
    1. Execute primary query via retrieve()
    2. Score confidence on results
    3. If cascade enabled AND confidence < threshold:
       - Expand to secondary layers
       - Merge results using reranking
       - Track cascade path
    4. Return results with confidence and cascade explanation
    """
    pass
```

---

## Cascade Flow (Phase 3 Design)

```
recall(query, cascade=True, confidence_threshold=0.5, max_cascade_depth=2)
│
├─ Step 1: Classify query type
│          ↓
├─ Step 2: Execute primary query (retrieve() → specific layer)
│          ↓
├─ Step 3: Apply confidence scores
│          ↓
├─ Step 4: Check cascade condition
│   if results.confidence['overall'] < 0.5 AND cascade_depth < 2:
│          ↓
├─ Step 5: Cascade to secondary layers (e.g., episodic, graph)
│          ↓
├─ Step 6: Rerank merged results (reuse SemanticSearch pattern)
│          ↓
├─ Step 7: Track cascade path in _explanation
│          ↓
└─ Step 8: Return results with cascade metadata
```

---

## Files to Modify for Phase 3

1. **src/athena/manager.py** - Add recall() method
2. **src/athena/manager.py** - Add _cascade_to_[layer]() methods (7 total)
3. **src/athena/manager.py** - Add _merge_cascade_results() method
4. **src/athena/manager.py** - Update _explain_query_routing() to track cascade path

---

## Testing Strategy for Phase 3

```python
# Test cascade triggering
def test_cascade_on_low_confidence():
    # Create query that matches semantic poorly
    results = manager.recall(query, cascade=True, confidence_threshold=0.9)
    assert results['_cascade_path']['cascaded_to'] == ['episodic', 'graph']
    assert results['confidence']['overall'] > 0.5

# Test no cascade when confidence high
def test_no_cascade_on_high_confidence():
    # Create query that matches semantic well
    results = manager.recall(query, cascade=True, confidence_threshold=0.1)
    assert results['_cascade_path']['cascaded_to'] == []

# Test cascade depth limit
def test_cascade_depth_limit():
    results = manager.recall(query, cascade=True, max_cascade_depth=1)
    assert len(results['_cascade_path']['cascaded_to']) <= 1

# Test result merging
def test_cascade_merges_results():
    results = manager.recall(query, cascade=True, confidence_threshold=0.9)
    assert 'semantic' in results
    assert 'episodic' in results  # Should have cascaded results
    # Final confidence should improve
    assert results['confidence']['overall'] > 0.5
```

