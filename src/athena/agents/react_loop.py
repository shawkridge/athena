"""ReAct (Reasoning + Acting) Loop Agent

Implements an autonomous agent that iteratively performs:
1. Thought (reason about current state and plan next step)
2. Action (execute a tool or query)
3. Observation (integrate results back into reasoning)

This creates a loop that improves reasoning through grounding in actual results.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

from .thought_action import (
    Action,
    ActionType,
    Observation,
    ObservationType,
    Thought,
    ThoughtActionHistory,
    ThoughtType,
)
from .observation_memory import ObservationMemory


class LoopStatus(str, Enum):
    """Status of the ReAct loop"""
    INITIALIZED = "initialized"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class LoopStepType(str, Enum):
    """Type of step in the loop"""
    INITIAL_ANALYSIS = "initial_analysis"
    REFINEMENT = "refinement"
    EXPLORATION = "exploration"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"


@dataclass
class LoopConfig:
    """Configuration for ReAct loop"""
    max_iterations: int = 10
    timeout_seconds: float = 300.0
    confidence_threshold: float = 0.7
    min_observation_relevance: float = 0.3
    enable_fallback: bool = True
    track_reasoning_depth: bool = True
    max_reasoning_depth: int = 10


@dataclass
class LoopMetrics:
    """Metrics tracking for ReAct loop execution"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_iterations: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_execution_time_ms: float = 0.0
    average_iteration_time_ms: float = 0.0
    final_confidence: float = 0.0
    insights_discovered: List[str] = field(default_factory=list)
    contradictions_resolved: List[str] = field(default_factory=list)

    def finalize(self) -> None:
        """Finalize metrics after loop completion"""
        self.end_time = datetime.now()
        if self.total_iterations > 0:
            self.average_iteration_time_ms = (
                self.total_execution_time_ms / self.total_iterations
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_iterations": self.total_iterations,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "total_execution_time_ms": self.total_execution_time_ms,
            "average_iteration_time_ms": self.average_iteration_time_ms,
            "success_rate": (
                self.successful_actions / (self.successful_actions + self.failed_actions)
                if (self.successful_actions + self.failed_actions) > 0
                else 0.0
            ),
            "final_confidence": self.final_confidence,
            "insights_discovered": self.insights_discovered,
            "contradictions_resolved": self.contradictions_resolved,
        }


@dataclass
class LoopResult:
    """Result of a ReAct loop execution"""
    status: LoopStatus
    final_thought: Optional[Thought]
    conclusion: str = ""
    confidence: float = 0.0
    iterations_completed: int = 0
    reasoning_chain: List[Dict[str, Any]] = field(default_factory=list)
    metrics: LoopMetrics = field(default_factory=LoopMetrics)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "status": self.status.value,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "iterations": self.iterations_completed,
            "reasoning_chain": self.reasoning_chain,
            "metrics": self.metrics.to_dict(),
            "errors": self.errors,
        }


class ReActLoop:
    """
    ReAct (Reasoning + Acting) loop implementation.

    Iteratively:
    1. Thinks (reason about current state)
    2. Acts (execute actions/tools)
    3. Observes (integrate observations)
    4. Updates reasoning based on observations
    """

    def __init__(
        self,
        problem_description: str,
        config: Optional[LoopConfig] = None,
        action_executor: Optional[Callable] = None,
    ):
        """Initialize ReAct loop

        Args:
            problem_description: The problem/task to solve
            config: Configuration for the loop
            action_executor: Callable to execute actions
        """
        self.problem_description = problem_description
        self.config = config or LoopConfig()
        self.action_executor = action_executor or self._default_action_executor

        # History and memory
        self.history = ThoughtActionHistory()
        self.observation_memory = ObservationMemory()

        # Tracking
        self.status = LoopStatus.INITIALIZED
        self.current_iteration = 0
        self.metrics = LoopMetrics()
        self.start_time = time.time()

        # Context
        self.current_problem_understanding = ""
        self.discovered_insights: List[str] = []
        self.key_observations: List[Observation] = []

    async def run(self) -> LoopResult:
        """Run the complete ReAct loop

        Returns:
            LoopResult with completion status and findings
        """
        self.status = LoopStatus.THINKING

        try:
            # Initial problem analysis
            await self._initial_analysis()

            # Main loop
            while self.current_iteration < self.config.max_iterations:
                elapsed_ms = (time.time() - self.start_time) * 1000

                # Check timeout
                if elapsed_ms > self.config.timeout_seconds * 1000:
                    self.status = LoopStatus.TIMEOUT
                    break

                # Run one iteration
                iteration_complete = await self._run_iteration()
                if iteration_complete:
                    break

            # Finalize
            return await self._finalize_loop()

        except Exception as e:
            self.status = LoopStatus.FAILED
            return LoopResult(
                status=self.status,
                final_thought=self.history.get_latest_thought(),
                conclusion=f"Loop failed: {str(e)}",
                iterations_completed=self.current_iteration,
                errors=[str(e)],
                metrics=self.metrics,
            )

    async def _initial_analysis(self) -> None:
        """Perform initial analysis of the problem"""
        # Create initial thought
        thought = self.history.add_thought(
            content=f"Analyzing problem: {self.problem_description}",
            thought_type=ThoughtType.PROBLEM_ANALYSIS,
            reasoning="Initial problem decomposition and understanding",
            confidence=0.5,
            reasoning_depth=1,
        )

        self.current_problem_understanding = self.problem_description
        self.status = LoopStatus.THINKING

    async def _run_iteration(self) -> bool:
        """Run one iteration of think-act-observe

        Returns:
            True if loop should terminate, False to continue
        """
        self.current_iteration += 1
        iteration_start = time.time()

        try:
            # Step 1: Think
            await self._think_step()

            # Step 2: Act
            await self._act_step()

            # Step 3: Observe
            await self._observe_step()

            # Check termination condition
            should_terminate = await self._check_termination()

            # Record iteration metrics
            iteration_time_ms = (time.time() - iteration_start) * 1000
            self.metrics.total_iterations += 1
            self.metrics.total_execution_time_ms += iteration_time_ms

            return should_terminate

        except Exception as e:
            self.metrics.failed_actions += 1
            raise

    async def _think_step(self) -> None:
        """Thought step: reason about current state"""
        self.status = LoopStatus.THINKING

        # Get context from recent observations
        recent_obs = self.history.observations[-3:] if self.history.observations else []

        # Determine reasoning depth
        thinking_depth = min(
            self.current_iteration + 1,
            self.config.max_reasoning_depth
            if self.config.track_reasoning_depth
            else 10,
        )

        # Create thought
        thought_content = self._generate_thought_content(recent_obs)
        thought = self.history.add_thought(
            content=thought_content,
            thought_type=self._select_thought_type(),
            reasoning=self._generate_reasoning_explanation(recent_obs),
            confidence=self._estimate_thought_confidence(recent_obs),
            reasoning_depth=thinking_depth,
            parent_thought_id=(
                self.history.get_latest_thought().id
                if self.history.thoughts
                else None
            ),
        )

        # Suggest next action
        thought.next_action_suggested = self._suggest_next_action(thought)

    async def _act_step(self) -> None:
        """Action step: execute an action based on current thought"""
        self.status = LoopStatus.ACTING

        latest_thought = self.history.get_latest_thought()
        if not latest_thought:
            return

        # Create action based on suggested action
        action = self.history.add_action(
            content=latest_thought.next_action_suggested or "Continue reasoning",
            action_type=self._classify_action_type(
                latest_thought.next_action_suggested or ""
            ),
            thought_id=latest_thought.id,
            expected_outcome=self._predict_outcome(latest_thought),
        )

        # Execute action
        action_start = time.time()
        try:
            result = await self.action_executor(action)
            action_time_ms = (time.time() - action_start) * 1000

            self.history.update_action_execution(
                action.id,
                execution_time_ms=action_time_ms,
                success=result.get("success", True),
                error=result.get("error"),
            )

            if result.get("success"):
                self.metrics.successful_actions += 1
            else:
                self.metrics.failed_actions += 1

        except Exception as e:
            action_time_ms = (time.time() - action_start) * 1000
            self.history.update_action_execution(
                action.id,
                execution_time_ms=action_time_ms,
                success=False,
                error=str(e),
            )
            self.metrics.failed_actions += 1

    async def _observe_step(self) -> None:
        """Observation step: process action results"""
        self.status = LoopStatus.OBSERVING

        latest_action = self.history.get_latest_action()
        if not latest_action:
            return

        # Create observation from action result
        obs_type = (
            ObservationType.SUCCESS
            if latest_action.success
            else ObservationType.FAILURE
        )

        obs_content = self._generate_observation_content(latest_action)
        observation = self.history.add_observation(
            content=obs_content,
            action_id=latest_action.id,
            observation_type=obs_type,
            relevance_score=self._evaluate_observation_relevance(latest_action),
            surprises=self._detect_surprises(obs_content),
            contradictions=self._detect_contradictions(obs_content),
        )

        # Store in observation memory for future reference
        self.observation_memory.add_observation(
            content=obs_content,
            action_type=latest_action.action_type.value,
            result_type=obs_type.value,
            success=latest_action.success,
            relevance_score=observation.relevance_score,
            action_context=latest_action.parameters,
            surprise_flags=observation.surprises,
            lesson_learned=self._extract_lesson(observation),
        )

        self.key_observations.append(observation)

        # Link observation to thought
        latest_thought = self.history.get_latest_thought()
        if latest_thought:
            latest_thought.supporting_observations.append(observation.id)

    async def _check_termination(self) -> bool:
        """Check if loop should terminate

        Returns:
            True if loop should terminate, False to continue
        """
        # Check if we have high confidence conclusion
        latest_thought = self.history.get_latest_thought()
        if latest_thought and latest_thought.confidence >= self.config.confidence_threshold:
            # Check if thought suggests conclusion
            if any(
                keyword in latest_thought.content.lower()
                for keyword in ["conclusion", "solution", "answer", "complete"]
            ):
                return True

        return False

    async def _finalize_loop(self) -> LoopResult:
        """Finalize loop and generate result"""
        self.status = LoopStatus.COMPLETED
        self.metrics.finalize()

        # Get final thought
        final_thought = self.history.get_latest_thought()

        # Extract conclusion
        conclusion = self._extract_conclusion()

        # Collect reasoning chain
        reasoning_chain = [
            self.history.get_loop_iteration(i)
            for i in range(len(self.history.thoughts))
        ]

        # Determine final confidence
        if final_thought:
            self.metrics.final_confidence = final_thought.confidence

        return LoopResult(
            status=self.status,
            final_thought=final_thought,
            conclusion=conclusion,
            confidence=self.metrics.final_confidence,
            iterations_completed=self.current_iteration,
            reasoning_chain=reasoning_chain,
            metrics=self.metrics,
            errors=[],
        )

    # Helper methods for thinking
    def _select_thought_type(self) -> ThoughtType:
        """Select appropriate thought type based on iteration"""
        if self.current_iteration == 1:
            return ThoughtType.PROBLEM_ANALYSIS
        elif self.current_iteration <= 3:
            return ThoughtType.DECOMPOSITION
        elif self.current_iteration <= 6:
            return ThoughtType.EVALUATION
        else:
            return ThoughtType.SYNTHESIS

    def _generate_thought_content(self, recent_obs: List[Observation]) -> str:
        """Generate thought content based on recent observations"""
        if not recent_obs:
            return f"How can I solve: {self.problem_description}"

        last_obs = recent_obs[-1]
        return f"Based on observation: {last_obs.content[:100]}..., next I should..."

    def _generate_reasoning_explanation(self, recent_obs: List[Observation]) -> str:
        """Generate explanation of reasoning"""
        if not recent_obs:
            return "Initial problem understanding and decomposition"

        return f"Based on {len(recent_obs)} recent observations, refining approach"

    def _estimate_thought_confidence(self, recent_obs: List[Observation]) -> float:
        """Estimate confidence in current thought"""
        if not recent_obs:
            return 0.5

        # Base confidence on successful observations
        relevant_obs = [o for o in recent_obs if o.relevance_score > 0.5]
        if not relevant_obs:
            return 0.5

        return min(0.5 + len(relevant_obs) * 0.1, 0.95)

    def _suggest_next_action(self, thought: Thought) -> str:
        """Suggest next action based on thought"""
        if ThoughtType.PROBLEM_ANALYSIS in thought.thought_type:
            return "Decompose problem into sub-tasks"
        elif ThoughtType.HYPOTHESIS in thought.thought_type:
            return "Test hypothesis with targeted queries"
        else:
            return "Execute planned action to gather more information"

    def _classify_action_type(self, action_description: str) -> ActionType:
        """Classify action type from description"""
        action_lower = action_description.lower()

        if "query" in action_lower or "ask" in action_lower:
            return ActionType.QUERY
        elif "retrieve" in action_lower or "fetch" in action_lower:
            return ActionType.RETRIEVE
        elif "compute" in action_lower or "calculate" in action_lower:
            return ActionType.COMPUTE
        elif "validate" in action_lower or "verify" in action_lower:
            return ActionType.VALIDATE
        else:
            return ActionType.QUERY

    def _predict_outcome(self, thought: Thought) -> str:
        """Predict expected outcome of action"""
        return f"Understand more about: {thought.content[:50]}..."

    def _generate_observation_content(self, action: Action) -> str:
        """Generate observation content from action"""
        if action.success:
            return f"Successfully executed {action.action_type.value}"
        else:
            return f"Failed to execute {action.action_type.value}: {action.error}"

    def _evaluate_observation_relevance(self, action: Action) -> float:
        """Evaluate relevance of observation"""
        if action.success:
            return 0.8
        else:
            return 0.3

    def _detect_surprises(self, content: str) -> List[str]:
        """Detect surprising aspects in observation"""
        surprises = []
        surprise_keywords = ["unexpected", "surprising", "contradiction", "error"]

        for keyword in surprise_keywords:
            if keyword in content.lower():
                surprises.append(keyword)

        return surprises

    def _detect_contradictions(self, content: str) -> List[str]:
        """Detect contradictions in observation"""
        contradictions = []

        # Check against previous observations
        for prev_obs in self.key_observations[:-1]:
            if "contradict" in content.lower() or (
                prev_obs.content and content.lower() != prev_obs.content.lower()
            ):
                contradictions.append(f"Contradicts: {prev_obs.id}")

        return contradictions

    def _extract_lesson(self, observation: Observation) -> str:
        """Extract lesson learned from observation"""
        if observation.surprises:
            return f"Discovered: {', '.join(observation.surprises)}"
        elif observation.observation_type == ObservationType.SUCCESS:
            return "Successfully validated approach"
        else:
            return "Need to adjust approach"

    def _extract_conclusion(self) -> str:
        """Extract conclusion from loop"""
        final_thought = self.history.get_latest_thought()
        if not final_thought:
            return "No conclusion reached"

        return final_thought.content[:200]

    async def _default_action_executor(self, action: Action) -> Dict[str, Any]:
        """Default action executor (can be overridden)

        Args:
            action: The action to execute

        Returns:
            Dictionary with 'success' and optional 'error' keys
        """
        # Simulate action execution
        await asyncio.sleep(0.1)
        return {"success": True, "result": f"Executed {action.content}"}

    def get_history(self) -> Dict[str, Any]:
        """Get complete reasoning history

        Returns:
            Dictionary with full history
        """
        return self.history.get_full_history()

    def get_observations_summary(self) -> Dict[str, Any]:
        """Get summary of observations

        Returns:
            Dictionary with observation statistics
        """
        return self.observation_memory.get_statistics()

    def get_insights(self) -> List[str]:
        """Get discovered insights

        Returns:
            List of insights discovered during reasoning
        """
        lessons = self.observation_memory.get_lessons_learned()
        return [lesson for _, lesson in lessons]
