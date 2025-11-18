"""
Symbol Parser for Multiple Languages

Provides language-specific parsing to extract symbols from source code.
Supports Python (via AST), JavaScript, and TypeScript.

Author: Claude Code
Date: 2025-10-31
"""

import ast
import re
from pathlib import Path
from typing import List, Optional

from athena.symbols.symbol_models import (
    Symbol,
    SymbolType,
    SymbolMetrics,
    SymbolAnalysisResult,
    create_symbol,
)
from athena.symbols.java_parser import JavaSymbolParser
from athena.symbols.go_parser import GoSymbolParser
from athena.symbols.rust_parser import RustSymbolParser
from athena.symbols.csharp_parser import CSharpSymbolParser
from athena.symbols.package_json_parser import PackageJsonParser
from athena.symbols.tsconfig_parser import TsConfigParser
from athena.symbols.babel_config_parser import BabelConfigParser
from athena.symbols.eslint_config_parser import ESLintConfigParser
from athena.symbols.jest_config_parser import JestConfigParser
from athena.symbols.prettier_config_parser import PrettierConfigParser
from athena.symbols.editorconfig_parser import EditorConfigParser


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================


class LanguageDetector:
    """Detects programming language from file extension."""

    LANGUAGE_MAP = {
        ".py": "python",
        ".pyw": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        "package.json": "package.json",
        "package-lock.json": "package-lock.json",
        "yarn.lock": "yarn.lock",
        "tsconfig.json": "tsconfig.json",
        "babel.config.json": "babel.config.json",
        "babel.config.js": "babel.config.js",
        ".eslintrc.json": "eslintrc.json",
        ".eslintrc.js": "eslintrc.js",
        ".eslintrc": "eslintrc",
        "jest.config.json": "jest.config.json",
        "jest.config.js": "jest.config.js",
        ".prettierrc": "prettierrc",
        ".prettierrc.json": "prettierrc.json",
        ".prettierrc.js": "prettierrc.js",
        "prettier.config.js": "prettier.config.js",
        ".editorconfig": "editorconfig",
    }

    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """
        Detect language from file extension or filename.

        Args:
            file_path: Path to source file

        Returns:
            Language name or None if not recognized
        """
        path = Path(file_path)
        filename = path.name.lower()

        # Check full filename first (for package.json, yarn.lock, etc.)
        if filename in cls.LANGUAGE_MAP:
            return cls.LANGUAGE_MAP[filename]

        # Check extension
        ext = path.suffix.lower()
        return cls.LANGUAGE_MAP.get(ext)


# ============================================================================
# PYTHON PARSER (AST-based)
# ============================================================================


class PythonSymbolParser:
    """Parse Python source code to extract symbols using AST."""

    @staticmethod
    def parse_file(file_path: str, code: str) -> SymbolAnalysisResult:
        """
        Parse Python file and extract symbols.

        Args:
            file_path: Path to Python file
            code: Source code content

        Returns:
            SymbolAnalysisResult with extracted symbols
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return SymbolAnalysisResult(
                file_path=file_path,
                language="python",
                symbols=[],
                parse_errors=[f"Syntax error at line {e.lineno}: {e.msg}"],
                total_lines=len(code.split("\n")),
                success=False,
            )

        symbols = []
        lines = code.split("\n")

        # Extract module-level symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbol = PythonSymbolParser._extract_function(node, file_path, lines, namespace="")
                if symbol:
                    symbols.append(symbol)

            elif isinstance(node, ast.ClassDef):
                class_symbol = PythonSymbolParser._extract_class(
                    node, file_path, lines, namespace=""
                )
                if class_symbol:
                    symbols.append(class_symbol)

                    # Extract methods from class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_symbol = PythonSymbolParser._extract_function(
                                item, file_path, lines, namespace=class_symbol.name
                            )
                            if method_symbol:
                                symbols.append(method_symbol)

            elif isinstance(node, ast.AsyncFunctionDef):
                symbol = PythonSymbolParser._extract_function(
                    node, file_path, lines, namespace="", is_async=True
                )
                if symbol:
                    symbols.append(symbol)

        return SymbolAnalysisResult(
            file_path=file_path,
            language="python",
            symbols=symbols,
            total_lines=len(lines),
            success=True,
        )

    @staticmethod
    def _extract_function(
        node: ast.FunctionDef,
        file_path: str,
        lines: List[str],
        namespace: str,
        is_async: bool = False,
    ) -> Optional[Symbol]:
        """Extract function symbol from AST node."""
        try:
            # Get docstring
            docstring = ast.get_docstring(node) or ""

            # Get source code
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            code_lines = lines[line_start - 1 : line_end]
            code = "\n".join(code_lines)

            # Get signature
            args = node.args
            param_count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
            params = ", ".join([arg.arg for arg in args.args[:3]])  # First 3 params
            if len(args.args) > 3:
                params += ", ..."
            signature = f"({params})"

            # Compute basic metrics
            metrics = PythonSymbolParser._compute_metrics(node, code)

            # Determine if deprecated
            is_deprecated = any(
                isinstance(d, ast.Name) and d.id == "deprecated" for d in node.decorator_list
            )

            full_qname = f"{namespace}.{node.name}" if namespace else node.name

            return create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.ASYNC_FUNCTION if is_async else SymbolType.FUNCTION,
                name=node.name,
                namespace=namespace,
                signature=signature,
                line_start=line_start,
                line_end=line_end,
                code=code,
                docstring=docstring,
                language="python",
                visibility="private" if node.name.startswith("_") else "public",
                is_async=is_async,
                is_deprecated=is_deprecated,
                metrics=metrics,
            )

        except (AttributeError, ValueError, TypeError, IndexError):
            # Handle parsing errors gracefully
            return None

    @staticmethod
    def _extract_class(
        node: ast.ClassDef, file_path: str, lines: List[str], namespace: str
    ) -> Optional[Symbol]:
        """Extract class symbol from AST node."""
        try:
            docstring = ast.get_docstring(node) or ""

            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            code_lines = lines[line_start - 1 : line_end]
            code = "\n".join(code_lines)

            # Get base classes
            bases = ", ".join([b.id if isinstance(b, ast.Name) else str(b) for b in node.bases[:3]])
            signature = f"({bases})" if bases else "()"

            metrics = PythonSymbolParser._compute_metrics(node, code)

            is_dataclass = any(
                isinstance(d, ast.Name) and d.id == "dataclass" for d in node.decorator_list
            )

            full_qname = f"{namespace}.{node.name}" if namespace else node.name

            return create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.DATACLASS if is_dataclass else SymbolType.CLASS,
                name=node.name,
                namespace=namespace,
                signature=signature,
                line_start=line_start,
                line_end=line_end,
                code=code,
                docstring=docstring,
                language="python",
                visibility="private" if node.name.startswith("_") else "public",
                metrics=metrics,
            )

        except (AttributeError, ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _compute_metrics(node: ast.AST, code: str) -> SymbolMetrics:
        """Compute basic metrics from AST node and code."""
        # Lines of code (excluding comments and docstrings)
        code_lines = [
            line.strip()
            for line in code.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        lines_of_code = len(code_lines)

        # Cyclomatic complexity (count branches)
        cyclomatic = 1
        for sub_node in ast.walk(node):
            if isinstance(sub_node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                cyclomatic += 1

        # Nesting depth
        max_depth = 0
        for sub_node in ast.walk(node):
            depth = PythonSymbolParser._get_nesting_depth(node, sub_node, 0)
            max_depth = max(max_depth, depth)

        # Maintainability index (simplified)
        maintainability = min(100.0, 100.0 - (lines_of_code * 0.5) - (cyclomatic * 5))
        maintainability = max(0.0, maintainability)

        return SymbolMetrics(
            lines_of_code=lines_of_code,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cyclomatic + max_depth,
            parameters=0,
            nesting_depth=max_depth,
            maintainability_index=maintainability,
        )

    @staticmethod
    def _get_nesting_depth(root: ast.AST, target: ast.AST, current_depth: int) -> int:
        """Calculate nesting depth of a node within its parent."""
        if root is target:
            return current_depth
        for child in ast.iter_child_nodes(root):
            if isinstance(
                child, (ast.If, ast.For, ast.While, ast.With, ast.FunctionDef, ast.ClassDef)
            ):
                result = PythonSymbolParser._get_nesting_depth(child, target, current_depth + 1)
                if result >= 0:
                    return result
        return -1


# ============================================================================
# JAVASCRIPT/TYPESCRIPT PARSER (Regex-based)
# ============================================================================


class JavaScriptSymbolParser:
    """Parse JavaScript/TypeScript source code using regex patterns."""

    # Regex patterns for different symbol types
    FUNCTION_PATTERN = re.compile(
        r"(?:async\s+)?(?:function\s+)?(\w+)\s*\(([^)]*)\)\s*[:{]", re.MULTILINE
    )
    ARROW_FUNCTION_PATTERN = re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", re.MULTILINE
    )
    CLASS_PATTERN = re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*[{]", re.MULTILINE)
    METHOD_PATTERN = re.compile(r"(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*[:{]", re.MULTILINE)
    IMPORT_PATTERN = re.compile(
        r'(?:import|require)\s+(?:\{[^}]*\}|[\w*]+)?\s*from?\s+["\']([^"\']+)["\']', re.MULTILINE
    )

    @staticmethod
    def parse_file(file_path: str, code: str, language: str = "javascript") -> SymbolAnalysisResult:
        """
        Parse JavaScript/TypeScript file and extract symbols.

        Args:
            file_path: Path to JS/TS file
            code: Source code content
            language: "javascript" or "typescript"

        Returns:
            SymbolAnalysisResult with extracted symbols
        """
        symbols = []
        lines = code.split("\n")

        try:
            # Extract classes
            for match in JavaScriptSymbolParser.CLASS_PATTERN.finditer(code):
                symbol = JavaScriptSymbolParser._extract_class(
                    match, file_path, code, lines, language
                )
                if symbol:
                    symbols.append(symbol)

            # Extract functions
            for match in JavaScriptSymbolParser.FUNCTION_PATTERN.finditer(code):
                symbol = JavaScriptSymbolParser._extract_function(
                    match, file_path, code, lines, language, is_declaration=True
                )
                if symbol:
                    symbols.append(symbol)

            # Extract arrow functions
            for match in JavaScriptSymbolParser.ARROW_FUNCTION_PATTERN.finditer(code):
                symbol = JavaScriptSymbolParser._extract_function(
                    match, file_path, code, lines, language, is_arrow=True
                )
                if symbol:
                    symbols.append(symbol)

            # Extract imports
            for match in JavaScriptSymbolParser.IMPORT_PATTERN.finditer(code):
                symbol = JavaScriptSymbolParser._extract_import(
                    match, file_path, code, lines, language
                )
                if symbol:
                    symbols.append(symbol)

        except (AttributeError, ValueError, TypeError) as e:
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=symbols,
                parse_errors=[str(e)],
                total_lines=len(lines),
                success=len(symbols) > 0,
            )

        return SymbolAnalysisResult(
            file_path=file_path,
            language=language,
            symbols=symbols,
            total_lines=len(lines),
            success=True,
        )

    @staticmethod
    def _extract_class(
        match, file_path: str, code: str, lines: List[str], language: str
    ) -> Optional[Symbol]:
        """Extract class from regex match."""
        try:
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Find class body end
            line_end = line_num
            for i in range(line_num, min(line_num + 100, len(lines))):
                if lines[i].strip().startswith("class"):
                    line_end = i + 1
                    break

            code_lines = lines[line_num - 1 : line_end]
            class_code = "\n".join(code_lines)

            return create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                name=name,
                namespace="",
                signature="()",
                line_start=line_num,
                line_end=line_end,
                code=class_code,
                docstring="",
                language=language,
                visibility="public",
            )

        except (AttributeError, ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _extract_function(
        match,
        file_path: str,
        code: str,
        lines: List[str],
        language: str,
        is_declaration: bool = False,
        is_arrow: bool = False,
    ) -> Optional[Symbol]:
        """Extract function from regex match."""
        try:
            name = match.group(1)
            params = match.group(2) if len(match.groups()) > 1 else ""
            line_num = code[: match.start()].count("\n") + 1

            # Estimate function end (simplified - look for next function or end)
            line_end = line_num
            for i in range(line_num, min(line_num + 50, len(lines))):
                if i > line_num and re.match(r"\s*(function|const|let|var|class)", lines[i]):
                    line_end = i
                    break
            line_end = max(line_num + 1, line_end)

            code_lines = lines[line_num - 1 : line_end]
            func_code = "\n".join(code_lines)

            is_async = "async" in func_code
            symbol_type = SymbolType.ASYNC_FUNCTION if is_async else SymbolType.FUNCTION

            return create_symbol(
                file_path=file_path,
                symbol_type=symbol_type,
                name=name,
                namespace="",
                signature=f"({params})",
                line_start=line_num,
                line_end=line_end,
                code=func_code,
                docstring="",
                language=language,
                visibility="public",
                is_async=is_async,
            )

        except (AttributeError, ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _extract_import(
        match, file_path: str, code: str, lines: List[str], language: str
    ) -> Optional[Symbol]:
        """Extract import statement as a symbol."""
        try:
            module_name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            import_line = lines[line_num - 1]

            return create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.IMPORT,
                name=module_name.split("/")[-1],
                namespace="imports",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code=import_line,
                docstring="",
                language=language,
                visibility="public",
            )

        except (AttributeError, ValueError, TypeError, IndexError):
            return None


# ============================================================================
# MAIN PARSER DISPATCHER
# ============================================================================


class SymbolParser:
    """Main parser that dispatches to language-specific parsers."""

    @staticmethod
    def parse_file(file_path: str, code: Optional[str] = None) -> SymbolAnalysisResult:
        """
        Parse source file and extract symbols.

        Args:
            file_path: Path to source file
            code: Source code (if None, will read from file)

        Returns:
            SymbolAnalysisResult with extracted symbols
        """
        # Read file if code not provided
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                return SymbolAnalysisResult(
                    file_path=file_path,
                    language="unknown",
                    symbols=[],
                    parse_errors=[f"Failed to read file: {str(e)}"],
                    success=False,
                )

        # Detect language
        language = LanguageDetector.detect_language(file_path)
        if not language:
            return SymbolAnalysisResult(
                file_path=file_path,
                language="unknown",
                symbols=[],
                parse_errors=["Unsupported file type"],
                success=False,
            )

        # Dispatch to language-specific parser
        if language == "python":
            return PythonSymbolParser.parse_file(file_path, code)
        elif language in ("javascript", "typescript"):
            return JavaScriptSymbolParser.parse_file(file_path, code, language)
        elif language == "java":
            java_symbols = JavaSymbolParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="java",
                symbols=java_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "go":
            go_symbols = GoSymbolParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="go",
                symbols=go_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "rust":
            rust_symbols = RustSymbolParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="rust",
                symbols=rust_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "csharp":
            csharp_symbols = CSharpSymbolParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="csharp",
                symbols=csharp_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "package.json":
            pkg_symbols = PackageJsonParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="package.json",
                symbols=pkg_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "tsconfig.json":
            tsconfig_symbols = TsConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language="tsconfig.json",
                symbols=tsconfig_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language in ("babel.config.json", "babel.config.js"):
            babel_symbols = BabelConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=babel_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language in ("eslintrc.json", "eslintrc.js", "eslintrc"):
            eslint_symbols = ESLintConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=eslint_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language in ("jest.config.json", "jest.config.js"):
            jest_symbols = JestConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=jest_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language in ("prettierrc", "prettierrc.json", "prettierrc.js", "prettier.config.js"):
            prettier_symbols = PrettierConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=prettier_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        elif language == "editorconfig":
            editorconfig_symbols = EditorConfigParser().parse_file(file_path, code)
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=editorconfig_symbols,
                parse_errors=[],
                total_lines=len(code.split("\n")),
                success=True,
            )
        else:
            return SymbolAnalysisResult(
                file_path=file_path,
                language=language,
                symbols=[],
                parse_errors=[f"Parser not implemented for {language}"],
                success=False,
            )


__all__ = [
    "LanguageDetector",
    "PythonSymbolParser",
    "JavaScriptSymbolParser",
    "JavaSymbolParser",
    "GoSymbolParser",
    "RustSymbolParser",
    "CSharpSymbolParser",
    "PackageJsonParser",
    "TsConfigParser",
    "BabelConfigParser",
    "ESLintConfigParser",
    "JestConfigParser",
    "PrettierConfigParser",
    "EditorConfigParser",
    "SymbolParser",
]
