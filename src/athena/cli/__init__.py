"""CLI module for Athena memory system.

Provides command-line interface for slash commands following Anthropic's
code-execution-with-MCP pattern:
- Discover operations
- Execute locally
- Return summaries (300 tokens max)
"""

from .commands import (
    MemorySearchCommand,
    PlanTaskCommand,
    ValidatePlanCommand,
    SessionStartCommand,
    ManageGoalCommand,
)

__all__ = [
    "MemorySearchCommand",
    "PlanTaskCommand",
    "ValidatePlanCommand",
    "SessionStartCommand",
    "ManageGoalCommand",
]
