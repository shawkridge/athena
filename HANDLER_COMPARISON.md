# Handler Comparison Matrix

## Quick Reference Table

| Aspect | Handler 1 (rules) | Handler 2 (sources) | Handler 3 (automation) | Handler 4 (conversations) | Handler 5 (hooks) |
|--------|-------------------|-------------------|----------------------|------------------------|------------------|
| **Location** | handlers.py:6604 | handlers.py:7728 | h_integration.py:754 | h_integration.py:1172 | h_tools.py:302 |
| **Lines** | 26 | 94 | 40 | 44 | 35 |
| **Return Format** | Plain text | JSON string | Markdown | Markdown | Markdown+JSON |
| **Async?** | No | No | Yes (await) | Yes (await) | No |
| **Lazy Init?** | No | No | Yes | Yes | Yes |
| **JSON Used?** | No | Yes | No | No | Yes (embedded) |
| **Error Handling** | Single try | Single try | Nested try | Nested try | Nested try |
| **Parameters** | project_id, category, enabled_only, limit | project_id, source_type | (none) | limit | (none) |
| **Data Source** | self.rules_store | ContextAdapterStore | AutomationOrchestrator | ConversationStore | HookDispatcher |
| **Polymorphic?** | No | No | Yes (to_dict) | Yes (to_dict) | No |
| **Direct Private Access?** | No | No | No | No | Yes (_hook_registry) |

---

## Output Format Examples

### Handler 1: Plain Text Format
```
Found 2 rule(s) for project 42:
  - ID 1: API_RATE_LIMIT (SECURITY, severity=HIGH)
  - ID 2: DEPLOYMENT_WINDOW (OPS, severity=MEDIUM)
```
**Pattern**: Linear text with f-string concatenation

---

### Handler 2: JSON Format
```json
{
  "status": "success",
  "timestamp": "2025-11-11T15:30:00Z",
  "sources_summary": {
    "total_count": 3,
    "active_count": 2,
    "disabled_count": 1,
    "by_type": {
      "GITHUB": 2,
      "SLACK": 1
    }
  },
  "sources": [
    {
      "id": 1,
      "name": "main-repo",
      "type": "GITHUB",
      "sync_direction": "bidirectional",
      "sync_frequency_minutes": 30,
      "enabled": true,
      "status": "Active"
    }
  ],
  "recommendations": [
    "Enable 1 disabled source(s) to resume synchronization",
    "Active integration with 2 source(s) - monitor sync frequency"
  ]
}
```
**Pattern**: Dict built incrementally, serialized via json.dumps()

---

### Handler 3: Markdown Format
```
**Automation Rules**

Total Rules: 2

**trigger_on_deployment** (ID: auto_rule_1)
Trigger: deployment_completed
Action: notify_team
Status: active

**trigger_on_error** (ID: auto_rule_2)
Trigger: error_threshold_exceeded
Action: escalate_incident
Status: active
```
**Pattern**: Markdown string built with multiline f-strings

---

### Handler 4: Markdown Format (Paginated)
```
**Active Conversations**

Total: 3

**Sprint Planning Discussion** (ID: conv_001)
Messages: 24
Status: active

**Bug Triage** (ID: conv_002)
Messages: 8
Status: active
```
**Pattern**: Same as Handler 3, but includes limit parameter

---

### Handler 5: Markdown + Embedded JSON
```
**Hook Registry**
Total Hooks: 3
Hooks:
[
  {
    "hook_type": "post_tool_use",
    "enabled": true,
    "execution_count": 42,
    "last_error": null
  },
  {
    "hook_type": "pre_consolidation",
    "enabled": true,
    "execution_count": 15,
    "last_error": null
  }
]
```
**Pattern**: Markdown header with embedded json.dumps()

---

## Code Structure Comparison

### Handler 1 Structure (Simplest)
```
1. Extract args (project_id, category, enabled_only, limit)
2. Validate (check project_id)
3. Query (rules_store.list_rules)
4. Filter (by category if provided)
5. Limit (apply limit)
6. Build response (f-string concatenation)
7. Return [TextContent]
```

### Handler 2 Structure (Most Complex)
```
1. Extract args (project_id, source_type)
2. Create store (ContextAdapterStore)
3. Query (list by project or all)
4. Filter (by source_type if provided)
5. Decide: empty or populated response
   IF empty:
     - Create empty response_data dict
   ELSE:
     - Calculate stats
     - Build sources array
     - Generate recommendations
6. Serialize (json.dumps)
7. Return [TextContent]
```

### Handler 3 Structure (Lazy Async)
```
1. Lazy init (AutomationOrchestrator with hasattr)
2. Query (await orchestrator.list_rules)
   - Nested error handling (fallback to [])
3. Build response (markdown template)
4. Populate items (polymorphic to_dict() + isinstance check)
5. Return [TextContent]
```

### Handler 4 Structure (Lazy Async with Pagination)
```
1. Extract args (limit with default 20)
2. Lazy init (ConversationStore with hasattr)
3. Query (await store.list(limit))
   - Nested error handling (fallback to [])
4. Build response (markdown template)
5. Populate items (polymorphic to_dict() + isinstance check)
6. Return [TextContent]
```

### Handler 5 Structure (Direct Registry Access)
```
1. Lazy init (HookDispatcher with hasattr)
2. Query (direct dict access to _hook_registry)
   - Nested error handling
3. Build hooks_info list (dict comprehension-like)
4. Build response (markdown + embedded JSON)
5. Return [TextContent]
```

---

## Parameter Analysis

| Handler | Parameters | Defaults | Validation |
|---------|-----------|----------|-----------|
| 1 | project_id (req), category (opt), enabled_only (opt), limit (opt) | enabled_only=True, limit=50 | Check project_id |
| 2 | project_id (opt), source_type (opt) | None | None |
| 3 | (none) | N/A | N/A |
| 4 | limit (opt) | limit=20 | None |
| 5 | (none) | N/A | N/A |

---

## Error Handling Patterns

### Single Try-Except (Handlers 1-2)
```python
try:
    # All logic
    ...
except Exception as e:
    logger.error(...)
    return [TextContent(type="text", text=f"Error: {str(e)}")]
```

### Nested Try-Except (Handlers 3-5)
```python
try:
    # Setup
    try:
        # Query logic
        data = await query()
    except Exception as inner_err:
        logger.debug(...)
        data = []  # Fallback
    
    # Build response
    response = ...
    return [TextContent(type="text", text=response)]
except Exception as e:
    logger.error(...)
    return [TextContent(type="text", text=f"Error: {str(e)}")]
```

**Difference**: Nested pattern gracefully degrades when query fails, still returns valid response.

---

## Async/Await Pattern

### Synchronous (Handlers 1, 2, 5)
```python
async def handler(...):  # Still async function signature
    rules = store.list_rules()  # Synchronous call
    # No await
```

### Asynchronous (Handlers 3, 4)
```python
async def handler(...):
    rules = await store.list_rules()  # Async call with await
    # OR
    conversations = await store.list(limit=limit)
```

---

## Lazy Initialization Pattern

### Not Used (Handlers 1, 2)
```python
# Direct instantiation or use of existing self.store
context_store = ContextAdapterStore(self.store.db)
```

### Used (Handlers 3, 4, 5)
```python
if not hasattr(server, '_automation_orchestrator'):
    from ..automation.orchestrator import AutomationOrchestrator
    server._automation_orchestrator = AutomationOrchestrator(server.store.db)

# Later use
rules = await server._automation_orchestrator.list_rules()
```

**Benefits**:
- Avoids repeated initialization
- Defers import until needed
- Caches on server object

---

## String Building Patterns

### Linear Concatenation (Handler 1)
```python
result = f"Found {len(rules)} rule(s)...\n"
for rule in rules:
    result += f"  - ID {rule.id}...\n"
```
**Pros**: Simple, direct
**Cons**: String concatenation in loops (O(n) reallocations)

### Dict Then JSON (Handler 2)
```python
response_data = {
    "status": "success",
    "sources": [...],
    ...
}
text = json.dumps(response_data, indent=2)
```
**Pros**: Structured, easily modified
**Cons**: Extra serialization step

### Multiline F-String (Handlers 3, 4)
```python
response = f"""**Automation Rules**

Total Rules: {len(rules)}
"""
for rule in rules:
    response += f"""
**{rule_dict.get('name')}** ...
"""
```
**Pros**: Template-like, readable
**Cons**: Still string concatenation in loops

### Embedded JSON (Handler 5)
```python
response = f"""**Hook Registry**
Total Hooks: {len(hooks_info)}
Hooks:
{json.dumps(hooks_info, indent=2)}"""
```
**Pros**: Hybrid readability + structure
**Cons**: Nested quotes, mixing formats

---

## Recommendations by Handler

### Handler 1: _handle_list_rules
- **Current State**: Simple, efficient
- **Opportunity**: Use response builder for consistency
- **Concern**: String concatenation in loop (could use list + join)
- **Priority**: Low (already efficient)

### Handler 2: _handle_list_external_sources
- **Current State**: Complex but well-structured
- **Opportunity**: Extract recommendation logic, use response builder
- **Concern**: 94 lines, large response structure
- **Priority**: High (reduce complexity)

### Handler 3: handle_list_automation_rules
- **Current State**: Solid pattern with async/await
- **Opportunity**: Extract markdown template, standardize polymorphic handling
- **Concern**: Nested error handling could be unified
- **Priority**: Medium (potential template extraction)

### Handler 4: handle_list_active_conversations
- **Current State**: Nearly identical to Handler 3
- **Opportunity**: Template extraction (3 and 4 are ~95% same)
- **Concern**: Code duplication with Handler 3
- **Priority**: High (duplication)

### Handler 5: handle_list_hooks
- **Current State**: Creative markdown + JSON hybrid
- **Opportunity**: Clarify format choice, standardize initialization
- **Concern**: Direct private attribute access (_hook_registry)
- **Priority**: Medium (API encapsulation)

---

## Unified TOON Handler Template

```python
async def _handle_list_X(self/server, args: dict) -> list[TextContent]:
    """Handle list_X tool call."""
    try:
        # 1. EXTRACT PARAMETERS
        limit = args.get("limit", DEFAULT_LIMIT)
        filter_param = args.get("filter")
        
        # 2. OPTIONAL: LAZY INITIALIZE
        if lazy:
            if not hasattr(server, '_store_attr'):
                from ..module import Store
                server._store_attr = Store(server.store.db, project_id=args.get('project_id'))
            store = server._store_attr
        else:
            store = self.store or StoreClass(self.store.db)
        
        # 3. SAFE QUERY
        try:
            if async_query:
                items = await store.query(limit=limit, filter=filter_param)
            else:
                items = store.query(limit=limit, filter=filter_param)
        except Exception as query_err:
            logger.debug(f"Query error: {query_err}")
            items = []
        
        # 4. BUILD RESPONSE (choose format)
        if format == "json":
            response_data = {"items": items, "count": len(items)}
            text = json.dumps(response_data, indent=2)
        elif format == "markdown":
            text = self.build_markdown("Title", items, item_formatter)
        else:  # plain text
            text = self.build_plain_text("Title", items, item_formatter)
        
        # 5. RETURN
        return [TextContent(type="text", text=text)]
    
    except Exception as e:
        logger.error(f"Error in list_X: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

