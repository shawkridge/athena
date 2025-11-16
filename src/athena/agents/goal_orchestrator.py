"""
Goal Orchestrator Agent

Autonomous agent for goal hierarchy management, activation, and lifecycle tracking.
Manages the complete goal lifecycle with state transitions, dependency tracking,
and context-aware activation.
"""

import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class GoalState(Enum):
    """Goal lifecycle states"""
    PENDING = "pending"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class GoalPriority(Enum):
    """Goal priority levels"""
    CRITICAL = 9
    HIGH = 7
    MEDIUM = 5
    LOW = 3


@dataclass
class GoalMetrics:
    """Metrics for a goal"""
    progress_percent: float = 0.0
    milestones_reached: int = 0
    milestones_total: int = 0
    errors_encountered: int = 0
    blockers_active: int = 0
    health_score: float = 1.0
    velocity: float = 0.0  # tasks per hour


@dataclass
class GoalContext:
    """Context for a goal"""
    goal_id: int
    name: str
    description: str
    state: GoalState
    priority: int
    deadline: Optional[str] = None
    owner: Optional[str] = None
    metrics: GoalMetrics = field(default_factory=GoalMetrics)
    dependencies: List[int] = field(default_factory=list)
    dependent_goals: List[int] = field(default_factory=list)
    created_at: Optional[str] = None
    activated_at: Optional[str] = None
    completed_at: Optional[str] = None


class GoalOrchestrator:
    """
    Autonomous orchestrator for goal management.

    Capabilities:
    - Goal hierarchy construction and maintenance
    - Automatic goal activation with context analysis
    - Progress tracking and milestone detection
    - Dependency graph management
    - Goal state transitions and completion
    """

    def __init__(self, database, mcp_client):
        """Initialize the goal orchestrator

        Args:
            database: Database connection for goal/task storage
            mcp_client: MCP client for tool operations
        """
        self.db = database
        self.mcp = mcp_client
        self.active_goals: Dict[int, GoalContext] = {}
        self.goal_hierarchy: Dict[int, GoalContext] = {}
        self.max_active_goals = 3
        self.deadline_warning_days = 3
        self.context_loss_threshold = 30  # minutes

    async def activate_goal(self, goal_id: int) -> Dict[str, Any]:
        """
        Activate a goal with comprehensive context analysis.

        Args:
            goal_id: Goal to activate

        Returns:
            Activation result with context analysis
        """
        result = {
            "goal_id": goal_id,
            "success": False,
            "analysis": {},
            "warnings": [],
            "errors": []
        }

        try:
            # Load goal context from database
            goal = await self._load_goal(goal_id)
            if not goal:
                result["errors"].append(f"Goal {goal_id} not found")
                return result

            # Check dependencies
            dep_check = await self._check_dependencies(goal)
            if not dep_check["satisfied"]:
                result["warnings"].append(
                    f"Dependency blocker: {dep_check['blocked_by']}"
                )
                result["analysis"]["dependencies"] = dep_check

            # Analyze context switching cost
            switch_cost = await self._analyze_context_switch(goal)
            result["analysis"]["context_switch"] = switch_cost

            if switch_cost["cost_minutes"] > self.context_loss_threshold:
                result["warnings"].append(
                    f"High context switch cost: {switch_cost['cost_minutes']} minutes"
                )

            # Check resource availability
            resource_check = await self._check_resources(goal)
            result["analysis"]["resources"] = resource_check
            if not resource_check["available"]:
                result["errors"].append(
                    f"Resource not available: {resource_check['missing_resources']}"
                )

            # Check goal priority vs deadline
            priority_analysis = await self._analyze_priority(goal)
            result["analysis"]["priority"] = priority_analysis

            # Deactivate current goal if needed
            if self.active_goals and len(self.active_goals) >= self.max_active_goals:
                removed = await self._suspend_lowest_priority_goal()
                result["analysis"]["suspended_goal"] = removed

            # Activate the goal
            goal.state = GoalState.ACTIVE
            goal.activated_at = datetime.utcnow().isoformat()
            self.active_goals[goal_id] = goal

            # Call MCP to activate goal
            mcp_result = await self.mcp.call_operation(
                "task_management_tools",
                "activate_goal",
                {"goal_id": goal_id}
            )

            result["success"] = True
            result["activated_at"] = goal.activated_at
            result["active_goals"] = list(self.active_goals.keys())

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            result["error_type"] = type(e).__name__

        return result

    async def track_goal_progress(self, goal_id: int, progress_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track progress for a goal with milestone detection.

        Args:
            goal_id: Goal being tracked
            progress_update: Progress update with metrics

        Returns:
            Updated goal context with milestone detection
        """
        result = {
            "goal_id": goal_id,
            "success": False,
            "progress": {},
            "milestones_reached": [],
            "warnings": []
        }

        try:
            goal = self.goal_hierarchy.get(goal_id)
            if not goal:
                result["errors"] = [f"Goal {goal_id} not tracked"]
                return result

            # Update metrics
            if "percent" in progress_update:
                goal.metrics.progress_percent = progress_update["percent"]
            if "errors" in progress_update:
                goal.metrics.errors_encountered = progress_update["errors"]
            if "blockers" in progress_update:
                goal.metrics.blockers_active = progress_update["blockers"]
                if progress_update["blockers"] > 0:
                    goal.state = GoalState.BLOCKED

            # Calculate health score
            goal.metrics.health_score = await self._calculate_health_score(goal)

            # Detect milestones
            milestones = await self._detect_milestones(goal)
            if milestones:
                goal.metrics.milestones_reached = len(milestones)
                result["milestones_reached"] = milestones

            # Check if goal is complete
            if goal.metrics.progress_percent >= 100:
                await self.complete_goal(goal_id, "success")
                result["goal_completed"] = True

            # Check if goal is slipping
            if goal.state == GoalState.IN_PROGRESS:
                slip_check = await self._check_timeline_slip(goal)
                if slip_check["is_slipping"]:
                    result["warnings"].append(
                        f"Goal slipping: {slip_check['days_behind']} days behind"
                    )

            # Record progress to MCP
            mcp_result = await self.mcp.call_operation(
                "task_management_tools",
                "record_execution_progress",
                {
                    "goal_id": goal_id,
                    "progress_percent": goal.metrics.progress_percent,
                    "health_score": goal.metrics.health_score,
                    "blockers": goal.metrics.blockers_active
                }
            )

            result["success"] = True
            result["progress"] = {
                "percent": goal.metrics.progress_percent,
                "health_score": goal.metrics.health_score,
                "state": goal.state.value
            }

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]
            result["error_type"] = type(e).__name__

        return result

    async def complete_goal(self, goal_id: int, outcome: str = "success") -> Dict[str, Any]:
        """
        Mark a goal as complete.

        Args:
            goal_id: Goal to complete
            outcome: "success", "partial", or "failure"

        Returns:
            Completion result with metrics
        """
        result = {
            "goal_id": goal_id,
            "success": False,
            "outcome": outcome,
            "metrics": {}
        }

        try:
            goal = self.goal_hierarchy.get(goal_id)
            if not goal:
                result["errors"] = [f"Goal {goal_id} not found"]
                return result

            # Update state based on outcome
            if outcome == "success":
                goal.state = GoalState.COMPLETED
            elif outcome == "failure":
                goal.state = GoalState.FAILED
            elif outcome == "partial":
                goal.state = GoalState.BLOCKED

            goal.completed_at = datetime.utcnow().isoformat()

            # Activate dependent goals if applicable
            dependent = goal.dependent_goals
            if outcome == "success" and dependent:
                for dep_goal_id in dependent:
                    dep_goal = self.goal_hierarchy.get(dep_goal_id)
                    if dep_goal and dep_goal.state == GoalState.PENDING:
                        await self.activate_goal(dep_goal_id)

            # Deactivate from active goals
            if goal_id in self.active_goals:
                del self.active_goals[goal_id]

            # Record completion to MCP
            mcp_result = await self.mcp.call_operation(
                "task_management_tools",
                "complete_goal",
                {
                    "goal_id": goal_id,
                    "outcome": outcome,
                    "metrics": {
                        "final_progress": goal.metrics.progress_percent,
                        "health_score": goal.metrics.health_score,
                        "errors": goal.metrics.errors_encountered
                    }
                }
            )

            result["success"] = True
            result["final_state"] = goal.state.value
            result["metrics"] = {
                "progress_percent": goal.metrics.progress_percent,
                "health_score": goal.metrics.health_score,
                "errors": goal.metrics.errors_encountered,
                "completed_at": goal.completed_at
            }

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]
            result["error_type"] = type(e).__name__

        return result

    async def get_goal_hierarchy(self) -> Dict[str, Any]:
        """
        Get the complete goal hierarchy.

        Returns:
            Goal hierarchy with dependencies and state
        """
        result = {
            "success": False,
            "hierarchy": [],
            "critical_path": [],
            "active_goals": []
        }

        try:
            # Load current hierarchy
            hierarchy_list = list(self.goal_hierarchy.values())

            # Sort by priority and deadline
            sorted_goals = sorted(
                hierarchy_list,
                key=lambda g: (g.priority, g.deadline or ""),
                reverse=True
            )

            result["hierarchy"] = [
                {
                    "goal_id": g.goal_id,
                    "name": g.name,
                    "state": g.state.value,
                    "priority": g.priority,
                    "progress": g.metrics.progress_percent,
                    "deadline": g.deadline,
                    "dependencies": g.dependencies,
                    "health_score": g.metrics.health_score
                }
                for g in sorted_goals
            ]

            # Identify critical path
            critical_path = await self._identify_critical_path()
            result["critical_path"] = critical_path

            # List active goals
            result["active_goals"] = [
                {
                    "goal_id": goal_id,
                    "name": goal.name,
                    "progress": goal.metrics.progress_percent
                }
                for goal_id, goal in self.active_goals.items()
            ]

            # Get workflow status from MCP
            workflow = await self.mcp.call_operation(
                "task_management_tools",
                "get_workflow_status",
                {}
            )
            result["workflow_status"] = workflow

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]
            result["error_type"] = type(e).__name__

        return result

    async def check_goal_deadlines(self) -> Dict[str, Any]:
        """
        Check approaching deadlines and generate warnings.

        Returns:
            Deadline analysis and warnings
        """
        result = {
            "success": False,
            "approaching_deadlines": [],
            "overdue": [],
            "warnings": []
        }

        try:
            now = datetime.utcnow()

            for goal_id, goal in self.goal_hierarchy.items():
                if goal.state in [GoalState.COMPLETED, GoalState.FAILED]:
                    continue

                if not goal.deadline:
                    continue

                deadline = datetime.fromisoformat(goal.deadline)
                days_until = (deadline - now).days

                if days_until < 0:
                    result["overdue"].append({
                        "goal_id": goal_id,
                        "name": goal.name,
                        "days_overdue": abs(days_until),
                        "progress": goal.metrics.progress_percent
                    })
                elif days_until <= self.deadline_warning_days:
                    result["approaching_deadlines"].append({
                        "goal_id": goal_id,
                        "name": goal.name,
                        "days_remaining": days_until,
                        "progress": goal.metrics.progress_percent,
                        "health": goal.metrics.health_score
                    })

            if result["overdue"]:
                result["warnings"].append(
                    f"⚠️ {len(result['overdue'])} overdue goals require immediate attention"
                )

            if result["approaching_deadlines"]:
                result["warnings"].append(
                    f"⏰ {len(result['approaching_deadlines'])} goals due within {self.deadline_warning_days} days"
                )

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]

        return result

    # Private helper methods

    async def _load_goal(self, goal_id: int) -> Optional[GoalContext]:
        """Load goal from database"""
        try:
            # Try to get from hierarchy cache
            if goal_id in self.goal_hierarchy:
                return self.goal_hierarchy[goal_id]

            # In production, would query database
            return None
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    async def _check_dependencies(self, goal: GoalContext) -> Dict[str, Any]:
        """Check if goal dependencies are satisfied"""
        result = {
            "satisfied": True,
            "blocked_by": [],
            "details": []
        }

        for dep_id in goal.dependencies:
            dep_goal = self.goal_hierarchy.get(dep_id)
            if dep_goal and dep_goal.state != GoalState.COMPLETED:
                result["satisfied"] = False
                result["blocked_by"].append(dep_id)
                result["details"].append({
                    "goal_id": dep_id,
                    "name": dep_goal.name,
                    "state": dep_goal.state.value
                })

        return result

    async def _analyze_context_switch(self, goal: GoalContext) -> Dict[str, Any]:
        """Analyze context switching cost"""
        result = {
            "cost_minutes": 0,
            "from_goal": None,
            "to_goal": goal.goal_id,
            "memory_loss": 0.0,
            "resume_time": 0
        }

        # Find current active goal
        if self.active_goals:
            current_goal_id = list(self.active_goals.keys())[0]
            current_goal = self.active_goals[current_goal_id]

            result["from_goal"] = current_goal_id
            result["cost_minutes"] = 12  # Context switch overhead
            result["memory_loss"] = 0.15  # ~15% context loss
            result["resume_time"] = 5  # 5 minutes to resume current goal

        return result

    async def _check_resources(self, goal: GoalContext) -> Dict[str, Any]:
        """Check resource availability"""
        result = {
            "available": True,
            "missing_resources": [],
            "utilization": {}
        }

        # In production, would check actual resource allocation
        if goal.owner:
            result["utilization"][goal.owner] = 0.4  # Example: 40% utilization

        return result

    async def _analyze_priority(self, goal: GoalContext) -> Dict[str, Any]:
        """Analyze goal priority vs deadline"""
        result = {
            "priority_score": goal.priority,
            "urgency_score": 0,
            "recommendation": ""
        }

        if goal.deadline:
            deadline = datetime.fromisoformat(goal.deadline)
            days_until = (deadline - datetime.utcnow()).days

            if days_until <= 3:
                result["urgency_score"] = 10
                result["recommendation"] = "CRITICAL - Start immediately"
            elif days_until <= 7:
                result["urgency_score"] = 7
                result["recommendation"] = "HIGH - Schedule this week"
            else:
                result["urgency_score"] = max(0, 10 - (days_until // 7))
                result["recommendation"] = "Plan for later"

        return result

    async def _suspend_lowest_priority_goal(self) -> Optional[int]:
        """Suspend the lowest priority active goal"""
        if not self.active_goals:
            return None

        lowest = min(
            self.active_goals.items(),
            key=lambda x: x[1].priority
        )

        goal_id = lowest[0]
        goal = lowest[1]
        goal.state = GoalState.SUSPENDED

        return goal_id

    async def _calculate_health_score(self, goal: GoalContext) -> float:
        """Calculate composite health score"""
        score = 1.0

        # Progress component (0.4)
        progress_score = min(1.0, goal.metrics.progress_percent / 100.0)
        score -= (1.0 - progress_score) * 0.4

        # Error component (0.3)
        error_penalty = min(0.3, goal.metrics.errors_encountered * 0.1)
        score -= error_penalty

        # Blocker component (0.2)
        if goal.metrics.blockers_active > 0:
            score -= 0.2

        # Timeline component (0.1)
        if goal.deadline:
            deadline = datetime.fromisoformat(goal.deadline)
            days_remaining = (deadline - datetime.utcnow()).days
            if days_remaining < 0:
                score -= 0.1

        return max(0.0, score)

    async def _detect_milestones(self, goal: GoalContext) -> List[str]:
        """Detect reached milestones"""
        milestones = []

        if goal.metrics.progress_percent >= 25 and goal.metrics.milestones_reached < 1:
            milestones.append("25% Progress")
        if goal.metrics.progress_percent >= 50 and goal.metrics.milestones_reached < 2:
            milestones.append("50% Progress (Halfway)")
        if goal.metrics.progress_percent >= 75 and goal.metrics.milestones_reached < 3:
            milestones.append("75% Progress (Final Push)")

        return milestones

    async def _check_timeline_slip(self, goal: GoalContext) -> Dict[str, Any]:
        """Check if goal is slipping on timeline"""
        result = {
            "is_slipping": False,
            "days_behind": 0,
            "expected_progress": 0
        }

        if not goal.activated_at or not goal.deadline:
            return result

        start = datetime.fromisoformat(goal.activated_at)
        deadline = datetime.fromisoformat(goal.deadline)
        now = datetime.utcnow()

        # Calculate expected progress
        total_days = (deadline - start).days
        elapsed_days = (now - start).days

        if total_days > 0:
            expected_progress = (elapsed_days / total_days) * 100
            result["expected_progress"] = expected_progress

            # Check if behind
            if goal.metrics.progress_percent < (expected_progress - 10):
                result["is_slipping"] = True
                result["days_behind"] = int((expected_progress - goal.metrics.progress_percent) / (100 / total_days))

        return result

    async def _identify_critical_path(self) -> List[int]:
        """Identify critical path through goals"""
        # Simple implementation: goals on critical path are:
        # 1. High priority
        # 2. Have dependencies on other critical goals
        # 3. Have dependent goals waiting

        critical = []
        for goal_id, goal in self.goal_hierarchy.items():
            has_dependents = len(goal.dependent_goals) > 0
            is_high_priority = goal.priority >= 7

            if has_dependents and is_high_priority:
                critical.append(goal_id)

        return critical
