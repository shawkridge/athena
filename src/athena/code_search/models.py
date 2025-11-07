"""Data models for Tree-Sitter code search."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CodeUnit:
    """Semantic unit of code (function, class, import, etc.)."""

    id: str  # "file:line:name"
    type: str  # "function", "class", "method", "import"
    name: str  # function/class name
    signature: str  # Full signature (first line of definition)
    code: str  # Full source code
    file_path: str  # /path/to/file.py
    start_line: int  # Starting line number
    end_line: int  # Ending line number
    docstring: str = ""  # Function/class documentation
    dependencies: List[str] = field(default_factory=list)  # Other units it uses
    embedding: Optional[List[float]] = None  # Semantic embedding

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "signature": self.signature,
            "code": self.code[:500],  # Limit code length in output
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "dependencies": self.dependencies,
            "lines_of_code": self.end_line - self.start_line + 1,
        }


@dataclass
class SearchResult:
    """A code search result match."""

    unit: CodeUnit  # The matched code unit
    relevance: float  # 0-1, how relevant (similarity score)
    context: str  # Why was it matched? (e.g., "semantic_match")
    matches: List[str] = field(default_factory=list)  # Which fields matched

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.unit.file_path,
            "start_line": self.unit.start_line,
            "end_line": self.unit.end_line,
            "type": self.unit.type,
            "name": self.unit.name,
            "signature": self.unit.signature,
            "code": self.unit.code[:500],
            "relevance": round(self.relevance, 3),
            "docstring": self.unit.docstring,
            "context": self.context,
            "matches": self.matches,
        }


@dataclass
class SearchQuery:
    """Parsed user search query."""

    original: str  # User's original question
    intent: str  # Parsed intent ("find auth code")
    embedding: Optional[List[float]] = None  # Query embedding
    structural_patterns: List[str] = field(default_factory=list)  # AST patterns to search

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "original": self.original,
            "intent": self.intent,
            "structural_patterns": self.structural_patterns,
        }
