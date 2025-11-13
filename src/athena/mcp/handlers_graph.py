"""Knowledge graph handlers - entities, relations, observations.

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

# 12 handler methods in this domain:
#   - _handle_create_entity
#   - _handle_create_relation
#   - _handle_add_observation
#   - _handle_search_graph
#   - _handle_search_graph_with_depth
#   - _handle_get_graph_metrics
#   - _handle_analyze_coverage
#   - _handle_analyze_graph_metrics
#   - _handle_detect_graph_communities
#   - _handle_get_community_details
#   - _handle_analyze_community_connectivity
#   - _handle_expand_knowledge_relations

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
