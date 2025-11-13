# Agent Discovery - Quick Start Guide

**Last Updated**: November 13, 2025
**Status**: Production Ready ✅

## For Agents (Claude Code, Future Agents)

### How to Discover Athena Operations

```bash
# 1. List all available memory layers
ls /athena/layers/

# 2. Explore a specific layer (e.g., semantic)
ls /athena/layers/semantic/

# 3. Read an operation's documentation
cat /athena/layers/semantic/recall.py | head -30

# 4. Use the operation
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/.work/athena/src')
from athena.mcp.filesystem_api_integration import get_integration

integration = get_integration()
result = integration.use_filesystem_api(
    layer="semantic",
    operation="search",
    params={"query": "authentication patterns", "limit": 5}
)
print(result)  # Summary with drill-down IDs
EOF
```

## Available Operations

### Semantic Layer
- **search**: Find semantic memories by query
  - Path: `/athena/layers/semantic/recall.py`
  - Returns: Summary (total, confidence, top_ids)

### Episodic Layer
- **search**: Find episodic events by query
  - Path: `/athena/layers/episodic/search.py`
  - Returns: Event count, temporal clustering
- **timeline**: Get events within time range
  - Path: `/athena/layers/episodic/timeline.py`
  - Returns: Timeline visualization data

### Graph Layer
- **search**: Search entities in knowledge graph
  - Path: `/athena/layers/graph/traverse.py`
  - Returns: Top entities, relationships
- **communities**: Detect entity communities
  - Path: `/athena/layers/graph/communities.py`
  - Returns: Community structure, entities

### Consolidation Layer
- **extract**: Extract patterns from episodic events
  - Path: `/athena/layers/consolidation/extract.py`
  - Returns: Pattern summary, confidence scores

### Procedural Layer
- **find**: Find reusable procedures/workflows
  - Path: `/athena/layers/procedural/find.py`
  - Returns: Procedure names, effectiveness metrics

### Prospective Layer
- **tasks**: List active tasks/goals
  - Path: `/athena/layers/prospective/tasks.py`
  - Returns: Task summary by priority/status

### Planning Layer
- **decompose**: Break down task into subtasks
  - Path: `/athena/layers/planning/decompose.py`
  - Returns: Task hierarchy, estimated effort

### Meta Layer
- **quality**: Assess memory system quality
  - Path: `/athena/layers/meta/quality.py`
  - Returns: Quality metrics, health status

## Usage Examples

### Search for Semantically Similar Memories

```python
from athena.mcp.filesystem_api_integration import get_integration

integration = get_integration()

# Search returns summary (300 tokens)
result = integration.use_filesystem_api(
    "semantic",
    "search",
    {"query": "error handling patterns", "limit": 5}
)

# Result:
# {
#     "query": "error handling patterns",
#     "total_results": 42,
#     "high_confidence_count": 15,
#     "avg_confidence": 0.82,
#     "top_5_ids": [1, 3, 7, 15, 22],
#     "domain_distribution": {"architecture": 8, "security": 7}
# }

# If you need full details on one result:
# memory = get_memory_details(memory_id=1)  # Full object (1.5K tokens)
```

### Find Related Events from Today

```python
integration = get_integration()

# Get events from past 24 hours
result = integration.use_filesystem_api(
    "episodic",
    "timeline",
    {
        "start_date": "2025-11-12T14:12:00Z",
        "end_date": "2025-11-13T14:12:00Z"
    }
)

# Result includes clustering by context/session
```

### Discover Knowledge Structure

```python
integration = get_integration()

# Find natural communities in knowledge graph
result = integration.use_filesystem_api(
    "graph",
    "communities",
    {"min_size": 2}
)

# Result shows:
# {
#     "community_count": 12,
#     "total_entities": 437,
#     "communities": [
#         {"id": "c1", "size": 45, "topic": "Authentication"},
#         {"id": "c2", "size": 38, "topic": "API Design"},
#         ...
#     ]
# }
```

## Key Principles

✅ **Progressive Disclosure**: Operations discovered on-demand, not loaded upfront
✅ **Summary-First**: Returns ~300 tokens with drill-down available
✅ **Local Execution**: Data processing happens in-process, not via external APIs
✅ **Cross-Project**: Works from any project via `/athena` symlink
✅ **Token Efficient**: 70× reduction compared to traditional approaches

## Integration Pattern

All operations follow this pattern:

```
1. DISCOVER → List operations via filesystem
2. READ → Get function signature from .py file
3. EXECUTE → Call via integration layer
4. SUMMARIZE → Get ~300 token result
5. DRILL DOWN (optional) → Get full details for specific ID
```

## For Developers

### Add New Operation

1. Create operation file in `/athena/layers/{layer}/`:
   ```python
   async def my_operation(param: str) -> Dict[str, Any]:
       """Brief description and usage example."""
       return {"summary": "...", "drill_down_ids": [...]}
   ```

2. Add routing in `filesystem_api_integration.py`:
   ```python
   elif layer == "semantic" and operation == "my_op":
       return self.router.route_semantic_operation(...)
   ```

3. Test discovery:
   ```bash
   cat /athena/layers/semantic/my_operation.py
   ```

### Wire MCP Handler

To migrate an existing MCP handler:

```python
# Before (old way - 10K+ tokens)
async def _handle_search_knowledge(self, args: dict):
    results = await self.manager.semantic_search(...)
    return [TextContent(text=json.dumps([r.to_dict() for r in results]))]

# After (new way - 300 tokens)
async def _handle_search_knowledge(self, args: dict):
    integration = get_integration()
    result = integration.use_filesystem_api(
        "semantic",
        "search",
        {"query": args.get("query", ""), "limit": args.get("limit", 100)}
    )
    return [TextContent(text=json.dumps(result))]
```

---

**For complete details, see**: `docs/AGENT_DISCOVERABILITY.md`
