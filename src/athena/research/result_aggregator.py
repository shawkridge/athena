"""Result Aggregator for Phase 3.2 - Real-time Result Synthesis.

Aggregates findings as research agents complete their work.
Supports streaming updates and progressive disclosure for Claude consumption.
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .models import ResearchFinding, ResearchFeedback, FeedbackType

logger = logging.getLogger(__name__)


@dataclass
class AggregatedResult:
    """Aggregated research findings with metadata."""
    task_id: int
    query: str
    findings: List[ResearchFinding] = field(default_factory=list)
    applied_feedback: List[ResearchFeedback] = field(default_factory=list)
    agent_contributions: Dict[str, int] = field(default_factory=dict)  # {agent: finding_count}
    quality_score: float = 0.0
    is_complete: bool = False
    last_updated: Optional[datetime] = None
    summary: str = ""

    def add_finding(self, finding: ResearchFinding, agent_name: str) -> None:
        """Add a finding from an agent."""
        if finding not in self.findings:
            self.findings.append(finding)
            self.agent_contributions[agent_name] = self.agent_contributions.get(agent_name, 0) + 1
            self.last_updated = datetime.utcnow()

    def add_feedback(self, feedback: ResearchFeedback) -> None:
        """Record applied feedback."""
        if feedback not in self.applied_feedback:
            self.applied_feedback.append(feedback)

    def filter_by_quality(self, threshold: float) -> List[ResearchFinding]:
        """Get findings above quality threshold."""
        return [f for f in self.findings if f.credibility_score >= threshold]

    def filter_by_source(self, sources: List[str]) -> List[ResearchFinding]:
        """Get findings from specific sources."""
        return [f for f in self.findings if f.source.lower() in [s.lower() for s in sources]]

    def exclude_sources(self, sources: List[str]) -> List[ResearchFinding]:
        """Get findings excluding specified sources."""
        excluded_lower = [s.lower() for s in sources]
        return [f for f in self.findings if f.source.lower() not in excluded_lower]

    def top_findings(self, limit: int = 10) -> List[ResearchFinding]:
        """Get top findings sorted by credibility."""
        sorted_findings = sorted(
            self.findings,
            key=lambda f: (f.credibility_score, f.created_at),
            reverse=True
        )
        return sorted_findings[:limit]

    def get_unique_sources(self) -> Set[str]:
        """Get unique sources in findings."""
        return {f.source for f in self.findings}

    def calculate_quality_score(self) -> float:
        """Calculate aggregate quality score from findings."""
        if not self.findings:
            return 0.0

        avg_score = sum(f.credibility_score for f in self.findings) / len(self.findings)
        self.quality_score = round(avg_score, 2)
        return self.quality_score


class ResultAggregator:
    """Aggregates findings from multiple research agents."""

    def __init__(self, task_id: int, query: str):
        """Initialize aggregator for a research task.

        Args:
            task_id: Research task ID
            query: Original research query
        """
        self.task_id = task_id
        self.query = query
        self.result = AggregatedResult(task_id=task_id, query=query)
        self.seen_urls: Set[str] = set()  # For deduplication

    def add_finding(self, finding: ResearchFinding, agent_name: str) -> bool:
        """Add a finding to aggregation.

        Deduplicates by URL if available.

        Args:
            finding: Finding to add
            agent_name: Name of agent that discovered it

        Returns:
            True if added, False if duplicate
        """
        # Deduplication by URL
        if finding.url:
            if finding.url in self.seen_urls:
                logger.debug(f"Skipping duplicate URL: {finding.url}")
                return False
            self.seen_urls.add(finding.url)

        # Add finding
        self.result.add_finding(finding, agent_name)
        self.result.calculate_quality_score()
        return True

    def add_feedback(self, feedback: ResearchFeedback) -> None:
        """Record applied feedback."""
        self.result.add_feedback(feedback)

    def mark_complete(self) -> None:
        """Mark aggregation as complete."""
        self.result.is_complete = True
        self.result.last_updated = datetime.utcnow()

    def get_results(
        self,
        quality_threshold: float = 0.5,
        excluded_sources: Optional[List[str]] = None,
        focused_sources: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict:
        """Get aggregated results with filtering.

        Args:
            quality_threshold: Min credibility score
            excluded_sources: Sources to exclude
            focused_sources: Sources to focus on
            limit: Max findings to return

        Returns:
            Dictionary with formatted results for Claude
        """
        # Apply filters
        findings = self.result.findings

        # Quality filtering
        findings = [f for f in findings if f.credibility_score >= quality_threshold]

        # Source filtering
        if excluded_sources:
            findings = self.result.exclude_sources(excluded_sources)

        if focused_sources:
            findings = self.result.filter_by_source(focused_sources)

        # Sort by quality
        findings = sorted(
            findings,
            key=lambda f: (f.credibility_score, f.created_at),
            reverse=True
        )[:limit]

        # Format findings
        formatted_findings = [
            {
                "source": f.source,
                "title": f.title,
                "summary": f.summary,
                "url": f.url,
                "credibility": f.credibility_score,
            }
            for f in findings
        ]

        return {
            "task_id": self.task_id,
            "query": self.query,
            "findings_count": len(self.result.findings),
            "quality_score": self.result.quality_score,
            "is_complete": self.result.is_complete,
            "agent_contributions": self.result.agent_contributions,
            "unique_sources": list(self.result.get_unique_sources()),
            "findings": formatted_findings,
            "summary": self._generate_summary(formatted_findings),
            "feedback_applied": len(self.result.applied_feedback),
        }

    def get_streaming_update(self, max_recent: int = 5) -> Dict:
        """Get recent findings for streaming update.

        Args:
            max_recent: Max recent findings to return

        Returns:
            Dictionary with latest findings for incremental updates
        """
        recent = sorted(
            self.result.findings,
            key=lambda f: f.created_at,
            reverse=True
        )[:max_recent]

        return {
            "task_id": self.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "new_findings": [
                {
                    "source": f.source,
                    "title": f.title,
                    "url": f.url,
                    "credibility": f.credibility_score,
                }
                for f in recent
            ],
            "total_findings": len(self.result.findings),
            "is_complete": self.result.is_complete,
        }

    def _generate_summary(self, findings: List[Dict]) -> str:
        """Generate text summary of findings."""
        if not findings:
            return "No findings yet."

        lines = []
        lines.append(f"Found {len(findings)} relevant result(s):")

        # Group by source
        by_source: Dict[str, List] = {}
        for f in findings:
            source = f["source"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(f)

        for source, source_findings in by_source.items():
            lines.append(f"\n**{source}** ({len(source_findings)} results)")
            for i, finding in enumerate(source_findings[:3], 1):  # Max 3 per source
                lines.append(f"{i}. {finding['title']}")
                if finding.get('url'):
                    lines.append(f"   {finding['url']}")

        if sum(len(v) for v in by_source.values()) > sum(len(v[:3]) for v in by_source.values()):
            lines.append("\n*(More results available on request)*")

        return "\n".join(lines)

    def export_for_claude(self) -> str:
        """Export results as formatted text for Claude consumption."""
        results = self.get_results()

        lines = []
        lines.append(f"# Research Results: {self.query}")
        lines.append("")

        if not results["findings"]:
            lines.append("No findings available yet.")
            return "\n".join(lines)

        lines.append(f"**Total Findings:** {results['findings_count']}")
        lines.append(f"**Quality Score:** {results['quality_score']:.2f}/1.0")
        lines.append(f"**Sources:** {', '.join(results['unique_sources'])}")
        lines.append("")

        lines.append("## Key Findings")
        lines.append("")

        for finding in results["findings"][:10]:
            lines.append(f"### {finding['title']}")
            lines.append(f"*Source:* {finding['source']} (credibility: {finding['credibility']:.1%})")
            lines.append(f"\n{finding['summary']}")
            if finding["url"]:
                lines.append(f"\n[Read more]({finding['url']})")
            lines.append("")

        if results["feedback_applied"] > 0:
            lines.append(f"*Note: {results['feedback_applied']} feedback refinements applied to this research*")

        return "\n".join(lines)


class StreamingResultCollector:
    """Collects streaming updates from research agents."""

    def __init__(self, aggregator: ResultAggregator):
        """Initialize collector.

        Args:
            aggregator: ResultAggregator to collect into
        """
        self.aggregator = aggregator
        self.updates: List[Dict] = []

    def record_update(self, findings: List[ResearchFinding], agent_name: str) -> None:
        """Record findings from an agent.

        Args:
            findings: List of findings from agent
            agent_name: Name of agent
        """
        added_count = 0
        for finding in findings:
            if self.aggregator.add_finding(finding, agent_name):
                added_count += 1

        self.updates.append({
            "agent": agent_name,
            "added": added_count,
            "timestamp": datetime.utcnow().isoformat(),
        })

        logger.info(f"Agent {agent_name} added {added_count} findings")

    def get_progress_summary(self) -> Dict:
        """Get progress summary across agents."""
        return {
            "total_findings": len(self.aggregator.result.findings),
            "agent_contributions": self.aggregator.result.agent_contributions,
            "is_complete": self.aggregator.result.is_complete,
            "updates": len(self.updates),
        }
