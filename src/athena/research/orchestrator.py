"""Research Agent Orchestrator - Autonomous multi-source research.

Coordinates research across multiple API providers with:
- Query planning and decomposition
- Parallel search across sources
- Result aggregation and deduplication
- Quality scoring and ranking
- Finding synthesis and insight extraction
- Memory integration for persistence
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .api_integrations import (
    WebSearchProvider,
    AcademicProvider,
    LLMProvider,
    SearchResult,
    AcademicPaper,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchQuery:
    """A research query with decomposition."""
    original_query: str
    sub_queries: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)  # e.g., ['ai', 'cognitive-science']


@dataclass
class ResearchResult:
    """Aggregated research result."""
    query: str
    web_results: List[SearchResult] = field(default_factory=list)
    academic_papers: List[AcademicPaper] = field(default_factory=list)
    synthesis: Optional[str] = None
    key_findings: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ResearchOrchestrator:
    """Orchestrates autonomous research across multiple sources.

    Usage:
    ```python
    orchestrator = ResearchOrchestrator(
        web_provider=SerpAPISearchProvider(api_key="..."),
        academic_provider=ArxivProvider(),
        llm_provider=AnthropicProvider(api_key="..."),
    )

    result = await orchestrator.research("memory consolidation in sleep")
    print(result.synthesis)
    print(f"Quality: {result.quality_score}")
    ```
    """

    def __init__(
        self,
        web_provider: Optional[WebSearchProvider] = None,
        academic_provider: Optional[AcademicProvider] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize orchestrator with providers.

        Args:
            web_provider: Web search provider (optional)
            academic_provider: Academic search provider (optional)
            llm_provider: LLM provider for synthesis (optional)
        """
        self.web_provider = web_provider
        self.academic_provider = academic_provider
        self.llm_provider = llm_provider

        # Caching
        self._result_cache: Dict[str, ResearchResult] = {}
        self._source_results: Dict[str, List[Any]] = {}

    async def research(
        self,
        query: str,
        decompose: bool = True,
        synthesize: bool = True,
        max_results: int = 30,
    ) -> ResearchResult:
        """Conduct multi-source research on a query.

        Args:
            query: Research query
            decompose: Break query into sub-queries (default: True)
            synthesize: Generate synthesis using LLM (default: True)
            max_results: Max total results to gather

        Returns:
            ResearchResult with aggregated findings
        """
        logger.info(f"Starting research on: {query}")

        # Check cache
        cache_key = f"{query}:{decompose}:{synthesize}"
        if cache_key in self._result_cache:
            logger.debug("Returning cached research result")
            return self._result_cache[cache_key]

        # Parse query
        parsed_query = await self._parse_query(query)

        # Decompose into sub-queries if enabled
        search_queries = [query]
        if decompose and parsed_query.sub_queries:
            search_queries = parsed_query.sub_queries

        # Parallel search across sources
        web_results = []
        academic_papers = []

        search_tasks = []

        # Search web
        if self.web_provider:
            for sq in search_queries[:3]:  # Limit sub-queries for API cost
                search_tasks.append(
                    self.web_provider.search(sq, limit=max_results // len(search_queries))
                )

        # Search academic
        if self.academic_provider:
            for sq in search_queries[:2]:
                search_tasks.append(
                    self.academic_provider.search(sq, limit=max_results // len(search_queries))
                )

        if search_tasks:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Search task failed: {result}")
                    continue

                if isinstance(result, list) and result:
                    if isinstance(result[0], SearchResult):
                        web_results.extend(result)
                    elif isinstance(result[0], AcademicPaper):
                        academic_papers.extend(result)

        # Deduplicate and score
        web_results = self._deduplicate_web_results(web_results)
        academic_papers = self._deduplicate_papers(academic_papers)

        # Synthesize findings if LLM available
        synthesis = None
        key_findings = []

        if synthesize and self.llm_provider:
            synthesis, key_findings = await self._synthesize_findings(
                query,
                web_results,
                academic_papers,
            )

        # Create result
        result = ResearchResult(
            query=query,
            web_results=web_results[:max_results // 2],
            academic_papers=academic_papers[:max_results // 2],
            synthesis=synthesis,
            key_findings=key_findings,
            quality_score=self._calculate_quality_score(
                len(web_results),
                len(academic_papers),
                synthesis is not None,
            ),
            sources_used=[
                p.__class__.__name__
                for p in [self.web_provider, self.academic_provider, self.llm_provider]
                if p is not None
            ],
        )

        # Cache result
        self._result_cache[cache_key] = result

        logger.info(
            f"Research complete: {len(web_results)} web + "
            f"{len(academic_papers)} papers"
        )

        return result

    async def _parse_query(self, query: str) -> ResearchQuery:
        """Parse query to extract structure."""
        parsed = ResearchQuery(original_query=query)

        # Simple keyword extraction
        words = query.lower().split()
        parsed.keywords = [w for w in words if len(w) > 3]

        # If LLM available, use it for better parsing
        if self.llm_provider:
            prompt = f"""Decompose this research query into 2-3 focused sub-queries:

Query: {query}

Provide sub-queries, one per line (without numbering):"""

            try:
                response = await self.llm_provider.complete(
                    prompt,
                    max_tokens=200,
                    temperature=0.5,
                )
                if response.text:
                    parsed.sub_queries = [
                        line.strip() for line in response.text.strip().split("\n")
                        if line.strip()
                    ]
            except Exception as e:
                logger.debug(f"Query decomposition failed: {e}")

        return parsed

    async def _synthesize_findings(
        self,
        query: str,
        web_results: List[SearchResult],
        papers: List[AcademicPaper],
    ) -> tuple[Optional[str], List[str]]:
        """Synthesize findings using LLM."""
        if not self.llm_provider:
            return None, []

        # Build synthesis prompt
        sources_text = "Web Results:\n"
        for r in web_results[:5]:  # Limit to top 5
            sources_text += f"- {r.title}: {r.snippet}\n"

        sources_text += "\nAcademic Papers:\n"
        for p in papers[:5]:
            sources_text += f"- {p.title} by {', '.join(p.authors[:2])}\n"

        prompt = f"""Based on these research sources, provide a synthesis of
key findings for the query: "{query}"

{sources_text}

Synthesis:"""

        try:
            response = await self.llm_provider.complete(
                prompt,
                max_tokens=1500,
                temperature=0.7,
            )

            synthesis = response.text

            # Extract key findings (simple heuristic)
            findings = [
                line.strip()
                for line in synthesis.split("\n")
                if line.strip().startswith(("-", "•", "*")) or len(line.strip()) > 50
            ][:5]

            return synthesis, findings

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return None, []

    def _deduplicate_web_results(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """Remove duplicate web results based on URL."""
        seen_urls = set()
        unique = []

        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique.append(result)

        return unique

    def _deduplicate_papers(
        self,
        papers: List[AcademicPaper],
    ) -> List[AcademicPaper]:
        """Remove duplicate papers based on title/ID."""
        seen = set()
        unique = []

        for paper in papers:
            key = (paper.title.lower(), paper.arxiv_id)
            if key not in seen:
                seen.add(key)
                unique.append(paper)

        return unique

    def _calculate_quality_score(
        self,
        web_count: int,
        paper_count: int,
        has_synthesis: bool,
    ) -> float:
        """Calculate quality score (0-1)."""
        score = 0.0

        # Source diversity
        if web_count > 0:
            score += min(0.3, web_count / 20)
        if paper_count > 0:
            score += min(0.3, paper_count / 20)

        # Synthesis bonus
        if has_synthesis:
            score += 0.4

        return min(1.0, score)

    def clear_cache(self) -> None:
        """Clear result cache."""
        self._result_cache.clear()
        logger.debug("Cleared research result cache")
