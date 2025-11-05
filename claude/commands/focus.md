---
description: Manage working memory and attention focus (cognitive load, inhibition, salience)
group: Working Memory & Attention
aliases: ["/attention", "/wm", "/load"]
---

# /focus

Control cognitive attention, working memory, and focus mechanisms. Manage information salience and inhibition.

## Usage

```bash
/focus                        # Current focus state
/focus --load MEMORY_ID      # Load specific memory into focus
/focus --inhibit ID:duration # Suppress memory from retrieval
/focus --clear               # Clear working memory
```

## What It Controls

- **Working Memory Load** - See what's in active focus (7±2 items)
- **Item Activation** - Decay rates for items in working memory
- **Attention Focus** - Primary/secondary/background focus levels
- **Memory Inhibition** - Suppress distracting information
- **Salience Adjustment** - Novelty, contradiction, surprise weighting

## Example Output

```
CURRENT FOCUS STATE
═══════════════════════════════════════════

Working Memory (4/7 slots):

PRIMARY FOCUS:
  📍 JWT Token Implementation (Age: 2h, Activation: 0.98)
     Last accessed: 5 min ago
     Related tasks: 3 pending

SECONDARY FOCUS:
  📍 Database Schema (Age: 1h, Activation: 0.65)
     Linked to: JWT implementation

  📍 Testing Strategy (Age: 3h, Activation: 0.52)
     Referenced in: 4 memories

BACKGROUND:
  📍 OAuth2 Research (Age: 6h, Activation: 0.28)
     For later review

Attention System:
  • Novelty Weight: 0.6 (emphasize new info)
  • Surprise Weight: 0.8 (highlight unexpected)
  • Contradiction Weight: 0.9 (flag conflicts)

Inhibited (Suppressed):
  • None currently active
  • Last inhibition: 4h ago (cleared)

Cognitive Load:
  • Utilization: 57% (4/7)
  • Saturation: Low
  • Capacity: Comfortable
  • Next swap: ~30 min (estimated)

Recommendations:
  1. Load `database-schema` to primary focus
  2. Inhibit `oauth2` until needed (6+ hours)
  3. Add `error-handling` to secondary focus
  4. Clear oldest item when capacity reached
```

## Commands

```bash
# Load memory into focus
/focus --load ID:456
/focus --load "JWT implementation"

# Set focus level
/focus --primary ID:456      # Primary focus
/focus --secondary ID:456    # Secondary focus
/focus --background ID:456   # Background focus

# Inhibit (suppress) from retrieval
/focus --inhibit ID:456:1h   # Suppress for 1 hour
/focus --inhibit ID:456:selectively  # Suppress strategically

# Clear and reset
/focus --clear               # Clear all WM
/focus --refresh             # Refresh activation levels

# Adjust salience
/focus --novelty 0.7         # Weight for novelty
/focus --surprise 0.8        # Weight for surprise
/focus --contradiction 0.9   # Weight for contradictions
```

## Integration

Works with:
- `/memory-query` - Search and load found memories
- `/project-status` - Load project context
- `/task-create` - Focus on task details
- `/consolidate` - Clear WM before consolidation

## Related Tools

- `get_working_memory` - View WM contents
- `update_working_memory` - Add items
- `clear_working_memory` - Clear all
- `get_attention_state` - Attention metrics
- `set_attention_focus` - Set focus level
- `inhibit_memory` - Suppress items

## Cognitive Load Management

| Utilization | Status | Action |
|------------|--------|--------|
| <40% | Underutilized | Load more context |
| 40-70% | Optimal | Maintain current focus |
| 70-90% | High | Prepare to offload |
| >90% | Saturation | Clear or inhibit items |

## Tips

1. Keep primary focus on current task
2. Use secondary focus for related context
3. Inhibit distracting information
4. Refresh every 30-60 min for long sessions
5. Clear before consolidation runs

## See Also

- `/memory-query` - Find items to load
- `/project-status` - Load project context
- `/memory-health` - Monitor cognitive load
