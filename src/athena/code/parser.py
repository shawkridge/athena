"""AST-based code parser using tree-sitter for multiple languages."""

import logging
from pathlib import Path
from typing import Any, List

from .models import CodeElement, CodeElementType, CodeLanguage

logger = logging.getLogger(__name__)


class CodeParser:
    """Parse code files using tree-sitter AST analysis.

    Supports: Python, JavaScript, TypeScript, Go, Rust, Java
    """

    def __init__(self):
        """Initialize parser with language support."""
        self._init_tree_sitter()
        self.supported_languages = {
            ".py": CodeLanguage.PYTHON,
            ".js": CodeLanguage.JAVASCRIPT,
            ".ts": CodeLanguage.TYPESCRIPT,
            ".go": CodeLanguage.GO,
            ".rs": CodeLanguage.RUST,
            ".java": CodeLanguage.JAVA,
            ".tsx": CodeLanguage.TYPESCRIPT,
            ".jsx": CodeLanguage.JAVASCRIPT,
        }

    def _init_tree_sitter(self) -> None:
        """Initialize tree-sitter language parsers.

        Note: In production, this would use actual tree-sitter bindings.
        For MVP, we use a simpler pattern-based approach.
        """
        try:
            import tree_sitter
            from tree_sitter import Language, Parser

            self.Parser = Parser
            self.Language = Language
            self._tree_sitter_available = True
            logger.info("tree-sitter initialized successfully")
        except ImportError:
            logger.warning(
                "tree-sitter not available, using fallback parsing (limited functionality)"
            )
            self._tree_sitter_available = False

    def parse_file(self, file_path: str) -> List[CodeElement]:
        """Parse a source code file and extract code elements.

        Args:
            file_path: Path to source file

        Returns:
            List of CodeElement objects extracted from the file
        """
        path = Path(file_path)

        # Determine language
        language = self.supported_languages.get(path.suffix)
        if not language:
            logger.warning(f"Unsupported file type: {path.suffix}")
            return []

        # Read file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

        # Parse based on language
        if language == CodeLanguage.PYTHON:
            return self._parse_python(file_path, source_code)
        elif language in (CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT):
            return self._parse_javascript(file_path, source_code, language)
        elif language == CodeLanguage.GO:
            return self._parse_go(file_path, source_code)
        else:
            # Fallback to regex-based extraction
            return self._parse_generic(file_path, source_code, language)

    def _parse_python(self, file_path: str, source: str) -> List[CodeElement]:
        """Parse Python source code using regex patterns.

        Extracts: functions, classes, imports, async functions
        """
        import ast

        elements = []

        try:
            # Parse AST
            tree = ast.parse(source)
            lines = source.split("\n")

            # Extract module docstring
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
            ):
                docstring = tree.body[0].value.value
            else:
                docstring = None

            # Add module-level element
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:module",
                    file_path=file_path,
                    language=CodeLanguage.PYTHON,
                    element_type=CodeElementType.MODULE,
                    name=Path(file_path).stem,
                    docstring=docstring,
                    source_code=source,
                    start_line=1,
                    end_line=len(lines),
                )
            )

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        elements.append(
                            CodeElement(
                                element_id=f"{file_path}:import:{alias.name}",
                                file_path=file_path,
                                language=CodeLanguage.PYTHON,
                                element_type=CodeElementType.IMPORT,
                                name=alias.name,
                                source_code=f"import {alias.name}",
                                start_line=node.lineno,
                                end_line=node.lineno,
                            )
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        elements.append(
                            CodeElement(
                                element_id=f"{file_path}:import:{alias.name}",
                                file_path=file_path,
                                language=CodeLanguage.PYTHON,
                                element_type=CodeElementType.IMPORT,
                                name=alias.name,
                                source_code=f"from {module} import {alias.name}",
                                start_line=node.lineno,
                                end_line=node.lineno,
                            )
                        )

            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_source = self._get_node_source(source, node)
                    docstring = ast.get_docstring(node)

                    # Get function signature
                    signature = self._get_function_signature(node)

                    elements.append(
                        CodeElement(
                            element_id=f"{file_path}:function:{node.name}",
                            file_path=file_path,
                            language=CodeLanguage.PYTHON,
                            element_type=CodeElementType.FUNCTION,
                            name=node.name,
                            docstring=docstring,
                            source_code=func_source,
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            signature=signature,
                            parameters=[arg.arg for arg in node.args.args] if node.args else [],
                            decorators=[d.id for d in node.decorator_list if hasattr(d, "id")],
                        )
                    )

                elif isinstance(node, ast.ClassDef):
                    class_source = self._get_node_source(source, node)
                    docstring = ast.get_docstring(node)

                    elements.append(
                        CodeElement(
                            element_id=f"{file_path}:class:{node.name}",
                            file_path=file_path,
                            language=CodeLanguage.PYTHON,
                            element_type=CodeElementType.CLASS,
                            name=node.name,
                            docstring=docstring,
                            source_code=class_source,
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                        )
                    )

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")

        return elements

    def _parse_javascript(
        self, file_path: str, source: str, language: CodeLanguage
    ) -> List[CodeElement]:
        """Parse JavaScript/TypeScript using regex patterns."""
        import re

        elements = []

        # Add module element
        elements.append(
            CodeElement(
                element_id=f"{file_path}:module",
                file_path=file_path,
                language=language,
                element_type=CodeElementType.MODULE,
                name=Path(file_path).stem,
                source_code=source,
                start_line=1,
                end_line=len(source.split("\n")),
            )
        )

        # Extract imports
        import_pattern = r"(?:import|require)\s+(?:.*?from\s+)?['\"]([^'\"]+)['\"]"
        for match in re.finditer(import_pattern, source):
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:import:{match.group(1)}",
                    file_path=file_path,
                    language=language,
                    element_type=CodeElementType.IMPORT,
                    name=match.group(1),
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        # Extract functions
        func_pattern = r"(?:async\s+)?(?:function|const|let|var)\s+(\w+)\s*(?:=\s*)?(?:\([^)]*\))?"
        for match in re.finditer(func_pattern, source):
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:function:{match.group(1)}",
                    file_path=file_path,
                    language=language,
                    element_type=CodeElementType.FUNCTION,
                    name=match.group(1),
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        # Extract classes
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, source):
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:class:{match.group(1)}",
                    file_path=file_path,
                    language=language,
                    element_type=CodeElementType.CLASS,
                    name=match.group(1),
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        return elements

    def _parse_go(self, file_path: str, source: str) -> List[CodeElement]:
        """Parse Go source code using regex patterns."""
        import re

        elements = []

        # Add module element
        elements.append(
            CodeElement(
                element_id=f"{file_path}:module",
                file_path=file_path,
                language=CodeLanguage.GO,
                element_type=CodeElementType.MODULE,
                name=Path(file_path).stem,
                source_code=source,
                start_line=1,
                end_line=len(source.split("\n")),
            )
        )

        # Extract imports
        import_pattern = r"import\s+(?:\"([^\"]+)\"|\\((?:[^\"]+\\n)*[^\"]+\\))"
        for match in re.finditer(import_pattern, source):
            pkg = match.group(1) or match.group(2)
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:import:{pkg}",
                    file_path=file_path,
                    language=CodeLanguage.GO,
                    element_type=CodeElementType.IMPORT,
                    name=pkg,
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        # Extract functions
        func_pattern = r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\("
        for match in re.finditer(func_pattern, source):
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:function:{match.group(1)}",
                    file_path=file_path,
                    language=CodeLanguage.GO,
                    element_type=CodeElementType.FUNCTION,
                    name=match.group(1),
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        # Extract interfaces and types
        type_pattern = r"(?:type|interface)\s+(\w+)\s*(?:struct|interface)?"
        for match in re.finditer(type_pattern, source):
            elements.append(
                CodeElement(
                    element_id=f"{file_path}:type:{match.group(1)}",
                    file_path=file_path,
                    language=CodeLanguage.GO,
                    element_type=CodeElementType.CLASS,
                    name=match.group(1),
                    source_code=match.group(0),
                    start_line=source[: match.start()].count("\n") + 1,
                    end_line=source[: match.start()].count("\n") + 1,
                )
            )

        return elements

    def _parse_generic(
        self, file_path: str, source: str, language: CodeLanguage
    ) -> List[CodeElement]:
        """Generic regex-based parser for unsupported languages."""
        elements = []

        # Add module element only
        elements.append(
            CodeElement(
                element_id=f"{file_path}:module",
                file_path=file_path,
                language=language,
                element_type=CodeElementType.MODULE,
                name=Path(file_path).stem,
                source_code=source,
                start_line=1,
                end_line=len(source.split("\n")),
            )
        )

        return elements

    @staticmethod
    def _get_node_source(source: str, node: Any) -> str:
        """Extract source code for an AST node."""
        lines = source.split("\n")
        start_line = node.lineno - 1
        end_line = node.end_lineno or node.lineno

        if 0 <= start_line < len(lines) and 0 <= end_line <= len(lines):
            return "\n".join(lines[start_line:end_line])
        return ""

    @staticmethod
    def _get_function_signature(node: Any) -> str:
        """Build function signature from AST node."""

        args = []
        if node.args:
            for arg in node.args.args:
                args.append(arg.arg)

        return f"def {node.name}({', '.join(args)})"

    def parse_directory(self, directory: str, pattern: str = "**/*.py") -> List[CodeElement]:
        """Parse all code files in a directory.

        Args:
            directory: Root directory to parse
            pattern: File pattern (glob) to match

        Returns:
            List of CodeElement objects from all files
        """
        elements = []
        root = Path(directory)

        for file_path in root.glob(pattern):
            if file_path.is_file():
                try:
                    file_elements = self.parse_file(str(file_path))
                    elements.extend(file_elements)
                    logger.debug(f"Parsed {len(file_elements)} elements from {file_path}")
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}")

        return elements
