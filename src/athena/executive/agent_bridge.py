"""
Executive Function ↔ Agent System Bridge Layer

Converts between Executive Function models (Goals, Strategies) and Agent models
(ExecutionPlans, Decomposition Strategies).

Enables goal-aware task decomposition and strategy-informed planning.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .models import (
    Goal,
    GoalType,
    StrategyType,
    ProgressMilestone,
    StrategyRecommendation,
)


@dataclass
class GoalDecompositionContext:
    """Context for goal-aware task decomposition."""

    goal: Goal
    strategy: StrategyType
    confidence: float
    reasoning: str
    alternative_strategies: List[StrategyType] = None

    def __post_init__(self):
        if self.alternative_strategies is None:
            self.alternative_strategies = []


class ExecutiveAgentBridge:
    """
    Bridge between Executive Function and Agent System.

    Converts Goals → ExecutionPlans using strategy-aware decomposition.
    Tracks goal progress through plan execution.
    Learns which strategies work best for which goal types.
    """

    # Strategy to decomposition type mapping
    STRATEGY_TO_DECOMPOSITION = {
        StrategyType.TOP_DOWN: "HIERARCHICAL",
        StrategyType.BOTTOM_UP: "ITERATIVE",
        StrategyType.SPIKE: "SPIKE",
        StrategyType.INCREMENTAL: "INCREMENTAL",
        StrategyType.PARALLEL: "PARALLEL",
        StrategyType.SEQUENTIAL: "SEQUENTIAL",
        StrategyType.DEADLINE_DRIVEN: "DEADLINE_DRIVEN",
        StrategyType.QUALITY_FIRST: "QUALITY_FIRST",
        StrategyType.COLLABORATION: "COLLABORATIVE",
        StrategyType.EXPERIMENTAL: "EXPLORATORY",
    }

    # Goal characteristics that influence strategy
    GOAL_CHARACTERISTICS = {
        GoalType.PRIMARY: {
            "preferred_strategies": [
                StrategyType.TOP_DOWN,
                StrategyType.DEADLINE_DRIVEN,
                StrategyType.PARALLEL,
            ],
            "min_milestone_count": 3,
            "require_external_validation": True,
        },
        GoalType.SUBGOAL: {
            "preferred_strategies": [
                StrategyType.BOTTOM_UP,
                StrategyType.INCREMENTAL,
                StrategyType.SEQUENTIAL,
            ],
            "min_milestone_count": 2,
            "require_external_validation": False,
        },
        GoalType.MAINTENANCE: {
            "preferred_strategies": [
                StrategyType.SEQUENTIAL,
                StrategyType.QUALITY_FIRST,
                StrategyType.COLLABORATION,
            ],
            "min_milestone_count": 1,
            "require_external_validation": False,
        },
    }

    def __init__(self):
        """Initialize bridge."""
        self.goal_strategy_history: Dict[int, List[StrategyRecommendation]] = {}

    def goal_to_decomposition_context(
        self,
        goal: Goal,
        available_strategies: Optional[List[StrategyType]] = None,
        historical_success_rates: Optional[Dict[StrategyType, float]] = None,
    ) -> GoalDecompositionContext:
        """
        Convert Goal to decomposition context for Planner Agent.

        Args:
            goal: Executive Goal to decompose
            available_strategies: Strategies available for this goal (uses all if None)
            historical_success_rates: Success rate of each strategy for this goal type

        Returns:
            GoalDecompositionContext with selected strategy and reasoning
        """
        if available_strategies is None:
            available_strategies = list(StrategyType)

        if historical_success_rates is None:
            historical_success_rates = {}

        # Get preferred strategies for goal type
        characteristics = self.GOAL_CHARACTERISTICS.get(
            goal.goal_type,
            self.GOAL_CHARACTERISTICS[GoalType.SUBGOAL],
        )
        preferred = characteristics.get("preferred_strategies", [])

        # Rank strategies by: (1) historical success, (2) preference, (3) priority
        ranked_strategies = self._rank_strategies(
            preferred,
            available_strategies,
            goal,
            historical_success_rates,
        )

        selected_strategy = ranked_strategies[0] if ranked_strategies else StrategyType.TOP_DOWN
        confidence = historical_success_rates.get(selected_strategy, 0.7)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            goal,
            selected_strategy,
            confidence,
            ranked_strategies[1:3] if len(ranked_strategies) > 1 else [],
        )

        return GoalDecompositionContext(
            goal=goal,
            strategy=selected_strategy,
            confidence=confidence,
            reasoning=reasoning,
            alternative_strategies=ranked_strategies[1:],
        )

    def _rank_strategies(
        self,
        preferred: List[StrategyType],
        available: List[StrategyType],
        goal: Goal,
        success_rates: Dict[StrategyType, float],
    ) -> List[StrategyType]:
        """
        Rank strategies by effectiveness for this goal.

        Ranking factors:
        1. Historical success rate (40%)
        2. Goal type preference (35%)
        3. Deadline urgency (15%)
        4. Priority level (10%)
        """
        scored = {}

        for strategy in available:
            score = 0.0

            # Historical success rate
            success_rate = success_rates.get(strategy, 0.5)
            score += success_rate * 0.40

            # Goal type preference
            if strategy in preferred:
                score += 0.35
            else:
                score += 0.10  # Still consider non-preferred

            # Deadline urgency
            if goal.is_urgent():
                if strategy in [StrategyType.DEADLINE_DRIVEN, StrategyType.TOP_DOWN]:
                    score += 0.15
            else:
                score += 0.05

            # Priority level (1-10)
            priority_boost = (goal.priority / 10.0) * 0.10
            score += priority_boost

            scored[strategy] = score

        return sorted(scored.keys(), key=lambda s: scored[s], reverse=True)

    def _generate_reasoning(
        self,
        goal: Goal,
        selected: StrategyType,
        confidence: float,
        alternatives: List[StrategyType],
    ) -> str:
        """Generate human-readable reasoning for strategy selection."""
        parts = []

        # Goal characteristics
        parts.append(f"Goal: {goal.goal_text}")
        parts.append(f"Type: {goal.goal_type.value}, Priority: {goal.priority}/10")

        # Strategy rationale
        parts.append(f"Selected: {selected.value} (confidence: {confidence:.1%})")

        # Deadline pressure
        if goal.is_urgent():
            days_left = goal.days_to_deadline()
            parts.append(f"Deadline pressure: {days_left} days left")

        # Progress status
        parts.append(f"Current progress: {goal.progress:.0%}")

        # Alternatives
        if alternatives:
            alt_strs = [s.value for s in alternatives[:2]]
            parts.append(f"Alternatives: {', '.join(alt_strs)}")

        return " | ".join(parts)

    def execution_plan_to_milestones(
        self,
        plan: "ExecutionPlan",  # from agents module
        goal: Goal,
    ) -> List[ProgressMilestone]:
        """
        Convert ExecutionPlan steps to ProgressMilestones for tracking.

        Args:
            plan: ExecutionPlan from Planner Agent
            goal: Goal being executed

        Returns:
            List of ProgressMilestones at key points
        """
        milestones = []

        if not plan.steps:
            return milestones

        # Create milestone at 25%, 50%, 75%, 100%
        step_count = len(plan.steps)
        checkpoint_indices = [
            int(step_count * 0.25),
            int(step_count * 0.50),
            int(step_count * 0.75),
            step_count - 1,
        ]

        for percent, idx in zip([25, 50, 75, 100], checkpoint_indices):
            step = plan.steps[min(idx, len(plan.steps) - 1)]
            milestone = ProgressMilestone(
                id=None,  # Will be assigned by store
                goal_id=goal.id,
                name=f"{percent}% - {step.description[:50]}",
                target_completion=datetime.now()
                + timedelta(milliseconds=plan.estimated_total_duration_ms * (percent / 100.0)),
                is_completed=False,
                completed_at=None,
            )
            milestones.append(milestone)

        return milestones

    def track_strategy_outcome(
        self,
        goal_id: int,
        strategy: StrategyType,
        outcome: str,  # "success", "partial", "failure"
        duration_ms: int,
        notes: str = "",
    ) -> StrategyRecommendation:
        """
        Record outcome of strategy application for learning.

        Args:
            goal_id: Goal being tracked
            strategy: Strategy that was used
            outcome: Result of strategy ("success", "partial", "failure")
            duration_ms: How long it took
            notes: Additional context

        Returns:
            StrategyRecommendation with outcome recorded
        """
        recommendation = StrategyRecommendation(
            id=None,
            strategy_type=strategy,
            goal_id=goal_id,
            confidence=self._confidence_from_outcome(outcome),
            reasoning=f"Applied {strategy.value} strategy. Outcome: {outcome}. {notes}",
            recommended_at=datetime.now(),
            applied_at=datetime.now(),
            outcome=outcome,
        )

        # Track for learning
        if goal_id not in self.goal_strategy_history:
            self.goal_strategy_history[goal_id] = []
        self.goal_strategy_history[goal_id].append(recommendation)

        return recommendation

    def _confidence_from_outcome(self, outcome: str) -> float:
        """Convert outcome to confidence score."""
        mapping = {
            "success": 0.95,
            "partial": 0.65,
            "failure": 0.25,
        }
        return mapping.get(outcome, 0.5)

    def get_strategy_success_rate(
        self,
        goal_type: GoalType,
        strategy: StrategyType,
    ) -> float:
        """
        Get historical success rate of strategy for goal type.

        Args:
            goal_type: Type of goal
            strategy: Strategy to evaluate

        Returns:
            Success rate (0.0-1.0)
        """
        matching = [
            rec
            for goal_id, recs in self.goal_strategy_history.items()
            for rec in recs
            if rec.strategy_type == strategy and rec.outcome == "success"
        ]

        if not matching:
            return 0.6  # Default neutral confidence

        success_count = len([r for r in matching if r.outcome == "success"])
        return success_count / len(matching) if matching else 0.6

    def plan_respects_goal_constraints(
        self,
        plan: "ExecutionPlan",
        goal: Goal,
    ) -> bool:
        """
        Validate that execution plan respects goal constraints.

        Args:
            plan: ExecutionPlan from Planner
            goal: Goal constraints

        Returns:
            True if plan is feasible given goal constraints
        """
        if not goal.estimated_hours:
            return True

        # Check duration
        plan_hours = plan.estimated_total_duration_ms / (1000 * 3600)
        if plan_hours > goal.estimated_hours * 1.5:
            return False  # Plan exceeds estimate by >50%

        # Check deadline feasibility
        if goal.deadline:
            time_available = (goal.deadline - datetime.now()).total_seconds() / 3600
            if plan_hours > time_available:
                return False  # Not enough time

        return True


# Export bridge functions for MCP tools
def create_goal_aware_plan(
    goal: Goal,
    planner_agent,  # PlannerAgent instance
    strategy_selector,  # StrategySelector instance from executive/strategy.py
) -> "ExecutionPlan":
    """
    High-level function to create strategy-aware plan for a goal.

    Args:
        goal: Goal to plan
        planner_agent: Planner agent for decomposition
        strategy_selector: Strategy selector for choosing approach

    Returns:
        ExecutionPlan aligned with goal strategy
    """
    bridge = ExecutiveAgentBridge()

    # Get goal decomposition context
    context = bridge.goal_to_decomposition_context(goal)

    # Call planner with strategy hint
    plan = planner_agent.decompose_task(
        task={
            "id": goal.id,
            "description": goal.goal_text,
            "strategy_hint": context.strategy.value,
            "reasoning": context.reasoning,
        }
    )

    return plan
