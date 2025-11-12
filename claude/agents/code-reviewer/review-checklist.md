# Code Review Checklist - Athena Project

Use this checklist when reviewing code for the Athena memory system project.

## Architecture Review

- [ ] Does the code follow Athena's 8-layer architecture?
- [ ] Correct layer assignment (episodic, semantic, consolidation, etc.)?
- [ ] Dependencies flow correctly (no backwards dependencies)?
- [ ] Integration with other layers is clear and documented?
- [ ] New abstractions justified and follow existing patterns?
- [ ] Isolation maintained between layers?

## Python Standards (Athena)

- [ ] Type hints present on all functions (PEP 484)?
- [ ] Async/await used correctly (async-first architecture)?
- [ ] Black formatting compliant?
- [ ] Ruff linting passes?
- [ ] MyPy type checking passes?
- [ ] No bare except clauses?
- [ ] Proper exception handling (specific types)?
- [ ] Resource cleanup (files, connections, DB)?

## Memory Layer Operations

### Episodic Layer
- [ ] Event schema valid and matches models.py?
- [ ] Timestamps and spatial-temporal grounding included?
- [ ] Events properly indexed?
- [ ] Cleanup/deletion handled?

### Semantic Layer
- [ ] Embeddings generated with correct provider (Ollama/Anthropic)?
- [ ] Vector storage using sqlite-vec properly?
- [ ] BM25 indexing functional?
- [ ] Caching working (LRU, TTL)?
- [ ] Search queries performant (<100ms)?

### Consolidation Layer
- [ ] Dual-process reasoning implemented (System 1 + System 2)?
- [ ] Clustering valid (temporal/semantic)?
- [ ] Pattern extraction working?
- [ ] LLM validation called when uncertainty >0.5?
- [ ] Output quality validated?

### Knowledge Graph
- [ ] Entity relationships maintained?
- [ ] Community detection working?
- [ ] No orphaned entities?
- [ ] Consistency maintained across updates?
- [ ] Graph queries performant?

## Database Operations

- [ ] Parameterized queries (no SQL injection)?
- [ ] Transactions used for multi-step operations?
- [ ] Proper rollback on error?
- [ ] Database migrations handled (CREATE TABLE IF NOT EXISTS)?
- [ ] Connection pooling if applicable?
- [ ] Indexes on frequently queried columns?
- [ ] No N+1 query patterns?

## Testing

- [ ] Unit tests for critical functions?
- [ ] Integration tests for layer interactions?
- [ ] Edge cases covered (empty, null, extreme values)?
- [ ] Error cases tested (exceptions, timeouts)?
- [ ] Test coverage >80% for critical code?
- [ ] Fixtures properly set up/torn down?
- [ ] Tests pass locally and in CI?
- [ ] No flaky tests?

## Security

- [ ] No hardcoded credentials?
- [ ] No secrets in logs or error messages?
- [ ] Database access validated?
- [ ] File paths properly validated?
- [ ] Input validation present?
- [ ] No eval() or exec() usage?
- [ ] Dependencies up-to-date?
- [ ] No known vulnerabilities?

## Performance

- [ ] Algorithm complexity documented?
- [ ] O(n) complexity acceptable for data size?
- [ ] Database queries optimized (EXPLAIN PLAN)?
- [ ] Caching used for expensive operations?
- [ ] Vector search performance acceptable?
- [ ] Memory usage reasonable?
- [ ] No obvious inefficiencies?
- [ ] Benchmarks included if performance-critical?

## Documentation

- [ ] Docstrings present and accurate?
- [ ] Complex logic explained with comments?
- [ ] Integration points documented?
- [ ] Configuration options documented?
- [ ] Examples provided for new APIs?
- [ ] README updated if applicable?
- [ ] Migration steps documented if needed?
- [ ] Architecture decisions explained?

## Commit Quality

- [ ] Commit message clear and descriptive?
- [ ] PR/change scope reasonable?
- [ ] Related changes grouped together?
- [ ] Unrelated changes separated?
- [ ] No debug code left in?
- [ ] No commented-out code?
- [ ] Files properly formatted?

## Pre-Merge Checks

- [ ] All tests passing?
- [ ] No merge conflicts?
- [ ] Code reviewed by team member?
- [ ] Performance impact assessed?
- [ ] Security review complete?
- [ ] Documentation complete?
- [ ] Ready for production deployment?

---

## Severity Scale

**CRITICAL** (Block merge):
- Security vulnerability
- Data loss risk
- Breaking change to API
- Memory leak
- Test failures

**MAJOR** (Should fix before merge):
- Performance regression
- Architectural issue
- Maintainability concern
- Missing test coverage
- Documentation gap

**MINOR** (Consider for next sprint):
- Code style suggestion
- Naming improvement
- Documentation enhancement
- Optimization opportunity
- Refactoring idea

---

## Quick Reference

**Athena 8-Layer Stack**:
1. Episodic Memory - Event storage with timestamps
2. Semantic Memory - Vector + BM25 search
3. Procedural Memory - Reusable workflows
4. Prospective Memory - Tasks and goals
5. Knowledge Graph - Entity relationships
6. Meta-Memory - Quality tracking
7. Consolidation - Pattern extraction (dual-process)
8. Supporting Systems - RAG, planning, GraphRAG

**Key Tools**:
- Database: `src/athena/core/database.py`
- Models: `src/athena/core/models.py`
- Config: `src/athena/core/config.py`
- Tests: `tests/unit/` and `tests/integration/`

**Required Commands**:
```bash
# Before committing
black src/ tests/
ruff check --fix src/ tests/
mypy src/athena
pytest tests/unit/ tests/integration/ -v

# Before pushing
pytest tests/ -v --timeout=300
```
