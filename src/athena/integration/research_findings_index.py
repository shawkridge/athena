"""Research Findings Indexing & Search Integration.

Makes research findings discoverable and searchable across memory layers:
- Extracts structured findings from research outputs
- Auto-tags findings for categorization
- Stores in semantic memory for searchability
- Maintains source attribution
- Indexes by domain, methodology, confidence
"""

import logging
import re
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class FindingType(str, Enum):
    """Classification of research findings."""

    FACTUAL = "factual"  # Empirical facts
    METHODOLOGICAL = "methodological"  # Method/approach insights
    PATTERN = "pattern"  # Identified patterns
    RECOMMENDATION = "recommendation"  # Recommended actions
    CONTRADICTION = "contradiction"  # Contradicts prior beliefs
    CONFIRMATION = "confirmation"  # Confirms prior beliefs
    NOVEL = "novel"  # New/unexpected finding


class ConfidenceLevel(str, Enum):
    """Confidence in finding."""

    HIGH = "high"  # Multiple sources, peer reviewed
    MEDIUM = "medium"  # Single high-quality source
    LOW = "low"  # Single source, needs verification


@dataclass
class Finding:
    """A single research finding."""

    id: Optional[str] = None
    statement: str = ""
    finding_type: FindingType = FindingType.FACTUAL
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    domain: str = ""  # Domain/topic area
    sources: List[str] = field(default_factory=list)
    supporting_evidence: Optional[str] = None
    contradicts_id: Optional[str] = None  # If contradiction
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: Set[str] = field(default_factory=set)
    related_findings: List[str] = field(default_factory=list)


@dataclass
class ResearchSession:
    """A research session with findings."""

    id: str
    topic: str
    findings: List[Finding] = field(default_factory=list)
    sources_consulted: List[str] = field(default_factory=list)
    methodology: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: str = ""


class ResearchFindingsIndexer:
    """Index and search research findings.

    Enables:
    - Finding extraction from research documents
    - Auto-tagging for categorization
    - Confidence assessment
    - Relationship tracking (contradictions, support)
    - Full-text search across findings

    Attributes:
        domain_keywords: Keywords for domain detection
        confidence_mapping: Maps indicators to confidence levels
    """

    # Common domain keywords for auto-tagging
    DOMAIN_KEYWORDS = {
        "machine-learning": ["machine learning", "neural", "deep learning", "algorithm", "model"],
        "security": ["security", "vulnerability", "attack", "encryption", "threat"],
        "performance": ["performance", "optimization", "latency", "throughput", "bottleneck"],
        "architecture": ["architecture", "design", "pattern", "structure", "component"],
        "testing": ["test", "testing", "unit test", "integration test", "coverage"],
        "documentation": ["documentation", "document", "spec", "specification", "guide"],
        "user-research": ["user", "usability", "user experience", "ux", "behavior"],
    }

    # Confidence indicators
    CONFIDENCE_INDICATORS = {
        "high": ["peer reviewed", "published", "verified", "rigorous", "multiple sources"],
        "medium": ["well-established", "authoritative", "reputable source"],
        "low": ["preliminary", "anecdotal", "unverified", "single source"],
    }

    def __init__(self):
        """Initialize research findings indexer."""
        self.logger = logging.getLogger(__name__)
        self._findings_index: Dict[str, Finding] = {}
        self._sessions: Dict[str, ResearchSession] = {}
        self._domain_index: Dict[str, List[str]] = {}  # domain -> finding IDs

    def extract_findings(
        self, text: str, research_topic: str = "", sources: Optional[List[str]] = None
    ) -> List[Finding]:
        """Extract findings from research text.

        Looks for patterns like:
        - Bullet points starting with "Finding:"
        - Numbered findings
        - Sections marked as "Results" or "Findings"

        Args:
            text: Research text/document
            research_topic: Topic of research
            sources: List of source URLs/citations

        Returns:
            List of extracted Finding objects
        """
        findings = []
        sources = sources or []

        # Pattern 1: Explicit "Finding:" markers
        for match in re.finditer(r"(?:Finding|Result):\s*([^\n.!?]+[.!?])", text, re.IGNORECASE):
            statement = match.group(1).strip()
            finding = Finding(
                statement=statement,
                finding_type=FindingType.FACTUAL,
                domain=self._detect_domain(statement),
                sources=sources,
                tags=self._generate_tags(statement),
            )
            findings.append(finding)

        # Pattern 2: Numbered findings
        for match in re.finditer(r"^\d+\.\s+([^\n]+)$", text, re.MULTILINE):
            statement = match.group(1).strip()
            if len(statement) > 10:  # Avoid trivial matches
                finding = Finding(
                    statement=statement,
                    finding_type=self._classify_finding(statement),
                    domain=self._detect_domain(statement),
                    sources=sources,
                    tags=self._generate_tags(statement),
                )
                findings.append(finding)

        # Pattern 3: Quoted sections
        for match in re.finditer(r'"([^"]{20,})"', text):
            statement = match.group(1).strip()
            if not any(f.statement == statement for f in findings):
                finding = Finding(
                    statement=statement,
                    finding_type=FindingType.FACTUAL,
                    domain=self._detect_domain(statement),
                    sources=sources,
                    tags=self._generate_tags(statement),
                )
                findings.append(finding)

        # Auto-generate IDs if not present
        for i, finding in enumerate(findings):
            if not finding.id:
                finding.id = f"finding_{datetime.now().timestamp()}_{i}"

        self.logger.info(f"Extracted {len(findings)} findings from research")
        return findings

    def _detect_domain(self, statement: str) -> str:
        """Detect domain from statement text.

        Args:
            statement: Finding statement

        Returns:
            Detected domain or empty string
        """
        statement_lower = statement.lower()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(keyword in statement_lower for keyword in keywords):
                return domain

        return "general"

    def _classify_finding(self, statement: str) -> FindingType:
        """Classify finding type.

        Args:
            statement: Finding statement

        Returns:
            FindingType classification
        """
        statement_lower = statement.lower()

        # Check for specific patterns
        if re.search(r"\b(?:recommends?|should|must|needs?)\b", statement_lower):
            return FindingType.RECOMMENDATION
        elif re.search(r"\b(?:contradicts?|conflicts?|differs?|opposite)\b", statement_lower):
            return FindingType.CONTRADICTION
        elif re.search(r"\b(?:confirms?|validates?|supports?|consistent)\b", statement_lower):
            return FindingType.CONFIRMATION
        elif re.search(r"\b(?:surprisingly|unexpected|novel|first time)\b", statement_lower):
            return FindingType.NOVEL
        elif re.search(r"\b(?:method|approach|technique|process)\b", statement_lower):
            return FindingType.METHODOLOGICAL
        elif re.search(r"\b(?:pattern|trend|correlation|relationship)\b", statement_lower):
            return FindingType.PATTERN

        return FindingType.FACTUAL

    def _assess_confidence(self, statement: str, sources: List[str]) -> ConfidenceLevel:
        """Assess confidence level of finding.

        Args:
            statement: Finding statement
            sources: List of sources

        Returns:
            ConfidenceLevel assessment
        """
        statement_lower = statement.lower()

        # Multiple high-quality sources = high confidence
        if len(sources) >= 2:
            return ConfidenceLevel.HIGH

        # Explicit confidence indicators
        for indicator in self.CONFIDENCE_INDICATORS["high"]:
            if indicator in statement_lower:
                return ConfidenceLevel.HIGH

        for indicator in self.CONFIDENCE_INDICATORS["low"]:
            if indicator in statement_lower:
                return ConfidenceLevel.LOW

        return ConfidenceLevel.MEDIUM

    def _generate_tags(self, statement: str) -> Set[str]:
        """Generate tags for finding.

        Args:
            statement: Finding statement

        Returns:
            Set of tags
        """
        tags = set()

        # Domain tags
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in statement.lower() for kw in keywords):
                tags.add(domain)

        # Type tags
        if re.search(r"\b(?:new|novel|unexpected)\b", statement.lower()):
            tags.add("novel")

        if re.search(r"\b(?:important|critical|significant)\b", statement.lower()):
            tags.add("important")

        if re.search(r"\b(?:warning|risk|danger)\b", statement.lower()):
            tags.add("warning")

        if re.search(r"\b(?:best practice|recommendation)\b", statement.lower()):
            tags.add("best-practice")

        # Length tag
        if len(statement.split()) < 15:
            tags.add("concise")
        else:
            tags.add("detailed")

        return tags

    def index_findings(self, findings: List[Finding], session_id: str = "") -> None:
        """Index findings for search.

        Args:
            findings: List of findings to index
            session_id: Associated session ID
        """
        for finding in findings:
            if not finding.id:
                finding.id = f"finding_{len(self._findings_index)}"

            self._findings_index[finding.id] = finding

            # Index by domain
            if finding.domain:
                if finding.domain not in self._domain_index:
                    self._domain_index[finding.domain] = []
                self._domain_index[finding.domain].append(finding.id)

        self.logger.info(f"Indexed {len(findings)} findings")

    def search_findings(
        self,
        query: str,
        domain: Optional[str] = None,
        confidence: Optional[ConfidenceLevel] = None,
        finding_type: Optional[FindingType] = None,
    ) -> List[Finding]:
        """Search findings by query and filters.

        Args:
            query: Search query (full-text)
            domain: Filter by domain
            confidence: Filter by confidence level
            finding_type: Filter by finding type

        Returns:
            List of matching findings
        """
        query_lower = query.lower()
        results = []

        for finding in self._findings_index.values():
            # Check domain filter
            if domain and finding.domain != domain:
                continue

            # Check confidence filter
            if confidence and finding.confidence != confidence:
                continue

            # Check type filter
            if finding_type and finding.finding_type != finding_type:
                continue

            # Check query match
            if query_lower in finding.statement.lower():
                results.append(finding)

        return sorted(
            results,
            key=lambda f: (
                f.confidence != ConfidenceLevel.HIGH,  # High confidence first
                -len(f.sources),  # More sources better
            ),
        )

    def get_findings_by_domain(self, domain: str) -> List[Finding]:
        """Get all findings for a domain.

        Args:
            domain: Domain/topic

        Returns:
            List of findings
        """
        finding_ids = self._domain_index.get(domain, [])
        return [self._findings_index[fid] for fid in finding_ids if fid in self._findings_index]

    def create_session(self, topic: str, findings: List[Finding] = None) -> ResearchSession:
        """Create a research session with findings.

        Args:
            topic: Research topic
            findings: List of findings

        Returns:
            Created ResearchSession
        """
        session_id = f"session_{datetime.now().timestamp()}"
        session = ResearchSession(id=session_id, topic=topic, findings=findings or [])

        self._sessions[session_id] = session

        # Index findings
        if findings:
            self.index_findings(findings, session_id)

        return session

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about indexed findings.

        Returns:
            Dictionary with stats
        """
        findings_by_type = {}
        findings_by_domain = {}

        for finding in self._findings_index.values():
            # Count by type
            type_key = finding.finding_type.value
            findings_by_type[type_key] = findings_by_type.get(type_key, 0) + 1

            # Count by domain
            domain_key = finding.domain or "unknown"
            findings_by_domain[domain_key] = findings_by_domain.get(domain_key, 0) + 1

        confidence_counts = {}
        for conf in ConfidenceLevel:
            count = sum(1 for f in self._findings_index.values() if f.confidence == conf)
            confidence_counts[conf.value] = count

        return {
            "total_findings": len(self._findings_index),
            "total_sessions": len(self._sessions),
            "findings_by_type": findings_by_type,
            "findings_by_domain": findings_by_domain,
            "findings_by_confidence": confidence_counts,
        }
