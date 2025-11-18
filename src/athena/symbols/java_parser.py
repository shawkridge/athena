"""Java symbol parser for extracting symbols from Java source files.

Supports:
- Classes and interfaces
- Methods and constructors
- Fields and constants
- Inner classes
- Annotations
- Visibility modifiers (public/private/protected/default)
- Generic types
- Inheritance and implementation
"""

import re
from typing import Optional
from .symbol_models import Symbol, SymbolType, create_symbol


class JavaSymbolParser:
    """Parser for Java source code using regex-based pattern matching."""

    # Regex patterns for Java constructs
    CLASS_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:(?:public|private|protected|static|final|abstract)\s+)*"
        r"class\s+(\w+)(?:\s*<[^>]+>)?\s*(?:extends\s+(\w+))?\s*(?:implements\s+([^{]+))?\s*\{",
        re.MULTILINE,
    )

    INTERFACE_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:(?:public|private|protected|static|final)\s+)*"
        r"interface\s+(\w+)(?:\s*<[^>]+>)?\s*(?:extends\s+([^{]+))?\s*\{",
        re.MULTILINE,
    )

    ENUM_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:(?:public|private|protected|static|final)\s+)*"
        r"enum\s+(\w+)\s*(?:implements\s+([^{]+))?\s*\{",
        re.MULTILINE,
    )

    METHOD_PATTERN = re.compile(
        r"(?:^|\n|\s)(?:(?:public|private|protected|static|final|abstract|synchronized)\s+)*"
        r"(?:[\w<>\[\]]+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*\{",
        re.MULTILINE,
    )

    CONSTRUCTOR_PATTERN = re.compile(
        r"(?:^|\n|\s)(?:(?:public|private|protected)\s+)*"
        r"(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*\{",
        re.MULTILINE,
    )

    FIELD_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:(?:public|private|protected|static|final|transient|volatile)\s+)*"
        r"[\w<>\[\]]+\s+(\w+)\s*(?:=\s*[^;]+)?\s*;",
        re.MULTILINE,
    )

    PACKAGE_PATTERN = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)

    IMPORT_PATTERN = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.MULTILINE)

    VISIBILITY_PATTERN = re.compile(r"(public|private|protected)\b")

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a Java file and extract symbols.

        Args:
            file_path: Path to the Java file
            code: Optional source code (if not provided, file will be read)

        Returns:
            List of extracted symbols
        """
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Extract package
        package_match = self.PACKAGE_PATTERN.search(code)
        package = package_match.group(1) if package_match else ""

        # Extract imports
        import_symbols = self._extract_imports(code, file_path)
        symbols.extend(import_symbols)

        # Extract classes and interfaces
        class_symbols = self._extract_classes(code, file_path, package)
        symbols.extend(class_symbols)

        # Extract top-level methods (rare in Java)
        method_symbols = self._extract_methods(code, file_path, package, "")
        symbols.extend(method_symbols)

        return symbols

    def _extract_imports(self, code: str, file_path: str) -> list[Symbol]:
        """Extract import statements."""
        symbols = []
        for match in self.IMPORT_PATTERN.finditer(code):
            import_path = match.group(1)
            # Get line number
            line_num = code[: match.start()].count("\n") + 1

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.IMPORT,
                name=import_path.split(".")[-1],
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="java",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols

    def _extract_classes(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract classes, interfaces, and enums."""
        symbols = []

        # Find all class/interface/enum definitions
        positions = []

        # Find classes
        for match in self.CLASS_PATTERN.finditer(code):
            positions.append((match, "class"))

        # Find interfaces
        for match in self.INTERFACE_PATTERN.finditer(code):
            positions.append((match, "interface"))

        # Find enums
        for match in self.ENUM_PATTERN.finditer(code):
            positions.append((match, "enum"))

        # Sort by position
        positions.sort(key=lambda x: x[0].start())

        for match, kind in positions:
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = self._get_visibility(code, match.start())

            qualified_name = f"{package}.{name}" if package else name

            # Extract parent class/interface
            parent = None
            if kind == "class" and match.group(2):
                parent = match.group(2).strip()
            elif kind in ["interface", "enum"] and match.group(2):
                parent = match.group(2).strip()

            # Create symbol for the class/interface/enum
            symbol_type = SymbolType.CLASS if kind in ["class", "enum"] else SymbolType.INTERFACE

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=symbol_type,
                name=name,
                namespace=package,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="java",
                visibility=visibility,
            )
            symbols.append(symbol)

            # Extract methods and fields from this class
            class_body_start = match.end()
            class_body_end = self._find_closing_brace(code, match.end())

            if class_body_end > class_body_start:
                class_body = code[class_body_start:class_body_end]

                # Extract methods
                methods = self._extract_methods(class_body, file_path, package, name)
                for method in methods:
                    # Adjust line numbers to file coordinates
                    method.line_start += code[:class_body_start].count("\n")
                    method.line_end += code[:class_body_start].count("\n")
                symbols.extend(methods)

                # Extract fields
                fields = self._extract_fields(class_body, file_path, package, name)
                for field in fields:
                    field.line_start += code[:class_body_start].count("\n")
                    field.line_end += code[:class_body_start].count("\n")
                symbols.extend(fields)

        return symbols

    def _extract_methods(
        self, code: str, file_path: str, package: str, class_name: str
    ) -> list[Symbol]:
        """Extract method definitions."""
        symbols = []

        for match in self.METHOD_PATTERN.finditer(code):
            name = match.group(1)
            params = match.group(2) if match.group(2) else ""

            # Skip if this looks like a control structure
            if name.lower() in ["if", "for", "while", "switch", "catch", "synchronized"]:
                continue

            line_num = code[: match.start()].count("\n") + 1
            visibility = self._get_visibility(code, match.start())

            # Extract signature
            signature = f"({params})"

            # Create symbol
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.METHOD,
                name=name,
                namespace=class_name,
                signature=signature,
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="java",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_fields(
        self, code: str, file_path: str, package: str, class_name: str
    ) -> list[Symbol]:
        """Extract field definitions."""
        symbols = []

        for match in self.FIELD_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1
            visibility = self._get_visibility(code, match.start())

            # Create symbol
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.PROPERTY,
                name=name,
                namespace=class_name,
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="java",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _get_visibility(self, code: str, position: int) -> str:
        """Extract visibility modifier from code context."""
        # Look backwards from position for visibility modifiers
        search_start = max(0, position - 200)
        search_text = code[search_start:position]

        if "private" in search_text.split("\n")[-1]:
            return "private"
        elif "protected" in search_text.split("\n")[-1]:
            return "protected"
        elif "public" in search_text.split("\n")[-1]:
            return "public"
        else:
            return "private"  # Default in Java

    def _find_closing_brace(self, code: str, start: int) -> int:
        """Find the position of the closing brace matching the opening brace at start."""
        depth = 0
        for i in range(start, len(code)):
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
        return len(code)

    def _find_closing_brace_line(self, code: str, start: int) -> int:
        """Find the line number of the closing brace."""
        closing_pos = self._find_closing_brace(code, start)
        return code[:closing_pos].count("\n") + 1
