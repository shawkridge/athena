"""Call Graph Analyzer for tracking function-to-function calls.

Provides:
- Function call detection and tracking
- Recursive call detection
- Call graph statistics (in-degree, out-degree)
- Caller/callee relationships
- Cross-file call tracking
"""

from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field
import re

from .symbol_models import Symbol, SymbolType


@dataclass
class CallNode:
    """A node in the call graph (a function/method)."""
    symbol: Symbol
    in_degree: int = 0  # Number of callers
    out_degree: int = 0  # Number of callees
    is_recursive: bool = False
    is_entry_point: bool = False
    call_count: int = 0  # Total calls made by this function


@dataclass
class CallEdge:
    """An edge in the call graph (a function call)."""
    from_symbol: Symbol
    to_symbol: Symbol
    call_count: int = 1
    line_number: int = 0
    is_recursive: bool = False


@dataclass
class CallPath:
    """A path of function calls."""
    symbols: List[Symbol]
    length: int = 0

    def __post_init__(self):
        self.length = len(self.symbols) - 1


class CallGraphAnalyzer:
    """Analyzes function call relationships."""

    def __init__(self, symbols: Dict[str, List[Symbol]]):
        """Initialize the call graph analyzer.

        Args:
            symbols: Dictionary mapping file paths to symbol lists
        """
        self.symbols = symbols
        self.symbol_index: Dict[str, Symbol] = {}
        self.call_graph: Dict[str, List[CallEdge]] = {}  # from_qname -> [CallEdge]
        self.reverse_call_graph: Dict[str, List[CallEdge]] = {}  # to_qname -> [CallEdge]
        self.call_nodes: Dict[str, CallNode] = {}
        self._build_symbol_index()

    def _build_symbol_index(self) -> None:
        """Build index of all symbols by qualified name."""
        for file_path, syms in self.symbols.items():
            for symbol in syms:
                qname = symbol.full_qualified_name or f"{file_path}:{symbol.name}"
                self.symbol_index[qname] = symbol
                self.call_nodes[qname] = CallNode(symbol=symbol)

    def analyze_file(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze a file for function calls.

        Args:
            file_path: Path to source file
            code: Source code content

        Returns:
            List of detected call edges
        """
        calls: List[CallEdge] = []

        # Detect language and use appropriate analyzer
        if file_path.endswith(('.py', '.pyw')):
            calls.extend(self._analyze_python_calls(file_path, code))
        elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            calls.extend(self._analyze_js_calls(file_path, code))
        elif file_path.endswith('.java'):
            calls.extend(self._analyze_java_calls(file_path, code))
        elif file_path.endswith('.go'):
            calls.extend(self._analyze_go_calls(file_path, code))
        elif file_path.endswith('.rs'):
            calls.extend(self._analyze_rust_calls(file_path, code))

        return calls

    def _analyze_python_calls(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze Python function calls."""
        calls: List[CallEdge] = []
        lines = code.split('\n')

        # Pattern: function_name() or object.method()
        call_pattern = re.compile(r'(\w+)\s*\(')

        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            if '#' in line:
                line = line[:line.index('#')]

            matches = call_pattern.findall(line)
            for func_name in matches:
                # Try to find this function in symbol index
                for qname, symbol in self.symbol_index.items():
                    if symbol.name == func_name:
                        call = CallEdge(
                            from_symbol=None,
                            to_symbol=symbol,
                            line_number=line_num
                        )
                        calls.append(call)
                        break

        return calls

    def _analyze_js_calls(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze JavaScript/TypeScript function calls."""
        calls: List[CallEdge] = []
        lines = code.split('\n')

        # Pattern: functionName() or object.method() or await func()
        call_pattern = re.compile(r'(?:await\s+)?(\w+)\s*\(')

        for line_num, line in enumerate(lines, 1):
            # Skip comments and strings
            if '//' in line:
                line = line[:line.index('//')]

            matches = call_pattern.findall(line)
            for func_name in matches:
                for qname, symbol in self.symbol_index.items():
                    if symbol.name == func_name:
                        call = CallEdge(
                            from_symbol=None,
                            to_symbol=symbol,
                            line_number=line_num
                        )
                        calls.append(call)
                        break

        return calls

    def _analyze_java_calls(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze Java method calls."""
        calls: List[CallEdge] = []
        lines = code.split('\n')

        # Pattern: methodName() or object.methodName()
        call_pattern = re.compile(r'(\w+)\s*\(')

        for line_num, line in enumerate(lines, 1):
            matches = call_pattern.findall(line)
            for method_name in matches:
                for qname, symbol in self.symbol_index.items():
                    if symbol.name == method_name:
                        call = CallEdge(
                            from_symbol=None,
                            to_symbol=symbol,
                            line_number=line_num
                        )
                        calls.append(call)
                        break

        return calls

    def _analyze_go_calls(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze Go function calls."""
        calls: List[CallEdge] = []
        lines = code.split('\n')

        # Pattern: FunctionName() or pkg.FunctionName()
        call_pattern = re.compile(r'(\w+)\s*\(')

        for line_num, line in enumerate(lines, 1):
            matches = call_pattern.findall(line)
            for func_name in matches:
                for qname, symbol in self.symbol_index.items():
                    if symbol.name == func_name:
                        call = CallEdge(
                            from_symbol=None,
                            to_symbol=symbol,
                            line_number=line_num
                        )
                        calls.append(call)
                        break

        return calls

    def _analyze_rust_calls(self, file_path: str, code: str) -> List[CallEdge]:
        """Analyze Rust function calls."""
        calls: List[CallEdge] = []
        lines = code.split('\n')

        # Pattern: function_name() or object.method()
        call_pattern = re.compile(r'(\w+)\s*\(')

        for line_num, line in enumerate(lines, 1):
            matches = call_pattern.findall(line)
            for func_name in matches:
                for qname, symbol in self.symbol_index.items():
                    if symbol.name == func_name:
                        call = CallEdge(
                            from_symbol=None,
                            to_symbol=symbol,
                            line_number=line_num
                        )
                        calls.append(call)
                        break

        return calls

    def build_call_graph(self, analyzed_calls: List[CallEdge]) -> None:
        """Build call graph from analyzed calls.

        Args:
            analyzed_calls: List of CallEdge objects detected from code
        """
        for call in analyzed_calls:
            if call.to_symbol is None:
                continue

            # Get qualified names
            from_qname = call.from_symbol.full_qualified_name or f"{call.from_symbol.file_path}:{call.from_symbol.name}" if call.from_symbol else "unknown"
            to_qname = call.to_symbol.full_qualified_name or f"{call.to_symbol.file_path}:{call.to_symbol.name}"

            # Add to call_graph (from -> to)
            if from_qname not in self.call_graph:
                self.call_graph[from_qname] = []
            self.call_graph[from_qname].append(call)

            # Add to reverse_call_graph (to <- from)
            if to_qname not in self.reverse_call_graph:
                self.reverse_call_graph[to_qname] = []
            self.reverse_call_graph[to_qname].append(call)

        # Update node degrees
        for qname, node in self.call_nodes.items():
            node.out_degree = len(self.call_graph.get(qname, []))
            node.in_degree = len(self.reverse_call_graph.get(qname, []))
            node.call_count = node.out_degree

    def detect_recursive_calls(self) -> List[Tuple[Symbol, Symbol]]:
        """Detect recursive function calls.

        Returns:
            List of (caller, callee) tuples for recursive calls
        """
        recursive_calls: List[Tuple[Symbol, Symbol]] = []

        for qname, node in self.call_nodes.items():
            # Check if function calls itself
            for call in self.call_graph.get(qname, []):
                if call.to_symbol and call.to_symbol.full_qualified_name == qname:
                    recursive_calls.append((call.to_symbol, call.to_symbol))
                    node.is_recursive = True

        return recursive_calls

    def get_callers(self, symbol: Symbol) -> List[Symbol]:
        """Get all functions that call a given symbol.

        Args:
            symbol: Symbol to find callers for

        Returns:
            List of symbols that call the given symbol
        """
        qname = symbol.full_qualified_name or f"{symbol.file_path}:{symbol.name}"
        edges = self.reverse_call_graph.get(qname, [])
        return [edge.from_symbol for edge in edges if edge.from_symbol]

    def get_callees(self, symbol: Symbol) -> List[Symbol]:
        """Get all functions called by a given symbol.

        Args:
            symbol: Symbol to find callees for

        Returns:
            List of symbols called by the given symbol
        """
        qname = symbol.full_qualified_name or f"{symbol.file_path}:{symbol.name}"
        edges = self.call_graph.get(qname, [])
        return [edge.to_symbol for edge in edges if edge.to_symbol]

    def get_call_graph_stats(self) -> Dict:
        """Get statistics about the call graph.

        Returns:
            Dictionary with call graph statistics
        """
        total_calls = sum(len(edges) for edges in self.call_graph.values())
        recursive_calls = len(self.detect_recursive_calls())

        max_in_degree = max((n.in_degree for n in self.call_nodes.values()), default=0)
        max_out_degree = max((n.out_degree for n in self.call_nodes.values()), default=0)
        avg_in_degree = total_calls / len(self.call_nodes) if self.call_nodes else 0

        return {
            "total_nodes": len(self.call_nodes),
            "total_calls": total_calls,
            "recursive_calls": recursive_calls,
            "max_in_degree": max_in_degree,
            "max_out_degree": max_out_degree,
            "avg_in_degree": avg_in_degree,
            "leaf_functions": len([n for n in self.call_nodes.values() if n.out_degree == 0]),
            "entry_points": len([n for n in self.call_nodes.values() if n.in_degree == 0]),
        }

    def find_call_paths(self, from_symbol: Symbol, to_symbol: Symbol, max_depth: int = 5) -> List[CallPath]:
        """Find all call paths between two symbols.

        Args:
            from_symbol: Starting symbol
            to_symbol: Target symbol
            max_depth: Maximum path depth to search

        Returns:
            List of call paths from from_symbol to to_symbol
        """
        from_qname = from_symbol.full_qualified_name or f"{from_symbol.file_path}:{from_symbol.name}"
        to_qname = to_symbol.full_qualified_name or f"{to_symbol.file_path}:{to_symbol.name}"

        paths: List[CallPath] = []
        visited: Set[str] = set()

        def dfs(current_qname: str, path: List[Symbol]) -> None:
            if len(path) > max_depth:
                return

            if current_qname == to_qname:
                paths.append(CallPath(symbols=path[:]))
                return

            if current_qname in visited:
                return

            visited.add(current_qname)

            for call in self.call_graph.get(current_qname, []):
                if call.to_symbol:
                    next_qname = call.to_symbol.full_qualified_name or f"{call.to_symbol.file_path}:{call.to_symbol.name}"
                    path.append(call.to_symbol)
                    dfs(next_qname, path)
                    path.pop()

            visited.discard(current_qname)

        if from_qname in self.call_nodes:
            dfs(from_qname, [from_symbol])

        return paths

    def get_call_graph_report(self) -> str:
        """Generate a human-readable call graph report.

        Returns:
            Formatted report string
        """
        stats = self.get_call_graph_stats()
        report = "═" * 70 + "\n"
        report += "                      CALL GRAPH ANALYSIS REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Functions:      {stats['total_nodes']}\n"
        report += f"Total Calls:          {stats['total_calls']}\n"
        report += f"Recursive Calls:      {stats['recursive_calls']}\n"
        report += f"Entry Points:         {stats['entry_points']}\n"
        report += f"Leaf Functions:       {stats['leaf_functions']}\n"
        report += f"Max In-Degree:        {stats['max_in_degree']}\n"
        report += f"Max Out-Degree:       {stats['max_out_degree']}\n"
        report += f"Avg In-Degree:        {stats['avg_in_degree']:.2f}\n\n"

        # Top callers
        top_callers = sorted(self.call_nodes.values(), key=lambda n: n.in_degree, reverse=True)[:5]
        if top_callers:
            report += "─" * 70 + "\n"
            report += "Top Called Functions:\n"
            report += "─" * 70 + "\n"
            for node in top_callers:
                report += f"{node.symbol.name:30} called {node.in_degree} times\n"

        # Top callee makers
        top_callee_makers = sorted(self.call_nodes.values(), key=lambda n: n.out_degree, reverse=True)[:5]
        if top_callee_makers:
            report += "\n" + "─" * 70 + "\n"
            report += "Top Calling Functions:\n"
            report += "─" * 70 + "\n"
            for node in top_callee_makers:
                report += f"{node.symbol.name:30} calls {node.out_degree} functions\n"

        return report
