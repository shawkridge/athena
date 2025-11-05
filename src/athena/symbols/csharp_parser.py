"""C# symbol parser for extracting symbols from C# source files.

Supports:
- Namespaces
- Using statements (imports)
- Classes and structs
- Interfaces
- Enums
- Methods and async methods
- Properties (with get/set)
- Fields
- Events
- Delegates
- Visibility modifiers (public/private/protected/internal)
"""

import re
from typing import Optional
from .symbol_models import Symbol, SymbolType, create_symbol


class CSharpSymbolParser:
    """Parser for C# source code using regex-based pattern matching."""

    # Regex patterns for C# constructs
    NAMESPACE_PATTERN = re.compile(
        r'(?:^|\n)\s*namespace\s+([\w.]+)\s*[{;]',
        re.MULTILINE
    )

    USING_PATTERN = re.compile(
        r'(?:^|\n)\s*using\s+(?:static\s+)?([^;]+);',
        re.MULTILINE
    )

    CLASS_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\[[\w\s,()="]+\]\s*)*(?:(?:public|private|protected|internal|abstract|sealed|static)\s+)*class\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?\s*\{',
        re.MULTILINE
    )

    STRUCT_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)*struct\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?\s*\{',
        re.MULTILINE
    )

    INTERFACE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)*interface\s+(\w+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?\s*\{',
        re.MULTILINE
    )

    ENUM_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)*enum\s+(\w+)\s*(?::\s*\w+)?\s*\{',
        re.MULTILINE
    )

    METHOD_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:\[[\w\s,()="]+\]\s*)*(?:(?:public|private|protected|internal|static|async|virtual|abstract|override)\s+)*(?:[\w<>[\]\s.]+\s+)?(\w+)\s*\(([^)]*)\)(?:\s*[{;])',
        re.MULTILINE
    )

    PROPERTY_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)+(?:[\w<>[\]\s.]+?)\s+([A-Z]\w*)\s*\{\s*(?:get|set)',
        re.MULTILINE
    )

    FIELD_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal|static|readonly|const)\s+)*(?:[\w<>[\]\s.]+)\s+(\w+)\s*(?:=|;)',
        re.MULTILINE
    )

    EVENT_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)*event\s+(?:[\w<>[\]\s.]+)\s+(\w+)',
        re.MULTILINE
    )

    DELEGATE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:(?:public|private|protected|internal)\s+)*delegate\s+(?:[\w<>[\]\s.]+)\s+(\w+)\s*\(',
        re.MULTILINE
    )

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a C# file and extract symbols.

        Args:
            file_path: Path to the C# file
            code: Optional source code (if not provided, file will be read)

        Returns:
            List of extracted symbols
        """
        if code is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Extract namespace
        namespace = self._extract_namespace(code)

        # Extract using statements
        using_symbols = self._extract_using_statements(code, file_path)
        symbols.extend(using_symbols)

        # Extract classes and structs
        class_symbols = self._extract_classes(code, file_path, namespace)
        symbols.extend(class_symbols)

        # Extract interfaces
        interface_symbols = self._extract_interfaces(code, file_path, namespace)
        symbols.extend(interface_symbols)

        # Extract enums
        enum_symbols = self._extract_enums(code, file_path, namespace)
        symbols.extend(enum_symbols)

        # Extract top-level delegates
        delegate_symbols = self._extract_delegates(code, file_path, namespace)
        symbols.extend(delegate_symbols)

        return symbols

    def _extract_namespace(self, code: str) -> str:
        """Extract namespace declaration."""
        match = self.NAMESPACE_PATTERN.search(code)
        return match.group(1) if match else ""

    def _extract_using_statements(self, code: str, file_path: str) -> list[Symbol]:
        """Extract using statements."""
        symbols = []

        for match in self.USING_PATTERN.finditer(code):
            import_path = match.group(1).strip()
            line_num = code[:match.start()].count('\n') + 1

            # Get the last component as the name
            name = import_path.split('.')[-1]

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
                language="csharp",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols

    def _extract_classes(self, code: str, file_path: str, namespace: str) -> list[Symbol]:
        """Extract class and struct definitions."""
        symbols = []

        # Extract classes
        for match in self.CLASS_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1

            visibility = self._get_visibility(code, match.start())

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                name=name,
                namespace=namespace,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

            # Extract members from class
            # match.end() is right after the '{', so we need match.end() - 1 to get the '{'
            opening_brace_pos = match.end() - 1
            class_body_end = self._find_closing_brace(code, opening_brace_pos)
            class_body_start = match.end()

            if class_body_end > class_body_start:
                class_body = code[class_body_start:class_body_end]

                # Extract methods
                methods = self._extract_methods(class_body, file_path, namespace, name)
                for method in methods:
                    method.line_start += code[:class_body_start].count('\n')
                    method.line_end += code[:class_body_start].count('\n')
                symbols.extend(methods)

                # Extract properties
                properties = self._extract_properties(class_body, file_path, namespace, name)
                for prop in properties:
                    prop.line_start += code[:class_body_start].count('\n')
                    prop.line_end += code[:class_body_start].count('\n')
                symbols.extend(properties)

                # Extract fields
                fields = self._extract_fields(class_body, file_path, namespace, name)
                for field in fields:
                    field.line_start += code[:class_body_start].count('\n')
                    field.line_end += code[:class_body_start].count('\n')
                symbols.extend(fields)

                # Extract events
                events = self._extract_events(class_body, file_path, namespace, name)
                for event in events:
                    event.line_start += code[:class_body_start].count('\n')
                    event.line_end += code[:class_body_start].count('\n')
                symbols.extend(events)

        # Extract structs
        for match in self.STRUCT_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1

            visibility = self._get_visibility(code, match.start())

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CLASS,
                name=name,
                namespace=namespace,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _extract_interfaces(self, code: str, file_path: str, namespace: str) -> list[Symbol]:
        """Extract interface definitions."""
        symbols = []

        for match in self.INTERFACE_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1

            visibility = self._get_visibility(code, match.start())

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.INTERFACE,
                name=name,
                namespace=namespace,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

            # Extract interface members
            interface_body_start = match.end()
            interface_body_end = self._find_closing_brace(code, interface_body_start)

            if interface_body_end > interface_body_start:
                interface_body = code[interface_body_start:interface_body_end]

                # Extract interface methods
                methods = self._extract_methods(interface_body, file_path, namespace, name)
                for method in methods:
                    method.line_start += code[:interface_body_start].count('\n')
                    method.line_end += code[:interface_body_start].count('\n')
                symbols.extend(methods)

        return symbols

    def _extract_enums(self, code: str, file_path: str, namespace: str) -> list[Symbol]:
        """Extract enum definitions."""
        symbols = []

        for match in self.ENUM_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1

            visibility = self._get_visibility(code, match.start())

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.ENUM,
                name=name,
                namespace=namespace,
                signature="",
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()),
                code="",
                docstring="",
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _extract_methods(
        self, code: str, file_path: str, namespace: str, class_name: str
    ) -> list[Symbol]:
        """Extract method definitions."""
        symbols = []

        for match in self.METHOD_PATTERN.finditer(code):
            name = match.group(1)
            params = match.group(2) if match.group(2) else ""

            # Skip if this looks like a control structure
            if name.lower() in ['if', 'for', 'while', 'switch', 'catch', 'using', 'lock']:
                continue

            line_num = code[:match.start()].count('\n') + 1
            visibility = self._get_visibility(code, match.start())

            # Check if async
            is_async = "async" in match.group(0)

            signature = f"({params})"

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.ASYNC_FUNCTION if is_async else SymbolType.METHOD,
                name=name,
                namespace=class_name,
                signature=signature,
                line_start=line_num,
                line_end=self._find_closing_brace_line(code, match.end()) if "{" in match.group(0) else line_num,
                code="",
                docstring="",
                language="csharp",
                visibility=visibility,
                is_async=is_async
            )
            symbols.append(symbol)

        return symbols

    def _extract_properties(
        self, code: str, file_path: str, namespace: str, class_name: str
    ) -> list[Symbol]:
        """Extract property definitions."""
        symbols = []
        seen_names = set()  # Track already extracted to avoid duplicates

        for match in self.PROPERTY_PATTERN.finditer(code):
            name = match.group(1)

            # Skip C# keywords and already seen properties
            if name.lower() in ['get', 'set', 'add', 'remove']:
                continue
            if name in seen_names:
                continue

            seen_names.add(name)
            line_num = code[:match.start()].count('\n') + 1
            visibility = self._get_visibility(code, match.start())

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
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _extract_fields(
        self, code: str, file_path: str, namespace: str, class_name: str
    ) -> list[Symbol]:
        """Extract field definitions."""
        symbols = []
        seen_names = set()  # Track already extracted to avoid duplicates

        for match in self.FIELD_PATTERN.finditer(code):
            name = match.group(1)

            # Skip C# keywords and already seen fields
            if name.lower() in ['get', 'set', 'add', 'remove']:
                continue
            if name in seen_names:
                continue

            seen_names.add(name)
            line_num = code[:match.start()].count('\n') + 1
            visibility = self._get_visibility(code, match.start())

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
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _extract_events(
        self, code: str, file_path: str, namespace: str, class_name: str
    ) -> list[Symbol]:
        """Extract event definitions."""
        symbols = []

        for match in self.EVENT_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1
            visibility = self._get_visibility(code, match.start())

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
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _extract_delegates(self, code: str, file_path: str, namespace: str) -> list[Symbol]:
        """Extract delegate definitions."""
        symbols = []

        for match in self.DELEGATE_PATTERN.finditer(code):
            name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1
            visibility = self._get_visibility(code, match.start())

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.FUNCTION,
                name=name,
                namespace=namespace,
                signature="",
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring="",
                language="csharp",
                visibility=visibility
            )
            symbols.append(symbol)

        return symbols

    def _get_visibility(self, code: str, position: int) -> str:
        """Extract visibility modifier from code context.

        Maps C# visibility modifiers to Symbol visibility:
        - public -> public
        - protected -> protected
        - protected internal -> protected (most permissive)
        - private -> private
        - internal -> private (not in Symbol model, maps to private as it's assembly-scoped)
        """
        search_start = max(0, position - 200)
        search_text = code[search_start:position]
        last_line = search_text.split('\n')[-1]

        if 'private' in last_line:
            return "private"
        elif 'protected' in last_line:
            return "protected"
        elif 'public' in last_line:
            return "public"
        else:
            return "private"  # Default: internal and unknown map to private

    def _find_closing_brace(self, code: str, start: int) -> int:
        """Find the position of the closing brace matching the opening brace at start."""
        depth = 0
        for i in range(start, len(code)):
            if code[i] == '{':
                depth += 1
            elif code[i] == '}':
                depth -= 1
                if depth == 0:
                    return i
        return len(code)

    def _find_closing_brace_line(self, code: str, start: int) -> int:
        """Find the line number of the closing brace."""
        closing_pos = self._find_closing_brace(code, start)
        return code[:closing_pos].count('\n') + 1
