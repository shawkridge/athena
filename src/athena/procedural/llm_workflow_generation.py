"""LLM-powered procedural workflow auto-generation and documentation.

Automatically generates reusable workflows from completed tasks and documents them.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from ..rag.llm_client import OllamaLLMClient

logger = logging.getLogger(__name__)


@dataclass
class GeneratedWorkflow:
    """Auto-generated reusable workflow."""

    name: str
    description: str
    steps: list[str]
    prerequisites: list[str]
    expected_outcomes: list[str]
    estimated_duration_mins: int
    complexity_level: int  # 1-10
    category: str  # "coding", "debugging", "deployment", "refactoring", "testing"
    success_criteria: list[str]
    common_pitfalls: list[str]
    automation_opportunities: list[str]
    confidence: float  # 0.0-1.0: How confident is this workflow?


class LLMWorkflowGenerator:
    """Generate and document reusable workflows using LLM reasoning."""

    def __init__(self, llm_client: Optional[OllamaLLMClient] = None):
        """Initialize workflow generator.

        Args:
            llm_client: Optional LLM client for advanced generation
        """
        self.llm_client = llm_client
        self._use_llm = llm_client is not None

        if self._use_llm:
            logger.info("LLM workflow generator: Auto-generation enabled")
        else:
            logger.info("LLM workflow generator: Using heuristic generation")

    def generate_workflow_from_task(
        self, task_description: str, steps_taken: list[str], outcome: str, duration_mins: int
    ) -> Optional[GeneratedWorkflow]:
        """Generate a reusable workflow from a completed task.

        Args:
            task_description: What was the task?
            steps_taken: Steps actually taken
            outcome: What was the result?
            duration_mins: How long did it take?

        Returns:
            GeneratedWorkflow if reusable pattern found, None otherwise
        """
        if self._use_llm:
            return self._generate_with_llm(task_description, steps_taken, outcome, duration_mins)
        else:
            return self._generate_heuristic(task_description, steps_taken, outcome, duration_mins)

    def _generate_with_llm(
        self, task_description: str, steps_taken: list[str], outcome: str, duration_mins: int
    ) -> Optional[GeneratedWorkflow]:
        """Generate workflow using LLM reasoning."""

        try:
            steps_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps_taken))

            prompt = f"""Analyze this completed task and extract a reusable workflow.

TASK: {task_description}

STEPS TAKEN:
{steps_str}

OUTCOME: {outcome}
DURATION: {duration_mins} minutes

Determine if this represents a reusable pattern that could be applied to similar tasks in the future.

If reusable, extract:
1. Workflow name (concise, action-oriented)
2. Generic description (applicable to similar tasks)
3. Generalized steps (remove task-specific details)
4. Prerequisites (what must be true before starting)
5. Expected outcomes
6. Category (coding, debugging, deployment, refactoring, testing)
7. Complexity (1-10)
8. Success criteria
9. Common pitfalls to avoid
10. Automation opportunities

Respond with JSON:
{{
    "is_reusable": true|false,
    "reason": "why this is/isn't reusable",
    "name": "...",
    "description": "...",
    "steps": ["step 1", "step 2", ...],
    "prerequisites": ["prereq 1", ...],
    "expected_outcomes": ["outcome 1", ...],
    "category": "coding|debugging|deployment|refactoring|testing",
    "complexity_level": 1-10,
    "success_criteria": ["criterion 1", ...],
    "common_pitfalls": ["pitfall 1", ...],
    "automation_opportunities": ["opportunity 1", ...]
}}

Be selective - only mark as reusable if truly generalizable."""

            result = self.llm_client.generate(prompt, max_tokens=600)
            analysis = json.loads(result)

            if not analysis.get("is_reusable", False):
                logger.debug(f"Task not identified as reusable: {analysis.get('reason', '')}")
                return None

            workflow = GeneratedWorkflow(
                name=analysis.get("name", "Workflow"),
                description=analysis.get("description", ""),
                steps=analysis.get("steps", []),
                prerequisites=analysis.get("prerequisites", []),
                expected_outcomes=analysis.get("expected_outcomes", []),
                estimated_duration_mins=duration_mins,
                complexity_level=int(analysis.get("complexity_level", 5)),
                category=analysis.get("category", "coding"),
                success_criteria=analysis.get("success_criteria", []),
                common_pitfalls=analysis.get("common_pitfalls", []),
                automation_opportunities=analysis.get("automation_opportunities", []),
                confidence=0.85,  # LLM analysis has good confidence
            )

            logger.info(f"Generated workflow: {workflow.name}")
            return workflow

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse LLM response: {e}")
            return None
        except Exception as e:
            logger.debug(f"Workflow generation failed: {e}")
            return None

    def _generate_heuristic(
        self, task_description: str, steps_taken: list[str], outcome: str, duration_mins: int
    ) -> Optional[GeneratedWorkflow]:
        """Generate workflow using heuristic rules (fallback)."""

        # Check if task has enough steps to be reusable
        if len(steps_taken) < 3:
            return None

        # Determine category from keywords
        description_lower = task_description.lower()
        if any(word in description_lower for word in ["bug", "error", "fix", "debug"]):
            category = "debugging"
        elif any(word in description_lower for word in ["deploy", "release", "production"]):
            category = "deployment"
        elif any(word in description_lower for word in ["refactor", "clean", "optimize"]):
            category = "refactoring"
        elif any(word in description_lower for word in ["test", "verify", "validate"]):
            category = "testing"
        else:
            category = "coding"

        # Extract generalized name from task
        words = task_description.split()[:5]
        name = "Workflow: " + " ".join(words)

        workflow = GeneratedWorkflow(
            name=name,
            description=f"Workflow for: {task_description}",
            steps=steps_taken,
            prerequisites=["Clear understanding of task", "Required tools available"],
            expected_outcomes=["Successful completion", outcome],
            estimated_duration_mins=duration_mins,
            complexity_level=min(10, max(1, len(steps_taken) // 2)),
            category=category,
            success_criteria=["Task completed", outcome],
            common_pitfalls=["Skipping validation", "Insufficient testing"],
            automation_opportunities=["Automate validation steps"],
            confidence=0.5,  # Lower confidence for heuristic
        )

        logger.info(f"Generated heuristic workflow: {workflow.name}")
        return workflow

    def generate_workflow_documentation(self, workflow: GeneratedWorkflow) -> str:
        """Generate markdown documentation for a workflow.

        Returns:
            Markdown-formatted documentation
        """
        doc = f"""# {workflow.name}

## Overview
{workflow.description}

**Category:** {workflow.category.title()}
**Complexity:** {workflow.complexity_level}/10
**Estimated Duration:** {workflow.estimated_duration_mins} minutes

## Prerequisites
{chr(10).join(f"- {p}" for p in workflow.prerequisites)}

## Steps
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(workflow.steps))}

## Expected Outcomes
{chr(10).join(f"- {outcome}" for outcome in workflow.expected_outcomes)}

## Success Criteria
{chr(10).join(f"- {criterion}" for criterion in workflow.success_criteria)}

## Common Pitfalls to Avoid
{chr(10).join(f"- {pitfall}" for pitfall in workflow.common_pitfalls)}

## Automation Opportunities
{chr(10).join(f"- {opp}" for opp in workflow.automation_opportunities)}

---
**Confidence Level:** {workflow.confidence:.0%}
**Auto-generated:** Yes
"""
        return doc

    def extract_similar_workflows(
        self, task_history: list[dict], num_workflows: int = 5
    ) -> list[GeneratedWorkflow]:
        """Extract multiple reusable workflows from task history.

        Args:
            task_history: List of completed tasks with description, steps, outcome
            num_workflows: Maximum number of workflows to generate

        Returns:
            List of generated workflows
        """
        workflows = []

        for task in task_history[:10]:  # Analyze up to 10 recent tasks
            if len(workflows) >= num_workflows:
                break

            workflow = self.generate_workflow_from_task(
                task_description=task.get("description", ""),
                steps_taken=task.get("steps", []),
                outcome=task.get("outcome", ""),
                duration_mins=task.get("duration_mins", 60),
            )

            if workflow:
                workflows.append(workflow)

        logger.info(f"Extracted {len(workflows)} reusable workflows from {len(task_history)} tasks")
        return workflows
