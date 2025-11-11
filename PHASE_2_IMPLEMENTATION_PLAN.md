# Phase 2: Executable Procedures Implementation Plan

**Status**: Ready to Start (Week 5-8)
**Current Date**: December 2, 2025
**Duration**: 4 weeks (160 hours)
**Team**: 3-4 engineers
**Dependencies**: Phase 1 completion ✅

---

## Executive Summary

Phase 2 transforms Athena from a **memory query system** to an **executable code system**. The key change: instead of storing procedures as metadata (JSON), we store them as **executable Python code** versioned in git with full rollback support.

**Key Outcomes**:
- All 101 procedures converted to executable Python code
- Git-backed procedure store with full version history
- Automated code extraction from agent workflows
- LLM-powered code generation with validation
- Backward compatibility with existing procedures

---

## Phase 2 Technical Challenges & Solutions

### Challenge 1: Async/Sync Signature Mismatch (FROM PHASE 1)

**Current State**:
- MemoryStore.remember() is `async`
- ProjectManager.create_project() is `async`
- MemoryAPI is sync (called from agent code)
- _run_async() helper bridges but has issues

**Root Cause**:
- PostgresDatabase operations are async-first
- Tests need sync context
- Agent code expects sync API

**Solution (Week 5)**:
```python
# src/athena/memory/store.py - Add sync wrapper
class MemoryStore:
    async def remember(self, ...):
        # Keep async implementation
        ...

    def remember_sync(self, ...):
        # NEW: Sync wrapper using _run_async
        return _run_async(self.remember(...))

    def remember_blocking(self, ...):
        # NEW: Alternative using ThreadPoolExecutor
        ...

# src/athena/projects/manager.py - Add sync methods
class ProjectManager:
    async def get_or_create_project(self, ...):
        # Keep async
        ...

    def get_or_create_project_sync(self, ...):
        # NEW: Sync wrapper
        return _run_async(self.get_or_create_project(...))
```

**Implementation Steps**:
1. Create `src/athena/core/async_utils.py` with robust async/sync bridge
2. Add sync wrappers to ProjectManager (2h)
3. Add sync wrappers to MemoryStore (2h)
4. Update MemoryAPI to use sync wrappers (1h)
5. Test all 41 MemoryAPI tests (2h)

**Timeline**: 1 week (7 hours)
**Risk**: Low (wrapper pattern well-tested)
**Impact**: Enables full MemoryAPI functionality

---

### Challenge 2: Procedure Code Extraction

**Current State**:
- Procedures stored as metadata (JSON)
- No code execution
- Manual procedure creation

**Goal**:
- Extract procedures from agent workflows
- Generate executable Python code
- Validate generated code
- Store in git with versioning

**Solution**:

```python
# src/athena/procedural/code_extractor.py
class CodeExtractor:
    """Extract reusable procedures from agent workflows."""

    def extract_from_event(self, event: EpisodicEvent) -> Optional[Procedure]:
        """Extract procedure from single event."""
        # Parse event content for repeatable patterns
        # Look for: "Performed action X with params Y → result Z"
        # Extract: (trigger, actions, conditions, outcomes)

    def extract_from_session(self, session_id: str) -> List[Procedure]:
        """Extract procedures from event session."""
        # Cluster events by action type
        # Group similar sequences
        # Extract common patterns

    def generate_code(self, procedure: Procedure) -> str:
        """Generate Python code for procedure."""
        # Use LLM to convert procedure → Python
        # Template: def {name}({params}): {docstring} {body}
        # Validate syntax with ast.parse()

class CodeValidator:
    """Validate generated procedure code."""

    def validate_syntax(self, code: str) -> bool:
        """Check Python syntax."""
        # Use ast.parse() and compile()

    def validate_imports(self, code: str) -> bool:
        """Check all imports available."""
        # Whitelist: stdlib, athena, common packages

    def validate_safety(self, code: str) -> bool:
        """Check for dangerous operations."""
        # Deny: eval, exec, open, __import__, etc.
        # Allow: memory_api.*, math.*, etc.
```

**Implementation Steps**:
1. Design Procedure model with code field (2h)
2. Implement CodeExtractor (6h)
   - Pattern matching from events
   - LLM code generation prompt engineering
   - Syntax validation
3. Implement CodeValidator (4h)
   - Syntax checking
   - Import validation
   - Safety rules
4. Create extraction tests (4h)
5. Create validation tests (4h)

**Timeline**: 3 weeks (20 hours)
**Risk**: Medium (LLM generation quality)
**Mitigation**: Manual review + confidence thresholds (>0.8 only auto-approve)

---

### Challenge 3: Git-Backed Procedure Store

**Current State**:
- Procedures in database
- No version history
- No rollback capability

**Goal**:
- Store procedures in git repository
- Each procedure = one .py file
- Full commit history
- Easy rollback

**Solution**:

```python
# src/athena/procedural/git_store.py
class GitBackedProcedureStore:
    """Store procedures in git with version history."""

    def __init__(self, repo_path: str):
        self.repo = Repo(repo_path)
        self.procedures_dir = Path(repo_path) / "procedures"

    def store_procedure(self, procedure: Procedure) -> str:
        """Store procedure code in git."""
        # Write: procedures/{procedure_id}/main.py
        # Write: procedures/{procedure_id}/metadata.json
        # Commit with message:
        #   "feat: Add procedure {name} v{version}"
        #   "- Category: {category}"
        #   "- Parameters: {params}"
        #   "- Extracted from: {source}"

    def get_procedure(self, procedure_id: str) -> Procedure:
        """Load procedure from git."""
        # Read .py file
        # Load metadata.json
        # Return as Procedure object

    def list_procedures(self, category: Optional[str] = None) -> List[Procedure]:
        """List all procedures."""

    def get_history(self, procedure_id: str) -> List[ProcedureVersion]:
        """Get all versions of procedure."""
        # Show commit history
        # Show diff between versions

    def rollback(self, procedure_id: str, version: int) -> Procedure:
        """Restore old version."""
        # Checkout old commit
        # Reload procedure

class ProcedureVersion:
    """Single version in history."""
    procedure_id: str
    version: int
    timestamp: datetime
    commit_hash: str
    author: str
    message: str
    code: str
```

**Directory Structure**:
```
athena/
└── procedures/
    ├── remember_event/
    │   ├── main.py
    │   ├── metadata.json
    │   └── tests.py
    ├── extract_pattern/
    │   ├── main.py
    │   ├── metadata.json
    │   └── tests.py
    └── consolidate_memories/
        ├── main.py
        ├── metadata.json
        └── tests.py
```

**Implementation Steps**:
1. Initialize git repo for procedures (1h)
2. Implement GitBackedProcedureStore (6h)
3. Create directory structure (1h)
4. Migrate 101 procedures to git (6h)
   - Write migration script
   - Validate all procedures readable
   - Check no data loss
5. Create git integration tests (4h)

**Timeline**: 2 weeks (18 hours)
**Risk**: Low (proven technology)
**Mitigation**: Keep DB copy until full git validation

---

### Challenge 4: LLM Code Generation & Extraction

**Current State**:
- No code generation
- Manual procedure creation

**Goal**:
- Agents generate code for new procedures
- System extracts procedures from workflows
- LLM validates and improves code

**Solution**:

```python
# src/athena/procedural/code_generator.py
class ProcedureCodeGenerator:
    """Generate executable Python from procedures."""

    def generate_code(self, procedure: Procedure) -> str:
        """Generate Python code for procedure.

        Template:
            def {name}(memory_api: MemoryAPI, {params}):
                '''
                {docstring}

                Parameters:
                    {param_docs}

                Returns:
                    {return_doc}
                '''
                # Implementation
                ...
        """
        prompt = f"""Generate Python code for this procedure:

Name: {procedure.name}
Category: {procedure.category}
Description: {procedure.description}
Parameters: {procedure.parameters}
Expected Output: {procedure.expected_output}

Requirements:
- Use memory_api parameter for all memory operations
- Include type hints
- Include docstring
- Handle errors gracefully
- Return expected output type

Generated code:
"""

        code = self.llm.generate(prompt, max_tokens=1000)
        # Validate syntax
        ast.parse(code)
        return code

    def extract_from_workflow(self, events: List[EpisodicEvent]) -> List[Procedure]:
        """Extract procedures from event sequence.

        Process:
        1. Cluster events by action type
        2. Identify repeating patterns
        3. Generate candidate procedures
        4. Validate each with confidence score
        5. Keep only high-confidence (>0.8)
        """

        # Clustering
        clusters = self.cluster_events(events)

        # Pattern extraction
        patterns = []
        for cluster in clusters:
            pattern = self.extract_pattern(cluster)
            if pattern.confidence > 0.8:
                patterns.append(pattern)

        # Code generation
        procedures = []
        for pattern in patterns:
            code = self.generate_code(pattern)
            procedure = Procedure(
                name=pattern.name,
                code=code,
                confidence=pattern.confidence,
            )
            procedures.append(procedure)

        return procedures
```

**Implementation Steps**:
1. Design LLM prompt templates (2h)
2. Implement code generation (4h)
3. Implement pattern extraction (4h)
4. Create confidence scoring (3h)
5. Test with real workflows (4h)

**Timeline**: 2.5 weeks (17 hours)
**Risk**: Medium (LLM generation quality varies)
**Mitigation**: Human review UI + manual override

---

## Week-by-Week Breakdown

### Week 5: Async/Sync Bridge & ExecutableProcedure Model

**Goal**: Fix async/sync issues and design new procedure model

**Tasks**:

| Task | Hours | Owner | Status |
|------|-------|-------|--------|
| Create async_utils.py with robust bridge | 4h | Eng1 | Pending |
| Add sync wrappers to ProjectManager | 2h | Eng1 | Pending |
| Add sync wrappers to MemoryStore | 2h | Eng1 | Pending |
| Test MemoryAPI (all 41 tests) | 2h | Eng2 | Pending |
| Design ExecutableProcedure model | 3h | Eng2 | Pending |
| Add version/git fields to Procedure | 2h | Eng2 | Pending |
| Create procedure migration strategy | 2h | Eng2 | Pending |

**Deliverables**:
- src/athena/core/async_utils.py (100 LOC)
- Updated ProjectManager (20 LOC new)
- Updated MemoryStore (20 LOC new)
- Updated Procedure model (50 LOC new)
- Migration plan document
- All MemoryAPI tests passing (41/41)

**Exit Criteria**:
- ✅ All 41 MemoryAPI tests passing
- ✅ Async/sync bridge stable
- ✅ ExecutableProcedure model ready
- ✅ Migration plan approved

---

### Week 6: Git Store & Code Extraction

**Goal**: Implement git-backed store and code extraction system

**Tasks**:

| Task | Hours | Owner | Status |
|------|-------|-------|--------|
| Implement GitBackedProcedureStore | 6h | Eng3 | Pending |
| Create procedure directory structure | 2h | Eng3 | Pending |
| Write procedure migration script | 4h | Eng3 | Pending |
| Migrate 101 procedures to git | 6h | Eng3 | Pending |
| Test git store (CRUD, history) | 4h | Eng2 | Pending |
| Implement CodeExtractor | 6h | Eng1 | Pending |
| Test extraction with real events | 2h | Eng1 | Pending |

**Deliverables**:
- src/athena/procedural/git_store.py (300 LOC)
- src/athena/procedural/code_extractor.py (250 LOC)
- scripts/migrate_procedures.py (200 LOC)
- All 101 procedures in git
- Extraction tests (100 LOC)

**Exit Criteria**:
- ✅ All 101 procedures migrated
- ✅ Git store tests passing
- ✅ Code extraction working
- ✅ No data loss in migration

---

### Week 7: LLM Code Generation & Validation

**Goal**: Implement code generation and validation system

**Tasks**:

| Task | Hours | Owner | Status |
|------|-------|-------|--------|
| Create code generation prompts | 3h | Eng2 | Pending |
| Implement ProcedureCodeGenerator | 6h | Eng1 | Pending |
| Implement CodeValidator | 4h | Eng1 | Pending |
| Add confidence scoring | 3h | Eng2 | Pending |
| Create generation tests | 4h | Eng2 | Pending |
| Test with 10 sample procedures | 3h | Eng3 | Pending |

**Deliverables**:
- src/athena/procedural/code_generator.py (300 LOC)
- src/athena/procedural/code_validator.py (150 LOC)
- Generation tests (200 LOC)
- Validation report (10 sample procedures)

**Exit Criteria**:
- ✅ Code generation working
- ✅ Validation system accurate
- ✅ >80% generation success rate
- ✅ Generated code passes tests

---

### Week 8: Integration, Testing, & Documentation

**Goal**: Full Phase 2 integration and finalization

**Tasks**:

| Task | Hours | Owner | Status |
|------|-------|-------|--------|
| Update MemoryAPI with procedure methods | 3h | Eng1 | Pending |
| Procedure execution in sandbox | 4h | Eng3 | Pending |
| Create end-to-end tests | 6h | Eng2 | Pending |
| Performance benchmarking | 4h | Eng3 | Pending |
| Documentation (guide + examples) | 4h | Writer | Pending |
| Code review + merge | 2h | Lead | Pending |

**Deliverables**:
- Updated MemoryAPI (100 LOC)
- End-to-end tests (400 LOC)
- Performance benchmarks
- PROCEDURE_GUIDE.md
- MIGRATION_GUIDE.md

**Exit Criteria**:
- ✅ All tests passing (>90% coverage)
- ✅ Procedures executable
- ✅ Performance <500ms per operation
- ✅ Documentation complete

---

## Risk Register (Phase 2 Specific)

### Risk 1: LLM Code Generation Quality
| Aspect | Details |
|--------|---------|
| Probability | Medium |
| Impact | High (unusable procedures) |
| Mitigation | Confidence thresholds, manual review |
| Contingency | Improve prompts, manual creation |
| Owner | Eng2 |

### Risk 2: Git Migration Data Loss
| Aspect | Details |
|--------|---------|
| Probability | Low |
| Impact | Critical (101 procedures lost) |
| Mitigation | Backup DB, validate each, staged rollout |
| Contingency | Restore from backup, re-migrate |
| Owner | Eng3 |

### Risk 3: Async/Sync Bridge Performance
| Aspect | Details |
|--------|---------|
| Probability | Low |
| Impact | Medium (slow operations) |
| Mitigation | Benchmarking, optimization |
| Contingency | Use ThreadPoolExecutor alternative |
| Owner | Eng1 |

### Risk 4: Procedure Test Coverage
| Aspect | Details |
|--------|---------|
| Probability | Medium |
| Impact | Medium (broken procedures) |
| Mitigation | Auto-generate tests, require validation |
| Contingency | Manual testing, disable bad procedures |
| Owner | Eng2 |

---

## Success Criteria (Phase 2)

### Functional
- ✅ All 101 procedures converted to executable code
- ✅ Git versioning working with full history
- ✅ Rollback tested and functional
- ✅ Code extraction working (>70% auto-extraction)
- ✅ Code generation working (>80% success rate)
- ✅ All procedures tested and passing

### Performance
- ✅ Procedure execution <500ms
- ✅ Code generation <2s per procedure
- ✅ Git operations <100ms
- ✅ No regression from Phase 1

### Quality
- ✅ >90% test coverage
- ✅ All MemoryAPI tests passing (41/41)
- ✅ Zero data loss in migration
- ✅ Code review approved

### Documentation
- ✅ Procedure authoring guide
- ✅ Migration guide
- ✅ Examples (5+ procedures)
- ✅ API reference updated

---

## Decision Points

**Week 5 Go/No-Go**:
- ✅ IF: Async/sync bridge stable AND MemoryAPI tests passing
- ❌ ELSE: Debug and extend timeline

**Week 6 Go/No-Go**:
- ✅ IF: All 101 procedures migrated AND git store tested
- ❌ ELSE: Restore from DB and debug migration

**Week 8 Go/No-Go**:
- ✅ IF: >90% test coverage AND procedures executable
- ❌ ELSE: Extend to Week 9, fix blockers

---

## Next Phase Preview (Phase 3)

Phase 3 implements **OS-level sandboxing** using Anthropic's SRT:
- Procedures execute in sandbox (not just database)
- Isolation from main Athena system
- Resource limits enforced
- Violation monitoring

**Depends On**:
- Phase 1: APIs exposed ✅
- Phase 2: Procedures executable ✅ (in progress)

---

## Appendices

### A. Procedure Code Template

```python
"""Procedure: {NAME}

Description: {DESCRIPTION}
Category: {CATEGORY}
Parameters: {PARAM_NAMES}
Returns: {RETURN_TYPE}

Examples:
    >>> result = {name}(memory_api, param1="value")
    >>> assert isinstance(result, {RETURN_TYPE})
"""

def {name}(
    memory_api,
    {PARAM_DEFINITIONS}
):
    """Execute procedure {NAME}.

    Args:
        memory_api: MemoryAPI instance for memory operations
        {PARAM_DOCS}

    Returns:
        {RETURN_DOC}

    Raises:
        {EXCEPTIONS}
    """
    # Implementation
    ...
    return {RETURN_VALUE}
```

### B. Code Generation Prompt

```
Generate a Python procedure function with these specs:

Name: {procedure.name}
Category: {procedure.category}
Description: {procedure.description}
Input Parameters: {procedure.parameters}
Expected Output: {procedure.expected_output}

Requirements:
1. Function signature: def {name}(memory_api, ...)
2. Include comprehensive docstring
3. Use memory_api for all memory operations
4. Add type hints to all parameters and return
5. Include error handling
6. Return value must match expected output

Generate the complete function code:
```

### C. Migration Script Template

```python
#!/usr/bin/env python
"""Migrate 101 procedures from database to git.

Phases:
1. Backup existing database
2. Read all procedures from database
3. Convert to executable code
4. Write to git repository
5. Validate all procedures
6. Verify no data loss
7. Update MemoryStore to use git

Usage:
    python scripts/migrate_procedures.py --dry-run
    python scripts/migrate_procedures.py --execute
"""
```

---

**Document Version**: 1.0
**Created**: December 2, 2025
**Owner**: Project Lead
**Status**: Ready for Implementation
