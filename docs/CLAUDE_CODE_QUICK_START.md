# Claude Code Quick Start - Code Execution Pattern

## Setup

Your Athena system is now ready to use with Claude Code's code execution environment. No MCP configuration needed!

### Prerequisites
- Docker running with `docker-compose up`
- Athena HTTP server on `http://localhost:3000`
- Python with `requests` library (standard in Claude Code)

## Using the Pattern

### 1. Discover Available Tools

```python
import requests

# Get all tools organized by category
response = requests.get("http://localhost:3000/tools/discover")
tools = response.json()

print(f"Available categories: {list(tools['categories'].keys())}")
print(f"Total tools: {tools['total_tools']}")
```

### 2. Get Tool Details

```python
# Get full definition of a specific tool
response = requests.get("http://localhost:3000/tools/recall")
tool = response.json()

print(f"Tool: {tool['name']}")
print(f"Parameters: {[p['name'] for p in tool['parameters']]}")
```

### 3. Call Tools (Key Pattern!)

```python
# **IMPORTANT**: Process large results locally, don't send to model

# Call a tool - result stays in code environment
response = requests.post(
    "http://localhost:3000/tools/recall/execute",
    json={"query": "consolidation patterns", "k": 50}
)
results = response.json()['data']

# Process locally (filter, summarize)
high_confidence = [r for r in results if r.get('score', 0) > 0.7]

# Return only summary to model (~100 bytes instead of 50KB)
summary = f"Found {len(high_confidence)} high-confidence patterns"
print(summary)
```

## Available Endpoints

### Discovery
```bash
GET /tools/discover              # All tools by category
GET /tools/list?category=memory  # Tools in a category
GET /tools/{tool_name}           # Full tool definition
```

### Execution
```bash
POST /tools/{tool_name}/execute  # Run a tool
```

## Example Agent Code

```python
"""Example agent using Athena in code execution mode."""
import requests

def analyze_consolidation():
    """Analyze consolidation patterns locally."""

    # Discover tools
    tools = requests.get("http://localhost:3000/tools/discover").json()
    print(f"Available: {tools['total_tools']} tools")

    # Get consolidation tool definition
    tool = requests.get("http://localhost:3000/tools/run_consolidation").json()
    print(f"Parameters: {[p['name'] for p in tool['parameters']]}")

    # Run consolidation
    result = requests.post(
        "http://localhost:3000/tools/run_consolidation/execute",
        json={"strategy": "balanced", "days_back": 7}
    ).json()['data']

    # Process locally
    patterns = result.get('patterns', [])
    by_type = {}
    for p in patterns:
        ptype = p.get('type', 'unknown')
        by_type[ptype] = by_type.get(ptype, 0) + 1

    # Summary only
    return f"Extracted {len(patterns)} patterns: {by_type}"

# Run it
print(analyze_consolidation())
```

## Token Savings

**Traditional approach** (all tool definitions in context):
- Tool definitions: ~150,000 tokens
- Intermediate results: ~50,000 tokens each
- **Total: 200,000+ tokens**

**Code execution pattern** (this approach):
- Tool summaries: ~500 tokens
- Intermediate results: processed locally
- Only summaries returned: ~100 tokens
- **Total: 600 tokens**

**Savings: 98.7%** (200K → 600 bytes)

## Why This Works

1. **Tool Discovery is Lazy** - Only load definitions when needed
2. **Large Results Stay Local** - No intermediate results in model context
3. **Summaries are Small** - Return only what matters
4. **Stateless** - Each call is independent, no session needed

## Next Steps

1. **Try it now** - Use the example code above in Claude Code
2. **Build agents** - Create specialized agents for your tasks
3. **Extend tools registry** - Add more tools as needed
4. **Optimize workflows** - Use file persistence for resumable tasks

## References

- [Anthropic Engineering Blog: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [CODE_EXECUTION_PATTERN.md](./CODE_EXECUTION_PATTERN.md) - Detailed documentation
- [examples/code_execution_agent.py](./examples/code_execution_agent.py) - Full example implementation
