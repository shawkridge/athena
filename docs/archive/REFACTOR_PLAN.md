# Athena Refactoring Plan: Direct Python Imports (Optimal Architecture)

## Goal
Remove MCP protocol layer. Replace with direct Python imports following the Anthropic paradigm.

## Why This Is Better
- **Token efficiency**: No serialization/protocol overhead
- **Latency**: Function calls, not network round-trips
- **Debuggability**: Direct stack traces, not protocol messages
- **Type safety**: Python types, not JSON
- **Simplicity**: Import and call, no server process needed

## Architecture Overview

**Before (MCP Protocol):**
```
Agent → MCP Protocol → Python Process → PostgreSQL
         (serialization)
```

**After (Direct Imports):**
```
Agent Code → Python Functions (async) → PostgreSQL
            (in same process)
```

## Implementation Plan

### Phase 1: Extract Operations from Handlers (~2 hours)

#### 1.1 Identify all handler methods
- Scan `src/athena/mcp/handlers*.py`
- Find `async def _handle_*` methods (150+ methods)
- Map to layers: episodic, semantic, procedural, prospective, graph, meta, consolidation, planning

#### 1.2 Create operations modules for each layer
```
src/athena/episodic/operations.py      # Extract from handlers_episodic.py
src/athena/semantic/operations.py      # New, from handlers (memory store)
src/athena/procedural/operations.py    # Extract from handlers_procedural.py
src/athena/prospective/operations.py   # Extract from handlers_prospective.py
src/athena/graph/operations.py         # Extract from handlers_graph.py
src/athena/meta/operations.py          # Extract from handlers_metacognition.py
src/athena/consolidation/operations.py # Extract from handlers_consolidation.py
src/athena/planning/operations.py      # Extract from handlers_planning.py
```

#### 1.3 Extract handler logic
For each handler method:
- Remove MCP-specific wrapping (args dict unpacking, TextContent wrapping)
- Keep core logic
- Convert to `async def operation_name(param1, param2, ...) -> result_type`
- Handle errors properly (not as MCP responses, but as exceptions)

#### 1.4 Structure each operations module
```python
# src/athena/episodic/operations.py
async def remember(
    content: str,
    context: dict | None = None,
    tags: list[str] | None = None,
    source: str = "agent"
) -> str:
    """Store an event. Returns memory ID."""
    ...

async def recall(
    query: str,
    limit: int = 10,
    min_confidence: float = 0.5
) -> list[EpisodicEvent]:
    """Search events. Returns matching events."""
    ...
```

### Phase 2: Update UnifiedMemoryManager (~30 minutes)

#### 2.1 Current state
Manager instantiates MCP server and stores for each layer.

#### 2.2 New state
Manager imports operations modules and exposes them as methods OR provides direct access to operation functions.

Example:
```python
# Before: manager.recall("query") → calls through layers/cache
# After: from athena.episodic.operations import recall
#        result = await recall("query")
```

### Phase 3: Update Tests (~1 hour)

#### 3.1 Change imports
From: `from athena.mcp.handlers import MemoryMCPServer`
To: `from athena.episodic.operations import remember, recall`

#### 3.2 Update test calls
From:
```python
server = MemoryMCPServer()
result = server._handle_remember({"content": "..."})
```

To:
```python
result = await remember("content")
```

#### 3.3 Fix assertions
- Remove TextContent wrapping checks
- Assert on actual return types (str, list, dict)

### Phase 4: Update TypeScript Stubs (~30 minutes)

#### 4.1 Update src/servers/* files
- Keep discovery function signatures
- Update to match actual Python signatures
- Remove reference to callMCPTool (agents will import Python directly)

Example:
```typescript
// src/servers/episodic/remember.ts
/**
 * Store an event in episodic memory
 * @param content Event description
 * @param tags Optional tags for categorization
 * @param context Optional context metadata
 * @returns Memory ID
 */
export async function remember(
  content: string,
  tags?: string[],
  context?: Record<string, unknown>
): Promise<string>
```

### Phase 5: Remove MCP Infrastructure (~30 minutes)

#### 5.1 Keep but deprecate
- `src/athena/mcp/handlers.py` - Keep as wrapper layer (for backwards compatibility)
- `src/athena/cli:main` - Update to import operations directly
- Rate limiting - Move to `src/athena/core/rate_limit.py`

#### 5.2 Delete MCP-specific files
- `src/athena/mcp/__main__.py` - No longer needed
- `src/athena/mcp/operation_router.py` - Routing not needed
- `src/athena/mcp/structured_result.py` - MCP response wrapping not needed
- `src/athena/mcp/handler_middleware_wrapper.py` - MCP middleware not needed

#### 5.3 Update pyproject.toml
```toml
# Remove:
[project.scripts]
memory-mcp = "athena.cli:main"

# Replace with direct access via imports
```

### Phase 6: Update Documentation (~30 minutes)

#### 6.1 Update CLAUDE.md
```markdown
## Architecture: Direct Python Imports

All operations are exposed as async Python functions in each layer:

### Import & Call
\`\`\`python
from athena.episodic.operations import remember, recall
from athena.semantic.operations import store, search

# Store an event
memory_id = await remember("User asked about timeline", tags=["meeting"])

# Retrieve memories
results = await recall("timeline", limit=5)
\`\`\`

### Discovery for Agents
TypeScript files in `src/servers/` show available operations and signatures.
Agents read these files to discover what's available, then import the Python functions directly.

No MCP protocol. No external server process. Just Python async functions.
```

#### 6.2 Update START_HERE.md
Replace "Start MCP Server" with "Use Directly in Code"

### Phase 7: Run Tests & Fix Failures (~2 hours)

#### 7.1 Run test suite
```bash
pytest tests/unit/ -v
```

#### 7.2 Fix import errors
- Update all `from athena.mcp.handlers import`
- Update all handler call patterns

#### 7.3 Fix logic errors
- Some tests may depend on MCP-specific behavior
- Fix by calling operations directly

### Phase 8: Verify Integration (~30 minutes)

#### 8.1 Create integration example
```python
# examples/direct_usage.py
async def main():
    from athena.episodic.operations import remember, recall
    from athena.consolidation.operations import consolidate

    # Store events
    id1 = await remember("First meeting", tags=["meeting"])
    id2 = await remember("Second meeting", tags=["meeting"])

    # Retrieve
    results = await recall("meeting", limit=10)

    # Extract patterns
    patterns = await consolidate(limit=10)

    return patterns
```

#### 8.2 Verify it works
- Run example
- Check performance (should be faster than MCP)
- Verify types match expectations

## Effort Estimate

| Phase | Time | Complexity |
|-------|------|-----------|
| 1. Extract operations | 2 hours | Medium |
| 2. Update manager | 30 min | Low |
| 3. Update tests | 1 hour | Medium |
| 4. Update TypeScript | 30 min | Low |
| 5. Remove MCP code | 30 min | Low |
| 6. Update docs | 30 min | Low |
| 7. Fix failures | 2 hours | High |
| 8. Verify integration | 30 min | Low |
| **Total** | **~7 hours** | **Medium** |

## Execution Order

1. Start with one layer (episodic) as proof of concept
2. Verify tests pass with direct imports
3. Extract remaining 7 layers
4. Run full test suite
5. Update documentation
6. Commit with comprehensive message

## Rollback Plan

If issues arise:
- Keep MCP server code in place (just don't use it)
- Revert operations modules to handlers
- No data loss (PostgreSQL unchanged)

## Success Criteria

✅ All 8,705 tests pass with direct imports
✅ No MCP protocol in execution path
✅ Operations discoverable from TypeScript signatures
✅ Agent code looks like: `from athena.episodic import recall; await recall(...)`
✅ Documentation reflects optimal architecture
