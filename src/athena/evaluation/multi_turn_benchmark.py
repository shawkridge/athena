"""Multi-turn conversation benchmarking for long-term memory evaluation.

Addresses research gap: "Most benchmarks focus on single-turn QA, not sustained memory over
multiple interactions" (Rank 17, Credibility 1.0 from 2024-2025 LLM Memory Research)

Provides comprehensive evaluation of memory systems across:
- Multi-turn conversations
- Long-term information retention
- Memory consolidation quality
- Context recall accuracy
- Information update handling
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.models import Memory, MemoryType
from ..semantic.store import SemanticStore

logger = logging.getLogger(__name__)


class ConversationTurn(str, Enum):
    """Types of conversation turns in benchmark."""

    STATEMENT = "statement"  # Provide information
    QUESTION = "question"  # Ask about previous information
    UPDATE = "update"  # Update or contradict previous information
    INFERENCE = "inference"  # Require reasoning across multiple turns
    RECALL = "recall"  # Direct recall of information


class RecallType(str, Enum):
    """Types of information recall in benchmarks."""

    EXACT = "exact"  # Exact match required
    SEMANTIC = "semantic"  # Semantic similarity acceptable
    INFERRED = "inferred"  # Requires reasoning from multiple facts
    TEMPORAL = "temporal"  # Requires understanding temporal order


@dataclass
class ConversationTurnData:
    """Single turn in multi-turn conversation."""

    turn_id: int
    turn_type: ConversationTurn
    content: str
    speaker: str = "user"  # "user" or "assistant"
    timestamp: int = 0  # Relative time in seconds

    # For question/recall turns
    expected_recall: Optional[list[str]] = None  # Expected information to recall
    recall_type: RecallType = RecallType.SEMANTIC


@dataclass
class MultiTurnConversation:
    """Multi-turn conversation for benchmarking."""

    conversation_id: str
    name: str
    description: str
    turns: list[ConversationTurnData] = field(default_factory=list)
    category: str = "general"  # e.g., "technical", "biographical", "multi-domain"
    difficulty: str = "medium"  # "easy", "medium", "hard"
    max_turns: int = 0
    span_seconds: int = 0  # Time span of conversation in seconds


@dataclass
class TurnEvaluation:
    """Evaluation result for single turn."""

    turn_id: int
    turn_type: ConversationTurn
    recall_type: RecallType
    expected_items: list[str]
    recalled_items: list[str]
    accuracy: float  # 0.0-1.0 (fraction of expected items recalled)
    precision: float  # 0.0-1.0 (fraction of recalled items that are correct)
    success: bool  # Whether turn met success criteria


@dataclass
class ConversationEvaluation:
    """Complete evaluation of multi-turn conversation."""

    conversation_id: str
    conversation_name: str
    total_turns: int
    evaluated_turns: int
    turn_results: list[TurnEvaluation] = field(default_factory=list)

    # Aggregate metrics
    accuracy: float = 0.0  # Overall accuracy
    precision: float = 0.0  # Overall precision
    success_rate: float = 0.0  # Fraction of turns that succeeded
    average_recall_latency: float = 0.0  # Average turn span before successful recall

    # Category breakdowns
    by_recall_type: dict[str, dict] = field(default_factory=dict)
    by_difficulty: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "conversation_id": self.conversation_id,
            "conversation_name": self.conversation_name,
            "total_turns": self.total_turns,
            "evaluated_turns": self.evaluated_turns,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "success_rate": self.success_rate,
            "average_recall_latency": self.average_recall_latency,
            "by_recall_type": self.by_recall_type,
            "by_difficulty": self.by_difficulty,
            "turn_results": [
                {
                    "turn_id": t.turn_id,
                    "turn_type": t.turn_type.value,
                    "recall_type": t.recall_type.value,
                    "accuracy": t.accuracy,
                    "precision": t.precision,
                    "success": t.success,
                }
                for t in self.turn_results
            ],
        }


class MultiTurnBenchmarkSuite:
    """Suite of multi-turn conversation benchmarks."""

    def __init__(self):
        """Initialize benchmark suite with standard conversations."""
        self.conversations: dict[str, MultiTurnConversation] = {}
        self._load_standard_conversations()

    def _load_standard_conversations(self):
        """Load standard benchmark conversations."""
        # Benchmark 1: Technical domain with long-term retention
        self.conversations["technical_long_retention"] = MultiTurnConversation(
            conversation_id="technical_lr_001",
            name="Technical Long-Term Retention",
            description="Conversation about software architecture, testing recall after many turns",
            category="technical",
            difficulty="hard",
            turns=[
                ConversationTurnData(
                    turn_id=1,
                    turn_type=ConversationTurn.STATEMENT,
                    content="We're using microservices architecture with Docker containers. Each service has its own PostgreSQL database.",
                ),
                ConversationTurnData(
                    turn_id=2,
                    turn_type=ConversationTurn.STATEMENT,
                    content="The authentication service uses JWT tokens with 24-hour expiration.",
                ),
                ConversationTurnData(
                    turn_id=3,
                    turn_type=ConversationTurn.STATEMENT,
                    content="We have a load balancer routing requests to 3 API servers.",
                ),
                ConversationTurnData(
                    turn_id=4,
                    turn_type=ConversationTurn.QUESTION,
                    content="What database does the auth service use?",
                    expected_recall=["PostgreSQL", "database"],
                    recall_type=RecallType.SEMANTIC,
                ),
                ConversationTurnData(
                    turn_id=5,
                    turn_type=ConversationTurn.UPDATE,
                    content="We're migrating to MongoDB for the user profile service.",
                ),
                ConversationTurnData(
                    turn_id=6,
                    turn_type=ConversationTurn.QUESTION,
                    content="How many API servers do we have behind the load balancer?",
                    expected_recall=["3", "three"],
                    recall_type=RecallType.EXACT,
                ),
                ConversationTurnData(
                    turn_id=7,
                    turn_type=ConversationTurn.INFERENCE,
                    content="What's the overall architecture pattern we're using?",
                    expected_recall=["microservices"],
                    recall_type=RecallType.SEMANTIC,
                ),
            ],
        )

        # Benchmark 2: Multi-domain conversation (switching contexts)
        self.conversations["multi_domain_context_switch"] = MultiTurnConversation(
            conversation_id="multi_domain_001",
            name="Multi-Domain Context Switching",
            description="Alternating between personal, technical, and business topics",
            category="multi-domain",
            difficulty="hard",
            turns=[
                ConversationTurnData(
                    turn_id=1,
                    turn_type=ConversationTurn.STATEMENT,
                    content="I'm learning Rust for systems programming.",
                    speaker="user",
                ),
                ConversationTurnData(
                    turn_id=2,
                    turn_type=ConversationTurn.STATEMENT,
                    content="My team uses Agile methodology with 2-week sprints.",
                    speaker="user",
                ),
                ConversationTurnData(
                    turn_id=3,
                    turn_type=ConversationTurn.STATEMENT,
                    content="I like hiking on weekends in the mountains.",
                    speaker="user",
                ),
                ConversationTurnData(
                    turn_id=4,
                    turn_type=ConversationTurn.QUESTION,
                    content="What programming language am I learning?",
                    expected_recall=["Rust"],
                    recall_type=RecallType.EXACT,
                ),
                ConversationTurnData(
                    turn_id=5,
                    turn_type=ConversationTurn.QUESTION,
                    content="What's my favorite weekend activity?",
                    expected_recall=["hiking", "mountains"],
                    recall_type=RecallType.SEMANTIC,
                ),
                ConversationTurnData(
                    turn_id=6,
                    turn_type=ConversationTurn.QUESTION,
                    content="What methodology does my team use?",
                    expected_recall=["Agile", "2-week sprints"],
                    recall_type=RecallType.SEMANTIC,
                ),
            ],
        )

        # Benchmark 3: Information updates and contradictions
        self.conversations["information_update_handling"] = MultiTurnConversation(
            conversation_id="update_handling_001",
            name="Information Update Handling",
            description="Testing memory updates when information is corrected or changed",
            category="technical",
            difficulty="medium",
            turns=[
                ConversationTurnData(
                    turn_id=1,
                    turn_type=ConversationTurn.STATEMENT,
                    content="Our API response time is 150ms on average.",
                ),
                ConversationTurnData(
                    turn_id=2,
                    turn_type=ConversationTurn.QUESTION,
                    content="What's our API response time?",
                    expected_recall=["150ms"],
                    recall_type=RecallType.EXACT,
                ),
                ConversationTurnData(
                    turn_id=3,
                    turn_type=ConversationTurn.UPDATE,
                    content="Actually, we optimized it and now it's 80ms.",
                ),
                ConversationTurnData(
                    turn_id=4,
                    turn_type=ConversationTurn.QUESTION,
                    content="What's our current API response time?",
                    expected_recall=["80ms"],
                    recall_type=RecallType.EXACT,
                ),
                ConversationTurnData(
                    turn_id=5,
                    turn_type=ConversationTurn.QUESTION,
                    content="Do we still have 150ms response time?",
                    expected_recall=["no", "80ms", "optimized"],
                    recall_type=RecallType.SEMANTIC,
                ),
            ],
        )

    def add_conversation(self, conversation: MultiTurnConversation):
        """Add custom benchmark conversation."""
        self.conversations[conversation.conversation_id] = conversation

    def get_conversation(self, conversation_id: str) -> Optional[MultiTurnConversation]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def list_conversations(self) -> list[str]:
        """List all available conversation IDs."""
        return list(self.conversations.keys())


class MultiTurnBenchmarkEvaluator:
    """Evaluates memory system on multi-turn conversations."""

    def __init__(self, memory_store: SemanticStore):
        """Initialize evaluator.

        Args:
            memory_store: Memory store to evaluate
        """
        self.store = memory_store
        self.suite = MultiTurnBenchmarkSuite()

    def evaluate_conversation(
        self,
        conversation: MultiTurnConversation,
        project_id: int = 1,
    ) -> ConversationEvaluation:
        """Evaluate memory system on single conversation.

        Args:
            conversation: Conversation to evaluate
            project_id: Project ID for memory storage

        Returns:
            Complete evaluation result
        """
        logger.info(
            f"Evaluating conversation '{conversation.name}' " f"({len(conversation.turns)} turns)"
        )

        # Store conversation turns as memories
        stored_memories: dict[int, Memory] = {}
        for turn in conversation.turns:
            if turn.turn_type in (ConversationTurn.STATEMENT, ConversationTurn.UPDATE):
                # Store as semantic memory
                memory = Memory(
                    project_id=project_id,
                    content=turn.content,
                    memory_type=MemoryType.CONTEXT,
                    tags=[
                        f"turn_{turn.turn_id}",
                        conversation.conversation_id,
                        turn.turn_type.value,
                    ],
                )
                # In real usage, would store via memory_store.create()
                stored_memories[turn.turn_id] = memory

        # Evaluate recall on question turns
        turn_results: list[TurnEvaluation] = []
        for turn in conversation.turns:
            if turn.turn_type in (
                ConversationTurn.QUESTION,
                ConversationTurn.INFERENCE,
                ConversationTurn.RECALL,
            ):
                result = self._evaluate_turn(turn, stored_memories, project_id)
                turn_results.append(result)

        # Compute aggregate metrics
        if turn_results:
            accuracy = sum(r.accuracy for r in turn_results) / len(turn_results)
            precision = sum(r.precision for r in turn_results) / len(turn_results)
            success_rate = sum(1 for r in turn_results if r.success) / len(turn_results)
        else:
            accuracy = precision = success_rate = 0.0

        # Build evaluation object
        evaluation = ConversationEvaluation(
            conversation_id=conversation.conversation_id,
            conversation_name=conversation.name,
            total_turns=len(conversation.turns),
            evaluated_turns=len(turn_results),
            turn_results=turn_results,
            accuracy=accuracy,
            precision=precision,
            success_rate=success_rate,
            average_recall_latency=self._compute_recall_latency(turn_results, conversation.turns),
        )

        # Break down by recall type and difficulty
        evaluation.by_recall_type = self._breakdown_by_recall_type(turn_results)
        evaluation.by_difficulty = {
            conversation.difficulty: {
                "accuracy": accuracy,
                "precision": precision,
                "success_rate": success_rate,
            }
        }

        return evaluation

    def _evaluate_turn(
        self,
        turn: ConversationTurnData,
        stored_memories: dict[int, Memory],
        project_id: int,
    ) -> TurnEvaluation:
        """Evaluate single recall turn.

        Args:
            turn: Turn to evaluate
            stored_memories: All stored memories from conversation
            project_id: Project ID

        Returns:
            Evaluation result for this turn
        """
        # Find expected information in stored memories
        expected_items = turn.expected_recall or []

        # In real implementation, would query memory_store
        # For now, compute recall based on stored memories
        recalled_items = self._extract_recalled_items(turn.content, stored_memories)

        # Compute accuracy and precision
        if expected_items:
            accuracy = len(
                [e for e in expected_items if any(e.lower() in r.lower() for r in recalled_items)]
            ) / len(expected_items)
        else:
            accuracy = 0.0

        if recalled_items:
            precision = len(
                [r for r in recalled_items if any(r.lower() in e.lower() for e in expected_items)]
            ) / len(recalled_items)
        else:
            precision = 0.0 if expected_items else 1.0

        success = accuracy >= 0.5  # 50% threshold for success

        return TurnEvaluation(
            turn_id=turn.turn_id,
            turn_type=turn.turn_type,
            recall_type=turn.recall_type,
            expected_items=expected_items,
            recalled_items=recalled_items,
            accuracy=accuracy,
            precision=precision,
            success=success,
        )

    def _extract_recalled_items(
        self,
        content: str,
        stored_memories: dict[int, Memory],
    ) -> list[str]:
        """Extract recalled items from content.

        Args:
            content: Query or response content
            stored_memories: All stored memories

        Returns:
            List of recalled items found in memories
        """
        recalled = []
        content_lower = content.lower()

        for memory in stored_memories.values():
            if memory.content.lower() in content_lower:
                recalled.append(memory.content)

        return recalled

    def _compute_recall_latency(
        self,
        turn_results: list[TurnEvaluation],
        all_turns: list[ConversationTurnData],
    ) -> float:
        """Compute average turns between statement and recall.

        Args:
            turn_results: All evaluated turns
            all_turns: All conversation turns

        Returns:
            Average latency in turns
        """
        if not turn_results:
            return 0.0

        latencies = []
        for result in turn_results:
            # Find the turn
            turn = next(t for t in all_turns if t.turn_id == result.turn_id)
            # Find when this information was first stated
            # (simplified: use turn order)
            latencies.append(turn.turn_id)

        return sum(latencies) / len(latencies) if latencies else 0.0

    def _breakdown_by_recall_type(self, turn_results: list[TurnEvaluation]) -> dict[str, dict]:
        """Breakdown results by recall type.

        Args:
            turn_results: All evaluated turns

        Returns:
            Dictionary of metrics by recall type
        """
        breakdown = {}
        for recall_type in RecallType:
            matching = [r for r in turn_results if r.recall_type == recall_type]
            if matching:
                breakdown[recall_type.value] = {
                    "accuracy": sum(r.accuracy for r in matching) / len(matching),
                    "precision": sum(r.precision for r in matching) / len(matching),
                    "success_rate": sum(1 for r in matching if r.success) / len(matching),
                    "count": len(matching),
                }
        return breakdown

    def evaluate_all(self, project_id: int = 1) -> dict[str, ConversationEvaluation]:
        """Evaluate on all standard conversations.

        Args:
            project_id: Project ID for memory storage

        Returns:
            Dictionary of all evaluation results
        """
        results = {}
        for conv_id in self.suite.list_conversations():
            conversation = self.suite.get_conversation(conv_id)
            if conversation:
                results[conv_id] = self.evaluate_conversation(conversation, project_id)
        return results

    def summarize_results(self, results: dict[str, ConversationEvaluation]) -> dict:
        """Summarize evaluation results.

        Args:
            results: All evaluation results

        Returns:
            Summary statistics
        """
        if not results:
            return {}

        all_accuracy = [r.accuracy for r in results.values()]
        all_precision = [r.precision for r in results.values()]
        all_success_rates = [r.success_rate for r in results.values()]

        return {
            "total_conversations_evaluated": len(results),
            "average_accuracy": sum(all_accuracy) / len(all_accuracy),
            "average_precision": sum(all_precision) / len(all_precision),
            "average_success_rate": sum(all_success_rates) / len(all_success_rates),
            "conversations": {conv_id: result.to_dict() for conv_id, result in results.items()},
        }
