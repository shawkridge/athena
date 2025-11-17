"""Integration tests for Phase 4.3a: Agent Communication & Discovery.

Tests verify that:
1. Agents can register with discovery service
2. Events are published and routed to subscribers
3. Event filtering works correctly
4. Agents can discover other agents
5. Agent request handlers work
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, '/home/user/.work/athena/src')

from athena.agents.agent_events import (
    AgentEvent,
    AgentEventType,
    AgentEventPriority,
    EventSubscription,
)
from athena.agents.event_bus import initialize_event_bus, get_event_bus, EventBus
from athena.agents.agent_discovery import (
    initialize_discovery,
    get_discovery,
    AgentCapability,
    AgentProfile,
)


class TestEventBusBasics:
    """Test basic event bus functionality."""

    def setup_method(self):
        """Setup for each test."""
        self.event_bus = initialize_event_bus()

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test publishing an event."""
        event = AgentEvent(
            agent_id="test-agent",
            event_type=AgentEventType.ANALYSIS_COMPLETE,
            data={"status": "success"},
            confidence=0.9,
        )

        await self.event_bus.publish(event)

        # Check event is in history
        assert len(self.event_bus.event_history) > 0

    @pytest.mark.asyncio
    async def test_event_sequencing(self):
        """Test events are sequenced correctly."""
        event1 = AgentEvent(
            agent_id="agent1",
            event_type=AgentEventType.ANALYSIS_STARTED,
        )
        event2 = AgentEvent(
            agent_id="agent2",
            event_type=AgentEventType.ANALYSIS_COMPLETE,
        )

        await self.event_bus.publish(event1)
        await self.event_bus.publish(event2)

        assert event1.sequence_number < event2.sequence_number
        assert event1.sequence_number == 1
        assert event2.sequence_number == 2

    @pytest.mark.asyncio
    async def test_get_events_from_history(self):
        """Test retrieving events from history."""
        await self.event_bus.publish(
            AgentEvent(
                agent_id="analyzer",
                event_type=AgentEventType.FINDING_IDENTIFIED,
                data={"issue": "null_pointer"},
            )
        )

        # Get from history
        events = await self.event_bus.get_events(
            event_type=AgentEventType.FINDING_IDENTIFIED
        )

        assert len(events) > 0
        assert events[0].agent_id == "analyzer"

    def test_event_bus_stats(self):
        """Test event bus statistics."""
        stats = self.event_bus.get_stats()

        assert "total_events" in stats
        assert "total_subscribers" in stats
        assert "event_counts" in stats
        assert stats["total_events"] >= 0


class TestEventBusSubscription:
    """Test event bus pub/sub functionality."""

    def setup_method(self):
        """Setup for each test."""
        self.event_bus = initialize_event_bus()

    @pytest.mark.asyncio
    async def test_subscribe_to_event_type(self):
        """Test subscribing to specific event type."""
        received_events = []

        async def subscriber():
            async for event in self.event_bus.subscribe(
                subscriber_id="listener1",
                event_types=[AgentEventType.FINDING_IDENTIFIED],
            ):
                received_events.append(event)
                if len(received_events) >= 2:
                    break

        # Start subscriber
        sub_task = asyncio.create_task(subscriber())

        # Publish matching events
        await asyncio.sleep(0.1)  # Let subscriber start
        await self.event_bus.publish(
            AgentEvent(
                agent_id="analyzer",
                event_type=AgentEventType.FINDING_IDENTIFIED,
                data={"issue": "bug"},
            )
        )
        await self.event_bus.publish(
            AgentEvent(
                agent_id="analyzer",
                event_type=AgentEventType.FINDING_IDENTIFIED,
                data={"issue": "bug2"},
            )
        )

        # Wait for subscriber to collect events
        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        assert len(received_events) == 2
        assert all(e.event_type == AgentEventType.FINDING_IDENTIFIED for e in received_events)

    @pytest.mark.asyncio
    async def test_filter_by_agent_id(self):
        """Test filtering events by agent ID."""
        received_events = []

        async def subscriber():
            async for event in self.event_bus.subscribe(
                subscriber_id="listener2",
                agent_ids=["code-analyzer"],
            ):
                received_events.append(event)
                if len(received_events) >= 1:
                    break

        sub_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0.1)
        await self.event_bus.publish(
            AgentEvent(agent_id="code-analyzer", event_type=AgentEventType.ANALYSIS_COMPLETE)
        )
        await self.event_bus.publish(
            AgentEvent(agent_id="research", event_type=AgentEventType.PLAN_CREATED)
        )

        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Should only receive from code-analyzer
        assert len(received_events) == 1
        assert received_events[0].agent_id == "code-analyzer"

    @pytest.mark.asyncio
    async def test_filter_by_confidence(self):
        """Test filtering by confidence threshold."""
        received_events = []

        async def subscriber():
            async for event in self.event_bus.subscribe(
                subscriber_id="listener3",
                min_confidence=0.8,
            ):
                received_events.append(event)
                if len(received_events) >= 1:
                    break

        sub_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0.1)
        await self.event_bus.publish(
            AgentEvent(
                agent_id="test",
                event_type=AgentEventType.FINDING_IDENTIFIED,
                confidence=0.9,  # Should pass filter
            )
        )
        await self.event_bus.publish(
            AgentEvent(
                agent_id="test",
                event_type=AgentEventType.FINDING_IDENTIFIED,
                confidence=0.5,  # Should NOT pass filter
            )
        )

        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        assert len(received_events) == 1
        assert received_events[0].confidence >= 0.8


class TestAgentDiscovery:
    """Test agent discovery service."""

    def setup_method(self):
        """Setup for each test."""
        self.discovery = initialize_discovery()

    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test registering an agent."""
        await self.discovery.register_agent(
            agent_id="code-analyzer",
            agent_type="analyzer",
            capabilities=[AgentCapability(name="analyze_code", description="Analyzes code")],
        )

        agent = await self.discovery.find_agent("code-analyzer")

        assert agent is not None
        assert agent.agent_id == "code-analyzer"
        assert agent.agent_type == "analyzer"
        assert len(agent.capabilities) > 0

    @pytest.mark.asyncio
    async def test_find_agents_by_type(self):
        """Test finding agents by type."""
        await self.discovery.register_agent("analyzer1", "analyzer")
        await self.discovery.register_agent("analyzer2", "analyzer")
        await self.discovery.register_agent("orchestrator1", "orchestrator")

        analyzers = await self.discovery.find_agents_by_type("analyzer")

        assert len(analyzers) == 2
        assert all(a.agent_type == "analyzer" for a in analyzers)

    @pytest.mark.asyncio
    async def test_find_agents_by_capability(self):
        """Test finding agents by capability."""
        await self.discovery.register_agent(
            "agent1",
            "analyzer",
            capabilities=[AgentCapability(name="analyze_code", description="")],
        )
        await self.discovery.register_agent(
            "agent2",
            "orchestrator",
            capabilities=[AgentCapability(name="route_task", description="")],
        )

        agents = await self.discovery.find_agents_by_capability("analyze_code")

        assert len(agents) == 1
        assert agents[0].agent_id == "agent1"

    @pytest.mark.asyncio
    async def test_get_agent_capabilities(self):
        """Test getting agent capabilities."""
        await self.discovery.register_agent(
            "analyzer",
            "analyzer",
            capabilities=[
                AgentCapability(name="analyze_code", description=""),
                AgentCapability(name="find_patterns", description=""),
            ],
        )

        capabilities = await self.discovery.get_agent_capabilities("analyzer")

        assert len(capabilities) == 2
        assert "analyze_code" in capabilities
        assert "find_patterns" in capabilities

    @pytest.mark.asyncio
    async def test_list_all_agents(self):
        """Test listing all registered agents."""
        await self.discovery.register_agent("agent1", "type1")
        await self.discovery.register_agent("agent2", "type2")
        await self.discovery.register_agent("agent3", "type1")

        agents = await self.discovery.list_all_agents()

        assert len(agents) >= 3

    @pytest.mark.asyncio
    async def test_update_agent_status(self):
        """Test updating agent status."""
        await self.discovery.register_agent("agent1", "type1")
        await self.discovery.update_agent_status("agent1", "inactive")

        agent = await self.discovery.find_agent("agent1")

        assert agent.status == "inactive"

    @pytest.mark.asyncio
    async def test_update_agent_success_rate(self):
        """Test updating agent success rate."""
        await self.discovery.register_agent("agent1", "type1")
        await self.discovery.update_agent_success_rate("agent1", 0.85)

        agent = await self.discovery.find_agent("agent1")

        assert agent.success_rate == 0.85

    def test_discovery_stats(self):
        """Test discovery service statistics."""
        stats = self.discovery.get_stats()

        assert "total_agents" in stats
        assert "active_agents" in stats
        assert "agent_types" in stats


class TestDiscoveryAndEventBusIntegration:
    """Test integration between discovery and event bus."""

    def setup_method(self):
        """Setup for each test."""
        self.discovery = initialize_discovery()
        self.event_bus = get_event_bus()

    @pytest.mark.asyncio
    async def test_agent_registration_broadcasts_event(self):
        """Test that agent registration triggers event."""
        received_events = []

        async def subscriber():
            async for event in self.event_bus.subscribe(
                subscriber_id="monitor",
                event_types=[AgentEventType.KNOWLEDGE_SHARED],
            ):
                received_events.append(event)
                if len(received_events) >= 1:
                    break

        sub_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0.1)
        await self.discovery.register_agent("agent1", "type1")

        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Should receive registration event
        assert any("agent_registered" in str(e.data) for e in received_events)

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting a message through discovery."""
        received_events = []

        async def subscriber():
            async for event in self.event_bus.subscribe(
                subscriber_id="listener",
            ):
                received_events.append(event)
                if len(received_events) >= 1:
                    break

        sub_task = asyncio.create_task(subscriber())

        await asyncio.sleep(0.1)
        await self.discovery.broadcast_message(
            source_agent="sender",
            message_type="test_message",
            data={"key": "value"},
        )

        try:
            await asyncio.wait_for(sub_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        assert len(received_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
