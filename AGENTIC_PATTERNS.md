# Agentic Patterns in Athena

## Overview

This document describes how Athena implements the **agentic loop** pattern from the Claude Agent SDK, making verification, remediation, and learning first-class architectural concerns.

The agentic loop has four phases:
1. **Gather Context** - Collect relevant information from multiple sources
2. **Take Action** - Execute operations with specialized agents
3. **Verify Output** - Run quality gates on results
4. **Learn & Improve** - Track outcomes and adjust behavior

## Architectural Layers

### 1. Verification Gateway (Layer 8.5: New)

**File**: `src/athena/verification/gateway.py`

Implements explicit quality gates that validate memory operations before commit:

```
Memory Operation
    ↓
┌─────────────────────────────┐
│   VerificationGateway       │
│                             │
│  ├─ GroundingGate          │ Verify: Is it grounded in source?
│  ├─ ConfidenceGate         │ Verify: Is confidence calibrated?
│  ├─ ConsistencyGate        │ Verify: Is it consistent with memory?
│  ├─ SoundnessGate          │ Verify: Is reasoning valid? (Q*)
│  ├─ MinimalityGate         │ Verify: Is it minimal/non-redundant?
│  ├─ CoherenceGate          │ Verify: Is it coherent with KG?
│  └─ EfficiencyGate         │ Verify: Is it performant?
│                             │
│  Result: GateResult         │ Pass/fail with violations
└─────────────────────────────┘
    ↓
Remediation (if failed) or Commit (if passed)
```

**Gate Types**:

| Gate | Purpose | Example Violation |
|------|---------|-------------------|
| Grounding | Source data coverage | Pattern based on <50% of cluster |
| Confidence | Calibration | 90% confidence with only 2 samples |
| Consistency | Memory alignment | Contradicts existing facts |
| Soundness | Valid reasoning | Missing Q* properties in plan |
| Minimality | No redundancy | Duplicated 20% of patterns |
| Coherence | Knowledge graph alignment | Orphaned entity (no relations) |
| Efficiency | Performance | Operation took 10s (target: 1s) |

**Usage Example**:

```python
from athena.verification import VerificationGateway

gateway = VerificationGateway()

# Verify a consolidation output
result = gateway.verify(
    operation_type="consolidate",
    operation_data={
        "grounding_score": 0.8,
        "confidence": 0.85,
        "consistency_score": 0.9,
        "verified_properties": ["optimality", "completeness"],
    }
)

if not result.passed:
    print(f"Violations: {result.violations}")
    print(f"Confidence adjusted to: {result.confidence_score}")
```

### 2. Observability Layer

**File**: `src/athena/verification/observability.py`

Tracks verification decisions and enables learning:

```
┌────────────────────────────────────┐
│   VerificationObserver              │
│                                    │
│  Decision Log:                     │
│  - What decisions were made?      │
│  - Why did they pass/fail?        │
│  - Were they correct in hindsight?│
│                                    │
│  Violation Patterns:               │
│  - Most common violations         │
│  - Root causes                    │
│  - Remediation effectiveness      │
│                                    │
│  Health Metrics:                  │
│  - Operation success rates        │
│  - Gate effectiveness             │
│  - Decision accuracy              │
└────────────────────────────────────┘
    ↓
Actionable Insights
```

**Key Insights Generated**:

- **Operation Health**: Which operations fail most often?
- **Gate Health**: Which gates are too strict/lenient?
- **Violation Patterns**: What issues keep recurring?
- **Decision Accuracy**: Are our decisions correct in hindsight?

**Usage Example**:

```python
from athena.verification import VerificationObserver

observer = VerificationObserver()

# Record decision
outcome = observer.record_decision(
    gate_result=result,
    action_taken="remediated",
)

# Later: record what actually happened
observer.record_outcome(
    decision_id=outcome.decision_id,
    actual_outcome="pattern successfully stored",
    was_correct=True,
    lessons=["Confidence adjustment worked well"]
)

# Get insights
for insight in observer.get_actionable_insights():
    print(insight)
```

### 3. Feedback Metrics Layer

**File**: `src/athena/verification/feedback_metrics.py`

Measures improvement in verification quality over time:

```
┌──────────────────────────────────┐
│  FeedbackMetricsCollector         │
│                                  │
│  Tracks:                         │
│  - Decision Accuracy (% correct) │
│  - Gate Pass Rate                │
│  - Remediation Effectiveness     │
│  - Operation Latency             │
│  - Violation Reduction           │
│                                  │
│  Trends:                         │
│  - Improving, Degrading, Flat  │
│  - Velocity of improvement      │
│  - Regression Risk              │
│                                  │
│  System Health Score: 0.0-1.0   │
└──────────────────────────────────┘
    ↓
Recommendations for improvement
```

**Key Metrics**:

| Metric | Target | Interpretation |
|--------|--------|-----------------|
| Decision Accuracy | >85% | % of decisions correct in hindsight |
| Gate Pass Rate | 70-80% | % of operations passing verification |
| Remediation Effectiveness | >75% | % of violations fixed successfully |
| Operation Latency | <1s | Time for core operations |
| Violation Reduction | Improving | Fewer violations over time |

**Usage Example**:

```python
from athena.verification import FeedbackMetricsCollector

metrics = FeedbackMetricsCollector()

# Record metrics
metrics.record_metric("decision_accuracy", 0.92)
metrics.record_metric("gate_pass_rate", 0.78)
metrics.record_metric("remediation_effectiveness", 0.85)

# Get health score
health = metrics.calculate_system_health_score()
print(f"System Health: {health:.0%}")

# Get recommendations
for rec in metrics.get_recommendations():
    print(rec)
```

### 4. SubAgent Orchestration

**File**: `src/athena/orchestration/subagent_orchestrator.py`

Executes complex operations using specialized agents in parallel:

```
Operation: "consolidate"
    ↓
┌─────────────────────────────────────────────────────┐
│  SubAgentOrchestrator                               │
│                                                     │
│  ┌──────────────────┐                              │
│  │ ClusteringAgent  │─────┐                        │
│  └──────────────────┘     │                        │
│                           ├─→ Feedback Coordination│
│  ┌──────────────────┐     │                        │
│  │ ExtractionAgent  │─────┤   (Results feed to    │
│  └──────────────────┘     │    dependent agents)   │
│                           │                        │
│  ┌──────────────────┐     │                        │
│  │ ValidationAgent  │─────┤                        │
│  └──────────────────┘     │                        │
│                           │                        │
│  ┌──────────────────┐     │                        │
│  │ IntegrationAgent │─────┘                        │
│  └──────────────────┘                              │
│                                                     │
│  Parallel Execution with Dependency Resolution    │
└─────────────────────────────────────────────────────┘
    ↓
Aggregated Results
```

**SubAgent Types**:

| Agent | Responsibility | Example |
|-------|-----------------|---------|
| Clustering | Event grouping | Temporal + semantic clustering |
| Extraction | Pattern discovery | Extract workflows from clusters |
| Validation | Quality checking | Verify patterns against source |
| Integration | Knowledge graph | Add patterns as entities/relations |
| Optimization | Performance | Cache results, parallelize |
| Remediation | Fix violations | Apply gate remediation handlers |
| Learning | Extract insights | Learn validation rules |
| Planning | Generate plans | Use Q* for planning |

**Usage Example**:

```python
from athena.orchestration import SubAgentOrchestrator, SubAgentType, SubAgentTask

orchestrator = SubAgentOrchestrator()

# Define tasks with dependencies
tasks = [
    SubAgentTask(
        task_id="cluster_events",
        agent_type=SubAgentType.CLUSTERING,
        operation_data={"events": events},
        priority=100,
    ),
    SubAgentTask(
        task_id="extract_patterns",
        agent_type=SubAgentType.EXTRACTION,
        operation_data={"events": events},
        dependencies=["cluster_events"],  # Runs after clustering
        priority=90,
    ),
]

# Execute in parallel with feedback coordination
results = await orchestrator.execute_parallel(tasks)

# Get insights
insights = orchestrator.get_orchestration_insights()
```

## Decision Flow by Layer

### Layer 1: Episodic Memory

**Decision**: Store event?

```
Incoming Event
    ↓
Verify:
  1. Grounding: Is context valid? (file path exists, CWD set)
  2. Confidence: >0.5 confidence required
  3. Efficiency: Store <10ms
    ↓
If passed: Store to SQLite
If failed: Log to decision log, potential retry with adjusted params
    ↓
Observe: Track event storage success rate
Metrics:  Record latency, confidence distribution
Learn:    Adjust file context validation rules
```

### Layer 2: Semantic Memory

**Decision**: Index search result?

```
Search Result (embedding + BM25)
    ↓
Verify:
  1. Consistency: Not contradicting existing knowledge?
  2. Coherence: Related to existing entities? (>0.6 KG coherence)
  3. Soundness: Retrieval valid (did retriever work correctly?)
    ↓
If passed: Index in semantic store + KG
If failed: Remediate via:
  - Update contradictory fact
  - Add missing KG relationships
  - Adjust embedding/BM25 weights
    ↓
Observe: Track false retrieval rate
Metrics:  Record search quality metrics
Learn:    Adjust rank weights for retriever
```

### Layer 3: Procedural Memory

**Decision**: Store extracted procedure?

```
Extracted Procedure (from pattern extraction)
    ↓
Verify:
  1. Grounding: ≥70% of steps appear in source events
  2. Minimality: Not a duplicate of existing procedure (redundancy <10%)
  3. Coherence: Logically connected steps (state transitions valid)
    ↓
If passed: Store as reusable procedure
If failed: Remediate via:
  - Merge with similar existing procedure
  - Re-run clustering with stricter constraints
    ↓
Observe: Track procedure reuse rate, effectiveness
Metrics:  Record extraction quality, reuse frequency
Learn:    Adjust extraction thresholds for better patterns
```

### Layer 4: Prospective Memory

**Decision**: Create task/goal?

```
Task/Goal Definition
    ↓
Verify:
  1. Soundness: Q* formal properties (optimality, completeness)
  2. Consistency: Not conflicting with active goals
  3. Efficiency: Feasible in estimated time?
    ↓
If passed: Store task + set up triggers
If failed: Remediate via:
  - Run scenario simulator (5 stress tests)
  - Adjust goal parameters
  - Flag for manual review
    ↓
Observe: Track goal completion rate, time accuracy
Metrics:  Record estimation error, deadline met %
Learn:    Improve time estimation, constraint detection
```

### Layer 5: Knowledge Graph

**Decision**: Add entity/relationship?

```
Entity or Relationship
    ↓
Verify:
  1. Grounding: Evidence in episodic store?
  2. Consistency: No conflicting relationships?
  3. Coherence: Connects to existing community? (prefer dense subgraphs)
    ↓
If passed: Add to KG, update indices
If failed: Remediate via:
  - Merge with existing entity (high similarity)
  - Flag for human review
  - Store as "candidate" with lower weight
    ↓
Observe: Track entity merge rate, community detection quality
Metrics:  Record KG growth, redundancy ratio
Learn:    Improve entity linking, relation extraction
```

### Layer 6: Meta-Memory

**Decision**: Update quality/expertise scores?

```
Quality/Expertise Update
    ↓
Verify:
  1. Consistency: Score change justified by evidence?
  2. Soundness: Evidence evaluation sound?
    ↓
If passed: Update meta-memory
If failed: Remediate via:
  - Revert to previous score
  - Manual expert review
    ↓
Observe: Track score calibration (vs actual performance)
Metrics:  Record quality metric stability
Learn:    Improve scoring functions, reduce noise
```

### Layer 7: Consolidation

**Decision**: Convert episodic → semantic?

```
Extracted Pattern
    ↓
Verify:
  1. Grounding: ≥50% of pattern in source events
  2. Hallucination Risk: <20% confidence loss after grounding
  3. Soundness: LLM validation if uncertainty >0.5
  4. Minimality: Not duplicate of existing semantic memory
    ↓
If passed: Store as semantic fact
If failed: Remediate via:
  - Adjust confidence downward
  - Cluster differently and retry
  - Mark for extended thinking validation
    ↓
Observe: Track consolidation accuracy (verify-learn cycle)
Metrics:  Record pattern quality, reuse rate
Learn:    Improve clustering, validation thresholds
```

### Layer 8: Planning

**Decision**: Accept generated plan?

```
Generated Plan
    ↓
Verify with Q* Formal Verification:
  1. Optimality: Is it optimal or near-optimal?
  2. Completeness: Does it cover all requirements?
  3. Consistency: No contradictory steps?
  4. Soundness: Valid reasoning chain?
  5. Minimality: No redundant steps?
    ↓
Run 5-scenario stress tests
  ↓
If all pass: Accept plan
If any fail: Remediate via:
  - Run adaptive replanning
  - Flag risky assumptions
  - Return alternative plans
    ↓
Observe: Track plan success rate vs estimates
Metrics:  Record plan quality, assumption accuracy
Learn:    Improve plan generation, assumption detection
```

## Feedback Loop Example: Complete Cycle

### Consolidation with Agentic Loop

**Step 1: Gather Context**
```
1. Collect recent episodes from episodic buffer
2. Search related semantic knowledge
3. Query KG for connected entities
4. Check meta-memory: are similar patterns already learned?
```

**Step 2: Take Action (SubAgents in Parallel)**
```
Clustering SubAgent:
  - Temporal clustering (events within 30min)
  - Semantic clustering (embedding similarity >0.8)
  → Output: 5 clusters of related events

Extraction SubAgent:
  - Extract patterns from each cluster
  - Check for workflows, decisions, facts
  → Output: 12 candidate patterns

Validation SubAgent:
  - Validate each pattern's grounding
  - Check for hallucinations
  → Output: Validation scores for each
```

**Step 3: Verify Output**
```
VerificationGateway.verify():
  ✓ Grounding: 8/12 pass (≥50% source events)
  ⚠ Confidence: 11/12 pass (one too confident with low samples)
  ✓ Consistency: All pass (no contradictions)
  ✓ Minimality: All pass (<10% redundancy)

Result: 11 pass, 1 needs remediation
Confidence adjusted: 0.78 → 0.72
```

**Step 4: Remediate & Learn**
```
Violation Handler (Confidence Gate):
  - Pattern: "Run tests after auth changes" (93% confident, 2 samples)
  - Action: Reduce confidence to 0.8 × 0.5 = 0.4
  - Flag: Mark for collection of more evidence

VerificationObserver.record_decision():
  - decision_id: "consolidate_20251110_001"
  - action_taken: "remediated"
  - violations: [ConfidenceGate violation]

FeedbackMetricsCollector.record_metric():
  - gate_pass_rate: 11/12 = 0.92
  - remediation_effectiveness: successful fix
  - confidence_adjustment_necessary: 1 instance
```

**Step 5: Commit & Monitor**
```
Store 11 patterns to semantic memory
Update knowledge graph with relationships
Record consolidation operation to episodic store

Next cycle:
  - Was the remediation correct? (confidence adjustment accurate?)
  - VerificationObserver.record_outcome()
  - FeedbackMetricsCollector updates trend for "decision_accuracy"
  - If pattern was correct: increase confidence in similar patterns
  - If pattern was wrong: adjust validation thresholds
```

## Integration Points

### With Existing Layers

1. **Verification Gateway** hooks into all store operations:
   ```python
   # In semantic/store.py (example)
   from athena.verification import VerificationGateway

   result = gateway.verify("semantic_store_fact", fact_data)
   if result.passed:
       self.db.store_semantic(fact)
   else:
       self._handle_violations(result)
   ```

2. **Observability** integrated into MCP tools:
   ```python
   # In mcp/handlers.py (example)
   observer.record_decision(gate_result, "accepted")
   # ... operation runs ...
   observer.record_outcome(decision_id, actual_outcome, was_correct)
   ```

3. **SubAgent Orchestrator** for complex operations:
   ```python
   # In consolidation/consolidator.py (example)
   results = await orchestrator.execute_operation(
       "consolidate",
       {"events": events},
       [SubAgentType.CLUSTERING, SubAgentType.EXTRACTION, SubAgentType.VALIDATION]
   )
   ```

4. **Feedback Metrics** for monitoring:
   ```python
   # In manager.py or monitoring.py (example)
   metrics.record_metric("gate_pass_rate", success_rate)
   metrics.record_metric("operation_latency_ms", elapsed_ms)
   ```

## Testing

### Unit Tests

```bash
# Test verification gates
pytest tests/unit/test_verification_gateway.py -v

# Test observability
pytest tests/unit/test_verification_observability.py -v

# Test metrics
pytest tests/unit/test_feedback_metrics.py -v

# Test orchestration
pytest tests/unit/test_subagent_orchestrator.py -v
```

### Integration Tests

```bash
# Test end-to-end agentic loop
pytest tests/integration/test_agentic_consolidation.py -v

# Test decision feedback loop
pytest tests/integration/test_decision_feedback_loop.py -v
```

## Performance Targets

| Component | Target | Current |
|-----------|--------|---------|
| Gate verification | <10ms | TBD (measure) |
| Observer recording | <1ms | TBD |
| Metrics collection | <1ms | TBD |
| SubAgent orchestration (4 parallel) | <500ms | TBD |
| **Complete agentic loop** | **<2s** | **TBD** |

## Future Enhancements

1. **Distributed Verification**: Run gates on separate processes
2. **Advanced Metrics**: ROC curves, calibration plots, performance profiles
3. **Policy Learning**: Learn optimal gate thresholds from data
4. **Proactive Remediation**: Automatically detect patterns needing revision
5. **Human-in-the-Loop**: Manual validation of high-value decisions

## References

- Claude Agent SDK: Agentic patterns (context gathering, action, verification)
- Chain-of-Thought brittleness: arXiv:2508.01191 (August 2025)
- Q* Formal Verification: Phase 6 planning system
- Dual-process reasoning: System 1 (fast) vs System 2 (LLM validation)

---

**Last Updated**: November 10, 2025
**Status**: Phase 8 - Agentic Patterns (Complete)
