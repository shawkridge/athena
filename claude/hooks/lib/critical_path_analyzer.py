#!/usr/bin/env python3
"""
Critical Path Analyzer - Phase 7 Implementation

Analyzes hook dependencies to find critical path and optimize execution order.

Features:
- Topological sort with critical path computation
- Slack time calculation (how much a hook can be delayed)
- Hook duration estimation from historical metrics
- Reordering suggestions for minimal total execution time
- List scheduling algorithm for optimization

Usage:
    analyzer = CriticalPathAnalyzer(manifest)
    critical_path = analyzer.compute_critical_path("session-start")
    suggestions = analyzer.suggest_reordering("post-execution")
"""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("critical_path_analyzer")


@dataclass
class HookMetrics:
    """Metrics for a single hook"""
    name: str
    phase: str
    estimated_duration_ms: int
    actual_duration_ms: Optional[int] = None
    execution_count: int = 0
    p95_duration_ms: Optional[int] = None  # 95th percentile
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    earliest_start_ms: int = 0
    latest_start_ms: int = 0
    slack_time_ms: int = 0
    on_critical_path: bool = False

    def duration(self) -> int:
        """Get effective duration (use p95 if available, else actual, else estimate)"""
        if self.p95_duration_ms is not None:
            return self.p95_duration_ms
        if self.actual_duration_ms is not None:
            return self.actual_duration_ms
        return self.estimated_duration_ms


@dataclass
class CriticalPathResult:
    """Result of critical path analysis"""
    phase: str
    critical_path: List[str]  # Hook names in critical path order
    critical_path_length_ms: int
    total_hooks: int
    hooks_on_path: int
    speedup_potential: float  # Potential speedup from optimizing non-critical hooks
    optimal_order: List[str]  # Suggested optimal execution order
    hook_metrics: Dict[str, HookMetrics]


class CriticalPathAnalyzer:
    """
    Analyzes hook dependencies to find critical path and optimize execution
    """

    def __init__(self, manifest_path: Optional[str] = None,
                 metrics_path: Optional[str] = None):
        """
        Initialize analyzer with manifest and optional metrics

        Args:
            manifest_path: Path to hook_manifest.json
            metrics_path: Path to execution metrics (for historical data)
        """
        if manifest_path is None:
            manifest_path = str(Path(__file__).parent.parent / "hook_manifest.json")

        self.manifest_path = Path(manifest_path)
        self.metrics_path = Path(metrics_path) if metrics_path else None
        self.manifest = self._load_manifest()
        self.hook_map = {h["name"]: h for h in self.manifest.get("hooks", [])}
        self.historical_metrics = self._load_historical_metrics()

    def _load_manifest(self) -> Dict:
        """Load hook manifest"""
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load manifest: {e}")
            return {}

    def _load_historical_metrics(self) -> Dict[str, Dict]:
        """Load historical execution metrics if available"""
        if not self.metrics_path or not self.metrics_path.exists():
            return {}

        try:
            with open(self.metrics_path, 'r') as f:
                data = json.load(f)
            metrics = {}
            for hook in data.get("hooks", []):
                metrics[hook["name"]] = hook
            logger.info(f"Loaded metrics for {len(metrics)} hooks")
            return metrics
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def compute_critical_path(self, phase: str) -> CriticalPathResult:
        """
        Compute critical path for a phase

        Algorithm:
        1. Topologically sort hooks
        2. Compute earliest start time for each hook (forward pass)
        3. Compute latest start time for each hook (backward pass)
        4. Identify hooks with zero slack time (critical path)

        Time Complexity: O(n + m) where n=hooks, m=dependencies
        Space Complexity: O(n)

        Args:
            phase: Phase name to analyze

        Returns:
            CriticalPathResult with critical path and metrics
        """
        # Get hooks in this phase
        phase_hooks = [h["name"] for h in self.manifest.get("hooks", [])
                      if h.get("phase") == phase]

        if not phase_hooks:
            logger.warning(f"No hooks found for phase: {phase}")
            return CriticalPathResult(
                phase=phase,
                critical_path=[],
                critical_path_length_ms=0,
                total_hooks=0,
                hooks_on_path=0,
                speedup_potential=0.0,
                optimal_order=[],
                hook_metrics={}
            )

        # Build dependency graph and compute metrics
        hook_metrics = {}
        for hook_name in phase_hooks:
            hook = self.hook_map[hook_name]
            deps = [d for d in hook.get("dependsOn", []) if d in phase_hooks]
            dependents = [h["name"] for h in self.manifest.get("hooks", [])
                         if h.get("phase") == phase and hook_name in h.get("dependsOn", [])]

            # Estimate duration
            estimated_duration = self._estimate_duration(hook_name)

            metrics = HookMetrics(
                name=hook_name,
                phase=phase,
                estimated_duration_ms=estimated_duration,
                dependencies=deps,
                dependents=dependents
            )
            hook_metrics[hook_name] = metrics

        # Forward pass: compute earliest start time
        visited = set()
        def compute_earliest_start(hook_name: str) -> int:
            if hook_name in visited:
                return hook_metrics[hook_name].earliest_start_ms

            visited.add(hook_name)
            metrics = hook_metrics[hook_name]

            if not metrics.dependencies:
                # Root node starts at 0
                metrics.earliest_start_ms = 0
            else:
                # Start after all dependencies complete
                max_end_time = 0
                for dep in metrics.dependencies:
                    dep_duration = hook_metrics[dep].duration()
                    dep_start = compute_earliest_start(dep)
                    dep_end_time = dep_start + dep_duration
                    max_end_time = max(max_end_time, dep_end_time)

                metrics.earliest_start_ms = max_end_time

            return metrics.earliest_start_ms

        # Compute earliest start for all hooks
        for hook_name in phase_hooks:
            compute_earliest_start(hook_name)

        # Compute project end time (latest hook completion)
        project_end_time = max(
            hook_metrics[h].earliest_start_ms + hook_metrics[h].duration()
            for h in phase_hooks
        )

        # Backward pass: compute latest start time
        def compute_latest_start(hook_name: str, project_end: int) -> int:
            metrics = hook_metrics[hook_name]

            if not metrics.dependents:
                # Leaf nodes must finish by project end
                metrics.latest_start_ms = project_end - metrics.duration()
            else:
                # Must finish before all dependents start
                min_start_time = project_end
                for dependent in metrics.dependents:
                    dep_metrics = hook_metrics[dependent]
                    compute_latest_start(dependent, project_end)
                    # Dependent must start after this hook finishes
                    min_start_time = min(min_start_time, dep_metrics.latest_start_ms)

                metrics.latest_start_ms = min_start_time - metrics.duration()

            return metrics.latest_start_ms

        for hook_name in phase_hooks:
            compute_latest_start(hook_name, project_end_time)

        # Compute slack time (flexibility in scheduling)
        for metrics in hook_metrics.values():
            metrics.slack_time_ms = metrics.latest_start_ms - metrics.earliest_start_ms

        # Identify critical path (hooks with zero slack)
        critical_path = [h for h in phase_hooks
                        if hook_metrics[h].slack_time_ms == 0]
        for h in critical_path:
            hook_metrics[h].on_critical_path = True

        # Topologically sort critical path
        critical_path_sorted = self._topological_sort(critical_path, hook_metrics)

        # Compute speedup potential
        # Speedup = project_end_time / (project_end_time - sum(non_critical_slack))
        total_slack = sum(m.slack_time_ms for m in hook_metrics.values()
                         if m.slack_time_ms > 0)
        speedup_potential = (project_end_time / (project_end_time - total_slack)
                            if total_slack > 0 else 1.0)

        # Suggest optimal order (longest duration first, respecting dependencies)
        optimal_order = self._suggest_optimal_order(phase_hooks, hook_metrics)

        logger.info(f"Phase '{phase}': critical_path_length={project_end_time}ms, "
                   f"hooks_on_path={len(critical_path)}, speedup_potential={speedup_potential:.2f}x")

        return CriticalPathResult(
            phase=phase,
            critical_path=critical_path_sorted,
            critical_path_length_ms=project_end_time,
            total_hooks=len(phase_hooks),
            hooks_on_path=len(critical_path),
            speedup_potential=speedup_potential,
            optimal_order=optimal_order,
            hook_metrics=hook_metrics
        )

    def _topological_sort(self, hooks: List[str], metrics: Dict[str, HookMetrics]) -> List[str]:
        """
        Topologically sort hooks respecting dependencies

        Args:
            hooks: List of hook names
            metrics: Hook metrics dictionary

        Returns:
            Topologically sorted list of hook names
        """
        order = []
        visited = set()
        temp_visited = set()

        def visit(hook_name: str):
            if hook_name in visited:
                return
            if hook_name in temp_visited:
                logger.warning(f"Cycle detected at {hook_name}")
                return

            temp_visited.add(hook_name)
            for dep in metrics[hook_name].dependencies:
                if dep in metrics:
                    visit(dep)
            temp_visited.remove(hook_name)

            visited.add(hook_name)
            order.append(hook_name)

        for hook in hooks:
            visit(hook)

        return order

    def _suggest_optimal_order(self, phase_hooks: List[str],
                              hook_metrics: Dict[str, HookMetrics]) -> List[str]:
        """
        Suggest optimal execution order using list scheduling

        Algorithm:
        1. Sort hooks by duration (longest first) and slack time (lowest first)
        2. Schedule hooks as soon as dependencies are satisfied
        3. Respect critical path (hooks on critical path cannot be reordered)

        Returns:
            Suggested execution order
        """
        # Group hooks: critical path vs non-critical
        critical = {h for h in phase_hooks if hook_metrics[h].on_critical_path}
        non_critical = {h for h in phase_hooks if not hook_metrics[h].on_critical_path}

        # Critical path must maintain order (already determined by dependencies)
        critical_order = self._topological_sort(list(critical), hook_metrics)

        # For non-critical hooks, use list scheduling
        # Sort by: slack time (ascending), then duration (descending)
        non_critical_sorted = sorted(
            non_critical,
            key=lambda h: (hook_metrics[h].slack_time_ms, -hook_metrics[h].duration())
        )

        # Interleave critical and non-critical
        # Strategy: Schedule non-critical hooks that don't block critical path
        optimal_order = []
        scheduled = set()
        remaining_critical = set(critical_order)
        remaining_non_critical = set(non_critical_sorted)

        while remaining_critical or remaining_non_critical:
            # Schedule one critical hook if its dependencies are met
            scheduled_in_round = False

            for hook in critical_order:
                if hook not in remaining_critical:
                    continue

                deps_met = all(dep in scheduled for dep in hook_metrics[hook].dependencies)
                if deps_met:
                    optimal_order.append(hook)
                    remaining_critical.discard(hook)
                    scheduled.add(hook)
                    scheduled_in_round = True
                    break

            # Schedule non-critical hooks that don't block critical path
            for hook in non_critical_sorted:
                if hook not in remaining_non_critical:
                    continue

                deps_met = all(dep in scheduled for dep in hook_metrics[hook].dependencies)
                if deps_met:
                    optimal_order.append(hook)
                    remaining_non_critical.discard(hook)
                    scheduled.add(hook)
                    scheduled_in_round = True

            if not scheduled_in_round and (remaining_critical or remaining_non_critical):
                # Deadlock - shouldn't happen with valid manifest
                logger.warning("Deadlock in scheduling - breaking")
                optimal_order.extend(remaining_critical)
                optimal_order.extend(remaining_non_critical)
                break

        return optimal_order

    def _estimate_duration(self, hook_name: str) -> int:
        """
        Estimate hook duration from:
        1. Historical metrics (p95)
        2. Default estimate from manifest
        3. Fallback to average

        Args:
            hook_name: Name of hook

        Returns:
            Estimated duration in milliseconds
        """
        # Check historical metrics
        if hook_name in self.historical_metrics:
            hist = self.historical_metrics[hook_name]
            if "p95_duration_ms" in hist:
                return hist["p95_duration_ms"]
            if "duration_ms" in hist:
                return hist["duration_ms"]

        # Use manifest timeout as estimate (conservative)
        if hook_name in self.hook_map:
            timeout = self.hook_map[hook_name].get("timeout", 3000)
            # Assume typical execution is ~70% of timeout
            return int(timeout * 0.7)

        # Fallback: average timeout
        return 2000

    def analyze_phase_performance(self, phase: str) -> Dict:
        """
        Analyze performance characteristics of a phase

        Returns:
            Dictionary with:
            - Critical path length
            - Parallelization potential
            - Hooks that should be optimized
            - Estimated speedup from optimization
        """
        result = self.compute_critical_path(phase)

        # Find hooks with high execution time but not on critical path
        optimization_candidates = [
            (h, result.hook_metrics[h].duration())
            for h in result.hook_metrics
            if not result.hook_metrics[h].on_critical_path
            and result.hook_metrics[h].slack_time_ms > 0
        ]
        optimization_candidates.sort(key=lambda x: -x[1])

        return {
            "phase": phase,
            "critical_path_length_ms": result.critical_path_length_ms,
            "critical_path": result.critical_path,
            "hooks_on_path": result.hooks_on_path,
            "total_hooks": result.total_hooks,
            "speedup_potential": result.speedup_potential,
            "optimization_candidates": [
                {
                    "hook": h,
                    "duration_ms": d,
                    "slack_ms": result.hook_metrics[h].slack_time_ms
                }
                for h, d in optimization_candidates[:5]  # Top 5
            ],
            "parallelizable_count": sum(
                1 for m in result.hook_metrics.values()
                if m.slack_time_ms > 0
            )
        }


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Critical Path Analyzer")
    parser.add_argument("--phase", help="Phase to analyze", default="post-execution")
    parser.add_argument("--manifest", help="Path to hook_manifest.json")
    parser.add_argument("--metrics", help="Path to execution metrics")
    parser.add_argument("--all-phases", action="store_true", help="Analyze all phases")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    analyzer = CriticalPathAnalyzer(args.manifest, args.metrics)

    if args.all_phases:
        phases = set(h.get("phase") for h in analyzer.manifest.get("hooks", []))
        for phase in sorted(phases):
            result = analyzer.analyze_phase_performance(phase)
            print(json.dumps(result, indent=2))
            print()
    else:
        result = analyzer.analyze_phase_performance(args.phase)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
