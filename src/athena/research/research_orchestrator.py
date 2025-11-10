"""Research orchestrator that combines mock and real web research agents with intelligent fallback."""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ResearchMode(Enum):
    """Research execution modes."""
    REAL_FIRST = "real_first"  # Try real APIs first, fallback to mock
    MOCK_ONLY = "mock_only"  # Use mock data for testing/demos
    HYBRID = "hybrid"  # Combine real and mock for comprehensive results
    OFFLINE = "offline"  # Mock only, with no network attempts


class ResearchOrchestrator:
    """Orchestrates research agents (real web + mock) with intelligent fallback."""

    def __init__(self, mode: ResearchMode = ResearchMode.HYBRID, timeout: int = 30):
        """Initialize research orchestrator.

        Args:
            mode: Research execution mode (real_first, mock_only, hybrid, offline)
            timeout: Timeout in seconds for web research operations
        """
        self.mode = mode
        self.timeout = timeout
        self.web_agents: Dict[str, Any] = {}
        self.mock_agents: Dict[str, Any] = {}
        self._init_agents()

    def _init_agents(self):
        """Initialize both real and mock research agents."""
        # Initialize real web research agents
        try:
            from .web_research import WEB_RESEARCH_AGENTS
            for agent_name, agent_class in WEB_RESEARCH_AGENTS.items():
                try:
                    self.web_agents[agent_name] = agent_class()
                except Exception as e:
                    logger.debug(f"Failed to initialize {agent_name}: {e}")

            logger.info(f"Initialized {len(self.web_agents)} web research agents")
        except ImportError:
            logger.warning("Web research agents not available")

        # Initialize mock research agents (always available)
        try:
            from .agents import RESEARCH_AGENTS
            for agent_name, agent_class in RESEARCH_AGENTS.items():
                try:
                    self.mock_agents[agent_name] = agent_class()
                except Exception as e:
                    logger.debug(f"Failed to initialize mock {agent_name}: {e}")

            logger.info(f"Initialized {len(self.mock_agents)} mock research agents")
        except ImportError:
            logger.warning("Mock research agents not available")

    async def research(
        self,
        topic: str,
        use_real: bool = True,
        use_mock: bool = False,
        parallel: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Execute research across agents with fallback support.

        Args:
            topic: Research topic
            use_real: Include real web research agents
            use_mock: Include mock research agents
            parallel: Run agents in parallel if True

        Returns:
            Dictionary mapping agent names to findings
        """
        results = {}

        # Determine which agents to use based on mode
        if self.mode == ResearchMode.MOCK_ONLY:
            agents_to_use = self.mock_agents
        elif self.mode == ResearchMode.OFFLINE:
            agents_to_use = self.mock_agents
        elif self.mode == ResearchMode.REAL_FIRST:
            agents_to_use = self.web_agents or self.mock_agents
        else:  # HYBRID
            agents_to_use = {**self.web_agents, **self.mock_agents}

        # Apply explicit flags
        if not use_real:
            agents_to_use = {
                k: v for k, v in agents_to_use.items()
                if k not in self.web_agents
            }
        if not use_mock and use_real:
            agents_to_use = {
                k: v for k, v in agents_to_use.items()
                if k in self.web_agents
            }

        if not agents_to_use:
            logger.warning(f"No research agents available for mode: {self.mode}")
            return {}

        # Execute research
        if parallel:
            results = await self._research_parallel(topic, agents_to_use)
        else:
            results = await self._research_sequential(topic, agents_to_use)

        return results

    async def _research_parallel(
        self,
        topic: str,
        agents: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Execute research in parallel with timeout and fallback.

        Args:
            topic: Research topic
            agents: Agents to use

        Returns:
            Dictionary mapping agent names to findings
        """
        results = {}
        tasks = {}

        # Create tasks for all agents
        for agent_name, agent in agents.items():
            task = asyncio.create_task(
                self._call_agent_with_timeout(agent_name, agent, topic)
            )
            tasks[agent_name] = task

        # Wait for all tasks with timeout
        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*tasks.values(), return_exceptions=True),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Research timeout after {self.timeout}s")
            # Cancel remaining tasks
            for task in tasks.values():
                task.cancel()
            completed = []

        # Collect results
        for agent_name, task in tasks.items():
            try:
                if task.done():
                    result = task.result()
                    if isinstance(result, Exception):
                        logger.warning(f"Agent {agent_name} error: {result}")
                        results[agent_name] = []
                    else:
                        results[agent_name] = result
            except asyncio.CancelledError:
                logger.debug(f"Agent {agent_name} cancelled")
                results[agent_name] = []
            except Exception as e:
                logger.warning(f"Error collecting results from {agent_name}: {e}")
                results[agent_name] = []

        return results

    async def _research_sequential(
        self,
        topic: str,
        agents: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Execute research sequentially with timeout and fallback.

        Args:
            topic: Research topic
            agents: Agents to use

        Returns:
            Dictionary mapping agent names to findings
        """
        results = {}

        for agent_name, agent in agents.items():
            try:
                findings = await asyncio.wait_for(
                    agent.search(topic),
                    timeout=self.timeout
                )
                results[agent_name] = findings
            except asyncio.TimeoutError:
                logger.warning(f"Agent {agent_name} timed out")
                results[agent_name] = []
            except Exception as e:
                logger.warning(f"Agent {agent_name} error: {e}")
                results[agent_name] = []

        return results

    async def _call_agent_with_timeout(
        self,
        agent_name: str,
        agent: Any,
        topic: str,
    ) -> List[Dict[str, Any]]:
        """Call agent with timeout and error handling.

        Args:
            agent_name: Agent name (for logging)
            agent: Agent instance
            topic: Research topic

        Returns:
            List of findings or empty list on error
        """
        try:
            findings = await asyncio.wait_for(
                agent.search(topic),
                timeout=self.timeout
            )
            return findings or []
        except asyncio.TimeoutError:
            logger.warning(f"Agent {agent_name} timed out after {self.timeout}s")
            return []
        except Exception as e:
            logger.warning(f"Agent {agent_name} error: {e}")
            return []

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics on available agents.

        Returns:
            Dictionary with agent statistics
        """
        return {
            "mode": self.mode.value,
            "web_agents_available": len(self.web_agents),
            "mock_agents_available": len(self.mock_agents),
            "total_agents": len(self.web_agents) + len(self.mock_agents),
            "web_agent_names": list(self.web_agents.keys()),
            "mock_agent_names": list(self.mock_agents.keys()),
        }


async def execute_research(
    topic: str,
    mode: ResearchMode = ResearchMode.HYBRID,
    use_real: bool = True,
    use_mock: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """Execute research with provided topic and mode.

    Args:
        topic: Research topic
        mode: Research execution mode
        use_real: Include real web research
        use_mock: Include mock research

    Returns:
        Dictionary mapping agent names to findings
    """
    orchestrator = ResearchOrchestrator(mode=mode)
    logger.info(f"Starting research: {topic} (mode={mode.value})")
    logger.info(f"Available agents: {orchestrator.get_agent_stats()}")

    results = await orchestrator.research(
        topic,
        use_real=use_real,
        use_mock=use_mock,
        parallel=True,
    )

    # Calculate summary statistics
    total_findings = sum(len(findings) for findings in results.values())
    credible_sources = {
        agent: len([f for f in findings if f.get("credibility", 0) > 0.7])
        for agent, findings in results.items()
    }

    logger.info(f"Research complete: {total_findings} findings from {len(results)} sources")
    logger.debug(f"Credible findings per source: {credible_sources}")

    return results
