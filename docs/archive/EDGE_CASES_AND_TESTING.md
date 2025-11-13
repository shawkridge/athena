# Edge Cases & Comprehensive Testing Guide

Complete guide for testing semantic code search under challenging conditions.

---

## Edge Cases Covered

### 1. Large Codebases

#### Scenario 1.1: Very Large Workspace (100K+ files)

**Setup**:
```bash
# Create test workspace
mkdir -p /tmp/large-workspace
for i in {1..100000}; do
  echo "def func_$i(): pass" > /tmp/large-workspace/file_$i.py
done
```

**Test Cases**:
- [ ] Indexing completes without crashing
- [ ] Memory usage stays under 2GB
- [ ] Search latency < 500ms (even with 100K+ units)
- [ ] No file descriptors leak
- [ ] Cache doesn't grow unbounded

**Expected Results**:
```
Files: 100K
Units indexed: ~100K
Memory: ~800MB-1.2GB
Index time: 30-60s
Search time: 100-300ms
```

**Performance Targets**:
- ✅ No crashes
- ✅ Memory linear to workspace size
- ✅ Search latency acceptable

---

#### Scenario 1.2: Deep Nesting (1000 levels)

**Setup**:
```bash
# Create deeply nested structure
cd /tmp
mkdir -p deep/nested/structure/{a,b,c,d,e}/{a,b,c,d,e}/{a,b,c,d,e}
find deep -type d | wc -l  # Should show many levels
```

**Test Cases**:
- [ ] File traversal doesn't hit recursion limits
- [ ] Relative paths handled correctly
- [ ] Performance doesn't degrade with depth

**Expected Results**: All paths indexed correctly, no stack overflow errors

---

### 2. Concurrent Searches

#### Scenario 2.1: Simultaneous Multi-User Searches

**Setup**:
```python
import concurrent.futures
import time

def concurrent_searches(searcher, num_users=10, duration_seconds=60):
    """Simulate concurrent searches."""
    queries = [
        "function that validates",
        "class for handling",
        "error recovery",
        "authentication",
        "database connection"
    ]

    def search_worker(worker_id):
        """Worker that performs repeated searches."""
        start = time.time()
        while time.time() - start < duration_seconds:
            query = queries[worker_id % len(queries)]
            results = searcher.search(query)
            time.sleep(0.1)  # Simulate user think time

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(search_worker, i) for i in range(num_users)]
        concurrent.futures.wait(futures)
```

**Test Cases**:
- [ ] No race conditions or data corruption
- [ ] Search results consistent across threads
- [ ] Cache thread-safe (no duplicate work)
- [ ] Memory doesn't leak under concurrent load
- [ ] Latency doesn't degrade significantly

**Expected Results**:
```
10 concurrent users → All searches succeed
Memory stable at ~500MB
No exceptions or crashes
P99 latency: <500ms
```

---

#### Scenario 2.2: Parallel Indexing & Searching

**Setup**:
```python
import threading

# Thread 1: Continuous indexing
def index_worker(indexer, directory):
    for i in range(5):
        indexer.index_workspace(directory)
        time.sleep(1)

# Thread 2: Concurrent searches
def search_worker(searcher):
    for i in range(100):
        searcher.search("test query")
        time.sleep(0.05)

index_thread = threading.Thread(target=index_worker, args=(indexer, "/tmp/test"))
search_thread = threading.Thread(target=search_worker, args=(searcher,))

index_thread.start()
search_thread.start()
```

**Test Cases**:
- [ ] Searches work during indexing
- [ ] Index updates don't corrupt search results
- [ ] No deadlocks
- [ ] Search results gradually improve as index updates

---

### 3. Malformed Input

#### Scenario 3.1: Special Characters in Queries

**Test Queries**:
- `"@#$%^&*()"` - Special characters
- `"'; DROP TABLE --"` - SQL injection attempt
- `"<script>alert('xss')</script>"` - XSS attempt
- `"../../../etc/passwd"` - Path traversal
- `"null\x00injection"` - Null byte
- Very long query (10K+ characters)

**Test Cases**:
- [ ] Queries sanitized/escaped
- [ ] No SQL injection vulnerability
- [ ] No command injection
- [ ] No path traversal
- [ ] Long queries handled gracefully (truncated or error)

---

#### Scenario 3.2: Unusual File Types

**Setup**:
```bash
# Create unusual files
touch /tmp/test/.hidden_file.py
touch "/tmp/test/file with spaces.py"
touch "/tmp/test/file-with-dashes.py"
touch "/tmp/test/file.multiple.dots.py"
touch "/tmp/test/UPPERCASE.PY"
touch "/tmp/test/file.pY"  # Wrong case
```

**Test Cases**:
- [ ] Hidden files handled correctly (excluded if desired)
- [ ] Spaces in filenames don't break parsing
- [ ] Special characters in names handled
- [ ] Case sensitivity correct for language detection

---

#### Scenario 3.3: Corrupt/Invalid Code

**Setup**:
```python
# Create files with invalid syntax
with open("/tmp/test/broken.py", "w") as f:
    f.write("def func( ]]] {{{ !!!")

with open("/tmp/test/incomplete.py", "w") as f:
    f.write("def func(:\n  if x")  # Unclosed

with open("/tmp/test/huge.py", "w") as f:
    f.write("x = " + ("1+" * 100000))  # Very long line
```

**Test Cases**:
- [ ] Parser doesn't crash on invalid syntax
- [ ] Graceful error handling for malformed files
- [ ] Partial extraction of valid code structures
- [ ] Very long lines handled (truncated or split)

---

### 4. Memory & Resource Limits

#### Scenario 4.1: Low Memory Conditions

**Setup**:
```bash
# Simulate low memory (requires root or memory limit)
ulimit -v 524288  # 512MB limit

# Then run search
python -m semantic_search.backend
```

**Test Cases**:
- [ ] Backend doesn't crash with OOM
- [ ] Graceful degradation (slower, not crash)
- [ ] Error message if insufficient memory
- [ ] Cache reduced under memory pressure

**Expected Behavior**:
- ✅ Reduced cache size
- ✅ Slower but functional
- ❌ NOT: Crashes or corrupted data

---

#### Scenario 4.2: Disk Space Issues

**Setup**:
```bash
# Fill disk to 95%
dd if=/dev/zero of=/tmp/fillup bs=1M count=1000

# Then try indexing
```

**Test Cases**:
- [ ] Indexing fails gracefully (not crash)
- [ ] Error message: "Insufficient disk space"
- [ ] Existing index intact (no corruption)
- [ ] Cleanup orphaned files

---

### 5. Networking Issues (For Distributed Setup)

#### Scenario 5.1: Backend Unavailable

**Setup**:
```python
# Block port 5000
# sudo iptables -A OUTPUT -p tcp --dport 5000 -j DROP
```

**Test Cases** (from IDE):
- [ ] Error message: "Backend not available"
- [ ] User guidance: "Check backend is running"
- [ ] IDE remains responsive
- [ ] Reconnection attempt after delay

---

#### Scenario 5.2: High Latency (Slow Network)

**Setup**:
```bash
# Simulate high latency with tc (traffic control)
sudo tc qdisc add dev lo root netem delay 1000ms

# Then make API calls
curl -X POST http://localhost:5000/search ...
```

**Test Cases**:
- [ ] Requests timeout appropriately
- [ ] User sees "Search taking longer..."
- [ ] Can cancel search
- [ ] Result displayed when available

---

#### Scenario 5.3: Intermittent Connection Loss

**Setup**:
```bash
# Simulate packet loss
sudo tc qdisc add dev lo root netem loss 30%
```

**Test Cases**:
- [ ] Automatic retry on failure
- [ ] Exponential backoff
- [ ] User sees "Connection lost, retrying..."
- [ ] Max retry limit (don't retry forever)

---

### 6. Language-Specific Edge Cases

#### Scenario 6.1: Python Edge Cases

**Test Files**:
```python
# Unicode identifiers
Ω = 42
def μ(): pass

# Complex decorators
@decorator(arg=lambda x: x.y.z)
def func(): pass

# Async/await
async def async_func():
    await something()

# F-strings with expressions
f"Value: {obj.method().result}"

# Type hints
def func(x: Dict[str, List[Tuple]]) -> Optional[str]:
    pass
```

**Test Cases**:
- [ ] Unicode names extracted correctly
- [ ] Complex decorators don't break parsing
- [ ] Async functions detected
- [ ] F-strings parsed
- [ ] Complex type hints handled

---

#### Scenario 6.2: JavaScript Edge Cases

**Test Files**:
```javascript
// Arrow functions
const fn = () => doSomething()

// Classes
class MyClass { constructor() {} }

// Async/await
async function asyncFn() {
  await promise()
}

// Template literals
const str = `Value: ${obj.method()}`

// Destructuring
const {a, b: {c}} = obj
```

**Test Cases**:
- [ ] Arrow functions detected
- [ ] Class methods extracted
- [ ] Async functions identified
- [ ] Template literals handled
- [ ] Destructuring patterns don't cause issues

---

#### Scenario 6.3: Mixed Languages in One File

**Setup**: Create files that mix languages (e.g., JavaScript with embedded SQL)

**Test Cases**:
- [ ] Primary language detected correctly
- [ ] Embedded code not mistakenly parsed
- [ ] Result quality acceptable

---

### 7. Cache-Related Edge Cases

#### Scenario 7.1: Cache Invalidation

**Setup**:
```python
# Search for "function"
results1 = searcher.search("function")

# Modify index
searcher.index_workspace("/path")

# Search again - should get updated results
results2 = searcher.search("function")
```

**Test Cases**:
- [ ] Cache invalidated after index update
- [ ] Results reflect latest code
- [ ] No stale results

---

#### Scenario 7.2: Cache Eviction Under Load

**Setup**:
```python
# Generate 2000 unique queries (larger than cache size of 1000)
for i in range(2000):
    searcher.search(f"unique_query_{i}")
```

**Test Cases**:
- [ ] Cache doesn't grow unbounded
- [ ] LRU eviction works (old items removed)
- [ ] Memory stable at ~max_size
- [ ] No memory leak

---

### 8. RAG-Specific Edge Cases

#### Scenario 8.1: Self-RAG with No Good Results

**Setup**:
```python
# Query for something that doesn't exist
results = searcher.search("nonexistent_function_xyz_12345", use_rag=True)
```

**Test Cases**:
- [ ] Returns empty list (not crash)
- [ ] Handles gracefully
- [ ] No exception thrown

---

#### Scenario 8.2: Corrective RAG with Failing Alternatives

**Setup**:
```python
# Query that needs refinement
results = searcher.search(
    "how to handle very specific edge case",
    use_rag=True,
    strategy="corrective"
)
```

**Test Cases**:
- [ ] Generates alternatives
- [ ] Returns best results if alternatives fail
- [ ] Doesn't crash on alternative failure

---

#### Scenario 8.3: Adaptive RAG Strategy Selection

**Setup**:
```python
# Various query complexities
queries = [
    ("simple", "find function"),
    ("medium", "function that validates emails"),
    ("complex", "how do we handle authentication across multiple systems?")
]

for name, query in queries:
    results = searcher.search(query, use_rag=True, strategy="adaptive")
    print(f"{name}: {len(results)} results")
```

**Test Cases**:
- [ ] Correct strategy selected per complexity
- [ ] Results quality appropriate for query
- [ ] Latency matches expected for strategy

---

## Automated Test Suite

### Unit Tests (Already in place)

```bash
pytest tests/unit/ -v
```

### Integration Tests (Already in place)

```bash
pytest tests/integration/ -v
```

### Edge Case Tests (Recommended)

Create `tests/edge_cases/`:

```python
# test_large_workspace.py
def test_index_100k_files():
    """Test indexing very large workspace."""
    assert indexer.index_workspace("/tmp/large") is not None

# test_concurrent_searches.py
def test_10_concurrent_users():
    """Test concurrent searches from multiple users."""
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(searcher.search, query) for query in queries]
        results = [f.result() for f in futures]
    assert all(len(r) >= 0 for r in results)

# test_malformed_input.py
def test_special_chars_query():
    """Test special characters in queries."""
    results = searcher.search("@#$%^&*()")
    assert isinstance(results, list)  # Shouldn't crash

# test_memory_pressure.py
def test_low_memory_handling():
    """Test behavior under memory constraints."""
    # Would require memory limit setup
    pass
```

Run with:

```bash
pytest tests/edge_cases/ -v --timeout=300
```

---

## Stress Testing

### Load Test

```python
import locust

class SemanticSearchUser(HttpUser):
    @task
    def search(self):
        self.client.post("/search", json={
            "query": "test function",
            "limit": 10
        })
```

Run:
```bash
locust -f load_test.py --host=http://localhost:5000 --users=100 --spawn-rate=10
```

---

### Endurance Test

```python
import time

def endurance_test(duration_hours=24):
    """Run searches continuously for duration."""
    start = time.time()
    queries = ["test"] * 100

    while time.time() - start < duration_hours * 3600:
        for query in queries:
            searcher.search(query)
        time.sleep(0.1)
```

---

## Monitoring During Tests

```python
# Monitor memory
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.1f}MB")

# Monitor CPU
print(f"CPU: {process.cpu_percent(interval=1)}%")

# Monitor file descriptors
print(f"File descriptors: {len(process.open_files())}")

# Monitor exceptions
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Success Criteria

All edge cases should:

✅ **Not crash** - No unhandled exceptions
✅ **Not corrupt data** - Index remains consistent
✅ **Not leak memory** - Memory usage bounded
✅ **Not leak file descriptors** - Resource limits respected
✅ **Provide feedback** - User sees status/errors
✅ **Recover gracefully** - Continue functioning after error

---

## Known Limitations

### Documented Constraints

| Constraint | Limit | Impact |
|-----------|-------|--------|
| Files per workspace | 500K tested | Beyond untested |
| Query length | 10K characters | Longer may be truncated |
| Concurrent searches | 100+ safe | May degrade latency |
| Memory usage | 1-2GB typical | Varies with workspace |

### Workarounds

- **Very large workspaces**: Use `.semanticsearchignore` to exclude directories
- **Memory pressure**: Reduce cache size or use mock embeddings
- **Many users**: Run multiple backend instances with load balancing

---

## Test Execution Checklist

Before release, verify:

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] 5 large workspace tests successful
- [ ] 10-user concurrent test successful
- [ ] Memory usage stable after 1 hour
- [ ] No file descriptor leaks
- [ ] Special character queries handled
- [ ] Malformed files don't crash
- [ ] RAG strategies function correctly
- [ ] Error messages helpful
- [ ] Recovery from failures works
- [ ] Performance targets met

---

**Last Updated**: November 7, 2025
**Status**: Testing Plan Ready
