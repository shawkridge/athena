"""Multi-Agent Research System - Specialized research agents.

Implements agent-based research with:
- Specialized agents (web searcher, academic researcher, synthesizer)
- Agent coordination and task distribution
- Shared context and memory
- Progress tracking and result aggregation
- Interactive refinement and feedback

Each agent focuses on specific research aspects and coordinates with others.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from .api_integrations import (
    SearchResult,
    AcademicPaper,
    WebSearchProvider,
    AcademicProvider,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles in research."""
    WEB_SEARCHER = "web_searcher"
    ACADEMIC_RESEARCHER = "academic_researcher"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"
    COORDINATOR = "coordinator"


@dataclass
class AgentMessage:
    """Message between agents."""
    sender_id: str
    receiver_id: Optional[str]  # None = broadcast
    role: AgentRole
    message_type: str  # 'task', 'result', 'feedback', 'status'
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResearchTask:
    """A research task to be assigned to agents."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    task_type: str = ""  # 'web_search', 'academic_search', 'synthesis', etc.
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, running, complete, failed
    results: List[Any] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SharedContext:
    """Shared context and memory for research session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_query: str = ""
    search_results: List[SearchResult] = field(default_factory=list)
    academic_papers: List[AcademicPaper] = field(default_factory=list)
    synthesis: Optional[str] = None
    key_findings: List[str] = field(default_factory=list)
    visited_urls: Set[str] = field(default_factory=set)
    explored_queries: Set[str] = field(default_factory=set)
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchAgent(ABC):
    """Base class for research agents."""

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        name: str,
        context: SharedContext,
    ):
        """Initialize agent.

        Args:
            agent_id: Unique agent identifier
            role: Agent's role in research
            name: Human-readable name
            context: Shared research context
        """
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.context = context
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._tasks: Dict[str, ResearchTask] = {}
        self._status = "idle"

    async def run(self) -> None:
        """Main agent loop."""
        logger.info(f"{self.name} ({self.agent_id}) started")
        self._status = "running"

        try:
            while self._status == "running":
                try:
                    # Get task with timeout
                    message = await asyncio.wait_for(
                        self._inbox.get(),
                        timeout=5.0
                    )
                    await self._handle_message(message)

                except asyncio.TimeoutError:
                    # Check for work to do
                    await self._check_work()

        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            self._status = "error"

        logger.info(f"{self.name} ({self.agent_id}) stopped")

    async def _handle_message(self, message: AgentMessage) -> None:
        """Handle incoming message."""
        if message.message_type == "task":
            task = ResearchTask(**message.content)
            await self.execute_task(task)

        elif message.message_type == "feedback":
            await self.handle_feedback(message.content)

        elif message.message_type == "status":
            await self.handle_status_request(message)

    @abstractmethod
    async def execute_task(self, task: ResearchTask) -> None:
        """Execute a research task."""
        pass

    @abstractmethod
    async def _check_work(self) -> None:
        """Check if there's work to do."""
        pass

    async def handle_feedback(self, feedback: Dict[str, Any]) -> None:
        """Handle feedback from user or other agents."""
        logger.debug(f"{self.name} received feedback: {feedback}")

    async def handle_status_request(self, message: AgentMessage) -> None:
        """Send status to requester."""
        status_msg = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            role=self.role,
            message_type="status",
            content={
                "status": self._status,
                "tasks_completed": len([t for t in self._tasks.values() if t.status == "complete"]),
                "tasks_pending": len([t for t in self._tasks.values() if t.status == "pending"]),
            }
        )

    async def send_message(self, message: AgentMessage) -> None:
        """Send message to another agent."""
        await self._inbox.put(message)

    def stop(self) -> None:
        """Stop agent."""
        self._status = "stopped"


class WebSearchAgent(ResearchAgent):
    """Agent specialized in web search."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        context: SharedContext,
        provider: WebSearchProvider,
    ):
        """Initialize web search agent."""
        super().__init__(agent_id, AgentRole.WEB_SEARCHER, name, context)
        self.provider = provider

    async def execute_task(self, task: ResearchTask) -> None:
        """Execute web search task."""
        if task.task_type != "web_search":
            return

        logger.info(f"{self.name} searching: {task.query}")
        task.status = "running"
        task.assigned_to = self.agent_id

        try:
            # Skip if already searched
            if task.query in self.context.explored_queries:
                logger.debug(f"Query already explored: {task.query}")
                task.results = []
                task.status = "complete"
                return

            # Search
            results = await self.provider.search(
                task.query,
                limit=15,
            )

            # Filter duplicates
            new_results = [
                r for r in results
                if r.url not in self.context.visited_urls
            ]

            # Update context
            self.context.search_results.extend(new_results)
            for result in new_results:
                self.context.visited_urls.add(result.url)
            self.context.explored_queries.add(task.query)

            task.results = new_results
            task.status = "complete"

            logger.info(f"{self.name} found {len(new_results)} results")

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            task.status = "failed"
            task.metadata["error"] = str(e)

        self._tasks[task.task_id] = task

    async def _check_work(self) -> None:
        """Check for pending work."""
        pass


class AcademicResearchAgent(ResearchAgent):
    """Agent specialized in academic research."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        context: SharedContext,
        provider: AcademicProvider,
    ):
        """Initialize academic research agent."""
        super().__init__(agent_id, AgentRole.ACADEMIC_RESEARCHER, name, context)
        self.provider = provider

    async def execute_task(self, task: ResearchTask) -> None:
        """Execute academic search task."""
        if task.task_type != "academic_search":
            return

        logger.info(f"{self.name} searching: {task.query}")
        task.status = "running"
        task.assigned_to = self.agent_id

        try:
            papers = await self.provider.search(
                task.query,
                limit=20,
            )

            self.context.academic_papers.extend(papers)
            task.results = papers
            task.status = "complete"

            logger.info(f"{self.name} found {len(papers)} papers")

        except Exception as e:
            logger.error(f"Academic search failed: {e}")
            task.status = "failed"
            task.metadata["error"] = str(e)

        self._tasks[task.task_id] = task

    async def _check_work(self) -> None:
        """Check for pending work."""
        pass


class SynthesisAgent(ResearchAgent):
    """Agent specialized in synthesizing findings."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        context: SharedContext,
        llm_provider: LLMProvider,
    ):
        """Initialize synthesis agent."""
        super().__init__(agent_id, AgentRole.SYNTHESIZER, name, context)
        self.llm_provider = llm_provider

    async def execute_task(self, task: ResearchTask) -> None:
        """Execute synthesis task."""
        if task.task_type != "synthesis":
            return

        logger.info(f"{self.name} synthesizing research")
        task.status = "running"
        task.assigned_to = self.agent_id

        try:
            # Prepare sources
            web_snippets = [f"- {r.title}: {r.snippet}" for r in self.context.search_results[:5]]
            paper_summaries = [
                f"- {p.title} ({', '.join(p.authors[:2])})"
                for p in self.context.academic_papers[:5]
            ]

            sources = "\n".join(web_snippets + paper_summaries)

            prompt = f"""Synthesize the following research sources into a comprehensive summary
for the query: "{self.context.original_query}"

Sources:
{sources}

Provide:
1. Key Findings (3-5 bullets)
2. Synthesis (2-3 paragraphs)
3. Gaps and Future Directions

Synthesis:"""

            response = await self.llm_provider.complete(
                prompt,
                max_tokens=2000,
                temperature=0.7,
            )

            self.context.synthesis = response.text

            # Extract key findings
            lines = response.text.split("\n")
            self.context.key_findings = [
                line.strip()
                for line in lines
                if line.strip().startswith(("-", "•", "*"))
            ][:5]

            task.results = [response.text]
            task.status = "complete"

            logger.info(f"{self.name} completed synthesis")

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            task.status = "failed"
            task.metadata["error"] = str(e)

        self._tasks[task.task_id] = task

    async def _check_work(self) -> None:
        """Check for pending work."""
        pass


class ResearchCoordinator:
    """Coordinates research agents and task distribution."""

    def __init__(
        self,
        web_provider: Optional[WebSearchProvider] = None,
        academic_provider: Optional[AcademicProvider] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize coordinator.

        Args:
            web_provider: Web search provider
            academic_provider: Academic search provider
            llm_provider: LLM synthesis provider
        """
        self.web_provider = web_provider
        self.academic_provider = academic_provider
        self.llm_provider = llm_provider

        self.agents: Dict[str, ResearchAgent] = {}
        self.context: Optional[SharedContext] = None
        self.task_queue: asyncio.Queue = asyncio.Queue()

    async def start_research(self, query: str) -> SharedContext:
        """Start multi-agent research on a query.

        Args:
            query: Research query

        Returns:
            SharedContext with research results
        """
        # Initialize context
        self.context = SharedContext(original_query=query)

        # Create agents
        await self._create_agents()

        # Start agent tasks
        agent_tasks = [agent.run() for agent in self.agents.values()]
        agents_task = asyncio.gather(*agent_tasks)

        try:
            # Distribute tasks
            await self._distribute_tasks(query)

            # Wait for agents to complete (with timeout)
            await asyncio.wait_for(agents_task, timeout=60.0)

        except asyncio.TimeoutError:
            logger.warning("Research timed out, collecting partial results")

        except Exception as e:
            logger.error(f"Research failed: {e}")

        finally:
            # Stop agents
            for agent in self.agents.values():
                agent.stop()

        return self.context

    async def _create_agents(self) -> None:
        """Create specialized research agents."""
        if self.web_provider:
            web_agent = WebSearchAgent(
                agent_id="web-searcher-1",
                name="Web Searcher",
                context=self.context,
                provider=self.web_provider,
            )
            self.agents[web_agent.agent_id] = web_agent

        if self.academic_provider:
            academic_agent = AcademicResearchAgent(
                agent_id="academic-researcher-1",
                name="Academic Researcher",
                context=self.context,
                provider=self.academic_provider,
            )
            self.agents[academic_agent.agent_id] = academic_agent

        if self.llm_provider:
            synthesis_agent = SynthesisAgent(
                agent_id="synthesizer-1",
                name="Synthesizer",
                context=self.context,
                llm_provider=self.llm_provider,
            )
            self.agents[synthesis_agent.agent_id] = synthesis_agent

    async def _distribute_tasks(self, query: str) -> None:
        """Distribute research tasks to agents."""
        # Task 1: Web search
        if self.web_provider:
            web_task = ResearchTask(
                query=query,
                task_type="web_search",
            )
            web_agent = self.agents.get("web-searcher-1")
            if web_agent:
                await web_agent.execute_task(web_task)

        # Task 2: Academic search
        if self.academic_provider:
            academic_task = ResearchTask(
                query=query,
                task_type="academic_search",
            )
            academic_agent = self.agents.get("academic-researcher-1")
            if academic_agent:
                await academic_agent.execute_task(academic_task)

        # Task 3: Synthesis (after searches complete)
        if self.llm_provider:
            await asyncio.sleep(1)  # Wait for searches
            synthesis_task = ResearchTask(
                query=query,
                task_type="synthesis",
                dependencies=["web_search", "academic_search"],
            )
            synthesis_agent = self.agents.get("synthesizer-1")
            if synthesis_agent:
                await synthesis_agent.execute_task(synthesis_task)
