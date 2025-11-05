"""
Symbol Analysis Data Models

Defines the core data structures for symbol-level code analysis in Athena.
Symbols represent identifiable code entities (functions, classes, methods, imports, etc.)
with metadata, metrics, and relationships.

Author: Claude Code
Date: 2025-10-31
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# ENUMS: Symbol Types and Relationships
# ============================================================================

class SymbolType(str, Enum):
    """Classification of different code symbol types."""

    FUNCTION = "function"                  # Standalone function
    CLASS = "class"                        # Class definition
    METHOD = "method"                      # Class method
    PROPERTY = "property"                  # Property/attribute
    INTERFACE = "interface"                # Interface/protocol
    MODULE = "module"                      # File or module
    IMPORT = "import"                      # External dependency
    CONSTANT = "constant"                  # Global constant
    ENUM = "enum"                          # Enumeration type
    ASYNC_FUNCTION = "async_function"      # Async function
    GENERATOR = "generator"                # Generator function
    LAMBDA = "lambda"                      # Anonymous function
    DATACLASS = "dataclass"                # Python dataclass
    PROTOCOL = "protocol"                  # Protocol/interface definition


class RelationType(str, Enum):
    """Types of relationships between symbols."""

    CALLS = "calls"                        # Function A calls Function B
    INHERITS_FROM = "inherits_from"        # Class A extends Class B
    IMPLEMENTS = "implements"              # Class implements Interface
    IMPORTS = "imports"                    # Module imports Symbol
    DEPENDS_ON = "depends_on"              # General dependency
    REFERENCES = "references"              # Type or value reference
    OVERRIDES = "overrides"                # Method overrides parent method
    IS_MEMBER_OF = "is_member_of"          # Method belongs to class


# ============================================================================
# DATACLASSES: Symbol Metrics and Properties
# ============================================================================

@dataclass
class SymbolMetrics:
    """
    Complexity and quality metrics for a symbol.

    Attributes:
        lines_of_code: Actual code lines (excluding comments/blanks)
        cyclomatic_complexity: Number of independent paths through code
        cognitive_complexity: Measure of readability difficulty
        parameters: Number of function/method parameters
        nesting_depth: Maximum nesting depth in the symbol
        maintainability_index: 0-100 quality score (higher is better)
    """

    lines_of_code: int = 0
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    parameters: int = 0
    nesting_depth: int = 0
    maintainability_index: float = 100.0

    def __post_init__(self):
        """Validate metric values."""
        if self.lines_of_code < 0:
            raise ValueError("lines_of_code must be non-negative")
        if self.cyclomatic_complexity < 1:
            raise ValueError("cyclomatic_complexity must be >= 1")
        if self.cognitive_complexity < 0:
            raise ValueError("cognitive_complexity must be non-negative")
        if self.parameters < 0:
            raise ValueError("parameters must be non-negative")
        if self.nesting_depth < 0:
            raise ValueError("nesting_depth must be non-negative")
        if not (0.0 <= self.maintainability_index <= 100.0):
            raise ValueError("maintainability_index must be between 0 and 100")


@dataclass
class SymbolDependency:
    """
    Represents a dependency relationship between symbols.

    Attributes:
        target_symbol_name: Full qualified name of the target symbol
        relation_type: Type of relationship (calls, imports, etc.)
        strength: Strength of dependency (0.0-1.0)
        location: Line number where dependency occurs (if applicable)
    """

    target_symbol_name: str
    relation_type: RelationType
    strength: float = 1.0
    location: Optional[int] = None

    def __post_init__(self):
        """Validate dependency values."""
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError("strength must be between 0.0 and 1.0")
        if self.location is not None and self.location < 1:
            raise ValueError("location (line number) must be >= 1")


@dataclass
class Symbol:
    """
    Represents a code symbol with full metadata.

    A symbol is an identifiable code entity like a function, class, method, etc.
    This class captures comprehensive information about the symbol for analysis
    and pattern matching.

    Attributes:
        id: Unique database identifier (assigned by store)
        file_path: Path to source file
        symbol_type: Type of symbol (function, class, etc.)
        name: Simple name (e.g., "encode", "JWTHandler")
        namespace: Hierarchical namespace (e.g., "auth.jwt")
        full_qualified_name: Complete identifier (e.g., "auth.jwt.JWTHandler.encode")
        signature: Function/method signature with parameters and return type
        line_start: Starting line number in source file
        line_end: Ending line number in source file
        code: Source code of the symbol
        docstring: Documentation string (if present)
        metrics: Complexity and quality metrics
        dependencies: Symbols this one depends on
        dependents: Symbols that depend on this one
        language: Programming language (python, javascript, typescript, etc.)
        visibility: Public, protected, private
        is_async: Whether symbol is async
        is_deprecated: Whether symbol is marked as deprecated
        created_at: Unix timestamp of creation
        last_modified: Unix timestamp of last modification
        change_frequency: How many times this symbol has been modified
        quality_issues: Count of code quality issues
        additional_metadata: Flexible metadata for extensions
    """

    file_path: str
    symbol_type: SymbolType
    name: str
    namespace: str
    full_qualified_name: str
    signature: str
    line_start: int
    line_end: int
    code: str
    docstring: str
    metrics: SymbolMetrics
    language: str = "python"
    visibility: str = "public"
    is_async: bool = False
    is_deprecated: bool = False
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    last_modified: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    id: Optional[int] = None
    change_frequency: int = 0
    quality_issues: int = 0
    dependencies: List[SymbolDependency] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    additional_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate symbol values."""
        if self.line_start < 1 or self.line_end < 1:
            raise ValueError("line_start and line_end must be >= 1")
        if self.line_end < self.line_start:
            raise ValueError("line_end must be >= line_start")
        if self.visibility not in ("public", "protected", "private"):
            raise ValueError("visibility must be 'public', 'protected', or 'private'")
        if self.change_frequency < 0:
            raise ValueError("change_frequency must be non-negative")
        if self.quality_issues < 0:
            raise ValueError("quality_issues must be non-negative")

    def get_lines_count(self) -> int:
        """Return number of lines this symbol spans."""
        return self.line_end - self.line_start + 1

    def is_complex(self) -> bool:
        """Return True if symbol has high complexity (cyclomatic > 10)."""
        return self.metrics.cyclomatic_complexity > 10

    def is_large(self) -> bool:
        """Return True if symbol is large (>100 LOC)."""
        return self.metrics.lines_of_code > 100

    def is_poorly_maintained(self) -> bool:
        """Return True if maintainability index is low (<50)."""
        return self.metrics.maintainability_index < 50


@dataclass
class SymbolAnalysisResult:
    """
    Result of analyzing a file for symbols.

    Attributes:
        file_path: Path to analyzed file
        language: Detected programming language
        symbols: List of extracted symbols
        parse_errors: Any errors encountered during parsing
        total_lines: Total lines in file
        analysis_time_ms: Time taken to analyze (milliseconds)
        success: Whether analysis completed successfully
    """

    file_path: str
    language: str
    symbols: List[Symbol]
    parse_errors: List[str] = field(default_factory=list)
    total_lines: int = 0
    analysis_time_ms: float = 0.0
    success: bool = True

    def get_symbol_count(self) -> int:
        """Return total number of symbols found."""
        return len(self.symbols)

    def get_error_count(self) -> int:
        """Return number of parse errors."""
        return len(self.parse_errors)

    def get_symbols_by_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Return symbols filtered by type."""
        return [s for s in self.symbols if s.symbol_type == symbol_type]

    def get_complexity_summary(self) -> Dict[str, Any]:
        """Return summary of complexity metrics."""
        if not self.symbols:
            return {
                "total_symbols": 0,
                "avg_cyclomatic": 0,
                "max_cyclomatic": 0,
                "complex_symbols": 0
            }

        cyclomatic_values = [s.metrics.cyclomatic_complexity for s in self.symbols]
        complex_count = sum(1 for s in self.symbols if s.is_complex())

        return {
            "total_symbols": len(self.symbols),
            "avg_cyclomatic": sum(cyclomatic_values) / len(self.symbols),
            "max_cyclomatic": max(cyclomatic_values),
            "complex_symbols": complex_count
        }


# ============================================================================
# TYPE ALIASES
# ============================================================================

SymbolMap = Dict[str, Symbol]  # Mapping of full qualified names to symbols
DependencyGraph = Dict[str, List[str]]  # Mapping of symbol names to dependent names


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_symbol(
    file_path: str,
    symbol_type: SymbolType,
    name: str,
    namespace: str,
    signature: str,
    line_start: int,
    line_end: int,
    code: str,
    docstring: str = "",
    language: str = "python",
    **kwargs
) -> Symbol:
    """
    Factory function to create a Symbol with validated inputs.

    Args:
        file_path: Path to source file
        symbol_type: Type of symbol
        name: Simple name
        namespace: Namespace path
        signature: Function/method signature
        line_start: Starting line
        line_end: Ending line
        code: Source code
        docstring: Documentation string
        language: Programming language
        **kwargs: Additional arguments for Symbol

    Returns:
        Validated Symbol instance

    Raises:
        ValueError: If inputs are invalid
    """
    full_qualified_name = f"{namespace}.{name}" if namespace else name
    metrics = kwargs.pop("metrics", SymbolMetrics())

    return Symbol(
        file_path=file_path,
        symbol_type=symbol_type,
        name=name,
        namespace=namespace,
        full_qualified_name=full_qualified_name,
        signature=signature,
        line_start=line_start,
        line_end=line_end,
        code=code,
        docstring=docstring,
        metrics=metrics,
        language=language,
        **kwargs
    )


__all__ = [
    "SymbolType",
    "RelationType",
    "SymbolMetrics",
    "SymbolDependency",
    "Symbol",
    "SymbolAnalysisResult",
    "SymbolMap",
    "DependencyGraph",
    "create_symbol",
]
