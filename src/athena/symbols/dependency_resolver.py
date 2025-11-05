"""Symbol Dependency Resolver for analyzing cross-file relationships.

Provides:
- Import statement resolution
- Symbol definition location tracking
- Dependency graph construction
- Circular dependency detection
- Impact analysis for code changes
- Module hierarchy visualization
"""

from typing import Optional, Dict, List, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class DependencyType(str, Enum):
    """Types of dependencies between symbols."""
    IMPORT = "import"  # Direct import
    INHERIT = "inherit"  # Class inheritance
    IMPLEMENT = "implement"  # Interface implementation
    CALL = "call"  # Function/method call
    TYPE = "type"  # Type reference
    GENERIC = "generic"  # Generic type parameter


@dataclass
class SymbolReference:
    """A reference to a symbol from another file."""
    source_file: str
    source_symbol: Optional[Symbol]
    target_module: str  # Module/file being imported
    target_symbol: str  # Symbol name being imported
    dependency_type: DependencyType
    line_number: int = 0


@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""
    from_symbol: Symbol
    to_symbol: Symbol
    dependency_type: DependencyType
    references: List[SymbolReference] = field(default_factory=list)


@dataclass
class DependencyPath:
    """A path in the dependency graph."""
    symbols: List[Symbol]
    types: List[DependencyType]

    @property
    def length(self) -> int:
        return len(self.symbols) - 1


class DependencyResolver:
    """Resolves dependencies between symbols across files."""

    def __init__(self):
        """Initialize the dependency resolver."""
        self.symbols: Dict[str, List[Symbol]] = {}  # file_path -> [Symbol]
        self.symbol_index: Dict[str, Symbol] = {}  # qname -> Symbol
        self.dependencies: Dict[str, List[DependencyEdge]] = {}  # qname -> [DependencyEdge]
        self.reverse_dependencies: Dict[str, List[DependencyEdge]] = {}  # qname -> [DependencyEdge]

    def add_symbols(self, file_path: str, symbols: List[Symbol]) -> None:
        """Add symbols from a file to the resolver.

        Args:
            file_path: Path to the source file
            symbols: List of extracted symbols
        """
        self.symbols[file_path] = symbols
        for symbol in symbols:
            qname = symbol.full_qualified_name or f"{file_path}:{symbol.name}"
            self.symbol_index[qname] = symbol

    def resolve_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve import statements in source code.

        Args:
            file_path: Path to the source file
            code: Source code content

        Returns:
            List of resolved symbol references
        """
        references: List[SymbolReference] = []

        # Detect language from file extension
        if file_path.endswith(('.py', '.pyw')):
            references.extend(self._resolve_python_imports(file_path, code))
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            references.extend(self._resolve_js_imports(file_path, code))
        elif file_path.endswith('.java'):
            references.extend(self._resolve_java_imports(file_path, code))
        elif file_path.endswith('.go'):
            references.extend(self._resolve_go_imports(file_path, code))
        elif file_path.endswith('.rs'):
            references.extend(self._resolve_rust_imports(file_path, code))

        return references

    def _resolve_python_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve Python import statements."""
        references: List[SymbolReference] = []
        lines = code.split('\n')

        # Pattern: from module import name
        from_pattern = re.compile(r'from\s+([\w.]+)\s+import\s+([^#\n]+)')
        # Pattern: import module
        import_pattern = re.compile(r'import\s+([\w.]+)(?:\s+as\s+(\w+))?')

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if '#' in line:
                line = line[:line.index('#')]

            # from ... import
            from_match = from_pattern.search(line)
            if from_match:
                module = from_match.group(1)
                imports = from_match.group(2)
                for imported in imports.split(','):
                    name = imported.strip().split(' as ')[-1].strip()
                    if name and name != '*':
                        ref = SymbolReference(
                            source_file=file_path,
                            source_symbol=None,
                            target_module=module,
                            target_symbol=name,
                            dependency_type=DependencyType.IMPORT,
                            line_number=line_num
                        )
                        references.append(ref)

            # import ...
            import_match = import_pattern.search(line)
            if import_match:
                module = import_match.group(1)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=module.split('.')[-1],
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)

        return references

    def _resolve_js_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve JavaScript/TypeScript import statements."""
        references: List[SymbolReference] = []
        lines = code.split('\n')

        # Pattern: import { name } from 'module'
        named_pattern = re.compile(r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]')
        # Pattern: import * as name from 'module'
        namespace_pattern = re.compile(r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]')
        # Pattern: import default from 'module'
        default_pattern = re.compile(r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]')
        # Pattern: require('module')
        require_pattern = re.compile(r'require\([\'"]([^\'"]+)[\'"]\)')

        for line_num, line in enumerate(lines, 1):
            # named imports
            named_match = named_pattern.search(line)
            if named_match:
                imports = named_match.group(1)
                module = named_match.group(2)
                for imported in imports.split(','):
                    name = imported.strip().split(' as ')[-1].strip()
                    if name:
                        ref = SymbolReference(
                            source_file=file_path,
                            source_symbol=None,
                            target_module=module,
                            target_symbol=name,
                            dependency_type=DependencyType.IMPORT,
                            line_number=line_num
                        )
                        references.append(ref)
                continue

            # namespace imports
            namespace_match = namespace_pattern.search(line)
            if namespace_match:
                module = namespace_match.group(2)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol="*",
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)
                continue

            # default imports
            default_match = default_pattern.search(line)
            if default_match and 'import {' not in line and 'import *' not in line:
                module = default_match.group(2)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol="default",
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)
                continue

            # require statements
            require_match = require_pattern.search(line)
            if require_match:
                module = require_match.group(1)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=module.split('/')[-1],
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)

        return references

    def _resolve_java_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve Java import statements."""
        references: List[SymbolReference] = []

        # Pattern: import package.Class; or import package.*;
        import_pattern = re.compile(r'import\s+([\w.]+(?:\.\*)?);')

        for line_num, line_obj in enumerate(code.split('\n'), 1):
            import_match = import_pattern.search(line_obj)
            if import_match:
                fully_qualified = import_match.group(1)

                # Handle wildcard imports
                if fully_qualified.endswith('.*'):
                    package = fully_qualified[:-2]  # Remove .*
                    ref = SymbolReference(
                        source_file=file_path,
                        source_symbol=None,
                        target_module=package,
                        target_symbol="*",
                        dependency_type=DependencyType.IMPORT,
                        line_number=line_num
                    )
                    references.append(ref)
                else:
                    class_name = fully_qualified.split('.')[-1]
                    package = '.'.join(fully_qualified.split('.')[:-1])

                    ref = SymbolReference(
                        source_file=file_path,
                        source_symbol=None,
                        target_module=package,
                        target_symbol=class_name,
                        dependency_type=DependencyType.IMPORT,
                        line_number=line_num
                    )
                    references.append(ref)

        return references

    def _resolve_go_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve Go import statements."""
        references: List[SymbolReference] = []

        # Pattern: import "package"
        import_pattern = re.compile(r'import\s+"([^"]+)"')
        # Pattern: import alias "package"
        alias_pattern = re.compile(r'import\s+(\w+)\s+"([^"]+)"')
        # Pattern: multi-line import block
        multiline_pattern = re.compile(r'import\s*\((.*?)\)', re.DOTALL)
        # Pattern: quoted string in import block
        quoted_pattern = re.compile(r'"([^"]+)"')

        # First check for multi-line import blocks
        multiline_match = multiline_pattern.search(code)
        if multiline_match:
            block_content = multiline_match.group(1)
            # Extract all quoted strings (package names)
            for match in quoted_pattern.finditer(block_content):
                module = match.group(1)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=module.split('/')[-1],
                    dependency_type=DependencyType.IMPORT,
                    line_number=1
                )
                references.append(ref)

        # Then check for single-line imports
        for line_num, line_obj in enumerate(code.split('\n'), 1):
            # Skip lines already processed in multi-line block
            if 'import (' in line_obj or ')' in line_obj:
                continue

            alias_match = alias_pattern.search(line_obj)
            if alias_match:
                module = alias_match.group(2)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=alias_match.group(1),
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)
                continue

            import_match = import_pattern.search(line_obj)
            if import_match:
                module = import_match.group(1)
                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=module.split('/')[-1],
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)

        return references

    def _resolve_rust_imports(self, file_path: str, code: str) -> List[SymbolReference]:
        """Resolve Rust import statements."""
        references: List[SymbolReference] = []

        # Pattern: use module::Item;
        use_pattern = re.compile(r'use\s+([\w:]+)(?:\s+as\s+(\w+))?;')

        for line_num, line_obj in enumerate(code.split('\n'), 1):
            use_match = use_pattern.search(line_obj)
            if use_match:
                path = use_match.group(1)
                parts = path.split('::')
                module = parts[0]
                symbol = parts[-1] if len(parts) > 1 else module

                ref = SymbolReference(
                    source_file=file_path,
                    source_symbol=None,
                    target_module=module,
                    target_symbol=symbol,
                    dependency_type=DependencyType.IMPORT,
                    line_number=line_num
                )
                references.append(ref)

        return references

    def find_symbol_uses(self, symbol: Symbol) -> List[SymbolReference]:
        """Find all uses of a specific symbol.

        Args:
            symbol: The symbol to find uses for

        Returns:
            List of references to the symbol
        """
        qname = symbol.full_qualified_name or f"{symbol.file_path}:{symbol.name}"
        return self.reverse_dependencies.get(qname, [])

    def find_symbol_dependencies(self, symbol: Symbol) -> List[Symbol]:
        """Find all symbols that a symbol depends on.

        Args:
            symbol: The symbol to find dependencies for

        Returns:
            List of symbols that this symbol depends on
        """
        qname = symbol.full_qualified_name or f"{symbol.file_path}:{symbol.name}"
        edges = self.dependencies.get(qname, [])
        return [edge.to_symbol for edge in edges]

    def detect_circular_dependencies(self) -> List[List[Symbol]]:
        """Detect circular dependency chains.

        Returns:
            List of circular dependency cycles
        """
        cycles: List[List[Symbol]] = []
        visited: Set[str] = set()

        def dfs(qname: str, path: List[str], rec_stack: Set[str]) -> None:
            visited.add(qname)
            rec_stack.add(qname)
            path.append(qname)

            edges = self.dependencies.get(qname, [])
            for edge in edges:
                to_qname = edge.to_symbol.full_qualified_name or f"{edge.to_symbol.file_path}:{edge.to_symbol.name}"

                if to_qname not in visited:
                    dfs(to_qname, path[:], rec_stack)
                elif to_qname in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(to_qname)
                    cycle_qnames = path[cycle_start:] + [to_qname]
                    cycle_symbols = [self.symbol_index.get(n) for n in cycle_qnames if n in self.symbol_index]
                    if cycle_symbols and len(cycle_symbols) > 1:
                        cycles.append(cycle_symbols)

            rec_stack.discard(qname)

        for qname in self.symbol_index:
            if qname not in visited:
                dfs(qname, [], set())

        return cycles

    def find_impact_of_change(self, symbol: Symbol) -> Dict[str, List[Symbol]]:
        """Find all symbols affected by a change to the given symbol.

        Args:
            symbol: The symbol being changed

        Returns:
            Dictionary mapping impact level to affected symbols
        """
        qname = symbol.full_qualified_name or f"{symbol.file_path}:{symbol.name}"
        directly_affected = self.find_symbol_uses(symbol)

        impact_map = {
            "direct": [ref.source_symbol for ref in directly_affected if ref.source_symbol],
            "indirect": []
        }

        # Find indirectly affected symbols (symbols that use the directly affected ones)
        visited = set()
        for direct_symbol in impact_map["direct"]:
            if direct_symbol:
                for indirect_ref in self.find_symbol_uses(direct_symbol):
                    if indirect_ref.source_symbol and indirect_ref.source_symbol not in visited:
                        impact_map["indirect"].append(indirect_ref.source_symbol)
                        visited.add(indirect_ref.source_symbol)

        return impact_map

    def get_dependency_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the dependency graph.

        Returns:
            Dictionary with graph statistics
        """
        total_symbols = len(self.symbol_index)
        total_dependencies = sum(len(edges) for edges in self.dependencies.values())
        circular_deps = len(self.detect_circular_dependencies())

        # Calculate max depth
        max_depth = 0
        for qname in self.symbol_index:
            depth = self._calculate_dependency_depth(qname)
            max_depth = max(max_depth, depth)

        return {
            "total_symbols": total_symbols,
            "total_dependencies": total_dependencies,
            "circular_dependencies": circular_deps,
            "max_dependency_depth": max_depth,
            "files_with_symbols": len(self.symbols)
        }

    def _calculate_dependency_depth(self, qname: str, visited: Optional[Set[str]] = None) -> int:
        """Calculate the dependency depth of a symbol."""
        if visited is None:
            visited = set()

        if qname in visited:
            return 0

        visited.add(qname)
        edges = self.dependencies.get(qname, [])

        if not edges:
            return 0

        max_child_depth = 0
        for edge in edges:
            to_qname = edge.to_symbol.full_qualified_name or f"{edge.to_symbol.file_path}:{edge.to_symbol.name}"
            depth = self._calculate_dependency_depth(to_qname, visited)
            max_child_depth = max(max_child_depth, depth)

        return max_child_depth + 1
