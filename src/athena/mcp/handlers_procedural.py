"""Procedural memory handlers - workflows and procedures.

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

# 29 handler methods in this domain:
#   - _handle_get_procedure_effectiveness
#   - _handle_suggest_procedure_improvements
#   - _handle_create_procedure
#   - _handle_find_procedures
#   - _handle_record_execution
#   - _handle_compare_procedure_versions
#   - _handle_rollback_procedure
#   - _handle_list_procedure_versions
#   - _handle_record_execution_feedback
#   - _handle_generate_workflow_from_task
#   - _handle_suggest_cost_optimizations
#   - _handle_train_estimation_model
#   - _handle_suggest_refactorings
#   - _handle_suggest_bug_fixes
#   - _handle_get_pattern_suggestions
#   ... and 14 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
