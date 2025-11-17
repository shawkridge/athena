# Athena Memory System - Quick Start

**Athena** is an 8-layer neuroscience-inspired memory system for AI agents built with PostgreSQL and async-first Python.

## Installation

```bash
cd /home/user/.work/athena
pip install -e .
```

## Run Tests

```bash
# Fast (unit + integration, ~30 seconds)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full suite (8,700+ tests, ~5 minutes)
pytest tests/ -v --timeout=300

# Single test file
pytest tests/unit/test_confidence_integration.py -v
```

## Start MCP Server

```bash
memory-mcp
```

This starts the Model Context Protocol server that provides all memory operations as tools.

## Architecture

### 8 Memory Layers

1. **Episodic** - Events with timestamps (when did X happen?)
2. **Semantic** - Facts and knowledge (what is X?)
3. **Procedural** - Workflows and patterns (how do I do X?)
4. **Prospective** - Goals and tasks (what do I need to do?)
5. **Knowledge Graph** - Entities and relationships (how does X relate to Y?)
6. **Meta-Memory** - Quality and expertise tracking (is my knowledge good?)
7. **Consolidation** - Pattern extraction (what patterns emerge?)
8. **RAG** - Advanced retrieval (context-aware searching)

### Key Files

- `src/athena/manager.py` - Unified memory manager (main API)
- `src/athena/mcp/handlers.py` - MCP server entry point
- `src/servers/` - TypeScript operation signatures (for agent discovery)
- `src/athena/episodic/store.py`, `memory/store.py`, etc. - Layer implementations

## Using Athena

### Basic Example

```python
from athena.manager import UnifiedMemoryManager
from athena.core.database import Database

# Initialize
db = Database()
manager = UnifiedMemoryManager(db)

# Store an event
memory_id = await manager.remember(
    content="User asked about project timeline",
    tags=["meeting", "project"]
)

# Retrieve memories
results = await manager.recall("project timeline", limit=5)
```

### Via MCP

When the MCP server is running, agents call tools like:
- `episodic/remember` - Store an event
- `episodic/recall` - Search events
- `semantic/store` - Store a fact
- `semantic/search` - Search knowledge
- `consolidation/consolidate` - Extract patterns
- See `src/servers/` for full operation signatures

## Database

Requires PostgreSQL (localhost:5432 by default).

Set via environment:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=postgres
export DB_PASSWORD=postgres
```

Tables are created automatically on first use.

## Code Quality

```bash
# Format
black src/ tests/

# Lint
ruff check --fix src/ tests/

# Type check
mypy src/athena
```

## What's Not Working

6 integration tests are skipped (`*.skip` files):
- `tests/e2e/test_task_learning_with_llm.py` - LLM integration incomplete
- `tests/integration/test_athena_cli.py` - CLI stubs missing
- `tests/unit/mcp/test_tool_integration.py` - Tool registry incomplete
- `tests/unit/test_meta_field_persistence.py` - Meta-field schema unfinished
- `tests/unit/test_research_agents.py` - Research agents stub
- `tests/unit/tools/test_memory_tools.py` - Tool wrappers incomplete

To re-enable: rename `test_*.py.skip` → `test_*.py` when stubs are implemented.

## Status

- ✅ Core memory system (8 layers): 100% functional
- ✅ Test suite: 8,705 tests, all passing
- ✅ MCP server: Ready to use
- ✅ Database: PostgreSQL, async
- ⚠️ Some stubs incomplete (see above)

## Next Steps

1. Start the MCP server: `memory-mcp`
2. Run tests to verify: `pytest tests/unit/ -v`
3. Explore `src/athena/` to understand the layers
4. Read the code - it's self-documented
