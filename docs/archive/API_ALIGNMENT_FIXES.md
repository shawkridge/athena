# API Alignment Fixes - Phase 7bc Test Suite

**Status**: ✅ Identified and Documented
**Priority**: HIGH (Blocking 11 tests)
**Estimated Effort**: 2-3 hours
**Owner**: Development Team

---

## Overview

The Phase 7bc test suite includes 256+ new tests. During execution, we identified 11 failing tests in the `WorkerPool` module that have API mismatches between the test expectations and the actual implementation.

**Summary**:
- ✅ 24 tests passing (68.6%)
- ❌ 11 tests failing (31.4%) - All due to API mismatches
- 🔧 All failures are fixable with API additions

---

## Failing Tests & Root Causes

### Group 1: Missing `num_workers` Property (3 tests)

**Tests Affected**:
1. `test_worker_pool_initialization` (line 191)
2. `test_load_balancer_adaptive_scaling` (line 358)
3. `test_worker_pool_with_min_equals_max` (line 442)
4. `test_worker_pool_single_worker` (line 456)

**Error**:
```
AttributeError: 'WorkerPool' object has no attribute 'num_workers'.
Did you mean: 'max_workers'?
```

**Root Cause**: Tests expect `num_workers` property but implementation has `active_workers`

**Fix**: Add property to `WorkerPool` class

```python
@property
def num_workers(self) -> int:
    """Get current number of active workers."""
    return self.active_workers
```

**Effort**: 5 minutes
**File**: `src/athena/optimization/worker_pool_executor.py`
**Lines**: After line 199 (after `self.active_workers = min_workers`)

---

### Group 2: Missing Health Status Method (2 tests)

**Tests Affected**:
1. `test_worker_pool_health_status` (line 326)
2. `test_worker_pool_handles_worker_failure` (line 417)

**Error**:
```
AttributeError: 'WorkerPool' object has no attribute 'get_health'
```

**Root Cause**: Tests expect `get_health()` method to return health status

**Fix**: Implement health status method

```python
def get_health(self) -> Dict[str, Any]:
    """Get health status of worker pool.

    Returns:
        Dictionary with health metrics:
        - active_workers: Number of currently active workers
        - total_tasks_submitted: Total tasks submitted
        - total_tasks_completed: Total tasks completed
        - total_tasks_failed: Total tasks that failed
        - avg_queue_depth: Average queue depth across workers
        - health_status: 'healthy', 'degraded', or 'unhealthy'
    """
    health_status = 'healthy'
    if self.total_tasks_failed > self.total_tasks_completed * 0.1:
        health_status = 'degraded'
    if self.total_tasks_failed > self.total_tasks_completed * 0.25:
        health_status = 'unhealthy'

    return {
        'active_workers': self.active_workers,
        'total_tasks_submitted': self.total_tasks_submitted,
        'total_tasks_completed': self.total_tasks_completed,
        'total_tasks_failed': self.total_tasks_failed,
        'task_success_rate': (
            self.total_tasks_completed / self.total_tasks_submitted
            if self.total_tasks_submitted > 0
            else 0.0
        ),
        'health_status': health_status,
    }
```

**Effort**: 20 minutes
**File**: `src/athena/optimization/worker_pool_executor.py`
**Lines**: After `get_worker_utilization()` method (or at end of class)

---

### Group 3: Missing Statistics Method (2 tests)

**Tests Affected**:
1. `test_worker_pool_statistics` (line 316)
2. `test_worker_utilization_tracking` (line 338)
3. `test_task_latency_tracking` (line 347)

**Error**:
```
AttributeError: 'WorkerPool' object has no attribute 'get_stats'
```

**Root Cause**: Tests expect `get_stats()` method to return performance statistics

**Fix**: Implement statistics method

```python
def get_stats(self) -> Dict[str, Any]:
    """Get performance statistics for the worker pool.

    Returns:
        Dictionary with performance metrics:
        - total_tasks_submitted: Total tasks submitted to pool
        - total_tasks_completed: Total tasks successfully completed
        - total_tasks_failed: Total tasks that failed
        - total_bytes_processed: Total bytes processed
        - active_workers: Current number of active workers
        - task_success_rate: Percentage of tasks completed successfully
    """
    return {
        'total_tasks_submitted': self.total_tasks_submitted,
        'total_tasks_completed': self.total_tasks_completed,
        'total_tasks_failed': self.total_tasks_failed,
        'total_bytes_processed': self.total_bytes_processed,
        'active_workers': self.active_workers,
        'task_success_rate': (
            (self.total_tasks_completed / self.total_tasks_submitted * 100)
            if self.total_tasks_submitted > 0
            else 0.0
        ),
    }
```

**Effort**: 15 minutes
**File**: `src/athena/optimization/worker_pool_executor.py`
**Lines**: After `get_health()` method

---

### Group 4: Async Context Manager Issues (3 tests)

**Tests Affected**:
1. `test_worker_pool_scales_up` (line 265)
2. `test_worker_pool_shutdown` (line 283)
3. Other async tests

**Error**:
```
TypeError: object async_generator can't be used in 'await' expression
```

**Root Cause**: Tests call `submit_task()` without `await` but implementation is async

**Issue**: The test fixtures use synchronous submission but implementation requires async

**Fix Strategy**:

**Option A**: Update tests to use async fixtures (Recommended)

```python
@pytest.fixture
async def worker_pool_async():
    """Create async worker pool fixture."""
    async with WorkerPool(min_workers=2, max_workers=8) as pool:
        yield pool
```

Then update tests:
```python
@pytest.mark.asyncio
async def test_worker_pool_scales_up(worker_pool_async):
    """Test worker pool scales up under load."""
    result = await worker_pool_async.submit_task(sample_task)
```

**Option B**: Add sync wrapper method to WorkerPool

```python
def submit_task_sync(self, task: WorkerTask, timeout_seconds: float = 30.0) -> WorkerTaskResult:
    """Synchronous wrapper for submit_task.

    For use in non-async contexts.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        self.submit_task(task, timeout_seconds)
    )
```

**Recommended**: Option A (better design)
**Effort**: 30 minutes
**Files**:
- `tests/unit/test_worker_pool_executor.py` (fixture updates)
- `src/athena/optimization/worker_pool_executor.py` (if Option B)

---

## Implementation Plan

### Phase 1: Quick Fixes (15 minutes)

1. Add `num_workers` property
   ```bash
   # Edit: src/athena/optimization/worker_pool_executor.py
   # Add property after line 199
   ```

2. Verify property works
   ```bash
   pytest tests/unit/test_worker_pool_executor.py::test_worker_pool_initialization -v
   ```

**Expected**: 4 tests pass

---

### Phase 2: Add Status Methods (35 minutes)

1. Implement `get_health()` method
   ```bash
   # Edit: src/athena/optimization/worker_pool_executor.py
   # Add method at end of class
   ```

2. Implement `get_stats()` method
   ```bash
   # Edit: src/athena/optimization/worker_pool_executor.py
   # Add method after get_health()
   ```

3. Verify methods work
   ```bash
   pytest tests/unit/test_worker_pool_executor.py -k "health or stats" -v
   ```

**Expected**: 5 more tests pass (total 9/35)

---

### Phase 3: Fix Async Issues (30 minutes)

1. Update test fixtures to use async
   ```bash
   # Edit: tests/unit/test_worker_pool_executor.py
   # Update worker_pool fixture to be async
   ```

2. Mark async tests with @pytest.mark.asyncio
   ```bash
   # Add decorator to async tests
   ```

3. Verify async tests pass
   ```bash
   pytest tests/unit/test_worker_pool_executor.py -k "scales_up or shutdown" -v
   ```

**Expected**: All remaining tests pass (total 35/35)

---

## Detailed Implementation Steps

### Step 1: Add `num_workers` Property

**File**: `src/athena/optimization/worker_pool_executor.py`
**Location**: After line 199 (self.active_workers = min_workers)

```python
@property
def num_workers(self) -> int:
    """Get current number of active workers.

    Returns:
        Current number of active worker processes.
    """
    return self.active_workers
```

**Verification**:
```bash
python -c "from athena.optimization.worker_pool_executor import WorkerPool; pool = WorkerPool(); print(pool.num_workers)"
# Should print: 2
```

### Step 2: Add `get_health()` Method

**File**: `src/athena/optimization/worker_pool_executor.py`
**Location**: After `shutdown()` method (end of class)

```python
def get_health(self) -> Dict[str, Any]:
    """Get health status of worker pool.

    Returns:
        Dictionary containing:
        - active_workers: Currently active worker count
        - total_tasks_submitted: Total tasks ever submitted
        - total_tasks_completed: Total tasks successfully completed
        - total_tasks_failed: Total tasks that failed
        - task_success_rate: Success rate percentage
        - health_status: 'healthy', 'degraded', or 'unhealthy'
    """
    if self.total_tasks_submitted == 0:
        success_rate = 100.0
    else:
        success_rate = (
            self.total_tasks_completed / self.total_tasks_submitted * 100
        )

    # Determine health status
    if success_rate >= 95:
        health_status = 'healthy'
    elif success_rate >= 80:
        health_status = 'degraded'
    else:
        health_status = 'unhealthy'

    return {
        'active_workers': self.active_workers,
        'min_workers': self.min_workers,
        'max_workers': self.max_workers,
        'total_tasks_submitted': self.total_tasks_submitted,
        'total_tasks_completed': self.total_tasks_completed,
        'total_tasks_failed': self.total_tasks_failed,
        'task_success_rate': success_rate,
        'health_status': health_status,
    }
```

### Step 3: Add `get_stats()` Method

**File**: `src/athena/optimization/worker_pool_executor.py`
**Location**: After `get_health()` method

```python
def get_stats(self) -> Dict[str, Any]:
    """Get performance statistics for the worker pool.

    Returns:
        Dictionary containing performance metrics:
        - total_tasks_submitted: Total tasks submitted
        - total_tasks_completed: Total tasks completed
        - total_tasks_failed: Total tasks failed
        - total_bytes_processed: Total bytes processed
        - active_workers: Current active worker count
        - task_success_rate: Success rate percentage
    """
    if self.total_tasks_submitted == 0:
        success_rate = 0.0
    else:
        success_rate = (
            self.total_tasks_completed / self.total_tasks_submitted * 100
        )

    return {
        'total_tasks_submitted': self.total_tasks_submitted,
        'total_tasks_completed': self.total_tasks_completed,
        'total_tasks_failed': self.total_tasks_failed,
        'total_bytes_processed': self.total_bytes_processed,
        'active_workers': self.active_workers,
        'task_success_rate': success_rate,
        'queue_size': self.task_queue_size if self.task_queue else 0,
    }
```

### Step 4: Update Test Fixtures for Async

**File**: `tests/unit/test_worker_pool_executor.py`
**Location**: Around line 31

Replace synchronous fixture:
```python
# Before:
@pytest.fixture
def worker_pool():
    """Create a fresh worker pool executor."""
    return WorkerPool(min_workers=2, max_workers=8)
```

With async version:
```python
# After:
@pytest.fixture
async def worker_pool_async():
    """Create async worker pool for testing."""
    pool = WorkerPool(min_workers=2, max_workers=8)
    await pool._initialize()
    yield pool
    await pool.shutdown()

@pytest.fixture
def worker_pool():
    """Create synchronous worker pool (non-async tests)."""
    return WorkerPool(min_workers=2, max_workers=8)
```

### Step 5: Mark Async Tests

**File**: `tests/unit/test_worker_pool_executor.py`
**Location**: Tests that use `worker_pool_async` fixture

```python
@pytest.mark.asyncio
async def test_worker_pool_scales_up(worker_pool_async):
    """Test worker pool scales up under load."""
    # Implementation
```

---

## Verification Checklist

After implementing each step, verify:

### After Step 1 (num_workers property)
- [ ] Property exists and returns correct value
- [ ] `test_worker_pool_initialization` passes
- [ ] `test_load_balancer_adaptive_scaling` passes
- [ ] `test_worker_pool_with_min_equals_max` passes
- [ ] `test_worker_pool_single_worker` passes

### After Step 2 (get_health method)
- [ ] Method returns dict with expected keys
- [ ] `test_worker_pool_health_status` passes
- [ ] `test_worker_pool_handles_worker_failure` passes

### After Step 3 (get_stats method)
- [ ] Method returns dict with expected keys
- [ ] `test_worker_pool_statistics` passes
- [ ] `test_worker_utilization_tracking` passes
- [ ] `test_task_latency_tracking` passes

### After Step 4-5 (async fixtures)
- [ ] Async tests have @pytest.mark.asyncio decorator
- [ ] `test_worker_pool_scales_up` passes
- [ ] `test_worker_pool_shutdown` passes

---

## Testing Commands

```bash
# Run individual failing tests
pytest tests/unit/test_worker_pool_executor.py::test_worker_pool_initialization -v

# Run all worker pool tests
pytest tests/unit/test_worker_pool_executor.py -v

# Run only failing tests
pytest tests/unit/test_worker_pool_executor.py::test_worker_pool_initialization \
        tests/unit/test_worker_pool_executor.py::test_worker_pool_health_status \
        tests/unit/test_worker_pool_executor.py::test_worker_pool_statistics -v

# Run with detailed output
pytest tests/unit/test_worker_pool_executor.py -v --tb=long

# Run without stopping on first failure
pytest tests/unit/test_worker_pool_executor.py -v --tb=short --no-header
```

---

## Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| All imports work | 0 errors | ✅ |
| num_workers property | 1 property | ⏳ |
| get_health() method | Returns dict | ⏳ |
| get_stats() method | Returns dict | ⏳ |
| Async fixtures | Properly marked | ⏳ |
| All 35 tests pass | 35/35 | ⏳ |

---

## Timeline

| Phase | Task | Duration | Cumulative |
|-------|------|----------|-----------|
| 1 | Add num_workers property | 15 min | 15 min |
| 2a | Implement get_health() | 20 min | 35 min |
| 2b | Implement get_stats() | 15 min | 50 min |
| 3 | Update async fixtures | 30 min | 80 min |
| 4 | Verify all tests | 20 min | **100 min** |

**Total Time**: ~1.5-2 hours

---

## Notes

- All changes are backward compatible
- Properties and methods don't break existing code
- Test fixtures are isolated per test
- Async handling uses standard pytest-asyncio patterns

---

**Last Updated**: November 12, 2025
**Next Review**: After implementation complete
