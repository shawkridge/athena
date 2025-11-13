# TOON Format Integration Analysis for Athena

## Executive Summary

**TOON (Token-Oriented Object Notation)** is a compact serialization format that reduces token usage by 30-60% when sending structured data to LLMs. It's highly relevant to Athena because:

1. **Athena extensively sends memory data to LLMs** via MCP tools and RAG operations
2. **Token efficiency directly reduces operational costs** and improves response latency
3. **Memory structures are highly uniform** (events, patterns, entities, relationships) - TOON's ideal use case
4. **Multiple integration points** exist across memory layers and MCP handlers

---

## What is TOON?

### Core Concept
TOON translates between JSON (programmatic) and a compact token-efficient format (LLM input):

```
# JSON (verbose)
{
  "users": [
    {"id": 1, "name": "Alice", "role": "admin"},
    {"id": 2, "name": "Bob", "role": "user"}
  ]
}

# TOON (compact - 39.6% fewer tokens!)
users[2]{id,name,role}:
 1,Alice,admin
 2,Bob,user
```

### Key Benefits

| Aspect | Benefit |
|--------|---------|
| **Token Efficiency** | 30-60% fewer tokens on uniform arrays |
| **LLM Comprehension** | 73.9% accuracy with 39.6% fewer tokens (benchmark) |
| **Cost Reduction** | Direct proportional reduction in API spend |
| **Performance** | Faster LLM response times (smaller input) |
| **Readability** | Still human-readable, minimal syntax |

### Design Philosophy
- **CSV's efficiency** for tabular data
- **YAML's structure** for nesting
- **JSON's clarity** (still explicit, machine-readable)
- **Minimal punctuation** (removes braces, brackets, redundant quotes)

---

## Athena Memory Structures (Perfect TOON Candidates)

### 1. Episodic Events Layer
**Current Problem**: Queries retrieve 10-50 events as JSON objects with repeated field declarations.

```python
# Current JSON output
{
  "events": [
    {
      "id": 1,
      "type": "code_interaction",
      "timestamp": "2025-11-10T10:30:00",
      "tags": ["refactor", "optimization"],
      "entity_type": "function",
      "entity_name": "consolidate_events"
    },
    {
      "id": 2,
      "type": "decision",
      "timestamp": "2025-11-10T11:00:00",
      "tags": ["planning", "strategy"],
      "entity_type": "goal",
      "entity_name": "improve_memory_efficiency"
    }
  ]
}
```

**With TOON** (estimated ~40% token reduction):
```
events[2]{id,type,timestamp,tags,entity_type,entity_name}:
 1,code_interaction,2025-11-10T10:30:00,[refactor; optimization],function,consolidate_events
 2,decision,2025-11-10T11:00:00,[planning; strategy],goal,improve_memory_efficiency
```

**Integration Point**: `src/athena/mcp/handlers_retrieval.py` - recall/search operations

---

### 2. Knowledge Graph Entities & Relations
**Current Problem**: Graph queries return many entity-relation pairs with repeated structure.

```python
# Candidate for TOON: Batch entity queries
{
  "entities": [
    {"id": 101, "type": "code_symbol", "name": "Database.execute", "domain": "core"},
    {"id": 102, "type": "code_symbol", "name": "RAGManager.retrieve", "domain": "rag"},
    {"id": 103, "type": "concept", "name": "consolidation", "domain": "memory"}
  ]
}

# TOON equivalent
entities[3]{id,type,name,domain}:
 101,code_symbol,Database.execute,core
 102,code_symbol,RAGManager.retrieve,rag
 103,concept,consolidation,memory
```

**Integration Point**: `src/athena/graph/store.py` and `src/athena/mcp/graphrag_tools.py`

---

### 3. Procedural Memory (Learned Procedures)
**Current Problem**: Procedures are complex nested structures with many similar steps.

```python
# Batch procedure list
{
  "procedures": [
    {
      "id": 1,
      "name": "code_refactoring",
      "steps_count": 5,
      "effectiveness_score": 0.92,
      "category": "development"
    },
    {
      "id": 2,
      "name": "memory_consolidation",
      "steps_count": 8,
      "effectiveness_score": 0.87,
      "category": "memory"
    }
  ]
}

# TOON equivalent
procedures[2]{id,name,steps_count,effectiveness_score,category}:
 1,code_refactoring,5,0.92,development
 2,memory_consolidation,8,0.87,memory
```

**Integration Point**: `src/athena/procedural/store.py` and MCP procedure tools

---

### 4. Semantic Memory Search Results
**Current Problem**: Search results are uniform with field repetition.

```python
# Search results (20-100 items typical)
{
  "results": [
    {"score": 0.95, "embedding_id": 1001, "text_preview": "consolidate events...", "date": "2025-11-10"},
    {"score": 0.91, "embedding_id": 1002, "text_preview": "pattern extraction...", "date": "2025-11-09"}
  ]
}

# TOON equivalent
results[2]{score,embedding_id,text_preview,date}:
 0.95,1001,consolidate events...,2025-11-10
 0.91,1002,pattern extraction...,2025-11-09
```

**Integration Point**: `src/athena/semantic/search.py` and RAG manager

---

### 5. Meta-Memory Metrics & Quality Scores
**Current Problem**: Status queries return many metrics with uniform structure.

```python
# Health check output
{
  "layers": [
    {"name": "episodic", "event_count": 8128, "quality_score": 0.87},
    {"name": "semantic", "entry_count": 3456, "quality_score": 0.91},
    {"name": "procedural", "procedure_count": 101, "quality_score": 0.79}
  ]
}

# TOON equivalent
layers[3]{name,event_count,quality_score}:
 episodic,8128,0.87
 semantic,3456,0.91
 procedural,101,0.79
```

**Integration Point**: `src/athena/meta/quality.py` and health check handlers

---

## Integration Strategy

### Phase 1: Foundation (Week 1)
**Goal**: Add TOON encoder/decoder to Athena with zero impact on existing code.

1. **Create `src/athena/serialization/toon_codec.py`**
   ```python
   from toon_format import encode, decode  # npm package wrapper

   class TOONCodec:
       @staticmethod
       def encode(data: dict, schema: dict) -> str:
           """Convert JSON to TOON using schema hints."""
           return encode(data)

       @staticmethod
       def decode(toon_str: str) -> dict:
           """Parse TOON back to JSON."""
           return decode(toon_str)

       @staticmethod
       def from_json_to_toon_safe(data, allow_toon=False):
           """Gracefully convert to TOON if enabled, fallback to JSON."""
           if not allow_toon:
               return data
           return TOONCodec.encode(data)
   ```

2. **Identify schema definitions**
   - Document field orders for each data type (events, entities, procedures, etc.)
   - Create `src/athena/serialization/schemas.py` with TOON schemas

3. **Add configuration flag**
   ```python
   # src/athena/core/config.py
   USE_TOON_FORMAT = os.getenv("ATHENA_USE_TOON", "false") == "true"
   ```

4. **Wrap Python-to-JS bridge**
   - Use `subprocess` to call Node.js `@toon-format/toon` CLI
   - Or use `quickjs-emscripten` to run TOON encoder in-process

---

### Phase 2: Tactical Integration (Week 2)
**Goal**: Integrate TOON into high-impact MCP handlers.

**Priority 1: RAG Recall Operations** (Most frequent LLM input)
- File: `src/athena/mcp/handlers_retrieval.py`
- Function: `recall`, `search`, `recall_events_by_session`
- Modification: Wrap JSON results with `TOONCodec.encode()` when enabled

```python
def recall(self, query: str, limit: int = 10) -> str:
    results = self.memory_manager.recall(query, limit)

    if CONFIG.USE_TOON_FORMAT:
        return TOONCodec.encode(results, schema="episodic_events")

    return json.dumps(results)
```

**Priority 2: Graph Queries** (Knowledge graph traversal)
- File: `src/athena/mcp/graphrag_tools.py`
- Functions: Entity batch queries, community detection results

**Priority 3: Semantic Search** (Frequent batch results)
- File: `src/athena/rag/manager.py`
- Function: `retrieve` - wrap search results in TOON

**Priority 4: Health/Metrics Queries**
- File: `src/athena/mcp/handlers_system.py`
- Function: `health_check`, `get_memory_stats`

---

### Phase 3: Advanced Integration (Week 3)
**Goal**: Optimize TOON usage patterns and add intelligence.

1. **Adaptive Format Selection**
   ```python
   def smart_format(data: dict, estimated_token_count: int):
       """Use TOON only when token savings > 15%."""

       if estimated_token_count < 100:
           return "json"  # No savings for tiny responses

       if is_uniform_array(data) and not has_deeply_nested(data):
           return "toon"

       return "json"
   ```

2. **Context Window Optimization**
   - Track LLM context window usage
   - Automatically enable TOON when context pressure > 70%
   - Fallback to JSON for LLMs with issues (debug mode)

3. **Format Negotiation**
   - Add `format` parameter to all MCP tools
   - Allow clients to request preferred format: `format="json"` or `format="toon"`

4. **Caching Layer**
   ```python
   # Cache pre-computed TOON encodings
   class TOONCache:
       def get_or_encode(self, data_id: str, data: dict) -> str:
           """Return cached TOON or encode fresh."""
           if cached := self.cache.get(data_id):
               return cached
           encoded = TOONCodec.encode(data)
           self.cache.set(data_id, encoded)
           return encoded
   ```

---

## Implementation Roadmap

### Quick Win: Minimal Integration
**Time**: ~4 hours | **Impact**: 30-40% token reduction on search results

```python
# Step 1: Add TOON codec
# File: src/athena/serialization/toon_codec.py
# Lines: ~50-100

# Step 2: Modify handlers
# Files: handlers_retrieval.py, graphrag_tools.py
# Changes: Wrap JSON results in TOONCodec.encode()
# Lines per file: ~10-20 changes

# Step 3: Add config flag
# File: src/athena/core/config.py
# Lines: ~5

# Step 4: Test
# New tests: test_toon_codec.py, test_toon_integration.py
# Lines: ~200-300
```

### Full Integration: Comprehensive
**Time**: ~2-3 weeks | **Impact**: 40-60% token reduction + cost optimization

- Adaptive format selection
- Streaming TOON for large result sets
- MCP tool parameter negotiation
- Comprehensive benchmarking
- Documentation & monitoring

---

## Cost-Benefit Analysis

### Costs
- **Implementation**: ~80-120 hours development
- **Testing**: ~40-60 hours (new test suite)
- **Maintenance**: +5-10% ongoing (format versioning, debugging)
- **Dependencies**: Add `@toon-format/toon` npm package

### Benefits
- **Direct Savings**: 30-60% reduction in LLM API token usage
  - If Athena uses 1M tokens/month at $0.10/1K tokens = **$100/month → $40-70/month**
  - ROI break-even: ~1-2 months of LLM usage

- **Performance**: 20-30% faster LLM response times (smaller input)
- **UX**: Better context window management for agents
- **Scalability**: Enables larger memory operations before hitting context limits

---

## Technical Challenges & Solutions

### Challenge 1: Python ↔ JavaScript Bridge
**Problem**: TOON is TypeScript/JavaScript; Athena is Python.

**Solutions**:
1. **Subprocess wrapper** (simplest)
   ```bash
   npm install @toon-format/toon -g
   echo '{"key": "value"}' | toon encode
   ```

2. **Node.js child process** (recommended)
   ```python
   import subprocess
   import json

   def encode_toon(data):
       result = subprocess.run(
           ["node", "-e", "require('@toon-format/toon').encode(...)"],
           input=json.dumps(data),
           capture_output=True,
           text=True
       )
       return result.stdout
   ```

3. **WASM binding** (advanced)
   - Compile TOON to WebAssembly
   - Use `wasmer` Python bindings
   - Requires maintenance

**Recommendation**: Start with subprocess, optimize to process pool if needed.

### Challenge 2: Schema Definition & Maintenance
**Problem**: TOON needs explicit field orders; changing schemas breaks old encodings.

**Solution**: Schema registry with versioning
```python
# src/athena/serialization/schemas.py
SCHEMAS = {
    "episodic_events": {
        "version": 1,
        "fields": ["id", "type", "timestamp", "tags", "entity_type", "entity_name"],
        "types": {"timestamp": "iso8601", "tags": "array", "id": "int"}
    }
}
```

### Challenge 3: Type Preservation
**Problem**: TOON compresses type info; LLM may misinterpret `0.95` as integer.

**Solution**: Type hints in TOON header or separate schema
```
# Option 1: Embedded types (verbose)
results[2]{score:float,embedding_id:int,text_preview:str,date:date}:

# Option 2: Separate schema (Athena approach)
# Schema ID in metadata, actual types in registry
```

### Challenge 4: Complex Nested Data
**Problem**: TOON is efficient for flat/tabular; Athena has nested structures (procedures with steps, events with metadata).

**Solution**: Multi-level TOON encoding
```
procedures[2]{id,name,steps_count,effectiveness_score}:
 1,code_refactoring,5,0.92
 2,memory_consolidation,8,0.87

# Nested steps within each (if needed):
# procedure_1_steps[5]{order,action,input,output}:
#  1,parse,code_file,ast
```

---

## Integration Points by Priority

### 🔴 High Priority (Immediate ROI)
1. **Search Results** (`handlers_retrieval.py`)
   - Most frequent LLM input
   - Highly uniform structure (array of scored results)
   - Estimated savings: **35-45% tokens**

2. **Entity/Knowledge Graph Queries** (`graphrag_tools.py`)
   - Batch entity lookups
   - Consistent field structure
   - Estimated savings: **40-50% tokens**

3. **Procedural Memory Lists** (`procedural/store.py`)
   - Uniform procedure metadata
   - Used in planning & synthesis
   - Estimated savings: **30-40% tokens**

### 🟡 Medium Priority (High Value)
4. **Semantic Search Results** (`semantic/search.py`)
   - Large result sets (100+ items)
   - Repeated scoring fields
   - Estimated savings: **40-50% tokens**

5. **System Health Metrics** (`meta/quality.py`)
   - Used in monitoring & decisions
   - Uniform metrics structure
   - Estimated savings: **35-45% tokens**

6. **Task/Goal Listings** (`prospective/store.py`)
   - Batch queries of goals/tasks
   - Consistent schema
   - Estimated savings: **30-40% tokens**

### 🟢 Lower Priority (Polish)
7. **Meta-memory Quality Reports**
   - Lower frequency queries
   - Smaller result sets
   - Estimated savings: **25-35% tokens**

8. **Context Metadata**
   - Auxiliary information
   - Can remain JSON for readability

---

## Proof of Concept: 2-Hour Implementation

```python
# 1. Add TOON codec (50 lines)
# src/athena/serialization/toon_codec.py
import subprocess
import json

class TOONCodec:
    @staticmethod
    def encode(data: dict) -> str:
        """Encode dict to TOON format."""
        result = subprocess.run(
            ["npx", "@toon-format/toon", "encode"],
            input=json.dumps(data),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            raise ValueError(f"TOON encoding failed: {result.stderr}")
        return result.stdout

    @staticmethod
    def decode(toon_str: str) -> dict:
        """Decode TOON to dict."""
        result = subprocess.run(
            ["npx", "@toon-format/toon", "decode"],
            input=toon_str,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            raise ValueError(f"TOON decoding failed: {result.stderr}")
        return json.loads(result.stdout)

# 2. Update search handler (10 lines)
# src/athena/mcp/handlers_retrieval.py
def recall(self, query: str, limit: int = 10) -> str:
    results = self.memory_manager.recall(query, limit)

    if os.getenv("ATHENA_USE_TOON") == "true":
        from athena.serialization.toon_codec import TOONCodec
        return TOONCodec.encode(results)

    return json.dumps(results)

# 3. Add tests (100 lines)
# tests/serialization/test_toon_codec.py
def test_encode_decode_roundtrip():
    data = {"events": [{"id": 1, "type": "test"}]}
    encoded = TOONCodec.encode(data)
    decoded = TOONCodec.decode(encoded)
    assert decoded == data
```

**Result**: 30-40% token reduction on search with <150 lines of code + config.

---

## Monitoring & Metrics

### Key Metrics to Track
```python
# src/athena/mcp/toon_metrics.py

class TOONMetrics:
    def __init__(self):
        self.json_tokens_total = 0      # Tokens if using JSON
        self.toon_tokens_total = 0      # Tokens with TOON
        self.encode_time_ms_total = 0   # Encoding overhead
        self.decode_time_ms_total = 0   # Decoding overhead
        self.format_usage_count = {
            "json": 0,
            "toon": 0
        }

    def record_encoding(self, data_size_bytes: int,
                       json_tokens: int, toon_tokens: int,
                       encode_time_ms: float):
        """Record TOON encoding event."""
        self.json_tokens_total += json_tokens
        self.toon_tokens_total += toon_tokens
        self.encode_time_ms_total += encode_time_ms
        self.format_usage_count["toon"] += 1

    def get_efficiency_report(self):
        return {
            "token_reduction_percent": (
                (self.json_tokens_total - self.toon_tokens_total) /
                self.json_tokens_total * 100
            ),
            "avg_encode_time_ms": (
                self.encode_time_ms_total /
                max(self.format_usage_count["toon"], 1)
            ),
            "toon_vs_json_ratio": (
                self.format_usage_count["toon"] /
                max(sum(self.format_usage_count.values()), 1)
            )
        }
```

### Dashboard Queries
- **Weekly token savings**: Track total reduction
- **TOON adoption rate**: % of queries using TOON
- **Encoding overhead**: Time cost of compression
- **LLM accuracy**: Ensure TOON doesn't degrade comprehension

---

## Recommendations

### ✅ Do Integrate TOON If:
1. Athena frequently sends 1000+ tokens per query
2. Cost optimization is a priority
3. You have control over LLM invocation
4. You can monitor & validate quality
5. Memory structure is mostly uniform (episodic, graph, procedures)

### ❌ Don't Integrate If:
1. Token efficiency is not a bottleneck
2. Debugging/readability is critical (TOON less readable)
3. You need broad ecosystem support (JSON is universal)
4. Very complex nested structures dominate queries

### 🎯 Optimal Approach:
**Hybrid Integration** (Recommended for Athena)
- Use TOON for uniform batch queries (search results, entity lists, metrics)
- Keep JSON for complex nested data (procedures with steps, events with full context)
- Add `format` parameter to MCP tools for client-side choice
- Monitor effectiveness; toggle on/off per tool based on ROI

---

## Next Steps

1. **Research validation** ✅ (This document)
2. **PoC implementation** (2-4 hours)
   - Basic TOON codec wrapper
   - One MCP handler integration
   - Measure token reduction
3. **Stakeholder review** (decision point)
   - Is 30-40% token reduction worth implementation cost?
   - Do we proceed with Phase 1 foundation?
4. **Phase 1: Foundation** (if approved)
   - Full TOON codec with error handling
   - Configuration system
   - Comprehensive tests
5. **Phase 2: Integration** (successive weeks)
   - Handler-by-handler integration
   - Performance benchmarking
   - Production monitoring

---

## References

- **TOON Spec**: https://github.com/toon-format/toon/blob/main/SPEC.md
- **TOON npm Package**: `@toon-format/toon`
- **TOON Repository**: https://github.com/toon-format/toon
- **Token Economy Overview**: https://platform.openai.com/docs/guides/tokens

---

**Author's Note**: TOON is particularly well-suited to Athena's architecture because:
1. **Episodic events** are naturally tabular (id, timestamp, type, tags, entity, context)
2. **Knowledge graph** queries return uniform entity/relation pairs
3. **Procedures** are lists of similar operations
4. **Search results** are scored arrays with consistent fields

The main implementation complexity is the Python↔JavaScript bridge, which can be solved elegantly with a subprocess wrapper or process pool for production use.
