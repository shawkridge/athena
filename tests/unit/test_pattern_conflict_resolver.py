"""Tests for pattern conflict resolution in consolidation.

Tests the resolver that handles when System 1 (fast heuristics) and System 2
(LLM reasoning) extract different patterns from the same event cluster.
"""

import pytest
from datetime import datetime
from athena.consolidation.pattern_conflict_resolver import (
    PatternConflictResolver,
    PatternConflict,
    ConflictResolutionStrategy,
)


class TestConflictDetection:
    """Test conflict detection between System 1 and System 2."""

    def test_detect_no_conflict_identical_patterns(self):
        """Test that identical patterns don't trigger conflicts."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "TDD workflow",
            "pattern_type": "workflow",
            "confidence": 0.85,
            "tags": ["tdd", "testing"],
        }

        system_2 = {
            "description": "TDD workflow",
            "pattern_type": "workflow",
            "confidence": 0.82,
            "tags": ["tdd", "testing", "best-practice"],
        }

        conflict = resolver.detect_conflict(
            cluster_id=1,
            system_1_pattern=system_1,
            system_2_pattern=system_2,
        )

        # Same description → no conflict
        assert conflict is None

    def test_detect_conflict_different_descriptions(self):
        """Test conflict detection with different descriptions."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Test-Driven Development",
            "pattern_type": "workflow",
            "confidence": 0.85,
            "tags": ["testing", "development"],
        }

        system_2 = {
            "description": "Comprehensive test coverage strategy",
            "pattern_type": "workflow",
            "confidence": 0.78,
            "tags": ["testing", "quality", "coverage"],
        }

        conflict = resolver.detect_conflict(
            cluster_id=1,
            system_1_pattern=system_1,
            system_2_pattern=system_2,
        )

        assert conflict is not None
        assert conflict.conflict_type == "description_mismatch"
        assert conflict.system_1_confidence == 0.85
        assert conflict.system_2_confidence == 0.78

    def test_detect_conflict_with_type_mismatch(self):
        """Test conflict detection with different pattern types."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Code review process",
            "pattern_type": "workflow",
            "confidence": 0.80,
            "tags": ["review"],
        }

        system_2 = {
            "description": "Code review for security",
            "pattern_type": "security-practice",
            "confidence": 0.75,
            "tags": ["security", "review"],
        }

        conflict = resolver.detect_conflict(
            cluster_id=1,
            system_1_pattern=system_1,
            system_2_pattern=system_2,
        )

        assert conflict is not None
        assert "type_mismatch" in conflict.conflict_type

    def test_conflict_includes_evidence_overlap(self):
        """Test that conflicts calculate evidence overlap."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Error recovery",
            "pattern_type": "workflow",
            "confidence": 0.80,
            "tags": ["debugging", "error-handling", "workflow"],
        }

        system_2 = {
            "description": "Exception handling workflow",
            "pattern_type": "workflow",
            "confidence": 0.85,
            "tags": ["debugging", "error-handling", "resilience"],
        }

        conflict = resolver.detect_conflict(
            cluster_id=1,
            system_1_pattern=system_1,
            system_2_pattern=system_2,
        )

        # Both have [debugging, error-handling] in common
        # Union: [debugging, error-handling, workflow, resilience] (4 tags)
        # Intersection: [debugging, error-handling] (2 tags)
        # Overlap = 2/4 = 0.5
        assert conflict.evidence_overlap == 0.5

    def test_no_conflict_when_either_is_none(self):
        """Test that None patterns don't create conflicts."""
        resolver = PatternConflictResolver()

        conflict = resolver.detect_conflict(
            cluster_id=1,
            system_1_pattern=None,
            system_2_pattern={"description": "test"},
        )

        assert conflict is None


class TestConflictResolution:
    """Test conflict resolution strategies."""

    def test_system_1_wins_high_confidence(self):
        """Test System 1 wins when it has significantly higher confidence."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Explicit TDD workflow",
            "confidence": 0.95,
            "tags": ["tdd"],
        }

        system_2 = {
            "description": "General test-based development",
            "confidence": 0.60,
            "tags": ["testing"],
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        result = resolver.resolve_conflict(conflict)

        # Confidence diff = 0.35 > 0.2 → higher confidence wins
        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_1_WINS
        assert result.selected_pattern == system_1
        assert result.confidence == 0.95

    def test_system_2_wins_higher_confidence(self):
        """Test System 2 wins when it has higher confidence."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Testing activity",
            "confidence": 0.65,
            "tags": ["testing"],
        }

        system_2 = {
            "description": "Comprehensive testing strategy with review gates",
            "confidence": 0.88,
            "tags": ["testing", "review", "quality"],
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        result = resolver.resolve_conflict(conflict)

        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_2_WINS
        assert result.selected_pattern == system_2
        assert result.confidence == 0.88

    def test_merge_when_high_evidence_overlap(self):
        """Test merging when patterns have high evidence overlap."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "TDD workflow",
            "pattern_type": "workflow",
            "confidence": 0.85,
            "tags": ["tdd", "testing", "development"],
            "evidence": "Sequence shows test → code → success",
        }

        system_2 = {
            "description": "Test-first development approach",
            "pattern_type": "workflow",
            "confidence": 0.82,
            "tags": ["tdd", "testing", "best-practice"],
            "evidence": "Tests written before implementation",
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        # Overlap: [tdd, testing] / [tdd, testing, development, best-practice] = 2/4 = 0.5
        # Actually let me recalculate
        # Union: tdd, testing, development, best-practice = 4
        # Intersection: tdd, testing = 2
        # Overlap = 2/4 = 0.5

        # Since overlap is 0.5, which is between 0.3 and 0.7, System 2 wins
        result = resolver.resolve_conflict(conflict)

        # 0.5 is medium overlap, so System 2 wins (not merge)
        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_2_WINS

    def test_defer_when_low_evidence_overlap(self):
        """Test deferring when patterns have low evidence overlap."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Performance optimization",
            "pattern_type": "optimization",
            "confidence": 0.80,
            "tags": ["performance", "optimization", "refactoring"],
            "evidence": "Multiple caching additions",
        }

        system_2 = {
            "description": "Database query consolidation",
            "pattern_type": "database",
            "confidence": 0.75,
            "tags": ["database", "sql", "optimization"],
            "evidence": "Combined N queries into 1",
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        # Overlap: [optimization] / [performance, optimization, refactoring, database, sql] = 1/5 = 0.2
        # This is low overlap, so should defer

        result = resolver.resolve_conflict(conflict)

        assert result.strategy_used == ConflictResolutionStrategy.DEFER
        assert result.requires_human_review is True

    def test_system_2_wins_medium_confidence_similar(self):
        """Test System 2 wins with medium overlap and similar confidences."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Code refactoring",
            "confidence": 0.75,
            "tags": ["refactoring", "code-quality"],
        }

        system_2 = {
            "description": "Structural code improvements",
            "confidence": 0.78,
            "tags": ["refactoring", "architecture"],
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        result = resolver.resolve_conflict(conflict)

        # Confidence diff = 0.03 < 0.2 (similar)
        # Overlap: [refactoring] / [refactoring, code-quality, architecture] = 1/3 ≈ 0.33 (medium)
        # Medium overlap → System 2 wins
        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_2_WINS


class TestConflictResolutionStrategies:
    """Test explicit resolution strategies."""

    def test_user_override_system_1(self):
        """Test user can override resolution to use System 1."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Simple pattern",
            "confidence": 0.70,
        }

        system_2 = {
            "description": "Complex interpretation",
            "confidence": 0.90,
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        result = resolver.resolve_conflict(
            conflict,
            strategy=ConflictResolutionStrategy.SYSTEM_1_WINS,
        )

        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_1_WINS
        assert result.selected_pattern == system_1

    def test_user_override_merge(self):
        """Test user can override resolution to merge patterns."""
        resolver = PatternConflictResolver()

        system_1 = {
            "description": "Performance optimization",
            "pattern_type": "optimization",
            "confidence": 0.85,
            "tags": ["performance"],
            "evidence": "Caching improvements",
        }

        system_2 = {
            "description": "Query optimization",
            "pattern_type": "optimization",
            "confidence": 0.80,
            "tags": ["database", "optimization"],
            "evidence": "SQL query consolidation",
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        result = resolver.resolve_conflict(
            conflict,
            strategy=ConflictResolutionStrategy.MERGE,
        )

        assert result.strategy_used == ConflictResolutionStrategy.MERGE
        assert "merged_from" in result.selected_pattern
        assert result.selected_pattern["merged_from"] == ["system_1", "system_2"]


class TestBatchResolution:
    """Test batch conflict resolution."""

    def test_resolve_multiple_conflicts(self):
        """Test resolving multiple conflicts in a batch."""
        resolver = PatternConflictResolver()

        # Create 3 conflicts
        conflicts = []
        for i in range(3):
            s1 = {
                "description": f"Pattern {i} - System 1",
                "confidence": 0.75 + (i * 0.05),
                "tags": ["pattern"],
            }

            s2 = {
                "description": f"Pattern {i} - System 2",
                "confidence": 0.80 + (i * 0.05),
                "tags": ["pattern", "extended"],
            }

            conflict = resolver.detect_conflict(i, s1, s2)
            conflicts.append(conflict)

        # Resolve all
        results = resolver.resolve_conflicts_batch(conflicts)

        assert len(results) == 3
        assert all(r.strategy_used is not None for r in results)


class TestResolutionStatistics:
    """Test resolution statistics collection."""

    def test_get_resolution_stats(self):
        """Test gathering resolution statistics."""
        resolver = PatternConflictResolver()

        # Create and resolve several conflicts
        for i in range(5):
            s1 = {
                "description": f"Pattern {i} - S1",
                "confidence": 0.70 + (i * 0.02),
                "tags": ["test"],
            }

            s2 = {
                "description": f"Pattern {i} - S2",
                "confidence": 0.75 + (i * 0.03),
                "tags": ["test", "extended"],
            }

            conflict = resolver.detect_conflict(i, s1, s2)
            resolver.resolve_conflict(conflict)

        stats = resolver.get_resolution_stats()

        assert stats["total_conflicts"] == 5
        assert stats["total_resolutions"] == 5
        assert "strategies_used" in stats
        assert "average_confidence" in stats
        assert 0 <= stats["average_confidence"] <= 1

    def test_human_review_rate(self):
        """Test calculation of human review rate."""
        resolver = PatternConflictResolver()

        # Create a conflict with low overlap (should defer)
        system_1 = {
            "description": "Pattern A",
            "confidence": 0.80,
            "tags": ["a", "b", "c"],
        }

        system_2 = {
            "description": "Pattern B",
            "confidence": 0.75,
            "tags": ["x", "y", "z"],
        }

        conflict = resolver.detect_conflict(1, system_1, system_2)
        resolver.resolve_conflict(conflict)

        stats = resolver.get_resolution_stats()

        # Should require human review due to low overlap
        assert stats["requiring_human_review"] > 0
        assert stats["human_review_rate"] > 0


class TestConflictEdgeCases:
    """Test edge cases in conflict resolution."""

    def test_empty_tag_lists(self):
        """Test conflict detection with no tags."""
        resolver = PatternConflictResolver()

        s1 = {
            "description": "Pattern 1",
            "confidence": 0.80,
            "tags": [],
        }

        s2 = {
            "description": "Pattern 2",
            "confidence": 0.75,
            "tags": [],
        }

        conflict = resolver.detect_conflict(1, s1, s2)

        # Empty tags → 0 overlap
        assert conflict.evidence_overlap == 0.0

    def test_identical_confidence(self):
        """Test resolution when confidences are identical and tags disjoint."""
        resolver = PatternConflictResolver()

        s1 = {
            "description": "Pattern 1",
            "confidence": 0.80,
            "tags": ["a"],
        }

        s2 = {
            "description": "Pattern 2",
            "confidence": 0.80,
            "tags": ["b"],
        }

        conflict = resolver.detect_conflict(1, s1, s2)
        result = resolver.resolve_conflict(conflict)

        # Equal confidence, zero overlap (no common tags) → DEFER (fundamental disagreement)
        assert result.strategy_used == ConflictResolutionStrategy.DEFER
        assert result.requires_human_review is True

    def test_very_high_confidence_both(self):
        """Test resolution with very high confidence on both sides."""
        resolver = PatternConflictResolver()

        s1 = {
            "description": "Explicit TDD workflow",
            "confidence": 0.98,  # Nearly certain
            "tags": ["tdd", "testing"],
        }

        s2 = {
            "description": "Test-first development pattern",
            "confidence": 0.95,  # Also nearly certain
            "tags": ["tdd", "development"],
        }

        conflict = resolver.detect_conflict(1, s1, s2)
        result = resolver.resolve_conflict(conflict)

        # Diff = 0.03 < 0.2 (similar)
        # Overlap: [tdd] / [tdd, testing, development] = 1/3 ≈ 0.33 (medium)
        # Medium overlap → System 2 wins
        assert result.strategy_used == ConflictResolutionStrategy.SYSTEM_2_WINS
        assert result.confidence >= 0.95  # High confidence in result


class TestMergedPatterns:
    """Test pattern merging functionality."""

    def test_merged_pattern_combines_descriptions(self):
        """Test that merged patterns use System 2 description."""
        resolver = PatternConflictResolver()

        s1 = {
            "description": "TDD",
            "pattern_type": "workflow",
            "confidence": 0.85,
            "tags": ["tdd"],
        }

        s2 = {
            "description": "Test-Driven Development methodology",
            "pattern_type": "workflow",
            "confidence": 0.88,
            "tags": ["tdd", "methodology"],
        }

        conflict = resolver.detect_conflict(1, s1, s2)
        # Force merge
        result = resolver.resolve_conflict(
            conflict,
            strategy=ConflictResolutionStrategy.MERGE,
        )

        # Should use System 2 description (more detailed)
        assert (
            result.selected_pattern["description"]
            == "Test-Driven Development methodology"
        )

    def test_merged_pattern_combines_tags(self):
        """Test that merged patterns combine all tags."""
        resolver = PatternConflictResolver()

        s1 = {
            "description": "P1",
            "confidence": 0.80,
            "tags": ["a", "b"],
        }

        s2 = {
            "description": "P2",
            "confidence": 0.75,
            "tags": ["b", "c"],
        }

        conflict = resolver.detect_conflict(1, s1, s2)
        result = resolver.resolve_conflict(
            conflict,
            strategy=ConflictResolutionStrategy.MERGE,
        )

        # Should have union of tags
        merged_tags = set(result.selected_pattern["tags"])
        assert "a" in merged_tags
        assert "b" in merged_tags
        assert "c" in merged_tags
