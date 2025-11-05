---
category: skill
name: fix-failing-tests
description: Systematically debug and fix failing tests with pattern recognition and suggestions
allowed-tools: ["Bash", "Read", "Write", "Grep", "Glob", "Edit"]
confidence: 0.91
trigger: Tests are failing, user wants to debug test failures, CI/CD shows red tests, "pytest failed"
---

# Fix Failing Tests Skill

Systematically debugs and fixes failing tests using pattern recognition and guided investigation.

## When I Invoke This

You have:
- Failing pytest tests that need debugging
- Test failures from CI/CD or local runs
- Unclear error messages
- Multiple tests failing at once
- Tests that pass locally but fail in CI

## What I Do

I guide systematic debugging in these phases:

```
1. ANALYZE Phase: Understand what failed
   → Run tests with detailed output
   → Parse error messages
   → Categorize failure types (assertion, timeout, fixture, import)
   → Identify patterns (same error in multiple tests?)

2. INVESTIGATE Phase: Find root cause
   → Examine test code for assumptions
   → Check mocks and fixtures
   → Review implementation code being tested
   → Trace execution path
   → Check for flaky test indicators (timing, order dependency)

3. CLASSIFY Phase: Determine failure type
   → Is it the code or the test?
   → Is it a missing dependency?
   → Is it a timing issue?
   → Is it a bad assumption?
   → Is it an integration problem?

4. FIX Phase: Implement the solution
   → Based on classification, fix the root cause
   → Update test if assumption was wrong
   → Update code if it has the bug
   → Validate fix is minimal and correct

5. VALIDATE Phase: Verify fix works
   → Run failing tests (should pass now)
   → Run full test suite (no regressions)
   → Check test is stable (run multiple times)
   → Commit with clear message
```

## Test Failure Classification

### Type 1: Assertion Failures
**Symptom**: `AssertionError` with actual vs expected

```
FAILED test_foo.py::test_bar - AssertionError: assert 10 == 5
```

**Investigation**:
- What changed in the code being tested?
- Is the expected value correct?
- Is the assertion checking the right thing?

**Fix**:
- Update code if logic is wrong
- Update test if expectation was wrong
- Clarify assertion with better variable names

---

### Type 2: Fixture Issues
**Symptom**: `E fixture 'something' not found` or fixture setup fails

```
FAILED test_foo.py::test_bar - fixture 'db' not found
```

**Investigation**:
- Does the fixture exist?
- Is it in conftest.py or the right scope?
- Are dependencies in the right order?
- Does fixture setup complete without error?

**Fix**:
- Add missing fixture
- Fix fixture dependencies
- Move fixture to conftest.py if needed
- Debug fixture setup code

---

### Type 3: Import Errors
**Symptom**: `ModuleNotFoundError` or `ImportError`

```
FAILED test_foo.py - ModuleNotFoundError: No module named 'something'
```

**Investigation**:
- Does module exist?
- Is Python path correct?
- Is there a circular import?
- Are dependencies installed?

**Fix**:
- Install missing dependency
- Fix circular import by reorganizing
- Fix relative import path
- Check __init__.py exists

---

### Type 4: Timeout Failures
**Symptom**: `Timeout: test took longer than X seconds`

```
FAILED test_foo.py::test_bar - TimeoutError: Timeout: 30s
```

**Investigation**:
- Is test actually slow or stuck?
- Is there an infinite loop?
- Is it waiting for external resource?
- Is it using wrong fixture/mock?

**Fix**:
- Add mock for external resource
- Optimize implementation
- Increase timeout if legitimate slowness
- Fix infinite loop

---

### Type 5: Flaky Tests
**Symptom**: Test passes sometimes, fails sometimes

```
FAILED test_foo.py::test_bar - (then passes on retry)
```

**Investigation**:
- Is there timing dependency?
- Is test order dependent?
- Is there random data?
- Is there shared state?
- Is there thread safety issue?

**Fix**:
- Add explicit waits instead of sleeps
- Don't depend on test order
- Use fixed seed for randomness
- Properly isolate tests
- Use locks if multithreaded

---

### Type 6: Logic Bugs in Code
**Symptom**: Test correctly finds a bug in implementation

```
FAILED test_foo.py::test_bar - AssertionError: None != expected_value
```

**Investigation**:
- Test is correct?
- Implementation has logic bug?
- Edge case not handled?

**Fix**:
- Fix implementation logic
- Add error handling for edge cases
- Add null checks if needed

---

## Step-by-Step Debug Process

### 1. Get Clear Error Message
```bash
# Run with verbose output
pytest test_file.py::test_name -v -s

# Run with full traceback
pytest test_file.py::test_name -v --tb=long

# Run with print statements visible
pytest test_file.py::test_name -v -s --capture=no
```

### 2. Examine Test Code
```
Look for:
- What is test trying to verify?
- What are the assumptions?
- What fixtures are used?
- What mocks are in place?
- What's the expected behavior?
```

### 3. Examine Implementation Code
```
Look for:
- Does implementation match test expectations?
- Are edge cases handled?
- Is error handling correct?
- Are null/empty inputs handled?
- Is return type correct?
```

### 4. Check Dependencies
```bash
# Are test fixtures defined?
pytest --fixtures | grep fixture_name

# Are imports working?
python -c "from module import thing"

# Is the module structure correct?
ls -la src/module/
```

### 5. Run Isolated
```bash
# Run just the failing test
pytest test_file.py::test_name -v

# Run test multiple times (for flakiness)
pytest test_file.py::test_name -v --count=5

# Run test in different order
pytest test_file.py -v -p no:randomly  # without randomization
```

## Common Test Failures & Fixes

### Issue: "fixture 'tmp_path' not found"
**Cause**: Using tmp_path in wrong function signature
```python
# ❌ Wrong
def test_foo():
    tmp_path = tmp_path  # Not available!

# ✓ Correct
def test_foo(tmp_path):
    # Now tmp_path is available
```

**Fix**: Add tmp_path as parameter to test function

---

### Issue: "assert None == something"
**Cause**: Function returned None unexpectedly
```python
# Check what was returned
def test_foo():
    result = function_under_test()
    print(f"Result: {result}")  # Add debugging
    assert result is not None
```

**Fix**:
- Add print/assert to find where None comes from
- Check function implementation returns value
- Check function doesn't have early return

---

### Issue: "TimeoutError" for query tests
**Cause**: Database query hanging or infinite loop
```python
# ❌ Might timeout
def test_slow_query(db):
    results = db.execute("SELECT * FROM huge_table")  # Takes too long

# ✓ Better
def test_slow_query(db, monkeypatch):
    # Mock the slow operation
    monkeypatch.setattr(db, "execute", lambda x: ["result"])
    results = db.execute(...)
```

**Fix**:
- Mock expensive operations
- Add LIMIT to queries
- Use smaller test data

---

### Issue: "Test passes alone, fails with others"
**Cause**: Test has shared state or order dependency
```python
# ❌ Uses shared state
class TestSuite:
    counter = 0  # Shared across tests!

    def test_one(self):
        self.counter += 1
        assert self.counter == 1

    def test_two(self):
        self.counter += 1
        assert self.counter == 1  # Fails if test_one ran first

# ✓ Each test isolated
def test_one():
    counter = 0
    counter += 1
    assert counter == 1

def test_two():
    counter = 0  # Fresh each time
    counter += 1
    assert counter == 1
```

**Fix**:
- Use tmp_path for file operations
- Use fresh databases
- Don't share state across tests
- Use monkeypatch for mocking

---

## Debug Checklist

- [ ] Run test with `-v -s` to see full output
- [ ] Read error message carefully (often tells you the problem)
- [ ] Check test assumptions (are they still valid?)
- [ ] Check implementation (was it changed?)
- [ ] Check fixtures (are they defined and working?)
- [ ] Check imports (are they available?)
- [ ] Run test in isolation (pytest test.py::test_name)
- [ ] Run test multiple times (is it flaky?)
- [ ] Check test logs (add print statements)
- [ ] Compare with similar passing tests
- [ ] Check git diff (what changed?)

## Related Skills

- **add-mcp-tool** - When test needs new tool to test
- **refactor-code** - If test code is complex and needs refactoring
- **debug-integration-issue** - For complex multi-layer test failures

## Success Criteria

✓ Root cause identified
✓ Test passes reliably (not flaky)
✓ Fix is minimal and correct
✓ No regressions (full test suite passes)
✓ Error message is clear if test should fail
✓ Test documents what it's testing
