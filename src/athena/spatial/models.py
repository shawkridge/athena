"""Spatial hierarchy models for location-aware episodic memory.

Implements cognitive mapping inspired by hippocampal place cells.
Based on EM-LLM (arXiv:43943928) spatial-temporal grounding.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SpatialNode:
    """A node in the spatial hierarchy (file path component or code symbol)."""

    name: str  # e.g., "src", "auth", "middleware" or "authenticate", "validate"
    full_path: (
        str  # e.g., "/project/src/auth/middleware" or "/project/src/auth/middleware:authenticate"
    )
    depth: int  # Distance from root (0 = root)
    parent_path: Optional[str] = None  # Parent node's full_path
    node_type: str = "directory"  # "directory", "file", "module", "class", "function", "method"
    language: Optional[str] = (
        None  # Programming language (python, typescript, etc) for code symbols
    )
    symbol_kind: Optional[str] = None  # "function", "class", "method", "interface", "type" for code

    def __post_init__(self):
        """Validate spatial node."""
        if self.depth < 0:
            raise ValueError(f"Depth must be >= 0, got {self.depth}")
        if self.depth > 0 and not self.parent_path:
            raise ValueError("Non-root node must have parent_path")

        # Symbol nodes require language
        if self.node_type in ["function", "class", "method"] and not self.language:
            raise ValueError(f"{self.node_type} node requires language field")

        # Validate node_type
        valid_types = {
            "directory",
            "file",
            "module",
            "class",
            "function",
            "method",
            "interface",
            "type",
        }
        if self.node_type not in valid_types:
            raise ValueError(f"Invalid node_type: {self.node_type}. Must be one of {valid_types}")


@dataclass
class SpatialRelation:
    """Relationship between spatial nodes."""

    from_path: str  # Parent/sibling path
    to_path: str  # Child/sibling path
    relation_type: str  # "contains", "sibling", "ancestor_of"
    strength: float = 1.0  # Relationship strength (0.0-1.0)

    def __post_init__(self):
        """Validate relation."""
        if self.relation_type not in ["contains", "sibling", "ancestor_of"]:
            raise ValueError(f"Invalid relation_type: {self.relation_type}")
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"Strength must be in [0.0, 1.0], got {self.strength}")


@dataclass
class SymbolNode:
    """A code symbol node (function, class, method) in spatial hierarchy."""

    name: str  # Function/class name (e.g., "authenticate", "JWTHandler")
    file_path: str  # Absolute file path
    line_number: int  # Line where symbol is defined
    symbol_kind: str  # "function", "class", "method", "interface", "type"
    language: str  # Programming language
    full_path: str  # e.g., "/path/to/file.py:authenticate"
    parent_class: Optional[str] = None  # Parent class name for methods
    signature: Optional[str] = None  # Function/method signature
    docstring: Optional[str] = None  # Documentation string
    complexity_score: Optional[float] = None  # Cyclomatic complexity

    def __post_init__(self):
        """Validate symbol node."""
        if self.line_number < 1:
            raise ValueError(f"Line number must be >= 1, got {self.line_number}")
        if self.complexity_score is not None and not (0.0 <= self.complexity_score <= 100.0):
            raise ValueError(
                f"Complexity score must be in [0.0, 100.0], got {self.complexity_score}"
            )
        valid_kinds = {"function", "class", "method", "interface", "type", "enum", "struct"}
        if self.symbol_kind not in valid_kinds:
            raise ValueError(f"Invalid symbol_kind: {self.symbol_kind}")


@dataclass
class SpatialQuery:
    """Query structure for spatial-aware retrieval."""

    query_text: str
    spatial_context: Optional[str] = None  # File path or symbol path to center search
    max_spatial_depth: int = 2  # How far to traverse spatially
    semantic_k: int = 5  # Number of semantic results to return
    symbol_filter: Optional[str] = None  # Filter by symbol kind (function, class, method)
    language_filter: Optional[str] = None  # Filter by language (python, typescript, etc)

    def __post_init__(self):
        """Validate query parameters."""
        if self.max_spatial_depth < 0:
            raise ValueError("max_spatial_depth must be >= 0")
        if self.semantic_k < 1:
            raise ValueError("semantic_k must be >= 1")
        if self.symbol_filter and self.symbol_filter not in {
            "function",
            "class",
            "method",
            "interface",
            "type",
        }:
            raise ValueError(f"Invalid symbol_filter: {self.symbol_filter}")


@dataclass
class SpatialQueryResult:
    """Result from spatial-aware query."""

    event_id: int
    content: str
    spatial_path: str
    spatial_distance: int  # Hops from query spatial_context
    semantic_score: float  # Similarity to query_text
    timestamp: datetime
    combined_score: float  # Weighted combination of spatial + semantic

    def __lt__(self, other):
        """Sort by combined score descending."""
        return self.combined_score > other.combined_score
