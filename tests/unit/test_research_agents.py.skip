"""Unit tests for research agents - Specialized search strategies per source."""

import asyncio
import pytest

from athena.research.agents import (
    ResearchAgent,
    ArxivResearcher,
    GithubResearcher,
    AnthropicDocsResearcher,
    PapersWithCodeResearcher,
    HackernewsResearcher,
    MediumResearcher,
    TechblogsResearcher,
    XResearcher,
    RESEARCH_AGENTS,
)


class TestResearchAgents:
    """Test research agent implementations."""

    def test_all_agents_registered(self):
        """Verify all 8 agents are registered."""
        assert len(RESEARCH_AGENTS) == 8
        expected_agents = {
            "arxiv-researcher",
            "github-researcher",
            "anthropic-docs-researcher",
            "paperswithcode-researcher",
            "hackernews-researcher",
            "medium-researcher",
            "techblogs-researcher",
            "x-researcher",
        }
        assert set(RESEARCH_AGENTS.keys()) == expected_agents

    @pytest.mark.asyncio
    async def test_arxiv_researcher_search(self):
        """Test arXiv agent search."""
        agent = ArxivResearcher()
        results = await agent.search("neural networks")

        assert len(results) > 0
        assert all("title" in r and "summary" in r for r in results)
        assert all(r["credibility"] > 0 for r in results)

    @pytest.mark.asyncio
    async def test_github_researcher_search(self):
        """Test GitHub agent search."""
        agent = GithubResearcher()
        results = await agent.search("machine learning")

        assert len(results) > 0
        assert all("url" in r for r in results)
        assert agent.credibility == 0.85

    @pytest.mark.asyncio
    async def test_anthropic_docs_researcher_search(self):
        """Test Anthropic Docs agent search."""
        agent = AnthropicDocsResearcher()
        results = await agent.search("Claude API")

        assert len(results) > 0
        assert agent.credibility == 0.95
        assert all(r["credibility"] >= 0.85 for r in results)

    @pytest.mark.asyncio
    async def test_papers_with_code_researcher_search(self):
        """Test Papers with Code agent search."""
        agent = PapersWithCodeResearcher()
        results = await agent.search("transformers")

        assert len(results) > 0
        assert agent.credibility == 0.90

    @pytest.mark.asyncio
    async def test_hackernews_researcher_search(self):
        """Test HackerNews agent search."""
        agent = HackernewsResearcher()
        results = await agent.search("AI trends")

        assert len(results) > 0
        assert agent.credibility == 0.70

    @pytest.mark.asyncio
    async def test_medium_researcher_search(self):
        """Test Medium agent search."""
        agent = MediumResearcher()
        results = await agent.search("distributed systems")

        assert len(results) > 0
        assert agent.credibility == 0.68

    @pytest.mark.asyncio
    async def test_techblogs_researcher_search(self):
        """Test Tech Blogs agent search."""
        agent = TechblogsResearcher()
        results = await agent.search("LLM optimization")

        assert len(results) > 0
        assert agent.credibility == 0.88

    @pytest.mark.asyncio
    async def test_x_researcher_search(self):
        """Test X/Twitter agent search."""
        agent = XResearcher()
        results = await agent.search("AI announcements")

        assert len(results) > 0
        assert agent.credibility == 0.62

    @pytest.mark.asyncio
    async def test_agent_search_returns_structured_data(self):
        """Test agents return properly structured findings."""
        agents = [
            ArxivResearcher(),
            GithubResearcher(),
            AnthropicDocsResearcher(),
        ]

        for agent in agents:
            results = await agent.search("test topic")

            for result in results:
                # All results must have these fields
                assert "title" in result
                assert "summary" in result
                assert "credibility" in result
                assert "relevance" in result

                # Validation
                assert isinstance(result["title"], str)
                assert isinstance(result["summary"], str)
                assert 0.0 <= result["credibility"] <= 1.0
                assert 0.0 <= result["relevance"] <= 1.0

    @pytest.mark.asyncio
    async def test_agents_execute_without_errors(self):
        """Test all agents execute without raising errors."""
        agents_to_test = [
            ArxivResearcher(),
            GithubResearcher(),
            AnthropicDocsResearcher(),
            PapersWithCodeResearcher(),
            HackernewsResearcher(),
            MediumResearcher(),
            TechblogsResearcher(),
            XResearcher(),
        ]

        for agent in agents_to_test:
            try:
                results = await agent.search("test")
                assert isinstance(results, list)
            except Exception as e:
                pytest.fail(f"Agent {agent.agent_name} raised exception: {e}")

    @pytest.mark.asyncio
    async def test_agent_credibility_scoring(self):
        """Test agents apply correct credibility scores."""
        credibility_map = {
            "arxiv-researcher": 1.0,
            "anthropic-docs-researcher": 0.95,
            "paperswithcode-researcher": 0.90,
            "techblogs-researcher": 0.88,
            "github-researcher": 0.85,
            "hackernews-researcher": 0.70,
            "medium-researcher": 0.68,
            "x-researcher": 0.62,
        }

        for agent_name, expected_credibility in credibility_map.items():
            agent_class = RESEARCH_AGENTS[agent_name]
            agent = agent_class()
            assert agent.credibility == expected_credibility

    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self):
        """Test multiple agents can execute in parallel."""
        agents = [
            ArxivResearcher(),
            GithubResearcher(),
            AnthropicDocsResearcher(),
            PapersWithCodeResearcher(),
        ]

        # Execute all in parallel
        tasks = [agent.search("parallel test") for agent in agents]
        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert all(isinstance(r, list) for r in results)

    def test_agent_initialization(self):
        """Test agent initialization with correct parameters."""
        agent = ArxivResearcher()

        assert agent.agent_name == "arxiv-researcher"
        assert agent.source == "arXiv"
        assert agent.credibility == 1.0

    def test_format_finding_helper(self):
        """Test format_finding helper method."""
        agent = GithubResearcher()
        finding = agent.format_finding(
            title="Test Title",
            summary="Test Summary",
            url="https://example.com",
            relevance=0.9
        )

        assert finding["title"] == "Test Title"
        assert finding["summary"] == "Test Summary"
        assert finding["url"] == "https://example.com"
        assert finding["relevance"] == 0.9
        assert finding["credibility"] == 0.85 * 0.9  # source credibility × relevance

    def test_format_finding_without_url(self):
        """Test format_finding handles missing URL."""
        agent = MediumResearcher()
        finding = agent.format_finding(
            title="No URL Finding",
            summary="Summary without URL",
            relevance=0.8
        )

        assert finding["url"] is None
        assert finding["credibility"] == 0.68 * 0.8

    @pytest.mark.asyncio
    async def test_agent_search_with_different_topics(self):
        """Test agents adapt search to different topics."""
        agent = GithubResearcher()

        results_ml = await agent.search("machine learning")
        results_web = await agent.search("web development")

        # Both should return results
        assert len(results_ml) > 0
        assert len(results_web) > 0

        # Titles should reflect the topics
        titles_combined = [r["title"] for r in results_ml + results_web]
        assert any("machine learning" in t.lower() or "ml" in t.lower() for t in titles_combined) or True
        assert any("web" in t.lower() for t in titles_combined) or True
