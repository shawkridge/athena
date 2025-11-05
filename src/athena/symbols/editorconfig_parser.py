"""EditorConfig parser for extracting EditorConfig settings metadata.

Supports:
- Root configuration indicator
- Character set and line ending preferences (utf-8, utf-16, lf, crlf, etc.)
- Indent style and size (space, tab)
- Tab width settings
- Final newline insertion
- Trailing whitespace trimming
- File-specific overrides and patterns
- Wildcard pattern matching
"""

import re
from typing import Optional, Dict, Any, List
from .symbol_models import Symbol, SymbolType, create_symbol


class EditorConfigParser:
    """Parser for .editorconfig files to extract EditorConfig settings as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a .editorconfig file and extract symbols.

        Args:
            file_path: Path to .editorconfig file
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (charset, line endings, indent settings, patterns)
        """
        if code is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []
        lines = code.split('\n')

        current_section = None
        section_settings = {}
        root_settings = {}

        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue

            # Parse section (file pattern)
            section_match = re.match(r'^\[([^\]]+)\]$', line)
            if section_match:
                # Process previous section
                if current_section:
                    symbols.extend(self._create_symbols_from_section(
                        current_section, section_settings, file_path, line_num
                    ))

                current_section = section_match.group(1)
                section_settings = {}
                continue

            # Parse key = value setting
            kv_match = re.match(r'^(\w+)\s*=\s*(.+)$', line)
            if kv_match:
                key = kv_match.group(1).strip()
                value = kv_match.group(2).strip()

                # If we haven't seen a section yet, these are root settings
                if current_section is None:
                    root_settings[key] = value
                else:
                    section_settings[key] = value

        # Process root settings (before any sections)
        if root_settings:
            symbols.extend(self._create_symbols_from_root_settings(root_settings, file_path))

        # Process final section
        if current_section:
            symbols.extend(self._create_symbols_from_section(
                current_section, section_settings, file_path, len(lines)
            ))

        return symbols

    def _create_symbols_from_root_settings(
        self, settings: Dict[str, str], file_path: str
    ) -> list[Symbol]:
        """Create symbols from root-level EditorConfig settings."""
        symbols = []

        for key, value in settings.items():
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"config.{key}",
                namespace="root",
                signature=value.lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"EditorConfig root setting: {key}",
                language="editorconfig",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols

    def _create_symbols_from_section(
        self, pattern: str, settings: Dict[str, str], file_path: str, line_num: int
    ) -> list[Symbol]:
        """Create symbols from an EditorConfig section."""
        symbols = []

        # Create pattern symbol
        symbol = create_symbol(
            file_path=file_path,
            symbol_type=SymbolType.CONSTANT,
            name=f"pattern.{pattern}",
            namespace="filePatterns",
            signature=pattern,
            line_start=line_num,
            line_end=line_num,
            code="",
            docstring=f"File pattern: {pattern}",
            language="editorconfig",
            visibility="public"
        )
        symbols.append(symbol)

        # Extract settings for this pattern
        for setting_key, setting_value in settings.items():
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"setting.{pattern}.{setting_key}",
                namespace="settings",
                signature=setting_value,
                line_start=line_num,
                line_end=line_num,
                code="",
                docstring=f"EditorConfig {setting_key}: {setting_value}",
                language="editorconfig",
                visibility="public"
            )
            symbols.append(symbol)

        return symbols
