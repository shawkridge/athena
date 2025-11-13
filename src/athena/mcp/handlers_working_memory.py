"""Working memory handlers - 7+/-2 cognitive limit operations.

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

# 11 handler methods in this domain:
#   - _handle_get_working_memory
#   - _handle_update_working_memory
#   - _handle_clear_working_memory
#   - _handle_consolidate_working_memory
#   - _handle_get_associations
#   - _handle_strengthen_association
#   - _handle_find_memory_path
#   - _handle_get_attention_state
#   - _handle_set_attention_focus
#   - _handle_auto_focus_top_memories
#   - _handle_get_active_buffer

# All methods are accessed via: server.METHODNAME(args)
# where server is a MemoryMCPServer instance
