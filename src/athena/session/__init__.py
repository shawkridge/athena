"""Session context management for query-aware memory retrieval.

This module provides session context tracking to enable query-aware memory
retrieval that adapts to the current task and phase.
"""

from .context_manager import SessionContext, SessionContextManager

__all__ = ["SessionContext", "SessionContextManager"]
