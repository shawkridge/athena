"""Code analysis and semantic code search module.

This module provides intelligent code search and analysis capabilities:
- AST-based code parsing (functions, classes, imports, docstrings)
- Semantic code indexing with embeddings
- Hybrid search combining structural + semantic + spatial ranking
- Code context extraction (relationships, history, dependencies)
- Git-aware context management for prioritizing changed files
"""

from .models import CodeElement, CodeSearchResult
from .parser import CodeParser
from .search import CodeSearchEngine
from .git_context import GitContext, FileChange, FileDiff
from .git_analyzer import GitAwareAnalyzer, create_git_aware_analyzer
from .enhanced_parser import EnhancedCodeParser, create_enhanced_parser

__all__ = [
    "CodeElement",
    "CodeSearchResult",
    "CodeParser",
    "CodeSearchEngine",
    "GitContext",
    "FileChange",
    "FileDiff",
    "GitAwareAnalyzer",
    "create_git_aware_analyzer",
    "EnhancedCodeParser",
    "create_enhanced_parser",
]
