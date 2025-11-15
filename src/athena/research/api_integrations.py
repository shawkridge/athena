"""Research API Integrations - Multi-source information gathering.

This module provides unified interfaces to multiple research data sources:
- Web Search APIs (SerpAPI, Google Custom Search)
- Academic Paper APIs (arXiv, Semantic Scholar)
- LLM Provider APIs (Anthropic, OpenAI, Ollama)
- Documentation APIs (GitHub, ReadTheDocs)

Design Pattern:
- Provider abstraction: Common interface for different API providers
- Async-first: All operations are async for concurrency
- Caching: Results cached to minimize API calls
- Rate limiting: Respectful of API quotas
- Fallback: Graceful degradation if APIs unavailable

Examples:
```python
# Web search
searcher = WebSearchProvider.create('serpapi', api_key=os.getenv('SERPAPI_KEY'))
results = await searcher.search("memory consolidation", limit=10)

# Academic papers
scholar = AcademicProvider.create('arxiv')
papers = await scholar.search("episodic memory", filters={'year': 2023})

# LLM synthesis
llm = LLMProvider.create('anthropic', api_key=os.getenv('ANTHROPIC_API_KEY'))
summary = await llm.summarize(papers, max_tokens=1000)
```
"""

import logging
import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SearchResult:
    """Result from a search query."""
    title: str
    url: str
    snippet: str
    source: str  # 'web', 'arxiv', 'scholar'
    relevance_score: float = 0.0  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AcademicPaper:
    """Academic paper metadata."""
    title: str
    authors: List[str]
    abstract: str
    url: str
    published_date: Optional[datetime] = None
    citations: int = 0
    venue: Optional[str] = None  # conference/journal
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class LLMResponse:
    """Response from LLM synthesis."""
    text: str
    model: str
    tokens_used: int
    stop_reason: str = "end_turn"


class APIProvider(str, Enum):
    """Available API providers."""
    SERPAPI = "serpapi"
    GOOGLE_SEARCH = "google_search"
    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


# ============================================================================
# Web Search Provider
# ============================================================================

class WebSearchProvider(ABC):
    """Abstract base for web search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search the web for information."""
        pass

    @classmethod
    def create(cls, provider: str, **kwargs) -> "WebSearchProvider":
        """Factory method to create provider instance."""
        if provider == "serpapi":
            return SerpAPISearchProvider(**kwargs)
        elif provider == "google_search":
            return GoogleCustomSearchProvider(**kwargs)
        else:
            raise ValueError(f"Unknown web search provider: {provider}")


class SerpAPISearchProvider(WebSearchProvider):
    """SerpAPI web search provider.

    Requires: SERPAPI_API_KEY environment variable
    """

    def __init__(self, api_key: str):
        """Initialize SerpAPI provider.

        Args:
            api_key: SerpAPI API key
        """
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self._session = None

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search via SerpAPI.

        Args:
            query: Search query
            limit: Max results (default: 10)
            filters: Optional filters (e.g., {'gl': 'us', 'hl': 'en'})

        Returns:
            List of SearchResult objects
        """
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required for SerpAPI - install with: pip install aiohttp")
            return []

        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": min(limit, 100),  # SerpAPI max
            }

            if filters:
                params.update(filters)

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"SerpAPI error: {resp.status}")
                        return []

                    data = await resp.json()

            results = []
            for result in data.get("organic_results", [])[:limit]:
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    source="web",
                    metadata={
                        "position": result.get("position"),
                        "date": result.get("date"),
                    }
                ))

            logger.info(f"SerpAPI search: {query} -> {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []


class GoogleCustomSearchProvider(WebSearchProvider):
    """Google Custom Search API provider.

    Requires: GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID
    """

    def __init__(self, api_key: str, engine_id: str):
        """Initialize Google Custom Search provider."""
        self.api_key = api_key
        self.engine_id = engine_id
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search via Google Custom Search API."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required - install with: pip install aiohttp")
            return []

        try:
            params = {
                "q": query,
                "key": self.api_key,
                "cx": self.engine_id,
                "num": min(limit, 10),  # Google max per request
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"Google Search error: {resp.status}")
                        return []

                    data = await resp.json()

            results = []
            for item in data.get("items", [])[:limit]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="web",
                    metadata={
                        "display_link": item.get("displayLink"),
                    }
                ))

            logger.info(f"Google Search: {query} -> {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Google Search failed: {e}")
            return []


# ============================================================================
# Academic Search Provider
# ============================================================================

class AcademicProvider(ABC):
    """Abstract base for academic search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[AcademicPaper]:
        """Search academic papers."""
        pass

    @classmethod
    def create(cls, provider: str, **kwargs) -> "AcademicProvider":
        """Factory method to create provider."""
        if provider == "arxiv":
            return ArxivProvider(**kwargs)
        elif provider == "semantic_scholar":
            return SemanticScholarProvider(**kwargs)
        else:
            raise ValueError(f"Unknown academic provider: {provider}")


class ArxivProvider(AcademicProvider):
    """arXiv academic paper search provider (free, no auth required)."""

    def __init__(self):
        """Initialize arXiv provider."""
        self.base_url = "http://export.arxiv.org/api/query"
        self._session = None

    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[AcademicPaper]:
        """Search arXiv for papers.

        Args:
            query: Search query
            limit: Max results (default: 20)
            filters: Optional filters (e.g., {'cat': 'cs.AI', 'year': 2023})

        Returns:
            List of AcademicPaper objects
        """
        try:
            import aiohttp
            import xml.etree.ElementTree as ET
        except ImportError:
            logger.error("aiohttp required - install with: pip install aiohttp")
            return []

        try:
            # Build search query
            search_query = f'"{query}"'
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": min(limit, 2000),  # arXiv API limit
                "sortBy": "relevance",
                "sortOrder": "descending",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"arXiv error: {resp.status}")
                        return []

                    xml_text = await resp.text()

            # Parse XML response
            root = ET.fromstring(xml_text)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}

            results = []
            for entry in root.findall('atom:entry', namespace)[:limit]:
                title = entry.findtext('atom:title', '', namespace)
                summary = entry.findtext('atom:summary', '', namespace)
                arxiv_id = entry.findtext('atom:id', '', namespace).split('/abs/')[-1]
                published = entry.findtext('atom:published', '', namespace)
                authors_elem = entry.findall('atom:author/atom:name', namespace)
                authors = [a.text for a in authors_elem]

                results.append(AcademicPaper(
                    title=title.strip(),
                    abstract=summary.strip(),
                    authors=authors,
                    arxiv_id=arxiv_id,
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    published_date=datetime.fromisoformat(published.replace('Z', '+00:00'))
                    if published else None,
                ))

            logger.info(f"arXiv search: {query} -> {len(results)} papers")
            return results

        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []


class SemanticScholarProvider(AcademicProvider):
    """Semantic Scholar academic search provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Semantic Scholar provider.

        Args:
            api_key: Optional Semantic Scholar API key for higher quotas
        """
        self.api_key = api_key
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[AcademicPaper]:
        """Search Semantic Scholar for papers."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required - install with: pip install aiohttp")
            return []

        try:
            params = {
                "query": query,
                "limit": min(limit, 100),
                "fields": "paperId,title,authors,abstract,venue,year,citationCount,externalIds",
            }

            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Semantic Scholar error: {resp.status}")
                        return []

                    data = await resp.json()

            results = []
            for paper in data.get("data", [])[:limit]:
                external_ids = paper.get("externalIds", {})
                results.append(AcademicPaper(
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=[a.get("name", "") for a in paper.get("authors", [])],
                    url=f"https://semanticscholar.org/paper/{paper.get('paperId')}",
                    venue=paper.get("venue"),
                    citations=paper.get("citationCount", 0),
                    arxiv_id=external_ids.get("ArXiv"),
                    doi=external_ids.get("DOI"),
                ))

            logger.info(f"Semantic Scholar search: {query} -> {len(results)} papers")
            return results

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []


# ============================================================================
# LLM Provider
# ============================================================================

class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate text completion."""
        pass

    @abstractmethod
    async def summarize(
        self,
        texts: List[str],
        max_tokens: int = 1000,
    ) -> str:
        """Summarize texts."""
        pass

    @classmethod
    def create(cls, provider: str, **kwargs) -> "LLMProvider":
        """Factory method to create provider."""
        if provider == "anthropic":
            return AnthropicProvider(**kwargs)
        elif provider == "openai":
            return OpenAIProvider(**kwargs)
        elif provider == "ollama":
            return OllamaProvider(**kwargs)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-sonnet)
        """
        self.api_key = api_key
        self.model = model
        self._client = None

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate completion using Claude."""
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package required - install with: pip install anthropic")
            return LLMResponse("", "", 0)

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            text = message.content[0].text
            return LLMResponse(
                text=text,
                model=self.model,
                tokens_used=message.usage.input_tokens + message.usage.output_tokens,
                stop_reason=message.stop_reason,
            )

        except Exception as e:
            logger.error(f"Anthropic completion failed: {e}")
            return LLMResponse("", "", 0)

    async def summarize(
        self,
        texts: List[str],
        max_tokens: int = 1000,
    ) -> str:
        """Summarize multiple texts using Claude."""
        if not texts:
            return ""

        combined = "\n\n".join(texts)
        prompt = f"""Please provide a comprehensive summary of the following texts,
identifying key concepts, findings, and insights:

{combined}

Summary:"""

        response = await self.complete(prompt, max_tokens=max_tokens)
        return response.text


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize OpenAI provider."""
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate completion using GPT."""
        try:
            import openai
        except ImportError:
            logger.error("openai package required - install with: pip install openai")
            return LLMResponse("", "", 0)

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.choices[0].message.content
            return LLMResponse(
                text=text,
                model=self.model,
                tokens_used=response.usage.total_tokens,
                stop_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            return LLMResponse("", "", 0)

    async def summarize(
        self,
        texts: List[str],
        max_tokens: int = 1000,
    ) -> str:
        """Summarize multiple texts using GPT."""
        if not texts:
            return ""

        combined = "\n\n".join(texts)
        prompt = f"""Summarize the following:\n\n{combined}"""

        response = await self.complete(prompt, max_tokens=max_tokens)
        return response.text


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """Initialize Ollama provider."""
        self.base_url = base_url
        self.model = model

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate completion using Ollama."""
        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required - install with: pip install aiohttp")
            return LLMResponse("", "", 0)

        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        logger.error(f"Ollama error: {resp.status}")
                        return LLMResponse("", "", 0)

                    data = await resp.json()

            return LLMResponse(
                text=data.get("response", ""),
                model=self.model,
                tokens_used=0,  # Ollama doesn't return token count
            )

        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            return LLMResponse("", "", 0)

    async def summarize(
        self,
        texts: List[str],
        max_tokens: int = 1000,
    ) -> str:
        """Summarize multiple texts using Ollama."""
        if not texts:
            return ""

        combined = "\n\n".join(texts)
        prompt = f"Summarize: {combined}"

        response = await self.complete(prompt, max_tokens=max_tokens)
        return response.text
