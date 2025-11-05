---
category: skill
name: analyze-dependencies
description: Analyze and visualize dependency graphs to understand architecture
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.80
trigger: Circular dependencies found, architecture unclear, "dependencies" mentioned, coupling too high
---

# Analyze Dependencies Skill

Guides analysis of project dependencies and architectural coupling.

## When I Invoke This

You have:
- Circular dependencies to understand/break
- Want to understand architecture visually
- Module coupling seems too tight
- Import structure confusing
- Need dependency matrix

## What I Do

I guide dependency analysis in these phases:

```
1. EXTRACT Phase: Find all dependencies
   → Parse imports
   → Build dependency graph
   → Identify circular paths
   → Check coupling levels

2. VISUALIZE Phase: Create dependency map
   → Layer dependency diagrams
   → Show circular dependencies
   → Highlight problematic imports
   → Identify clusters

3. ANALYZE Phase: Evaluate architecture
   → Check layering (proper separation?)
   → Measure coupling (too tight?)
   → Find circular dependencies
   → Identify improvement opportunities

4. REPORT Phase: Document findings
   → Create dependency matrix
   → Show circular paths
   → Suggest fixes
   → Prioritize improvements
```

## Dependency Analysis Techniques

### Technique 1: Find Circular Dependencies

```bash
# Python: use networkx to detect cycles
python3 << 'EOF'
import ast
import os
from collections import defaultdict, deque

def find_imports(file_path):
    """Extract imports from Python file."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

# Build dependency graph
dependencies = defaultdict(set)
for root, dirs, files in os.walk('src/memory_mcp'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            module = path.replace('src/', '').replace('.py', '').replace('/', '.')
            imports = find_imports(path)
            for imp in imports:
                if imp.startswith('memory_mcp'):
                    dependencies[module].add(imp)

# Find cycles using DFS
def find_cycles(graph):
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles

cycles = find_cycles(dependencies)
for cycle in cycles:
    print(f"Circular dependency: {' -> '.join(cycle)}")
EOF
```

**Output**: Shows all circular dependencies in the project

---

### Technique 2: Measure Coupling

```bash
# Count dependencies per module
python3 << 'EOF'
from collections import defaultdict

# For each module, count how many others depend on it
dependents = defaultdict(int)
for module, deps in dependencies.items():
    for dep in deps:
        dependents[dep] += 1

# Modules with high dependents = core modules
for module, count in sorted(dependents.items(), key=lambda x: -x[1])[:10]:
    print(f"{module}: {count} dependents (high coupling)")
EOF
```

**Output**: Shows which modules are most depended upon

---

### Technique 3: Layered Dependency Check

```python
# Memory MCP should have layers:
# Layer 1 (top):    Commands, MCP handlers
# Layer 2:          Skills, Agents
# Layer 3:          Managers, Integration
# Layer 4:          Individual layers (episodic, semantic, etc.)
# Layer 5 (bottom): Core (database, models)

# Check: Do dependencies flow downward only?
# Top layer should NOT import from itself!

def check_layering(dependencies):
    layers = {
        'mcp': ['mcp/handlers.py'],
        'skills': ['skills/'],
        'managers': ['integration/', 'consolidation/'],
        'layers': ['episodic/', 'semantic/', 'memory/', 'graph/', 'procedural/'],
        'core': ['core/', 'models.py'],
    }

    for module, deps in dependencies.items():
        current_layer = get_layer(module, layers)
        for dep in deps:
            dep_layer = get_layer(dep, layers)
            if layer_order[current_layer] >= layer_order[dep_layer]:
                print(f"⚠️ BAD: {current_layer} ({module}) depends on {dep_layer} ({dep})")
```

---

## Common Dependency Issues

### Issue 1: Circular Dependency

**Symptom**: Module A imports B, B imports A

```python
# authStore.ts
import { swarmApi } from './swarmApi';

export const login = async (credentials) => {
    return await swarmApi.login(credentials);
};

# swarmApi.ts
import { authStore } from './stores/authStore';  // CIRCULAR!

export const login = async (credentials) => {
    authStore.setUser(response.user);
};
```

**Fix**:
```python
# Option 1: Break the circle - move shared logic
// shared/auth.ts
export const handleAuthResponse = (response) => {
    return response.user;
};

// authStore.ts - uses shared logic
import { handleAuthResponse } from './shared/auth';

// swarmApi.ts - uses shared logic
import { handleAuthResponse } from './shared/auth';

# Option 2: Inject dependency
// swarmApi.ts - takes callback
export const login = async (credentials, onSuccess) => {
    const response = await api.post('/login', credentials);
    onSuccess(response);
};
```

**Impact**: Prevents import errors, simplifies refactoring

---

### Issue 2: Tight Coupling

**Symptom**: Module depends on too many others

```python
# ❌ Bad: consolidation imports from 5 layers
from memory_mcp.episodic import EpisodicStore
from memory_mcp.semantic import SemanticStore
from memory_mcp.procedural import ProceduralStore
from memory_mcp.graph import GraphStore
from memory_mcp.meta import MetaStore

# All tightly coupled!

# ✓ Good: consolidation uses manager
from memory_mcp.core.manager import UnifiedMemoryManager

manager = UnifiedMemoryManager()
episodic_events = manager.query_episodic()
semantic_results = manager.consolidate()
```

**Fix**: Use manager/coordinator pattern to reduce direct dependencies

---

### Issue 3: Implicit Dependencies

**Symptom**: Hidden dependency on initialization order

```python
# ❌ Bad: Assumes global state is initialized
class UserService:
    def get_user(self, user_id):
        # Assumes singleton is already created!
        user_store = UserStore.instance()
        return user_store.get(user_id)

# What if UserStore wasn't initialized?

# ✓ Good: Explicit dependency injection
class UserService:
    def __init__(self, user_store: UserStore):
        self.user_store = user_store

    def get_user(self, user_id):
        return self.user_store.get(user_id)

# Clear: needs UserStore to work
```

**Fix**: Use dependency injection instead of singletons

---

## Step-by-Step Analysis Process

### Step 1: Extract Dependencies
```bash
# For Python
python -m py_modules --help
# Or manual extraction (see techniques above)

# For TypeScript/JavaScript
npm install dependency-cruiser
npx depcruise src/ --output-type text

# For all files
find src -name "*.py" | while read f; do
  echo "=== $f ==="
  grep "^from\|^import" "$f"
done
```

### Step 2: Build Graph
```bash
# Create dependency matrix
# List rows: modules
# List cols: modules
# Mark X where A depends on B
```

### Step 3: Identify Issues
```
Look for:
- Cycles (X → Y → X)
- High coupling (module many depend on)
- Layer violations (lower layer imports upper)
- Circular imports (A imports B, B imports A)
```

### Step 4: Document Findings
```
For each issue:
- What: Module X imports Module Y (creates cycle)
- Why: Problem - makes refactoring hard, potential import errors
- How: Solution - extract shared code, use injection, etc.
```

### Step 5: Implement Fixes
```bash
# For each circular dependency
# 1. Understand the circular path
# 2. Identify the breaking point
# 3. Refactor to break cycle
# 4. Verify with analysis tool
# 5. Update tests if needed
```

## Dependency Analysis Checklist

- [ ] All dependencies extracted
- [ ] Circular dependencies identified
- [ ] Coupling metrics calculated
- [ ] Layering checked (top to bottom only)
- [ ] Issues documented with examples
- [ ] Solutions proposed for each issue
- [ ] Priority determined (which to fix first)
- [ ] Fixes implemented
- [ ] Verified with re-analysis

## Related Skills

- **refactor-code** - Often needed after dependency analysis
- **debug-integration-issue** - Circular deps cause integration problems
- **code-review** - Review ensures no new circular deps

## Success Criteria

✓ Circular dependencies identified
✓ Coupling metrics calculated
✓ Layering verified
✓ Issues documented
✓ Solutions proposed
✓ High-impact circular deps broken
✓ Architecture improved
