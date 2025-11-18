"""
Architecture layer filesystem API.

Provides local execution of architecture operations with summary-first results.

Available operations:
- adr: ADR management (create, list, get details, get context)
- patterns: Design pattern library (add, search, record usage)
- constraints: Architectural constraints (add, verify, check blockers)
"""

from .adr import (
    create_adr,
    list_adrs,
    get_adr_details,
    get_arch_context,
)

__all__ = [
    "create_adr",
    "list_adrs",
    "get_adr_details",
    "get_arch_context",
]
