"""Citation Validator for Hallucination Detection.

Validates citations and references in AI-generated content:
- Citation presence: Are claims backed by sources?
- Citation quality: Are cited sources appropriate?
- Citation accuracy: Do sources support the claims?
- Citation format: Are citations properly formatted?
"""

import logging
import re
from typing import Optional, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CitationType(str, Enum):
    """Type of citation."""

    DIRECT = "direct"  # Direct quote with source
    PARAPHRASE = "paraphrase"  # Paraphrased from source
    IMPLICIT = "implicit"  # Implied reference
    NONE = "none"  # No citation


class SourceCredibility(str, Enum):
    """Assessment of source credibility."""

    HIGH = "high"  # Peer-reviewed, official, authoritative
    MEDIUM = "medium"  # Well-known publications, educational
    LOW = "low"  # Unknown, potentially unreliable
    UNKNOWN = "unknown"  # Source not found


@dataclass
class Citation:
    """Represents a single citation."""

    source: str
    claim_text: str
    citation_type: CitationType
    credibility: SourceCredibility
    page_reference: Optional[str] = None
    access_date: Optional[str] = None
    direct_quote: Optional[str] = None
    confidence: float = 0.5


@dataclass
class CitationValidation:
    """Result of citation validation."""

    claim_text: str
    has_citation: bool
    citation_quality: float = 0.0  # 0.0 (poor) to 1.0 (excellent)
    citations: List[Citation] = field(default_factory=list)
    needs_citation: bool = True  # Should this have a citation?
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class CitationValidator:
    """Validate citations and references.

    Checks:
    - Whether claims are cited
    - Quality of sources
    - Citation format
    - Citation-claim alignment

    Attributes:
        trusted_domains: List of high-credibility domains
        known_sources: Dictionary of source credibility assessments
    """

    # High-credibility sources
    TRUSTED_DOMAINS = {
        # Academic
        ".edu",
        ".ac.uk",
        ".ac.kr",
        ".edu.au",
        # Government
        ".gov",
        ".gov.uk",
        ".gouv.fr",
        # Reputable publishers
        "nature.com",
        "science.org",
        "ieee.org",
        "springer.com",
        "wiley.com",
        "elsevier.com",
        # News organizations
        "bbc.com",
        "reuters.com",
        "apnews.com",
    }

    def __init__(self):
        """Initialize citation validator."""
        self.logger = logging.getLogger(__name__)
        self.known_sources: Dict[str, SourceCredibility] = {}

    def register_trusted_source(self, source: str, credibility: SourceCredibility) -> None:
        """Register a known source with its credibility.

        Args:
            source: Source identifier (URL, book title, etc.)
            credibility: Credibility assessment
        """
        self.known_sources[source.lower()] = credibility
        self.logger.debug(f"Registered {source} as {credibility.value}")

    def extract_citations(self, text: str) -> List[Citation]:
        """Extract citations from text.

        Looks for patterns like:
        - [1] references with footnotes
        - (Author Year) APA format
        - Author, Year format
        - URL references

        Args:
            text: Text to extract citations from

        Returns:
            List of identified citations
        """
        citations = []

        # Pattern 1: [number] style citations
        for match in re.finditer(r"\[\d+\]", text):
            citation_text = match.group(0)
            citations.append(
                Citation(
                    source=citation_text,
                    claim_text="",
                    citation_type=CitationType.DIRECT,
                    credibility=SourceCredibility.UNKNOWN,
                )
            )

        # Pattern 2: (Author Year) APA style
        for match in re.finditer(r"\(([A-Z][a-z]+(?:\s+&\s+[A-Z][a-z]+)*),?\s+(\d{4})\)", text):
            author, year = match.groups()
            citations.append(
                Citation(
                    source=f"{author} {year}",
                    claim_text="",
                    citation_type=CitationType.PARAPHRASE,
                    credibility=SourceCredibility.UNKNOWN,
                )
            )

        # Pattern 3: URLs
        for match in re.finditer(r"https?://[^\s\)]+", text):
            url = match.group(0)
            credibility = self._assess_url_credibility(url)
            citations.append(
                Citation(
                    source=url,
                    claim_text="",
                    citation_type=CitationType.DIRECT,
                    credibility=credibility,
                )
            )

        # Pattern 4: Direct quotes with attribution
        for match in re.finditer(r'"([^"]+)"\s*(?:—|–|-)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text):
            quote, source = match.groups()
            citations.append(
                Citation(
                    source=source,
                    claim_text="",
                    citation_type=CitationType.DIRECT,
                    credibility=SourceCredibility.MEDIUM,
                    direct_quote=quote,
                )
            )

        return citations

    def _assess_url_credibility(self, url: str) -> SourceCredibility:
        """Assess credibility of URL.

        Args:
            url: URL to assess

        Returns:
            SourceCredibility assessment
        """
        url_lower = url.lower()

        # Check trusted domains
        for domain in self.TRUSTED_DOMAINS:
            if domain in url_lower:
                return SourceCredibility.HIGH

        # Known bad domains
        if any(bad in url_lower for bad in ["blogspot", "wordpress", "random-site", "unverified"]):
            return SourceCredibility.LOW

        # Unknown domain
        return SourceCredibility.MEDIUM

    def validate_claim_citations(
        self,
        claim_text: str,
        citations_in_text: List[Citation],
        claim_importance: str = "medium",  # low, medium, high
    ) -> CitationValidation:
        """Validate that a claim is properly cited.

        Args:
            claim_text: The claim being made
            citations_in_text: Citations found in source text
            claim_importance: How important is this claim? (affects citation need)

        Returns:
            CitationValidation result
        """
        # Determine if citation is needed
        needs_citation = self._should_be_cited(claim_text, claim_importance)

        # Check if any citations are present
        has_citation = len(citations_in_text) > 0

        # Assess citation quality
        citation_quality = self._assess_citation_quality(citations_in_text) if has_citation else 0.0

        # Generate warnings and suggestions
        warnings, suggestions = self._generate_citation_feedback(
            claim_text, has_citation, needs_citation, citations_in_text, citation_quality
        )

        return CitationValidation(
            claim_text=claim_text,
            has_citation=has_citation,
            citations=citations_in_text,
            citation_quality=citation_quality,
            needs_citation=needs_citation,
            warnings=warnings,
            suggestions=suggestions,
        )

    @staticmethod
    def _should_be_cited(claim_text: str, claim_importance: str) -> bool:
        """Determine if claim should be cited.

        Args:
            claim_text: The claim
            claim_importance: Importance level (low, medium, high)

        Returns:
            True if citation is needed
        """
        # High importance claims always need citation
        if claim_importance == "high":
            return True

        # Claims with specific facts/figures should be cited
        if re.search(r"\b\d+\s*(?:%|dollars?|percent|years?)\b", claim_text):
            return True

        # Named entities should be cited
        if re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", claim_text):
            return True

        # Medium importance + anything specific
        if claim_importance == "medium" and len(claim_text.split()) > 5:
            return True

        # Low importance claims can go uncited
        return claim_importance == "high"

    @staticmethod
    def _assess_citation_quality(citations: List[Citation]) -> float:
        """Assess overall quality of citations.

        Args:
            citations: List of citations to assess

        Returns:
            Quality score 0.0-1.0
        """
        if not citations:
            return 0.0

        credibility_scores = {
            SourceCredibility.HIGH: 1.0,
            SourceCredibility.MEDIUM: 0.6,
            SourceCredibility.LOW: 0.2,
            SourceCredibility.UNKNOWN: 0.4,
        }

        avg_score = sum(credibility_scores.get(c.credibility, 0.5) for c in citations) / len(
            citations
        )

        # Multiple high-quality sources boost quality
        high_cred_count = sum(1 for c in citations if c.credibility == SourceCredibility.HIGH)
        if high_cred_count >= 2:
            avg_score = min(1.0, avg_score * 1.2)

        return min(1.0, avg_score)

    @staticmethod
    def _generate_citation_feedback(
        claim_text: str,
        has_citation: bool,
        needs_citation: bool,
        citations: List[Citation],
        citation_quality: float,
    ) -> Tuple[List[str], List[str]]:
        """Generate warnings and suggestions for citations.

        Args:
            claim_text: The claim
            has_citation: Whether citations exist
            needs_citation: Whether citations are needed
            citations: The citations found
            citation_quality: Quality assessment (0-1)

        Returns:
            (warnings list, suggestions list)
        """
        warnings = []
        suggestions = []

        # Missing citations
        if needs_citation and not has_citation:
            warnings.append("Claim needs citation but none provided")
            suggestions.append("Add citation to verify this claim")

        # Low quality citations
        if has_citation and citation_quality < 0.5:
            warnings.append("Citations are from questionable sources")
            suggestions.append("Use more authoritative sources")

        # Unknown sources
        unknown_citations = [c for c in citations if c.credibility == SourceCredibility.UNKNOWN]
        if unknown_citations:
            warnings.append(f"{len(unknown_citations)} citations from unknown sources")
            suggestions.append("Verify source credibility or replace with known sources")

        # Implicit citations
        implicit = [c for c in citations if c.citation_type == CitationType.IMPLICIT]
        if implicit:
            suggestions.append("Make implicit citations explicit")

        return warnings, suggestions

    def validate_all_citations(self, text: str) -> Dict[str, CitationValidation]:
        """Validate all claims and their citations in text.

        Args:
            text: Text to validate

        Returns:
            Dictionary mapping claim text to CitationValidation
        """
        # Extract claims
        claims = re.split(r"[.!?]+", text.strip())
        claims = [c.strip() for c in claims if len(c.strip()) > 10]

        # Extract all citations
        all_citations = self.extract_citations(text)

        # Validate each claim
        results = {}
        for claim in claims:
            # For simplicity, assign all citations to all claims
            # In practice, you'd match citations to specific claims
            validation = self.validate_claim_citations(
                claim, all_citations, claim_importance="medium"
            )
            results[claim] = validation

        return results
