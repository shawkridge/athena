"""Hook system for automatic session and conversation management.

Components:
- HookDispatcher: Core session/conversation/task lifecycle hooks with integrated safety
- HookEventBridge: Bridges HookDispatcher with EventHandlers for unified event system
- UnifiedHookSystem: High-level interface for complete hook + event coordination
"""

from .dispatcher import HookDispatcher
from .bridge import HookEventBridge, UnifiedHookSystem

__all__ = ["HookDispatcher", "HookEventBridge", "UnifiedHookSystem"]
