"""Advanced Consolidation Strategies - Sophisticated pattern extraction and synthesis.

Implements:
- Hierarchical pattern extraction (micro → macro patterns)
- Causal relationship discovery
- Pattern validation and confidence scoring
- Multi-agent pattern synthesis
- Procedural knowledge extraction
"""

from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

from athena.learning.tracker import LearningTracker
from athena.core.database import Database


class AdvancedConsolidationStrategy:
    """Implements advanced consolidation strategies.

    Goes beyond simple pattern extraction to understand causal
    relationships and hierarchical patterns.
    """

    def __init__(self, db: Database):
        """Initialize advanced strategy.

        Args:
            db: Database for accessing learning data
        """
        self.db = db
        self.tracker = LearningTracker(db)

    def extract_causal_patterns(self, time_window_days: int = 30) -> List[Dict[str, Any]]:
        """Extract causal relationships: when A happens, B tends to follow.

        Args:
            time_window_days: Time period to analyze

        Returns:
            List of causal patterns with confidence
        """
        # Get all outcomes from all agents
        agents = ["code-analyzer", "research-coordinator", "workflow-orchestrator", "metacognition"]

        all_outcomes = []
        for agent in agents:
            history = self.tracker.get_decision_history(agent, limit=500)
            all_outcomes.extend(history)

        # Sort by timestamp
        all_outcomes.sort(key=lambda o: o.timestamp)

        # Find decision patterns: when decision X happens, what follows?
        sequences = defaultdict(list)
        for i in range(len(all_outcomes) - 1):
            current = all_outcomes[i]
            next_outcome = all_outcomes[i + 1]

            # Only link if close in time (within 1 hour)
            time_diff = (next_outcome.timestamp - current.timestamp).total_seconds() / 3600
            if time_diff > 1:
                continue

            sequence_key = f"{current.decision} → {next_outcome.decision}"
            sequences[sequence_key].append(
                {"result": next_outcome.success_rate, "outcome_type": next_outcome.outcome}
            )

        # Analyze sequences for causal patterns
        causal_patterns = []
        for sequence, results in sequences.items():
            if len(results) < 2:  # Need at least 2 occurrences
                continue

            avg_success = sum(r["result"] for r in results) / len(results)
            success_count = len([r for r in results if r["outcome_type"] == "success"])
            success_rate = success_count / len(results)

            if avg_success > 0.6 and success_rate > 0.5:
                causal_patterns.append(
                    {
                        "pattern": sequence,
                        "strength": avg_success,
                        "consistency": success_rate,
                        "occurrences": len(results),
                        "causality_score": (avg_success + success_rate) / 2,
                    }
                )

        return sorted(causal_patterns, key=lambda x: x["causality_score"], reverse=True)

    def extract_hierarchical_patterns(self, agent_name: str) -> Dict[str, Any]:
        """Extract hierarchical patterns: micro patterns combine into macro patterns.

        Args:
            agent_name: Agent to analyze

        Returns:
            Hierarchical pattern structure
        """
        history = self.tracker.get_decision_history(agent_name, limit=200)

        # Level 1: Individual decisions (micro)
        micro_patterns = defaultdict(lambda: {"count": 0, "success_sum": 0.0})
        for outcome in history:
            micro_patterns[outcome.decision]["count"] += 1
            micro_patterns[outcome.decision]["success_sum"] += outcome.success_rate

        # Calculate micro pattern stats
        micro_stats = {}
        for decision, data in micro_patterns.items():
            micro_stats[decision] = {
                "frequency": data["count"],
                "avg_success": data["success_sum"] / data["count"],
                "level": "micro",
            }

        # Level 2: Pattern pairs (meso)
        meso_patterns = defaultdict(lambda: {"count": 0, "success_sum": 0.0})
        for i in range(len(history) - 1):
            pair = f"{history[i].decision}:{history[i+1].decision}"
            meso_patterns[pair]["count"] += 1
            meso_patterns[pair]["success_sum"] += history[i + 1].success_rate

        meso_stats = {}
        for pair, data in meso_patterns.items():
            if data["count"] >= 2:
                meso_stats[pair] = {
                    "frequency": data["count"],
                    "avg_success": data["success_sum"] / data["count"],
                    "level": "meso",
                }

        # Level 3: Aggregate strategy effectiveness (macro)
        macro_stats = {
            "overall_success": (
                sum(o.success_rate for o in history) / len(history) if history else 0
            ),
            "consistency": 1.0
            - (
                (max(o.success_rate for o in history) - min(o.success_rate for o in history))
                if history
                else 0
            ),
            "level": "macro",
        }

        return {
            "agent": agent_name,
            "micro_patterns": micro_stats,
            "meso_patterns": meso_stats,
            "macro_pattern": macro_stats,
            "hierarchy_depth": 3,
        }

    def validate_pattern_confidence(
        self, pattern: Dict[str, Any], min_occurrences: int = 3
    ) -> float:
        """Calculate confidence score for a pattern.

        Args:
            pattern: Pattern to validate
            min_occurrences: Minimum required occurrences

        Returns:
            Confidence score (0-1)
        """
        if pattern.get("occurrences", 0) < min_occurrences:
            return 0.0

        occurrences = pattern.get("occurrences", 1)
        strength = pattern.get("strength", 0.5)
        consistency = pattern.get("consistency", 0.5)

        # Confidence components:
        # 1. Statistical significance (more occurrences = more confident)
        significance = min(occurrences / (min_occurrences * 5), 1.0)

        # 2. Pattern strength (success rate)
        strength_score = strength

        # 3. Consistency (how stable the pattern is)
        consistency_score = consistency

        # Weighted average
        confidence = significance * 0.3 + strength_score * 0.4 + consistency_score * 0.3

        return min(confidence, 1.0)

    def synthesize_multi_agent_patterns(self) -> Dict[str, Any]:
        """Synthesize patterns across multiple agents.

        Finds universal principles that apply across agents.

        Returns:
            Cross-agent pattern synthesis
        """
        agents = ["code-analyzer", "research-coordinator", "workflow-orchestrator", "metacognition"]

        patterns_by_agent = {}
        for agent in agents:
            patterns_by_agent[agent] = self.extract_hierarchical_patterns(agent)

        # Find common successful decisions
        all_decisions = set()
        for agent_data in patterns_by_agent.values():
            all_decisions.update(agent_data["micro_patterns"].keys())

        universal_patterns = {}
        for decision in all_decisions:
            success_rates = []
            occurrences = []

            for agent_data in patterns_by_agent.values():
                if decision in agent_data["micro_patterns"]:
                    stats = agent_data["micro_patterns"][decision]
                    success_rates.append(stats["avg_success"])
                    occurrences.append(stats["frequency"])

            if len(success_rates) >= 2:  # Present in multiple agents
                avg_success = sum(success_rates) / len(success_rates)
                universality = len(success_rates) / len(agents)

                if avg_success > 0.7 and universality > 0.5:
                    universal_patterns[decision] = {
                        "avg_success": avg_success,
                        "universality": universality,
                        "agents_using": len(success_rates),
                        "principle": f"Decision '{decision}' tends to succeed universally",
                    }

        return {
            "universal_patterns": universal_patterns,
            "agents_analyzed": len(agents),
            "synthesis_timestamp": datetime.now().isoformat(),
        }

    def extract_procedural_knowledge(
        self, agent_name: str, min_success_rate: float = 0.8
    ) -> List[Dict[str, Any]]:
        """Extract reusable procedures from successful decision sequences.

        Args:
            agent_name: Agent to extract from
            min_success_rate: Minimum success to consider

        Returns:
            List of extracted procedures
        """
        history = self.tracker.get_decision_history(agent_name, limit=300)

        # Filter successful outcomes
        successful = [o for o in history if o.success_rate >= min_success_rate]

        # Find sequences of successful decisions
        procedures = []
        i = 0
        while i < len(successful) - 1:
            # Look for a run of consecutive successes
            sequence = [successful[i]]
            j = i + 1
            while j < len(successful) and j - i < 5:  # Max length 5
                sequence.append(successful[j])
                j += 1

            if len(sequence) >= 2:  # Need at least 2 steps
                procedure = {
                    "name": f"Procedure: {' → '.join(s.decision for s in sequence[:3])}",
                    "steps": [s.decision for s in sequence],
                    "success_rate": sum(s.success_rate for s in sequence) / len(sequence),
                    "length": len(sequence),
                    "extracted_timestamp": datetime.now().isoformat(),
                }
                procedures.append(procedure)

            i = j

        return sorted(procedures, key=lambda x: (x["length"], x["success_rate"]), reverse=True)
