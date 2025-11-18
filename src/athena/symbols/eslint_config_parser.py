"""ESLint config parser for extracting linting configuration metadata.

Supports:
- Parser selection (espree, @babel/eslint-parser, @typescript-eslint/parser, etc.)
- Environments (browser, node, es6, etc.)
- Extended configs (eslint, airbnb, google, standard, etc.)
- Rules and their severity levels
- Plugins and their rule namespaces
- Override configurations for specific file patterns
"""

import json
import re
from typing import Optional, Dict, Any, List
from .symbol_models import Symbol, SymbolType, create_symbol


class ESLintConfigParser:
    """Parser for .eslintrc.json/.eslintrc.js files to extract ESLint configuration as symbols."""

    def parse_file(self, file_path: str, code: Optional[str] = None) -> list[Symbol]:
        """Parse an ESLint config file and extract symbols.

        Args:
            file_path: Path to .eslintrc.json or .eslintrc.js
            code: Optional file content (if not provided, file will be read)

        Returns:
            List of extracted symbols (parser, environments, extends, rules, plugins)
        """
        if code is None:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except (IOError, UnicodeDecodeError):
                return []

        symbols = []

        # Try JSON parsing first (for .eslintrc.json or plain .eslintrc)
        if file_path.endswith(".json") or file_path.endswith(".eslintrc"):
            try:
                data = json.loads(code)
                symbols.extend(self._extract_from_json(data, file_path))
                if symbols:  # If JSON parsing succeeded, return
                    return symbols
            except json.JSONDecodeError:
                pass  # Fall through to JS parsing

        # For JS files, use regex-based extraction
        if file_path.endswith(".js") or file_path.endswith(".eslintrc"):
            symbols.extend(self._extract_from_js(code, file_path))
            return symbols

        return symbols

    def _extract_from_json(self, data: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract configuration from JSON data."""
        symbols = []

        # Extract parser
        if "parser" in data:
            parser = data["parser"]
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.parser",
                namespace="root",
                signature=parser,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"ESLint parser: {parser}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract parser options
        if "parserOptions" in data:
            options = data["parserOptions"]
            if isinstance(options, dict):
                for key, value in options.items():
                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"parserOptions.{key}",
                        namespace="parserOptions",
                        signature=str(value),
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Parser option: {key}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        # Extract environments
        if "env" in data:
            env = data["env"]
            if isinstance(env, dict):
                enabled_envs = [name for name, enabled in env.items() if enabled]
                for env_name in enabled_envs:
                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"env.{env_name}",
                        namespace="environments",
                        signature=env_name,
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"Environment: {env_name}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        # Extract extended configs
        if "extends" in data:
            extends = data["extends"]
            if isinstance(extends, list):
                for config in extends:
                    self._add_extends_symbol(config, file_path, symbols)
            else:
                self._add_extends_symbol(extends, file_path, symbols)

        # Extract plugins
        if "plugins" in data:
            plugins = data["plugins"]
            if isinstance(plugins, list):
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
                        docstring=f"ESLint plugin: {plugin}",
                        language="json",
                        visibility="public",
                    )
                    symbols.append(symbol)

        # Extract rules
        rules_symbols = self._extract_rules(data.get("rules", {}), file_path)
        symbols.extend(rules_symbols)

        # Extract overrides
        if "overrides" in data:
            overrides = data["overrides"]
            if isinstance(overrides, list):
                for i, override in enumerate(overrides):
                    if isinstance(override, dict):
                        # Extract file patterns
                        files = override.get("files", [])
                        if isinstance(files, list):
                            for file_pattern in files:
                                symbol = create_symbol(
                                    file_path=file_path,
                                    symbol_type=SymbolType.CONSTANT,
                                    name=f"override.{i}.files.{file_pattern}",
                                    namespace="overrides",
                                    signature=file_pattern,
                                    line_start=1,
                                    line_end=1,
                                    code="",
                                    docstring=f"Override for pattern: {file_pattern}",
                                    language="json",
                                    visibility="public",
                                )
                                symbols.append(symbol)

        return symbols

    def _extract_from_js(self, code: str, file_path: str) -> list[Symbol]:
        """Extract configuration from JavaScript code using regex."""
        symbols = []

        # Extract parser
        parser_match = re.search(r'parser\s*:\s*["\']([^"\']+)["\']', code)
        if parser_match:
            parser = parser_match.group(1)
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name="config.parser",
                namespace="root",
                signature=parser,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"ESLint parser: {parser}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract environments
        env_pattern = r"env\s*:\s*{([^}]+)}"
        env_match = re.search(env_pattern, code)
        if env_match:
            env_content = env_match.group(1)
            # Find environment names with true values
            envs = re.findall(r"(\w+)\s*:\s*true", env_content)
            for env_name in envs:
                symbol = create_symbol(
                    file_path=file_path,
                    symbol_type=SymbolType.CONSTANT,
                    name=f"env.{env_name}",
                    namespace="environments",
                    signature=env_name,
                    line_start=1,
                    line_end=1,
                    code="",
                    docstring=f"Environment: {env_name}",
                    language="javascript",
                    visibility="public",
                )
                symbols.append(symbol)

        # Extract extends
        extends_pattern = r'extends\s*:\s*["\']([^"\']+)["\']'
        extends_matches = re.findall(extends_pattern, code)
        for extends_config in extends_matches:
            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"extends.{extends_config}",
                namespace="extends",
                signature=extends_config,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"Extended config: {extends_config}",
                language="javascript",
                visibility="public",
            )
            symbols.append(symbol)

        # Extract plugins
        plugins_pattern = r"plugins\s*:\s*\[([^\]]+)\]"
        plugins_match = re.search(plugins_pattern, code)
        if plugins_match:
            plugins_content = plugins_match.group(1)
            plugins = re.findall(r'["\']([^"\']+)["\']', plugins_content)
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
                    docstring=f"ESLint plugin: {plugin}",
                    language="javascript",
                    visibility="public",
                )
                symbols.append(symbol)

        # Extract rules (look for rules object with proper brace matching)
        rules_match = re.search(r"rules\s*:\s*{", code)
        if rules_match:
            # Find the rules object by counting braces
            start = rules_match.end() - 1
            depth = 0
            end = start
            for i in range(start, len(code)):
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break

            if end > start:
                rules_content = code[start : end + 1]
                # Extract rule names - look for quoted strings followed by colons
                rule_pattern = (
                    r'["\']([^"\']+)["\'](?:\s*:\s*(?:["\']?(?:off|\d+|warn|error)["\']?|[\[\{]))'
                )
                for rule_match in re.finditer(rule_pattern, rules_content):
                    rule_name = rule_match.group(1)
                    # Try to find the severity
                    after_match = rules_content[rule_match.end() :]
                    severity_match = re.match(r'["\']?(off|\d+|warn|error)["\']?', after_match)
                    severity = severity_match.group(1) if severity_match else "off"

                    symbol = create_symbol(
                        file_path=file_path,
                        symbol_type=SymbolType.CONSTANT,
                        name=f"rule.{rule_name}",
                        namespace="rules",
                        signature=severity,
                        line_start=1,
                        line_end=1,
                        code="",
                        docstring=f"ESLint rule: {rule_name} ({severity})",
                        language="javascript",
                        visibility="public",
                    )
                    symbols.append(symbol)

        return symbols

    def _add_extends_symbol(self, config: str, file_path: str, symbols: List[Symbol]) -> None:
        """Add an extends configuration symbol."""
        symbol = create_symbol(
            file_path=file_path,
            symbol_type=SymbolType.CONSTANT,
            name=f"extends.{config}",
            namespace="extends",
            signature=config,
            line_start=1,
            line_end=1,
            code="",
            docstring=f"Extended config: {config}",
            language="json",
            visibility="public",
        )
        symbols.append(symbol)

    def _extract_rules(self, rules: Dict[str, Any], file_path: str) -> list[Symbol]:
        """Extract ESLint rules."""
        symbols = []

        for rule_name, rule_config in rules.items():
            # Handle different rule formats:
            # - "off", 0, "warn", 1, "error", 2
            # - { ... } (object with options)
            if isinstance(rule_config, str):
                severity = rule_config
                options_str = ""
            elif isinstance(rule_config, int):
                severity_map = {0: "off", 1: "warn", 2: "error"}
                severity = severity_map.get(rule_config, str(rule_config))
                options_str = ""
            elif isinstance(rule_config, list) and len(rule_config) > 0:
                # Array format: [severity, options]
                first = rule_config[0]
                if isinstance(first, str):
                    severity = first
                elif isinstance(first, int):
                    severity_map = {0: "off", 1: "warn", 2: "error"}
                    severity = severity_map.get(first, str(first))
                else:
                    severity = str(first)

                options = rule_config[1] if len(rule_config) > 1 else {}
                options_str = json.dumps(options) if isinstance(options, dict) else str(options)
            else:
                continue

            signature = f"{severity}" if not options_str else f"{severity}: {options_str[:50]}..."

            symbol = create_symbol(
                file_path=file_path,
                symbol_type=SymbolType.CONSTANT,
                name=f"rule.{rule_name}",
                namespace="rules",
                signature=signature,
                line_start=1,
                line_end=1,
                code="",
                docstring=f"ESLint rule: {rule_name}",
                language="json",
                visibility="public",
            )
            symbols.append(symbol)

        return symbols
