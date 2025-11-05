"""
Conflict Resolver Agent

Autonomous agent for detecting and resolving goal conflicts automatically.
Analyzes 5 conflict types and proposes resolution strategies.
"""

import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ConflictType(Enum):
    """Types of conflicts detected"""
    RESOURCE_CONTENTION = "resource_contention"  # Same person/tool
    DEPENDENCY_CYCLE = "dependency_cycle"  # A→B→A circular
    TIMING_CONFLICT = "timing_conflict"  # Overlapping deadlines
    PRIORITY_CONFLICT = "priority_conflict"  # High-priority goals block each other
    CAPACITY_OVERLOAD = "capacity_overload"  # Too much work


class ConflictSeverity(Enum):
    """Severity levels for conflicts"""
    CRITICAL = 9  # Blocks multiple high-priority goals
    HIGH = 7  # Blocks one high-priority goal
    MEDIUM = 5  # Manageable impact
    LOW = 2  # Minimal impact


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts"""
    PRIORITY_BASED = "priority"  # Suspend lower-priority goals
    TIMELINE_BASED = "timeline"  # Reschedule less urgent
    RESOURCE_BASED = "resource"  # Redistribute assignments
    SEQUENTIAL = "sequential"  # Serialize dependent goals
    CUSTOM = "custom"  # User-defined


@dataclass
class ConflictDetail:
    """Details about a detected conflict"""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    involved_goals: List[int]
    description: str
    root_cause: str
    detection_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ResolutionOption:
    """Option for resolving a conflict"""
    option_id: str
    strategy: ResolutionStrategy
    description: str
    timeline_impact_days: int
    resource_impact: Dict[str, float]
    risk_level: str  # LOW, MEDIUM, HIGH
    estimated_cost: float
    affected_goals: List[int] = field(default_factory=list)


class ConflictResolver:
    """
    Autonomous agent for conflict detection and resolution.

    Capabilities:
    - Detect 5 types of conflicts
    - Propose 5 resolution strategies
    - Impact analysis and ranking
    - Automatic or approval-based resolution
    """

    def __init__(self, database, mcp_client):
        """Initialize the conflict resolver

        Args:
            database: Database connection
            mcp_client: MCP client for tool operations
        """
        self.db = database
        self.mcp = mcp_client
        self.detected_conflicts: Dict[str, ConflictDetail] = {}
        self.resolution_history: List[Dict[str, Any]] = []
        self.auto_resolve = False
        self.severity_threshold = ConflictSeverity.MEDIUM

    async def detect_conflicts(self, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect all conflicts in the goal set.

        Args:
            goals: List of goal objects with id, deadline, owner, priority

        Returns:
            Detected conflicts grouped by type
        """
        result = {
            "success": False,
            "conflicts_detected": 0,
            "by_type": {},
            "by_severity": {},
            "conflicts": [],
            "summary": ""
        }

        try:
            # Initialize conflict counters
            for conflict_type in ConflictType:
                result["by_type"][conflict_type.value] = []
            for severity in ConflictSeverity:
                result["by_severity"][severity.value] = []

            # Run all detection methods
            resource_conflicts = await self._detect_resource_contention(goals)
            dependency_conflicts = await self._detect_dependency_cycles(goals)
            timing_conflicts = await self._detect_timing_conflicts(goals)
            priority_conflicts = await self._detect_priority_conflicts(goals)
            capacity_conflicts = await self._detect_capacity_overload(goals)

            all_conflicts = (
                resource_conflicts + dependency_conflicts +
                timing_conflicts + priority_conflicts + capacity_conflicts
            )

            # Store and categorize
            for conflict in all_conflicts:
                self.detected_conflicts[conflict.conflict_id] = conflict
                result["by_type"][conflict.conflict_type.value].append(conflict.conflict_id)
                result["by_severity"][conflict.severity.value].append(conflict.conflict_id)
                result["conflicts"].append({
                    "id": conflict.conflict_id,
                    "type": conflict.conflict_type.value,
                    "severity": conflict.severity.value,
                    "severity_score": conflict.severity.value,
                    "involved_goals": conflict.involved_goals,
                    "description": conflict.description,
                    "root_cause": conflict.root_cause
                })

            result["conflicts_detected"] = len(all_conflicts)
            result["success"] = True

            # Generate summary
            critical_count = len(result["by_severity"].get("critical", []))
            high_count = len(result["by_severity"].get("high", []))
            result["summary"] = f"{result['conflicts_detected']} conflicts detected ({critical_count} CRITICAL, {high_count} HIGH)"

            # Call MCP detection for validation
            await self.mcp.call_operation(
                "task_management_tools",
                "check_goal_conflicts",
                {"goals": goals}
            )

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]
            result["error_type"] = type(e).__name__

        return result

    async def resolve_conflicts(
        self,
        conflict_ids: Optional[List[str]] = None,
        strategy: str = "priority",
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve detected conflicts.

        Args:
            conflict_ids: Specific conflicts to resolve (None = all)
            strategy: Resolution strategy to use
            dry_run: If True, preview without applying

        Returns:
            Resolution plan and impact analysis
        """
        result = {
            "success": False,
            "dry_run": dry_run,
            "conflicts_resolved": 0,
            "resolutions": [],
            "timeline_impact": 0,
            "resource_impact": {},
            "warnings": [],
            "errors": []
        }

        try:
            # Filter conflicts
            conflicts_to_resolve = (
                [self.detected_conflicts[cid] for cid in conflict_ids]
                if conflict_ids
                else list(self.detected_conflicts.values())
            )

            if not conflicts_to_resolve:
                result["success"] = True
                result["summary"] = "No conflicts to resolve"
                return result

            # Generate resolution options for each conflict
            all_resolutions = []
            for conflict in conflicts_to_resolve:
                options = await self._generate_resolution_options(conflict, strategy)
                best_option = self._rank_options(options)[0]
                all_resolutions.append((conflict, best_option))

            # Analyze combined impact
            combined_timeline = 0
            combined_resources = {}

            for conflict, option in all_resolutions:
                result["resolutions"].append({
                    "conflict_id": conflict.conflict_id,
                    "conflict_type": conflict.conflict_type.value,
                    "severity": conflict.severity.value,
                    "resolution_strategy": option.strategy.value,
                    "description": option.description,
                    "timeline_impact": option.timeline_impact_days,
                    "resource_impact": option.resource_impact,
                    "affected_goals": option.affected_goals,
                    "risk": option.risk_level
                })

                combined_timeline += option.timeline_impact_days
                for resource, impact in option.resource_impact.items():
                    combined_resources[resource] = combined_resources.get(resource, 0) + impact

            result["timeline_impact"] = combined_timeline
            result["resource_impact"] = combined_resources
            result["conflicts_resolved"] = len(all_resolutions)

            # Apply resolutions if not dry-run
            if not dry_run:
                for conflict, option in all_resolutions:
                    await self._apply_resolution(conflict, option)
                    self.resolution_history.append({
                        "conflict_id": conflict.conflict_id,
                        "strategy": option.strategy.value,
                        "applied_at": datetime.utcnow().isoformat()
                    })

            # Call MCP resolution
            mcp_result = await self.mcp.call_operation(
                "task_management_tools",
                "resolve_goal_conflicts",
                {
                    "conflict_ids": conflict_ids or list(self.detected_conflicts.keys()),
                    "strategy": strategy,
                    "dry_run": dry_run
                }
            )

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            result["error_type"] = type(e).__name__

        return result

    async def suggest_resolution(self, conflict_id: str) -> Dict[str, Any]:
        """
        Suggest resolution options for a specific conflict.

        Args:
            conflict_id: Conflict to suggest resolution for

        Returns:
            Ranked list of resolution options
        """
        result = {
            "success": False,
            "conflict_id": conflict_id,
            "options": [],
            "recommended": None
        }

        try:
            conflict = self.detected_conflicts.get(conflict_id)
            if not conflict:
                result["errors"] = [f"Conflict {conflict_id} not found"]
                return result

            # Generate all options
            options = await self._generate_resolution_options(conflict)

            # Rank by effectiveness
            ranked = self._rank_options(options)

            result["options"] = [
                {
                    "option_id": opt.option_id,
                    "strategy": opt.strategy.value,
                    "description": opt.description,
                    "timeline_impact": opt.timeline_impact_days,
                    "resource_impact": opt.resource_impact,
                    "risk": opt.risk_level,
                    "estimated_cost": opt.estimated_cost
                }
                for opt in ranked
            ]

            result["recommended"] = ranked[0].option_id if ranked else None
            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"] = [str(e)]

        return result

    # Private helper methods

    async def _detect_resource_contention(self, goals: List[Dict]) -> List[ConflictDetail]:
        """Detect resource conflicts (same person/tool)"""
        conflicts = []
        owner_map = {}

        for goal in goals:
            owner = goal.get("owner")
            if not owner:
                continue

            if owner not in owner_map:
                owner_map[owner] = []
            owner_map[owner].append(goal["id"])

        # Check for multiple concurrent goals per owner
        for owner, goal_ids in owner_map.items():
            if len(goal_ids) > 1:
                # Calculate overlap
                concurrent = goal_ids[:2]  # Simplified
                conflict = ConflictDetail(
                    conflict_id=f"rc_{owner}",
                    conflict_type=ConflictType.RESOURCE_CONTENTION,
                    severity=ConflictSeverity.HIGH,
                    involved_goals=concurrent,
                    description=f"Resource '{owner}' needed for multiple concurrent goals: {concurrent}",
                    root_cause=f"Goals {concurrent} both require {owner} in overlapping timeframes"
                )
                conflicts.append(conflict)

        return conflicts

    async def _detect_dependency_cycles(self, goals: List[Dict]) -> List[ConflictDetail]:
        """Detect circular dependencies"""
        conflicts = []

        # Build dependency graph
        dep_graph = {goal["id"]: goal.get("dependencies", []) for goal in goals}

        # DFS to find cycles
        for goal_id in dep_graph:
            visited = set()
            path = []
            if self._has_cycle(goal_id, dep_graph, visited, path):
                conflict = ConflictDetail(
                    conflict_id=f"dc_{goal_id}",
                    conflict_type=ConflictType.DEPENDENCY_CYCLE,
                    severity=ConflictSeverity.HIGH,
                    involved_goals=path,
                    description=f"Circular dependency detected: {' → '.join(map(str, path))} → {goal_id}",
                    root_cause=f"Cyclic dependency chain prevents execution"
                )
                conflicts.append(conflict)

        return conflicts

    async def _detect_timing_conflicts(self, goals: List[Dict]) -> List[ConflictDetail]:
        """Detect overlapping deadlines and capacity issues"""
        conflicts = []

        # Group goals by deadline
        deadline_map = {}
        for goal in goals:
            deadline = goal.get("deadline")
            if deadline:
                if deadline not in deadline_map:
                    deadline_map[deadline] = []
                deadline_map[deadline].append(goal["id"])

        # Check for overloaded deadlines
        for deadline, goal_ids in deadline_map.items():
            if len(goal_ids) > 2:
                conflict = ConflictDetail(
                    conflict_id=f"tc_{deadline}",
                    conflict_type=ConflictType.TIMING_CONFLICT,
                    severity=ConflictSeverity.MEDIUM,
                    involved_goals=goal_ids,
                    description=f"Multiple goals due on {deadline}: {goal_ids}",
                    root_cause=f"Insufficient capacity for {len(goal_ids)} concurrent goals"
                )
                conflicts.append(conflict)

        return conflicts

    async def _detect_priority_conflicts(self, goals: List[Dict]) -> List[ConflictDetail]:
        """Detect priority-based conflicts"""
        conflicts = []

        # Find high-priority goals that depend on lower-priority goals
        high_priority = [g for g in goals if g.get("priority", 0) >= 7]

        for high_goal in high_priority:
            deps = high_goal.get("dependencies", [])
            low_priority_deps = [
                d for d in deps
                if next((g["priority"] for g in goals if g["id"] == d), 0) < 5
            ]

            if low_priority_deps:
                conflict = ConflictDetail(
                    conflict_id=f"pc_{high_goal['id']}",
                    conflict_type=ConflictType.PRIORITY_CONFLICT,
                    severity=ConflictSeverity.MEDIUM,
                    involved_goals=[high_goal["id"]] + low_priority_deps,
                    description=f"High-priority goal #{high_goal['id']} depends on low-priority goals",
                    root_cause=f"Priority inversion: high-priority task blocked by low-priority dependencies"
                )
                conflicts.append(conflict)

        return conflicts

    async def _detect_capacity_overload(self, goals: List[Dict]) -> List[ConflictDetail]:
        """Detect total capacity overload"""
        conflicts = []

        # Calculate total effort required
        total_hours = sum(g.get("estimated_hours", 0) for g in goals)
        available_hours = 40 * 4  # 40 hrs/week, 4 weeks

        utilization = total_hours / available_hours if available_hours > 0 else 0

        if utilization > 0.85:  # More than 85% utilization
            conflict = ConflictDetail(
                conflict_id="co_team",
                conflict_type=ConflictType.CAPACITY_OVERLOAD,
                severity=ConflictSeverity.CRITICAL if utilization > 1.0 else ConflictSeverity.HIGH,
                involved_goals=[g["id"] for g in goals],
                description=f"Team capacity overloaded: {utilization:.0%} utilization required",
                root_cause=f"Total effort {total_hours}h exceeds available capacity {available_hours}h"
            )
            conflicts.append(conflict)

        return conflicts

    async def _generate_resolution_options(
        self,
        conflict: ConflictDetail,
        strategy: str = "all"
    ) -> List[ResolutionOption]:
        """Generate resolution options for a conflict"""
        options = []

        if conflict.conflict_type == ConflictType.RESOURCE_CONTENTION:
            # Option 1: Suspend lower-priority goal
            options.append(ResolutionOption(
                option_id="rc_1",
                strategy=ResolutionStrategy.PRIORITY_BASED,
                description="Suspend lower-priority goal until resource available",
                timeline_impact_days=7,
                resource_impact={},
                risk_level="MEDIUM",
                estimated_cost=0,
                affected_goals=[conflict.involved_goals[1]]
            ))

            # Option 2: Redistribute to different person
            options.append(ResolutionOption(
                option_id="rc_2",
                strategy=ResolutionStrategy.RESOURCE_BASED,
                description="Assign goal to different team member",
                timeline_impact_days=0,
                resource_impact={"team_member_b": 0.5},
                risk_level="MEDIUM",
                estimated_cost=0,
                affected_goals=conflict.involved_goals
            ))

        elif conflict.conflict_type == ConflictType.DEPENDENCY_CYCLE:
            # Option 1: Serialize goals
            options.append(ResolutionOption(
                option_id="dc_1",
                strategy=ResolutionStrategy.SEQUENTIAL,
                description="Execute dependent goals sequentially to break cycle",
                timeline_impact_days=7,
                resource_impact={},
                risk_level="LOW",
                estimated_cost=0,
                affected_goals=conflict.involved_goals
            ))

        elif conflict.conflict_type == ConflictType.TIMING_CONFLICT:
            # Option 1: Reschedule lower-priority goals
            options.append(ResolutionOption(
                option_id="tc_1",
                strategy=ResolutionStrategy.TIMELINE_BASED,
                description="Move lower-priority goals to next week",
                timeline_impact_days=7,
                resource_impact={},
                risk_level="MEDIUM",
                estimated_cost=0,
                affected_goals=conflict.involved_goals[1:]
            ))

        elif conflict.conflict_type == ConflictType.CAPACITY_OVERLOAD:
            # Option 1: Defer non-critical goals
            options.append(ResolutionOption(
                option_id="co_1",
                strategy=ResolutionStrategy.TIMELINE_BASED,
                description="Defer non-critical goals to next period",
                timeline_impact_days=14,
                resource_impact={},
                risk_level="MEDIUM",
                estimated_cost=0,
                affected_goals=conflict.involved_goals
            ))

        return options if strategy == "all" else [
            opt for opt in options if opt.strategy.value == strategy
        ]

    def _rank_options(self, options: List[ResolutionOption]) -> List[ResolutionOption]:
        """Rank resolution options by effectiveness"""
        # Scoring: prefer minimal timeline impact, low cost, low risk
        def score(option: ResolutionOption) -> float:
            timeline_penalty = abs(option.timeline_impact_days) * 0.5
            risk_penalty = {
                "LOW": 0,
                "MEDIUM": 5,
                "HIGH": 10
            }.get(option.risk_level, 5)
            cost_penalty = option.estimated_cost / 1000

            return timeline_penalty + risk_penalty + cost_penalty

        return sorted(options, key=score)

    async def _apply_resolution(self, conflict: ConflictDetail, option: ResolutionOption) -> None:
        """Apply a resolution to the system"""
        # This would update goal states, deadlines, assignments, etc.
        # In production, would call MCP operations to update goals
        pass

    def _has_cycle(
        self,
        node: int,
        graph: Dict[int, List[int]],
        visited: Set[int],
        path: List[int]
    ) -> bool:
        """DFS to detect cycles"""
        if node in visited:
            return node in path

        visited.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if self._has_cycle(neighbor, graph, visited, path):
                return True

        path.pop()
        return False
