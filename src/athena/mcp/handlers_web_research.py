"""MCP handlers for web research operations with real web API integration."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def register_web_research_tools(server):
    """Register web research tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    async def research_topic(
        topic: str,
        mode: str = "hybrid",
        use_real: bool = True,
        use_mock: bool = True,
        parallel: bool = True,
    ) -> dict:
        """Execute comprehensive research on a topic using multiple sources.

        Combines real web research (WebSearch, WebFetch) with mock agents for fallback.
        Useful for grounding decisions in reality per "teach AI to think like a senior engineer".

        Args:
            topic: Research topic (e.g., "Python async patterns", "React hooks best practices")
            mode: Research mode: "hybrid" (real+mock), "real_first" (real with mock fallback),
                  "mock_only" (demo/testing), or "offline" (mock only, no network)
            use_real: Include real web research agents
            use_mock: Include mock research agents for fallback
            parallel: Run agents in parallel for speed (default True)

        Returns:
            {
                "topic": str,
                "mode": str,
                "total_findings": int,
                "sources": {
                    "agent_name": [
                        {"title": str, "summary": str, "url": str, "credibility": float}
                    ]
                },
                "synthesis": {
                    "key_themes": [str],
                    "confidence": float,
                    "gaps": [str],
                    "recommendations": [str],
                }
            }
        """
        try:
            from ..research.research_orchestrator import (
                ResearchOrchestrator,
                ResearchMode,
            )

            # Validate mode
            try:
                research_mode = ResearchMode[mode.upper()]
            except KeyError:
                return {
                    "error": f"Invalid mode: {mode}. Must be one of: hybrid, real_first, mock_only, offline",
                    "topic": topic,
                }

            # Execute research
            orchestrator = ResearchOrchestrator(mode=research_mode)
            results = await orchestrator.research(
                topic,
                use_real=use_real,
                use_mock=use_mock,
                parallel=parallel,
            )

            # Calculate summary
            total_findings = sum(len(findings) for findings in results.values())
            high_credibility = sum(
                len([f for f in findings if f.get("credibility", 0) > 0.75])
                for findings in results.values()
            )

            # Extract themes and recommendations
            all_findings = [
                f for findings in results.values() for f in findings
            ]
            themes = list(set(
                word
                for f in all_findings
                for word in f.get("summary", "").lower().split()
                if len(word) > 5
            ))[:5]

            return {
                "topic": topic,
                "mode": mode,
                "total_findings": total_findings,
                "high_credibility_findings": high_credibility,
                "sources": results,
                "synthesis": {
                    "key_themes": themes,
                    "confidence": high_credibility / max(total_findings, 1),
                    "agent_count": len(results),
                    "orchestrator_stats": orchestrator.get_agent_stats(),
                },
            }

        except Exception as e:
            logger.error(f"Research failed: {e}")
            return {
                "error": f"Research execution failed: {str(e)}",
                "topic": topic,
            }

    @server.tool()
    async def research_library(
        library_name: str,
        research_type: str = "documentation",
    ) -> dict:
        """Research a specific library for documentation and best practices.

        Performs targeted research for a library's official docs, examples, and community patterns.

        Args:
            library_name: Name of library to research (e.g., "react", "pytest", "langchain")
            research_type: Type of research: "documentation", "examples", "best_practices",
                          "vulnerabilities", or "all"

        Returns:
            {
                "library": str,
                "research_type": str,
                "documentation": [findings],
                "examples": [findings],
                "best_practices": [findings],
                "vulnerabilities": [findings],
            }
        """
        try:
            from ..research.research_orchestrator import (
                ResearchOrchestrator,
                ResearchMode,
            )

            orchestrator = ResearchOrchestrator(mode=ResearchMode.HYBRID)

            # Perform targeted research
            research_queries = {
                "documentation": f"{library_name} official documentation",
                "examples": f"{library_name} code examples and tutorials",
                "best_practices": f"{library_name} best practices and patterns",
                "vulnerabilities": f"{library_name} security vulnerabilities CVE",
            }

            results = {}
            if research_type == "all":
                queries = research_queries
            elif research_type in research_queries:
                queries = {research_type: research_queries[research_type]}
            else:
                return {"error": f"Unknown research type: {research_type}"}

            # Execute research for each query type
            for query_type, query in queries.items():
                findings = await orchestrator.research(
                    query, use_real=True, use_mock=True, parallel=False
                )
                results[query_type] = findings

            return {
                "library": library_name,
                "research_type": research_type,
                **results,
            }

        except Exception as e:
            logger.error(f"Library research failed: {e}")
            return {
                "error": f"Library research failed: {str(e)}",
                "library": library_name,
            }

    @server.tool()
    async def research_pattern(
        pattern_name: str,
        context: str = "general",
    ) -> dict:
        """Research a design pattern, architecture pattern, or best practice.

        Finds implementations, discussions, and guidance on a specific pattern.

        Args:
            pattern_name: Name of pattern (e.g., "dependency injection", "event sourcing")
            context: Context for pattern ("web", "distributed", "async", "testing", "general")

        Returns:
            {
                "pattern": str,
                "context": str,
                "definition": str,
                "implementations": [findings],
                "best_practices": [findings],
                "pitfalls": [findings],
                "languages": [str],
            }
        """
        try:
            from ..research.research_orchestrator import ResearchOrchestrator

            orchestrator = ResearchOrchestrator()

            # Research the pattern comprehensively
            queries = [
                f"{pattern_name} design pattern {context}",
                f"{pattern_name} implementation examples",
                f"{pattern_name} best practices and pitfalls",
            ]

            all_findings = {}
            for query in queries:
                results = await orchestrator.research(query, parallel=True)
                all_findings.update(results)

            return {
                "pattern": pattern_name,
                "context": context,
                "findings": all_findings,
                "total_sources": len(all_findings),
                "confidence": sum(
                    len(findings) for findings in all_findings.values()
                ) / max(len(all_findings), 1),
            }

        except Exception as e:
            logger.error(f"Pattern research failed: {e}")
            return {
                "error": f"Pattern research failed: {str(e)}",
                "pattern": pattern_name,
            }

    @server.tool()
    async def get_research_agents() -> dict:
        """Get information about available research agents.

        Returns list of configured research agents (real and mock).

        Returns:
            {
                "available_agents": {
                    "web_agents": [str],
                    "mock_agents": [str],
                },
                "modes": [str],
                "status": str,
            }
        """
        try:
            from ..research.research_orchestrator import (
                ResearchOrchestrator,
                ResearchMode,
            )

            orchestrator = ResearchOrchestrator()
            stats = orchestrator.get_agent_stats()

            return {
                "available_agents": {
                    "web_agents": stats["web_agent_names"],
                    "mock_agents": stats["mock_agent_names"],
                },
                "agent_counts": {
                    "web": stats["web_agents_available"],
                    "mock": stats["mock_agents_available"],
                    "total": stats["total_agents"],
                },
                "modes": [mode.value for mode in ResearchMode],
                "current_mode": stats["mode"],
                "status": "ready" if stats["total_agents"] > 0 else "degraded",
            }

        except Exception as e:
            logger.error(f"Failed to get agent info: {e}")
            return {"error": str(e), "status": "error"}
