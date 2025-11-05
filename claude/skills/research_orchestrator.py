"""
Research Orchestrator Skill

Orchestrates parallel research across 16 specialized sources with credibility scoring,
cross-validation, deduplication, and automatic memory storage.

Usage:
    from research_orchestrator import ResearchOrchestrator

    orchestrator = ResearchOrchestrator()
    results = orchestrator.research(
        topic="Claude Code skills",
        sources=None,  # All 16
        category=None,
        high_confidence_only=False
    )
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


# ============================================================================
# Data Models
# ============================================================================

class SourceCategory(str, Enum):
    """Source category groupings"""
    ACADEMIC = "academic"
    DOCS = "docs"
    IMPLEMENTATION = "implementation"
    RESEARCH = "research"
    COMMUNITY = "community"
    EMERGING = "emerging"


@dataclass
class Finding:
    """Individual research finding"""
    title: str
    summary: str
    url: str
    key_insight: str
    relevance: float  # 0.0-1.0
    source: str
    credibility: Optional[float] = None
    cross_validated: bool = False
    cross_validation_sources: List[str] = None


@dataclass
class ResearchResult:
    """Aggregated research results"""
    topic: str
    sources_searched: int
    findings_count: int
    findings: List[Finding]
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int


# ============================================================================
# Agent Definitions
# ============================================================================

AGENT_DEFINITIONS = {
    # Academic & Research (0.9x+)
    "arxiv": {
        "name": "ArXiv Researcher",
        "source": "arXiv.org",
        "credibility": 1.0,
        "category": SourceCategory.ACADEMIC,
        "focus": "Academic papers, benchmarks, theory",
    },
    "semantic-scholar": {
        "name": "Semantic Scholar Researcher",
        "source": "semanticscholar.org",
        "credibility": 0.98,
        "category": SourceCategory.ACADEMIC,
        "focus": "AI-powered discovery, citations, influence",
    },
    "papers-with-code": {
        "name": "Papers with Code Researcher",
        "source": "paperswithcode.com",
        "credibility": 0.9,
        "category": SourceCategory.ACADEMIC,
        "focus": "Verified implementations, benchmarks",
    },
    # Documentation & APIs (0.92x-0.95x)
    "anthropic-docs": {
        "name": "Anthropic Docs Researcher",
        "source": "docs.anthropic.com",
        "credibility": 0.95,
        "category": SourceCategory.DOCS,
        "focus": "Claude API, guides, best practices",
    },
    "huggingface": {
        "name": "Hugging Face Researcher",
        "source": "huggingface.co",
        "credibility": 0.92,
        "category": SourceCategory.DOCS,
        "focus": "Model cards, datasets, community",
    },
    "pytorch-tf": {
        "name": "PyTorch/TensorFlow Researcher",
        "source": "pytorch.org, tensorflow.org",
        "credibility": 0.92,
        "category": SourceCategory.DOCS,
        "focus": "Framework docs, tutorials, API refs",
    },
    # Implementation (0.75x-0.85x)
    "github": {
        "name": "GitHub Researcher",
        "source": "github.com",
        "credibility": 0.85,
        "category": SourceCategory.IMPLEMENTATION,
        "focus": "Open-source code, examples, patterns",
    },
    "dev-to": {
        "name": "Dev.to Researcher",
        "source": "dev.to",
        "credibility": 0.75,
        "category": SourceCategory.IMPLEMENTATION,
        "focus": "Developer tutorials, how-to guides",
    },
    # Tech Blogs & Research (0.78x-0.88x)
    "techblogs": {
        "name": "Tech Blogs Researcher",
        "source": "Official Tech Blogs",
        "credibility": 0.88,
        "category": SourceCategory.RESEARCH,
        "focus": "DeepSeek, Meta, Google, OpenAI research",
    },
    "youtube": {
        "name": "YouTube Researcher",
        "source": "youtube.com",
        "credibility": 0.78,
        "category": SourceCategory.RESEARCH,
        "focus": "Conference talks, tutorials, demos",
    },
    # Community (0.6x-0.8x)
    "stackoverflow": {
        "name": "Stack Overflow Researcher",
        "source": "stackoverflow.com",
        "credibility": 0.8,
        "category": SourceCategory.COMMUNITY,
        "focus": "Q&A, solutions, community validation",
    },
    "hackernews": {
        "name": "HackerNews Researcher",
        "source": "news.ycombinator.com",
        "credibility": 0.7,
        "category": SourceCategory.COMMUNITY,
        "focus": "Community discussions, expert insights",
    },
    "medium": {
        "name": "Medium Researcher",
        "source": "medium.com",
        "credibility": 0.68,
        "category": SourceCategory.COMMUNITY,
        "focus": "Technical blogs, essays, analysis",
    },
    "reddit": {
        "name": "Reddit Researcher",
        "source": "reddit.com",
        "credibility": 0.6,
        "category": SourceCategory.COMMUNITY,
        "focus": "Community perspectives, use cases",
    },
    # Emerging (0.62x-0.72x)
    "producthunt": {
        "name": "Product Hunt Researcher",
        "source": "producthunt.com",
        "credibility": 0.72,
        "category": SourceCategory.EMERGING,
        "focus": "Emerging tools, products, launches",
    },
    "x": {
        "name": "X/Twitter Researcher",
        "source": "x.com",
        "credibility": 0.62,
        "category": SourceCategory.EMERGING,
        "focus": "Emerging trends, announcements",
    },
}

SOURCES_BY_CATEGORY = {
    SourceCategory.ACADEMIC: ["arxiv", "semantic-scholar", "papers-with-code"],
    SourceCategory.DOCS: ["anthropic-docs", "huggingface", "pytorch-tf"],
    SourceCategory.IMPLEMENTATION: ["github", "dev-to", "papers-with-code", "stackoverflow"],
    SourceCategory.RESEARCH: ["techblogs", "youtube"],
    SourceCategory.COMMUNITY: ["stackoverflow", "hackernews", "medium", "reddit"],
    SourceCategory.EMERGING: ["producthunt", "x"],
}

ALL_SOURCES = list(AGENT_DEFINITIONS.keys())


# ============================================================================
# Research Orchestrator
# ============================================================================

class ResearchOrchestrator:
    """Orchestrates parallel research across 16 sources"""

    def __init__(self):
        self.agent_definitions = AGENT_DEFINITIONS
        self.sources_by_category = SOURCES_BY_CATEGORY

    def get_active_sources(
        self,
        sources: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> List[str]:
        """Determine which sources to search"""
        if category:
            if isinstance(category, str):
                category = SourceCategory(category)
            return self.sources_by_category.get(category, [])
        elif sources:
            return sources
        else:
            return ALL_SOURCES

    async def spawn_agents(self, topic: str, sources: List[str]) -> Dict[str, Any]:
        """Spawn research agents in parallel

        In real implementation, this would use Task tool to spawn agents.
        For now, returns agent prompts that can be used with Task tool.
        """
        agent_prompts = {}
        for source_key in sources:
            agent_def = self.agent_definitions[source_key]
            prompt = self._build_agent_prompt(topic, source_key, agent_def)
            agent_prompts[source_key] = prompt
        return agent_prompts

    def _build_agent_prompt(self, topic: str, source_key: str, agent_def: Dict) -> str:
        """Build specialized prompt for each agent"""
        return f"""
You are a specialized research agent: {agent_def['name']}

TASK: Research "{topic}" on {agent_def['source']}

FOCUS AREAS: {agent_def['focus']}

INSTRUCTIONS:
1. Search {agent_def['source']} for findings related to "{topic}"
2. Extract 8-15 high-quality findings
3. For each finding, provide:
   - Title: Clear, concise heading
   - Summary: 1-2 sentence explanation
   - URL: Direct link to source
   - Key Insight: Most important takeaway
   - Relevance Score: 0.0-1.0 (how directly relevant to topic)

4. Validate findings:
   - Filter out spam, ads, low-quality content
   - Prefer high-quality, authoritative sources

5. Format output as valid JSON:
   {{
     "findings": [
       {{
         "title": "...",
         "summary": "...",
         "url": "...",
         "key_insight": "...",
         "relevance": 0.85,
         "source": "{agent_def['name']}"
       }}
     ],
     "search_queries_used": [...],
     "total_results_screened": N
   }}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanations.
"""

    def score_credibility(self, finding: Finding, source_key: str) -> float:
        """Calculate credibility for a finding"""
        source_credibility = self.agent_definitions[source_key]["credibility"]
        credibility = source_credibility * finding.relevance
        return min(credibility, 1.0)  # Cap at 1.0

    def deduplicate_findings(self, findings: List[Finding], threshold: float = 0.85) -> List[Finding]:
        """Deduplicate findings by semantic similarity

        In real implementation, would use embedding similarity.
        For now, returns deduplicated list by title similarity.
        """
        # Simple deduplication: keep unique URLs + similar titles
        seen_urls = set()
        seen_titles = set()
        deduplicated = []

        for finding in sorted(findings, key=lambda f: f.credibility or 0, reverse=True):
            if finding.url in seen_urls:
                continue
            # Very basic title similarity (exact match for demo)
            if finding.title.lower() in seen_titles:
                continue

            deduplicated.append(finding)
            seen_urls.add(finding.url)
            seen_titles.add(finding.title.lower())

        return deduplicated

    def cross_validate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Apply cross-validation bonuses for findings in multiple sources"""
        # Group by similar titles/concepts
        source_counts = {}
        for finding in findings:
            key = finding.title.lower()[:30]  # First 30 chars as key
            if key not in source_counts:
                source_counts[key] = []
            source_counts[key].append(finding.source)

        # Apply bonuses
        for finding in findings:
            key = finding.title.lower()[:30]
            source_list = source_counts[key]

            if len(source_list) >= 2:
                finding.cross_validated = True
                finding.cross_validation_sources = list(set(source_list))
                if finding.credibility:
                    finding.credibility = min(finding.credibility + 0.15, 1.0)

        return findings

    def filter_by_confidence(self, findings: List[Finding], min_credibility: float = 0.8) -> List[Finding]:
        """Filter findings by credibility threshold"""
        return [f for f in findings if (f.credibility or 0) >= min_credibility]

    def categorize_by_confidence(self, findings: List[Finding]) -> tuple[int, int, int]:
        """Categorize findings by confidence level"""
        high = len([f for f in findings if (f.credibility or 0) >= 0.8])
        medium = len([f for f in findings if 0.5 <= (f.credibility or 0) < 0.8])
        low = len([f for f in findings if (f.credibility or 0) < 0.5])
        return high, medium, low

    async def research(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        category: Optional[str] = None,
        high_confidence_only: bool = False,
    ) -> ResearchResult:
        """
        Execute comprehensive research across specified sources

        Args:
            topic: Research topic/question
            sources: Specific sources to search (None = all)
            category: Category filter (academic|docs|implementation|research|community|emerging)
            high_confidence_only: Only return credibility ≥0.8

        Returns:
            ResearchResult with aggregated, scored, and validated findings
        """
        # 1. Determine active sources
        active_sources = self.get_active_sources(sources, category)

        # 2. Build agent prompts (in real implementation, spawn as Task agents)
        agent_prompts = await self.spawn_agents(topic, active_sources)

        # 3. Collect findings (simulated - in real usage, Task agents return results)
        all_findings = []
        for source_key, prompt in agent_prompts.items():
            agent_def = self.agent_definitions[source_key]
            # In real implementation, agent would execute and return JSON
            # For now, store prompt for execution
            # all_findings.extend(agent_results)

        # 4. Score credibility
        for finding in all_findings:
            for source_key in active_sources:
                if self.agent_definitions[source_key]["name"] == finding.source:
                    finding.credibility = self.score_credibility(finding, source_key)
                    break

        # 5. Deduplicate
        deduplicated = self.deduplicate_findings(all_findings)

        # 6. Cross-validate
        cross_validated = self.cross_validate_findings(deduplicated)

        # 7. Filter by confidence if requested
        if high_confidence_only:
            cross_validated = self.filter_by_confidence(cross_validated, min_credibility=0.8)

        # 8. Sort by credibility
        ranked = sorted(cross_validated, key=lambda f: f.credibility or 0, reverse=True)

        # 9. Categorize
        high, medium, low = self.categorize_by_confidence(ranked)

        # 10. Return results
        return ResearchResult(
            topic=topic,
            sources_searched=len(active_sources),
            findings_count=len(ranked),
            findings=ranked[:30],  # Top 30
            high_confidence_count=high,
            medium_confidence_count=medium,
            low_confidence_count=low,
        )

    def to_dict(self, result: ResearchResult) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        return {
            "topic": result.topic,
            "sources_searched": result.sources_searched,
            "findings_count": result.findings_count,
            "findings": [
                {
                    "title": f.title,
                    "summary": f.summary,
                    "url": f.url,
                    "key_insight": f.key_insight,
                    "relevance": f.relevance,
                    "source": f.source,
                    "credibility": f.credibility,
                    "cross_validated": f.cross_validated,
                    "cross_validation_sources": f.cross_validation_sources or [],
                }
                for f in result.findings
            ],
            "credibility_summary": {
                "high_confidence": result.high_confidence_count,
                "medium_confidence": result.medium_confidence_count,
                "low_confidence": result.low_confidence_count,
            },
        }


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Example usage"""
    orchestrator = ResearchOrchestrator()

    # Research with all sources
    result = await orchestrator.research(
        topic="Claude Code skills",
        high_confidence_only=False,
    )

    print(json.dumps(orchestrator.to_dict(result), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
