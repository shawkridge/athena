"""
Conflict Detector Skill - Phase 3 Executive Function with Extended Thinking.

Detects resource, dependency, and priority conflicts between active goals
using Claude's extended thinking for deep analysis.

This skill shows a different use case: detecting non-obvious conflicts that
heuristics might miss. Uses smaller thinking budget (3000) since it's more
focused analysis than open-ended strategy selection.
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


class ConflictDetectorExtendedSkill(ExtendedThinkingSkill):
    """Detect conflicts between goals using extended thinking."""

    def __init__(self):
        """Initialize conflict detector."""
        super().__init__(
            skill_id="conflict-detector-extended",
            skill_name="Conflict Detector (Extended)",
            thinking_budget=3000  # Smaller budget - more focused analysis
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect conflicts between active goals.

        Args:
            context: Execution context with:
                - active_goals: List of goal dicts
                - memory_manager: For recording thinking
                - session_id: Session identifier

        Returns:
            Result with conflicts detected and thinking_trace_id
        """
        try:
            active_goals = context.get('active_goals', [])
            memory_manager = context.get('memory_manager')
            session_id = context.get('session_id', 'unknown')

            if len(active_goals) < 2:
                return {
                    "status": "skipped",
                    "data": {"reason": "Less than 2 active goals"}
                }.to_dict() if hasattr({}, 'to_dict') else {
                    "status": "skipped",
                    "data": {"reason": "Less than 2 active goals"}
                }

            start_time = datetime.now()

            # ================================================================
            # STEP 1: Use Extended Thinking for Deep Conflict Analysis
            # ================================================================

            if not self.client:
                # Fallback to heuristic if API unavailable
                return await self._execute_heuristic(active_goals, context)

            logger.info(f"[ConflictDetector] Analyzing {len(active_goals)} goals with extended thinking...")

            # Call Claude with extended thinking
            conflicts_data, claude_reasoning = await self._analyze_with_thinking(
                active_goals, session_id
            )

            # Capture: Analysis reasoning
            reasoning_steps = [
                ReasoningStep(
                    step_number=1,
                    thought=f"Analyzed {len(active_goals)} active goals for conflicts across multiple dimensions",
                    confidence=0.95,
                    decision_point=False
                ),
                ReasoningStep(
                    step_number=2,
                    thought=f"Identified {conflicts_data.get('conflicts_detected', 0)} potential conflicts",
                    confidence=0.90,
                    decision_point=False
                ),
                ReasoningStep(
                    step_number=3,
                    thought=f"Severity: {conflicts_data.get('severity', 'none')}",
                    confidence=0.85,
                    decision_point=True,
                    decision_made=conflicts_data.get('severity', 'none'),
                    rationale="Based on impact analysis of detected conflicts"
                ),
            ]

            # ================================================================
            # STEP 2: Record Thinking Trace
            # ================================================================

            thinking_id = await self.record_thinking_trace(
                memory_manager=memory_manager,
                problem=f"Detect conflicts among {len(active_goals)} active goals",
                problem_type=ProblemType.INTEGRATION,
                problem_complexity=min(10, max(1, len(active_goals) * 2 - 2)),
                reasoning_steps=reasoning_steps,
                conclusion=f"Found {conflicts_data.get('conflicts_detected', 0)} conflicts, severity: {conflicts_data.get('severity', 'none')}",
                session_id=session_id,
                duration_seconds=int((datetime.now() - start_time).total_seconds()),
                reasoning_quality=0.88,
                primary_pattern=ReasoningPattern.DECOMPOSITION,
                secondary_patterns=[ReasoningPattern.ANALOGY, ReasoningPattern.DEDUCTIVE],
            )

            # ================================================================
            # STEP 3: Build Result
            # ================================================================

            result = {
                "status": "success",
                "data": {
                    "conflicts_detected": conflicts_data.get('conflicts_detected', 0),
                    "severity": conflicts_data.get('severity', 'none'),
                    "details": conflicts_data.get('details', []),
                    "resolution_priority": conflicts_data.get('resolution_priority', []),
                    "thinking_trace_id": thinking_id,
                    "extended_thinking_used": True,
                    "confidence": 0.88,
                    "claude_insights": claude_reasoning.get("insights", []),
                    "timestamp": datetime.now().isoformat(),
                },
                "actions": [
                    f"Review {conflicts_data.get('conflicts_detected', 0)} detected conflicts",
                    f"Address conflicts with severity: {conflicts_data.get('severity', 'none')}",
                    "Follow suggested resolution order",
                    "Re-analyze after conflict resolution",
                ] if conflicts_data.get('conflicts_detected', 0) > 0 else [
                    "No significant conflicts detected",
                    "Proceed with current goal execution",
                ]
            }

            self._log_execution(result)
            return result

        except Exception as e:
            logger.error(f"Error in conflict detection: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _analyze_with_thinking(
        self, active_goals: List[Dict[str, Any]], session_id: str
    ) -> tuple:
        """
        Analyze goals for conflicts using extended thinking.

        Returns:
            (conflicts_data, reasoning_summary)
        """
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        # Build goal descriptions
        goal_descriptions = "\n".join([
            f"Goal {i+1} (ID: {g.get('id', 'unknown')}):\n"
            f"  Description: {g.get('description', '')}\n"
            f"  Priority: {g.get('priority', 'medium')}\n"
            f"  Status: {g.get('status', 'active')}\n"
            f"  Owner: {g.get('owner', 'unknown')}\n"
            f"  Estimated Duration: {g.get('estimated_hours', 'unknown')} hours\n"
            f"  Dependencies: {', '.join(g.get('dependencies', [])) or 'None'}\n"
            f"  Tools/Resources Needed: {', '.join(g.get('required_tools', [])) or 'None'}"
            for i, g in enumerate(active_goals)
        ])

        prompt = f"""Analyze these {len(active_goals)} active goals for conflicts and interactions:

{goal_descriptions}

Identify:
1. **Resource Conflicts**: Same person/tool needed at same time
2. **Dependency Conflicts**: Goal A blocks goal B
3. **Priority Conflicts**: Both critical with limited resources
4. **Technical Conflicts**: Incompatible requirements
5. **Timing Conflicts**: Overlapping timelines creating pressure
6. **Hidden Conflicts**: Non-obvious interactions

For each conflict, assess:
- Which goals are involved?
- What is the impact (low/high)?
- When will it become critical?
- What's the recommended resolution?

Return JSON:
{{
    "conflicts_detected": <count>,
    "severity": "none" | "low" | "medium" | "high" | "critical",
    "analysis_summary": "...",
    "details": [
        {{
            "type": "resource" | "dependency" | "priority" | "technical" | "timing" | "hidden",
            "goals_involved": [<id>, ...],
            "description": "...",
            "impact": "low" | "high",
            "timeline": "immediate" | "soon" | "later",
            "recommendation": "..."
        }}
    ],
    "resolution_priority": [<goal_id>, ...],
    "key_insights": ["...", ...]
}}"""

        try:
            text_response, thinking_content = await self.call_claude_with_thinking(
                prompt,
                model="claude-sonnet-4-5"
            )

            conflicts_data = json.loads(text_response)

            # Build reasoning summary
            reasoning = {
                "analysis_summary": conflicts_data.get("analysis_summary", ""),
                "insights": conflicts_data.get("key_insights", []),
                "thinking_depth": len(thinking_content.split('\n')),
            }

            return conflicts_data, reasoning

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValueError(f"Invalid JSON response from Claude")
        except Exception as e:
            logger.error(f"Extended thinking analysis failed: {e}")
            raise

    async def _execute_heuristic(
        self, active_goals: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback heuristic conflict detection."""
        logger.warning("Extended thinking unavailable, using heuristic conflict detection")

        # Simple heuristic: check for overlapping owners
        conflicts = self._detect_conflicts_heuristic(active_goals)

        return {
            "status": "success",
            "data": {
                "conflicts_detected": len(conflicts),
                "severity": "high" if len(conflicts) > 2 else "low" if len(conflicts) > 0 else "none",
                "details": conflicts,
                "resolution_priority": [c['goals_involved'][0] for c in conflicts],
                "extended_thinking_used": False,
                "fallback_reason": "Extended thinking unavailable",
            }
        }

    def _detect_conflicts_heuristic(self, active_goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple heuristic conflict detection."""
        conflicts = []

        # Check for resource (owner) conflicts
        owners = {}
        for goal in active_goals:
            owner = goal.get('owner', 'unknown')
            if owner not in owners:
                owners[owner] = []
            owners[owner].append(goal.get('id', 'unknown'))

        # Flag if one person has multiple critical goals
        for owner, goal_ids in owners.items():
            if len(goal_ids) > 1:
                # Check priority
                goals_for_owner = [g for g in active_goals if g.get('owner') == owner]
                critical_count = sum(1 for g in goals_for_owner if g.get('priority') == 'critical')

                if critical_count >= 2:
                    conflicts.append({
                        "type": "resource",
                        "goals_involved": goal_ids,
                        "description": f"{owner} assigned to {len(goal_ids)} goals ({critical_count} critical)",
                        "impact": "high",
                        "recommendation": f"Reassign non-critical goals from {owner}",
                    })

        # Check for dependency conflicts
        for goal in active_goals:
            deps = goal.get('dependencies', [])
            if deps:
                for dep_id in deps:
                    dep_goal = next((g for g in active_goals if g.get('id') == dep_id), None)
                    if dep_goal and dep_goal.get('status') == 'blocked':
                        conflicts.append({
                            "type": "dependency",
                            "goals_involved": [goal.get('id'), dep_id],
                            "description": f"Goal depends on blocked goal",
                            "impact": "high",
                            "recommendation": f"Resolve blocker for {dep_id}",
                        })

        return conflicts


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = ConflictDetectorExtendedSkill()
    return _instance
