---
name: quality-evaluation
description: |
  Quality evaluation using filesystem API paradigm (discover → read → execute → summarize).
  4-metric framework assesses memory health: compression, recall, consistency, density.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Quality Evaluation Skill (Filesystem API Edition)

Assess memory quality and identify knowledge gaps for targeted improvement using 4-metric framework.

## When to Use

- Evaluating overall memory health periodically
- Finding contradictions and inconsistencies
- Identifying knowledge gaps and weak areas
- Planning consolidation and optimization priorities
- Domain-specific expertise assessment
- Detecting uncertainty regions that need reinforcement

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("meta")`
- Discover available quality assessment operations
- Show what quality evaluation operations exist

### Step 2: Analyze Memory State
- Determine assessment scope (global, domain-specific, layer-specific)
- Check for contradictions and inconsistencies
- Identify uncertainty regions and gaps

### Step 3: Execute Locally
- Use `adapter.execute_operation("meta", "evaluate_quality", args)`
- Quality scoring happens in sandbox (~200ms)
- Multi-layer analysis and synthesis
- Domain expertise tracking
- No data loaded into context

### Step 4: Return Summary
- Overall quality score (0.0-1.0)
- Per-domain expertise breakdown
- Identified contradictions and severity
- Uncertainty regions flagged
- Knowledge gaps discovered
- Consolidation recommendations by priority

## Quality Metrics (4-Metric Framework)

1. **Compression** (Target: 70-85%): How efficiently patterns compress episodic events
   - Measures: event-to-semantic ratio
   - Optimal: 70-85% reduction from raw events

2. **Recall** (Target: >80%): Ability to retrieve relevant information
   - Measures: retrieval success rate
   - Optimal: >80% relevant results in top-k

3. **Consistency** (Target: >75%): Absence of contradictions
   - Measures: contradiction ratio
   - Optimal: <25% contradictory assertions

4. **Density**: Richness of context per memory unit
   - Measures: context depth and breadth
   - Optimal: Well-connected, multi-faceted knowledge

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 234,

  "overall_quality_score": 0.82,
  "quality_status": "HEALTHY",

  "metrics": {
    "compression_ratio": 0.78,
    "compression_score": 0.85,
    "recall_score": 0.84,
    "consistency_score": 0.79,
    "density_score": 0.81,
    "overall_composite": 0.82
  },

  "contradictions_found": 3,
  "contradictions": [
    {
      "id": 42,
      "type": "factual_conflict",
      "severity": "high",
      "statement_a": "Authentication uses JWT tokens",
      "statement_b": "Authentication uses OAuth 2.0",
      "affected_memories": 2,
      "resolution_needed": true
    }
  ],

  "uncertainty_regions": 5,
  "high_uncertainty_patterns": [
    {"id": 87, "pattern": "deployment_strategy", "uncertainty": 0.68},
    {"id": 92, "pattern": "error_handling", "uncertainty": 0.62}
  ],

  "knowledge_gaps": [
    {
      "domain": "security",
      "gap": "OAuth 2.0 flow details",
      "severity": "medium",
      "affected_queries": 3,
      "recommendation": "Document OAuth 2.0 implementation"
    },
    {
      "domain": "performance",
      "gap": "Caching strategy",
      "severity": "low",
      "affected_queries": 1,
      "recommendation": "Add caching patterns from recent work"
    }
  ],

  "domain_expertise": {
    "security": {"coverage": 0.85, "confidence": 0.82},
    "performance": {"coverage": 0.72, "confidence": 0.68},
    "architecture": {"coverage": 0.91, "confidence": 0.89},
    "testing": {"coverage": 0.78, "confidence": 0.81}
  },

  "consolidation_priority": [
    {
      "priority": 1,
      "type": "contradiction_resolution",
      "target": "Authentication approach",
      "impact": "high",
      "estimated_time_minutes": 30
    },
    {
      "priority": 2,
      "type": "gap_filling",
      "target": "OAuth 2.0 flow",
      "impact": "medium",
      "estimated_time_minutes": 45
    },
    {
      "priority": 3,
      "type": "uncertainty_validation",
      "target": "Deployment strategy",
      "impact": "medium",
      "estimated_time_minutes": 20
    }
  ],

  "recommendations": [
    "Resolve contradiction #42 (Authentication approach) - HIGH priority",
    "Consolidate knowledge in 'security' domain (coverage: 85%)",
    "Fill gap on 'Caching strategy' (affects 1 query)",
    "Validate uncertainty in pattern #87 (deployment_strategy)",
    "Consider domain-specific consolidation for 'performance' (72% coverage)"
  ],

  "next_assessment": "2025-11-19",

  "note": "Call adapter.get_detail('meta', 'contradiction', 42) for full contradiction analysis"
}
```

## Quality Status Levels

- **HEALTHY** (≥0.85): Continue current practices, minor improvements only
- **WARNING** (0.65-0.85): Schedule consolidation and gap-filling
- **CRITICAL** (<0.65): Immediate consolidation and validation needed

## Token Efficiency
Old: 150K tokens | New: <400 tokens | **Savings: 99%**

## Examples

### Basic Quality Assessment

```python
# Discover available quality operations
adapter.list_operations_in_layer("meta")
# Returns: ['evaluate_quality', 'assess_domain', 'find_contradictions', 'measure_gaps']

# Run comprehensive quality assessment
result = adapter.execute_operation(
    "meta",
    "evaluate_quality",
    {"scope": "global", "include_domain_analysis": True}
)

# Check overall status
print(f"Quality Status: {result['quality_status']}")
print(f"Score: {result['overall_quality_score']:.2f}")

# Review priority actions
for item in result['consolidation_priority'][:3]:
    print(f"{item['priority']}: {item['type']} on {item['target']}")
```

### Domain-Specific Assessment

```python
# Assess specific domain
result = adapter.execute_operation(
    "meta",
    "assess_domain",
    {"domain": "security", "detailed_gaps": True}
)

print(f"Security coverage: {result['domain_expertise']['security']['coverage']:.1%}")

# Get gap recommendations
for gap in result['knowledge_gaps']:
    if gap['domain'] == 'security':
        print(f"Gap: {gap['gap']} (severity: {gap['severity']})")
```

### Contradiction Resolution

```python
# Find and analyze contradictions
result = adapter.execute_operation(
    "meta",
    "find_contradictions",
    {"min_severity": "medium"}
)

print(f"Contradictions found: {result['contradictions_found']}")

for contradiction in result['contradictions']:
    print(f"\n{contradiction['statement_a']}")
    print(f"vs")
    print(f"{contradiction['statement_b']}")
    print(f"Resolution needed: {contradiction['resolution_needed']}")
```

### Uncertainty Validation

```python
# Find patterns needing validation
result = adapter.execute_operation(
    "meta",
    "identify_uncertainty",
    {"threshold": 0.6}
)

for pattern in result['high_uncertainty_patterns']:
    print(f"{pattern['pattern']}: {pattern['uncertainty']:.2f} uncertainty")
    # Could trigger System 2 (LLM) validation
```

## Implementation Notes

Demonstrates filesystem API paradigm for memory quality assessment. This skill:
- Discovers available quality operations via filesystem
- Evaluates memory across 4 quality metrics
- Identifies contradictions, gaps, and uncertainties
- Returns only summary metrics (scores, IDs, recommendations)
- Supports drill-down for full details via `adapter.get_detail()`
- Provides domain-specific expertise tracking
- Prioritizes consolidation actions by impact
- Learns quality patterns for proactive assessment
