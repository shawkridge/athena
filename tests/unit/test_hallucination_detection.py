"""Unit tests for Hallucination Detection (Claim + Citation Validation).

Tests for:
- ClaimValidator: Claim classification and risk assessment
- CitationValidator: Citation extraction and validation
"""

import pytest

from athena.validation.claim_validator import (
    ClaimValidator, ValidatedClaim, ClaimType, VerifiabilityScore
)
from athena.validation.citation_validator import (
    CitationValidator, Citation, CitationType, SourceCredibility
)


# ============================================================================
# ClaimValidator Tests
# ============================================================================

class TestClaimClassification:
    """Tests for claim type classification."""

    def test_classify_fact(self):
        """Should classify concrete statements as facts."""
        validator = ClaimValidator()
        claim = "The Earth orbits the Sun"
        claim_type = validator.classify_claim(claim)
        assert claim_type == ClaimType.FACT

    def test_classify_opinion(self):
        """Should classify subjective statements as opinions."""
        validator = ClaimValidator()
        claim = "I think Python is the best programming language"
        claim_type = validator.classify_claim(claim)
        assert claim_type == ClaimType.OPINION

    def test_classify_uncertainty(self):
        """Should classify uncertain statements."""
        validator = ClaimValidator()
        claim = "This may be true or might not be"
        claim_type = validator.classify_claim(claim)
        assert claim_type == ClaimType.UNCERTAINTY

    def test_classify_hypothetical(self):
        """Should classify conditional statements."""
        validator = ClaimValidator()
        claim = "If it rains, then the ground gets wet"
        claim_type = validator.classify_claim(claim)
        assert claim_type == ClaimType.HYPOTHETICAL

    def test_classify_hearsay(self):
        """Should classify reported information."""
        validator = ClaimValidator()
        claim = "According to sources, the economy is improving"
        claim_type = validator.classify_claim(claim)
        assert claim_type == ClaimType.HEARSAY


class TestVerifiabilityAssessment:
    """Tests for claim verifiability assessment."""

    def test_high_verifiability_with_specific_facts(self):
        """Claims with dates/names should be high verifiability."""
        validator = ClaimValidator()
        claim = "The 2024 Olympics were held in Paris, France in July 2024"
        verifiability = validator.assess_verifiability(claim)
        assert verifiability == VerifiabilityScore.HIGH

    def test_medium_verifiability_with_names(self):
        """Claims with named entities should be medium verifiability."""
        validator = ClaimValidator()
        claim = "Albert Einstein developed the theory of relativity"
        verifiability = validator.assess_verifiability(claim)
        assert verifiability in [VerifiabilityScore.MEDIUM, VerifiabilityScore.HIGH]

    def test_low_verifiability_vague_claims(self):
        """Vague claims should be low verifiability."""
        validator = ClaimValidator()
        claim = "Things are getting better"
        verifiability = validator.assess_verifiability(claim)
        assert verifiability in [VerifiabilityScore.LOW, VerifiabilityScore.MEDIUM]

    def test_impossible_verifiability_unfalsifiable(self):
        """Unfalsifiable claims should be impossible."""
        validator = ClaimValidator()
        claim = "This will always be true forever"
        verifiability = validator.assess_verifiability(claim)
        assert verifiability in [VerifiabilityScore.LOW, VerifiabilityScore.IMPOSSIBLE]


class TestClaimValidation:
    """Tests for complete claim validation."""

    def test_validate_high_confidence_specific_fact(self):
        """High confidence on specific facts should have low risk."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="Paris is the capital of France",
            stated_confidence=0.95
        )

        assert validated.claim_type == ClaimType.FACT
        assert validated.verifiability == VerifiabilityScore.HIGH
        assert validated.confidence_justified is True
        assert validated.risk_score < 0.3

    def test_validate_high_confidence_unverifiable(self):
        """High confidence on vague claims should have high risk."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="Things will always be like this",
            stated_confidence=0.95
        )

        assert not validated.confidence_justified
        assert validated.risk_score > 0.5
        assert len(validated.warnings) > 0

    def test_validate_opinion_requires_low_confidence(self):
        """Opinions with high confidence should flag."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="I think Python is beautiful",
            stated_confidence=0.95
        )

        assert validated.claim_type == ClaimType.OPINION
        assert not validated.confidence_justified

    def test_validate_claim_with_suggestions(self):
        """Low verifiability should generate suggestions."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="Some things are important",
            stated_confidence=0.9
        )

        assert len(validated.suggestions) > 0
        assert any('specific' in s.lower() for s in validated.suggestions)


class TestClaimCitationRequirements:
    """Tests for determining citation needs."""

    def test_high_verifiability_requires_citation(self):
        """Specific claims should require citations."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="The population of Japan is 125 million",
            stated_confidence=0.8
        )

        assert validated.requires_citation is True

    def test_opinion_may_not_require_citation(self):
        """Opinions may not require citations."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="I think this is good",
            stated_confidence=0.5
        )

        # Depends on configuration, but test it exists
        assert isinstance(validated.requires_citation, bool)


# ============================================================================
# CitationValidator Tests
# ============================================================================

class TestCitationExtraction:
    """Tests for citation extraction."""

    def test_extract_bracketed_citations(self):
        """Should extract [1] style citations."""
        validator = CitationValidator()
        text = "This is true[1] and this is cited[2]."
        citations = validator.extract_citations(text)

        assert len(citations) >= 2
        assert any('[1]' in c.source for c in citations)

    def test_extract_apa_citations(self):
        """Should extract (Author Year) style citations."""
        validator = CitationValidator()
        text = "According to research (Smith 2020), this is true."
        citations = validator.extract_citations(text)

        assert len(citations) > 0
        assert any('Smith' in c.source for c in citations)

    def test_extract_url_citations(self):
        """Should extract URLs as citations."""
        validator = CitationValidator()
        text = "As reported at https://example.com/article, this is true."
        citations = validator.extract_citations(text)

        assert len(citations) > 0
        assert any('https' in c.source for c in citations)

    def test_extract_direct_quotes(self):
        """Should extract quoted citations."""
        validator = CitationValidator()
        text = '"This is a quote" — John Smith'
        citations = validator.extract_citations(text)

        assert len(citations) > 0


class TestSourceCredibility:
    """Tests for source credibility assessment."""

    def test_assess_academic_url_credibility(self):
        """URLs from .edu should have high credibility."""
        validator = CitationValidator()
        credibility = validator._assess_url_credibility("https://www.university.edu/research")
        assert credibility == SourceCredibility.HIGH

    def test_assess_government_url_credibility(self):
        """URLs from .gov should have high credibility."""
        validator = CitationValidator()
        credibility = validator._assess_url_credibility("https://data.gov/statistics")
        assert credibility == SourceCredibility.HIGH

    def test_assess_unknown_url_credibility(self):
        """Unknown URLs should have medium/low credibility."""
        validator = CitationValidator()
        credibility = validator._assess_url_credibility("https://random-website.com/article")
        assert credibility in [SourceCredibility.MEDIUM, SourceCredibility.LOW]


class TestCitationValidation:
    """Tests for citation validation."""

    def test_validate_well_cited_claim(self):
        """Claims with good citations should validate well."""
        validator = CitationValidator()
        citations = [
            Citation(
                source="https://www.nature.com/article",
                claim_text="Test claim",
                citation_type=CitationType.DIRECT,
                credibility=SourceCredibility.HIGH
            )
        ]

        validation = validator.validate_claim_citations(
            claim_text="This is a scientific claim",
            citations_in_text=citations,
            claim_importance="high"
        )

        assert validation.has_citation is True
        assert validation.citation_quality > 0.5

    def test_validate_uncited_important_claim(self):
        """Important claims without citations should warn."""
        validator = CitationValidator()

        validation = validator.validate_claim_citations(
            claim_text="The climate is changing rapidly",
            citations_in_text=[],
            claim_importance="high"
        )

        assert not validation.has_citation
        assert validation.needs_citation is True
        assert len(validation.warnings) > 0

    def test_validate_low_quality_citations(self):
        """Claims with poor citations should flag."""
        validator = CitationValidator()
        citations = [
            Citation(
                source="https://random-blog.wordpress.com",
                claim_text="Test",
                citation_type=CitationType.IMPLICIT,
                credibility=SourceCredibility.LOW
            )
        ]

        validation = validator.validate_claim_citations(
            claim_text="Scientific fact",
            citations_in_text=citations,
            claim_importance="high"
        )

        assert validation.has_citation is True
        assert validation.citation_quality < 0.5


class TestSourceRegistration:
    """Tests for registering known sources."""

    def test_register_trusted_source(self):
        """Should remember registered sources."""
        validator = CitationValidator()
        validator.register_trusted_source("Journal of Nature", SourceCredibility.HIGH)

        # Registration happened without error
        assert "journal of nature" in validator.known_sources


class TestHallucinationRiskScoring:
    """Tests for hallucination risk calculation."""

    def test_risk_score_range(self):
        """Risk scores should be 0.0-1.0."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="This is a test claim",
            stated_confidence=0.5
        )

        assert 0.0 <= validated.risk_score <= 1.0

    def test_low_risk_verifiable_confident(self):
        """Verifiable + confident = low risk."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="Paris is in France",
            stated_confidence=0.99
        )

        assert validated.risk_score < 0.4

    def test_high_risk_unverifiable_confident(self):
        """Unverifiable + confident = high risk."""
        validator = ClaimValidator()
        validated = validator.validate_claim(
            claim_text="In the future everything will change forever always",
            stated_confidence=0.99
        )

        assert validated.risk_score > 0.6


class TestValidateMultipleClaims:
    """Tests for validating multiple claims."""

    def test_validate_text_multiple_claims(self):
        """Should validate all claims in text."""
        validator = ClaimValidator()
        text = """
        Paris is the capital of France.
        The Earth orbits the Sun.
        Maybe something is true.
        """

        results = validator.validate_text(text)

        assert len(results) >= 2
        assert all(isinstance(r, ValidatedClaim) for r in results)

    def test_validate_with_confidence_scores(self):
        """Should use provided confidence scores."""
        validator = ClaimValidator()
        text = "Claim one. Claim two. Claim three."

        results = validator.validate_text(
            text,
            confidences=[0.3, 0.7, 0.95]
        )

        assert len(results) == 3
        assert results[0].confidence == 0.3
        assert results[1].confidence == 0.7
        assert results[2].confidence == 0.95
