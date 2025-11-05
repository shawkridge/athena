"""
Athena Symbols Module

Symbol-level code analysis for Athena. This module provides:
- Symbol extraction from source code
- Symbol metrics computation
- Relationship tracking between symbols
- Integration with Phase 4 procedural learning

Key Components:
- symbol_models: Core data structures
- symbol_parser: Language-specific parsing (Python, JavaScript, TypeScript)
- symbol_store: Database persistence (Phase 1B)
- symbol_analyzer: Metrics and analysis (Phase 1B)
"""

from athena.symbols.symbol_models import (
    SymbolType,
    RelationType,
    SymbolMetrics,
    SymbolDependency,
    Symbol,
    SymbolAnalysisResult,
    SymbolMap,
    DependencyGraph,
    create_symbol,
)

from athena.symbols.symbol_parser import (
    SymbolParser,
    LanguageDetector,
    PythonSymbolParser,
    JavaScriptSymbolParser,
)

from athena.symbols.symbol_store import SymbolStore
from athena.symbols.symbol_analyzer import SymbolAnalyzer, ComplexityAnalysis
from athena.symbols.symbol_tools import SymbolTools
from athena.symbols.symbol_pattern_integration import SymbolPatternLinker, PatternApplication

__all__ = [
    # Models
    "SymbolType",
    "RelationType",
    "SymbolMetrics",
    "SymbolDependency",
    "Symbol",
    "SymbolAnalysisResult",
    "SymbolMap",
    "DependencyGraph",
    "create_symbol",
    # Parser
    "SymbolParser",
    "LanguageDetector",
    "PythonSymbolParser",
    "JavaScriptSymbolParser",
    # Store
    "SymbolStore",
    # Analyzer
    "SymbolAnalyzer",
    "ComplexityAnalysis",
    # Tools & Integration
    "SymbolTools",
    "SymbolPatternLinker",
    "PatternApplication",
]
