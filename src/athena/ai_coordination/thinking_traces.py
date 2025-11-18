"""Data models for thinking traces - AI reasoning process and correctness.

Stores the reasoning process AI goes through to solve problems, and links
it to execution outcomes to extract effective reasoning patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReasoningPattern(str, Enum):
    """Type of reasoning approach used."""

    DECOMPOSITION = "decomposition"  # Break problem into parts
    ANALOGY = "analogy"  # Reason by similarity to known problems
    FIRST_PRINCIPLES = "first_principles"  # Build up from basics
    EMPIRICAL = "empirical"  # Test and iterate
    HEURISTIC = "heuristic"  # Use rules of thumb
    DEDUCTIVE = "deductive"  # Logical inference
    ABDUCTIVE = "abductive"  # Inference to best explanation


class ProblemType(str, Enum):
    """Type of problem being reasoned about."""

    ARCHITECTURE = "architecture"  # System design decisions
    DEBUGGING = "debugging"  # Finding and fixing bugs
    OPTIMIZATION = "optimization"  # Performance or efficiency
    REFACTORING = "refactoring"  # Code improvement
    FEATURE_DESIGN = "feature_design"  # New feature planning
    INTEGRATION = "integration"  # Component integration
    TESTING = "testing"  # Test strategy


class ReasoningStep(BaseModel):
    """Single step in reasoning process."""

    step_number: int
    thought: str  # What was considered
    confidence: float = 0.5  # 0.0-1.0: Confidence in this thought
    decision_point: bool = False  # Did this lead to a decision?
    decision_made: Optional[str] = None  # If decision_point=True
    rationale: Optional[str] = None  # Why this decision?


class ThinkingTrace(BaseModel):
    """Complete reasoning process for solving a problem.

    Captures the chain of thoughts, conclusions, and links to execution
    outcomes to track reasoning correctness and effectiveness.
    """

    id: Optional[int] = None

    # Problem context
    problem: str  # What problem was being solved?
    problem_type: ProblemType
    problem_complexity: int = 5  # 1-10 scale

    # Reasoning process
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    conclusion: str  # Final conclusion from reasoning
    reasoning_quality: float = 0.5  # 0.0-1.0: Quality of reasoning process

    # Reasoning pattern
    primary_pattern: Optional[ReasoningPattern] = None
    secondary_patterns: list[ReasoningPattern] = Field(default_factory=list)
    pattern_effectiveness: Optional[float] = None  # 0.0-1.0: Did this pattern work?

    # Link to execution
    linked_execution_id: Optional[str] = None  # UUID as string to ExecutionTrace
    was_reasoning_correct: Optional[bool] = None  # Correctness verified after execution
    execution_outcome_quality: Optional[float] = None  # How well did execution go? (0.0-1.0)

    # Metadata
    session_id: str  # Session this thinking happened in
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_seconds: int = 0  # Time spent reasoning
    ai_model_used: Optional[str] = None  # Which model generated this thinking?

    # Consolidation tracking
    consolidation_status: Optional[str] = None  # "unconsolidated", "consolidated"
    consolidated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
