"""Java code parser implementation."""

import re
import logging
from typing import List, Set
from pathlib import Path

from .models import CodeUnit

logger = logging.getLogger(__name__)


class JavaParser:
    """
    Parse Java code.

    Extracts:
    - Methods (static, instance, constructors)
    - Classes (with inheritance and interfaces)
    - Imports (single and wildcard)
    - Type annotations and generics
    """

    def __init__(self, language: str = "java"):
        """Initialize Java parser.

        Args:
            language: "java"
        """
        self.language = language

    def extract_functions(
        self, code: str, file_path: str
    ) -> List[CodeUnit]:
        """Extract methods from Java code.

        Handles:
        - Regular methods: public/private/protected void/String method()
        - Static methods: public static void method()
        - Constructors: public ClassName()
        - Abstract methods: abstract void method()
        - Generic methods: public <T> T method()

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for methods
        """
        methods = []
        lines = code.split("\n")

        # Pattern for method declarations (handles modifiers, return types, etc.)
        # Matches: [modifiers] [<generics>] returnType methodName(params)
        method_pattern = r"^\s*(?:public|private|protected|static|abstract|final|\s)*(?:<[^>]+>\s*)?(?:\w+(?:<[^>]+>)?(?:\[\])*\s+)?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\("

        # Constructor pattern (no return type, same name as class)
        constructor_pattern = r"^\s*(?:public|private|protected|final|\s)*([A-Z][a-zA-Z0-9_$]*)\s*\("

        # Extract class name for constructor matching
        class_name = self._extract_class_name(code)

        for i, line in enumerate(lines):
            # Try constructor first
            constructor_match = re.match(constructor_pattern, line)
            if constructor_match and constructor_match.group(1) == class_name:
                method_name = constructor_match.group(1)
                signature = self._extract_method_signature(code, i)

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:method:{method_name}:{i}",
                    type="method",
                    name=method_name,
                    signature=signature,
                    code=self._extract_method_body(code, i),
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=self._find_method_end(lines, i),
                    docstring=self._extract_javadoc(lines, i),
                    dependencies=self._extract_method_dependencies(code, i, method_name),
                )
                methods.append(unit)
            else:
                # Try regular method
                method_match = re.match(method_pattern, line)
                if method_match and "@" not in line:  # Skip annotations on same line
                    method_name = method_match.group(1)

                    # Skip if it's a variable declaration
                    if method_name[0].islower():  # Methods typically lowercase
                        signature = self._extract_method_signature(code, i)

                        unit = CodeUnit(
                            id=f"{Path(file_path).stem}:method:{method_name}:{i}",
                            type="method",
                            name=method_name,
                            signature=signature,
                            code=self._extract_method_body(code, i),
                            file_path=file_path,
                            start_line=i + 1,
                            end_line=self._find_method_end(lines, i),
                            docstring=self._extract_javadoc(lines, i),
                            dependencies=self._extract_method_dependencies(code, i, method_name),
                        )
                        methods.append(unit)

        return methods

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract classes from Java code.

        Handles:
        - Class declarations
        - Class inheritance (extends)
        - Interface implementation (implements)
        - Generic class parameters
        - Abstract classes
        - Inner classes (at appropriate level)

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for classes
        """
        classes = []
        lines = code.split("\n")

        # Pattern for class declarations
        # Matches: [modifiers] class Name [<generics>] [extends Base] [implements Interface1, Interface2]
        class_pattern = r"^\s*(?:public|final|abstract|\s)*class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)"

        for i, line in enumerate(lines):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)

                # Extract class body
                class_start = i
                class_end = self._find_class_end(lines, i)

                # Extract base class and interfaces
                base_class = None
                interfaces = []

                extends_match = re.search(r"extends\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", line)
                if extends_match:
                    base_class = extends_match.group(1)

                implements_match = re.search(r"implements\s+(.+?)(?:\{|$)", line)
                if implements_match:
                    interfaces_str = implements_match.group(1)
                    interfaces = [i.strip() for i in interfaces_str.split(",")]

                # Build dependencies
                dependencies = []
                if base_class:
                    dependencies.append(base_class)
                dependencies.extend(interfaces)

                signature = f"class {class_name}"
                if base_class:
                    signature += f" extends {base_class}"
                if interfaces:
                    signature += f" implements {', '.join(interfaces)}"

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:class:{class_name}:{i}",
                    type="class",
                    name=class_name,
                    signature=signature,
                    code="\n".join(lines[class_start : class_end + 1]),
                    file_path=file_path,
                    start_line=i + 1,
                    end_line=class_end + 1,
                    docstring=self._extract_javadoc(lines, i),
                    dependencies=dependencies,
                )
                classes.append(unit)

        return classes

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract imports from Java code.

        Handles:
        - Single imports: import java.util.List;
        - Wildcard imports: import java.util.*;
        - Static imports: import static java.util.Collections.*;

        Args:
            code: Source code
            file_path: File path for context

        Returns:
            List of CodeUnit objects for imports
        """
        imports = []
        lines = code.split("\n")

        # Pattern for imports
        import_pattern = r"^\s*import\s+(?:static\s+)?(.+?);\s*$"

        for i, line in enumerate(lines):
            match = re.match(import_pattern, line)
            if match:
                import_spec = match.group(1).strip()

                # Determine import type
                import_type = "import_wildcard" if import_spec.endswith("*") else "import"

                unit = CodeUnit(
                    id=f"{Path(file_path).stem}:import:{import_spec}:{i}",
                    type=import_type,
                    name=import_spec,
                    signature=line.strip(),
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
        """Extract all code units from Java code.

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

    def _extract_class_name(self, code: str) -> str:
        """Extract the main class name from code.

        Args:
            code: Source code

        Returns:
            Class name or empty string
        """
        # Look for public class first, then any class
        public_match = re.search(r"public\s+(?:abstract\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", code)
        if public_match:
            return public_match.group(1)

        class_match = re.search(r"class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", code)
        if class_match:
            return class_match.group(1)

        return ""

    def _extract_method_signature(self, code: str, start_line: int) -> str:
        """Extract method signature.

        Args:
            code: Source code
            start_line: Starting line index

        Returns:
            Method signature string
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

    def _extract_method_body(self, code: str, start_line: int) -> str:
        """Extract method body.

        Args:
            code: Source code
            start_line: Starting line index

        Returns:
            Method body code
        """
        lines = code.split("\n")
        end_line = self._find_method_end(lines, start_line)
        return "\n".join(lines[start_line : end_line + 1])

    def _find_method_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of a method.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            End line index
        """
        brace_count = 0
        in_method = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            brace_count += line.count("{")
            brace_count -= line.count("}")

            if "{" in line:
                in_method = True

            if in_method and brace_count == 0:
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
        return self._find_method_end(lines, start_line)

    def _extract_javadoc(self, lines: List[str], start_line: int) -> str:
        """Extract JavaDoc comment.

        Args:
            lines: Code lines
            start_line: Starting line index

        Returns:
            JavaDoc content
        """
        if start_line == 0:
            return ""

        javadoc_lines = []
        i = start_line - 1

        # Look for JavaDoc or comment
        while i >= 0:
            line = lines[i].strip()
            if line.endswith("*/"):
                # Found end of block comment
                while i >= 0:
                    javadoc_lines.insert(0, lines[i].strip())
                    if lines[i].strip().startswith("/*"):
                        break
                    i -= 1
                break
            elif line.startswith("//"):
                # Single-line comment
                javadoc_lines.insert(0, line)
            else:
                break
            i -= 1

        return " ".join(javadoc_lines)[:250]

    def _extract_method_dependencies(
        self, code: str, start_line: int, method_name: str
    ) -> Set[str]:
        """Extract method dependencies (called methods).

        Args:
            code: Source code
            start_line: Starting line index
            method_name: Method name

        Returns:
            Set of dependency names
        """
        lines = code.split("\n")
        end_line = self._find_method_end(lines, start_line)
        method_body = "\n".join(lines[start_line : end_line + 1])

        # Find method calls (simple heuristic)
        pattern = r"\.?([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\("
        matches = re.findall(pattern, method_body)

        # Filter out keywords and the method itself
        keywords = {
            "if", "while", "for", "switch", "catch", "try", "synchronized",
            "return", "throw", "new", "instanceof", "super", "this",
            "public", "private", "protected", "static", "final", "abstract",
            "class", "interface", "enum", "extends", "implements",
        }

        dependencies = {
            m for m in matches
            if m not in keywords and m != method_name and not m[0].isupper()
        }

        return dependencies
