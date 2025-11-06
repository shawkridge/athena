"""Integration with modern code analysis tools: ast-grep, ripgrep, tree-sitter, semgrep."""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchMatch:
    """Result from a code search operation."""

    file_path: str
    line_number: int
    column: int
    matched_text: str
    context: Optional[str] = None


class RipgrepSearcher:
    """Fast file and pattern searching using ripgrep."""

    def __init__(self):
        """Initialize ripgrep searcher."""
        self.rg_available = self._check_ripgrep()

    @staticmethod
    def _check_ripgrep() -> bool:
        """Check if ripgrep is available."""
        try:
            subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            logger.info("ripgrep available for code searching")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            logger.warning("ripgrep not available, falling back to os.walk")
            return False

    def search(
        self,
        pattern: str,
        directory: str,
        file_type: Optional[str] = None,
        context_lines: int = 2,
    ) -> List[SearchMatch]:
        """Search for pattern using ripgrep.

        Args:
            pattern: Regex pattern to search for
            directory: Directory to search in
            file_type: File type filter (e.g., 'ts', 'js', 'py')
            context_lines: Lines of context to include

        Returns:
            List of SearchMatch objects
        """
        if not self.rg_available:
            return []

        try:
            cmd = [
                "rg",
                "--json",
                pattern,
                directory,
            ]

            if file_type:
                cmd.extend(["-t", file_type])

            if context_lines > 0:
                cmd.extend([f"-B{context_lines}", f"-A{context_lines}"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            matches = []
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        if data.get("type") == "match":
                            match_data = data.get("data", {})
                            matches.append(
                                SearchMatch(
                                    file_path=match_data.get("path", {}).get("text", ""),
                                    line_number=match_data.get("line_number", 0),
                                    column=match_data.get("submatches", [{}])[0].get("start", 0),
                                    matched_text=match_data.get("lines", {}).get("text", ""),
                                )
                            )
                    except json.JSONDecodeError:
                        continue

            return matches

        except subprocess.TimeoutExpired:
            logger.error(f"ripgrep search timed out for pattern: {pattern}")
            return []
        except Exception as e:
            logger.error(f"Error during ripgrep search: {e}")
            return []

    def find_imports(self, directory: str, file_type: str = "ts") -> List[str]:
        """Find all imports in a directory.

        Args:
            directory: Directory to search
            file_type: File type (ts, js, py, etc.)

        Returns:
            List of import statements
        """
        pattern = r"^import .* from ['\"]([^'\"]+)['\"]"
        matches = self.search(pattern, directory, file_type)
        return [m.matched_text for m in matches]

    def find_functions(self, directory: str, file_type: str = "ts") -> List[str]:
        """Find all function definitions.

        Args:
            directory: Directory to search
            file_type: File type

        Returns:
            List of function names
        """
        pattern = r"(?:function|const|async function)\s+(\w+)"
        matches = self.search(pattern, directory, file_type)
        return [m.matched_text for m in matches]


class AstGrepSearcher:
    """AST-based pattern matching using ast-grep."""

    def __init__(self):
        """Initialize ast-grep searcher."""
        self.available = self._check_astgrep()

    @staticmethod
    def _check_astgrep() -> bool:
        """Check if ast-grep is available."""
        try:
            subprocess.run(
                ["ast-grep", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            logger.info("ast-grep available for AST-based searching")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            logger.warning("ast-grep not available, falling back to regex")
            return False

    def search(
        self,
        pattern: str,
        language: str,
        directory: str,
    ) -> List[Dict[str, Any]]:
        """Search using AST patterns.

        Args:
            pattern: AST pattern (e.g., "useState($HOOK)")
            language: Language (ts, js, py, go, rust, java, etc.)
            directory: Directory to search

        Returns:
            List of matches with AST information
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ast-grep",
                "--pattern",
                pattern,
                "--lang",
                language,
                "--json",
                "short",
                directory,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if not result.stdout:
                return []

            matches = []
            try:
                data = json.loads(result.stdout)
                matches = data.get("matches", [])
            except json.JSONDecodeError:
                pass

            return matches

        except subprocess.TimeoutExpired:
            logger.error(f"ast-grep search timed out for pattern: {pattern}")
            return []
        except Exception as e:
            logger.error(f"Error during ast-grep search: {e}")
            return []

    def find_react_hooks(self, directory: str) -> List[Dict[str, Any]]:
        """Find all React hooks (useState, useEffect, etc.).

        Args:
            directory: Directory to search

        Returns:
            List of hook usage matches
        """
        patterns = [
            "useState($STATE)",
            "useEffect($EFFECT)",
            "useCallback($CALLBACK)",
            "useMemo($MEMO)",
            "useContext($CONTEXT)",
            "useReducer($REDUCER)",
            "useRef($REF)",
        ]

        all_matches = []
        for pattern in patterns:
            matches = self.search(pattern, "typescript", directory)
            all_matches.extend(matches)

        return all_matches

    def find_api_calls(self, directory: str) -> List[Dict[str, Any]]:
        """Find all API calls (fetch, axios, etc.).

        Args:
            directory: Directory to search

        Returns:
            List of API call matches
        """
        patterns = [
            "fetch($URL)",
            "axios.get($URL)",
            "axios.post($URL)",
            "axios.put($URL)",
            "axios.delete($URL)",
        ]

        all_matches = []
        for pattern in patterns:
            matches = self.search(pattern, "typescript", directory)
            all_matches.extend(matches)

        return all_matches

    def find_component_exports(self, directory: str) -> List[Dict[str, Any]]:
        """Find exported React components.

        Args:
            directory: Directory to search

        Returns:
            List of export matches
        """
        pattern = "export default $COMPONENT"
        return self.search(pattern, "typescript", directory)


class TreeSitterParser:
    """Tree-sitter based parsing for production-grade AST."""

    def __init__(self):
        """Initialize tree-sitter parser."""
        self.available = self._check_treesitter()
        self.parser = None
        self.languages = {}

    @staticmethod
    def _check_treesitter() -> bool:
        """Check if tree-sitter is available."""
        try:
            import tree_sitter  # noqa
            logger.info("tree-sitter available for precise AST parsing")
            return True
        except ImportError:
            logger.warning(
                "tree-sitter not installed. Install with: pip install tree-sitter tree-sitter-languages"
            )
            return False

    def parse(self, source_code: str, language: str) -> Optional[Any]:
        """Parse source code to AST.

        Args:
            source_code: Source code to parse
            language: Language (typescript, python, go, rust, java, etc.)

        Returns:
            AST root node or None if parsing fails
        """
        if not self.available:
            return None

        try:
            if self.parser is None:
                from tree_sitter import Parser
                self.parser = Parser()

            # Load language if not cached
            if language not in self.languages:
                from tree_sitter_languages import get_language
                self.languages[language] = get_language(language)

            lang = self.languages[language]
            self.parser.set_language(lang)

            tree = self.parser.parse(source_code.encode())
            return tree.root_node

        except Exception as e:
            logger.error(f"Error parsing with tree-sitter: {e}")
            return None

    def query(self, source_code: str, language: str, query_string: str) -> List[tuple]:
        """Query AST with a tree-sitter query.

        Args:
            source_code: Source code
            language: Language
            query_string: Tree-sitter query string

        Returns:
            List of (node, capture_name) tuples
        """
        if not self.available:
            return []

        try:
            from tree_sitter_languages import get_language

            lang = self.languages.get(language)
            if not lang:
                lang = get_language(language)
                self.languages[language] = lang

            query = lang.query(query_string)
            root = self.parse(source_code, language)

            if not root:
                return []

            captures = query.captures(root)
            return captures

        except Exception as e:
            logger.error(f"Error querying AST: {e}")
            return []


class SemgrepAnalyzer:
    """Security and pattern analysis using semgrep."""

    def __init__(self):
        """Initialize semgrep analyzer."""
        self.available = self._check_semgrep()

    @staticmethod
    def _check_semgrep() -> bool:
        """Check if semgrep is available."""
        try:
            subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            logger.info("semgrep available for advanced code analysis")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            logger.warning(
                "semgrep not installed. Install with: pip install semgrep or docker pull returntocorp/semgrep"
            )
            return False

    def scan(
        self,
        directory: str,
        rules: Optional[List[str]] = None,
        config: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scan directory with semgrep rules.

        Args:
            directory: Directory to scan
            rules: Specific rules to run (e.g., ['p/security-audit'])
            config: Path to config file

        Returns:
            Scan results with matches and metrics
        """
        if not self.available:
            return {"results": [], "errors": ["semgrep not available"]}

        try:
            cmd = ["semgrep", "--json", directory]

            if rules:
                for rule in rules:
                    cmd.extend(["--include-rule", rule])

            if config:
                cmd.extend(["--config", config])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.stdout:
                return json.loads(result.stdout)

            return {"results": [], "errors": result.stderr.split("\n")}

        except subprocess.TimeoutExpired:
            logger.error("semgrep scan timed out")
            return {"results": [], "errors": ["Timeout"]}
        except Exception as e:
            logger.error(f"Error during semgrep scan: {e}")
            return {"results": [], "errors": [str(e)]}

    def find_security_issues(self, directory: str) -> Dict[str, Any]:
        """Scan for common security issues.

        Args:
            directory: Directory to scan

        Returns:
            Security scan results
        """
        security_rules = [
            "p/security-audit",
            "p/owasp-top-ten",
            "p/cwe-top-25",
        ]

        return self.scan(directory, rules=security_rules)


# Unified interface
class ModernCodeAnalyzer:
    """Unified interface to modern code analysis tools."""

    def __init__(self):
        """Initialize all available tools."""
        self.ripgrep = RipgrepSearcher()
        self.astgrep = AstGrepSearcher()
        self.treesitter = TreeSitterParser()
        self.semgrep = SemgrepAnalyzer()

    def analyze(self, directory: str, analysis_type: str = "all") -> Dict[str, Any]:
        """Comprehensive code analysis.

        Args:
            directory: Directory to analyze
            analysis_type: 'all', 'search', 'patterns', 'security', 'ast'

        Returns:
            Analysis results
        """
        results = {}

        if analysis_type in ["all", "search"]:
            results["fast_search"] = {
                "imports": self.ripgrep.find_imports(directory),
                "functions": self.ripgrep.find_functions(directory),
            }

        if analysis_type in ["all", "patterns"]:
            results["patterns"] = {
                "react_hooks": self.astgrep.find_react_hooks(directory),
                "api_calls": self.astgrep.find_api_calls(directory),
                "exports": self.astgrep.find_component_exports(directory),
            }

        if analysis_type in ["all", "security"]:
            results["security"] = self.semgrep.find_security_issues(directory)

        return results


if __name__ == "__main__":
    # Example usage
    analyzer = ModernCodeAnalyzer()

    print("Available Tools:")
    print(f"  ripgrep: {analyzer.ripgrep.rg_available}")
    print(f"  ast-grep: {analyzer.astgrep.available}")
    print(f"  tree-sitter: {analyzer.treesitter.available}")
    print(f"  semgrep: {analyzer.semgrep.available}")

    # Analyze current directory
    results = analyzer.analyze(".", analysis_type="search")
    print(f"\nAnalysis Results:\n{json.dumps(results, indent=2, default=str)}")
