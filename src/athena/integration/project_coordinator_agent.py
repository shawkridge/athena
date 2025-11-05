"""Project Coordinator Agent - Multi-project orchestration and coordination.

Phase 5-8 Agent: Manages cross-project dependencies, identifies resource
conflicts, analyzes critical paths, and coordinates task execution across
multiple projects.
"""

from typing import Optional
from dataclasses import dataclass
from ..integration.project_coordinator import ProjectCoordinator
from ..prospective.store import ProspectiveStore
from ..core.database import Database


@dataclass
class ProjectCoordinationSummary:
    """Summary of multi-project coordination."""

    total_projects: int
    total_tasks: int
    critical_path_duration: int  # minutes
    critical_tasks: list[int]
    resource_conflicts: list[dict]
    bottleneck_persons: list[str]
    bottleneck_tools: list[str]
    timeline_status: str  # "on_track", "at_risk", "critical"
    recommendations: list[str]


class ProjectCoordinatorAgent:
    """Autonomous agent for multi-project coordination.

    Manages cross-project dependencies, detects resource conflicts,
    analyzes critical paths, and coordinates task execution across
    multiple projects.
    """

    def __init__(self, db: Database):
        """Initialize project coordinator agent.

        Args:
            db: Database connection for accessing task data
        """
        self.db = db
        self.coordinator = ProjectCoordinator(db)
        self.store = ProspectiveStore(db)

    async def coordinate_projects(
        self, project_ids: list[int]
    ) -> ProjectCoordinationSummary:
        """Coordinate multiple projects with dependencies and conflicts.

        Args:
            project_ids: List of project IDs to coordinate

        Returns:
            ProjectCoordinationSummary with coordination details
        """
        if not project_ids:
            raise ValueError("At least one project ID required")

        # Analyze critical path for primary project
        critical_path = await self.coordinator.analyze_critical_path(
            project_ids[0]
        )

        # Detect resource conflicts across all projects
        conflicts = await self.coordinator.detect_resource_conflicts(
            project_ids
        )

        # Count total tasks
        total_tasks = self._count_tasks(project_ids)

        # Extract bottlenecks
        bottleneck_persons = self._extract_bottleneck_persons(conflicts)
        bottleneck_tools = self._extract_bottleneck_tools(conflicts)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            critical_path, conflicts, bottleneck_persons
        )

        # Assess timeline status
        timeline_status = self._assess_timeline_status(
            critical_path, len(conflicts)
        )

        # Extract critical task IDs
        critical_tasks = (
            critical_path.task_ids
            if hasattr(critical_path, "task_ids")
            and critical_path.task_ids
            else []
        )

        critical_path_duration = (
            critical_path.total_duration_minutes
            if hasattr(critical_path, "total_duration_minutes")
            else 0
        )

        return ProjectCoordinationSummary(
            total_projects=len(project_ids),
            total_tasks=total_tasks,
            critical_path_duration=critical_path_duration,
            critical_tasks=critical_tasks[:10],  # Top 10
            resource_conflicts=[
                {
                    "type": conflict.conflict_type
                    if hasattr(conflict, "conflict_type")
                    else conflict.get("conflict_type", "unknown"),
                    "severity": conflict.severity
                    if hasattr(conflict, "severity")
                    else conflict.get("severity", "medium"),
                    "recommendation": conflict.recommendations[0]
                    if (
                        hasattr(conflict, "recommendations")
                        and conflict.recommendations
                    )
                    else conflict.get("recommendations", ["TBD"])[0]
                    if isinstance(conflict, dict)
                    else "TBD",
                }
                for conflict in (conflicts if conflicts else [])
            ][:5],  # Top 5
            bottleneck_persons=bottleneck_persons,
            bottleneck_tools=bottleneck_tools,
            timeline_status=timeline_status,
            recommendations=recommendations,
        )

    def _count_tasks(self, project_ids: list[int]) -> int:
        """Count total tasks across projects.

        Args:
            project_ids: Project IDs

        Returns:
            Total task count
        """
        try:
            cursor = self.db.conn.cursor()
            placeholders = ",".join("?" * len(project_ids))
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM prospective_tasks
                WHERE project_id IN ({placeholders})
                """,
                project_ids,
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def _extract_bottleneck_persons(
        self, conflicts: list
    ) -> list[str]:
        """Extract persons involved in resource conflicts.

        Args:
            conflicts: List of conflicts

        Returns:
            List of person names with conflicts
        """
        persons = []
        for conflict in conflicts or []:
            # Try to extract person from conflict
            if isinstance(conflict, dict):
                if "assignee" in conflict:
                    persons.append(conflict["assignee"])
                if "person" in conflict:
                    persons.append(conflict["person"])
            else:
                if hasattr(conflict, "assignee"):
                    persons.append(conflict.assignee)
                if hasattr(conflict, "person"):
                    persons.append(conflict.person)

        # Remove duplicates and return top 3
        return list(set(persons))[:3]

    def _extract_bottleneck_tools(
        self, conflicts: list
    ) -> list[str]:
        """Extract tools involved in resource conflicts.

        Args:
            conflicts: List of conflicts

        Returns:
            List of tool names with conflicts
        """
        tools = []
        for conflict in conflicts or []:
            if isinstance(conflict, dict):
                if "tool" in conflict:
                    tools.append(conflict["tool"])
                if "resource" in conflict:
                    tools.append(conflict["resource"])
            else:
                if hasattr(conflict, "tool"):
                    tools.append(conflict.tool)
                if hasattr(conflict, "resource"):
                    tools.append(conflict.resource)

        return list(set(tools))[:3]

    def _assess_timeline_status(
        self, critical_path, conflict_count: int
    ) -> str:
        """Assess project timeline status.

        Args:
            critical_path: Critical path analysis result
            conflict_count: Number of resource conflicts

        Returns:
            Status: 'on_track', 'at_risk', or 'critical'
        """
        # Extract slack time if available
        slack_time = 0
        if hasattr(critical_path, "slack_time_minutes"):
            slack_time = critical_path.slack_time_minutes

        if conflict_count >= 3:
            return "critical"
        elif conflict_count >= 1 or slack_time < 120:  # < 2 hours
            return "at_risk"
        else:
            return "on_track"

    def _generate_recommendations(
        self, critical_path, conflicts: list, bottleneck_persons: list
    ) -> list[str]:
        """Generate specific recommendations.

        Args:
            critical_path: Critical path analysis
            conflicts: Resource conflicts
            bottleneck_persons: Persons with bottlenecks

        Returns:
            List of recommendations
        """
        recommendations = []

        # Critical path recommendations
        slack_time = (
            critical_path.slack_time_minutes
            if hasattr(critical_path, "slack_time_minutes")
            else 0
        )

        if slack_time < 60:
            recommendations.append(
                "CRITICAL: Slack time < 1 hour - any delay will miss deadline"
            )
        elif slack_time < 480:  # 8 hours
            recommendations.append(
                "ACTION: Limited slack time - prioritize critical path tasks"
            )
        else:
            recommendations.append(
                "✓ Adequate slack time for schedule adjustments"
            )

        # Resource conflict recommendations
        if conflicts:
            if len(conflicts) >= 3:
                recommendations.append(
                    "ACTION: Multiple resource conflicts - consider reassignment"
                )
            else:
                recommendations.append(
                    f"ACTION: Resolve {len(conflicts)} resource conflict(s)"
                )

        # Bottleneck person recommendations
        if bottleneck_persons:
            recommendations.append(
                f"ACTION: Cross-train on {bottleneck_persons[0]}'s critical tasks"
            )

        # Dependency recommendations
        if hasattr(critical_path, "task_ids") and critical_path.task_ids:
            recommendations.append(
                f"MONITOR: {len(critical_path.task_ids)} tasks on critical path"
            )

        # Default if no issues
        if not recommendations:
            recommendations.append(
                "✓ Multi-project coordination is healthy"
            )

        return recommendations

    async def suggest_task_reordering(
        self, project_ids: list[int]
    ) -> list[dict]:
        """Suggest task reordering to optimize resource utilization.

        Args:
            project_ids: Projects to optimize

        Returns:
            List of reordering suggestions
        """
        suggestions = []

        try:
            # Detect conflicts
            conflicts = await self.coordinator.detect_resource_conflicts(
                project_ids
            )

            # For each conflict, suggest resolution
            for conflict in conflicts or []:
                conflict_type = (
                    conflict.conflict_type
                    if hasattr(conflict, "conflict_type")
                    else conflict.get("conflict_type", "unknown")
                )

                if conflict_type == "person_overload":
                    suggestions.append(
                        {
                            "action": "defer",
                            "reason": f"Person has multiple concurrent critical tasks",
                            "recommendation": "Defer one task to sequential window",
                            "priority": "high",
                        }
                    )
                elif conflict_type == "tool_contention":
                    suggestions.append(
                        {
                            "action": "sequence",
                            "reason": "Tool not available - tasks must serialize",
                            "recommendation": "Reorder tasks by tool dependency",
                            "priority": "medium",
                        }
                    )
                elif conflict_type == "dependency_blocker":
                    suggestions.append(
                        {
                            "action": "unblock",
                            "reason": "Dependency task is blocked",
                            "recommendation": "Resolve blocker in dependency task first",
                            "priority": "critical",
                        }
                    )

            return suggestions[:5]  # Top 5 suggestions
        except Exception:
            return [
                {
                    "action": "review",
                    "reason": "Unable to analyze conflicts",
                    "recommendation": "Manual review required",
                    "priority": "medium",
                }
            ]

    async def check_deadline_risks(
        self, project_ids: list[int], target_date: str
    ) -> dict:
        """Check if projects can meet target deadline.

        Args:
            project_ids: Projects to check
            target_date: Target completion date (ISO format)

        Returns:
            Dictionary with risk assessment
        """
        try:
            # Analyze critical path
            critical_path = await self.coordinator.analyze_critical_path(
                project_ids[0]
            )

            # Extract duration
            cp_duration = (
                critical_path.total_duration_minutes
                if hasattr(critical_path, "total_duration_minutes")
                else 0
            )

            # Check slack time
            slack_time = (
                critical_path.slack_time_minutes
                if hasattr(critical_path, "slack_time_minutes")
                else 0
            )

            # Assess risk
            risk_level = (
                "critical"
                if slack_time < 0
                else "high" if slack_time < 240
                else "medium" if slack_time < 480
                else "low"
            )

            return {
                "target_date": target_date,
                "critical_path_duration_hours": cp_duration / 60,
                "slack_time_hours": slack_time / 60,
                "risk_level": risk_level,
                "feasible": slack_time >= 0,
                "recommendation": (
                    "On schedule" if slack_time > 480
                    else "At risk - tight deadline" if slack_time > 0
                    else "CRITICAL - deadline will be missed"
                ),
            }
        except Exception as e:
            return {
                "error": str(e),
                "feasible": False,
                "risk_level": "unknown",
            }
