# Athena Tools

Filesystem-discoverable tools for agent execution.

## Categories

### Consolidation (2 tools)
- `consolidate`: Extract patterns from episodic events (sleep-like consolidation)
- `get_patterns`: Retrieve learned patterns from consolidation

### Memory (3 tools)
- `recall`: Search and retrieve memories using semantic search
- `remember`: Record a new episodic event or semantic memory
- `forget`: Delete a memory by ID

### Planning (2 tools)
- `plan_task`: Decompose a task into an executable plan
- `validate_plan`: Validate a plan using formal verification and scenario testing

## Usage

### Discover Tools
```bash
ls /athena/tools/              # List categories
ls /athena/tools/memory/       # List memory tools
cat /athena/tools/memory/recall.py  # Read tool definition
```

### Use a Tool
```python
from athena.tools.memory.recall import recall
results = recall('query', limit=10)
```
