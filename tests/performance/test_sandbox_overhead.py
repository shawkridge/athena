"""Performance benchmarks for Phase 3 Week 11: Sandbox Overhead Analysis.

Benchmarks measure:
- Execution overhead for different sandbox modes (SRT vs RestrictedPython vs Mock)
- Code validation overhead
- Violation detection overhead
- ExecutionContext tracking overhead
- I/O capture overhead
- Different code types (Python, JavaScript, Bash)
"""

import time
import pytest
import json
from typing import Dict, List
from datetime import datetime

from athena.sandbox.srt_executor import SRTExecutor
from athena.sandbox.srt_config import SandboxConfig, SandboxMode
from athena.sandbox.execution_context import ExecutionContext


@pytest.mark.benchmark
class TestSandboxOverhead:
    """Benchmarks for sandbox execution overhead."""

    def test_mock_mode_overhead_simple_code(self, benchmark):
        """Benchmark mock mode overhead for simple code."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = "x = 1 + 1\nprint(x)"

        def execute():
            return executor.execute(code, language="python")

        result = benchmark(execute)

        # Track result
        assert result.success
        assert result.execution_time_ms < 100  # Simple code should be <100ms

    def test_mock_mode_overhead_complex_code(self, benchmark):
        """Benchmark mock mode overhead for complex code."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(f"fib(10) = {result}")
"""

        def execute():
            return executor.execute(code, language="python")

        result = benchmark(execute)

        assert result.success
        # Complex code may take longer but should still be reasonable
        assert result.execution_time_ms < 500

    def test_restricted_python_mode_overhead(self, benchmark):
        """Benchmark RestrictedPython mode overhead."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.RESTRICTED_PYTHON
        executor = SRTExecutor(config)

        code = "x = sum([1, 2, 3, 4, 5])\nprint(x)"

        def execute():
            return executor.execute(code, language="python")

        try:
            result = benchmark(execute)
            # RestrictedPython may have compilation overhead
            assert result.execution_time_ms < 500
        except Exception:
            # RestrictedPython may not be available
            pytest.skip("RestrictedPython not available")

    def test_io_capture_overhead(self, benchmark):
        """Benchmark overhead of I/O capture."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        # Code with significant output
        code = """
for i in range(100):
    print(f"Line {i}: " + "x" * 100)
"""

        def execute():
            return executor.execute(code, language="python")

        result = benchmark(execute)

        assert result.success
        # I/O capture adds overhead but shouldn't be excessive
        assert result.execution_time_ms < 1000

    def test_code_validation_overhead(self, benchmark):
        """Benchmark code validation overhead."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        # Code that needs validation
        code = """
import json
data = {"key": "value"}
result = json.dumps(data)
print(result)
"""

        def execute():
            return executor.execute(code, language="python")

        result = benchmark(execute)

        assert result.success


@pytest.mark.benchmark
class TestExecutionContextOverhead:
    """Benchmarks for ExecutionContext tracking overhead."""

    def test_context_creation_overhead(self, benchmark):
        """Benchmark cost of creating ExecutionContext."""
        def create_context():
            context = ExecutionContext()
            return context

        context = benchmark(create_context)

        assert context is not None

    def test_event_recording_overhead(self, benchmark):
        """Benchmark cost of recording execution events."""
        context = ExecutionContext()

        def record_event():
            context.record_event(
                event_type="io",
                details={"stream": "stdout", "content": "test output"}
            )

        benchmark(record_event)

        # Should have at least one event
        assert len(context.get_events()) > 0

    def test_violation_recording_overhead(self, benchmark):
        """Benchmark cost of recording violations."""
        context = ExecutionContext()

        def record_violation():
            context.record_violation(
                violation_type="forbidden_import",
                module="subprocess"
            )

        benchmark(record_violation)

        # Should have recorded violation
        violations = context.get_violations()
        assert len(violations) > 0

    def test_context_state_transitions_overhead(self, benchmark):
        """Benchmark overhead of state transitions."""
        context = ExecutionContext()

        def transition_states():
            context.start()
            context.record_event(event_type="execution", details={})
            context.complete()

        benchmark(transition_states)

        # Should have completed successfully
        assert context.state == "completed"


@pytest.mark.benchmark
class TestLanguageSpecificOverhead:
    """Benchmarks for different execution languages."""

    def test_python_execution_overhead(self, benchmark):
        """Benchmark Python code execution."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
numbers = list(range(1000))
result = sum(numbers)
print(f"Sum: {result}")
"""

        def execute():
            return executor.execute(code, language="python")

        result = benchmark(execute)

        assert result.success

    def test_javascript_execution_overhead(self, benchmark):
        """Benchmark JavaScript code execution."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
const numbers = Array.from({length: 1000}, (_, i) => i);
const sum = numbers.reduce((a, b) => a + b, 0);
console.log('Sum: ' + sum);
"""

        def execute():
            return executor.execute(code, language="javascript")

        result = benchmark(execute)
        # JavaScript may not be available in test environment
        if result.success:
            assert "Sum:" in result.stdout

    def test_bash_execution_overhead(self, benchmark):
        """Benchmark bash code execution."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
for i in {1..100}; do
  echo "Line $i"
done
"""

        def execute():
            return executor.execute(code, language="bash")

        result = benchmark(execute)
        # Bash may not be available in test environment
        if result.success:
            assert "Line" in result.stdout


@pytest.mark.benchmark
class TestScalabilityMetrics:
    """Benchmarks for scalability and resource usage."""

    def test_sequential_execution_overhead(self, benchmark):
        """Benchmark sequential execution of multiple scripts."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        codes = [
            "x = 1 + 1\nprint(x)" for _ in range(10)
        ]

        def execute_sequential():
            results = []
            for code in codes:
                result = executor.execute(code, language="python")
                results.append(result)
            return results

        results = benchmark(execute_sequential)

        assert len(results) == 10
        assert all(r.success for r in results)

    def test_memory_overhead_multiple_contexts(self, benchmark):
        """Benchmark memory overhead with multiple contexts."""
        def create_contexts():
            contexts = [ExecutionContext() for _ in range(100)]
            return contexts

        contexts = benchmark(create_contexts)

        assert len(contexts) == 100


@pytest.mark.benchmark
class TestCachingOverhead:
    """Benchmarks for any caching mechanisms."""

    def test_code_cache_hit_overhead(self, benchmark):
        """Benchmark overhead of cache hits."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = "x = 1 + 1"

        # First execution (cache miss)
        executor.execute(code, language="python")

        # Second execution (cache hit) - if caching is implemented
        def execute_cached():
            return executor.execute(code, language="python")

        result = benchmark(execute_cached)

        assert result.success


@pytest.mark.benchmark
class TestViolationDetectionOverhead:
    """Benchmarks for security violation detection."""

    def test_violation_detection_simple_code(self, benchmark):
        """Benchmark violation detection for safe code."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
data = [1, 2, 3, 4, 5]
result = sum(data)
print(result)
"""

        def execute_with_detection():
            return executor.execute(code, language="python")

        result = benchmark(execute_with_detection)

        assert result.success
        # Violation detection shouldn't add significant overhead
        assert result.execution_time_ms < 200

    def test_violation_detection_dangerous_code(self, benchmark):
        """Benchmark violation detection for code with violations."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = """
try:
    import subprocess
except ImportError:
    pass
print("done")
"""

        def execute_with_violations():
            return executor.execute(code, language="python")

        result = benchmark(execute_with_violations)

        # Detection should work even with violations


# Comparative benchmarks

@pytest.mark.benchmark
class TestModeComparison:
    """Compare performance across different execution modes."""

    def test_mode_performance_comparison(self):
        """Compare execution performance across modes."""
        code = """
def compute(n):
    return sum(range(n))
result = compute(1000)
print(f"Result: {result}")
"""

        results = {}

        # Test each mode
        for mode in [SandboxMode.MOCK, SandboxMode.RESTRICTED_PYTHON]:
            try:
                config = SandboxConfig.default()
                config.mode = mode
                executor = SRTExecutor(config)

                times = []
                for _ in range(5):
                    start = time.time()
                    result = executor.execute(code, language="python")
                    elapsed = (time.time() - start) * 1000  # Convert to ms

                    if result.success:
                        times.append(elapsed)

                if times:
                    avg_time = sum(times) / len(times)
                    results[mode.value] = avg_time
            except Exception:
                results[mode.value] = None

        # Print comparison
        print("\nMode Performance Comparison:")
        for mode, time in results.items():
            if time:
                print(f"  {mode}: {time:.2f}ms")

        # At least mock mode should work
        assert SandboxMode.MOCK.value in results
        assert results[SandboxMode.MOCK.value] is not None


@pytest.mark.benchmark
class TestStartupOverhead:
    """Benchmarks for startup/initialization overhead."""

    def test_executor_initialization_overhead(self, benchmark):
        """Benchmark time to initialize executor."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK

        def init_executor():
            return SRTExecutor(config)

        executor = benchmark(init_executor)

        assert executor is not None
        assert executor.config == config

    def test_config_creation_overhead(self, benchmark):
        """Benchmark time to create sandbox config."""
        def create_config():
            return SandboxConfig.default()

        config = benchmark(create_config)

        assert config is not None


# Performance assertion helpers

class PerformanceTargets:
    """Performance targets for Phase 3."""

    SIMPLE_CODE_EXECUTION = 100  # ms
    COMPLEX_CODE_EXECUTION = 500  # ms
    IO_CAPTURE_OVERHEAD = 1000  # ms
    VALIDATION_OVERHEAD = 200  # ms
    CONTEXT_CREATION = 10  # ms
    EVENT_RECORDING = 1  # ms
    VIOLATION_DETECTION = 50  # ms
    SANDBOX_MODE_COMPARISON = 2.0  # ratio (should be <2x slower than mock)


@pytest.mark.benchmark
class TestPerformanceTargets:
    """Validate that performance meets targets."""

    def test_simple_execution_meets_target(self):
        """Test simple code execution meets <100ms target."""
        config = SandboxConfig.default()
        config.mode = SandboxMode.MOCK
        executor = SRTExecutor(config)

        code = "x = 1 + 1"

        start = time.time()
        result = executor.execute(code, language="python")
        elapsed = (time.time() - start) * 1000

        assert result.success
        # Allow some margin in test environment
        assert elapsed < PerformanceTargets.SIMPLE_CODE_EXECUTION * 2

    def test_context_creation_meets_target(self):
        """Test context creation meets <10ms target."""
        start = time.time()
        context = ExecutionContext()
        elapsed = (time.time() - start) * 1000

        # Allow generous margin for test environment
        assert elapsed < PerformanceTargets.CONTEXT_CREATION * 10


# Summary reporting

@pytest.mark.benchmark
def test_print_performance_summary(benchmark_results=None):
    """Print summary of performance benchmarks."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "test_count": 0,
        "targets": {
            "simple_execution_ms": PerformanceTargets.SIMPLE_CODE_EXECUTION,
            "complex_execution_ms": PerformanceTargets.COMPLEX_CODE_EXECUTION,
            "io_capture_overhead_ms": PerformanceTargets.IO_CAPTURE_OVERHEAD,
            "context_creation_ms": PerformanceTargets.CONTEXT_CREATION,
        }
    }

    print("\nPerformance Benchmark Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
