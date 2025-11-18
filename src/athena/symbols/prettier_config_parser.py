"""Prettier config parser for extracting Prettier formatting configuration metadata.

Supports:
- Print width and tab width settings
- Quote and semicolon preferences
- Trailing comma and arrow function settings
- Bracket and brace spacing
- JSX formatting preferences
- File-specific overrides
- Plugin configurations
- HTML and Vue formatting options
"""

import json
import re
from typing import Optional, Dict, Any
from .symbol_models import Symbol, SymbolType, create_symbol


class PrettierConfigParser:
    """Parser for .prettierrc/.prettierrc.json/prettier.config.js files to extract Prettier configuration as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse a Prettier config file and extract symbols.

        Args:
            file_path: Path to .prettierrc, .prettierrc.json, .prettierrc.js, or prettier.config.js
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (formatting options, overrides, plugins)
        """
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Try JSON parsing first (for .prettierrc, .prettierrc.json, prettier.config.json)
        if (
            file_path.endswith(".json")
            or file_path.endswith(".prettierrc")
            or file_path.endswith("/.prettierrc")
        ):
            try:
                data = json.loads(code)
                symbols.extend(self._extract_from_json(data, file_path))
                if symbols:  # If JSON parsing succeeded, return
                    return symbols
            except json.JSONDecodeError:
                pass  # Fall through to JS parsing

        # For JS files, use regex-based extraction
        if file_path.endswith(".js") or file_path.endswith("/.prettierrc"):
            symbols.extend(self._extract_from_js(code, file_path))
            return symbols

        return symbols

    def _extract_from_json(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract configuration from JSON data."""
        symbols = []

        # Extract print width
        if "printWidth" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.printWidth",
                namespace="root",
                signature=str(data["printWidth"]),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Print width: {data['printWidth']} characters",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract tab width
        if "tabWidth" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.tabWidth",
                namespace="root",
                signature=str(data["tabWidth"]),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Tab width: {data['tabWidth']} spaces",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract useTabs setting
        if "useTabs" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.useTabs",
                namespace="root",
                signature=str(data["useTabs"]).lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Use tabs: {data['useTabs']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract quote preferences
        if "singleQuote" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.singleQuote",
                namespace="root",
                signature=str(data["singleQuote"]).lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Use single quotes: {data['singleQuote']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract trailing comma setting
        if "trailingComma" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.trailingComma",
                namespace="root",
                signature=data["trailingComma"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Trailing comma: {data['trailingComma']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract bracket spacing
        if "bracketSpacing" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.bracketSpacing",
                namespace="root",
                signature=str(data["bracketSpacing"]).lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Bracket spacing: {data['bracketSpacing']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract semicolon setting
        if "semi" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.semi",
                namespace="root",
                signature=str(data["semi"]).lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Print semicolons: {data['semi']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract arrow function parens
        if "arrowParens" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.arrowParens",
                namespace="root",
                signature=data["arrowParens"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Arrow function parens: {data['arrowParens']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract JSX bracket same line
        if "bracketSameLine" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.bracketSameLine",
                namespace="root",
                signature=str(data["bracketSameLine"]).lower(),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"JSX bracket same line: {data['bracketSameLine']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract endOfLine setting
        if "endOfLine" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.endOfLine",
                namespace="root",
                signature=data["endOfLine"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"End of line: {data['endOfLine']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract prose wrap
        if "proseWrap" in data:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.proseWrap",
                namespace="root",
                signature=data["proseWrap"],
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Prose wrap: {data['proseWrap']}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract plugins
        if "plugins" in data and isinstance(data["plugins"], list):
            for plugin in data["plugins"]:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"plugin.{plugin}",
                    namespace="plugins",
                    signature=plugin,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Prettier plugin: {plugin}",
                    language="json",
                    visibility="public",
                )
                symbols.append(symbol)

        # Extract overrides
        if "overrides" in data and isinstance(data["overrides"], list):
            for i, override in enumerate(data["overrides"]):
                if isinstance(override, dict):
                    # Extract file patterns
                    files = override.get("files", [])
                    if isinstance(files, list):
                        for file_pattern in files:
                            symbol = create_symbol(
                                file_path=file_path,
                                symbol_type=SymbolType.CONSTANT,
                                name=f"override.{i}.pattern.{file_pattern}",
                                namespace="overrides",
                                signature=file_pattern,
                                line_start=1,
                                line_end=1,
                                code="",
                                docstring=f"Override pattern: {file_pattern}",
                                language="json",
                                visibility="public",
                            )
                            symbols.append(symbol)

                    # Extract override options
                    for option_key, option_value in override.items():
                        if option_key != "files":
                            symbol = create_symbol(
                                file_path=file_path,
                                symbol_type=SymbolType.CONSTANT,
                                name=f"override.{i}.{option_key}",
                                namespace="overrides",
                                signature=str(option_value),
                                line_start=1,
                                line_end=1,
                                code="",
                                docstring=f"Override option: {option_key}",
                                language="json",
                                visibility="public",
                            )
                            symbols.append(symbol)

        return symbols

    def _extract_from_js(self, code: str, file_path: str) -> list[Symbol]:
        """Extract configuration from JavaScript code using regex."""
        symbols = []

        # Extract printWidth
        print_width_match = re.search(r"printWidth\s*:\s*(\d+)", code)
        if print_width_match:
            width = print_width_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.printWidth",
                namespace="root",
                signature=width,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Print width: {width} characters",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract tabWidth
        tab_width_match = re.search(r"tabWidth\s*:\s*(\d+)", code)
        if tab_width_match:
            width = tab_width_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.tabWidth",
                namespace="root",
                signature=width,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Tab width: {width} spaces",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract useTabs
        use_tabs_match = re.search(r"useTabs\s*:\s*(true|false)", code)
        if use_tabs_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.useTabs",
                namespace="root",
                signature=use_tabs_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Use tabs: {use_tabs_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract singleQuote
        single_quote_match = re.search(r"singleQuote\s*:\s*(true|false)", code)
        if single_quote_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.singleQuote",
                namespace="root",
                signature=single_quote_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Use single quotes: {single_quote_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract trailingComma
        trailing_comma_match = re.search(r'trailingComma\s*:\s*["\']?(all|es5|none)["\']?', code)
        if trailing_comma_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.trailingComma",
                namespace="root",
                signature=trailing_comma_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Trailing comma: {trailing_comma_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract bracketSpacing
        bracket_spacing_match = re.search(r"bracketSpacing\s*:\s*(true|false)", code)
        if bracket_spacing_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.bracketSpacing",
                namespace="root",
                signature=bracket_spacing_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Bracket spacing: {bracket_spacing_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract semi
        semi_match = re.search(r"semi\s*:\s*(true|false)", code)
        if semi_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.semi",
                namespace="root",
                signature=semi_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Print semicolons: {semi_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract arrowParens
        arrow_parens_match = re.search(r'arrowParens\s*:\s*["\']?(always|avoid)["\']?', code)
        if arrow_parens_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.arrowParens",
                namespace="root",
                signature=arrow_parens_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Arrow function parens: {arrow_parens_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract bracketSameLine
        bracket_same_line_match = re.search(r"bracketSameLine\s*:\s*(true|false)", code)
        if bracket_same_line_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.bracketSameLine",
                namespace="root",
                signature=bracket_same_line_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"JSX bracket same line: {bracket_same_line_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract endOfLine
        end_of_line_match = re.search(r'endOfLine\s*:\s*["\']?(lf|crlf|cr|auto)["\']?', code)
        if end_of_line_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.endOfLine",
                namespace="root",
                signature=end_of_line_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"End of line: {end_of_line_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract proseWrap
        prose_wrap_match = re.search(r'proseWrap\s*:\s*["\']?(always|never|preserve)["\']?', code)
        if prose_wrap_match:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.proseWrap",
                namespace="root",
                signature=prose_wrap_match.group(1),
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Prose wrap: {prose_wrap_match.group(1)}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract plugins
        plugins_pattern = r"plugins\s*:\s*\[([^\]]+)\]"
        plugins_match = re.search(plugins_pattern, code)
        if plugins_match:
            plugins_content = plugins_match.group(1)
            plugins = re.findall(r'["\']([^\'"]+)["\']', plugins_content)
            for plugin in plugins:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"plugin.{plugin}",
                    namespace="plugins",
                    signature=plugin,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Prettier plugin: {plugin}",
                    language="javascript",
                    visibility="public",
                )
                symbols.append(symbol)

        # Extract overrides with file patterns using brace matching
        overrides_match = re.search(r"overrides\s*:\s*\[", code)
        if overrides_match:
            # Find the entire overrides array using brace matching
            start = overrides_match.end() - 1  # Position of [
            depth = 0
            end = start
            for i in range(start, len(code)):
                if code[i] == "[":
                    depth += 1
                elif code[i] == "]":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            if end > start:
                overrides_content = code[start : end + 1]
                # Find file patterns within overrides
                file_patterns = re.findall(
                    r"files\s*:\s*\[([^\]]+)\]", overrides_content, re.DOTALL
                )
                for i, patterns_str in enumerate(file_patterns):
                    patterns = re.findall(r'["\']([^\'"]+)["\']', patterns_str)
                    for pattern in patterns:
                        symbol = create_symbol(
                            file_path=file_path,
                            symbol_type=SymbolType.CONSTANT,
                            name=f"override.{i}.pattern.{pattern}",
                            namespace="overrides",
                            signature=pattern,
                            line_start=1,
                            line_end=1,
                            code="",
                            docstring=f"Override pattern: {pattern}",
                            language="javascript",
                            visibility="public",
                        )
                        symbols.append(symbol)

        return symbols
