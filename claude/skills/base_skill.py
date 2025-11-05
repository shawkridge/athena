"""
Base class for Phase 3 Executive Function skills.

Provides common infrastructure for auto-triggered skills.
"""

from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """Base class for all Phase 3 skills."""

    def __init__(self, skill_id: str, skill_name: str):
        """Initialize skill.

        Args:
            skill_id: Unique skill identifier
            skill_name: Human-readable skill name
        """
        self.skill_id = skill_id
        self.skill_name = skill_name
        self.last_triggered = None
        self.trigger_count = 0
        self.last_result = None

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the skill.

        Args:
            context: Execution context containing:
                - memory_manager: UnifiedMemoryManager instance
                - working_memory: Current working memory state
                - active_goal_id: Current goal (if any)
                - event: Triggering event (if auto-triggered)

        Returns:
            Dict with 'status', 'data', 'actions' keys
        """
        pass

    def _log_execution(self, result: Dict[str, Any]):
        """Log skill execution."""
        self.last_triggered = datetime.now()
        self.trigger_count += 1
        self.last_result = result

        status = result.get('status', 'unknown')
        logger.info(
            f"[{self.skill_name}] Execution #{self.trigger_count}: {status}",
            extra={"skill_id": self.skill_id}
        )

    def should_trigger(self, trigger_type: str, trigger_value: Any) -> bool:
        """Check if skill should trigger on given event.

        Args:
            trigger_type: 'event', 'time', or 'context'
            trigger_value: Value to match

        Returns:
            True if skill should execute
        """
        # Override in subclasses for custom trigger logic
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Get skill metadata."""
        return {
            "id": self.skill_id,
            "name": self.skill_name,
            "triggered_count": self.trigger_count,
            "last_triggered": self.last_triggered,
        }


class SkillResult:
    """Helper class for skill results."""

    def __init__(self, status: str = "success", data: Optional[Dict] = None,
                 actions: Optional[List[str]] = None, error: Optional[str] = None):
        """Initialize result.

        Args:
            status: 'success', 'partial', 'failed', 'skipped'
            data: Result data
            actions: List of recommended actions
            error: Error message if failed
        """
        self.status = status
        self.data = data or {}
        self.actions = actions or []
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return {
            "status": self.status,
            "data": self.data,
            "actions": self.actions,
            "error": self.error,
        }
