"""Metacognition handlers - quality, learning, gaps, expertise.

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

# 8 handler methods in this domain:
#   - _handle_get_expertise
#   - _handle_evaluate_memory_quality
#   - _handle_get_learning_rates
#   - _handle_detect_knowledge_gaps
#   - _handle_get_self_reflection
#   - _handle_check_cognitive_load
#   - _handle_get_metacognition_insights
#   - _handle_get_memory_quality_summary

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
