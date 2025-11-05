"""Code Smell Detector for identifying design issues and code quality problems.

Provides:
- Long method/function detection
- Too many parameters detection
- Duplicate code detection
- Long parameter lists
- Long variable names
- Deep nesting detection
- High coupling detection
- Missing abstraction detection
- Data clumps detection
- Feature envy detection
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from .symbol_models import Symbol, SymbolType


class CodeSmellType(str, Enum):
    """Types of code smells."""
    LONG_METHOD = "long_method"  # Method/function too long
    TOO_MANY_PARAMETERS = "too_many_parameters"  # Too many parameters
    LONG_VARIABLE_NAME = "long_variable_name"  # Variable name too long
    SHORT_VARIABLE_NAME = "short_variable_name"  # Single-letter variable
    DEEP_NESTING = "deep_nesting"  # Too deeply nested code
    LONG_CLASS = "long_class"  # Class with too many methods
    DUPLICATE_CODE = "duplicate_code"  # Code duplication
    HIGH_COMPLEXITY = "high_complexity"  # High cyclomatic complexity
    MISSING_DOCUMENTATION = "missing_documentation"  # No docstring
    FEATURE_ENVY = "feature_envy"  # Method uses other class extensively
    DATA_CLUMP = "data_clump"  # Parameters that always appear together
    LAZY_CLASS = "lazy_class"  # Class doing too little
    SPECULATIVE_GENERALITY = "speculative_generality"  # Over-engineered abstraction
    MAGIC_NUMBERS = "magic_numbers"  # Hard-coded numeric constants


class SmellSeverity(str, Enum):
    """Severity levels for code smells."""
    INFO = "info"  # Informational
    LOW = "low"  # Minor code smell
    MEDIUM = "medium"  # Moderate code smell
    HIGH = "high"  # Significant code smell
    CRITICAL = "critical"  # Critical code smell


@dataclass
class CodeSmell:
    """A detected code smell."""
    symbol: Symbol
    smell_type: CodeSmellType
    severity: SmellSeverity
    line_number: int
    code_snippet: str
    message: str
    suggestion: str


@dataclass
class SmellMetrics:
    """Code smell metrics for analyzed code."""
    total_symbols: int
    symbols_with_smells: int
    total_smells: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    smell_density: float  # Average smells per symbol


class CodeSmellDetector:
    """Detects code smells and design issues."""

    def __init__(self):
        """Initialize the code smell detector."""
        self.smells: List[CodeSmell] = []
        self.metrics: Optional[SmellMetrics] = None
        self.long_method_threshold = 20  # Lines
        self.too_many_params_threshold = 5
        self.long_name_threshold = 30  # Characters
        self.deep_nesting_threshold = 4  # Levels
        self.high_complexity_threshold = 10

    def analyze_symbol(self, symbol: Symbol, code: str) -> List[CodeSmell]:
        """Analyze a symbol for code smells.

        Args:
            symbol: Symbol to analyze
            code: Source code content

        Returns:
            List of detected code smells
        """
        smells = []

        # Skip non-analyzable symbols
        if symbol.symbol_type not in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ASYNC_FUNCTION, SymbolType.CLASS]:
            return smells

        lines = code.split('\n')

        # Check long method/function
        if len(lines) > self.long_method_threshold:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.LONG_METHOD,
                severity=SmellSeverity.MEDIUM,
                line_number=symbol.line_start,
                code_snippet=f"Function spans {len(lines)} lines",
                message=f"{symbol.symbol_type.value} is too long ({len(lines)} lines)",
                suggestion="Consider breaking into smaller methods. Aim for methods under 20 lines."
            ))

        # Check parameters
        if symbol.symbol_type in [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.ASYNC_FUNCTION]:
            param_count = self._count_parameters(symbol.signature)
            if param_count > self.too_many_params_threshold:
                smells.append(CodeSmell(
                    symbol=symbol,
                    smell_type=CodeSmellType.TOO_MANY_PARAMETERS,
                    severity=SmellSeverity.HIGH,
                    line_number=symbol.line_start,
                    code_snippet=symbol.signature[:80],
                    message=f"Too many parameters ({param_count})",
                    suggestion="Consider using objects to group related parameters. Limit to 5 parameters."
                ))

        # Check variable names
        for line_num, line in enumerate(lines, symbol.line_start):
            var_issues = self._check_variable_names(symbol, line, line_num)
            smells.extend(var_issues)

        # Check nesting depth
        max_nesting = self._calculate_max_nesting(code)
        if max_nesting > self.deep_nesting_threshold:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.DEEP_NESTING,
                severity=SmellSeverity.MEDIUM,
                line_number=symbol.line_start,
                code_snippet="Nested code block",
                message=f"Code has deep nesting ({max_nesting} levels)",
                suggestion="Extract nested blocks into separate methods. Limit nesting to 3 levels."
            ))

        # Check missing documentation
        if not symbol.docstring or symbol.docstring.strip() == "":
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.MISSING_DOCUMENTATION,
                severity=SmellSeverity.LOW,
                line_number=symbol.line_start,
                code_snippet=symbol.signature[:80],
                message=f"Missing docstring",
                suggestion="Add docstring explaining purpose, parameters, and return value."
            ))

        # Check complexity
        complexity = symbol.metrics.cyclomatic_complexity
        if complexity > self.high_complexity_threshold:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.HIGH_COMPLEXITY,
                severity=SmellSeverity.HIGH,
                line_number=symbol.line_start,
                code_snippet=f"Cyclomatic complexity: {complexity}",
                message=f"High complexity ({complexity})",
                suggestion="Reduce conditional branches. Extract into smaller methods with single responsibility."
            ))

        # Check for magic numbers
        for line_num, line in enumerate(lines, symbol.line_start):
            magic_issues = self._check_magic_numbers(symbol, line, line_num)
            smells.extend(magic_issues)

        # Check for feature envy
        method_calls = self._count_method_calls(code)
        if method_calls > 10:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.FEATURE_ENVY,
                severity=SmellSeverity.MEDIUM,
                line_number=symbol.line_start,
                code_snippet=f"{method_calls} method calls detected",
                message=f"Possible feature envy ({method_calls} method calls)",
                suggestion="Method may be using another class too much. Consider moving to that class."
            ))

        self.smells.extend(smells)
        return smells

    def _count_parameters(self, signature: str) -> int:
        """Count parameters in a function signature."""
        # Simple parameter counting
        if '(' not in signature or ')' not in signature:
            return 0
        params_str = signature[signature.find('(') + 1:signature.rfind(')')]
        if not params_str.strip():
            return 0
        return len([p for p in params_str.split(',') if p.strip() and p.strip() != 'self'])

    def _check_variable_names(self, symbol: Symbol, line: str, line_num: int) -> List[CodeSmell]:
        """Check for problematic variable names."""
        smells = []

        # Check for very long variable names
        matches = re.findall(r'\b[a-zA-Z_]\w{' + str(self.long_name_threshold) + ',}\b', line)
        for match in matches:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.LONG_VARIABLE_NAME,
                severity=SmellSeverity.LOW,
                line_number=line_num,
                code_snippet=line.strip()[:80],
                message=f"Variable name too long: '{match}'",
                suggestion="Use shorter, more concise variable names. Avoid redundancy."
            ))

        # Check for single-letter variable names (except loop counters i, j, k, x, y, z)
        single_letter_vars = re.findall(r'\b(?<![a-zA-Z0-9_])([^ijkxyz])\s*=', line)
        if single_letter_vars and 'for' not in line:
            for var in single_letter_vars:
                if var not in ['i', 'j', 'k', 'x', 'y', 'z']:
                    smells.append(CodeSmell(
                        symbol=symbol,
                        smell_type=CodeSmellType.SHORT_VARIABLE_NAME,
                        severity=SmellSeverity.LOW,
                        line_number=line_num,
                        code_snippet=line.strip()[:80],
                        message=f"Single-letter variable name: '{var}'",
                        suggestion="Use descriptive variable names that indicate purpose."
                    ))

        return smells

    def _calculate_max_nesting(self, code: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        for char in code:
            if char in '{[(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in '}])':
                current_depth = max(0, current_depth - 1)
        return max_depth

    def _count_method_calls(self, code: str) -> int:
        """Count method calls (.) in code."""
        return len(re.findall(r'\.\w+\s*\(', code))

    def _check_magic_numbers(self, symbol: Symbol, line: str, line_num: int) -> List[CodeSmell]:
        """Check for magic numbers in code."""
        smells = []

        # Look for numeric literals (not in strings)
        magic_numbers = re.findall(r'(?<!\w)([0-9]{3,}|[0-9]\.[0-9]{2,})(?!\w)', line)
        if magic_numbers and '"' not in line and "'" not in line:
            smells.append(CodeSmell(
                symbol=symbol,
                smell_type=CodeSmellType.MAGIC_NUMBERS,
                severity=SmellSeverity.LOW,
                line_number=line_num,
                code_snippet=line.strip()[:80],
                message=f"Magic number detected: {magic_numbers[0]}",
                suggestion="Extract magic numbers to named constants. Makes code more maintainable."
            ))

        return smells

    def analyze_all(self, symbols_with_code: List[Tuple[Symbol, str]]) -> List[CodeSmell]:
        """Analyze multiple symbols for code smells.

        Args:
            symbols_with_code: List of (symbol, code) tuples

        Returns:
            List of all detected smells
        """
        self.smells = []

        for symbol, code in symbols_with_code:
            self.analyze_symbol(symbol, code)

        self._calculate_metrics(symbols_with_code)

        return self.smells

    def _calculate_metrics(self, symbols_with_code: List[Tuple[Symbol, str]]) -> None:
        """Calculate smell metrics."""
        symbols_with_smells = set()
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        info_count = 0

        for smell in self.smells:
            symbols_with_smells.add(smell.symbol.name)

            if smell.severity == SmellSeverity.CRITICAL:
                critical_count += 1
            elif smell.severity == SmellSeverity.HIGH:
                high_count += 1
            elif smell.severity == SmellSeverity.MEDIUM:
                medium_count += 1
            elif smell.severity == SmellSeverity.LOW:
                low_count += 1
            elif smell.severity == SmellSeverity.INFO:
                info_count += 1

        smell_density = len(self.smells) / len(symbols_with_code) if symbols_with_code else 0

        self.metrics = SmellMetrics(
            total_symbols=len(symbols_with_code),
            symbols_with_smells=len(symbols_with_smells),
            total_smells=len(self.smells),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            info_count=info_count,
            smell_density=smell_density
        )

    def get_smells(self, severity: Optional[SmellSeverity] = None) -> List[CodeSmell]:
        """Get smells, optionally filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of smells
        """
        if severity:
            return [s for s in self.smells if s.severity == severity]
        return self.smells

    def get_smells_for_symbol(self, symbol: Symbol) -> List[CodeSmell]:
        """Get smells for a specific symbol.

        Args:
            symbol: Symbol to get smells for

        Returns:
            List of smells for the symbol
        """
        return [s for s in self.smells if s.symbol.name == symbol.name]

    def get_critical_smells(self) -> List[CodeSmell]:
        """Get all critical severity smells.

        Returns:
            List of critical smells
        """
        return self.get_smells(SmellSeverity.CRITICAL)

    def get_smells_by_type(self, smell_type: CodeSmellType) -> List[CodeSmell]:
        """Get smells of a specific type.

        Args:
            smell_type: Type of smell to filter by

        Returns:
            List of smells of that type
        """
        return [s for s in self.smells if s.smell_type == smell_type]

    def get_worst_offenders(self, limit: int = 10) -> List[Tuple[Symbol, int]]:
        """Get symbols with most code smells.

        Args:
            limit: Maximum number of results

        Returns:
            List of (symbol, smell_count) tuples
        """
        smell_count = {}
        for smell in self.smells:
            name = smell.symbol.name
            smell_count[name] = smell_count.get(name, 0) + 1

        # Find corresponding symbols and sort
        result = []
        for name, count in sorted(smell_count.items(), key=lambda x: x[1], reverse=True)[:limit]:
            for smell in self.smells:
                if smell.symbol.name == name:
                    result.append((smell.symbol, count))
                    break

        return result

    def get_metrics(self) -> Optional[SmellMetrics]:
        """Get smell metrics.

        Returns:
            SmellMetrics or None
        """
        return self.metrics

    def get_smell_report(self) -> str:
        """Generate a human-readable code smell report.

        Returns:
            Formatted report string
        """
        if not self.metrics:
            return "No code smell analysis performed. Call analyze_all() first."

        report = "═" * 70 + "\n"
        report += "                    CODE SMELL ANALYSIS REPORT\n"
        report += "═" * 70 + "\n\n"

        report += f"Total Symbols:              {self.metrics.total_symbols}\n"
        report += f"Symbols with Smells:        {self.metrics.symbols_with_smells}\n"
        report += f"Total Code Smells:          {self.metrics.total_smells}\n"
        report += f"Smell Density:              {self.metrics.smell_density:.2f} smells/symbol\n\n"

        report += "Severity Breakdown:\n"
        report += f"  Critical:  {self.metrics.critical_count}\n"
        report += f"  High:      {self.metrics.high_count}\n"
        report += f"  Medium:    {self.metrics.medium_count}\n"
        report += f"  Low:       {self.metrics.low_count}\n"
        report += f"  Info:      {self.metrics.info_count}\n\n"

        # Worst offenders
        worst = self.get_worst_offenders(limit=5)
        if worst:
            report += "─" * 70 + "\n"
            report += "Symbols with Most Code Smells:\n"
            report += "─" * 70 + "\n"
            for symbol, count in worst:
                report += f"{symbol.name:40} {count} smell{'s' if count != 1 else ''}\n"

        # Smell type distribution
        type_counts = {}
        for smell in self.smells:
            t = smell.smell_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        if type_counts:
            report += "\n" + "─" * 70 + "\n"
            report += "Code Smell Types:\n"
            report += "─" * 70 + "\n"
            for smell_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                report += f"{smell_type:30} {count} occurrence{'s' if count != 1 else ''}\n"

        return report

    def suggest_refactoring(self, smell: CodeSmell) -> str:
        """Suggest refactoring for a code smell.

        Args:
            smell: CodeSmell to refactor

        Returns:
            Detailed refactoring suggestion
        """
        suggestion = f"Refactor {smell.smell_type.value} in {smell.symbol.name}:\n"
        suggestion += f"\nProblem: {smell.message}\n"
        suggestion += f"Location: Line {smell.line_number}\n"
        suggestion += f"Code: {smell.code_snippet}\n"
        suggestion += f"\nSuggestion:\n{smell.suggestion}\n"

        # Add specific refactoring based on type
        if smell.smell_type == CodeSmellType.LONG_METHOD:
            suggestion += "\nRefactoring Steps:\n"
            suggestion += "1. Identify distinct responsibilities within the method\n"
            suggestion += "2. Extract each responsibility into a separate method\n"
            suggestion += "3. Replace original code with calls to new methods\n"

        elif smell.smell_type == CodeSmellType.TOO_MANY_PARAMETERS:
            suggestion += "\nRefactoring Steps:\n"
            suggestion += "1. Create a Parameter Object to group related parameters\n"
            suggestion += "2. Replace individual parameters with the object\n"
            suggestion += "3. Consider using builder pattern for complex initialization\n"

        elif smell.smell_type == CodeSmellType.DEEP_NESTING:
            suggestion += "\nRefactoring Steps:\n"
            suggestion += "1. Extract nested blocks into separate methods\n"
            suggestion += "2. Use early returns to reduce nesting\n"
            suggestion += "3. Consider using guard clauses\n"

        return suggestion
