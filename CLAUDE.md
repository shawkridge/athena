# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
```

**Memory Operations** (via MCP or CLI):
```bash
/memory-query "topic"          # Search memories with advanced RAG
/memory-health                 # Check system health + quality metrics
/consolidate                   # Extract patterns from episodic events
/project-status               # Overview with goal rankings + metrics
```

---

## Project Overview

**Athena** is a sophisticated 8-layer neuroscience-inspired memory system for AI agents. The key innovation is *sleep-like consolidation* - converting episodic events into semantic knowledge using dual-process reasoning (fast heuristics + slow LLM validation).

**Current Status**: 95% complete, 94/94 tests passing

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
SQLite + sqlite-vec (Local-first, no cloud)
Current: 8,128 episodic events, 101 procedures, 5.5MB database
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
| `mcp/` | MCP server & tools | `handlers.py` (main), `handlers_*.py` (specialized), `operation_router.py` |
| `manager.py` | Unified memory manager | Query routing, layer orchestration |

### MCP Server Architecture

The MCP server in `src/athena/mcp/` implements 27 tools with 228+ operations:

- **`handlers.py`** (526KB): Main server class `MemoryMCPServer` with all tool definitions
- **`handlers_*.py`**: Specialized handlers for tool groups:
  - `handlers_tools.py`: Memory core operations (recall, remember, forget, optimize)
  - `handlers_system.py`: System operations (health, monitoring, consolidation)
  - `handlers_planning.py`: Planning & validation operations
  - `handlers_retrieval.py`: Advanced RAG operations
  - `handlers_consolidation.py`: Consolidation strategy operations
  - `handlers_integration.py`: Cross-layer integration operations
  - `handlers_agent_optimization.py`: Agent optimization operations
  - `handlers_skill_optimization.py`: Skill enhancement operations
  - `handlers_hook_coordination.py`: Hook coordination operations
  - `handlers_slash_commands.py`: Slash command implementations

**Operation Routing**: `operation_router.py` dispatches tool calls to the appropriate handler based on operation name and parameters.

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

## Critical Implementation Details

### 1. Database Access

All database access goes through `Database` class in `src/athena/core/database.py`:

```python
# ✅ Correct
db.execute("INSERT INTO events ...", params)
db.execute_one("SELECT * FROM events WHERE id = ?", (event_id,))

# ❌ Don't do direct SQL
db.conn.execute(...)  # Dangerous, bypasses logging/monitoring
```

**Key Points**:
- Always use parameterized queries (prevent SQL injection)
- Database is local SQLite (no network calls)
- Vector search uses `sqlite-vec` extension (requires special setup)

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

1. **Environment variables**: `ANTHROPIC_API_KEY`, `OLLAMA_HOST`, `DEBUG`
2. **Config file**: `~/.claude/settings.local.json` (local user settings)
3. **Defaults**: Hardcoded in `src/athena/core/config.py`

**Precedence**: Env vars > local settings file > hardcoded defaults

### 5. Error Handling in Hooks

The hook system in `src/athena/hooks/` includes graceful degradation:

- If MCP tool fails, hook falls back to mock response
- If embedding generation fails, returns null vector
- Hooks always return valid JSON (never crash)

---

## Common Tasks

### Debugging Memory Layer Issues

1. **Check memory health**:
   ```bash
   /memory-health --detail
   ```

2. **Query the database directly**:
   ```python
   from athena.core.database import Database
   db = Database("memory.db")

   # List all tables
   tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'")

   # Inspect a table
   events = db.execute("SELECT * FROM episodic_events LIMIT 10")
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

### Why Local-First?

- **Privacy**: No data leaves local machine
- **Performance**: No network latency
- **Cost**: No API fees for basic operations
- **Reliability**: Works offline

### Why Dual-Process Consolidation?

- **System 1 (Fast)**: Statistical clustering gives baseline in <100ms
- **System 2 (Slow)**: LLM validation improves quality when needed
- **Hybrid**: Combines speed with accuracy for optimal performance

### Why Spatial-Temporal Grounding?

- **Code Understanding**: Hierarchical file paths map to code structure
- **Temporal Reasoning**: Automatic causality inference between events
- **Hybrid Scoring**: 70% semantic + 30% spatial balances both signals

### Why SQLite + sqlite-vec?

- **Simplicity**: Single file, no server
- **Performance**: <100ms most queries
- **Vectors**: sqlite-vec extension supports embedding storage
- **Maturity**: SQLite proven at scale

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

## Troubleshooting

### Tests Failing

1. **Ensure fresh database**: Tests use `tmp_path` fixture for isolation
2. **Check dependencies**: `pip install -e ".[dev]"` includes test deps
3. **Run with verbose output**: `pytest -v -s` shows detailed logs
4. **Check Python version**: Requires 3.10+ (use `python --version`)

### Memory Database Growing Too Large

1. **Run consolidation**: `/consolidate` extracts patterns, reduces storage
2. **Delete old events**: Use `/memory-forget ID` for low-value items
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

**Version**: 1.0 (Project-specific for Athena MCP)
**Status**: Production-ready prototype (95% complete)
**Last Updated**: November 5, 2025
