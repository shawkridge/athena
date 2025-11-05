"""
Priority Calculator Skill - Phase 3 Executive Function with Extended Thinking.

Ranks goals by composite score using extended thinking to handle nuanced
trade-offs between urgency, importance, progress, and alignment.

This skill demonstrates how extended thinking helps with optimization/ranking
problems where multiple factors must be weighted together intelligently.
Uses moderate thinking budget (2000) since it's focused on ranking, not discovery.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .extended_thinking_skill import ExtendedThinkingSkill
from memory_mcp.ai_coordination.thinking_traces import (
    ReasoningPattern, ProblemType, ReasoningStep
)

logger = logging.getLogger(__name__)


class PriorityCalculatorExtendedSkill(ExtendedThinkingSkill):
    """Calculate goal priorities using extended thinking."""

    def __init__(self):
        """Initialize priority calculator."""
        super().__init__(
            skill_id="priority-calculator-extended",
            skill_name="Priority Calculator (Extended)",
            thinking_budget=2000  # Moderate budget - optimization problem
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate priorities for all active goals.

        Args:
            context: Execution context with:
                - active_goals: List of goal dicts
                - memory_manager: For recording thinking
                - session_id: Session identifier

        Returns:
            Result with ranked goals and thinking_trace_id
        """
        try:
            active_goals = context.get('active_goals', [])
            memory_manager = context.get('memory_manager')
            session_id = context.get('session_id', 'unknown')

            if not active_goals:
                return {
                    "status": "skipped",
                    "data": {"reason": "No active goals"}
                }

            start_time = datetime.now()

            # ================================================================
            # STEP 1: Use Extended Thinking for Priority Analysis
            # ================================================================

            if not self.client:
                # Fallback to heuristic if API unavailable
                return await self._execute_heuristic(active_goals, context)

            logger.info(f"[PriorityCalculator] Ranking {len(active_goals)} goals with extended thinking...")

            # Call Claude with extended thinking
            ranking_data, claude_reasoning = await self._analyze_with_thinking(
                active_goals, session_id
            )

            # Capture: Ranking reasoning
            reasoning_steps = [
                ReasoningStep(
                    step_number=1,
                    thought=f"Analyzed {len(active_goals)} goals across dimensions: urgency, importance, progress, alignment",
                    confidence=0.95,
                    decision_point=False
                ),
                ReasoningStep(
                    step_number=2,
                    thought="Considered trade-offs between competing priorities and strategic alignment",
                    confidence=0.90,
                    decision_point=False
                ),
                ReasoningStep(
                    step_number=3,
                    thought=f"Generated optimal ranking with recommended focus order",
                    confidence=0.88,
                    decision_point=True,
                    decision_made=f"Top priority: {ranking_data['ranking'][0]['goal_id']}",
                    rationale=f"Highest composite score: {ranking_data['ranking'][0]['composite_score']:.2f}"
                ),
            ]

            # ================================================================
            # STEP 2: Record Thinking Trace
            # ================================================================

            thinking_id = await self.record_thinking_trace(
                memory_manager=memory_manager,
                problem=f"Rank {len(active_goals)} goals by priority",
                problem_type=ProblemType.FEATURE_DESIGN,  # Could also be ARCHITECTURE
                problem_complexity=min(10, len(active_goals) + 1),
                reasoning_steps=reasoning_steps,
                conclusion=f"Optimal ranking calculated with recommendations",
                session_id=session_id,
                duration_seconds=int((datetime.now() - start_time).total_seconds()),
                reasoning_quality=0.89,
                primary_pattern=ReasoningPattern.HEURISTIC,  # Ranking uses heuristic weighting
                secondary_patterns=[ReasoningPattern.DEDUCTIVE, ReasoningPattern.ANALOGY],
            )

            # ================================================================
            # STEP 3: Build Result
            # ================================================================

            result = {
                "status": "success",
                "data": {
                    "ranking": ranking_data.get('ranking', []),
                    "composite_scores": {
                        r['goal_id']: r['composite_score']
                        for r in ranking_data.get('ranking', [])
                    },
                    "score_breakdown": ranking_data.get('score_breakdown', {}),
                    "thinking_trace_id": thinking_id,
                    "extended_thinking_used": True,
                    "recommendations": ranking_data.get('recommendations', []),
                    "strategic_notes": ranking_data.get('strategic_notes', ''),
                    "timestamp": datetime.now().isoformat(),
                },
                "actions": [
                    f"Focus on top priority: {ranking_data['ranking'][0]['goal_id']}",
                    "Allocate resources according to ranking",
                    "Review strategic notes for context",
                    "Revisit ranking if priorities change",
                ]
            }

            self._log_execution(result)
            return result

        except Exception as e:
            logger.error(f"Error in priority calculation: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _analyze_with_thinking(
        self, active_goals: List[Dict[str, Any]], session_id: str
    ) -> tuple:
        """
        Analyze and rank goals using extended thinking.

        Returns:
            (ranking_data, reasoning_summary)
        """
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        # Build goal descriptions with all relevant factors
        goal_descriptions = "\n".join([
            f"Goal {i+1} (ID: {g.get('id', 'unknown')}):\n"
            f"  Description: {g.get('description', '')}\n"
            f"  Priority Level: {g.get('priority', 'medium')}\n"
            f"  Deadline: {g.get('deadline', 'none')}\n"
            f"  Progress: {g.get('progress', 0):.0%} complete\n"
            f"  Strategic Value: {g.get('strategic_value', 'medium')}\n"
            f"  Blockers: {g.get('blocker_count', 0)}\n"
            f"  Team Capacity Impact: {g.get('team_impact', 'medium')}\n"
            f"  Technical Risk: {g.get('technical_risk', 'low')}"
            for i, g in enumerate(active_goals)
        ])

        prompt = f"""Rank these {len(active_goals)} active goals by priority, considering multiple dimensions:

{goal_descriptions}

Consider factors:
1. **Urgency** (deadline pressure, time-sensitive): 0-10
2. **Importance** (strategic value, impact): 0-10
3. **Progress** (% complete, momentum): affects priority
4. **Dependencies** (blocks others, blocked by others)
5. **Risk** (technical, resource, schedule risks)
6. **Alignment** (strategic alignment, team capacity)

Provide:
1. Composite score for each goal (weighted blend of factors)
2. Ranking from highest to lowest priority
3. Rationale for top 3 priorities
4. Recommendations for resource allocation
5. Strategic notes on trade-offs

Return JSON:
{{
    "ranking": [
        {{
            "goal_id": "...",
            "rank": 1,
            "composite_score": 8.5,
            "rationale": "..."
        }},
        ...
    ],
    "score_breakdown": {{
        "<goal_id>": {{
            "urgency": 7.0,
            "importance": 9.0,
            "progress": 0.3,
            "risk_factor": 0.8,
            "alignment": 0.9,
            "composite": 8.5
        }},
        ...
    }},
    "recommendations": ["...", "..."],
    "strategic_notes": "...",
    "reasoning_summary": "..."
}}"""

        try:
            text_response, thinking_content = await self.call_claude_with_thinking(
                prompt,
                model="claude-sonnet-4-5"
            )

            ranking_data = json.loads(text_response)

            # Build reasoning summary
            reasoning = {
                "summary": ranking_data.get("reasoning_summary", ""),
                "recommendations": ranking_data.get("recommendations", []),
                "thinking_depth": len(thinking_content.split('\n')),
            }

            return ranking_data, reasoning

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValueError(f"Invalid JSON response from Claude")
        except Exception as e:
            logger.error(f"Extended thinking analysis failed: {e}")
            raise

    async def _execute_heuristic(
        self, active_goals: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback heuristic priority calculation."""
        logger.warning("Extended thinking unavailable, using heuristic priority calculation")

        # Simple heuristic: score based on visible factors
        ranking = self._calculate_scores_heuristic(active_goals)

        return {
            "status": "success",
            "data": {
                "ranking": ranking,
                "composite_scores": {r['goal_id']: r['composite_score'] for r in ranking},
                "extended_thinking_used": False,
                "fallback_reason": "Extended thinking unavailable",
            }
        }

    def _calculate_scores_heuristic(self, active_goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple heuristic priority scoring."""
        scored_goals = []

        for goal in active_goals:
            # Simple scoring formula
            priority_map = {'critical': 10, 'high': 8, 'medium': 5, 'low': 2}
            priority_score = priority_map.get(goal.get('priority', 'medium'), 5)

            # Deadline urgency (days remaining)
            deadline = goal.get('deadline')
            if deadline:
                # Simple: closer deadline = higher urgency
                days_remaining = 7  # Placeholder
                urgency_score = min(10, 10 - days_remaining)
            else:
                urgency_score = 3

            # Progress (prioritize stalled goals)
            progress = goal.get('progress', 0)
            if progress == 0:
                progress_score = 8  # Not started, might be important
            elif progress < 0.5:
                progress_score = 7  # In progress, keep momentum
            else:
                progress_score = 5  # Near complete, less urgent

            # Blockers (prioritize unblocked)
            blockers = goal.get('blocker_count', 0)
            blocker_score = max(2, 10 - blockers * 2)

            # Composite
            composite = (
                priority_score * 0.4 +
                urgency_score * 0.3 +
                progress_score * 0.2 +
                blocker_score * 0.1
            )

            scored_goals.append({
                "goal_id": goal.get('id', 'unknown'),
                "composite_score": min(10, max(1, composite)),
                "rationale": f"Priority: {priority_score}, Urgency: {urgency_score:.1f}, Progress: {progress_score}"
            })

        # Sort by composite score
        scored_goals.sort(key=lambda x: x['composite_score'], reverse=True)

        # Add rank
        for i, goal in enumerate(scored_goals, 1):
            goal['rank'] = i

        return scored_goals


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = PriorityCalculatorExtendedSkill()
    return _instance
