---
name: pattern-extraction
description: |
  Pattern extraction using filesystem API paradigm (discover → read → execute → summarize).
  Dual-process reasoning: fast statistical clustering + optional LLM validation for uncertainty regions.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Pattern Extraction Skill (Filesystem API Edition)

Extract patterns from episodic events and consolidate work into lasting semantic knowledge using dual-process reasoning.

## When to Use

- After completing major work sessions
- To extract learnings and create reusable procedures
- Improving memory quality and compression ratios
- Analyzing temporal patterns and causal relationships
- Identifying uncertainty regions for deeper analysis

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("consolidation")`
- Discover available consolidation strategies
- Show what pattern extraction operations exist

### Step 2: Analyze Events
- Determine consolidation type (temporal, causal, semantic, statistical)
- Auto-select optimal strategy
- Prepare clustering parameters

### Step 3: Execute Locally
- Use `adapter.execute_operation("consolidation", strategy, args)`
- Statistical clustering happens in sandbox (~100ms)
- LLM validation only for high-uncertainty regions (>0.5)
- No data loaded into context

### Step 4: Return Summary
- Pattern count and types discovered
- Compression ratio achieved
- New procedures created
- Quality metrics (recall, consistency, density)
- Uncertainty regions for drill-down
- Consolidation recommendations

## Dual-Process Reasoning

### System 1 (Fast, ~100ms)
- Statistical clustering of episodic events
- Frequency-based pattern detection
- Heuristic weighting and scoring
- Automatic uncertainty assessment

### System 2 (Slow, ~1-5s, Selective)
- Triggered only for uncertainty > 0.5
- LLM semantic validation
- Confidence verification and refinement
- Context enrichment for complex patterns

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 245,

  "consolidation_strategy": "balanced",
  "events_analyzed": 127,
  "patterns_discovered": 18,

  "compression_ratio": 0.78,
  "new_semantic_memories": 12,
  "procedures_created": 3,

  "quality_metrics": {
    "recall_score": 0.84,
    "consistency_score": 0.79,
    "density_score": 0.81,
    "overall_quality": 0.81
  },

  "pattern_categories": {
    "temporal": 7,
    "causal": 5,
    "semantic": 6
  },

  "high_confidence_patterns": 15,
  "uncertainty_regions": 3,

  "top_patterns": [
    {"id": 42, "type": "temporal", "confidence": 0.92, "events": 23},
    {"id": 43, "type": "causal", "confidence": 0.88, "events": 18},
    {"id": 44, "type": "semantic", "confidence": 0.85, "events": 15}
  ],

  "procedures_created": [
    {"id": 1, "name": "error_debugging", "reuse_count": 5, "success_rate": 0.92},
    {"id": 2, "name": "code_review", "reuse_count": 3, "success_rate": 0.85},
    {"id": 3, "name": "testing_workflow", "reuse_count": 2, "success_rate": 0.88}
  ],

  "recommendations": [
    "Validate uncertainty region #2 with System 2 LLM analysis",
    "Archive consolidated pattern #42 (high confidence, frequently reused)",
    "Consider creating procedure from pattern cluster #5"
  ],

  "note": "Call adapter.get_detail('consolidation', 'pattern', id) for full pattern details"
}
```

## Consolidation Strategies

1. **Balanced**: Mixed temporal + semantic clustering (default)
2. **Temporal**: Focus on time-series patterns and causality
3. **Semantic**: Focus on meaning and relationships
4. **Statistical**: Pure frequency analysis without LLM validation
5. **Adaptive**: Strategy selection based on event distribution

## Token Efficiency
Old: 150K tokens | New: <400 tokens | **Savings: 99%**

## Examples

### Basic Pattern Extraction

```python
# Discover available strategies
adapter.list_operations_in_layer("consolidation")
# Returns: ['balanced', 'temporal', 'semantic', 'statistical', 'adaptive']

# Execute extraction
result = adapter.execute_operation(
    "consolidation",
    "balanced",
    {"events_limit": 500, "min_confidence": 0.6}
)

# Analyze summary
print(f"Extracted {result['patterns_discovered']} patterns")
print(f"Compression: {result['compression_ratio']:.2%}")

# Drill down on uncertainty
if result['uncertainty_regions'] > 0:
    adapter.execute_operation(
        "consolidation",
        "llm_validate",
        {"pattern_ids": result['uncertain_pattern_ids']}
    )
```

### Temporal Pattern Analysis

```python
result = adapter.execute_operation(
    "consolidation",
    "temporal",
    {
        "time_window_days": 7,
        "causality_analysis": True
    }
)

# Results include temporal relationships and causal chains
for pattern in result['top_patterns']:
    if pattern['type'] == 'causal':
        print(f"Causal chain: {pattern['id']} (confidence: {pattern['confidence']})")
```

### Procedure Creation from Patterns

```python
# Extract patterns then create procedures
result = adapter.execute_operation(
    "consolidation",
    "procedure_extraction",
    {"min_reuse_count": 3}
)

# Returns procedures created and effectiveness metrics
for proc in result['procedures_created']:
    print(f"{proc['name']}: {proc['success_rate']:.2%} success rate")
```

## Implementation Notes

Demonstrates filesystem API paradigm for pattern consolidation and procedure learning. This skill:
- Discovers available consolidation strategies via filesystem
- Executes dual-process reasoning locally
- Returns only summary metrics (pattern counts, quality scores, IDs)
- Supports drill-down for specific pattern details via `adapter.get_detail()`
- Auto-selects System 1 vs System 2 based on uncertainty thresholds
- Learns when deeper validation is needed for future reference
