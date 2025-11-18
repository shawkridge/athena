"""Code parser for extracting semantic units from source code."""

import ast
import logging
from typing import List, Optional

from .models import CodeUnit

logger = logging.getLogger(__name__)


class CodeParser:
    """
    Parse source code and extract semantic units.

    Uses Python's ast module for reliable parsing, with Tree-sitter
    integration available for other languages.
    """

    def __init__(self, language: str = "python"):
        """
        Initialize parser for specific language.

        Args:
            language: Programming language (default: python)
                     Supported: python, javascript, typescript, java, go
        """
        self.language = language
        self.parser = None

        # Initialize language-specific parser
        if language == "python":
            self._init_python_parser()
        elif language in ("javascript", "typescript"):
            self._init_javascript_parser(language)
        elif language == "java":
            self._init_java_parser()
        elif language == "go":
            self._init_go_parser()

    def _init_python_parser(self) -> None:
        """Initialize Python AST parser."""
        self.parser = PythonASTParser()

    def _init_javascript_parser(self, language: str) -> None:
        """Initialize JavaScript/TypeScript parser."""
        from .javascript_parser import JavaScriptParser

        self.parser = JavaScriptParser(language)

    def _init_java_parser(self) -> None:
        """Initialize Java parser."""
        from .java_parser import JavaParser

        self.parser = JavaParser()

    def _init_go_parser(self) -> None:
        """Initialize Go parser."""
        from .go_parser import GoParser

        self.parser = GoParser()

    def extract_functions(self, code: str, file_path: str) -> List[CodeUnit]:
        """
        Extract all functions from code.

        Args:
            code: Source code as string
            file_path: Path to source file

        Returns:
            List of CodeUnit objects representing functions
        """
        if self.parser is None:
            logger.warning(f"No parser available for language: {self.language}")
            return []

        return self.parser.extract_functions(code, file_path)

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """
        Extract all classes from code.

        Args:
            code: Source code as string
            file_path: Path to source file

        Returns:
            List of CodeUnit objects representing classes
        """
        if self.parser is None:
            logger.warning(f"No parser available for language: {self.language}")
            return []

        return self.parser.extract_classes(code, file_path)

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """
        Extract all imports from code.

        Args:
            code: Source code as string
            file_path: Path to source file

        Returns:
            List of CodeUnit objects representing imports
        """
        if self.parser is None:
            logger.warning(f"No parser available for language: {self.language}")
            return []

        return self.parser.extract_imports(code, file_path)

    def extract_all(self, code: str, file_path: str) -> List[CodeUnit]:
        """
        Extract all semantic units from code.

        Args:
            code: Source code as string
            file_path: Path to source file

        Returns:
            List of all CodeUnit objects
        """
        units = []
        units.extend(self.extract_functions(code, file_path))
        units.extend(self.extract_classes(code, file_path))
        units.extend(self.extract_imports(code, file_path))
        return units


class PythonASTParser:
    """Parse Python code using ast module."""

    def extract_functions(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract function definitions."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return []

        functions = []

        # Only extract top-level functions from module body
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                unit = self._node_to_function_unit(node, code, file_path)
                if unit:
                    functions.append(unit)

        return functions

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract class definitions."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return []

        classes = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                unit = self._node_to_class_unit(node, code, file_path)
                if unit:
                    classes.append(unit)

        return classes

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract import statements."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            return []

        imports = []

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                unit = self._node_to_import_unit(node, code, file_path)
                if unit:
                    imports.append(unit)

        return imports

    def _node_to_function_unit(self, node, code: str, file_path: str) -> Optional[CodeUnit]:
        """Convert function AST node to CodeUnit."""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # Get function source code
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else start_line + 1

        lines = code.split("\n")
        func_code = "\n".join(lines[start_line:end_line])

        # Extract signature
        signature = self._extract_function_signature(node, code, start_line)

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Extract dependencies (called functions)
        dependencies = self._extract_function_dependencies(node)

        return CodeUnit(
            id=f"{file_path}:{node.lineno}:{node.name}",
            type="function",
            name=node.name,
            signature=signature,
            code=func_code,
            file_path=file_path,
            start_line=node.lineno,
            end_line=end_line,
            docstring=docstring,
            dependencies=list(dependencies),
        )

    def _node_to_class_unit(
        self, node: ast.ClassDef, code: str, file_path: str
    ) -> Optional[CodeUnit]:
        """Convert class AST node to CodeUnit."""
        if not isinstance(node, ast.ClassDef):
            return None

        # Get class source code
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else start_line + 1

        lines = code.split("\n")
        class_code = "\n".join(lines[start_line:end_line])

        # Extract signature (class definition line)
        signature = self._extract_class_signature(node, code, start_line)

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Extract base classes as dependencies
        dependencies = [base.id for base in node.bases if isinstance(base, ast.Name)]

        return CodeUnit(
            id=f"{file_path}:{node.lineno}:{node.name}",
            type="class",
            name=node.name,
            signature=signature,
            code=class_code,
            file_path=file_path,
            start_line=node.lineno,
            end_line=end_line,
            docstring=docstring,
            dependencies=dependencies,
        )

    def _node_to_import_unit(self, node: ast.stmt, code: str, file_path: str) -> Optional[CodeUnit]:
        """Convert import AST node to CodeUnit."""
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else start_line + 1

        lines = code.split("\n")
        import_code = "\n".join(lines[start_line:end_line])

        # Extract import names
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            import_type = "import"
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            import_type = "import_from"
            if node.module:
                names.insert(0, node.module)
        else:
            return None

        name = ", ".join(names[:3])  # First 3 imports for name
        if len(names) > 3:
            name += f" (+{len(names) - 3})"

        return CodeUnit(
            id=f"{file_path}:{node.lineno}:import",
            type=import_type,
            name=name,
            signature=import_code.strip(),
            code=import_code,
            file_path=file_path,
            start_line=node.lineno,
            end_line=end_line,
            docstring="",
            dependencies=names,
        )

    def _extract_function_signature(self, node: ast.FunctionDef, code: str, start_line: int) -> str:
        """Extract function signature from code."""
        lines = code.split("\n")
        # Get the first line (function definition)
        return lines[start_line].strip() if start_line < len(lines) else f"def {node.name}():"

    def _extract_class_signature(self, node: ast.ClassDef, code: str, start_line: int) -> str:
        """Extract class signature from code."""
        lines = code.split("\n")
        # Get the first line (class definition)
        return lines[start_line].strip() if start_line < len(lines) else f"class {node.name}:"

    def _extract_function_dependencies(self, node: ast.FunctionDef) -> set:
        """Extract functions called within this function."""
        dependencies = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    dependencies.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    # For method calls, get the base object
                    if isinstance(child.func.value, ast.Name):
                        dependencies.add(child.func.value.id)

        return dependencies
