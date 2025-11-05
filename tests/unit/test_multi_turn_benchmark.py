"""Tests for multi-turn conversation benchmarking."""

import pytest

from athena.evaluation.multi_turn_benchmark import (
    ConversationTurn,
    ConversationTurnData,
    MultiTurnBenchmarkEvaluator,
    MultiTurnBenchmarkSuite,
    MultiTurnConversation,
    RecallType,
)
from athena.memory.store import MemoryStore


@pytest.fixture
def benchmark_suite():
    """Fixture providing benchmark suite."""
    return MultiTurnBenchmarkSuite()


@pytest.fixture
def memory_store(tmp_path):
    """Fixture providing memory store."""
    return MemoryStore(tmp_path / "memory.db")


@pytest.fixture
def evaluator(memory_store):
    """Fixture providing benchmark evaluator."""
    return MultiTurnBenchmarkEvaluator(memory_store)


class TestBenchmarkSuite:
    """Tests for MultiTurnBenchmarkSuite."""

    def test_suite_loads_standard_conversations(self, benchmark_suite):
        """Test that suite loads standard conversations."""
        conversations = benchmark_suite.list_conversations()
        assert len(conversations) > 0
        assert "technical_long_retention" in conversations
        assert "multi_domain_context_switch" in conversations
        assert "information_update_handling" in conversations

    def test_get_conversation(self, benchmark_suite):
        """Test retrieving conversation by ID."""
        conv = benchmark_suite.get_conversation("technical_long_retention")
        assert conv is not None
        assert conv.name == "Technical Long-Term Retention"
        assert len(conv.turns) > 0

    def test_add_custom_conversation(self, benchmark_suite):
        """Test adding custom conversation."""
        custom_conv = MultiTurnConversation(
            conversation_id="custom_test",
            name="Custom Test",
            description="Test conversation",
            category="test",
            difficulty="easy",
            turns=[
                ConversationTurnData(
                    turn_id=1,
                    turn_type=ConversationTurn.STATEMENT,
                    content="Test statement",
                ),
            ],
        )
        benchmark_suite.add_conversation(custom_conv)

        retrieved = benchmark_suite.get_conversation("custom_test")
        assert retrieved is not None
        assert retrieved.name == "Custom Test"

    def test_conversation_structure(self, benchmark_suite):
        """Test structure of conversation."""
        conv = benchmark_suite.get_conversation("technical_long_retention")

        # Check basic properties
        assert conv.conversation_id == "technical_lr_001"
        assert conv.category == "technical"
        assert conv.difficulty == "hard"

        # Check turns
        assert len(conv.turns) > 0
        for turn in conv.turns:
            assert hasattr(turn, "turn_id")
            assert hasattr(turn, "turn_type")
            assert hasattr(turn, "content")


class TestConversationTurns:
    """Tests for conversation turns."""

    def test_statement_turn(self):
        """Test creating statement turn."""
        turn = ConversationTurnData(
            turn_id=1,
            turn_type=ConversationTurn.STATEMENT,
            content="Here is information",
        )
        assert turn.turn_type == ConversationTurn.STATEMENT
        assert turn.content == "Here is information"

    def test_question_turn(self):
        """Test creating question turn with expected recall."""
        turn = ConversationTurnData(
            turn_id=2,
            turn_type=ConversationTurn.QUESTION,
            content="What did I say?",
            expected_recall=["information"],
            recall_type=RecallType.SEMANTIC,
        )
        assert turn.turn_type == ConversationTurn.QUESTION
        assert turn.expected_recall == ["information"]
        assert turn.recall_type == RecallType.SEMANTIC

    def test_turn_types(self):
        """Test all turn types are defined."""
        turn_types = [
            ConversationTurn.STATEMENT,
            ConversationTurn.QUESTION,
            ConversationTurn.UPDATE,
            ConversationTurn.INFERENCE,
            ConversationTurn.RECALL,
        ]
        assert len(turn_types) == 5

    def test_recall_types(self):
        """Test all recall types are defined."""
        recall_types = [
            RecallType.EXACT,
            RecallType.SEMANTIC,
            RecallType.INFERRED,
            RecallType.TEMPORAL,
        ]
        assert len(recall_types) == 4


class TestBenchmarkEvaluator:
    """Tests for MultiTurnBenchmarkEvaluator."""

    def test_evaluator_initialization(self, evaluator):
        """Test evaluator initializes with memory store."""
        assert evaluator.store is not None
        assert evaluator.suite is not None
        assert len(evaluator.suite.list_conversations()) > 0

    def test_evaluate_conversation(self, evaluator):
        """Test evaluating single conversation."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        result = evaluator.evaluate_conversation(conv)

        assert result.conversation_id == "technical_lr_001"
        assert result.total_turns == len(conv.turns)
        assert result.evaluated_turns > 0
        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.precision <= 1.0
        assert 0.0 <= result.success_rate <= 1.0

    def test_evaluation_results_structure(self, evaluator):
        """Test structure of evaluation results."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        result = evaluator.evaluate_conversation(conv)

        # Check turn results
        for turn_result in result.turn_results:
            assert turn_result.turn_id > 0
            assert turn_result.turn_type in ConversationTurn.__members__.values()
            assert 0.0 <= turn_result.accuracy <= 1.0
            assert 0.0 <= turn_result.precision <= 1.0
            assert isinstance(turn_result.success, bool)

    def test_evaluate_all(self, evaluator):
        """Test evaluating all standard conversations."""
        results = evaluator.evaluate_all()

        assert len(results) > 0
        for conv_id, evaluation in results.items():
            # evaluation.conversation_id is the internal ID, conv_id is the dict key
            # They might not match, but both should exist
            assert evaluation.conversation_id is not None
            assert evaluation.total_turns > 0

    def test_summarize_results(self, evaluator):
        """Test summarizing evaluation results."""
        results = evaluator.evaluate_all()
        summary = evaluator.summarize_results(results)

        assert "total_conversations_evaluated" in summary
        assert "average_accuracy" in summary
        assert "average_precision" in summary
        assert "average_success_rate" in summary
        assert "conversations" in summary

        # Check summary statistics are valid
        assert summary["total_conversations_evaluated"] == len(results)
        assert 0.0 <= summary["average_accuracy"] <= 1.0
        assert 0.0 <= summary["average_precision"] <= 1.0
        assert 0.0 <= summary["average_success_rate"] <= 1.0

    def test_empty_results_summary(self, evaluator):
        """Test summarizing empty results."""
        summary = evaluator.summarize_results({})
        assert summary == {}

    def test_breakdown_by_recall_type(self, evaluator):
        """Test breakdown by recall type."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        result = evaluator.evaluate_conversation(conv)

        # Check breakdown structure
        assert "by_recall_type" in result.__dict__
        for recall_type_str, metrics in result.by_recall_type.items():
            assert "accuracy" in metrics
            assert "precision" in metrics
            assert "success_rate" in metrics
            assert "count" in metrics

    def test_breakdown_by_difficulty(self, evaluator):
        """Test breakdown by difficulty."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        result = evaluator.evaluate_conversation(conv)

        # Check breakdown structure
        assert "by_difficulty" in result.__dict__
        assert conv.difficulty in result.by_difficulty
        metrics = result.by_difficulty[conv.difficulty]
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "success_rate" in metrics


class TestConversationEvaluation:
    """Tests for ConversationEvaluation."""

    def test_evaluation_to_dict(self, evaluator):
        """Test converting evaluation to dictionary."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        evaluation = evaluator.evaluate_conversation(conv)

        result_dict = evaluation.to_dict()

        assert "conversation_id" in result_dict
        assert "conversation_name" in result_dict
        assert "total_turns" in result_dict
        assert "accuracy" in result_dict
        assert "precision" in result_dict
        assert "success_rate" in result_dict
        assert "turn_results" in result_dict
        assert isinstance(result_dict["turn_results"], list)

    def test_evaluation_serialization(self, evaluator):
        """Test that evaluation can be serialized."""
        conv = evaluator.suite.get_conversation("technical_long_retention")
        evaluation = evaluator.evaluate_conversation(conv)

        # Should be convertible to JSON
        result_dict = evaluation.to_dict()

        # All string and number values
        assert isinstance(result_dict["conversation_id"], str)
        assert isinstance(result_dict["accuracy"], float)
        assert isinstance(result_dict["turn_results"], list)


class TestMultiDomainConversation:
    """Tests for multi-domain conversation."""

    def test_multi_domain_conversation_setup(self, evaluator):
        """Test that multi-domain conversation is properly set up."""
        conv = evaluator.suite.get_conversation("multi_domain_context_switch")

        assert conv.category == "multi-domain"
        # Should have turns from different domains
        assert any(t.content.lower().count("rust") > 0 for t in conv.turns)
        assert any(t.content.lower().count("agile") > 0 for t in conv.turns)
        assert any(t.content.lower().count("hiking") > 0 for t in conv.turns)

    def test_multi_domain_evaluation(self, evaluator):
        """Test evaluating multi-domain conversation."""
        conv = evaluator.suite.get_conversation("multi_domain_context_switch")
        result = evaluator.evaluate_conversation(conv)

        assert result.evaluated_turns > 0
        # Should test context switching ability
        assert result.by_recall_type is not None


class TestInformationUpdateHandling:
    """Tests for information update handling."""

    def test_information_update_conversation(self, evaluator):
        """Test that update conversation is properly set up."""
        conv = evaluator.suite.get_conversation("information_update_handling")

        # Should have UPDATE turns
        update_turns = [
            t for t in conv.turns
            if t.turn_type == ConversationTurn.UPDATE
        ]
        assert len(update_turns) > 0

    def test_update_memory_handling(self, evaluator):
        """Test evaluating memory with updates."""
        conv = evaluator.suite.get_conversation("information_update_handling")
        result = evaluator.evaluate_conversation(conv)

        assert result.evaluated_turns > 0
        # Should correctly handle information updates
        # (i.e., remember new values, not old ones)


class TestBenchmarkFidelity:
    """Tests for benchmark fidelity and properties."""

    def test_all_conversations_have_turns(self, benchmark_suite):
        """Test that all conversations have turns."""
        for conv_id in benchmark_suite.list_conversations():
            conv = benchmark_suite.get_conversation(conv_id)
            assert len(conv.turns) > 0

    def test_conversations_have_questions(self, benchmark_suite):
        """Test that conversations include question turns."""
        for conv_id in benchmark_suite.list_conversations():
            conv = benchmark_suite.get_conversation(conv_id)
            question_turns = [
                t for t in conv.turns
                if t.turn_type in (
                    ConversationTurn.QUESTION,
                    ConversationTurn.INFERENCE,
                    ConversationTurn.RECALL,
                )
            ]
            assert len(question_turns) > 0

    def test_question_turns_have_expected_recall(self, benchmark_suite):
        """Test that question turns have expected recall items."""
        for conv_id in benchmark_suite.list_conversations():
            conv = benchmark_suite.get_conversation(conv_id)
            for turn in conv.turns:
                if turn.turn_type == ConversationTurn.QUESTION:
                    assert turn.expected_recall is not None
                    assert len(turn.expected_recall) > 0

    def test_difficulty_values_valid(self, benchmark_suite):
        """Test that difficulty values are valid."""
        valid_difficulties = {"easy", "medium", "hard"}
        for conv_id in benchmark_suite.list_conversations():
            conv = benchmark_suite.get_conversation(conv_id)
            assert conv.difficulty in valid_difficulties
