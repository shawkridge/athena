"""
Orchestration Bridge: Unified Goal + Execution State Management

Manages workflow orchestration with goal awareness:
- Multi-goal workflow management
- Goal switching with cost analysis
- Conflict resolution automation
- Unified goal-level metrics (not just task-level)
- Strategy-aware planning pipeline
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from .models import Goal, GoalStatus, GoalType, TaskSwitch, StrategyType
from .hierarchy import GoalHierarchy
from .strategy import StrategySelector
from .conflict import ConflictResolver
from .progress import ProgressMonitor
from .agent_bridge import ExecutiveAgentBridge


class WorkflowState(str, Enum):
    """State of goal-oriented workflow."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    SWITCHING = "switching"
    VALIDATING = "validating"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class OrchestrationBridge:
    """
    Unified orchestration of goals and execution.

    Responsibilities:
    - Manage active goals and task switching
    - Coordinate strategy selection across goals
    - Track goal progress through agent execution
    - Resolve goal conflicts automatically
    - Provide goal-level metrics to agents
    - Enable multi-goal parallel execution
    """

    def __init__(
        self,
        hierarchy: GoalHierarchy,
        strategy_selector: StrategySelector,
        conflict_resolver: ConflictResolver,
        progress_tracker: ProgressMonitor,
    ):
        """
        Initialize orchestration bridge.

        Args:
            hierarchy: Goal hierarchy manager
            strategy_selector: Strategy selection system
            conflict_resolver: Conflict resolution system
            progress_tracker: Progress tracking system
        """
        self.hierarchy = hierarchy
        self.strategy_selector = strategy_selector
        self.conflict_resolver = conflict_resolver
        self.progress_tracker = progress_tracker
        self.agent_bridge = ExecutiveAgentBridge()

        # State tracking
        self.active_goals: Set[int] = set()
        self.current_goal: Optional[int] = None
        self.workflow_state = WorkflowState.IDLE
        self.switch_history: List[TaskSwitch] = []

        # Integration with agents
        self.planner_queue: List[Tuple[Goal, Dict]] = []  # (goal, decomposition_context)
        self.executor_queue: List[Tuple[Goal, "ExecutionPlan"]] = []  # (goal, plan)
        self.monitor_state: Dict[int, Dict] = {}  # goal_id → health metrics

    def activate_goal(self, goal_id: int, from_goal_id: Optional[int] = None) -> Dict:
        """
        Activate a goal and switch workflow context.

        Args:
            goal_id: Goal to activate
            from_goal_id: Previous goal (if switching)

        Returns:
            Activation result with switch cost analysis
        """
        goal = self.hierarchy.get_goal(goal_id)
        if not goal:
            return {"status": "error", "error": f"Goal {goal_id} not found"}

        # Handle goal switching
        if self.current_goal and self.current_goal != goal_id:
            switch_result = self._switch_goal(self.current_goal, goal_id)
            if not switch_result.get("success"):
                return switch_result

        # Update state
        self.current_goal = goal_id
        self.active_goals.add(goal_id)
        self.workflow_state = WorkflowState.PLANNING

        # Update goal status
        goal.status = GoalStatus.ACTIVE
        self.hierarchy.update_goal(goal)

        return {
            "status": "success",
            "goal_id": goal_id,
            "goal_text": goal.goal_text,
            "priority": goal.priority,
            "progress": goal.progress,
        }

    def _switch_goal(self, from_id: int, to_id: int) -> Dict:
        """
        Switch between goals with cost analysis.

        Args:
            from_id: Source goal
            to_id: Target goal

        Returns:
            Switch result with cost metrics
        """
        from_goal = self.hierarchy.get_goal(from_id)
        to_goal = self.hierarchy.get_goal(to_id)

        if not from_goal or not to_goal:
            return {"status": "error", "error": "Invalid goal IDs"}

        # Calculate switch cost (context restoration time)
        switch_cost_ms = self._calculate_switch_cost(from_goal, to_goal)

        # Record switch
        switch_event = TaskSwitch(
            id=None,
            project_id=from_goal.project_id,
            from_goal_id=from_id,
            to_goal_id=to_id,
            switch_cost_ms=switch_cost_ms,
            reason="goal_switching",
            switched_at=datetime.now(),
            context_snapshot=None,  # Could capture state here
        )
        self.switch_history.append(switch_event)

        # Pause source goal
        from_goal.status = GoalStatus.SUSPENDED
        self.hierarchy.update_goal(from_goal)

        return {
            "status": "success",
            "from_goal": from_id,
            "to_goal": to_id,
            "switch_cost_ms": switch_cost_ms,
            "switch_cost_minutes": switch_cost_ms / 60000.0,
        }

    def _calculate_switch_cost(self, from_goal: Goal, to_goal: Goal) -> int:
        """
        Calculate context switching cost in milliseconds.

        Factors:
        - Goal similarity (same domain = lower cost)
        - Priority difference (high to low = higher cost)
        - Dependency distance (closely related = lower cost)
        """
        cost = 300000  # Base: 5 minutes

        # Similarity factor
        if from_goal.goal_type == to_goal.goal_type:
            cost *= 0.7  # 30% reduction if same type

        # Priority factor
        priority_diff = abs(from_goal.priority - to_goal.priority)
        cost *= (1.0 + priority_diff * 0.05)  # Max 50% increase

        # Dependency factor
        if to_goal.parent_goal_id == from_goal.id:
            cost *= 0.5  # 50% reduction if child of current

        return int(cost)

    def check_goal_conflicts(self, project_id: int) -> Dict:
        """
        Check for conflicts between active goals.

        Returns:
            Conflict analysis and resolution suggestions
        """
        goals = self.hierarchy.get_active_goals(project_id)
        conflicts = self.conflict_resolver.detect_conflicts(goals)

        return {
            "project_id": project_id,
            "active_goal_count": len(goals),
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "resolution_suggested": True,
        }

    def resolve_conflicts_auto(self, project_id: int) -> Dict:
        """
        Automatically resolve conflicts between goals.

        Uses priority, deadline, and dependency analysis to make decisions.

        Returns:
            Resolution result with goals reordered/suspended
        """
        goals = self.hierarchy.get_active_goals(project_id)
        conflicts = self.conflict_resolver.detect_conflicts(goals)

        if not conflicts:
            return {"status": "success", "resolved": 0}

        resolved_count = 0
        for conflict in conflicts:
            # Try to resolve
            if conflict["type"] == "resource_contention":
                # Suspend lower-priority goal
                lower_priority_id = max(
                    conflict["goal_ids"],
                    key=lambda gid: (
                        self.hierarchy.get_goal(gid).priority
                        if self.hierarchy.get_goal(gid)
                        else 0
                    ),
                )
                goal = self.hierarchy.get_goal(lower_priority_id)
                if goal:
                    goal.status = GoalStatus.SUSPENDED
                    self.hierarchy.update_goal(goal)
                    resolved_count += 1

            elif conflict["type"] == "dependency_cycle":
                # Log for human review
                pass

        return {
            "status": "success",
            "resolved": resolved_count,
            "conflicts": conflicts,
        }

    def prepare_goal_for_planner(self, goal_id: int) -> Dict:
        """
        Prepare goal for Planner Agent with strategy context.

        Converts goal to decomposition context that Planner can consume.

        Args:
            goal_id: Goal to prepare

        Returns:
            Decomposition context for Planner Agent
        """
        goal = self.hierarchy.get_goal(goal_id)
        if not goal:
            return {"status": "error", "error": f"Goal {goal_id} not found"}

        # Get historical strategy success rates
        success_rates = {
            strategy: self.agent_bridge.get_strategy_success_rate(goal.goal_type, strategy)
            for strategy in list(StrategyType)
        }

        # Get decomposition context
        context = self.agent_bridge.goal_to_decomposition_context(
            goal,
            historical_success_rates=success_rates,
        )

        return {
            "status": "success",
            "goal_id": goal_id,
            "goal_text": goal.goal_text,
            "strategy": context.strategy.value,
            "confidence": context.confidence,
            "reasoning": context.reasoning,
            "alternative_strategies": [s.value for s in context.alternative_strategies],
        }

    def record_plan_execution(
        self,
        goal_id: int,
        plan_id: int,
        steps_completed: int,
        total_steps: int,
        errors: int,
        blockers: int,
    ) -> Dict:
        """
        Record plan execution progress for goal tracking.

        Args:
            goal_id: Goal being executed
            plan_id: Execution plan ID
            steps_completed: Number of completed steps
            total_steps: Total steps in plan
            errors: Error count
            blockers: Blocker count

        Returns:
            Updated goal progress and health metrics
        """
        goal = self.hierarchy.get_goal(goal_id)
        if not goal:
            return {"status": "error"}

        # Calculate progress
        progress = steps_completed / total_steps if total_steps > 0 else 0.0
        goal.progress = progress
        self.hierarchy.update_goal(goal)

        # Update monitor state
        self.monitor_state[goal_id] = {
            "plan_id": plan_id,
            "progress": progress,
            "steps_completed": steps_completed,
            "total_steps": total_steps,
            "errors": errors,
            "blockers": blockers,
            "last_updated": datetime.now().isoformat(),
        }

        # Check if on track
        on_track = goal.is_on_track()

        return {
            "status": "success",
            "goal_id": goal_id,
            "progress": progress,
            "on_track": on_track,
            "health": {
                "errors": errors,
                "blockers": blockers,
                "steps_completed": steps_completed,
            },
        }

    def mark_goal_completed(
        self,
        goal_id: int,
        outcome: str,  # "success", "partial", "failure"
        notes: str = "",
    ) -> Dict:
        """
        Mark goal as completed with outcome.

        Args:
            goal_id: Goal to complete
            outcome: Result of goal execution
            notes: Completion notes

        Returns:
            Completion result
        """
        goal = self.hierarchy.get_goal(goal_id)
        if not goal:
            return {"status": "error"}

        # Update goal
        goal.status = GoalStatus.COMPLETED if outcome == "success" else GoalStatus.FAILED
        goal.completed_at = datetime.now()
        self.hierarchy.update_goal(goal)

        # Remove from active
        if goal_id in self.active_goals:
            self.active_goals.discard(goal_id)

        # Clear from current if was active
        if self.current_goal == goal_id:
            self.current_goal = None
            self.workflow_state = WorkflowState.IDLE

        return {
            "status": "success",
            "goal_id": goal_id,
            "outcome": outcome,
            "completed_at": goal.completed_at.isoformat(),
            "total_time": str(goal.completed_at - goal.created_at),
        }

    def get_workflow_status(self) -> Dict:
        """
        Get comprehensive workflow status.

        Returns:
            Current workflow state with metrics
        """
        return {
            "workflow_state": self.workflow_state.value,
            "current_goal": self.current_goal,
            "active_goals": list(self.active_goals),
            "goal_count": len(self.active_goals),
            "recent_switches": len(self.switch_history),
            "avg_switch_cost_ms": (
                sum(s.switch_cost_ms for s in self.switch_history) / len(self.switch_history)
                if self.switch_history
                else 0
            ),
            "monitor_tracked": len(self.monitor_state),
        }

    def get_goal_priority_ranking(self, project_id: int) -> List[Dict]:
        """
        Get goals ranked by priority considering deadline and dependencies.

        Args:
            project_id: Project to analyze

        Returns:
            Ranked list of goals with scores
        """
        goals = self.hierarchy.get_active_goals(project_id)
        scored = []

        for goal in goals:
            # Calculate composite score
            score = self._calculate_goal_priority_score(goal)
            scored.append({
                "goal_id": goal.id,
                "goal_text": goal.goal_text,
                "priority": goal.priority,
                "score": score,
                "on_track": goal.is_on_track(),
                "days_to_deadline": goal.days_to_deadline(),
            })

        # Sort by score descending
        return sorted(scored, key=lambda g: g["score"], reverse=True)

    def _calculate_goal_priority_score(self, goal: Goal) -> float:
        """Calculate composite priority score for goal."""
        score = 0.0

        # Base priority (40%)
        score += (goal.priority / 10.0) * 0.40

        # Deadline urgency (35%)
        days_left = goal.days_to_deadline()
        if days_left is not None:
            if days_left <= 3:
                score += 0.35
            elif days_left <= 7:
                score += 0.25
            elif days_left <= 14:
                score += 0.10

        # Progress toward completion (15%)
        score += goal.progress * 0.15

        # On-track bonus (10%)
        if goal.is_on_track():
            score += 0.05  # Slight boost for staying on track
        else:
            score -= 0.05  # Penalty for falling behind

        return min(score, 1.0)  # Clamp to [0, 1]

    def recommend_next_goal(self, project_id: int) -> Optional[Dict]:
        """
        Recommend next goal to activate based on priority and state.

        Args:
            project_id: Project to analyze

        Returns:
            Recommended goal or None
        """
        ranked = self.get_goal_priority_ranking(project_id)
        if not ranked:
            return None

        # Get top candidate (excluding current)
        for goal_info in ranked:
            if goal_info["goal_id"] != self.current_goal:
                return goal_info

        return None
