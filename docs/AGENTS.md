# Athena Autonomous Agents

**Status**: ✅ Implemented and tested
**Version**: 1.0
**Last Updated**: November 17, 2025

---

## Overview

Athena now includes two specialized **autonomous agents** that proactively manage memory without requiring explicit user requests. These agents complement the existing Claude Code skills by adding autonomous intelligence to the memory system.

### What Are Agents?

**Agents** are unlike skills:
- **Skills** (user-initiated): User asks "What happened?" → Agent invokes skill → Retrieve data
- **Agents** (autonomous): Agent observes work → Agent decides → Agent stores memory

Agents make the system **proactive** instead of purely reactive.

---

## The Two Agents

### 1. Memory Coordinator Agent

**Purpose**: Autonomously decide what's worth remembering during sessions

**Where It Runs**: Active throughout every session

**What It Does**:
1. **Observes** work happening (tool executions, user actions, errors)
2. **Decides** if information is worth storing
3. **Classifies** the information (episodic, semantic, or procedural)
4. **Stores** in appropriate memory layer

**Decision Logic**:
- **Novelty Check**: Is this new information or already stored?
- **Importance Assessment**: Will this matter in future sessions?
- **Memory Type Selection**: Where should it go?
  - **Episodic**: Events, errors, what happened when
  - **Semantic**: Facts, knowledge, insights learned
  - **Procedural**: Workflows, processes, repeatable steps

**Example Decisions**:
```python
# Input: User completes important task
{
    "content": "Completed API caching optimization",
    "type": "completion",
    "importance": 0.9
}
# Decision: Store as semantic memory (reusable knowledge)

# Input: Database error occurs
{
    "content": "Connection timeout after 30 seconds",
    "type": "error",
    "importance": 0.7
}
# Decision: Store as episodic memory (learn what happened)

# Input: Short noise
{
    "content": "x",
    "type": "noise",
    "importance": 0.1
}
# Decision: Skip (not worth storing)
```

**Token Cost**: ~600 tokens definition + ~50 tokens per decision
**ROI**: Positive after ~3 memory operations/session

---

### 2. Pattern Extractor Agent

**Purpose**: Autonomously extract learnable patterns from session events

**Where It Runs**: At session end (SessionEnd hook)

**What It Does**:
1. **Retrieves** recent episodic events
2. **Analyzes** them for repeated sequences
3. **Extracts** workflows as procedures
4. **Stores** learned patterns in procedural memory
5. **Tracks** extraction quality and metrics

**Extraction Logic**:
- **Clustering**: Group similar events by type/tools
- **Pattern Detection**: Find sequences that repeat (confidence-based)
- **Procedure Extraction**: Convert clusters to reusable procedures
- **Quality Filtering**: Only store high-confidence patterns (default: 0.8+)

**Example Extraction**:
```
Recent events:
  - Edit file X
  - Run test suite
  - Check results
  - Deploy to staging
  - Run smoke tests

Cluster analysis:
  - Pattern found: "test + deploy flow"
  - Confidence: 0.85
  - Repetitions: 3 times this session

Result:
  - Extract as procedure: "Testing and Deployment Workflow"
  - Store in procedural memory
  - Next session: Can reuse this workflow
```

**Token Cost**: 0 tokens in-session + ~200 tokens per extraction at session end
**ROI**: Very high (each pattern saves 1000+ tokens in future sessions)

---

## How Agents Relate to Skills

### Complementary Design

| Aspect | Skill | Agent |
|--------|-------|-------|
| **Trigger** | User request / context hint | Time-based or event-based |
| **Example** | "What did we do?" | Observes work, auto-stores |
| **Control** | User-initiated | Autonomous |
| **Visibility** | Clear to user | Background |
| **Use Case** | Retrieval ("show me X") | Storage & learning ("learn from Y") |

### In Practice

```
Session Flow:
  1. User works (coding, research, etc.)
  2. Memory Coordinator Agent (background):
     - Observes important moments
     - Decides what to remember
     - Stores automatically
  3. User asks "What happened?"
     - Claude invokes athena-episodic SKILL
     - Gets back both explicit + auto-remembered events
  4. Session ends
     - Pattern Extractor Agent runs
     - Analyzes events from session
     - Extracts 1-3 reusable procedures
     - Stores in procedural memory
  5. Next session
     - User can use athena-procedural SKILL
     - Lists procedures (including auto-extracted ones)
```

---

## Using the Agents

### Direct Usage (Python)

```python
from athena.agents import (
    get_coordinator,
    get_extractor,
    coordinate_memory_storage,
    run_consolidation,
)
import asyncio

async def example():
    # Use Memory Coordinator
    coordinator = get_coordinator()
    memory_type = await coordinator.coordinate_storage({
        "content": "Important learning about caching patterns",
        "type": "learning",
        "importance": 0.9
    })
    # Returns: "semantic" (stored as fact)

    # Run Pattern Extractor at session end
    result = await run_consolidation()
    # Returns: consolidation report with patterns extracted
```

### Automatic Integration (Hooks)

The agents are automatically integrated into Claude Code's hook system:

**During Session**:
```bash
# ~/.claude/hooks/post-tool-use.sh
# After each tool execution, Memory Coordinator Agent is invoked
# Decides if result is worth storing
```

**Session End**:
```bash
# ~/.claude/hooks/session-end.sh
# Pattern Extractor Agent runs
# Consolidates learning from the session
```

---

## Agent Statistics

Both agents track their own metrics:

```python
coordinator = get_coordinator()
stats = coordinator.get_statistics()
# {
#   "decisions_made": 42,
#   "memories_stored": 34,
#   "skipped": 8
# }

extractor = get_extractor()
stats = extractor.get_statistics()
# {
#   "patterns_extracted": 5,
#   "consolidation_runs": 3,
#   "last_run": "2025-11-17T11:32:52.184104"
# }
```

---

## Configuration

### Memory Coordinator Settings

**Minimum Importance Threshold**:
```python
# Default: 0.5
# Events with importance < 0.5 are skipped
# Errors (type="error") always stored regardless of importance
```

**Memory Type Classification**:
Current heuristics (can be extended):
- Errors → episodic
- Learning/insight → semantic
- Workflow → procedural
- Default → episodic

**Novelty Detection**:
Current: All information treated as novel
Future: Query semantic memory to detect duplicates

### Pattern Extractor Settings

**Minimum Confidence**:
```python
# Default: 0.8
# Only patterns with confidence >= 0.8 are stored
# Prevents false patterns from low-quality clustering
```

**Minimum Repetitions**:
```python
# Default: 2 occurrences
# Need at least 2 repetitions to extract pattern
```

---

## Implementation Status

### Completed ✅
- Memory Coordinator Agent implementation
- Pattern Extractor Agent implementation
- Agent initialization and singleton pattern
- Basic decision logic and classification
- Statistics tracking
- Unit tests

### Future Enhancements
- Novelty detection via semantic memory querying
- Cross-session pattern learning (patterns from prior sessions)
- Agent tuning based on user feedback
- Machine learning for decision refinement
- Temporal pattern extraction (finding cyclic patterns)
- Priority-based memory filtering

---

## Design Principles

### 1. Proactive but Transparent

**Agents act autonomously, but decisions are observable**:
- Statistics available: `agent.get_statistics()`
- Decisions logged at INFO level
- User can see what's being stored via memory skills

### 2. Conservative Storage

**When in doubt, don't store**:
- Minimum importance threshold (0.5 default)
- Minimum confidence threshold (0.8 for patterns)
- Skip noise and duplicates
- Better to miss something than to clutter memory

### 3. Complementary to Skills

**Agents enhance, don't replace skills**:
- Skills: User-initiated memory access (retrieval)
- Agents: Autonomous memory management (storage/learning)
- Together: Complete memory ecosystem

### 4. Token Efficient

**Follows Anthropic's 99.2% efficiency paradigm**:
- Agents use direct Python imports (no protocol overhead)
- Operations stay local (no round-trips)
- Results summarized (300 tokens max)

---

## Example Workflow

### Scenario: Completing a Complex Task

```
1. User works on feature implementation (30 minutes)

2. Throughout session:
   - Memory Coordinator observes:
     - "User debugged database query"
     - "Found optimal indexing strategy"
     - "Error: Connection pool exhausted"
   - Stores automatically:
     - Episodic: Error event (learn what happened)
     - Semantic: Indexing strategy (learn knowledge)
     - Episodic: Feature completion (track progress)

3. User asks "What did I do today?"
   - Claude invokes athena-episodic skill
   - Gets 15 events (both explicit hook + auto-stored)
   - Much richer memory than hooks alone

4. Session ends (SessionEnd hook fires)
   - Pattern Extractor analyzes 25 events
   - Identifies: "Database optimization workflow"
   - Confidence: 0.82 (repeats 3x this session)
   - Extracts as procedure: "Optimize DB Indexes"
   - Stores in procedural memory

5. Next session
   - User works on different project
   - athena-procedural skill is available
   - Lists procedures: "Optimize DB Indexes" available
   - User can reuse learned workflow
   - Saves 20+ minutes of rediscovery
```

---

## Monitoring & Health

### Agent Health Checks

```python
# Check agent activity
coordinator = get_coordinator()
stats = coordinator.get_statistics()

if stats["decisions_made"] == 0:
    print("⚠️ Coordinator idle (no decisions made)")

if stats["skipped"] > stats["memories_stored"]:
    print("⚠️ Coordinator skipping too much (tune importance threshold)")

# Check pattern extraction
extractor = get_extractor()
stats = extractor.get_statistics()

if stats["consolidation_runs"] > 0 and stats["patterns_extracted"] == 0:
    print("⚠️ Extractor running but finding no patterns")
```

---

## Future Work

### Phase 2: Agent Enhancement

1. **Semantic Novelty Detection**
   - Query semantic memory before storing
   - Avoid duplicate knowledge
   - Learn "what we already know"

2. **User Feedback Loop**
   - Rate agent decisions: "This was worth remembering" / "This was noise"
   - Fine-tune thresholds based on feedback
   - Personalize to user's preferences

3. **Cross-Session Learning**
   - Detect patterns across multiple sessions
   - "You usually debug for 30 minutes per session"
   - "You typically refactor after feature completion"

4. **Advanced Clustering**
   - Temporal clustering (events near each other)
   - Semantic clustering (similar content)
   - Tool-based clustering (similar tools used)

### Phase 3: Agent Expansion

1. **Knowledge Curator Agent**
   - Automatically build knowledge graph
   - Connect related facts and entities
   - Identify topic communities

2. **Task Tracker Agent**
   - Monitor task completion
   - Surface overdue items
   - Suggest prioritization

3. **Quality Optimizer Agent**
   - Monitor memory quality metrics
   - Recommend consolidation
   - Identify memory fragmentation

---

## Troubleshooting

### Memory Coordinator Not Storing Anything

**Check**:
- Importance threshold: `coordinator.importance_threshold`
- Decisions made: `coordinator.get_statistics()["decisions_made"]`
- Actual decisions: Enable DEBUG logging

**Solution**:
- Lower importance threshold if too conservative
- Check if events are being observed correctly

### Pattern Extractor Not Finding Patterns

**Check**:
- Events in episodic memory: `await recall_recent(limit=50)`
- Clustering: Are events being grouped?
- Confidence threshold: Default 0.8 (may be too high)

**Solution**:
- Lower confidence threshold to 0.7
- Ensure events are similar enough for clustering
- Check event metadata (type, tools, etc.)

---

## References

- **Architecture**: See `/home/user/.work/athena/docs/PARADIGM.md` for overall design
- **Skills**: See `/home/user/.claude/skills/memory-management/` for user-initiated memory access
- **Operations**: See `src/athena/[layer]/operations.py` for underlying memory functions
- **Consolidation**: See `src/athena/consolidation/` for pattern extraction details

---

**Next Steps**:
- Monitor agent decisions in real sessions
- Collect feedback on what's worth remembering
- Refine thresholds based on usage patterns
- Expand agents with semantic novelty detection

