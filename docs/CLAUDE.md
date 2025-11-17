# CLAUDE.md - Developing Athena

This file guides development **on** the Athena memory system.

For guidance on **using** Athena from other projects, see `~/.claude/CLAUDE.md` or `README.md`.

---

## Quick Start

```bash
# Install in development mode
pip install -e .

# Run unit tests
pytest tests/unit/ -v

# Full test suite (6,133 core tests)
pytest tests/ -v --timeout=300

# Format and lint
black src/ tests/
ruff check --fix src/ tests/

# Type checking
mypy src/athena
```

---

## Architecture: Direct Python Imports (Optimal Design)

**NO MCP SERVER. NO PROTOCOL OVERHEAD.**

### How It Works

All memory operations are exposed as clean async Python functions:

```python
# Import operations directly
from athena.episodic.operations import remember, recall
from athena.semantic.operations import store, search

# Use them
event_id = await remember("User asked about timeline", tags=["meeting"])
results = await recall("timeline", limit=5)

fact_id = await store("Python is dynamically typed", topics=["programming"])
facts = await search("programming", limit=10)
```

### Operations Modules

Each memory layer has an `operations.py` module:
- `src/athena/episodic/operations.py` - Remember, recall, get_recent, get_by_session, get_by_tags, etc.
- `src/athena/memory/operations.py` - Semantic: store, search
- `src/athena/procedural/operations.py` - Workflows (upcoming)
- `src/athena/prospective/operations.py` - Tasks (upcoming)
- `src/athena/graph/operations.py` - Knowledge graph (upcoming)
- `src/athena/meta/operations.py` - Meta-memory (upcoming)
- `src/athena/consolidation/operations.py` - Pattern extraction (upcoming)
- `src/athena/planning/operations.py` - Planning (upcoming)

### Discovery (TypeScript Stubs)

Agents discover available operations by reading TypeScript files in `src/servers/`:
```typescript
// src/servers/episodic/remember.ts
export async function remember(
  content: string,
  tags?: string[],
  context?: Record<string, unknown>
): Promise<string>
```

These are pure type definitions. Agents read them to discover operations, then import Python functions directly.

### Why This Works

✅ **Token efficiency**: No serialization, no protocol overhead
✅ **Type safety**: Python types, not JSON
✅ **Performance**: Direct function calls, not network round-trips
✅ **Simplicity**: Import and call, no server process
✅ **Follows Anthropic paradigm**: Discover from code → Import → Execute locally

---

## Architecture: 8-Layer Memory System

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

**Status**: 95% complete, 94/94 tests passing ✅

---

## Code Organization

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
| `mcp/` | MCP server & tools | `handlers.py` (core), `handlers_*.py` (domain-organized) |

---

## Key Design Patterns

### 1. Layer Initialization

```python
class [Layer]Store:
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()  # Create tables on first use

    def _init_schema(self):
        """Create schema on-demand (idempotent)."""
        # Use db.execute() with CREATE TABLE IF NOT EXISTS
```

Benefits: Quick prototyping, test isolation, no migration management.

### 2. Query Routing

The `UnifiedMemoryManager` routes queries to appropriate layers:

```python
class QueryType:
    TEMPORAL = "temporal"           # Episodic layer
    FACTUAL = "factual"             # Semantic layer
    RELATIONAL = "relational"       # Knowledge graph
    PROCEDURAL = "procedural"       # Procedural layer
    PROSPECTIVE = "prospective"     # Prospective layer
    META = "meta"                   # Meta-memory
    PLANNING = "planning"           # Planning layer
```

### 3. Optional RAG Degradation

RAG components are optional (graceful fallback):

```python
try:
    from .rag import RAGManager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
```

### 4. Consolidation Dual-Process

```python
# System 1 (Fast, ~100ms)
clusters = statistical_clustering(events)
patterns = heuristic_extraction(clusters)

# System 2 (Slow, triggered when uncertainty > 0.5)
if pattern_uncertainty > 0.5:
    validated_patterns = llm_validate(patterns)
```

---

## Async/Sync Architecture

**All new code MUST be async-first**:

```python
# ✅ CORRECT - Async for I/O
async def save(self, skill: Skill) -> bool:
    await self.db.initialize()
    async with self.db.get_connection() as conn:
        await conn.execute(sql, params)
    return True

# ✅ CORRECT - Sync for pure computation
def _compute_relevance(self, task: str, skill: Skill) -> float:
    score = 0.0
    for keyword in skill.metadata.tags:
        if keyword.lower() in task.lower():
            score += 0.1
    return min(score, 1.0)

# ❌ WRONG - Missing await
async def execute(self, skill):
    result = self.library.save(skill)  # Missing await!
    return result
```

---

## Development Workflow

### Adding a New MCP Tool

1. Define in `src/athena/mcp/handlers.py`:
   ```python
   @self.server.tool()
   def my_new_tool(param1: str, param2: int) -> str:
       """Description of what the tool does."""
       return "result"
   ```

2. Test in `tests/mcp/`:
   ```python
   def test_my_new_tool():
       server = MemoryMCPServer()
       result = server.my_new_tool("test", 123)
       assert result == "expected"
   ```

3. Update API_REFERENCE.md

### Adding a New Memory Layer

1. Create `src/athena/[layer_name]/`
2. Implement `models.py`, `store.py`, `[operation].py`
3. Update `manager.py` (initialization, routing, public methods)
4. Add MCP tools in `src/athena/mcp/handlers.py`
5. Write tests in `tests/unit/test_[layer_name].py`

### Running Tests

```bash
# Unit + integration only (fast)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Single test file
pytest tests/unit/test_episodic_store.py -v

# Single test with output
pytest tests/unit/test_episodic_store.py::TestEpisodicStore::test_store_event -v -s

# With coverage
pytest tests/ --cov=src/athena --cov-report=html
```

### Code Style

```bash
# Auto-fix
black src/ tests/
ruff check --fix src/ tests/

# Type check (in venv)
mypy src/athena

# Verify before commit
black --check src/ tests/
ruff check src/ tests/
```

---

## Database Access

PostgreSQL with async/await:

```python
# High-level methods (preferred)
memory_id = db.store_memory(memory: Memory) -> int
memory = db.get_memory(memory_id: int) -> Optional[Memory]
success = db.delete_memory(memory_id: int) -> bool
memories = db.list_memories(project_id: int, ...) -> list[Memory]

# Direct connection (for complex queries)
cursor = db.conn.cursor()
cursor.execute(
    "SELECT * FROM memories WHERE project_id = ? AND usefulness_score > ?",
    (project_id, min_score)  # Always parameterized
)
results = cursor.fetchall()
db.conn.commit()
```

**Key Points**:
- Always use parameterized queries (prevents SQL injection)
- Database is PostgreSQL with async connection pooling
- Use transactions for multi-step operations
- Document WHY direct access is needed

---

## MCP Handlers Refactoring ✅

**Status**: All 335 handler methods refactored into domain-organized modules.

```
src/athena/mcp/
├── handlers.py (1,270 lines) - Core MemoryMCPServer class
├── handlers_episodic.py (1,232 lines) - Episodic memory (16 methods)
├── handlers_memory_core.py (349 lines) - Core operations (6 methods)
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

**Benefits**:
- ✅ 89.7% reduction in main file (12,363 → 1,270 lines)
- ✅ 148+ methods extracted into domain modules
- ✅ 100% backward compatible
- ✅ Clear separation of concerns

---

## Memory Storage and Hook Integration

### Where Memory Actually Lives

**Database**: PostgreSQL on `localhost:5432` (or `ATHENA_POSTGRES_HOST:ATHENA_POSTGRES_PORT`)

**Tables** (created automatically by MCP server):
- `episodic_events`: Individual events (tool use, user input, outputs)
- `prospective_tasks`: Goals, tasks, triggers
- `projects`: Project contexts
- `semantic_memories`: Learned facts and insights
- `knowledge_graph_*`: Entities, relations, communities
- `procedural_skills`: Learned workflows
- `meta_*`: Quality scores, expertise, attention

### How Hooks Access Memory

1. **Hook fires** (e.g., `PostToolUse` after a tool runs)
2. **Hook loads** `memory_bridge.py` (direct PostgreSQL connection)
3. **Hook queries** episodic_events, prospective_tasks tables
4. **Hook formats** results using `session_context_manager.py`
5. **Hook prints to stdout** (injected into Claude as "Working Memory")

**Example workflow**:
```
User submits input → PostToolUse fires
  ↓
Hook calls memory_bridge.get_active_memories(project_id, limit=7)
  ↓
Returns top 7 working memory items from PostgreSQL
  ↓
Hook formats with session_context_manager (includes importance scores)
  ↓
Prints to stdout: "## Working Memory" section
  ↓
Claude receives as context for next response
```

### If Hooks Aren't Injecting Memory

**Most likely cause**: PostgreSQL not accessible to hook processes.

**Verify**:
1. PostgreSQL is running: `psql -h localhost -U postgres -d athena -c "SELECT 1"`
2. Tables exist: `psql -h localhost -U postgres -d athena -c "\dt"`
3. Check environment vars: `env | grep ATHENA_POSTGRES`
4. Watch hook execution: Add `DEBUG=1` to see hook logs (stderr)

If hooks fail silently, check `~/.claude/hooks/` shell scripts - they catch exceptions and log to stderr.

---

## Anthropic Pattern Enforcement

All code **MUST** follow the pattern:

1. **Discover** → List available operations via filesystem
2. **Read** → Load only needed signatures
3. **Execute** → Process data locally
4. **Summarize** → Return 300-token max

**Why**: 98.7% token reduction + improved efficiency.

Example (✅ Correct):
```python
operations = list_directory("/athena/layers/semantic")
for op in operations:
    signature = read_file(f"/athena/layers/semantic/{op}")  # Just schema

results = execute("search", query, limit=5)  # Execute locally
summary = aggregate_results(results)  # Filter/process here
return {"count": len(results), "top_matches": summary[:3]}  # 300 tokens max
```

---

## Troubleshooting

### Tests Failing

1. Ensure fresh database: Tests use `tmp_path` fixture
2. Check dependencies: `pip install -e ".[dev]"`
3. Run with verbose output: `pytest -v -s`
4. Check Python version: Requires 3.10+

### MCP Server Not Starting

1. Check startup: `memory-mcp` should start cleanly
2. Verify imports: All modules must load
3. Check schemas: Tables created on first use
4. Enable debug: `DEBUG=1 memory-mcp`

### PostgreSQL Connection Failing

The memory system requires PostgreSQL to be running. The hooks use this to access memory.

1. Check if PostgreSQL is running: `psql -h localhost -U postgres -d athena -c "SELECT 1"`
2. Verify environment variables are set (or use defaults):
   ```bash
   echo "ATHENA_POSTGRES_HOST=${ATHENA_POSTGRES_HOST:-localhost}"
   echo "ATHENA_POSTGRES_PORT=${ATHENA_POSTGRES_PORT:-5432}"
   echo "ATHENA_POSTGRES_DB=${ATHENA_POSTGRES_DB:-athena}"
   echo "ATHENA_POSTGRES_USER=${ATHENA_POSTGRES_USER:-postgres}"
   ```
3. If tables don't exist, MCP server will create them on first run: `memory-mcp`
4. Check hook logs: `/home/user/.claude/hooks/` scripts run on SessionStart and PostToolUse events

### Memory Database Growing Large

1. Monitor usage: Query episodic_events directly via `psql`
2. Run consolidation: Extract patterns to compress episodic events
3. Check database size: `psql -h localhost -U postgres -d athena -c "SELECT pg_size_pretty(pg_database_size('athena'))"`

---

## Key Files

- `src/athena/manager.py` - Entry point for memory operations
- `src/athena/mcp/handlers.py` - MCP tool definitions
- `src/athena/consolidation/consolidator.py` - Pattern extraction
- `src/athena/core/database.py` - Database abstraction
- `tests/unit/test_*.py` - Layer unit tests

---

## Git Workflow

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

## Configuration

### PostgreSQL Setup (Required for Hooks)

Hooks require PostgreSQL to be running and accessible. Set these environment variables (or use defaults):

```bash
# Used by hooks (memory_bridge.py)
export ATHENA_POSTGRES_HOST=localhost         # default: localhost
export ATHENA_POSTGRES_PORT=5432              # default: 5432
export ATHENA_POSTGRES_DB=athena              # default: athena
export ATHENA_POSTGRES_USER=postgres          # default: postgres
export ATHENA_POSTGRES_PASSWORD=postgres      # default: postgres

# Used by MCP server and core system (config.py)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_MIN_POOL_SIZE=2
export DB_MAX_POOL_SIZE=10
```

**Critical**: Hooks will fail silently if PostgreSQL is not accessible. Check with:
```bash
psql -h ${ATHENA_POSTGRES_HOST:-localhost} -U postgres -d athena -c "SELECT 1"
```

### LLM Provider Configuration

**Embedding provider** (src/athena/core/config.py):
- `"ollama"` (local, requires Ollama running on http://localhost:11434)
- `"llamacpp"` (HTTP servers for embeddings + reasoning)
- `"claude"` (Anthropic API, requires ANTHROPIC_API_KEY)
- `"mock"` (testing only)

### Hook Environment

Hooks are configured in `~/.claude/settings.json` and execute in response to:
- `SessionStart`: Load working memory at session beginning
- `PreToolUse`: Validate execution environment
- `PostToolUse`: Record tool results to episodic memory
- `UserPromptSubmit`: Ground user input in spatial-temporal context
- `SessionEnd`: Consolidate session learnings

Hook helper libraries in `~/.claude/hooks/lib/`:
- `memory_bridge.py`: Direct PostgreSQL access for hooks
- `session_context_manager.py`: Format memory for Claude injection
- `advanced_context_intelligence.py`: Smart context selection
- `consolidation_helper.py`: Pattern extraction helpers

---

**Version**: 1.0 (Athena Development)
**Last Updated**: November 14, 2025
