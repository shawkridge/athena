---
name: learning-tracker
description: Track encoding effectiveness and identify optimal learning strategies
triggers: SessionEnd, PostToolUse
category: learning
enabled: true
---

# Skill: Learning Tracker

Track encoding effectiveness, confidence calibration, and learning curves per domain. Identify which strategies work best.

## How It Works

**SessionEnd**: Collect events, group by domain, calculate metrics
**PostToolUse**: Tag events, track success/failure, update running stats

## Metrics Per Domain

- Encoding rate (retained / encountered)
- Retrieval success rate  
- Confidence accuracy
- Learning curve type (exponential/logarithmic/linear)
- Optimal strategy
- Time to mastery estimate

## Algorithm

```
encoding_rate = consolidated_memories / total_encountered

confidence_calibration = |predicted_confidence - actual_success|

learning_curve = f(time, exposures, consolidations)

strategy_effectiveness = success_rate per strategy
```

## Configuration

```
ANALYSIS_WINDOW: 30 days (rolling)
MIN_SAMPLES: 10 events
CONFIDENCE_METHOD: Brier score
DOMAIN_AUTO_DETECT: true
```

## Integration

- Works with: `/learning` command
- Feeds into: `learning-monitor` agent
- Tracks: Learning history

## See Also
- `/learning` command
- Spacing effect research
- Confidence calibration theory
