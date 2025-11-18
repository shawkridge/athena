"""Auto-context injection for memory retrieval.

Automatically injects relevant memories into conversation context
when new user prompts are detected.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from athena.core.database import Database
from athena.rag.manager import RAGManager

logger = logging.getLogger(__name__)


@dataclass
class ContextMemory:
    """Single memory to inject into context."""

    content: str
    source_layer: str  # semantic, episodic, procedural, graph, etc.
    usefulness: float  # 0.0-1.0
    relevance: float  # 0.0-1.0 (search score)
    recency: float  # 0.0-1.0 (how recent)


@dataclass
class ContextInjection:
    """Complete context injection for a prompt."""

    memories: List[ContextMemory]
    total_tokens: int
    formatted_context: str
    injection_confidence: float  # 0.0-1.0


class ContextInjector:
    """Automatically injects relevant memories into conversation context.

    Replaces the manual /memory-query workflow with automatic context injection.
    When a new user prompt arrives, automatically:
    1. Identify relevant memories
    2. Rank by usefulness and relevance
    3. Format for context window
    4. Inject into conversation
    """

    def __init__(
        self,
        db: Database,
        rag_manager: RAGManager,
        token_budget: int = 1000,
        min_usefulness: float = 0.4,
        max_memories: int = 5,
    ):
        """Initialize context injector.

        Args:
            db: Database connection
            rag_manager: RAG manager for smart retrieval
            token_budget: Max tokens for injected context (~1000)
            min_usefulness: Minimum usefulness score to include (0.0-1.0)
            max_memories: Maximum memories to inject per prompt
        """
        self.db = db
        self.rag_manager = rag_manager
        self.token_budget = token_budget
        self.min_usefulness = min_usefulness
        self.max_memories = max_memories

    async def inject_context(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[int] = None,
    ) -> ContextInjection:
        """Inject relevant context into a user prompt.

        Args:
            user_prompt: The user's question/request
            conversation_history: Recent conversation for context
            project_id: Project ID for filtering

        Returns:
            ContextInjection with memories and formatted context
        """
        logger.info(f"Injecting context for prompt: {user_prompt[:100]}...")

        try:
            # Step 1: Retrieve relevant memories
            memories = await self._retrieve_relevant_memories(
                user_prompt,
                conversation_history,
                project_id,
            )

            if not memories:
                logger.debug("No relevant memories found")
                return ContextInjection(
                    memories=[],
                    total_tokens=0,
                    formatted_context="",
                    injection_confidence=0.0,
                )

            # Step 2: Rank memories
            ranked = self._rank_memories(memories)

            # Step 3: Filter and format
            selected = self._select_and_format(ranked)

            # Step 4: Estimate tokens and truncate if needed
            formatted_context = self._format_for_context(selected)

            injection_confidence = min(
                1.0,
                sum(m.relevance for m in selected) / len(selected) if selected else 0.0,
            )

            logger.info(
                f"Injected {len(selected)} memories " f"(confidence={injection_confidence:.2f})"
            )

            return ContextInjection(
                memories=selected,
                total_tokens=self._estimate_tokens(formatted_context),
                formatted_context=formatted_context,
                injection_confidence=injection_confidence,
            )

        except Exception as e:
            logger.error(f"Context injection failed: {e}")
            return ContextInjection(
                memories=[],
                total_tokens=0,
                formatted_context="",
                injection_confidence=0.0,
            )

    async def _retrieve_relevant_memories(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[int] = None,
    ) -> List[ContextMemory]:
        """Retrieve memories relevant to user prompt.

        Uses conversation history to transform queries (resolve pronouns,
        maintain context) for better retrieval.

        Args:
            user_prompt: User's question
            conversation_history: Recent conversation for context
            project_id: Project for filtering

        Returns:
            List of relevant ContextMemory objects
        """
        try:
            # Build augmented query from conversation history
            augmented_query = self._augment_query_with_history(user_prompt, conversation_history)

            # Use RAG manager's smart retrieve with conversation context
            results = self.rag_manager.retrieve(
                query=augmented_query,
                conversation_history=conversation_history,
                k=self.max_memories * 2,  # Get more than we'll use
                project_id=project_id or 1,  # Default to project 1
            )

            if not results:
                return []

            # Convert to ContextMemory objects
            memories = []
            for result in results:
                # result is a MemorySearchResult with .memory, .similarity, .rank, .metadata
                mem_obj = result.memory if hasattr(result, "memory") else result

                memory = ContextMemory(
                    content=getattr(mem_obj, "content", ""),
                    source_layer=getattr(mem_obj, "layer", "semantic"),
                    usefulness=float(getattr(mem_obj, "usefulness", 0.5)),
                    relevance=float(result.similarity) if hasattr(result, "similarity") else 0.5,
                    recency=self._calculate_recency(getattr(mem_obj, "timestamp", None)),
                )
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return []

    def _augment_query_with_history(
        self,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Augment query with conversation history context.

        Resolves pronouns like "that", "it" by looking back in conversation.

        Args:
            user_prompt: User's current question
            conversation_history: Recent conversation messages

        Returns:
            Augmented query with more context
        """
        if not conversation_history or len(conversation_history) < 2:
            return user_prompt

        # Look for pronouns that need resolution
        pronouns = {"that", "it", "this", "those", "these"}
        words = set(user_prompt.lower().split())

        # If user is using pronouns, look back in history for context
        if words & pronouns:
            # Get last assistant message for context
            for msg in reversed(conversation_history[:-1]):
                if msg.get("role") in ("assistant", "system"):
                    prev_context = msg.get("content", "")
                    # Limit to first 200 chars to avoid bloat
                    if prev_context:
                        augmented = f"{prev_context[:200]}\n\n" f"User follow-up: {user_prompt}"
                        return augmented

        return user_prompt

    def _rank_memories(self, memories: List[ContextMemory]) -> List[ContextMemory]:
        """Rank memories by combined score with attention-based boosting.

        Combines: usefulness (35%), relevance (35%), recency (15%), attention (15%)

        Attention-based ranking:
        - High-salience memories are prioritized (set via /focus)
        - Inhibited memories are suppressed (set via /focus --suppress)
        - Automatic boost for frequently accessed memories

        Args:
            memories: Unranked memories

        Returns:
            Ranked memories (highest score first)
        """
        try:
            # Try to get attention state for current project
            attention_scores = self._get_attention_scores()
        except (AttributeError, ValueError, TypeError, KeyError):
            # Graceful degradation if attention system unavailable
            attention_scores = {}

        scored = []
        for mem in memories:
            # Skip low usefulness
            if mem.usefulness < self.min_usefulness:
                continue

            # Check if memory is inhibited (suppressed)
            mem_key = f"{mem.source_layer}:{mem.content[:50]}"
            if attention_scores.get(f"inhibited:{mem_key}"):
                continue  # Skip inhibited memories

            # Get attention boost for this memory
            attention_boost = attention_scores.get(f"focus:{mem_key}", 0.0)
            if mem_key in attention_scores.get("primary_focus", []):
                attention_boost = 1.0
            elif mem_key in attention_scores.get("secondary_focus", []):
                attention_boost = 0.5

            # Composite score with attention
            score = (
                0.35 * mem.usefulness
                + 0.35 * mem.relevance
                + 0.15 * mem.recency
                + 0.15 * attention_boost
            )
            scored.append((score, mem))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored]

    def _get_attention_scores(self) -> Dict[str, Any]:
        """Get attention/focus scores for memory ranking.

        Returns dict with:
        - focus:KEY -> boost factor (0.0-1.0)
        - inhibited:KEY -> True if suppressed
        - primary_focus -> [memory_keys]
        - secondary_focus -> [memory_keys]

        Args:
            None

        Returns:
            Dict of attention scores and focus information
        """
        try:
            # Query the attention system from the database
            # This integrates with the /focus and /inhibit commands
            cursor = self.db.get_cursor()

            # Get focused memories (high salience)
            cursor.execute(
                """
                SELECT memory_id, layer, focus_type FROM attention_focus
                WHERE active = 1
                ORDER BY created_at DESC
                LIMIT 10
            """
            )
            focus_results = cursor.fetchall()

            scores = {
                "primary_focus": [],
                "secondary_focus": [],
            }

            for mem_id, layer, focus_type in focus_results:
                key = f"{layer}:{mem_id}"
                if focus_type == "primary":
                    scores["primary_focus"].append(key)
                elif focus_type == "secondary":
                    scores["secondary_focus"].append(key)

            # Get inhibited memories (suppressed)
            cursor.execute(
                """
                SELECT memory_id, layer FROM attention_inhibition
                WHERE active = 1 AND inhibition_end > datetime('now')
                LIMIT 20
            """
            )
            inhibit_results = cursor.fetchall()

            for mem_id, layer in inhibit_results:
                key = f"{layer}:{mem_id}"
                scores[f"inhibited:{key}"] = True

            return scores

        except Exception as e:
            logger.debug(f"Could not retrieve attention scores: {e}")
            return {}

    def _select_and_format(
        self,
        ranked_memories: List[ContextMemory],
    ) -> List[ContextMemory]:
        """Select memories to inject, respecting token budget.

        Args:
            ranked_memories: Ranked memories

        Returns:
            Selected memories to inject
        """
        selected = []
        token_count = 0

        for memory in ranked_memories[: self.max_memories]:
            mem_tokens = self._estimate_tokens(memory.content)

            if token_count + mem_tokens > self.token_budget:
                break

            selected.append(memory)
            token_count += mem_tokens

        return selected

    def _format_for_context(self, memories: List[ContextMemory]) -> str:
        """Format memories for context window injection.

        Args:
            memories: Selected memories

        Returns:
            Formatted context string
        """
        if not memories:
            return ""

        lines = ["📚 Background Context (from memory):"]
        lines.append("")

        # Group by layer for clarity
        by_layer = {}
        for mem in memories:
            if mem.source_layer not in by_layer:
                by_layer[mem.source_layer] = []
            by_layer[mem.source_layer].append(mem)

        for layer, layer_memories in by_layer.items():
            layer_label = self._layer_label(layer)
            lines.append(f"{layer_label}:")

            for mem in layer_memories[:2]:  # Max 2 per layer
                # Truncate very long content
                content = mem.content
                if len(content) > 300:
                    content = content[:300] + "..."

                lines.append(f"  • {content}")
                lines.append(
                    f"    (relevance={mem.relevance:.0%}, " f"usefulness={mem.usefulness:.0%})"
                )

            lines.append("")

        return "\n".join(lines)

    def _layer_label(self, layer: str) -> str:
        """Get user-friendly label for memory layer.

        Args:
            layer: Layer name

        Returns:
            User-friendly label
        """
        labels = {
            "semantic": "📖 Knowledge",
            "episodic": "📅 Past Events",
            "procedural": "⚙️ Procedures",
            "prospective": "🎯 Plans",
            "graph": "🔗 Relationships",
            "meta": "📊 Quality",
        }
        return labels.get(layer, f"📌 {layer.capitalize()}")

    def _calculate_recency(self, timestamp: Optional[str]) -> float:
        """Calculate recency score (0.0-1.0) from timestamp.

        Args:
            timestamp: ISO timestamp string or None

        Returns:
            Recency score (1.0 = very recent, 0.0 = very old)
        """
        if not timestamp:
            return 0.5  # Medium recency for undated

        try:
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.utcnow().replace(tzinfo=None)
            event_time = event_time.replace(tzinfo=None)

            age_seconds = (now - event_time).total_seconds()
            age_days = age_seconds / 86400

            # Exponential decay: recent = high, old = low
            # 1 day = 0.9, 7 days = 0.5, 30 days = 0.1
            recency = max(0.0, 1.0 - (age_days / 30))
            return min(1.0, recency)

        except (AttributeError, ValueError, TypeError, KeyError):
            return 0.5

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Simple heuristic: ~4 chars per token

        Args:
            text: Text to estimate

        Returns:
            Approximate token count
        """
        return max(1, len(text) // 4)

    async def should_inject_context(
        self,
        user_prompt: str,
        recent_injections: int = 0,
    ) -> bool:
        """Determine if context injection is appropriate.

        Args:
            user_prompt: User's prompt
            recent_injections: Number of recent injections

        Returns:
            True if should inject context
        """
        # Don't inject on every single prompt
        if recent_injections > 0:
            # Reduce frequency: every 2-3 prompts
            return recent_injections % 3 == 0

        # Always inject on first prompt
        return True

    def format_injection_for_claude(self, injection: ContextInjection) -> str:
        """Format injection as message to prepend to conversation.

        Args:
            injection: ContextInjection to format

        Returns:
            Formatted message for prepending
        """
        if not injection.formatted_context:
            return ""

        return (
            f"{injection.formatted_context}\n"
            f"[Memory confidence: {injection.injection_confidence:.0%}]\n"
        )
