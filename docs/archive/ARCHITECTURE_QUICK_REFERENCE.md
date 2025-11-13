# ATHENA ARCHITECTURE - QUICK REFERENCE INDEX

**Fast lookup guide for the Athena codebase**
**For detailed info, see ARCHITECTURE_COMPLETE_OVERVIEW.md**

---

## COMPONENT LOOKUP TABLE

### Memory Layers (8 total)

| Layer | Location | Main Class | Purpose | Status |
|-------|----------|-----------|---------|--------|
| 1. Episodic | `episodic/` | `EpisodicStore` | Events with spatio-temporal grounding | 8K+ events |
| 2. Semantic | `memory/` | `MemoryStore` | Hybrid vector+BM25 facts | <100ms search |
| 3. Procedural | `procedural/` | `ProceduralStore` | Reusable workflows, 101 extracted | Learning |
| 4. Prospective | `prospective/` | `ProspectiveStore` | Tasks, goals, smart triggers | Active |
| 5. Knowledge Graph | `graph/` | `GraphStore` | Entities, relations, communities | Leiden algo |
| 6. Meta-Memory | `meta/` | `MetaMemoryStore` | Quality, expertise, confidence | Tracking |
| 7. Consolidation | `consolidation/` | `ConsolidationSystem` | Dual-process episodic→semantic | System 1: 100ms |
| 8. Supporting | `rag/`, `planning/`, etc. | Various | RAG, Planning (Q*), Safety, Rules | Optional |

---

## CORE CLASSES

### Memory Manager

```
UnifiedMemoryManager (manager.py)
  ├─ semantic: MemoryStore
  ├─ episodic: EpisodicStore
  ├─ procedural: ProceduralStore
  ├─ prospective: ProspectiveStore
  ├─ graph: GraphStore
  ├─ meta: MetaMemoryStore
  ├─ consolidation: ConsolidationSystem
  └─ rag_manager: RAGManager (optional)
```

### MCP Server

```
MemoryMCPServer (mcp/handlers.py - 11K lines)
  ├─ manager: UnifiedMemoryManager
  ├─ router: OperationRouter
  ├─ rate_limiter: MCPRateLimiter
  └─ [40+ tool definitions]
```

### Agents

```
BaseAgent (agents/base.py)
  ├─ agent_type: AgentType
  ├─ metrics: AgentMetrics
  └─ process_message()

AgentOrchestrator (agents/orchestrator.py)
  ├─ agents: Dict[name → Agent]
  └─ execute_plan(ExecutionPlan)  [DAG-based, parallel]
```

### Hooks

```
HookDispatcher (hooks/dispatcher.py)
  ├─ 13 lifecycle hooks
  ├─ Safety utils: idempotency, rate limiting, cascade detection
  └─ Auto record episodic events
```

---

## OPERATION CATEGORIES

### MCP Operations (228+ total)

| Category | Count | Main Operations |
|----------|-------|-----------------|
| Memory | 27 | recall, remember, forget, optimize |
| Episodic | 10 | record_event, recall_events, get_timeline |
| Graph | 15 | create_entity, create_relation, search_graph |
| Planning | 16 | plan, validate, verify, scenario_test |
| Consolidation | 12 | consolidate, extract_patterns, learn |
| Procedural | 8 | extract_workflow, match_pattern, suggest |
| Prospective | 7 | create_task, update_task, monitor |
| RAG | 20 | search, expand, compress, rerank |
| Code | 30+ | analyze, search, extract patterns |
| Agent | 20+ | orchestrate, execute, monitor |

### Slash Commands (20+ total)

| Tier | Category | Count | Examples |
|------|----------|-------|----------|
| Critical | Execution | 6 | monitor-task, validate-plan, plan-task |
| Advanced | Learning | 2 | optimize-agents, find-communities |
| Useful | Assistance | 6 | retrieve-smart, analyze-code, budget-task |
| Important | Optimization | 6 | consolidate, assess-memory, explore-graph |

---

## FILE LOCATION QUICK FIND

### Entry Points
- **MCP Server**: `src/athena/mcp/handlers.py`
- **Manager**: `src/athena/manager.py`
- **CLI**: `src/athena/cli.py`
- **Database**: `src/athena/core/database.py`

### Store Classes (All extend BaseStore)
```
Layer 1: episodic/store.py        → EpisodicStore
Layer 2: memory/store.py          → MemoryStore
Layer 3: procedural/store.py      → ProceduralStore
Layer 4: prospective/store.py     → ProspectiveStore
Layer 5: graph/store.py           → GraphStore
Layer 6: meta/store.py            → MetaMemoryStore
Advanced: consolidation/system.py → ConsolidationSystem
```

### Systems
```
RAG:       rag/manager.py
Planning:  planning/store.py
Safety:    safety/store.py
Rules:     rules/engine.py
Research:  research/store.py
Execution: execution/monitor.py
```

### MCP Handlers (30+ files)
```
Core:           handlers_tools.py, handlers_episodic.py
System:         handlers_system.py, handlers_consolidation.py
Advanced:       handlers_retrieval.py, handlers_planning.py
Agentic:        handlers_agentic.py, handlers_agent_optimization.py
Integration:    handlers_integration.py, handlers_slash_commands.py
Analysis:       handlers_code_analysis.py, handlers_code_search.py
Routing:        operation_router.py
Rate Limiting:  rate_limiter.py
```

### Agent Files (25+ files)
```
Base:           agents/base.py
Orchestration:  agents/orchestrator.py, agents/planning_orchestrator.py
Types:          agents/planner.py, agents/executor.py, agents/monitor.py
Utils:          agents/message_bus.py, agents/conflict_resolver.py
Specialized:    agents/research_coordinator.py, agents/temporal_reasoner.py
```

### Hooks
```
Dispatcher:     hooks/dispatcher.py
Safety:         hooks/lib/idempotency_tracker.py
                hooks/lib/rate_limiter.py
                hooks/lib/cascade_monitor.py
Integration:    hooks/bridge.py, hooks/mcp_wrapper.py
```

### Skills
```
Python:         skills/bottleneck_detector.py, skills/plan_learner.py
Claude Skills:  claude/skills/[name]/SKILL.md (15 total)
```

### Commands
```
Slash Commands: claude/commands/[tier]/[name].md (20+ total)
Handlers:       mcp/handlers_slash_commands.py
Integration:    integration/slash_commands.py
```

---

## QUICK PATTERNS

### Creating a New Memory Layer

```python
# 1. Create models.py
from pydantic import BaseModel
class MyModel(BaseModel):
    id: int
    name: str

# 2. Create store.py
from core.base_store import BaseStore
class MyStore(BaseStore[MyModel]):
    def _init_schema(self):
        self.db.execute("CREATE TABLE IF NOT EXISTS my_table ...")

# 3. Add to manager.py
self.my_layer = MyStore(db)

# 4. Add MCP tool (handlers_*.py)
@self.server.tool()
def my_operation(param: str) → str:
    return "result"
```

### Creating a New Agent

```python
from agents.base import BaseAgent, AgentType

class MyAgent(BaseAgent):
    def __init__(self, db_path: str):
        super().__init__(AgentType.PLANNER, db_path)
    
    async def process_message(self, message: Dict) → Dict:
        # Process message
        return {"result": "..."}

# Register with orchestrator
orchestrator.register_agent(MyAgent(db_path))
```

### Adding a Slash Command

```
# 1. Create claude/commands/[tier]/[name].md with CLAUDE.md-style content

# 2. Implement handler (mcp/handlers_slash_commands.py)
async def _handle_[name](self, params: Dict) → Dict:
    return await self.manager.operation(params)

# 3. Register in SlashCommandRouter
```

### Adding a Hook

```python
# Register in HookDispatcher.__init__
self._hook_registry["my_hook"] = {"enabled": True, ...}

# Implement handler
async def on_my_hook(self, context: Dict) → None:
    with self._execute_with_safety("my_hook", context, lambda: ...):
        # Implementation
```

---

## DATA STRUCTURES

### Key Models

```python
# Episodic
EpisodicEvent(timestamp, event_type, context, description, outcome)
EventContext(file_path, line_number, function_name, arguments)

# Semantic
SemanticMemory(content, embedding, quality_score, metadata)

# Procedure
Procedure(name, category, steps, effectiveness_score, times_executed)

# Graph
Entity(type, name, description, properties)
Relation(source_id, target_id, relation_type, strength)

# Task
ProspectiveTask(title, status, priority, deadline, phase)

# Consolidation
PatternExtraction(pattern_type, pattern_data, confidence, support)

# Planning
ExecutionPlan(plan_id, tasks, execution_order, dependencies)
AgentTask(id, agent_name, input_data, dependencies, status)
```

---

## PERFORMANCE TARGETS

| Operation | Target | Current |
|-----------|--------|---------|
| Semantic search | <100ms | ~50-80ms |
| Graph query | <50ms | ~30-40ms |
| Consolidation (1K events) | <5s | ~2-3s |
| Event insertion | 2000+/sec | ~1500-2000/sec |
| Working memory access | <10ms | ~5ms |
| System 1 consolidation | <100ms | ~100ms |
| System 2 LLM validation | ~1-5s | ~1-5s |

---

## DATABASE TABLES (80+ total)

### Memory
```
memories, memory_metadata
```

### Episodic
```
episodic_events, event_sessions, event_timeline
```

### Graph
```
entities, relations, observations, communities
```

### Tasks
```
prospective_tasks, task_phases, task_triggers, goals
```

### Procedures/Patterns
```
procedures, patterns, pattern_matches
```

### Consolidation
```
consolidation_runs, consolidation_metrics
```

### Planning
```
plans, plan_validations, rules
```

### Conversation/Hooks
```
conversations, conversation_turns, hook_executions
```

### Other
```
code_artifacts, ide_context, spatial_data, temporal_chains
```

---

## INITIALIZATION ORDER

1. **Database** - `Database(path)` or `DatabaseFactory.create()`
2. **Stores** - EpisodicStore, MemoryStore, etc. (init schemas on-demand)
3. **Manager** - UnifiedMemoryManager(semantic, episodic, ...)
4. **MCP Server** - MemoryMCPServer() [initializes manager + all tools]
5. **Agents** - AgentOrchestrator(agents) [register agent types]
6. **Hooks** - HookDispatcher(db) [register lifecycle hooks]
7. **Integration** - Initialize coordinators as needed

---

## CONFIGURATION

**File**: `src/athena/core/config.py`

```python
# Database
DATABASE_TYPE = "sqlite" | "postgres"
DATABASE_PATH = "memory.db"
POSTGRES_URL = None

# LLM/Embedding
EMBEDDING_PROVIDER = "ollama" | "anthropic" | "mock"
LLM_PROVIDER = "ollama" | "anthropic"
OLLAMA_HOST = "http://localhost:11434"
ANTHROPIC_API_KEY = None

# Features
ENABLE_RAG = True
ENABLE_PLANNING = True
ENABLE_SAFETY = True
DEBUG = False
```

---

## TESTING PATTERNS

```python
@pytest.fixture
def db(tmp_path):
    return Database(str(tmp_path / "test.db"))

@pytest.fixture
def episodic_store(db):
    return EpisodicStore(db)

def test_record_event(episodic_store):
    event = EpisodicEvent(...)
    event_id = episodic_store.record_event(event)
    assert event_id > 0
```

**Run tests**:
```bash
pytest tests/unit/ tests/integration/ -v -m "not benchmark"  # Fast
pytest tests/ -v --timeout=300                                # Full
```

---

## DEBUGGING TIPS

1. **Enable logging**: `DEBUG=1` environment variable
2. **Check database**: `sqlite3 memory.db ".tables"`
3. **Monitor metrics**: `manager.get_metrics()`
4. **Check hooks**: `dispatcher._hook_registry`
5. **Trace operations**: `operation_router.route(op)`
6. **Agent status**: `orchestrator.get_execution_history()`

---

## KEY FILES BY PURPOSE

### Understanding Query Flow
1. Start: `/src/athena/manager.py` (UnifiedMemoryManager.retrieve)
2. Routing: `/src/athena/mcp/operation_router.py`
3. Handlers: `/src/athena/mcp/handlers_tools.py` (_handle_recall)
4. Stores: `/src/athena/memory/store.py` (MemoryStore.search)

### Understanding Consolidation
1. Entry: `/src/athena/consolidation/system.py` (ConsolidationSystem.consolidate)
2. System 1: `/src/athena/consolidation/clustering.py` + `pattern_extraction.py`
3. System 2: `/src/athena/consolidation/pattern_validation.py`
4. Output: `/src/athena/memory/store.py` (store facts)

### Understanding Agent Execution
1. Plan: `/src/athena/agents/orchestrator.py` (create_plan)
2. Execute: `/src/athena/agents/orchestrator.py` (execute_plan)
3. Message: `/src/athena/agents/message_bus.py`
4. Monitor: `/src/athena/agents/monitor.py`

### Understanding Hooks
1. Dispatch: `/src/athena/hooks/dispatcher.py` (on_session_start)
2. Safety: `/src/athena/hooks/lib/*.py`
3. Record: `/src/athena/episodic/store.py` (record_event)

---

## STATISTICS AT A GLANCE

- **500+ Python files**, 250K+ lines of code
- **8 memory layers** with 60+ implementation files
- **40+ MCP handlers** with 228+ operations
- **30+ agent files** implementing orchestration
- **25+ integration coordinators**
- **15 Claude Skills** + 20+ slash commands
- **80+ database tables**
- **50+ test files** with 20K+ LOC
- **8,000+ episodic events** in current database
- **101+ extracted procedures**

---

## NEXT STEPS

1. **Read full overview**: See ARCHITECTURE_COMPLETE_OVERVIEW.md
2. **Explore core**: Read manager.py → episodic/store.py → consolidation/system.py
3. **Understand tools**: Read mcp/handlers.py → operation_router.py → handlers_tools.py
4. **Try it**: `python -m athena.mcp` or `memory-mcp`
5. **Test it**: `pytest tests/unit/ -v`

---

**For detailed architectural deep-dives, property diagrams, and specific implementation details, refer to ARCHITECTURE_COMPLETE_OVERVIEW.md**

