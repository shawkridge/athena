"""Thought-Action Tracking for ReAct Loop

Implements tracking and history management for thoughts, actions, and observations
in a ReAct (Reasoning + Acting) loop. Provides structured representation of the
reasoning process with full context and confidence tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ThoughtType(str, Enum):
    """Types of thoughts in reasoning process"""
    PROBLEM_ANALYSIS = "problem_analysis"
    DECOMPOSITION = "decomposition"
    HYPOTHESIS = "hypothesis"
    STRATEGY = "strategy"
    EVALUATION = "evaluation"
    REFINEMENT = "refinement"
    SYNTHESIS = "synthesis"
    UNCERTAINTY = "uncertainty"


class ActionType(str, Enum):
    """Types of actions in ReAct loop"""
    QUERY = "query"
    RETRIEVE = "retrieve"
    COMPUTE = "compute"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    SYNTHESIZE = "synthesize"
    FALLBACK = "fallback"


class ObservationType(str, Enum):
    """Types of observations from actions"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNEXPECTED = "unexpected"
    TIMEOUT = "timeout"


@dataclass
class Thought:
    """Represents a reasoning thought in the loop"""
    id: str = field(default_factory=lambda: str(uuid4()))
    thought_type: ThoughtType = ThoughtType.PROBLEM_ANALYSIS
    content: str = ""
    reasoning: str = ""
    confidence: float = 0.5
    reasoning_depth: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    parent_thought_id: Optional[str] = None
    supporting_observations: List[str] = field(default_factory=list)
    next_action_suggested: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert thought to dictionary representation"""
        return {
            "id": self.id,
            "type": self.thought_type.value,
            "content": self.content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "depth": self.reasoning_depth,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_thought_id,
            "observations": self.supporting_observations,
            "next_action": self.next_action_suggested,
        }


@dataclass
class Action:
    """Represents an action taken in the loop"""
    id: str = field(default_factory=lambda: str(uuid4()))
    action_type: ActionType = ActionType.QUERY
    content: str = ""
    tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    thought_id: str = ""
    expected_outcome: str = ""
    timeout_seconds: float = 30.0
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary representation"""
        return {
            "id": self.id,
            "type": self.action_type.value,
            "content": self.content,
            "tool": self.tool,
            "parameters": self.parameters,
            "thought_id": self.thought_id,
            "expected_outcome": self.expected_outcome,
            "timestamp": self.timestamp.isoformat(),
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class Observation:
    """Represents an observation from action execution"""
    id: str = field(default_factory=lambda: str(uuid4()))
    observation_type: ObservationType = ObservationType.SUCCESS
    content: str = ""
    action_id: str = ""
    relevance_score: float = 0.5
    surprises: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert observation to dictionary representation"""
        return {
            "id": self.id,
            "type": self.observation_type.value,
            "content": self.content,
            "action_id": self.action_id,
            "relevance": self.relevance_score,
            "surprises": self.surprises,
            "contradictions": self.contradictions,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ThoughtActionHistory:
    """Maintains and manages history of thoughts, actions, and observations"""

    def __init__(self, max_history_size: int = 1000):
        """Initialize thought-action history tracker

        Args:
            max_history_size: Maximum number of items to keep in history
        """
        self.thoughts: List[Thought] = []
        self.actions: List[Action] = []
        self.observations: List[Observation] = []
        self.max_size = max_history_size

    def add_thought(
        self,
        content: str,
        thought_type: ThoughtType = ThoughtType.PROBLEM_ANALYSIS,
        reasoning: str = "",
        confidence: float = 0.5,
        reasoning_depth: int = 1,
        parent_thought_id: Optional[str] = None,
    ) -> Thought:
        """Add a thought to the history

        Args:
            content: The thought content
            thought_type: Type of thought
            reasoning: Detailed reasoning behind the thought
            confidence: Confidence level (0.0-1.0)
            reasoning_depth: Depth of reasoning (1-10)
            parent_thought_id: ID of parent thought if hierarchical

        Returns:
            The created Thought object
        """
        thought = Thought(
            thought_type=thought_type,
            content=content,
            reasoning=reasoning,
            confidence=confidence,
            reasoning_depth=reasoning_depth,
            parent_thought_id=parent_thought_id,
        )
        self.thoughts.append(thought)

        # Maintain size limit
        if len(self.thoughts) > self.max_size:
            self.thoughts = self.thoughts[-self.max_size :]

        return thought

    def add_action(
        self,
        content: str,
        action_type: ActionType = ActionType.QUERY,
        tool: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        thought_id: str = "",
        expected_outcome: str = "",
        timeout_seconds: float = 30.0,
    ) -> Action:
        """Add an action to the history

        Args:
            content: The action description
            action_type: Type of action
            tool: Tool/function to execute
            parameters: Parameters for the tool
            thought_id: ID of the thought that triggered this action
            expected_outcome: Expected outcome of the action
            timeout_seconds: Timeout for action execution

        Returns:
            The created Action object
        """
        action = Action(
            action_type=action_type,
            content=content,
            tool=tool,
            parameters=parameters or {},
            thought_id=thought_id,
            expected_outcome=expected_outcome,
            timeout_seconds=timeout_seconds,
        )
        self.actions.append(action)

        # Maintain size limit
        if len(self.actions) > self.max_size:
            self.actions = self.actions[-self.max_size :]

        return action

    def add_observation(
        self,
        content: str,
        action_id: str,
        observation_type: ObservationType = ObservationType.SUCCESS,
        relevance_score: float = 0.5,
        surprises: Optional[List[str]] = None,
        contradictions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Observation:
        """Add an observation to the history

        Args:
            content: The observation content
            action_id: ID of the action that produced this observation
            observation_type: Type of observation
            relevance_score: How relevant this observation is (0.0-1.0)
            surprises: Any surprises or unexpected findings
            contradictions: Any contradictions discovered
            metadata: Additional metadata about the observation

        Returns:
            The created Observation object
        """
        observation = Observation(
            observation_type=observation_type,
            content=content,
            action_id=action_id,
            relevance_score=relevance_score,
            surprises=surprises or [],
            contradictions=contradictions or [],
            metadata=metadata or {},
        )
        self.observations.append(observation)

        # Maintain size limit
        if len(self.observations) > self.max_size:
            self.observations = self.observations[-self.max_size :]

        return observation

    def update_action_execution(
        self,
        action_id: str,
        execution_time_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> bool:
        """Update action with execution results

        Args:
            action_id: ID of the action to update
            execution_time_ms: Time taken to execute (in milliseconds)
            success: Whether action succeeded
            error: Error message if failed

        Returns:
            True if action was found and updated
        """
        for action in self.actions:
            if action.id == action_id:
                action.execution_time_ms = execution_time_ms
                action.success = success
                action.error = error
                return True
        return False

    def get_latest_thought(self) -> Optional[Thought]:
        """Get the most recent thought

        Returns:
            The most recent Thought or None if no thoughts recorded
        """
        return self.thoughts[-1] if self.thoughts else None

    def get_latest_action(self) -> Optional[Action]:
        """Get the most recent action

        Returns:
            The most recent Action or None if no actions recorded
        """
        return self.actions[-1] if self.actions else None

    def get_latest_observation(self) -> Optional[Observation]:
        """Get the most recent observation

        Returns:
            The most recent Observation or None if no observations recorded
        """
        return self.observations[-1] if self.observations else None

    def get_thought_chain(self, start_thought_id: Optional[str] = None) -> List[Thought]:
        """Get chain of related thoughts (hierarchical lineage)

        Args:
            start_thought_id: ID to start from (defaults to latest)

        Returns:
            List of thoughts forming a chain
        """
        if not self.thoughts:
            return []

        if start_thought_id is None:
            start_thought_id = self.thoughts[-1].id

        chain = []
        current_id = start_thought_id

        # Build chain backward
        thoughts_by_id = {t.id: t for t in self.thoughts}

        while current_id in thoughts_by_id:
            thought = thoughts_by_id[current_id]
            chain.insert(0, thought)
            if thought.parent_thought_id is None:
                break
            current_id = thought.parent_thought_id

        return chain

    def get_action_for_thought(self, thought_id: str) -> Optional[Action]:
        """Get the action that was triggered by a specific thought

        Args:
            thought_id: ID of the thought

        Returns:
            The Action triggered by this thought, or None
        """
        for action in self.actions:
            if action.thought_id == thought_id:
                return action
        return None

    def get_observation_for_action(self, action_id: str) -> Optional[Observation]:
        """Get the observation from a specific action

        Args:
            action_id: ID of the action

        Returns:
            The Observation from this action, or None
        """
        for observation in self.observations:
            if observation.action_id == action_id:
                return observation
        return None

    def get_loop_iteration(self, iteration_idx: int) -> Dict[str, Any]:
        """Get a complete loop iteration (thought-action-observation)

        Args:
            iteration_idx: Index of the iteration (0-based)

        Returns:
            Dictionary containing the iteration data
        """
        if iteration_idx >= len(self.thoughts):
            return {}

        thought = self.thoughts[iteration_idx]
        action = self.get_action_for_thought(thought.id)
        observation = (
            self.get_observation_for_action(action.id) if action else None
        )

        return {
            "iteration": iteration_idx,
            "thought": thought.to_dict() if thought else None,
            "action": action.to_dict() if action else None,
            "observation": observation.to_dict() if observation else None,
        }

    def get_full_history(self) -> Dict[str, Any]:
        """Get the full history as a structured dictionary

        Returns:
            Dictionary containing all thoughts, actions, and observations
        """
        return {
            "thoughts": [t.to_dict() for t in self.thoughts],
            "actions": [a.to_dict() for a in self.actions],
            "observations": [o.to_dict() for o in self.observations],
            "stats": {
                "total_thoughts": len(self.thoughts),
                "total_actions": len(self.actions),
                "total_observations": len(self.observations),
                "successful_actions": sum(1 for a in self.actions if a.success),
                "failed_actions": sum(1 for a in self.actions if not a.success),
                "average_action_time_ms": (
                    sum(a.execution_time_ms for a in self.actions) / len(self.actions)
                    if self.actions
                    else 0.0
                ),
            },
        }

    def clear_history(self) -> None:
        """Clear all recorded history"""
        self.thoughts.clear()
        self.actions.clear()
        self.observations.clear()

    def get_high_confidence_thoughts(
        self, threshold: float = 0.7
    ) -> List[Thought]:
        """Get thoughts above a confidence threshold

        Args:
            threshold: Minimum confidence level (0.0-1.0)

        Returns:
            List of thoughts with confidence >= threshold
        """
        return [t for t in self.thoughts if t.confidence >= threshold]

    def get_failed_actions(self) -> List[Action]:
        """Get all failed actions

        Returns:
            List of actions that failed
        """
        return [a for a in self.actions if not a.success]

    def get_surprising_observations(self) -> List[Observation]:
        """Get observations with surprises

        Returns:
            List of observations with surprises
        """
        return [o for o in self.observations if o.surprises]
