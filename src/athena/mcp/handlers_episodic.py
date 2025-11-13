"""Episodic memory handlers - event recording and temporal retrieval.

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

# 16 handler methods in this domain:
#   - _handle_record_event
#   - _handle_get_timeline
#   - _handle_batch_record_events
#   - _handle_schedule_consolidation
#   - _handle_consolidation_quality_metrics
#   - _handle_cluster_consolidation_events
#   - _handle_consolidation_run_consolidation
#   - _handle_consolidation_extract_patterns
#   - _handle_consolidation_cluster_events
#   - _handle_consolidation_measure_quality
#   - _handle_consolidation_measure_advanced
#   - _handle_consolidation_analyze_strategy
#   - _handle_consolidation_analyze_project
#   - _handle_consolidation_analyze_validation
#   - _handle_consolidation_discover_orchestration
#   ... and 1 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
