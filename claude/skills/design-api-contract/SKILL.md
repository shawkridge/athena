---
category: skill
name: design-api-contract
description: Design stable, well-documented API contracts for MCP tools and layer interfaces
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.79
trigger: Adding new MCP tool, changing API, breaking change risk, "contract" mentioned, API stability needed
---

# Design API Contract Skill

Guides design of stable, backward-compatible API contracts for Memory MCP tools and layer interfaces.

## When I Invoke This

You have:
- New MCP tool to design (before implementation)
- Existing tool API change needed
- Worried about breaking changes
- Need inter-layer interface definition
- Want API versioning strategy

## What I Do

I guide API contract design in these phases:

```
1. DEFINE Phase: Specify the contract
   → What inputs are required/optional?
   → What outputs are guaranteed?
   → What can change safely?
   → What's stable (guaranteed) vs unstable?

2. VALIDATE Phase: Check for completeness
   → Are all edge cases handled?
   → Are types fully specified?
   → Is error handling clear?
   → Are examples provided?

3. DOCUMENT Phase: Create contract docs
   → Parameter documentation
   → Return value documentation
   → Error conditions documented
   → Examples for common use cases

4. IMPLEMENT Phase: Enforce the contract
   → Validation at entry point
   → Type checking
   → Error handling matching contract
   → No undocumented behavior

5. EVOLVE Phase: Plan for changes
   → What if we need to add parameters?
   → Deprecation strategy
   → Backward compatibility plan
   → Version signaling
```

## API Contract Design Principles

### Principle 1: Explicit Contracts (Not Implicit Dependencies)

```python
# ❌ Bad: Implicit contract, no docs
def create_memory(content):
    # Assumes content is string? list? dict?
    # What if content is empty?
    # Returns what? Model or dict or ID?
    return self.store.create(content)

# ✓ Good: Explicit contract with types
def create_memory(self, content: str) -> MemoryModel:
    """Create semantic memory from content.

    Args:
        content: Non-empty text content (required)
                 Must be 1-10000 characters

    Returns:
        MemoryModel with id, content, embedding, created_at

    Raises:
        ValueError: If content empty or >10000 chars
        DatabaseError: If storage fails

    Example:
        >>> memory = manager.create_memory("Learn Python")
        >>> memory.id
        42
    """
    if not content or not content.strip():
        raise ValueError("Content required and non-empty")
    if len(content) > 10000:
        raise ValueError("Content must be <10000 characters")

    try:
        return self.store.create(content)
    except Exception as e:
        raise DatabaseError(f"Failed to create memory: {e}") from e
```

**Key**: Types, constraints, examples, error cases all explicit

---

### Principle 2: Input Validation (Fail Fast, Fail Clearly)

```python
# ❌ Bad: Silent failures
def search(query, limit=10):
    # What if query is None? Empty? Not a string?
    # What if limit is negative?
    # What if limit is 1 million?
    results = self.store.search(query, limit)
    return results

# ✓ Good: Explicit validation with clear errors
def search(self, query: str, limit: int = 10) -> list[MemoryModel]:
    """Search for memories matching query.

    Args:
        query: Search query (1-1000 characters)
        limit: Max results (1-1000, default: 10)

    Returns:
        list[MemoryModel] ranked by relevance, or empty list

    Raises:
        ValueError: If query/limit out of range
        SearchError: If search fails
    """
    # Validate input
    if not query or not isinstance(query, str):
        raise ValueError("Query must be non-empty string")
    if len(query) > 1000:
        raise ValueError("Query must be <1000 characters")
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        raise ValueError("Limit must be int between 1-1000")

    try:
        return self.store.search(query, limit)
    except Exception as e:
        raise SearchError(f"Search failed: {e}") from e
```

**Key**: Validate every input; give specific error messages

---

### Principle 3: Stable Return Types (Never Change Structure)

```python
# ❌ Bad: Return type changes over time
def get_memory(id):
    # v1: returned dict with {'content': ..., 'id': ...}
    # v2: changed to return MemoryModel object (BREAKING!)
    # v3: changed back to dict but different fields
    # Clients break with every change!
    result = self.store.get(id)
    return result

# ✓ Good: Return type is stable, additions are backward compatible
def get_memory(self, id: int) -> Optional[MemoryModel]:
    """Get memory by ID or None if not found.

    Returns MemoryModel with:
    - id: int (always present, never changes)
    - content: str (always present, never changes)
    - created_at: int (always present, never changes)
    - embedding: list[float] (added in v0.9, always present now)
    - metadata: dict (added in v0.10, optional but always present as {})

    Adding new fields is OK (backward compatible).
    Removing or renaming fields breaks clients (not OK).
    """
    return self.store.get(id)

# If you need to add a field later:
# ✓ DO THIS (backward compatible):
#   Add new optional field with default
#   All old clients still work (get None or default)

# ❌ DON'T DO THIS (breaking change):
#   Remove a field
#   Rename a field
#   Change type of existing field
```

**Key**: Return structure is permanent; only add (never remove)

---

### Principle 4: Error Handling Contract (Document All Errors)

```python
# ❌ Bad: Undocumented exceptions
def consolidate(events):
    # What if events is None? Empty? Invalid?
    # What exceptions can be raised?
    # Clients have no idea how to handle errors
    results = process_events(events)
    return results

# ✓ Good: All error cases documented and typed
def consolidate(
    self,
    events: list[EpisodicEvent]
) -> list[SemanticMemory]:
    """Consolidate episodic events into semantic memories.

    Args:
        events: List of episodic events (can be empty)

    Returns:
        list[SemanticMemory] (can be empty if no patterns found)

    Raises:
        ValueError: If events is None or contains invalid events
        ConsolidationError: If consolidation fails (e.g., LLM error)
        DatabaseError: If semantic store fails to save

    Example error handling:
        try:
            results = manager.consolidate(events)
        except ValueError as e:
            # Invalid input, check data
            log.error(f"Bad input: {e}")
        except ConsolidationError as e:
            # Consolidation failed, retry later
            log.error(f"Consolidation failed: {e}")
            # Don't propagate; save for retry
        except DatabaseError as e:
            # Storage failed, critical issue
            raise  # Let caller handle
    """
    if events is None:
        raise ValueError("Events list required (can be empty list)")

    if not all(isinstance(e, EpisodicEvent) for e in events):
        raise ValueError("All events must be EpisodicEvent instances")

    try:
        results = self._run_consolidation(events)
    except LLMError as e:
        raise ConsolidationError(f"LLM consolidation failed: {e}") from e
    except Exception as e:
        if "database" in str(e).lower():
            raise DatabaseError(f"Failed to save results: {e}") from e
        raise ConsolidationError(f"Unknown consolidation error: {e}") from e

    return results
```

**Key**: Every exception type documented; example error handling shown

---

### Principle 5: Optional Parameters (Use Defaults Safely)

```python
# ❌ Bad: Optional parameter behavior unclear
def query(text, filters=None, limit=None, sort=None):
    # What are default values?
    # What if filters is {}? Does that mean filter nothing or filter everything?
    # Is sort ascending or descending by default?
    pass

# ✓ Good: Optional parameters have safe defaults + docs
def query(
    self,
    text: str,
    filters: dict[str, Any] = None,
    limit: int = 10,
    sort: str = "relevance"
) -> list[MemoryModel]:
    """Query memories with optional filters.

    Args:
        text: Search query (required)
        filters: Optional filter dict (default: None = no filters)
                 Example: {"layer": "episodic", "created_after": 1234567890}
        limit: Max results (default: 10, range: 1-1000)
        sort: Sort order (default: "relevance")
              Options: "relevance", "recent", "oldest"

    Returns:
        list[MemoryModel] matching criteria

    Examples:
        # Simple query
        results = manager.query("python")

        # With filters
        results = manager.query("python", filters={"layer": "episodic"})

        # With multiple parameters
        results = manager.query("python", limit=50, sort="recent")
    """
    if filters is None:
        filters = {}  # Explicit empty dict, not None

    return self.store.query(text, filters, limit, sort)
```

**Key**: All defaults explicit; examples show common use cases

---

## MCP Tool Contract Template

```python
@mcp.tool()
async def my_mcp_tool(
    self,
    required_param: str,
    optional_param: int = 10
) -> dict:
    """Human-readable description of what this tool does.

    This is the tool's contract - what it guarantees to the user.

    Args:
        required_param: Description of required parameter
                        Constraints: (e.g., non-empty, 1-100 chars, etc.)
        optional_param: Description of optional parameter
                        Default: 10
                        Range: 1-1000

    Returns:
        dict with keys:
        - status: "success" or "error" (always present)
        - data: Result data if successful (present if status="success")
        - error: Error message if failed (present if status="error")

    Raises:
        ValueError: If required_param violates constraints
        ToolError: If operation fails

    Examples:
        >>> result = await my_mcp_tool("test")
        >>> result["status"]
        "success"
        >>> result["data"]
        {...}
    """
    # Validate inputs
    if not required_param or not isinstance(required_param, str):
        return {
            "status": "error",
            "error": "required_param must be non-empty string"
        }

    if not isinstance(optional_param, int) or optional_param < 1 or optional_param > 1000:
        return {
            "status": "error",
            "error": "optional_param must be int between 1-1000"
        }

    try:
        # Perform operation
        result = await self._perform_operation(required_param, optional_param)

        return {
            "status": "success",
            "data": result
        }

    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Operation failed: {e}"}
```

---

## Layer Interface Contract Template

```python
# Contract for communication between memory layers
class MemoryLayerContract:
    """Interface that all memory layers must implement.

    This defines the stable contract between layers.
    All layers must implement these methods with these signatures.
    """

    def create(self, item: BaseModel) -> BaseModel:
        """Create item and return with ID.

        Contract:
        - Input: Valid BaseModel instance (validated by caller)
        - Output: Same model with id field populated
        - Exceptions: DatabaseError only

        Guarantees:
        - returned.id is not None
        - returned.created_at is populated
        - Item persisted to database
        """
        pass

    def get(self, id: int) -> Optional[BaseModel]:
        """Get item by ID or None.

        Contract:
        - Input: Valid integer ID
        - Output: Model instance or None (never raises if ID not found)
        - Exceptions: DatabaseError only

        Guarantees:
        - If item exists: return complete model
        - If item doesn't exist: return None (not exception)
        """
        pass

    def list(self, **filters) -> list[BaseModel]:
        """List items matching filters.

        Contract:
        - Input: Filter dict (can be empty for all)
        - Output: list[BaseModel] (can be empty)
        - Exceptions: DatabaseError only

        Guarantees:
        - Always returns list (never None)
        - Empty list means no matches (not error)
        """
        pass

    def update(self, item: BaseModel) -> bool:
        """Update existing item.

        Contract:
        - Input: Model with id field set
        - Output: bool (True if updated, False if not found)
        - Exceptions: DatabaseError only

        Guarantees:
        - True = updated and persisted
        - False = ID not found (not an error)
        """
        pass

    def delete(self, id: int) -> bool:
        """Delete item by ID.

        Contract:
        - Input: Valid integer ID
        - Output: bool (True if deleted, False if not found)
        - Exceptions: DatabaseError only

        Guarantees:
        - True = deleted and persisted
        - False = ID not found (not an error)
        """
        pass
```

---

## Common API Contract Patterns

### Pattern 1: Status-Based Responses

```python
# ✓ MCP tools should return status dict
@mcp.tool()
async def operation(self, param: str) -> dict:
    """Operation returning status dict.

    Returns dict with:
    - status: "success", "error", or "partial"
    - data: Result if successful
    - error: Error message if failed
    """
    try:
        result = await self._do_operation(param)
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
    except ValueError as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

---

### Pattern 2: Type-Safe Parameters

```python
# ✓ Use Pydantic models for complex parameters
from pydantic import BaseModel, Field

class QueryParams(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=1000)
    sort: str = Field(default="relevance", pattern="^(relevance|recent|oldest)$")

@mcp.tool()
async def search(self, params: QueryParams) -> dict:
    """Search with type-validated parameters."""
    # params.text is guaranteed valid (1-1000 chars)
    # params.limit is guaranteed 1-1000
    # params.sort is guaranteed to be valid option
    pass
```

---

### Pattern 3: Pagination for Large Results

```python
# ✓ For results that could be large, support pagination
@mcp.tool()
async def list_memories(
    self,
    skip: int = 0,
    limit: int = 50
) -> dict:
    """List memories with pagination.

    Returns:
    {
        "status": "success",
        "data": [...memories...],
        "total": 1000,        # Total available
        "returned": 50,       # Returned in this call
        "skip": 0,
        "has_more": true      # More available
    }
    """
    skip = max(0, skip)
    limit = min(max(1, limit), 1000)  # Clamp 1-1000

    total = self.store.count()
    results = self.store.list(skip=skip, limit=limit)

    return {
        "status": "success",
        "data": results,
        "total": total,
        "returned": len(results),
        "skip": skip,
        "has_more": (skip + limit) < total
    }
```

---

## API Versioning Strategy

### Version 1: Don't Break (Add Only)

```python
# v0.9 (current)
class Memory(BaseModel):
    id: Optional[int] = None
    content: str
    created_at: int

# v0.10 (backward compatible - only add fields)
class Memory(BaseModel):
    id: Optional[int] = None
    content: str
    created_at: int
    embedding: Optional[list[float]] = None  # ✓ NEW FIELD (safe)
    project_id: int = 1                      # ✓ NEW WITH DEFAULT (safe)

# ❌ NOT backward compatible:
# - Remove 'content' field
# - Rename 'created_at' to 'timestamp'
# - Change 'created_at' from int to str
```

### Version 2: Deprecation Strategy

```python
# If you MUST break compatibility:

# Step 1: Announce (v0.11)
def get_memory_old_api(self, id):
    """DEPRECATED: Use get_memory_v2 instead.

    This API will be removed in v1.0.
    Migration guide: Use get_memory_v2(id) - same results.
    """
    return self.get_memory_v2(id)

# Step 2: New API alongside old (v0.11-0.15)
def get_memory_v2(self, id):
    """New API with different return format."""
    pass

# Step 3: Remove old API (v1.0)
# Delete get_memory_old_api entirely
```

---

## API Contract Checklist

- [ ] Function signature fully typed (no `Any` types)
- [ ] Docstring with Args, Returns, Raises sections
- [ ] All parameters have constraints documented
- [ ] All exceptions documented with when they occur
- [ ] Examples show common usage patterns
- [ ] Error handling documented with example
- [ ] Return type is stable (never changes structure)
- [ ] Optional parameters have safe defaults
- [ ] Input validation at entry point
- [ ] Error messages are informative
- [ ] Contract is backward compatible (additions only)
- [ ] MCP tools return status dict (not exceptions)
- [ ] Pagination supported for large results
- [ ] Rate limits or quotas documented (if applicable)
- [ ] Idempotency guarantees documented (if applicable)

## Step-by-Step Contract Design

### Step 1: Define What Tool Does
```
Tool: consolidate_memories
Purpose: Convert episodic events into semantic patterns
Input: List of episodic events (or None for all)
Output: List of new semantic memories created
```

### Step 2: Define Input Contract
```
Required: events (list of EpisodicEvent or None)
Optional: None
Constraints: events can be empty list
             events cannot contain None items
             events must be valid EpisodicEvent instances
```

### Step 3: Define Output Contract
```
Returns: list[SemanticMemory]
Guarantees: Can be empty (no patterns found)
            Each memory has id, content, created_at
            Memories are persisted (not in-memory)
```

### Step 4: Define Error Contract
```
ValueError: If events contains invalid items
ConsolidationError: If consolidation fails (LLM error)
DatabaseError: If persistence fails
```

### Step 5: Document with Examples
```python
def consolidate_memories(self, events: list[EpisodicEvent]) -> list[SemanticMemory]:
    """Consolidate episodic events into semantic patterns.

    Args:
        events: List of episodic events (can be None=all, or empty list)

    Returns:
        list[SemanticMemory] newly created (can be empty if no patterns)

    Raises:
        ValueError: If events contains invalid items
        ConsolidationError: If consolidation process fails
        DatabaseError: If saving results fails

    Example:
        >>> events = manager.get_unconsolidated_events()
        >>> results = manager.consolidate_memories(events)
        >>> len(results)
        5  # 5 new semantic memories created
    """
```

### Step 6: Review for Stability
```
- Is this contract stable? (Won't need to change)
- Are all edge cases handled?
- Are error cases clear to callers?
- Can this be extended without breaking?
```

## Related Skills

- **implement-memory-layer** - Implement layer matching this contract
- **fix-failing-tests** - Tests verify contract compliance
- **refactor-code** - Refactor to match contracts
- **add-mcp-tool** - Add MCP tool following this contract

## Success Criteria

✓ API contract fully documented
✓ All inputs validated explicitly
✓ All outputs have stable structure
✓ All errors documented with examples
✓ No undocumented behavior
✓ Backward compatible (additions only)
✓ Examples provided for common cases
✓ Error handling shown to callers
✓ Contract is implementable consistently
✓ Tool/interface is maintainable
