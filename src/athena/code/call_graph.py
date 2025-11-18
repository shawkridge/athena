"""Call Graph Analysis - Extract and analyze function call relationships.

Builds call graphs from Python source code to understand function dependencies,
data flow, and call patterns. Uses AST (Abstract Syntax Tree) parsing to
accurately extract function definitions and calls.

Features:
- Function definition and call extraction via AST
- Call graph construction and traversal
- Data flow analysis (parameter and return value tracking)
- Cycle detection
- Path finding between functions
- Call depth analysis
"""

import ast
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class FunctionDef:
    """Function definition metadata."""

    name: str
    module: str  # Module where function is defined
    lineno: int  # Line number in source
    qualname: str  # Fully qualified name (for methods)
    params: List[str] = field(default_factory=list)  # Parameter names
    returns: Optional[str] = None  # Return type annotation
    is_method: bool = False  # Is this a class method?
    class_name: Optional[str] = None  # Parent class if method
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class FunctionCall:
    """Function call metadata."""

    caller: str  # Function that makes the call
    callee: str  # Function being called
    lineno: int  # Line number of call
    args: List[str] = field(default_factory=list)  # Argument names
    kwargs: Dict[str, str] = field(default_factory=dict)  # Keyword arguments
    is_external: bool = False  # Call to external module?


@dataclass
class CallGraphConfig:
    """Configuration for call graph analysis."""

    include_external: bool = False  # Include calls to external modules
    include_builtins: bool = False  # Include built-in function calls
    max_recursion_depth: int = 50  # Max depth for cycle detection
    analyze_dataflow: bool = True  # Track data flow
    extract_docstrings: bool = True  # Extract function docstrings


class CallGraphBuilder(ast.NodeVisitor):
    """Builds call graph from Python source code using AST parsing."""

    def __init__(
        self, source: str, module_name: str = "__main__", config: Optional[CallGraphConfig] = None
    ):
        """Initialize call graph builder.

        Args:
            source: Python source code
            module_name: Module name for the source
            config: Call graph configuration
        """
        self.source = source
        self.module_name = module_name
        self.config = config or CallGraphConfig()

        self.functions: Dict[str, FunctionDef] = {}
        self.calls: List[FunctionCall] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None

        # Parse source
        try:
            self.tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in source: {e}")
            self.tree = None

    def build(self) -> "CallGraph":
        """Build call graph from source.

        Returns:
            CallGraph object
        """
        if self.tree is None:
            return CallGraph(functions={}, calls=[], config=self.config)

        # Extract functions and calls
        self.visit(self.tree)

        return CallGraph(
            functions=self.functions,
            calls=self.calls,
            config=self.config,
            module_name=self.module_name,
        )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        qualname = f"{self.current_class}.{node.name}" if self.current_class else node.name
        full_qualname = f"{self.module_name}.{qualname}"

        # Extract parameters
        params = [arg.arg for arg in node.args.args]

        # Extract decorators
        decorators = [self._get_name(d) for d in node.decorator_list]

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Create function definition
        func_def = FunctionDef(
            name=node.name,
            module=self.module_name,
            lineno=node.lineno,
            qualname=qualname,
            params=params,
            is_method=self.current_class is not None,
            class_name=self.current_class,
            decorators=decorators,
            docstring=docstring,
        )

        self.functions[full_qualname] = func_def

        # Visit body to find calls
        prev_function = self.current_function
        self.current_function = full_qualname
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition (same as FunctionDef)."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_Call(self, node: ast.Call):
        """Visit function call."""
        if self.current_function:
            callee_name = self._get_name(node.func)

            # Extract arguments
            args = [self._get_name(arg) for arg in node.args]
            kwargs = {kw.arg: self._get_name(kw.value) for kw in node.keywords}

            # Create call record
            call = FunctionCall(
                caller=self.current_function,
                callee=callee_name,
                lineno=node.lineno,
                args=args,
                kwargs=kwargs,
                is_external=not self._is_internal_call(callee_name),
            )

            # Filter based on config
            if not self.config.include_external and call.is_external:
                pass
            elif not self.config.include_builtins and self._is_builtin(callee_name):
                pass
            else:
                self.calls.append(call)

        self.generic_visit(node)

    def _get_name(self, node: ast.expr) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        else:
            return "unknown"

    def _is_internal_call(self, name: str) -> bool:
        """Check if call is to internal function."""
        # Simple heuristic: internal calls don't have module prefix
        return "." not in name or name.startswith(self.module_name)

    def _is_builtin(self, name: str) -> bool:
        """Check if function is builtin."""
        builtins = {
            "print",
            "len",
            "range",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "bool",
            "type",
            "open",
            "input",
            "sum",
            "min",
            "max",
        }
        return name in builtins


class CallGraph:
    """Represents a function call graph."""

    def __init__(
        self,
        functions: Dict[str, FunctionDef],
        calls: List[FunctionCall],
        config: Optional[CallGraphConfig] = None,
        module_name: str = "__main__",
    ):
        """Initialize call graph.

        Args:
            functions: Dictionary of function definitions
            calls: List of function calls
            config: Call graph configuration
            module_name: Module name
        """
        self.functions = functions
        self.calls = calls
        self.config = config or CallGraphConfig()
        self.module_name = module_name

        # Build adjacency structures
        self._build_adjacency()

    def _build_adjacency(self):
        """Build adjacency lists for quick traversal."""
        self.callers: Dict[str, List[str]] = defaultdict(list)  # function -> [callers]
        self.callees: Dict[str, List[str]] = defaultdict(list)  # function -> [callees]

        for call in self.calls:
            self.callees[call.caller].append(call.callee)
            self.callers[call.callee].append(call.caller)

    def get_all_callers(self, func_name: str, recursive: bool = False) -> Set[str]:
        """Get all functions that call a given function.

        Args:
            func_name: Function name to analyze
            recursive: If True, recursively get all transitive callers

        Returns:
            Set of caller function names
        """
        if not recursive:
            return set(self.callers.get(func_name, []))

        # BFS to find all transitive callers
        visited = set()
        queue = deque([func_name])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for caller in self.callers.get(current, []):
                if caller not in visited:
                    queue.append(caller)

        visited.discard(func_name)  # Don't include the starting function
        return visited

    def get_all_callees(self, func_name: str, recursive: bool = False) -> Set[str]:
        """Get all functions called by a given function.

        Args:
            func_name: Function name to analyze
            recursive: If True, recursively get all transitive callees

        Returns:
            Set of callee function names
        """
        if not recursive:
            return set(self.callees.get(func_name, []))

        # BFS to find all transitive callees
        visited = set()
        queue = deque([func_name])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for callee in self.callees.get(current, []):
                if callee not in visited:
                    queue.append(callee)

        visited.discard(func_name)  # Don't include the starting function
        return visited

    def find_call_paths(self, start: str, end: str, max_depth: int = 10) -> List[List[str]]:
        """Find all call paths from one function to another.

        Args:
            start: Starting function name
            end: Ending function name
            max_depth: Maximum depth to search

        Returns:
            List of paths (each path is a list of function names)
        """
        if start == end:
            return [[start]]

        paths = []

        def dfs(current: str, target: str, path: List[str], visited: Set[str], depth: int):
            if depth > max_depth:
                return

            for callee in self.callees.get(current, []):
                if callee == target:
                    paths.append(path + [callee])
                elif callee not in visited:
                    visited.add(callee)
                    dfs(callee, target, path + [callee], visited.copy(), depth + 1)

        dfs(start, end, [start], {start}, 0)
        return paths

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the call graph.

        Returns:
            List of cycles (each cycle is a list of function names)
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def visit(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.callees.get(node, []):
                if neighbor not in visited:
                    visit(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            rec_stack.discard(node)

        for func in self.functions:
            if func not in visited:
                visit(func, [func])

        return cycles

    def get_call_depth(self, func_name: str) -> Dict[str, int]:
        """Get call depth for all reachable functions.

        Args:
            func_name: Starting function name

        Returns:
            Dictionary mapping function names to call depth
        """
        depths = {func_name: 0}
        queue = deque([func_name])

        while queue:
            current = queue.popleft()
            current_depth = depths[current]

            for callee in self.callees.get(current, []):
                if callee not in depths:
                    depths[callee] = current_depth + 1
                    queue.append(callee)

        return depths

    def get_function_metrics(self, func_name: str) -> Dict[str, Any]:
        """Get metrics for a function.

        Args:
            func_name: Function name

        Returns:
            Dictionary of metrics
        """
        if func_name not in self.functions:
            return {}

        func_def = self.functions[func_name]
        direct_callers = self.callers.get(func_name, [])
        direct_callees = self.callees.get(func_name, [])
        all_callers = self.get_all_callers(func_name, recursive=True)
        all_callees = self.get_all_callees(func_name, recursive=True)
        cycles = [c for c in self.detect_cycles() if func_name in c]

        return {
            "name": func_def.name,
            "qualname": func_def.qualname,
            "lineno": func_def.lineno,
            "is_method": func_def.is_method,
            "direct_callers": len(direct_callers),
            "direct_callees": len(direct_callees),
            "transitive_callers": len(all_callers),
            "transitive_callees": len(all_callees),
            "has_cycles": len(cycles) > 0,
            "parameters": len(func_def.params),
            "decorators": func_def.decorators,
        }

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get overall graph statistics.

        Returns:
            Dictionary of statistics
        """
        # Find entry points (functions with no callers)
        all_called = set()
        for call in self.calls:
            all_called.add(call.callee)

        entry_points = [f for f in self.functions if f not in all_called]

        # Find leaf functions (functions with no callees)
        all_callers_set = set(call.caller for call in self.calls)
        leaf_functions = [f for f in self.functions if f not in all_callers_set]

        return {
            "total_functions": len(self.functions),
            "total_calls": len(self.calls),
            "entry_points": len(entry_points),
            "leaf_functions": len(leaf_functions),
            "cycles": len(self.detect_cycles()),
            "average_fanout": len(self.calls) / max(1, len(self.functions)),
        }

    def export_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Export metrics for all functions.

        Returns:
            Dictionary mapping function names to their metrics
        """
        metrics = {}
        for func_name in self.functions:
            metrics[func_name] = self.get_function_metrics(func_name)
        return metrics
