"""Claim Validator for Hallucination Detection.

Validates claims in AI-generated content by checking:
- Verifiability: Can claim be objectively verified?
- Specificity: Is claim specific enough to be falsifiable?
- Confidence alignment: Does confidence match verifiability?
- Consistency: Is claim consistent with known facts?
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ClaimType(str, Enum):
    """Classification of claim types."""
    FACT = "fact"  # Objective, verifiable claim
    OPINION = "opinion"  # Subjective, interpretation
    HYPOTHETICAL = "hypothetical"  # Conditional, if-then
    HEARSAY = "hearsay"  # Reported from other source
    UNCERTAINTY = "uncertainty"  # Explicitly uncertain


class VerifiabilityScore(str, Enum):
    """How verifiable is a claim?"""
    HIGH = "high"  # Directly verifiable (dates, names, quantities)
    MEDIUM = "medium"  # Verifiable but requires research
    LOW = "low"  # Hard to verify (interpretations, vague)
    IMPOSSIBLE = "impossible"  # Unfalsifiable


@dataclass
class ValidatedClaim:
    """Result of claim validation."""
    claim_text: str
    claim_type: ClaimType
    verifiability: VerifiabilityScore
    confidence: float  # Model's stated confidence
    confidence_justified: bool  # Does confidence match verifiability?
    requires_citation: bool  # Should this claim be cited?
    risk_score: float  # 0.0 (safe) to 1.0 (high hallucination risk)
    warnings: List[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


class ClaimValidator:
    """Validate AI-generated claims for hallucination risk.

    Uses linguistic patterns, confidence analysis, and verifiability
    assessment to flag potentially hallucinated content.

    Attributes:
        confidence_threshold: Flag if confidence > this (default 0.8)
        require_low_confidence_citations: Force citations for unverifiable claims
    """

    # Patterns indicating uncertainty
    UNCERTAINTY_PATTERNS = [
        r'\bmight\b', r'\bcould\b', r'\bpossibly\b',
        r'\bprobably\b', r'\blikely\b', r'\bseems\b',
        r'\bappears\b', r'\bmay\b', r'\bmaybe\b',
        r'\bperhaps\b', r'\b(?:is )?(?:said|alleged)\b'
    ]

    # Patterns indicating strong claims
    STRONG_CLAIM_PATTERNS = [
        r'\balways\b', r'\bnever\b', r'\bcertainly\b',
        r'\bprovably\b', r'\bfactually\b', r'\bonline\b'
    ]

    # Patterns indicating opinion
    OPINION_PATTERNS = [
        r'\bi (?:think|believe|feel)\b',
        r'\bin my (?:opinion|view|experience)\b',
        r'\b(?:is )?(?:beautiful|ugly|good|bad|great|terrible)\b',
        r'\bshould\b', r'\boughtto\b'
    ]

    # Specific fact patterns (high verifiability)
    FACT_PATTERNS = [
        r'\b(?:year|month|day|date|time):\s*\d+',  # Dates
        r'\b\d{1,2}(?:/|-)\d{1,2}(?:/|-)\d{4}\b',  # Date formats
        r'\b\d+\s*(?:percent|%|degrees?|dollars?|euros?)\b',  # Quantities
        r'\b(?:Dr|Mr|Mrs|Prof)\.\s+[A-Z]',  # Titles
        r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Names
    ]

    def __init__(
        self,
        confidence_threshold: float = 0.8,
        require_low_confidence_citations: bool = True
    ):
        """Initialize claim validator.

        Args:
            confidence_threshold: Flag claims with confidence above this
            require_low_confidence_citations: Require citations for unverifiable
        """
        self.confidence_threshold = confidence_threshold
        self.require_low_confidence_citations = require_low_confidence_citations
        self.logger = logging.getLogger(__name__)

    def extract_claims(self, text: str) -> List[str]:
        """Extract individual claims from text.

        Splits on sentence boundaries and returns main claims.

        Args:
            text: Text to extract claims from

        Returns:
            List of claim strings
        """
        # Simple sentence splitting (can be improved with better NLP)
        sentences = re.split(r'[.!?]+', text.strip())
        claims = [s.strip() for s in sentences if len(s.strip()) > 10]
        return claims

    def classify_claim(self, claim_text: str) -> ClaimType:
        """Classify type of claim.

        Args:
            claim_text: Claim to classify

        Returns:
            ClaimType classification
        """
        claim_lower = claim_text.lower()

        # Check for explicit uncertainty markers
        if re.search(r'\b(?:I |may|might|possibly|allegedly|reportedly|supposedly)\b', claim_lower):
            return ClaimType.UNCERTAINTY

        # Check for opinions
        if re.search('|'.join(self.OPINION_PATTERNS), claim_lower):
            return ClaimType.OPINION

        # Check for hypothetical
        if re.search(r'\bif\b.*\bthen\b', claim_lower):
            return ClaimType.HYPOTHETICAL

        # Check for hearsay
        if re.search(r'\b(?:according to|says|claimed|reported that|sources say)\b', claim_lower):
            return ClaimType.HEARSAY

        # Default to fact for concrete claims
        return ClaimType.FACT

    def assess_verifiability(self, claim_text: str) -> VerifiabilityScore:
        """Assess how verifiable a claim is.

        Args:
            claim_text: Claim to assess

        Returns:
            VerifiabilityScore assessment
        """
        claim_lower = claim_text.lower()

        # Unfalsifiable claims
        if re.search(r'\b(?:in the future|eventually|always|never)\b', claim_lower):
            if len(claim_text.split()) < 5:
                return VerifiabilityScore.IMPOSSIBLE

        # High verifiability: specific facts
        fact_count = sum(1 for pattern in self.FACT_PATTERNS if re.search(pattern, claim_text))
        if fact_count >= 2:
            return VerifiabilityScore.HIGH

        # Medium verifiability: named entities, specific claims
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim_text):
            return VerifiabilityScore.MEDIUM

        # Low verifiability: vague, general claims
        if len(claim_text.split()) < 10 or re.search(r'\b(?:thing|stuff|some|many|lots?)\b', claim_lower):
            return VerifiabilityScore.LOW

        return VerifiabilityScore.MEDIUM

    def validate_claim(
        self,
        claim_text: str,
        stated_confidence: float = 0.5,
        known_facts: Optional[Dict[str, Any]] = None
    ) -> ValidatedClaim:
        """Validate a single claim.

        Args:
            claim_text: Claim to validate
            stated_confidence: Model's confidence in this claim (0.0-1.0)
            known_facts: Dictionary of known facts to check against

        Returns:
            ValidatedClaim with validation results
        """
        if not (0.0 <= stated_confidence <= 1.0):
            stated_confidence = 0.5

        claim_type = self.classify_claim(claim_text)
        verifiability = self.assess_verifiability(claim_text)

        # Check confidence-verifiability alignment
        confidence_justified = self._is_confidence_justified(
            stated_confidence, verifiability, claim_type
        )

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            stated_confidence,
            verifiability,
            claim_type,
            confidence_justified
        )

        # Determine if citation is needed
        requires_citation = (
            verifiability in [VerifiabilityScore.MEDIUM, VerifiabilityScore.HIGH] or
            (self.require_low_confidence_citations and verifiability == VerifiabilityScore.LOW)
        )

        # Generate warnings and suggestions
        warnings, suggestions = self._generate_feedback(
            claim_text, claim_type, verifiability, risk_score, confidence_justified
        )

        return ValidatedClaim(
            claim_text=claim_text,
            claim_type=claim_type,
            verifiability=verifiability,
            confidence=stated_confidence,
            confidence_justified=confidence_justified,
            requires_citation=requires_citation,
            risk_score=risk_score,
            warnings=warnings,
            suggestions=suggestions
        )

    @staticmethod
    def _is_confidence_justified(
        confidence: float,
        verifiability: VerifiabilityScore,
        claim_type: ClaimType
    ) -> bool:
        """Check if stated confidence matches claim characteristics.

        Args:
            confidence: Stated confidence (0-1)
            verifiability: Verifiability assessment
            claim_type: Type of claim

        Returns:
            True if confidence seems justified
        """
        # Low confidence always justified
        if confidence < 0.5:
            return True

        # Opinions shouldn't have high confidence
        if claim_type == ClaimType.OPINION and confidence > 0.7:
            return False

        # Uncertain claims shouldn't have high confidence
        if claim_type == ClaimType.UNCERTAINTY and confidence > 0.6:
            return False

        # Low verifiability + high confidence = red flag
        if verifiability == VerifiabilityScore.LOW and confidence > 0.8:
            return False

        if verifiability == VerifiabilityScore.IMPOSSIBLE and confidence > 0.3:
            return False

        return True

    @staticmethod
    def _calculate_risk_score(
        confidence: float,
        verifiability: VerifiabilityScore,
        claim_type: ClaimType,
        confidence_justified: bool
    ) -> float:
        """Calculate hallucination risk score (0=safe, 1=high risk).

        Args:
            confidence: Stated confidence
            verifiability: Verifiability assessment
            claim_type: Type of claim
            confidence_justified: Is confidence appropriate?

        Returns:
            Risk score 0.0-1.0
        """
        risk = 0.0

        # Base risk from verifiability
        verifiability_risks = {
            VerifiabilityScore.HIGH: 0.1,
            VerifiabilityScore.MEDIUM: 0.3,
            VerifiabilityScore.LOW: 0.6,
            VerifiabilityScore.IMPOSSIBLE: 0.9
        }
        risk += verifiability_risks.get(verifiability, 0.5)

        # Increase risk if confidence unjustified
        if not confidence_justified:
            risk += 0.3

        # Increase risk for types that tend to hallucinate
        type_risks = {
            ClaimType.FACT: 0.0,
            ClaimType.OPINION: 0.1,
            ClaimType.HYPOTHETICAL: 0.2,
            ClaimType.HEARSAY: 0.3,
            ClaimType.UNCERTAINTY: -0.2  # Actually lowers risk
        }
        risk += type_risks.get(claim_type, 0.0)

        # Cap at 1.0
        return min(1.0, max(0.0, risk))

    @staticmethod
    def _generate_feedback(
        claim_text: str,
        claim_type: ClaimType,
        verifiability: VerifiabilityScore,
        risk_score: float,
        confidence_justified: bool
    ) -> Tuple[List[str], List[str]]:
        """Generate warnings and suggestions for claim.

        Args:
            claim_text: The claim
            claim_type: Type of claim
            verifiability: Verifiability assessment
            risk_score: Calculated risk score
            confidence_justified: Is confidence appropriate?

        Returns:
            (warnings list, suggestions list)
        """
        warnings = []
        suggestions = []

        # Risk-based warnings
        if risk_score > 0.7:
            warnings.append(f"HIGH hallucination risk ({risk_score:.1%})")
        elif risk_score > 0.4:
            warnings.append(f"MEDIUM hallucination risk ({risk_score:.1%})")

        # Verifiability warnings
        if verifiability == VerifiabilityScore.IMPOSSIBLE:
            warnings.append("Claim is unfalsifiable")
            suggestions.append("Rephrase to make claim falsifiable")

        if verifiability == VerifiabilityScore.LOW:
            warnings.append("Claim lacks specificity")
            suggestions.append("Add specific details, dates, or names")

        # Confidence warnings
        if not confidence_justified:
            warnings.append("Confidence doesn't match claim characteristics")
            suggestions.append("Lower confidence or increase claim specificity")

        # Type-specific suggestions
        if claim_type == ClaimType.HEARSAY:
            suggestions.append("Include citation for reported information")

        if claim_type == ClaimType.OPINION:
            suggestions.append("Frame as opinion rather than fact")

        return warnings, suggestions

    def validate_text(self, text: str, confidences: Optional[List[float]] = None) -> List[ValidatedClaim]:
        """Validate all claims in text.

        Args:
            text: Text containing multiple claims
            confidences: Optional list of confidence scores per claim

        Returns:
            List of ValidatedClaim objects
        """
        claims = self.extract_claims(text)

        if confidences is None:
            confidences = [0.5] * len(claims)

        results = []
        for claim, confidence in zip(claims, confidences):
            validated = self.validate_claim(claim, confidence)
            results.append(validated)

        return results
