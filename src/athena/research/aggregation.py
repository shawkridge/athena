"""Research findings aggregation, deduplication, and cross-validation."""

import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AggregatedFinding:
    """A deduplicated, cross-validated finding from multiple sources."""

    title: str
    summary: str
    url: Optional[str] = None
    primary_source: str = ""
    secondary_sources: list[str] = field(default_factory=list)
    base_credibility: float = 0.8
    cross_validation_boost: float = 0.0
    final_credibility: float = field(default=0.0, init=False)
    relevance_score: float = 0.8

    def __post_init__(self):
        """Calculate final credibility after init."""
        self.final_credibility = self._calculate_final_credibility()

    def _calculate_final_credibility(self) -> float:
        """Calculate final credibility score.

        Base score multiplied by relevance, plus cross-validation boost.
        """
        base = self.base_credibility * self.relevance_score

        # Cross-validation boost: +0.10 for 1+ secondary, +0.15 for 2+ sources, +0.25 for 3+ sources
        boost = 0.0
        if len(self.secondary_sources) >= 3:
            boost = 0.25
        elif len(self.secondary_sources) >= 2:
            boost = 0.15
        elif len(self.secondary_sources) >= 1:
            boost = 0.10

        final = min(base + boost, 1.0)  # Cap at 1.0
        return final

    def add_secondary_source(self, source: str) -> None:
        """Add a secondary source that validates this finding."""
        if source not in self.secondary_sources and source != self.primary_source:
            self.secondary_sources.append(source)
            self.final_credibility = self._calculate_final_credibility()


class FindingDeduplicator:
    """Deduplicate findings based on semantic similarity."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize deduplicator.

        Args:
            similarity_threshold: Cosine similarity threshold for considering findings as duplicates
        """
        self.similarity_threshold = similarity_threshold

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Simplified implementation using word overlap.
        In production, would use embeddings for semantic similarity.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union

    def find_duplicates(self, title1: str, title2: str) -> bool:
        """Check if two findings are likely duplicates.

        Args:
            title1: First finding title
            title2: Second finding title

        Returns:
            True if findings are likely duplicates
        """
        similarity = self.calculate_text_similarity(title1, title2)
        return similarity >= self.similarity_threshold

    def deduplicate_findings(self, findings: list[dict]) -> list[AggregatedFinding]:
        """Deduplicate findings and merge from multiple sources.

        Args:
            findings: List of raw findings from agents
                Each with: title, summary, url, source, credibility_score, relevance

        Returns:
            List of deduplicated, aggregated findings
        """
        aggregated = {}

        for finding in findings:
            title = finding.get("title", "")
            summary = finding.get("summary", "")
            url = finding.get("url")
            source = finding.get("source", "Unknown")
            credibility = finding.get("credibility_score", 0.8)
            relevance = finding.get("relevance_score", 0.8)

            # Check if this is a duplicate of an existing finding
            duplicate_key = None
            for existing_title in aggregated.keys():
                if self.find_duplicates(title, existing_title):
                    duplicate_key = existing_title
                    break

            if duplicate_key:
                # Merge with existing finding
                existing = aggregated[duplicate_key]

                # Add this source as secondary source
                existing.add_secondary_source(source)

                # Update base credibility if this source is higher
                if credibility > existing.base_credibility:
                    existing.base_credibility = credibility
                    existing.primary_source = source

                # Update URL if missing
                if not existing.url and url:
                    existing.url = url

                logger.info(f"Merged duplicate finding: {title[:50]}... from {source}")

            else:
                # New finding
                aggregated_finding = AggregatedFinding(
                    title=title,
                    summary=summary,
                    url=url,
                    primary_source=source,
                    base_credibility=credibility,
                    relevance_score=relevance,
                )
                aggregated[title] = aggregated_finding

        return list(aggregated.values())


class FindingCrossValidator:
    """Cross-validate findings across sources."""

    def __init__(self):
        """Initialize cross-validator."""
        self.source_credibility_map = {
            "arXiv": 1.0,
            "Anthropic Docs": 0.95,
            "Papers with Code": 0.90,
            "Tech Blogs": 0.88,
            "GitHub": 0.85,
            "HackerNews": 0.70,
            "Medium": 0.68,
            "X/Twitter": 0.62,
        }

    def validate_findings(self, findings: list[AggregatedFinding]) -> list[AggregatedFinding]:
        """Validate and score findings based on source credibility.

        Args:
            findings: List of aggregated findings

        Returns:
            Findings with updated credibility scores
        """
        validated = []

        for finding in findings:
            # Get credibility for primary source
            primary_cred = self.source_credibility_map.get(finding.primary_source, 0.5)
            finding.base_credibility = primary_cred

            # Boost if found in multiple sources
            if finding.secondary_sources:
                validated_sources = [
                    s
                    for s in finding.secondary_sources
                    if self.source_credibility_map.get(s, 0) >= 0.7
                ]
                if validated_sources:
                    finding.cross_validation_boost = 0.15 * len(validated_sources)

            finding.final_credibility = finding._calculate_final_credibility()
            validated.append(finding)

        # Sort by credibility
        validated.sort(key=lambda f: f.final_credibility, reverse=True)

        return validated

    def filter_high_confidence(
        self, findings: list[AggregatedFinding], min_credibility: float = 0.8
    ) -> list[AggregatedFinding]:
        """Filter findings to only high-confidence ones.

        Args:
            findings: List of findings
            min_credibility: Minimum credibility score to keep

        Returns:
            Filtered findings
        """
        return [f for f in findings if f.final_credibility >= min_credibility]


class FindingAggregator:
    """Aggregate findings from multiple agents."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize aggregator.

        Args:
            similarity_threshold: Threshold for deduplication
        """
        self.deduplicator = FindingDeduplicator(similarity_threshold)
        self.cross_validator = FindingCrossValidator()

    def aggregate(
        self, findings: list[dict], high_confidence_only: bool = False
    ) -> list[AggregatedFinding]:
        """Aggregate, deduplicate, and validate findings.

        Args:
            findings: Raw findings from agents
            high_confidence_only: If True, only return credibility >= 0.8

        Returns:
            List of validated, ranked findings
        """
        # Step 1: Deduplicate
        deduplicated = self.deduplicator.deduplicate_findings(findings)
        logger.info(f"Deduplicated {len(findings)} findings to {len(deduplicated)}")

        # Step 2: Cross-validate
        validated = self.cross_validator.validate_findings(deduplicated)

        # Step 3: Filter if requested
        if high_confidence_only:
            validated = self.cross_validator.filter_high_confidence(validated)
            logger.info(f"Filtered to {len(validated)} high-confidence findings")

        return validated

    def get_summary_stats(self, findings: list[AggregatedFinding]) -> dict:
        """Get summary statistics for findings.

        Args:
            findings: List of aggregated findings

        Returns:
            Statistics dict
        """
        if not findings:
            return {
                "total": 0,
                "average_credibility": 0.0,
                "high_confidence_count": 0,
                "sources_represented": set(),
            }

        sources = set()
        for finding in findings:
            sources.add(finding.primary_source)
            sources.update(finding.secondary_sources)

        high_confidence = len([f for f in findings if f.final_credibility >= 0.8])

        return {
            "total": len(findings),
            "average_credibility": sum(f.final_credibility for f in findings) / len(findings),
            "high_confidence_count": high_confidence,
            "sources_represented": sources,
            "multi_source_findings": len([f for f in findings if f.secondary_sources]),
        }
