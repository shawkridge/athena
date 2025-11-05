"""
Learning Monitor Agent

Autonomous agent for tracking encoding effectiveness and optimizing learning strategies.
Monitors long-term learning effectiveness, identifies optimal patterns, and recommends strategy improvements.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict


class LearningStrategy(Enum):
    """Learning strategy types"""
    SPACED_REPETITION = "spaced_repetition"
    ACTIVE_RECALL = "active_recall"
    ELABORATION = "elaboration"
    INTERLEAVING = "interleaving"
    CHUNKING = "chunking"
    MULTI_SENSORY = "multi_sensory"
    SCENARIO_BASED = "scenario_based"
    PEER_TEACHING = "peer_teaching"


class PerformanceLevel(Enum):
    """Learning performance levels"""
    EXCELLENT = (0.85, 1.0)
    GOOD = (0.70, 0.85)
    ADEQUATE = (0.55, 0.70)
    NEEDS_IMPROVEMENT = (0.30, 0.55)
    CRITICAL = (0.0, 0.30)


@dataclass
class LearningEvent:
    """A single learning event"""
    event_id: str
    timestamp: str
    strategy: LearningStrategy
    domain: str
    content: str
    encoding_type: str  # "episodic", "semantic", "procedural", "meta"
    recall_attempts: int = 0
    successful_recalls: int = 0
    time_to_recall_ms: int = 0
    confidence: float = 0.5


@dataclass
class LearningMetrics:
    """Metrics for learning performance"""
    domain: str
    strategy: LearningStrategy
    total_events: int = 0
    successful_recalls: int = 0
    average_confidence: float = 0.0
    encoding_effectiveness: float = 0.0  # Recall success rate
    retention_rate: float = 0.0  # Percentage of events retained over time
    average_recall_speed_ms: int = 0
    performance_level: PerformanceLevel = PerformanceLevel.ADEQUATE
    trend: str = "stable"  # "improving", "declining", "stable"


@dataclass
class StrategyRecommendation:
    """Recommendation for learning strategy optimization"""
    current_strategy: LearningStrategy
    recommended_strategy: LearningStrategy
    confidence: float
    reasoning: str
    expected_improvement: float  # 0.0-1.0
    implementation_complexity: str  # "low", "medium", "high"
    estimated_impact_days: int


@dataclass
class LearningCurve:
    """Learning curve analysis"""
    domain: str
    strategy: LearningStrategy
    timeframe_days: int
    initial_performance: float
    current_performance: float
    trajectory: str  # "accelerating", "plateau", "declining"
    learning_rate: float  # per day
    estimated_mastery_days: int
    confidence_in_estimate: float


class LearningMonitor:
    """
    Autonomous agent for monitoring and optimizing learning.

    Capabilities:
    - Track encoding effectiveness across domains
    - Analyze learning curves and performance trends
    - Compare strategy effectiveness
    - Identify optimal learning patterns
    - Recommend strategy improvements
    - Predict mastery timelines
    - Monitor cognitive load impact
    """

    def __init__(self, database, mcp_client):
        """Initialize learning monitor

        Args:
            database: Database connection for storage
            mcp_client: MCP client for tool operations
        """
        self.db = database
        self.mcp = mcp_client
        self.events: Dict[str, LearningEvent] = {}
        self.metrics: Dict[Tuple[str, str], LearningMetrics] = {}
        self.recommendations: List[StrategyRecommendation] = []
        self.learning_curves: Dict[str, LearningCurve] = {}
        self.monitoring_history: List[Dict[str, Any]] = []

    async def analyze_learning_effectiveness(
        self,
        timeframe_days: int = 30,
        domain_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze encoding effectiveness over time.

        Args:
            timeframe_days: Number of days to analyze
            domain_filter: Optional domain to focus on

        Returns:
            Effectiveness analysis with metrics and trends
        """
        result = {
            "timeframe_days": timeframe_days,
            "success": False,
            "analysis_period": {
                "start": (datetime.utcnow() - timedelta(days=timeframe_days)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "domains_analyzed": [],
            "overall_metrics": {},
            "strategy_comparison": {},
            "performance_levels": {},
            "recommendations": [],
            "errors": []
        }

        try:
            # Filter events by timeframe
            recent_events = self._filter_events_by_timeframe(timeframe_days)

            # Group by domain and strategy
            domain_strategy_events = self._group_events(recent_events, domain_filter)

            # Calculate metrics for each domain-strategy combination
            metrics_list = []
            for (domain, strategy), events in domain_strategy_events.items():
                metrics = self._calculate_metrics(domain, strategy, events)
                self.metrics[(domain, strategy)] = metrics
                metrics_list.append(metrics)

                result["domains_analyzed"].append({
                    "domain": domain,
                    "strategy": strategy,
                    "event_count": metrics.total_events,
                    "effectiveness": metrics.encoding_effectiveness,
                    "performance_level": metrics.performance_level.name,
                    "trend": metrics.trend
                })

            # Overall metrics
            if metrics_list:
                overall_effectiveness = sum(m.encoding_effectiveness for m in metrics_list) / len(metrics_list)
                overall_retention = sum(m.retention_rate for m in metrics_list) / len(metrics_list)
                overall_confidence = sum(m.average_confidence for m in metrics_list) / len(metrics_list)

                result["overall_metrics"] = {
                    "effectiveness": overall_effectiveness,
                    "retention_rate": overall_retention,
                    "average_confidence": overall_confidence,
                    "total_events": sum(m.total_events for m in metrics_list),
                    "success_rate": overall_effectiveness
                }

            # Strategy comparison
            strategy_performance = self._compare_strategies(metrics_list)
            result["strategy_comparison"] = strategy_performance

            # Performance levels
            result["performance_levels"] = {
                m.domain: {
                    "level": m.performance_level.name,
                    "score": m.encoding_effectiveness,
                    "strategy": m.strategy.value
                }
                for m in metrics_list
            }

            # Generate recommendations
            recommendations = await self._generate_recommendations(metrics_list)
            result["recommendations"] = [
                {
                    "current_strategy": r.current_strategy.value,
                    "recommended_strategy": r.recommended_strategy.value,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                    "expected_improvement": r.expected_improvement,
                    "domain": r.reasoning.split("domain")[0] if "domain" in r.reasoning else "general"
                }
                for r in recommendations
            ]
            self.recommendations = recommendations

            result["success"] = True
            self.monitoring_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "timeframe": timeframe_days,
                "domains_count": len(set(m.domain for m in metrics_list)),
                "overall_effectiveness": result["overall_metrics"].get("effectiveness", 0.0)
            })

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            result["error_type"] = type(e).__name__

        return result

    async def analyze_learning_curves(
        self,
        domain: Optional[str] = None,
        days_back: int = 60
    ) -> Dict[str, Any]:
        """
        Analyze learning curves to predict mastery.

        Args:
            domain: Optional domain to focus on
            days_back: Days of history to analyze

        Returns:
            Learning curve analysis with trajectory predictions
        """
        result = {
            "domain": domain or "all",
            "success": False,
            "curves": [],
            "mastery_predictions": {},
            "acceleration_analysis": {},
            "errors": []
        }

        try:
            # Get events for analysis
            events = self._filter_events_by_timeframe(days_back)

            # Analyze by domain and strategy
            domain_strategy_events = self._group_events(events, domain)

            for (dom, strategy), strategy_events in domain_strategy_events.items():
                # Build learning curve
                curve = self._analyze_learning_curve(dom, strategy, strategy_events)
                self.learning_curves[f"{dom}_{strategy.value}"] = curve

                result["curves"].append({
                    "domain": dom,
                    "strategy": strategy.value,
                    "initial_performance": curve.initial_performance,
                    "current_performance": curve.current_performance,
                    "learning_rate": curve.learning_rate,
                    "trajectory": curve.trajectory,
                    "estimated_mastery_days": curve.estimated_mastery_days,
                    "confidence": curve.confidence_in_estimate
                })

                # Mastery prediction
                if curve.trajectory == "accelerating":
                    prediction_status = "on_track"
                elif curve.trajectory == "plateau":
                    prediction_status = "needs_intervention"
                else:
                    prediction_status = "declining"

                result["mastery_predictions"][dom] = {
                    "strategy": strategy.value,
                    "days_to_mastery": curve.estimated_mastery_days,
                    "status": prediction_status,
                    "confidence": curve.confidence_in_estimate
                }

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        return result

    async def optimize_learning_strategy(
        self,
        domain: str,
        current_strategy: str,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize learning strategy for a domain.

        Args:
            domain: Domain to optimize for
            current_strategy: Current strategy name
            constraints: Optional constraints (time, resources, etc.)

        Returns:
            Strategy optimization recommendation
        """
        result = {
            "domain": domain,
            "current_strategy": current_strategy,
            "success": False,
            "recommended_strategy": None,
            "optimization_plan": None,
            "expected_improvements": {},
            "errors": []
        }

        try:
            # Analyze current strategy performance
            metrics = self.metrics.get((domain, current_strategy))

            if not metrics:
                result["errors"].append(f"No metrics found for {domain}/{current_strategy}")
                result["success"] = False
                return result

            # Find alternative strategies
            alternative_metrics = [
                m for (d, s), m in self.metrics.items()
                if d == domain and s != current_strategy
            ]

            # Compare effectiveness
            best_alternative = max(
                alternative_metrics,
                key=lambda m: m.encoding_effectiveness,
                default=None
            )

            if best_alternative:
                improvement = best_alternative.encoding_effectiveness - metrics.encoding_effectiveness

                result["recommended_strategy"] = best_alternative.strategy.value
                result["expected_improvements"] = {
                    "encoding_effectiveness": improvement,
                    "retention_rate": best_alternative.retention_rate - metrics.retention_rate,
                    "recall_speed_ms": metrics.average_recall_speed_ms - best_alternative.average_recall_speed_ms
                }

                # Create optimization plan
                result["optimization_plan"] = {
                    "phase_1_days": 7,
                    "phase_1_action": f"Introduce {best_alternative.strategy.value}",
                    "phase_2_days": 14,
                    "phase_2_action": "Evaluate new strategy effectiveness",
                    "success_criteria": improvement > 0.1,
                    "fallback": f"Return to {current_strategy} if no improvement"
                }

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        return result

    # Private helper methods

    def _filter_events_by_timeframe(self, days: int) -> List[LearningEvent]:
        """Filter events within timeframe"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        return [
            event for event in self.events.values()
            if event.timestamp >= cutoff_iso
        ]

    def _group_events(
        self,
        events: List[LearningEvent],
        domain_filter: Optional[str] = None
    ) -> Dict[Tuple[str, LearningStrategy], List[LearningEvent]]:
        """Group events by domain and strategy"""
        grouped = defaultdict(list)

        for event in events:
            if domain_filter and event.domain != domain_filter:
                continue

            key = (event.domain, event.strategy)
            grouped[key].append(event)

        return grouped

    def _calculate_metrics(
        self,
        domain: str,
        strategy: LearningStrategy,
        events: List[LearningEvent]
    ) -> LearningMetrics:
        """Calculate metrics for domain-strategy combination"""
        metrics = LearningMetrics(
            domain=domain,
            strategy=strategy,
            total_events=len(events)
        )

        if not events:
            return metrics

        # Calculate success metrics
        total_recalls = sum(e.recall_attempts for e in events)
        successful_recalls = sum(e.successful_recalls for e in events)

        metrics.successful_recalls = successful_recalls
        metrics.encoding_effectiveness = successful_recalls / max(total_recalls, 1)

        # Average confidence
        metrics.average_confidence = sum(e.confidence for e in events) / len(events)

        # Retention rate (events recalled at least once)
        retained = sum(1 for e in events if e.recall_attempts > 0)
        metrics.retention_rate = retained / len(events)

        # Average recall speed
        if successful_recalls > 0:
            recall_speeds = [e.time_to_recall_ms for e in events if e.successful_recalls > 0]
            metrics.average_recall_speed_ms = sum(recall_speeds) // len(recall_speeds)

        # Performance level
        for level in PerformanceLevel:
            min_perf, max_perf = level.value
            if min_perf <= metrics.encoding_effectiveness <= max_perf:
                metrics.performance_level = level
                break

        # Trend detection (simplified)
        if len(events) >= 2:
            early_events = events[:len(events)//2]
            late_events = events[len(events)//2:]

            early_effectiveness = sum(e.successful_recalls for e in early_events) / max(
                sum(e.recall_attempts for e in early_events), 1
            )
            late_effectiveness = sum(e.successful_recalls for e in late_events) / max(
                sum(e.recall_attempts for e in late_events), 1
            )

            if late_effectiveness > early_effectiveness + 0.1:
                metrics.trend = "improving"
            elif late_effectiveness < early_effectiveness - 0.1:
                metrics.trend = "declining"

        return metrics

    def _compare_strategies(self, metrics_list: List[LearningMetrics]) -> Dict[str, Any]:
        """Compare effectiveness of different strategies"""
        comparison = {}

        for strategy in LearningStrategy:
            strategy_metrics = [m for m in metrics_list if m.strategy == strategy]

            if strategy_metrics:
                avg_effectiveness = sum(m.encoding_effectiveness for m in strategy_metrics) / len(strategy_metrics)
                avg_retention = sum(m.retention_rate for m in strategy_metrics) / len(strategy_metrics)

                comparison[strategy.value] = {
                    "effectiveness": avg_effectiveness,
                    "retention_rate": avg_retention,
                    "domains_used": len(strategy_metrics),
                    "rank": 0  # Will be set after comparison
                }

        # Rank strategies
        sorted_strategies = sorted(
            comparison.items(),
            key=lambda x: x[1]["effectiveness"],
            reverse=True
        )

        for rank, (strategy, data) in enumerate(sorted_strategies, 1):
            comparison[strategy]["rank"] = rank

        return comparison

    async def _generate_recommendations(
        self,
        metrics_list: List[LearningMetrics]
    ) -> List[StrategyRecommendation]:
        """Generate strategy recommendations"""
        recommendations = []

        # Find underperforming domain-strategy combinations
        for metrics in metrics_list:
            if metrics.performance_level in [PerformanceLevel.NEEDS_IMPROVEMENT, PerformanceLevel.CRITICAL]:
                # Find better strategy for this domain
                better_metrics = [
                    m for m in metrics_list
                    if m.domain == metrics.domain and
                    m.encoding_effectiveness > metrics.encoding_effectiveness + 0.15
                ]

                if better_metrics:
                    best = max(better_metrics, key=lambda m: m.encoding_effectiveness)

                    rec = StrategyRecommendation(
                        current_strategy=metrics.strategy,
                        recommended_strategy=best.strategy,
                        confidence=min(best.encoding_effectiveness, 0.95),
                        reasoning=f"Switch to {best.strategy.value} for {metrics.domain} domain",
                        expected_improvement=best.encoding_effectiveness - metrics.encoding_effectiveness,
                        implementation_complexity="medium",
                        estimated_impact_days=7
                    )
                    recommendations.append(rec)

        return recommendations

    def _analyze_learning_curve(
        self,
        domain: str,
        strategy: LearningStrategy,
        events: List[LearningEvent]
    ) -> LearningCurve:
        """Analyze learning curve for domain-strategy"""
        curve = LearningCurve(
            domain=domain,
            strategy=strategy,
            timeframe_days=60,
            initial_performance=0.0,
            current_performance=0.0,
            trajectory="stable",
            learning_rate=0.0,
            estimated_mastery_days=30,
            confidence_in_estimate=0.5
        )

        if not events:
            return curve

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Initial performance (first 25%)
        initial_count = max(1, len(sorted_events) // 4)
        initial_events = sorted_events[:initial_count]
        curve.initial_performance = sum(e.successful_recalls for e in initial_events) / max(
            sum(e.recall_attempts for e in initial_events), 1
        )

        # Current performance (last 25%)
        current_events = sorted_events[-initial_count:]
        curve.current_performance = sum(e.successful_recalls for e in current_events) / max(
            sum(e.recall_attempts for e in current_events), 1
        )

        # Learning rate (per day)
        if len(sorted_events) >= 2:
            time_span = len(sorted_events) / max(len(sorted_events), 1)
            perf_change = curve.current_performance - curve.initial_performance
            curve.learning_rate = perf_change / max(time_span, 1)

            # Trajectory
            if curve.learning_rate > 0.01:
                curve.trajectory = "accelerating"
            elif curve.learning_rate < -0.01:
                curve.trajectory = "declining"
            else:
                curve.trajectory = "plateau"

            # Estimate mastery (reaching 0.9)
            if curve.learning_rate > 0:
                remaining = 0.9 - curve.current_performance
                curve.estimated_mastery_days = int(remaining / max(curve.learning_rate, 0.001))
                curve.confidence_in_estimate = min(abs(curve.learning_rate) * 100, 0.95)

        return curve
