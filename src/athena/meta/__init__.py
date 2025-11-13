"""Meta-memory layer for self-awareness and coverage analysis."""

from .analysis import analyze_domain_coverage, detect_knowledge_gaps
from .attention import AttentionManager
from .models import (
    DomainCoverage,
    ExpertiseLevel,
    KnowledgeTransfer,
    MemoryQuality,
    AttentionItem,
    WorkingMemory,
    AttentionBudget,
)
from .store import MetaMemoryStore

__all__ = [
    "DomainCoverage",
    "MemoryQuality",
    "KnowledgeTransfer",
    "ExpertiseLevel",
    "AttentionItem",
    "WorkingMemory",
    "AttentionBudget",
    "MetaMemoryStore",
    "AttentionManager",
    "analyze_domain_coverage",
    "detect_knowledge_gaps",
]
