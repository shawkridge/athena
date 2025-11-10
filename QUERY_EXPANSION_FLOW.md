# Query Expansion Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SemanticSearch.recall()                      │
│                                                                 │
│  Input: query="How do we handle authentication?"               │
│         project_id=1, k=5                                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │  Query Expansion Enabled?      │
         │  (RAG_QUERY_EXPANSION_ENABLED) │
         └────────┬───────────────┬────────┘
                  │               │
            YES   │               │ NO
                  │               │
                  ▼               ▼
    ┌─────────────────────┐   ┌──────────────────┐
    │ QueryExpander.      │   │ Single Query     │
    │ expand(query)       │   │ (original flow)  │
    │                     │   │                  │
    │ Generates:          │   │ embedding =      │
    │ - Original          │   │   embed(query)   │
    │ - Alternative 1     │   │                  │
    │ - Alternative 2     │   │ search(embedding)│
    │ - Alternative 3     │   │                  │
    │ - Alternative 4     │   │ return results   │
    └─────────┬───────────┘   └──────────────────┘
              │
              ▼
┌──────────────────────────────────┐
│  For each variant:               │
│                                  │
│  1. "How do we handle auth?"     │
│  2. "What auth methods used?"    │
│  3. "How is user auth impl?"     │
│  4. "Auth approach in code?"     │
│  5. "User verification system?"  │
└────────────┬─────────────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Generate Embedding    │
    │  (5 total)             │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Execute Search        │
    │  (backend: PG/Qdrant/  │
    │   SQLite)              │
    │                        │
    │  Request k*2 results   │
    │  per variant (k=5 →    │
    │  10 results/variant)   │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Collect All Results   │
    │  (5 variants × 10      │
    │   = 50 raw results)    │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  _merge_results()      │
    │                        │
    │  1. Group by memory_id │
    │  2. Keep highest score │
    │  3. Sort by similarity │
    │  4. Take top-k         │
    │  5. Update ranks       │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Return Final Results  │
    │  (5 unique memories)   │
    └────────────────────────┘
```

## Detailed Flow Example

### Input

```python
search.recall(
    query="How do we handle authentication?",
    project_id=1,
    k=5
)
```

### Step 1: Query Expansion (500ms cold, 0ms warm)

```
QueryExpander.expand("How do we handle authentication?")
  ↓
QueryExpansions(
  original="How do we handle authentication?",
  alternatives=[
    "What authentication methods are used?",
    "How is user auth implemented?",
    "Authentication approach in codebase?",
    "User verification and login system?"
  ],
  total_variants=5
)
```

### Step 2: Embed All Variants (50ms)

```
Variant 1: [0.23, 0.45, 0.67, ...] (768 dims)
Variant 2: [0.21, 0.48, 0.69, ...]
Variant 3: [0.25, 0.43, 0.65, ...]
Variant 4: [0.22, 0.46, 0.68, ...]
Variant 5: [0.24, 0.44, 0.66, ...]
```

### Step 3: Search Each Variant (400ms total, sequential)

```
Variant 1 → [mem_1(0.85), mem_2(0.78), mem_5(0.72), mem_7(0.68), ...]  (10 results)
Variant 2 → [mem_1(0.82), mem_3(0.75), mem_6(0.71), mem_9(0.65), ...]  (10 results)
Variant 3 → [mem_2(0.80), mem_4(0.74), mem_5(0.70), mem_8(0.64), ...]  (10 results)
Variant 4 → [mem_1(0.79), mem_3(0.73), mem_7(0.69), mem_10(0.63), ...] (10 results)
Variant 5 → [mem_2(0.77), mem_4(0.72), mem_6(0.68), mem_11(0.62), ...] (10 results)

Total: 50 raw results
```

### Step 4: Merge and Deduplicate (1ms)

```
Group by memory_id:
  mem_1: max(0.85, 0.82, 0.79) = 0.85
  mem_2: max(0.78, 0.80, 0.77) = 0.80
  mem_3: max(0.75, 0.73) = 0.75
  mem_4: max(0.74, 0.72) = 0.74
  mem_5: max(0.72, 0.70) = 0.72
  mem_6: max(0.71, 0.68) = 0.71
  mem_7: max(0.68, 0.69) = 0.69
  ...

Sort by similarity (descending):
  [mem_1(0.85), mem_2(0.80), mem_3(0.75), mem_4(0.74), mem_5(0.72), ...]

Take top-k (k=5):
  [mem_1, mem_2, mem_3, mem_4, mem_5]

Update ranks:
  mem_1: rank=1, similarity=0.85
  mem_2: rank=2, similarity=0.80
  mem_3: rank=3, similarity=0.75
  mem_4: rank=4, similarity=0.74
  mem_5: rank=5, similarity=0.72
```

### Step 5: Return Results

```python
[
  MemorySearchResult(memory=mem_1, similarity=0.85, rank=1),
  MemorySearchResult(memory=mem_2, similarity=0.80, rank=2),
  MemorySearchResult(memory=mem_3, similarity=0.75, rank=3),
  MemorySearchResult(memory=mem_4, similarity=0.74, rank=4),
  MemorySearchResult(memory=mem_5, similarity=0.72, rank=5),
]
```

**Total Time**: ~951ms (cold cache) or ~451ms (warm cache)

## Error Flow

```
┌─────────────────────────┐
│ Query Expansion Attempt │
└────────┬────────────────┘
         │
         ▼
    ┌────────────┐
    │ LLM Error? │
    └─┬────────┬─┘
      │        │
  YES │        │ NO
      │        │
      ▼        ▼
┌─────────┐  ┌──────────┐
│ Log     │  │ Continue │
│ Warning │  │ Normal   │
│         │  │ Flow     │
│ Fall    │  └──────────┘
│ Back to │
│ Single  │
│ Query   │
└─────────┘
```

## Configuration Flow

```
Environment Variables
  ↓
config.py
  ↓
SemanticSearch.__init__()
  ↓
QueryExpander initialization
  ↓
  If RAG_QUERY_EXPANSION_ENABLED=false:
    → self._query_expander = None
    → recall() uses single query

  If RAG_QUERY_EXPANSION_ENABLED=true:
    → Create LLM client (Claude or Ollama)
    → Create QueryExpander with config
    → recall() uses expansion flow
```

## Backend Routing

```
recall() with expansion
  ↓
  For each variant:
    ↓
    ┌──────────────────┐
    │ Check Backend    │
    └────┬────┬────┬───┘
         │    │    │
    ┌────┘    │    └────┐
    ▼         ▼         ▼
PostgreSQL  Qdrant  SQLite-vec
  hybrid    vector   fallback
  search    search   search
    │         │         │
    └────┬────┴────┬────┘
         ▼         ▼
    Variant    Variant
    Results    Results
```

## Performance Optimization Opportunities

### Current (Sequential)

```
Expansion: 500ms
  ↓
Embed V1: 10ms ──┐
Embed V2: 10ms   │
Embed V3: 10ms   │──→ 50ms
Embed V4: 10ms   │
Embed V5: 10ms ──┘
  ↓
Search V1: 80ms ──┐
Search V2: 80ms   │
Search V3: 80ms   │──→ 400ms
Search V4: 80ms   │
Search V5: 80ms ──┘
  ↓
Merge: 1ms
  ↓
Total: 951ms
```

### Optimized (Parallel)

```
Expansion: 500ms
  ↓
┌───────────────────────┐
│ Batch Embed (5 vars)  │──→ 15ms
└───────────────────────┘
  ↓
┌───────────────────────┐
│ Parallel Search (5x)  │──→ 80ms
│ via asyncio.gather()  │
└───────────────────────┘
  ↓
Merge: 1ms
  ↓
Total: 596ms (37% reduction)
```

## Memory Usage

```
Query String: ~100 bytes
Expanded Queries: ~500 bytes (5 variants)
Embeddings: 15 KB (5 × 768 dims × 4 bytes)
Raw Results: ~50 KB (50 results × ~1KB each)
Merged Results: ~5 KB (5 final results)

Peak Memory: ~70 KB (negligible)
```

## Logging Output

```
INFO - Initialized QueryExpander with Claude
INFO - Query expansion enabled (4 variants)
INFO - Query expansion: 5 variants in 0.52s
DEBUG - Searching variant: 'How do we handle authentication?'
DEBUG - Searching variant: 'What authentication methods are used?'
DEBUG - Searching variant: 'How is user auth implemented?'
DEBUG - Searching variant: 'Authentication approach in codebase?'
DEBUG - Searching variant: 'User verification and login system?'
INFO - Searched 5 variants in 0.41s (50 raw results)
DEBUG - Merged 50 results into 5 unique memories (deduplication: 45 duplicates)
INFO - Query expansion complete: 5 final results (total time: 0.93s)
```
