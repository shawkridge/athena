"""Domain coverage analysis and knowledge gap detection."""

from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from ..episodic.store import EpisodicStore
from ..procedural.store import ProceduralStore
from .models import DomainCoverage, ExpertiseLevel
from .store import MetaMemoryStore


def analyze_domain_coverage(
    project_id: int,
    episodic_store: EpisodicStore,
    procedural_store: ProceduralStore,
    meta_store: MetaMemoryStore,
) -> List[DomainCoverage]:
    """Analyze domain coverage across all memory layers.

    Args:
        project_id: Project ID to analyze
        episodic_store: Episodic memory store
        procedural_store: Procedural memory store
        meta_store: Meta-memory store

    Returns:
        List of domain coverage reports
    """
    domains = defaultdict(lambda: {
        "memory_count": 0,
        "episodic_count": 0,
        "procedural_count": 0,
        "entity_count": 0,
        "confidence_sum": 0.0,
        "usefulness_sum": 0.0,
        "first_encounter": None,
    })

    # Analyze episodic events
    events = episodic_store.get_recent_events(project_id, hours=720)  # 30 days
    for event in events:
        # Extract domains from content
        event_domains = _extract_domains_from_text(event.content)

        for domain in event_domains:
            domains[domain]["episodic_count"] += 1
            if domains[domain]["first_encounter"] is None:
                domains[domain]["first_encounter"] = event.timestamp

    # Analyze procedural memory
    procedures = procedural_store.list_procedures(limit=1000)
    for proc in procedures:
        proc_domains = _extract_domains_from_text(proc.name + " " + proc.description)

        for domain in proc_domains:
            domains[domain]["procedural_count"] += 1

    # Create domain coverage objects
    coverage_list = []
    for domain_name, stats in domains.items():
        total_memories = stats["memory_count"]
        avg_confidence = (
            stats["confidence_sum"] / total_memories if total_memories > 0 else 0.0
        )
        avg_usefulness = (
            stats["usefulness_sum"] / total_memories if total_memories > 0 else 0.0
        )

        # Infer expertise level
        expertise = _infer_expertise(
            stats["memory_count"],
            stats["episodic_count"],
            stats["procedural_count"],
            avg_confidence,
        )

        # Infer category
        category = _infer_category(domain_name)

        coverage = DomainCoverage(
            domain=domain_name,
            category=category,
            memory_count=stats["memory_count"],
            episodic_count=stats["episodic_count"],
            procedural_count=stats["procedural_count"],
            entity_count=0,  # Would need graph store integration
            avg_confidence=avg_confidence,
            avg_usefulness=avg_usefulness,
            last_updated=datetime.now(),
            gaps=[],  # Filled by detect_knowledge_gaps
            strength_areas=[],
            first_encounter=stats["first_encounter"],
            expertise_level=expertise,
        )

        # Store in meta-memory
        meta_store.create_domain(coverage)
        coverage_list.append(coverage)

    return coverage_list


def detect_knowledge_gaps(
    domain: DomainCoverage, episodic_store: EpisodicStore, project_id: int
) -> List[str]:
    """Detect knowledge gaps for a domain.

    Args:
        domain: Domain to analyze
        episodic_store: Episodic store for error analysis
        project_id: Project ID

    Returns:
        List of identified gaps
    """
    gaps = []

    # Low memory count indicates gap
    if domain.memory_count < 5:
        gaps.append(f"Limited knowledge (only {domain.memory_count} memories)")

    # Low confidence indicates uncertainty
    if domain.avg_confidence < 0.5:
        gaps.append(f"Low confidence ({domain.avg_confidence:.1%})")

    # No procedural knowledge
    if domain.procedural_count == 0 and domain.episodic_count > 10:
        gaps.append("No learned procedures despite experience")

    # Check for error patterns
    events = episodic_store.get_recent_events(project_id, hours=720)
    domain_events = [e for e in events if domain.domain.lower() in e.content.lower()]
    error_count = sum(1 for e in domain_events if e.outcome == "failure")

    if error_count > len(domain_events) * 0.3:  # >30% failure rate
        gaps.append(f"High error rate ({error_count}/{len(domain_events)} failures)")

    return gaps


def _extract_domains_from_text(text: str) -> List[str]:
    """Extract technology/domain keywords from text.

    Args:
        text: Text to analyze

    Returns:
        List of domain names
    """
    text_lower = text.lower()
    domains = []

    # Common technology domains
    tech_keywords = {
        "react": "react",
        "vue": "vue",
        "angular": "angular",
        "typescript": "typescript",
        "javascript": "javascript",
        "python": "python",
        "rust": "rust",
        "go": "golang",
        "java": "java",
        "auth": "authentication",
        "authentication": "authentication",
        "database": "database",
        "sql": "sql",
        "postgres": "postgresql",
        "mongodb": "mongodb",
        "redis": "redis",
        "api": "api",
        "rest": "rest-api",
        "graphql": "graphql",
        "test": "testing",
        "testing": "testing",
        "pytest": "testing",
        "jest": "testing",
        "git": "git",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "aws": "aws",
        "azure": "azure",
        "gcp": "gcp",
    }

    for keyword, domain in tech_keywords.items():
        if keyword in text_lower:
            domains.append(domain)

    return list(set(domains))  # Unique domains


def _infer_expertise(
    memory_count: int, episodic_count: int, procedural_count: int, avg_confidence: float
) -> ExpertiseLevel:
    """Infer expertise level from metrics.

    Args:
        memory_count: Number of semantic memories
        episodic_count: Number of episodic events
        procedural_count: Number of procedures
        avg_confidence: Average confidence score

    Returns:
        Inferred expertise level
    """
    # Calculate experience score
    experience = memory_count * 2 + episodic_count + procedural_count * 5

    # Weight by confidence
    score = experience * avg_confidence

    if score >= 100:
        return ExpertiseLevel.EXPERT
    elif score >= 50:
        return ExpertiseLevel.ADVANCED
    elif score >= 20:
        return ExpertiseLevel.INTERMEDIATE
    else:
        return ExpertiseLevel.BEGINNER


def _infer_category(domain_name: str) -> str:
    """Infer domain category from name.

    Args:
        domain_name: Domain name

    Returns:
        Category string
    """
    tech_domains = ["react", "vue", "angular", "typescript", "javascript", "python", "rust", "golang", "java"]
    infrastructure = ["docker", "kubernetes", "aws", "azure", "gcp"]
    databases = ["sql", "postgresql", "mongodb", "redis", "database"]
    patterns = ["authentication", "testing", "api", "rest-api", "graphql"]

    domain_lower = domain_name.lower()

    if any(tech in domain_lower for tech in tech_domains):
        return "technology"
    elif any(infra in domain_lower for infra in infrastructure):
        return "infrastructure"
    elif any(db in domain_lower for db in databases):
        return "database"
    elif any(pattern in domain_lower for pattern in patterns):
        return "pattern"
    else:
        return "general"
