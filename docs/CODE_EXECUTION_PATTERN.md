# Athena Code Execution Pattern

## Overview

This implements the code execution with MCP pattern described in [Anthropic's engineering blog](https://www.anthropic.com/engineering/code-execution-with-mcp).

**Key insight**: Instead of loading all tool definitions into the model's context window, expose tools as HTTP APIs that agents can call directly in a code execution environment. This saves **~98% of tokens** by processing large intermediate results locally.

## Problem Solved

Traditional MCP:
- ❌ All 228 tool definitions loaded upfront (~150KB tokens)
- ❌ Large intermediate results passed through model context repeatedly
- ❌ 50,000+ tokens for single document processed across multiple tool calls

Code execution pattern:
- ✅ Tools discovered lazily (only load definitions when needed)
- ✅ Large results stay local (agent processes in code environment)
- ✅ Only summaries returned to model (2,000 tokens vs 150,000)

## Architecture

```
Claude Code (Local Execution)
    ↓ HTTP requests
Athena HTTP MCP Server (localhost:3000)
    ↓
Memory Layers (SQLite)
```

## Using the Pattern

### 1. Discover Tools (Lazy Loading)

```python
from athena import AthenaClient

client = AthenaClient("http://localhost:3000")

# Get tool summaries without full definitions
tools = client.discover_tools()
for category, info in tools['categories'].items():
    print(f"{category}: {info['count']} tools")

# Load specific tool definition only when needed
tool_def = client.get_tool("recall")
```

### 2. Call Tools and Process Locally

```python
# Call tool - returns potentially large result
result = client.consolidate(strategy="balanced", days_back=7)

# Process locally (stays in code execution environment)
patterns = result['patterns']
high_confidence = [p for p in patterns if p['confidence'] > 0.8]

# Return only summary to model (100 bytes instead of 50KB)
return f"Found {len(high_confidence)} high-confidence patterns"
```

### 3. State Persistence

```python
# Write intermediate results to files for resumability
import json

with open("consolidation_results.json", "w") as f:
    json.dump(result, f)

# Can resume later without re-running consolidation
with open("consolidation_results.json") as f:
    result = json.load(f)
```

## Registry Endpoints

### Discover Tools
```http
GET /tools/discover
```

Returns all available tools organized by category:
```json
{
  "categories": {
    "memory": {
      "description": "Core memory operations",
      "count": 3,
      "tools": [
        {"name": "recall", "description": "Search memories"},
        ...
      ]
    }
  },
  "total_tools": 50
}
```

### List Tools
```http
GET /tools/list?category=memory
```

Returns list of tool names in a category.

### Get Tool Definition
```http
GET /tools/{tool_name}
```

Returns full tool schema with parameters and examples:
```json
{
  "name": "recall",
  "description": "Search memories matching query",
  "parameters": [
    {
      "name": "query",
      "type": "string",
      "description": "Search query",
      "required": true
    }
  ],
  "returns": {
    "type": "array",
    "description": "List of matching memories"
  }
}
```

### Execute Tool
```http
POST /tools/{tool_name}/execute
Content-Type: application/json

{
  "query": "performance patterns",
  "k": 50
}
```

Executes tool and returns result.

## Client Library Usage

The `AthenaClient` provides ergonomic access to all endpoints:

```python
from athena import AthenaClient

client = AthenaClient("http://localhost:3000")

# Discovery
tools = client.discover_tools()
tool = client.get_tool("recall")

# Memory operations
results = client.recall(query="...", k=10)
memory = client.remember(content="...", tags=["tag1"])
success = client.forget(memory_id=123)

# Events
event = client.record_event(event_type="action", content="...")
events = client.recall_events(session_id="...", limit=50)

# Knowledge graph
entity = client.create_entity(name="...", entity_type="Task")
matches = client.search_graph(query="...", max_results=10)

# Consolidation
result = client.consolidate(strategy="balanced", days_back=7)

# Generic tool call
result = client.call_tool("recall", query="...", k=5)
```

### Context Manager Usage

```python
with AthenaClient("http://localhost:3000") as client:
    results = client.recall(query="...")
    # Connection closed automatically
```

## Example Agent Implementation

See `examples/code_execution_agent.py` for complete examples showing:

1. **Tool discovery** - Lazy loading with summaries
2. **Large result processing** - Filter/summarize locally
3. **State persistence** - Write intermediate results
4. **Context-efficient returns** - Only summaries to model

Run it with:
```bash
python examples/code_execution_agent.py
```

## Token Savings Breakdown

### Traditional MCP (228 tools in context)

```
Tool definitions:          ~150,000 tokens
First operation result:    ~5,000 tokens
Second operation result:   ~5,000 tokens
(results passed through context each time)
───────────────────────────
Total:                     ~160,000 tokens
```

### Code Execution Pattern

```
Tool summaries (lazy):     ~500 tokens
(only load definitions when needed)

Operation 1:
  - Intermediate result:   ~50,000 tokens (processed locally)
  - Summary returned:      ~100 tokens

Operation 2:
  - Intermediate result:   ~50,000 tokens (processed locally)
  - Summary returned:      ~100 tokens
───────────────────────────
Total to model context:    ~700 tokens

Savings: 98.7% (160KB → 2KB)
```

## When to Use This Pattern

✅ **Good fit**:
- Processing large search results (100+ items)
- Running consolidations with many patterns
- Complex filtering/aggregation operations
- Multi-step workflows where intermediate results are large

❌ **Overkill for**:
- Simple single-operation calls
- Small results that fit easily in context
- First-time exploration of data

## Advanced Usage

### Process Results Efficiently

```python
# BAD: Send everything back
result = client.consolidate()
return str(result)  # Entire 50KB structure

# GOOD: Process locally, return summary
result = client.consolidate()
patterns = result['patterns']
summary = {
    'total': len(patterns),
    'high_confidence': len([p for p in patterns if p['confidence'] > 0.8]),
    'by_type': count_by_type(patterns)
}
return summary
```

### Resumable Workflows

```python
import json
from pathlib import Path

cache_file = Path("consolidation_cache.json")

# Load from cache if available
if cache_file.exists():
    with open(cache_file) as f:
        result = json.load(f)
else:
    # Run consolidation (expensive operation)
    result = client.consolidate(strategy="quality", days_back=30)

    # Cache for later use
    with open(cache_file, "w") as f:
        json.dump(result, f)

# Process cached result
patterns = process_patterns(result['patterns'])
```

### Streaming Large Results

```python
# For very large results, process in batches
results = client.recall(query="...", k=1000)

# Process in chunks
batch_size = 100
for i in range(0, len(results), batch_size):
    batch = results[i:i+batch_size]
    processed = process_batch(batch)
    # Store or process further
```

## Configuration

Athena HTTP server runs by default on `http://localhost:3000`. Configure with environment variables:

```bash
# Change port
ATHENA_PORT=8000

# Enable debug logging
DEBUG=1

# Custom database path
ATHENA_DB_PATH=/path/to/memory.db
```

## See Also

- [Anthropic Engineering Blog: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Claude Code Documentation](https://code.claude.com/docs)
- [MCP Specification](https://modelcontextprotocol.io/)

## Next Steps

1. ✅ Registry endpoints implemented
2. ✅ Client library created
3. ✅ Examples provided
4. ⏳ Extend tools registry with all 228 operations
5. ⏳ Add more sophisticated result processing examples
6. ⏳ Implement caching and resumability patterns
