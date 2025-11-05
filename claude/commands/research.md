---
description: Multi-source research with autonomous agent orchestration and memory storage
allowed-tools: mcp__memory__task, Task
group: research
---

# /research - Autonomous Multi-Source Research

Execute comprehensive research across authoritative sources with autonomous agent orchestration and automatic memory storage.

## Usage

```
/research "<topic>" [--task-id <id>]
```

**Arguments:**
- `topic` (required): Research question or topic (e.g., "agentic coding patterns", "RAG optimization")
- `--task-id` (optional): Check status of existing research task

**Examples:**
```
/research "agentic coding task management"
/research "LLM memory architectures"
/research "RAG evaluation frameworks"
/research --task-id 42  # Check status of task 42
```

## How It Works

### Step 1: Create Research Task
```
mcp__memory__task(operation="create", topic="<your topic>")
→ Returns: Task ID (e.g., 1)
→ Status: RUNNING
```

### Step 2: Autonomous Research Execution (Background)
The research-coordinator agent is automatically invoked:
- **Parallel agent deployment** - 8 specialized researchers execute simultaneously:
  - arxiv-researcher (Academic papers, 1.0x credibility)
  - anthropic-docs-researcher (Official docs, 0.95x)
  - github-researcher (Open source, 0.85x)
  - paperswithcode-researcher (Implementations, 0.90x)
  - techblogs-researcher (Company research, 0.88x)
  - hackernews-researcher (Community insights, 0.70x)
  - medium-researcher (Technical essays, 0.68x)
  - x-researcher (Emerging trends, 0.62x)

- **Finding extraction** - Each agent:
  - Searches its source (WebFetch or WebSearch)
  - Extracts findings with title, summary, URL
  - Scores credibility based on source + relevance
  - Records to research_findings table

- **Finding storage** - Automatically:
  - Stores findings in semantic memory with embeddings
  - Links to knowledge graph entities
  - Creates episodic event with progress
  - Aggregates statistics (entity/relation counts)

### Step 3: Check Progress
```
mcp__memory__task(operation="get_status", task_id=<id>)
→ Shows: Task status, findings count, agent progress breakdown
```

### Step 4: Retrieve Findings
```
mcp__memory__research_findings(operation="get", task_id=<id>)
→ Returns: Top 10 findings sorted by credibility
→ Shows: Source, title, credibility score, URL
```

## Architecture

### Research Task Model
- **ID**: Unique task identifier
- **Topic**: Research question
- **Status**: PENDING → RUNNING → COMPLETED/FAILED
- **Timestamps**: created_at, started_at, completed_at
- **Statistics**: findings_count, entities_created, relations_created
- **Agent Results**: Per-agent breakdown {agent_name: finding_count}

### Finding Model
- **Source**: arXiv, GitHub, Anthropic Docs, etc.
- **Title**: Finding title
- **Summary**: Brief finding description
- **URL**: Direct link to source
- **Credibility Score**: 0.0-1.0 (source_credibility × relevance)
- **Memory Status**: Tracks if stored to semantic memory

### Agent Progress Tracking
- **Agent Name**: Researcher name
- **Status**: PENDING → RUNNING → COMPLETED/FAILED/SKIPPED
- **Findings Count**: Incremented as agent discovers findings
- **Timestamps**: started_at, completed_at
- **Error Messages**: Captured if agent fails

## Integration with Memory System

### Automatic Memory Storage
Each finding is automatically:
1. **Embedded** - Vectorized using Ollama embeddings (nomic-embed-text)
2. **Stored** - Inserted into semantic memory with credibility score
3. **Linked** - Connected to knowledge graph entities
4. **Indexed** - Made searchable via `/memory-query`

### Cross-Memory Integration
- **Semantic Layer**: Findings indexed for search
- **Episodic Layer**: Research events recorded (agent completion, finding counts)
- **Knowledge Graph**: Entities extracted from findings, relations created
- **Meta-Memory**: Domain coverage updated (expertise in research topic)

### Query Later
```
/memory-query "agentic coding patterns"
→ Returns: All research findings with credibility scores
→ Sorted: By relevance to query, then by credibility

/memory-query --type findings --source "arXiv"
→ Returns: Only academic paper findings from this research
```

## Quality Assurance

### Credibility Scoring
- **Base score**: Source credibility (0.5-1.0)
- **Multiplied by**: Finding relevance to query (0.0-1.0)
- **Boosted by**: Cross-validation (±0.15 if ≥2 sources agree)
- **Final**: source_credibility × relevance × cross_validation

### Deduplication
- Semantic similarity detection (cosine >0.85)
- Automatic merging of duplicate findings
- Highest credibility version preserved

### Validation
- All agent errors logged and reported
- Timeout protection (agent fails gracefully)
- Fallback sources if primary agent fails

## Progress Tracking

Real-time status visible via:
```
mcp__memory__task(operation="get_status", task_id=<id>)

Output:
✓ Research Task Status (ID: 1)
Topic: agentic coding task management
Status: RUNNING
Findings: 23
Entities Created: 5
Relations Created: 8

Agent Progress:
  ✓ arxiv-researcher: completed (8 findings)
  🔄 github-researcher: running (4 findings)
  ⏳ anthropic-docs-researcher: pending
  ✓ paperswithcode-researcher: completed (6 findings)
  ...
```

## Performance

- **Parallel execution**: All agents run simultaneously (~20-90 seconds)
- **Per-agent performance**: 8-20 findings per agent typical
- **Total findings**: 100-300+ per research task
- **Memory storage**: ~100-300ms per finding (async)
- **Query latency**: <100ms once stored in semantic memory

## Error Handling

- **Agent timeout**: Marked FAILED, other agents continue
- **Invalid topic**: Returns error immediately
- **Storage failure**: Finding recorded locally, can retry
- **Graceful degradation**: Missing source doesn't block research

## Advanced Usage

### Monitor Multiple Researches
```
mcp__memory__task(operation="list")
→ Shows: Last 10 research tasks
→ Status icons: ✓ COMPLETED, 🔄 RUNNING, ⏳ PENDING
```

### Filter Findings by Source
```
mcp__memory__research_findings(operation="list_by_source", task_id=1, source="GitHub")
→ Returns: Only GitHub findings for this research
```

### Summary View
```
mcp__memory__research_findings(operation="summary", task_id=1)
→ Shows:
  - Total findings: 47
  - By source: arXiv (8), GitHub (6), etc.
  - Avg credibility: 0.82
  - Entities/relations created
```

## Under the Hood

### Database Tables
- `research_tasks` - Task metadata + statistics
- `research_findings` - Individual findings with scores
- `agent_progress` - Per-agent execution tracking

### MCP Tools
- `mcp__memory__task` - Create/status/list research tasks
- `mcp__memory__research_findings` - Query findings with filters

### Async Processing
- Research execution runs in background
- Findings stored incrementally as agents complete
- Status updates reflect real-time progress

### Consolidation
- Research findings consolidated to semantic memory
- Episodic events recorded for timeline
- Knowledge graph updated with extracted entities
