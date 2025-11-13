"""Research handlers - research tasks and findings.

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

# 2 handler methods in this domain:
#   - _handle_research_task
#   - _handle_research_findings

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
