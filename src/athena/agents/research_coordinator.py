"""
Research Coordinator Agent

Autonomous agent for multi-source research synthesis and memory storage.
Orchestrates parallel source investigation, synthesis, and knowledge integration.
"""

import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ResearchPhase(Enum):
    """Research workflow phases"""
    PLANNING = "planning"
    SOURCE_IDENTIFICATION = "source_identification"
    PARALLEL_RESEARCH = "parallel_research"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    STORAGE = "storage"
    REPORTING = "reporting"


class SourceType(Enum):
    """Types of research sources"""
    DOCUMENTATION = "documentation"
    CODE = "code"
    ISSUE_TRACKER = "issue_tracker"
    DISCUSSION = "discussion"
    EXTERNAL_RESOURCE = "external_resource"
    MEMORY = "memory"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class FindingConfidence(Enum):
    """Confidence levels for findings"""
    CERTAIN = 0.95
    HIGH = 0.75
    MEDIUM = 0.60
    LOW = 0.40
    UNCERTAIN = 0.20


@dataclass
class ResearchSource:
    """A single research source"""
    source_id: str
    source_type: SourceType
    name: str
    url: Optional[str] = None
    relevance_score: float = 0.0
    content_preview: str = ""
    last_accessed: Optional[str] = None


@dataclass
class Finding:
    """A single research finding"""
    finding_id: str
    topic: str
    content: str
    source_ids: List[str] = field(default_factory=list)
    confidence: FindingConfidence = FindingConfidence.MEDIUM
    citations: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ResearchSynthesis:
    """Synthesized research findings"""
    synthesis_id: str
    topic: str
    summary: str
    key_findings: List[Finding] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    cross_references: List[str] = field(default_factory=list)


class ResearchCoordinator:
    """
    Autonomous agent for multi-source research coordination.

    Capabilities:
    - Identify relevant sources across project
    - Parallelize research across multiple sources
    - Synthesize findings from diverse sources
    - Validate findings through cross-referencing
    - Store results in semantic memory
    """

    def __init__(self, database, mcp_client):
        """Initialize research coordinator

        Args:
            database: Database connection for storage
            mcp_client: MCP client for tool operations
        """
        self.db = database
        self.mcp = mcp_client
        self.current_research: Optional[str] = None
        self.sources: Dict[str, ResearchSource] = {}
        self.findings: Dict[str, Finding] = {}
        self.syntheses: Dict[str, ResearchSynthesis] = {}
        self.research_history: List[Dict[str, Any]] = []

    async def research(self, query: str, depth: str = "medium") -> Dict[str, Any]:
        """
        Conduct comprehensive multi-source research.

        Args:
            query: Research question or topic
            depth: "quick", "medium", or "deep"

        Returns:
            Research result with findings and synthesis
        """
        result = {
            "query": query,
            "depth": depth,
            "success": False,
            "phases": {},
            "sources_used": [],
            "findings": [],
            "synthesis": None,
            "errors": []
        }

        try:
            # Phase 1: Planning
            plan = await self._plan_research(query, depth)
            result["phases"]["planning"] = plan

            # Phase 2: Source identification
            sources = await self._identify_sources(query, depth)
            result["sources_used"] = [
                {"source_id": s.source_id, "type": s.source_type.value, "name": s.name}
                for s in sources.values()
            ]
            self.sources.update(sources)

            # Phase 3: Parallel research (could be parallelized with asyncio.gather)
            findings = await self._conduct_parallel_research(query, sources, depth)
            result["findings"] = [
                {
                    "finding_id": f.finding_id,
                    "topic": f.topic,
                    "content": f.content[:200],  # Preview
                    "confidence": f.confidence.value,
                    "sources": f.source_ids
                }
                for f in findings.values()
            ]
            self.findings.update(findings)

            # Phase 4: Synthesis
            synthesis = await self._synthesize_findings(query, findings)
            result["synthesis"] = {
                "topic": synthesis.topic,
                "summary": synthesis.summary,
                "key_findings": len(synthesis.key_findings),
                "themes": synthesis.themes,
                "gaps": synthesis.gaps,
                "confidence": synthesis.confidence_score
            }
            self.syntheses[synthesis.synthesis_id] = synthesis

            # Phase 5: Validation
            validation = await self._validate_synthesis(synthesis, findings)
            result["validation"] = validation

            # Phase 6: Storage in memory
            storage_result = await self._store_research(synthesis, findings)
            result["storage"] = storage_result

            # Phase 7: Reporting
            report = await self._generate_report(synthesis, findings, validation)
            result["report"] = report

            result["success"] = True
            self.current_research = query
            self.research_history.append({
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "source_count": len(sources),
                "finding_count": len(findings),
                "confidence": synthesis.confidence_score
            })

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))
            result["error_type"] = type(e).__name__

        return result

    async def cross_project_research(self, query: str, project_sources: List[str]) -> Dict[str, Any]:
        """
        Research across multiple projects.

        Args:
            query: Research query
            project_sources: List of project identifiers

        Returns:
            Cross-project research result
        """
        result = {
            "query": query,
            "projects": project_sources,
            "success": False,
            "findings_by_project": {},
            "cross_project_patterns": [],
            "unified_synthesis": None,
            "errors": []
        }

        try:
            # Research each project in parallel
            project_findings = {}
            for project in project_sources:
                findings = await self._research_project(query, project)
                project_findings[project] = findings

            result["findings_by_project"] = {
                proj: {"count": len(findings), "topics": list(set(f.topic for f in findings.values()))}
                for proj, findings in project_findings.items()
            }

            # Identify cross-project patterns
            patterns = await self._identify_cross_project_patterns(project_findings)
            result["cross_project_patterns"] = patterns

            # Create unified synthesis
            all_findings = {}
            for findings in project_findings.values():
                all_findings.update(findings)

            unified = await self._synthesize_findings(query, all_findings)
            result["unified_synthesis"] = {
                "summary": unified.summary,
                "themes": unified.themes,
                "confidence": unified.confidence_score
            }

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        return result

    async def update_research(self, research_id: str, new_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update existing research with new findings.

        Args:
            research_id: ID of existing research
            new_findings: New findings to add

        Returns:
            Updated research result
        """
        result = {
            "research_id": research_id,
            "success": False,
            "new_findings_count": len(new_findings),
            "updated_synthesis": None,
            "errors": []
        }

        try:
            # Add new findings
            for finding_data in new_findings:
                finding = Finding(
                    finding_id=f"{research_id}_new_{len(self.findings)}",
                    topic=finding_data.get("topic", ""),
                    content=finding_data.get("content", ""),
                    source_ids=finding_data.get("sources", []),
                    confidence=FindingConfidence.MEDIUM
                )
                self.findings[finding.finding_id] = finding

            # Re-synthesize with new findings
            synthesis = await self._synthesize_findings(
                self.current_research or research_id,
                self.findings
            )
            result["updated_synthesis"] = {
                "summary": synthesis.summary,
                "confidence": synthesis.confidence_score
            }

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["errors"].append(str(e))

        return result

    # Private helper methods

    async def _plan_research(self, query: str, depth: str) -> Dict[str, Any]:
        """Plan research approach"""
        depth_config = {
            "quick": {"sources": 3, "time_limit": 300},
            "medium": {"sources": 7, "time_limit": 900},
            "deep": {"sources": 15, "time_limit": 3600}
        }

        config = depth_config.get(depth, depth_config["medium"])

        return {
            "query": query,
            "depth": depth,
            "target_sources": config["sources"],
            "time_limit_seconds": config["time_limit"],
            "phases": ["planning", "source_id", "research", "synthesis", "validation", "storage"]
        }

    async def _identify_sources(self, query: str, depth: str) -> Dict[str, ResearchSource]:
        """Identify relevant sources"""
        # In production, would call MCP to search across sources
        sources = {}

        # Example sources
        source_types = [SourceType.DOCUMENTATION, SourceType.CODE, SourceType.MEMORY]
        for i, source_type in enumerate(source_types):
            source = ResearchSource(
                source_id=f"src_{i}",
                source_type=source_type,
                name=f"Source {i} - {source_type.value}",
                relevance_score=0.8 - (i * 0.1),
                content_preview=f"Content related to {query}"
            )
            sources[source.source_id] = source

        return sources

    async def _conduct_parallel_research(
        self,
        query: str,
        sources: Dict[str, ResearchSource],
        depth: str
    ) -> Dict[str, Finding]:
        """Conduct research across all sources"""
        findings = {}

        for source in sources.values():
            # Call MCP to research source
            finding = Finding(
                finding_id=f"find_{len(findings)}",
                topic=query,
                content=f"Finding from {source.name}: {query} context",
                source_ids=[source.source_id],
                confidence=FindingConfidence(source.relevance_score)
            )
            findings[finding.finding_id] = finding

        return findings

    async def _synthesize_findings(
        self,
        query: str,
        findings: Dict[str, Finding]
    ) -> ResearchSynthesis:
        """Synthesize findings into unified knowledge"""
        themes = self._extract_themes(findings)
        gaps = self._identify_gaps(query, findings)
        recommendations = self._generate_recommendations(themes, gaps)

        # Calculate confidence
        confidences = [f.confidence.value for f in findings.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        synthesis = ResearchSynthesis(
            synthesis_id=f"synth_{len(self.syntheses)}",
            topic=query,
            summary=f"Comprehensive synthesis of {query} from {len(findings)} findings",
            key_findings=list(findings.values()),
            themes=themes,
            gaps=gaps,
            recommendations=recommendations,
            confidence_score=avg_confidence
        )

        return synthesis

    async def _validate_synthesis(
        self,
        synthesis: ResearchSynthesis,
        findings: Dict[str, Finding]
    ) -> Dict[str, Any]:
        """Validate synthesis against source findings"""
        validation = {
            "finding_coverage": len(synthesis.key_findings) / max(len(findings), 1),
            "contradiction_count": sum(len(f.contradictions) for f in findings.values()),
            "average_confidence": synthesis.confidence_score,
            "is_valid": synthesis.confidence_score >= 0.6
        }

        return validation

    async def _store_research(
        self,
        synthesis: ResearchSynthesis,
        findings: Dict[str, Finding]
    ) -> Dict[str, Any]:
        """Store research in semantic memory"""
        # Call MCP to store findings
        result = await self.mcp.call_operation(
            "memory_tools",
            "remember",
            {
                "content": synthesis.summary,
                "memory_type": "pattern",
                "tags": ["research", synthesis.topic] + synthesis.themes
            }
        )

        return {
            "stored": True,
            "memory_id": result.get("memory_id", None),
            "synthesis_id": synthesis.synthesis_id
        }

    async def _generate_report(
        self,
        synthesis: ResearchSynthesis,
        findings: Dict[str, Finding],
        validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate research report"""
        return {
            "topic": synthesis.topic,
            "summary": synthesis.summary,
            "findings_count": len(findings),
            "themes": synthesis.themes,
            "gaps_identified": synthesis.gaps,
            "recommendations": synthesis.recommendations,
            "validation_score": validation["average_confidence"],
            "is_validated": validation["is_valid"]
        }

    async def _research_project(self, query: str, project: str) -> Dict[str, Finding]:
        """Research a single project"""
        findings = {}

        finding = Finding(
            finding_id=f"proj_{project}_{query}",
            topic=query,
            content=f"Findings from {project} context",
            source_ids=[project],
            confidence=FindingConfidence.HIGH
        )
        findings[finding.finding_id] = finding

        return findings

    async def _identify_cross_project_patterns(
        self,
        project_findings: Dict[str, Dict[str, Finding]]
    ) -> List[str]:
        """Identify patterns appearing across projects"""
        patterns = []

        # Find common themes
        all_topics = []
        for findings in project_findings.values():
            all_topics.extend([f.topic for f in findings.values()])

        # Count occurrences
        from collections import Counter
        topic_counts = Counter(all_topics)
        patterns = [topic for topic, count in topic_counts.items() if count > 1]

        return patterns

    def _extract_themes(self, findings: Dict[str, Finding]) -> List[str]:
        """Extract themes from findings"""
        themes = set()

        for finding in findings.values():
            # Extract keywords from content
            words = finding.content.split()
            # Simple extraction - in production would use NLP
            for word in words[:5]:  # First 5 words
                if len(word) > 5:  # Only significant words
                    themes.add(word.lower())

        return list(themes)

    def _identify_gaps(self, query: str, findings: Dict[str, Finding]) -> List[str]:
        """Identify knowledge gaps"""
        gaps = []

        # Check for contradictions
        contradiction_count = sum(len(f.contradictions) for f in findings.values())
        if contradiction_count > 0:
            gaps.append(f"Found {contradiction_count} contradictions needing resolution")

        # Check confidence spread
        confidences = [f.confidence.value for f in findings.values()]
        if confidences and max(confidences) - min(confidences) > 0.5:
            gaps.append("High uncertainty variance between sources")

        # Check finding count
        if len(findings) < 3:
            gaps.append("Insufficient findings for comprehensive understanding")

        return gaps

    def _generate_recommendations(self, themes: List[str], gaps: List[str]) -> List[str]:
        """Generate recommendations based on synthesis"""
        recommendations = []

        if gaps:
            recommendations.append(f"Address {len(gaps)} identified knowledge gaps")

        if themes:
            recommendations.append(f"Explore deeper into {themes[0]} theme")

        recommendations.append("Schedule follow-up research in 2 weeks")

        return recommendations
