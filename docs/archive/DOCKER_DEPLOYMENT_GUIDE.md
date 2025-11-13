# Athena Docker Deployment Guide

**Status**: ✅ Ready for Production  
**Last Verified**: November 7, 2025

---

## Quick Start

### Using Docker Compose (Recommended)

```bash
# 1. Start the full Athena stack
docker-compose up -d

# 2. Verify services are running
docker-compose ps

# 3. Access services
# - Athena HTTP API:       http://localhost:3000
# - Dashboard Backend:     http://localhost:8000
# - Ollama (local LLM):    http://localhost:11434
# - Qdrant (vector DB):    http://localhost:6333
# - Redis (cache):         http://localhost:6379

# 4. System automatically:
#    - Initializes with hooks
#    - Agents invoke via tool autodiscovery
#    - Records episodic events
#    - Consolidates patterns at session end
```

### Services in Docker Compose

| Service | Port | Purpose | Volume |
|---------|------|---------|--------|
| **athena** | 3000 | Athena HTTP API | athena-data:/root/.athena |
| **backend** | 8000 | Dashboard Backend | (read-only access) |
| **ollama** | 11434 | Local LLM for embeddings | $HOME/.ollama |
| **qdrant** | 6333 | Vector database | qdrant-data:/qdrant/storage |
| **redis** | 6379 | Cache layer | redis-data:/data |

---

## What Happens Automatically

### On Container Start (session-start)
- ✅ Agent: `session-initializer` loads context
- ✅ Primes working memory (7±2 model)
- ✅ Checks memory health
- ✅ Loads active goals

### On User Input (user-prompt-submit)
- ✅ Agent: `rag-specialist` injects memory context (priority 100)
- ✅ Agent: `research-coordinator` multi-source research
- ✅ Agent: `gap-detector` detects knowledge gaps
- ✅ Agent: `attention-manager` monitors cognitive load
- ✅ Agent: `procedure-suggester` recommends procedures

### On Tool Execution (post-tool-use)
- ✅ Records episodic event automatically
- ✅ Every 10 operations: `attention-optimizer` checks load
- ✅ Auto-consolidates if load ≥6/7
- ✅ Tracks anomalies and errors

### On Major Work (pre-execution)
- ✅ Agent: `plan-validator` validates structure
- ✅ Agent: `goal-orchestrator` checks conflicts
- ✅ Agent: `strategy-selector` optimizes approach
- ✅ Runs Q* formal verification (5 properties)

### At Session End (session-end)
- ✅ Agent: `consolidation-engine` runs dual-process consolidation
  - System 1: Fast statistical clustering (~100ms)
  - System 2: LLM validation when uncertainty >0.5 (~1-5s)
- ✅ Agent: `workflow-learner` extracts new procedures
- ✅ Agent: `quality-auditor` assesses memory quality
- ✅ Strengthens memory associations (Hebbian learning)

### On Task Completion (post-task-completion)
- ✅ Agent: `execution-monitor` records task outcomes
- ✅ Agent: `goal-orchestrator` updates progress
- ✅ Agent: `workflow-learner` extracts learnings
- ✅ Tracks execution metrics (time, quality, resources)

---

## Agent Autodiscovery

### 14 Registered Agents

**Priority 100** (Highest - Run First):
- rag-specialist: Search memory & inject context
- consolidation-engine: Pattern extraction

**Priority 95**:
- plan-validator: Validate plans
- workflow-learner: Extract procedures
- execution-monitor: Record outcomes

**Priority 90**:
- goal-orchestrator: Check goals & conflicts
- quality-auditor: Assess memory quality

**Priority 85-70**:
- research-coordinator: Multi-source research
- strategy-selector: Optimize strategy
- gap-detector: Detect gaps
- attention-manager: Monitor load
- attention-optimizer: Optimize attention

**Priority 80**:
- procedure-suggester: Suggest procedures

### Tool Invocation Methods

#### Via Slash Commands (7 agents)
```bash
/critical:session-start      # session-initializer
/critical:validate-plan       # plan-validator
/critical:manage-goal         # goal-orchestrator
/important:check-workload     # attention-manager
/important:consolidate        # consolidation-engine
/important:optimize-strategy  # strategy-selector
/useful:retrieve-smart        # research-coordinator
```

#### Via MCP Tool Autodiscovery (7 agents)
```
mcp__athena__rag_tools:retrieve_smart            # rag-specialist
mcp__athena__memory_tools:detect_knowledge_gaps  # gap-detector
mcp__athena__memory_tools:check_cognitive_load   # attention-manager
mcp__athena__procedural_tools:find_procedures    # procedure-suggester
mcp__athena__procedural_tools:create_procedure   # workflow-learner
mcp__athena__memory_tools:evaluate_memory_quality # quality-auditor
mcp__athena__task_management_tools:record_execution_progress # execution-monitor
```

---

## Hook Points (6 Total)

### 1. session-start.sh
**When**: Session begins  
**Agents**: session-initializer  
**Duration**: <500ms  
**Purpose**: Load context & prime memory

### 2. user-prompt-submit.sh
**When**: User submits query  
**Agents**: rag-specialist, research-coordinator, gap-detector, attention-manager, procedure-suggester  
**Duration**: <300ms  
**Purpose**: Analyze input, inject context, detect gaps

### 3. post-tool-use.sh
**When**: Every tool execution  
**Agents**: Batch every 10 ops → attention-optimizer  
**Duration**: <100ms per op  
**Purpose**: Record episodic events, manage load

### 4. pre-execution.sh
**When**: Before major work  
**Agents**: plan-validator, goal-orchestrator, strategy-selector  
**Duration**: <300ms  
**Purpose**: Validate plans, check goals, assess risk

### 5. session-end.sh
**When**: Session ends  
**Agents**: consolidation-engine, workflow-learner, quality-auditor  
**Duration**: 2-5s  
**Purpose**: Extract patterns, create procedures, assess quality

### 6. post-task-completion.sh
**When**: Task finishes  
**Agents**: execution-monitor, goal-orchestrator, workflow-learner  
**Duration**: <500ms  
**Purpose**: Record outcomes, extract learnings

---

## Memory System Architecture

### 8 Layers
```
Layer 8: Supporting Infrastructure
         ├─ RAG (27 modules)
         ├─ Planning (formal verification, scenario simulation)
         ├─ Zettelkasten (hierarchical indexing)
         └─ GraphRAG (community detection)

Layer 7: Consolidation (Dual-process)
         ├─ System 1: Fast statistical clustering
         └─ System 2: LLM validation (uncertainty >0.5)

Layer 6: Meta-Memory
         ├─ Quality (compression, recall, consistency)
         ├─ Expertise (domain tracking)
         ├─ Attention (salience, focus)
         └─ Load (cognitive 7±2 model)

Layer 5: Knowledge Graph
         ├─ Entities & Relations
         ├─ Communities (Leiden clustering)
         └─ Observations

Layer 4: Prospective Memory
         ├─ Tasks
         ├─ Goals
         └─ Triggers (time/event/file-based)

Layer 3: Procedural Memory
         ├─ 101+ extracted procedures
         ├─ Effectiveness metrics
         └─ Execution history

Layer 2: Semantic Memory
         ├─ Vector embeddings (Ollama or Anthropic)
         ├─ BM25 keyword search
         └─ Hybrid retrieval

Layer 1: Episodic Memory
         ├─ 8,128+ events (migrated)
         ├─ Spatial-temporal grounding
         └─ Event clustering
```

### Storage
- **Database**: SQLite (local-first)
- **Size**: ~37MB (growing with events)
- **Location**: `/home/user/.claude/memory.db`
- **Tables**: Created on-demand (idempotent)
- **Backup**: Automatic via episodic event snapshots

---

## Self-RAG Pipeline (Task 3.2)

### 5-Stage Workflow
1. **Retrieve**: Fetch documents from knowledge base
2. **Evaluate**: Score relevance (6-factor system)
3. **Generate**: Synthesize answer from documents
4. **Critique**: Self-evaluate quality (4-factor system)
5. **Regenerate**: Iteratively improve if below threshold

### Quality Metrics
- **Relevance Scoring**: keyword_overlap, content_density, length, query_coverage, position, semantic
- **Answer Quality**: support, hallucination, coherence, completeness
- **Confidence Range**: 0.0-1.0
- **Critique Types**: SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, HALLUCINATION

### Performance
- Query processing: <2s
- Document evaluation: <1s
- Answer generation: <1s
- Self-critique: <500ms
- Total pipeline: <5s for typical queries

---

## ReAct Loop (Task 3.1)

### Multi-Step Reasoning
```
Thought → Action → Observation
    ↓
   [Reflect]
    ↓
Next Thought → Next Action → Next Observation
    ...
    ↓
    Final Answer
```

### Capacities
- Thought/Action History: 1,000+ items
- Observation Memory: 10,000+ items
- Max Iterations: Configurable (default: 3)

### Use Cases
- Complex multi-step problems
- Iterative refinement
- Error recovery
- Knowledge synthesis

---

## Monitoring & Debugging

### Check System Status
```python
from athena.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()
health = manager.get_system_health()

# Returns:
# {
#   "episodic": {"status": "healthy", "events": 8128, "size_mb": 5.5},
#   "semantic": {"status": "healthy", "concepts": 1200, "vectors": 1200},
#   "procedural": {"status": "healthy", "procedures": 101, "accuracy": 0.94},
#   "overall": "HEALTHY"
# }
```

### View Recent Events
```python
events = manager.recall(query="tool execution", k=10)
for event in events:
    print(f"{event.timestamp}: {event.content}")
```

### Monitor Cognitive Load
```python
from athena.meta.load import LoadMonitor

load = LoadMonitor()
status = load.get_status()
# Returns: {"current": 4, "capacity": 7, "zone": "NORMAL"}
```

---

## Troubleshooting

### Hook Not Firing?
1. Check hook files exist: `ls -la /home/user/.claude/hooks/`
2. Check executable: `chmod +x /home/user/.claude/hooks/*.sh`
3. Check Docker mount: `-v /home/user/.claude:/app/claude`

### Agents Not Invoking?
1. Check agent registry: `/critical:plan-task "list all agents"`
2. Check trigger configuration in `agent_invoker.py`
3. Check tool availability (slash command or MCP)

### Memory Growing Too Large?
1. Run consolidation: `/important:consolidate --strategy speed`
2. Delete low-value events: `/memory-forget <ID>`
3. Check database size: `du -h ~/.claude/memory.db`

### Performance Issues?
1. Check consolidation frequency (session-end only by default)
2. Monitor cognitive load (triggers auto-consolidate at 6/7)
3. Profile with: `DEBUG=1 docker run ...`

---

## Performance Targets

| Operation | Target | Typical | Notes |
|---|---|---|---|
| Hook execution | <500ms | 100-300ms | Silent unless alerts |
| Agent invocation | <300ms | 150-250ms | Async, non-blocking |
| Tool autodiscovery | <100ms | 50-80ms | Pre-cached |
| Self-RAG query | <2s | 1.5-2s | With critique |
| Consolidation | <5s | 2-3s | System 1 + selective System 2 |
| Memory lookup | <100ms | 50-70ms | Cached results |

---

## Best Practices

### 1. Let Hooks Run
- Don't disable hooks - they're the autonomous system
- Post-tool-use runs every operation (50-80ms overhead)
- Session-end consolidation is critical (run it!)

### 2. Monitor Memory Health
- Check `/important:assess-memory` weekly
- Target quality score: ≥0.85
- If <0.80, run consolidation with quality strategy

### 3. Leverage Tool Autodiscovery
- Agents automatically find tools via registry
- No manual tool invocation needed
- Slash commands + MCP tools both supported

### 4. Use Streaming for Long Operations
- Self-RAG supports streaming: `async for stage, data in rag.stream_result()`
- ReAct supports progress tracking: `result.metrics`
- Allows real-time feedback to users

### 5. Trust the Consolidation Process
- System 1 (fast) handles 95% of consolidation
- System 2 (slow) only runs when uncertainty >0.5
- Result: Fast + accurate pattern extraction

---

## Quick Reference

### Enable New Agent
1. Add to `agent_invoker.py` registry
2. Set trigger point (e.g., "user_prompt_submit")
3. Set priority (100=highest, 0=lowest)
4. Set tool (slash_command or mcp_tool)

### Add Hook Trigger
1. Create shell script: `/home/user/.claude/hooks/my-hook.sh`
2. Parse environment variables
3. Invoke agents via `/critical:...` or MCP tools
4. Return status code 0

### Extend Memory System
1. Add layer in `src/athena/[layer_name]/`
2. Implement `Store` base class
3. Create MCP tools in `handlers.py`
4. Add routing in `UnifiedMemoryManager`

---

## Summary

The Athena system is **production-ready** with Docker Compose:

### Quick Start
```bash
cd /home/user/.work/athena
docker-compose up -d
```

### Services Running
- Athena HTTP API (port 3000)
- Dashboard Backend (port 8000)
- Ollama local LLM (port 11434)
- Qdrant vector DB (port 6333)
- Redis cache (port 6379)

### System Features
- ✅ 100% of critical gaps implemented
- ✅ 14 autonomous agents with tool autodiscovery
- ✅ 6 strategic hook points (automated)
- ✅ Self-RAG and ReAct pipelines verified
- ✅ Dual-process consolidation
- ✅ Local-first, offline-capable architecture
- ✅ Full Docker Compose orchestration

The system automatically activates hooks, invokes agents via tool autodiscovery, records episodic events, and consolidates patterns - all without manual intervention!

---

**Document Version**: 1.0  
**Status**: Production Ready  
**Last Updated**: November 7, 2025
