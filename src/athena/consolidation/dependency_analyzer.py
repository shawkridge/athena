"""
AST-based dependency analyzer for procedure code.

Analyzes Python procedure code to extract dependencies, variable usage,
and data flow for safe constraint relaxation during dream generation.
"""

import ast
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Variable:
    """Represents a variable used in procedure code."""

    name: str
    line_number: int
    is_assignment: bool = False  # True if variable is assigned
    is_used: bool = False  # True if variable is used/read
    scope: str = "global"  # Scope level


@dataclass
class FunctionCall:
    """Represents a function call in procedure code."""

    name: str
    line_number: int
    module: Optional[str] = None  # e.g., 'subprocess' for subprocess.run()
    args: List[str] = field(default_factory=list)


@dataclass
class Step:
    """Represents a logical step in procedure code."""

    index: int
    line_start: int
    line_end: int
    code: str
    variables_assigned: Set[str] = field(default_factory=set)
    variables_used: Set[str] = field(default_factory=set)
    function_calls: List[FunctionCall] = field(default_factory=list)
    has_side_effects: bool = False  # File I/O, subprocess, etc.


@dataclass
class DependencyGraph:
    """Complete dependency information for a procedure."""

    procedure_id: int
    procedure_code: str
    steps: List[Step] = field(default_factory=list)
    variable_assignments: Dict[str, Set[int]] = field(default_factory=dict)  # var -> line numbers
    variable_usages: Dict[str, Set[int]] = field(default_factory=dict)  # var -> line numbers
    function_calls: List[FunctionCall] = field(default_factory=list)
    imports: Set[str] = field(default_factory=set)
    has_loops: bool = False
    has_conditionals: bool = False
    has_side_effects: bool = False

    def can_reorder(self, step_a_idx: int, step_b_idx: int) -> bool:
        """
        Check if two steps can be safely reordered.

        Step A can move after Step B if:
        - Step B doesn't use variables assigned by Step A
        - Step A doesn't use variables assigned by Step B
        - Neither step has ordering dependencies

        Args:
            step_a_idx: Index of step A
            step_b_idx: Index of step B (must be > step_a_idx for forward movement)

        Returns:
            True if steps can be safely swapped
        """
        if step_a_idx >= len(self.steps) or step_b_idx >= len(self.steps):
            return False

        step_a = self.steps[step_a_idx]
        step_b = self.steps[step_b_idx]

        # Check variable dependencies
        # Step B can't use variables assigned by Step A
        if step_a.variables_assigned & step_b.variables_used:
            return False

        # Check side effects - generally don't reorder side-effecting operations
        if step_a.has_side_effects or step_b.has_side_effects:
            # Can only reorder if completely independent
            return not (
                step_a.variables_assigned & step_b.variables_used
                or step_b.variables_assigned & step_a.variables_used
            )

        return True

    def can_parallelize(self, step_indices: List[int]) -> bool:
        """
        Check if a list of steps can be parallelized.

        Steps can be parallel if they have no data dependencies between them.

        Args:
            step_indices: Indices of steps to parallelize

        Returns:
            True if all steps can run in parallel
        """
        if len(step_indices) < 2:
            return False

        steps = [self.steps[i] for i in step_indices if i < len(self.steps)]

        # Check all pairs
        for i, step_a in enumerate(steps):
            for step_b in steps[i + 1 :]:
                # Check if either uses variables from the other
                if (
                    step_a.variables_assigned & step_b.variables_used
                    or step_b.variables_assigned & step_a.variables_used
                ):
                    return False

                # Can't parallelize side-effecting operations
                if step_a.has_side_effects or step_b.has_side_effects:
                    return False

        return True

    def find_independent_steps(self) -> List[Set[int]]:
        """
        Find groups of steps that can be executed in parallel.

        Returns:
            List of sets, where each set contains step indices that can run in parallel
        """
        independent_groups = []

        for step in self.steps:
            # Find which existing groups this step is independent of
            compatible_groups = []

            for group in independent_groups:
                step_can_join = True
                for other_idx in group:
                    if not self.can_reorder(min(step.index, other_idx), max(step.index, other_idx)):
                        step_can_join = False
                        break

                if step_can_join:
                    compatible_groups.append(group)

            if compatible_groups:
                # Add to first compatible group
                compatible_groups[0].add(step.index)
            else:
                # Create new group
                independent_groups.append({step.index})

        return independent_groups


class ProcedureDependencyAnalyzer(ast.NodeVisitor):
    """
    AST visitor to analyze Python procedure code for dependencies.

    Usage:
        analyzer = ProcedureDependencyAnalyzer(procedure_code)
        dep_graph = analyzer.analyze()
    """

    def __init__(self, procedure_id: int, procedure_code: str):
        self.procedure_id = procedure_id
        self.procedure_code = procedure_code
        self.tree: Optional[ast.AST] = None
        self.lines = procedure_code.split("\n")

        # State tracking during traversal
        self.current_step_index = 0
        self.steps: List[Step] = []
        self.current_variables_assigned: Set[str] = set()
        self.current_variables_used: Set[str] = set()
        self.current_function_calls: List[FunctionCall] = []
        self.imports: Set[str] = set()
        self.has_loops = False
        self.has_conditionals = False

    def analyze(self) -> DependencyGraph:
        """
        Analyze procedure code and return dependency graph.

        Returns:
            DependencyGraph with complete dependency information
        """
        try:
            self.tree = ast.parse(self.procedure_code)
        except SyntaxError as e:
            logger.error(f"Syntax error in procedure {self.procedure_id}: {e}")
            # Return empty graph on parse error
            return DependencyGraph(
                procedure_id=self.procedure_id, procedure_code=self.procedure_code
            )

        # First pass: extract imports
        self._extract_imports()

        # Second pass: identify steps (usually comment-delimited or logical blocks)
        self._identify_steps()

        # Third pass: analyze each step for dependencies
        self._analyze_step_dependencies()

        # Build dependency graph
        return DependencyGraph(
            procedure_id=self.procedure_id,
            procedure_code=self.procedure_code,
            steps=self.steps,
            variable_assignments=self._build_variable_assignments(),
            variable_usages=self._build_variable_usages(),
            function_calls=self.current_function_calls,
            imports=self.imports,
            has_loops=self.has_loops,
            has_conditionals=self.has_conditionals,
        )

    def _extract_imports(self):
        """Extract all import statements."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module)

    def _identify_steps(self):
        """Identify logical steps in the procedure."""
        # Simple heuristic: each assignment or function call is a step
        step_index = 0

        for i, node in enumerate(ast.walk(self.tree)):
            if isinstance(node, ast.Assign) or isinstance(node, ast.Expr):
                if hasattr(node, "lineno"):
                    step_index += 1
                    line_start = node.lineno - 1 if node.lineno else 0
                    line_end = min(line_start + 5, len(self.lines))  # Assume 5-line max per step

                    code = "\n".join(self.lines[line_start:line_end])

                    self.steps.append(
                        Step(
                            index=step_index - 1,
                            line_start=line_start,
                            line_end=line_end,
                            code=code,
                        )
                    )

    def _analyze_step_dependencies(self):
        """Analyze variable usage for each step."""
        for step in self.steps:
            try:
                step_tree = ast.parse(step.code)
                visitor = StepAnalysisVisitor()
                visitor.visit(step_tree)

                step.variables_assigned = visitor.assigned_variables
                step.variables_used = visitor.used_variables
                step.function_calls = visitor.function_calls
                step.has_side_effects = visitor.has_side_effects

            except SyntaxError:
                # If step can't be parsed, mark it as having side effects
                step.has_side_effects = True

        # Track loop/conditional structures
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.For, ast.While)):
                self.has_loops = True
            elif isinstance(node, (ast.If, ast.IfExp)):
                self.has_conditionals = True

    def _build_variable_assignments(self) -> Dict[str, Set[int]]:
        """Build mapping of variables to their assignment line numbers."""
        result = {}
        for step in self.steps:
            for var in step.variables_assigned:
                if var not in result:
                    result[var] = set()
                result[var].add(step.index)
        return result

    def _build_variable_usages(self) -> Dict[str, Set[int]]:
        """Build mapping of variables to their usage line numbers."""
        result = {}
        for step in self.steps:
            for var in step.variables_used:
                if var not in result:
                    result[var] = set()
                result[var].add(step.index)
        return result


class StepAnalysisVisitor(ast.NodeVisitor):
    """Visitor to analyze a single procedure step for variable usage."""

    def __init__(self):
        self.assigned_variables: Set[str] = set()
        self.used_variables: Set[str] = set()
        self.function_calls: List[FunctionCall] = []
        self.has_side_effects = False

    def visit_Assign(self, node):
        """Track variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.assigned_variables.add(target.id)
            elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        self.assigned_variables.add(elt.id)

        # Visit the value being assigned
        self.visit(node.value)

    def visit_Name(self, node):
        """Track variable usage."""
        if isinstance(node.ctx, ast.Load):
            self.used_variables.add(node.id)

    def visit_Call(self, node):
        """Track function calls, especially side-effecting ones."""
        if isinstance(node.func, ast.Name):
            name = node.func.id
            self.function_calls.append(
                FunctionCall(
                    name=name, line_number=node.lineno, args=[ast.unparse(arg) for arg in node.args]
                )
            )

            # Check for side-effecting functions
            if name in ("open", "write", "remove", "rename", "system", "exec", "eval"):
                self.has_side_effects = True

        elif isinstance(node.func, ast.Attribute):
            # e.g., subprocess.run(), file.write()
            if isinstance(node.func.value, ast.Name):
                module = node.func.value.id
                func_name = node.func.attr

                self.function_calls.append(
                    FunctionCall(
                        name=func_name,
                        line_number=node.lineno,
                        module=module,
                        args=[ast.unparse(arg) for arg in node.args],
                    )
                )

                # Check for side-effecting operations
                if module in ("subprocess", "os", "shutil") or func_name in (
                    "write",
                    "remove",
                    "rename",
                ):
                    self.has_side_effects = True

        self.generic_visit(node)
