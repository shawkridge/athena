"""Bottleneck Detector Skill - Identify resource bottlenecks and constraints.

Detects and analyzes:
- Person overload (too many concurrent tasks)
- Tool/data contention
- Knowledge/skill gaps
- Dependencies that block progress
- Suggests resource rebalancing
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..core.database import Database


@dataclass
class Bottleneck:
    """Resource bottleneck description."""

    bottleneck_type: str  # person, tool, knowledge, dependency
    resource: str  # name of person, tool, or concept
    current_load: int  # tasks affected
    severity: str  # low, medium, high, critical
    impact_hours: int  # estimated hours of impact
    affected_tasks: List[int]
    recommendations: List[str]


class BottleneckDetector:
    """Detect and analyze resource bottlenecks."""

    def __init__(self, db: Database):
        """Initialize bottleneck detector.

        Args:
            db: Database connection
        """
        self.db = db

    def detect_person_overload(self, project_id: int) -> List[Bottleneck]:
        """Detect if any person is overloaded.

        Args:
            project_id: Project to analyze

        Returns:
            List of person overload bottlenecks
        """
        bottlenecks = []

        try:
            cursor = self.db.get_cursor()

            # Count tasks per person
            cursor.execute(
                """
                SELECT assignee, COUNT(*) as task_count,
                       GROUP_CONCAT(id) as task_ids
                FROM prospective_tasks
                WHERE project_id = ? AND status IN ('active', 'pending')
                AND assignee IS NOT NULL
                GROUP BY assignee
                ORDER BY task_count DESC
                """,
                (project_id,),
            )

            overload_threshold = 3  # More than 3 concurrent tasks

            for row in cursor.fetchall():
                assignee = row[0]
                task_count = row[1]
                task_ids_str = row[2]

                if task_count > overload_threshold:
                    task_ids = [
                        int(t.strip())
                        for t in task_ids_str.split(",")
                        if t.strip()
                    ]

                    severity = (
                        "critical"
                        if task_count > 5
                        else "high"
                        if task_count > 4
                        else "medium"
                    )

                    recommendations = [
                        f"Reassign {task_count - overload_threshold} tasks from {assignee}",
                        "Prioritize critical tasks only",
                        "Consider bringing in additional person",
                    ]

                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_type="person",
                            resource=assignee,
                            current_load=task_count,
                            severity=severity,
                            impact_hours=task_count * 8,  # Rough estimate
                            affected_tasks=task_ids[:5],
                            recommendations=recommendations,
                        )
                    )

            return bottlenecks
        except Exception:
            return []

    def detect_blocked_tasks(self, project_id: int) -> List[Bottleneck]:
        """Detect tasks blocked by dependencies or issues.

        Args:
            project_id: Project to analyze

        Returns:
            List of blocking bottlenecks
        """
        bottlenecks = []

        try:
            cursor = self.db.get_cursor()

            # Find blocked tasks
            cursor.execute(
                """
                SELECT id, blocked_reason, COUNT(*) OVER (
                    PARTITION BY blocked_reason
                ) as blocker_count
                FROM prospective_tasks
                WHERE project_id = ? AND status = 'blocked'
                AND blocked_reason IS NOT NULL
                ORDER BY blocker_count DESC
                """,
                (project_id,),
            )

            seen_blockers = set()

            for row in cursor.fetchall():
                task_id = row[0]
                blocker_reason = row[1]
                blocker_count = row[2]

                if blocker_reason not in seen_blockers:
                    # Extract blocker type
                    blocker_type = (
                        "dependency"
                        if "depend" in blocker_reason.lower()
                        else "tool"
                        if "tool" in blocker_reason.lower()
                        else "knowledge"
                        if "know" in blocker_reason.lower()
                        else "other"
                    )

                    recommendations = [
                        f"Resolve blocker: {blocker_reason}",
                        f"Affects {blocker_count} tasks",
                        "Escalate if external dependency",
                    ]

                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_type=blocker_type,
                            resource=blocker_reason[:50],
                            current_load=blocker_count,
                            severity=(
                                "critical"
                                if blocker_count > 3
                                else "high"
                                if blocker_count > 1
                                else "medium"
                            ),
                            impact_hours=blocker_count * 4,
                            affected_tasks=[task_id],
                            recommendations=recommendations,
                        )
                    )

                    seen_blockers.add(blocker_reason)

            return bottlenecks
        except Exception:
            return []

    def detect_tool_contention(self, project_id: int) -> List[Bottleneck]:
        """Detect if tools/resources are contended.

        Args:
            project_id: Project to analyze

        Returns:
            List of tool contention bottlenecks
        """
        bottlenecks = []

        try:
            cursor = self.db.get_cursor()

            # Find tasks requiring same tools/data
            cursor.execute(
                """
                SELECT content, COUNT(*) as count, GROUP_CONCAT(id) as task_ids
                FROM prospective_tasks
                WHERE project_id = ? AND status IN ('active', 'pending', 'executing')
                GROUP BY content
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 5
                """,
                (project_id,),
            )

            for row in cursor.fetchall():
                content = row[0]
                count = row[1]
                task_ids_str = row[2]

                if count > 2:  # Multiple tasks using same resource
                    task_ids = [
                        int(t.strip())
                        for t in task_ids_str.split(",")
                        if t.strip()
                    ]

                    bottlenecks.append(
                        Bottleneck(
                            bottleneck_type="tool",
                            resource=content[:40],
                            current_load=count,
                            severity=(
                                "high"
                                if count > 3
                                else "medium"
                            ),
                            impact_hours=count * 2,
                            affected_tasks=task_ids,
                            recommendations=[
                                "Serialize task execution",
                                "Request additional licenses/access",
                                "Parallelize if possible",
                            ],
                        )
                    )

            return bottlenecks
        except Exception:
            return []

    def get_project_bottlenecks(
        self, project_id: int
    ) -> Dict[str, any]:
        """Get comprehensive bottleneck analysis for project.

        Args:
            project_id: Project to analyze

        Returns:
            Dictionary with all bottleneck types
        """
        person_bottlenecks = self.detect_person_overload(project_id)
        blocked_bottlenecks = self.detect_blocked_tasks(project_id)
        tool_bottlenecks = self.detect_tool_contention(project_id)

        all_bottlenecks = (
            person_bottlenecks
            + blocked_bottlenecks
            + tool_bottlenecks
        )

        # Sort by severity and impact
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_bottlenecks.sort(
            key=lambda b: (
                severity_order.get(b.severity, 4),
                -b.impact_hours,
            )
        )

        return {
            "project_id": project_id,
            "total_bottlenecks": len(all_bottlenecks),
            "critical_count": sum(
                1 for b in all_bottlenecks if b.severity == "critical"
            ),
            "person_bottlenecks": len(person_bottlenecks),
            "blocked_bottlenecks": len(blocked_bottlenecks),
            "tool_bottlenecks": len(tool_bottlenecks),
            "bottlenecks": [
                {
                    "type": b.bottleneck_type,
                    "resource": b.resource,
                    "load": b.current_load,
                    "severity": b.severity,
                    "impact_hours": b.impact_hours,
                    "recommendations": b.recommendations,
                }
                for b in all_bottlenecks[:5]
            ],
            "overall_health": self._assess_health(all_bottlenecks),
        }

    def _assess_health(self, bottlenecks: List[Bottleneck]) -> str:
        """Assess overall resource health.

        Args:
            bottlenecks: List of detected bottlenecks

        Returns:
            Health assessment string
        """
        if not bottlenecks:
            return "Excellent - no bottlenecks detected"

        critical_count = sum(
            1 for b in bottlenecks if b.severity == "critical"
        )
        high_count = sum(1 for b in bottlenecks if b.severity == "high")

        if critical_count > 0:
            return f"Critical - {critical_count} critical bottlenecks"
        elif high_count > 2:
            return f"Poor - {high_count} high-severity bottlenecks"
        elif high_count > 0:
            return f"Fair - {high_count} high-severity bottlenecks"
        else:
            return "Good - only minor bottlenecks"

    def suggest_rebalancing(
        self, project_id: int
    ) -> List[Dict[str, any]]:
        """Suggest resource rebalancing options.

        Args:
            project_id: Project to analyze

        Returns:
            List of rebalancing suggestions
        """
        suggestions = []

        # Get person bottlenecks
        person_bottlenecks = (
            self.detect_person_overload(project_id)
        )
        for bottleneck in person_bottlenecks:
            suggestions.append(
                {
                    "action": "reassign",
                    "from": bottleneck.resource,
                    "task_ids": bottleneck.affected_tasks[:2],
                    "reason": f"Person overloaded with {bottleneck.current_load} tasks",
                    "priority": "high"
                    if bottleneck.severity == "critical"
                    else "medium",
                }
            )

        # Get blocked tasks
        blocked_bottlenecks = self.detect_blocked_tasks(project_id)
        for bottleneck in blocked_bottlenecks:
            suggestions.append(
                {
                    "action": "unblock",
                    "blocker": bottleneck.resource,
                    "task_ids": bottleneck.affected_tasks,
                    "reason": f"Tasks blocked by {bottleneck.resource}",
                    "priority": "critical"
                    if bottleneck.severity == "critical"
                    else "high",
                }
            )

        return suggestions[:5]  # Top 5 suggestions

    def estimate_resolution_impact(
        self, bottleneck: Bottleneck
    ) -> Dict[str, any]:
        """Estimate impact of resolving bottleneck.

        Args:
            bottleneck: Bottleneck to resolve

        Returns:
            Dictionary with impact estimates
        """
        return {
            "bottleneck_type": bottleneck.bottleneck_type,
            "resource": bottleneck.resource,
            "tasks_unblocked": len(bottleneck.affected_tasks),
            "hours_saved": bottleneck.impact_hours * 0.5,  # Estimate 50% improvement
            "timeline_improvement_hours": bottleneck.impact_hours,
            "effort_to_resolve_hours": (
                2 if bottleneck.severity == "critical" else 4
            ),
            "roi": "High" if bottleneck.severity == "critical" else "Medium",
        }
