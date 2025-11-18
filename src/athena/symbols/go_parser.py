"""Go symbol parser for extracting symbols from Go source files.

Supports:
- Package declarations
- Import statements (single and block)
- Struct definitions
- Interface definitions
- Function definitions
- Methods with receivers
- Constants and variables
- Type definitions and aliases
"""

import re
from typing import Optional
from .symbol_models import Symbol, SymbolType, create_symbol


class GoSymbolParser:
    """Parser for Go source code using regex-based pattern matching."""

    # Regex patterns for Go constructs
    PACKAGE_PATTERN = re.compile(r"^package\s+(\w+)", re.MULTILINE)

    IMPORT_PATTERN = re.compile(
        r"import\s+(?:"
        r'(?:"([^"]+)"|`([^`]+)`)|'  # Single import with quotes or backticks
        r"\(([^)]*)\)"  # Import block
        r")",
        re.MULTILINE,
    )

    STRUCT_PATTERN = re.compile(r"(?:^|\n)\s*type\s+(\w+)\s+struct\s*\{", re.MULTILINE)

    INTERFACE_PATTERN = re.compile(r"(?:^|\n)\s*type\s+(\w+)\s+interface\s*\{", re.MULTILINE)

    FUNCTION_PATTERN = re.compile(
        r"(?:^|\n)\s*func\s+(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\))?", re.MULTILINE
    )

    METHOD_PATTERN = re.compile(
        r"(?:^|\n)\s*func\s*\(\s*(\w+)\s+\*?(\w+)\s*\)\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE
    )

    CONST_PATTERN = re.compile(r"(?:^|\n)\s*const\s+(\w+)(?:\s+\w+)?\s*=", re.MULTILINE)

    VAR_PATTERN = re.compile(r"(?:^|\n)\s*var\s+(\w+)(?:\s+[^=]+)?(?:\s*=)?", re.MULTILINE)

    TYPE_PATTERN = re.compile(
        r"(?:^|\n)\s*type\s+(\w+)\s+(?:struct|interface|\*?\w+)", re.MULTILINE
    )

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a Go file and extract symbols.

        Args:
            file_path: Path to the Go file
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

        # Extract struct definitions
        struct_symbols = self._extract_structs(code, file_path, package)
        symbols.extend(struct_symbols)

        # Extract interface definitions
        interface_symbols = self._extract_interfaces(code, file_path, package)
        symbols.extend(interface_symbols)

        # Extract top-level functions
        function_symbols = self._extract_functions(code, file_path, package)
        symbols.extend(function_symbols)

        # Extract methods
        method_symbols = self._extract_methods(code, file_path, package)
        symbols.extend(method_symbols)

        # Extract constants
        const_symbols = self._extract_constants(code, file_path, package)
        symbols.extend(const_symbols)

        # Extract variables
        var_symbols = self._extract_variables(code, file_path, package)
        symbols.extend(var_symbols)

        return symbols

    def _extract_imports(self, code: str, file_path: str) -> list[Symbol]:
        """Extract import statements."""
        symbols = []

        # Handle single imports: import "fmt"
        single_import_pattern = re.compile(r'import\s+(?:"([^"]+)"|`([^`]+)`)')
        for match in single_import_pattern.finditer(code):
            import_path = match.group(1) or match.group(2)
            line_num = code[: match.start()].count("\n") + 1

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.IMPORT,
                name=import_path.split("/")[-1],
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="go",
                visibility="public",
            )
            symbols.append(symbol)

        # Handle import blocks: import ( "fmt"; "os" )
        import_block_pattern = re.compile(r"import\s*\(\s*([^)]+)\)", re.MULTILINE | re.DOTALL)
        for block_match in import_block_pattern.finditer(code):
            block_content = block_match.group(1)
            # Extract individual imports from block
            for line in block_content.split("\n"):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                # Match quoted paths
                path_match = re.search(r'(?:"([^"]+)"|`([^`]+)`)', line)
                if path_match:
                    import_path = path_match.group(1) or path_match.group(2)
                    line_num = code[: block_match.start()].count("\n") + 1

                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.IMPORT,
                        name=import_path.split("/")[-1],
                        namespace="",
                        signature="",
                        line_start=line_num,
                        line_end=line_num,
                        code="",
                        docstring="",
                        language="go",
                        visibility="public",
                    )
                    symbols.append(symbol)

        return symbols

    def _extract_structs(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract struct definitions."""
        symbols = []

        for match in self.STRUCT_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (exported if capitalized)
            visibility = "public" if name[0].isupper() else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                name=name,
                namespace=package,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

            # Extract fields from struct
            struct_body_start = match.end()
            struct_body_end = self._find_closing_brace(code, struct_body_start)

            if struct_body_end > struct_body_start:
                struct_body = code[struct_body_start:struct_body_end]

                # Extract struct fields
                field_pattern = re.compile(
                    r"(?:^|\n)\s*(\w+)\s+(?:\*)?[\w\[\]\.]+(?:\s+`[^`]*`)?", re.MULTILINE
                )
                for field_match in field_pattern.finditer(struct_body):
                    field_name = field_match.group(1)
                    # Skip if it looks like a method or other construct
                    if field_name.lower() in ["func", "type", "const", "var"]:
                        continue

                    field_line = code[: struct_body_start + field_match.start()].count("\n") + 1
                    field_visibility = "public" if field_name[0].isupper() else "private"

                    field_symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.PROPERTY,
                        name=field_name,
                        namespace=name,
                        signature="",
                        line_start=field_line,
                        line_end=field_line,
                        code="",
                        docstring="",
                        language="go",
                        visibility=field_visibility,
                    )
                    symbols.append(field_symbol)

        return symbols

    def _extract_interfaces(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract interface definitions."""
        symbols = []

        for match in self.INTERFACE_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (exported if capitalized)
            visibility = "public" if name[0].isupper() else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.INTERFACE,
                name=name,
                namespace=package,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

            # Extract methods from interface
            interface_body_start = match.end()
            interface_body_end = self._find_closing_brace(code, interface_body_start)

            if interface_body_end > interface_body_start:
                interface_body = code[interface_body_start:interface_body_end]

                # Extract interface methods
                method_pattern = re.compile(
                    r"(?:^|\n)\s*(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\))?", re.MULTILINE
                )
                for method_match in method_pattern.finditer(interface_body):
                    method_name = method_match.group(1)
                    params = method_match.group(2) if method_match.group(2) else ""
                    returns = method_match.group(3) if method_match.group(3) else ""

                    method_line = (
                        code[: interface_body_start + method_match.start()].count("\n") + 1
                    )
                    method_visibility = "public" if method_name[0].isupper() else "private"
                    signature = f"({params}) ({returns})" if returns else f"({params})"

                    method_symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.METHOD,
                        name=method_name,
                        namespace=name,
                        signature=signature,
                        line_start=method_line,
                        line_end=method_line,
                        code="",
                        docstring="",
                        language="go",
                        visibility=method_visibility,
                    )
                    symbols.append(method_symbol)

        return symbols

    def _extract_functions(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract top-level function definitions."""
        symbols = []

        for match in self.FUNCTION_PATTERN.finditer(code):
            name = match.group(1)
            params = match.group(2) if match.group(2) else ""
            returns = match.group(3) if match.group(3) else ""

            # Skip if this is actually a method (has receiver)
            # Methods are detected before function in code with "func (receiver Type)"
            if name.lower() in ["type", "const", "var", "import", "package"]:
                continue

            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (exported if capitalized)
            visibility = "public" if name[0].isupper() else "private"

            signature = f"({params}) ({returns})" if returns else f"({params})"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.FUNCTION,
                name=name,
                namespace=package,
                signature=signature,
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_methods(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract method definitions with receivers."""
        symbols = []

        for match in self.METHOD_PATTERN.finditer(code):
            receiver_var = match.group(1)
            receiver_type = match.group(2)
            method_name = match.group(3)
            params = match.group(4) if match.group(4) else ""

            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (exported if capitalized)
            visibility = "public" if method_name[0].isupper() else "private"

            signature = f"({params})"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.METHOD,
                name=method_name,
                namespace=receiver_type,
                signature=signature,
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_constants(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract constant definitions."""
        symbols = []

        for match in self.CONST_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (exported if capitalized)
            visibility = "public" if name[0].isupper() else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=name,
                namespace=package,
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_variables(self, code: str, file_path: str, package: str) -> list[Symbol]:
        """Extract variable definitions."""
        symbols = []

        for match in self.VAR_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Skip if already extracted by other patterns
            if name.lower() in ["package", "import", "type", "func", "const"]:
                continue

            # Determine visibility (exported if capitalized)
            visibility = "public" if name[0].isupper() else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.PROPERTY,
                name=name,
                namespace=package,
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="go",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

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
