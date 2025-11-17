"""AgentCoordinator base class - provides communication patterns for agents.

This class provides high-level methods for agents to coordinate via shared memory,
implementing the coordination protocol defined in docs/AGENT_COORDINATION.md.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Import core memory operations
from ..episodic.operations import remember as remember_event
from ..memory.operations import store as store_fact, search as search_facts
from ..prospective.operations import (
    create_task as create_prospective_task,
    get_active_tasks as get_prospective_tasks,
    get_task as get_prospective_task,
    update_task_status as update_prospective_task_status,
)
from ..meta.operations import (
    update_cognitive_load as update_load,
    get_cognitive_load as get_load,
)
from ..graph.operations import (
    add_entity as add_graph_entity,
    add_relationship as add_graph_relationship,
    find_related as find_related_entities,
)

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Base class for coordinated agents in Athena.

    Provides methods for:
    - Creating tasks for other agents
    - Emitting events for others to observe
    - Sharing learned knowledge
    - Tracking agent health/status
    - Querying shared context
    """

    def __init__(self, agent_id: str, agent_type: str):
        """Initialize coordinator.

        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent (e.g., "memory-coordinator", "pattern-extractor")
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.statistics = {
            "tasks_created": 0,
            "events_emitted": 0,
            "knowledge_shared": 0,
            "status_updates": 0,
        }

    # ========== TASK DELEGATION PATTERN ==========

    async def create_task(
        self,
        description: str,
        required_skills: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        deadline: Optional[str] = None,
    ) -> str:
        """Create a task for another agent to execute.

        Args:
            description: Task description
            required_skills: List of agent types that can execute this
            parameters: Task-specific parameters
            depends_on: List of task IDs this depends on
            deadline: Optional deadline (ISO format)

        Returns:
            Task ID
        """
        task_id = await create_prospective_task(
            title=description,
            description=description,
            task_type="agent_task",
            metadata={
                "created_by": self.agent_id,
                "required_skills": required_skills,
                "parameters": parameters or {},
                "depends_on": depends_on or [],
                "deadline": deadline,
            },
        )

        self.statistics["tasks_created"] += 1
        logger.info(f"Agent {self.agent_id} created task {task_id}")

        return task_id

    async def get_available_tasks(
        self,
        agent_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get tasks available for this agent to execute.

        Args:
            agent_type: Filter by required skill (default: this agent's type)
            tags: Filter by task tags

        Returns:
            List of available tasks
        """
        agent_type = agent_type or self.agent_type

        # Get active tasks
        tasks = await get_prospective_tasks(limit=50)

        # Filter by:
        # 1. Agent type matches required_skills
        # 2. Dependencies satisfied
        # 3. Status is pending/unstarted
        available = []

        for task in tasks:
            metadata = task.get("metadata", {})
            required_skills = metadata.get("required_skills", [])

            # Check agent type matches
            if agent_type not in required_skills:
                continue

            # Check status
            if task.get("status") not in ["pending", None]:
                continue

            # Check dependencies (simplified - in production would verify completion)
            depends_on = metadata.get("depends_on", [])
            if depends_on:
                # For now, assume we can check - in production, verify each one
                logger.debug(f"Task {task['id']} has dependencies, skipping for now")
                continue

            # Check tags if specified
            if tags:
                task_tags = task.get("tags", [])
                if not any(tag in task_tags for tag in tags):
                    continue

            available.append(task)

        logger.debug(f"Found {len(available)} available tasks for {agent_type}")
        return available

    async def update_task(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update task status after execution.

        Args:
            task_id: Task ID to update
            status: New status ("started", "completed", "failed")
            result: Optional result data
            error: Optional error message

        Returns:
            True if successful
        """
        metadata = {}
        if result:
            metadata["result"] = result
        if error:
            metadata["error"] = error
        metadata["updated_by"] = self.agent_id
        metadata["updated_at"] = datetime.utcnow().isoformat()

        success = await update_prospective_task_status(
            task_id=task_id,
            status=status,
            metadata=metadata,
        )

        self.statistics["status_updates"] += 1
        logger.info(f"Agent {self.agent_id} updated task {task_id} to {status}")

        return success

    # ========== EVENT NOTIFICATION PATTERN ==========

    async def emit_event(
        self,
        event_type: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> str:
        """Emit an event that other agents can observe.

        Args:
            event_type: Type of event (e.g., "pattern_extracted", "error_detected")
            content: Detailed event content
            tags: Tags for filtering/discovery
            importance: Importance score (0-1)

        Returns:
            Event ID
        """
        all_tags = [event_type, f"agent:{self.agent_type}"]
        if tags:
            all_tags.extend(tags)

        event_id = await remember_event(
            content=content,
            context={"agent_id": self.agent_id, "agent_type": self.agent_type},
            tags=all_tags,
            importance=importance,
            source=f"agent:{self.agent_id}",
        )

        self.statistics["events_emitted"] += 1
        logger.info(
            f"Agent {self.agent_id} emitted event {event_id} (type={event_type})"
        )

        return event_id

    async def query_events(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query for events emitted by other agents.

        Args:
            query: Search query
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of matching events
        """
        from ..episodic.operations import recall

        # If tags specified, add them to query
        all_tags = tags or []

        events = await recall(query=query, limit=limit)

        # Filter by tags if specified
        if all_tags:
            events = [
                e
                for e in events
                if any(tag in e.get("tags", []) for tag in all_tags)
            ]

        logger.debug(
            f"Agent {self.agent_id} queried {len(events)} events (query={query})"
        )

        return events

    # ========== KNOWLEDGE SHARING PATTERN ==========

    async def share_knowledge(
        self,
        content: str,
        topics: Optional[List[str]] = None,
        confidence: float = 0.5,
    ) -> str:
        """Share learned knowledge with other agents.

        Args:
            content: The fact/knowledge to share
            topics: Categories/topics for this knowledge
            confidence: Confidence in this knowledge (0-1)

        Returns:
            Knowledge ID
        """
        all_topics = topics or ["learned"]
        all_topics.append(f"agent:{self.agent_type}")

        knowledge_id = await store_fact(
            content=content,
            topics=all_topics,
            confidence=confidence,
        )

        self.statistics["knowledge_shared"] += 1
        logger.info(
            f"Agent {self.agent_id} shared knowledge {knowledge_id} "
            f"(confidence={confidence})"
        )

        return knowledge_id

    async def query_knowledge(
        self,
        query: str,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query knowledge shared by other agents.

        Args:
            query: Search query
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching facts
        """
        facts = await search_facts(query=query, limit=limit)

        # Filter by confidence
        facts = [f for f in facts if f.get("confidence", 0) >= min_confidence]

        logger.debug(
            f"Agent {self.agent_id} queried {len(facts)} facts (query={query})"
        )

        return facts

    # ========== STATUS COORDINATION PATTERN ==========

    async def report_status(
        self,
        load: float,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Report current agent status/health.

        Args:
            load: Current cognitive load (0-1)
            metrics: Optional metrics dict

        Returns:
            True if successful
        """
        metadata = metrics or {}
        metadata["reported_at"] = datetime.utcnow().isoformat()

        success = await update_load(
            agent_id=self.agent_id,
            load=load,
            metadata=metadata,
        )

        self.statistics["status_updates"] += 1
        logger.debug(f"Agent {self.agent_id} reported load={load}")

        return success

    async def check_agent_status(
        self,
        agent_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Check status of another agent.

        Args:
            agent_id: Agent to check (default: self)

        Returns:
            Status dict or None
        """
        check_id = agent_id or self.agent_id

        try:
            load = await get_load(agent_id=check_id)
            return {
                "agent_id": check_id,
                "cognitive_load": load.get("load", 0.5),
                "metadata": load.get("metadata", {}),
            }
        except Exception as e:
            logger.warning(f"Failed to get status for {check_id}: {e}")
            return None

    # ========== CONTEXT ENRICHMENT PATTERN ==========

    async def add_context(
        self,
        entity_name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add context entity to knowledge graph.

        Args:
            entity_name: Entity name/ID
            entity_type: Type of entity (e.g., "project", "file", "pattern")
            properties: Optional properties

        Returns:
            True if successful
        """
        try:
            await add_graph_entity(
                name=entity_name,
                entity_type=entity_type,
                properties=properties or {},
            )

            logger.debug(
                f"Agent {self.agent_id} added context entity {entity_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add context entity {entity_name}: {e}")
            return False

    async def link_context(
        self,
        from_entity: str,
        to_entity: str,
        relationship: str,
    ) -> bool:
        """Link two context entities.

        Args:
            from_entity: Source entity ID
            to_entity: Target entity ID
            relationship: Relationship type (e.g., "uses", "contains")

        Returns:
            True if successful
        """
        try:
            await add_graph_relationship(
                from_entity=from_entity,
                to_entity=to_entity,
                relationship=relationship,
            )

            logger.debug(
                f"Agent {self.agent_id} linked {from_entity} -> {to_entity}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to link entities {from_entity} -> {to_entity}: {e}"
            )
            return False

    async def get_context(
        self,
        entity_id: str,
    ) -> List[Dict[str, Any]]:
        """Get related context for an entity.

        Args:
            entity_id: Entity to get context for

        Returns:
            List of related entities
        """
        try:
            related = await find_related_entities(entity_id=entity_id, limit=20)
            logger.debug(f"Agent {self.agent_id} got {len(related)} related entities")
            return related

        except Exception as e:
            logger.warning(f"Failed to get context for {entity_id}: {e}")
            return []

    # ========== STATISTICS & MONITORING ==========

    def get_statistics(self) -> Dict[str, int]:
        """Get agent coordination statistics.

        Returns:
            Statistics dict
        """
        return self.statistics.copy()

    async def shutdown(self) -> None:
        """Graceful shutdown - report final status.

        Should be called when agent is stopping.
        """
        # Report idle status
        await self.report_status(load=0.0, metrics={"status": "shutdown"})

        # Log final statistics
        stats = self.get_statistics()
        logger.info(
            f"Agent {self.agent_id} shutdown: {stats}"
        )
