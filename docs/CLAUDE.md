# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Global Context

This project exports the **Athena memory system** that powers global hooks for ALL projects:

- **Global Hooks**: Registered in `~/.claude/settings.json` and active for all projects
- **Memory Access**: All hooks use the Athena memory API to provide cross-project memory
- **No MCP Servers**: Projects no longer use MCP servers; hooks provide memory access directly
- **Documentation**: See `~/.claude/HOOKS_AND_MEMORY.md` for complete integration guide

### What This Means

Every project in `~/.work/` automatically has access to:
- **Episodic memory** (what happened when)
- **Semantic memory** (facts learned across projects)
- **Procedural memory** (reusable workflows)
- **Working memory** (7±2 focus items from previous session)
- **Knowledge graph** (entity relationships)

This is managed entirely through global hooks - no configuration needed per-project.

## Quick Commands

**Development**:
```bash
# Install in development mode
pip install -e .

# Run tests (skip slow/benchmark tests for fast feedback)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Run full test suite
pytest tests/ -v --timeout=300

# Format and lint
black src/ tests/
ruff check --fix src/ tests/

# Type checking
mypy src/athena

# Start MCP server
memory-mcp

# Install ast-grep for syntax-aware code matching & refactoring
cargo install ast-grep  # or: brew install ast-grep
```

**Memory Operations** (via FilesystemAPI only):

Use the FilesystemAPIAdapter to access all memory operations:

```python
from filesystem_api_adapter import FilesystemAPIAdapter

adapter = FilesystemAPIAdapter()

# Discover available operations
layers = adapter.list_layers()
ops = adapter.list_operations_in_layer("semantic")

# Read operation code
code = adapter.read_operation("semantic", "recall")

# Execute operation
result = adapter.execute_operation("semantic", "recall", {
    "query": "topic",
    "host": "localhost",
    "port": 5432,
    "dbname": "athena",
    "user": "postgres",
    "password": "postgres"
})
```

For detailed examples, see `docs/ANTHROPIC_PATTERN_IMPLEMENTATION.md`

## Anthropic Code Execution Pattern Alignment ✅

This project aligns with **Anthropic's code-execution pattern** from their article on code-execution-with-MCP (source: https://www.anthropic.com/engineering/code-execution-with-mcp).

**Important Note**: We implement the **pattern principles** (progressive disclosure, local processing, summary-first) but not the **MCP protocol** itself. MCP is an optional protocol choice - the key efficiency comes from the pattern.

### Design Principles (MANDATORY for all new code)

**The Pattern**: Discover operations → Execute locally → Summarize results

| Aspect | ❌ Old Way | ✅ New Way |
|--------|-----------|-----------|
| Tool definitions | Loaded upfront (150K tokens) | Discovered on-demand via filesystem |
| Data handling | Full objects in context (50K token duplication) | Processed locally, 300-token summaries returned |
| Execution | Alternating agent↔tool calls | Direct code execution in process |
| Context efficiency | Wasteful | 98.7% token reduction |

### Implementation Requirements

Every hook, skill, agent, and slash command **MUST** follow this pattern:

```
1. Discover  → List available operations (filesystem, API)
2. Read      → Load only needed signatures (import, describe_api)
3. Execute   → Process data locally in execution environment
4. Summarize → Return 300-token summary (NOT full objects)
```

**Why**: This pattern drastically reduces token usage (150K → 2K) and improves efficiency.

### Token Limits and Context Budgeting

**Context Token Targets** (MANDATORY for all handlers):

Every MCP handler result **MUST** respect these token limits:

| Result Type | Target | Notes |
|-------------|--------|-------|
| **Summary** | ~300 tokens | Primary use case - top results + metadata |
| **Pagination metadata** | ~50 tokens | Tells user how to drill down |
| **Full context** | ~4000 tokens max | Only on explicit drill-down request |

**Default Item Limits** (MANDATORY for all list-returning handlers):

```python
# All handlers returning lists MUST implement these defaults
args = {
    "limit": min(args.get("limit", 10), 100),  # Default 10, max 100
    "offset": args.get("offset", 0),
}
results = fetch_results(offset=args["offset"], limit=args["limit"])
```

**Pagination Pattern** (MANDATORY for all list-returning handlers):

Every handler that returns multiple items MUST include pagination metadata:

```python
from src.athena.mcp.structured_result import StructuredResult, PaginationMetadata

# Fetch results with limit
results = fetch_results(limit=limit)

# Return with pagination metadata
return StructuredResult.success(
    data=results,
    pagination=PaginationMetadata(
        returned=len(results),
        total=total_count,  # Get from database
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total_count,
    ),
    summary=f"Returned {len(results)} of {total_count} items. Use adapter.get_detail() to drill into specific items."
)
```

**When to Use Pagination vs Drill-Down**:

| Scenario | Use Pagination | Reason |
|----------|----------------|--------|
| User asks "list all tasks" | ✅ YES | Return top-10 with "has_more" flag |
| User asks "show first 3 items" | ✅ YES | Limit by default, add drill-down guidance |
| User asks "details on item #5" | ❌ NO (drill-down) | Return full item without pagination |
| Search returns 500+ results | ✅ YES | Must paginate for token efficiency |
| A single operation returns <5 items | ⚠️ OPTIONAL | Can return all if <100 tokens |

**Overflow Handling Strategies** (when content exceeds limits):

The TokenBudgetManager in `src/athena/efficiency/token_budget.py` provides 6 strategies:

1. **COMPRESS** - Use TOON encoding (40-60% savings)
2. **TRUNCATE_START** - Remove older/less relevant items from start
3. **TRUNCATE_END** - Remove newer/less relevant items from end
4. **TRUNCATE_MIDDLE** - Remove middle items, keep head and tail
5. **DELEGATE** - Suggest pagination/drill-down instead
6. **DEGRADE** - Return simpler format (metadata only vs full objects)

**Default overflow strategy**:
```python
# Priority: COMPRESS → TRUNCATE_END → DELEGATE
if content_tokens > 300:
    result = compress_with_toon(result)  # Try 40-60% reduction
    if remaining_tokens > 300:
        result = truncate_to_top_k(result, k=5)  # Keep top-5
    if still_too_large:
        return error_with_drill_down_suggestion()  # Delegate to user
```

**Example: Implementing a Paginated Handler**

```python
async def _handle_list_tasks(self, args: dict) -> StructuredResult:
    """List tasks with mandatory pagination."""
    # Parse arguments with safe defaults
    limit = min(args.get("limit", 10), 100)  # Max 100
    offset = max(args.get("offset", 0), 0)   # Min 0

    # Fetch results
    tasks = await self.db.list_tasks(limit=limit, offset=offset)
    total_count = await self.db.count_tasks()  # Get total for pagination

    # Check token budget
    tokens = self.token_budget.count_tokens(json.dumps(tasks))
    if tokens > 300:
        # Compress or truncate
        tasks = tasks[:5]  # Keep only top-5

    # Return with pagination metadata
    return StructuredResult.success(
        data={
            "tasks": [task.to_dict() for task in tasks],
            "count": len(tasks),
        },
        pagination=PaginationMetadata(
            returned=len(tasks),
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count,
        ),
        summary=f"Returned {len(tasks)} of {total_count} tasks. "
                f"Use adapter.get_detail() with task_id for full details."
    )
```

**Monitoring Token Usage**:

Enable token budget enforcement globally to catch violations:

```bash
# Check token budget metrics
curl -X POST http://localhost:3000/health/metrics
# Returns: total_tokens_used, budget_violations, compression_ratio

# Enable detailed logging
DEBUG=1 memory-mcp
```

---

### Subagent Strategy: When to Use What

Athena uses **three complementary layers** for agent-based work:

| Layer | Tool | Use When | Example |
|-------|------|----------|---------|
| **Claude Code Built-in** | `Task(subagent_type=...)` | Claude should delegate to specialized agent | Code review, research, planning validation |
| **Project Skills** | Auto-triggered by context | Claude autonomously decides to use skill | Discussing memory quality, evaluating code changes |
| **Custom Orchestration** | `SubAgentOrchestrator` | Athena internal operations need coordination | Consolidation (clustering → extraction → validation) |

**Decision Tree**:

```
When Claude needs to accomplish a task:
├─ "Does Claude Code have a built-in subagent type?"
│  ├─ YES → Use Task(subagent_type=...)
│  │        (Fresh context, optimized model selection, auto-delegation)
│  │
│  └─ NO → Continue below
│
├─ "Is this a reusable capability across projects?"
│  ├─ YES → Create/use Skill (auto-triggered by context)
│  │        (Progressive disclosure, progressive activation)
│  │
│  └─ NO → Continue below
│
└─ "Is this internal Athena workflow needing coordination?"
   ├─ YES → Use SubAgentOrchestrator in Python
   │        (Local data processing, feedback loops, state tracking)
   │
   └─ NO → Execute inline without subagents
```

**Built-in Subagent Types (from Claude Code)**:
- `general-purpose`: Research, complex questions, code execution
- `code-analyzer`: Codebase analysis, refactoring suggestions
- `code-reviewer`: Code review, quality checks
- `debugger`: Debugging, error investigation
- `data-scientist`: Data analysis, ML work
- `plan-validator`: Plan verification with Q* and scenarios
- Plus others available via Task tool

**Athena Skills (Auto-triggered)**:
- `memory-quality-assessment`: Evaluate system health
- `code-impact-analysis`: Assess change safety
- `planning-validation`: Validate plans formally
- `consolidation-optimization`: Optimize experience consolidation
- `knowledge-discovery`: Explore knowledge relationships
- Plus 15+ others in `.claude/skills/`

**Custom SubAgentOrchestrator** (Internal):
- Coordinates clustering, extraction, validation, integration
- Manages dependency graphs between subagents
- Maintains local state and feedback loops
- Measures coordination effectiveness

**Key Principle**: Use the **highest-level abstraction** available. Built-in subagents > Skills > Custom code.

### Examples of Aligned Patterns

**✅ Correct** (Anthropic-aligned):
```python
# Hook discovers available operations, executes locally, returns summary
operations = list_directory("/athena/layers/semantic")
for op in operations:
    signature = read_file(f"/athena/layers/semantic/{op}")  # Just the schema

results = execute("search", query, filter=top_k=5)  # Execute locally
summary = aggregate_results(results)  # Filter/process here
return {"count": len(results), "top_matches": summary[:3]}  # 300 tokens max
```

**❌ Incorrect** (old tool-calling way):
```python
# Loads all tool definitions, returns full objects
tools = describe_all_memory_tools()  # 15K tokens upfront
results = memory.search(query)  # Returns 50K of full objects
return results  # Context bloat!
```

---

## Alignment Verification ✅

**Verified November 12, 2025** - All systems aligned with Anthropic's MCP code execution model.

### Verification Results

| Component | Status | Alignment | Actions Taken |
|-----------|--------|-----------|---|
| **Skills (10)** | ✅ Perfect | 100% | None needed - textbook implementation |
| **Agents (27)** | ✅ Perfect | 100% | None needed - all use AgentInvoker |
| **Hooks (7)** | ✅ Optimized | 95% → 100% | Migrated 5 hooks to AgentInvoker |
| **Slash Commands (33)** | ✅ Improved | 95% → 98% | Enhanced search commands with summary pattern |
| **MCP Handlers** | ✅ Perfect | 100% | None needed - proper operation routing |

### Changes Made

**Hooks Optimized** (5 hooks):
1. `session-end.sh` - Migrated graph/procedural operations to AgentInvoker
2. `pre-execution.sh` - All 5 validation checks now use AgentInvoker
3. `post-task-completion.sh` - Removed MCP direct calls, workflow-learner handles creation
4. `smart-context-injection.sh` - Added local result filtering via retrieval-specialist

**FilesystemAPI Operations** (All 10 operations now use filesystem discovery only):
1. `semantic/recall` - Search memories using FilesystemAPI
2. `episodic/search` - Search events using FilesystemAPI
(Plus 8 more operations across 8 layers - see docs/ANTHROPIC_PATTERN_IMPLEMENTATION.md)

### Key Principles Enforced

1. **Discover** - Use filesystem/MCP list operations (on-demand)
2. **Execute** - Process data locally in Python/sandbox
3. **Summarize** - Return 300-token max, full objects only on drill-down

---

## Project Overview

**Athena** is a sophisticated 8-layer neuroscience-inspired memory system for AI agents. The key innovation is *sleep-like consolidation* - converting episodic events into semantic knowledge using dual-process reasoning (fast heuristics + slow LLM validation).

**Current Status**:
- **Core Layers**: 95% complete, 94/94 tests passing ✅
- **MCP Interface**: Feature-complete, limited test coverage (22,000 lines of code)
- **Overall Code Coverage**: ~65% (core layers 90%+, MCP handlers <20%)
- **Test Suite**: 94 unit/integration tests (core logic), missing MCP server tests
- **Production Readiness**: Ready for core features, MCP testing in progress

### Core Architecture: 8-Layer Memory System

```
MCP Interface (27 tools, 228+ operations)
    ↓
Layer 8: Supporting Infrastructure (RAG, Planning, Zettelkasten, GraphRAG)
Layer 7: Consolidation (Dual-process pattern extraction)
Layer 6: Meta-Memory (Quality tracking, attention, cognitive load)
Layer 5: Knowledge Graph (Entities, relations, communities)
Layer 4: Prospective Memory (Tasks, goals, triggers)
Layer 3: Procedural Memory (Reusable workflows, 101 extracted)
Layer 2: Semantic Memory (Vector + BM25 hybrid search)
Layer 1: Episodic Memory (Events with spatial-temporal grounding)
    ↓
PostgreSQL (Async-first, connection pooling)
Current: 8,128 episodic events, 101 procedures
```

### Key Layers & Responsibilities

1. **Episodic** (`src/athena/episodic/`) - Event storage with timestamps, context, spatial-temporal grounding
   - `storage.py`: Persist events to database
   - `buffer.py`: Working memory (7±2 items)
   - `temporal.py`: Temporal reasoning & chaining

2. **Semantic** (`src/athena/semantic/` + `src/athena/memory/`) - Knowledge representation via vector+BM25
   - `embeddings.py`: Generate embeddings (Ollama or Anthropic)
   - `search.py`: Hybrid semantic search
   - `store.py`: Semantic memory persistence

3. **Procedural** (`src/athena/procedural/`) - Learn & reuse workflows
   - `extraction.py`: Extract patterns from episodic events
   - `procedures.py`: Store and execute reusable procedures
   - `effectiveness.py`: Track procedure quality metrics

4. **Prospective** (`src/athena/prospective/`) - Task management & goals
   - `tasks.py`: Task storage and tracking
   - `goals.py`: Goal hierarchies and lifecycle
   - `triggers.py`: Smart triggers (time/event/file-based)

5. **Knowledge Graph** (`src/athena/graph/`) - Semantic structure
   - `store.py`: Entity & relation storage
   - `communities.py`: Community detection (Leiden algorithm)
   - `observations.py`: Contextual observations on entities

6. **Meta-Memory** (`src/athena/meta/`) - Knowledge about knowledge
   - `quality.py`: Compression, recall, consistency metrics
   - `expertise.py`: Domain expertise tracking
   - `attention.py`: Salience & focus management
   - `load.py`: Cognitive load monitoring (Baddeley 7±2)

7. **Consolidation** (`src/athena/consolidation/`) - Sleep-like pattern extraction
   - `consolidator.py`: Main orchestration engine
   - `clustering.py`: Event clustering by proximity/session
   - `patterns.py`: Pattern extraction (statistical)
   - `validation.py`: LLM validation when uncertainty >0.5

8. **Supporting Systems** (`src/athena/rag/`, `src/athena/planning/`, etc.)
   - **RAG** (`rag/`): HyDE, reranking, reflective, query transform
   - **Planning** (`planning/`): Q* verification, adaptive replanning, scenario simulation
   - **Zettelkasten** (`associations/`): Memory versioning, hierarchical indexing (Luhmann)
   - **GraphRAG** (`graphrag_tools.py`): Community-based retrieval

---

## Code Organization

### Core Modules

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `core/` | Database, config, base interfaces | `database.py`, `models.py`, `config.py` |
| `episodic/` | Event storage (Layer 1) | `storage.py`, `buffer.py`, `temporal.py` |
| `memory/` + `semantic/` | Semantic memory (Layer 2) | `search.py`, `embeddings.py`, `store.py` |
| `procedural/` | Workflow learning (Layer 3) | `extraction.py`, `procedures.py` |
| `prospective/` | Task management (Layer 4) | `tasks.py`, `goals.py`, `triggers.py` |
| `graph/` | Knowledge graph (Layer 5) | `store.py`, `communities.py`, `observations.py` |
| `meta/` | Meta-memory (Layer 6) | `quality.py`, `expertise.py`, `attention.py` |
| `consolidation/` | Pattern extraction (Layer 7) | `consolidator.py`, `clustering.py`, `patterns.py` |
| `rag/` | Advanced retrieval | `manager.py`, `reflective.py`, `hyde.py`, `reranker.py` |
| `planning/` | Advanced planning (Phase 6) | `validator.py`, `formal_verification.py`, `scenario_simulator.py` |
| `associations/` | Zettelkasten | `zettelkasten.py`, `hierarchical_index.py`, `hebbian.py` |
| `mcp/` | MCP server & tools | `handlers.py` (core), `handlers_*.py` (domain-organized), `operation_router.py` |
| `manager.py` | Unified memory manager | Query routing, layer orchestration |

### MCP Server Architecture

The MCP server in `src/athena/mcp/` implements 27 tools with 228+ operations (313 handler methods):

#### Core Handler Organization (November 13, 2025 Refactoring)

**Status**: ✅ Refactored into 11 domain-organized modules (forwarding pattern)

The MCP server handler methods are now logically organized by memory domain while maintaining 100% backward compatibility:

- **`handlers.py`** (12,363 lines): Main `MemoryMCPServer` class with all 313 handler method implementations
- **Domain-Organized Handler Modules** (forwarding pattern for code navigation):
  - `handlers_memory_core.py`: Core operations (25 methods) - remember, recall, forget, list, optimize, search
  - `handlers_episodic.py`: Episodic memory (16 methods) - event recording, temporal retrieval, consolidation
  - `handlers_procedural.py`: Procedural memory (29 methods) - workflows, procedures, execution tracking
  - `handlers_prospective.py`: Prospective memory (24 methods) - tasks, goals, milestones, planning
  - `handlers_graph.py`: Knowledge graph (12 methods) - entities, relations, observations, search
  - `handlers_working_memory.py`: Working memory (11 methods) - 7±2 cognitive limit operations
  - `handlers_metacognition.py`: Metacognition (8 methods) - quality, learning, gaps, expertise, load
  - `handlers_planning.py`: Planning (33 methods) - decomposition, verification, validation, strategy
  - `handlers_consolidation.py`: Consolidation (12 methods) - pattern extraction, RAG, retrieval
  - `handlers_research.py`: Research (2 methods) - research tasks, findings integration
  - `handlers_system.py`: System (141 methods) - health, analytics, code, automation, budget, IDE, patterns

**Design Pattern**: Forwarding modules provide logical separation without code duplication:
- All implementations remain in `handlers.py::MemoryMCPServer`
- Domain modules import and reference these methods for discoverability
- Zero breaking changes, 100% backward compatible
- Enables incremental migration to full extraction

**Operation Routing**: `operation_router.py` dispatches tool calls to the appropriate `MemoryMCPServer._handle_*` method based on operation name.

### Testing

Tests are organized by type:
- `tests/unit/` - Individual layer validation
- `tests/integration/` - Cross-layer coordination
- `tests/performance/` - Benchmark tests (marked with `@pytest.mark.benchmark`)
- `tests/mcp/` - MCP server integration tests
- `tests/fixtures/` - Shared pytest fixtures

**Fixture Pattern**:
```python
@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))

@pytest.fixture
def episodic_store(db):
    """Create episodic store with schema."""
    return EpisodicStore(db)
```

---

## Key Design Patterns

### 1. Layer Initialization Pattern

Each memory layer follows the same initialization pattern:

```python
# src/athena/[layer]/store.py
class [Layer]Store:
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()  # Create tables if not exist

    def _init_schema(self):
        """Create schema on first use (idempotent)."""
        # Use db.execute() with CREATE TABLE IF NOT EXISTS
```

**Key Point**: Schemas are created on-demand, not in migrations. This enables:
- Quick prototyping
- Test isolation (each test gets fresh database)
- Development simplicity (no migration management)

### 2. Query Routing Pattern

The `UnifiedMemoryManager` in `manager.py` routes queries to appropriate layers:

```python
class QueryType:
    TEMPORAL = "temporal"           # Episodic layer
    FACTUAL = "factual"             # Semantic layer
    RELATIONAL = "relational"       # Knowledge graph
    PROCEDURAL = "procedural"       # Procedural layer
    PROSPECTIVE = "prospective"     # Prospective layer
    META = "meta"                   # Meta-memory
    PLANNING = "planning"           # Planning layer

# Router uses query type + heuristics to select optimal layer
```

### 3. Optional RAG Degradation

RAG components are optional to support local-only deployments:

```python
# manager.py
try:
    from .rag import RAGManager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Later: graceful fallback if RAG not available
if RAG_AVAILABLE:
    results = self.rag_manager.retrieve(...)
else:
    results = self.semantic_store.search(...)
```

### 4. MCP Tool Naming Convention

Operations follow a hierarchical naming pattern:

- `recall` / `remember` / `forget`: Core memory operations
- `[operation]_[details]`: Scoped operations (e.g., `recall_events_by_session`)
- `[layer]_[operation]`: Layer-specific operations (e.g., `episodic_store_event`)

### 5. Consolidation Dual-Process

The consolidation system uses dual-process reasoning for quality:

```python
# System 1 (Fast, ~100ms)
clusters = statistical_clustering(events)
patterns = heuristic_extraction(clusters)

# System 2 (Slow, triggered when uncertainty > 0.5)
if pattern_uncertainty > 0.5:
    validated_patterns = llm_validate(patterns)
```

---

## Development Workflow

### Adding a New MCP Tool

1. **Define the tool** in `src/athena/mcp/handlers.py`:
   ```python
   @self.server.tool()
   def my_new_tool(param1: str, param2: int) -> str:
       """Description of what the tool does."""
       return "result"
   ```

2. **Test it** in `tests/mcp/`:
   ```python
   def test_my_new_tool():
       server = MemoryMCPServer()
       result = server.my_new_tool("test", 123)
       assert result == "expected"
   ```

3. **Update docs** in appropriate markdown (README.md, API_REFERENCE.md, etc.)

### Adding a New Memory Layer

1. **Create layer directory**: `src/athena/[layer_name]/`

2. **Implement core files**:
   - `models.py` - Data models (Pydantic classes)
   - `store.py` - Persistence layer (extends `Store` base class)
   - `[operation].py` - Layer-specific operations

3. **Update UnifiedMemoryManager** in `manager.py`:
   - Add layer initialization
   - Add routing rules for query types
   - Add public methods to expose layer

4. **Add MCP tools** in `src/athena/mcp/handlers.py`:
   - Create tool definitions for layer operations
   - Add handler methods for each tool

5. **Write tests** in `tests/unit/test_[layer_name].py`:
   - Test model validation
   - Test store operations (CRUD)
   - Test error cases

### Running Tests

```bash
# Fast feedback (unit + integration, no benchmarks)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full test suite
pytest tests/ -v --timeout=300

# Single test file
pytest tests/unit/test_episodic_store.py -v

# Single test with output
pytest tests/unit/test_episodic_store.py::TestEpisodicStore::test_store_event -v -s

# With coverage
pytest tests/ --cov=src/athena --cov-report=html
```

### Decomposing Complex Tasks

For multi-phase work, break tasks into sequential single-goal prompts. This ensures clarity, reproducibility, and prevents scope creep:

**Pattern**:
1. Each prompt targets one goal (one feature, one layer, one phase)
2. Prompt structure: **Task** | **Input** | **Constraints** | **Output format** | **Verify method**
3. Chain results: output of task N feeds into task N+1
4. Decision point between tasks: explicitly state what happens next or pause for human input

**Example: Adding a new memory layer**

*Prompt 1*: "Create episodic store with schema and CRUD operations"
- Input: Database interface, existing layer patterns
- Constraints: Use existing Store base class, <300 lines
- Output: models.py + store.py
- Verify: Run `pytest tests/unit/test_episodic_*.py`

*Prompt 2*: "Implement query routing in UnifiedMemoryManager"
- Input: Completed episodic layer from Prompt 1
- Constraints: Extend existing routing patterns, add tests
- Output: Updated manager.py + new routing tests
- Verify: Run integration tests

*Prompt 3*: "Add MCP tools for layer exposure"
- Input: Completed layer + routing from Prompts 1-2
- Constraints: Follow existing MCP naming convention
- Output: Tool definitions in handlers.py
- Verify: Test tool invocations with sample data

**Benefits**:
- Clear success criteria at each step
- Reproducible (same prompts work next week)
- Easier debugging (failure points are isolated)
- No context sprawl (each prompt is focused)

### Code Style & Linting

The project enforces:
- **Formatting**: `black` (line length 100)
- **Linting**: `ruff` (PEP 8 + style rules)
- **Type checking**: `mypy` (strict mode)

```bash
# Auto-fix formatting and linting
black src/ tests/
ruff check --fix src/ tests/

# Type check (in venv)
mypy src/athena

# Check before commit
black --check src/ tests/
ruff check src/ tests/
```

---

## Async/Sync Architecture Strategy

### Design Principle: Async-First

All new code MUST be **async-first**. This is non-negotiable because:

1. **PostgreSQL backend requires async** - Direct synchronous calls will block the event loop
2. **Consistency** - Mixing async/sync creates tight coupling and brittle code
3. **Future-proof** - Async patterns scale better and support concurrency

### When to Use Async

**Use `async def` when**:
- Calling database operations (e.g., `await db.execute()`)
- Calling other async functions
- Implementing handlers, skills, or agents
- Any I/O operation (network, filesystem, database)

**Example** (Correct):
```python
# ✅ CORRECT - Async-first
class SkillLibrary:
    async def save(self, skill: Skill) -> bool:
        await self.db.initialize()
        async with self.db.get_connection() as conn:
            await conn.execute(sql, params)
        return True

class SkillExecutor:
    async def execute(self, skill: Skill) -> Dict[str, Any]:
        bound = self._bind_parameters(skill, params)  # Sync helper
        result = entry_func(**bound)  # Could be sync or async
        await self.library.update_usage(skill.id, True)  # Async call
        return {'success': True, 'result': result}
```

### When Sync is OK

**Use `def` (sync) only for**:
- Pure computation with no I/O (e.g., scoring, calculations)
- Helper/utility functions (e.g., `_bind_parameters`, `_compute_relevance`)
- Configuration and initialization (if non-blocking)

**Example** (Correct):
```python
# ✅ CORRECT - Sync helpers called from async
class SkillMatcher:
    def _compute_relevance(self, task: str, skill: Skill) -> float:
        # Pure computation - no async needed
        score = 0.0
        for keyword in skill.metadata.tags:
            if keyword.lower() in task.lower():
                score += 0.1
        return min(score, 1.0)

    async def find_skills(self, task: str) -> List[SkillMatch]:
        # Async method calls sync helper
        candidates = await self.library.list_all()
        matches = []
        for skill in candidates:
            relevance = self._compute_relevance(task, skill)  # Sync call OK
            if relevance > 0.5:
                matches.append(SkillMatch(skill, relevance))
        return matches
```

### Anti-Patterns to Avoid

**❌ WRONG - Mixing sync/async without await**:
```python
async def execute(self, skill):
    result = self.library.save(skill)  # ❌ Missing await!
    return result
```

**❌ WRONG - Calling async from sync**:
```python
def execute(self, skill):
    result = await self.library.save(skill)  # ❌ Can't await in sync!
    return result
```

**❌ WRONG - Blocking I/O in async function**:
```python
async def save(self, skill):
    # ❌ This blocks the event loop!
    with open('skill.pkl', 'wb') as f:
        f.write(pickle.dumps(skill))
    return True
```

### Migration Guide (for existing code)

If you find synchronous code that needs to be async:

1. Add `async` keyword to function signature
2. Add `await` to all async calls inside
3. Update all callers to use `await`
4. Test with `pytest tests/ -v`

Example:
```python
# Before
def process_events(self, events):
    for event in events:
        self.store.save(event)  # Sync call

# After
async def process_events(self, events):
    for event in events:
        await self.store.save(event)  # Now async
```

---

## MCP Handlers Refactoring - COMPLETED ✅

### Final State (November 13, 2025)

**Refactoring Complete**: All 148+ handler methods extracted from 12,363 lines into 11 domain-organized mixin modules.

**Original Structure**:
- **File**: `src/athena/mcp/handlers.py` (12,363 lines)
- **Methods**: 335 handler methods
- **Problem**: Monolithic structure made maintenance difficult

### Final Structure

```
src/athena/mcp/
├── handlers.py (1,270 lines) - Core MemoryMCPServer class, tool registration
├── handlers_episodic.py (1,232 lines) - Episodic memory handlers (16 methods)
├── handlers_memory_core.py (349 lines) - Core memory operations (6 methods)
├── handlers_procedural.py (945 lines) - Procedural memory (21 methods)
├── handlers_prospective.py (1,486 lines) - Prospective memory (24 methods)
├── handlers_graph.py (515 lines) - Knowledge graph (10 methods)
├── handlers_consolidation.py (363 lines) - Consolidation (16 methods)
├── handlers_planning.py (5,982 lines) - Planning operations (29 methods)
├── handlers_metacognition.py (1,222 lines) - Metacognition (8 methods)
├── handlers_working_memory.py (31 lines) - Working memory (stub)
├── handlers_research.py (22 lines) - Research (stub)
└── handlers_system.py (725 lines) - System operations (34 methods)
```

### Completion Results

✅ **89.7% reduction** in main handler file (12,363 → 1,270 lines)
✅ **148+ methods extracted** into domain-organized mixins
✅ **100% backward compatible** - zero breaking changes
✅ **Mixin inheritance pattern** - clean separation of concerns
✅ **All imports verified** - MemoryMCPServer loads successfully

### Benefits Realized

✅ Improved code organization - methods grouped by domain
✅ Easier navigation - 300-6,000 lines per file (vs. 12K monolith)
✅ Reduced cognitive load - clear separation of concerns
✅ Better collaboration - fewer merge conflicts, clearer ownership
✅ Stronger architecture - inheritance chain shows memory layer structure

---

## Critical Implementation Details

### 1. Database Access

Database access uses PostgreSQL with async/await for connection management. The `Database` class in `src/athena/core/database.py` (which aliases `PostgresDatabase`) provides both high-level methods and direct connection access through an async connection pool.

**High-Level Methods** (Preferred for common operations):

```python
# Store memory
memory_id = db.store_memory(memory: Memory) -> int

# Retrieve memory
memory = db.get_memory(memory_id: int) -> Optional[Memory]

# Delete memory
success = db.delete_memory(memory_id: int) -> bool

# List memories with filters
memories = db.list_memories(project_id: int, ...) -> list[Memory]

# Project management
project = db.create_project(name: str, path: str) -> Project
```

**Direct Connection Access** (For complex queries):

When high-level methods don't cover your use case, use direct connection with cursor:

```python
# ✅ Correct - parameterized queries
cursor = db.conn.cursor()
cursor.execute(
    "SELECT * FROM memories WHERE project_id = ? AND usefulness_score > ?",
    (project_id, min_score)
)
results = cursor.fetchall()
db.conn.commit()

# ❌ Avoid - SQL injection vulnerability
cursor.execute(f"SELECT * FROM memories WHERE id = {memory_id}")  # DANGEROUS!
```

**Key Points**:
- Always use parameterized queries with `?` placeholders (prevents SQL injection)
- Database is PostgreSQL with async connection pooling (no cloud dependencies)
- Use transactions for multi-step operations with rollback on error
- Async/await required for all database operations
- Connection pool automatically manages thread-safe access

**Guidelines for Direct Access**:
- Use direct `.conn` access only when high-level methods don't support your query
- Always wrap in try/except blocks
- Always commit or rollback transactions
- Document WHY direct access is needed (add comment)
- Consider proposing new Database method for reusable patterns

### 2. Embeddings Generation

Embeddings can come from multiple sources (graceful degradation):

```python
# src/athena/core/config.py
EMBEDDING_PROVIDER = "ollama" | "anthropic" | "mock"

# src/athena/semantic/embeddings.py
class EmbeddingManager:
    # Tries Ollama first, falls back to Anthropic, then mock
```

**For Development**: Mock embeddings work in tests without external services.
**For Production**: Use Ollama (local) or Anthropic (requires API key).

### 3. Performance Optimization

Key optimization points:

- **Vector search**: Cached in `semantic/cache.py` (LRU, 1000 items)
- **Graph queries**: Indexed on entity_id, relation_type
- **Event storage**: Bulk insertion optimized (2,000+ events/sec)
- **Consolidation**: Uses temporal clustering to reduce computation

**Monitoring**: Run benchmarks with:
```bash
pytest tests/performance/ -v --benchmark-only
```

### 4. Configuration Management

Configuration is managed through:

1. **Environment variables**: `ANTHROPIC_API_KEY`, `OLLAMA_HOST`, `DEBUG`, `DB_*` (PostgreSQL connection)
2. **Config file**: `~/.claude/settings.local.json` (local user settings)
3. **Defaults**: Hardcoded in `src/athena/core/config.py`

**Precedence**: Env vars > local settings file > hardcoded defaults

**Database Configuration** (PostgreSQL):
```bash
# Default connection (localhost)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres

# Connection pool settings
DB_MIN_POOL_SIZE=2
DB_MAX_POOL_SIZE=10
```

### 5. Error Handling in Hooks

The hook system in `src/athena/hooks/` includes graceful degradation:

- If MCP tool fails, hook falls back to mock response
- If embedding generation fails, returns null vector
- Hooks always return valid JSON (never crash)

---

## Common Tasks

### Debugging Memory Layer Issues

1. **Check memory health**:
   ```python
   from filesystem_api_adapter import FilesystemAPIAdapter
   adapter = FilesystemAPIAdapter()
   result = adapter.execute_operation("meta", "quality", {...})
   ```

2. **Query the database directly** (PostgreSQL):
   ```python
   import asyncio
   from athena.core.database import get_database

   async def debug():
       db = get_database()
       # List all tables
       tables = await db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")

       # Inspect a table
       events = await db.execute("SELECT * FROM episodic_events LIMIT 10")

   asyncio.run(debug())
   ```

3. **Enable debug logging**:
   ```bash
   DEBUG=1 pytest tests/unit/ -v -s
   ```

### Adding a Consolidation Strategy

1. **Create new strategy** in `src/athena/consolidation/strategies/`:
   ```python
   class MyStrategy(ConsolidationStrategy):
       def consolidate(self, events: List[EpisodicEvent]) -> List[SemanticMemory]:
           # Implementation
   ```

2. **Register** in `src/athena/consolidation/consolidator.py`:
   ```python
   STRATEGIES = {
       "balanced": BalancedStrategy(),
       "speed": SpeedStrategy(),
       "my_strategy": MyStrategy(),
   }
   ```

3. **Test** with strategy parameter:
   ```python
   consolidator.consolidate(strategy="my_strategy")
   ```

### Implementing Phase 6 Features (Planning)

The `src/athena/planning/` module includes:

- **`formal_verification.py`**: Q* pattern (5 properties: optimality, completeness, consistency, soundness, minimality)
- **`scenario_simulator.py`**: 5-scenario stress testing
- **`adaptive_replanning.py`**: Auto-adjust on assumption violation

To extend planning:

1. Add new property verification in `formal_verification.py`
2. Add new scenario type in `scenario_simulator.py`
3. Add new replanning strategy in `adaptive_replanning.py`
4. Expose via MCP tool in `src/athena/mcp/handlers_planning.py`

---

## Architecture Decisions

### Why PostgreSQL?

- **Scalability**: Handles large datasets efficiently
- **Concurrency**: Built-in support for async operations
- **Reliability**: ACID compliance, crash recovery
- **Performance**: Optimized for complex queries and indexing
- **Ecosystem**: Rich tooling and library support

### Why Dual-Process Consolidation?

- **System 1 (Fast)**: Statistical clustering gives baseline in <100ms
- **System 2 (Slow)**: LLM validation improves quality when needed
- **Hybrid**: Combines speed with accuracy for optimal performance

### Why Spatial-Temporal Grounding?

- **Code Understanding**: Hierarchical file paths map to code structure
- **Temporal Reasoning**: Automatic causality inference between events
- **Hybrid Scoring**: 70% semantic + 30% spatial balances both signals

---

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Semantic search | <100ms | ~50-80ms |
| Graph query | <50ms | ~30-40ms |
| Consolidation (1000 events) | <5s | ~2-3s |
| Event insertion | 2000+ events/sec | ~1500-2000/sec |
| Working memory access | <10ms | ~5ms |

**Optimization priorities**:
1. Consolidation: 5s → 2s (2-3x improvement)
2. Search: 100ms → 50ms (2x improvement)
3. Bulk insert: 2000 → 5000 events/sec (2.5x improvement)

---

## Git Workflow & Commits

**Branch strategy**:
- `main`: Production-ready
- `develop`: Integration branch
- `feature/xxx`: Feature branches (from develop)
- `fix/xxx`: Bug fixes (from develop)

**Before commit**:
```bash
pytest tests/unit/ tests/integration/ -v -m "not benchmark"
black --check src/ tests/
ruff check src/ tests/
mypy src/athena
```

**Commit messages**: Follow conventional commits
```
feat: Add new feature
fix: Fix issue
refactor: Improve code structure
test: Add/update tests
docs: Update documentation
```

---

## Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview & quick start |
| `ARCHITECTURE.md` | Deep dive into 8-layer design |
| `DEVELOPMENT_GUIDE.md` | Detailed development instructions |
| `API_REFERENCE.md` | Complete MCP tool documentation |
| `CONTRIBUTING.md` | Contributing guidelines |
| `PROJECT_STATUS.md` | Current completion status |
| `PHASE_*_COMPLETION_REPORT.md` | Phase-specific documentation |

---

## Syntax-Aware Code Matching with ast-grep

For systematic code refactoring and pattern finding, use `ast-grep` instead of regex. It understands code structure, ignores comments/strings, and enables safe rewrites.

### Key Principles

- **Use ast-grep when**:
  - Refactoring API calls, variable names, or import forms
  - Enforcing patterns across a repo
  - Need to understand syntax (ignore strings/comments)
  - **Safe rewrites**: Apply changes to matched nodes

- **Use ripgrep when**:
  - Hunting for literals, TODOs, config values, non-code assets
  - Quick text-based search across files
  - Speed matters more than precision

### Common Patterns in Athena

**Find all class method definitions** (ignore docstrings):
```bash
ast-grep --lang python -p 'class $CLASS { function $METHOD($$$) { $$$ } }'
```

**Rename an API** (Python imports):
```bash
ast-grep run --lang python -p 'from $MOD import $OLD' -r 'from $MOD import new_name'
```

**Find all database queries** (understand context):
```bash
ast-grep --lang python -p 'db.execute($$$)'
```

**Identify async/await patterns** (TypeScript):
```bash
ast-grep run -l typescript -p 'async function $NAME() { $$$ await $CALL() }'
```

**Find unhandled error cases**:
```bash
ast-grep --lang python -p 'try { $$$ } catch { pass }'  # Catches silent failures
```

### Workflow: Combine rg + ast-grep

1. **Quick hunt** with ripgrep to narrow candidates:
   ```bash
   rg -l 'useQuery' src/  # Find files with useQuery
   ```

2. **Precise matching** with ast-grep:
   ```bash
   ast-grep run -l typescript -p 'useQuery($$$)' -r 'useSuspenseQuery($$$)'
   ```

3. **Verify changes** before committing:
   ```bash
   git diff --stat
   pytest tests/ -v
   ```

### ast-grep vs ripgrep Decision Tree

- **Need correctness over speed?** → ast-grep (understands syntax)
- **Just hunting text?** → ripgrep (fastest way)
- **Both together?** → ripgrep to pre-filter, ast-grep to match precisely

---

## Troubleshooting

### Tests Failing

1. **Ensure fresh database**: Tests use `tmp_path` fixture for isolation
2. **Check dependencies**: `pip install -e ".[dev]"` includes test deps
3. **Run with verbose output**: `pytest -v -s` shows detailed logs
4. **Check Python version**: Requires 3.10+ (use `python --version`)

### Memory Database Growing Too Large

1. **Run consolidation**: Use `adapter.execute_operation("consolidation", "extract", {...})` to extract patterns
2. **Monitor usage**: Query episodic_events table directly or use `adapter.get_detail()` for specifics
3. **Monitor size**: `du -h ~/.claude/memory-mcp/memory.db`

### MCP Tools Not Loading

1. **Check server startup**: `memory-mcp` should start without errors
2. **Verify imports**: All tool modules must import cleanly
3. **Check schemas**: Database tables created on first use
4. **Enable debug**: `DEBUG=1 memory-mcp` for detailed logs

---

## Key Files to Know

- `src/athena/manager.py` - Entry point for all memory operations
- `src/athena/mcp/handlers.py` - All MCP tool definitions
- `src/athena/consolidation/consolidator.py` - Pattern extraction engine
- `src/athena/core/database.py` - Database abstraction
- `tests/unit/test_*.py` - Layer unit tests (fixtures in test_*.py)

---

## Documentation Organization

The documentation structure follows a clear hierarchy for maintainability:

### Directory Structure

```
docs/
├── README.md              # Project overview (link from root)
├── ARCHITECTURE.md        # Technical architecture deep-dive
├── CLAUDE.md             # This file - Claude Code guidance
├── CONTRIBUTING.md       # How to contribute to the project
├── CHANGELOG.md          # Version history and breaking changes
├── DEVELOPMENT_GUIDE.md  # Development setup and workflow
├── API_REFERENCE.md      # Complete MCP tool documentation
├── USAGE_GUIDE.md        # User guide and common tasks
├── INSTALLATION.md       # Installation and setup instructions
├── CONFIGURATION.md      # Configuration options and environment
├── DEPLOYMENT_GUIDE.md   # Deployment and scaling
├── TESTING_GUIDE.md      # Testing strategy and running tests
├── TROUBLESHOOTING.md    # Common issues and solutions
├── EXAMPLES.md           # Code examples and usage patterns
├── tmp/                  # Temporary working documents
│   ├── SESSION_*.md      # Session summaries and resumé docs
│   ├── *_PROGRESS.md     # In-progress work reports
│   └── *.md              # Temporary analysis and planning docs
├── archive/              # Historical documentation
│   ├── PHASE_*.md        # Completed phase reports
│   ├── *_COMPLETE.md     # Historical completion reports
│   └── *.md              # Other archived docs
└── tutorials/            # Step-by-step guides
    ├── getting-started.md     # Quick start guide
    ├── memory-basics.md       # Understanding memory layers
    └── advanced-features.md   # Advanced usage patterns
```

### When to Create New Docs

**Create in `docs/` (standard documentation)**:
- Architecture decisions (ARCHITECTURE.md)
- API reference (API_REFERENCE.md)
- Development guides (DEVELOPMENT_GUIDE.md)
- Contribution guidelines (CONTRIBUTING.md)
- Installation steps (INSTALLATION.md)
- Changelog entries (CHANGELOG.md)

**Create in `docs/tmp/` (temporary/session docs)**:
- Session resumé documents (SESSION_N_SUMMARY.md)
- Progress reports on ongoing work (FEATURE_NAME_PROGRESS.md)
- Analysis documents for current investigation
- Work-in-progress planning documents
- Temporary notes and findings

**Move to `docs/archive/` when**:
- A session is complete and won't be edited again
- A progress report becomes historical (project completed)
- A temporary document becomes superseded by standard docs

### When to Update docs/CLAUDE.md

Update this file when you:
1. **Change project structure** - Update code organization section
2. **Establish new patterns** - Add to design patterns section
3. **Add critical guidance** - Document important decisions
4. **Change development workflow** - Update quick commands section

**Do NOT put in CLAUDE.md**:
- Session-specific details (use docs/tmp/)
- Temporary analysis (use docs/tmp/)
- Historical phase reports (use docs/archive/)
- User tutorials (use docs/tutorials/)

### Maintaining Documentation

**Update frequency**:
- **CLAUDE.md**: Every major feature (quarterly or on pattern changes)
- **ARCHITECTURE.md**: When adding layers or major refactors
- **CHANGELOG.md**: With every commit/release
- **docs/tmp/**: Every session (auto-clean old files)
- **docs/archive/**: When moving completed work (quarterly)

**Version updates**:
- Update version number in CLAUDE.md footer only when releasing
- Update "Last Updated" date whenever making significant changes

---

**Version**: 1.0 (Project-specific for Athena MCP)
**Status**: Production-ready prototype (95% complete)
**Last Updated**: November 13, 2025
