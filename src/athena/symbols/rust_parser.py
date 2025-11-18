"""Rust symbol parser for extracting symbols from Rust source files.

Supports:
- Module declarations
- Import statements (use declarations)
- Struct definitions
- Enum definitions
- Trait definitions
- Impl blocks with methods
- Function definitions
- Constants and static variables
- Type definitions and aliases
"""

import re
from typing import Optional
from .symbol_models import Symbol, SymbolType, create_symbol


class RustSymbolParser:
    """Parser for Rust source code using regex-based pattern matching."""

    # Regex patterns for Rust constructs
    MODULE_PATTERN = re.compile(r"(?:^|\n)\s*(?:pub\s+)?mod\s+(\w+)(?:\s*\{)?", re.MULTILINE)

    USE_PATTERN = re.compile(r"(?:^|\n)\s*(?:pub\s+)?use\s+(?:crate::)?([^;]+);", re.MULTILINE)

    STRUCT_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:pub\s+)?struct\s+(\w+)(?:<[^>]*>)?\s*(?:\{|;)", re.MULTILINE
    )

    ENUM_PATTERN = re.compile(r"(?:^|\n)\s*(?:pub\s+)?enum\s+(\w+)(?:<[^>]*>)?\s*\{", re.MULTILINE)

    TRAIT_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:pub\s+)?trait\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*[^{]+)?\s*\{", re.MULTILINE
    )

    IMPL_PATTERN = re.compile(
        r"(?:^|\n)\s*impl(?:<[^>]*>)?\s+(?:(\w+)\s+for\s+)?(\w+)(?:<[^>]*>)?\s*\{", re.MULTILINE
    )

    FUNCTION_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)(?:\s*->\s*[^{]+)?",
        re.MULTILINE,
    )

    CONST_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:pub\s+)?const\s+(\w+)(?:\s*:\s*[^=]+)?\s*=", re.MULTILINE
    )

    STATIC_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:pub\s+)?static\s+(?:mut\s+)?(\w+)(?:\s*:\s*[^=]+)?\s*=", re.MULTILINE
    )

    TYPE_PATTERN = re.compile(r"(?:^|\n)\s*(?:pub\s+)?type\s+(\w+)(?:<[^>]*>)?\s*=", re.MULTILINE)

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a Rust file and extract symbols.

        Args:
            file_path: Path to the Rust file
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

        # Extract modules
        module_symbols = self._extract_modules(code, file_path)
        symbols.extend(module_symbols)

        # Extract imports
        import_symbols = self._extract_imports(code, file_path)
        symbols.extend(import_symbols)

        # Extract structs
        struct_symbols = self._extract_structs(code, file_path)
        symbols.extend(struct_symbols)

        # Extract enums
        enum_symbols = self._extract_enums(code, file_path)
        symbols.extend(enum_symbols)

        # Extract traits
        trait_symbols = self._extract_traits(code, file_path)
        symbols.extend(trait_symbols)

        # Extract impl blocks and methods
        impl_symbols = self._extract_impl_blocks(code, file_path)
        symbols.extend(impl_symbols)

        # Extract top-level functions
        function_symbols = self._extract_functions(code, file_path)
        symbols.extend(function_symbols)

        # Extract constants
        const_symbols = self._extract_constants(code, file_path)
        symbols.extend(const_symbols)

        # Extract static variables
        static_symbols = self._extract_statics(code, file_path)
        symbols.extend(static_symbols)

        return symbols

    def _extract_modules(self, code: str, file_path: str) -> list[Symbol]:
        """Extract module declarations."""
        symbols = []

        for match in self.MODULE_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility (pub or private)
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.MODULE,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_imports(self, code: str, file_path: str) -> list[Symbol]:
        """Extract import statements."""
        symbols = []

        for match in self.USE_PATTERN.finditer(code):
            import_path = match.group(1).strip()
            line_num = code[: match.start()].count("\n") + 1

            # Get the last component as the name
            name = import_path.split("::")[-1].split(" as ")[-1]

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.IMPORT,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="rust",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols

    def _extract_structs(self, code: str, file_path: str) -> list[Symbol]:
        """Extract struct definitions."""
        symbols = []

        for match in self.STRUCT_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=(
                    self._find_closing_brace_line(code, match.end())
                    if "{" in match.group(0)
                    else line_num
                ),
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

            # Extract fields from struct if it has braces
            if "{" in match.group(0):
                struct_body_start = match.end()
                struct_body_end = self._find_closing_brace(code, struct_body_start)

                if struct_body_end > struct_body_start:
                    struct_body = code[struct_body_start:struct_body_end]

                    # Extract struct fields
                    field_pattern = re.compile(
                        r"(?:^|\n)\s*(?:pub(?:\([^)]*\))?\s+)?(\w+)\s*:", re.MULTILINE
                    )
                    for field_match in field_pattern.finditer(struct_body):
                        field_name = field_match.group(1)
                        field_line = code[: struct_body_start + field_match.start()].count("\n") + 1
                        field_visibility = "public" if "pub" in field_match.group(0) else "private"

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
                            language="rust",
                            visibility=field_visibility,
                        )
                        symbols.append(field_symbol)

        return symbols

    def _extract_enums(self, code: str, file_path: str) -> list[Symbol]:
        """Extract enum definitions."""
        symbols = []

        for match in self.ENUM_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.ENUM,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_traits(self, code: str, file_path: str) -> list[Symbol]:
        """Extract trait definitions."""
        symbols = []

        for match in self.TRAIT_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.INTERFACE,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

            # Extract trait methods
            trait_body_start = match.end()
            trait_body_end = self._find_closing_brace(code, trait_body_start)

            if trait_body_end > trait_body_start:
                trait_body = code[trait_body_start:trait_body_end]

                # Extract trait methods
                method_pattern = re.compile(
                    r"(?:^|\n)\s*(?:fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\))", re.MULTILINE
                )
                for method_match in method_pattern.finditer(trait_body):
                    method_name = method_match.group(1)
                    params = method_match.group(2) if method_match.group(2) else ""

                    method_line = code[: trait_body_start + method_match.start()].count("\n") + 1
                    signature = f"({params})"

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
                        language="rust",
                        visibility="public",
                    )
                    symbols.append(method_symbol)

        return symbols

    def _extract_impl_blocks(self, code: str, file_path: str) -> list[Symbol]:
        """Extract impl blocks and their methods."""
        symbols = []

        for match in self.IMPL_PATTERN.finditer(code):
            # match.group(1) is the trait name (if impl Trait for Type)
            # match.group(2) is the struct/type name
            struct_name = match.group(2)
            line_num = code[: match.start()].count("\n") + 1

            impl_body_start = match.end()
            impl_body_end = self._find_closing_brace(code, impl_body_start)

            if impl_body_end > impl_body_start:
                impl_body = code[impl_body_start:impl_body_end]

                # Extract methods from impl block
                method_pattern = re.compile(
                    r"(?:^|\n)\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)",
                    re.MULTILINE,
                )
                for method_match in method_pattern.finditer(impl_body):
                    method_name = method_match.group(1)
                    params = method_match.group(2) if method_match.group(2) else ""

                    method_line = code[: impl_body_start + method_match.start()].count("\n") + 1
                    method_visibility = "public" if "pub" in method_match.group(0) else "private"
                    signature = f"({params})"

                    method_symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.METHOD,
                        name=method_name,
                        namespace=struct_name,
                        signature=signature,
                        line_start=method_line,
                        line_end=self._find_closing_brace_line(
                            code, impl_body_start + method_match.end()
                        ),
                        code="",
                        docstring="",
                        language="rust",
                        visibility=method_visibility,
                    )
                    symbols.append(method_symbol)

        return symbols

    def _extract_functions(self, code: str, file_path: str) -> list[Symbol]:
        """Extract top-level function definitions."""
        symbols = []

        for match in self.FUNCTION_PATTERN.finditer(code):
            name = match.group(1)
            params = match.group(2) if match.group(2) else ""

            # Skip if this is inside an impl block (will be extracted as method)
            # Simple heuristic: check if preceded by 'impl'
            preceding_text = code[max(0, match.start() - 100) : match.start()]
            if "impl" in preceding_text and "{" in preceding_text:
                continue

            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            signature = f"({params})"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.FUNCTION,
                name=name,
                namespace="",
                signature=signature,
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_constants(self, code: str, file_path: str) -> list[Symbol]:
        """Extract constant definitions."""
        symbols = []

        for match in self.CONST_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="rust",
                visibility=visibility,
            )
            symbols.append(symbol)

        return symbols

    def _extract_statics(self, code: str, file_path: str) -> list[Symbol]:
        """Extract static variable definitions."""
        symbols = []

        for match in self.STATIC_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[: match.start()].count("\n") + 1

            # Determine visibility
            visibility = "public" if "pub" in match.group(0) else "private"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.PROPERTY,
                name=name,
                namespace="",
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="rust",
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
