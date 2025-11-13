# ATHENA MCP ALIGNMENT: COMPLETE TASK LIST

**Project**: Athena → 100% MCP Code-Execution Paradigm Alignment
**Duration**: 12-16 weeks (3-4 person-months)
**Status**: Ready for Implementation
**Last Updated**: November 11, 2025

---

## PHASE 1: MEMORY API EXPOSURE (Weeks 1-2)

### Goal
Replace tool abstraction with direct memory layer APIs. Agents call functions instead of tools.

---

### PHASE 1.1: Core Memory API Implementation (Week 1)

#### Task 1.1.1: Create MemoryAPI Base Class
- **File**: `src/athena/mcp/memory_api.py`
- **Scope**: 300 lines
- **Subtasks**:
  - [ ] Define base `MemoryAPI` class
  - [ ] Implement `recall_semantic(query, limit, min_confidence)` method
  - [ ] Implement `recall_episodic(time_range, event_type)` method
  - [ ] Implement `recall_procedural(context)` method
  - [ ] Add docstrings with examples
  - [ ] Type hints for all parameters
  - [ ] Error handling (ProcedureNotFound, QueryError)
- **Success Criteria**:
  - All methods callable from test code
  - Type hints complete
  - Docstrings include examples
  - Error handling matches existing patterns
- **Dependencies**: UnifiedMemoryManager (existing)
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 1.1.2: Implement Remember Methods
- **File**: `src/athena/mcp/memory_api.py` (extension)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Implement `remember_semantic(content, metadata)` method
  - [ ] Implement `remember_episodic(content, event_type, context)` method
  - [ ] Implement `remember_procedural(name, description)` method
  - [ ] Add deduplication checks (SHA256 hashing)
  - [ ] Return memory IDs for chaining
- **Success Criteria**:
  - Memories stored correctly
  - IDs returned for verification
  - Deduplication working
- **Dependencies**: EpisodicStore, SemanticStore, ProceduralStore
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 1.1.3: Implement Consolidation & Graph Methods
- **File**: `src/athena/mcp/memory_api.py` (extension)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Implement `consolidate(strategy, lookback_hours)` method
  - [ ] Implement graph methods: `create_entity()`, `search_entities()`, `link_entities()`
  - [ ] Implement query methods: `search_graph()`, `get_communities()`
  - [ ] Return structured results (not just JSON strings)
  - [ ] Add filtering/ranking for results
- **Success Criteria**:
  - Consolidation runs and returns patterns
  - Graph operations work correctly
  - Results are ranked/filtered
- **Dependencies**: ConsolidationSystem, KnowledgeGraphStore
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 1.1.4: Create SandboxConfig Model
- **File**: `src/athena/sandbox/config.py` (new)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Define `SandboxConfig` dataclass with all options
  - [ ] Add defaults (timeout, memory limit, API call limits)
  - [ ] Document all configuration options
  - [ ] Add validation (ensure sensible ranges)
  - [ ] Add `to_json()` method for serialization
- **Success Criteria**:
  - Config can be instantiated with defaults
  - All fields validated
  - Can be serialized to JSON
- **Owner**: @[assign]
- **Est. Time**: 2 hours

---

### PHASE 1.2: MCP Server Integration (Week 1-2)

#### Task 1.2.1: Update handlers.py with Code Execution Tools
- **File**: `src/athena/mcp/handlers.py` (modified)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Add `execute_memory_code()` tool (placeholder for Phase 3)
  - [ ] Add `discover_apis()` tool (returns available APIs)
  - [ ] Add `get_api_docs(api_name)` tool (returns docstrings)
  - [ ] Register tools with server
  - [ ] Add error handling for tool execution
  - [ ] Add rate limiting checks
- **Success Criteria**:
  - Tools registered in MCP server
  - Agents can call discover_apis
  - API docs accessible
- **Dependencies**: MemoryAPI (from Task 1.1.1)
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 1.2.2: Create APIRegistry & Discovery System
- **File**: `src/athena/mcp/api_registry.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Define `APIRegistry` class for managing available APIs
  - [ ] Implement `register_api()` method
  - [ ] Implement `list_apis()` with filtering
  - [ ] Implement `get_api_docs()` with detail levels
  - [ ] Add caching for performance
  - [ ] Add search functionality (find APIs by keyword)
- **Success Criteria**:
  - Registry tracks all memory APIs
  - Docs discoverable by agents
  - Search working
  - Caching improving performance
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 1.2.3: Create API Documentation Generator
- **File**: `src/athena/mcp/api_docs.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Auto-generate markdown docs from docstrings
  - [ ] Extract parameter information (type, default, description)
  - [ ] Extract return type information
  - [ ] Pull examples from docstrings
  - [ ] Generate HTML + JSON versions
  - [ ] Create doc index (table of contents)
- **Success Criteria**:
  - Docs auto-generated from code
  - All methods documented
  - Examples present
  - Docs match source code
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 1.3: Backward Compatibility & Migration (Week 2)

#### Task 1.3.1: Add Compatibility Layer
- **File**: `src/athena/mcp/compatibility.py` (new)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Create adapter functions mapping old tool calls to new APIs
  - [ ] Ensure old handlers still work
  - [ ] Add deprecation warnings for old tools
  - [ ] Log migration statistics
- **Success Criteria**:
  - Old tools still callable (with warnings)
  - Migration tracking working
  - No breaking changes
- **Owner**: @[assign]
- **Est. Time**: 2 hours

#### Task 1.3.2: Update Documentation
- **File**: `docs/API_REFERENCE.md` (updated)
- **Scope**: 50 lines
- **Subtasks**:
  - [ ] Document new MemoryAPI methods
  - [ ] Add usage examples
  - [ ] Migration guide from old tools
  - [ ] Best practices section
  - [ ] Update README with API reference link
- **Success Criteria**:
  - Documentation complete and clear
  - Examples working
  - Migration path documented
- **Owner**: @[assign]
- **Est. Time**: 2 hours

---

### PHASE 1.4: Testing (Week 2)

#### Task 1.4.1: Unit Tests for MemoryAPI
- **File**: `tests/mcp/test_memory_api.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Test `recall_semantic()` with various queries
  - [ ] Test `recall_episodic()` with time ranges
  - [ ] Test `remember_semantic()` and `remember_episodic()`
  - [ ] Test error cases (empty queries, invalid IDs)
  - [ ] Test result ranking/filtering
  - [ ] Test consolidation triggering
- **Success Criteria**:
  - All core API methods tested
  - Edge cases covered
  - >90% line coverage
  - All tests passing
- **Dependencies**: test fixtures for database
- **Owner**: @[assign]
- **Est. Time**: 5 hours

#### Task 1.4.2: Integration Tests
- **File**: `tests/mcp/test_api_integration.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Test end-to-end recall → consolidate → remember workflow
  - [ ] Test cross-layer integration
  - [ ] Test API discovery and documentation
  - [ ] Test deprecated tool compatibility
  - [ ] Test rate limiting
- **Success Criteria**:
  - All integration scenarios tested
  - No regressions from old system
  - Performance acceptable (<100ms per operation)
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 1.4.3: Performance Benchmarks
- **File**: `tests/performance/test_api_latency.py` (new)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Benchmark `recall_semantic()` latency (<100ms)
  - [ ] Benchmark `remember()` latency (<50ms)
  - [ ] Benchmark consolidation (<5s for 1000 events)
  - [ ] Compare vs old tool abstraction
  - [ ] Document latency improvements
- **Success Criteria**:
  - All operations meet latency targets
  - Latency improvements documented
  - Benchmarks reproducible
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 1 Summary

| Deliverable | File | Lines | Owner | Status |
|-------------|------|-------|-------|--------|
| Memory API | `src/athena/mcp/memory_api.py` | 400 | @[assign] | - |
| Sandbox Config | `src/athena/sandbox/config.py` | 100 | @[assign] | - |
| MCP Integration | `src/athena/mcp/handlers.py` | 150 | @[assign] | - |
| API Registry | `src/athena/mcp/api_registry.py` | 200 | @[assign] | - |
| Documentation | `docs/API_REFERENCE.md` | 50 | @[assign] | - |
| Tests | `tests/mcp/test_*.py` | 550 | @[assign] | - |
| **Total** | | **1,450** | | **Week 1-2** |

---

## PHASE 2: EXECUTABLE PROCEDURES (Weeks 3-6)

### Goal
Convert procedures from metadata to executable Python code with versioning.

---

### PHASE 2.1: Model & Storage Updates (Week 3)

#### Task 2.1.1: Update ExecutableProcedure Model
- **File**: `src/athena/procedural/models.py` (modified)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Add `source_code: str` field (replace template)
  - [ ] Add `signature: str` field for type hints
  - [ ] Add `version: int` field for versioning
  - [ ] Add `git_hash: str` field for git tracking
  - [ ] Add `previous_versions: List[Dict]` for rollback
  - [ ] Add `execution_log: List[ExecutionRecord]` for history
  - [ ] Add `async execute(**kwargs)` method
  - [ ] Add `rollback_to_version(version)` method
  - [ ] Add validation (syntax checking)
- **Success Criteria**:
  - Model instantiates correctly
  - Validation working
  - All fields present
  - Type hints complete
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 2.1.2: Create Git-Backed Procedure Store
- **File**: `src/athena/procedural/git_store.py` (new)
- **Scope**: 300 lines
- **Subtasks**:
  - [ ] Initialize git repo in `~/.athena/procedures/`
  - [ ] Implement `save_procedure()` (writes to git)
  - [ ] Implement `get_procedure()` (reads from git)
  - [ ] Implement `list_procedures()` with filtering
  - [ ] Implement `rollback_to_version()` (restore git commit)
  - [ ] Implement tagging system (`procedure-name-v1`, etc)
  - [ ] Add commit message generation
  - [ ] Add error handling (git errors, missing procedures)
- **Success Criteria**:
  - Procedures stored in git
  - Version control working
  - Rollback functional
  - All procedures queryable
- **Dependencies**: PyGit2
- **Owner**: @[assign]
- **Est. Time**: 5 hours

#### Task 2.1.3: Migrate Existing 101 Procedures
- **File**: `scripts/migrate_procedures.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Load existing 101 procedures from PostgreSQL
  - [ ] Convert metadata to executable code (manual + LLM)
  - [ ] Validate generated code
  - [ ] Store in git repository
  - [ ] Update database with git_hash references
  - [ ] Generate migration report
  - [ ] Rollback mechanism (restore from backup)
- **Success Criteria**:
  - All 101 procedures migrated
  - Generated code syntactically valid
  - Git repo contains all versions
  - Rollback tested
  - Migration report generated
- **Owner**: @[assign]
- **Est. Time**: 8 hours

---

### PHASE 2.2: Procedure Execution & Learning (Week 4-5)

#### Task 2.2.1: Create Code Extraction System
- **File**: `src/athena/procedural/code_extractor.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Build extraction prompt template (from events → code)
  - [ ] Integrate with LLM client (Ollama or Anthropic)
  - [ ] Implement code validation (syntax, no dangerous patterns)
  - [ ] Implement code testing (execute with test data)
  - [ ] Add confidence scoring
  - [ ] Handle extraction failures gracefully
  - [ ] Log extraction metrics
- **Success Criteria**:
  - LLM generates valid Python code from events
  - Generated code is syntactically valid
  - Confidence scoring working
  - Extraction failures handled
- **Dependencies**: LLM client, event temporal patterns
- **Owner**: @[assign]
- **Est. Time**: 6 hours

#### Task 2.2.2: Update Procedure Execution Engine
- **File**: `src/athena/procedural/executor.py` (modified)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Implement `execute(procedure_name, **kwargs)` method
  - [ ] Load procedure from git store
  - [ ] Validate inputs before execution
  - [ ] Execute in sandbox (Phase 3 placeholder)
  - [ ] Capture execution results (output, logs, errors)
  - [ ] Record execution metrics (duration, success_rate)
  - [ ] Handle execution failures
  - [ ] Update success_rate based on results
- **Success Criteria**:
  - Procedures execute successfully
  - Results captured correctly
  - Metrics updated
  - Failures handled gracefully
- **Dependencies**: SRTExecutor (Phase 3)
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 2.2.3: Implement Procedure Learning from Events
- **File**: `src/athena/procedural/pattern_learning.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Detect repeated patterns in episodic events
  - [ ] Group similar sequences
  - [ ] Extract procedure from patterns
  - [ ] Generate code via CodeExtractor
  - [ ] Store new procedure in git
  - [ ] Link to source events
  - [ ] Update learning metrics
- **Success Criteria**:
  - Patterns detected correctly
  - New procedures created automatically
  - Learning metrics tracked
  - Procedures usable
- **Owner**: @[assign]
- **Est. Time**: 5 hours

---

### PHASE 2.3: API Exposure & Integration (Week 5-6)

#### Task 2.3.1: Add Procedure Methods to MemoryAPI
- **File**: `src/athena/mcp/memory_api.py` (extended)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Add `execute_procedure(name, **kwargs)` method
  - [ ] Add `learn_procedure(name, source_code, description)` method
  - [ ] Add `list_procedures(category=None)` method
  - [ ] Add `get_procedure_docs(name)` method
  - [ ] Add `rollback_procedure(name, to_version)` method
  - [ ] Add error handling for missing procedures
- **Success Criteria**:
  - All procedure operations callable
  - Error handling working
  - Docs accessible
- **Owner**: @[assign]
- **Est. Time**: 2 hours

#### Task 2.3.2: MCP Tool Registration for Procedures
- **File**: `src/athena/mcp/handlers.py` (extended)
- **Scope**: 50 lines
- **Subtasks**:
  - [ ] Register `execute_procedure` tool
  - [ ] Register `learn_procedure` tool
  - [ ] Register `list_procedures` tool
  - [ ] Add operation routing
  - [ ] Add parameter validation
- **Success Criteria**:
  - Tools registered
  - Agents can invoke procedures
  - Parameters validated
- **Owner**: @[assign]
- **Est. Time**: 1.5 hours

---

### PHASE 2.4: Testing & Validation (Week 6)

#### Task 2.4.1: Unit Tests for Executable Procedures
- **File**: `tests/procedural/test_executable_procedures.py` (new)
- **Scope**: 300 lines
- **Subtasks**:
  - [ ] Test procedure execution with various inputs
  - [ ] Test successful execution
  - [ ] Test failed execution handling
  - [ ] Test procedure learning from patterns
  - [ ] Test code extraction from events
  - [ ] Test git versioning
  - [ ] Test rollback functionality
  - [ ] Test execution metrics tracking
- **Success Criteria**:
  - All procedure operations tested
  - Edge cases covered
  - >90% coverage
  - All tests passing
- **Owner**: @[assign]
- **Est. Time**: 6 hours

#### Task 2.4.2: Code Quality & Security Validation
- **File**: `tests/procedural/test_code_validation.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Test syntax validation (catches bad code)
  - [ ] Test dangerous pattern detection
  - [ ] Test generated code quality
  - [ ] Test code execution in sandbox
  - [ ] Test error handling
  - [ ] Performance testing (execution speed)
- **Success Criteria**:
  - Invalid code rejected
  - Dangerous patterns blocked
  - Generated code quality high
  - Execution safe
- **Owner**: @[assign]
- **Est. Time**: 4 hours

---

### PHASE 2 Summary

| Deliverable | File | Lines | Owner | Status |
|-------------|------|-------|-------|--------|
| Executable Procedure Model | `src/athena/procedural/models.py` | 150 | @[assign] | - |
| Git Store | `src/athena/procedural/git_store.py` | 300 | @[assign] | - |
| Migration Script | `scripts/migrate_procedures.py` | 200 | @[assign] | - |
| Code Extraction | `src/athena/procedural/code_extractor.py` | 250 | @[assign] | - |
| Procedure Executor | `src/athena/procedural/executor.py` | 150 | @[assign] | - |
| Pattern Learning | `src/athena/procedural/pattern_learning.py` | 200 | @[assign] | - |
| API Methods | `src/athena/mcp/memory_api.py` | 100 | @[assign] | - |
| Tests | `tests/procedural/test_*.py` | 450 | @[assign] | - |
| **Total** | | **1,800** | | **Week 3-6** |

---

## PHASE 3: SANDBOXED CODE EXECUTION (Weeks 7-9)

### Goal
Implement OS-level sandboxing using Anthropic's Sandbox Runtime (srt).

---

### PHASE 3.1: SRT Integration & Setup (Week 7)

#### Task 3.1.1: Create SRTExecutor Class
- **File**: `src/athena/sandbox/srt_executor.py` (new)
- **Scope**: 400 lines
- **Subtasks**:
  - [ ] Check srt installation (`which srt`)
  - [ ] Generate srt configuration from SandboxConfig
  - [ ] Write code to temporary file
  - [ ] Write config to temporary file
  - [ ] Execute command with srt
  - [ ] Capture stdout/stderr
  - [ ] Handle timeouts
  - [ ] Cleanup temporary files
  - [ ] Generate ExecutionResult
  - [ ] Add logging for debugging
- **Success Criteria**:
  - srt is called correctly
  - Code executes with restrictions
  - Timeouts handled
  - Results captured
  - Cleanup working
- **Dependencies**: srt installed (cargo install sandbox-runtime)
- **Owner**: @[assign]
- **Est. Time**: 6 hours

#### Task 3.1.2: Create SRT Configuration Manager
- **File**: `src/athena/sandbox/srt_config.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Load default config template
  - [ ] Implement config merging (user + defaults)
  - [ ] Validate configuration
  - [ ] Generate JSON for srt
  - [ ] Support multiple presets (conservative, balanced, permissive)
  - [ ] Save/load config from files
  - [ ] Add configuration validation
- **Success Criteria**:
  - Configurations generated correctly
  - Validation working
  - Presets available
  - JSON output correct
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 3.1.3: Setup SRT Installation Documentation
- **File**: `docs/SANDBOX_SETUP.md` (new)
- **Scope**: 50 lines
- **Subtasks**:
  - [ ] Installation instructions (cargo, brew, etc)
  - [ ] Verify installation script
  - [ ] Configuration template
  - [ ] Troubleshooting guide
  - [ ] Platform-specific notes
  - [ ] Performance considerations
- **Success Criteria**:
  - Clear installation instructions
  - Troubleshooting guide helpful
  - All platforms covered
  - Setup verification script works
- **Owner**: @[assign]
- **Est. Time**: 2 hours

---

### PHASE 3.2: Agent Code Execution Pipeline (Week 8)

#### Task 3.2.1: Implement Code Execution Entry Point
- **File**: `src/athena/mcp/memory_api.py` (extended)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Add `execute_code(code, language, timeout)` method
  - [ ] Add `execute_code_with_custom_config()` method
  - [ ] Add input validation (code syntax check)
  - [ ] Add timeout validation
  - [ ] Add language detection
  - [ ] Error handling and reporting
- **Success Criteria**:
  - Code execution methods callable
  - Inputs validated
  - Language detection working
  - Error messages clear
- **Owner**: @[assign]
- **Est. Time**: 2 hours

#### Task 3.2.2: Create Code Validation System
- **File**: `src/athena/sandbox/code_validator.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Validate Python syntax (ast.parse)
  - [ ] Detect dangerous patterns (subprocess, file ops, network)
  - [ ] Validate JavaScript syntax (can use simple regex)
  - [ ] Check code length limits
  - [ ] Check for infinite loops (heuristic detection)
  - [ ] Generate helpful error messages
- **Success Criteria**:
  - Syntax validation working
  - Dangerous patterns detected
  - Error messages helpful
  - False positives minimized
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 3.2.3: Agent Code Examples & Documentation
- **File**: `docs/AGENT_CODE_EXAMPLES.md` (new)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Example 1: Simple semantic search
  - [ ] Example 2: Episodic query + consolidation
  - [ ] Example 3: Procedure execution
  - [ ] Example 4: Learning new procedure
  - [ ] Example 5: Cross-layer workflow
  - [ ] Example 6: Error handling
  - [ ] Best practices section
  - [ ] Common patterns section
- **Success Criteria**:
  - All examples executable
  - Best practices clear
  - Common patterns documented
  - Agents can learn from examples
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 3.3: Security & Monitoring (Week 8-9)

#### Task 3.3.1: Create Violation Monitoring System
- **File**: `src/athena/sandbox/violation_monitor.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Parse srt violation logs
  - [ ] Classify violations (filesystem, network, process)
  - [ ] Alert on suspicious activity (attempted exfiltration)
  - [ ] Store violation history
  - [ ] Generate violation reports
  - [ ] Integration with logging system
- **Success Criteria**:
  - Violations detected and logged
  - Alerts triggered for serious violations
  - Reports generated
  - Integration working
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 3.3.2: Create Execution Context & Logging
- **File**: `src/athena/sandbox/execution_context.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Define ExecutionContext (who, when, what, how)
  - [ ] Implement audit logging for all executions
  - [ ] Store execution history with metadata
  - [ ] Implement query interface (find executions)
  - [ ] Implement retention policy
  - [ ] Add compliance reporting
- **Success Criteria**:
  - All executions logged
  - History queryable
  - Audit trail complete
  - Compliance reports generated
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 3.3.3: Security Test Suite
- **File**: `tests/sandbox/test_srt_security.py` (new)
- **Scope**: 300 lines
- **Subtasks**:
  - [ ] Test SSH key exfiltration is blocked
  - [ ] Test network exfiltration is blocked
  - [ ] Test subprocess restrictions
  - [ ] Test filesystem read restrictions
  - [ ] Test filesystem write restrictions
  - [ ] Test process escape attempts
  - [ ] Test privilege escalation is blocked
  - [ ] Test resource limits (CPU, memory, timeout)
- **Success Criteria**:
  - All attacks blocked
  - Sandbox escape impossible
  - Resource limits enforced
  - Violation detection working
- **Owner**: Security Audit Team
- **Est. Time**: 8 hours

---

### PHASE 3.4: Performance & Integration (Week 9)

#### Task 3.4.1: Performance Benchmarking
- **File**: `tests/performance/test_sandbox_overhead.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Measure srt startup overhead
  - [ ] Measure code execution latency
  - [ ] Measure I/O performance (within sandbox)
  - [ ] Measure network proxy latency
  - [ ] Generate performance report
  - [ ] Compare vs no sandboxing (unrestricted)
- **Success Criteria**:
  - Overhead <50ms per execution
  - I/O performance acceptable
  - Network proxy latency <10ms
  - Performance acceptable for agent use
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 3.4.2: MCP Tool Registration
- **File**: `src/athena/mcp/handlers.py` (extended)
- **Scope**: 50 lines
- **Subtasks**:
  - [ ] Register `execute_code` tool
  - [ ] Register `execute_code_with_custom_config` tool
  - [ ] Register `get_sandbox_config` tool
  - [ ] Register `list_sandbox_presets` tool
  - [ ] Add operation routing
- **Success Criteria**:
  - All tools registered
  - Agents can execute code
  - Configuration available
  - Operation routing working
- **Owner**: @[assign]
- **Est. Time**: 1.5 hours

#### Task 3.4.3: Integration Testing
- **File**: `tests/sandbox/test_srt_integration.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Test end-to-end code execution workflow
  - [ ] Test execution with various languages (Python, JavaScript)
  - [ ] Test file I/O within sandbox
  - [ ] Test network requests with allowed domains
  - [ ] Test blocked network requests
  - [ ] Test procedure execution in sandbox
  - [ ] Test error handling and reporting
- **Success Criteria**:
  - All languages work
  - I/O operations work within bounds
  - Network restrictions enforced
  - Integration seamless
- **Owner**: @[assign]
- **Est. Time**: 5 hours

---

### PHASE 3 Summary

| Deliverable | File | Lines | Owner | Status |
|-------------|------|-------|-------|--------|
| SRT Executor | `src/athena/sandbox/srt_executor.py` | 400 | @[assign] | - |
| Config Manager | `src/athena/sandbox/srt_config.py` | 200 | @[assign] | - |
| Code Validator | `src/athena/sandbox/code_validator.py` | 150 | @[assign] | - |
| Violation Monitor | `src/athena/sandbox/violation_monitor.py` | 200 | @[assign] | - |
| Execution Context | `src/athena/sandbox/execution_context.py` | 150 | @[assign] | - |
| Documentation | `docs/SANDBOX_SETUP.md` | 50 | @[assign] | - |
| Tests | `tests/sandbox/test_*.py` | 600 | @[assign] | - |
| **Total** | | **1,750** | | **Week 7-9** |

---

## PHASE 4: PROGRESSIVE DISCOVERY & MARKETPLACE (Weeks 10-12)

### Goal
Implement filesystem-based API discovery and procedure marketplace.

---

### PHASE 4.1: API Discovery System (Week 10)

#### Task 4.1.1: Create APIDiscovery Class
- **File**: `src/athena/api/discovery.py` (new)
- **Scope**: 300 lines
- **Subtasks**:
  - [ ] Scan filesystem for API modules
  - [ ] Extract function signatures via introspection
  - [ ] Extract docstrings and examples
  - [ ] Index APIs by category and tags
  - [ ] Implement search functionality
  - [ ] Implement filtering (by context, capability)
  - [ ] Add caching for performance
  - [ ] Generate API index
- **Success Criteria**:
  - All APIs discovered
  - Discovery is fast (<100ms)
  - Search working
  - Caching effective
- **Owner**: @[assign]
- **Est. Time**: 5 hours

#### Task 4.1.2: Create APISpec Models
- **File**: `src/athena/api/models.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Define `APIParameter` dataclass
  - [ ] Define `APISpec` dataclass
  - [ ] Implement `to_markdown()` method
  - [ ] Implement `to_json()` method
  - [ ] Add serialization support
  - [ ] Add comparison operators
- **Success Criteria**:
  - Specs serialize correctly
  - Documentation formatting works
  - Comparison operators functional
- **Owner**: @[assign]
- **Est. Time**: 2 hours

#### Task 4.1.3: Implement API Discovery Tools
- **File**: `src/athena/mcp/handlers.py` (extended)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Register `discover_apis()` tool
  - [ ] Register `get_api_docs()` tool
  - [ ] Register `find_apis_for_task()` tool (semantic search)
  - [ ] Add result formatting
  - [ ] Add pagination for large result sets
- **Success Criteria**:
  - Discovery tools work
  - Semantic search functional
  - Pagination working
  - Results well-formatted
- **Owner**: @[assign]
- **Est. Time**: 2 hours

---

### PHASE 4.2: Procedure Marketplace (Weeks 10-11)

#### Task 4.2.1: Create Marketplace Backend
- **File**: `src/athena/api/marketplace.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Define Marketplace API interface
  - [ ] Implement `list_procedures()` with filtering
  - [ ] Implement `get_procedure()` with details
  - [ ] Implement `install_procedure()` (fetch and store)
  - [ ] Implement `publish_procedure()` (share locally)
  - [ ] Implement rating/feedback system
  - [ ] Add metadata tracking (downloads, ratings)
- **Success Criteria**:
  - Marketplace APIs functional
  - Installation working
  - Ratings system operational
  - Metadata tracked
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 4.2.2: Create Marketplace Storage
- **File**: `src/athena/api/marketplace_store.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Database schema for marketplace metadata
  - [ ] Store procedure details (name, version, author, ratings)
  - [ ] Track installation history
  - [ ] Implement search over marketplace
  - [ ] Cache popular procedures
- **Success Criteria**:
  - Metadata stored correctly
  - Queries fast
  - Caching working
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 4.2.3: Marketplace MCP Tools
- **File**: `src/athena/mcp/handlers.py` (extended)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Register `list_community_procedures()` tool
  - [ ] Register `install_community_procedure()` tool
  - [ ] Register `publish_procedure()` tool
  - [ ] Register `rate_procedure()` tool
  - [ ] Add filtering and search
- **Success Criteria**:
  - All marketplace tools available
  - Agents can discover and install procedures
  - Rating system working
- **Owner**: @[assign]
- **Est. Time**: 2 hours

---

### PHASE 4.3: Semantic Search & Recommendations (Week 11-12)

#### Task 4.3.1: Create Semantic API Search
- **File**: `src/athena/api/semantic_search.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Embed API descriptions
  - [ ] Embed task descriptions
  - [ ] Implement similarity scoring
  - [ ] Find relevant APIs for tasks
  - [ ] Rank results by relevance
  - [ ] Add caching for common queries
- **Success Criteria**:
  - Semantic search working
  - Relevant APIs returned
  - Performance acceptable (<200ms)
  - Caching effective
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 4.3.2: Create Recommendation Engine
- **File**: `src/athena/api/recommendations.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Analyze agent execution patterns
  - [ ] Recommend APIs based on history
  - [ ] Recommend procedures based on task
  - [ ] Learn from agent feedback
  - [ ] Track recommendation accuracy
- **Success Criteria**:
  - Recommendations useful
  - Learning from feedback
  - Accuracy tracked
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 4.3.3: Testing & Optimization
- **File**: `tests/api/test_discovery.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Test API discovery accuracy
  - [ ] Test semantic search relevance
  - [ ] Test marketplace functionality
  - [ ] Test recommendation accuracy
  - [ ] Performance testing
  - [ ] Integration tests
- **Success Criteria**:
  - All discovery features tested
  - Accuracy acceptable
  - Performance meets targets
  - Integration working
- **Owner**: @[assign]
- **Est. Time**: 4 hours

---

### PHASE 4 Summary

| Deliverable | File | Lines | Owner | Status |
|-------------|------|-------|-------|--------|
| API Discovery | `src/athena/api/discovery.py` | 300 | @[assign] | - |
| API Specs | `src/athena/api/models.py` | 150 | @[assign] | - |
| Marketplace | `src/athena/api/marketplace.py` | 250 | @[assign] | - |
| Marketplace Store | `src/athena/api/marketplace_store.py` | 200 | @[assign] | - |
| Semantic Search | `src/athena/api/semantic_search.py` | 200 | @[assign] | - |
| Recommendations | `src/athena/api/recommendations.py` | 150 | @[assign] | - |
| Tests | `tests/api/test_*.py` | 200 | @[assign] | - |
| **Total** | | **1,450** | | **Week 10-12** |

---

## PHASE 5: PRIVACY-PRESERVING DATA HANDLING (Weeks 13-16)

### Goal
Implement automatic tokenization and encryption of sensitive data.

---

### PHASE 5.1: Tokenization System (Weeks 13-14)

#### Task 5.1.1: Create Data Tokenizer
- **File**: `src/athena/privacy/tokenizer.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Define sensitive pattern regexes (AWS keys, emails, etc)
  - [ ] Implement pattern matching
  - [ ] Generate deterministic tokens
  - [ ] Track token → value mapping
  - [ ] Implement untokenization
  - [ ] Add custom pattern support
  - [ ] Performance optimization
- **Success Criteria**:
  - All sensitive patterns detected
  - Tokenization/untokenization working
  - Performance acceptable (<10ms per event)
  - Custom patterns supported
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 5.1.2: Create Secure Token Storage
- **File**: `src/athena/privacy/token_storage.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Implement encrypted token storage (Fernet)
  - [ ] Store in separate secure database
  - [ ] Implement token → value lookup
  - [ ] Add access control (who can untokenize)
  - [ ] Implement retention policies
  - [ ] Add audit logging for untokenization
  - [ ] Performance optimization
- **Success Criteria**:
  - Tokens stored encrypted
  - Lookup fast (<5ms)
  - Access control working
  - Audit logging complete
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 5.1.3: Integrate Tokenization into Episodic Store
- **File**: `src/athena/episodic/store.py` (modified)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Auto-tokenize on event creation
  - [ ] Store tokenized content in database
  - [ ] Store tokens in secure storage
  - [ ] Implement `get_event(untokenize=True/False)`
  - [ ] Add migration for existing events
  - [ ] Performance testing
- **Success Criteria**:
  - Events stored tokenized
  - Untokenization working when authorized
  - Migration complete
  - No performance regression
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 5.2: Encryption at Rest (Week 14-15)

#### Task 5.2.1: Create Encryption Manager
- **File**: `src/athena/privacy/encryption.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Implement AES-256 encryption (using cryptography lib)
  - [ ] Key management (generate, store, rotate)
  - [ ] Implement encryption/decryption
  - [ ] Add field-level encryption support
  - [ ] Implement key rotation
  - [ ] Performance optimization
- **Success Criteria**:
  - Encryption working correctly
  - Keys managed securely
  - Rotation working
  - Performance acceptable (<5ms per operation)
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 5.2.2: Add Encryption to Sensitive Fields
- **File**: `src/athena/core/database.py` (modified)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Identify sensitive fields (content, context, learned)
  - [ ] Encrypt on write
  - [ ] Decrypt on read
  - [ ] Add encryption metadata
  - [ ] Implement selective decryption
  - [ ] Migrate existing data
- **Success Criteria**:
  - Sensitive fields encrypted
  - Transparent encryption/decryption
  - Migration complete
  - Query performance acceptable
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task 5.2.3: Create Key Management System
- **File**: `src/athena/privacy/key_manager.py` (new)
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] Generate master key
  - [ ] Store key securely (environment variable or vault)
  - [ ] Implement key rotation schedule
  - [ ] Support multiple keys (versioning)
  - [ ] Add key backup/recovery
  - [ ] Compliance documentation
- **Success Criteria**:
  - Keys managed securely
  - Rotation working
  - Backups functional
  - Compliance documented
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 5.3: Privacy-Preserving Data Transfer (Week 15-16)

#### Task 5.3.1: Create Privacy Bridge
- **File**: `src/athena/integration/privacy_bridge.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Implement `transfer_to_semantic()` with tokenization
  - [ ] Implement `transfer_to_graph()` with tokenization
  - [ ] Implement `transfer_to_procedural()` with tokenization
  - [ ] Ensure real data flows to services
  - [ ] Ensure tokenized data logged
  - [ ] Add compliance logging
- **Success Criteria**:
  - Cross-layer transfers working
  - Real data flows between services
  - Tokenized data in logs
  - Compliance logging complete
- **Owner**: @[assign]
- **Est. Time**: 3 hours

#### Task 5.3.2: Add Privacy Methods to MemoryAPI
- **File**: `src/athena/mcp/memory_api.py` (extended)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Add `remember_with_privacy()` method
  - [ ] Add `get_event_untokenized()` method (with access control)
  - [ ] Add `enable_auto_tokenization()` method
  - [ ] Add `check_tokenization_status()` method
  - [ ] Add privacy audit logging
- **Success Criteria**:
  - Privacy methods available
  - Auto-tokenization working
  - Access control enforced
  - Audit logging complete
- **Owner**: @[assign]
- **Est. Time**: 2 hours

#### Task 5.3.3: Testing & Compliance
- **File**: `tests/privacy/test_tokenization.py` (new)
- **Scope**: 250 lines
- **Subtasks**:
  - [ ] Test sensitive data detection
  - [ ] Test tokenization/untokenization
  - [ ] Test encryption/decryption
  - [ ] Test cross-layer privacy
  - [ ] Test access control
  - [ ] Test compliance logging
  - [ ] Audit logging verification
- **Success Criteria**:
  - All privacy features tested
  - Sensitive data never logged unencrypted
  - Access control enforced
  - Audit trail complete
  - Compliance tests passing
- **Owner**: @[assign]
- **Est. Time**: 5 hours

#### Task 5.3.4: Privacy Documentation
- **File**: `docs/PRIVACY_GUIDE.md` (new)
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Privacy architecture overview
  - [ ] Data protection mechanisms
  - [ ] Tokenization explanation
  - [ ] Encryption overview
  - [ ] Access control policies
  - [ ] Audit logging information
  - [ ] Compliance checklist
- **Success Criteria**:
  - Privacy architecture documented
  - Mechanisms explained
  - Compliance checklist useful
  - Users understand data protection
- **Owner**: @[assign]
- **Est. Time**: 3 hours

---

### PHASE 5 Summary

| Deliverable | File | Lines | Owner | Status |
|-------------|------|-------|-------|--------|
| Tokenizer | `src/athena/privacy/tokenizer.py` | 250 | @[assign] | - |
| Token Storage | `src/athena/privacy/token_storage.py` | 200 | @[assign] | - |
| Encryption Manager | `src/athena/privacy/encryption.py` | 200 | @[assign] | - |
| Key Manager | `src/athena/privacy/key_manager.py` | 150 | @[assign] | - |
| Privacy Bridge | `src/athena/integration/privacy_bridge.py` | 200 | @[assign] | - |
| Documentation | `docs/PRIVACY_GUIDE.md` | 100 | @[assign] | - |
| Tests | `tests/privacy/test_*.py` | 250 | @[assign] | - |
| **Total** | | **1,350** | | **Week 13-16** |

---

## CROSS-PHASE TASKS

### Documentation & Training (Ongoing)

#### Task: Create Implementation Guide
- **File**: `docs/IMPLEMENTATION_GUIDE.md`
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Overview of 5 phases
  - [ ] Phase-by-phase details
  - [ ] Integration points
  - [ ] Testing strategy
  - [ ] Rollout plan
- **Owner**: @[assign]
- **Est. Time**: 4 hours

#### Task: Create Agent Developer Guide
- **File**: `docs/AGENT_DEVELOPER_GUIDE.md`
- **Scope**: 150 lines
- **Subtasks**:
  - [ ] How to write agent code
  - [ ] API reference (all methods)
  - [ ] Code examples
  - [ ] Error handling
  - [ ] Best practices
  - [ ] Troubleshooting
- **Owner**: @[assign]
- **Est. Time**: 6 hours

#### Task: Create Migration Guide (for existing users)
- **File**: `docs/MIGRATION_GUIDE.md`
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Old API deprecation timeline
  - [ ] Migration examples
  - [ ] Compatibility layer
  - [ ] FAQs
  - [ ] Support contact
- **Owner**: @[assign]
- **Est. Time**: 4 hours

### System Integration & Deployment

#### Task: Update Manager.py with New APIs
- **File**: `src/athena/manager.py` (modified)
- **Scope**: 50 lines
- **Subtasks**:
  - [ ] Register MemoryAPI
  - [ ] Initialize SRTExecutor
  - [ ] Setup API discovery
  - [ ] Initialize marketplace
- **Owner**: @[assign]
- **Est. Time**: 1.5 hours

#### Task: Create Integration Tests
- **File**: `tests/integration/test_full_workflow.py` (new)
- **Scope**: 200 lines
- **Subtasks**:
  - [ ] Test full agent code execution workflow
  - [ ] Test procedure learning end-to-end
  - [ ] Test privacy enforcement
  - [ ] Test marketplace functionality
  - [ ] Test error handling
- **Owner**: @[assign]
- **Est. Time**: 5 hours

### Quality & Deployment

#### Task: Security Audit (External)
- **Scope**: 40 hours
- **Subtasks**:
  - [ ] SRT sandbox escape testing
  - [ ] Code execution vulnerability assessment
  - [ ] Privacy implementation review
  - [ ] Access control audit
  - [ ] Generate security report
- **Owner**: Security Team
- **Est. Time**: 40 hours

#### Task: Performance Testing & Optimization
- **Scope**: 30 hours
- **Subtasks**:
  - [ ] Latency benchmarking
  - [ ] Throughput testing
  - [ ] Resource usage optimization
  - [ ] Caching strategy optimization
  - [ ] Generate performance report
- **Owner**: Performance Team
- **Est. Time**: 30 hours

#### Task: Production Deployment Plan
- **File**: `docs/DEPLOYMENT_PLAN.md`
- **Scope**: 100 lines
- **Subtasks**:
  - [ ] Rollout schedule
  - [ ] Rollback procedures
  - [ ] Monitoring setup
  - [ ] Incident response plan
  - [ ] Communication plan
- **Owner**: DevOps/Release Manager
- **Est. Time**: 5 hours

---

## SUMMARY BY PHASE

| Phase | Duration | LOC | Total Cost | Complexity |
|-------|----------|-----|-----------|-----------|
| **1: API Exposure** | Weeks 1-2 | 1,450 | 50-60 hrs | Medium |
| **2: Executable Procedures** | Weeks 3-6 | 1,800 | 60-70 hrs | High |
| **3: Sandbox Execution** | Weeks 7-9 | 1,750 | 55-65 hrs | Very High |
| **4: Progressive Discovery** | Weeks 10-12 | 1,450 | 40-50 hrs | Medium |
| **5: Privacy Handling** | Weeks 13-16 | 1,350 | 40-50 hrs | High |
| **Cross-Phase** | Throughout | 500 | 70-90 hrs | Medium |
| **Quality/Security** | Throughout | - | 70-80 hrs | High |
| **TOTAL** | **16 weeks** | **8,300** | **380-445 hrs** | **HIGH** |

---

## RESOURCE ALLOCATION

### Recommended Team Composition

- **1 Lead Architect** (40 hrs/week) - Phase leadership, decisions
- **2 Senior Engineers** (40 hrs/week each) - Core implementation
- **2 Mid-level Engineers** (40 hrs/week each) - Features, testing
- **1 Security Engineer** (20 hrs/week) - Security reviews, audit
- **1 DevOps Engineer** (10 hrs/week) - Deployment, infrastructure
- **1 Technical Writer** (10 hrs/week) - Documentation

**Total**: 170 hours/week = ~4.25 person-months

---

## CRITICAL PATH

1. **Week 1-2**: Phase 1 (API Exposure) - blocks everything else
2. **Week 3-6**: Phase 2 (Procedures) - can run in parallel with Phase 1 testing
3. **Week 7-9**: Phase 3 (Sandbox) - must wait for Phase 1
4. **Week 10-12**: Phase 4 (Discovery) - can start after Phase 1
5. **Week 13-16**: Phase 5 (Privacy) - can start after Phase 1, but needs Phase 2

**Critical bottleneck**: Phase 3 security audit (40 hours)
**Recommendation**: Start security audit at Week 5, not Week 9

---

## RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| SRT sandbox escape | Low | Critical | External security audit (40hrs) |
| Performance regression | Medium | High | Benchmarking at each phase |
| Data migration issues | Low | High | Backup + rollback testing |
| Schedule slippage | Medium | Medium | Weekly status checks, buffer time |
| Code integration conflicts | Medium | Medium | Feature branches, merge discipline |
| LLM code generation quality | Medium | High | Manual review + test coverage |

---

## SUCCESS METRICS

### By Phase

**Phase 1**:
- ✅ All memory APIs callable
- ✅ Zero regressions
- ✅ Latency <100ms per operation

**Phase 2**:
- ✅ 101 procedures executable
- ✅ Git versioning working
- ✅ Auto-extraction >80% success rate

**Phase 3**:
- ✅ Code execution safe (no sandbox escapes)
- ✅ Overhead <50ms
- ✅ All security tests passing

**Phase 4**:
- ✅ All APIs discoverable
- ✅ Marketplace functional
- ✅ Recommendations accurate

**Phase 5**:
- ✅ Sensitive data tokenized
- ✅ Encryption at rest
- ✅ Zero sensitive data in logs

### Overall

- ✅ **100% MCP paradigm alignment** (from 60%)
- ✅ **50% token reduction** vs tool abstraction
- ✅ **75%+ faster workflows** (fewer round-trips)
- ✅ **Zero security incidents** post-launch
- ✅ **>95% test coverage**

---

## NEXT STEPS

1. **Week 1**: Kickoff meeting, assign team members
2. **Week 1-2**: Phase 1 implementation
3. **Week 2-3**: Phase 1 review & approval
4. **Week 3-4**: Phase 2 begins (parallel with Phase 1 wrap-up)
5. **Week 5**: Start security audit for Phase 3
6. **Week 7-9**: Phase 3 implementation (with audit findings)
7. **Week 16**: Production deployment

---

**Document Version**: 1.0
**Status**: Ready for Implementation
**Approved By**: [Signature]
**Date**: November 11, 2025
