"""Code-aware chunking strategies for semantic search."""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Code chunking strategies."""
    FUNCTION = "function"      # Chunk by function boundaries
    CLASS = "class"            # Chunk by class boundaries
    MODULE = "module"          # Chunk by module/file
    SYMBOL = "symbol"          # Chunk by symbol (function/class)
    FIXED_SIZE = "fixed_size"  # Fixed-size chunks with overlap
    SEMANTIC = "semantic"      # Semantic boundaries (imports, blocks)
    HYBRID = "hybrid"          # Combine multiple strategies


@dataclass
class Chunk:
    """Represents a chunk of code."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata."""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "language": self.language,
            "metadata": self.metadata,
        }


class CodeChunker:
    """Intelligent code chunking for semantic search."""

    def __init__(self, language: str = "python"):
        """
        Initialize code chunker.

        Args:
            language: Programming language
        """
        self.language = language
        self._init_delimiters()

    def _init_delimiters(self):
        """Initialize language-specific delimiters."""
        self.delimiters = {
            "python": {
                "function_start": "def ",
                "class_start": "class ",
                "import": "import ",
                "indent_level": 0,
            },
            "javascript": {
                "function_start": "function ",
                "arrow_function": "const ",
                "class_start": "class ",
                "import": "import ",
            },
            "typescript": {
                "function_start": "function ",
                "class_start": "class ",
                "interface_start": "interface ",
                "import": "import ",
            },
            "java": {
                "function_start": "public ",
                "class_start": "class ",
                "import": "import ",
            },
            "go": {
                "function_start": "func ",
                "struct_start": "type ",
                "import": "import",
            },
        }

    def chunk_by_function(
        self,
        code: str,
        file_path: str,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk code by function boundaries.

        Args:
            code: Source code
            file_path: File path
            language: Programming language

        Returns:
            List of chunks
        """
        chunks = []
        lines = code.split("\n")
        current_chunk_start = 0
        current_function = None
        indent_stack = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect function definition
            if stripped.startswith("def ") or stripped.startswith("function "):
                if current_function is not None:
                    # Save previous chunk
                    chunk_content = "\n".join(lines[current_chunk_start:i])
                    chunks.append(
                        Chunk(
                            content=chunk_content,
                            file_path=file_path,
                            start_line=current_chunk_start + 1,
                            end_line=i,
                            symbol_name=current_function,
                            symbol_type="function",
                            language=language or self.language,
                        )
                    )

                # Extract function name
                if stripped.startswith("def "):
                    current_function = stripped.split("(")[0].replace("def ", "").strip()
                else:
                    current_function = stripped.split("(")[0].replace("function ", "").strip()

                current_chunk_start = i
                indent_stack = [len(line) - len(line.lstrip())]

        # Add final chunk
        if current_function is not None:
            chunk_content = "\n".join(lines[current_chunk_start:])
            chunks.append(
                Chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=current_chunk_start + 1,
                    end_line=len(lines),
                    symbol_name=current_function,
                    symbol_type="function",
                    language=language or self.language,
                )
            )

        return chunks

    def chunk_by_class(
        self,
        code: str,
        file_path: str,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk code by class boundaries.

        Args:
            code: Source code
            file_path: File path
            language: Programming language

        Returns:
            List of chunks
        """
        chunks = []
        lines = code.split("\n")
        current_chunk_start = 0
        current_class = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect class definition
            if stripped.startswith("class "):
                if current_class is not None:
                    # Save previous chunk
                    chunk_content = "\n".join(lines[current_chunk_start:i])
                    chunks.append(
                        Chunk(
                            content=chunk_content,
                            file_path=file_path,
                            start_line=current_chunk_start + 1,
                            end_line=i,
                            symbol_name=current_class,
                            symbol_type="class",
                            language=language or self.language,
                        )
                    )

                # Extract class name
                current_class = stripped.split("(")[0].replace("class ", "").replace(":", "").strip()
                current_chunk_start = i

        # Add final chunk
        if current_class is not None:
            chunk_content = "\n".join(lines[current_chunk_start:])
            chunks.append(
                Chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=current_chunk_start + 1,
                    end_line=len(lines),
                    symbol_name=current_class,
                    symbol_type="class",
                    language=language or self.language,
                )
            )

        return chunks

    def chunk_by_module(
        self,
        code: str,
        file_path: str,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk code by module (entire file as one chunk).

        Args:
            code: Source code
            file_path: File path
            language: Programming language

        Returns:
            List with single chunk
        """
        lines = code.split("\n")
        return [
            Chunk(
                content=code,
                file_path=file_path,
                start_line=1,
                end_line=len(lines),
                symbol_type="module",
                language=language or self.language,
                metadata={"chunk_type": "module"},
            )
        ]

    def chunk_by_fixed_size(
        self,
        code: str,
        file_path: str,
        chunk_size: int = 50,
        overlap: int = 10,
        language: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Chunk code by fixed size with overlap.

        Args:
            code: Source code
            file_path: File path
            chunk_size: Lines per chunk
            overlap: Lines of overlap between chunks
            language: Programming language

        Returns:
            List of chunks
        """
        chunks = []
        lines = code.split("\n")
        start = 0

        while start < len(lines):
            end = min(start + chunk_size, len(lines))
            chunk_content = "\n".join(lines[start:end])

            chunks.append(
                Chunk(
                    content=chunk_content,
                    file_path=file_path,
                    start_line=start + 1,
                    end_line=end,
                    symbol_type="fixed_size",
                    language=language or self.language,
                    metadata={
                        "chunk_type": "fixed_size",
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                    },
                )
            )

            start += chunk_size - overlap

        return chunks

    def chunk(
        self,
        code: str,
        file_path: str,
        strategy: ChunkingStrategy = ChunkingStrategy.FUNCTION,
        language: Optional[str] = None,
        **kwargs,
    ) -> List[Chunk]:
        """
        Chunk code using specified strategy.

        Args:
            code: Source code
            file_path: File path
            strategy: Chunking strategy to use
            language: Programming language
            **kwargs: Strategy-specific arguments

        Returns:
            List of chunks
        """
        if strategy == ChunkingStrategy.FUNCTION:
            return self.chunk_by_function(code, file_path, language)
        elif strategy == ChunkingStrategy.CLASS:
            return self.chunk_by_class(code, file_path, language)
        elif strategy == ChunkingStrategy.MODULE:
            return self.chunk_by_module(code, file_path, language)
        elif strategy == ChunkingStrategy.FIXED_SIZE:
            return self.chunk_by_fixed_size(
                code,
                file_path,
                chunk_size=kwargs.get("chunk_size", 50),
                overlap=kwargs.get("overlap", 10),
                language=language,
            )
        elif strategy == ChunkingStrategy.HYBRID:
            # Combine function and class chunking
            functions = self.chunk_by_function(code, file_path, language)
            classes = self.chunk_by_class(code, file_path, language)
            return sorted(
                functions + classes,
                key=lambda x: x.start_line,
            )
        else:
            # Default to function chunking
            return self.chunk_by_function(code, file_path, language)

    def suggest_strategy(self, code: str, query: str) -> ChunkingStrategy:
        """
        Suggest optimal chunking strategy based on code and query.

        Args:
            code: Source code
            query: Search query

        Returns:
            Recommended chunking strategy
        """
        # If query mentions specific function/class, use function chunking
        if "function" in query.lower() or "def " in query:
            return ChunkingStrategy.FUNCTION

        # If query mentions class structure
        if "class" in query.lower():
            return ChunkingStrategy.CLASS

        # If code has many large functions, use hybrid
        function_count = code.count("def ")
        if function_count > 10:
            return ChunkingStrategy.HYBRID

        # Default to function chunking
        return ChunkingStrategy.FUNCTION
