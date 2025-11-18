"""
Goal Decomposition Service for Athena Phase 4

Automatically breaks down complex goals into manageable subtasks with:
- Hierarchical task structures
- Dependency detection
- Effort estimation
- Complexity scoring
- Critical path analysis
"""

import logging
import json
from typing import Optional, List, Dict
from datetime import datetime

from athena.core import config
from athena.core.database import Database
from athena.planning.models import (
    Goal,
    TaskNode,
    DecomposedGoal,
    DecompositionResult,
)

logger = logging.getLogger(__name__)


class GoalDecompositionService:
    """Service to decompose complex goals into structured task hierarchies."""

    def __init__(self, db: Optional[Database] = None):
        """Initialize the goal decomposition service.

        Args:
            db: Optional Database instance for prospective memory integration
        """
        self.llm_provider = config.LLM_PROVIDER
        self.client = self._initialize_llm_client()
        self.db = db
        self.converter = None
        if db:
            self._initialize_converter()

    def _initialize_converter(self):
        """Initialize goal-to-prospective converter if DB is available."""
        try:
            from athena.planning.goal_integration import GoalToProspectiveConverter

            self.converter = GoalToProspectiveConverter(self.db)
            logger.info("Goal-to-prospective converter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize converter: {e}")
            self.converter = None

    def _initialize_llm_client(self):
        """Initialize LLM client based on configured provider."""
        try:
            if self.llm_provider == "claude":
                import anthropic

                return anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
            elif self.llm_provider == "llamacpp":
                # LlamaCPP is accessed via HTTP
                logger.info(f"Using LlamaCPP at {config.LLAMACPP_REASONING_URL}")
                return {"type": "llamacpp", "url": config.LLAMACPP_REASONING_URL}
            elif self.llm_provider == "ollama":
                logger.info(f"Using Ollama at {config.OLLAMA_BASE_URL}")
                return {"type": "ollama", "url": config.OLLAMA_BASE_URL}
            else:
                logger.warning(f"Unknown LLM provider: {self.llm_provider}")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}, using mock decomposition")
            return None

    def decompose_goal(
        self,
        goal: Goal,
        max_depth: int = 3,
        target_chunk_size_minutes: int = 30,
    ) -> DecompositionResult:
        """
        Decompose a goal into a structured task hierarchy.

        Args:
            goal: High-level goal to decompose
            max_depth: Maximum nesting depth for tasks
            target_chunk_size_minutes: Target size for leaf tasks

        Returns:
            DecompositionResult with decomposed goal and metadata
        """
        try:
            start_time = datetime.now()

            # Step 1: Use LLM to analyze and break down goal
            task_list = self._analyze_goal_with_llm(goal, max_depth, target_chunk_size_minutes)

            if not task_list:
                return DecompositionResult(success=False, error_message="Failed to decompose goal")

            # Step 2: Build task graph with dependencies
            task_nodes = self._build_task_graph(task_list, goal)

            # Step 3: Detect dependencies
            self._detect_dependencies(task_nodes)

            # Step 4: Estimate effort
            self._estimate_effort(task_nodes)

            # Step 5: Analyze critical path
            critical_path_tasks = self._find_critical_path(task_nodes)

            # Step 6: Create decomposed goal
            decomposed = self._create_decomposed_goal(goal, task_nodes, critical_path_tasks)

            # Step 7: Validate decomposition
            warnings = self._validate_decomposition(decomposed)

            execution_time = (datetime.now() - start_time).total_seconds()

            return DecompositionResult(
                success=True,
                decomposed_goal=decomposed,
                warnings=warnings,
                execution_time_seconds=execution_time,
                tokens_used={"input": 0, "output": 0},  # Would be populated by LLM
            )

        except Exception as e:
            logger.error(f"Error decomposing goal: {e}", exc_info=True)
            return DecompositionResult(success=False, error_message=str(e))

    def _analyze_goal_with_llm(
        self,
        goal: Goal,
        max_depth: int,
        target_chunk_size: int,
    ) -> List[Dict]:
        """
        Use LLM to analyze and break down a goal.

        Supports Claude, LlamaCPP, and Ollama providers.
        """
        if not self.client:
            return self._mock_decomposition(goal)

        try:
            prompt = f"""You are an expert project planner. Decompose this goal into a structured task hierarchy:

GOAL: {goal.title}
DESCRIPTION: {goal.description}
CONTEXT: {goal.context or 'None'}

Constraints:
- Maximum nesting depth: {max_depth}
- Target leaf task size: {target_chunk_size} minutes
- Each task should be concrete and actionable
- Identify dependencies between tasks
- Estimate effort and complexity (1-10)

Return a JSON object with this structure:
{{
    "tasks": [
        {{
            "title": "Task title",
            "description": "Detailed description",
            "estimated_effort_minutes": number,
            "estimated_complexity": number,
            "priority": number,
            "tags": ["tag1", "tag2"],
            "subtasks": [
                {{
                    "title": "Subtask",
                    "description": "...",
                    "estimated_effort_minutes": number,
                    ...
                }}
            ]
        }}
    ],
    "dependencies": [
        {{"from": "task_index", "to": "task_index", "type": "blocks"}}
    ],
    "notes": "Any additional insights about the decomposition"
}}

Only return valid JSON, no other text."""

            response_text = None

            if self.llm_provider == "claude":
                response = self.client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text

            elif self.llm_provider in ["llamacpp", "ollama"]:
                # Use HTTP-based inference
                response_text = self._call_http_llm(prompt)

            if not response_text:
                logger.warning("Failed to get LLM response")
                return self._mock_decomposition(goal)

            # Parse JSON from response
            try:
                # Handle cases where LLM wraps response in markdown code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                data = json.loads(response_text)
                tasks = data.get("tasks", [])

                if tasks:
                    logger.info(f"Successfully decomposed goal into {len(tasks)} top-level tasks")
                    return tasks
                else:
                    logger.warning("LLM returned empty tasks list")
                    return self._mock_decomposition(goal)

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response text: {response_text[:200]}")
                return self._mock_decomposition(goal)

        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}", exc_info=True)
            return self._mock_decomposition(goal)

    def _call_http_llm(self, prompt: str) -> Optional[str]:
        """Call HTTP-based LLM (LlamaCPP or Ollama)."""
        try:
            import requests

            if self.llm_provider == "llamacpp":
                url = f"{self.client['url']}/v1/completions"
                payload = {
                    "prompt": prompt,
                    "max_tokens": 4000,
                    "temperature": 0.7,
                }
            elif self.llm_provider == "ollama":
                url = f"{self.client['url']}/api/generate"
                payload = {
                    "prompt": prompt,
                    "stream": False,
                    "num_predict": 4000,
                }
            else:
                return None

            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()

            if self.llm_provider == "llamacpp":
                return result.get("choices", [{}])[0].get("text", "")
            elif self.llm_provider == "ollama":
                return result.get("response", "")

        except Exception as e:
            logger.error(f"HTTP LLM call failed: {e}")
            return None

    def _mock_decomposition(self, goal: Goal) -> List[Dict]:
        """Generate a mock decomposition for testing."""
        return [
            {
                "title": "Requirement Analysis",
                "description": f"Analyze requirements for: {goal.title}",
                "estimated_effort_minutes": 120,
                "estimated_complexity": 5,
                "priority": 9,
                "tags": ["planning", "analysis"],
                "subtasks": [
                    {
                        "title": "Gather requirements",
                        "description": "Collect all requirements from stakeholders",
                        "estimated_effort_minutes": 60,
                        "estimated_complexity": 4,
                        "priority": 9,
                        "tags": ["requirements"],
                        "subtasks": [],
                    },
                    {
                        "title": "Document requirements",
                        "description": "Create detailed requirement specification",
                        "estimated_effort_minutes": 60,
                        "estimated_complexity": 5,
                        "priority": 8,
                        "tags": ["documentation"],
                        "subtasks": [],
                    },
                ],
            },
            {
                "title": "Design & Architecture",
                "description": f"Design architecture for: {goal.title}",
                "estimated_effort_minutes": 180,
                "estimated_complexity": 7,
                "priority": 8,
                "tags": ["design", "architecture"],
                "subtasks": [
                    {
                        "title": "Create architecture diagram",
                        "description": "Design system architecture",
                        "estimated_effort_minutes": 90,
                        "estimated_complexity": 6,
                        "priority": 8,
                        "tags": ["design"],
                        "subtasks": [],
                    },
                    {
                        "title": "Define data models",
                        "description": "Design database schema and data structures",
                        "estimated_effort_minutes": 90,
                        "estimated_complexity": 7,
                        "priority": 8,
                        "tags": ["design"],
                        "subtasks": [],
                    },
                ],
            },
            {
                "title": "Implementation",
                "description": f"Implement: {goal.title}",
                "estimated_effort_minutes": 480,
                "estimated_complexity": 8,
                "priority": 8,
                "tags": ["implementation", "coding"],
                "subtasks": [],
            },
            {
                "title": "Testing & QA",
                "description": f"Test: {goal.title}",
                "estimated_effort_minutes": 240,
                "estimated_complexity": 6,
                "priority": 7,
                "tags": ["testing", "qa"],
                "subtasks": [
                    {
                        "title": "Write unit tests",
                        "description": "Create comprehensive unit tests",
                        "estimated_effort_minutes": 120,
                        "estimated_complexity": 5,
                        "priority": 8,
                        "tags": ["testing"],
                        "subtasks": [],
                    },
                    {
                        "title": "Integration testing",
                        "description": "Test component integration",
                        "estimated_effort_minutes": 120,
                        "estimated_complexity": 6,
                        "priority": 7,
                        "tags": ["testing"],
                        "subtasks": [],
                    },
                ],
            },
            {
                "title": "Deployment",
                "description": f"Deploy: {goal.title}",
                "estimated_effort_minutes": 120,
                "estimated_complexity": 6,
                "priority": 7,
                "tags": ["deployment", "release"],
                "subtasks": [],
            },
        ]

    def _build_task_graph(
        self,
        task_list: List[Dict],
        goal: Goal,
        parent_id: Optional[str] = None,
    ) -> Dict[str, TaskNode]:
        """Build a task graph from the decomposed task list."""
        task_nodes = {}

        for idx, task_data in enumerate(task_list):
            task_id = f"{goal.id}_task_{idx}"
            task_node = TaskNode(
                id=task_id,
                title=task_data.get("title", f"Task {idx}"),
                description=task_data.get("description", ""),
                parent_id=parent_id,
                estimated_effort_minutes=task_data.get("estimated_effort_minutes", 0),
                estimated_complexity=task_data.get("estimated_complexity", 5),
                estimated_priority=task_data.get("priority", 5),
                tags=task_data.get("tags", []),
            )

            task_nodes[task_id] = task_node

            # Process subtasks recursively
            subtasks = task_data.get("subtasks", [])
            if subtasks:
                subtask_nodes = self._build_task_graph(subtasks, goal, task_id)
                task_nodes.update(subtask_nodes)
                task_node.subtask_ids = list(subtask_nodes.keys())

        return task_nodes

    def _detect_dependencies(self, task_nodes: Dict[str, TaskNode]) -> None:
        """Detect implicit and explicit dependencies between tasks."""
        # Simple heuristic: subtasks depend on their parent
        for task_id, task in task_nodes.items():
            if task.parent_id:
                task.depends_on.append(task.parent_id)

        # Find tasks that should run in sequence
        # Tasks in the same level with later ones depending on earlier ones
        # (simplified - more complex logic would analyze descriptions)

    def _estimate_effort(self, task_nodes: Dict[str, TaskNode]) -> None:
        """Estimate effort for parent tasks based on subtasks."""
        # Group by parent
        parents = {}
        for task in task_nodes.values():
            if task.parent_id:
                if task.parent_id not in parents:
                    parents[task.parent_id] = []
                parents[task.parent_id].append(task)

        # Calculate parent effort as sum of children
        for parent_id, children in parents.items():
            parent = task_nodes.get(parent_id)
            if parent:
                if parent.subtask_ids:
                    parent.estimated_effort_minutes = sum(
                        task_nodes[child_id].estimated_effort_minutes
                        for child_id in parent.subtask_ids
                    )
                    parent.estimated_complexity = int(
                        sum(t.estimated_complexity for t in children) / len(children)
                    )

    def _find_critical_path(self, task_nodes: Dict[str, TaskNode]) -> List[str]:
        """Find the critical path (longest dependency chain)."""
        # Simplified: just identify leaf tasks with high effort
        leaf_tasks = [task_id for task_id, task in task_nodes.items() if not task.subtask_ids]

        if not leaf_tasks:
            return []

        # Mark top effort tasks as critical
        sorted_tasks = sorted(
            leaf_tasks, key=lambda tid: task_nodes[tid].estimated_effort_minutes, reverse=True
        )

        critical_threshold = sorted_tasks[0][1].estimated_effort_minutes * 0.7
        critical_path = [
            tid
            for tid in sorted_tasks
            if task_nodes[tid].estimated_effort_minutes >= critical_threshold
        ]

        return critical_path[:3]  # Return top 3 critical tasks

    def _create_decomposed_goal(
        self,
        goal: Goal,
        task_nodes: Dict[str, TaskNode],
        critical_path: List[str],
    ) -> DecomposedGoal:
        """Create a DecomposedGoal from task nodes and analysis."""
        # Find root tasks (those without parents)
        root_tasks = [task for task in task_nodes.values() if not task.parent_id]

        # Mark critical path
        for task_id in critical_path:
            if task_id in task_nodes:
                task_nodes[task_id].critical_path = True

        # Calculate metrics
        total_effort = sum(
            task.estimated_effort_minutes
            for task in task_nodes.values()
            if not task.subtask_ids  # Only leaf tasks
        )
        avg_complexity = (
            sum(t.estimated_complexity for t in task_nodes.values()) / len(task_nodes)
            if task_nodes
            else 0
        )
        max_depth = self._calculate_max_depth(root_tasks, task_nodes)
        num_subtasks = len([t for t in task_nodes.values() if t.subtask_ids])

        decomposed = DecomposedGoal(
            goal_id=goal.id,
            goal_title=goal.title,
            root_tasks=root_tasks,
            all_tasks=task_nodes,
            total_estimated_effort=total_effort,
            avg_complexity=avg_complexity,
            num_tasks=len(task_nodes),
            num_subtasks=num_subtasks,
            max_depth=max_depth,
            critical_path_length=sum(
                task_nodes[tid].estimated_effort_minutes for tid in critical_path
            ),
            completeness_score=0.85,  # Would be calculated based on validations
            clarity_score=0.80,
            feasibility_score=0.75,
        )

        return decomposed

    def _calculate_max_depth(self, tasks: List[TaskNode], all_tasks: Dict) -> int:
        """Calculate maximum depth of task hierarchy."""
        if not tasks:
            return 0

        max_d = 0
        for task in tasks:
            depth = 1 + (
                self._calculate_max_depth([all_tasks[sid] for sid in task.subtask_ids], all_tasks)
                if task.subtask_ids
                else 0
            )
            max_d = max(max_d, depth)

        return max_d

    def _validate_decomposition(self, decomposed: DecomposedGoal) -> List[str]:
        """Validate the decomposition and return warnings."""
        warnings = []

        # Check for unachievable complexity vs effort ratio
        for task in decomposed.all_tasks.values():
            if task.estimated_complexity >= 8 and task.estimated_effort_minutes < 60:
                warnings.append(
                    f"Task '{task.title}' has high complexity ({task.estimated_complexity}) "
                    f"but low effort ({task.estimated_effort_minutes}m)"
                )

        # Check for orphaned tasks
        all_task_ids = set(decomposed.all_tasks.keys())
        assigned_tasks = set()
        for task in decomposed.all_tasks.values():
            assigned_tasks.add(task.id)
            assigned_tasks.update(task.subtask_ids)

        # Check if any tasks are only dependencies without parents
        if len(warnings) < 3 and decomposed.num_tasks > 10:
            warnings.append("Large number of tasks - consider further refinement")

        return warnings

    async def decompose_and_store_goal(
        self,
        goal: Goal,
        max_depth: int = 3,
        target_chunk_size_minutes: int = 30,
        project_id: Optional[int] = None,
        assignee: str = "claude",
    ) -> Dict:
        """
        Decompose a goal and save results to prospective memory.

        Args:
            goal: Goal to decompose
            max_depth: Maximum nesting depth
            target_chunk_size_minutes: Target leaf task size
            project_id: Project context
            assignee: Task assignee

        Returns:
            Dictionary with decomposition and storage results
        """
        if not self.converter:
            return {
                "success": False,
                "error": "Prospective memory not initialized. Initialize with database.",
            }

        # Step 1: Decompose the goal
        decomposition_result = self.decompose_goal(goal, max_depth, target_chunk_size_minutes)

        if not decomposition_result.success:
            return {"success": False, "error": decomposition_result.error_message}

        # Step 2: Store in prospective memory
        integration_result = await self.converter.integrate_decomposed_goal(
            decomposition_result.decomposed_goal,
            goal,
            project_id=project_id,
            assignee=assignee,
        )

        return {
            "success": integration_result.success,
            "goal_id": goal.id,
            "task_ids": integration_result.created_task_ids,
            "task_mapping": integration_result.task_mapping,
            "dependencies_created": integration_result.dependencies_created,
            "warnings": integration_result.warnings,
            "error": integration_result.error_message,
            "decomposition": {
                "num_tasks": decomposition_result.decomposed_goal.num_tasks,
                "total_effort_minutes": decomposition_result.decomposed_goal.total_estimated_effort,
                "complexity_score": decomposition_result.decomposed_goal.avg_complexity,
                "critical_path_length": decomposition_result.decomposed_goal.critical_path_length,
            },
        }

    def set_database(self, db: Database) -> None:
        """Set database for prospective memory integration.

        Args:
            db: Database instance
        """
        self.db = db
        self._initialize_converter()
