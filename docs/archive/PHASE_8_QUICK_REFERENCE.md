# Phase 8: Quick Reference Guide

## The Four New Systems

### 1. VerificationGateway
```python
from athena.verification import VerificationGateway, GateType

gateway = VerificationGateway()

# Verify an operation
result = gateway.verify(
    operation_type="consolidate",
    operation_data={
        "grounding_score": 0.8,
        "confidence": 0.85,
        "consistency_score": 0.9,
        "base_confidence": 0.7,
    }
)

print(f"Passed: {result.passed}")
print(f"Confidence: {result.confidence_score:.2%}")
print(f"Violations: {len(result.violations)}")

# Register custom remediation handler
def remediate_confidence_violation(violation, data):
    data["confidence"] *= 0.8  # Reduce by 20%
    return data

gateway.register_remediation_handler(GateType.CONFIDENCE, remediate_confidence_violation)

# Apply remediation
if not result.passed:
    remediated_data = gateway.apply_remediation(result, data)
```

**7 Gate Types**:
- Grounding: Source coverage
- Confidence: Calibration
- Consistency: No contradictions
- Soundness: Valid reasoning (Q*)
- Minimality: No redundancy
- Coherence: KG connected
- Efficiency: Performance

---

### 2. VerificationObserver
```python
from athena.verification import VerificationObserver

observer = VerificationObserver()

# Record a decision
outcome = observer.record_decision(
    gate_result=result,
    action_taken="remediated"
)

# Later: record the outcome
observer.record_outcome(
    decision_id=outcome.decision_id,
    actual_outcome="pattern stored successfully",
    was_correct=True,
    lessons=["Confidence adjustment was correct"]
)

# Get insights
for insight in observer.get_actionable_insights():
    print(insight)

# Get operation health
health = observer.get_operation_health("consolidate")
print(f"Pass rate: {health['pass_rate']:.0%}")
print(f"Accuracy: {health['accuracy']:.0%}")

# Get decision history
history = observer.get_decision_history(limit=10)
```

**Provides**:
- Decision tracking (pass/fail, violations, remediation)
- Outcome recording (was decision correct?)
- Recurring violation patterns
- Operation health metrics
- Gate effectiveness analysis

---

### 3. FeedbackMetricsCollector
```python
from athena.verification import FeedbackMetricsCollector

metrics = FeedbackMetricsCollector(window_hours=24)

# Record metrics
metrics.record_metric("decision_accuracy", 0.92)
metrics.record_metric("gate_pass_rate", 0.78)
metrics.record_metric("remediation_effectiveness", 0.85)
metrics.record_metric("operation_latency_ms", 250)

# Get trends
trend = metrics.get_metric_trend("decision_accuracy")
print(f"Mean: {trend.mean:.2%}")
print(f"Trend: {trend.trend}")  # "improving", "degrading", "flat"
print(f"Improvement rate: {trend.trend_magnitude:.0%}")

# Get health score
health = metrics.calculate_system_health_score()
print(f"System Health: {health:.0%}")

# Detect issues
anomalies = metrics.get_anomalies(sigma_threshold=2.0)
alerts = metrics.get_metric_alerts()

# Get recommendations
for rec in metrics.get_recommendations():
    print(rec)

# Export report
report = metrics.export_metrics_report()
```

**Tracks**:
- Decision Accuracy (% correct in hindsight)
- Gate Pass Rate (% passing verification)
- Remediation Effectiveness (% violations fixed)
- Operation Latency (performance)
- Violation Reduction (declining)

**Detects**:
- Regressions (degrading metrics)
- Anomalies (outliers)
- Performance issues

---

### 4. SubAgentOrchestrator
```python
from athena.orchestration import (
    SubAgentOrchestrator,
    SubAgentTask,
    SubAgentType
)
import asyncio

async def main():
    orchestrator = SubAgentOrchestrator()

    # Define tasks with dependencies
    tasks = [
        SubAgentTask(
            task_id="cluster_1",
            agent_type=SubAgentType.CLUSTERING,
            operation_data={"events": events},
            priority=100,
        ),
        SubAgentTask(
            task_id="extract_1",
            agent_type=SubAgentType.EXTRACTION,
            operation_data={"events": events},
            dependencies=["cluster_1"],  # Runs after clustering
            priority=90,
        ),
        SubAgentTask(
            task_id="validate_1",
            agent_type=SubAgentType.VALIDATION,
            operation_data={"patterns": patterns},
            dependencies=["extract_1"],
            priority=80,
        ),
    ]

    # Execute with dependency resolution and feedback coordination
    results = await orchestrator.execute_parallel(tasks)

    # Check results
    for task_id, result in results.items():
        print(f"{task_id}: {result.status.value}")
        if result.is_success():
            print(f"  Output: {result.output}")

    # Get insights
    insights = orchestrator.get_orchestration_insights()
    print(f"Coordination effectiveness: {insights['coordination_effectiveness']:.0%}")

asyncio.run(main())
```

**SubAgent Types**:
- Clustering: Event grouping (temporal + semantic)
- Validation: Quality checking
- Extraction: Pattern discovery
- Integration: Knowledge graph integration
- Optimization: Performance
- Remediation: Fixing violations
- Learning: Extracting insights
- Planning: Generating plans

---

## Integration Examples

### In Consolidation
```python
from athena.consolidation import ConsolidationSystem
from athena.verification import VerificationGateway, VerificationObserver
from athena.orchestration import SubAgentOrchestrator

class EnhancedConsolidationSystem:
    def __init__(self):
        self.consolidator = ConsolidationSystem()
        self.gateway = VerificationGateway()
        self.observer = VerificationObserver()
        self.orchestrator = SubAgentOrchestrator()

    async def consolidate_with_agentic_loop(self, events):
        # 1. Gather Context (existing)
        # 2. Take Action with SubAgents
        results = await self.orchestrator.execute_operation(
            "consolidate",
            {"events": events},
            subagent_types=[CLUSTERING, EXTRACTION, VALIDATION]
        )

        # 3. Verify Output
        patterns = results["subagent_results"]["extraction"]
        result = self.gateway.verify("consolidate", {
            "patterns": patterns,
            "grounding_score": 0.8,
            "confidence": 0.85,
        })

        # 4. Remediate if needed
        if not result.passed:
            patterns = self.gateway.apply_remediation(result, patterns)

        # 5. Commit
        for pattern in patterns:
            self.consolidator.store_pattern(pattern)

        # 6. Record & Learn
        outcome = self.observer.record_decision(result, "committed")
        # Later: observer.record_outcome(outcome.decision_id, ...)
```

---

## Common Patterns

### Pattern 1: Gate + Remediate + Record
```python
result = gateway.verify(operation_type, data)
if not result.passed:
    data = gateway.apply_remediation(result, data)
observer.record_decision(result, "remediated" if not result.passed else "accepted")
```

### Pattern 2: Track Metric Over Time
```python
metrics.record_metric("gate_pass_rate", success_count / total_count)
trend = metrics.get_metric_trend("gate_pass_rate")
if trend.trend == "degrading":
    alerts.append(f"Gate pass rate degrading: {trend.trend_magnitude:.0%}")
```

### Pattern 3: Parallel with Feedback
```python
tasks = [clustering_task, extraction_task, validation_task]
# extraction_task depends on clustering
# validation_task depends on extraction
results = await orchestrator.execute_parallel(tasks)
# Feedback coordination automatically handled
```

### Pattern 4: Decision Feedback Loop
```python
# Decision phase
outcome = observer.record_decision(gate_result, "remediated")

# Execution phase
try:
    pattern = store_pattern(remediated_data)
    success = True
except Exception as e:
    success = False

# Feedback phase
observer.record_outcome(
    outcome.decision_id,
    f"pattern_stored" if success else "error",
    success
)
```

---

## Monitoring Checklist

### Daily Checks
- [ ] System health score >0.8?
- [ ] Gate pass rate stable (70-80%)?
- [ ] Any anomalies in metrics?
- [ ] Recent decision accuracy >85%?

### Weekly Checks
- [ ] Are metrics improving or degrading?
- [ ] Any recurring violation patterns?
- [ ] Operation latency within targets?
- [ ] Recommendations being addressed?

### Monthly Checks
- [ ] Update gate thresholds based on trends?
- [ ] Retire low-effectiveness gates?
- [ ] Analyze root causes of failures?
- [ ] Update documentation?

---

## Troubleshooting

### Gate Failing Too Often
1. Check which gate: `result.violations[0].gate_type`
2. Look at violation details: `violation.details`
3. Loosen threshold: `gateway.gates[gate_type].threshold = new_value`
4. Or: add better remediation handler

### Decision Accuracy Low (<80%)
1. Get recent decisions: `observer.get_decision_history(limit=20)`
2. Find false decisions: `[d for d in history if d.was_correct == False]`
3. Analyze patterns: Why were these wrong?
4. Adjust relevant gates or validation rules

### Metrics Anomalies
1. Check anomalies: `metrics.get_anomalies(sigma_threshold=2.0)`
2. Time-correlate with events: When did it spike?
3. Get alerts: `metrics.get_metric_alerts()`
4. Investigate root cause, adjust if needed

### SubAgent Slow
1. Check individual agent times: `results[task_id].execution_time_ms`
2. Profile the _do_work() method
3. Check dependencies: Is it blocked on prerequisites?
4. Consider timeout adjustment: `SubAgentTask.timeout_seconds`

---

## Performance Tips

1. **Batch Operations**: Group multiple items before verification
2. **Cache Gate Results**: Same data shouldn't be verified twice
3. **Async SubAgents**: Use parallel execution for independent tasks
4. **Tune Thresholds**: Start strict, gradually relax as confidence builds
5. **Monitor Baselines**: Record performance before/after changes

---

## API Quick Reference

### VerificationGateway
```
verify()              - Run gates on operation data
apply_remediation()   - Fix violations
register_remediation_handler() - Custom violation handling
get_gate_health()     - Gate success rates
get_decision_insights() - Recent decisions
```

### VerificationObserver
```
record_decision()     - Log verification decision
record_outcome()      - Log actual outcome
get_operation_health() - Success rates by operation
get_gate_health()     - Success rates by gate
get_top_violation_patterns() - Most common issues
get_actionable_insights() - Recommended actions
get_decision_history() - Recent decisions
```

### FeedbackMetricsCollector
```
record_metric()       - Log metric value
get_metric_trend()    - Analyze trend (improving/degrading)
calculate_system_health_score() - Overall 0.0-1.0 score
get_anomalies()       - Outlier detection
get_metric_alerts()   - Issues to address
get_recommendations() - Improvement suggestions
export_metrics_report() - Full telemetry export
```

### SubAgentOrchestrator
```
execute_parallel()    - Run tasks with dependency resolution
execute_operation()   - Run operation with subagents
register_agent()      - Register custom subagent
get_orchestration_insights() - Coordination metrics
```

---

## Next Steps

1. **Write Unit Tests**: ~50 tests total for new modules
2. **Integration Testing**: End-to-end agentic loop
3. **Manager Integration**: Inject gateways into manager.py
4. **MCP Tools**: Expose features via `/memory-verify`, `/memory-health-detailed`, etc.
5. **Policy Learning**: Learn optimal thresholds from data

---

**Created**: November 10, 2025
**Version**: 1.0
**Status**: Ready for use
