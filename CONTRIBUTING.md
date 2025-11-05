# Contributing to Athena

Thank you for your interest in contributing to Athena! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Python 3.10+
- Git
- SQLite3
- (Optional) Ollama for local embeddings
- (Optional) ANTHROPIC_API_KEY for advanced features

### Local Setup

```bash
# Clone the repository
git clone https://github.com/shawkridge/athena.git
cd athena

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Workflow

### 1. Branch Strategy
- **main**: Production-ready code (protected)
- **develop**: Integration branch for features
- **feature/xxx**: Feature branches (from develop)
- **fix/xxx**: Bug fix branches (from develop)
- **docs/xxx**: Documentation branches

### 2. Before Starting Work
```bash
# Get latest code
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name
```

### 3. Code Style

**Python Formatting** (enforced):
```bash
# Format code
black src/ tests/

# Check linting
ruff check src/ tests/
ruff check --fix src/ tests/

# Type checking
mypy src/athena
```

**Naming Conventions**:
- **Classes**: `PascalCase` (e.g., `EpisodicStore`)
- **Functions/Methods**: `snake_case` (e.g., `store_event`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_EVENTS`)
- **Private**: Prefix with `_` (e.g., `_internal_method`)

**Docstrings** (Google style):
```python
def store_event(self, event: Event) -> int:
    """Store an episodic event with spatial-temporal grounding.

    Args:
        event: The event to store with timestamps and context.

    Returns:
        The ID of the stored event.

    Raises:
        ValueError: If event data is invalid.
    """
```

### 4. Testing Requirements

**Test Every Change**:
```bash
# Fast feedback (skip benchmarks)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full suite before PR
pytest tests/ -v --timeout=300

# Specific test file
pytest tests/unit/test_episodic.py -v

# Specific test function
pytest tests/unit/test_episodic.py::TestEpisodicStore::test_store_event -v
```

**Test Markers**:
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.benchmark` - Performance benchmarks
- `@pytest.mark.integration` - Cross-layer tests
- `@pytest.mark.llm` - LLM-dependent tests (optional)

**Coverage Requirements**:
- New code: >90% coverage
- Modified code: >85% coverage
- Overall: >80% coverage

```bash
pytest tests/ --cov=src/athena --cov-report=html
```

### 5. Commit Messages

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Test additions/changes
- `chore`: Maintenance, dependencies

**Examples**:
```
feat(episodic): add spatial-temporal grounding for events
fix(consolidation): handle clustering edge case with < 3 events
docs: update memory architecture diagrams
refactor(rag): simplify query transformation logic
perf(semantic): optimize BM25 ranking algorithm
```

### 6. Pull Request Process

**Before Creating PR**:
1. Ensure all tests pass
2. Update documentation if needed
3. Add entry to CHANGELOG.md
4. Self-review your code

**PR Description**:
```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- Test 1
- Test 2

## Motivation
Why is this change needed?

## Checklist
- [ ] Tests pass
- [ ] Code formatted (black, ruff)
- [ ] Documentation updated
- [ ] No breaking changes
```

**Review Process**:
1. Request review from maintainers
2. Address all comments
3. Re-request review after changes
4. Squash commits before merge (if needed)

## Architecture Guidelines

### Adding a Memory Layer

1. **Create module** in `src/athena/new_layer/`
2. **Define models** in `models.py`
3. **Implement store** with database operations
4. **Add SQL schema** to `migrations/`
5. **Create MCP tools** in `mcp/handlers.py`
6. **Write unit tests** in `tests/unit/`
7. **Write integration tests** in `tests/integration/`
8. **Document** in CLAUDE.md and README.md

### Adding an MCP Tool

1. **Define in handlers.py**:
   ```python
   @mcp.tool()
   async def my_tool(param: str) -> dict:
       """Tool description."""
       return {"result": "value"}
   ```

2. **Add integration test**:
   ```python
   def test_my_tool():
       result = server.my_tool("input")
       assert result["result"] == "value"
   ```

3. **Document in README.md**

### Performance Considerations

**Before Optimizing**:
- Profile with `pytest tests/benchmark/` (if applicable)
- Identify actual bottlenecks
- Measure impact after changes

**Targets**:
- Semantic search: <100ms
- Graph operations: <50ms
- Consolidation: <5s
- Working memory: <10ms

## Documentation Standards

### Code Comments
Use comments for **why**, not **what**:

```python
# Good: Explains reasoning
# Cluster by session first to respect temporal boundaries
events_by_session = self._group_events_by_session(events)

# Bad: States obvious facts
# Cluster events
events_by_session = self._group_events_by_session(events)
```

### Docstrings
- **Module level**: Brief description + example usage
- **Class level**: Purpose, key methods, example
- **Function level**: Args, returns, raises, example

### Updates
When modifying existing code:
1. Update docstrings if behavior changes
2. Add/update comments for non-obvious logic
3. Update related documentation files
4. Add entry to CHANGELOG.md

## Release Process

### Version Numbering
Semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Steps
1. Update version in `src/athena/__init__.py`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.2.3`
4. Push tags: `git push origin --tags`
5. Create GitHub release with changelog

## Issues & Discussions

### Reporting Bugs
1. Check if issue already exists
2. Include:
   - Python version
   - Athena version
   - Minimal reproduction code
   - Actual vs expected behavior
   - Relevant logs/output

### Proposing Features
1. Check if already proposed
2. Explain motivation and use case
3. Describe proposed solution
4. Discuss alternatives

### Asking Questions
Use GitHub Discussions for:
- How-to questions
- Design discussions
- Architecture questions
- Feature brainstorming

## Performance Testing

```bash
# Run benchmarks
pytest tests/benchmark/ -v

# Profile specific operation
python -m cProfile -s cumtime -m pytest tests/benchmark/test_consolidation.py

# Memory profiling
pip install memory-profiler
python -m memory_profiler tests/benchmark/test_memory.py
```

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Run Specific Test with Output
```bash
pytest tests/unit/test_episodic.py::TestClass::test_method -v -s
```

### Interactive Debugging
```bash
pytest tests/unit/test_episodic.py -v -s --pdb
```

### View Database Schema
```bash
sqlite3 ~/.memory-mcp/memory.db ".schema"
```

## Common Development Tasks

### Create New Test
```bash
# In tests/unit/ or tests/integration/
touch tests/unit/test_new_feature.py

# Add to pytest structure
# See existing tests for pattern
```

### Run Type Checking
```bash
mypy src/athena --strict
```

### Update Dependencies
```bash
pip install --upgrade pip
pip install -e ".[dev]"
pip freeze > requirements.txt
```

### Clean Up
```bash
# Remove cache files
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Remove test artifacts
rm -rf .pytest_cache/
rm -rf htmlcov/
rm -rf .mypy_cache/
```

## Support

- **Documentation**: See `CLAUDE.md` and `README.md`
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Code Review**: Pull requests

## Code of Conduct

- Be respectful and professional
- Focus on code, not people
- Assume good intentions
- Help others learn and grow

## Questions?

- Check existing issues/PRs
- Review CLAUDE.md for architecture
- Read TESTING.md for test patterns
- Ask in GitHub Discussions

Thank you for contributing to Athena!
