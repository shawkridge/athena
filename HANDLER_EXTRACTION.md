# COMPLETE CODE EXTRACTION: 5 List Handlers for TOON Optimization

## Summary of Handlers

All 5 handlers follow the **TOON pattern** - they build **TEXT-ONLY OBJECT NARRATIVE** responses:
- Convert structured data to human-readable text/JSON
- No structured return types (always TextContent with string text)
- String formatting with concatenation or json.dumps()
- Error handling with try/except wrapping

---

## HANDLER 1: _handle_list_rules

**Location**: `/home/user/.work/athena/src/athena/mcp/handlers.py` (lines 6604-6629)

**Method Signature**:
```python
async def _handle_list_rules(self, args: dict) -> list[TextContent]:
```

**Complete Method Body**:
```python
async def _handle_list_rules(self, args: dict) -> list[TextContent]:
    """Handle list_rules tool call."""
    try:
        project_id = args.get("project_id")
        category = args.get("category")
        enabled_only = args.get("enabled_only", True)
        limit = args.get("limit", 50)

        if not project_id:
            return [TextContent(type="text", text="Missing project_id")]

        rules = self.rules_store.list_rules(project_id, enabled_only=enabled_only)

        if category:
            rules = [r for r in rules if str(r.category).lower() == category.lower()]

        rules = rules[:limit]

        result = f"Found {len(rules)} rule(s) for project {project_id}:\n"
        for rule in rules:
            result += f"  - ID {rule.id}: {rule.name} ({rule.category}, severity={rule.severity})\n"

        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error in list_rules: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

**Return Format**: `TextContent` with string formatting
- Builds plain text using f-string concatenation
- Returns single-item list with formatted narrative

**Data Structure**:
- Input: Rules objects from `self.rules_store.list_rules()`
- Each rule has: `id`, `name`, `category`, `severity`
- Output: Plain text narrative listing rules

**TOON Pattern Analysis**:
- Linear text building with f-strings
- No JSON serialization
- Simple concatenation loop
- 26 lines total

---

## HANDLER 2: _handle_list_external_sources

**Location**: `/home/user/.work/athena/src/athena/mcp/handlers.py` (lines 7728-7821)

**Method Signature**:
```python
async def _handle_list_external_sources(self, args: dict) -> list[TextContent]:
```

**Complete Method Body**:
```python
async def _handle_list_external_sources(self, args: dict) -> list[TextContent]:
    """List external sources with quality metrics and recommendations."""
    try:
        project_id = args.get("project_id")
        source_type = args.get("source_type")

        # Create store
        context_store = ContextAdapterStore(self.store.db)

        # Get connections
        if project_id:
            connections = context_store.list_connections_by_project(project_id)
        else:
            connections = context_store.list_all_connections()

        if source_type:
            connections = [c for c in connections if c.source_type.value == source_type]

        # Build JSON response
        now = datetime.utcnow().isoformat() + "Z"

        if not connections:
            response_data = {
                "status": "success",
                "timestamp": now,
                "sources_summary": {
                    "total_count": 0,
                    "active_count": 0,
                    "disabled_count": 0,
                    "by_type": {}
                },
                "sources": [],
                "recommendations": [
                    "No external sources configured. Consider connecting GitHub, Jira, or Slack for enhanced integration.",
                    "Start with GitHub for version control awareness and commit history tracking."
                ]
            }
        else:
            # Calculate statistics
            active_count = sum(1 for c in connections if c.enabled)
            disabled_count = len(connections) - active_count
            by_type = {}
            for conn in connections:
                source_type_val = conn.source_type.value.upper()
                by_type[source_type_val] = by_type.get(source_type_val, 0) + 1

            # Build sources array
            sources_list = []
            for conn in connections:
                sources_list.append({
                    "id": conn.id,
                    "name": conn.source_name,
                    "type": conn.source_type.value.upper(),
                    "sync_direction": conn.sync_direction.value,
                    "sync_frequency_minutes": conn.sync_frequency_minutes,
                    "enabled": conn.enabled,
                    "status": "Active" if conn.enabled else "Disabled"
                })

            # Generate recommendations
            recommendations = []
            if disabled_count > 0:
                recommendations.append(f"Enable {disabled_count} disabled source(s) to resume synchronization")
            if len(connections) > 5:
                recommendations.append("Consider consolidating sources - 5+ connections may impact sync performance")
            if "GITHUB" not in by_type:
                recommendations.append("Add GitHub integration for version control awareness and code change tracking")
            if active_count == 0:
                recommendations.append("All sources are disabled. Enable at least one for active integration")
            if not recommendations:
                recommendations.append(f"Active integration with {active_count} source(s) - monitor sync frequency")

            response_data = {
                "status": "success",
                "timestamp": now,
                "sources_summary": {
                    "total_count": len(connections),
                    "active_count": active_count,
                    "disabled_count": disabled_count,
                    "by_type": by_type
                },
                "sources": sources_list,
                "recommendations": recommendations[:3]  # Top 3 recommendations
            }

        return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
    except Exception as e:
        logger.error(f"Error in list_external_sources: {e}", exc_info=True)
        error_response = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
```

**Return Format**: `TextContent` with JSON string
- Builds dict structure: response_data
- Serializes to JSON string with `json.dumps(response_data, indent=2)`
- Returns single-item list with JSON text

**Data Structure**:
- Input: Connection objects from ContextAdapterStore
- Each connection has: `id`, `source_name`, `source_type`, `sync_direction`, `sync_frequency_minutes`, `enabled`
- Output: JSON with nested structure:
  - `status`: success/error
  - `timestamp`: ISO format
  - `sources_summary`: aggregated statistics
  - `sources`: array of connection dicts
  - `recommendations`: string list of suggestions

**TOON Pattern Analysis**:
- Dict building (not direct text)
- JSON serialization via json.dumps()
- Conditional response (empty vs. with data)
- Recommendation generation logic
- 94 lines total

---

## HANDLER 3: _handle_list_automation_rules

**Location**: `/home/user/.work/athena/src/athena/mcp/handlers_integration.py` (lines 754-793)

**Method Signature**:
```python
async def handle_list_automation_rules(server, args: dict) -> List[TextContent]:
```

**Complete Method Body**:
```python
async def handle_list_automation_rules(server, args: dict) -> List[TextContent]:
    """List all registered automation rules.

    Returns:
        List of active automation rules with details
    """
    try:
        # Get automation orchestrator
        if not hasattr(server, '_automation_orchestrator'):
            from ..automation.orchestrator import AutomationOrchestrator
            server._automation_orchestrator = AutomationOrchestrator(server.store.db)

        # List rules
        try:
            rules = await server._automation_orchestrator.list_rules()
        except Exception as list_err:
            logger.debug(f"List rules error: {list_err}")
            rules = []

        response = f"""**Automation Rules**

Total Rules: {len(rules) if rules else 0}
"""

        if rules:
            for rule in rules:
                rule_dict = rule.to_dict() if hasattr(rule, 'to_dict') else rule
                if isinstance(rule_dict, dict):
                    response += f"""
**{rule_dict.get('name', 'Unknown')}** (ID: {rule_dict.get('id', 'N/A')})
Trigger: {rule_dict.get('trigger_event', 'N/A')}
Action: {rule_dict.get('action', 'N/A')}
Status: {rule_dict.get('status', 'active')}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in list_automation_rules: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

**Return Format**: `TextContent` with markdown-style text
- Builds markdown formatted text using f-strings
- Bold headers with `**` syntax
- Multi-line template strings
- Returns single-item list with formatted narrative

**Data Structure**:
- Input: Rule objects from `AutomationOrchestrator.list_rules()`
- Each rule has (via to_dict()): `id`, `name`, `trigger_event`, `action`, `status`
- Output: Markdown-formatted text with rules listed

**TOON Pattern Analysis**:
- Lazy initialization of AutomationOrchestrator
- Error graceful fallback (empty list on error)
- Markdown formatting with multiline f-strings
- Polymorphic handling (to_dict() or raw object)
- 40 lines total
- Note: Calls are **awaited** (async rule listing)

---

## HANDLER 4: _handle_list_active_conversations

**Location**: `/home/user/.work/athena/src/athena/mcp/handlers_integration.py` (lines 1172-1215)

**Method Signature**:
```python
async def handle_list_active_conversations(server, args: dict) -> List[TextContent]:
```

**Complete Method Body**:
```python
async def handle_list_active_conversations(server, args: dict) -> List[TextContent]:
    """List all active conversation sessions.

    Args:
        limit: Maximum number to return (default: 20)

    Returns:
        List of active conversations
    """
    try:
        limit = args.get("limit", 20)

        # Get conversation store
        if not hasattr(server, '_conversation_store'):
            from ..conversation.store import ConversationStore
            server._conversation_store = ConversationStore(server.store.db)

        # List conversations
        try:
            conversations = await server._conversation_store.list(limit=limit)
        except Exception as list_err:
            logger.debug(f"List conversations error: {list_err}")
            conversations = []

        response = f"""**Active Conversations**

Total: {len(conversations) if conversations else 0}
"""

        if conversations:
            for conv in conversations:
                conv_dict = conv.to_dict() if hasattr(conv, 'to_dict') else conv
                if isinstance(conv_dict, dict):
                    response += f"""
**{conv_dict.get('title', 'Untitled')}** (ID: {conv_dict.get('id', 'N/A')})
Messages: {conv_dict.get('message_count', 0)}
Status: {conv_dict.get('status', 'active')}
"""

        return [TextContent(type="text", text=response)]

    except Exception as e:
        logger.error(f"Error in list_active_conversations: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

**Return Format**: `TextContent` with markdown-style text
- Builds markdown formatted text using f-strings
- Similar structure to handler 3
- Returns single-item list with formatted narrative

**Data Structure**:
- Input: Conversation objects from `ConversationStore.list()`
- Each conversation has (via to_dict()): `id`, `title`, `message_count`, `status`
- Output: Markdown-formatted text with conversations listed

**TOON Pattern Analysis**:
- Lazy initialization of ConversationStore
- Error graceful fallback (empty list on error)
- Markdown formatting with multiline f-strings
- Polymorphic handling (to_dict() or raw object)
- **Includes limit parameter** (pagination)
- 44 lines total
- Note: **Awaited** async call

---

## HANDLER 5: _handle_list_hooks

**Location**: `/home/user/.work/athena/src/athena/mcp/handlers_tools.py` (lines 302-336)

**Method Signature**:
```python
async def handle_list_hooks(server: Any, args: dict) -> List[TextContent]:
```

**Complete Method Body**:
```python
async def handle_list_hooks(server: Any, args: dict) -> List[TextContent]:
    """List all registered hooks and their execution status.

    Shows hook registry with execution counts and error status.
    """
    try:
        # Lazy initialize HookDispatcher
        if not hasattr(server, '_hook_dispatcher'):
            from ..hooks.dispatcher import HookDispatcher
            server._hook_dispatcher = HookDispatcher(server.store.db, project_id=1)

        # Get hook registry
        try:
            hook_registry = server._hook_dispatcher._hook_registry
            hooks_info = []
            for hook_type, info in hook_registry.items():
                hooks_info.append({
                    "hook_type": hook_type,
                    "enabled": info.get("enabled", False),
                    "execution_count": info.get("execution_count", 0),
                    "last_error": info.get("last_error")
                })

            response = f"""**Hook Registry**
Total Hooks: {len(hooks_info)}
Hooks:
{json.dumps(hooks_info, indent=2)}"""
        except Exception as op_err:
            logger.debug(f"Hook listing error: {op_err}")
            response = "Error: Could not list hooks"

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_list_hooks: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
```

**Return Format**: `TextContent` with mixed markdown + JSON text
- Builds text with markdown header
- Embeds JSON string via `json.dumps()`
- Returns single-item list with formatted narrative

**Data Structure**:
- Input: Hook registry dict from `HookDispatcher._hook_registry`
- Each hook type has: `enabled`, `execution_count`, `last_error`
- Output: Markdown header + embedded JSON

**TOON Pattern Analysis**:
- Lazy initialization of HookDispatcher
- Direct registry access (no async call - registry is dict)
- Accesses private `_hook_registry` attribute
- Builds list of hook info dicts
- Embeds json.dumps() in f-string
- Nested error handling (inner try for registry access)
- 35 lines total
- **NO await** (unlike handlers 3-4)

---

## Comparative Analysis: TOON Patterns

| Handler | Line Count | Format Type | JSON? | Awaited? | Lazy Init? | Error Handling |
|---------|-----------|-------------|-------|----------|-----------|---|
| list_rules | 26 | Plain text | No | No | No | Single try-except |
| list_external_sources | 94 | JSON string | Yes | No | No | Single try-except |
| list_automation_rules | 40 | Markdown | No | Yes | Yes | Nested try-except |
| list_active_conversations | 44 | Markdown | No | Yes | Yes | Nested try-except |
| list_hooks | 35 | Markdown + JSON | Yes | No | Yes | Nested try-except |

### Key Observations:

1. **Three Return Formats**:
   - Plain text narratives (handler 1)
   - JSON strings (handlers 2, 5)
   - Markdown text (handlers 3, 4)

2. **Common TOON Elements**:
   - All return `[TextContent(type="text", text=...)]`
   - All build strings before return (no streaming)
   - All concatenate or serialize to strings

3. **Opportunity for TOON Optimization**:
   - Unified response builder helper
   - Template system for markdown/JSON formats
   - Shared error handling pattern
   - Lazy initialization pattern extraction

4. **Async Pattern Variation**:
   - Handlers 3-4: Call async methods with **await**
   - Handlers 1, 2, 5: Synchronous operations
   - Inconsistency in whether operations are async

---

## Files Affected

- `/home/user/.work/athena/src/athena/mcp/handlers.py` (handlers 1-2)
- `/home/user/.work/athena/src/athena/mcp/handlers_integration.py` (handler 3-4)
- `/home/user/.work/athena/src/athena/mcp/handlers_tools.py` (handler 5)

