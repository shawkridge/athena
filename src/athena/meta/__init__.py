"""Meta-memory layer for self-awareness and coverage analysis."""

from .analysis import analyze_domain_coverage, detect_knowledge_gaps
from .models import DomainCoverage, ExpertiseLevel, KnowledgeTransfer, MemoryQuality
from .store import MetaMemoryStore

__all__ = [
    "DomainCoverage",
    "MemoryQuality",
    "KnowledgeTransfer",
    "ExpertiseLevel",
    "MetaMemoryStore",
    "analyze_domain_coverage",
    "detect_knowledge_gaps",
]
