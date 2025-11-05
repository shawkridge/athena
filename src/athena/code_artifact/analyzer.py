"""AST-based code analyzer for extracting entities and metrics."""

import ast
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import CodeEntity, ComplexityLevel, ComplexityMetrics, EntityType, TypeSignature


class CodeAnalyzer:
    """Analyze Python code using AST for entity extraction and metrics."""

    def __init__(self):
        """Initialize analyzer."""
        self.current_file_path: Optional[str] = None
        self.current_module_id: Optional[int] = None

    def analyze_file(self, file_path: str, project_id: int, module_id: Optional[int] = None) -> list[CodeEntity]:
        """Analyze a Python file and extract code entities.

        Args:
            file_path: Path to Python file
            project_id: Project ID for storing entities
            module_id: ID of module entity (if analyzing as part of module)

        Returns:
            List of extracted CodeEntity objects
        """
        self.current_file_path = file_path
        self.current_module_id = module_id
        entities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return entities

        # Parse AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return entities

        # Create module entity
        module_entity = CodeEntity(
            project_id=project_id,
            name=Path(file_path).stem,
            entity_type=EntityType.MODULE,
            file_path=file_path,
            start_line=1,
            end_line=len(source_code.split("\n")),
            docstring=ast.get_docstring(tree),
        )
        entities.append(module_entity)

        # Extract top-level entities
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.col_offset == 0:  # Top-level function
                    entity = self._extract_function_entity(node, project_id, file_path, module_entity)
                    if entity:
                        entities.append(entity)

            elif isinstance(node, ast.ClassDef):
                if node.col_offset == 0:  # Top-level class
                    class_entity = self._extract_class_entity(node, project_id, file_path, module_entity)
                    if class_entity:
                        entities.append(class_entity)
                        # Extract methods
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                method_entity = self._extract_function_entity(
                                    item, project_id, file_path, module_entity, parent_entity=class_entity
                                )
                                if method_entity:
                                    entities.append(method_entity)

        return entities

    def _extract_function_entity(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        project_id: int,
        file_path: str,
        module_entity: CodeEntity,
        parent_entity: Optional[CodeEntity] = None,
    ) -> Optional[CodeEntity]:
        """Extract function entity from AST node."""
        try:
            cyclomatic = self._calculate_cyclomatic_complexity(node)
            cognitive = self._calculate_cognitive_complexity(node)

            entity = CodeEntity(
                project_id=project_id,
                name=node.name,
                entity_type=EntityType.FUNCTION,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                column_offset=node.col_offset,
                docstring=ast.get_docstring(node),
                is_public=not node.name.startswith("_"),
                is_deprecated=self._is_deprecated(node),
                parent_entity_id=parent_entity.id if parent_entity else None,
                module_id=module_entity.id,
                cyclomatic_complexity=cyclomatic,
                cognitive_complexity=cognitive,
                lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 1,
            )
            return entity
        except Exception as e:
            print(f"Error extracting function {node.name}: {e}")
            return None

    def _extract_class_entity(
        self, node: ast.ClassDef, project_id: int, file_path: str, module_entity: CodeEntity
    ) -> Optional[CodeEntity]:
        """Extract class entity from AST node."""
        try:
            cyclomatic = self._calculate_cyclomatic_complexity(node)

            entity = CodeEntity(
                project_id=project_id,
                name=node.name,
                entity_type=EntityType.CLASS,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                column_offset=node.col_offset,
                docstring=ast.get_docstring(node),
                is_public=not node.name.startswith("_"),
                is_deprecated=self._is_deprecated(node),
                module_id=module_entity.id,
                cyclomatic_complexity=cyclomatic,
                cognitive_complexity=0,
                lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 1,
            )
            return entity
        except Exception as e:
            print(f"Error extracting class {node.name}: {e}")
            return None

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity using AST traversal."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each 'and'/'or' in boolean expression adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.ExceptHandler, ast.Try)):
                complexity += 1

        return complexity

    def _calculate_cognitive_complexity(self, node: ast.AST, nesting_level: int = 0) -> int:
        """Calculate cognitive complexity (incremental complexity)."""
        complexity = 0

        for child in ast.walk(node):
            if isinstance(child, ast.If):
                complexity += 1 + nesting_level
            elif isinstance(child, ast.While):
                complexity += 1 + nesting_level
            elif isinstance(child, ast.For):
                complexity += 1 + nesting_level
            elif isinstance(child, ast.AsyncFor):
                complexity += 1 + nesting_level
            elif isinstance(child, ast.Try):
                complexity += 1 + nesting_level
            elif isinstance(child, (ast.Lambda,)):
                complexity += 1

        return complexity

    def _is_deprecated(self, node: ast.FunctionDef | ast.ClassDef) -> bool:
        """Check if entity is marked as deprecated."""
        decorators = node.decorator_list if hasattr(node, "decorator_list") else []
        for dec in decorators:
            if isinstance(dec, ast.Name) and dec.id == "deprecated":
                return True
            if isinstance(dec, ast.Attribute) and dec.attr == "deprecated":
                return True
        return False

    def extract_type_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> TypeSignature:
        """Extract type signature from function node."""
        parameters = []
        for arg in node.args.args:
            param = {
                "name": arg.arg,
                "type_annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            }
            parameters.append(param)

        # Handle *args and **kwargs
        if node.args.vararg:
            parameters.append(
                {
                    "name": f"*{node.args.vararg.arg}",
                    "type_annotation": ast.unparse(node.args.vararg.annotation)
                    if node.args.vararg.annotation
                    else None,
                }
            )
        if node.args.kwarg:
            parameters.append(
                {
                    "name": f"**{node.args.kwarg.arg}",
                    "type_annotation": ast.unparse(node.args.kwarg.annotation)
                    if node.args.kwarg.annotation
                    else None,
                }
            )

        return_type = ast.unparse(node.returns) if node.returns else None

        # Check decorators
        is_async = isinstance(node, ast.AsyncFunctionDef)
        is_classmethod = any(
            isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list
        )
        is_staticmethod = any(
            isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list
        )

        return TypeSignature(
            parameters=parameters,
            return_type=return_type,
            is_async=is_async,
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
        )

    def analyze_imports(self, file_path: str) -> list[tuple[str, Optional[str]]]:
        """Extract import statements from a file.

        Returns:
            List of (module, entity) tuples
        """
        imports = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, None))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append((module, alias.name))

        return imports

    @staticmethod
    def calculate_maintainability_index(metrics: ComplexityMetrics) -> float:
        """Calculate maintainability index (0-100, higher is better).

        Based on: https://www.ndepend.com/docs/code-metrics#MI
        """
        # Simplified MI calculation
        # MI = 171 - 5.2*ln(Halstead Volume) - 0.23*CC - 16.2*ln(LOC)

        import math

        halstead = max(metrics.halstead_volume, 1)
        cyclomatic = max(metrics.cyclomatic_complexity, 1)
        loc = max(metrics.lines_of_code, 1)

        mi = 171 - 5.2 * math.log(halstead) - 0.23 * cyclomatic - 16.2 * math.log(loc)

        # Clamp to 0-100 range
        return max(0, min(100, mi))

    @staticmethod
    def get_complexity_level(cyclomatic: int) -> ComplexityLevel:
        """Map cyclomatic complexity to complexity level."""
        if cyclomatic <= 2:
            return ComplexityLevel.LOW
        elif cyclomatic <= 10:
            return ComplexityLevel.MEDIUM
        elif cyclomatic <= 30:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.VERY_HIGH

    @staticmethod
    def calculate_halstead_metrics(node: ast.AST) -> tuple[int, int, int, int]:
        """Calculate Halstead metrics from AST.

        Returns:
            (distinct_operators, distinct_operands, total_operators, total_operands)
        """
        operators = set()
        operands = set()
        op_count = 0
        operand_count = 0

        for child in ast.walk(node):
            # Count operators
            if isinstance(child, (ast.BinOp, ast.UnaryOp, ast.Compare)):
                operators.add(type(child).__name__)
                op_count += 1

            # Count operands (variable names, literals)
            if isinstance(child, ast.Name):
                operands.add(child.id)
                operand_count += 1
            elif isinstance(child, (ast.Constant, ast.Num)):
                operands.add(str(child))
                operand_count += 1

        return len(operators), len(operands), op_count, operand_count
