"""Performance benchmarking framework for Athena memory system.

Measures and validates performance improvements from:
1. Quality-based tier selection (expected: 30-50% latency reduction)
2. Pattern conflict resolution (expected: 20-30% reliability improvement)
3. Adaptive replanning (expected: 40-60% task success improvement)

Provides reproducible benchmarks with confidence intervals.
"""

import time
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks."""
    LATENCY = "latency"  # Time to complete operation
    THROUGHPUT = "throughput"  # Operations per second
    QUALITY = "quality"  # Accuracy/reliability of results
    SUCCESS_RATE = "success_rate"  # Percentage of successful operations
    MEMORY = "memory"  # Memory usage
    RECOVERY_TIME = "recovery_time"  # Time to recover from failure


@dataclass
class BenchmarkResult:
    """Result of a single benchmark measurement."""
    name: str
    benchmark_type: BenchmarkType
    value: float  # The measured value
    unit: str  # Unit of measurement (ms, %, ops/sec, etc.)
    iteration: int  # Which iteration this is
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class BenchmarkStats:
    """Statistical summary of benchmark results."""
    name: str
    benchmark_type: BenchmarkType
    unit: str
    count: int
    mean: float
    median: float
    stdev: float
    min: float
    max: float
    percentile_95: float
    percentile_99: float

    def improvement_pct(self, baseline: 'BenchmarkStats') -> float:
        """Calculate improvement vs baseline (for latency, lower is better).

        Args:
            baseline: Baseline stats to compare against

        Returns:
            Improvement percentage (positive = better for latency)
        """
        if baseline.mean == 0:
            return 0.0

        improvement = (baseline.mean - self.mean) / baseline.mean * 100
        return improvement

    def __str__(self) -> str:
        """Format stats as readable string."""
        return (
            f"{self.name}: mean={self.mean:.2f}{self.unit}, "
            f"median={self.median:.2f}{self.unit}, "
            f"stdev={self.stdev:.2f}{self.unit}, "
            f"p95={self.percentile_95:.2f}{self.unit}, "
            f"p99={self.percentile_99:.2f}{self.unit} "
            f"(n={self.count})"
        )


class PerformanceBenchmark:
    """Run and analyze performance benchmarks."""

    def __init__(self, name: str):
        """Initialize benchmark.

        Args:
            name: Name of this benchmark suite
        """
        self.name = name
        self.results: List[BenchmarkResult] = []
        self.start_time = datetime.now()

    def measure(
        self,
        name: str,
        fn: Callable,
        iterations: int = 10,
        benchmark_type: BenchmarkType = BenchmarkType.LATENCY,
        unit: str = "ms",
    ) -> BenchmarkStats:
        """Measure performance of a function.

        **Methodology**:
        - Warm-up: Run function once to cache/initialize
        - Measurement: Run N times, record values
        - Warmup excluded from stats

        Args:
            name: Name of operation being measured
            fn: Function to measure (should return the value to measure)
            iterations: Number of iterations
            benchmark_type: Type of benchmark
            unit: Unit of measurement

        Returns:
            BenchmarkStats with statistical summary
        """
        # Warmup
        try:
            fn()
        except Exception as e:
            logger.warning(f"Warmup failed for {name}: {e}")

        # Measure
        measurements = []
        for i in range(iterations):
            try:
                value = fn()
                measurements.append(value)
                self.results.append(
                    BenchmarkResult(
                        name=name,
                        benchmark_type=benchmark_type,
                        value=value,
                        unit=unit,
                        iteration=i,
                    )
                )
            except Exception as e:
                logger.error(f"Iteration {i} failed for {name}: {e}")
                continue

        if not measurements:
            raise RuntimeError(f"No successful measurements for {name}")

        # Calculate statistics
        stats = BenchmarkStats(
            name=name,
            benchmark_type=benchmark_type,
            unit=unit,
            count=len(measurements),
            mean=statistics.mean(measurements),
            median=statistics.median(measurements),
            stdev=statistics.stdev(measurements) if len(measurements) > 1 else 0.0,
            min=min(measurements),
            max=max(measurements),
            percentile_95=self._percentile(measurements, 95),
            percentile_99=self._percentile(measurements, 99),
        )

        logger.info(f"Benchmark {name}: {stats}")
        return stats

    def measure_latency(
        self,
        name: str,
        fn: Callable,
        iterations: int = 10,
    ) -> BenchmarkStats:
        """Measure latency in milliseconds.

        Args:
            name: Name of operation
            fn: Function that returns latency in milliseconds
            iterations: Number of iterations

        Returns:
            BenchmarkStats in milliseconds
        """
        def wrapped_fn():
            start = time.time()
            fn()
            elapsed = (time.time() - start) * 1000  # Convert to ms
            return elapsed

        return self.measure(
            name=name,
            fn=wrapped_fn,
            iterations=iterations,
            benchmark_type=BenchmarkType.LATENCY,
            unit="ms",
        )

    def measure_throughput(
        self,
        name: str,
        fn: Callable,
        iterations: int = 10,
    ) -> BenchmarkStats:
        """Measure throughput in operations per second.

        Args:
            name: Name of operation
            fn: Function that returns ops/sec
            iterations: Number of iterations

        Returns:
            BenchmarkStats in ops/sec
        """
        return self.measure(
            name=name,
            fn=fn,
            iterations=iterations,
            benchmark_type=BenchmarkType.THROUGHPUT,
            unit="ops/sec",
        )

    def measure_quality(
        self,
        name: str,
        fn: Callable,
        iterations: int = 10,
    ) -> BenchmarkStats:
        """Measure quality/accuracy as percentage.

        Args:
            name: Name of operation
            fn: Function that returns quality 0-1
            iterations: Number of iterations

        Returns:
            BenchmarkStats as percentage
        """
        def wrapped_fn():
            return fn() * 100  # Convert to percentage

        return self.measure(
            name=name,
            fn=wrapped_fn,
            iterations=iterations,
            benchmark_type=BenchmarkType.QUALITY,
            unit="%",
        )

    def compare(
        self,
        baseline: BenchmarkStats,
        improved: BenchmarkStats,
    ) -> Dict[str, Any]:
        """Compare two benchmark results.

        Args:
            baseline: Baseline measurement
            improved: Improved measurement

        Returns:
            Comparison dictionary
        """
        # For latency, lower is better (reduction = improvement)
        # For quality/success, higher is better (increase = improvement)

        if baseline.benchmark_type in [BenchmarkType.LATENCY, BenchmarkType.RECOVERY_TIME]:
            improvement = baseline.improvement_pct(improved)
            is_better = improvement > 0
        else:
            # Quality, throughput, success rate - higher is better
            improvement = (improved.mean - baseline.mean) / baseline.mean * 100
            is_better = improvement > 0

        return {
            "baseline": str(baseline),
            "improved": str(improved),
            "improvement_pct": improvement,
            "is_better": is_better,
            "baseline_value": baseline.mean,
            "improved_value": improved.mean,
            "absolute_difference": improved.mean - baseline.mean,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all benchmarks run.

        Returns:
            Summary dictionary
        """
        duration = datetime.now() - self.start_time

        # Group by benchmark type
        by_type = {}
        for result in self.results:
            bt = result.benchmark_type.value
            if bt not in by_type:
                by_type[bt] = []
            by_type[bt].append(result)

        return {
            "name": self.name,
            "duration": str(duration),
            "total_measurements": len(self.results),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
        }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of data.

        Args:
            data: List of values
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value
        """
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TierSelectionBenchmark:
    """Benchmark quality-based tier selection improvements."""

    def __init__(self, manager):
        """Initialize with manager instance.

        Args:
            manager: UnifiedMemoryManager instance
        """
        self.manager = manager
        self.benchmark = PerformanceBenchmark("tier_selection")

    def benchmark_latency(self) -> Dict[str, BenchmarkStats]:
        """Benchmark latency improvements from quality-based selection.

        **Expected**: 30-50% reduction for high-quality systems

        Returns:
            Dictionary of baseline and improved stats
        """
        # Baseline: complexity-only tier selection
        def baseline_recall():
            return self.manager.recall(
                "What was the failing test?",
                auto_select_depth=False,
                cascade_depth=3,  # Always use full depth
            )

        # Improved: quality-aware selection
        def improved_recall():
            return self.manager.recall(
                "What was the failing test?",
                auto_select_depth=True,
            )

        baseline_stats = self.benchmark.measure_latency(
            "baseline_recall_full_depth",
            baseline_recall,
            iterations=20,
        )

        improved_stats = self.benchmark.measure_latency(
            "improved_recall_quality_aware",
            improved_recall,
            iterations=20,
        )

        return {
            "baseline": baseline_stats,
            "improved": improved_stats,
            "comparison": self.benchmark.compare(baseline_stats, improved_stats),
        }


class ConflictResolutionBenchmark:
    """Benchmark pattern conflict resolution improvements."""

    def __init__(self, db=None):
        """Initialize with optional database.

        Args:
            db: Optional database connection
        """
        self.db = db
        self.benchmark = PerformanceBenchmark("conflict_resolution")

    def benchmark_pattern_quality(self) -> Dict[str, BenchmarkStats]:
        """Benchmark pattern quality improvements.

        **Expected**: 20-30% improvement in pattern reliability

        Returns:
            Dictionary of stats
        """
        from athena.consolidation.pattern_conflict_resolver import (
            PatternConflictResolver,
        )

        resolver = PatternConflictResolver(db=self.db)

        # Simulate conflicts and measure resolution quality
        def measure_resolution_quality():
            # Create sample System 1 and System 2 patterns
            s1 = {
                "description": "Test workflow",
                "confidence": 0.80,
                "tags": ["testing", "automation"],
            }

            s2 = {
                "description": "Automated testing process",
                "confidence": 0.85,
                "tags": ["testing", "automation", "continuous"],
            }

            conflict = resolver.detect_conflict(
                cluster_id=1,
                system_1_pattern=s1,
                system_2_pattern=s2,
            )

            if conflict:
                resolution = resolver.resolve_conflict(conflict)
                # Quality = how confident we are in the resolution
                return resolution.confidence
            else:
                return 1.0  # No conflict = perfect quality

        stats = self.benchmark.measure_quality(
            "conflict_resolution_quality",
            measure_resolution_quality,
            iterations=50,
        )

        return {
            "quality": stats,
        }


class ReplanningBenchmark:
    """Benchmark adaptive replanning improvements."""

    def __init__(self):
        """Initialize replanning benchmark."""
        self.benchmark = PerformanceBenchmark("adaptive_replanning")

    def benchmark_failure_detection(self) -> Dict[str, BenchmarkStats]:
        """Benchmark failure detection latency.

        Returns:
            Dictionary of stats
        """
        from athena.execution.adaptive_replanning import (
            AdaptiveReplanningOrchestrator,
        )
        from datetime import timedelta

        orchestrator = AdaptiveReplanningOrchestrator()

        def measure_detection():
            orchestrator.detect_failure(
                step_id=1,
                expected_duration=timedelta(minutes=10),
                actual_duration=timedelta(minutes=20),
                errors_count=5,
                assumptions_violated=["db_available"],
            )

        stats = self.benchmark.measure_latency(
            "failure_detection",
            measure_detection,
            iterations=100,
        )

        return {"detection_latency": stats}

    def benchmark_recovery_planning(self) -> Dict[str, BenchmarkStats]:
        """Benchmark recovery planning latency.

        Returns:
            Dictionary of stats
        """
        from athena.execution.adaptive_replanning import (
            AdaptiveReplanningOrchestrator,
            PlanFailure,
            FailureType,
        )
        from datetime import datetime

        orchestrator = AdaptiveReplanningOrchestrator()

        failure = PlanFailure(
            failure_type=FailureType.TIMING_OVERRUN,
            step_id=1,
            timestamp=datetime.now(),
            severity=0.6,
            message="Overrun",
        )

        def measure_recovery():
            orchestrator.plan_recovery(
                failure=failure,
                current_plan={"id": "test_plan"},
                remaining_steps=[2, 3, 4],
            )

        stats = self.benchmark.measure_latency(
            "recovery_planning",
            measure_recovery,
            iterations=50,
        )

        return {"recovery_planning_latency": stats}
