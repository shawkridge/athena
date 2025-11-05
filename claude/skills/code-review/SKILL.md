---
category: skill
name: code-review
description: Perform comprehensive code review for quality, consistency, and best practices
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.81
trigger: Code review needed, pull request to review, "review" mentioned, quality check needed
---

# Code Review Skill

Guides comprehensive code review of Memory MCP following project standards.

## When I Invoke This

You have:
- Pull request needing review
- New code to quality check
- Want to ensure standards met
- Need to provide feedback
- Verify best practices followed

## What I Do

I guide code review in these phases:

```
1. STRUCTURE Phase: Check architecture
   → Follows project patterns?
   → Right location in codebase?
   → Dependencies correct?
   → No circular imports?

2. IMPLEMENTATION Phase: Check correctness
   → Logic sound?
   → Error handling complete?
   → Edge cases handled?
   → Types correct?

3. STYLE Phase: Check consistency
   → Follows naming conventions?
   → Code formatting correct?
   → Consistent with codebase?
   → Comments/docs present?

4. TESTING Phase: Check coverage
   → Unit tests present?
   → Integration tests?
   → Edge cases tested?
   → Coverage adequate?

5. PERFORMANCE Phase: Check efficiency
   → Any obvious inefficiencies?
   → Database queries optimized?
   → Memory usage reasonable?
   → No N+1 problems?

6. MAINTENANCE Phase: Check quality
   → Will this be easy to maintain?
   → Is it clear what it does?
   → Any technical debt?
   → Dependencies up-to-date?
```

## Review Checklist

### Architecture & Design
- [ ] Code location correct (right file, right directory)
- [ ] Follows project patterns (same as existing code)
- [ ] No circular dependencies
- [ ] Proper separation of concerns
- [ ] Reuses existing code (no duplication)
- [ ] Extends existing abstractions properly

### Implementation Quality
- [ ] Logic is sound and correct
- [ ] Error handling comprehensive
- [ ] Edge cases handled
- [ ] No hardcoded values (use constants)
- [ ] No TODO/FIXME comments (should be issues)
- [ ] Validation present for inputs

### Type Safety (Python/TypeScript)
- [ ] Type hints present and correct
- [ ] No use of `any` type (Python: `Any`)
- [ ] Generics used appropriately
- [ ] Union types clear
- [ ] No type: ignore comments

### Testing
- [ ] Unit tests present
- [ ] Integration tests (if applicable)
- [ ] Edge cases tested
- [ ] Error conditions tested
- [ ] Test isolation (no shared state)
- [ ] Test naming clear

### Code Style
- [ ] Formatting matches project (black/ruff)
- [ ] Naming conventions followed
- [ ] No unused imports
- [ ] No unused variables
- [ ] Proper docstrings/comments
- [ ] Line length reasonable

### Performance
- [ ] No obvious inefficiencies
- [ ] Database queries indexed
- [ ] No N+1 query patterns
- [ ] Memory usage reasonable
- [ ] Algorithms efficient
- [ ] No unnecessary computations

### Documentation
- [ ] Function docstrings present
- [ ] Complex logic documented
- [ ] Parameters documented
- [ ] Return types documented
- [ ] Examples provided (if needed)
- [ ] Architecture decisions explained

## Code Review Patterns

### Pattern 1: Check Architectural Fit

```python
# Review question: Does this belong here?

# ✓ Good: Memory layer extending existing pattern
class WorkingMemoryStore(BaseMemoryStore):
    def _ensure_schema(self):
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS working_memory_items (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                ...
            )
        """)

# ❌ Bad: Random code in wrong place
def process_user_input():
    # Magical user input handling
    # This belongs in a different module!
```

**Check**: Does new code fit the architecture? Is it in the right place?

---

### Pattern 2: Check Error Handling

```python
# Review question: What if something fails?

# ❌ Bad: No error handling
def get_memory(memory_id):
    result = db.query("SELECT * FROM memories WHERE id = ?", memory_id)
    return result[0]  # What if result is empty?

# ✓ Good: Proper error handling
def get_memory(memory_id: int) -> Optional[Memory]:
    try:
        result = db.query("SELECT * FROM memories WHERE id = ?", memory_id)
        if not result:
            return None
        return Memory(**result[0])
    except DatabaseError as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        raise MemoryNotFoundError(memory_id) from e
```

**Check**: Are failures handled? Are errors informative?

---

### Pattern 3: Check Type Safety

```python
# Review question: Is this typesafe?

# ❌ Bad: Loose types
def process_memory(memory):  # What type is memory?
    result = memory.get('content')  # Or memory.content?
    return str(result)  # Why convert to string?

# ✓ Good: Type hints
def process_memory(memory: Memory) -> str:
    result: str = memory.content  # Clear type
    return result
```

**Check**: Are types correct? Are hints comprehensive?

---

### Pattern 4: Check for Code Duplication

```python
# Review question: Is this code repeated?

# ❌ Bad: Duplicated validation
def create_episodic_event(content: str):
    if not content or not content.strip():
        raise ValueError("Content required")
    return EpisodicEvent(content=content)

def create_semantic_memory(content: str):
    if not content or not content.strip():  # DUPLICATE!
        raise ValueError("Content required")
    return SemanticMemory(content=content)

# ✓ Good: Extract common validation
def validate_content(content: str) -> str:
    if not content or not content.strip():
        raise ValueError("Content required")
    return content.strip()

def create_episodic_event(content: str):
    return EpisodicEvent(content=validate_content(content))

def create_semantic_memory(content: str):
    return SemanticMemory(content=validate_content(content))
```

**Check**: Is code repeated? Should it be extracted?

---

### Pattern 5: Check Test Coverage

```python
# Review question: Is everything tested?

# ❌ Bad: No test
def find_similar(query, threshold=0.8):
    """Find memories similar to query."""
    results = search(query)
    return [r for r in results if r.score > threshold]
# No test! Is this function correct?

# ✓ Good: Comprehensive tests
def test_find_similar_basic():
    """Find similar returns matching results."""
    result = find_similar("test query")
    assert len(result) > 0

def test_find_similar_threshold():
    """Threshold filters low-confidence results."""
    result = find_similar("test", threshold=0.95)
    assert all(r.score > 0.95 for r in result)

def test_find_similar_empty():
    """Returns empty for no matches."""
    result = find_similar("xyz" * 100)
    assert len(result) == 0
```

**Check**: Are tests present? Do they cover edge cases?

---

### Pattern 6: Check Documentation

```python
# Review question: Can someone understand this?

# ❌ Bad: No docs
def process(x, y):
    return x * y + x / y

# ✓ Good: Clear docs
def calculate_weighted_score(
    base_score: float,
    confidence: float
) -> float:
    """Calculate final confidence score with weighting.

    Args:
        base_score: Raw similarity score (0.0-1.0)
        confidence: Confidence in the match (0.0-1.0)

    Returns:
        Weighted score combining base and confidence

    Example:
        >>> calculate_weighted_score(0.9, 0.8)
        0.87
    """
    # 40% base score, 40% confidence, 20% buffer
    return base_score * 0.4 + confidence * 0.4 + 0.2
```

**Check**: Are functions documented? Is logic clear?

---

## Step-by-Step Review Process

### Step 1: Understand the Change
```bash
# What files changed?
git diff --name-only main..feature-branch

# What was changed?
git diff main..feature-branch

# Review each file one by one
```

### Step 2: Check Architecture
```
Ask:
- Does this fit the project architecture?
- Is the code in the right place?
- Does it reuse existing patterns?
- Is it the right abstraction level?
```

### Step 3: Check Implementation
```
Ask:
- Is the logic correct?
- Are error cases handled?
- Are there edge cases?
- Is it efficient?
```

### Step 4: Check Tests
```bash
# Did tests pass?
pytest tests/ -v

# What's the coverage?
coverage run && coverage report

# Are there new tests for new code?
```

### Step 5: Check Style
```bash
# Formatting correct?
black --check .

# Linting issues?
ruff check .

# Type checking?
mypy .
```

### Step 6: Provide Feedback
```
For each issue:
1. Where: Specific line/file
2. What: What's the problem?
3. Why: Why is it a problem?
4. How: How to fix it?
5. Optional: Example code
```

### Step 7: Approve or Request Changes
```
If all checks pass:
"Looks good! Approved with minor suggestions."

If issues found:
"Changes needed: fix error handling (line 45), add tests for edge case, update docstring."

If major issues:
"Please revise: architecture doesn't fit pattern, needs redesign of X."
```

## Common Review Comments

### Comment 1: Type Safety
```
❌ Comment: "Type hints missing"
def get_memory(id):  # What type?
    return self.store.get(id)  # What's returned?

✓ Fix:
def get_memory(self, id: int) -> Optional[Memory]:
    return self.store.get(id)
```

### Comment 2: Error Handling
```
❌ Comment: "What if this is empty?"
def get_first(results):
    return results[0]  # IndexError if empty!

✓ Fix:
def get_first(results: List[T]) -> Optional[T]:
    return results[0] if results else None
```

### Comment 3: Duplication
```
❌ Comment: "This validation is duplicated in 3 places"
[See validation code repeated]

✓ Fix:
[Extract to shared function]
```

### Comment 4: Documentation
```
❌ Comment: "Can you add a docstring? What does this do?"
def process(x, y, z):
    return x * y + z

✓ Fix:
def calculate_score(base: float, weight: float, offset: float) -> float:
    """Calculate weighted score with offset."""
    return base * weight + offset
```

### Comment 5: Testing
```
❌ Comment: "No test for empty input case"
def find_memories(query):
    results = search(query)
    return results

✓ Fix:
[Add test for empty query, no results, etc.]
```

## Review Approval Criteria

**Approve if:**
- ✓ All architecture checks pass
- ✓ Implementation is correct
- ✓ Tests present and passing
- ✓ Code style consistent
- ✓ Documentation complete
- ✓ No major concerns

**Request Changes if:**
- ❌ Architecture issues (redesign needed)
- ❌ Logic errors
- ❌ Missing error handling
- ❌ Missing tests
- ❌ Type safety issues
- ❌ Performance concerns

**Conditional Approval if:**
- ⚠️ Minor improvements needed (can be separate PR)
- ⚠️ Follow-up tests recommended
- ⚠️ Documentation could be better

## Related Skills

- **refactor-code** - Often triggered by code review findings
- **fix-failing-tests** - Ensure tests pass during review
- **improve-typescript-safety** - Type safety review focus

## Success Criteria

✓ All checks completed
✓ Issues identified clearly
✓ Feedback is constructive
✓ Suggested improvements clear
✓ Code quality improved
✓ Standards enforced consistently
