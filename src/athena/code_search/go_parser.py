"""Go code parser implementation."""

import re
import logging
from typing import List, Set
from pathlib import Path

from .models import CodeUnit

logger = logging.getLogger(__name__)


class GoParser:
    """
    Parse Go code.

    Extracts:
    - Functions (regular, receiver methods)
    - Structs and interfaces
    - Imports (single and grouped)
    - Type definitions and constants
    """

    def __init__(self, language: str = "go"):
        """Initialize Go parser.

        Args:
            language: "go"
        """
        self.language = language

    def extract_functions(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract functions from Go code.

        Handles:
        - Top-level functions: func name() {}
        - Methods with receivers: func (r Receiver) methodName() {}
        - Multiple return values: func name() (int, error) {}
        - Variadic parameters: func name(args ...string) {}

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for functions
        """
        functions = []
        lines = code.split("\n")

        # Pattern for function declarations
        # Matches: func [receiver] functionName(params) [returns]
        func_pattern = r"^func\s+(?:\([^)]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\("

        for i, line in enumerate(lines):
            match = re.match(func_pattern, line)
            if match:
                func_name = match.group(1)
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
                    docstring=self._extract_comment(lines, i),
                    dependencies=self._extract_function_dependencies(code, i, func_name),
                )
                functions.append(unit)

        return functions

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract structs and interfaces from Go code.

        Handles:
        - Struct definitions: type Name struct { ... }
        - Interface definitions: type Name interface { ... }
        - Type aliases: type Name = BaseType

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for structs/interfaces
        """
        classes = []
        lines = code.split("\n")

        # Pattern for struct/interface declarations
        # Matches: type TypeName struct|interface { ... }
        type_pattern = r"^type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(struct|interface)(?:\s|\{)"

        for i, line in enumerate(lines):
            match = re.match(type_pattern, line)
            if match:
                type_name = match.group(1)
                type_kind = match.group(2)

                # Extract struct/interface body
                start_line = i
                end_line = self._find_type_end(lines, i)

                # Extract embedded/interface types (dependencies)
                body = "\n".join(lines[start_line : end_line + 1])
                dependencies = self._extract_type_dependencies(body, type_kind)

                signature = f"type {type_name} {type_kind}"

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:{type_kind}:{type_name}:{i}",
                    type=type_kind,
                    name=type_name,
                    signature=signature,
                    code=body,
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=end_line + 1,
                    docstring=self._extract_comment(lines, i),
                    dependencies=dependencies,
                )
                classes.append(unit)

        return classes

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract imports from Go code.

        Handles:
        - Single imports: import "package"
        - Grouped imports: import ( "pkg1" "pkg2" )
        - Import aliases: import alias "package"

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for imports
        """
        imports = []
        lines = code.split("\n")

        # Pattern for single import
        single_pattern = r'^import\s+(?:(\w+)\s+)?"([^"]+)"'

        # Pattern for grouped imports
        grouped_pattern = r"^import\s*\("

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for grouped imports
            if re.match(grouped_pattern, line):
                # Extract all imports in the group
                i += 1
                while i < len(lines):
                    group_line = lines[i].strip()
                    if group_line == ")":
                        break

                    # Parse individual import line in group
                    import_match = re.match(r'(?:(\w+)\s+)?"([^"]+)"', group_line)
                    if import_match:
                        import_path = import_match.group(2)
                        unit = CodeUnit(
                            id=f"{Path(file_path).stem}:import:{import_path}:{i}",
                            type="import",
                            name=import_path,
                            signature=group_line.strip(),
                            code=group_line.strip(),
                            file_path=file_path,
                            start_line=i + 1,
                            end_line=i + 1,
                            docstring="",
                            dependencies=[],
                        )
                        imports.append(unit)
                    i += 1
            else:
                # Check for single import
                match = re.match(single_pattern, line)
                if match:
                    import_path = match.group(2)

                    unit = CodeUnit(
                        id=f"{Path(file_path).stem}:import:{import_path}:{i}",
                        type="import",
                        name=import_path,
                        signature=line.strip(),
                        code=line.strip(),
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=i + 1,
                        docstring="",
                        dependencies=[],
                    )
                    imports.append(unit)

            i += 1

        return imports

    def extract_all(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract all code units from Go code.

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of all CodeUnit objects
        """
        try:
            units = []
            units.extend(self.extract_imports(code, file_path))
            units.extend(self.extract_classes(code, file_path))
            units.extend(self.extract_functions(code, file_path))
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
            if "{" in lines[i]:
                break

        signature = " ".join(signature_lines)
        # Limit to first 150 chars
        return signature[:150] + ("..." if len(signature) > 150 else "")

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

    def _find_type_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of a struct/interface.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            End line index
        """
        return self._find_function_end(lines, start_line)

    def _extract_comment(self, lines: List[str], start_line: int) -> str:
        """Extract comment for documentation.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            Comment content
        """
        if start_line == 0:
            return ""

        comment_lines = []
        i = start_line - 1

        # Look for comments
        while i >= 0:
            line = lines[i].strip()
            if line.startswith("//"):
                comment_lines.insert(0, line)
                i -= 1
            else:
                break

        return " ".join(comment_lines)[:250]

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
        pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
        matches = re.findall(pattern, func_body)

        # Filter out keywords and the function itself
        keywords = {
            "if",
            "for",
            "switch",
            "case",
            "select",
            "go",
            "defer",
            "panic",
            "make",
            "len",
            "cap",
            "append",
            "copy",
            "delete",
            "close",
            "complex",
            "real",
            "imag",
            "new",
            "print",
            "println",
            "error",
            "type",
            "func",
            "interface",
            "struct",
            "range",
            "return",
            "package",
            "import",
            "const",
            "var",
            "chan",
        }

        dependencies = {
            m for m in matches if m not in keywords and m != func_name and not m[0].isupper()
        }

        return dependencies

    def _extract_type_dependencies(self, body: str, type_kind: str) -> List[str]:
        """Extract dependencies from struct/interface definition.

        For structs: embedded types
        For interfaces: embedded interfaces

        Args:
            body: Struct/interface body code
            type_kind: "struct" or "interface"

        Returns:
            List of dependency names
        """
        dependencies = []

        if type_kind == "struct":
            # Look for embedded types (types without field names)
            # e.g., "Reader" in "type Writer struct { Reader }"
            pattern = r"^\s+([A-Z][a-zA-Z0-9_]*)\s*$"
            for line in body.split("\n"):
                match = re.match(pattern, line)
                if match:
                    dependencies.append(match.group(1))
        elif type_kind == "interface":
            # Look for interface method signatures (contain parentheses)
            # and embedded interfaces
            pattern = r"^\s+([A-Z][a-zA-Z0-9_]*)\s*(?:\(|$)"
            for line in body.split("\n"):
                match = re.match(pattern, line)
                if match:
                    dependencies.append(match.group(1))

        return dependencies
