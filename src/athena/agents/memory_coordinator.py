"""Memory Coordinator Agent - Autonomously decides when and what to remember.

The Memory Coordinator Agent observes work happening in the session and makes
intelligent decisions about what's worth storing in memory. It acts like the
memory-management skill, but proactively rather than waiting for user requests.

This agent runs continuously during the session, analyzing:
- Tool executions and their outcomes
- User interactions and context
- Patterns and repeated behaviors
- Learning moments and insights

Decision Logic:
1. Novelty Check: Is this information new or already stored?
2. Importance Assessment: Will this matter in future sessions?
3. Memory Type Selection: Where should it go (episodic, semantic, procedural)?
4. Storage: Call appropriate memory operations
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

# Import coordinator base class
from .coordinator import AgentCoordinator

# Import core memory operations
from ..episodic.operations import remember as remember_event
from ..memory.operations import store as store_fact
from ..procedural.operations import extract_procedure as extract_proc

logger = logging.getLogger(__name__)


class MemoryCoordinatorAgent(AgentCoordinator):
    """Autonomously manages memory storage decisions.

    Inherits from AgentCoordinator to coordinate with other agents via shared memory.
    """

    def __init__(self):
        """Initialize the Memory Coordinator Agent."""
        super().__init__(
            agent_id="memory-coordinator",
            agent_type="memory-coordinator",
        )
        self.decisions_made = 0
        self.memories_stored = 0
        self.skipped = 0

    async def should_remember(self, context: Dict[str, Any]) -> bool:
        """Decide if context is worth storing.

        Args:
            context: Dictionary with 'content', 'type', 'importance' keys

        Returns:
            True if worth storing, False otherwise
        """
        # Check for required fields
        if not context.get("content"):
            return False

        # Skip very short content (likely noise)
        if len(str(context.get("content", ""))) < 10:
            self.skipped += 1
            return False

        # Check importance threshold
        importance = float(context.get("importance", 0.5))
        if importance < 0.3:
            self.skipped += 1
            return False

        # If it's an error, always remember
        if context.get("type") == "error":
            return True

        # If it's a completion, check if it's novel
        if context.get("type") == "completion":
            return await self._check_novelty(context)

        # Default: remember if above threshold
        return importance > 0.5

    async def _check_novelty(self, context: Dict[str, Any]) -> bool:
        """Check if this is new information via semantic search.

        Queries semantic memory to detect potential duplicates.

        Args:
            context: Context to check

        Returns:
            True if novel, False if likely duplicate
        """
        content = str(context.get("content", ""))
        if not content:
            return False

        try:
            # Query semantic memory for similar content
            from ..memory.operations import search as search_semantic
            similar = await search_semantic(content, limit=1)

            # If we find something with high confidence, it's not novel
            if similar and len(similar) > 0:
                first_result = similar[0]
                confidence = first_result.get("confidence", 0.0)
                # If confidence > 0.8, consider it a duplicate
                if confidence > 0.8:
                    logger.debug(f"Duplicate detected (confidence={confidence})")
                    return False

            return True
        except Exception as e:
            logger.warning(f"Novelty check failed: {e}, assuming novel")
            return True

    async def choose_memory_type(self, context: Dict[str, Any]) -> Optional[str]:
        """Choose memory layer (episodic, semantic, procedural).

        Args:
            context: Context to categorize

        Returns:
            Memory type: 'episodic', 'semantic', 'procedural', or None
        """
        event_type = context.get("type", "")
        content = str(context.get("content", "")).lower()

        # Decision logic based on content and type
        if event_type == "error" or event_type == "failure":
            # Failures are episodic (learn what went wrong)
            return "episodic"

        if "learned" in content or "pattern" in content or "discovered" in content:
            # Learning moments are semantic (general knowledge)
            return "semantic"

        if event_type == "completion" and "task" in content.lower():
            # Task completions could reveal procedures
            return "episodic"  # Store as episode first, extract procedure later

        if event_type == "workflow" or "workflow" in content:
            # Workflows are procedural
            return "procedural"

        # Default: store as episodic event
        return "episodic"

    async def coordinate_storage(
        self, context: Dict[str, Any]
    ) -> Optional[str]:
        """Coordinate memory storage decision and execution.

        This is the main entry point for the agent. Given a context,
        it decides what to store and where and calls the appropriate
        memory operations to actually store it.

        Args:
            context: Context with 'content', 'type', 'importance', etc.

        Returns:
            Memory ID if stored, None otherwise
        """
        self.decisions_made += 1

        # Step 1: Should we remember?
        if not await self.should_remember(context):
            logger.debug(
                f"Coordinator decided to skip (importance={context.get('importance', 0.5)})"
            )
            return None

        # Step 2: Choose memory type
        memory_type = await self.choose_memory_type(context)
        if not memory_type:
            logger.debug("Coordinator could not determine memory type")
            return None

        # Step 3: Store the memory in appropriate layer
        try:
            content = context.get("content", "")
            importance = float(context.get("importance", 0.5))
            tags = context.get("tags", [])
            source = context.get("source", "coordinator")

            memory_id = None

            if memory_type == "episodic":
                # Store as episodic event
                memory_id = await remember_event(
                    content=content,
                    context={"original_type": context.get("type")},
                    tags=tags,
                    source=source,
                    importance=importance,
                )
                logger.info(
                    f"Coordinator stored episodic memory: {memory_id}"
                )

            elif memory_type == "semantic":
                # Store as semantic fact
                memory_id = await store_fact(
                    content=content,
                    topics=tags,
                    confidence=importance,
                )
                logger.info(
                    f"Coordinator stored semantic memory: {memory_id}"
                )

            elif memory_type == "procedural":
                # Note: procedural extraction happens from episodic events
                # Store as episodic first, then consolidation extracts procedures
                memory_id = await remember_event(
                    content=content,
                    context={"original_type": "workflow"},
                    tags=tags + ["workflow"],
                    source=source,
                    importance=importance,
                )
                logger.info(
                    f"Coordinator stored procedural source (episodic): {memory_id}"
                )

            if memory_id:
                self.memories_stored += 1
                logger.info(
                    f"Coordinator decided: {memory_type} memory for {context.get('type')} -> {memory_id}"
                )

                # Emit event for other agents to observe
                try:
                    await self.emit_event(
                        event_type="memory_stored",
                        content=f"Stored {memory_type} memory: {content[:100]}...",
                        tags=[memory_type, "memory_coordination"],
                        importance=importance,
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit event: {e}")

                # Share knowledge if semantic memory
                if memory_type == "semantic" and importance > 0.7:
                    try:
                        await self.share_knowledge(
                            content=content,
                            topics=tags,
                            confidence=importance,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to share knowledge: {e}")

                return memory_id
            else:
                logger.warning(f"Failed to store {memory_type} memory")
                return None

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return None

    def get_statistics(self) -> Dict[str, int]:
        """Get agent statistics.

        Returns:
            Dictionary with decisions_made, memories_stored, skipped
        """
        return {
            "decisions_made": self.decisions_made,
            "memories_stored": self.memories_stored,
            "skipped": self.skipped,
        }


# Singleton instance
_coordinator: Optional[MemoryCoordinatorAgent] = None


def get_coordinator() -> MemoryCoordinatorAgent:
    """Get or create the Memory Coordinator Agent singleton.

    Returns:
        MemoryCoordinatorAgent instance
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = MemoryCoordinatorAgent()
    return _coordinator


async def coordinate_memory_storage(context: Dict[str, Any]) -> Optional[str]:
    """Convenience function to coordinate memory storage.

    Args:
        context: Context with memory details

    Returns:
        Memory ID if stored, None otherwise
    """
    coordinator = get_coordinator()
    return await coordinator.coordinate_storage(context)
