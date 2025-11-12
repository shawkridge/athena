# Phase 3 Implementation Architecture - Cascading Recall

## Current State: retrieve() Method

```
User Query
    ↓
retrieve(query, context, k, include_confidence_scores=True)
    ↓
[1] _classify_query(query)
    ├─ TEMPORAL → _query_episodic()
    ├─ RELATIONAL → _query_graph()
    ├─ PLANNING → _query_planning()
    ├─ PROCEDURAL → _query_procedural()
    ├─ PROSPECTIVE → _query_prospective()
    ├─ META → _query_meta()
    └─ FACTUAL (default) → _hybrid_search()
    ↓
[2] Execute query
    └─ Returns layer-specific results (list or dict)
    ↓
[3] apply_confidence_scores()
    ├─ For each result: compute 5 factors
    │   ├─ semantic_relevance (vector similarity)
    │   ├─ source_quality (layer base + meta-memory)
    │   ├─ recency (exponential decay)
    │   ├─ consistency (from flags)
    │   └─ completeness (metadata richness)
    ├─ Aggregate: 35% relevance + 25% quality + 15% recency + 15% consistency + 10% completeness
    └─ Add confidence dict to each result
    ↓
[4] _explain_query_routing() (optional)
    └─ Track which layers were queried
    ↓
[5] Return structured results
    {
        "semantic": [...],
        "episodic": [...],
        ...
        "_explanation": {...}
    }
```

---

## Phase 3 Addition: recall() Method

```
User Query
    ↓
recall(query, context, k, cascade=True, confidence_threshold=0.5, max_cascade_depth=2)
    ↓
[1] _classify_query(query)
    └─ Determines primary layer
    ↓
[2] CALL retrieve() [existing method]
    └─ Execute primary query + confidence scoring
    ↓
[3] Extract confidence from results
    confidence = results['semantic'][0]['confidence']['overall']
    ↓
[4] Cascade Decision
    IF cascade AND confidence < threshold AND cascade_depth < max_cascade_depth:
        ↓
        [5A] _cascade_to_[secondary_layers]()  [NEW METHODS]
             ├─ _cascade_to_episodic()
             ├─ _cascade_to_graph()
             ├─ _cascade_to_procedural()
             ├─ _cascade_to_prospective()
             └─ etc (7 total)
        ↓
        [5B] _merge_cascade_results()  [NEW METHOD]
             ├─ Combine primary + secondary results
             ├─ Apply reranking (reuse SemanticSearch pattern)
             ├─ Composite score: 0.7*primary_confidence + 0.3*secondary_confidence
             └─ Return merged ranked results
        ↓
    ELSE:
        Return primary results as-is
    ↓
[5] _explain_query_routing()  [EXTENDED]
    ├─ Original: which layers were queried
    └─ NEW: cascade_path tracking
        {
            "primary_layer": "semantic",
            "primary_confidence": 0.45,
            "cascaded_to": ["episodic", "graph"],
            "cascade_confidences": [0.72, 0.68],
            "final_confidence": 0.64,
            "merge_strategy": "confidence_weighted"
        }
    ↓
[6] Return cascaded results with metadata
    {
        "semantic": [...],
        "episodic": [...],      # NEW: from cascade
        "graph": [...],         # NEW: from cascade
        "_cascade_path": {...}, # NEW: tracking
        "_explanation": {...}
    }
```

---

## Cascade Decision Tree

```
confidence['overall'] < threshold?
│
├─ YES: cascade_depth < max_cascade_depth?
│       │
│       ├─ YES:
│       │   ├─ Select secondary layers based on primary layer
│       │   │   ├─ semantic → [episodic, graph, procedural]
│       │   │   ├─ episodic → [semantic, graph]
│       │   │   ├─ procedural → [episodic, semantic]
│       │   │   ├─ graph → [semantic, procedural, episodic]
│       │   │   └─ etc
│       │   │
│       │   ├─ Fetch from secondary layers (parallel or sequential)
│       │   │
│       │   ├─ Merge results
│       │   │   ├─ Over-fetch: 3*k from each secondary layer
│       │   │   ├─ Rerank by composite score
│       │   │   └─ Return top-k merged
│       │   │
│       │   └─ Recurse with cascade_depth + 1
│       │       (if still confidence < threshold)
│       │
│       └─ NO: Return primary results (depth limit reached)
│
└─ NO: Return primary results (high confidence)
```

---

## Result Merging Strategy (Reranking Pattern)

```
Primary Results (e.g., semantic layer)
    confidence = 0.45  [LOW - triggers cascade]
    ↓
Secondary Results (e.g., episodic + graph)
    episodic: [3 results]
    graph: [3 results]
    ↓
MERGE STEP:
    
    1. Over-fetch from each secondary
       episodic = _query_episodic(query, context, k=15)  # 3*k
       graph = _query_graph(query, context, k=15)
    
    2. Apply confidence to all results
       primary_results → [5 results with confidence]
       episodic_results → [15 results with confidence]
       graph_results → [15 results with confidence]
    
    3. Create composite pool
       all_results = primary_results + episodic_results + graph_results
       # 5 + 15 + 15 = 35 results
    
    4. Calculate composite score for each
       for result in all_results:
           source_weight = get_layer_weight(result.layer)
           composite = (
               0.5 * result.confidence['overall'] +  # 50% confidence
               0.3 * source_weight +                 # 30% source weighting
               0.2 * recency_boost                   # 20% recency
           )
    
    5. Sort by composite and return top-k (e.g., top-5)
       final_results = sorted(all_results, key=composite)[:k]
    
    6. Update ranks
       for i, result in enumerate(final_results):
           result.rank = i + 1
    ↓
FINAL MERGED RESULTS
    confidence improved: 0.45 → 0.68  [MEDIUM - acceptable]
    source diversity: semantic + episodic + graph
    result freshness: mixed recencies
```

---

## Cascade Path Tracking Example

```
Query: "What happened with the database configuration last week?"

[Step 1] Classify → TEMPORAL (contains "last week")

[Step 2] Execute primary
    → _query_episodic("What happened...", context, k=5)
    → Results: 2 matching events
    → Confidence: {
        "semantic_relevance": 0.45,    # Weak match to query
        "source_quality": 0.85,        # Episodic is strong
        "recency": 0.92,               # Recent (3 days)
        "consistency": 0.70,
        "completeness": 0.60,
        "overall": 0.68,               # MEDIUM
        "level": "medium"
    }

[Step 3] Check cascade
    confidence['overall'] = 0.68
    confidence_threshold = 0.5
    0.68 > 0.5? → NO cascade triggered
    
    → Return primary results only

RESULT:
{
    "episodic": [
        {
            "event_id": 42,
            "content": "Updated PostgreSQL connection pool from 10 to 20...",
            "timestamp": "2025-11-10T14:23:00Z",
            "type": "action",
            "confidence": {
                "semantic_relevance": 0.45,
                "source_quality": 0.85,
                "recency": 0.92,
                "consistency": 0.70,
                "completeness": 0.60,
                "overall": 0.68,
                "level": "medium"
            }
        }
    ],
    "_cascade_path": {
        "primary_layer": "episodic",
        "primary_confidence": 0.68,
        "cascaded_to": [],              # No cascade
        "final_confidence": 0.68,
        "cascade_trigger": "confidence > threshold",
        "reason": "Primary results had medium-high confidence"
    }
}

---

Query: "How should I optimize the memory system?"

[Step 1] Classify → PLANNING (contains "how should I", "optimize", "strategy")

[Step 2] Execute primary
    → _query_planning("How should I optimize...", context, k=5)
    → Results: 1 weak planning pattern
    → Confidence: {
        "semantic_relevance": 0.35,
        "source_quality": 0.70,
        "recency": 0.80,
        "consistency": 0.50,
        "completeness": 0.40,
        "overall": 0.55,              # MEDIUM, borderline
        "level": "medium"
    }

[Step 3] Check cascade
    confidence['overall'] = 0.55
    confidence_threshold = 0.5
    0.55 > 0.5? → YES but barely
    
    confidence_threshold = 0.65 (stricter)
    0.55 < 0.65? → YES cascade triggered!

[Step 4] Cascade to secondary layers
    → _cascade_to_semantic("How should I optimize...", context, k=15)
    → _cascade_to_procedural("How should I optimize...", context, k=15)
    → Results:
        semantic: [15 results with ~0.65-0.75 confidence]
        procedural: [15 results with ~0.70-0.80 confidence]

[Step 5] Merge and rerank
    primary (planning): 1 result @ 0.55
    secondary (semantic): 15 results @ 0.65-0.75
    secondary (procedural): 15 results @ 0.70-0.80
    
    → Over-sample from secondary (already 15 each)
    → Create composite scores
    → Return top-5
    
    → Final confidence: 0.68  [improved from 0.55]

RESULT:
{
    "planning": [
        {
            "type": "planning_pattern",
            "content": "Optimize consolidation by reducing...",
            "confidence": {..., "overall": 0.55},
            "pattern_type": "performance_optimization",
            "rationale": "Based on historical patterns"
        }
    ],
    "semantic": [
        {
            "content": "Memory consolidation algorithm achieves 2-3s per 1000 events...",
            "type": "fact",
            "similarity": 0.72,
            "confidence": {..., "overall": 0.70}
        }
    ],
    "procedural": [
        {
            "name": "Optimize Consolidation Process",
            "category": "system_improvement",
            "template": "1. Measure current performance... 2. Identify bottleneck...",
            "success_rate": 0.85,
            "confidence": {..., "overall": 0.75}
        }
    ],
    "_cascade_path": {
        "primary_layer": "planning",
        "primary_confidence": 0.55,
        "cascaded_to": ["semantic", "procedural"],     # Triggered cascade
        "cascade_confidences": [0.70, 0.75],
        "final_confidence": 0.68,                      # Improved
        "cascade_trigger": "confidence < stricter_threshold (0.65)",
        "reason": "Primary layer had insufficient confidence; expanded to related layers",
        "merge_strategy": "confidence_weighted (50% planning + 25% semantic + 25% procedural)",
        "results_combined": "1 primary + 15 secondary + 15 tertiary = 31 total → top-5 selected"
    }
}
```

---

## Implementation Checklist for Phase 3

```
Core Methods:
  ☐ recall() - Main entry point with cascade logic
  ☐ _cascade_to_episodic() - Fallback to Layer 1
  ☐ _cascade_to_semantic() - Fallback to Layer 2
  ☐ _cascade_to_procedural() - Fallback to Layer 3
  ☐ _cascade_to_prospective() - Fallback to Layer 4
  ☐ _cascade_to_graph() - Fallback to Layer 5
  ☐ _cascade_to_meta() - Fallback to Layer 6
  ☐ _merge_cascade_results() - Merge + rerank from multiple layers
  
Result Management:
  ☐ Update _explain_query_routing() to track cascade path
  ☐ Add cascade_path dict to result metadata
  ☐ Ensure all cascade results include confidence scores
  ☐ Implement cascade depth tracking
  
Configuration:
  ☐ DEFAULT_CONFIDENCE_THRESHOLD = 0.5
  ☐ MAX_CASCADE_DEPTH = 2
  ☐ CASCADE_LAYER_WEIGHTS = {...}  # For composite scoring
  ☐ MERGE_STRATEGY = "confidence_weighted"
  
Testing:
  ☐ test_cascade_triggered_on_low_confidence()
  ☐ test_no_cascade_on_high_confidence()
  ☐ test_cascade_depth_limit()
  ☐ test_result_merging()
  ☐ test_cascade_path_tracking()
  ☐ test_confidence_improvement_after_cascade()
  ☐ test_layer_weighting_in_merge()
  
Documentation:
  ☐ Update CLAUDE.md with recall() method docs
  ☐ Add cascade architecture diagram
  ☐ Document cascade layer precedence
  ☐ Add example queries showing cascade behavior
```

---

## Layer Precedence for Cascade Selection

When cascading from each primary layer:

```
Primary: SEMANTIC
  Secondary 1: EPISODIC (episodic provides temporal grounding)
  Secondary 2: GRAPH (graph provides relational context)
  Secondary 3: PROCEDURAL (procedural provides how-to patterns)

Primary: EPISODIC
  Secondary 1: SEMANTIC (semantic provides fact verification)
  Secondary 2: GRAPH (graph provides entity relationships)

Primary: PROCEDURAL
  Secondary 1: EPISODIC (episodic provides examples)
  Secondary 2: SEMANTIC (semantic provides background)

Primary: PROSPECTIVE
  Secondary 1: PROCEDURAL (procedural provides how-to for tasks)
  Secondary 2: SEMANTIC (semantic provides context)

Primary: GRAPH
  Secondary 1: SEMANTIC (semantic for entity facts)
  Secondary 2: EPISODIC (episodic for entity history)

Primary: META
  Secondary 1: SEMANTIC (semantic for domain examples)
  Secondary 2: GRAPH (graph for domain structure)

Primary: PLANNING
  Secondary 1: SEMANTIC (semantic for background facts)
  Secondary 2: PROCEDURAL (procedural for similar patterns)
```

---

## Expected Phase 3 Impact

```
BEFORE (retrieve() only):
  - User query → Primary layer only
  - If primary layer has low confidence → User gets poor results
  - No fallback mechanism

AFTER (recall() with cascade):
  - User query → Primary layer
  - If confidence < threshold → Automatically cascade
  - Secondary layers supplement primary
  - Results merged with improved confidence
  - User gets richer, more confident answers

Example: "How to optimize PostgreSQL?"
  BEFORE:
    - Classified as PROCEDURAL
    - Returns: 2 procedures (low semantic relevance to specific question)
    - Confidence: 0.45 (medium-low)
    - User disappointed
  
  AFTER:
    - Classified as PROCEDURAL
    - Primary: 2 procedures (confidence 0.45)
    - Cascade triggered: Fetch SEMANTIC + EPISODIC
    - Merge: Top-5 from 32 results
    - Final: 2 procedures + 2 semantic facts + 1 episode (better variety)
    - Confidence: 0.68 (improved)
    - User satisfied
```

