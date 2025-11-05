"""Performance Profiling for code analysis.

Provides:
- Execution time profiling
- Memory usage tracking
- Performance bottleneck identification
- Performance improvement recommendations
- Performance trending analysis
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import math


class PerformanceIssueType(str, Enum):
    """Types of performance issues."""
    SLOW_EXECUTION = "slow_execution"
    HIGH_MEMORY = "high_memory"
    INEFFICIENT_ALGORITHM = "inefficient_algorithm"
    EXCESSIVE_CALLS = "excessive_calls"
    MEMORY_LEAK = "memory_leak"
    LOCK_CONTENTION = "lock_contention"


class PerfomanceLevel(str, Enum):
    """Performance quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class ProfilingData:
    """Performance profiling data for a symbol."""
    symbol_name: str
    execution_time_ms: float  # Total execution time in milliseconds
    memory_usage_mb: float  # Memory usage in megabytes
    cpu_cycles: int  # CPU cycles used
    call_count: int  # Number of times called
    cache_misses: int  # Cache misses
    instructions_executed: int  # Total instructions


@dataclass
class PerformanceMetric:
    """Single performance metric."""
    metric_name: str
    value: float
    unit: str
    baseline: Optional[float] = None
    variance_percent: float = 0.0


@dataclass
class PerformanceIssue:
    """Identified performance issue."""
    symbol_name: str
    issue_type: PerformanceIssueType
    severity: str  # low, medium, high, critical
    severity_score: float  # 0-1
    current_value: float
    threshold: float
    metric_name: str
    remediation: List[str]


@dataclass
class PerformanceProfile:
    """Complete performance profile for a symbol."""
    symbol_name: str
    overall_score: float  # 0-100
    performance_level: str  # excellent, good, acceptable, poor, critical
    metrics: Dict[str, PerformanceMetric]
    issues: List[PerformanceIssue]
    bottlenecks: List[Dict]  # Top performance bottlenecks
    improvement_potential: float  # 0-100, % improvement possible
    recommendations: List[str]


class PerformanceProfiler:
    """Profiles code performance and identifies optimization opportunities."""

    def __init__(self):
        """Initialize profiler."""
        self.profiles: Dict[str, PerformanceProfile] = {}
        self.historical_data: Dict[str, List[ProfilingData]] = {}
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}

    def set_baseline(self, symbol_name: str, metrics: Dict[str, float]) -> None:
        """Set baseline performance metrics for a symbol.

        Args:
            symbol_name: Name of symbol
            metrics: Dict of metric_name -> baseline_value
        """
        self.baseline_metrics[symbol_name] = metrics

    def profile_symbol(self, symbol_data: Dict) -> PerformanceProfile:
        """Profile performance of a symbol.

        Args:
            symbol_data: Dict with profiling data

        Returns:
            PerformanceProfile with metrics and recommendations
        """
        symbol_name = symbol_data.get("name", "unknown")

        # Extract metrics
        metrics = self._extract_metrics(symbol_data)

        # Identify issues
        issues = self._identify_issues(symbol_name, symbol_data, metrics)

        # Calculate overall score
        overall_score = self._calculate_performance_score(issues, metrics)

        # Determine performance level
        perf_level = self._determine_performance_level(overall_score)

        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(symbol_data, metrics)

        # Calculate improvement potential
        improvement_potential = self._calculate_improvement_potential(
            issues, symbol_data
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(issues, bottlenecks)

        profile = PerformanceProfile(
            symbol_name=symbol_name,
            overall_score=overall_score,
            performance_level=perf_level,
            metrics=metrics,
            issues=issues,
            bottlenecks=bottlenecks,
            improvement_potential=improvement_potential,
            recommendations=recommendations,
        )

        self.profiles[symbol_name] = profile
        return profile

    def _extract_metrics(self, symbol_data: Dict) -> Dict[str, PerformanceMetric]:
        """Extract performance metrics from symbol data.

        Args:
            symbol_data: Symbol profiling data

        Returns:
            Dict of metric_name -> PerformanceMetric
        """
        metrics = {}

        # Execution time metric
        exec_time = symbol_data.get("execution_time_ms", 0.0)
        baseline = self.baseline_metrics.get(
            symbol_data.get("name", ""), {}
        ).get("execution_time_ms")
        variance = self._calculate_variance(exec_time, baseline)

        metrics["execution_time"] = PerformanceMetric(
            metric_name="Execution Time",
            value=exec_time,
            unit="ms",
            baseline=baseline,
            variance_percent=variance,
        )

        # Memory usage metric
        memory = symbol_data.get("memory_usage_mb", 0.0)
        baseline = self.baseline_metrics.get(
            symbol_data.get("name", ""), {}
        ).get("memory_usage_mb")
        variance = self._calculate_variance(memory, baseline)

        metrics["memory_usage"] = PerformanceMetric(
            metric_name="Memory Usage",
            value=memory,
            unit="MB",
            baseline=baseline,
            variance_percent=variance,
        )

        # CPU cycles metric
        cpu_cycles = symbol_data.get("cpu_cycles", 0)
        metrics["cpu_cycles"] = PerformanceMetric(
            metric_name="CPU Cycles",
            value=float(cpu_cycles),
            unit="cycles",
        )

        # Call count metric
        call_count = symbol_data.get("call_count", 1)
        metrics["call_count"] = PerformanceMetric(
            metric_name="Call Count",
            value=float(call_count),
            unit="calls",
        )

        # Cache misses metric
        cache_misses = symbol_data.get("cache_misses", 0)
        metrics["cache_misses"] = PerformanceMetric(
            metric_name="Cache Misses",
            value=float(cache_misses),
            unit="misses",
        )

        # Instructions metric
        instructions = symbol_data.get("instructions_executed", 0)
        metrics["instructions"] = PerformanceMetric(
            metric_name="Instructions Executed",
            value=float(instructions),
            unit="instructions",
        )

        return metrics

    def _calculate_variance(
        self, current_value: float, baseline: Optional[float]
    ) -> float:
        """Calculate percent variance from baseline.

        Args:
            current_value: Current value
            baseline: Baseline value

        Returns:
            Variance percentage (negative = improvement, positive = regression)
        """
        if baseline is None or baseline == 0:
            return 0.0

        return ((current_value - baseline) / baseline) * 100.0

    def _identify_issues(
        self,
        symbol_name: str,
        symbol_data: Dict,
        metrics: Dict[str, PerformanceMetric],
    ) -> List[PerformanceIssue]:
        """Identify performance issues.

        Args:
            symbol_name: Symbol name
            symbol_data: Symbol profiling data
            metrics: Extracted metrics

        Returns:
            List of identified issues
        """
        issues = []

        # Check execution time (threshold: > 100ms)
        exec_time = metrics["execution_time"].value
        if exec_time > 100:
            severity = "critical" if exec_time > 500 else "high"
            issues.append(
                PerformanceIssue(
                    symbol_name=symbol_name,
                    issue_type=PerformanceIssueType.SLOW_EXECUTION,
                    severity=severity,
                    severity_score=min(1.0, exec_time / 1000.0),
                    current_value=exec_time,
                    threshold=100.0,
                    metric_name="execution_time_ms",
                    remediation=[
                        "Profile with detailed instrumentation",
                        "Identify hot loops",
                        "Consider algorithm optimization",
                        "Cache computed results",
                    ],
                )
            )

        # Check memory usage (threshold: > 50MB)
        memory = metrics["memory_usage"].value
        if memory > 50:
            severity = "critical" if memory > 200 else "high"
            issues.append(
                PerformanceIssue(
                    symbol_name=symbol_name,
                    issue_type=PerformanceIssueType.HIGH_MEMORY,
                    severity=severity,
                    severity_score=min(1.0, memory / 500.0),
                    current_value=memory,
                    threshold=50.0,
                    metric_name="memory_usage_mb",
                    remediation=[
                        "Review data structure choices",
                        "Implement streaming/pagination",
                        "Check for memory leaks",
                        "Use generators instead of lists",
                    ],
                )
            )

        # Check excessive calls (threshold: > 10000 calls)
        calls = metrics["call_count"].value
        if calls > 10000:
            issues.append(
                PerformanceIssue(
                    symbol_name=symbol_name,
                    issue_type=PerformanceIssueType.EXCESSIVE_CALLS,
                    severity="medium",
                    severity_score=min(1.0, (calls - 10000) / 90000.0),
                    current_value=calls,
                    threshold=10000.0,
                    metric_name="call_count",
                    remediation=[
                        "Cache results to reduce calls",
                        "Batch operations",
                        "Use memoization",
                        "Consider async processing",
                    ],
                )
            )

        # Check cache misses (threshold: > 1000)
        cache_misses = metrics["cache_misses"].value
        if cache_misses > 1000:
            issues.append(
                PerformanceIssue(
                    symbol_name=symbol_name,
                    issue_type=PerformanceIssueType.INEFFICIENT_ALGORITHM,
                    severity="medium",
                    severity_score=min(1.0, cache_misses / 10000.0),
                    current_value=cache_misses,
                    threshold=1000.0,
                    metric_name="cache_misses",
                    remediation=[
                        "Improve data locality",
                        "Optimize access patterns",
                        "Use appropriate data structures",
                        "Consider algorithmic improvements",
                    ],
                )
            )

        # Check variance from baseline
        for metric_name, metric in metrics.items():
            if metric.variance_percent > 20:  # 20% regression
                issues.append(
                    PerformanceIssue(
                        symbol_name=symbol_name,
                        issue_type=PerformanceIssueType.SLOW_EXECUTION,
                        severity="medium",
                        severity_score=min(1.0, metric.variance_percent / 100.0),
                        current_value=metric.value,
                        threshold=metric.baseline or 0.0,
                        metric_name=metric_name,
                        remediation=[
                            f"Investigate regression in {metric.metric_name}",
                            "Review recent code changes",
                            "Profile and compare with baseline",
                        ],
                    )
                )

        return issues

    def _calculate_performance_score(
        self, issues: List[PerformanceIssue], metrics: Dict[str, PerformanceMetric]
    ) -> float:
        """Calculate overall performance score.

        Args:
            issues: Performance issues
            metrics: Performance metrics

        Returns:
            Score 0-100
        """
        base_score = 100.0

        # Deduct for each issue based on severity
        severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        for issue in issues:
            weight = severity_weights.get(issue.severity, 5)
            base_score -= weight

        # Bonus for good metrics (if available)
        if metrics and "execution_time" in metrics:
            if metrics["execution_time"].value < 10:
                base_score += 5
        if metrics and "memory_usage" in metrics:
            if metrics["memory_usage"].value < 10:
                base_score += 5

        return max(0.0, min(100.0, base_score))

    def _determine_performance_level(self, score: float) -> str:
        """Determine performance level from score.

        Args:
            score: Performance score 0-100

        Returns:
            Performance level string
        """
        if score >= 85:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 55:
            return "acceptable"
        elif score >= 40:
            return "poor"
        else:
            return "critical"

    def _identify_bottlenecks(
        self, symbol_data: Dict, metrics: Dict[str, PerformanceMetric]
    ) -> List[Dict]:
        """Identify performance bottlenecks.

        Args:
            symbol_data: Symbol data
            metrics: Performance metrics

        Returns:
            List of bottleneck dicts
        """
        bottlenecks = []

        # Bottleneck: High execution time relative to calls
        exec_time = metrics["execution_time"].value
        calls = metrics["call_count"].value
        if calls > 0:
            time_per_call = exec_time / calls
            if time_per_call > 1.0:  # >1ms per call
                bottlenecks.append({
                    "name": "High Time Per Call",
                    "metric": time_per_call,
                    "unit": "ms",
                    "severity": "high" if time_per_call > 10 else "medium",
                })

        # Bottleneck: High memory per call
        memory = metrics["memory_usage"].value
        if calls > 0:
            memory_per_call = memory / calls
            if memory_per_call > 0.1:  # >0.1MB per call
                bottlenecks.append({
                    "name": "High Memory Per Call",
                    "metric": memory_per_call,
                    "unit": "MB",
                    "severity": "high",
                })

        # Bottleneck: Instructions per cache miss
        instructions = metrics["instructions"].value
        cache_misses = metrics["cache_misses"].value
        if cache_misses > 0:
            instr_per_miss = instructions / cache_misses
            if instr_per_miss < 10:  # <10 instructions per cache miss
                bottlenecks.append({
                    "name": "Poor Cache Efficiency",
                    "metric": instr_per_miss,
                    "unit": "instr/miss",
                    "severity": "medium",
                })

        return sorted(bottlenecks, key=lambda x: x["severity"], reverse=True)

    def _calculate_improvement_potential(
        self, issues: List[PerformanceIssue], symbol_data: Dict
    ) -> float:
        """Calculate potential for improvement.

        Args:
            issues: Performance issues
            symbol_data: Symbol data

        Returns:
            Improvement potential 0-100
        """
        if not issues:
            return 0.0

        # Calculate based on issue severity and count
        total_potential = 0.0
        for issue in issues:
            severity_potential = {
                "critical": 30,
                "high": 20,
                "medium": 10,
                "low": 5,
            }
            total_potential += severity_potential.get(issue.severity, 5)

        return min(100.0, total_potential)

    def _generate_recommendations(
        self, issues: List[PerformanceIssue], bottlenecks: List[Dict]
    ) -> List[str]:
        """Generate performance improvement recommendations.

        Args:
            issues: Performance issues
            bottlenecks: Identified bottlenecks

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            recommendations.append(
                f"URGENT: Address {len(critical_issues)} critical performance issue(s)"
            )
            for issue in critical_issues[:2]:
                recommendations.extend(issue.remediation[:2])

        # High issues
        high_issues = [i for i in issues if i.severity == "high"]
        if high_issues:
            recommendations.append(
                f"Priority: Optimize {high_issues[0].issue_type.value}"
            )

        # Top bottleneck
        if bottlenecks:
            recommendations.append(
                f"Key Bottleneck: {bottlenecks[0]['name']} ({bottlenecks[0]['metric']:.2f} {bottlenecks[0]['unit']})"
            )

        # Generic recommendations
        if not recommendations:
            recommendations.append("Code is performing well. Consider profiling for further optimization.")

        return recommendations

    def compare_profiles(
        self, symbol_name1: str, symbol_name2: str
    ) -> Dict:
        """Compare performance profiles of two symbols.

        Args:
            symbol_name1: First symbol
            symbol_name2: Second symbol

        Returns:
            Comparison dict
        """
        prof1 = self.profiles.get(symbol_name1)
        prof2 = self.profiles.get(symbol_name2)

        if not prof1 or not prof2:
            return {"error": "One or both profiles not found"}

        return {
            "symbol1": symbol_name1,
            "symbol2": symbol_name2,
            "score_difference": prof2.overall_score - prof1.overall_score,
            "faster": symbol_name2 if prof2.overall_score > prof1.overall_score else symbol_name1,
            "metrics_comparison": {
                "exec_time": {
                    symbol_name1: prof1.metrics["execution_time"].value,
                    symbol_name2: prof2.metrics["execution_time"].value,
                },
                "memory": {
                    symbol_name1: prof1.metrics["memory_usage"].value,
                    symbol_name2: prof2.metrics["memory_usage"].value,
                },
            },
        }

    def track_performance_trend(self, symbol_name: str, profile: PerformanceProfile) -> None:
        """Track performance trend over time.

        Args:
            symbol_name: Symbol to track
            profile: Performance profile
        """
        if symbol_name not in self.historical_data:
            self.historical_data[symbol_name] = []

        # Store as ProfilingData
        data = ProfilingData(
            symbol_name=symbol_name,
            execution_time_ms=profile.metrics["execution_time"].value,
            memory_usage_mb=profile.metrics["memory_usage"].value,
            cpu_cycles=int(profile.metrics["cpu_cycles"].value),
            call_count=int(profile.metrics["call_count"].value),
            cache_misses=int(profile.metrics["cache_misses"].value),
            instructions_executed=int(profile.metrics["instructions"].value),
        )

        self.historical_data[symbol_name].append(data)

    def get_performance_trend(self, symbol_name: str) -> Dict:
        """Get performance trend for a symbol.

        Args:
            symbol_name: Symbol to analyze

        Returns:
            Trend analysis dict
        """
        history = self.historical_data.get(symbol_name, [])

        if len(history) < 2:
            return {"status": "insufficient_data", "count": len(history)}

        # Calculate trends
        exec_times = [d.execution_time_ms for d in history]
        memory_usage = [d.memory_usage_mb for d in history]

        exec_trend = "improving" if exec_times[-1] < exec_times[0] else "degrading"
        memory_trend = "improving" if memory_usage[-1] < memory_usage[0] else "degrading"

        return {
            "symbol": symbol_name,
            "data_points": len(history),
            "execution_time": {
                "first": exec_times[0],
                "latest": exec_times[-1],
                "trend": exec_trend,
                "change_percent": ((exec_times[-1] - exec_times[0]) / exec_times[0]) * 100,
            },
            "memory_usage": {
                "first": memory_usage[0],
                "latest": memory_usage[-1],
                "trend": memory_trend,
                "change_percent": ((memory_usage[-1] - memory_usage[0]) / memory_usage[0]) * 100,
            },
        }

    def get_profiling_summary(self) -> Dict:
        """Get summary of all profiles.

        Returns:
            Summary dict
        """
        if not self.profiles:
            return {
                "total_symbols": 0,
                "average_score": 0.0,
                "performance_levels": {},
            }

        scores = [p.overall_score for p in self.profiles.values()]
        levels = {}
        for profile in self.profiles.values():
            level = profile.performance_level
            levels[level] = levels.get(level, 0) + 1

        return {
            "total_symbols": len(self.profiles),
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 100.0,
            "performance_levels": levels,
            "critical_count": len([p for p in self.profiles.values() if p.performance_level == "critical"]),
            "excellent_count": len([p for p in self.profiles.values() if p.performance_level == "excellent"]),
        }
