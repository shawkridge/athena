"""Hook support libraries for Claude Code automation."""

__version__ = "1.0.0"
__author__ = "Claude Code Hook System"

# Import main utilities
from .event_recorder import EventRecorder
from .agent_invoker import AgentInvoker
from .load_monitor import LoadMonitor

__all__ = [
    "EventRecorder",
    "AgentInvoker",
    "LoadMonitor",
]
