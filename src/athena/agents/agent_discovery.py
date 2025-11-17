"""Agent Discovery Service - enables agents to find and communicate with each other.

Agents register themselves with capabilities, and can be discovered by other agents
who need specific skills or information.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

from .agent_events import AgentEvent, AgentEventType
from .event_bus import get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Capability that an agent offers."""

    name: str
    description: str
    requires: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentProfile:
    """Profile of a registered agent."""

    agent_id: str
    agent_type: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: str = "active"  # active, inactive, error
    last_seen: datetime = field(default_factory=datetime.utcnow)
    success_rate: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentDiscovery:
    """Service for agent registration, discovery, and communication."""

    def __init__(self):
        """Initialize discovery service."""
        self.agents: Dict[str, AgentProfile] = {}
        self.event_bus = get_event_bus()

        # Handlers for inter-agent communication
        self.request_handlers: Dict[str, Callable] = {}

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Optional[List[AgentCapability]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an agent with the discovery service.

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (code-analyzer, research-coordinator, etc.)
            capabilities: List of capabilities agent provides
            metadata: Additional metadata about agent
        """
        profile = AgentProfile(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or [],
            metadata=metadata or {},
        )

        self.agents[agent_id] = profile

        logger.info(f"Discovery: Registered {agent_id} ({agent_type})")

        # Publish registration event
        await self.event_bus.publish(
            AgentEvent(
                agent_id="discovery",
                event_type=AgentEventType.KNOWLEDGE_SHARED,
                data={
                    "action": "agent_registered",
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "capabilities": [c.name for c in (capabilities or [])],
                },
                confidence=1.0,
                tags=["discovery", "registration"],
            )
        )

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Discovery: Unregistered {agent_id}")

    async def find_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Find a specific agent by ID.

        Args:
            agent_id: Agent ID to find

        Returns:
            Agent profile or None
        """
        return self.agents.get(agent_id)

    async def find_agents_by_type(self, agent_type: str) -> List[AgentProfile]:
        """Find all agents of a specific type.

        Args:
            agent_type: Type of agents to find

        Returns:
            List of matching agent profiles
        """
        return [a for a in self.agents.values() if a.agent_type == agent_type]

    async def find_agents_by_capability(self, capability: str) -> List[AgentProfile]:
        """Find agents that have a specific capability.

        Args:
            capability: Capability name to search for

        Returns:
            List of agents with that capability
        """
        agents = []
        for agent in self.agents.values():
            if any(cap.name == capability for cap in agent.capabilities):
                agents.append(agent)
        return agents

    async def find_agents_by_tag(self, tag: str) -> List[AgentProfile]:
        """Find agents with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of agents with that tag
        """
        agents = []
        for agent in self.agents.values():
            if any(tag in cap.tags for cap in agent.capabilities):
                agents.append(agent)
        return agents

    async def list_all_agents(self) -> List[AgentProfile]:
        """List all registered agents.

        Returns:
            List of all agent profiles
        """
        return list(self.agents.values())

    async def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities of a specific agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of capability names
        """
        agent = self.agents.get(agent_id)
        if agent:
            return [cap.name for cap in agent.capabilities]
        return []

    async def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update agent status (active, inactive, error, etc.).

        Args:
            agent_id: Agent ID
            status: New status
        """
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self.agents[agent_id].last_seen = datetime.utcnow()
            logger.debug(f"Discovery: {agent_id} status updated to {status}")

    async def update_agent_success_rate(self, agent_id: str, success_rate: float) -> None:
        """Update agent's success rate metric.

        Args:
            agent_id: Agent ID
            success_rate: Success rate (0.0-1.0)
        """
        if agent_id in self.agents:
            self.agents[agent_id].success_rate = max(0.0, min(1.0, success_rate))

    async def broadcast_message(
        self,
        source_agent: str,
        message_type: str,
        data: Dict[str, Any],
        target_agents: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Broadcast a message to agents.

        Args:
            source_agent: Agent sending message
            message_type: Type of message
            data: Message payload
            target_agents: Optional list of specific target agents
            tags: Tags for message
        """
        event = AgentEvent(
            agent_id=source_agent,
            event_type=AgentEventType.KNOWLEDGE_SHARED,
            data={"message_type": message_type, "payload": data},
            tags=tags or [],
            confidence=0.8,
        )

        await self.event_bus.publish(event)

        logger.debug(f"Discovery: Broadcast from {source_agent}: {message_type}")

    def register_request_handler(
        self,
        action: str,
        handler: Callable[[Dict[str, Any]], Awaitable[Any]],
    ) -> None:
        """Register a handler for agent requests.

        Args:
            action: Action name
            handler: Async callable to handle requests
        """
        self.request_handlers[action] = handler
        logger.debug(f"Discovery: Registered handler for {action}")

    async def handle_request(self, action: str, params: Dict[str, Any]) -> Any:
        """Handle an inter-agent request.

        Args:
            action: Action to perform
            params: Action parameters

        Returns:
            Result from handler
        """
        if action not in self.request_handlers:
            logger.warning(f"Discovery: No handler for action {action}")
            return None

        handler = self.request_handlers[action]
        try:
            result = await handler(params)
            return result
        except Exception as e:
            logger.error(f"Discovery: Error handling {action}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get discovery service statistics.

        Returns:
            Dict with stats
        """
        total_agents = len(self.agents)
        active_agents = sum(1 for a in self.agents.values() if a.status == "active")

        agent_types = {}
        for agent in self.agents.values():
            agent_types[agent.agent_type] = agent_types.get(agent.agent_type, 0) + 1

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "agent_types": agent_types,
            "registered_handlers": len(self.request_handlers),
        }


# Global discovery instance
_discovery: Optional[AgentDiscovery] = None


def initialize_discovery() -> AgentDiscovery:
    """Initialize global discovery service.

    Returns:
        Initialized discovery service
    """
    global _discovery
    _discovery = AgentDiscovery()
    logger.info("Discovery: Initialized")
    return _discovery


def get_discovery() -> AgentDiscovery:
    """Get global discovery service instance.

    Returns:
        Discovery service (creates if needed)
    """
    global _discovery
    if _discovery is None:
        _discovery = AgentDiscovery()
    return _discovery
