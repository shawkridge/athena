---
category: skill
name: add-mcp-tool
description: Guide through creating new MCP tools with proper structure, tests, and documentation
allowed-tools: ["Bash", "Read", "Write", "Glob", "Grep", "Edit"]
confidence: 0.92
trigger: User is adding new MCP tool to Memory MCP project, or mentions "add tool", "new tool", "expose via MCP"
---

# Add MCP Tool Skill

Guides creation of new MCP tools following Memory MCP project patterns and conventions.

## When I Invoke This

You're:
- Adding a new capability that should be exposed via MCP
- Creating a tool to wrap existing memory layer functionality
- Exposing a new operation or analysis function to MCP clients
- Need to follow Memory MCP tool patterns (error handling, async, docstrings)

## What I Do

I guide you through this 5-step process:

```
1. DESIGN Phase: Understand what tool to create
   → What problem does it solve?
   → What memory layer(s) does it access?
   → What parameters (required vs optional)?
   → What should it return?

2. IMPLEMENT Phase: Create the tool handler
   → Generate proper async handler with @mcp.tool() decorator
   → Implement error handling (try/except with informative returns)
   → Add comprehensive docstring (What, Args, Returns, Examples)
   → Import necessary types and functions

3. INTEGRATION Phase: Hook it into MCP server
   → Add to src/memory_mcp/mcp/handlers.py in MemoryMCPServer class
   → Validate it compiles (no syntax errors)
   → Check it follows project error handling patterns

4. TEST Phase: Create comprehensive tests
   → Unit test: Happy path, edge cases, error cases
   → Integration test: Multi-layer workflows
   → Verify tests pass before moving on
   → Check error messages are helpful

5. DOCUMENTATION Phase: Document the tool
   → Update README.md with new tool
   → Add to MCP tool matrix if applicable
   → Document parameters and return types
   → Include usage examples
```

## Project Patterns to Follow

### 1. Tool Signature Pattern

```python
@mcp.tool()
async def my_new_tool(
    self,
    required_param: str,
    optional_param: int = 10,
    option_param: Optional[str] = None
) -> dict:
    """Human-readable tool description with examples.

    What the tool does and when to use it. Should be clear and specific.

    Args:
        required_param: Description of what this parameter does
        optional_param: Description (default: 10 means this)
        option_param: Description of optional choices

    Returns:
        dict with keys:
            - status: "success" or "error"
            - data: Result if successful
            - error: Error message if failed

    Example:
        >>> result = my_new_tool(required_param="value")
        >>> print(result["status"])
        "success"
    """
    try:
        # Implementation here
        result = self.some_store.operation(required_param, optional_param)
        return {"status": "success", "data": result}
    except ValueError as e:
        return {"status": "error", "error": f"Invalid parameter: {e}"}
    except Exception as e:
        return {"status": "error", "error": f"Unexpected error: {e}"}
```

### 2. Error Handling Pattern

Always return dict with status field:
- ✓ `{"status": "success", "data": ...}` for success
- ✓ `{"status": "error", "error": "description"}` for errors
- Never raise exceptions to MCP client
- Provide actionable error messages

### 3. Validation Pattern

```python
# Validate inputs early
try:
    if not required_param:
        return {"status": "error", "error": "required_param cannot be empty"}

    if optional_param < 1 or optional_param > 100:
        return {"status": "error", "error": "optional_param must be 1-100"}

    # Then proceed with operation
    result = self.store.operation(required_param, optional_param)
    return {"status": "success", "data": result}
except Exception as e:
    return {"status": "error", "error": str(e)}
```

### 4. Async Pattern

All MCP tools should be async:

```python
@mcp.tool()
async def my_tool(self, param: str) -> dict:  # async def
    """Tool description."""
    try:
        # Can use await if calling async functions
        result = await self.some_async_operation(param)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## File Locations Reference

| File | Purpose |
|------|---------|
| `src/memory_mcp/mcp/handlers.py` | Where you add the @mcp.tool() method |
| `src/memory_mcp/<layer>/store.py` | Where underlying operation likely lives |
| `tests/unit/test_mcp_tools.py` | Where unit tests for tools go |
| `tests/integration/test_mcp_integration.py` | Where integration tests go |
| `README.md` | Where you document the new tool |

## Example Workflow

### Scenario: Adding a "summarize-memory" tool

**Design Phase**:
- Problem: Users want quick summary of what's in memory
- Layer: Semantic memory + episodic memory
- Parameters: optional filter by type, optional limit
- Returns: Count, summary, key concepts

**Implementation Phase**:
```python
@mcp.tool()
async def summarize_memory(
    self,
    memory_type: Optional[str] = None,
    limit: int = 5
) -> dict:
    """Summarize stored memories with key insights.

    Provides overview of what's in your memory system,
    optionally filtered by memory type.

    Args:
        memory_type: Filter by "semantic", "episodic", "procedural" (optional)
        limit: Max number of top items to show (default: 5)

    Returns:
        dict with: count, top_items, key_concepts, coverage
    """
    try:
        if memory_type and memory_type not in ["semantic", "episodic", "procedural"]:
            return {"status": "error", "error": f"Unknown type: {memory_type}"}

        result = self.semantic_store.summarize(memory_type, limit)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

**Test Phase**:
```python
@pytest.mark.asyncio
async def test_summarize_memory(mcp_server):
    # Test basic call
    result = await mcp_server.summarize_memory()
    assert result["status"] == "success"
    assert "data" in result

    # Test with type filter
    result = await mcp_server.summarize_memory(memory_type="semantic")
    assert result["status"] == "success"

    # Test invalid type
    result = await mcp_server.summarize_memory(memory_type="invalid")
    assert result["status"] == "error"
    assert "Unknown type" in result["error"]
```

**Documentation Phase**:
```markdown
### summarize_memory

Summarize what's in your memory system.

```python
await mcp.summarize_memory(memory_type="semantic", limit=10)
```

Returns summary of key memories, concepts, and coverage stats.
```

## Step-by-Step Checklist

- [ ] **Design**: Problem clear? Parameters defined? Return shape clear?
- [ ] **Implement**: Handler written with error handling? Docstring comprehensive?
- [ ] **Integration**: Added to MemoryMCPServer? Imports correct? No syntax errors?
- [ ] **Test**: Unit tests pass? Integration tests pass? Error cases covered?
- [ ] **Document**: README updated? Examples clear? Tool is discoverable?
- [ ] **Validate**: Run full test suite? All tests pass? No regressions?

## Common Mistakes to Avoid

❌ **Mistake**: Raising exceptions to MCP
✓ **Fix**: Return `{"status": "error", "error": "message"}` instead

❌ **Mistake**: Missing docstring with Args/Returns
✓ **Fix**: Comprehensive docstring required (users can't see code)

❌ **Mistake**: Optional parameters with no validation
✓ **Fix**: Validate parameter ranges early, return helpful errors

❌ **Mistake**: Synchronous function that blocks
✓ **Fix**: Make async, use await for I/O operations

❌ **Mistake**: Unclear return shape
✓ **Fix**: Always use consistent {"status": ..., "data": ..., "error": ...} structure

❌ **Mistake**: No tests for error cases
✓ **Fix**: Test both success and all error paths

## Related Skills

- **query-strategist** - For tools that search memory
- **insight-generator** - For tools that analyze data
- **task-planner** - For tools that create tasks

## Success Criteria

✓ Tool solves a real problem
✓ Handler compiles without errors
✓ Error handling is comprehensive
✓ Tests cover happy path + edge cases + errors
✓ Documentation is clear with examples
✓ All tests pass (unit + integration)
✓ README updated with tool description
