"""Data models for code analysis and search."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CodeElementType(str, Enum):
    """Types of code elements."""

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    IMPORT = "import"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE_ANNOTATION = "type_annotation"
    DECORATOR = "decorator"
    DOCSTRING = "docstring"


class CodeLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"


class CodeElement(BaseModel):
    """Represents a code element (function, class, import, etc.)."""

    element_id: str = Field(..., description="Unique identifier for the code element")
    file_path: str = Field(..., description="Relative path to source file")
    language: CodeLanguage = Field(..., description="Programming language")
    element_type: CodeElementType = Field(..., description="Type of code element")
    name: str = Field(..., description="Name of the element (function name, class name, etc.)")
    docstring: Optional[str] = Field(None, description="Docstring or documentation")
    source_code: str = Field(..., description="Full source code of the element")
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    parent_element: Optional[str] = Field(
        None, description="Parent element ID (for nested elements)"
    )
    imports: List[str] = Field(default_factory=list, description="List of imported modules/names")
    references: List[str] = Field(default_factory=list, description="References to other elements")
    signature: Optional[str] = Field(None, description="Function/method signature")
    return_type: Optional[str] = Field(None, description="Return type annotation")
    parameters: Optional[List[dict]] = Field(None, description="Parameters with types")
    decorators: List[str] = Field(default_factory=list, description="Decorators applied")
    is_exported: bool = Field(default=False, description="Whether this is exported/public")
    complexity: Optional[float] = Field(None, description="Cyclomatic complexity score")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    embedding_model: Optional[str] = Field(None, description="Model used for embedding")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CodeSearchResult(BaseModel):
    """Represents a code search result."""

    element: CodeElement = Field(..., description="Matched code element")
    semantic_score: float = Field(..., description="Semantic similarity score (0-1)")
    ast_score: float = Field(..., description="AST pattern match score (0-1)")
    spatial_score: float = Field(..., description="Spatial proximity score (0-1)")
    combined_score: float = Field(..., description="Combined ranking score (0-1)")
    rank: int = Field(..., description="Rank in search results")
    context: Optional[dict] = Field(None, description="Additional context")
    reasoning: Optional[str] = Field(None, description="Explanation of scoring")

    class Config:
        """Pydantic config."""

        use_enum_values = True


class CodeIndex(BaseModel):
    """Represents the code index structure."""

    project_id: str = Field(..., description="Project identifier")
    root_path: str = Field(..., description="Root directory of indexed code")
    language: CodeLanguage = Field(..., description="Primary language")
    total_files: int = Field(default=0, description="Total files indexed")
    total_elements: int = Field(default=0, description="Total code elements")
    last_indexed: datetime = Field(default_factory=datetime.now)
    index_version: str = Field(default="1.0", description="Index format version")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class CodeQuery(BaseModel):
    """Represents a code search query."""

    query_text: str = Field(..., description="Natural language search query")
    language: Optional[CodeLanguage] = Field(None, description="Filter by language")
    element_type: Optional[CodeElementType] = Field(None, description="Filter by element type")
    file_pattern: Optional[str] = Field(None, description="File path glob pattern")
    max_results: int = Field(default=10, description="Maximum results to return")
    min_score: float = Field(default=0.3, description="Minimum score threshold")
    explain: bool = Field(default=False, description="Include scoring explanation")
    search_context: Optional[str] = Field(None, description="Additional context for search")
