"""Learn which decomposition strategies work best for different task types."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class StrategyPerformance:
    """Performance metrics for a decomposition strategy."""

    strategy_id: int
    task_type: str
    complexity: int  # 1-10
    domain: str
    success_rate: float
    avg_quality_score: float
    avg_duration_variance_pct: float
    execution_count: int
    confidence: float


class StrategyLearningEngine:
    """Learn optimal decomposition strategies for task types and complexities."""

    def __init__(self):
        """Initialize strategy learning engine."""
        self._strategy_performance: Dict[str, List[StrategyPerformance]] = defaultdict(list)
        self._task_clusters: Dict[str, List[Dict]] = defaultdict(list)
        self._strategy_recommendations: Dict[str, StrategyPerformance] = {}

    def analyze_task_type_cluster(
        self,
        task_type: str,
        complexity: int,
        domain: str,
        execution_records: List[Dict],
    ) -> StrategyPerformance:
        """Analyze performance of a strategy for a task type/complexity/domain cluster.

        Args:
            task_type: Type of task (e.g., 'refactoring', 'feature', 'bug-fix')
            complexity: Complexity level (1-10)
            domain: Domain (e.g., 'frontend', 'backend', 'database')
            execution_records: List of execution feedback records

        Returns:
            Performance metrics for this cluster
        """
        if not execution_records:
            return StrategyPerformance(
                strategy_id=0,
                task_type=task_type,
                complexity=complexity,
                domain=domain,
                success_rate=0.0,
                avg_quality_score=0.0,
                avg_duration_variance_pct=0.0,
                execution_count=0,
                confidence=0.0,
            )

        # Extract metrics
        strategy_ids = [r.get("strategy_id") for r in execution_records if r.get("strategy_id")]
        most_common_strategy = max(set(strategy_ids), key=strategy_ids.count) if strategy_ids else 0

        successes = len([r for r in execution_records if r.get("success")])
        success_rate = successes / len(execution_records)

        quality_scores = [r.get("quality_score", 0) for r in execution_records]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        duration_variances = [r.get("duration_variance_pct", 0) for r in execution_records]
        avg_variance = (
            sum(duration_variances) / len(duration_variances) if duration_variances else 0.0
        )

        # Confidence based on execution count
        confidence = min(0.95, 0.3 + len(execution_records) * 0.1)

        performance = StrategyPerformance(
            strategy_id=most_common_strategy,
            task_type=task_type,
            complexity=complexity,
            domain=domain,
            success_rate=success_rate,
            avg_quality_score=avg_quality,
            avg_duration_variance_pct=avg_variance,
            execution_count=len(execution_records),
            confidence=confidence,
        )

        # Store performance
        cluster_key = f"{task_type}_{complexity}_{domain}"
        self._strategy_performance[cluster_key].append(performance)
        self._task_clusters[cluster_key].extend(execution_records)

        return performance

    def get_best_strategy_for_cluster(
        self,
        task_type: str,
        complexity: int,
        domain: str,
    ) -> Optional[StrategyPerformance]:
        """Get the best performing strategy for a task cluster.

        Args:
            task_type: Type of task
            complexity: Complexity level
            domain: Domain

        Returns:
            Best strategy for this cluster, or None if no data
        """
        cluster_key = f"{task_type}_{complexity}_{domain}"

        performances = self._strategy_performance.get(cluster_key, [])
        if not performances:
            return None

        # Sort by success rate, then by quality score
        sorted_performances = sorted(
            performances,
            key=lambda p: (p.success_rate, p.avg_quality_score),
            reverse=True,
        )

        return sorted_performances[0] if sorted_performances else None

    def identify_optimal_strategies(self) -> Dict[str, StrategyPerformance]:
        """Identify optimal strategy for each task type/complexity/domain combination.

        Returns:
            Dict mapping cluster key to optimal strategy
        """
        optimal = {}

        for cluster_key, performances in self._strategy_performance.items():
            if not performances:
                continue

            # Sort by effectiveness (success_rate * avg_quality)
            sorted_perfs = sorted(
                performances,
                key=lambda p: p.success_rate * p.avg_quality_score,
                reverse=True,
            )

            optimal[cluster_key] = sorted_perfs[0]

        self._strategy_recommendations = optimal
        return optimal

    def extract_strategy_insights(self) -> List[str]:
        """Extract key insights about decomposition strategies.

        Returns:
            List of actionable insights
        """
        insights = []

        if not self._strategy_recommendations:
            self.identify_optimal_strategies()

        for cluster_key, strategy in self._strategy_recommendations.items():
            if strategy.confidence < 0.6:
                continue

            cluster_parts = cluster_key.split("_")
            task_type, complexity, domain = (
                cluster_parts[0],
                int(cluster_parts[1]),
                cluster_parts[2],
            )

            # Insight 1: Recommended strategy
            if strategy.success_rate > 0.85:
                insights.append(
                    f"Strategy {strategy.strategy_id} highly effective for {task_type} "
                    f"(complexity={complexity}, domain={domain}): "
                    f"success_rate={strategy.success_rate:.1%}, "
                    f"quality={strategy.avg_quality_score:.2f}"
                )

            # Insight 2: Problematic combinations
            if strategy.success_rate < 0.6 and strategy.execution_count > 3:
                insights.append(
                    f"⚠️ Strategy {strategy.strategy_id} struggles with {task_type} "
                    f"(complexity={complexity}): only {strategy.success_rate:.1%} success rate"
                )

            # Insight 3: Duration estimation accuracy
            if abs(strategy.avg_duration_variance_pct) > 30:
                insights.append(
                    f"Duration variance high for {task_type} (complexity={complexity}): "
                    f"avg {abs(strategy.avg_duration_variance_pct):.0f}% off estimates"
                )

        return insights

    def get_strategy_conditions(
        self,
        strategy_id: int,
    ) -> Dict:
        """Get optimal conditions for using a specific strategy.

        Args:
            strategy_id: Strategy ID

        Returns:
            Dict with conditions where strategy works best
        """
        performances = []
        for perfs in self._strategy_performance.values():
            performances.extend([p for p in perfs if p.strategy_id == strategy_id])

        if not performances:
            return {}

        # Identify patterns
        successful = [p for p in performances if p.success_rate > 0.8]
        avg_complexity = (
            sum(p.complexity for p in successful) / len(successful) if successful else 5
        )

        task_types = set(p.task_type for p in successful)
        domains = set(p.domain for p in successful)

        conditions = {
            "strategy_id": strategy_id,
            "best_for_task_types": list(task_types),
            "best_for_domains": list(domains),
            "optimal_complexity_range": (
                (
                    int(min(p.complexity for p in successful)),
                    int(max(p.complexity for p in successful)),
                )
                if successful
                else (1, 10)
            ),
            "overall_success_rate": (
                sum(p.success_rate for p in successful) / len(successful) if successful else 0.0
            ),
            "execution_count": sum(p.execution_count for p in successful),
        }

        return conditions

    def compare_strategies_for_task_type(
        self,
        task_type: str,
    ) -> List[Tuple[int, float]]:
        """Compare strategies for a given task type.

        Args:
            task_type: Type of task

        Returns:
            List of (strategy_id, effectiveness_score) tuples sorted by effectiveness
        """
        matching = []

        for cluster_key, performances in self._strategy_performance.items():
            if not cluster_key.startswith(task_type):
                continue

            for perf in performances:
                score = perf.success_rate * perf.avg_quality_score
                matching.append((perf.strategy_id, score))

        # Aggregate by strategy
        strategy_scores: Dict[int, List[float]] = defaultdict(list)
        for strategy_id, score in matching:
            strategy_scores[strategy_id].append(score)

        # Average scores per strategy
        strategy_avg = [
            (strategy_id, sum(scores) / len(scores))
            for strategy_id, scores in strategy_scores.items()
        ]

        # Sort by effectiveness
        strategy_avg.sort(key=lambda x: x[1], reverse=True)
        return strategy_avg
