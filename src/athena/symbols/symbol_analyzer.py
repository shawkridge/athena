"""
Symbol Analyzer - Advanced Metrics & Analysis (Phase 1B)

Provides advanced analysis of symbols:
- Complexity metrics (cyclomatic, cognitive)
- Code quality scoring (maintainability index)
- Dependency analysis
- Pattern linking for Phase 4 integration

Author: Claude Code
Date: 2025-10-31
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from athena.symbols.symbol_models import Symbol, SymbolMetrics
from athena.symbols.symbol_store import SymbolStore


@dataclass
class ComplexityAnalysis:
    """Analysis results for a symbol."""

    symbol_id: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: float
    branch_count: int
    nesting_levels: List[int]
    quality_issues: List[str]


class SymbolAnalyzer:
    """Analyzes symbols for complexity, quality, and dependencies."""

    # Complexity indicators
    BRANCH_KEYWORDS = {
        "if",
        "elif",
        "else",
        "for",
        "while",
        "except",
        "case",
        "switch",
        "catch",
        "finally",
        "ternary",
    }

    COGNITIVE_OPERATORS = {
        "if",
        "else",
        "elif",
        "for",
        "while",
        "switch",
        "case",
        "catch",
        "&&",
        "||",
        "?",
        "?.",
        "throw",
        "try",
        "except",
    }

    def __init__(self, store: SymbolStore):
        """Initialize analyzer with symbol store.

        Args:
            store: SymbolStore instance for database access
        """
        self.store = store

    def analyze_symbol(self, symbol: Symbol) -> ComplexityAnalysis:
        """Perform comprehensive analysis on a symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            ComplexityAnalysis with all metrics and issues
        """
        # Compute metrics
        cyclomatic = self.compute_cyclomatic_complexity(symbol)
        cognitive = self.compute_cognitive_complexity(symbol)
        maintainability = self.compute_maintainability_index(symbol, cyclomatic)

        # Detect quality issues
        issues = self._detect_quality_issues(symbol, cyclomatic, cognitive)

        # Analyze nesting
        nesting_levels = self._analyze_nesting(symbol)

        return ComplexityAnalysis(
            symbol_id=symbol.id or 0,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            maintainability_index=maintainability,
            branch_count=cyclomatic - 1,  # Branch count = CC - 1
            nesting_levels=nesting_levels,
            quality_issues=issues,
        )

    def compute_cyclomatic_complexity(self, symbol: Symbol) -> int:
        """Compute cyclomatic complexity for a symbol.

        Cyclomatic complexity = 1 + number of decision points
        Decision points: if, elif, else, for, while, except, case, etc.

        Args:
            symbol: Symbol to analyze

        Returns:
            Cyclomatic complexity (minimum 1)
        """
        if not symbol.code:
            return 1

        code = symbol.code
        complexity = 1

        # Count branch keywords
        for keyword in self.BRANCH_KEYWORDS:
            # Use word boundaries to avoid matching partial words
            pattern = r"\b" + keyword + r"\b"
            matches = len(re.findall(pattern, code, re.IGNORECASE))
            complexity += matches

        return max(1, complexity)

    def compute_cognitive_complexity(self, symbol: Symbol) -> int:
        """Compute cognitive complexity for a symbol.

        Cognitive complexity = sum of:
        - Each decision point (+1)
        - Each nesting level (+1 per level)
        - Boolean operators at high nesting (+1 per boolean)

        Args:
            symbol: Symbol to analyze

        Returns:
            Cognitive complexity (minimum 1)
        """
        if not symbol.code:
            return 1

        code = symbol.code
        complexity = 0
        nesting_depth = 0

        # Simple heuristic: count indentation changes and operators
        lines = code.split("\n")

        for line in lines:
            # Get indentation level
            indent = len(line) - len(line.lstrip())
            level = indent // 4  # Assume 4-space indentation

            # Count operators at this nesting level
            stripped = line.strip()
            if stripped:
                # Decision points - use simple string matching for operators
                found_operator = False
                for keyword in self.COGNITIVE_OPERATORS:
                    # For special characters, use simple substring match
                    if keyword in ("&&", "||", "?."):
                        if keyword in stripped:
                            found_operator = True
                            break
                    else:
                        # For word-based keywords, use regex with word boundaries
                        pattern = r"\b" + re.escape(keyword) + r"\b"
                        if re.search(pattern, stripped, re.IGNORECASE):
                            found_operator = True
                            break

                if found_operator:
                    # Add 1 for the operator, +nesting bonus
                    complexity += 1 + (level // 2)

                # Boolean operators
                if (
                    "&&" in stripped
                    or "||" in stripped
                    or " and " in stripped
                    or " or " in stripped
                ):
                    complexity += level  # More cognitive load at higher nesting

        return max(1, complexity)

    def compute_maintainability_index(
        self, symbol: Symbol, cyclomatic_complexity: Optional[int] = None
    ) -> float:
        """Compute maintainability index (0-100 scale).

        Formula approximation:
        MI = 100 - (3.2 * ln(Halstead Volume) - 0.23 * CC + 50 * sqrt(LLOC))

        We use simplified version:
        MI = 100 - min(50, CC * 5 + LOC * 0.1 - docstring_bonus)

        Args:
            symbol: Symbol to analyze
            cyclomatic_complexity: Pre-computed CC (if available)

        Returns:
            Maintainability Index (0.0-100.0)
        """
        if cyclomatic_complexity is None:
            cyclomatic_complexity = self.compute_cyclomatic_complexity(symbol)

        loc = (
            symbol.metrics.lines_of_code if symbol.metrics else len((symbol.code or "").split("\n"))
        )

        # Start with base score
        score = 100.0

        # Penalty for cyclomatic complexity
        score -= cyclomatic_complexity * 3

        # Penalty for size
        score -= loc * 0.05

        # Bonus for documentation
        if symbol.docstring and len(symbol.docstring) > 20:
            score += 5

        # Bonus for short parameter list
        if symbol.metrics and symbol.metrics.parameters <= 2:
            score += 3

        # Clamp to 0-100
        return max(0.0, min(100.0, score))

    def compute_dependencies(self, symbol: Symbol) -> Dict[str, int]:
        """Analyze dependencies for a symbol.

        Looks for function calls, imports, and other references in symbol code.

        Args:
            symbol: Symbol to analyze

        Returns:
            Dictionary mapping target symbol name to dependency type
        """
        if not symbol.code:
            return {}

        dependencies = {}
        code = symbol.code

        # Simple heuristics for finding dependencies

        # Pattern 1: Function calls - identifier followed by (
        call_pattern = r"([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\("
        for match in re.finditer(call_pattern, code):
            target = match.group(1)
            dependencies[target] = 1

        # Pattern 2: Method calls - object.method
        method_pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)\."
        for match in re.finditer(method_pattern, code):
            target = match.group(1)
            if target not in dependencies:
                dependencies[target] = 1

        # Pattern 3: Imports (basic)
        import_pattern = r"(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)"
        for match in re.finditer(import_pattern, code):
            target = match.group(1)
            dependencies[target] = 1

        return dependencies

    def compute_metrics(self, symbol: Symbol) -> SymbolMetrics:
        """Compute or update all metrics for a symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            Updated SymbolMetrics instance
        """
        cyclomatic = self.compute_cyclomatic_complexity(symbol)
        cognitive = self.compute_cognitive_complexity(symbol)
        maintainability = self.compute_maintainability_index(symbol, cyclomatic)

        loc = len((symbol.code or "").split("\n"))
        nesting = self._compute_nesting_depth(symbol)

        return SymbolMetrics(
            lines_of_code=loc,
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            parameters=symbol.metrics.parameters if symbol.metrics else 0,
            nesting_depth=nesting,
            maintainability_index=maintainability,
        )

    def link_symbol_to_patterns(self, symbol: Symbol, pattern_names: List[str]) -> Dict[str, float]:
        """Link symbol to procedural patterns (Phase 4 integration).

        Scores how well this symbol matches known patterns from Phase 4.

        Args:
            symbol: Symbol to analyze
            pattern_names: Names of patterns to match against

        Returns:
            Dictionary mapping pattern name to match score (0.0-1.0)
        """
        scores = {}

        # For each pattern, compute a match score
        for pattern in pattern_names:
            score = self._compute_pattern_match_score(symbol, pattern)
            scores[pattern] = score

        return scores

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _detect_quality_issues(self, symbol: Symbol, cyclomatic: int, cognitive: int) -> List[str]:
        """Detect quality issues in a symbol.

        Args:
            symbol: Symbol to analyze
            cyclomatic: Cyclomatic complexity
            cognitive: Cognitive complexity

        Returns:
            List of quality issues found
        """
        issues = []

        # Complexity issues
        if cyclomatic > 10:
            issues.append(f"High cyclomatic complexity: {cyclomatic}")
        if cognitive > 20:
            issues.append(f"High cognitive complexity: {cognitive}")

        # Size issues
        if symbol.metrics and symbol.metrics.lines_of_code > 200:
            issues.append(f"Large function: {symbol.metrics.lines_of_code} LOC")

        # Documentation issues
        if not symbol.docstring or len(symbol.docstring) < 10:
            issues.append("Missing or minimal docstring")

        # Parameter issues
        if symbol.metrics and symbol.metrics.parameters > 5:
            issues.append(f"Many parameters: {symbol.metrics.parameters}")

        # Nesting issues
        if symbol.metrics and symbol.metrics.nesting_depth > 4:
            issues.append(f"Deep nesting: {symbol.metrics.nesting_depth} levels")

        return issues

    def _analyze_nesting(self, symbol: Symbol) -> List[int]:
        """Analyze nesting levels in symbol code.

        Args:
            symbol: Symbol to analyze

        Returns:
            List of nesting depths per line
        """
        if not symbol.code:
            return []

        nesting_levels = []
        lines = symbol.code.split("\n")

        for line in lines:
            if line.strip():
                # Count indentation (assume 4 spaces = 1 level)
                indent = len(line) - len(line.lstrip())
                level = indent // 4
                nesting_levels.append(level)

        return nesting_levels

    def _compute_nesting_depth(self, symbol: Symbol) -> int:
        """Compute maximum nesting depth in symbol code.

        Args:
            symbol: Symbol to analyze

        Returns:
            Maximum nesting depth
        """
        nesting_levels = self._analyze_nesting(symbol)
        return max(nesting_levels) if nesting_levels else 0

    def _compute_pattern_match_score(self, symbol: Symbol, pattern_name: str) -> float:
        """Compute match score between symbol and a pattern.

        Args:
            symbol: Symbol to match
            pattern_name: Name of pattern to match against

        Returns:
            Match score (0.0-1.0)
        """
        # This is a placeholder for Phase 4 integration
        # In Phase 4, this will interface with the procedural learning system

        score = 0.0

        # Example: Check if symbol matches common patterns
        if "get_" in symbol.name or "fetch_" in symbol.name:
            if pattern_name == "getter":
                score = 0.8

        if "set_" in symbol.name or "update_" in symbol.name:
            if pattern_name == "setter":
                score = 0.8

        if symbol.symbol_type == "class":
            if pattern_name == "class_pattern":
                score = 0.9

        # Bonus for simple, well-documented functions
        if symbol.docstring and len(symbol.docstring) > 50:
            score += 0.1

        return min(1.0, score)
