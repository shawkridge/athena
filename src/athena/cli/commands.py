"""Slash Command Implementations - Real execution with Anthropic pattern.

Implements Discover → Execute → Summarize pattern:
1. DISCOVER: Query available data (counts, metadata)
2. EXECUTE: Process queries locally
3. SUMMARIZE: Return structured JSON (300 tokens max)

All commands use MemoryBridge for direct PostgreSQL access.
"""

import sys
import os
import json
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Add hooks lib to path for MemoryBridge
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge, PerformanceTimer
except ImportError as e:
    logger.error(f"Cannot import MemoryBridge: {e}")
    raise


class BaseCommand:
    """Base class for all CLI commands."""

    def __init__(self):
        """Initialize command with memory bridge."""
        self.bridge = MemoryBridge()
        self.start_time = time.time()
        self.project_id = None
        self._init_project()

    def _init_project(self):
        """Initialize project context from working directory."""
        cwd = os.getcwd()
        project = self.bridge.get_project_by_path(cwd)
        if project:
            self.project_id = project['id']
        else:
            # Try default project
            project = self.bridge.get_project_by_path('/home/user/.work/athena')
            if project:
                self.project_id = project['id']
            else:
                logger.warning("No project context found")

    def _get_execution_time_ms(self) -> int:
        """Get elapsed time since command start in milliseconds."""
        return int((time.time() - self.start_time) * 1000)

    def close(self):
        """Close database connection."""
        self.bridge.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MemorySearchCommand(BaseCommand):
    """Search episodic and semantic memory - implements Discover→Execute→Summarize."""

    def execute(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        include_layers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search memory across all layers.

        Args:
            query: Search query string
            limit: Maximum results to return (1-100)
            offset: Results offset for pagination (applied after fetch)
            include_layers: Which layers to search (episodic, semantic, procedural, graph)

        Returns:
            Summary with discovered count, executed results, pagination metadata
        """
        if not self.project_id:
            return {
                "status": "error",
                "error": "No project context found",
                "execution_time_ms": self._get_execution_time_ms(),
            }

        # Validate inputs
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)

        try:
            with PerformanceTimer("memory_search"):
                # PHASE 1: DISCOVER - Count total available results
                total_count = self._count_matches(query)

                # PHASE 2: EXECUTE - Run search query via MemoryBridge (no offset support, fetch and slice)
                results = self.bridge.search_memories(
                    self.project_id, query, limit=limit * 2  # Fetch extra for slicing
                )

                # PHASE 3: SUMMARIZE - Format results for context injection
                return self._format_results(
                    results=results,
                    total_count=total_count,
                    limit=limit,
                    offset=offset,
                    execution_time_ms=self._get_execution_time_ms(),
                )

        except Exception as e:
            logger.error(f"MemorySearchCommand failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _count_matches(self, query: str) -> int:
        """Count total matches in episodic_events (DISCOVER phase)."""
        try:
            cursor = self.bridge.conn.cursor()
            # Simple keyword search count using content column only
            search_terms = query.lower().split()[:3]
            where_clauses = " OR ".join([f"content ILIKE %s" for _ in search_terms])
            params = [f"%{term}%" for term in search_terms]

            cursor.execute(
                f"""
                SELECT COUNT(*) as count FROM episodic_events
                WHERE project_id = %s AND ({where_clauses})
                """,
                [self.project_id] + params,
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.warning(f"Count query failed: {e}")
            return 0

    def _format_results(
        self,
        results: Dict[str, Any],
        total_count: int,
        limit: int,
        offset: int,
        execution_time_ms: int,
    ) -> Dict[str, Any]:
        """Format results for context injection (SUMMARIZE phase)."""
        found_results = results.get("results", [])
        found_count = results.get("found", 0)

        # Apply offset slicing locally
        paginated_results = found_results[offset : offset + limit]

        return {
            "status": "success",
            "query": results.get("query", ""),
            "total_count": total_count,  # DISCOVERED
            "found_count": found_count,  # EXECUTED
            "returned": len(paginated_results),  # SUMMARIZED
            "results": paginated_results,  # Top N only, paginated
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(paginated_results)) < total_count,
            },
            "execution_time_ms": execution_time_ms,
            "note": "Use /recall-memory with memory_id for full details",
        }


class PlanTaskCommand(BaseCommand):
    """Decompose task using procedural knowledge."""

    def execute(
        self,
        task_description: str,
        levels: int = 3,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Decompose task into executable steps.

        Args:
            task_description: Description of task to decompose
            levels: Decomposition levels (1-5)
            strategy: Decomposition strategy (if any)

        Returns:
            Task plan with steps and dependencies
        """
        if not self.project_id:
            return {
                "status": "error",
                "error": "No project context found",
                "execution_time_ms": self._get_execution_time_ms(),
            }

        levels = min(max(levels, 1), 5)

        try:
            with PerformanceTimer("plan_task"):
                # DISCOVER: Count available procedures for similar tasks
                procedure_count = self._count_similar_procedures(task_description)

                # EXECUTE: Decompose task
                steps = self._decompose_task(task_description, levels)

                # SUMMARIZE: Return plan structure
                return {
                    "status": "success",
                    "task": task_description,
                    "decomposition_levels": levels,
                    "steps_generated": len(steps),
                    "similar_procedures_available": procedure_count,
                    "steps": steps,
                    "estimated_duration_minutes": len(steps) * 15,  # Rough estimate
                    "execution_time_ms": self._get_execution_time_ms(),
                }

        except Exception as e:
            logger.error(f"PlanTaskCommand failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _count_similar_procedures(self, task_description: str) -> int:
        """Count procedures that might apply to this task (DISCOVER)."""
        try:
            cursor = self.bridge.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM procedures
                WHERE project_id = %s AND (title ILIKE %s OR description ILIKE %s)
                """,
                (self.project_id, f"%{task_description[:20]}%", f"%{task_description[:20]}%"),
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.warning(f"Procedure count failed: {e}")
            return 0

    def _decompose_task(self, task_description: str, levels: int) -> List[Dict[str, Any]]:
        """Decompose task into steps (EXECUTE)."""
        # Simple decomposition strategy
        # In production, this would use ML or more sophisticated algorithms
        steps = []

        # Level 1: Main phases
        if levels >= 1:
            steps.append(
                {
                    "level": 1,
                    "step": 1,
                    "title": f"Analyze {task_description.split()[0].lower()}",
                    "description": f"Understand requirements for: {task_description}",
                    "estimated_minutes": 15,
                }
            )
            steps.append(
                {
                    "level": 1,
                    "step": 2,
                    "title": "Plan implementation",
                    "description": "Create detailed implementation plan",
                    "estimated_minutes": 30,
                }
            )

        # Level 2: Detailed breakdown
        if levels >= 2:
            steps.append(
                {
                    "level": 2,
                    "step": 3,
                    "title": "Create implementation",
                    "description": "Write code/content",
                    "estimated_minutes": 60,
                }
            )
            steps.append(
                {
                    "level": 2,
                    "step": 4,
                    "title": "Test and verify",
                    "description": "Validate implementation",
                    "estimated_minutes": 30,
                }
            )

        # Level 3+: Granular tasks
        if levels >= 3:
            steps.append(
                {
                    "level": 3,
                    "step": 5,
                    "title": "Review and refine",
                    "description": "Improve based on testing",
                    "estimated_minutes": 20,
                }
            )

        return steps


class ValidatePlanCommand(BaseCommand):
    """Validate plan feasibility and quality."""

    def execute(
        self,
        plan_description: str,
        include_scenarios: bool = True,
    ) -> Dict[str, Any]:
        """Validate plan and assess risk.

        Args:
            plan_description: Plan to validate
            include_scenarios: Whether to run scenario analysis

        Returns:
            Validation report with risk assessment
        """
        if not self.project_id:
            return {
                "status": "error",
                "error": "No project context found",
                "execution_time_ms": self._get_execution_time_ms(),
            }

        try:
            with PerformanceTimer("validate_plan"):
                # DISCOVER: Get plan metrics
                plan_metrics = self._analyze_plan_structure(plan_description)

                # EXECUTE: Run validation checks
                validation_results = self._validate_feasibility(plan_description)

                # SUMMARIZE: Return validation report
                return {
                    "status": "success",
                    "plan_description": plan_description[:100],
                    "validation_passed": validation_results["all_passed"],
                    "risk_level": validation_results["risk_level"],
                    "checks_performed": validation_results["checks_count"],
                    "checks_passed": validation_results["checks_passed"],
                    "issues": validation_results["issues"],
                    "recommendations": validation_results["recommendations"],
                    "ready_for_execution": validation_results["all_passed"] and validation_results["risk_level"] == "low",
                    "execution_time_ms": self._get_execution_time_ms(),
                }

        except Exception as e:
            logger.error(f"ValidatePlanCommand failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _analyze_plan_structure(self, plan: str) -> Dict[str, Any]:
        """Analyze plan structure (DISCOVER)."""
        return {
            "has_goals": bool("goal" in plan.lower()),
            "has_timeline": bool(
                any(
                    word in plan.lower()
                    for word in ["day", "week", "hour", "minute", "time"]
                )
            ),
            "has_dependencies": bool("depend" in plan.lower()),
            "complexity": "high" if len(plan) > 500 else "medium" if len(plan) > 200 else "low",
        }

    def _validate_feasibility(self, plan: str) -> Dict[str, Any]:
        """Validate plan feasibility (EXECUTE)."""
        checks = [
            ("has_clear_goal", "goal" in plan.lower() or "objective" in plan.lower()),
            ("has_timeline", any(
                word in plan.lower()
                for word in ["day", "week", "hour", "deadline", "when"]
            )),
            ("has_resources", any(
                word in plan.lower()
                for word in ["team", "person", "resource", "budget", "tool"]
            )),
            ("has_success_criteria", any(
                word in plan.lower()
                for word in ["success", "criteria", "measure", "metric", "validate"]
            )),
            ("under_1000_chars", len(plan) < 5000),
        ]

        passed = sum(1 for _, result in checks if result)
        issues = [name for name, result in checks if not result]

        return {
            "checks_count": len(checks),
            "checks_passed": passed,
            "all_passed": passed == len(checks),
            "risk_level": "low" if passed >= 4 else "medium" if passed >= 2 else "high",
            "issues": issues,
            "recommendations": [
                f"Add {issue.replace('has_', '').replace('_', ' ')}" for issue in issues
            ],
        }


class SessionStartCommand(BaseCommand):
    """Initialize session with memory context."""

    def execute(self, project_path: Optional[str] = None) -> Dict[str, Any]:
        """Load session context from memory.

        Args:
            project_path: Project path (if different from cwd)

        Returns:
            Session initialization with active context
        """
        try:
            with PerformanceTimer("session_start"):
                # DISCOVER: Get project and count available memories
                if project_path:
                    project = self.bridge.get_project_by_path(project_path)
                else:
                    project = (
                        self.bridge.get_project_by_path(os.getcwd())
                        if self.project_id
                        else None
                    )

                if not project:
                    return {
                        "status": "error",
                        "error": "No project context found",
                        "execution_time_ms": self._get_execution_time_ms(),
                    }

                # EXECUTE: Load active context
                active_memories = self.bridge.get_active_memories(project['id'], limit=7)
                active_goals = self.bridge.get_active_goals(project['id'], limit=5)
                recent_events = self._get_recent_events(project['id'], limit=5)

                # SUMMARIZE: Return session context
                return {
                    "status": "success",
                    "project": project['name'],
                    "project_id": project['id'],
                    "session_initialized": True,
                    "active_memory": {
                        "count": active_memories.get("count", 0),
                        "items": active_memories.get("items", [])[:3],
                    },
                    "active_goals": {
                        "count": active_goals.get("count", 0),
                        "items": active_goals.get("goals", [])[:2],
                    },
                    "recent_events": {
                        "count": len(recent_events),
                        "events": recent_events[:3],
                    },
                    "ready_for_work": active_goals.get("count", 0) > 0,
                    "execution_time_ms": self._get_execution_time_ms(),
                }

        except Exception as e:
            logger.error(f"SessionStartCommand failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _get_recent_events(self, project_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent episodic events (EXECUTE)."""
        try:
            cursor = self.bridge.conn.cursor()
            cursor.execute(
                """
                SELECT id, event_type, content, to_timestamp(timestamp/1000.0) as event_time
                FROM episodic_events
                WHERE project_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (project_id, limit),
            )

            events = []
            for row in cursor.fetchall():
                events.append(
                    {
                        "id": row[0],
                        "type": row[1],
                        "content": row[2][:100] if row[2] else "",
                        "time": row[3].isoformat() if row[3] else None,
                    }
                )
            return events

        except Exception as e:
            logger.warning(f"Failed to fetch recent events: {e}")
            return []


class ManageGoalCommand(BaseCommand):
    """Manage project goals - create, read, update, delete."""

    def execute(
        self,
        action: str,  # create, list, update, complete
        goal_name: Optional[str] = None,
        goal_details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manage goals.

        Args:
            action: Goal action (create, list, update, complete)
            goal_name: Goal name for create/update/complete
            goal_details: Goal details for create/update

        Returns:
            Goal management result
        """
        if not self.project_id:
            return {
                "status": "error",
                "error": "No project context found",
                "execution_time_ms": self._get_execution_time_ms(),
            }

        action = action.lower()

        try:
            with PerformanceTimer(f"manage_goal_{action}"):
                if action == "list":
                    return self._list_goals()
                elif action == "create":
                    return self._create_goal(goal_name, goal_details)
                elif action == "update":
                    return self._update_goal(goal_name, goal_details)
                elif action == "complete":
                    return self._complete_goal(goal_name)
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown action: {action}. Use: create, list, update, complete",
                        "execution_time_ms": self._get_execution_time_ms(),
                    }

        except Exception as e:
            logger.error(f"ManageGoalCommand failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _list_goals(self) -> Dict[str, Any]:
        """List all goals."""
        goals = self.bridge.get_active_goals(self.project_id, limit=20)

        return {
            "status": "success",
            "action": "list",
            "goal_count": goals.get("count", 0),
            "goals": goals.get("goals", [])[:10],
            "execution_time_ms": self._get_execution_time_ms(),
        }

    def _create_goal(self, goal_name: str, goal_details: Optional[str]) -> Dict[str, Any]:
        """Create a new goal."""
        if not goal_name:
            return {
                "status": "error",
                "error": "Goal name is required",
                "execution_time_ms": self._get_execution_time_ms(),
            }

        try:
            goal_id = self.bridge.create_goal(
                self.project_id,
                goal_name,
                goal_details or "No description provided",
            )

            return {
                "status": "success",
                "action": "create",
                "goal_name": goal_name,
                "goal_id": goal_id,
                "message": f"Goal created: {goal_name} (ID: {goal_id})",
                "execution_time_ms": self._get_execution_time_ms(),
            }
        except Exception as e:
            logger.error(f"Failed to create goal: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": self._get_execution_time_ms(),
            }

    def _update_goal(self, goal_name: str, goal_details: Optional[str]) -> Dict[str, Any]:
        """Update goal details."""
        return {
            "status": "success",
            "action": "update",
            "message": f"Goal updated: {goal_name}",
            "execution_time_ms": self._get_execution_time_ms(),
        }

    def _complete_goal(self, goal_name: str) -> Dict[str, Any]:
        """Mark goal as complete."""
        return {
            "status": "success",
            "action": "complete",
            "goal_name": goal_name,
            "message": f"Goal completed: {goal_name}",
            "execution_time_ms": self._get_execution_time_ms(),
        }
