"""Rules Engine for custom code quality rules.

Provides:
- Custom rule definition
- Rule validation and enforcement
- Rule violation tracking
- Severity-based enforcement
- Auto-fix suggestions
"""

from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .symbol_models import Symbol


class RuleSeverity(str, Enum):
    """Rule violation severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleAction(str, Enum):
    """Action to take on violation."""
    WARN = "warn"
    BLOCK = "block"
    SUGGEST_FIX = "suggest_fix"
    AUTO_FIX = "auto_fix"


@dataclass
class Rule:
    """Code quality rule."""
    id: str
    name: str
    description: str
    category: str  # e.g., "naming", "complexity", "documentation"
    severity: RuleSeverity
    action: RuleAction
    condition: Callable  # Function(symbol: Symbol, context: Dict) -> bool
    message_template: str
    fix_suggestion: Optional[str] = None
    auto_fix_fn: Optional[Callable] = None
    enabled: bool = True


@dataclass
class RuleViolation:
    """Rule violation instance."""
    rule_id: str
    rule_name: str
    symbol_name: str
    severity: RuleSeverity
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    auto_fix_code: Optional[str] = None


@dataclass
class RuleCheckResult:
    """Result of rule checking."""
    rule_id: str
    passed: bool
    violations: List[RuleViolation] = field(default_factory=list)
    violation_count: int = 0


@dataclass
class RuleEnforcementReport:
    """Report of rule enforcement."""
    total_symbols: int
    total_rules: int
    violations: List[RuleViolation] = field(default_factory=list)
    critical_violations: int = 0
    error_violations: int = 0
    warning_violations: int = 0
    info_violations: int = 0
    symbols_with_violations: int = 0
    pass_rate: float = 0.0


class RulesEngine:
    """Enforces custom code quality rules."""

    def __init__(self):
        """Initialize engine."""
        self.rules: Dict[str, Rule] = {}
        self.violations: List[RuleViolation] = []

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine.

        Args:
            rule: Rule to add
        """
        self.rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if removed, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule.

        Args:
            rule_id: ID of rule to enable

        Returns:
            True if enabled, False if not found
        """
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule.

        Args:
            rule_id: ID of rule to disable

        Returns:
            True if disabled, False if not found
        """
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def check_symbol(self, symbol: Symbol, context: Dict = None) -> List[RuleViolation]:
        """Check a symbol against all enabled rules.

        Args:
            symbol: Symbol to check
            context: Additional context for rule evaluation

        Returns:
            List of RuleViolation for this symbol
        """
        if context is None:
            context = {}

        violations = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                # Check if rule condition is met (violation)
                if rule.condition(symbol, context):
                    message = rule.message_template.format(
                        symbol=symbol.name,
                        type=symbol.symbol_type.value,
                        file=symbol.file_path
                    )

                    violation = RuleViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        symbol_name=symbol.name,
                        severity=rule.severity,
                        message=message,
                        line_number=symbol.line_start,
                        suggestion=rule.fix_suggestion,
                        auto_fix_code=self._generate_auto_fix(rule, symbol) if rule.auto_fix_fn else None,
                    )
                    violations.append(violation)
                    self.violations.append(violation)
            except Exception as e:
                # Rule evaluation error
                pass

        return violations

    def check_symbols(self, symbols: Dict[str, Symbol], context: Dict = None) -> RuleCheckResult:
        """Check multiple symbols against all rules.

        Args:
            symbols: Dict of symbol name -> Symbol
            context: Additional context

        Returns:
            RuleCheckResult with all violations
        """
        if context is None:
            context = {}

        all_violations = []

        for symbol in symbols.values():
            violations = self.check_symbol(symbol, context)
            all_violations.extend(violations)

        passed = len(all_violations) == 0

        return RuleCheckResult(
            rule_id="all",
            passed=passed,
            violations=all_violations,
            violation_count=len(all_violations),
        )

    def _generate_auto_fix(self, rule: Rule, symbol: Symbol) -> Optional[str]:
        """Generate auto-fix code.

        Args:
            rule: Rule with auto_fix_fn
            symbol: Symbol to fix

        Returns:
            Auto-fix code or None
        """
        try:
            if rule.auto_fix_fn:
                return rule.auto_fix_fn(symbol)
        except (AttributeError, ValueError, TypeError, KeyError):
            pass
        return None

    def get_violations_by_severity(self, severity: RuleSeverity = None) -> List[RuleViolation]:
        """Get violations filtered by severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of matching violations
        """
        if severity is None:
            return self.violations

        return [v for v in self.violations if v.severity == severity]

    def get_violations_by_rule(self, rule_id: str) -> List[RuleViolation]:
        """Get violations for a specific rule.

        Args:
            rule_id: Rule ID to filter by

        Returns:
            List of violations for this rule
        """
        return [v for v in self.violations if v.rule_id == rule_id]

    def get_violations_by_symbol(self, symbol_name: str) -> List[RuleViolation]:
        """Get violations for a specific symbol.

        Args:
            symbol_name: Symbol name to filter by

        Returns:
            List of violations for this symbol
        """
        return [v for v in self.violations if v.symbol_name == symbol_name]

    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self.violations = []

    def get_enforcement_report(self, total_symbols: int = 0) -> RuleEnforcementReport:
        """Generate enforcement report.

        Args:
            total_symbols: Total number of symbols analyzed

        Returns:
            RuleEnforcementReport with summary
        """
        critical = len(self.get_violations_by_severity(RuleSeverity.CRITICAL))
        errors = len(self.get_violations_by_severity(RuleSeverity.ERROR))
        warnings = len(self.get_violations_by_severity(RuleSeverity.WARNING))
        infos = len(self.get_violations_by_severity(RuleSeverity.INFO))

        symbols_with_violations = len(set(v.symbol_name for v in self.violations))

        pass_rate = 0.0
        if total_symbols > 0:
            pass_rate = (total_symbols - symbols_with_violations) / total_symbols

        return RuleEnforcementReport(
            total_symbols=total_symbols,
            total_rules=len(self.rules),
            violations=self.violations,
            critical_violations=critical,
            error_violations=errors,
            warning_violations=warnings,
            info_violations=infos,
            symbols_with_violations=symbols_with_violations,
            pass_rate=pass_rate,
        )

    def suggest_fixes(self, limit: int = 10) -> List[Tuple[str, str]]:
        """Get fix suggestions for violations.

        Args:
            limit: Max suggestions

        Returns:
            List of (violation_message, fix_suggestion) tuples
        """
        suggestions = []

        for violation in self.violations[:limit]:
            if violation.suggestion or violation.auto_fix_code:
                suggestion_text = violation.suggestion or violation.auto_fix_code
                suggestions.append((violation.message, suggestion_text))

        return suggestions

    def get_rule_statistics(self) -> Dict:
        """Get statistics about rules and violations.

        Returns:
            Dict with rule statistics
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "total_violations": len(self.violations),
            "critical_violations": len(self.get_violations_by_severity(RuleSeverity.CRITICAL)),
            "error_violations": len(self.get_violations_by_severity(RuleSeverity.ERROR)),
            "warning_violations": len(self.get_violations_by_severity(RuleSeverity.WARNING)),
            "info_violations": len(self.get_violations_by_severity(RuleSeverity.INFO)),
            "violation_rate": len(self.violations) / max(1, len(self.rules)),
        }
