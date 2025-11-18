"""Pipeline Instrumentation - Track consolidation pipeline performance and throughput.

Monitors each stage of the consolidation pipeline:
1. Clustering - Group episodic events
2. Dual-Process Extraction - Extract patterns via System 1/2
3. Validation - Validate patterns and detect hallucinations
4. Storage - Store consolidated patterns

Metrics tracked:
- Stage duration (seconds)
- Pattern count transitions
- Throughput (patterns/second)
- Stage-level breakdown (percentage of total time)
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from typing import Dict, List, Optional


@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""

    stage_name: str
    execution_count: int = 0
    total_duration_seconds: float = 0.0
    durations: List[float] = field(default_factory=list)

    @property
    def avg_duration(self) -> float:
        """Average duration for this stage."""
        return (
            self.total_duration_seconds / self.execution_count if self.execution_count > 0 else 0.0
        )

    @property
    def min_duration(self) -> float:
        """Minimum duration for this stage."""
        return min(self.durations) if self.durations else 0.0

    @property
    def max_duration(self) -> float:
        """Maximum duration for this stage."""
        return max(self.durations) if self.durations else 0.0

    @property
    def stdev_duration(self) -> float:
        """Standard deviation of durations."""
        return stdev(self.durations) if len(self.durations) > 1 else 0.0


class PipelineInstrumentation:
    """Track consolidation pipeline performance metrics.

    This class instruments the consolidation pipeline to measure:
    - How long each stage takes
    - How many patterns flow through each stage
    - Overall throughput and bottlenecks
    """

    def __init__(self):
        """Initialize pipeline instrumentation."""
        self.stage_metrics: Dict[str, StageMetrics] = {}
        self.consolidation_runs: List[Dict] = []
        self.current_run: Optional[Dict] = None

    def start_consolidation_run(self, session_id: str, run_id: Optional[int] = None):
        """Start tracking a new consolidation run.

        Args:
            session_id: Session being consolidated
            run_id: Optional consolidation run ID
        """
        self.current_run = {
            "session_id": session_id,
            "run_id": run_id,
            "started_at": datetime.now(),
            "completed_at": None,
            "stage_durations": {},
            "pattern_counts": {
                "input_events": 0,
                "clustered_groups": 0,
                "patterns_extracted": 0,
                "patterns_validated": 0,
                "patterns_stored": 0,
            },
        }

    def end_consolidation_run(self):
        """End tracking current consolidation run."""
        if self.current_run:
            self.current_run["completed_at"] = datetime.now()
            self.consolidation_runs.append(self.current_run)
            self.current_run = None

    @contextmanager
    def time_stage(self, stage_name: str):
        """Context manager to time a pipeline stage.

        Usage:
            with instrumentation.time_stage('clustering'):
                # Do clustering work
                pass

        Args:
            stage_name: Name of pipeline stage

        Yields:
            None
        """
        if stage_name not in self.stage_metrics:
            self.stage_metrics[stage_name] = StageMetrics(stage_name)

        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            metrics = self.stage_metrics[stage_name]

            # Update stage metrics
            metrics.execution_count += 1
            metrics.total_duration_seconds += duration
            metrics.durations.append(duration)

            # Update current run if active
            if self.current_run:
                self.current_run["stage_durations"][stage_name] = duration

    def record_stage(self, stage_name: str, duration_seconds: float):
        """Manually record a stage duration.

        Args:
            stage_name: Name of pipeline stage
            duration_seconds: Duration in seconds
        """
        if stage_name not in self.stage_metrics:
            self.stage_metrics[stage_name] = StageMetrics(stage_name)

        metrics = self.stage_metrics[stage_name]
        metrics.execution_count += 1
        metrics.total_duration_seconds += duration_seconds
        metrics.durations.append(duration_seconds)

        if self.current_run:
            self.current_run["stage_durations"][stage_name] = duration_seconds

    def record_pattern_count(self, stage_name: str, count: int):
        """Record number of patterns at a stage.

        Args:
            stage_name: Stage identifier (e.g., 'input', 'extracted', 'validated')
            count: Number of patterns
        """
        if self.current_run:
            key = f"{stage_name}_count"
            if key not in self.current_run["pattern_counts"]:
                self.current_run["pattern_counts"][key] = 0
            self.current_run["pattern_counts"][key] = count

    def calculate_throughput(self) -> float:
        """Calculate patterns extracted per second.

        Returns:
            Patterns per second (higher is better)
        """
        if not self.consolidation_runs:
            return 0.0

        # Use most recent consolidation run
        last_run = self.consolidation_runs[-1]
        total_duration = (last_run["completed_at"] - last_run["started_at"]).total_seconds()

        patterns_extracted = last_run["pattern_counts"].get("patterns_extracted", 0)

        if total_duration <= 0:
            return 0.0

        return patterns_extracted / total_duration

    def calculate_avg_throughput(self) -> float:
        """Calculate average throughput across all runs.

        Returns:
            Average patterns per second
        """
        if not self.consolidation_runs:
            return 0.0

        throughputs = []
        for run in self.consolidation_runs:
            total_duration = (run["completed_at"] - run["started_at"]).total_seconds()
            patterns_extracted = run["pattern_counts"].get("patterns_extracted", 0)

            if total_duration > 0:
                throughputs.append(patterns_extracted / total_duration)

        return mean(throughputs) if throughputs else 0.0

    def get_stage_breakdown(self) -> Dict[str, float]:
        """Get percentage breakdown of time by stage.

        Returns:
            Dict mapping stage_name -> percentage of total time
        """
        if not self.stage_metrics:
            return {}

        total_time = sum(m.total_duration_seconds for m in self.stage_metrics.values())
        if total_time <= 0:
            return {}

        return {
            stage: (metrics.total_duration_seconds / total_time * 100)
            for stage, metrics in self.stage_metrics.items()
        }

    def get_stage_stats(self) -> Dict[str, Dict]:
        """Get detailed statistics for each stage.

        Returns:
            Dict mapping stage_name -> stats dict
        """
        stats = {}
        for stage_name, metrics in self.stage_metrics.items():
            stats[stage_name] = {
                "execution_count": metrics.execution_count,
                "total_duration_seconds": metrics.total_duration_seconds,
                "avg_duration_seconds": metrics.avg_duration,
                "min_duration_seconds": metrics.min_duration,
                "max_duration_seconds": metrics.max_duration,
                "stdev_duration_seconds": metrics.stdev_duration,
            }
        return stats

    def get_pipeline_summary(self) -> Dict:
        """Get summary statistics for the entire pipeline.

        Returns:
            Dict with overall pipeline metrics
        """
        if not self.consolidation_runs:
            return {
                "total_runs": 0,
                "avg_throughput_patterns_per_sec": 0.0,
                "total_time_seconds": 0.0,
                "total_patterns_extracted": 0,
            }

        total_runs = len(self.consolidation_runs)
        total_patterns = sum(
            run["pattern_counts"].get("patterns_extracted", 0) for run in self.consolidation_runs
        )
        total_time = sum(
            (run["completed_at"] - run["started_at"]).total_seconds()
            for run in self.consolidation_runs
            if run["completed_at"]
        )

        return {
            "total_runs": total_runs,
            "avg_throughput_patterns_per_sec": (
                total_patterns / total_time if total_time > 0 else 0.0
            ),
            "total_time_seconds": total_time,
            "total_patterns_extracted": total_patterns,
            "avg_patterns_per_run": total_patterns / total_runs if total_runs > 0 else 0.0,
            "stage_breakdown": self.get_stage_breakdown(),
            "stage_stats": self.get_stage_stats(),
        }

    def get_bottlenecks(self) -> List[Dict]:
        """Identify pipeline bottlenecks.

        Returns:
            List of bottleneck stages, sorted by impact (descending)
        """
        breakdown = self.get_stage_breakdown()
        stats = self.get_stage_stats()

        bottlenecks = []
        for stage_name, percentage in breakdown.items():
            if percentage >= 20:  # Stages taking >20% are potential bottlenecks
                bottlenecks.append(
                    {
                        "stage": stage_name,
                        "percentage": percentage,
                        "avg_duration": stats[stage_name]["avg_duration_seconds"],
                        "execution_count": stats[stage_name]["execution_count"],
                    }
                )

        # Sort by percentage descending
        bottlenecks.sort(key=lambda x: x["percentage"], reverse=True)
        return bottlenecks

    def get_run_summary(self, run_index: int = -1) -> Dict:
        """Get summary for a specific consolidation run.

        Args:
            run_index: Index of run (-1 for most recent)

        Returns:
            Dict with run metrics
        """
        if not self.consolidation_runs:
            return {}

        run = self.consolidation_runs[run_index]
        total_duration = (run["completed_at"] - run["started_at"]).total_seconds()
        patterns_extracted = run["pattern_counts"].get("patterns_extracted", 0)

        return {
            "session_id": run["session_id"],
            "run_id": run["run_id"],
            "started_at": run["started_at"].isoformat(),
            "completed_at": run["completed_at"].isoformat(),
            "total_duration_seconds": total_duration,
            "throughput_patterns_per_sec": (
                patterns_extracted / total_duration if total_duration > 0 else 0.0
            ),
            "pattern_counts": run["pattern_counts"],
            "stage_durations": run["stage_durations"],
        }

    def reset(self):
        """Reset all instrumentation data."""
        self.stage_metrics.clear()
        self.consolidation_runs.clear()
        self.current_run = None

    def get_performance_recommendations(self) -> List[str]:
        """Generate recommendations for pipeline optimization.

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            recommendations.append(
                f"Optimize {bottlenecks[0]['stage']} stage "
                f"({bottlenecks[0]['percentage']:.1f}% of time)"
            )

        avg_throughput = self.calculate_avg_throughput()
        if avg_throughput < 10:
            recommendations.append(
                f"Low throughput ({avg_throughput:.1f} patterns/sec). "
                "Consider batch processing or parallelization."
            )

        # Check for high variance stages
        stats = self.get_stage_stats()
        for stage_name, stage_stats in stats.items():
            if stage_stats["stdev_duration_seconds"] > stage_stats["avg_duration_seconds"]:
                recommendations.append(
                    f"High variance in {stage_name} duration. "
                    "Investigate input data distribution."
                )

        return recommendations if recommendations else ["Pipeline performance is optimal"]


class PipelineTimer:
    """Simple timer context manager for use with instrumentation.

    Usage:
        timer = PipelineTimer()
        with timer.time('stage_name'):
            # Do work
            pass
        print(timer.elapsed)
    """

    def __init__(self):
        """Initialize timer."""
        self.elapsed = 0.0
        self.start_time = None

    @contextmanager
    def time(self, stage_name: str = None):
        """Time a block of code.

        Args:
            stage_name: Optional stage name for logging
        """
        self.start_time = time.time()
        try:
            yield
        finally:
            self.elapsed = time.time() - self.start_time
