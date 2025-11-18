"""Performance Profiler - Track and optimize agent execution performance.

Monitors:
- Execution time per decision
- Memory usage patterns
- Decision latency trends
- Performance bottlenecks
- Optimization opportunities
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


@dataclass
class PerformanceMetric:
    """Single performance measurement."""

    agent_name: str
    operation: str
    execution_time_ms: float
    timestamp: datetime
    memory_mb: Optional[float] = None
    result_size: Optional[int] = None


class PerformanceProfiler:
    """Profiles and optimizes agent performance.

    Tracks execution metrics and identifies opportunities for speedup.
    """

    def __init__(self, db: Database):
        """Initialize performance profiler.

        Args:
            db: Database for storing metrics
        """
        self.db = db
        self.tracker = LearningTracker(db)
        self._metrics_buffer = []
        self._performance_targets = {
            "code-analyzer": 500,  # ms
            "research-coordinator": 1000,
            "workflow-orchestrator": 800,
            "metacognition": 600,
        }

    def record_execution(
        self,
        agent_name: str,
        operation: str,
        execution_time_ms: float,
        memory_mb: Optional[float] = None,
        result_size: Optional[int] = None,
    ):
        """Record an agent execution metric.

        Args:
            agent_name: Name of agent
            operation: Operation performed
            execution_time_ms: How long it took
            memory_mb: Optional memory used
            result_size: Optional size of result
        """
        metric = PerformanceMetric(
            agent_name=agent_name,
            operation=operation,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now(),
            memory_mb=memory_mb,
            result_size=result_size,
        )

        self._metrics_buffer.append(metric)

        # Check if performance is concerning
        target = self._performance_targets.get(agent_name, 1000)
        if execution_time_ms > target * 1.5:  # 50% over target
            self._flag_performance_issue(metric, target)

    def _flag_performance_issue(self, metric: PerformanceMetric, target_ms: float):
        """Flag when performance degrades.

        Args:
            metric: The slow execution
            target_ms: The target execution time
        """
        # Track as learning outcome (slow = partial success)
        self.tracker.track_outcome(
            agent_name=f"{metric.agent_name}-perf",
            decision=metric.operation,
            outcome="partial",
            success_rate=target_ms / metric.execution_time_ms,  # Ratio to target
            execution_time_ms=metric.execution_time_ms,
            context={
                "target_ms": target_ms,
                "actual_ms": metric.execution_time_ms,
                "memory_mb": metric.memory_mb,
            },
        )

    def get_performance_stats(self, agent_name: str, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get performance statistics for an agent.

        Args:
            agent_name: Agent to analyze
            time_window_hours: Time period to analyze

        Returns:
            Performance statistics
        """
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        relevant_metrics = [
            m for m in self._metrics_buffer if m.agent_name == agent_name and m.timestamp >= cutoff
        ]

        if not relevant_metrics:
            return {"agent": agent_name, "measurements": 0, "status": "insufficient_data"}

        times = [m.execution_time_ms for m in relevant_metrics]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        target_time = self._performance_targets.get(agent_name, 1000)

        # Calculate performance score
        if avg_time <= target_time:
            perf_score = 1.0
        else:
            perf_score = target_time / avg_time

        return {
            "agent": agent_name,
            "measurements": len(relevant_metrics),
            "avg_time_ms": avg_time,
            "min_time_ms": min_time,
            "max_time_ms": max_time,
            "target_time_ms": target_time,
            "performance_score": perf_score,
            "status": "healthy" if perf_score > 0.8 else "degraded",
            "trend": self._calculate_trend(relevant_metrics),
        }

    def _calculate_trend(self, metrics: List[PerformanceMetric]) -> str:
        """Calculate performance trend.

        Args:
            metrics: Metrics to analyze

        Returns:
            'improving', 'stable', or 'degrading'
        """
        if len(metrics) < 2:
            return "stable"

        # Split into halves
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        avg_first = sum(m.execution_time_ms for m in first_half) / len(first_half)
        avg_second = sum(m.execution_time_ms for m in second_half) / len(second_half)

        delta = (avg_first - avg_second) / avg_first

        if delta > 0.1:
            return "improving"
        elif delta < -0.1:
            return "degrading"
        else:
            return "stable"

    def get_slowest_operations(
        self, agent_name: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get slowest operations for optimization.

        Args:
            agent_name: Optional agent to filter
            limit: Max results

        Returns:
            Slowest operations sorted by time
        """
        filtered = [m for m in self._metrics_buffer if not agent_name or m.agent_name == agent_name]

        # Group by operation
        by_operation = defaultdict(list)
        for metric in filtered:
            by_operation[metric.operation].append(metric.execution_time_ms)

        # Calculate stats per operation
        operations = []
        for op_name, times in by_operation.items():
            operations.append(
                {
                    "operation": op_name,
                    "avg_time_ms": sum(times) / len(times),
                    "max_time_ms": max(times),
                    "occurrences": len(times),
                    "optimization_priority": (sum(times) / len(times))
                    * len(times),  # Total time impact
                }
            )

        return sorted(operations, key=lambda x: x["optimization_priority"], reverse=True)[:limit]

    def recommend_optimizations(self, agent_name: str) -> List[Dict[str, Any]]:
        """Recommend performance optimizations.

        Args:
            agent_name: Agent to optimize

        Returns:
            List of optimization recommendations
        """
        stats = self.get_performance_stats(agent_name)
        slowest = self.get_slowest_operations(agent_name, limit=5)

        recommendations = []

        # If degrading, recommend investigation
        if stats.get("status") == "degraded":
            recommendations.append(
                {
                    "type": "investigation",
                    "priority": "high",
                    "description": f"{agent_name} performance is degrading",
                    "action": "Profile recent code changes",
                }
            )

        # Focus on slowest operations
        for operation in slowest:
            if operation["optimization_priority"] > 5000:  # High impact
                recommendations.append(
                    {
                        "type": "optimization",
                        "priority": (
                            "high" if operation["optimization_priority"] > 10000 else "medium"
                        ),
                        "operation": operation["operation"],
                        "description": f"Optimize {operation['operation']} (avg: {operation['avg_time_ms']:.0f}ms)",
                        "potential_savings": operation["avg_time_ms"]
                        * 0.3,  # Estimate 30% improvement
                    }
                )

        return recommendations

    def get_system_performance(self) -> Dict[str, Any]:
        """Get overall system performance metrics.

        Returns:
            System-wide performance statistics
        """
        agents = ["code-analyzer", "research-coordinator", "workflow-orchestrator", "metacognition"]

        agent_stats = {agent: self.get_performance_stats(agent) for agent in agents}

        avg_score = sum(s.get("performance_score", 0.5) for s in agent_stats.values()) / len(
            agent_stats
        )

        return {
            "agents": agent_stats,
            "system_health_score": avg_score,
            "system_status": (
                "excellent"
                if avg_score > 0.95
                else "good" if avg_score > 0.8 else "fair" if avg_score > 0.6 else "poor"
            ),
            "timestamp": datetime.now().isoformat(),
        }
