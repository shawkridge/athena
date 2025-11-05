---
name: wm-monitor
description: Monitor working memory capacity and prevent cognitive overload
triggers: SessionStart, PostToolUse, UserPromptSubmit
category: cognitive-management
enabled: true
---

# Skill: WM Monitor

Monitor working memory (7±2 capacity) and prevent overload. Alerts user and triggers auto-consolidation when saturation approaches.

## How It Works

**SessionStart**: Load WM state, report capacity
**PostToolUse** (every 5 items): Check capacity, alert if High/Critical
**UserPromptSubmit**: Quick WM check, report if overloaded

## Cognitive Load Levels

- Low (1-3 items): ✅ Continue
- Medium (4-5 items): ⚠️ Monitor  
- High (6-7 items): 🔴 Alert
- Critical (7+ items): 🚨 Emergency consolidation

## Configuration

```
CHECK_INTERVAL: 5 WM items
ALERT_THRESHOLD: 60% capacity
CRITICAL_THRESHOLD: 85% capacity
AUTO_CONSOLIDATE_AT_CRITICAL: true
```

## Performance

- Per-check: <5ms
- Memory overhead: <1MB

## Integration

- Works with: `/working-memory` command
- Tracks: Episodic events (load patterns)

## See Also
- `/working-memory` command
- Baddeley's working memory model
