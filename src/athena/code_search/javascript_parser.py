"""JavaScript/TypeScript code parser implementation."""

import re
import logging
from typing import List, Set
from pathlib import Path

from .models import CodeUnit

logger = logging.getLogger(__name__)


class JavaScriptParser:
    """
    Parse JavaScript and TypeScript code.

    Extracts:
    - Functions (regular, arrow, async)
    - Classes (ES6 and class expressions)
    - Imports (ES6 modules)
    - Type annotations (TypeScript)
    """

    def __init__(self, language: str = "javascript"):
        """Initialize JavaScript parser.

        Args:
            language: "javascript" or "typescript"
        """
        self.language = language
        self.is_typescript = language == "typescript"

    def extract_functions(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract functions from JavaScript code.

        Handles:
        - Regular functions: function name() {}
        - Arrow functions: const name = () => {}
        - Async functions: async function name() {}
        - Class methods: method() {}

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for functions
        """
        functions = []
        lines = code.split("\n")

        # Pattern for regular function declarations
        func_pattern = r"^\s*(async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\("
        # Pattern for arrow functions
        arrow_pattern = (
            r"(const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(async\s*)?\([^)]*\)\s*=>"
        )
        arrow_pattern_simple = r"(const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(async\s*)?[a-zA-Z_$][a-zA-Z0-9_$]*\s*=>"

        for i, line in enumerate(lines):
            # Regular function
            match = re.match(func_pattern, line)
            if match:
                is_async = match.group(1) is not None
                func_name = match.group(2)
                signature = self._extract_function_signature(code, i)

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:function:{func_name}:{i}",
                    type="function",
                    name=func_name,
                    signature=signature,
                    code=self._extract_function_body(code, i),
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=self._find_function_end(lines, i),
                    docstring=self._extract_docstring(lines, i),
                    dependencies=self._extract_function_dependencies(code, i, func_name),
                )
                functions.append(unit)

            # Arrow function
            for arrow_pat in [arrow_pattern, arrow_pattern_simple]:
                match = re.match(arrow_pat, line)
                if match:
                    func_name = match.group(2)
                    signature = f"{func_name} = ..."

                    unit = CodeUnit(
                        id=f"{Path(file_path).stem}:function:{func_name}:{i}",
                        type="function",
                        name=func_name,
                        signature=signature,
                        code=self._extract_function_body(code, i),
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=self._find_function_end(lines, i),
                        docstring=self._extract_docstring(lines, i),
                        dependencies=self._extract_function_dependencies(code, i, func_name),
                    )
                    functions.append(unit)
                    break

        return functions

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract classes from JavaScript code.

        Handles:
        - ES6 class declarations
        - Class methods and constructors
        - TypeScript class properties

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for classes
        """
        classes = []
        lines = code.split("\n")

        # Pattern for class declarations
        class_pattern = r"^\s*(export\s+)?(abstract\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)"

        for i, line in enumerate(lines):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(3)

                # Extract class body
                class_start = i
                class_end = self._find_class_end(lines, i)

                # Extract methods
                methods = []
                for j in range(class_start, class_end):
                    method_match = re.search(
                        r"(constructor|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(",
                        lines[j],
                    )
                    if method_match:
                        methods.append(method_match.group(1))

                signature = f"class {class_name}"
                if "extends" in line:
                    extends_match = re.search(r"extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", line)
                    if extends_match:
                        signature += f" extends {extends_match.group(1)}"

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:class:{class_name}:{i}",
                    type="class",
                    name=class_name,
                    signature=signature,
                    code="\n".join(lines[class_start : class_end + 1]),
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=class_end + 1,
                    docstring=self._extract_docstring(lines, i),
                    dependencies=methods + self._extract_class_dependencies(code, i, class_name),
                )
                classes.append(unit)

        return classes

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract imports from JavaScript code.

        Handles:
        - ES6 imports: import x from 'module'
        - Named imports: import { x, y } from 'module'
        - Default imports: import default from 'module'
        - CommonJS requires: const x = require('module')

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for imports
        """
        imports = []
        lines = code.split("\n")

        # Pattern for ES6 imports
        es6_pattern = r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]"
        # Pattern for CommonJS requires
        cjs_pattern = r"^\s*(const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"

        for i, line in enumerate(lines):
            # ES6 import
            match = re.match(es6_pattern, line)
            if match:
                spec = match.group(1).strip()
                module = match.group(2)

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:import:{module}:{i}",
                    type="import_es6",
                    name=module,
                    signature=f"import {spec} from '{module}'",
                    code=line.strip(),
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=i + 1,
                    docstring="",
                    dependencies=[],
                )
                imports.append(unit)

            # CommonJS require
            else:
                match = re.match(cjs_pattern, line)
                if match:
                    var_name = match.group(2)
                    module = match.group(3)

                    unit = CodeUnit(
                        id=f"{Path(file_path).stem}:import:{module}:{i}",
                        type="import_cjs",
                        name=var_name,
                        signature=f"const {var_name} = require('{module}')",
                        code=line.strip(),
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=i + 1,
                        docstring="",
                        dependencies=[],
                    )
                    imports.append(unit)

        return imports

    def extract_all(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract all code units from JavaScript/TypeScript code.

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of all CodeUnit objects
        """
        try:
            units = []
            units.extend(self.extract_functions(code, file_path))
            units.extend(self.extract_classes(code, file_path))
            units.extend(self.extract_imports(code, file_path))
            return units
        except Exception as e:
            logger.warning(f"Error extracting from {file_path}: {e}")
            return []

    def _extract_function_signature(self, code: str, start_line: int) -> str:
        """Extract function signature.

        Args:
            code: Source code
            start_line: Starting line index

        Returns:
            Function signature string
        """
        lines = code.split("\n")
        signature_lines = []

        for i in range(start_line, min(start_line + 5, len(lines))):
            signature_lines.append(lines[i].strip())
            if ")" in lines[i]:
                break

        signature = " ".join(signature_lines)
        # Limit to first 100 chars
        return signature[:100] + ("..." if len(signature) > 100 else "")

    def _extract_function_body(self, code: str, start_line: int) -> str:
        """Extract function body.

        Args:
            code: Source code
            start_line: Starting line index

        Returns:
            Function body code
        """
        lines = code.split("\n")
        end_line = self._find_function_end(lines, start_line)
        return "\n".join(lines[start_line : end_line + 1])

    def _find_function_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of a function.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            End line index
        """
        brace_count = 0
        in_function = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            brace_count += line.count("{")
            brace_count -= line.count("}")

            if "{" in line:
                in_function = True

            if in_function and brace_count == 0:
                return i

        return min(start_line + 50, len(lines) - 1)

    def _find_class_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of a class.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            End line index
        """
        return self._find_function_end(lines, start_line)

    def _extract_docstring(self, lines: List[str], start_line: int) -> str:
        """Extract docstring or JSDoc comment.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            Docstring content
        """
        if start_line == 0:
            return ""

        docstring_lines = []
        i = start_line - 1

        # Look for JSDoc or comment
        while i >= 0:
            line = lines[i].strip()
            if line.endswith("*/"):
                # Found end of block comment
                while i >= 0:
                    docstring_lines.insert(0, lines[i].strip())
                    if lines[i].strip().startswith("/*"):
                        break
                    i -= 1
                break
            elif line.startswith("//"):
                # Single-line comment
                docstring_lines.insert(0, line)
            else:
                break
            i -= 1

        return " ".join(docstring_lines)[:200]

    def _extract_function_dependencies(
        self, code: str, start_line: int, func_name: str
    ) -> Set[str]:
        """Extract function dependencies (called functions).

        Args:
            code: Source code
            start_line: Starting line index
            func_name: Function name

        Returns:
            Set of dependency names
        """
        lines = code.split("\n")
        end_line = self._find_function_end(lines, start_line)
        func_body = "\n".join(lines[start_line : end_line + 1])

        # Find function calls (simple heuristic)
        pattern = r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\("
        matches = re.findall(pattern, func_body)

        # Filter out keywords and the function itself
        keywords = {
            "if",
            "while",
            "for",
            "switch",
            "catch",
            "function",
            "class",
            "return",
            "throw",
            "async",
            "await",
            "new",
            "typeof",
            "instanceof",
            "this",
            "super",
            "import",
            "export",
            "from",
            "as",
            "default",
        }

        dependencies = {m for m in matches if m not in keywords and m != func_name}

        return dependencies

    def _extract_class_dependencies(self, code: str, start_line: int, class_name: str) -> List[str]:
        """Extract class dependencies (base class, used classes).

        Args:
            code: Source code
            start_line: Starting line index
            class_name: Class name

        Returns:
            List of dependency names
        """
        lines = code.split("\n")
        line = lines[start_line]

        dependencies = []

        # Extract base class
        if "extends" in line:
            match = re.search(r"extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", line)
            if match:
                dependencies.append(match.group(1))

        # Extract implemented interfaces (TypeScript)
        if "implements" in line:
            match = re.search(r"implements\s+(.+?)(?:\{|$)", line)
            if match:
                interfaces = match.group(1).split(",")
                dependencies.extend([i.strip() for i in interfaces])

        return dependencies
