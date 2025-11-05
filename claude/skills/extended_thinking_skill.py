"""
Base class for Phase 3 skills that use extended thinking.

Provides common infrastructure for:
- Calling Claude's extended thinking API
- Capturing reasoning steps
- Recording ThinkingTraces
- Fallback to heuristics if API unavailable
"""

import asyncio
import json
import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base_skill import BaseSkill, SkillResult
from memory_mcp.ai_coordination.thinking_traces import (
    ThinkingTrace, ReasoningStep, ReasoningPattern, ProblemType
)

logger = logging.getLogger(__name__)


class ExtendedThinkingSkill(BaseSkill):
    """
    Base class for skills that use Claude's extended thinking.

    Provides:
    - Call Claude with extended thinking (with budget control)
    - Capture reasoning steps from Claude's response
    - Record ThinkingTraces automatically
    - Fallback to heuristics if API unavailable
    - Link reasoning to execution outcomes
    """

    def __init__(self, skill_id: str, skill_name: str, thinking_budget: int = 5000):
        """
        Initialize extended thinking skill.

        Args:
            skill_id: Unique skill identifier
            skill_name: Human-readable skill name
            thinking_budget: Extended thinking token budget (default 5000)
        """
        super().__init__(skill_id, skill_name)
        self.thinking_budget = thinking_budget
        self.client = None

        if ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic()
                logger.info(f"[{skill_name}] Anthropic client initialized with thinking budget: {thinking_budget}")
            except Exception as e:
                logger.warning(f"[{skill_name}] Failed to initialize Anthropic client: {e}")

    @abstractmethod
    async def _analyze_with_thinking(
        self, problem: str, session_id: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Subclasses must implement this to call Claude with extended thinking.

        Args:
            problem: Problem description
            session_id: Session ID for context

        Returns:
            (analysis_dict, reasoning_summary_dict)
        """
        pass

    @abstractmethod
    async def _execute_heuristic(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Subclasses must implement heuristic fallback.

        Args:
            problem: Problem description
            context: Execution context

        Returns:
            Skill result dict
        """
        pass

    async def call_claude_with_thinking(
        self, prompt: str, model: str = "claude-sonnet-4-5"
    ) -> Tuple[str, str]:
        """
        Call Claude with extended thinking enabled.

        Args:
            prompt: Prompt to send to Claude
            model: Model to use (must support extended thinking)

        Returns:
            (text_response, thinking_content)
        """
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=2000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": self.thinking_budget
                },
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            thinking_content = ""
            text_response = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    text_response += block.text

            return text_response, thinking_content

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    def extract_reasoning_from_thinking(
        self, thinking_content: str, max_steps: int = 5
    ) -> List[ReasoningStep]:
        """
        Extract reasoning steps from Claude's thinking content.

        Simple heuristic: Split thinking by numbered points or major thoughts.

        Args:
            thinking_content: Raw thinking from Claude
            max_steps: Maximum steps to extract

        Returns:
            List of ReasoningStep objects
        """
        steps = []

        # Split by newlines and filter meaningful lines
        lines = [l.strip() for l in thinking_content.split('\n') if l.strip()]

        step_number = 1
        for i, line in enumerate(lines):
            if step_number > max_steps:
                break

            # Skip very short lines or meta-commentary
            if len(line) < 10 or line.startswith('Let me'):
                continue

            # Check if this looks like a decision point (ends with ?, contains decision keywords)
            is_decision_point = (
                line.endswith('?') or
                any(keyword in line.lower() for keyword in ['choose', 'select', 'decide', 'best', 'recommend'])
            )

            # Estimate confidence based on certainty keywords
            confidence = 0.8
            if any(kw in line.lower() for kw in ['uncertain', 'might', 'could', 'possibly']):
                confidence = 0.6
            elif any(kw in line.lower() for kw in ['clearly', 'definitely', 'must', 'should']):
                confidence = 0.9

            steps.append(ReasoningStep(
                step_number=step_number,
                thought=line[:200],  # Limit to 200 chars
                confidence=confidence,
                decision_point=is_decision_point,
            ))

            step_number += 1

        return steps if steps else [
            ReasoningStep(
                step_number=1,
                thought="Extended thinking analysis completed",
                confidence=0.85,
                decision_point=False
            )
        ]

    async def record_thinking_trace(
        self,
        memory_manager: Any,
        problem: str,
        problem_type: ProblemType,
        problem_complexity: int,
        reasoning_steps: List[ReasoningStep],
        conclusion: str,
        session_id: str,
        duration_seconds: int,
        reasoning_quality: Optional[float] = None,
        primary_pattern: Optional[ReasoningPattern] = None,
        secondary_patterns: Optional[List[ReasoningPattern]] = None,
    ) -> Optional[int]:
        """
        Record thinking trace in memory.

        Args:
            memory_manager: Memory manager with MCP tool access
            problem: Problem being reasoned about
            problem_type: Type of problem (from ProblemType enum)
            problem_complexity: Complexity 1-10
            reasoning_steps: List of reasoning steps
            conclusion: Final conclusion
            session_id: Session identifier
            duration_seconds: Time spent reasoning
            reasoning_quality: Optional quality score (0.0-1.0)
            primary_pattern: Primary reasoning pattern used
            secondary_patterns: Secondary patterns used

        Returns:
            ID of recorded thinking trace, or None if failed
        """
        if not memory_manager:
            return None

        try:
            # Calculate reasoning quality if not provided
            if reasoning_quality is None:
                reasoning_quality = (
                    sum(s.confidence for s in reasoning_steps) / len(reasoning_steps)
                    if reasoning_steps else 0.5
                )

            # Default patterns if not provided
            if primary_pattern is None:
                primary_pattern = ReasoningPattern.DECOMPOSITION
            if secondary_patterns is None:
                secondary_patterns = [ReasoningPattern.DEDUCTIVE]

            # Call MCP tool to record thinking
            result = await memory_manager.call_tool(
                "record_reasoning",
                {
                    "problem": problem,
                    "problem_type": problem_type.value if hasattr(problem_type, 'value') else str(problem_type),
                    "problem_complexity": problem_complexity,
                    "reasoning_steps": [
                        {
                            "step_number": s.step_number,
                            "thought": s.thought,
                            "confidence": s.confidence,
                            "decision_point": s.decision_point,
                            "decision_made": s.decision_made,
                            "rationale": s.rationale,
                        }
                        for s in reasoning_steps
                    ],
                    "conclusion": conclusion,
                    "reasoning_quality": reasoning_quality,
                    "primary_pattern": primary_pattern.value if hasattr(primary_pattern, 'value') else str(primary_pattern),
                    "secondary_patterns": [
                        p.value if hasattr(p, 'value') else str(p)
                        for p in secondary_patterns
                    ],
                    "session_id": session_id,
                    "duration_seconds": duration_seconds,
                    "ai_model_used": "claude-sonnet-4-5-extended",
                }
            )

            thinking_id = result.get("thinking_id") or result.get("id")
            if thinking_id:
                logger.info(f"[{self.skill_name}] Recorded thinking trace: {thinking_id}")
            return thinking_id

        except Exception as e:
            logger.error(f"[{self.skill_name}] Failed to record thinking trace: {e}", exc_info=True)
            return None

    async def link_reasoning_to_execution(
        self,
        memory_manager: Any,
        thinking_id: int,
        execution_id: str,
        was_correct: bool,
        outcome_quality: float,
    ) -> bool:
        """
        Link a reasoning trace to execution outcome for learning.

        Call this AFTER the decision has been executed and you know the result.

        Args:
            memory_manager: Memory manager with MCP tool access
            thinking_id: ID of thinking trace
            execution_id: ID of execution that resulted
            was_correct: Was the reasoning correct?
            outcome_quality: Quality of execution outcome (0.0-1.0)

        Returns:
            True if successful, False otherwise
        """
        if not memory_manager or not thinking_id:
            return False

        try:
            await memory_manager.call_tool(
                "link_reasoning_to_execution",
                {
                    "thinking_id": thinking_id,
                    "execution_id": execution_id,
                    "was_correct": was_correct,
                    "outcome_quality": outcome_quality,
                }
            )
            logger.info(
                f"[{self.skill_name}] Linked thinking {thinking_id} to execution {execution_id}: "
                f"correct={was_correct}, quality={outcome_quality:.1%}"
            )
            return True

        except Exception as e:
            logger.error(f"[{self.skill_name}] Failed to link reasoning to execution: {e}")
            return False

    def get_thinking_stats(self) -> Dict[str, Any]:
        """Get statistics about thinking usage."""
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "thinking_budget": self.thinking_budget,
            "api_available": self.client is not None,
            "executions": self.trigger_count,
            "last_triggered": self.last_triggered,
        }
