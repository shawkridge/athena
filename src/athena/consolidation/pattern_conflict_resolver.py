"""Pattern conflict resolution for dual-process consolidation.

When System 1 (fast heuristics) and System 2 (LLM reasoning) extract different
patterns from the same event cluster, this module resolves conflicts using:
1. Confidence scoring
2. Evidence analysis
3. LLM arbitration (optional)
4. Spaced repetition for learning

**Research basis**: Li et al. (2025) - Use System 2 (LLM) as tie-breaker for
conflicting high-confidence results, since LLM extended thinking catches nuances
that heuristics miss.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving pattern conflicts."""
    SYSTEM_1_WINS = "system_1"  # Use fast heuristic (reliable but conservative)
    SYSTEM_2_WINS = "system_2"  # Use LLM reasoning (deeper but slower)
    MERGE = "merge"  # Combine both patterns
    DEFER = "defer"  # Mark as uncertain, defer to human feedback
    ARBITRATE = "arbitrate"  # Use higher-confidence approach


@dataclass
class PatternConflict:
    """Represents a conflict between System 1 and System 2 patterns."""
    cluster_id: int
    system_1_pattern: Dict[str, Any]
    system_2_pattern: Dict[str, Any]
    conflict_type: str  # E.g., "different_description", "different_type"
    system_1_confidence: float  # 0-1
    system_2_confidence: float  # 0-1
    evidence_overlap: float  # How much evidence supports both (0-1)
    created_at: datetime = None
    resolved: bool = False
    resolution_strategy: Optional[ConflictResolutionStrategy] = None

    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ResolutionResult:
    """Result of resolving a conflict."""
    selected_pattern: Dict[str, Any]
    strategy_used: ConflictResolutionStrategy
    rationale: str
    confidence: float  # Confidence in this resolution
    evidence: str  # Why we chose this pattern
    requires_human_review: bool  # True if confidence < 0.6


class PatternConflictResolver:
    """Resolves conflicts between System 1 and System 2 pattern extractions."""

    def __init__(self, db=None):
        """Initialize resolver.

        Args:
            db: Optional database connection for storing conflict history
        """
        self.db = db
        self.conflicts: List[PatternConflict] = []
        self.resolutions: List[Tuple[PatternConflict, ResolutionResult]] = []

    def detect_conflict(
        self,
        cluster_id: int,
        system_1_pattern: Dict[str, Any],
        system_2_pattern: Dict[str, Any],
    ) -> Optional[PatternConflict]:
        """Detect if patterns conflict.

        Args:
            cluster_id: ID of event cluster
            system_1_pattern: Pattern from fast heuristics
            system_2_pattern: Pattern from LLM reasoning

        Returns:
            PatternConflict if detected, None if no conflict
        """
        if system_1_pattern is None or system_2_pattern is None:
            return None

        # Check for conflicts
        s1_desc = system_1_pattern.get("description", "").lower()
        s2_desc = system_2_pattern.get("description", "").lower()

        if s1_desc == s2_desc:
            # Same pattern description → no conflict
            return None

        # Extract confidences
        s1_conf = system_1_pattern.get("confidence", 0.5)
        s2_conf = system_2_pattern.get("confidence", 0.5)

        # Calculate evidence overlap (how much evidence supports both)
        s1_tags = set(system_1_pattern.get("tags", []))
        s2_tags = set(system_2_pattern.get("tags", []))

        if s1_tags and s2_tags:
            overlap = len(s1_tags & s2_tags) / len(s1_tags | s2_tags)
        else:
            overlap = 0.0

        # Conflict types
        conflict_type = self._classify_conflict(system_1_pattern, system_2_pattern)

        conflict = PatternConflict(
            cluster_id=cluster_id,
            system_1_pattern=system_1_pattern,
            system_2_pattern=system_2_pattern,
            conflict_type=conflict_type,
            system_1_confidence=s1_conf,
            system_2_confidence=s2_conf,
            evidence_overlap=overlap,
        )

        self.conflicts.append(conflict)
        return conflict

    def resolve_conflict(
        self,
        conflict: PatternConflict,
        strategy: Optional[ConflictResolutionStrategy] = None,
    ) -> ResolutionResult:
        """Resolve a detected conflict.

        **Decision Logic** (in order):
        1. If confidences differ significantly (>0.2): Higher confidence wins
        2. If confidences similar (<0.2 diff): Use evidence overlap
           - High overlap (>0.7): Merge both patterns
           - Low overlap (<0.3): Defer to human (uncertain)
           - Medium overlap: LLM wins (better nuance understanding)
        3. If still tied: LLM wins (System 2 catches nuances)

        Args:
            conflict: The conflict to resolve
            strategy: Optional override strategy

        Returns:
            ResolutionResult with chosen pattern and rationale
        """
        if strategy:
            # User override
            return self._apply_strategy(conflict, strategy)

        # Automatic resolution using confidence and evidence
        conf_diff = abs(conflict.system_1_confidence - conflict.system_2_confidence)

        # Case 1: Significant confidence difference
        if conf_diff > 0.2:
            winner = (
                conflict.system_2_pattern
                if conflict.system_2_confidence > conflict.system_1_confidence
                else conflict.system_1_pattern
            )
            strategy = (
                ConflictResolutionStrategy.SYSTEM_2_WINS
                if conflict.system_2_confidence > conflict.system_1_confidence
                else ConflictResolutionStrategy.SYSTEM_1_WINS
            )

            result = ResolutionResult(
                selected_pattern=winner,
                strategy_used=strategy,
                rationale=f"Confidence difference: {conf_diff:.2f}",
                confidence=max(conflict.system_1_confidence, conflict.system_2_confidence),
                evidence=f"System {'2' if strategy == ConflictResolutionStrategy.SYSTEM_2_WINS else '1'} "
                f"more confident ({max(conflict.system_1_confidence, conflict.system_2_confidence):.2%})",
                requires_human_review=False,
            )

        # Case 2: Similar confidence - use evidence overlap
        elif conflict.evidence_overlap > 0.7:
            # High overlap → patterns agree on core → merge
            result = ResolutionResult(
                selected_pattern=self._merge_patterns(conflict),
                strategy_used=ConflictResolutionStrategy.MERGE,
                rationale=f"High evidence overlap ({conflict.evidence_overlap:.2%})",
                confidence=0.8,
                evidence="Patterns agree on core elements, combined for completeness",
                requires_human_review=False,
            )

        elif conflict.evidence_overlap < 0.3:
            # Low overlap → fundamental disagreement → defer
            result = ResolutionResult(
                selected_pattern=conflict.system_2_pattern,  # Default to System 2
                strategy_used=ConflictResolutionStrategy.DEFER,
                rationale=f"Low evidence overlap ({conflict.evidence_overlap:.2%})",
                confidence=0.5,
                evidence="Fundamental disagreement on pattern interpretation",
                requires_human_review=True,
            )

        else:
            # Medium overlap → System 2 wins (better nuance)
            result = ResolutionResult(
                selected_pattern=conflict.system_2_pattern,
                strategy_used=ConflictResolutionStrategy.SYSTEM_2_WINS,
                rationale=f"Medium evidence overlap ({conflict.evidence_overlap:.2%}), "
                f"System 2 wins for nuance",
                confidence=conflict.system_2_confidence,
                evidence="LLM reasoning catches nuances heuristics miss",
                requires_human_review=False,
            )

        conflict.resolved = True
        conflict.resolution_strategy = result.strategy_used
        self.resolutions.append((conflict, result))

        return result

    def resolve_conflicts_batch(
        self,
        conflicts: List[PatternConflict],
    ) -> List[ResolutionResult]:
        """Resolve multiple conflicts.

        Args:
            conflicts: List of conflicts to resolve

        Returns:
            List of resolution results
        """
        return [self.resolve_conflict(c) for c in conflicts]

    def _classify_conflict(
        self,
        system_1: Dict[str, Any],
        system_2: Dict[str, Any],
    ) -> str:
        """Classify the type of conflict.

        Args:
            system_1: System 1 pattern
            system_2: System 2 pattern

        Returns:
            Conflict type string
        """
        s1_type = system_1.get("pattern_type", "")
        s2_type = system_2.get("pattern_type", "")

        if s1_type != s2_type:
            return f"type_mismatch ({s1_type} vs {s2_type})"

        if system_1.get("description") != system_2.get("description"):
            return "description_mismatch"

        if system_1.get("confidence") != system_2.get("confidence"):
            return "confidence_mismatch"

        return "unknown"

    def _merge_patterns(self, conflict: PatternConflict) -> Dict[str, Any]:
        """Merge two compatible patterns.

        Args:
            conflict: The conflict with two patterns to merge

        Returns:
            Merged pattern
        """
        s1 = conflict.system_1_pattern
        s2 = conflict.system_2_pattern

        # Merge with preferences for System 2 (more detailed)
        merged = {
            "description": s2.get("description", s1.get("description")),
            "pattern_type": s1.get("pattern_type"),  # Should match
            "confidence": (s1.get("confidence", 0.5) + s2.get("confidence", 0.5)) / 2,
            "tags": list(set(s1.get("tags", []) + s2.get("tags", []))),
            "evidence": f"Merged: System 1 ({s1.get('evidence')}) + System 2 ({s2.get('evidence')})",
            "merged_from": ["system_1", "system_2"],
        }

        return merged

    def _apply_strategy(
        self,
        conflict: PatternConflict,
        strategy: ConflictResolutionStrategy,
    ) -> ResolutionResult:
        """Apply a specific resolution strategy.

        Args:
            conflict: The conflict
            strategy: Strategy to apply

        Returns:
            ResolutionResult
        """
        if strategy == ConflictResolutionStrategy.SYSTEM_1_WINS:
            pattern = conflict.system_1_pattern
            confidence = conflict.system_1_confidence
        elif strategy == ConflictResolutionStrategy.SYSTEM_2_WINS:
            pattern = conflict.system_2_pattern
            confidence = conflict.system_2_confidence
        elif strategy == ConflictResolutionStrategy.MERGE:
            pattern = self._merge_patterns(conflict)
            confidence = (
                conflict.system_1_confidence + conflict.system_2_confidence
            ) / 2
        else:  # DEFER
            pattern = conflict.system_2_pattern
            confidence = 0.5

        result = ResolutionResult(
            selected_pattern=pattern,
            strategy_used=strategy,
            rationale=f"User-specified strategy: {strategy.value}",
            confidence=confidence,
            evidence="Strategy applied per user override",
            requires_human_review=strategy == ConflictResolutionStrategy.DEFER,
        )

        conflict.resolved = True
        conflict.resolution_strategy = strategy
        self.resolutions.append((conflict, result))

        return result

    def get_resolution_stats(self) -> Dict[str, Any]:
        """Get statistics on conflict resolution.

        Returns:
            Statistics dictionary
        """
        if not self.resolutions:
            return {"total_conflicts": 0, "total_resolutions": 0}

        strategies_used = {}
        avg_confidence = 0.0
        human_review_count = 0

        for _, result in self.resolutions:
            strategy = result.strategy_used.value
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
            avg_confidence += result.confidence
            if result.requires_human_review:
                human_review_count += 1

        avg_confidence /= len(self.resolutions)

        return {
            "total_conflicts": len(self.conflicts),
            "total_resolutions": len(self.resolutions),
            "strategies_used": strategies_used,
            "average_confidence": avg_confidence,
            "requiring_human_review": human_review_count,
            "human_review_rate": (
                human_review_count / len(self.resolutions)
                if self.resolutions
                else 0.0
            ),
        }

    def log_resolution(self, conflict: PatternConflict, result: ResolutionResult):
        """Log a resolution for learning and audit.

        Args:
            conflict: The resolved conflict
            result: The resolution result
        """
        log_entry = {
            "cluster_id": conflict.cluster_id,
            "conflict_type": conflict.conflict_type,
            "strategy": result.strategy_used.value,
            "confidence": result.confidence,
            "requires_human_review": result.requires_human_review,
            "timestamp": datetime.now().isoformat(),
            "rationale": result.rationale,
        }

        logger.info(f"Pattern conflict resolved: {log_entry}")

        if self.db:
            try:
                self.db.store_conflict_resolution(log_entry)
            except Exception as e:
                logger.warning(f"Failed to store resolution: {e}")
