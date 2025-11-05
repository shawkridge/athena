"""Cascade Monitor for Hook Safety.

Detects and prevents:
- Hook cycles (A → B → A)
- Deep nesting (A → B → C → D → ... with depth > limit)
- Infinite loops from hook-triggered hooks
"""

import logging
from typing import Set, List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CallStack:
    """Represents current hook call stack during execution."""
    hooks: List[str] = field(default_factory=list)
    depth: int = 0
    parent_hook: Optional[str] = None

    def push(self, hook_id: str) -> None:
        """Add hook to stack."""
        self.hooks.append(hook_id)
        self.depth += 1

    def pop(self) -> Optional[str]:
        """Remove hook from stack."""
        if self.hooks:
            self.depth -= 1
            return self.hooks.pop()
        return None

    def contains(self, hook_id: str) -> bool:
        """Check if hook is in current call stack."""
        return hook_id in self.hooks

    def get_path(self) -> List[str]:
        """Get full call path."""
        return list(self.hooks)

    def clear(self) -> None:
        """Clear stack."""
        self.hooks.clear()
        self.depth = 0
        self.parent_hook = None


class CascadeMonitor:
    """Monitor and prevent hook cascades.

    Detects:
    - Cycles: Hook A triggers B which triggers A (circular)
    - Deep nesting: Call depth exceeds threshold
    - Breadth explosion: One hook triggers many hooks

    Attributes:
        max_depth: Maximum call stack depth (default: 5)
        max_breadth: Maximum hooks triggered by single hook (default: 10)
    """

    def __init__(self, max_depth: int = 5, max_breadth: int = 10):
        """Initialize cascade monitor.

        Args:
            max_depth: Maximum call nesting depth
            max_breadth: Maximum hooks triggered in single execution
        """
        self.max_depth = max_depth
        self.max_breadth = max_breadth
        self._call_stack = CallStack()
        self._triggered_hooks: Dict[str, int] = {}  # hook_id -> count in current execution
        self.logger = logging.getLogger(__name__)

    def push_hook(self, hook_id: str) -> bool:
        """Push hook onto call stack.

        Checks for cycles and depth violations.

        Args:
            hook_id: Hook to push

        Returns:
            True if hook can execute, False if cascade detected
        """
        # Check for cycle
        if self._call_stack.contains(hook_id):
            cycle_path = self._call_stack.get_path() + [hook_id]
            self.logger.warning(f"Hook cycle detected: {' -> '.join(cycle_path)}")
            return False

        # Check depth limit
        if self._call_stack.depth >= self.max_depth:
            self.logger.warning(
                f"Hook depth limit exceeded: {self._call_stack.depth + 1} > {self.max_depth}"
            )
            return False

        # Check breadth limit
        if hook_id in self._triggered_hooks:
            self._triggered_hooks[hook_id] += 1
        else:
            self._triggered_hooks[hook_id] = 1

        if self._triggered_hooks[hook_id] > self.max_breadth:
            self.logger.warning(
                f"Hook breadth limit exceeded: {hook_id} triggered "
                f"{self._triggered_hooks[hook_id]} > {self.max_breadth} times"
            )
            return False

        # All checks passed
        self._call_stack.push(hook_id)
        return True

    def pop_hook(self) -> Optional[str]:
        """Pop hook from call stack.

        Returns:
            Hook ID that was popped
        """
        return self._call_stack.pop()

    def get_call_stack(self) -> List[str]:
        """Get current call stack.

        Returns:
            List of hook IDs in current call stack
        """
        return self._call_stack.get_path()

    def get_depth(self) -> int:
        """Get current call depth.

        Returns:
            Current nesting depth
        """
        return self._call_stack.depth

    def is_at_depth_limit(self) -> bool:
        """Check if at max depth.

        Returns:
            True if depth at or above limit
        """
        return self._call_stack.depth >= self.max_depth

    def is_at_breadth_limit(self, hook_id: str) -> bool:
        """Check if hook at breadth limit.

        Args:
            hook_id: Hook to check

        Returns:
            True if hook triggered too many times
        """
        return self._triggered_hooks.get(hook_id, 0) >= self.max_breadth

    def reset(self) -> None:
        """Reset cascade monitor (typically at end of execution).

        Clears call stack and breadth tracking.
        """
        self._call_stack.clear()
        self._triggered_hooks.clear()
        self.logger.debug("Cascade monitor reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get cascade monitoring statistics.

        Returns:
            Dictionary with current stats
        """
        return {
            'current_depth': self._call_stack.depth,
            'max_depth': self.max_depth,
            'at_depth_limit': self.is_at_depth_limit(),
            'call_stack': self.get_call_stack(),
            'hook_trigger_counts': dict(self._triggered_hooks),
            'max_breadth': self.max_breadth
        }

    def format_call_stack(self) -> str:
        """Format call stack for logging/debugging.

        Returns:
            Human-readable call stack string
        """
        if not self._call_stack.hooks:
            return "(empty)"
        return " -> ".join(self._call_stack.hooks)
