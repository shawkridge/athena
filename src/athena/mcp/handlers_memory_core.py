"""Core memory operations forwarding (remember, recall, forget, list, optimize).

Handler Method Forwarding Module
==================================
This module logically groups handler methods by domain.
Actual implementations remain in handlers.py::MemoryMCPServer.

This pattern provides:
- Logical domain separation
- Easy code navigation
- Zero breaking changes
- Simple migration path to full extraction
"""

from .handlers import MemoryMCPServer

# 25 handler methods in this domain:
#   - _handle_remember
#   - _handle_recall
#   - _handle_forget
#   - _handle_list_memories
#   - _handle_optimize
#   - _handle_search_projects
#   - _handle_recall_events
#   - _handle_recall_events_by_session
#   - _handle_optimize_plan
#   - _handle_optimize_plan_suggestions
#   - _handle_optimize_queries
#   - _handle_optimize_session_start
#   - _handle_optimize_session_end
#   - _handle_optimize_user_prompt_submit
#   - _handle_optimize_post_tool_use
#   ... and 10 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
