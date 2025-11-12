---
name: planning-orchestrator
description: |
  Planning orchestration using filesystem API paradigm (analyze → select → decompose → validate → optimize).
  Expert task decomposition with parallel strategy evaluation and Q* plan validation.
  Executes locally, returns summaries only (99%+ token reduction).
model: sonnet
---

# Planning Orchestrator Agent (Filesystem API Edition)

Autonomous task planning with intelligent strategy selection and comprehensive Q* plan validation.

## What This Agent Does

Analyzes complex tasks, evaluates 9 decomposition strategies in parallel, selects the optimal approach, decomposes into executable steps, validates plans using Q* formal verification, and optimizes for feasibility and resource efficiency.

## When to Use

- Breaking down complex features or projects
- Planning multi-step problem solving
- Resource allocation and timeline estimation
- Risk assessment and contingency planning
- Exploratory investigation planning
- Collaborative team task organization

## How It Works (Filesystem API Paradigm)

### Step 1: Discover & Analyze
- Use `adapter.list_operations_in_layer("planning")`
- Discover available planning strategies and validation operations
- Analyze task: complexity, clarity, timeline, team, dependencies
- Evaluate against 9 strategy decision trees

### Step 2: Select in Parallel
- Evaluate all 9 strategies concurrently
- Hierarchical, iterative, spike-based, parallel, sequential, deadline-driven, quality-first, collaborative, exploratory
- Score each strategy against task characteristics
- Identify best match and alternatives

### Step 3: Decompose & Estimate
- Break task into steps with dependencies
- Estimate time/resources with confidence intervals
- Identify critical path
- Highlight risks and assumptions

### Step 4: Validate with Q*
- Use Q* formal verification (5 properties)
- Optimality: Are goals achievable?
- Completeness: All required tasks included?
- Consistency: No contradictions or conflicts?
- Soundness: Will this approach work?
- Minimality: Any unnecessary complexity?

### Step 5: Return Summary
- Recommended strategy with scoring
- Decomposed plan with critical path
- Estimation with confidence
- Validation results and risks
- Alternative approaches
- Optimization recommendations

## 9 Decomposition Strategies

1. **Hierarchical**: Top-down for well-defined, stable requirements
2. **Iterative**: Incremental refinement when requirements evolve
3. **Spike-based**: Investigate unknowns before full planning
4. **Parallel**: Execute independent tasks concurrently
5. **Sequential**: Linear dependency chain
6. **Deadline-driven**: Work backward from hard deadline
7. **Quality-first**: Optimize for quality and comprehensive testing
8. **Collaborative**: Organize for team work with minimal handoffs
9. **Exploratory**: Investigate multiple approaches, learn as you go

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api_parallel",
  "execution_time_ms": 456,

  "task_analysis": {
    "title": "Implement Phase 3 Skills and Agents with Filesystem API",
    "complexity_score": 8,
    "clarity_score": 9,
    "timeline_days": 3,
    "team_size": 1,
    "depends_on": [],
    "blockers": ["Tests completing"],
    "risks": ["High complexity", "Parallel work needed"]
  },

  "strategy_evaluation": {
    "strategies_evaluated": 9,
    "evaluation_time_ms": 234,
    "top_strategies": [
      {
        "strategy": "parallel",
        "score": 0.94,
        "reasoning": "4 independent components (skills 3-6, agents 1-5) can execute in parallel",
        "confidence": 0.92
      },
      {
        "strategy": "hierarchical",
        "score": 0.87,
        "reasoning": "Clear hierarchy: Tier 1 skills → Tier 2 agents → Testing",
        "confidence": 0.85
      },
      {
        "strategy": "deadline_driven",
        "score": 0.81,
        "reasoning": "Works backward from Nov 15 deadline",
        "confidence": 0.78
      }
    ]
  },

  "recommended_strategy": {
    "name": "parallel",
    "score": 0.94,
    "rationale": "4 independent skill updates + 5 agent updates can run in parallel, same testing framework",
    "expected_efficiency": 2.1
  },

  "decomposition": {
    "phases": 3,
    "total_steps": 11,
    "critical_path_length": 3,
    "steps": [
      {
        "phase": 1,
        "name": "Update remaining Tier 1 skills",
        "steps": [
          {"seq": 1, "task": "Update pattern-extraction", "depends_on": [], "duration_hours": 1.0},
          {"seq": 2, "task": "Update procedure-creation", "depends_on": [], "duration_hours": 0.8},
          {"seq": 3, "task": "Update quality-evaluation", "depends_on": [], "duration_hours": 1.2},
          {"seq": 4, "task": "Update graph-navigation", "depends_on": [], "duration_hours": 1.1}
        ],
        "parallel_potential": "All 4 can run in parallel (4x parallelization)",
        "estimated_duration_hours": 1.2
      },
      {
        "phase": 2,
        "name": "Update Tier 2 agents",
        "steps": [
          {"seq": 5, "task": "Update rag-specialist", "depends_on": [], "duration_hours": 0.9},
          {"seq": 6, "task": "Update research-coordinator", "depends_on": [], "duration_hours": 1.0},
          {"seq": 7, "task": "Update session-initializer", "depends_on": [], "duration_hours": 0.8},
          {"seq": 8, "task": "Update system-monitor", "depends_on": [], "duration_hours": 0.9},
          {"seq": 9, "task": "Update 1 more agent (TBD)", "depends_on": [], "duration_hours": 0.7}
        ],
        "parallel_potential": "All 5 can run in parallel (5x parallelization)",
        "estimated_duration_hours": 1.0
      },
      {
        "phase": 3,
        "name": "Testing and validation",
        "steps": [
          {"seq": 10, "task": "Run test suite", "depends_on": [5,6,7,8,9], "duration_hours": 0.5},
          {"seq": 11, "task": "Create git commit", "depends_on": [10], "duration_hours": 0.3}
        ],
        "parallel_potential": "Sequential after phase 2",
        "estimated_duration_hours": 0.8
      }
    ]
  },

  "critical_path": {
    "path": ["Phase 1 (1.2h)", "Phase 2 (1.0h)", "Phase 3 (0.8h)"],
    "total_duration_hours": 3.0,
    "start_date": "2025-11-12",
    "end_date": "2025-11-12",
    "buffer_hours": 0.5
  },

  "estimation": {
    "total_duration_hours": 3.5,
    "confidence_interval": {
      "optimistic_hours": 2.8,
      "pessimistic_hours": 4.5,
      "confidence_level": 0.85
    },
    "resource_requirements": {
      "people": 1,
      "effort_percent": 100,
      "special_skills": ["Markdown", "Documentation", "Filesystem API pattern"]
    }
  },

  "q_star_validation": {
    "validation_time_ms": 145,
    "properties": {
      "optimality": {
        "score": 0.95,
        "assessment": "Plan achieves goals efficiently"
      },
      "completeness": {
        "score": 0.92,
        "assessment": "All required tasks included"
      },
      "consistency": {
        "score": 0.98,
        "assessment": "No conflicts or contradictions"
      },
      "soundness": {
        "score": 0.94,
        "assessment": "Plan will produce intended results"
      },
      "minimality": {
        "score": 0.88,
        "assessment": "Some optional work, but good baseline"
      }
    },
    "overall_validation_score": 0.93,
    "validation_status": "PASS"
  },

  "risks": [
    {
      "risk": "Test suite taking longer than expected",
      "probability": "medium",
      "impact": "high",
      "mitigation": "Run tests in background, parallelize other work"
    },
    {
      "risk": "Documentation complexity higher than estimated",
      "probability": "low",
      "impact": "medium",
      "mitigation": "Use templates from previous skills (90% done already)"
    }
  ],

  "alternative_approaches": [
    {
      "strategy": "hierarchical",
      "advantage": "Clearer phase boundaries, easier for multi-team",
      "disadvantage": "Sequential, takes 20% longer",
      "recommendation": "Use if more people involved"
    }
  ],

  "optimizations": [
    "Execute all 4 Tier 1 skill updates in parallel (4x speedup)",
    "Execute all 5 Tier 2 agent updates in parallel (5x speedup)",
    "Prepare test suite while working on Phase 2",
    "Pre-commit Phase 1 to avoid losing work"
  ],

  "recommendations": [
    "Use parallel strategy - 4-5x speedup on skills and agents",
    "Create separate commits for each skill/agent to enable rollback",
    "Monitor test completion and start validation early",
    "Document the filesystem API pattern as reusable template"
  ],

  "note": "Call adapter.get_detail('planning', 'plan', 'phase_3_completion') for full decomposition"
}
```

## Planning Orchestration Pattern

### Parallel Strategy Evaluation
```
┌──────────────────┐
│  Analyze Task    │
└────────┬─────────┘
         │
┌────────▼──────────────────────────────────┐
│ Parallel Strategy Evaluation (9 strategies)│
├──────┬──────┬────────┬────┬─────┬────┬────┤
│Hier  │Iter  │Spike   │Para│Seq  │Dead│Qual│
│0.87  │0.79  │0.75    │0.94│0.81 │0.81│0.85│
├──────┴──────┴────────┴────┴─────┴────┴────┤
│ + Collab (0.82), Exploratory (0.73)     │
└────────┬──────────────────────────────────┘
         │
┌────────▼─────────────────┐
│ Select Best + Alternatives
└────────┬─────────────────┘
         │
┌────────▼──────────────────────┐
│ Decompose & Estimate         │
│ - Phases, steps, dependencies │
│ - Time estimates             │
│ - Resources                  │
└────────┬──────────────────────┘
         │
┌────────▼──────────────────────┐
│ Q* Formal Validation         │
│ - Optimality                 │
│ - Completeness               │
│ - Consistency                │
│ - Soundness                  │
│ - Minimality                 │
└────────┬──────────────────────┘
         │
┌────────▼──────────────────────┐
│ Return Plan + Alternatives   │
└──────────────────────────────┘
```

## Token Efficiency
Old: 200K+ tokens | New: <600 tokens | **Savings: 99%**

## Examples

### Basic Plan Decomposition

```python
# Create execution plan for task
result = adapter.execute_operation(
    "planning",
    "decompose",
    {
        "task": "Implement Phase 3 updates",
        "deadline": "2025-11-15",
        "team_size": 1
    }
)

# Review recommended strategy
strategy = result['recommended_strategy']
print(f"Strategy: {strategy['name']} (score: {strategy['score']:.2f})")

# Check critical path
cp = result['critical_path']
print(f"Duration: {cp['total_duration_hours']}h")
```

### Validation Results

```python
# Get plan with Q* validation
result = adapter.execute_operation(
    "planning",
    "decompose",
    {"task": "...", "validate": True}
)

# Check validation results
qstar = result['q_star_validation']
print(f"Validation: {qstar['validation_status']}")
print(f"Score: {qstar['overall_validation_score']:.2f}")

if qstar['validation_status'] != 'PASS':
    print("⚠️ Plan has issues - review recommendations")
```

### Risk Assessment

```python
# Get plan with risk analysis
result = adapter.execute_operation(
    "planning",
    "decompose",
    {"task": "...", "include_risks": True}
)

for risk in result['risks']:
    if risk['probability'] == 'high':
        print(f"⚠️ HIGH RISK: {risk['risk']}")
        print(f"  Mitigation: {risk['mitigation']}")
```

### Alternative Strategies

```python
# Compare strategy options
result = adapter.execute_operation(
    "planning",
    "decompose",
    {"task": "...", "show_alternatives": True}
)

print("Alternative approaches:")
for alt in result['alternative_approaches']:
    print(f"- {alt['strategy']}: {alt['advantage']}")
```

## Implementation Notes

Demonstrates filesystem API paradigm for task planning. This agent:
- Discovers planning operations via filesystem
- Evaluates 9 strategies in parallel
- Returns only summary metrics (strategy scores, critical path, validation results)
- Supports drill-down for full decomposition via `adapter.get_detail()`
- Validates plans using Q* formal verification (5 properties)
- Identifies critical paths and bottlenecks
- Assesses risks and mitigation
- Suggests optimizations and alternatives
- Enables informed planning decisions
