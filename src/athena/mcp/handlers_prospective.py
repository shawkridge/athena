"""Prospective memory handlers - tasks, goals, milestones.

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

# 24 handler methods in this domain:
#   - _handle_create_task
#   - _handle_list_tasks
#   - _handle_update_task_status
#   - _handle_create_task_with_planning
#   - _handle_start_task
#   - _handle_verify_task
#   - _handle_create_task_with_milestones
#   - _handle_update_milestone_progress
#   - _handle_get_active_goals
#   - _handle_set_goal
#   - _handle_get_task_health
#   - _handle_generate_task_plan
#   - _handle_calculate_task_cost
#   - _handle_calculate_task_cost
#   - _handle_get_task_health
#   ... and 9 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
