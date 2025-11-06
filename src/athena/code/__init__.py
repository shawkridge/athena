"""Code analysis and semantic code search module.

This module provides intelligent code search and analysis capabilities:
- AST-based code parsing (functions, classes, imports, docstrings)
- Semantic code indexing with embeddings
- Hybrid search combining structural + semantic + spatial ranking
- Code context extraction (relationships, history, dependencies)
"""

from .models import CodeElement, CodeSearchResult
from .parser import CodeParser
from .search import CodeSearchEngine

__all__ = [
    "CodeElement",
    "CodeSearchResult",
    "CodeParser",
    "CodeSearchEngine",
]
