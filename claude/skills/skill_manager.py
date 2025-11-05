"""Skill Manager - Orchestrates auto-triggering of Phase 3 skills.

Enhanced with thinking trace tracking and execution outcome linking for learning.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class SkillManager:
    """Manages skill execution and auto-triggering with learning support."""

    def __init__(self, memory_manager=None):
        """Initialize skill manager.

        Args:
            memory_manager: UnifiedMemoryManager instance for MCP tool calls
        """
        self.memory_manager = memory_manager
        self.skills = {}
        self.trigger_handlers = {}
        self.execution_history = []

        # Extended thinking support
        self.pending_outcomes = {}  # thinking_id → {skill_id, timestamp, context}
        self.linked_outcomes = []   # Track linked thinking-to-execution pairs
        self.learning_metrics = {}  # Pattern effectiveness tracking

    def register_skill(self, skill_id: str, skill_class):
        """Register a skill for auto-triggering.

        Args:
            skill_id: Unique skill identifier
            skill_class: Skill class (callable that returns skill instance)
        """
        self.skills[skill_id] = skill_class

    def on_event(self, event_type: str, handler: Callable):
        """Register event handler for skill triggering.

        Args:
            event_type: 'progress_recorded', 'goal_activated', etc.
            handler: Async callable that executes skills
        """
        if event_type not in self.trigger_handlers:
            self.trigger_handlers[event_type] = []
        self.trigger_handlers[event_type].append(handler)

    async def trigger_on_event(self, event_type: str, context: Dict) -> List[Dict]:
        """Trigger applicable skills for an event.

        Args:
            event_type: Type of event that occurred
            context: Event context and execution environment

        Returns:
            List of skill execution results
        """
        results = []

        # Map events to skills
        event_skill_map = {
            "progress_recorded": [
                "goal-state-tracker",
                "priority-calculator",
                "workflow-monitor",
            ],
            "goal_activated": [
                "conflict-detector",
                "strategy-selector",
                "priority-calculator",
            ],
            "deadline_changed": [
                "priority-calculator",
                "conflict-detector",
            ],
            "daily_check": [
                "conflict-detector",
                "priority-calculator",
                "workflow-monitor",
            ],
            "periodic_check": [
                "workflow-monitor",
                "goal-state-tracker",
            ],
        }

        # Get applicable skills
        applicable_skills = event_skill_map.get(event_type, [])

        # Execute applicable skills
        for skill_id in applicable_skills:
            if skill_id in self.skills:
                try:
                    result = await self._execute_skill(skill_id, context)
                    results.append(result)

                    # Track thinking trace IDs for later linking
                    thinking_id = result.get('data', {}).get('thinking_trace_id')
                    if thinking_id:
                        self.pending_outcomes[thinking_id] = {
                            "skill_id": skill_id,
                            "event_type": event_type,
                            "timestamp": datetime.now(),
                            "context": context,
                        }
                        logger.info(f"[SkillManager] Tracking thinking {thinking_id} from {skill_id}")

                    # Log execution
                    self.execution_history.append({
                        "skill_id": skill_id,
                        "event_type": event_type,
                        "status": result.get('status'),
                        "thinking_trace_id": thinking_id,
                        "timestamp": datetime.now().isoformat(),
                    })

                except Exception as e:
                    logger.error(
                        f"Error executing skill {skill_id}: {e}",
                        exc_info=True
                    )
                    results.append({
                        "skill_id": skill_id,
                        "status": "failed",
                        "error": str(e),
                    })

        return results

    async def _execute_skill(self, skill_id: str, context: Dict) -> Dict:
        """Execute a single skill.

        Args:
            skill_id: Skill to execute
            context: Execution context

        Returns:
            Skill result dict
        """
        if skill_id not in self.skills:
            return {"skill_id": skill_id, "status": "error", "error": "Unknown skill"}

        skill_class = self.skills[skill_id]
        skill = skill_class()

        # Add memory manager to context
        context_with_manager = {
            **context,
            "memory_manager": self.memory_manager,
        }

        return await skill.execute(context_with_manager)

    def get_execution_history(self, limit: int = 50) -> List[Dict]:
        """Get recent skill execution history.

        Args:
            limit: Max results to return

        Returns:
            List of recent executions
        """
        return self.execution_history[-limit:]

    def get_skill_stats(self) -> Dict:
        """Get statistics about skill executions."""
        if not self.execution_history:
            return {"total_executions": 0}

        successes = sum(
            1 for e in self.execution_history if e.get('status') == 'success'
        )
        failures = sum(
            1 for e in self.execution_history if e.get('status') == 'failed'
        )

        return {
            "total_executions": len(self.execution_history),
            "successes": successes,
            "failures": failures,
            "success_rate": (successes / len(self.execution_history) * 100) if self.execution_history else 0,
            "registered_skills": len(self.skills),
        }

    async def link_execution_to_thinking(
        self,
        execution_id: str,
        was_successful: bool,
        outcome_quality: float
    ) -> bool:
        """
        Link an execution result to its corresponding thinking trace.

        Call this when a goal/task completes to link the outcome back to
        the skill's reasoning.

        Args:
            execution_id: ID of the executed goal/task
            was_successful: Whether execution succeeded
            outcome_quality: Quality of execution (0.0-1.0)

        Returns:
            True if linking was successful
        """
        if not self.pending_outcomes:
            logger.warning(f"No pending outcomes to link for execution {execution_id}")
            return False

        # Find thinking trace that matches (by proximity)
        # For now, link to the most recent thinking trace
        thinking_id = None
        pending_entry = None

        # Get most recent pending outcome
        if self.pending_outcomes:
            # Get the most recent one (assume it matches this execution)
            thinking_id = max(
                self.pending_outcomes.keys(),
                key=lambda k: self.pending_outcomes[k]['timestamp']
            )
            pending_entry = self.pending_outcomes.pop(thinking_id)

        if not thinking_id:
            logger.warning("Could not find matching thinking trace for execution")
            return False

        try:
            if not self.memory_manager:
                logger.warning("No memory manager available for linking")
                return False

            # Call MCP tool to link
            await self.memory_manager.call_tool(
                "link_reasoning_to_execution",
                {
                    "thinking_id": thinking_id,
                    "execution_id": execution_id,
                    "was_correct": was_successful,
                    "outcome_quality": outcome_quality,
                }
            )

            # Track the linking
            link_record = {
                "thinking_id": thinking_id,
                "execution_id": execution_id,
                "was_successful": was_successful,
                "outcome_quality": outcome_quality,
                "skill_id": pending_entry['skill_id'],
                "timestamp": datetime.now().isoformat(),
            }
            self.linked_outcomes.append(link_record)

            logger.info(
                f"[SkillManager] Linked thinking {thinking_id} to execution {execution_id}: "
                f"success={was_successful}, quality={outcome_quality:.1%}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to link reasoning to execution: {e}")
            return False

    def get_pending_outcomes(self) -> Dict[int, Dict[str, Any]]:
        """Get all thinking traces waiting for execution linkage."""
        return self.pending_outcomes.copy()

    def cleanup_stale_outcomes(self, max_age_seconds: int = 3600) -> int:
        """
        Remove thinking traces that haven't been linked within time window.

        Args:
            max_age_seconds: Maximum age in seconds (default 1 hour)

        Returns:
            Number of entries cleaned up
        """
        now = datetime.now()
        to_remove = []

        for thinking_id, entry in self.pending_outcomes.items():
            age = (now - entry['timestamp']).total_seconds()
            if age > max_age_seconds:
                to_remove.append(thinking_id)

        for thinking_id in to_remove:
            del self.pending_outcomes[thinking_id]
            logger.info(f"[SkillManager] Cleaned up stale thinking trace {thinking_id}")

        return len(to_remove)

    async def get_learning_effectiveness(self) -> Dict[str, Any]:
        """
        Get learning effectiveness metrics from thinking traces.

        Returns:
            Dict with effectiveness metrics and pattern analysis
        """
        if not self.memory_manager or not self.linked_outcomes:
            return {"error": "No linked outcomes yet"}

        try:
            # Query memory for pattern effectiveness
            patterns = await self.memory_manager.call_tool(
                "get_reasoning_patterns_effectiveness",
                {}
            )

            # Query correctness analysis
            correctness = await self.memory_manager.call_tool(
                "get_correctness_analysis",
                {}
            )

            # Build effectiveness summary
            effectiveness = {
                "total_linked_outcomes": len(self.linked_outcomes),
                "overall_correctness_rate": correctness.get('correctness_rate', 0.0),
                "patterns": patterns,
                "top_patterns": sorted(
                    patterns.items(),
                    key=lambda x: x[1].get('success_rate', 0),
                    reverse=True
                )[:3],
                "recommendations": self._generate_pattern_recommendations(patterns),
            }

            return effectiveness

        except Exception as e:
            logger.error(f"Failed to get learning effectiveness: {e}")
            return {"error": str(e)}

    def _generate_pattern_recommendations(self, patterns: Dict[str, Dict]) -> List[str]:
        """Generate recommendations based on pattern effectiveness."""
        recommendations = []

        if not patterns:
            return ["Insufficient data for recommendations"]

        # Find most effective pattern
        best_pattern = max(
            patterns.items(),
            key=lambda x: x[1].get('success_rate', 0)
        )
        recommendations.append(
            f"Use {best_pattern[0]} reasoning (success rate: {best_pattern[1]['success_rate']:.0%})"
        )

        # Find patterns to avoid
        worst_pattern = min(
            patterns.items(),
            key=lambda x: x[1].get('success_rate', 1.0)
        )
        if worst_pattern[1].get('success_rate', 0) < 0.6:
            recommendations.append(
                f"Reduce use of {worst_pattern[0]} (success rate: {worst_pattern[1]['success_rate']:.0%})"
            )

        return recommendations

    def get_learning_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive learning dashboard."""
        execution_count = len(self.execution_history)
        with_thinking = sum(
            1 for e in self.execution_history if e.get('thinking_trace_id')
        )

        return {
            "skill_executions": {
                "total": execution_count,
                "with_extended_thinking": with_thinking,
                "thinking_adoption": f"{with_thinking/execution_count*100:.1f}%" if execution_count > 0 else "0%",
            },
            "thinking_traces": {
                "recorded": with_thinking,
                "pending_linking": len(self.pending_outcomes),
                "linked_outcomes": len(self.linked_outcomes),
            },
            "learning_status": {
                "ready_for_learning": len(self.linked_outcomes) >= 10,
                "minimum_data_reached": len(self.linked_outcomes) >= 5,
            },
            "execution_history_recent": self.get_execution_history(10),
        }


# Global manager instance
_manager: Optional[SkillManager] = None


def get_manager(memory_manager=None) -> SkillManager:
    """Get or create global skill manager.

    Args:
        memory_manager: Optional memory manager to attach

    Returns:
        SkillManager instance
    """
    global _manager
    if _manager is None:
        _manager = SkillManager(memory_manager)

        # Import and register skills
        from . import (
            get_goal_state_tracker,
            get_strategy_selector,
            get_conflict_detector,
            get_priority_calculator,
            get_workflow_monitor,
        )

        _manager.register_skill("goal-state-tracker", get_goal_state_tracker)
        _manager.register_skill("strategy-selector", get_strategy_selector)
        _manager.register_skill("conflict-detector", get_conflict_detector)
        _manager.register_skill("priority-calculator", get_priority_calculator)
        _manager.register_skill("workflow-monitor", get_workflow_monitor)

    if memory_manager and _manager.memory_manager is None:
        _manager.memory_manager = memory_manager

    return _manager
