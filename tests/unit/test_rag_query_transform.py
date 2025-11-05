"""Tests for query transformation."""

import pytest

from athena.rag.llm_client import LLMClient
from athena.rag.query_transform import (
    QueryTransformConfig,
    QueryTransformer,
    batch_transform,
)


class MockLLMClient(LLMClient):
    """Mock LLM that returns predictable transformations."""

    def __init__(self, response: str = "transformed query"):
        self.response = response
        self.generate_calls = []

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        self.generate_calls.append((prompt, max_tokens, temperature))
        return self.response

    def score_relevance(self, query: str, document: str) -> float:
        return 0.5


def test_query_transformer_basic():
    """Test basic query transformation."""
    mock_llm = MockLLMClient(response="What is the JWT token expiry for authentication?")
    transformer = QueryTransformer(mock_llm)

    history = [
        {"role": "user", "content": "How do we handle authentication?"},
        {"role": "assistant", "content": "We use JWT tokens with middleware."},
    ]

    query = "What's the expiry for those?"
    transformed = transformer.transform(query, history)

    # Check LLM was called
    assert len(mock_llm.generate_calls) == 1

    # Check result
    assert transformed == "What is the JWT token expiry for authentication?"


def test_query_transformer_no_history():
    """Test transformer returns query as-is when no history."""
    mock_llm = MockLLMClient()
    transformer = QueryTransformer(mock_llm)

    query = "What's the authentication method?"
    transformed = transformer.transform(query, conversation_history=None)

    # Should not call LLM
    assert len(mock_llm.generate_calls) == 0

    # Should return original query
    assert transformed == query


def test_query_transformer_no_pronouns():
    """Test transformer skips queries without pronouns."""
    mock_llm = MockLLMClient()
    transformer = QueryTransformer(mock_llm)

    history = [{"role": "user", "content": "Previous question"}]

    # Query with no pronouns or implicit references
    query = "How do we implement JWT authentication?"
    transformed = transformer.transform(query, history)

    # Should not call LLM (no transformation needed)
    assert len(mock_llm.generate_calls) == 0
    assert transformed == query


def test_needs_transformation_pronouns():
    """Test detection of pronouns."""
    transformer = QueryTransformer(MockLLMClient())

    # Pronouns that should trigger transformation
    assert transformer._needs_transformation("What does it do?")
    assert transformer._needs_transformation("How do I use that?")
    assert transformer._needs_transformation("Tell me about this")
    assert transformer._needs_transformation("Where are they stored?")
    assert transformer._needs_transformation("What about those files?")
    assert transformer._needs_transformation("Can you explain these?")


def test_needs_transformation_implicit_refs():
    """Test detection of implicit references."""
    transformer = QueryTransformer(MockLLMClient())

    # Implicit references that should trigger transformation
    assert transformer._needs_transformation("What does the function do?")
    assert transformer._needs_transformation("Where is the class defined?")
    assert transformer._needs_transformation("What's in the file?")
    assert transformer._needs_transformation("As mentioned earlier")
    assert transformer._needs_transformation("The same approach")
    assert transformer._needs_transformation("Like the previous example")


def test_needs_transformation_negative():
    """Test queries that don't need transformation."""
    transformer = QueryTransformer(MockLLMClient())

    # Self-contained queries
    assert not transformer._needs_transformation("How do we implement authentication?")
    assert not transformer._needs_transformation("Where is JWT configuration stored?")
    assert not transformer._needs_transformation("What are the available memory types?")


def test_format_history():
    """Test conversation history formatting."""
    transformer = QueryTransformer(MockLLMClient())

    history = [
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "user", "content": "Question 2"},
    ]

    formatted = transformer._format_history(history)

    assert "User: Question 1" in formatted
    assert "Assistant: Answer 1" in formatted
    assert "User: Question 2" in formatted


def test_format_history_truncates_long_messages():
    """Test that very long messages get truncated."""
    transformer = QueryTransformer(MockLLMClient())

    long_content = "x" * 500

    history = [{"role": "user", "content": long_content}]

    formatted = transformer._format_history(history)

    # Should be truncated to ~300 chars + "..."
    assert len(formatted) < 400
    assert "..." in formatted


def test_format_history_empty():
    """Test formatting empty history."""
    transformer = QueryTransformer(MockLLMClient())

    formatted = transformer._format_history([])

    assert formatted == "(no history)"


def test_query_transformer_max_history_turns():
    """Test limiting history to recent turns."""
    mock_llm = MockLLMClient(response="transformed")
    transformer = QueryTransformer(mock_llm)

    # Long history
    history = [
        {"role": "user", "content": f"Question {i}"}
        for i in range(10)
    ]

    query = "What about that?"
    transformer.transform(query, history, max_history_turns=2)

    # Check prompt only includes recent history
    prompt = mock_llm.generate_calls[0][0]

    # Should include last 4 messages (2 turns * 2 messages)
    assert "Question 9" in prompt
    assert "Question 8" in prompt
    assert "Question 7" in prompt
    assert "Question 6" in prompt

    # Should NOT include older messages
    assert "Question 0" not in prompt


def test_query_transformer_error_fallback():
    """Test transformer falls back to original query on error."""

    class FailingLLM(LLMClient):
        def generate(self, prompt, max_tokens=500, temperature=0.7):
            raise Exception("LLM error")

        def score_relevance(self, query, document):
            return 0.5

    transformer = QueryTransformer(FailingLLM())

    history = [{"role": "user", "content": "Previous question"}]
    query = "What about that?"

    # Should not crash, should return original query
    transformed = transformer.transform(query, history)

    assert transformed == query


def test_query_transform_config():
    """Test configuration object."""
    config = QueryTransformConfig(max_history_turns=5, temperature=0.1)

    assert config.max_history_turns == 5
    assert config.temperature == 0.1
    assert config.enabled is True


def test_query_transform_config_invalid_option(caplog):
    """Test config warns on invalid options."""
    config = QueryTransformConfig(invalid_option=True)

    assert "Unknown query transform config option" in caplog.text


def test_batch_transform():
    """Test batch query transformation."""
    mock_llm = MockLLMClient(response="transformed")
    transformer = QueryTransformer(mock_llm)

    queries = ["What about it?", "How does that work?"]
    histories = [
        [{"role": "user", "content": "Question 1"}],
        [{"role": "user", "content": "Question 2"}],
    ]

    results = batch_transform(transformer, queries, histories)

    assert len(results) == 2
    assert all(r == "transformed" for r in results)


def test_batch_transform_length_mismatch():
    """Test batch transform validates input lengths."""
    transformer = QueryTransformer(MockLLMClient())

    with pytest.raises(ValueError, match="Number of queries"):
        batch_transform(transformer, ["q1"], [[], []])


def test_query_transformer_preserves_context():
    """Test that conversation context is properly included."""
    mock_llm = MockLLMClient(response="transformed")
    transformer = QueryTransformer(mock_llm)

    history = [
        {"role": "user", "content": "Tell me about JWT authentication"},
        {"role": "assistant", "content": "JWT stands for JSON Web Token..."},
    ]

    query = "What's the expiry time for it?"
    transformer.transform(query, history)

    # Check that history was included in prompt
    prompt = mock_llm.generate_calls[0][0]

    assert "JWT authentication" in prompt
    assert "JSON Web Token" in prompt
    assert "What's the expiry time for it?" in prompt


def test_query_transformer_temperature():
    """Test that low temperature is used for consistency."""
    mock_llm = MockLLMClient(response="transformed")
    transformer = QueryTransformer(mock_llm)

    history = [{"role": "user", "content": "Previous"}]
    query = "What about that?"

    transformer.transform(query, history)

    # Check temperature parameter
    _, _, temperature = mock_llm.generate_calls[0]
    assert temperature == 0.3  # Low temp for consistent transformations
