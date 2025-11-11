# ATHENA: MCP CODE-EXECUTION PARADIGM ALIGNMENT BLUEPRINT

**Status**: 60% Current Adherence → 100% Target Adherence
**Effort**: 12-16 weeks (3-4 person-months)
**Risk Level**: Medium
**Priority**: High (core architectural shift)

---

## EXECUTIVE SUMMARY

Athena's current tool-abstraction architecture serves neuroscience-inspired memory learning. The MCP code-execution paradigm targets token efficiency and agent flexibility.

**This blueprint achieves both** by:
1. Exposing memory layers as **callable code APIs** (not predefined tools)
2. Converting **procedures to executable code** (with versioning)
3. Implementing **sandboxed code execution** (resource-limited, safe)
4. Adding **progressive discovery** (agents find APIs on-demand)
5. Enabling **privacy-preserving data handling** (tokenization + encryption)

**Outcome**: Agents write Python/TypeScript code to compose memory operations, achieving MCP's efficiency gains while preserving Athena's learning architecture.

---

## PHASE 1: MEMORY API EXPOSURE (Weeks 1-2)

### Goal
Replace tool abstraction with direct API calls. Agents call functions instead of tools.

### Architecture Change

**Before**:
```python
# handlers.py (303 handlers in one file)
class MemoryMCPServer:
    async def _handle_recall(self, args: dict):
        query = args.get("query")
        results = self.manager.recall(query)
        return [TextContent(type="text", text=json.dumps(results))]
```

**After**:
```python
# src/athena/mcp/memory_api.py (new)
class MemoryAPI:
    """Direct memory layer APIs for code execution."""

    def __init__(self, manager: UnifiedMemoryManager):
        self.manager = manager

    async def recall_semantic(
        self,
        query: str,
        limit: int = 5,
        min_confidence: float = 0.5
    ) -> List[Memory]:
        """Query semantic memory directly."""
        return self.manager.semantic_store.search(
            query=query,
            limit=limit,
            filters={"confidence": (">=", min_confidence)}
        )

    async def recall_episodic(
        self,
        time_range: Tuple[datetime, datetime],
        event_type: Optional[str] = None
    ) -> List[EpisodicEvent]:
        """Query episodic memory by time range."""
        return self.manager.episodic_store.get_events(
            start_time=time_range[0],
            end_time=time_range[1],
            event_type=event_type
        )

    async def recall_procedural(
        self,
        context: Optional[Dict] = None
    ) -> List[ExecutableProcedure]:
        """Get applicable procedures for context."""
        return self.manager.procedural_store.find_procedures(
            applicable_contexts=context.get("tags", []) if context else []
        )

    async def remember_semantic(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """Store semantic memory directly."""
        memory = Memory(
            content=content,
            memory_type="semantic",
            metadata=metadata or {}
        )
        return self.manager.semantic_store.store(memory)

    async def remember_episodic(
        self,
        content: str,
        event_type: EventType,
        context: EventContext
    ) -> int:
        """Record episodic event directly."""
        event = EpisodicEvent(
            content=content,
            event_type=event_type,
            context=context
        )
        return self.manager.episodic_store.create_event(event)

    async def consolidate(
        self,
        strategy: str = "balanced",
        lookback_hours: int = 24
    ) -> ConsolidationResult:
        """Run consolidation pipeline."""
        return self.manager.consolidator.consolidate(
            strategy=strategy,
            lookback_hours=lookback_hours
        )
```

### MCP Server Integration

```python
# src/athena/mcp/handlers.py (modified)
class MemoryMCPServer:
    def __init__(self):
        self.manager = UnifiedMemoryManager()
        self.memory_api = MemoryAPI(self.manager)  # NEW
        self._register_code_execution_tools()  # NEW

    def _register_code_execution_tools(self):
        """Register tools for agent code execution."""

        @self.server.tool()
        def execute_memory_code(code: str) -> str:
            """Execute Python code with access to memory APIs."""
            return asyncio.run(self._execute_sandboxed(code))

        @self.server.tool()
        def discover_apis() -> Dict[str, List[str]]:
            """Discover available memory APIs."""
            return {
                "recall": [
                    "recall_semantic(query: str, limit: int)",
                    "recall_episodic(time_range, event_type)",
                    "recall_procedural(context)",
                ],
                "remember": [
                    "remember_semantic(content, metadata)",
                    "remember_episodic(content, event_type, context)",
                ],
                "consolidate": [
                    "consolidate(strategy, lookback_hours)",
                ],
                "execute": [
                    "execute_procedure(name, **kwargs)",
                ],
                "learn": [
                    "learn_procedure(name, code, description)",
                ]
            }

        @self.server.tool()
        def get_api_docs(api_name: str) -> str:
            """Get detailed docs for specific API."""
            # Returns docstring, signature, examples
            return self._get_api_documentation(api_name)

    async def _execute_sandboxed(self, code: str) -> str:
        """Execute agent-written code safely."""
        # Phase 3 implementation
        sandbox = SandboxExecutor(self.memory_api)
        result = await sandbox.execute(code)
        return json.dumps(result)
```

### Deliverables
- [ ] `src/athena/mcp/memory_api.py` (300 lines) - Core API classes
- [ ] `src/athena/mcp/handlers.py` (updated) - Register code execution tools
- [ ] `src/athena/mcp/api_registry.py` (200 lines) - API discovery mechanism
- [ ] Tests: `tests/mcp/test_memory_api.py` (250 lines)

### Success Metrics
- All memory layer queries accessible via API
- Zero regression on existing tool functionality
- Agent can call `await athena.recall_semantic()` directly
- API discovery working for all functions

---

## PHASE 2: EXECUTABLE PROCEDURES (Weeks 3-6)

### Goal
Convert procedures from metadata to executable Python/TypeScript code. Agents can run procedures directly.

### Current State (Metadata-Based)
```python
# Procedure stored as metadata
{
    "name": "validate_typescript_project",
    "template": "npm run lint; npm run test",
    "steps": [
        {"action": "npm", "args": ["run", "lint"]},
        {"action": "npm", "args": ["run", "test"]},
    ],
    "success_rate": 0.87,
    "version": 1
}
```

### Target State (Code-Based)
```python
# Procedure stored as executable code
async def validate_typescript_project():
    """Validate TypeScript project with linting and tests."""
    try:
        # Run linter
        lint_result = await shell.run("npm run lint")
        if lint_result.exit_code != 0:
            return ExecutionResult(
                success=False,
                error=lint_result.stderr,
                logs=lint_result.stdout
            )

        # Run tests
        test_result = await shell.run("npm run test")
        if test_result.exit_code != 0:
            return ExecutionResult(
                success=False,
                error=test_result.stderr,
                logs=test_result.stdout
            )

        return ExecutionResult(
            success=True,
            logs=lint_result.stdout + test_result.stdout,
            duration_ms=time.time()
        )
    except Exception as e:
        return ExecutionResult(success=False, error=str(e))
```

### Database Schema Change

```python
# src/athena/procedural/models.py (modified)

from typing import Callable

class ExecutableProcedure(BaseModel):
    """Versioned, executable procedure."""

    id: Optional[int] = None
    project_id: int
    name: str
    category: ProcedureCategory
    description: Optional[str]

    # CHANGE: Store code, not metadata
    source_code: str  # Python/TypeScript source
    signature: str  # "(a: int, b: str) -> bool"

    # Version control
    version: int = 1
    git_hash: str  # Commit hash of code
    git_branch: str = "main"
    git_tag: Optional[str]  # Release tags

    # Previous versions (for rollback)
    previous_versions: List[Dict[str, Any]] = []

    # Learning metrics
    executions: int = 0
    success_rate: float = 1.0
    avg_duration_ms: Optional[float] = None

    # Metadata
    created_at: datetime
    created_by: str  # Agent name or "user"
    last_executed: Optional[datetime]
    last_modified: Optional[datetime]

    # Execution history (for rollback)
    execution_log: List[ExecutionRecord] = []

    async def execute(self, **kwargs) -> ExecutionResult:
        """Execute the procedure code."""
        executor = SandboxExecutor()
        return await executor.execute(self.source_code, kwargs)

    def rollback_to_version(self, version: int) -> 'ExecutableProcedure':
        """Restore previous version of procedure."""
        if version not in [v["version"] for v in self.previous_versions]:
            raise ValueError(f"Version {version} not found")

        previous = next(v for v in self.previous_versions if v["version"] == version)
        self.source_code = previous["source_code"]
        self.git_hash = previous["git_hash"]
        self.version = version + 1  # Create new version for rollback
        return self
```

### Procedure Storage (Git-Backed)

```python
# src/athena/procedural/git_store.py (new)

import pygit2
from pathlib import Path

class GitBackedProcedureStore:
    """Store procedures as git-versioned files."""

    def __init__(self, repo_path: str = "~/.athena/procedures"):
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self.repo = pygit2.init_repository(str(self.repo_path))

    async def save_procedure(self, procedure: ExecutableProcedure):
        """Save procedure as Python file in git."""
        file_path = self.repo_path / f"{procedure.name}.py"

        # Write source code
        file_path.write_text(procedure.source_code)

        # Commit to git
        index = self.repo.index
        index.add(str(file_path.relative_to(self.repo_path)))
        index.write()

        # Create commit
        author = pygit2.Signature(procedure.created_by, "agent@athena.local")
        tree = index.write_tree()
        commit_id = self.repo.create_commit(
            "HEAD",
            author,
            author,
            f"Procedure: {procedure.name} v{procedure.version}",
            tree,
            [self.repo.head.target]
        )

        procedure.git_hash = str(commit_id)
        return procedure

    async def get_procedure(self, name: str, version: Optional[int] = None):
        """Load procedure from git."""
        file_path = self.repo_path / f"{name}.py"

        if not file_path.exists():
            return None

        source_code = file_path.read_text()

        # If specific version requested, checkout that commit
        if version is not None:
            # Use git tags: "procedure-name-v1", "procedure-name-v2"
            tag_name = f"{name}-v{version}"
            try:
                tag = self.repo.references[f"refs/tags/{tag_name}"]
                commit = self.repo[tag.target]
                source_code = self.repo[commit.tree[f"{name}.py"].id].data.decode()
            except KeyError:
                raise ValueError(f"Version {version} not found for {name}")

        return source_code

    async def list_procedures(self) -> List[str]:
        """List all stored procedures."""
        return [f.stem for f in self.repo_path.glob("*.py")]
```

### Procedure Learning (Auto-Extraction)

```python
# src/athena/procedural/code_extractor.py (new)

class CodeExtractor:
    """Extract executable code from event patterns."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def extract_procedure_from_pattern(
        self,
        pattern: TemporalPattern,
        event_sequence: List[EpisodicEvent]
    ) -> Optional[ExecutableProcedure]:
        """Convert event pattern into executable Python code."""

        # Use LLM to generate code from event sequence
        prompt = self._build_extraction_prompt(event_sequence)

        generated_code = await self.llm.generate(prompt)

        # Validate generated code
        if not self._validate_code(generated_code):
            return None

        # Create procedure object
        procedure = ExecutableProcedure(
            name=pattern.name,
            source_code=generated_code,
            description=f"Auto-learned from {len(event_sequence)} events",
            created_by="learned"
        )

        return procedure

    def _build_extraction_prompt(self, events: List[EpisodicEvent]) -> str:
        """Build prompt for LLM code generation."""
        return f"""
Given this sequence of events, generate Python code that reproduces the pattern:

{self._format_events(events)}

Generate:
1. Function definition with type hints
2. Error handling (try/except)
3. Return ExecutionResult(success=bool, logs=str)

Return ONLY the Python code, no explanation.
"""

    def _validate_code(self, code: str) -> bool:
        """Validate generated code is syntactically correct."""
        try:
            compile(code, "<string>", "exec")
            # Check for dangerous patterns
            dangerous = ["__import__", "eval", "exec", "open"]
            return not any(d in code for d in dangerous)
        except SyntaxError:
            return False
```

### Procedure Execution

```python
# src/athena/procedural/executor.py (modified)

class ProcedureExecutor:
    """Execute procedures in sandbox."""

    def __init__(self, git_store: GitBackedProcedureStore):
        self.git_store = git_store
        self.sandbox = SandboxExecutor()

    async def execute(
        self,
        name: str,
        **kwargs
    ) -> ExecutionResult:
        """Execute procedure by name."""
        procedure = await self.git_store.get_procedure(name)

        if not procedure:
            raise ProcedureNotFound(f"Procedure '{name}' not found")

        # Execute in sandbox
        result = await self.sandbox.execute(procedure, kwargs)

        # Record execution
        self._record_execution(name, result)

        return result

    def _record_execution(self, name: str, result: ExecutionResult):
        """Record execution for learning."""
        # Update success_rate, avg_duration, execution_log
        # This feeds into next iteration of procedure refinement
```

### MCP Integration

```python
# src/athena/mcp/api.py (updated MemoryAPI)

class MemoryAPI:
    # ... existing methods ...

    async def execute_procedure(self, name: str, **kwargs) -> ExecutionResult:
        """Execute a learned procedure."""
        return await self.manager.procedure_executor.execute(name, **kwargs)

    async def learn_procedure(
        self,
        name: str,
        source_code: str,
        description: str
    ) -> ExecutableProcedure:
        """Learn new procedure from code."""
        procedure = ExecutableProcedure(
            name=name,
            source_code=source_code,
            description=description,
            created_by="agent"
        )
        await self.manager.git_store.save_procedure(procedure)
        return procedure

    async def list_procedures(self) -> List[str]:
        """List all learned procedures."""
        return await self.manager.git_store.list_procedures()

    async def rollback_procedure(self, name: str, to_version: int):
        """Restore previous version of procedure."""
        # Implementation for rollback
```

### Deliverables
- [ ] `src/athena/procedural/models.py` (updated) - ExecutableProcedure model
- [ ] `src/athena/procedural/git_store.py` (300 lines) - Git-backed storage
- [ ] `src/athena/procedural/code_extractor.py` (200 lines) - LLM code generation
- [ ] `src/athena/procedural/executor.py` (updated) - Execution logic
- [ ] Tests: `tests/procedural/test_executable_procedures.py` (300 lines)

### Success Metrics
- Procedures stored as Python source code
- Agent can call `await athena.execute_procedure("validate_code")`
- Version control working (git history)
- Rollback capability functional
- LLM-based code extraction working

---

## PHASE 3: SANDBOXED CODE EXECUTION (Weeks 7-9)

### Goal
Implement safe execution environment where agents write and run Python code with access to memory APIs.

### Sandbox Design

```python
# src/athena/sandbox/executor.py (new)

from RestrictedPython import compile_restricted

class SandboxExecutor:
    """Execute agent code safely with resource limits."""

    def __init__(
        self,
        memory_api: MemoryAPI,
        config: SandboxConfig = None
    ):
        self.memory_api = memory_api
        self.config = config or SandboxConfig()

    async def execute(
        self,
        code: str,
        context: Optional[Dict] = None,
        timeout_sec: float = 30
    ) -> ExecutionResult:
        """Execute code in isolated sandbox."""

        # 1. Validate code syntax
        if not self._validate_syntax(code):
            return ExecutionResult(
                success=False,
                error="Syntax error in code"
            )

        # 2. Check for blacklisted operations
        if self._contains_dangerous_patterns(code):
            return ExecutionResult(
                success=False,
                error="Code contains disallowed operations"
            )

        # 3. Compile to bytecode with RestrictedPython
        compiled = compile_restricted(code, "<string>", "exec")

        if compiled.errors:
            return ExecutionResult(
                success=False,
                error=f"Compilation errors: {compiled.errors}"
            )

        # 4. Create restricted namespace
        namespace = self._create_namespace(context or {})

        # 5. Execute with timeout and resource limits
        try:
            result = await asyncio.wait_for(
                self._execute_with_limits(compiled, namespace),
                timeout=timeout_sec
            )
            return ExecutionResult(success=True, output=result)

        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                error=f"Execution timeout ({timeout_sec}s)"
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                traceback=traceback.format_exc()
            )

    def _create_namespace(self, context: Dict) -> Dict:
        """Create restricted execution namespace."""
        return {
            # Memory API access
            "athena": self.memory_api,

            # Safe builtins
            "print": self._safe_print,
            "len": len,
            "range": range,
            "list": list,
            "dict": dict,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "tuple": tuple,
            "set": set,

            # Safe imports
            "json": self._safe_json_module,
            "datetime": datetime,
            "time": time,

            # User context
            **context,

            # Execution metadata
            "__builtins__": {},
        }

    async def _execute_with_limits(self, compiled, namespace):
        """Execute code with resource monitoring."""
        # Use `resource` module to limit CPU, memory
        import resource

        # Limit memory to 512MB
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)

        # Execute in thread pool (for CPU limiting)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            exec,
            compiled.code,
            namespace
        )

    def _validate_syntax(self, code: str) -> bool:
        """Check basic syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _contains_dangerous_patterns(self, code: str) -> bool:
        """Detect dangerous patterns."""
        dangerous = [
            "__import__",
            "eval",
            "exec",
            "open",
            "__code__",
            "__globals__",
            "subprocess",
        ]
        return any(d in code for d in dangerous)

    def _safe_print(self, *args, **kwargs):
        """Safe print with output limits."""
        # Limit output to 10KB
        output = " ".join(str(a) for a in args)
        if len(output) > 10000:
            output = output[:10000] + "... [truncated]"
        return output

    @property
    def _safe_json_module(self):
        """Provide safe json module."""
        return type('SafeJSON', (), {
            'dumps': json.dumps,
            'loads': json.loads,
        })()
```

### Sandbox Configuration

```python
# src/athena/sandbox/config.py (new)

from dataclasses import dataclass

@dataclass
class SandboxConfig:
    """Configuration for code execution sandbox."""

    # Resource limits
    timeout_sec: float = 30  # 30 second execution timeout
    memory_limit_mb: int = 512  # 512MB memory limit
    cpu_limit_pct: float = 50  # 50% CPU usage limit
    max_output_bytes: int = 10000  # 10KB max output

    # API access limits
    max_api_calls: int = 100  # Max memory API calls per execution
    max_memory_queries: int = 50  # Max queries
    max_memory_writes: int = 50  # Max writes

    # Code restrictions
    allow_imports: List[str] = None  # None = only safe modules
    dangerous_patterns: List[str] = None  # Patterns to block

    def __post_init__(self):
        if self.allow_imports is None:
            self.allow_imports = ["json", "datetime", "math", "re"]

        if self.dangerous_patterns is None:
            self.dangerous_patterns = [
                "__import__", "eval", "exec", "open",
                "subprocess", "__code__", "__globals__",
            ]
```

### Agent Code Execution Example

Agents can now write code like this:

```typescript
// Agent writes this code
const code = `
# Get recent events
recent_events = await athena.recall_episodic(
    time_range=(now - timedelta(days=1), now),
    event_type="ACTION"
)

# Filter for completed tasks
completed = [e for e in recent_events if "completed" in e.content.lower()]

# Consolidate patterns
consolidated = await athena.consolidate("balanced")

# Save for later
await athena.learn_procedure("auto_consolidate_daily", source_code=__code__)

print(f"Found {len(completed)} completed tasks")
print(f"Consolidated {len(consolidated)} patterns")
`;

// Execute the code
const result = await athena.execute_code(code);
// Returns: ExecutionResult with success, output, logs
```

### MCP Tool Registration

```python
# src/athena/mcp/api.py (updated)

class MemoryAPI:
    async def execute_code(self, code: str, timeout_sec: float = 30) -> ExecutionResult:
        """Execute arbitrary Python code with memory API access."""
        sandbox = SandboxExecutor(self, SandboxConfig(timeout_sec=timeout_sec))
        return await sandbox.execute(code)
```

### Deliverables
- [ ] `src/athena/sandbox/executor.py` (400 lines) - Core execution engine
- [ ] `src/athena/sandbox/config.py` (100 lines) - Configuration
- [ ] `src/athena/sandbox/monitoring.py` (200 lines) - Resource monitoring
- [ ] Tests: `tests/sandbox/test_executor.py` (350 lines)

### Success Metrics
- Agent code executes safely with timeout/memory limits
- Dangerous patterns detected and blocked
- RestrictedPython compilation working
- Memory API accessible from agent code
- Resource limits enforced

---

## PHASE 4: PROGRESSIVE DISCOVERY & TOOL MARKETPLACE (Weeks 10-12)

### Goal
Implement filesystem-based API discovery. Agents discover available functions on-demand.

### Filesystem Structure

```
src/athena/api/
├── __init__.py
├── discovery.py      # API discovery system
├── memory/
│   ├── __init__.py
│   ├── recall.py    # recall_semantic, recall_episodic, recall_procedural
│   ├── remember.py  # remember_semantic, remember_episodic
│   └── consolidate.py
├── graph/
│   ├── __init__.py
│   ├── entities.py
│   └── relations.py
├── procedural/
│   ├── __init__.py
│   ├── execute.py
│   └── learn.py
└── marketplace/
    ├── __init__.py
    └── community_procedures.py
```

### API Discovery

```python
# src/athena/api/discovery.py (new)

import inspect
from pathlib import Path

class APIDiscovery:
    """Discover available memory APIs at runtime."""

    def __init__(self, api_root: str = "src/athena/api"):
        self.api_root = Path(api_root)
        self._cache = {}

    def discover_all(self) -> Dict[str, List[APISpec]]:
        """Discover all available APIs."""
        apis = {}

        for category_dir in self.api_root.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            category = category_dir.name
            apis[category] = self._discover_category(category_dir)

        return apis

    def _discover_category(self, category_dir: Path) -> List[APISpec]:
        """Discover APIs in a category."""
        specs = []

        for file_path in category_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            module = self._import_module(file_path)

            for name, obj in inspect.getmembers(module):
                if inspect.iscoroutinefunction(obj):
                    spec = self._extract_spec(name, obj)
                    specs.append(spec)

        return specs

    def _extract_spec(self, name: str, func) -> APISpec:
        """Extract API specification from function."""
        sig = inspect.signature(func)

        return APISpec(
            name=name,
            module=func.__module__,
            signature=str(sig),
            docstring=inspect.getdoc(func) or "",
            parameters=[
                APIParameter(
                    name=param.name,
                    type=str(param.annotation),
                    default=param.default,
                    description=self._extract_param_doc(func, param.name)
                )
                for param in sig.parameters.values()
            ],
            return_type=str(sig.return_annotation),
            examples=self._extract_examples(func),
        )

    def get_api(self, path: str) -> Optional[APISpec]:
        """Get specific API spec (e.g., 'memory/recall')."""
        parts = path.split("/")
        if len(parts) != 2:
            return None

        category, function = parts
        apis = self.discover_all()

        if category not in apis:
            return None

        for spec in apis[category]:
            if spec.name == function:
                return spec

        return None

    def get_apis_for_task(self, task_description: str) -> List[APISpec]:
        """Find relevant APIs for a task (using semantic search)."""
        # Use embeddings to find most relevant APIs
        all_apis = []
        for specs in self.discover_all().values():
            all_apis.extend(specs)

        task_embedding = embed(task_description)

        scores = [
            (api, cosine_similarity(
                task_embedding,
                embed(f"{api.name} {api.docstring}")
            ))
            for api in all_apis
        ]

        # Return top 5
        return [api for api, score in sorted(scores, key=lambda x: x[1], reverse=True)][:5]
```

### API Specification Model

```python
# src/athena/api/models.py (new)

from dataclasses import dataclass
from typing import Any, List, Optional

@dataclass
class APIParameter:
    """Specification for function parameter."""
    name: str
    type: str
    default: Any
    description: str

@dataclass
class APISpec:
    """Full specification of an API function."""
    name: str
    module: str
    signature: str
    docstring: str
    parameters: List[APIParameter]
    return_type: str
    examples: List[Dict[str, str]]

    def to_markdown(self) -> str:
        """Generate markdown documentation."""
        doc = f"## {self.name}\n\n"
        doc += f"{self.docstring}\n\n"
        doc += f"### Signature\n```python\n{self.signature}\n```\n\n"
        doc += f"### Parameters\n"

        for param in self.parameters:
            doc += f"- `{param.name}` ({param.type}): {param.description}\n"

        doc += f"\n### Return\n{self.return_type}\n\n"

        if self.examples:
            doc += f"### Examples\n"
            for example in self.examples:
                doc += f"```python\n{example['code']}\n```\n"

        return doc

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "signature": self.signature,
            "docstring": self.docstring,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description
                }
                for p in self.parameters
            ],
            "return_type": self.return_type,
        }
```

### Progressive Tool Loading

```python
# src/athena/mcp/handlers.py (updated)

class MemoryMCPServer:
    def __init__(self):
        self.discovery = APIDiscovery()
        self._register_discovery_tools()

    def _register_discovery_tools(self):
        """Register tools for API discovery."""

        @self.server.tool()
        def discover_apis(category: Optional[str] = None) -> Dict:
            """Discover available APIs (optionally filtered by category)."""
            if category:
                return self.discovery._discover_category(
                    self.discovery.api_root / category
                )
            return self.discovery.discover_all()

        @self.server.tool()
        def get_api_docs(api_path: str) -> str:
            """Get detailed documentation for specific API (e.g., 'memory/recall')."""
            spec = self.discovery.get_api(api_path)
            if not spec:
                return f"API '{api_path}' not found"
            return spec.to_markdown()

        @self.server.tool()
        def find_apis_for_task(task_description: str) -> List[Dict]:
            """Find relevant APIs for a task description."""
            specs = self.discovery.get_apis_for_task(task_description)
            return [spec.to_dict() for spec in specs]
```

### Marketplace System

```python
# src/athena/api/marketplace.py (new)

class ProcedureMarketplace:
    """Community-shared procedures (like Skills marketplace)."""

    def __init__(self, db: Database):
        self.db = db

    async def list_community_procedures(self, category: Optional[str] = None):
        """List shared procedures from community."""
        # Implementation for fetching from marketplace

    async def install_procedure(self, proc_id: str):
        """Install procedure from marketplace."""
        # Download, validate, store locally

    async def publish_procedure(self, procedure: ExecutableProcedure):
        """Publish local procedure to marketplace."""
        # Validate, upload, list in marketplace

    async def rate_procedure(self, proc_id: str, rating: int):
        """Rate a community procedure."""
        # 1-5 star rating for learning
```

### Deliverables
- [ ] `src/athena/api/discovery.py` (250 lines) - Discovery mechanism
- [ ] `src/athena/api/models.py` (150 lines) - Specification models
- [ ] `src/athena/api/marketplace.py` (200 lines) - Procedure sharing
- [ ] Tests: `tests/api/test_discovery.py` (200 lines)

### Success Metrics
- APIs discoverable at runtime from filesystem
- Agent can call `discover_apis("memory")`
- Documentation auto-generated from docstrings
- Semantic search finding relevant APIs
- Marketplace working for community procedures

---

## PHASE 5: PRIVACY-PRESERVING DATA HANDLING (Weeks 13-16)

### Goal
Implement automatic tokenization of sensitive data before logging. Real data flows between services; model only sees tokens.

### Tokenization System

```python
# src/athena/privacy/tokenizer.py (new)

import re
from typing import Dict, Tuple

class DataTokenizer:
    """Automatically tokenize sensitive data."""

    # Patterns for sensitive data
    PATTERNS = {
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "api_key": r"(api[_-]?key|apikey)[\s]*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "password": r"(password|passwd)[\s]*[=:]\s*['\"]?([a-zA-Z0-9_\-!@#$%^&*]{8,})['\"]?",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    }

    def __init__(self):
        self.token_map: Dict[str, str] = {}  # Reverse lookup
        self.reverse_map: Dict[str, str] = {}  # For untokenization

    def tokenize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Tokenize sensitive data in text."""
        tokenized = text
        replacements = {}

        for pattern_name, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text)

            for i, match in enumerate(matches):
                sensitive_value = match.group(0)
                token = f"[{pattern_name.upper()}_{i}]"

                tokenized = tokenized.replace(sensitive_value, token, 1)
                replacements[token] = sensitive_value
                self.reverse_map[token] = sensitive_value

        return tokenized, replacements

    def untokenize(self, tokenized_text: str) -> str:
        """Restore original data from tokens."""
        untoken = tokenized_text

        for token, value in self.reverse_map.items():
            untoken = untoken.replace(token, value)

        return untoken

    def save_tokens(self, tokens: Dict[str, str], storage: TokenStorage):
        """Save token mapping to secure storage."""
        storage.save_tokens(tokens)
```

### Secure Token Storage

```python
# src/athena/privacy/storage.py (new)

from cryptography.fernet import Fernet

class TokenStorage:
    """Store token mappings securely."""

    def __init__(self, cipher_key: str, db: Database):
        self.cipher = Fernet(cipher_key)
        self.db = db

    def save_tokens(self, tokens: Dict[str, str], session_id: str):
        """Save token mapping encrypted in database."""
        encrypted = self.cipher.encrypt(json.dumps(tokens).encode())

        self.db.execute("""
            INSERT INTO token_mappings (session_id, encrypted_tokens)
            VALUES (?, ?)
        """, (session_id, encrypted))

    def restore_tokens(self, session_id: str) -> Dict[str, str]:
        """Restore tokens for a session."""
        result = self.db.execute("""
            SELECT encrypted_tokens FROM token_mappings
            WHERE session_id = ?
        """, (session_id,)).fetchone()

        if not result:
            return {}

        decrypted = self.cipher.decrypt(result[0])
        return json.loads(decrypted)
```

### Event Storage with Tokenization

```python
# src/athena/episodic/store.py (modified)

class EpisodicStore:
    def __init__(self, db: Database, tokenizer: DataTokenizer = None):
        self.db = db
        self.tokenizer = tokenizer or DataTokenizer()

    async def create_event(self, event: EpisodicEvent) -> int:
        """Store event with automatic tokenization."""

        # Tokenize sensitive content
        tokenized_content, tokens = self.tokenizer.tokenize(event.content)

        # Store tokenized version
        event.content = tokenized_content

        # Save tokens to secure storage
        session_id = event.session_id
        token_storage = TokenStorage(cipher_key=os.getenv("CIPHER_KEY"), db=self.db)
        token_storage.save_tokens(tokens, session_id)

        # Insert event
        event_id = self.db.execute("""
            INSERT INTO episodic_events (
                project_id, session_id, timestamp, event_type,
                content, outcome, context
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event.project_id,
            event.session_id,
            event.timestamp,
            event.event_type,
            event.content,  # Tokenized
            event.outcome,
            event.context.model_dump_json()
        )).lastrowid

        return event_id

    async def get_event(self, event_id: int, untokenize: bool = False) -> Optional[EpisodicEvent]:
        """Retrieve event, optionally untokenizing."""
        result = self.db.execute("""
            SELECT * FROM episodic_events WHERE id = ?
        """, (event_id,)).fetchone()

        if not result:
            return None

        event = EpisodicEvent.from_db_row(result)

        if untokenize:
            # Restore real data
            token_storage = TokenStorage(cipher_key=os.getenv("CIPHER_KEY"), db=self.db)
            tokens = token_storage.restore_tokens(event.session_id)

            for token, value in tokens.items():
                event.content = event.content.replace(token, value)

        return event
```

### Cross-Layer Data Transfer (Privacy-Preserving)

```python
# src/athena/integration/privacy_bridge.py (new)

class PrivacyPreservingBridge:
    """Transfer data between layers while tokenizing for logging."""

    def __init__(self, tokenizer: DataTokenizer):
        self.tokenizer = tokenizer

    async def transfer_to_semantic(
        self,
        event: EpisodicEvent,
        semantic_store: SemanticStore,
        log_output: bool = False
    ) -> int:
        """Transfer episodic to semantic, optionally anonymizing logs."""

        # Real content
        real_content = event.content

        # For logging: tokenize
        logged_content, tokens = self.tokenizer.tokenize(real_content)

        # Store semantic memory with REAL content (not tokenized)
        memory = Memory(
            content=real_content,  # Real data
            memory_type="semantic",
            source_event_id=event.id
        )

        memory_id = await semantic_store.store(memory)

        # Log only tokenized version
        if log_output:
            logger.info(f"Stored semantic memory from event: {logged_content}")

        return memory_id
```

### MCP Tool Registration

```python
# src/athena/mcp/api.py (updated)

class MemoryAPI:
    async def remember_with_privacy(
        self,
        content: str,
        auto_tokenize: bool = True
    ) -> int:
        """Store memory with automatic sensitive data protection."""

        if auto_tokenize:
            tokenized, tokens = self.tokenizer.tokenize(content)
            # Store tokenized version; real data stays in secure storage
            return await self.semantic_store.store(
                Memory(content=tokenized, ...)
            )
        else:
            # Store as-is (dangerous)
            return await self.semantic_store.store(
                Memory(content=content, ...)
            )
```

### Deliverables
- [ ] `src/athena/privacy/tokenizer.py` (200 lines) - Tokenization
- [ ] `src/athena/privacy/storage.py` (150 lines) - Secure storage
- [ ] `src/athena/privacy/bridge.py` (150 lines) - Privacy-preserving transfer
- [ ] `src/athena/core/database.py` (updated) - Encryption at rest
- [ ] Tests: `tests/privacy/test_tokenization.py` (250 lines)

### Success Metrics
- Sensitive data automatically tokenized before logging
- Real data flows between services
- Model never sees unencrypted secrets
- Cross-layer transfers maintain privacy
- Token restoration working for authorized access

---

## INTEGRATION: FROM TOOL ABSTRACTION TO CODE EXECUTION

### Before (Current State)

```python
# Agent calls predefined tools
await agent.call_tool("memory", "recall", {"query": "task status"})
await agent.call_tool("memory", "remember", {"content": "...","type": "semantic"})
await agent.call_tool("consolidation", "run", {"strategy": "balanced"})

# Each is a round-trip through ReAct loop
# Model decides each step
# ~3-5 model API calls per workflow
```

### After (100% Aligned)

```python
# Agent writes Python code
code = """
# Get recent episodic events
recent = await athena.recall_episodic(
    time_range=(now - timedelta(days=1), now),
    event_type="ACTION"
)

# Filter for patterns
completed_tasks = [e for e in recent if "completed" in e.content]

# Learn from pattern
if len(completed_tasks) > 3:
    await athena.learn_procedure(
        name="auto_daily_consolidation",
        source_code=__code__,
        description="Daily consolidation of completed tasks"
    )

# Consolidate
patterns = await athena.consolidate("balanced")

# Save results
await athena.remember_semantic(
    content=f"Consolidated {len(patterns)} patterns from {len(completed_tasks)} tasks"
)

return ExecutionResult(
    success=True,
    patterns_found=len(patterns),
    tasks_completed=len(completed_tasks)
)
"""

# Execute code once
result = await athena.execute_code(code)

# Execution happens in sandbox (100% safe)
# No model involved in loop logic
# Real data stays in execution environment
# Model only sees final output
# ~1 model API call for entire workflow
```

---

## TESTING STRATEGY

### Unit Tests (Phase-specific)
- Phase 1: API exposure tests
- Phase 2: Procedure versioning + rollback tests
- Phase 3: Sandbox execution + resource limits tests
- Phase 4: API discovery tests
- Phase 5: Tokenization + privacy tests

### Integration Tests
```python
# test_full_workflow.py - Test complete flow

async def test_code_execution_with_memory_api():
    """Agent writes code that uses memory APIs end-to-end."""

    # Setup
    athena = MemoryAPI()
    sandbox = SandboxExecutor(athena)

    # Agent code
    code = """
    events = await athena.recall_episodic(
        time_range=(now - timedelta(hours=1), now)
    )
    await athena.remember_semantic(f"Found {len(events)} events")
    """

    # Execute
    result = await sandbox.execute(code)

    # Verify
    assert result.success
    assert "Found" in result.output
```

### Performance Tests
```python
# test_performance.py - Validate MCP paradigm benefits

async def test_token_efficiency_improvement():
    """Verify token savings from code execution vs tool calls."""

    # Tool call approach (many round-trips)
    tool_tokens = measure_tokens([
        call_tool("recall", ...),
        call_tool("filter", ...),
        call_tool("consolidate", ...),
        call_tool("remember", ...),
    ])

    # Code execution approach (one call)
    code_tokens = measure_tokens([
        execute_code("""
            data = await athena.recall()
            filtered = [d for d in data if ...]
            await athena.consolidate()
            await athena.remember()
        """)
    ])

    # Code execution should use 70%+ fewer tokens
    assert code_tokens < tool_tokens * 0.3
```

---

## ROLLOUT PLAN

### Week 1-2: Phase 1 (API Exposure)
- Merge: `src/athena/mcp/memory_api.py`
- Deprecate: Old tool abstraction (keep working, mark deprecated)
- Documentation: API reference guide

### Week 3-6: Phase 2 (Executable Procedures)
- Migrate: 101 existing procedures to code format
- Add: Git versioning system
- Test: LLM-based code extraction

### Week 7-9: Phase 3 (Sandbox Execution)
- Deploy: RestrictedPython sandbox
- Monitor: Resource usage, security events
- Iterate: Refine resource limits based on usage

### Week 10-12: Phase 4 (Progressive Discovery)
- Implement: Filesystem-based API discovery
- Launch: Procedure marketplace
- Educate: Agents on discovering APIs

### Week 13-16: Phase 5 (Privacy)
- Enable: Automatic tokenization
- Test: Untokenization, cross-layer transfer
- Audit: Compliance with data protection

### Post-Launch (Ongoing)
- Monitor: Agent code patterns
- Refine: Sandbox security rules
- Expand: Community procedure marketplace

---

## SUCCESS CRITERIA

### Functionality
- ✅ Agents can write Python code using memory APIs
- ✅ Code executes safely in sandbox
- ✅ Procedures versioned and rollback-able
- ✅ APIs discoverable at runtime
- ✅ Sensitive data tokenized before logging

### Performance
- ✅ Token usage reduced 50%+ vs tool calls
- ✅ Latency improved (fewer API round-trips)
- ✅ Consolidation 2-3x faster (parallel code execution)

### Security
- ✅ No dangerous code execution
- ✅ Resource limits enforced
- ✅ Audit trail maintained
- ✅ Sensitive data never reaches model

### Learning
- ✅ 101 procedures converted to executable code
- ✅ Auto-extracted procedures work end-to-end
- ✅ Community marketplace functional

---

## RISK MITIGATION

### Risk 1: Sandbox Bypass
- Mitigation: Use RestrictedPython + OS-level isolation
- Testing: Regular security audits
- Fallback: Revert to tool abstraction for unsafe code

### Risk 2: Performance Regression
- Mitigation: Comprehensive benchmarking
- Testing: Compare code execution vs tool calls
- Fallback: Keep both paths available, toggle via config

### Risk 3: Breaking Changes
- Mitigation: Deprecation period for old tools
- Testing: Backward compatibility tests
- Fallback: Maintain legacy tool abstraction

### Risk 4: Data Loss from Git Procedure Store
- Mitigation: Regular backups, git replica
- Testing: Rollback testing, disaster recovery
- Fallback: Keep PostgreSQL fallback

---

## CONCLUSION

This 16-week remediation blueprint achieves **100% alignment with the MCP code-execution paradigm** while preserving Athena's neuroscience-inspired memory architecture.

The result is an agent memory system that combines:
- **Efficiency**: Code-driven control flow (50%+ fewer tokens)
- **Learning**: 8-layer semantic structure (long-term knowledge)
- **Safety**: Sandboxed execution (no arbitrary system access)
- **Privacy**: Automatic tokenization (sensitive data protection)
- **Flexibility**: Composable memory APIs (code-based orchestration)

---

**Document Version**: 1.0
**Last Updated**: November 11, 2025
**Status**: Ready for Implementation
