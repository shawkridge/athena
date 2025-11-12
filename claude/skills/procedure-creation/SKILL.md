---
name: procedure-creation
description: |
  Procedure creation using filesystem API paradigm (discover → read → execute → summarize).
  Extract reusable workflows from completed multi-step work and create procedures with effectiveness metrics.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Procedure Creation Skill (Filesystem API Edition)

Extract and create reusable procedures from completed multi-step work with effectiveness metrics and reuse analysis.

## When to Use

- After completing a complex multi-step task
- To create procedures for repeated patterns and workflows
- Documenting best practices and learnings for future reuse
- Building a library of reusable workflows
- Improving procedure effectiveness through execution tracking

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("procedural")`
- Discover available procedure operations
- Show what procedure extraction and creation operations exist

### Step 2: Analyze Work
- Determine procedure type (sequential, conditional, decision-tree, parallel)
- Extract step dependencies and decision points
- Identify inputs, outputs, and success criteria

### Step 3: Execute Locally
- Use `adapter.execute_operation("procedural", "extract", args)`
- Pattern analysis happens in sandbox (~150ms)
- Effectiveness calculation and reuse prediction
- Similarity check against existing procedures
- No data loaded into context

### Step 4: Return Summary
- New procedure created with ID
- Applicability score (0.0-1.0)
- Estimated time and effort savings
- Success rate from execution history
- Recommendations for improvements
- Similar existing procedures found

## What Gets Captured

- **Steps**: Sequential or conditional tasks
- **Dependencies**: Which steps depend on others
- **Inputs**: What's needed to start
- **Outputs**: Expected results
- **Decision Points**: Where choices happen
- **Success Criteria**: How to verify completion
- **Edge Cases**: Special handling needed
- **Metrics**: Effectiveness measures (time saved, success rate)

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 178,

  "procedure_created": true,
  "procedure_id": 142,
  "procedure_name": "code_review_workflow",
  "procedure_description": "Multi-step code review process with quality checks",

  "applicability_analysis": {
    "reuse_frequency": 0.87,
    "estimated_time_savings_minutes": 45,
    "success_rate": 0.91,
    "confidence": 0.85
  },

  "procedure_structure": {
    "total_steps": 12,
    "sequential_steps": 8,
    "conditional_steps": 3,
    "parallel_executable": 2,
    "dependencies": 15
  },

  "execution_history": {
    "total_executions": 23,
    "successful": 21,
    "failed": 2,
    "success_rate": 0.91
  },

  "effectiveness": {
    "average_duration_minutes": 52,
    "fastest_execution_minutes": 35,
    "slowest_execution_minutes": 78,
    "quality_improvement": 0.12
  },

  "similar_procedures": [
    {"id": 98, "name": "pr_review_process", "similarity": 0.78},
    {"id": 105, "name": "quality_check", "similarity": 0.65}
  ],

  "steps_summary": [
    {"step": 1, "name": "Checkout code", "type": "sequential"},
    {"step": 2, "name": "Run tests", "type": "sequential"},
    {"step": 3, "name": "Check coverage", "type": "conditional"},
    {"step": 4, "name": "Review style", "type": "sequential"}
  ],

  "recommendations": [
    "Parallelize steps 5-7 for 20% faster execution",
    "Add automation for step 3 (currently manual)",
    "Consider merging with procedure #98 (78% similar)",
    "Document edge case from execution #19"
  ],

  "note": "Call adapter.get_detail('procedural', 'procedure', 142) for full procedure details"
}
```

## Procedure Types

1. **Sequential**: Steps execute in order (task → next → final)
2. **Conditional**: Steps include if/else decision points
3. **Decision-Tree**: Multiple parallel branches
4. **Parallel-Compatible**: Some steps can execute concurrently
5. **Adaptive**: Adjusts steps based on inputs or previous execution

## Token Efficiency
Old: 100K tokens | New: <300 tokens | **Savings: 99%**

## Examples

### Basic Procedure Creation

```python
# Discover available procedure operations
adapter.list_operations_in_layer("procedural")
# Returns: ['extract', 'create', 'optimize', 'execute', 'analyze_effectiveness']

# Extract and create procedure from completed work
result = adapter.execute_operation(
    "procedural",
    "extract",
    {
        "task_id": 42,
        "extract_decisions": True,
        "analyze_parallel_potential": True
    }
)

# Analyze results
if result['applicability_analysis']['reuse_frequency'] > 0.7:
    print(f"High-value procedure: {result['procedure_name']}")
    print(f"Estimated savings: {result['applicability_analysis']['estimated_time_savings_minutes']} min/execution")

# Check recommendations
for rec in result['recommendations']:
    print(f"→ {rec}")
```

### Procedure Optimization

```python
# Get suggestions for existing procedure
result = adapter.execute_operation(
    "procedural",
    "optimize",
    {"procedure_id": 142}
)

# Results include parallelization opportunities
for rec in result['recommendations']:
    if 'Parallelize' in rec:
        print(f"Optimization opportunity: {rec}")
```

### Procedure Effectiveness Analysis

```python
# Analyze execution history
result = adapter.execute_operation(
    "procedural",
    "analyze_effectiveness",
    {"procedure_id": 142, "period_days": 30}
)

print(f"Success rate: {result['execution_history']['success_rate']:.1%}")
print(f"Avg duration: {result['effectiveness']['average_duration_minutes']} min")

# Find improvement opportunities
for rec in result['recommendations']:
    if 'automation' in rec.lower():
        print(f"Automation opportunity: {rec}")
```

### Merging Similar Procedures

```python
# Check for duplicate/similar procedures
result = adapter.execute_operation(
    "procedural",
    "find_similar",
    {"procedure_id": 142, "similarity_threshold": 0.7}
)

for similar in result['similar_procedures']:
    print(f"Similar: {similar['name']} (similarity: {similar['similarity']:.1%})")
    # Could merge them
```

## Implementation Notes

Demonstrates filesystem API paradigm for procedure learning and workflow automation. This skill:
- Discovers available procedure operations via filesystem
- Extracts procedures from completed multi-step work
- Analyzes effectiveness based on execution history
- Returns only summary metrics (procedure IDs, scores, recommendations)
- Supports drill-down for full procedure details via `adapter.get_detail()`
- Identifies parallelization and automation opportunities
- Learns best practices through repeated execution tracking
