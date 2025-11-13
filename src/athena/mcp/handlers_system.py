"""System handlers - health, analytics, code analysis, automation.

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

# 141 handler methods in this domain:
#   - _handle_inhibit_memory
#   - _handle_get_project_status
#   - _handle_recommend_orchestration
#   - _handle_bayesian_surprise_benchmark
#   - _handle_temporal_kg_synthesis
#   - _handle_get_project_dashboard
#   - _handle_discover_patterns
#   - _handle_estimate_resources
#   - _handle_add_project_dependency
#   - _handle_analyze_critical_path
#   - _handle_detect_resource_conflicts
#   - _handle_create_rule
#   - _handle_list_rules
#   - _handle_delete_rule
#   - _handle_get_suggestions
#   ... and 126 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
