# Discovery Event API

The Discovery Event API allows you to explicitly record discoveries, insights, findings, and analysis during sessions. These events are high-importance episodic events that trigger consolidation and are converted to semantic memories.

## Overview

**Purpose**: Capture significant analysis, findings, gaps, and patterns that should be learned and remembered.

**Key Features**:
- Higher importance than regular tool executions
- Trigger pattern extraction during consolidation
- Create semantic memories for future retrieval
- Support multiple discovery types

**Location**: `~/.claude/hooks/lib/discovery_recorder.py`

---

## Quick Start

### Python API

```python
from discovery_recorder import DiscoveryRecorder

recorder = DiscoveryRecorder()

# Record a discovery
event_id = recorder.record_discovery(
    project_id=2,  # Your project ID
    title="My Discovery",
    description="Detailed findings...",
    discovery_type="analysis",  # or: insight, gap, pattern
    impact_level="high"  # or: medium, low, critical
)

if event_id:
    print(f"Recorded discovery with ID: {event_id}")

recorder.close()
```

### Convenience Methods

```python
recorder = DiscoveryRecorder()

# Record analysis
recorder.record_analysis(
    project_id=2,
    analysis_title="Assessment Methodology Gap",
    findings="Feature-based vs operation-based counting yields 11% difference",
    impact="high"
)

# Record insight
recorder.record_insight(
    project_id=2,
    insight_title="Pattern Recognition",
    detail="Temporal clustering reveals 5-minute work cycles",
    impact="medium"
)

# Record discovered gap
recorder.record_gap(
    project_id=2,
    gap_title="Missing Consolidation Logic",
    description="Hooks fire but consolidation doesn't actually extract patterns",
    impact="critical"
)

# Record discovered pattern
recorder.record_pattern(
    project_id=2,
    pattern_title="Tool Execution Clustering",
    evidence="2,400+ tool executions cluster into 10 distinct temporal groups",
    impact="high"
)

recorder.close()
```

### Standalone Function

```python
from discovery_recorder import record_discovery

# One-shot recording
event_id = record_discovery(
    project_id=2,
    title="Session 7 Discovery",
    description="Assessment methodology gap found...",
    discovery_type="analysis",
    impact_level="high"
)
```

---

## Discovery Types

| Type | Use When | Example |
|------|----------|---------|
| **analysis** | Comparing two approaches, methodologies, or results | "Feature-based vs operation-based measurement comparison" |
| **insight** | Understanding a pattern or relationship | "Tool executions cluster in 5-minute cycles" |
| **gap** | Finding something missing or broken | "Consolidation doesn't extract actual patterns" |
| **pattern** | Identifying recurring sequences or structures | "10 distinct temporal clusters in event logs" |
| **finding** | Factual discovery or observation | "Database has 2,504 episodic events" |

---

## Impact Levels

| Level | When to Use | Effect on Consolidation |
|-------|------------|------------------------|
| **low** | Minor observations | Standard processing |
| **medium** | Important but not urgent | Prioritized for pattern extraction |
| **high** | Significant discovery | High priority for consolidation + semantic memory creation |
| **critical** | System-level findings | Triggers immediate consolidation if enabled |

---

## What Happens to Discoveries

### 1. Recording (Immediate)
```
record_discovery()
  → episodic_event created with type: "discovery:analysis"
  → importance_score: 0.8 (higher than regular events)
  → stored in database
```

### 2. Session End (Automatic)
```
SessionEnd hook fires
  → session-end.sh runs consolidation
  → ConsolidationHelper._identify_discoveries() finds all discovery: events
  → Extracts discovery metadata
```

### 3. Consolidation (Automatic)
```
Consolidation engine processes:
  → Clusters discovery events by type
  → Creates semantic memories for each discovery
  → Extracts patterns across discoveries
  → Records consolidation results
```

### 4. Next Session (Automatic)
```
SessionStart hook fires
  → Loads recent discoveries in working memory
  → Makes them available for context
  → Helps with subsequent tasks
```

---

## Examples

### Example 1: Recording a Bug Discovery

```python
from discovery_recorder import DiscoveryRecorder

recorder = DiscoveryRecorder()

recorder.record_gap(
    project_id=2,
    gap_title="Hooks Don't Capture Tool Context",
    description="""
    Discovered that post-tool-use.sh hook fires but receives no tool context from Claude Code.

    Evidence:
    - All recorded events show: Tool: unknown | Status: unknown
    - Environment variables TOOL_NAME, TOOL_STATUS not set by Claude Code

    Impact:
    - Tool execution tracking is meaningless
    - Can't identify which tools are used
    - Prevents effective learning and analysis

    Fix Required:
    - Claude Code must set env vars before hook invocation
    - Or: Provide tool context through hook parameters
    """,
    impact="high"
)

recorder.close()
```

### Example 2: Recording a Methodology Gap (Session 7)

```python
recorder.record_analysis(
    project_id=2,
    analysis_title="Assessment Methodology Gap",
    findings="""
    Session 6 reported: 78.1% completeness (feature-based counting)
    Session 7 found: 89.9% completeness (operation-based counting)
    Gap: 11.8% due to different measurement approaches

    Root Cause: Features are not granular operations.
    - Each feature may contain multiple operations
    - Operation-based measurement is more accurate

    Recommendation: Standardize on operation-based measurement.
    """,
    impact="high"
)
```

### Example 3: Recording a Pattern Discovery

```python
recorder.record_pattern(
    project_id=2,
    pattern_title="Temporal Clustering in Tool Execution",
    evidence="""
    Analysis of 2,457 tool execution events reveals:

    - 10 distinct temporal clusters
    - Cluster duration ranges from 3 to 236 minutes
    - Most clusters: 5-minute work cycles

    Pattern suggests:
    - Batch tool execution for related tasks
    - Natural workflow boundaries
    - Potential for procedure extraction
    """,
    impact="high"
)
```

---

## Integration with Hooks

The discovery system integrates with the automatic hook infrastructure:

### 1. Manual Recording (During Session)

```python
# In your code or a hook
from discovery_recorder import record_discovery

record_discovery(
    project_id=2,
    title="Something Important Discovered",
    description="...",
    discovery_type="analysis",
    impact_level="high"
)
```

### 2. Automatic Consolidation (Session End)

```bash
# Automatically runs in session-end.sh
python3
  consolidator = ConsolidationHelper()
  results = consolidator.consolidate_session(project_id)
  # Identifies all discoveries and extracts patterns
```

### 3. Context Injection (Next Session)

```bash
# Automatically runs in session-start.sh
bridge.get_active_memories(limit=7)
# Returns discoveries in top-7 working memory items
```

---

## Database Schema

Discovery events are stored in `episodic_events` with special handling:

```sql
INSERT INTO episodic_events (
    project_id,
    event_type,           -- "discovery:analysis", "discovery:gap", etc.
    content,              -- Full discovery details
    timestamp,            -- When discovered
    outcome,              -- impact_level: high, critical, etc.
    consolidation_status, -- "unconsolidated" → "consolidated"
    importance_score      -- 0.8 (higher than regular events)
)
```

---

## Querying Discoveries

```python
from discovery_recorder import DiscoveryRecorder

recorder = DiscoveryRecorder()

# Get discoveries from current session
discoveries = recorder.get_session_discoveries(
    project_id=2,
    session_id=None,  # None = current session
    limit=20
)

for d in discoveries:
    print(f"[{d['type']}] {d['content'][:100]}...")

recorder.close()
```

---

## Best Practices

### ✅ DO

- **Record discoveries immediately** while they're fresh
- **Be specific** about what you discovered and why it matters
- **Include evidence** (data, examples, comparisons)
- **Use appropriate types** (analysis, insight, gap, pattern)
- **Set impact level accurately** (helps with consolidation priority)

### ❌ DON'T

- Record tool executions here (use post-tool-use hook)
- Record generic observations without detail
- Mix multiple unrelated discoveries in one event
- Set impact="critical" for everything
- Forget to close the recorder

---

## Troubleshooting

### Issue: Discovery not recorded

```python
# Check project ID exists
from memory_bridge import MemoryBridge
bridge = MemoryBridge()
project = bridge.get_project_by_path("/home/user/.work/athena")
# Use project['id']
```

### Issue: Discovery not in consolidation results

```python
# Check that discovery was recorded
recorder.get_session_discoveries(project_id=2, limit=10)

# Check consolidation is running
# Should see discoveries in consolidation results:
# "discoveries_found": 1+
```

### Issue: Environmental variable issues

```python
# Set if missing
import os
os.environ["ATHENA_POSTGRES_HOST"] = "localhost"
os.environ["ATHENA_POSTGRES_DB"] = "athena"
```

---

## Future Enhancements

Potential improvements to discovery system:

1. **Automatic discovery detection** - Identify when code finds something new
2. **Discovery validation** - LLM-based assessment of discovery importance
3. **Cross-project discovery sharing** - Link discoveries across projects
4. **Discovery follow-up** - Track what was done with each discovery
5. **Discovery metrics** - Track how often discoveries lead to procedures

---

## See Also

- `consolidation_helper.py` - Pattern extraction and consolidation
- `memory_bridge.py` - Low-level database access
- `session-end.sh` - Hook that triggers consolidation
- `AUTOMATION_GAP_ROOT_CAUSE_ANALYSIS.md` - Investigation of discovery capture gap

---

**Created**: November 13, 2025
**Status**: Beta (core functionality working, enhancements planned)
**Version**: 1.0
