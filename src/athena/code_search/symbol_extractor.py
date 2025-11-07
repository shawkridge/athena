"""Symbol extraction and indexing for code search."""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SymbolType(Enum):
    """Types of code symbols."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    CONSTANT = "constant"
    DECORATOR = "decorator"
    INTERFACE = "interface"
    ENUM = "enum"
    TYPE_ALIAS = "type_alias"


@dataclass
class Symbol:
    """Represents a code symbol (function, class, variable, etc.)."""
    name: str
    type: SymbolType
    file_path: str
    line_number: int
    column_number: int = 0
    docstring: Optional[str] = None
    signature: Optional[str] = None
    complexity: int = 1
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "docstring": self.docstring,
            "signature": self.signature,
            "complexity": self.complexity,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


class SymbolExtractor:
    """Extracts symbols from code using AST parsing."""

    def __init__(self, language: str = "python"):
        """
        Initialize symbol extractor.

        Args:
            language: Programming language (python, javascript, typescript, go, java)
        """
        self.language = language
        self._init_language_patterns()

    def _init_language_patterns(self):
        """Initialize language-specific patterns."""
        self.patterns = {
            "python": {
                "function": r"^\s*def\s+(\w+)\s*\(",
                "class": r"^\s*class\s+(\w+)",
                "decorator": r"^\s*@(\w+)",
                "import": r"^\s*(from|import)\s+",
                "constant": r"^\s*([A-Z_]+)\s*=",
            },
            "javascript": {
                "function": r"^\s*(async\s+)?function\s+(\w+)\s*\(",
                "class": r"^\s*class\s+(\w+)",
                "arrow_function": r"^\s*const\s+(\w+)\s*=\s*(async\s+)?\(",
                "import": r"^\s*(import|require)",
            },
            "typescript": {
                "function": r"^\s*(async\s+)?function\s+(\w+)\s*\(",
                "class": r"^\s*class\s+(\w+)",
                "interface": r"^\s*interface\s+(\w+)",
                "type": r"^\s*type\s+(\w+)\s*=",
            },
            "go": {
                "function": r"^\s*func\s+(\w+)\s*\(",
                "struct": r"^\s*type\s+(\w+)\s+struct",
                "interface": r"^\s*type\s+(\w+)\s+interface",
            },
            "java": {
                "function": r"^\s*public\s+\w+\s+(\w+)\s*\(",
                "class": r"^\s*public\s+class\s+(\w+)",
                "interface": r"^\s*public\s+interface\s+(\w+)",
            },
        }

    def extract_symbols(
        self,
        code: str,
        file_path: str,
        calculate_complexity: bool = True,
    ) -> List[Symbol]:
        """
        Extract all symbols from code.

        Args:
            code: Source code string
            file_path: Path to the file
            calculate_complexity: Whether to calculate complexity

        Returns:
            List of extracted symbols
        """
        symbols = []
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Try to match different symbol types
            symbol = self._match_line(line, line_num, file_path)
            if symbol:
                symbols.append(symbol)

        return symbols

    def _match_line(
        self,
        line: str,
        line_num: int,
        file_path: str,
    ) -> Optional[Symbol]:
        """Try to match a symbol on a line."""
        import re

        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            return None

        patterns = self.patterns.get(self.language, {})

        # Check for function
        if "function" in patterns:
            match = re.search(patterns["function"], line)
            if match:
                name = match.group(1) if match.lastindex == 1 else match.group(2)
                return Symbol(
                    name=name,
                    type=SymbolType.FUNCTION,
                    file_path=file_path,
                    line_number=line_num,
                    signature=line.strip(),
                )

        # Check for class
        if "class" in patterns:
            match = re.search(patterns["class"], line)
            if match:
                name = match.group(1)
                return Symbol(
                    name=name,
                    type=SymbolType.CLASS,
                    file_path=file_path,
                    line_number=line_num,
                    signature=line.strip(),
                )

        # Check for interface (TypeScript/Java/Go)
        if "interface" in patterns:
            match = re.search(patterns["interface"], line)
            if match:
                name = match.group(1)
                return Symbol(
                    name=name,
                    type=SymbolType.INTERFACE,
                    file_path=file_path,
                    line_number=line_num,
                    signature=line.strip(),
                )

        # Check for imports
        if "import" in patterns:
            match = re.search(patterns["import"], line)
            if match:
                return Symbol(
                    name=line.strip()[:50],  # First 50 chars as name
                    type=SymbolType.IMPORT,
                    file_path=file_path,
                    line_number=line_num,
                    signature=line.strip(),
                )

        # Check for constants
        if "constant" in patterns:
            match = re.search(patterns["constant"], line)
            if match:
                name = match.group(1)
                return Symbol(
                    name=name,
                    type=SymbolType.CONSTANT,
                    file_path=file_path,
                    line_number=line_num,
                    signature=line.strip(),
                )

        return None

    def extract_by_type(
        self,
        code: str,
        file_path: str,
        symbol_type: SymbolType,
    ) -> List[Symbol]:
        """Extract symbols of a specific type."""
        all_symbols = self.extract_symbols(code, file_path)
        return [s for s in all_symbols if s.type == symbol_type]

    def calculate_symbol_complexity(self, symbol: Symbol, code: str) -> int:
        """
        Calculate complexity of a symbol.

        Args:
            symbol: Symbol to analyze
            code: Full source code

        Returns:
            Complexity score (1-10)
        """
        if symbol.type == SymbolType.FUNCTION:
            # Count branching statements
            branching_keywords = ["if", "elif", "else", "for", "while", "try", "except"]
            complexity = 1

            # Get symbol's code block (simplified)
            lines = code.split("\n")
            for i in range(symbol.line_number, min(symbol.line_number + 100, len(lines))):
                line = lines[i]
                for keyword in branching_keywords:
                    if keyword in line.lower():
                        complexity += 1

            return min(complexity, 10)

        return 1


class SymbolIndex:
    """Index for efficient symbol lookup."""

    def __init__(self):
        """Initialize symbol index."""
        self.symbols: List[Symbol] = []
        self.by_name: Dict[str, List[Symbol]] = {}
        self.by_type: Dict[SymbolType, List[Symbol]] = {}
        self.by_file: Dict[str, List[Symbol]] = {}

    def add_symbol(self, symbol: Symbol):
        """Add symbol to index."""
        self.symbols.append(symbol)

        # Index by name
        if symbol.name not in self.by_name:
            self.by_name[symbol.name] = []
        self.by_name[symbol.name].append(symbol)

        # Index by type
        if symbol.type not in self.by_type:
            self.by_type[symbol.type] = []
        self.by_type[symbol.type].append(symbol)

        # Index by file
        if symbol.file_path not in self.by_file:
            self.by_file[symbol.file_path] = []
        self.by_file[symbol.file_path].append(symbol)

    def add_symbols(self, symbols: List[Symbol]):
        """Add multiple symbols to index."""
        for symbol in symbols:
            self.add_symbol(symbol)

    def find_by_name(self, name: str, exact: bool = True) -> List[Symbol]:
        """Find symbols by name."""
        if exact:
            return self.by_name.get(name, [])
        else:
            # Partial match
            results = []
            for sym_name, symbols in self.by_name.items():
                if name.lower() in sym_name.lower():
                    results.extend(symbols)
            return results

    def find_by_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Find symbols by type."""
        return self.by_type.get(symbol_type, [])

    def find_by_file(self, file_path: str) -> List[Symbol]:
        """Find symbols in a file."""
        return self.by_file.get(file_path, [])

    def find_in_range(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> List[Symbol]:
        """Find symbols in a line range."""
        return [
            s for s in self.by_file.get(file_path, [])
            if start_line <= s.line_number <= end_line
        ]

    def search(self, query: str) -> List[Symbol]:
        """Search symbols (name + type + docstring)."""
        results = []
        query_lower = query.lower()

        for symbol in self.symbols:
            match = (
                query_lower in symbol.name.lower()
                or (symbol.docstring and query_lower in symbol.docstring.lower())
                or query_lower in symbol.type.value.lower()
            )
            if match:
                results.append(symbol)

        return results

    def get_all(self) -> List[Symbol]:
        """Get all symbols."""
        return self.symbols.copy()

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_symbols": len(self.symbols),
            "by_type": {
                sym_type.value: len(symbols)
                for sym_type, symbols in self.by_type.items()
            },
            "by_file": {
                file: len(symbols)
                for file, symbols in self.by_file.items()
            },
            "avg_complexity": (
                sum(s.complexity for s in self.symbols) / len(self.symbols)
                if self.symbols else 0
            ),
        }
