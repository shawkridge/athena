"""Track validation rule effectiveness and improve rules over time."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class RuleExecution:
    """Record of a validation rule execution."""

    rule_id: int
    rule_name: str
    execution_time: datetime
    issue_present: bool  # Was issue actually present?
    rule_flagged_issue: bool  # Did rule detect it?
    false_positive: bool = False
    false_negative: bool = False
    execution_context: Dict = field(default_factory=dict)


@dataclass
class RuleMetrics:
    """Calculated metrics for a validation rule."""

    rule_id: int
    rule_name: str
    total_executions: int
    true_positives: int  # Correctly flagged
    false_positives: int  # Incorrectly flagged
    false_negatives: int  # Missed issues
    true_negatives: int  # Correctly didn't flag
    precision: float  # TP / (TP + FP)
    recall: float  # TP / (TP + FN)
    f1_score: float
    accuracy: float
    effectiveness: float  # Custom metric for priority
    confidence: float


class ValidationLearningEngine:
    """Learn which validation rules are most effective."""

    def __init__(self):
        """Initialize validation learning engine."""
        self._rule_executions: List[RuleExecution] = []
        self._rule_metrics: Dict[int, RuleMetrics] = {}
        self._rule_combinations: Dict[Tuple[int, int], float] = {}

    def record_rule_execution(
        self,
        rule_id: int,
        rule_name: str,
        issue_present: bool,
        rule_flagged_issue: bool,
        execution_context: Optional[Dict] = None,
    ) -> RuleExecution:
        """Record execution of a validation rule.

        Args:
            rule_id: Rule ID
            rule_name: Human-readable rule name
            issue_present: Was issue actually present?
            rule_flagged_issue: Did rule detect/flag it?
            execution_context: Context about the execution

        Returns:
            Recorded execution
        """
        execution = RuleExecution(
            rule_id=rule_id,
            rule_name=rule_name,
            execution_time=datetime.now(),
            issue_present=issue_present,
            rule_flagged_issue=rule_flagged_issue,
            false_positive=rule_flagged_issue and not issue_present,
            false_negative=not rule_flagged_issue and issue_present,
            execution_context=execution_context or {},
        )

        self._rule_executions.append(execution)
        return execution

    def calculate_rule_metrics(
        self,
        rule_id: int,
    ) -> RuleMetrics:
        """Calculate metrics for a rule based on executions.

        Args:
            rule_id: Rule ID

        Returns:
            Calculated metrics
        """
        executions = [e for e in self._rule_executions if e.rule_id == rule_id]

        if not executions:
            return RuleMetrics(
                rule_id=rule_id,
                rule_name="Unknown",
                total_executions=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                true_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                accuracy=0.0,
                effectiveness=0.0,
                confidence=0.0,
            )

        # Calculate confusion matrix
        tp = len([e for e in executions if e.rule_flagged_issue and e.issue_present])
        fp = len([e for e in executions if e.rule_flagged_issue and not e.issue_present])
        fn = len([e for e in executions if not e.rule_flagged_issue and e.issue_present])
        tn = len([e for e in executions if not e.rule_flagged_issue and not e.issue_present])

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

        # Effectiveness: weighted combination prioritizing recall (catching issues)
        effectiveness = (recall * 0.6 + precision * 0.4) * accuracy

        # Confidence based on execution count
        confidence = min(0.95, 0.3 + len(executions) * 0.05)

        rule_name = executions[0].rule_name if executions else "Unknown"

        metrics = RuleMetrics(
            rule_id=rule_id,
            rule_name=rule_name,
            total_executions=len(executions),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            effectiveness=effectiveness,
            confidence=confidence,
        )

        self._rule_metrics[rule_id] = metrics
        return metrics

    def calculate_all_metrics(self) -> Dict[int, RuleMetrics]:
        """Calculate metrics for all rules.

        Returns:
            Dict mapping rule IDs to their metrics
        """
        rule_ids = set(e.rule_id for e in self._rule_executions)
        for rule_id in rule_ids:
            self.calculate_rule_metrics(rule_id)

        return self._rule_metrics

    def rank_rules_by_effectiveness(self) -> List[RuleMetrics]:
        """Rank all rules by effectiveness.

        Returns:
            Rules sorted by effectiveness (highest first)
        """
        # Recalculate all metrics
        self.calculate_all_metrics()

        rules = list(self._rule_metrics.values())
        rules.sort(key=lambda r: (r.effectiveness * r.confidence), reverse=True)

        return rules

    def identify_low_value_rules(
        self,
        effectiveness_threshold: float = 0.5,
    ) -> List[Tuple[int, str, float]]:
        """Identify rules with low effectiveness for removal.

        Args:
            effectiveness_threshold: Minimum effectiveness to keep

        Returns:
            List of (rule_id, rule_name, effectiveness) tuples
        """
        self.calculate_all_metrics()

        low_value = [
            (r.rule_id, r.rule_name, r.effectiveness)
            for r in self._rule_metrics.values()
            if r.effectiveness < effectiveness_threshold and r.total_executions > 10
        ]

        low_value.sort(key=lambda x: x[2])
        return low_value

    def identify_high_value_rules(
        self,
        effectiveness_threshold: float = 0.75,
    ) -> List[RuleMetrics]:
        """Identify rules with high effectiveness to promote.

        Args:
            effectiveness_threshold: Minimum effectiveness

        Returns:
            List of high-value rules
        """
        ranked = self.rank_rules_by_effectiveness()

        high_value = [
            r for r in ranked if r.effectiveness >= effectiveness_threshold and r.confidence > 0.6
        ]

        return high_value

    def get_complementary_rules(
        self,
        rule_id: int,
    ) -> List[Tuple[int, float]]:
        """Find rules that complement a given rule.

        Complementary rules catch different types of issues or have different false positive rates.

        Args:
            rule_id: Rule ID

        Returns:
            List of (other_rule_id, complementarity_score) tuples
        """
        rule_exec = [e for e in self._rule_executions if e.rule_id == rule_id]
        if not rule_exec:
            return []

        # Calculate what this rule misses
        missed_issues = [e for e in rule_exec if e.false_negative]

        if not missed_issues:
            return []

        # Find rules that catch what this one misses
        complementary = defaultdict(float)

        for missed in missed_issues:
            # Look for other rules that executed on same context
            context = missed.execution_context
            for other_exec in self._rule_executions:
                if other_exec.rule_id == rule_id:
                    continue
                # Rough match: both executed in similar context
                if other_exec.rule_flagged_issue and other_exec.issue_present:
                    complementary[other_exec.rule_id] += 1.0

        # Normalize scores
        result = [(rule_id, score / len(missed_issues)) for rule_id, score in complementary.items()]

        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def get_rule_dependencies(
        self,
        rule_id: int,
    ) -> List[int]:
        """Get rules that should run before this rule.

        Args:
            rule_id: Rule ID

        Returns:
            List of prerequisite rule IDs
        """
        # Simple heuristic: rules with high precision should run first
        self.calculate_all_metrics()

        metrics = self.rank_rules_by_effectiveness()
        high_precision_rules = [
            r.rule_id for r in metrics if r.precision > 0.9 and r.rule_id != rule_id
        ]

        return high_precision_rules[:3]  # Top 3

    def extract_validation_insights(self) -> List[str]:
        """Extract key insights about validation rules.

        Returns:
            List of actionable insights
        """
        insights = []

        if not self._rule_executions:
            return ["No validation rule data yet"]

        self.calculate_all_metrics()

        # Insight 1: Best rules
        ranked = self.rank_rules_by_effectiveness()
        top_rules = ranked[:3]

        for rule in top_rules:
            if rule.total_executions > 5:
                insights.append(
                    f"✅ Excellent rule '{rule.rule_name}': "
                    f"{rule.precision:.0%} precision, {rule.recall:.0%} recall (F1={rule.f1_score:.2f})"
                )

        # Insight 2: Rules to improve
        low_value = self.identify_low_value_rules()
        for rule_id, rule_name, effectiveness in low_value[:3]:
            insights.append(
                f"⚠️ Consider improving '{rule_name}': effectiveness={effectiveness:.1%}"
            )

        # Insight 3: Recommended rule combinations
        if len(ranked) > 1:
            best_rule = ranked[0]
            complements = self.get_complementary_rules(best_rule.rule_id)
            if complements:
                insights.append(
                    f"💡 Pair '{best_rule.rule_name}' with '{ranked[complements[0][0]].rule_name}' "
                    f"for better coverage"
                )

        return insights

    def recommend_rule_set_for_plan(
        self,
        task_type: str,
        max_rules: int = 5,
    ) -> List[int]:
        """Recommend a set of rules for validating a plan.

        Args:
            task_type: Type of task being planned
            max_rules: Maximum number of rules to recommend

        Returns:
            List of rule IDs to use
        """
        ranked = self.rank_rules_by_effectiveness()

        # Filter to high-effectiveness rules with high confidence
        recommended = [
            r.rule_id
            for r in ranked
            if r.effectiveness > 0.6 and r.confidence > 0.5 and r.total_executions > 3
        ]

        return recommended[:max_rules]
