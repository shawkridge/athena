# Athena Architecture Guide

**For Claude Sessions**: This document explains how Athena works internally so you can understand, debug, and improve the system.

**Status**: 95% complete, production-ready. 50+ subsystems, 8,128 episodic events, 101 learned procedures.

---

## System Overview

Athena is a persistent memory system for Claude Code instances on this machine. It works like human memory: recording experiences, extracting patterns, and making knowledge available across sessions and projects.

### Core Purpose

- **Cross-session memory**: Remember what happened in previous sessions
- **Cross-project memory**: Recall insights from any project when working on a new one
- **Pattern learning**: Automatically extract reusable workflows and best practices
- **Knowledge graph**: Track relationships between concepts and domains
- **Context injection**: Load relevant working memory at session start

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code Instance (Any Project)                      │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ MCP Interface (27 tools, 228+ operations)               │
│ - Memory tools (recall, remember, forget)               │
│ - Planning tools (plan_task, validate_plan)             │
│ - Consolidation tools (consolidate, get_patterns)       │
│ - Graph tools (query, analyze)                          │
│ - Retrieval tools (hybrid search)                       │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 8: Supporting Infrastructure                      │
│ - RAG (Reflective, HyDE, Reranking)                    │
│ - Advanced Planning (Verification, Scenario Testing)    │
│ - Zettelkasten (Hierarchical associations)              │
│ - GraphRAG (Community detection)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 7: Consolidation                                  │
│ - Dual-process pattern extraction                       │
│ - Fast System 1: Statistical clustering (~100ms)        │
│ - Slow System 2: LLM validation (triggered on high      │
│   uncertainty)                                          │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 6: Meta-Memory                                    │
│ - Quality scores (usefulness, accuracy, recency)        │
│ - Attention allocation (which memories get focus)       │
│ - Cognitive load (working memory capacity)              │
│ - Expertise tracking (domains of strength)              │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 5: Knowledge Graph                                │
│ - Entities (concepts, tools, projects)                  │
│ - Relations (causality, similarity, depends-on)         │
│ - Communities (domains, problem spaces)                 │
│ - Observations (empirical findings)                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 4: Prospective Memory                             │
│ - Tasks (what needs doing)                             │
│ - Goals (long-term objectives)                         │
│ - Triggers (when to act)                               │
│ - Status tracking                                       │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 3: Procedural Memory                              │
│ - Reusable workflows (101 currently extracted)           │
│ - Pattern-based execution                               │
│ - Skill composition                                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 2: Semantic Memory                                │
│ - Vector embeddings (semantic meaning)                  │
│ - BM25 full-text search (keyword matching)              │
│ - Hybrid search (combine both)                          │
│ - Fact storage                                          │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ Layer 1: Episodic Memory                                │
│ - Events (tool use, decisions, outcomes)                │
│ - Spatial-temporal grounding (when, where, context)     │
│ - Raw experience recording                              │
│ - Event buffer (current session)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│ PostgreSQL (Async-first, connection pooling)            │
│ - 20+ schema tables                                     │
│ - Full-text search indices                             │
│ - Vector similarity support                            │
└──────────────────────────────────────────────────────────┘
```

---

## Data Flow: How Athena Records & Retrieves Memory

### Recording a Memory (During Session)

```
1. Tool execution happens
   └─> PostToolUse hook fires automatically

2. Hook runs post-tool-use.sh
   └─> Loads memory_bridge.py (PostgreSQL access)
   └─> Creates episodic event
   └─> Stores: {action, outcome, timestamp, project_id, tags}

3. Event stored in episodic_events table
   └─> Indexed by timestamp + full-text search

4. Session-end (SessionEnd hook)
   └─> Consolidation runs automatically
   └─> Extracts patterns from episodic events
   └─> Stores in procedural_skills table
   └─> Updates semantic_memories table
```

### Retrieving Memory (Start of New Session)

```
1. Session starts
   └─> SessionStart hook fires

2. Hook loads memory_bridge.py + session_context_manager.py
   └─> Queries episodic_events table
   └─> Runs consolidation_helper for smart selection
   └─> Selects top 7±2 working memory items by importance

3. Working memory formatted as markdown
   └─> "## Working Memory" section
   └─> Includes importance scores
   └─> Injected into Claude's context

4. Claude can explicitly query via recall() tool
   └─> Searches semantic_memories + episodic_events
   └─> Uses hybrid search (vector + BM25)
   └─> Returns relevant memories with scores
```

---

## Code Organization

### Core Infrastructure (`src/athena/core/`)
- `database.py` - PostgreSQL async connection, schema management
- `config.py` - Configuration from environment variables
- `models.py` - Data models for all memory types
- `base.py` - Abstract base classes for layers

### Memory Layers (`src/athena/[layer]/`)

| Layer | Directory | Key Files | Purpose |
|-------|-----------|-----------|---------|
| 1 | `episodic/` | storage.py, buffer.py, temporal.py | Record events |
| 2 | `semantic/` | search.py, embeddings.py, store.py | Store facts |
| 3 | `procedural/` | extraction.py, procedures.py | Learn workflows |
| 4 | `prospective/` | tasks.py, goals.py, triggers.py | Track goals |
| 5 | `graph/` | store.py, communities.py, observations.py | Track relationships |
| 6 | `meta/` | quality.py, expertise.py, attention.py | Track quality |
| 7 | `consolidation/` | consolidator.py, clustering.py, patterns.py | Extract patterns |
| 8 | `rag/`, `planning/`, `associations/` | Various | Supporting layers |

### MCP Server (`src/athena/mcp/`)
- `handlers.py` (1,270 lines) - Main MemoryMCPServer class
- `handlers_episodic.py` - Episodic layer tools (16 methods)
- `handlers_memory_core.py` - Core operations (6 methods)
- `handlers_procedural.py` - Procedural tools (21 methods)
- `handlers_prospective.py` - Prospective tools (24 methods)
- `handlers_graph.py` - Graph tools (10 methods)
- `handlers_consolidation.py` - Consolidation tools (16 methods)
- `handlers_planning.py` - Planning tools (29 methods)
- `handlers_metacognition.py` - Meta-memory tools (8 methods)
- `handlers_system.py` - System tools (34 methods)

### Hooks & Integration (`claude/hooks/`)
- `session-start.sh` - Load working memory at session start
- `session-end.sh` - Consolidate learnings at session end
- `post-tool-use.sh` - Record tool results automatically
- `user-prompt-submit.sh` - Ground user input in context
- `pre-execution.sh` - Validate environment before execution

### Hook Libraries (`claude/hooks/lib/`)
- `memory_bridge.py` (12,128 lines) - Direct PostgreSQL access for hooks
- `session_context_manager.py` (15,773 lines) - Format memory for injection
- `advanced_context_intelligence.py` (19,657 lines) - Smart memory selection
- `consolidation_helper.py` (23,066 lines) - Pattern extraction helpers
- `athena_http_client.py` (22,562 lines) - HTTP API client
- And 24 more helper modules

### Tools & Skills (`src/athena/tools/` & `claude/skills/`)
- `tools/` - Filesystem-discoverable tool files
- `skills/` - 30+ reusable skills for Claude to invoke

---

## Key Design Patterns

### 1. Layer Initialization (On-Demand Schema Creation)

```python
class [LayerName]Store:
    def __init__(self, db: Database):
        self.db = db
        self._init_schema()  # Create tables if they don't exist

    def _init_schema(self):
        """Create schema on first use (idempotent)."""
        # Tables created with CREATE TABLE IF NOT EXISTS
        # No migration management needed
        # Quick for prototyping, safe for testing
```

**Why**: No migration files to maintain, schema evolves with code, safe concurrent initialization.

### 2. Query Routing (Unified Manager)

```python
class UnifiedMemoryManager:
    # Routes queries to appropriate layers based on type
    async def query(self, query_text: str, query_type: str) -> List:
        if query_type == QueryType.TEMPORAL:
            return await self.episodic.search(query_text)
        elif query_type == QueryType.FACTUAL:
            return await self.semantic.search(query_text)
        elif query_type == QueryType.RELATIONAL:
            return await self.graph.query(query_text)
        # ... etc
```

**Why**: Single entry point, type-safe routing, consistent interface.

### 3. Dual-Process Consolidation (Fast + Slow Thinking)

```python
# System 1: Fast consolidation (~100ms)
# - Statistical clustering of episodic events
# - Heuristic pattern extraction
# - Low certainty patterns
clusters = self._cluster_events(events)
fast_patterns = self._heuristic_extraction(clusters)

# System 2: Slow consolidation (triggered if uncertainty > 0.5)
# - LLM validation of uncertain patterns
# - Semantic verification
# - High-confidence results
if self._pattern_uncertainty(fast_patterns) > 0.5:
    validated = await self._llm_validate(fast_patterns)
    return validated
return fast_patterns
```

**Why**: Fast learning for common cases, careful validation when uncertain.

### 4. Async-First Architecture

```python
# ✅ CORRECT: Async for I/O operations
async def remember(self, content: str, tags: List[str]) -> str:
    await self.db.initialize()
    async with self.db.get_connection() as conn:
        event_id = await self.episodic.store(content, tags)
    return event_id

# ✅ CORRECT: Sync for computation
def _compute_relevance(self, memory: Memory, query: str) -> float:
    score = 0.0
    for tag in memory.tags:
        if tag in query.lower():
            score += 0.1
    return min(score, 1.0)

# ❌ WRONG: Mixing sync and async without await
async def broken(self):
    result = self.sync_operation()  # Missing await if this is async!
    return result
```

**Why**: I/O operations (database, network) are async to not block. Pure computation stays sync.

---

## PostgreSQL Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `episodic_events` | Raw experiences | id, content, event_type, timestamp, project_id, tags |
| `semantic_memories` | Learned facts | id, content, embedding, importance_score, tags |
| `procedural_skills` | Workflows | id, name, steps, frequency_used, success_rate |
| `prospective_tasks` | Current goals | id, description, status, due_date, triggers |
| `knowledge_graph_entities` | Concepts | id, name, type, domain, definition |
| `knowledge_graph_relations` | Connections | id, entity1_id, entity2_id, relation_type, strength |
| `meta_quality_scores` | Memory quality | id, memory_id, usefulness, accuracy, recency |
| `meta_expertise` | Domain expertise | id, domain, competence_score, experience_count |
| `working_memory` | Current focus | id, memory_id, importance_score, session_id |

### Indices
- Full-text search on episodic_events.content
- Vector similarity on semantic_memories.embedding
- Temporal index on episodic_events.timestamp
- Project index on episodic_events.project_id

---

## MCP Tools: Available Operations

### Memory Tools (recall, remember, forget)
- Query across all layers with unified search interface
- Full-text + semantic hybrid search
- Automatic importance scoring

### Planning Tools (plan_task, validate_plan)
- Formal verification of plans
- Scenario simulation
- Risk assessment

### Consolidation Tools (consolidate, get_patterns)
- Manual pattern extraction
- Retrieve learned workflows
- Quality metrics

### Graph Tools (query, analyze)
- Knowledge graph traversal
- Entity relationship analysis
- Community detection

### Retrieval Tools (hybrid, advanced_search)
- Advanced search strategies
- Reranking
- Reflective retrieval

---

## Extension Points: How to Improve Athena

### Adding a New Memory Layer

1. **Create directory structure**:
   ```
   src/athena/my_layer/
   ├── __init__.py
   ├── models.py       # Data models for this layer
   ├── store.py        # Persistence logic
   └── operations.py   # Layer-specific operations
   ```

2. **Implement Store class**:
   ```python
   class MyLayerStore:
       def __init__(self, db: Database):
           self.db = db
           self._init_schema()

       def _init_schema(self):
           # CREATE TABLE IF NOT EXISTS my_layer_data...
   ```

3. **Add to UnifiedMemoryManager**:
   ```python
   # In manager.py __init__
   self.my_layer = MyLayerStore(self.db)

   # Add public methods that delegate to this layer
   async def my_layer_operation(self, param: str) -> Result:
       return await self.my_layer.do_something(param)
   ```

4. **Register MCP tools** in `src/athena/mcp/handlers.py`:
   ```python
   @self.server.tool()
   async def my_new_tool(self, param: str) -> str:
       """Description of what this does."""
       result = await self.manager.my_layer_operation(param)
       return result
   ```

5. **Write tests** in `tests/unit/test_my_layer.py`

### Adding a New Hook

1. **Create hook script** in `~/.claude/hooks/`:
   ```bash
   #!/bin/bash
   # Hook that does something useful
   ```

2. **Add to settings.json** under the appropriate event:
   ```json
   {
     "hooks": {
       "SessionStart": [{ "hooks": [{ "type": "command", "command": "~/.claude/hooks/my-hook.sh" }] }]
     }
   }
   ```

3. **Access memory** via memory_bridge:
   ```python
   from lib.memory_bridge import get_active_memories
   memories = get_active_memories(project_id, limit=7)
   ```

### Adding a New Skill

1. **Create skill directory** in `~/.claude/skills/my-skill/`:
   ```
   SKILL.md        # Usage documentation
   prompt.md       # The actual prompt/instructions
   examples.md     # Example usage
   ```

2. **Document when to use it** in SKILL.md:
   ```markdown
   # My Skill

   ## When to Use
   - Use when you need to...
   - Use if you're...

   ## How to Invoke
   /my-skill [parameters]
   ```

---

## Debugging Guide

### Problem: Memory Not Being Recorded

**Check**:
1. PostgreSQL is running: `psql -h localhost -U postgres -d athena -c "SELECT 1"`
2. Tables exist: `psql -h localhost -U postgres -d athena -c "\dt"`
3. Hooks are executing: Check `~/.claude/hooks/*.sh` are executable
4. Environment variables set:
   ```bash
   export ATHENA_POSTGRES_HOST=localhost
   export ATHENA_POSTGRES_PORT=5432
   export ATHENA_POSTGRES_DB=athena
   export ATHENA_POSTGRES_USER=postgres
   export ATHENA_POSTGRES_PASSWORD=postgres
   ```

**Debug**:
```bash
# Watch hook execution
tail -f ~/.claude/hooks/logs/*

# Verify memory is stored
psql -h localhost -U postgres -d athena \
  -c "SELECT COUNT(*) FROM episodic_events;"

# Check hook output
DEBUG=1 bash ~/.claude/hooks/post-tool-use.sh
```

### Problem: Tools Not Discoverable

**Check**:
1. Tools generated: `ls ~/.work/athena/src/athena/tools/`
2. Tool files are readable: `cat ~/.work/athena/src/athena/tools/memory/recall.py`
3. INDEX.md exists: `cat ~/.work/athena/src/athena/tools/INDEX.md`

**Debug**:
```python
# Test tool discovery
import sys
sys.path.insert(0, '/home/user/.work/athena/src')

from pathlib import Path
tools_dir = Path('/home/user/.work/athena/src/athena/tools')
for tool_file in tools_dir.glob('*/*.py'):
    if tool_file.name != '__init__.py':
        print(f"Tool: {tool_file.relative_to(tools_dir)}")
```

### Problem: Consolidation Not Extracting Patterns

**Check**:
1. Episodic events exist: Count in database
2. Consolidation threshold: Default is uncertainty > 0.5
3. LLM provider configured: Check config.py for embeddings_provider

**Debug**:
```python
# Manually trigger consolidation
from athena.manager import UnifiedMemoryManager

async def debug_consolidation():
    manager = UnifiedMemoryManager()
    await manager.initialize()

    # Check recent events
    events = await manager.episodic.get_recent(days=7)
    print(f"Recent events: {len(events)}")

    # Run consolidation
    report = await manager.consolidate()
    print(f"Patterns extracted: {len(report.patterns)}")
    print(f"Confidence scores: {report.confidence_scores}")
```

---

## Performance Optimization

### Query Optimization

1. **Use hybrid search** for broad queries:
   ```python
   # Good: Combines semantic + full-text
   results = await manager.semantic.hybrid_search(query, limit=10)
   ```

2. **Index frequently queried fields**:
   - timestamp (for temporal queries)
   - project_id (for project context)
   - tags (for categorical queries)

3. **Use pagination** for large result sets:
   ```python
   results = await manager.episodic.search(query, limit=10, offset=page*10)
   ```

### Memory Optimization

1. **Archive old events**: Consolidation extracts patterns, allowing deletion of raw events
2. **Compression**: Store procedural skills (learned workflows) instead of raw event sequences
3. **Connection pooling**: DB_MIN_POOL_SIZE=2, DB_MAX_POOL_SIZE=10

### Database Optimization

```bash
# Monitor database size
psql -h localhost -U postgres -d athena \
  -c "SELECT pg_size_pretty(pg_database_size('athena'));"

# Run VACUUM to reclaim space
psql -h localhost -U postgres -d athena -c "VACUUM;"

# Check slow queries
psql -h localhost -U postgres -d athena \
  -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC;"
```

---

## Key Files

- `src/athena/manager.py` - Entry point for all operations
- `src/athena/mcp/handlers.py` - MCP tool definitions
- `src/athena/core/database.py` - Database abstraction
- `src/athena/consolidation/consolidator.py` - Pattern extraction
- `claude/hooks/` - Integration hooks
- `pyproject.toml` - Package configuration, dependencies

---

## Related Documentation

- `~/.claude/CLAUDE.md` - How to use Athena from any project
- `~/.work/athena/CLAUDE.md` - Development guide for Athena itself
- `~/.work/athena/src/athena/tools/INDEX.md` - Available tools
- `~/.claude/skills/*/SKILL.md` - Skill documentation
