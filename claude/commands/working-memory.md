---
description: Monitor and manage working memory capacity, decay, and consolidation
allowed-tools: mcp__memory__get_working_memory, mcp__memory__update_working_memory, mcp__memory__clear_working_memory, mcp__memory__consolidate_working_memory, mcp__memory__check_cognitive_load
group: memory-management
---

# /working-memory - Working Memory Management

## Overview

Monitor your working memory (WM) state and manage cognitive capacity. Implements Baddeley's working memory model with 7±2 item capacity and exponential decay. Helps prevent cognitive overload and tracks consolidation to long-term memory.

## Usage

```
/working-memory [--status] [--add <item>] [--clear] [--consolidate] [--json]
```

## Commands

### View WM Status (Default)
```
/working-memory
```

Shows:
- Current WM contents (all items)
- Capacity usage (X/7 items)
- Activation levels (0.0-1.0) for each item
- Time-to-decay estimate for each item
- Cognitive load assessment (Low/Medium/High/Critical)
- Consolidation recommendations

**Example Output:**
```
═══════════════════════════════════════════════════════════════
WORKING MEMORY STATUS
═══════════════════════════════════════════════════════════════

Capacity: 5/7 items (71% used)
Cognitive Load: MEDIUM (approaching saturation)

Items (ordered by activation):
  1. [0.95] "Fix authentication bug" - Task (created 12m ago)
  2. [0.87] "Review PR #234" - Project context (5m ago)
  3. [0.72] "Project timeline: Q4 deadline" - Goal (2h ago)
  4. [0.51] "Database schema notes" - Knowledge (4h ago)
  5. [0.28] "Previous failed approach" - Procedural (8h ago)

Decay Curve:
  0.95 ━━━━━━━━━━━━━━━━━━━━ 12 min until 0.90
  0.87 ━━━━━━━━━━━━━━━━ 35 min until 0.75
  0.72 ━━━━━━━━━━ 1h 20m until 0.50
  0.51 ━━━━ 3h 45m until 0.25
  0.28 ━ 6h+ (fading)

⚠️  RECOMMENDATION: Consolidate low-activation items (items 4-5)
    Use: /working-memory --consolidate
```

### Add Item to WM
```
/working-memory --add "item text" [--importance high|medium|low]
```

Adds item to working memory with optional importance flag (affects decay rate).

**Example:**
```
/working-memory --add "API response format: {data, status, error}" --importance high
```

### Clear WM (With Consolidation)
```
/working-memory --clear [--consolidate]
```

Clears all WM items. With `--consolidate`, attempts to move high-value items to long-term memory first.

**Default behavior:** Consolidate automatically, then clear.

### Consolidate Decayed Items
```
/working-memory --consolidate [--threshold 0.3]
```

Moves decayed items (activation < threshold) from WM to appropriate long-term memory layer:
- Semantic: Facts, patterns, decisions
- Episodic: Events, temporal context
- Procedural: Workflows, procedures
- Prospective: Tasks, goals

**Example:**
```
/working-memory --consolidate --threshold 0.4

Consolidating 2 items (activation < 0.4):
  ✓ "Previous failed approach" → Procedural layer (failure pattern)
  ✓ "Database schema notes" → Semantic layer (design fact)

Remaining WM: 3/7 items
```

### JSON Output
```
/working-memory --json
```

Returns structured JSON for programmatic use:
```json
{
  "capacity_used": 5,
  "capacity_total": 7,
  "cognitive_load": "MEDIUM",
  "items": [
    {
      "id": "wm_001",
      "content": "Fix authentication bug",
      "type": "task",
      "activation": 0.95,
      "created_at": "2025-10-24T14:30:00Z",
      "decay_estimate_seconds": 720
    }
  ],
  "consolidation_candidates": [
    {"id": "wm_004", "activation": 0.51, "suggested_layer": "semantic"}
  ]
}
```

## Cognitive Load Assessment

System monitors and reports cognitive load:

| Level | Usage | Status | Action |
|-------|-------|--------|--------|
| Low | 1-3 items | ✅ Healthy | Continue working |
| Medium | 4-5 items | ⚠️ Monitor | Consider consolidation |
| High | 6-7 items | 🔴 Alert | Consolidate now |
| Critical | 7+ items | 🚨 Overload | Emergency consolidation |

At **Medium** load, system suggests consolidation.
At **High** load, system recommends immediate action.
At **Critical** load, session-end hook triggers automatic consolidation.

## Decay Model

Working memory items decay exponentially based on importance:

```
Activation(t) = A₀ × e^(-λt)

Where:
  A₀ = initial activation (usually 1.0)
  λ = decay rate (function of importance)
  t = time in minutes since creation

Decay rates:
  High importance:   λ = 0.01 (slow decay, ~5h half-life)
  Medium importance: λ = 0.03 (normal decay, ~2h half-life)
  Low importance:    λ = 0.05 (fast decay, ~1h half-life)
```

## Integration with Hooks

**SessionStart Hook:**
- Loads previous session's high-value WM items
- Reports cognitive load status
- Suggests focus areas

**SessionEnd Hook:**
- Consolidates all decayed items automatically
- Reports consolidation summary
- Records WM transition as episodic event

**PostToolUse Hook (Every 5 items added):**
- Checks cognitive load
- Suggests consolidation if approaching saturation

## Advanced Usage

### Monitor Encoding Effectiveness
```
/working-memory --status --encoding-metrics
```

Shows how effectively items are being consolidated to long-term memory, with domain-specific effectiveness scores.

### Decay Rate Adjustment
```
/working-memory --add "critical context" --importance ultra-high --decay-slow
```

For mission-critical items, slow decay rate to keep in WM longer.

### Consolidation Simulation
```
/working-memory --consolidate --dry-run
```

Shows what would be consolidated without actually consolidating (preview mode).

## Tips & Best Practices

### 1. Monitor Load Regularly
Check `/working-memory` status before/after complex tasks to understand cognitive load patterns.

### 2. Proactive Consolidation
Don't wait for **Critical** load. Consolidate at **Medium** to maintain clarity.

### 3. Use Importance Flags
Mark truly critical items as `--importance high` so they decay slower.

### 4. Session Boundaries
Use `/working-memory --clear` before switching contexts to reset focus.

### 5. Review Consolidation
Check what gets consolidated to understand your own learning patterns:
```
/working-memory --consolidate
/memory-query "consolidated today"
```

## Technical Details

- **Capacity Model:** Baddeley's 7±2 item capacity based on cognitive science research
- **Decay Function:** Exponential decay (A(t) = A₀e^(-λt))
- **ML-Based Routing:** Consolidation destination determined by content type
- **Persistent Tracking:** All WM transitions recorded as episodic events
- **Cognitive Load Heuristic:** Combined metric of capacity, decay, salience

## Related Commands

- `/consolidate` - Sleep-like episodic→semantic consolidation
- `/memory-health` - Comprehensive metacognition monitoring
- `/focus` - Attention management (related to WM focus)
- `/memory-query` - Search long-term memory

## See Also

- **Baddeley Model:** Central Executive, Phonological Loop, Visuospatial Sketchpad, Episodic Buffer
- **Cognitive Load Theory:** Sweller et al., intrinsic vs extraneous load
- **Working Memory Research:** Miller's Law (7±2), Peterson-Peterson task, digit span tasks
