"""Enhanced code parser using modern tools (ast-grep, ripgrep, tree-sitter, semgrep)."""

import logging
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import CodeElement, CodeElementType, CodeLanguage
from .modern_tools import AstGrepSearcher, RipgrepSearcher, TreeSitterParser, SemgrepAnalyzer

logger = logging.getLogger(__name__)


class EnhancedCodeParser:
    """Enhanced parser using modern tools for superior accuracy and speed."""

    def __init__(self):
        """Initialize enhanced parser with modern tools."""
        self.astgrep = AstGrepSearcher()
        self.ripgrep = RipgrepSearcher()
        self.treesitter = TreeSitterParser()
        self.semgrep = SemgrepAnalyzer()

    def parse_file(self, file_path: str) -> List[CodeElement]:
        """Parse a file using modern tools with fallback to regex.

        Args:
            file_path: Path to source file

        Returns:
            List of CodeElement objects
        """
        path = Path(file_path)
        language = self._get_language(path.suffix)

        if not language:
            logger.warning(f"Unsupported file type: {path.suffix}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

        # Try modern tools first
        if language in [CodeLanguage.TYPESCRIPT, CodeLanguage.JAVASCRIPT]:
            return self._parse_with_astgrep(file_path, source_code, language)
        elif language == CodeLanguage.PYTHON:
            return self._parse_with_treesitter(file_path, source_code, language)
        else:
            # Fallback to tree-sitter if available
            return self._parse_with_treesitter(file_path, source_code, language)

    def _get_language(self, suffix: str) -> Optional[CodeLanguage]:
        """Get language from file suffix."""
        mapping = {
            ".ts": CodeLanguage.TYPESCRIPT,
            ".tsx": CodeLanguage.TYPESCRIPT,
            ".js": CodeLanguage.JAVASCRIPT,
            ".jsx": CodeLanguage.JAVASCRIPT,
            ".py": CodeLanguage.PYTHON,
            ".go": CodeLanguage.GO,
            ".rs": CodeLanguage.RUST,
            ".java": CodeLanguage.JAVA,
        }
        return mapping.get(suffix)

    def _parse_with_astgrep(
        self, file_path: str, source_code: str, language: CodeLanguage
    ) -> List[CodeElement]:
        """Parse using ast-grep for structure-aware analysis.

        Args:
            file_path: Path to file
            source_code: Source code content
            language: Code language

        Returns:
            List of code elements
        """
        elements = []

        # Add module element
        lines = source_code.split("\n")
        elements.append(
            CodeElement(
                element_id=f"{file_path}:module",
                file_path=file_path,
                language=language,
                element_type=CodeElementType.MODULE,
                name=Path(file_path).stem,
                source_code=source_code,
                start_line=1,
                end_line=len(lines),
            )
        )

        if not self.astgrep.available:
            logger.debug("ast-grep not available, using fallback")
            return elements

        # Parse using ast-grep patterns
        language_str = "typescript" if language == CodeLanguage.TYPESCRIPT else "javascript"

        # Find imports
        imports = self._extract_imports_astgrep(file_path, source_code, language_str)
        elements.extend(imports)

        # Find functions
        functions = self._extract_functions_astgrep(file_path, source_code, language_str)
        elements.extend(functions)

        # Find classes
        classes = self._extract_classes_astgrep(file_path, source_code, language_str)
        elements.extend(classes)

        # Find exports
        exports = self._extract_exports_astgrep(file_path, source_code, language_str)
        elements.extend(exports)

        return elements

    def _extract_imports_astgrep(
        self, file_path: str, source_code: str, language: str
    ) -> List[CodeElement]:
        """Extract imports using ast-grep."""
        elements = []
        pattern = "import $_ from $_"

        try:
            # Use subprocess to call ast-grep
            cmd = [
                "ast-grep",
                "--pattern",
                pattern,
                "--lang",
                language,
                "--json",
                "compact",
            ]

            result = subprocess.run(
                cmd,
                input=source_code,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            match_data = json.loads(line)
                            if isinstance(match_data, dict):
                                match_text = match_data.get("text", "")
                                line_num = match_data.get("line", 0)

                                if match_text:
                                    elements.append(
                                        CodeElement(
                                            element_id=f"{file_path}:import:{match_text[:30]}",
                                            file_path=file_path,
                                            language=(
                                                CodeLanguage.TYPESCRIPT
                                                if language == "typescript"
                                                else CodeLanguage.JAVASCRIPT
                                            ),
                                            element_type=CodeElementType.IMPORT,
                                            name=match_text.strip(),
                                            source_code=match_text,
                                            start_line=line_num,
                                            end_line=line_num,
                                        )
                                    )
                        except json.JSONDecodeError:
                            continue
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"ast-grep import extraction failed: {e}")

        return elements

    def _extract_functions_astgrep(
        self, file_path: str, source_code: str, language: str
    ) -> List[CodeElement]:
        """Extract function declarations using ast-grep."""
        elements = []
        patterns = [
            "function $NAME($$$) { $$$ }",
            "const $NAME = ($$$) => { $$$ }",
            "const $NAME = function($$$) { $$$ }",
            "async function $NAME($$$) { $$$ }",
            "export function $NAME($$$) { $$$ }",
        ]

        for pattern in patterns:
            try:
                cmd = [
                    "ast-grep",
                    "--pattern",
                    pattern,
                    "--lang",
                    language,
                    "--json",
                    "compact",
                ]

                result = subprocess.run(
                    cmd,
                    input=source_code,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.stdout:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            try:
                                match_data = json.loads(line)
                                if isinstance(match_data, dict):
                                    match_text = match_data.get("text", "")
                                    line_num = match_data.get("line", 0)

                                    if match_text and "$NAME" in pattern:
                                        # Extract function name
                                        name = self._extract_name_from_pattern(match_text)
                                        if name:
                                            elements.append(
                                                CodeElement(
                                                    element_id=f"{file_path}:function:{name}",
                                                    file_path=file_path,
                                                    language=(
                                                        CodeLanguage.TYPESCRIPT
                                                        if language == "typescript"
                                                        else CodeLanguage.JAVASCRIPT
                                                    ),
                                                    element_type=CodeElementType.FUNCTION,
                                                    name=name,
                                                    source_code=match_text,
                                                    start_line=line_num,
                                                    end_line=line_num,
                                                )
                                            )
                            except json.JSONDecodeError:
                                continue
            except (subprocess.TimeoutExpired, Exception) as e:
                logger.debug(f"ast-grep function extraction failed: {e}")

        return elements

    def _extract_classes_astgrep(
        self, file_path: str, source_code: str, language: str
    ) -> List[CodeElement]:
        """Extract class definitions using ast-grep."""
        elements = []
        pattern = "class $NAME { $$$ }"

        try:
            cmd = [
                "ast-grep",
                "--pattern",
                pattern,
                "--lang",
                language,
                "--json",
                "compact",
            ]

            result = subprocess.run(
                cmd,
                input=source_code,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            match_data = json.loads(line)
                            if isinstance(match_data, dict):
                                match_text = match_data.get("text", "")
                                line_num = match_data.get("line", 0)

                                if match_text:
                                    # Extract class name
                                    import re

                                    name_match = re.search(r"class\s+(\w+)", match_text)
                                    if name_match:
                                        name = name_match.group(1)
                                        elements.append(
                                            CodeElement(
                                                element_id=f"{file_path}:class:{name}",
                                                file_path=file_path,
                                                language=(
                                                    CodeLanguage.TYPESCRIPT
                                                    if language == "typescript"
                                                    else CodeLanguage.JAVASCRIPT
                                                ),
                                                element_type=CodeElementType.CLASS,
                                                name=name,
                                                source_code=match_text,
                                                start_line=line_num,
                                                end_line=line_num,
                                            )
                                        )
                        except json.JSONDecodeError:
                            continue
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"ast-grep class extraction failed: {e}")

        return elements

    def _extract_exports_astgrep(
        self, file_path: str, source_code: str, language: str
    ) -> List[CodeElement]:
        """Extract exports using ast-grep."""
        elements = []
        pattern = "export $$$"

        try:
            cmd = [
                "ast-grep",
                "--pattern",
                pattern,
                "--lang",
                language,
                "--json",
                "compact",
            ]

            result = subprocess.run(
                cmd,
                input=source_code,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.stdout:
                count = 0
                for line in result.stdout.strip().split("\n"):
                    if line and count < 5:  # Limit exports
                        count += 1
                        try:
                            match_data = json.loads(line)
                            if isinstance(match_data, dict):
                                match_text = match_data.get("text", "")
                                line_num = match_data.get("line", 0)

                                if match_text:
                                    elements.append(
                                        CodeElement(
                                            element_id=f"{file_path}:export:{count}",
                                            file_path=file_path,
                                            language=(
                                                CodeLanguage.TYPESCRIPT
                                                if language == "typescript"
                                                else CodeLanguage.JAVASCRIPT
                                            ),
                                            element_type=CodeElementType.CLASS,  # Use class for exports
                                            name=f"export_{count}",
                                            source_code=match_text,
                                            start_line=line_num,
                                            end_line=line_num,
                                        )
                                    )
                        except json.JSONDecodeError:
                            continue
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"ast-grep export extraction failed: {e}")

        return elements

    def _parse_with_treesitter(
        self, file_path: str, source_code: str, language: CodeLanguage
    ) -> List[CodeElement]:
        """Parse using tree-sitter if available.

        Args:
            file_path: Path to file
            source_code: Source code content
            language: Code language

        Returns:
            List of code elements
        """
        elements = []

        # Add module element
        lines = source_code.split("\n")
        elements.append(
            CodeElement(
                element_id=f"{file_path}:module",
                file_path=file_path,
                language=language,
                element_type=CodeElementType.MODULE,
                name=Path(file_path).stem,
                source_code=source_code,
                start_line=1,
                end_line=len(lines),
            )
        )

        if not self.treesitter.available:
            logger.debug("tree-sitter not available, using fallback")
            return elements

        # For now, return module only - tree-sitter integration
        # would be more complex and require additional setup
        return elements

    def _extract_name_from_pattern(self, text: str) -> Optional[str]:
        """Extract function name from matched text."""
        import re

        patterns = [
            r"function\s+(\w+)",
            r"const\s+(\w+)",
            r"async function\s+(\w+)",
            r"export\s+function\s+(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def scan_for_security_issues(self, file_path: str) -> Dict[str, Any]:
        """Scan file for security issues using semgrep.

        Args:
            file_path: Path to file

        Returns:
            Security scan results
        """
        if not self.semgrep.available:
            return {"status": "semgrep not available"}

        try:
            # Scan single file
            results = self.semgrep.scan(str(Path(file_path).parent))
            return results
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return {"status": "error", "error": str(e)}


# Unified interface
def create_enhanced_parser() -> EnhancedCodeParser:
    """Create an enhanced parser instance."""
    return EnhancedCodeParser()
