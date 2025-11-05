"""Consolidation system for background optimization and learning.

Implements sleep-like memory consolidation (episodic→semantic) inspired by
complementary learning systems theory (Larimar, ICML 2024).

New additions (Phase 1):
- consolidate_episodic_to_semantic: Main consolidation pipeline
- cluster_events_by_context: Event clustering by session+spatial proximity
- extract_patterns: LLM-based pattern extraction with Claude extended thinking
"""

from .models import (
    ConsolidationRun,
    ConsolidationType,
    ExtractedPattern,
    MemoryConflict,
    PatternType,
)
from .system import ConsolidationSystem

# Phase 1: Core consolidation pipeline
from .pipeline import (
    consolidate_episodic_to_semantic,
    consolidation_daemon,
    ConsolidationReport,
)
from .clustering import (
    cluster_events_by_context,
    EventCluster,
    analyze_cluster_quality,
)
from .pattern_extraction import (
    extract_patterns,
    Pattern,
    extract_common_tags,
)

# Phase 2: Project learning
from .project_learning import (
    ProjectLearningEngine,
    ProjectInsight,
    ProjectTemplate,
    ProjectDifficulty,
)

# Phase 3: Advanced consolidation
from .strategy_learning import (
    StrategyLearningEngine,
    StrategyPerformance,
)
from .orchestration_learning import (
    OrchestrationLearningEngine,
    DiscoveredPattern,
)
from .validation_learning import (
    ValidationLearningEngine,
    RuleExecution,
    RuleMetrics,
)

__all__ = [
    # Original
    "ConsolidationRun",
    "ExtractedPattern",
    "MemoryConflict",
    "ConsolidationType",
    "PatternType",
    "ConsolidationSystem",

    # Phase 1: Consolidation pipeline
    "consolidate_episodic_to_semantic",
    "consolidation_daemon",
    "ConsolidationReport",

    # Phase 1: Event clustering
    "cluster_events_by_context",
    "EventCluster",
    "analyze_cluster_quality",

    # Phase 1: Pattern extraction
    "extract_patterns",
    "Pattern",
    "extract_common_tags",

    # Phase 2: Project learning
    "ProjectLearningEngine",
    "ProjectInsight",
    "ProjectTemplate",
    "ProjectDifficulty",

    # Phase 3: Advanced consolidation
    "StrategyLearningEngine",
    "StrategyPerformance",
    "OrchestrationLearningEngine",
    "DiscoveredPattern",
    "ValidationLearningEngine",
    "RuleExecution",
    "RuleMetrics",
]
