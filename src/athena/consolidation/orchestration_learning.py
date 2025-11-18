"""Discover orchestration patterns from multi-agent executions."""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime


@dataclass
class DiscoveredPattern:
    """A newly discovered orchestration pattern."""

    agent_sequence: List[str]  # Ordered list of agents
    coordination_type: str  # sequential|parallel|hierarchical
    success_rate: float
    avg_execution_time_ms: int
    speedup_factor: float
    execution_count: int
    applicable_domains: List[str]
    applicable_task_types: List[str]
    confidence: float


class OrchestrationLearningEngine:
    """Discover optimal orchestration patterns from execution data."""

    def __init__(self):
        """Initialize orchestration learning engine."""
        self._execution_traces: List[Dict] = []
        self._discovered_patterns: List[DiscoveredPattern] = []
        self._agent_effectiveness: Dict[str, float] = {}
        self._handoff_success_rates: Dict[Tuple[str, str], float] = {}

    def record_execution_trace(
        self,
        delegations: List[Dict],
        total_time_ms: int,
        success: bool,
        task_type: str,
        domains: List[str],
        task_complexity: int,
    ) -> None:
        """Record a multi-agent execution trace.

        Args:
            delegations: List of delegation records with from_agent, to_agent, success fields
            total_time_ms: Total execution time in milliseconds
            success: Whether overall execution succeeded
            task_type: Type of task being executed
            domains: Domains involved
            task_complexity: Complexity of the task (1-10)
        """
        trace = {
            "delegations": delegations,
            "total_time_ms": total_time_ms,
            "success": success,
            "task_type": task_type,
            "domains": domains,
            "complexity": task_complexity,
            "recorded_at": datetime.now(),
        }

        self._execution_traces.append(trace)

        # Update agent effectiveness
        for delegation in delegations:
            agent = delegation.get("to_agent")
            if agent and delegation.get("success"):
                self._agent_effectiveness[agent] = self._agent_effectiveness.get(agent, 0) + 1

        # Update handoff success rates
        for i, delegation in enumerate(delegations[:-1]):
            from_agent = delegation.get("from_agent", "unknown")
            to_agent = delegations[i + 1].get("to_agent", "unknown")
            pair = (from_agent, to_agent)

            if pair not in self._handoff_success_rates:
                self._handoff_success_rates[pair] = 0.0

            if delegation.get("success") and delegations[i + 1].get("success"):
                self._handoff_success_rates[pair] = (
                    self._handoff_success_rates[pair] * 0.8 + 0.2  # Exponential moving average
                )

    def discover_patterns(
        self,
        min_confidence: float = 0.70,
    ) -> List[DiscoveredPattern]:
        """Discover new orchestration patterns from execution traces.

        Args:
            min_confidence: Minimum confidence threshold for discovered patterns

        Returns:
            List of newly discovered patterns
        """
        if not self._execution_traces:
            return []

        # Group traces by characteristics
        trace_groups: Dict[str, List[Dict]] = defaultdict(list)

        for trace in self._execution_traces:
            task_type = trace.get("task_type", "unknown")
            complexity = trace.get("complexity", 5)
            group_key = f"{task_type}_{complexity}"
            trace_groups[group_key].append(trace)

        discovered = []

        for group_key, traces in trace_groups.items():
            if len(traces) < 3:  # Need at least 3 executions to discover pattern
                continue

            # Extract agent sequences
            sequences: Dict[str, int] = defaultdict(int)
            successful_traces = [t for t in traces if t.get("success")]

            for trace in successful_traces:
                delegations = trace.get("delegations", [])
                if not delegations:
                    continue

                # Build agent sequence
                sequence = [delegations[0].get("from_agent", "orchestrator")]
                for delegation in delegations:
                    sequence.append(delegation.get("to_agent", "unknown"))

                sequence_key = ",".join(sequence)
                sequences[sequence_key] += 1

            # Find most common successful sequence
            if not sequences:
                continue

            best_sequence_key = max(sequences, key=sequences.get)
            agent_sequence = best_sequence_key.split(",")

            # Calculate metrics
            success_count = len(successful_traces)
            total_count = len(traces)
            success_rate = success_count / total_count if total_count > 0 else 0.0

            times = [t.get("total_time_ms", 0) for t in successful_traces]
            avg_time = sum(times) / len(times) if times else 0

            # Calculate speedup factor (vs sequential)
            speedup = 1.0 + (len(agent_sequence) - 1) * 0.3 if success_rate > 0.75 else 1.0

            # Determine coordination type
            coordination_type = self._infer_coordination_type(agent_sequence, traces)

            # Extract domains and task types
            task_type = group_key.split("_")[0]
            domains = []
            for trace in successful_traces:
                domains.extend(trace.get("domains", []))
            unique_domains = list(set(domains))

            # Calculate confidence
            confidence = min(0.95, 0.5 + (total_count * 0.1))

            pattern = DiscoveredPattern(
                agent_sequence=agent_sequence,
                coordination_type=coordination_type,
                success_rate=success_rate,
                avg_execution_time_ms=int(avg_time),
                speedup_factor=speedup,
                execution_count=total_count,
                applicable_domains=unique_domains,
                applicable_task_types=[task_type],
                confidence=confidence,
            )

            if confidence >= min_confidence:
                discovered.append(pattern)

        self._discovered_patterns.extend(discovered)
        return discovered

    def _infer_coordination_type(
        self,
        agent_sequence: List[str],
        traces: List[Dict],
    ) -> str:
        """Infer coordination type from agent sequence and traces.

        Args:
            agent_sequence: Sequence of agents
            traces: Execution traces

        Returns:
            Coordination type: sequential|parallel|hierarchical
        """
        # Simple heuristic: check if agents are repeated
        unique_agents = set(agent_sequence)

        if len(unique_agents) == 1:
            return "sequential"
        elif len(unique_agents) <= 3:
            # Check if any agent delegates to multiple others
            delegation_count: Dict[str, Set[str]] = defaultdict(set)
            for trace in traces:
                for delegation in trace.get("delegations", []):
                    from_agent = delegation.get("from_agent")
                    to_agent = delegation.get("to_agent")
                    if from_agent and to_agent:
                        delegation_count[from_agent].add(to_agent)

            # If orchestrator delegates to multiple agents, it's parallel
            orchestrator_delegates = len(delegation_count.get("orchestrator", set()))
            if orchestrator_delegates > 1:
                return "parallel"

            return "hierarchical"
        else:
            return "hybrid"

    def get_best_pattern_for_task(
        self,
        task_type: str,
        complexity: int,
    ) -> Optional[DiscoveredPattern]:
        """Get best pattern for a task type and complexity.

        Args:
            task_type: Type of task
            complexity: Complexity level

        Returns:
            Best pattern for this task, or None
        """
        matching = [
            p
            for p in self._discovered_patterns
            if task_type in p.applicable_task_types and p.success_rate > 0.75
        ]

        if not matching:
            return None

        # Sort by success_rate * confidence
        matching.sort(
            key=lambda p: p.success_rate * p.confidence,
            reverse=True,
        )

        return matching[0]

    def get_successful_agent_teams(
        self,
        min_success_rate: float = 0.80,
    ) -> List[Tuple[List[str], float]]:
        """Get list of successful agent teams ranked by success rate.

        Args:
            min_success_rate: Minimum success rate threshold

        Returns:
            List of (agent_sequence, success_rate) tuples
        """
        successful = [
            (p.agent_sequence, p.success_rate)
            for p in self._discovered_patterns
            if p.success_rate >= min_success_rate
        ]

        successful.sort(key=lambda x: x[1], reverse=True)
        return successful

    def get_handoff_bottlenecks(self) -> List[Tuple[str, str, float]]:
        """Identify handoff pairs with low success rates.

        Returns:
            List of (from_agent, to_agent, success_rate) tuples sorted by success_rate
        """
        pairs = [
            (pair[0], pair[1], success_rate)
            for pair, success_rate in self._handoff_success_rates.items()
        ]

        pairs.sort(key=lambda x: x[2])
        return pairs

    def estimate_speedup_for_pattern(
        self,
        agent_count: int,
        coordination_type: str,
    ) -> float:
        """Estimate speedup factor based on pattern characteristics.

        Args:
            agent_count: Number of agents in team
            coordination_type: Type of coordination

        Returns:
            Estimated speedup factor (1.0 = no speedup)
        """
        if agent_count == 1:
            return 1.0

        # Base speedup: 0.3 per additional agent
        base_speedup = 1.0 + (agent_count - 1) * 0.3

        # Coordination adjustment
        if coordination_type == "parallel":
            multiplier = 1.2  # 20% boost for parallel
        elif coordination_type == "hierarchical":
            multiplier = 0.9  # 10% reduction for hierarchy overhead
        else:
            multiplier = 1.0  # No adjustment for sequential

        return min(base_speedup * multiplier, 5.0)  # Cap at 5x speedup

    def extract_orchestration_insights(self) -> List[str]:
        """Extract key insights from discovered patterns.

        Returns:
            List of actionable insights
        """
        insights = []

        if not self._discovered_patterns:
            return ["No orchestration patterns discovered yet"]

        # Insight 1: Best performing patterns
        best_patterns = sorted(
            self._discovered_patterns,
            key=lambda p: p.success_rate * p.confidence,
            reverse=True,
        )[:3]

        for pattern in best_patterns:
            if pattern.success_rate > 0.85:
                insights.append(
                    f"✅ Highly effective pattern: {' → '.join(pattern.agent_sequence)} "
                    f"({pattern.success_rate:.1%} success, {pattern.speedup_factor:.1f}x speedup)"
                )

        # Insight 2: Problematic handoffs
        bottlenecks = self.get_handoff_bottlenecks()
        for from_agent, to_agent, success_rate in bottlenecks[:3]:
            if success_rate < 0.70:
                insights.append(
                    f"⚠️ Handoff problem: {from_agent} → {to_agent} only {success_rate:.1%} success"
                )

        # Insight 3: Most effective agents
        if self._agent_effectiveness:
            top_agents = sorted(
                self._agent_effectiveness.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]

            agent_names = [f"{agent}" for agent, count in top_agents]
            insights.append(f"⭐ Most reliable agents: {', '.join(agent_names)}")

        return insights
