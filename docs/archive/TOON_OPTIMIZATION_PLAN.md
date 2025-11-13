# TOON Optimization Plan for 5 List Handlers

## Executive Summary

Extracted complete code for 5 list_* handlers across 3 MCP modules. All handlers follow the **TOON pattern** (TEXT-ONLY OBJECT NARRATIVE) - converting structured data into text/JSON strings for the MCP interface. This document provides the complete extraction and identifies optimization opportunities.

### Extraction Locations

| Handler | File | Lines | Format |
|---------|------|-------|--------|
| 1. _handle_list_rules | handlers.py | 6604-6629 | Plain text |
| 2. _handle_list_external_sources | handlers.py | 7728-7821 | JSON string |
| 3. handle_list_automation_rules | handlers_integration.py | 754-793 | Markdown |
| 4. handle_list_active_conversations | handlers_integration.py | 1172-1215 | Markdown |
| 5. handle_list_hooks | handlers_tools.py | 302-336 | Markdown + JSON |

---

## Complete Handler Analysis

### HANDLER 1: _handle_list_rules (26 lines)

**Signature**: `async def _handle_list_rules(self, args: dict) -> list[TextContent]`

**Pattern**:
- Get project_id from args (required parameter)
- Fetch rules from `self.rules_store.list_rules()`
- Filter by category (optional)
- Limit results (default 50)
- Build plain text narrative with f-string concatenation
- Return TextContent with string text

**Data Shape**:
```python
Rule:
  - id: int
  - name: str
  - category: str
  - severity: str
```

**Output Format**:
```
Found N rule(s) for project X:
  - ID 1: rule_name (CATEGORY, severity=HIGH)
  - ID 2: rule_name (CATEGORY, severity=LOW)
```

**Optimization Opportunities**:
- ✓ Simplest handler (no JSON, no async, no lazy init)
- ✓ Good baseline for plain text format
- Could benefit from response builder helper

---

### HANDLER 2: _handle_list_external_sources (94 lines)

**Signature**: `async def _handle_list_external_sources(self, args: dict) -> list[TextContent]`

**Pattern**:
- Instantiate ContextAdapterStore
- Get connections (by project or all)
- Filter by source_type (optional)
- Build response_data dict with:
  - Status envelope
  - sources_summary (aggregated stats)
  - sources array (transformed connections)
  - recommendations (generated suggestions)
- Serialize to JSON string with json.dumps()
- Return TextContent with JSON text
- Handle errors with error_response dict

**Data Shape**:
```python
Connection:
  - id: int
  - source_name: str
  - source_type: Enum (value)
  - sync_direction: Enum (value)
  - sync_frequency_minutes: int
  - enabled: bool

Output JSON:
{
  "status": "success",
  "timestamp": "2025-11-11T..Z",
  "sources_summary": {
    "total_count": int,
    "active_count": int,
    "disabled_count": int,
    "by_type": {TYPE: count}
  },
  "sources": [
    {
      "id", "name", "type", "sync_direction",
      "sync_frequency_minutes", "enabled", "status"
    }
  ],
  "recommendations": [str, str, str]
}
```

**Optimization Opportunities**:
- Largest handler - complex response structure
- Conditional logic for empty vs. populated response
- Recommendation generation is 7 separate if statements
- Good candidate for response template system

---

### HANDLER 3: handle_list_automation_rules (40 lines)

**Signature**: `async def handle_list_automation_rules(server, args: dict) -> List[TextContent]`

**Pattern**:
- Lazy initialize AutomationOrchestrator (stored in server._automation_orchestrator)
- Await async list_rules() call
- Fallback to empty list on error (nested try-except)
- Build markdown response using f-string template
- Polymorphic rule handling (to_dict() or raw)
- Check isinstance(dict) before accessing
- Return TextContent with markdown text

**Data Shape**:
```python
Rule (via to_dict()):
  - id: str
  - name: str
  - trigger_event: str
  - action: str
  - status: str
```

**Output Format**:
```
**Automation Rules**

Total Rules: N

**rule_name** (ID: 123)
Trigger: event_type
Action: do_something
Status: active
```

**Key Differences from Handlers 1-2**:
- ✓ Lazy initialization pattern
- ✓ Async/await pattern (awaited)
- ✓ Nested error handling
- ✓ Markdown formatting instead of JSON/plain text
- ✓ Polymorphic object handling (to_dict() fallback)

---

### HANDLER 4: handle_list_active_conversations (44 lines)

**Signature**: `async def handle_list_active_conversations(server, args: dict) -> List[TextContent]`

**Pattern**:
- Lazy initialize ConversationStore (stored in server._conversation_store)
- Include limit parameter (default 20) for pagination
- Await async list() call with limit
- Fallback to empty list on error (nested try-except)
- Build markdown response using f-string template
- Polymorphic object handling (to_dict() or raw)
- Check isinstance(dict) before accessing
- Return TextContent with markdown text

**Data Shape**:
```python
Conversation (via to_dict()):
  - id: str
  - title: str
  - message_count: int
  - status: str
```

**Output Format**:
```
**Active Conversations**

Total: N

**conversation_title** (ID: 123)
Messages: 42
Status: active
```

**Key Differences from Handler 3**:
- ✓ Adds limit parameter (pagination)
- Structure almost identical to handler 3
- Good candidate for template extraction

---

### HANDLER 5: handle_list_hooks (35 lines)

**Signature**: `async def handle_list_hooks(server: Any, args: dict) -> List[TextContent]`

**Pattern**:
- Lazy initialize HookDispatcher (stored in server._hook_dispatcher)
- Access private _hook_registry attribute directly
- NO async/await call (registry is synchronous dict)
- Build list of hook info dicts from registry.items()
- Nested error handling (inner try-except for registry access)
- Build markdown response with embedded JSON
- Embed json.dumps() in f-string template
- Return TextContent with markdown + JSON text

**Data Shape**:
```python
HookRegistry (dict):
  hook_type: {
    "enabled": bool,
    "execution_count": int,
    "last_error": str | None
  }

Output:
**Hook Registry**
Total Hooks: N
Hooks:
[
  {"hook_type": "...", "enabled": true, ...}
]
```

**Key Differences**:
- ✓ Hybrid format (markdown header + JSON body)
- ✓ NO await (synchronous registry access)
- ✓ Direct private attribute access (_hook_registry)
- ✓ Embeds json.dumps() in f-string

---

## TOON Pattern Summary

All handlers exhibit the TOON pattern:

```python
async def _handle_list_X(self/server, args: dict) -> list[TextContent]:
    """Docstring."""
    try:
        # 1. EXTRACT PARAMETERS
        param1 = args.get("param1", default)
        
        # 2. OPTIONAL: LAZY INITIALIZE
        if not hasattr(server, '_store'):
            server._store = Store(server.store.db)
        
        # 3. FETCH/QUERY DATA
        data = store.query()  # or await store.async_query()
        
        # 4. BUILD RESPONSE STRUCTURE (text/dict/markdown)
        response = "..."  # Build narrative
        # OR response = {...}  # Build dict
        # OR response = f"""..."""  # Build markdown
        
        # 5. SERIALIZE TO TEXT
        if isinstance(response, dict):
            text = json.dumps(response)
        else:
            text = response
        
        # 6. RETURN TEXT CONTENT
        return [TextContent(type="text", text=text)]
    
    except Exception as e:
        logger.error(...)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

---

## Optimization Opportunities

### 1. Response Builder Helper (High Impact)

Create a unified response builder to reduce duplication:

```python
class TOONResponseBuilder:
    @staticmethod
    def plain_text(title: str, items: list, item_format: Callable) -> str:
        """Build plain text response."""
        result = f"{title}\n"
        for item in items:
            result += item_format(item)
        return result
    
    @staticmethod
    def markdown(title: str, items: list, item_format: Callable) -> str:
        """Build markdown response."""
        result = f"**{title}**\n\nTotal: {len(items)}\n"
        for item in items:
            result += item_format(item)
        return result
    
    @staticmethod
    def json_response(data: dict) -> str:
        """Serialize dict to JSON."""
        return json.dumps(data, indent=2)
```

**Affected handlers**: All 5 (2-4x code reduction)

### 2. Lazy Initialization Pattern (Medium Impact)

Extract lazy initialization helper:

```python
@staticmethod
def lazy_init(server, attr_name: str, init_class, *args, **kwargs):
    """Lazy initialize and cache on server."""
    if not hasattr(server, attr_name):
        setattr(server, attr_name, init_class(*args, **kwargs))
    return getattr(server, attr_name)
```

**Usage**:
```python
store = self.lazy_init(server, '_automation_orchestrator', 
                       AutomationOrchestrator, server.store.db)
```

**Affected handlers**: 3, 4, 5 (20-30 lines reduction per handler)

### 3. Polymorphic Object Handler (Low Impact)

Extract polymorphic to_dict() handling:

```python
@staticmethod
def to_dict_safe(obj):
    """Convert object to dict safely."""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return None
```

**Affected handlers**: 3, 4 (5-10 lines per handler)

### 4. Error Handling Standardization (Medium Impact)

Unified error handling:

```python
@staticmethod
async def safe_list(self, query_func, fallback_empty=True):
    """Safely execute list query with fallback."""
    try:
        return await query_func() if asyncio.iscoroutinefunction(query_func) else query_func()
    except Exception as e:
        logger.debug(f"Query error: {e}")
        return [] if fallback_empty else None
```

**Affected handlers**: 2, 3, 4, 5 (10-15 lines reduction per)

### 5. Recommendation Engine (Handler 2 specific)

Extract the 7-condition recommendation logic:

```python
class RecommendationEngine:
    @staticmethod
    def generate_source_recommendations(connections) -> list[str]:
        """Generate recommendations for external sources."""
        recommendations = []
        active_count = sum(1 for c in connections if c.enabled)
        disabled_count = len(connections) - active_count
        by_type = {}
        
        for conn in connections:
            by_type[conn.source_type.value.upper()] = \
                by_type.get(conn.source_type.value.upper(), 0) + 1
        
        # Recommendation generation logic
        if disabled_count > 0:
            recommendations.append(...)
        # ... more conditions
        
        return recommendations[:3]
```

**Impact**: Handler 2 reduced from 94 to 40 lines

---

## Implementation Priority

### Phase 1: High-Impact (20-30% token reduction)
1. Response Builder Helper (affects all 5 handlers)
2. Lazy Initialization Pattern (affects handlers 3-5)
3. Error Handling Standardization (affects handlers 2-5)

### Phase 2: Medium-Impact (10-15% token reduction)
4. Recommendation Engine (affects handler 2)
5. Polymorphic Object Handler (affects handlers 3-4)

### Phase 3: Validation
- Test all handlers maintain output format
- Verify error handling still works
- Check async/await consistency

---

## Testing Checklist

- [ ] Handler 1 still returns plain text narrative
- [ ] Handler 2 still returns valid JSON with recommendations
- [ ] Handler 3 still returns markdown with awaited rules
- [ ] Handler 4 still returns markdown with limit parameter
- [ ] Handler 5 still returns markdown + embedded JSON
- [ ] All error cases still handled gracefully
- [ ] Lazy initialization still works (no duplicate init)
- [ ] Polymorphic object handling still works

---

## Files for Refactoring

1. `/home/user/.work/athena/src/athena/mcp/handlers.py` - Handlers 1-2
2. `/home/user/.work/athena/src/athena/mcp/handlers_integration.py` - Handlers 3-4
3. `/home/user/.work/athena/src/athena/mcp/handlers_tools.py` - Handler 5

Optional: Create new helper module `/home/user/.work/athena/src/athena/mcp/toon_helpers.py` for shared utilities.

---

## Complete Code Reference

See `/home/user/.work/athena/HANDLER_EXTRACTION.md` for complete code listings of all 5 handlers with detailed annotations.

