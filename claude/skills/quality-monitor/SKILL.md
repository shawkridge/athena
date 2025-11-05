---
category: skill
description: Continuously monitor memory quality and suggest improvements
trigger: Runs periodically or on major memory operations
confidence: 0.90
---

# Quality Monitor Skill

Monitors memory health in real-time and suggests improvements proactively.

## When I Invoke This

I detect:
- After consolidation completion
- After major memory operations
- On-demand with `/memory-health --detail`
- Periodically (every 24h)

## What I Do

```
1. Evaluate quality
   → Call: evaluate_memory_quality()
   → Measure: Accuracy, false positives, consistency
   → Compare: Against targets
   → Identify: Degradations

2. Check cognitive load
   → Call: check_cognitive_load()
   → Track: Working memory saturation
   → Predict: When capacity reached
   → Recommend: When to clear

3. Get learning rates
   → Call: get_learning_rates()
   → Measure: Encoding effectiveness
   → Identify: Best strategies
   → Recommend: Improvements

4. Get metacognition
   → Call: get_metacognition_insights()
   → Analyze: Overall system health
   → Identify: Patterns in performance
   → Suggest: Adjustments
```

## MCP Tools Used

- `evaluate_memory_quality` - Quality metrics
- `check_cognitive_load` - Capacity monitoring
- `get_learning_rates` - Learning effectiveness
- `get_metacognition_insights` - System assessment
- `record_execution` - Track monitoring

## Example Invocation

```
Quality Monitor running continuous check...

Memory Quality Status: 91/100 ✓ EXCELLENT
  • Accuracy: 94% (target: >90%) ✓
  • False Positives: 2% (target: <5%) ✓
  • Consistency: 91% (target: >85%) ✓

Cognitive Load: 4/7 slots (57%) ✓ HEALTHY
  • Working memory: Comfortable capacity
  • Decay rate: Normal
  • Next prediction: Capacity in ~4 hours

Learning Effectiveness: 0.87/1.0 (GOOD)
  • Best strategy: Episodic + semantic (0.95)
  • Moderate: Procedural learning (0.81)
  • Needs work: Ad-hoc memorization (0.62)
  → Recommendation: Use episodic approach for new learning

Overall Assessment:
  ✓ System healthy
  ✓ Quality targets met
  ✓ Learning effective
  ⚠ Monitor cognitive load (approaching capacity in 4h)
  → Recommendation: Consider consolidation when reaching 70%
```

## Success Criteria

✓ Quality metrics tracked
✓ Deviations detected early
✓ Improvements recommended
✓ System health maintained

## Related Commands

- `/memory-health` - Full health report
- `/focus` - Manage cognitive load
- `/consolidate` - Address quality issues

