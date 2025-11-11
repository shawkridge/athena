# Athena Hooks - Local-First Python API Guide

## Overview

The hooks system has been refactored to use **direct Python API** calls instead of HTTP. This means:

- ✅ **No HTTP server required** - works entirely in Python
- ✅ **Faster execution** - no network latency
- ✅ **Better error handling** - full Python exceptions
- ✅ **Simpler debugging** - direct logs

## Architecture

```
Hook Script (shell)
    ↓
Agent Invoker (Python)
    ↓
Athena Direct Client (Python wrapper)
    ↓
MemoryAPI (Direct Python API)
    ↓
Memory Layers (Database, Embeddings, LLM)
```

## Core Components

### 1. AthenaDirectClient (`athena_direct_client.py`)

Wrapper around Athena's MemoryAPI. Provides simple methods:

```python
from athena_direct_client import AthenaDirectClient

client = AthenaDirectClient()

# Check health
health = client.health()

# Recall memories
results = client.recall(query="recent work", k=5)

# Store memory
memory_id = client.remember(
    content="Important finding",
    memory_type="semantic"
)

# Record episodic event
event_id = client.record_event(
    event_type="action",
    content="Ran tests",
    importance=0.8
)

# Run consolidation
results = client.run_consolidation(strategy="balanced")

# Check cognitive load
load = client.check_cognitive_load()

# Get memory health
health = client.get_memory_health()
```

### 2. AgentInvoker (`agent_invoker.py`)

Orchestrates autonomous agent invocation. Agents are defined in `AGENT_REGISTRY`:

```python
from agent_invoker import AgentInvoker

invoker = AgentInvoker()

# Invoke an agent
success = invoker.invoke_agent("session-initializer", context={
    "session_id": "sess-123",
    "timestamp": "2025-11-11T15:30:00Z"
})

# Get agents for a trigger
agents = invoker.get_agents_for_trigger("session_start")
# Returns: ["session-initializer"]
```

## Agent Registry

Agents are defined in `AgentInvoker.AGENT_REGISTRY`:

```python
{
    "agent-name": {
        "trigger": "session_start|user_prompt_submit|post_tool_use_batch|pre_execution|session_end|post_task_completion",
        "description": "What this agent does",
        "priority": 100,  # Higher = runs first
        "api_method": "recall|remember|record_event|run_consolidation|check_cognitive_load|get_memory_health|get_memory_quality_summary|forget",
        "api_args": {
            "query": "search query",  # For recall
            # ... other args specific to method
        }
    }
}
```

## Hook Script Pattern

All hooks follow this pattern:

```bash
#!/bin/bash
# Hook: [Name]

set -e

# Logging
log() {
    echo -e "[HOOK] $1" >&2
}

log "Starting hook..."

# Call Python to invoke agents
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from agent_invoker import AgentInvoker

try:
    invoker = AgentInvoker()
    
    # Invoke agent(s) for this hook trigger
    success = invoker.invoke_agent("agent-name", context={
        # Context data
    })
    
    if success:
        print("✓ Agent invoked successfully", file=sys.stderr)
    else:
        print("⚠ Agent invocation had warnings", file=sys.stderr)
        
except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
PYTHON_EOF

log "Hook complete"
exit 0
```

## Trigger Points

### session-start
Fired when Claude Code session begins

**Agents:**
- `session-initializer` - Load context and goals

### user-prompt-submit
Fired when user submits a query

**Agents:**
- `rag-specialist` (priority 100) - Search and inject context
- `research-coordinator` (priority 99) - Multi-source research
- `gap-detector` (priority 90) - Find knowledge gaps
- `attention-manager` (priority 85) - Manage cognitive load
- `procedure-suggester` (priority 80) - Suggest procedures

### post-tool-use-batch
Fired every 10 tool executions

**Agents:**
- `attention-optimizer` - Optimize focus

### pre-execution
Fired before major work begins

**Agents:**
- `plan-validator` - Validate execution plans
- `goal-orchestrator` - Check goal conflicts
- `strategy-selector` - Confirm strategy

### session-end
Fired when Claude Code session ends

**Agents:**
- `consolidation-engine` (priority 100) - Extract patterns
- `workflow-learner` (priority 95) - Learn procedures
- `quality-auditor` (priority 90) - Assess quality

### post-task-completion
Fired when a task completes

**Agents:**
- `execution-monitor` - Record completion

## Configuration

File: `~/.claude/hooks/config.env`

```bash
# Enable debug logging
export ATHENA_DEBUG=0

# Optional: Custom database path
# export ATHENA_DB_PATH="~/.claude/memory.db"

# If athena not in Python path, set:
# export PYTHONPATH="/path/to/athena/src:$PYTHONPATH"
```

## Debugging

### Enable verbose logging

In your hook script:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
```

### Check if API is available

```python
from athena_direct_client import AthenaDirectClient

client = AthenaDirectClient()
health = client.health()

if health.get('status') == 'healthy':
    print("✅ API ready")
else:
    print(f"❌ API not available: {health.get('message')}")
```

### Check agent registry

```python
from agent_invoker import AgentInvoker

invoker = AgentInvoker()

# List all agents
for name, config in invoker.AGENT_REGISTRY.items():
    print(f"{name}: trigger={config['trigger']}, priority={config['priority']}")

# Get agents for specific trigger
agents = invoker.get_agents_for_trigger("session_start")
print(f"Session start agents: {agents}")
```

## Performance

All operations are local Python calls:

- **recall**: ~100-200ms (database + embeddings)
- **remember**: ~50-100ms (database write)
- **record_event**: ~30-50ms (database write)
- **run_consolidation**: 2-5s (depends on event count)
- **check_cognitive_load**: ~10-20ms (metadata lookup)
- **get_memory_health**: ~50-100ms (database scan)

No network overhead - all operations are in-process.

## Error Handling

All client methods return `None` or `False` on error and log warnings:

```python
# Safe to call even if services unavailable
results = client.recall("query")
if results is None:
    # Handle gracefully - logs explain why
    results = []
```

## Migration from HTTP

**Old way (removed):**
```bash
# HTTP call to external service
curl http://localhost:8000/api/memory/recall?query=...
```

**New way (direct API):**
```python
# Direct Python API call
client = AthenaDirectClient()
results = client.recall(query="...")
```

All agent configuration changed from `http_endpoint` to `api_method`:

```python
# Old
"rag-specialist": {
    "http_endpoint": "/api/memory/recall",
    "http_method": "GET",
}

# New
"rag-specialist": {
    "api_method": "recall",
    "api_args": {"query": "...", "k": 5},
}
```

---

**Status**: Production-ready local-first implementation
**Version**: 1.0 (Post-HTTP-migration)
**Last Updated**: November 11, 2025
