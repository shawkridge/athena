"""Plan Learner Skill - Extract reusable planning patterns from executed tasks.

Learns from successful and failed task executions to:
- Build task type templates
- Create risk checklists
- Extract estimation heuristics
- Identify reusable step sequences
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..core.database import Database


@dataclass
class TaskTemplate:
    """Reusable task template."""

    task_type: str
    description: str
    typical_steps: List[str]
    estimated_duration_hours: float
    common_risks: List[str]
    prerequisite_knowledge: List[str]
    success_rate: float
    last_updated: str


class PlanLearner:
    """Learn planning patterns from executed tasks."""

    def __init__(self, db: Database):
        """Initialize plan learner.

        Args:
            db: Database connection
        """
        self.db = db

    def extract_task_templates(
        self, project_id: int, min_samples: int = 3
    ) -> Dict[str, TaskTemplate]:
        """Extract task templates from completed tasks.

        Args:
            project_id: Project to analyze
            min_samples: Minimum completed tasks to define template

        Returns:
            Dictionary of task_type -> TaskTemplate
        """
        templates = {}

        try:
            cursor = self.db.get_cursor()

            # Get completed tasks grouped by type keywords
            cursor.execute(
                """
                SELECT
                    id, content, estimated_duration_minutes,
                    actual_duration_minutes, blocker_reason, failure_reason,
                    created_at
                FROM prospective_tasks
                WHERE project_id = ? AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (project_id,),
            )

            completed_tasks = cursor.fetchall()

            # Group by task type
            task_groups = self._group_by_type(completed_tasks)

            for task_type, tasks in task_groups.items():
                if len(tasks) >= min_samples:
                    template = self._build_template(task_type, tasks)
                    templates[task_type] = template

            return templates
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return {}

    def _group_by_type(self, tasks: List) -> Dict[str, List]:
        """Group tasks by inferred type.

        Args:
            tasks: List of task tuples

        Returns:
            Dictionary of type -> task list
        """
        groups = {}
        task_type_keywords = {
            "implementation": ["implement", "add", "create", "build"],
            "bug_fix": ["bug", "fix", "error", "issue"],
            "refactoring": ["refactor", "clean", "optimize", "restructure"],
            "documentation": ["document", "write", "explain", "readme"],
            "testing": ["test", "verify", "check", "validate"],
            "research": ["research", "investigate", "explore", "learn"],
        }

        for task in tasks:
            content = task[1].lower() if task[1] else ""
            assigned_type = "other"

            for type_name, keywords in task_type_keywords.items():
                if any(kw in content for kw in keywords):
                    assigned_type = type_name
                    break

            if assigned_type not in groups:
                groups[assigned_type] = []
            groups[assigned_type].append(task)

        return groups

    def _build_template(
        self, task_type: str, tasks: List
    ) -> TaskTemplate:
        """Build template from task samples.

        Args:
            task_type: Type of task
            tasks: Sample completed tasks

        Returns:
            TaskTemplate for this type
        """
        # Calculate metrics
        durations = [
            t[4] for t in tasks if t[4]
        ]  # actual_duration_minutes
        avg_duration = (
            sum(durations) / len(durations) / 60 if durations else 2.0
        )

        # Extract common risks
        risks = []
        blockers = [t[5] for t in tasks if t[5]]  # blocker_reason
        if blockers:
            risks.extend(
                [f"Blocker: {b}" for b in blockers[:2]]
            )

        failures = [t[6] for t in tasks if t[6]]  # failure_reason
        if failures:
            risks.extend(
                [f"Common failure: {f}" for f in failures[:2]]
            )

        if not risks:
            risks = self._get_default_risks(task_type)

        # Extract typical steps
        steps = self._extract_typical_steps(task_type)

        # Calculate success rate
        success_count = len([t for t in tasks if not t[6]])  # Not failed
        success_rate = (
            success_count / len(tasks) if tasks else 0
        )

        # Get prerequisite knowledge
        prerequisites = self._get_prerequisites(task_type)

        return TaskTemplate(
            task_type=task_type,
            description=f"Template for {task_type} tasks",
            typical_steps=steps,
            estimated_duration_hours=avg_duration,
            common_risks=risks[:3],
            prerequisite_knowledge=prerequisites,
            success_rate=success_rate,
            last_updated=datetime.utcnow().isoformat(),
        )

    def _get_default_risks(self, task_type: str) -> List[str]:
        """Get default risks for task type.

        Args:
            task_type: Type of task

        Returns:
            List of common risks
        """
        default_risks = {
            "implementation": [
                "Scope creep - document requirements clearly",
                "Integration issues - test frequently",
                "Performance regression - benchmark baseline",
            ],
            "bug_fix": [
                "Root cause misidentification - trace carefully",
                "New bugs introduced - add regression tests",
                "Incomplete fix - test edge cases",
            ],
            "refactoring": [
                "Breaking changes - maintain backward compatibility",
                "Performance degradation - profile before/after",
                "Hidden dependencies - test comprehensively",
            ],
            "documentation": [
                "Outdated examples - keep in sync",
                "Unclear explanations - seek feedback",
                "Missing edge cases - document thoroughly",
            ],
            "testing": [
                "False positives - verify test logic",
                "Incomplete coverage - identify gaps",
                "Flaky tests - investigate timing issues",
            ],
            "research": [
                "Analysis paralysis - set time limits",
                "Contradictory sources - verify authority",
                "Context drift - document assumptions",
            ],
        }

        return default_risks.get(
            task_type,
            ["Plan carefully", "Test thoroughly", "Document clearly"],
        )

    def _extract_typical_steps(self, task_type: str) -> List[str]:
        """Extract typical execution steps for task type.

        Args:
            task_type: Type of task

        Returns:
            List of step descriptions
        """
        step_templates = {
            "implementation": [
                "1. Understand requirements and acceptance criteria",
                "2. Design solution (architecture, algorithms)",
                "3. Implement core functionality",
                "4. Add error handling and edge cases",
                "5. Write tests and documentation",
                "6. Code review and refine",
                "7. Deploy and monitor",
            ],
            "bug_fix": [
                "1. Reproduce the bug consistently",
                "2. Isolate the root cause",
                "3. Implement minimal fix",
                "4. Add regression test",
                "5. Verify fix in various scenarios",
                "6. Document fix and lessons learned",
                "7. Deploy with monitoring",
            ],
            "refactoring": [
                "1. Define refactoring goals",
                "2. Ensure comprehensive test coverage",
                "3. Refactor in small increments",
                "4. Verify no behavioral changes",
                "5. Performance benchmarking",
                "6. Code review for improvements",
                "7. Deploy and monitor",
            ],
            "documentation": [
                "1. Identify audience and goals",
                "2. Outline structure and flow",
                "3. Write first draft",
                "4. Create examples and diagrams",
                "5. Peer review for clarity",
                "6. Update after feedback",
                "7. Version control and publish",
            ],
            "testing": [
                "1. Define test scope and objectives",
                "2. Identify test cases and scenarios",
                "3. Implement unit/integration tests",
                "4. Run test suite and validate",
                "5. Measure code coverage",
                "6. Document test results",
                "7. Archive for regression",
            ],
            "research": [
                "1. Define research question clearly",
                "2. Gather sources (documentation, code, experts)",
                "3. Read and synthesize information",
                "4. Test hypothesis with experiments",
                "5. Document findings and examples",
                "6. Identify gaps and next steps",
                "7. Share knowledge with team",
            ],
        }

        return step_templates.get(
            task_type,
            [
                "1. Plan approach",
                "2. Execute work",
                "3. Test results",
                "4. Document",
                "5. Review and refine",
            ],
        )

    def _get_prerequisites(self, task_type: str) -> List[str]:
        """Get prerequisite knowledge for task type.

        Args:
            task_type: Type of task

        Returns:
            List of prerequisite knowledge areas
        """
        prerequisites = {
            "implementation": [
                "System architecture understanding",
                "Required technology stack",
                "Coding standards",
            ],
            "bug_fix": [
                "System behavior understanding",
                "Debugging techniques",
                "Test writing",
            ],
            "refactoring": [
                "Original design intent",
                "Current code patterns",
                "Testing framework",
            ],
            "documentation": [
                "Product knowledge",
                "Target audience",
                "Documentation tool proficiency",
            ],
            "testing": [
                "Test framework knowledge",
                "Acceptance criteria",
                "System behavior",
            ],
            "research": [
                "Domain knowledge",
                "Research methodology",
                "Documentation skills",
            ],
        }

        return prerequisites.get(
            task_type,
            ["Domain knowledge", "Technical skills", "Testing ability"],
        )

    def build_risk_checklist(
        self, project_id: int, task_type: str
    ) -> Dict[str, any]:
        """Build risk checklist for task type.

        Args:
            project_id: Project context
            task_type: Type of task

        Returns:
            Dictionary with risk checklist
        """
        templates = self.extract_task_templates(project_id)
        template = templates.get(task_type)

        if not template:
            # Build default checklist
            checklist_items = self._get_default_checklist(
                task_type
            )
        else:
            checklist_items = [
                {
                    "item": risk,
                    "check": False,
                    "notes": "",
                }
                for risk in template.common_risks
            ]

        return {
            "task_type": task_type,
            "checklist": checklist_items,
            "instructions": f"Before starting {task_type} task, verify all items",
            "template_confidence": (
                template.success_rate if template else 0.5
            ),
        }

    def _get_default_checklist(
        self, task_type: str
    ) -> List[Dict[str, any]]:
        """Get default risk checklist.

        Args:
            task_type: Type of task

        Returns:
            List of checklist items
        """
        return [
            {"item": "Requirements clear and documented", "check": False},
            {"item": "Dependencies identified", "check": False},
            {"item": "Test strategy defined", "check": False},
            {"item": "Time estimate validated", "check": False},
            {"item": "Blockers identified and mitigated", "check": False},
            {
                "item": "Peer review scheduled",
                "check": False,
            },
        ]

    async def suggest_execution_approach(
        self, project_id: int, task_type: str
    ) -> Dict[str, any]:
        """Suggest execution approach based on templates.

        Args:
            project_id: Project context
            task_type: Task type

        Returns:
            Dictionary with execution suggestions
        """
        templates = self.extract_task_templates(project_id)
        template = templates.get(task_type)

        if template:
            return {
                "task_type": task_type,
                "approach": "Use learned template",
                "typical_steps": template.typical_steps,
                "estimated_duration_hours": template.estimated_duration_hours,
                "success_rate": template.success_rate,
                "risks": template.common_risks,
                "prerequisites": template.prerequisite_knowledge,
                "confidence": "High" if template.success_rate > 0.7 else "Medium",
            }
        else:
            return {
                "task_type": task_type,
                "approach": "Use default approach",
                "confidence": "Low - insufficient historical data",
                "recommendation": f"Execute and document for future {task_type} tasks",
            }
