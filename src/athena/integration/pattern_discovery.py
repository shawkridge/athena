"""
PHASE 6: Pattern Discovery

Discovers reusable patterns from task execution history.
Identifies duration, dependency, resource, temporal, and quality patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import Counter, defaultdict
import statistics


@dataclass
class DurationPattern:
    """A pattern in task durations."""
    task_type: str
    avg_duration: float                 # hours
    std_dev: float                      # standard deviation
    min_duration: float
    max_duration: float
    confidence_level: float             # 0-1
    sample_count: int

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"{self.task_type}: "
            f"{self.avg_duration:.1f}h ± {self.std_dev:.1f}h "
            f"(range: {self.min_duration:.1f}-{self.max_duration:.1f}h, "
            f"n={self.sample_count})"
        )


@dataclass
class DependencyPattern:
    """A pattern in task dependencies."""
    predecessor_type: str
    successor_type: str
    frequency: int                      # How often this pattern occurs
    avg_gap: float                      # Average time between tasks (hours)
    success_rate: float                 # % of times successor succeeds after predecessor
    common_bottleneck: bool

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"{self.predecessor_type} → {self.successor_type}: "
            f"frequency={self.frequency}, "
            f"avg_gap={self.avg_gap:.1f}h, "
            f"success={self.success_rate:.0f}%"
        )


@dataclass
class ResourcePattern:
    """Resource requirements pattern."""
    task_type: str
    typical_team_size: int
    required_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    typical_duration: float = 0.0
    confidence: float = 0.0

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"{self.task_type}: "
            f"team_size={self.typical_team_size}, "
            f"skills={', '.join(self.required_skills[:3])}, "
            f"duration={self.typical_duration:.1f}h"
        )


@dataclass
class TemporalPattern:
    """Time-based patterns."""
    task_type: str
    faster_on_days: List[str]           # ["Monday", "Friday"]
    faster_on_hours: List[int]          # [9, 10, 14, 15]
    slower_on_days: List[str]
    speed_variance: float               # % difference between fast/slow times
    sample_count: int

    def __str__(self) -> str:
        """Human-readable representation."""
        fast_days = ", ".join(self.faster_on_days[:2]) if self.faster_on_days else "none"
        return (
            f"{self.task_type}: "
            f"faster on {fast_days}, "
            f"variance={self.speed_variance:.0f}%"
        )


@dataclass
class QualityPattern:
    """Quality outcome patterns."""
    task_type: str
    avg_quality_score: float            # 0-100
    defect_rate: float                  # % of tasks with defects
    rework_rate: float                  # % requiring rework
    quality_variance: float             # std dev of quality
    factors_affecting_quality: List[str]

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"{self.task_type}: "
            f"quality={self.avg_quality_score:.0f}, "
            f"defect_rate={self.defect_rate:.0f}%, "
            f"rework={self.rework_rate:.0f}%"
        )


@dataclass
class Pattern:
    """Generic pattern container."""
    name: str
    pattern_type: str                   # "duration" | "dependency" | "resource" | "temporal" | "quality"
    frequency: int                      # How often pattern occurs
    impact: float                       # 0-1: impact on outcomes
    actionability: float                # 0-1: how easy to apply
    score: float                        # composite score
    data: any                           # Duration/Dependency/Resource/Temporal/QualityPattern


class PatternDiscovery:
    """Discovers reusable patterns from task execution history."""

    def __init__(self, db):
        """Initialize PatternDiscovery.

        Args:
            db: Database instance
        """
        self.db = db

    def discover_duration_patterns(self) -> List[DurationPattern]:
        """Find typical durations for task types.

        Returns:
            List of duration patterns with confidence
        """
        # Group tasks by type and calculate duration statistics
        task_durations: Dict[str, List[float]] = defaultdict(list)

        # Would query completed tasks from database
        # For now, return empty list (would be implemented with real DB queries)
        patterns = []

        # Example pattern structure (would be generated from real data):
        # for task_type, durations in task_durations.items():
        #     if len(durations) >= 3:
        #         patterns.append(DurationPattern(
        #             task_type=task_type,
        #             avg_duration=statistics.mean(durations),
        #             std_dev=statistics.stdev(durations) if len(durations) > 1 else 0,
        #             min_duration=min(durations),
        #             max_duration=max(durations),
        #             confidence_level=min(1.0, len(durations) / 10),
        #             sample_count=len(durations),
        #         ))

        return patterns

    def discover_dependency_patterns(self) -> List[DependencyPattern]:
        """Find tasks that commonly follow others.

        Returns:
            List of dependency patterns
        """
        # Track predecessor → successor relationships
        transitions: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        transition_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        # Would query task execution history
        # For now, return empty list (would be implemented with real DB queries)
        patterns = []

        # Example pattern structure:
        # for (pred, succ), gaps in transitions.items():
        #     if transition_counts[(pred, succ)] >= 2:
        #         patterns.append(DependencyPattern(
        #             predecessor_type=pred,
        #             successor_type=succ,
        #             frequency=transition_counts[(pred, succ)],
        #             avg_gap=statistics.mean(gaps),
        #             success_rate=0.9,  # Would calculate from data
        #             common_bottleneck=False,
        #         ))

        return patterns

    def discover_resource_patterns(self) -> List[ResourcePattern]:
        """Find typical resource requirements by task type.

        Returns:
            List of resource patterns
        """
        # Analyze resource requirements by task type
        resource_data: Dict[str, Dict[str, any]] = {}

        # Would query resource allocation data
        patterns = []

        return patterns

    def discover_temporal_patterns(self) -> List[TemporalPattern]:
        """Find time-of-day or day-of-week patterns.

        Returns:
            List of temporal patterns
        """
        # Analyze task execution times by day/hour
        timing_data: Dict[str, Dict[str, List[float]]] = {}

        # Would query task execution history with timestamps
        patterns = []

        return patterns

    def discover_quality_patterns(self) -> List[QualityPattern]:
        """Find patterns in quality outcomes.

        Returns:
            List of quality patterns
        """
        # Analyze quality metrics by task type
        quality_data: Dict[str, List[float]] = defaultdict(list)
        defect_data: Dict[str, int] = defaultdict(int)
        rework_data: Dict[str, int] = defaultdict(int)

        # Would query quality metrics from episodic events
        patterns = []

        return patterns

    def discover_all_patterns(self) -> List[Pattern]:
        """Discover all pattern types.

        Returns:
            List of all patterns sorted by score
        """
        patterns: List[Pattern] = []

        # Discover each pattern type
        for duration_pattern in self.discover_duration_patterns():
            patterns.append(Pattern(
                name=f"Duration pattern: {duration_pattern.task_type}",
                pattern_type="duration",
                frequency=duration_pattern.sample_count,
                impact=0.7,  # Duration has high impact
                actionability=0.9,  # Easy to apply
                score=0.7 * 0.9 * min(1.0, duration_pattern.sample_count / 10),
                data=duration_pattern,
            ))

        for dependency_pattern in self.discover_dependency_patterns():
            patterns.append(Pattern(
                name=f"Dependency: {dependency_pattern.predecessor_type} → {dependency_pattern.successor_type}",
                pattern_type="dependency",
                frequency=dependency_pattern.frequency,
                impact=0.8,  # Dependencies have high impact
                actionability=0.7,
                score=0.8 * 0.7 * min(1.0, dependency_pattern.frequency / 10),
                data=dependency_pattern,
            ))

        for resource_pattern in self.discover_resource_patterns():
            patterns.append(Pattern(
                name=f"Resources: {resource_pattern.task_type}",
                pattern_type="resource",
                frequency=resource_pattern.sample_count if hasattr(resource_pattern, 'sample_count') else 5,
                impact=0.6,
                actionability=0.8,
                score=0.6 * 0.8 * 0.7,
                data=resource_pattern,
            ))

        for temporal_pattern in self.discover_temporal_patterns():
            patterns.append(Pattern(
                name=f"Temporal: {temporal_pattern.task_type}",
                pattern_type="temporal",
                frequency=temporal_pattern.sample_count,
                impact=0.5,  # Temporal has moderate impact
                actionability=0.6,
                score=0.5 * 0.6 * min(1.0, temporal_pattern.sample_count / 10),
                data=temporal_pattern,
            ))

        for quality_pattern in self.discover_quality_patterns():
            patterns.append(Pattern(
                name=f"Quality: {quality_pattern.task_type}",
                pattern_type="quality",
                frequency=10,  # Would come from data
                impact=0.8,  # Quality has high impact
                actionability=0.7,
                score=0.8 * 0.7 * 0.8,
                data=quality_pattern,
            ))

        # Sort by score (descending)
        patterns.sort(key=lambda p: p.score, reverse=True)
        return patterns

    def rank_patterns(
        self, patterns: List[Pattern], top_n: int = 10
    ) -> List[Pattern]:
        """Rank patterns by combined score.

        Args:
            patterns: List of patterns to rank
            top_n: Return top N patterns

        Returns:
            Sorted patterns (highest impact first)
        """
        # Score = frequency × impact × actionability
        for pattern in patterns:
            pattern.score = pattern.frequency * pattern.impact * pattern.actionability

        # Sort by score descending
        patterns.sort(key=lambda p: p.score, reverse=True)
        return patterns[:top_n]

    def get_patterns_by_type(
        self, pattern_type: str
    ) -> List[Pattern]:
        """Get patterns of a specific type.

        Args:
            pattern_type: "duration" | "dependency" | "resource" | "temporal" | "quality"

        Returns:
            List of patterns of that type
        """
        all_patterns = self.discover_all_patterns()
        return [p for p in all_patterns if p.pattern_type == pattern_type]

    def get_actionable_patterns(self, top_n: int = 5) -> List[Pattern]:
        """Get most actionable patterns.

        Args:
            top_n: Number of patterns to return

        Returns:
            Top N patterns by actionability
        """
        patterns = self.discover_all_patterns()
        patterns.sort(key=lambda p: p.actionability * p.frequency, reverse=True)
        return patterns[:top_n]

    def suggest_improvements(self) -> List[str]:
        """Suggest process improvements based on patterns.

        Returns:
            List of actionable suggestions
        """
        suggestions = []
        patterns = self.get_actionable_patterns(5)

        for pattern in patterns:
            if pattern.pattern_type == "duration":
                suggestions.append(
                    f"Consider using {pattern.data.avg_duration:.0f}h "
                    f"as baseline for {pattern.data.task_type} tasks"
                )
            elif pattern.pattern_type == "dependency":
                suggestions.append(
                    f"Plan {pattern.data.avg_gap:.1f}h gap between "
                    f"{pattern.data.predecessor_type} and {pattern.data.successor_type}"
                )
            elif pattern.pattern_type == "resource":
                suggestions.append(
                    f"Allocate {pattern.data.typical_team_size} people for {pattern.data.task_type}"
                )
            elif pattern.pattern_type == "temporal":
                suggestions.append(
                    f"Schedule {pattern.data.task_type} on {pattern.data.faster_on_days}"
                )
            elif pattern.pattern_type == "quality":
                if pattern.data.rework_rate > 20:
                    suggestions.append(
                        f"High rework rate ({pattern.data.rework_rate:.0f}%) for {pattern.data.task_type} - "
                        f"consider additional review"
                    )

        return suggestions
