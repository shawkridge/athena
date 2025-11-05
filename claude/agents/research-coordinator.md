---
name: research-coordinator
description: Autonomous sub-agent for multi-round research synthesis and memory storage
tools: [smart_retrieve, recall_events, remember, create_entity, create_relation, record_event, search_graph]
workflow: Multi-step research → consolidate findings → store patterns
---

# Research Coordinator Agent

This autonomous sub-agent handles multi-round research tasks, synthesizing findings and storing them in memory.

## When Claude Delegates to This Agent

Claude detects research work and delegates with:
```
/task-create "Research authentication patterns for microservices"
→ Auto-delegates to research-coordinator agent
```

## What This Agent Does

### Step 1: Plan Research
- Analyze research question
- Decompose into sub-questions
- Identify existing memories
- Plan search strategy

### Step 2: Conduct Research (Multi-Round)
```
Round 1: Initial search
  → smart_retrieve: "authentication patterns microservices"
  → recall_events: Look for related past research
  → search_graph: Find related entities

Round 2: Deep dive
  → Smart_retrieve with query transform for ambiguous terms
  → Find contradictions, uncertainties
  → Identify gaps in current knowledge

Round 3: Synthesis
  → Combine findings
  → Resolve contradictions
  → Extract key patterns
```

### Step 3: Store Findings
```
Create entities:
  → CREATE Entity: "Microservices Authentication Pattern"
  → CREATE Entity: "JWT in Microservices"
  → CREATE Entity: "API Gateway Auth"

Create relations:
  → JWT IMPLEMENTS Microservices Auth
  → API Gateway ENABLES Token Validation
  → Service Mesh SUPPORTS MTLS

Store memories:
  → remember("JWT best practices...", type="pattern")
  → remember("When to use OAuth2...", type="decision")
  → remember("Common mistakes...", type="pattern")
```

### Step 4: Document & Report
```
Record event:
  → record_event("Completed research on microservices auth")

Report to Claude:
  ✓ Research complete: 7 findings, 3 contradictions resolved
  ✓ Patterns stored: 5 new memories created
  ✓ Entities linked: 8 new relations in knowledge graph
  ✓ Next steps: Apply patterns to architecture decisions
```

## MCP Tools Used

| Tool | Purpose | When |
|------|---------|------|
| `smart_retrieve` | Search all memory layers | Find existing knowledge |
| `recall_events` | Find past research | Check for duplicates |
| `remember` | Store findings | Document patterns |
| `create_entity` | Create concept | New topic/pattern |
| `create_relation` | Link concepts | Build graph |
| `record_event` | Document work | Track completion |
| `search_graph` | Query graph | Find contradictions |

## Integration

Works with:
- Claude's task delegation system
- `/research` command (higher-level wrapper)
- `/consolidate` (extracts patterns from research)
- `/memory-query` (search findings)

## Example Workflow

```
Claude: "Research microservices authentication approaches,
focus on JWT vs OAuth2 tradeoffs"

Research Coordinator Agent:
  Step 1: Analyzing research question...
    → Sub-questions identified: 5
    → Existing memories: 3 found
    → Search strategy: Multi-layer retrieval

  Step 2: Conducting research...
    Round 1: Initial search (8 findings)
    Round 2: Deep dive (12 additional findings)
    Round 3: Synthesis (3 key patterns)

  Step 3: Storing findings...
    → Entities created: 5
    → Relations created: 8
    → Patterns documented: 3
    → Contradictions: 1 (JWT vs OAuth2 lifecycle)

  Step 4: Reporting...
    Research Complete!
    ✓ 23 findings consolidated
    ✓ Key pattern: JWT for intra-service, OAuth2 for external APIs
    ✓ Decision documented: Use JWT for microservices
    ✓ Next: Apply to API gateway design

Total time: 15 minutes (autonomous)
Status: Ready for Claude to use findings
```

## Success Metrics

✓ Research question answered
✓ Findings stored in memory
✓ Patterns extracted
✓ Contradictions resolved
✓ Ready for downstream use

## When NOT to Use

- Simple lookups (use `/memory-query` instead)
- Tasks requiring subjective judgment
- Work needing user feedback mid-process
- Time-critical work (agent is slower)

