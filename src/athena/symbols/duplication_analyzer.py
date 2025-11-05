"""Code Duplication Analyzer for detecting duplicate and similar code.

Provides:
- Exact code duplication detection
- Similar code pattern detection (fuzzy matching)
- Duplication metrics and statistics
- Similarity scoring (0.0-1.0)
- Refactoring opportunity identification
- Clone classification (Type 1, 2, 3)
"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import difflib
import hashlib

from .symbol_models import Symbol, SymbolType


class CloneType(str, Enum):
    """Types of code clones."""
    EXACT = "exact"  # Identical code
    SIMILAR = "similar"  # Very similar with minor differences
    LOOSE = "loose"  # Same logic, different structure


@dataclass
class CodeBlock:
    """A block of code from a symbol."""
    symbol: Symbol
    content: str
    hash_value: str
    line_count: int


@dataclass
class DuplicationPair:
    """A pair of duplicated code blocks."""
    symbol1: Symbol
    symbol2: Symbol
    clone_type: CloneType
    similarity_score: float  # 0.0-1.0
    lines_duplicated: int
    lines_total: int
    recommendation: str


@dataclass
class DuplicationMetrics:
    """Duplication metrics for a codebase."""
    total_symbols: int
    symbols_with_duplication: int
    duplication_pairs: int
    exact_duplicates: int
    similar_duplicates: int
    loose_duplicates: int
    total_duplicated_lines: int
    total_lines: int
    duplication_percentage: float


class DuplicationAnalyzer:
    """Analyzes code duplication patterns."""

    def __init__(self):
        """Initialize the duplication analyzer."""
        self.code_blocks: Dict[str, CodeBlock] = {}
        self.duplication_pairs: List[DuplicationPair] = []
        self.metrics: Optional[DuplicationMetrics] = None

    def add_symbol(self, symbol: Symbol, code: str) -> CodeBlock:
        """Add a symbol's code for duplication analysis.

        Args:
            symbol: Symbol to analyze
            code: Source code content

        Returns:
            CodeBlock for the symbol
        """
        # Normalize code for hashing
        normalized = self._normalize_code(code)
        hash_value = self._hash_code(normalized)
        line_count = len(code.split('\n'))

        block = CodeBlock(
            symbol=symbol,
            content=code,
            hash_value=hash_value,
            line_count=line_count
        )

        key = symbol.full_qualified_name or symbol.name
        self.code_blocks[key] = block

        return block

    def analyze_all(self, similarity_threshold: float = 0.8) -> List[DuplicationPair]:
        """Analyze all added symbols for duplication.

        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of detected duplication pairs
        """
        self.duplication_pairs = []
        blocks = list(self.code_blocks.values())

        # Check all pairs
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                pair = self._compare_blocks(blocks[i], blocks[j], similarity_threshold)
                if pair:
                    self.duplication_pairs.append(pair)

        # Calculate metrics
        self._calculate_metrics()

        return self.duplication_pairs

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison.

        Removes comments, extra whitespace, and normalizes indentation.
        """
        lines = code.split('\n')
        normalized = []

        for line in lines:
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]

            # Strip whitespace
            line = line.strip()

            # Skip empty lines
            if line:
                normalized.append(line)

        return '\n'.join(normalized)

    def _hash_code(self, code: str) -> str:
        """Generate hash of normalized code."""
        return hashlib.md5(code.encode()).hexdigest()

    def _compare_blocks(self, block1: CodeBlock, block2: CodeBlock, threshold: float) -> Optional[DuplicationPair]:
        """Compare two code blocks for duplication.

        Args:
            block1: First code block
            block2: Second code block
            threshold: Minimum similarity threshold

        Returns:
            DuplicationPair if similarity meets threshold, None otherwise
        """
        # Exact match check
        if block1.hash_value == block2.hash_value:
            lines_dup = min(block1.line_count, block2.line_count)
            lines_total = max(block1.line_count, block2.line_count)

            return DuplicationPair(
                symbol1=block1.symbol,
                symbol2=block2.symbol,
                clone_type=CloneType.EXACT,
                similarity_score=1.0,
                lines_duplicated=lines_dup,
                lines_total=lines_total,
                recommendation=f"Extract {lines_dup} duplicated lines into a shared function."
            )

        # Fuzzy similarity matching
        normalized1 = self._normalize_code(block1.content)
        normalized2 = self._normalize_code(block2.content)

        similarity = self._calculate_similarity(normalized1, normalized2)

        if similarity >= threshold:
            clone_type = self._classify_clone(normalized1, normalized2, similarity)
            lines_dup = self._count_matching_lines(normalized1, normalized2)
            lines_total = max(block1.line_count, block2.line_count)

            return DuplicationPair(
                symbol1=block1.symbol,
                symbol2=block2.symbol,
                clone_type=clone_type,
                similarity_score=similarity,
                lines_duplicated=lines_dup,
                lines_total=lines_total,
                recommendation=self._generate_recommendation(clone_type, similarity, lines_dup)
            )

        return None

    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code blocks.

        Uses SequenceMatcher for fuzzy matching.
        """
        matcher = difflib.SequenceMatcher(None, code1, code2)
        return matcher.ratio()

    def _classify_clone(self, code1: str, code2: str, similarity: float) -> CloneType:
        """Classify the type of code clone.

        Type 1: Exact duplicates
        Type 2: Similar with minor differences (variable names, etc.)
        Type 3: Same logic, different structure
        """
        if similarity >= 0.95:
            return CloneType.SIMILAR
        else:
            return CloneType.LOOSE

    def _count_matching_lines(self, code1: str, code2: str) -> int:
        """Count approximately matching lines between two code blocks."""
        lines1 = code1.split('\n')
        lines2 = code2.split('\n')

        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        matching_blocks = matcher.get_matching_blocks()

        count = 0
        for block in matching_blocks:
            count += block.size

        return count

    def _generate_recommendation(self, clone_type: CloneType, similarity: float, lines: int) -> str:
        """Generate refactoring recommendation based on duplication."""
        if clone_type == CloneType.EXACT:
            return f"Extract {lines} identical lines into a shared function or utility."
        elif clone_type == CloneType.SIMILAR:
            return f"Extract {lines} similar lines into a parameterized function ({similarity*100:.0f}% match)."
        else:
            return f"Refactor {lines} lines with similar logic into a shared implementation ({similarity*100:.0f}% match)."

    def _calculate_metrics(self) -> None:
        """Calculate overall duplication metrics."""
        if not self.code_blocks:
            self.metrics = DuplicationMetrics(
                total_symbols=0,
                symbols_with_duplication=0,
                duplication_pairs=0,
                exact_duplicates=0,
                similar_duplicates=0,
                loose_duplicates=0,
                total_duplicated_lines=0,
                total_lines=0,
                duplication_percentage=0.0
            )
            return

        # Count symbols with duplication
        symbols_with_dup = set()
        for pair in self.duplication_pairs:
            symbols_with_dup.add(pair.symbol1.name)
            symbols_with_dup.add(pair.symbol2.name)

        # Count by clone type
        exact_count = len([p for p in self.duplication_pairs if p.clone_type == CloneType.EXACT])
        similar_count = len([p for p in self.duplication_pairs if p.clone_type == CloneType.SIMILAR])
        loose_count = len([p for p in self.duplication_pairs if p.clone_type == CloneType.LOOSE])

        # Total duplicated lines
        total_dup_lines = sum(p.lines_duplicated for p in self.duplication_pairs)

        # Total lines
        total_lines = sum(block.line_count for block in self.code_blocks.values())

        dup_percentage = (total_dup_lines / total_lines * 100) if total_lines > 0 else 0.0

        self.metrics = DuplicationMetrics(
            total_symbols=len(self.code_blocks),
            symbols_with_duplication=len(symbols_with_dup),
            duplication_pairs=len(self.duplication_pairs),
            exact_duplicates=exact_count,
            similar_duplicates=similar_count,
            loose_duplicates=loose_count,
            total_duplicated_lines=total_dup_lines,
            total_lines=total_lines,
            duplication_percentage=dup_percentage
        )

    def get_exact_duplicates(self) -> List[DuplicationPair]:
        """Get exact code duplicates.

        Returns:
            List of exact duplication pairs
        """
        return [p for p in self.duplication_pairs if p.clone_type == CloneType.EXACT]

    def get_similar_duplicates(self) -> List[DuplicationPair]:
        """Get similar code duplicates.

        Returns:
            List of similar duplication pairs
        """
        return [p for p in self.duplication_pairs if p.clone_type == CloneType.SIMILAR]

    def get_loose_duplicates(self) -> List[DuplicationPair]:
        """Get loosely similar code duplicates.

        Returns:
            List of loose duplication pairs
        """
        return [p for p in self.duplication_pairs if p.clone_type == CloneType.LOOSE]

    def get_duplicates_for_symbol(self, symbol: Symbol) -> List[DuplicationPair]:
        """Get all duplication pairs involving a symbol.

        Args:
            symbol: Symbol to find duplicates for

        Returns:
            List of duplication pairs
        """
        return [
            p for p in self.duplication_pairs
            if p.symbol1.name == symbol.name or p.symbol2.name == symbol.name
        ]

    def get_worst_offenders(self, limit: int = 10) -> List[Tuple[Symbol, int]]:
        """Get symbols with most duplication.

        Args:
            limit: Maximum number of results

        Returns:
            List of (symbol, duplication_count) tuples sorted by count
        """
        dup_count: Dict[str, int] = {}

        for pair in self.duplication_pairs:
            name1 = pair.symbol1.name
            name2 = pair.symbol2.name
            dup_count[name1] = dup_count.get(name1, 0) + 1
            dup_count[name2] = dup_count.get(name2, 0) + 1

        # Find corresponding symbols
        result = []
        for name, count in sorted(dup_count.items(), key=lambda x: x[1], reverse=True)[:limit]:
            for block in self.code_blocks.values():
                if block.symbol.name == name:
                    result.append((block.symbol, count))
                    break

        return result

    def get_refactoring_opportunities(self) -> List[Tuple[DuplicationPair, str]]:
        """Get prioritized refactoring opportunities.

        Returns:
            List of (duplication_pair, priority_reason) sorted by impact
        """
        opportunities = []

        for pair in self.duplication_pairs:
            # Prioritize by lines * similarity
            impact = pair.lines_duplicated * pair.similarity_score

            if pair.clone_type == CloneType.EXACT:
                priority = "CRITICAL"
            elif pair.similarity_score >= 0.95:
                priority = "HIGH"
            else:
                priority = "MEDIUM"

            reason = f"{priority} - {pair.lines_duplicated} lines, {pair.similarity_score*100:.0f}% similar"
            opportunities.append((pair, reason))

        # Sort by impact
        return sorted(opportunities, key=lambda x: x[0].lines_duplicated * x[0].similarity_score, reverse=True)

    def get_metrics(self) -> Optional[DuplicationMetrics]:
        """Get overall duplication metrics.

        Returns:
            DuplicationMetrics or None if not analyzed
        """
        return self.metrics

    def get_duplication_report(self) -> str:
        """Generate a human-readable duplication report.

        Returns:
            Formatted report string
        """
        if not self.metrics:
            return "No duplication analysis performed. Call analyze_all() first."

        report = "═" * 70 + "\n"
        report += "                    CODE DUPLICATION REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Symbols:              {self.metrics.total_symbols}\n"
        report += f"Symbols with Duplication:   {self.metrics.symbols_with_duplication}\n"
        report += f"Duplication Pairs Found:    {self.metrics.duplication_pairs}\n"
        report += f"Total Duplicated Lines:     {self.metrics.total_duplicated_lines}\n"
        report += f"Total Lines:                {self.metrics.total_lines}\n"
        report += f"Duplication Percentage:     {self.metrics.duplication_percentage:.1f}%\n\n"

        report += "Clone Type Distribution:\n"
        report += f"  Exact:    {self.metrics.exact_duplicates} pairs\n"
        report += f"  Similar:  {self.metrics.similar_duplicates} pairs\n"
        report += f"  Loose:    {self.metrics.loose_duplicates} pairs\n\n"

        # Exact duplicates
        exact = self.get_exact_duplicates()
        if exact:
            report += "─" * 70 + "\n"
            report += "Exact Code Duplicates:\n"
            report += "─" * 70 + "\n"
            for pair in exact[:10]:
                report += f"{pair.symbol1.name:30} <-> {pair.symbol2.name:30}\n"

        # Worst offenders
        worst = self.get_worst_offenders(limit=5)
        if worst:
            report += "\n" + "─" * 70 + "\n"
            report += "Symbols with Most Duplication:\n"
            report += "─" * 70 + "\n"
            for symbol, count in worst:
                report += f"{symbol.name:40} duplicates: {count}\n"

        # Refactoring opportunities
        opportunities = self.get_refactoring_opportunities()
        if opportunities:
            report += "\n" + "─" * 70 + "\n"
            report += "Top Refactoring Opportunities:\n"
            report += "─" * 70 + "\n"
            for pair, reason in opportunities[:5]:
                report += f"{pair.symbol1.name:25} <-> {pair.symbol2.name:25}\n"
                report += f"  {reason}\n"

        return report

    def suggest_extraction(self, pair: DuplicationPair) -> List[str]:
        """Suggest extraction strategy for a duplication pair.

        Args:
            pair: Duplication pair to extract

        Returns:
            List of extraction suggestions
        """
        suggestions = []

        if pair.clone_type == CloneType.EXACT:
            suggestions.append(
                f"Extract {pair.lines_duplicated} lines into a shared function that both "
                f"'{pair.symbol1.name}' and '{pair.symbol2.name}' can call."
            )
        elif pair.clone_type == CloneType.SIMILAR:
            suggestions.append(
                f"Extract {pair.lines_duplicated} similar lines into a parameterized function "
                f"({pair.similarity_score*100:.0f}% match). Replace variable names with parameters."
            )
            suggestions.append(
                "Consider using a template or strategy pattern if the logic differs."
            )
        else:
            suggestions.append(
                f"The logic is {pair.similarity_score*100:.0f}% similar. Consider refactoring "
                "to extract common algorithm into a helper function."
            )

        if pair.lines_duplicated > 10:
            suggestions.append(
                f"This is a large duplication ({pair.lines_duplicated} lines). "
                "Strongly recommend extraction to reduce code maintenance burden."
            )

        return suggestions
