"""Documentation Analyzer for measuring code documentation quality.

Provides:
- Docstring presence and completeness checking
- Parameter documentation verification
- Return type documentation checking
- Example code detection and quality
- Documentation coverage metrics
- Quality scoring and grading
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class DocumentationQuality(str, Enum):
    """Documentation quality levels."""
    MISSING = "missing"  # No docstring
    INCOMPLETE = "incomplete"  # Missing key sections
    ADEQUATE = "adequate"  # Has docstring with basic info
    GOOD = "good"  # Well documented with examples
    EXCELLENT = "excellent"  # Comprehensive with multiple examples


@dataclass
class DocumentationMetrics:
    """Documentation metrics for a symbol."""
    symbol: Symbol
    has_docstring: bool
    docstring_length: int
    has_summary: bool
    has_description: bool
    has_parameters: bool
    documented_parameters: int
    total_parameters: int
    has_return_type: bool
    has_return_description: bool
    has_raises: bool
    has_examples: bool
    example_count: int
    parameter_coverage: float  # 0.0-1.0
    quality_score: float  # 0.0-100.0
    quality_grade: DocumentationQuality


@dataclass
class DocumentationViolation:
    """A detected documentation issue."""
    symbol: Symbol
    violation_type: str  # "missing_docstring", "missing_params", "missing_return", etc.
    severity: str  # low, medium, high, critical
    missing_items: List[str]
    recommendation: str


class DocumentationAnalyzer:
    """Analyzes code documentation quality."""

    def __init__(self):
        """Initialize the documentation analyzer."""
        self.metrics: Dict[str, DocumentationMetrics] = {}
        self.violations: List[DocumentationViolation] = []

    def analyze_symbol(self, symbol: Symbol) -> DocumentationMetrics:
        """Analyze documentation of a symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            DocumentationMetrics for the symbol
        """
        has_doc = symbol.docstring is not None and len(symbol.docstring.strip()) > 0
        doc_length = len(symbol.docstring) if has_doc else 0

        if not has_doc:
            # No documentation
            metrics = DocumentationMetrics(
                symbol=symbol,
                has_docstring=False,
                docstring_length=0,
                has_summary=False,
                has_description=False,
                has_parameters=False,
                documented_parameters=0,
                total_parameters=0,
                has_return_type=False,
                has_return_description=False,
                has_raises=False,
                has_examples=False,
                example_count=0,
                parameter_coverage=0.0,
                quality_score=0.0,
                quality_grade=DocumentationQuality.MISSING
            )
            self.metrics[symbol.full_qualified_name or symbol.name] = metrics
            self._check_violations(metrics)
            return metrics

        # Parse docstring
        doc_lines = symbol.docstring.strip().split('\n')
        has_summary = len(doc_lines) > 0 and len(doc_lines[0].strip()) > 0
        has_description = len(doc_lines) > 1
        has_params = self._check_section_exists(symbol.docstring, ['Args:', 'Arguments:', 'Parameters:'])
        has_return = self._check_section_exists(symbol.docstring, ['Returns:', 'Return:'])
        has_raises = self._check_section_exists(symbol.docstring, ['Raises:', 'Exceptions:'])
        has_examples = self._check_section_exists(symbol.docstring, ['Examples:', 'Example:'])
        example_count = self._count_examples(symbol.docstring)

        # Count documented parameters
        total_params = self._count_parameters(symbol)
        documented_params = self._count_documented_parameters(symbol.docstring) if has_params else 0
        param_coverage = documented_params / total_params if total_params > 0 else 1.0 if not has_params else 0.0

        has_return_desc = self._has_return_description(symbol.docstring) if has_return else False

        quality_score = self._calculate_quality_score(
            has_summary, has_description, has_params, has_return,
            has_raises, has_examples, param_coverage, doc_length
        )
        quality_grade = self._grade_quality(quality_score, has_docstring=True)

        metrics = DocumentationMetrics(
            symbol=symbol,
            has_docstring=True,
            docstring_length=doc_length,
            has_summary=has_summary,
            has_description=has_description,
            has_parameters=has_params,
            documented_parameters=documented_params,
            total_parameters=total_params,
            has_return_type=has_return,
            has_return_description=has_return_desc,
            has_raises=has_raises,
            has_examples=has_examples,
            example_count=example_count,
            parameter_coverage=param_coverage,
            quality_score=quality_score,
            quality_grade=quality_grade
        )

        self.metrics[symbol.full_qualified_name or symbol.name] = metrics
        self._check_violations(metrics)

        return metrics

    def _check_section_exists(self, docstring: str, section_names: List[str]) -> bool:
        """Check if any of the section names exist in docstring."""
        for section in section_names:
            if section in docstring:
                return True
        return False

    def _count_examples(self, docstring: str) -> int:
        """Count number of code examples in docstring."""
        # Look for code blocks marked with >>> or ```
        code_blocks = len(re.findall(r'```|>>>', docstring))
        return code_blocks

    def _count_parameters(self, symbol: Symbol) -> int:
        """Count function parameters."""
        if not symbol.signature:
            return 0

        sig = symbol.signature.strip('()')
        if not sig:
            return 0

        params = [p.strip() for p in sig.split(',')]
        params = [p for p in params if p and p not in ('self', 'cls')]

        return len(params)

    def _count_documented_parameters(self, docstring: str) -> int:
        """Count number of documented parameters in docstring."""
        # Look for parameter documentation patterns like "param_name:" or "- param_name"
        param_pattern = re.compile(r'(\w+)\s*(?::|:=|-)')
        matches = param_pattern.findall(docstring)

        # Filter to likely parameter documentation (after Args/Parameters section)
        args_section = False
        documented = set()

        for line in docstring.split('\n'):
            if 'Args:' in line or 'Arguments:' in line or 'Parameters:' in line:
                args_section = True
                continue
            if args_section and line.strip().startswith(('Returns:', 'Yields:', 'Raises:', 'Examples:')):
                break
            if args_section and ':' in line:
                param_name = line.split(':')[0].strip().lstrip('-').strip()
                if param_name and not param_name.startswith('*'):
                    documented.add(param_name)

        return len(documented)

    def _has_return_description(self, docstring: str) -> bool:
        """Check if return section has description."""
        returns_section = False
        for line in docstring.split('\n'):
            if 'Returns:' in line or 'Return:' in line:
                returns_section = True
                continue
            if returns_section:
                if line.strip().startswith(('Raises:', 'Examples:', 'Args:')):
                    break
                if len(line.strip()) > 0 and not line.strip().startswith('-'):
                    return True

        return False

    def _calculate_quality_score(
        self,
        has_summary: bool,
        has_description: bool,
        has_params: bool,
        has_return: bool,
        has_raises: bool,
        has_examples: bool,
        param_coverage: float,
        doc_length: int
    ) -> float:
        """Calculate documentation quality score (0-100)."""
        score = 0.0

        # Summary (20 points)
        if has_summary:
            score += 20

        # Description (15 points)
        if has_description:
            score += 15

        # Parameters (20 points)
        if has_params:
            score += 20 * param_coverage

        # Return documentation (15 points)
        if has_return:
            score += 15

        # Raises documentation (10 points)
        if has_raises:
            score += 10

        # Examples (15 points)
        if has_examples:
            score += 15

        # Bonus for length (5 points) - comprehensive documentation
        if doc_length > 200:
            score += 5

        return min(100.0, score)

    def _grade_quality(self, quality_score: float, has_docstring: bool) -> DocumentationQuality:
        """Grade documentation quality based on score."""
        if not has_docstring:
            return DocumentationQuality.MISSING
        if quality_score >= 85:
            return DocumentationQuality.EXCELLENT
        elif quality_score >= 70:
            return DocumentationQuality.GOOD
        elif quality_score >= 50:
            return DocumentationQuality.ADEQUATE
        else:
            return DocumentationQuality.INCOMPLETE

    def _check_violations(self, metrics: DocumentationMetrics) -> None:
        """Check for documentation violations."""
        missing_items = []

        # Critical: no docstring for public functions/classes
        if (metrics.symbol.visibility == "public" and
            metrics.symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS] and
            not metrics.has_docstring):
            violation = DocumentationViolation(
                symbol=metrics.symbol,
                violation_type="missing_docstring",
                severity="critical",
                missing_items=["Docstring"],
                recommendation=f"Add docstring to public {metrics.symbol.symbol_type.value} '{metrics.symbol.name}'."
            )
            self.violations.append(violation)
            return

        if not metrics.has_docstring:
            return

        # Missing summary
        if not metrics.has_summary:
            missing_items.append("Summary line")

        # Missing parameter documentation
        if metrics.total_parameters > 0 and metrics.parameter_coverage < 1.0:
            undocumented = metrics.total_parameters - metrics.documented_parameters
            missing_items.append(f"{undocumented} parameter(s)")

        # Missing return documentation for functions that return value
        if (metrics.symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ASYNC_FUNCTION] and
            not metrics.has_return_type):
            missing_items.append("Return type documentation")

        # Missing examples for complex functions
        if (metrics.symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD] and
            not metrics.has_examples and metrics.quality_score < 70):
            missing_items.append("Usage example")

        if missing_items:
            severity = "critical" if metrics.quality_score < 30 else "high" if metrics.quality_score < 50 else "medium"
            violation = DocumentationViolation(
                symbol=metrics.symbol,
                violation_type="incomplete_documentation",
                severity=severity,
                missing_items=missing_items,
                recommendation=f"Improve documentation by adding: {', '.join(missing_items)}"
            )
            self.violations.append(violation)

    def get_metrics(self, symbol: Symbol) -> Optional[DocumentationMetrics]:
        """Get documentation metrics for a symbol.

        Args:
            symbol: Symbol to get metrics for

        Returns:
            DocumentationMetrics or None
        """
        key = symbol.full_qualified_name or symbol.name
        return self.metrics.get(key)

    def get_undocumented_symbols(self) -> List[Symbol]:
        """Get all undocumented public symbols.

        Returns:
            List of symbols without docstrings
        """
        undocumented = [
            m.symbol for m in self.metrics.values()
            if not m.has_docstring and m.symbol.visibility == "public"
        ]
        return undocumented

    def get_incomplete_documentation(self, quality_threshold: float = 70.0) -> List[Tuple[Symbol, float]]:
        """Get symbols with incomplete documentation.

        Args:
            quality_threshold: Minimum quality score (0-100)

        Returns:
            List of (symbol, quality_score) tuples sorted by score
        """
        incomplete = [
            (m.symbol, m.quality_score)
            for m in self.metrics.values()
            if m.quality_score < quality_threshold and m.has_docstring
        ]
        return sorted(incomplete, key=lambda x: x[1])

    def get_well_documented_symbols(self, quality_threshold: float = 85.0) -> List[Tuple[Symbol, float]]:
        """Get symbols with excellent documentation.

        Args:
            quality_threshold: Minimum quality score (0-100)

        Returns:
            List of (symbol, quality_score) tuples sorted by score
        """
        well_doc = [
            (m.symbol, m.quality_score)
            for m in self.metrics.values()
            if m.quality_score >= quality_threshold
        ]
        return sorted(well_doc, key=lambda x: x[1], reverse=True)

    def get_missing_parameter_docs(self) -> List[Tuple[Symbol, int, int]]:
        """Get symbols with missing parameter documentation.

        Returns:
            List of (symbol, documented_count, total_count) tuples
        """
        missing = [
            (m.symbol, m.documented_parameters, m.total_parameters)
            for m in self.metrics.values()
            if m.total_parameters > 0 and m.documented_parameters < m.total_parameters
        ]
        return missing

    def get_missing_return_docs(self) -> List[Symbol]:
        """Get functions/methods without return documentation.

        Returns:
            List of symbols that should have return documentation
        """
        missing = [
            m.symbol for m in self.metrics.values()
            if m.symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ASYNC_FUNCTION]
            and not m.has_return_type
        ]
        return missing

    def get_violations(self, severity: Optional[str] = None) -> List[DocumentationViolation]:
        """Get documentation violations.

        Args:
            severity: Filter by severity (low, medium, high, critical)

        Returns:
            List of violations
        """
        if severity:
            return [v for v in self.violations if v.severity == severity]
        return self.violations

    def get_coverage_stats(self) -> Dict:
        """Get overall documentation coverage statistics.

        Returns:
            Dictionary with coverage metrics
        """
        if not self.metrics:
            return {
                "total_symbols": 0,
                "documented": 0,
                "undocumented": 0,
                "coverage": 0.0,
                "avg_quality_score": 0.0,
                "excellent_count": 0,
                "good_count": 0,
                "adequate_count": 0,
                "incomplete_count": 0,
                "missing_count": 0,
            }

        documented = len([m for m in self.metrics.values() if m.has_docstring])
        undocumented = len(self.metrics) - documented

        coverage = documented / len(self.metrics) if self.metrics else 0.0
        avg_score = sum(m.quality_score for m in self.metrics.values()) / len(self.metrics) if self.metrics else 0.0

        excellent = len([m for m in self.metrics.values() if m.quality_grade == DocumentationQuality.EXCELLENT])
        good = len([m for m in self.metrics.values() if m.quality_grade == DocumentationQuality.GOOD])
        adequate = len([m for m in self.metrics.values() if m.quality_grade == DocumentationQuality.ADEQUATE])
        incomplete = len([m for m in self.metrics.values() if m.quality_grade == DocumentationQuality.INCOMPLETE])
        missing = len([m for m in self.metrics.values() if m.quality_grade == DocumentationQuality.MISSING])

        return {
            "total_symbols": len(self.metrics),
            "documented": documented,
            "undocumented": undocumented,
            "coverage": coverage,
            "avg_quality_score": avg_score,
            "excellent_count": excellent,
            "good_count": good,
            "adequate_count": adequate,
            "incomplete_count": incomplete,
            "missing_count": missing,
        }

    def get_documentation_report(self) -> str:
        """Generate a human-readable documentation report.

        Returns:
            Formatted report string
        """
        stats = self.get_coverage_stats()

        report = "═" * 70 + "\n"
        report += "                DOCUMENTATION COVERAGE REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Symbols:        {stats['total_symbols']}\n"
        report += f"Documented:           {stats['documented']} ({stats['coverage']*100:.1f}%)\n"
        report += f"Undocumented:         {stats['undocumented']}\n"
        report += f"Avg Quality Score:    {stats['avg_quality_score']:.1f}/100\n\n"

        report += "Quality Distribution:\n"
        report += f"  Excellent:  {stats['excellent_count']} symbols\n"
        report += f"  Good:       {stats['good_count']} symbols\n"
        report += f"  Adequate:   {stats['adequate_count']} symbols\n"
        report += f"  Incomplete: {stats['incomplete_count']} symbols\n"
        report += f"  Missing:    {stats['missing_count']} symbols\n\n"

        # Undocumented symbols
        undocumented = self.get_undocumented_symbols()
        if undocumented:
            report += "─" * 70 + "\n"
            report += "Undocumented Public Symbols:\n"
            report += "─" * 70 + "\n"
            for symbol in undocumented[:10]:
                report += f"{symbol.name:40} ({symbol.symbol_type.value})\n"

        # Incomplete documentation
        incomplete = self.get_incomplete_documentation(quality_threshold=70.0)
        if incomplete:
            report += "\n" + "─" * 70 + "\n"
            report += "Symbols with Incomplete Documentation:\n"
            report += "─" * 70 + "\n"
            for symbol, score in incomplete[:10]:
                report += f"{symbol.name:40} quality: {score:.1f}\n"

        # Missing return docs
        missing_return = self.get_missing_return_docs()
        if missing_return:
            report += "\n" + "─" * 70 + "\n"
            report += "Functions Missing Return Documentation:\n"
            report += "─" * 70 + "\n"
            for symbol in missing_return[:10]:
                report += f"{symbol.name:40}\n"

        return report

    def suggest_improvements(self, symbol: Symbol) -> List[str]:
        """Suggest documentation improvements for a symbol.

        Args:
            symbol: Symbol to suggest improvements for

        Returns:
            List of improvement suggestions
        """
        metrics = self.get_metrics(symbol)
        if not metrics:
            return []

        suggestions = []

        # No docstring
        if not metrics.has_docstring:
            suggestions.append(
                f"Add docstring to {symbol.symbol_type.value} '{symbol.name}'. "
                "Include summary, parameters, return type, and examples."
            )
            return suggestions

        # Missing summary
        if not metrics.has_summary:
            suggestions.append("Add a one-line summary at the start of the docstring.")

        # Missing description
        if not metrics.has_description:
            suggestions.append("Add a more detailed description after the summary.")

        # Missing parameter documentation
        if metrics.total_parameters > 0 and metrics.parameter_coverage < 1.0:
            missing_params = metrics.total_parameters - metrics.documented_parameters
            suggestions.append(
                f"Document {missing_params} missing parameter(s) in the Args section."
            )

        # Missing return documentation
        if not metrics.has_return_type and metrics.symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD]:
            suggestions.append(
                "Add a Returns section documenting the return type and value."
            )

        # Missing examples
        if not metrics.has_examples and metrics.quality_score < 80:
            suggestions.append(
                "Add usage examples with >>> or ``` code blocks to illustrate how to use this function."
            )

        # Missing raises documentation
        if not metrics.has_raises and metrics.quality_score < 70:
            suggestions.append(
                "Document any exceptions that might be raised in a Raises section."
            )

        return suggestions
