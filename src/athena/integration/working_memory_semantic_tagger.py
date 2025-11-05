"""Working Memory Semantic Tagging Integration.

Automatically analyzes working memory items and applies semantic tags
for better routing to consolidation layers.

Tags working memory by:
- Content type (code, documentation, concept, strategy, error)
- Domain (ml, security, performance, testing, architecture)
- Temporal association (recent, session-related, project-related)
- Consolidation target (semantic, procedural, episodic)
- Urgency (immediate, soon, later, archive)
"""

import logging
import re
from typing import Optional, Dict, Any, List, Set
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Semantic content types."""
    CODE = "code"
    DOCUMENTATION = "documentation"
    CONCEPT = "concept"
    STRATEGY = "strategy"
    ERROR = "error"
    PATTERN = "pattern"
    INSIGHT = "insight"
    TOOL = "tool"


class Domain(str, Enum):
    """Knowledge domains."""
    MACHINE_LEARNING = "machine-learning"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    WORKFLOW = "workflow"
    DEBUG = "debugging"


class ConsolidationTarget(str, Enum):
    """Where should this memory item be consolidated to?"""
    SEMANTIC = "semantic"  # General knowledge
    PROCEDURAL = "procedural"  # Reusable workflow
    EPISODIC = "episodic"  # Historical record
    PROSPECTIVE = "prospective"  # Future task
    GRAPH = "graph"  # Knowledge graph entity


class Urgency(str, Enum):
    """How urgent is consolidation?"""
    IMMEDIATE = "immediate"  # Consolidate now
    SOON = "soon"  # Within session
    LATER = "later"  # After session
    ARCHIVE = "archive"  # Can wait, low value


class SemanticTag:
    """Semantic tag for working memory item."""

    def __init__(
        self,
        content_type: ContentType,
        domain: Domain,
        consolidation_target: ConsolidationTarget,
        urgency: Urgency,
        custom_tags: Optional[Set[str]] = None,
        confidence: float = 0.5
    ):
        self.content_type = content_type
        self.domain = domain
        self.consolidation_target = consolidation_target
        self.urgency = urgency
        self.custom_tags = custom_tags or set()
        self.confidence = confidence  # How confident in tagging


class WorkingMemorySemanticTagger:
    """Analyze and tag working memory items with semantic information.

    Enables better routing of consolidation by understanding:
    - What type of content is in working memory
    - What domain it belongs to
    - Where it should consolidate to
    - How urgent consolidation is

    Attributes:
        domain_keywords: Patterns for domain detection
        content_patterns: Patterns for content type detection
    """

    # Domain detection patterns
    DOMAIN_PATTERNS = {
        Domain.MACHINE_LEARNING: [
            r'\b(?:neural|network|model|learning|algorithm|classifier|regression)\b',
            r'\b(?:train|epoch|gradient|tensor|embedding)\b'
        ],
        Domain.SECURITY: [
            r'\b(?:security|encrypt|hash|token|authentication|vulnerability)\b',
            r'\b(?:attack|threat|breach|exploit|permission)\b'
        ],
        Domain.PERFORMANCE: [
            r'\b(?:performance|optimize|latency|throughput|cache|memory)\b',
            r'\b(?:bottleneck|profile|benchmark|load)\b'
        ],
        Domain.TESTING: [
            r'\b(?:test|unit|integration|coverage|mock|assert)\b',
            r'\b(?:validate|verify|check|qa|bug)\b'
        ],
        Domain.ARCHITECTURE: [
            r'\b(?:architecture|design|pattern|component|module|interface)\b',
            r'\b(?:layer|service|dependency|coupling)\b'
        ]
    }

    # Content type detection patterns
    CONTENT_PATTERNS = {
        ContentType.CODE: [
            r'(?:^|\n)\s*(?:def|class|function|const|let|var|import)',
            r'(?:{|}|\(|\)|;|==|=>)',
            r'(?:```|<code>)'
        ],
        ContentType.ERROR: [
            r'\b(?:error|exception|failed|failure|traceback|stack trace)\b',
            r'\b(?:warning|deprecated|null|undefined)\b'
        ],
        ContentType.CONCEPT: [
            r'\b(?:concept|idea|theory|principle|framework|model)\b',
            r'\b(?:understand|explain|define|outline)\b'
        ],
        ContentType.STRATEGY: [
            r'\b(?:strategy|approach|method|technique|plan|process)\b',
            r'\b(?:implement|execute|follow|workflow)\b'
        ],
        ContentType.DOCUMENTATION: [
            r'\b(?:documentation|document|manual|guide|readme|spec)\b',
            r'(?:```|##+\s|\*\*)'
        ]
    }

    # Consolidation target routing rules
    CONSOLIDATION_RULES = {
        (ContentType.CODE, Domain.MACHINE_LEARNING): ConsolidationTarget.PROCEDURAL,
        (ContentType.ERROR, None): ConsolidationTarget.EPISODIC,
        (ContentType.CONCEPT, None): ConsolidationTarget.SEMANTIC,
        (ContentType.STRATEGY, None): ConsolidationTarget.PROCEDURAL,
        (ContentType.DOCUMENTATION, None): ConsolidationTarget.SEMANTIC,
    }

    def __init__(self):
        """Initialize semantic tagger."""
        self.logger = logging.getLogger(__name__)

    def analyze_item(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> SemanticTag:
        """Analyze working memory item and generate semantic tags.

        Args:
            content: Working memory item content
            metadata: Optional metadata (session_id, project_id, etc.)

        Returns:
            SemanticTag with all semantic information
        """
        metadata = metadata or {}

        # Detect content type
        content_type = self._detect_content_type(content)

        # Detect domain
        domain = self._detect_domain(content)

        # Determine consolidation target
        consolidation_target = self._determine_consolidation_target(content_type, domain)

        # Assess urgency
        urgency = self._assess_urgency(content_type, metadata)

        # Generate custom tags
        custom_tags = self._generate_custom_tags(content, content_type, domain)

        # Calculate overall confidence
        confidence = self._calculate_confidence(content, content_type, domain)

        tag = SemanticTag(
            content_type=content_type,
            domain=domain,
            consolidation_target=consolidation_target,
            urgency=urgency,
            custom_tags=custom_tags,
            confidence=confidence
        )

        self.logger.debug(
            f"Tagged WM item: {content_type.value} / {domain.value} "
            f"→ {consolidation_target.value} ({urgency.value})"
        )

        return tag

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect content type of working memory item.

        Args:
            content: Item content

        Returns:
            ContentType classification
        """
        content_lower = content.lower()

        for ctype, patterns in self.CONTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return ctype

        # Check for patterns
        if re.search(r'(?:pattern|trend|relationship|correlation)', content_lower):
            return ContentType.PATTERN

        # Check for insights
        if re.search(r'(?:insight|discover|find|learn|realize)', content_lower):
            return ContentType.INSIGHT

        # Default based on length
        if len(content) < 50:
            return ContentType.CONCEPT
        else:
            return ContentType.DOCUMENTATION

    def _detect_domain(self, content: str) -> Domain:
        """Detect domain/topic of working memory item.

        Args:
            content: Item content

        Returns:
            Domain classification
        """
        content_lower = content.lower()
        match_scores = {}

        for domain, patterns in self.DOMAIN_PATTERNS.items():
            matches = sum(1 for p in patterns if re.search(p, content_lower))
            if matches > 0:
                match_scores[domain] = matches

        if match_scores:
            return max(match_scores, key=match_scores.get)

        return Domain.ARCHITECTURE  # Default

    def _determine_consolidation_target(
        self,
        content_type: ContentType,
        domain: Domain
    ) -> ConsolidationTarget:
        """Determine where item should consolidate to.

        Args:
            content_type: Type of content
            domain: Domain/topic

        Returns:
            ConsolidationTarget destination
        """
        # Check specific rule
        rule_key = (content_type, domain)
        if rule_key in self.CONSOLIDATION_RULES:
            return self.CONSOLIDATION_RULES[rule_key]

        # Check content type rule
        rule_key = (content_type, None)
        if rule_key in self.CONSOLIDATION_RULES:
            return self.CONSOLIDATION_RULES[rule_key]

        # Default routing
        if content_type in [ContentType.CODE, ContentType.STRATEGY]:
            return ConsolidationTarget.PROCEDURAL
        elif content_type in [ContentType.ERROR]:
            return ConsolidationTarget.EPISODIC
        elif content_type in [ContentType.CONCEPT, ContentType.INSIGHT]:
            return ConsolidationTarget.SEMANTIC
        else:
            return ConsolidationTarget.SEMANTIC

    def _assess_urgency(self, content_type: ContentType, metadata: Dict[str, Any]) -> Urgency:
        """Assess how urgent consolidation is.

        Args:
            content_type: Type of content
            metadata: Metadata about item

        Returns:
            Urgency level
        """
        # Errors are immediate
        if content_type == ContentType.ERROR:
            return Urgency.IMMEDIATE

        # Strategies need consolidation soon
        if content_type == ContentType.STRATEGY:
            return Urgency.SOON

        # Recent/hot content
        if metadata.get('is_recent'):
            return Urgency.SOON

        # Default
        return Urgency.LATER

    @staticmethod
    def _generate_custom_tags(
        content: str,
        content_type: ContentType,
        domain: Domain
    ) -> Set[str]:
        """Generate custom tags for item.

        Args:
            content: Item content
            content_type: Content type
            domain: Domain

        Returns:
            Set of custom tags
        """
        tags = set()

        # Add domain and type tags
        tags.add(domain.value)
        tags.add(content_type.value)

        # Add length tags
        if len(content) < 50:
            tags.add('concise')
        elif len(content) > 500:
            tags.add('detailed')

        # Add urgency indicators
        if re.search(r'(?:critical|urgent|immediate|asap)', content, re.IGNORECASE):
            tags.add('urgent')

        if re.search(r'(?:important|significant|key)', content, re.IGNORECASE):
            tags.add('important')

        # Add source indicators
        if re.search(r'(?:research|study|paper)', content, re.IGNORECASE):
            tags.add('research-backed')

        if re.search(r'(?:best practice|industry standard)', content, re.IGNORECASE):
            tags.add('best-practice')

        return tags

    @staticmethod
    def _calculate_confidence(
        content: str,
        content_type: ContentType,
        domain: Domain
    ) -> float:
        """Calculate confidence of tagging.

        Args:
            content: Item content
            content_type: Detected content type
            domain: Detected domain

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.5

        # More specific types are more confident
        specific_types = [ContentType.CODE, ContentType.ERROR, ContentType.STRATEGY]
        if content_type in specific_types:
            confidence += 0.2

        # More specific domains are more confident
        if domain != Domain.ARCHITECTURE:  # Default
            confidence += 0.2

        # Longer content allows higher confidence
        if len(content) > 100:
            confidence += 0.1

        return min(1.0, confidence)

    def get_routing_recommendation(self, tag: SemanticTag) -> Dict[str, Any]:
        """Get consolidation routing recommendation.

        Args:
            tag: SemanticTag to route

        Returns:
            Routing recommendation with target and priority
        """
        priority = {
            Urgency.IMMEDIATE: 3,
            Urgency.SOON: 2,
            Urgency.LATER: 1,
            Urgency.ARCHIVE: 0
        }

        return {
            'target': tag.consolidation_target.value,
            'priority': priority[tag.urgency],
            'urgency': tag.urgency.value,
            'confidence': tag.confidence,
            'tags': list(tag.custom_tags),
            'domain': tag.domain.value,
            'content_type': tag.content_type.value
        }
