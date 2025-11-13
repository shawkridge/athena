"""Planning handlers - verification, validation, strategy.

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

# 33 handler methods in this domain:
#   - _handle_decompose_hierarchically
#   - _handle_validate_plan
#   - _handle_suggest_planning_strategy
#   - _handle_trigger_replanning
#   - _handle_verify_plan
#   - _handle_planning_validation_benchmark
#   - _handle_analyze_estimation_accuracy
#   - _handle_validate_task_against_rules
#   - _handle_validate_plan_with_reasoning
#   - _handle_generate_confidence_scores
#   - _handle_analyze_uncertainty
#   - _handle_generate_alternative_plans
#   - _handle_estimate_confidence_interval
#   - _handle_recommend_strategy
#   - _handle_decompose_with_strategy
#   ... and 18 more

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
