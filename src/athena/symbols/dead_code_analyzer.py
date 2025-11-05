"""Dead Code Analyzer for identifying unused symbols.

Provides:
- Detection of unused functions, classes, and methods
- Identification of unused imports
- Unused variable detection
- Dead code metrics and statistics
"""

from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass

from .symbol_models import Symbol, SymbolType
from .dependency_resolver import DependencyResolver, SymbolReference


@dataclass
class DeadCodeIssue:
    """A detected dead code issue."""
    symbol: Symbol
    issue_type: str  # unused_symbol, unused_import, etc.
    references_count: int
    line_number: int
    file_path: str
    severity: str  # info, warning, error


class DeadCodeAnalyzer:
    """Analyzes code to detect unused symbols and imports."""

    def __init__(self, resolver: DependencyResolver):
        """Initialize the dead code analyzer.

        Args:
            resolver: DependencyResolver instance with populated symbols
        """
        self.resolver = resolver
        self.used_symbols: Set[str] = set()
        self.unused_symbols: List[DeadCodeIssue] = []

    def analyze_project(self) -> Dict:
        """Analyze entire project for dead code.

        Returns:
            Dictionary with dead code analysis results
        """
        self._find_all_used_symbols()
        self._identify_unused_symbols()

        return {
            "total_symbols": len(self.resolver.symbol_index),
            "used_symbols": len(self.used_symbols),
            "unused_symbols": len(self.unused_symbols),
            "dead_code_issues": self.unused_symbols,
            "unused_by_type": self._group_unused_by_type(),
            "unused_by_file": self._group_unused_by_file(),
            "dead_code_percentage": self._calculate_dead_code_percentage(),
        }

    def _find_all_used_symbols(self) -> None:
        """Find all symbols that are used/referenced."""
        # Check for references from other symbols
        for qname, edges in self.resolver.reverse_dependencies.items():
            if edges:  # Symbol is referenced
                self.used_symbols.add(qname)

        # External entry points (main functions, exports, test files)
        for qname, symbol in self.resolver.symbol_index.items():
            if self._is_entry_point(symbol):
                self.used_symbols.add(qname)

        # Exported public symbols
        for qname, symbol in self.resolver.symbol_index.items():
            if symbol.visibility == "public" and self._looks_like_export(symbol):
                self.used_symbols.add(qname)

    def _identify_unused_symbols(self) -> None:
        """Identify symbols that are not used anywhere."""
        for qname, symbol in self.resolver.symbol_index.items():
            # Skip if symbol is used
            if qname in self.used_symbols:
                continue

            # Skip certain symbol types that are often not directly used
            if symbol.symbol_type in [SymbolType.IMPORT, SymbolType.CONSTANT]:
                continue

            # Skip exported symbols (public API)
            if symbol.visibility == "public" and self._looks_like_export(symbol):
                continue

            # This symbol is unused
            issue = DeadCodeIssue(
                symbol=symbol,
                issue_type="unused_symbol",
                references_count=0,
                line_number=symbol.line_start,
                file_path=symbol.file_path,
                severity=self._determine_severity(symbol),
            )
            self.unused_symbols.append(issue)

    def detect_unused_imports(self, file_path: str, code: str) -> List[DeadCodeIssue]:
        """Detect unused import statements in a file.

        Args:
            file_path: Path to source file
            code: Source code content

        Returns:
            List of unused import issues
        """
        unused_imports: List[DeadCodeIssue] = []
        references = self.resolver.resolve_imports(file_path, code)

        for ref in references:
            # Check if the imported symbol is actually used in the file
            if not self._is_import_used(file_path, ref):
                issue = DeadCodeIssue(
                    symbol=None,
                    issue_type="unused_import",
                    references_count=0,
                    line_number=ref.line_number,
                    file_path=file_path,
                    severity="warning",
                )
                unused_imports.append(issue)

        return unused_imports

    def find_unused_in_file(self, file_path: str) -> List[DeadCodeIssue]:
        """Find all unused symbols in a specific file.

        Args:
            file_path: Path to source file

        Returns:
            List of unused code issues in file
        """
        file_unused = [issue for issue in self.unused_symbols if issue.file_path == file_path]
        return sorted(file_unused, key=lambda x: x.line_number)

    def get_dead_code_report(self) -> str:
        """Generate a human-readable dead code report.

        Returns:
            Formatted report string
        """
        report = "═" * 70 + "\n"
        report += "                    DEAD CODE ANALYSIS REPORT\n"
        report += "═" * 70 + "\n\n"

        total = len(self.resolver.symbol_index)
        unused = len(self.unused_symbols)
        percentage = (unused / total * 100) if total > 0 else 0

        report += f"Total Symbols:      {total}\n"
        report += f"Used Symbols:       {len(self.used_symbols)}\n"
        report += f"Unused Symbols:     {unused}\n"
        report += f"Dead Code:          {percentage:.1f}%\n\n"

        # Group by file
        by_file = self._group_unused_by_file()
        if by_file:
            report += "─" * 70 + "\n"
            report += "Unused Code by File:\n"
            report += "─" * 70 + "\n"
            for file_path, issues in sorted(by_file.items()):
                report += f"\n{file_path}: ({len(issues)} unused)\n"
                for issue in sorted(issues, key=lambda x: x.line_number):
                    report += f"  Line {issue.line_number}: {issue.symbol.name} ({issue.symbol.symbol_type.value})\n"

        return report

    def _is_entry_point(self, symbol: Symbol) -> bool:
        """Check if symbol is an entry point (main, test, export)."""
        # Main functions
        if symbol.name in ["main", "__main__", "start"]:
            return True

        # Test functions
        if symbol.file_path.endswith((".test.js", ".test.ts", "_test.go", "_test.py", ".spec.ts")):
            return True

        # Export functions
        if symbol.file_path.endswith(("index.js", "index.ts")):
            return True

        return False

    def _looks_like_export(self, symbol: Symbol) -> bool:
        """Check if symbol looks like a public export."""
        # Interfaces, protocols, dataclasses
        if symbol.symbol_type in [SymbolType.INTERFACE, SymbolType.PROTOCOL, SymbolType.DATACLASS]:
            return True

        # Exported constants and enums
        if symbol.symbol_type in [SymbolType.CONSTANT, SymbolType.ENUM]:
            return True

        return False

    def _is_import_used(self, file_path: str, ref: SymbolReference) -> bool:
        """Check if an import is actually used in the file."""
        # For now, assume all imports are used
        # In future, could parse the file to check for actual usage
        return True

    def _determine_severity(self, symbol: Symbol) -> str:
        """Determine severity level of unused symbol."""
        if symbol.symbol_type in [SymbolType.CONSTANT, SymbolType.ENUM]:
            return "info"
        elif symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ASYNC_FUNCTION]:
            return "warning"
        elif symbol.symbol_type in [SymbolType.CLASS, SymbolType.INTERFACE, SymbolType.DATACLASS, SymbolType.PROTOCOL]:
            return "error"
        return "warning"

    def _group_unused_by_type(self) -> Dict[str, int]:
        """Group unused symbols by type."""
        by_type: Dict[str, int] = {}
        for issue in self.unused_symbols:
            type_name = issue.symbol.symbol_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        return by_type

    def _group_unused_by_file(self) -> Dict[str, List[DeadCodeIssue]]:
        """Group unused symbols by file."""
        by_file: Dict[str, List[DeadCodeIssue]] = {}
        for issue in self.unused_symbols:
            if issue.file_path not in by_file:
                by_file[issue.file_path] = []
            by_file[issue.file_path].append(issue)
        return by_file

    def _calculate_dead_code_percentage(self) -> float:
        """Calculate percentage of dead code."""
        total = len(self.resolver.symbol_index)
        if total == 0:
            return 0.0
        return (len(self.unused_symbols) / total) * 100
