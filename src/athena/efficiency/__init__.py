"""Efficiency and optimization modules for context management.

This package provides tools for reducing token usage and API costs:
- Gisting: Pre-computed document summaries with prompt caching
- Compression: Token budget optimization
- Caching: Smart caching strategies
"""

from .gisting import GistManager, GistCacheEntry, CacheMetrics, create_gist_manager

__all__ = [
    "GistManager",
    "GistCacheEntry",
    "CacheMetrics",
    "create_gist_manager",
]
