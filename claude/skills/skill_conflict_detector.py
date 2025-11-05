"""
Conflict Detector Skill - Phase 3 Executive Function.

Auto-detects resource/dependency conflicts between goals.
Classifies conflicts and calculates severity.
"""

from typing import Any, Dict, List
from datetime import datetime
from .base_skill import BaseSkill, SkillResult


class ConflictDetectorSkill(BaseSkill):
    """Detects conflicts between active goals."""

    # Conflict types
    CONFLICT_TYPES = {
        "RESOURCE_CONTENTION": {
            "description": "Same resource needed by multiple goals",
            "severity_base": 7,
            "auto_resolvable": True,
        },
        "DEPENDENCY_CYCLE": {
            "description": "Circular dependencies (A→B→A)",
            "severity_base": 10,
            "auto_resolvable": False,
        },
        "TIMING_CONFLICT": {
            "description": "Overlapping deadlines with capacity limits",
            "severity_base": 6,
            "auto_resolvable": True,
        },
        "CAPACITY_OVERLOAD": {
            "description": "Team capacity >100%",
            "severity_base": 8,
            "auto_resolvable": True,
        },
        "PRIORITY_CONFLICT": {
            "description": "High-priority goals block each other",
            "severity_base": 7,
            "auto_resolvable": False,
        },
    }

    def __init__(self):
        """Initialize skill."""
        super().__init__(
            skill_id="conflict-detector",
            skill_name="Conflict Detector"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect conflicts between active goals.

        Args:
            context: Execution context with active goals

        Returns:
            Result with detected conflicts and severity analysis
        """
        try:
            memory_manager = context.get('memory_manager')
            active_goals = context.get('active_goals', [])
            event = context.get('event')

            if not active_goals or len(active_goals) < 2:
                return SkillResult(
                    status="skipped",
                    data={"reason": "Less than 2 active goals"}
                ).to_dict()

            # Detect all conflict types
            conflicts = await self._detect_all_conflicts(active_goals)

            # Classify and score
            classified = self._classify_conflicts(conflicts)

            # Find related conflict clusters
            clusters = self._cluster_conflicts(classified)

            # Determine if escalation needed
            max_severity = max(
                (c['severity'] for c in classified), default=0
            ) if classified else 0
            should_escalate = max_severity >= 8

            result = SkillResult(
                status="success" if not classified else "success",
                data={
                    "conflict_count": len(classified),
                    "critical_count": sum(1 for c in classified if c['severity'] >= 8),
                    "high_count": sum(1 for c in classified if 6 <= c['severity'] < 8),
                    "conflicts": classified,
                    "clusters": clusters,
                    "max_severity": max_severity,
                    "should_escalate": should_escalate,
                    "timestamp": datetime.now().isoformat(),
                },
                actions=[
                    "🔍 Conflicts detected - review impact" if classified else "✓ No conflicts",
                    "⚡ Escalate to conflict-resolver" if should_escalate else "",
                    "/resolve-conflicts (to auto-fix)" if classified else "",
                ] if classified else []
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            return SkillResult(
                status="failed",
                error=str(e)
            ).to_dict()

    async def _detect_all_conflicts(self, active_goals: List[Dict]) -> Dict[str, List]:
        """Detect all conflict types."""
        conflicts = {
            "RESOURCE_CONTENTION": self._detect_resource_conflicts(active_goals),
            "DEPENDENCY_CYCLE": self._detect_cycles(active_goals),
            "TIMING_CONFLICT": self._detect_timing_conflicts(active_goals),
            "CAPACITY_OVERLOAD": self._detect_overload(active_goals),
            "PRIORITY_CONFLICT": self._detect_priority_conflicts(active_goals),
        }

        # Filter out empty lists
        return {k: v for k, v in conflicts.items() if v}

    def _detect_resource_conflicts(self, goals: List[Dict]) -> List[Dict]:
        """Detect resource contention."""
        conflicts = []

        # Group by assigned resource (person)
        resource_map = {}
        for goal in goals:
            resource = goal.get('assigned_to', 'unknown')
            if resource not in resource_map:
                resource_map[resource] = []
            resource_map[resource].append(goal)

        # Find resource conflicts
        for resource, resource_goals in resource_map.items():
            if len(resource_goals) > 1:
                estimated_hours = sum(g.get('estimated_hours', 40) for g in resource_goals)
                available_hours = 40  # Standard week

                if estimated_hours > available_hours:
                    overlap = estimated_hours - available_hours
                    conflicts.append({
                        "type": "RESOURCE_CONTENTION",
                        "goals": [g['id'] for g in resource_goals],
                        "resource": resource,
                        "conflict_hours": overlap,
                        "estimated_total": estimated_hours,
                        "available": available_hours,
                    })

        return conflicts

    def _detect_cycles(self, goals: List[Dict]) -> List[Dict]:
        """Detect dependency cycles."""
        conflicts = []

        # Build dependency graph
        deps = {g['id']: g.get('dependencies', []) for g in goals}

        # Simple cycle detection (DFS)
        for goal_id in deps:
            if self._has_cycle(goal_id, deps, set()):
                # Find cycle partners
                cycle_goals = self._find_cycle_partners(goal_id, deps)
                conflicts.append({
                    "type": "DEPENDENCY_CYCLE",
                    "goals": cycle_goals,
                    "cycle_description": f"Goals {cycle_goals} form a cycle",
                })

        return conflicts

    def _detect_timing_conflicts(self, goals: List[Dict]) -> List[Dict]:
        """Detect deadline overlap issues."""
        conflicts = []

        # Sort by deadline
        sorted_goals = sorted(
            goals,
            key=lambda g: g.get('deadline', '')
        )

        # Find overlapping deadlines
        total_effort = sum(g.get('estimated_hours', 40) for g in goals)
        available_time = 40 * 2  # Assume 2-week window

        if total_effort > available_time:
            overlapping = [g for g in goals if overlapping_deadline(g)]
            if overlapping:
                conflicts.append({
                    "type": "TIMING_CONFLICT",
                    "goals": [g['id'] for g in overlapping],
                    "total_effort": total_effort,
                    "available_time": available_time,
                    "overload": total_effort - available_time,
                })

        return conflicts

    def _detect_overload(self, goals: List[Dict]) -> List[Dict]:
        """Detect team capacity overload."""
        conflicts = []

        total_effort = sum(g.get('estimated_hours', 40) for g in goals)
        available_capacity = 40  # Single person baseline

        utilization = (total_effort / available_capacity) * 100
        if utilization > 100:
            conflicts.append({
                "type": "CAPACITY_OVERLOAD",
                "goals": [g['id'] for g in goals],
                "utilization_percent": utilization,
                "total_effort": total_effort,
                "available_capacity": available_capacity,
            })

        return conflicts

    def _detect_priority_conflicts(self, goals: List[Dict]) -> List[Dict]:
        """Detect priority conflicts."""
        conflicts = []

        # Find high-priority goals
        high_priority = [g for g in goals if g.get('priority', 0) >= 8]

        if len(high_priority) > 1:
            # Check if they block each other
            for g1 in high_priority:
                for g2 in high_priority:
                    if g1['id'] != g2['id']:
                        if g2['id'] in g1.get('dependencies', []):
                            conflicts.append({
                                "type": "PRIORITY_CONFLICT",
                                "goals": [g1['id'], g2['id']],
                                "description": f"Goal {g1['id']} depends on Goal {g2['id']}",
                                "both_high_priority": True,
                            })
                            break

        return conflicts

    def _classify_conflicts(self, conflicts: Dict[str, List]) -> List[Dict]:
        """Classify and score conflicts."""
        classified = []

        for conflict_type, conflict_list in conflicts.items():
            type_info = self.CONFLICT_TYPES.get(
                conflict_type,
                {"description": "", "severity_base": 5, "auto_resolvable": False}
            )

            for conflict in conflict_list:
                # Calculate severity
                base = type_info['severity_base']
                multiplier = 1.0

                if 'conflict_hours' in conflict:
                    multiplier = min(3, 1 + (conflict['conflict_hours'] / 20))
                elif 'utilization_percent' in conflict:
                    multiplier = min(2, conflict['utilization_percent'] / 100)

                severity = min(10, base * multiplier)

                classified.append({
                    "type": conflict_type,
                    "description": type_info['description'],
                    "severity": severity,
                    "severity_rating": self._get_severity_rating(severity),
                    "auto_resolvable": type_info['auto_resolvable'],
                    "affected_goals": conflict.get('goals', []),
                    "details": conflict,
                })

        # Sort by severity
        return sorted(classified, key=lambda c: c['severity'], reverse=True)

    def _cluster_conflicts(self, conflicts: List[Dict]) -> List[Dict]:
        """Group related conflicts."""
        clusters = []

        # Simple clustering by affected goals
        goal_conflict_map = {}
        for conflict in conflicts:
            for goal_id in conflict['affected_goals']:
                if goal_id not in goal_conflict_map:
                    goal_conflict_map[goal_id] = []
                goal_conflict_map[goal_id].append(conflict)

        # Create clusters
        seen = set()
        for goal_id, conflict_list in goal_conflict_map.items():
            if goal_id not in seen:
                cluster_goals = set()
                for conflict in conflict_list:
                    cluster_goals.update(conflict['affected_goals'])

                clusters.append({
                    "goals": list(cluster_goals),
                    "conflict_count": len(conflict_list),
                    "max_severity": max(c['severity'] for c in conflict_list),
                    "conflicts": conflict_list,
                })

                seen.update(cluster_goals)

        return clusters

    def _get_severity_rating(self, severity: float) -> str:
        """Get human-readable severity."""
        if severity >= 8:
            return "🔴 CRITICAL"
        elif severity >= 6:
            return "🟠 HIGH"
        elif severity >= 4:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"

    def _has_cycle(self, node: int, graph: Dict, visited: set) -> bool:
        """DFS cycle detection."""
        if node in visited:
            return True

        visited.add(node)
        for neighbor in graph.get(node, []):
            if self._has_cycle(neighbor, graph, visited.copy()):
                return True

        return False

    def _find_cycle_partners(self, node: int, graph: Dict) -> List[int]:
        """Find goals involved in cycle with node."""
        # Simplified - just return the node and its dependencies
        return [node] + graph.get(node, [])


def overlapping_deadline(goal: Dict) -> bool:
    """Check if goal deadline overlaps with others."""
    # Simplified - would check against other goals
    return False


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = ConflictDetectorSkill()
    return _instance
