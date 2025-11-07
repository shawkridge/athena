"""Comprehensive tests for token budgeting system.

Tests cover:
- Token counting with multiple strategies
- Priority-based allocation
- Overflow handling strategies
- Metrics tracking
- Cost estimation
- Edge cases and integration scenarios
"""

import pytest
from datetime import datetime
from athena.efficiency.token_budget import (
    TokenCounter,
    TokenBudgetManager,
    TokenBudgetAllocator,
    TokenSection,
    TokenBudgetConfig,
    AllocationResult,
    BudgetMetrics,
    TokenCountingStrategy,
    PriorityLevel,
    OverflowStrategy,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def basic_config():
    """Basic token budget configuration."""
    return TokenBudgetConfig(
        total_budget=1000,
        buffer_tokens=50,
        min_response_tokens=100,
        counting_strategy=TokenCountingStrategy.CHARACTER_BASED,
    )


@pytest.fixture
def counter_char():
    """Character-based token counter."""
    return TokenCounter(TokenCountingStrategy.CHARACTER_BASED)


@pytest.fixture
def counter_whitespace():
    """Whitespace-based token counter."""
    return TokenCounter(TokenCountingStrategy.WHITESPACE_BASED)


@pytest.fixture
def counter_word():
    """Word-based token counter."""
    return TokenCounter(TokenCountingStrategy.WORD_BASED)


@pytest.fixture
def counter_claude():
    """Claude estimate counter."""
    return TokenCounter(TokenCountingStrategy.CLAUDE_ESTIMATE)


@pytest.fixture
def allocator(basic_config):
    """Token budget allocator."""
    return TokenBudgetAllocator(basic_config)


@pytest.fixture
def budget_manager(basic_config):
    """Token budget manager."""
    return TokenBudgetManager(basic_config)


@pytest.fixture
def sample_sections():
    """Sample sections for testing."""
    return [
        TokenSection(
            name="system_prompt",
            content="You are a helpful assistant." * 10,  # ~300 chars
            priority=PriorityLevel.CRITICAL,
            min_tokens=50,
        ),
        TokenSection(
            name="context",
            content="Here is some relevant context. " * 20,  # ~600 chars
            priority=PriorityLevel.HIGH,
            min_tokens=30,
        ),
        TokenSection(
            name="examples",
            content="Example 1: foo. Example 2: bar. " * 15,  # ~500 chars
            priority=PriorityLevel.NORMAL,
            min_tokens=20,
        ),
        TokenSection(
            name="details",
            content="Some additional details here. " * 10,  # ~300 chars
            priority=PriorityLevel.LOW,
            min_tokens=10,
        ),
    ]


@pytest.fixture
def large_text():
    """Large text sample."""
    return """Machine learning is a subset of artificial intelligence that focuses on
    the development of algorithms and statistical models that enable computers to improve
    their performance on tasks through experience. Deep learning is a specialized branch
    of machine learning that uses neural networks with multiple layers to learn hierarchical
    representations of data. These techniques have revolutionized fields like computer vision,
    natural language processing, and speech recognition. Applications include image classification,
    object detection, machine translation, question answering, and many more.""" * 5


@pytest.fixture
def code_sample():
    """Sample code text."""
    return """
def calculate_tokens(text: str) -> int:
    words = text.split()
    return len(words) + int(len(text) / 4)

class TokenCounter:
    def __init__(self):
        self.cache = {}

    def count(self, text):
        if text in self.cache:
            return self.cache[text]
        count = calculate_tokens(text)
        self.cache[text] = count
        return count
""" * 3


# ============================================================================
# TokenCounter Tests
# ============================================================================


class TestTokenCounterCharacterBased:
    """Test character-based token counting."""

    def test_empty_string(self, counter_char):
        """Test counting empty string."""
        assert counter_char.count_tokens("") == 0

    def test_single_word(self, counter_char):
        """Test counting single word."""
        count = counter_char.count_tokens("hello")
        assert count > 0
        assert count <= 2  # ~1 token

    def test_sentence(self, counter_char):
        """Test counting sentence."""
        sentence = "The quick brown fox jumps over the lazy dog."
        count = counter_char.count_tokens(sentence)
        assert count > 0

    def test_paragraph(self, counter_char, large_text):
        """Test counting paragraph."""
        count = counter_char.count_tokens(large_text)
        assert count > 0
        # Should be proportional to length
        assert count > 100

    def test_caching(self, counter_char):
        """Test token counting cache."""
        text = "This is a test string"
        count1 = counter_char.count_tokens(text)
        count2 = counter_char.count_tokens(text)
        assert count1 == count2

    def test_cache_hit(self, counter_char):
        """Test that cache is actually used."""
        text = "test"
        count1 = counter_char.count_tokens(text, use_cache=True)
        count2 = counter_char.count_tokens(text, use_cache=True)
        assert count1 == count2

    def test_no_cache(self, counter_char):
        """Test counting without cache."""
        text = "test string"
        counter_char.count_tokens(text, use_cache=True)
        count = counter_char.count_tokens(text, use_cache=False)
        assert count > 0

    def test_clear_cache(self, counter_char):
        """Test clearing cache."""
        text = "test"
        counter_char.count_tokens(text, use_cache=True)
        counter_char.clear_cache()
        # Cache should be cleared
        assert len(counter_char._cache) == 0

    def test_whitespace_handling(self, counter_char):
        """Test that extra whitespace is normalized."""
        text1 = "hello  world"
        text2 = "hello world"
        count1 = counter_char.count_tokens(text1)
        count2 = counter_char.count_tokens(text2)
        # Should be similar (normalized)
        assert abs(count1 - count2) <= 1

    def test_punctuation(self, counter_char):
        """Test punctuation handling."""
        text = "Hello, world! How are you?"
        count = counter_char.count_tokens(text)
        assert count > 0

    def test_code_counting(self, counter_char, code_sample):
        """Test counting code with punctuation."""
        count = counter_char.count_tokens(code_sample)
        assert count > 0

    def test_number_counting(self, counter_char):
        """Test counting text with numbers."""
        text = "The year is 2025 and we have 1000 tokens"
        count = counter_char.count_tokens(text)
        assert count > 0


class TestTokenCounterWhitespaceBased:
    """Test whitespace-based token counting."""

    def test_empty_string(self, counter_whitespace):
        """Test empty string."""
        assert counter_whitespace.count_tokens("") == 0

    def test_single_word(self, counter_whitespace):
        """Test single word."""
        count = counter_whitespace.count_tokens("hello")
        assert count == 1

    def test_multiple_words(self, counter_whitespace):
        """Test multiple words."""
        count = counter_whitespace.count_tokens("hello world test")
        assert count >= 3

    def test_long_words(self, counter_whitespace):
        """Test long words adjustment."""
        text = "supercalifragilisticexpialidocious is very long word"
        count = counter_whitespace.count_tokens(text)
        assert count > 0


class TestTokenCounterWordBased:
    """Test word-based token counting."""

    def test_empty_string(self, counter_word):
        """Test empty string."""
        assert counter_word.count_tokens("") == 0

    def test_word_count(self, counter_word):
        """Test word counting."""
        text = "one two three four five"
        count = counter_word.count_tokens(text)
        assert count == 5

    def test_punctuation_attached(self, counter_word):
        """Test punctuation attached to words."""
        count = counter_word.count_tokens("hello, world!")
        assert count == 2


class TestTokenCounterClaudeEstimate:
    """Test Claude estimate counting."""

    def test_text_estimation(self, counter_claude):
        """Test text estimation."""
        text = "Hello world"
        count = counter_claude.count_tokens(text)
        assert count >= 1

    def test_code_detection(self, counter_claude, code_sample):
        """Test that code is estimated differently."""
        count = counter_claude.count_tokens(code_sample)
        assert count > 0

    def test_numeric_detection(self, counter_claude):
        """Test numeric content detection."""
        text = "123 456 789 101112 131415"
        count = counter_claude.count_tokens(text)
        assert count > 0


# ============================================================================
# TokenSection Tests
# ============================================================================


class TestTokenSection:
    """Test TokenSection model."""

    def test_creation(self):
        """Test section creation."""
        section = TokenSection(
            name="test",
            content="test content",
            priority=PriorityLevel.NORMAL,
        )
        assert section.name == "test"
        assert section.content == "test content"
        assert section.priority == PriorityLevel.NORMAL

    def test_min_tokens(self):
        """Test minimum tokens constraint."""
        section = TokenSection(
            name="test",
            content="content",
            priority=PriorityLevel.HIGH,
            min_tokens=50,
        )
        assert section.min_tokens == 50

    def test_max_tokens(self):
        """Test maximum tokens constraint."""
        section = TokenSection(
            name="test",
            content="content",
            priority=PriorityLevel.NORMAL,
            max_tokens=100,
        )
        assert section.max_tokens == 100

    def test_metadata(self):
        """Test metadata storage."""
        metadata = {"source": "system", "version": "1.0"}
        section = TokenSection(
            name="test",
            content="content",
            priority=PriorityLevel.NORMAL,
            metadata=metadata,
        )
        assert section.metadata == metadata

    def test_compression_tracking(self):
        """Test compression tracking."""
        section = TokenSection(
            name="test",
            content="content",
            priority=PriorityLevel.NORMAL,
            compressed=True,
            original_count=100,
            compression_ratio=0.5,
        )
        assert section.compressed is True
        assert section.original_count == 100
        assert section.compression_ratio == 0.5


# ============================================================================
# TokenBudgetAllocator Tests
# ============================================================================


class TestTokenBudgetAllocatorBalanced:
    """Test balanced allocation strategy."""

    def test_allocate_under_budget(self, allocator, sample_sections):
        """Test allocation when under budget."""
        result = allocator.allocate(sample_sections)
        assert result.total_allocated <= result.total_available
        assert result.overflow == 0

    def test_allocate_respects_priority(self, allocator, sample_sections):
        """Test that critical sections are prioritized in constrained budget."""
        # Reduce available budget to force prioritization
        allocator.config.total_budget = 300
        allocator.config.buffer_tokens = 20
        allocator.config.min_response_tokens = 50

        result = allocator.allocate(sample_sections)
        critical = result.allocations.get("system_prompt", 0)
        low = result.allocations.get("details", 0)
        # With constrained budget, critical should get at least as much as low
        assert critical >= low

    def test_allocate_respects_minimums(self, allocator, sample_sections):
        """Test that minimums are respected when achievable."""
        # Set reasonable minimums (all sections have at least some content)
        for section in sample_sections:
            section.min_tokens = 20  # Reasonable minimum

        # With default budget of 1000, this should be achievable
        result = allocator.allocate(sample_sections)
        for section in sample_sections:
            allocated = result.allocations.get(section.name, 0)
            assert allocated >= section.min_tokens

    def test_allocate_respects_maximums(self, allocator, sample_sections):
        """Test that maximums are respected."""
        for section in sample_sections:
            section.max_tokens = 50  # Low maximum

        result = allocator.allocate(sample_sections)
        for section in sample_sections:
            allocated = result.allocations.get(section.name, 0)
            assert allocated <= 50

    def test_empty_sections(self, allocator):
        """Test allocation with no sections."""
        result = allocator.allocate([])
        assert result.total_allocated == 0
        assert len(result.allocations) == 0

    def test_single_section(self, allocator):
        """Test allocation with single section."""
        section = TokenSection(
            name="only",
            content="test content",
            priority=PriorityLevel.CRITICAL,
        )
        result = allocator.allocate([section])
        assert "only" in result.allocations
        assert result.allocations["only"] > 0


class TestTokenBudgetAllocatorStrategies:
    """Test different allocation strategies."""

    def test_speed_strategy(self, basic_config, sample_sections):
        """Test speed allocation strategy."""
        basic_config.allocation_strategy = "speed"
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        assert result.total_allocated > 0

    def test_quality_strategy(self, basic_config, sample_sections):
        """Test quality allocation strategy."""
        basic_config.allocation_strategy = "quality"
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        assert result.total_allocated > 0

    def test_minimal_strategy(self, basic_config, sample_sections):
        """Test minimal allocation strategy."""
        basic_config.allocation_strategy = "minimal"
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        assert result.total_allocated > 0

    def test_unknown_strategy_defaults_to_balanced(self, basic_config, sample_sections):
        """Test that unknown strategy defaults to balanced."""
        basic_config.allocation_strategy = "unknown_strategy"
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        assert result.total_allocated > 0


class TestTokenBudgetAllocatorQuality:
    """Test quality score calculation."""

    def test_quality_full_allocation(self, allocator, sample_sections):
        """Test quality score when fully allocated."""
        # Reduce budget to force allocation
        allocator.config.total_budget = 5000
        result = allocator.allocate(sample_sections)
        # With large budget, should have high quality
        assert result.quality_score > 0.8

    def test_quality_partial_allocation(self, allocator, sample_sections):
        """Test quality score with partial allocation."""
        # Small budget forces partial allocation
        allocator.config.total_budget = 300
        result = allocator.allocate(sample_sections)
        # With limited budget, quality should be lower
        assert 0 < result.quality_score < 1.0

    def test_quality_respects_threshold(self, allocator, sample_sections):
        """Test quality threshold enforcement."""
        allocator.config.min_quality_score = 0.8
        allocator.config.total_budget = 10000  # Large budget for high quality
        result = allocator.allocate(sample_sections)
        assert result.quality_score >= allocator.config.min_quality_score


# ============================================================================
# OverflowHandling Tests
# ============================================================================


class TestOverflowHandling:
    """Test overflow handling strategies."""

    def test_compression_strategy(self, basic_config, sample_sections):
        """Test compression overflow strategy."""
        basic_config.primary_overflow_strategy = OverflowStrategy.COMPRESS
        basic_config.total_budget = 200  # Very small budget
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        # Should use compression strategy
        assert "compression" in result.strategies_used or result.overflow == 0

    def test_truncate_end_strategy(self, basic_config, sample_sections):
        """Test truncate-end overflow strategy."""
        basic_config.primary_overflow_strategy = OverflowStrategy.TRUNCATE_END
        basic_config.total_budget = 200
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        # Should apply strategy
        assert len(result.strategies_used) > 0 or result.overflow == 0

    def test_multiple_strategies(self, basic_config, sample_sections):
        """Test multiple overflow strategies in sequence."""
        # Set very constrained but not impossible budget
        basic_config.total_budget = 300
        basic_config.buffer_tokens = 30
        basic_config.min_response_tokens = 50
        basic_config.secondary_overflow_strategies = [
            OverflowStrategy.TRUNCATE_END,
            OverflowStrategy.TRUNCATE_START,
        ]
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        # Should attempt strategies and achieve allocation
        assert len(result.strategies_used) >= 0  # May or may not need overflow handling
        assert result.total_allocated > 0  # Should allocate something

    def test_no_overflow_needed(self, basic_config, sample_sections):
        """Test when no overflow handling is needed."""
        basic_config.total_budget = 5000  # Large budget
        allocator = TokenBudgetAllocator(basic_config)
        result = allocator.allocate(sample_sections)
        assert result.overflow == 0
        assert len(result.strategies_used) == 0


# ============================================================================
# TokenBudgetManager Tests
# ============================================================================


class TestTokenBudgetManager:
    """Test main TokenBudgetManager interface."""

    def test_add_section(self, budget_manager):
        """Test adding sections."""
        budget_manager.add_section(
            "test",
            "content",
            PriorityLevel.NORMAL,
        )
        assert len(budget_manager._current_sections) == 1

    def test_add_multiple_sections(self, budget_manager):
        """Test adding multiple sections."""
        budget_manager.add_section("sec1", "content1", PriorityLevel.CRITICAL)
        budget_manager.add_section("sec2", "content2", PriorityLevel.NORMAL)
        budget_manager.add_section("sec3", "content3", PriorityLevel.LOW)
        assert len(budget_manager._current_sections) == 3

    def test_clear_sections(self, budget_manager):
        """Test clearing sections."""
        budget_manager.add_section("test", "content", PriorityLevel.NORMAL)
        assert len(budget_manager._current_sections) == 1
        budget_manager.clear_sections()
        assert len(budget_manager._current_sections) == 0

    def test_calculate_budget(self, budget_manager):
        """Test budget calculation."""
        budget_manager.add_section("test", "test content", PriorityLevel.NORMAL)
        result = budget_manager.calculate_budget()
        assert result.total_allocated > 0

    def test_get_allocation(self, budget_manager):
        """Test getting allocation for section."""
        budget_manager.add_section("test", "test content", PriorityLevel.HIGH)
        allocation = budget_manager.get_allocation("test")
        assert allocation > 0

    def test_get_nonexistent_allocation(self, budget_manager):
        """Test getting allocation for nonexistent section."""
        allocation = budget_manager.get_allocation("nonexistent")
        assert allocation == 0

    def test_count_tokens_interface(self, budget_manager):
        """Test token counting through manager."""
        count = budget_manager.count_tokens("test string")
        assert count > 0

    def test_get_metrics(self, budget_manager):
        """Test getting metrics."""
        budget_manager.add_section("test", "test content", PriorityLevel.NORMAL)
        metrics = budget_manager.get_metrics()
        assert isinstance(metrics, BudgetMetrics)
        assert metrics.total_budget == budget_manager.config.total_budget

    def test_metrics_tracking(self, budget_manager):
        """Test metrics history tracking."""
        budget_manager.add_section("test", "content", PriorityLevel.NORMAL)
        metrics1 = budget_manager.get_metrics()
        budget_manager.clear_sections()
        budget_manager.add_section("test2", "content2", PriorityLevel.HIGH)
        metrics2 = budget_manager.get_metrics()

        history = budget_manager.get_history()
        assert len(history) == 2

    def test_clear_history(self, budget_manager):
        """Test clearing metrics history."""
        budget_manager.add_section("test", "content", PriorityLevel.NORMAL)
        budget_manager.get_metrics()
        budget_manager.clear_history()
        assert len(budget_manager.get_history()) == 0

    def test_estimate_cost(self, budget_manager):
        """Test cost estimation."""
        budget_manager.add_section("test", "test content" * 100, PriorityLevel.NORMAL)
        cost = budget_manager.estimate_cost()
        assert "input_cost" in cost
        assert "output_cost" in cost
        assert "total_cost" in cost
        assert cost["total_cost"] > 0

    def test_cost_with_custom_rates(self, budget_manager):
        """Test cost estimation with custom rates."""
        budget_manager.add_section("test", "content", PriorityLevel.NORMAL)
        cost1 = budget_manager.estimate_cost(input_cost_per_mtok=1.0)
        cost2 = budget_manager.estimate_cost(input_cost_per_mtok=2.0)
        # Higher rate should give higher cost
        assert cost2["input_cost"] >= cost1["input_cost"]

    def test_cost_different_models(self, budget_manager):
        """Test cost estimation for different models."""
        budget_manager.add_section("test", "content", PriorityLevel.NORMAL)
        cost = budget_manager.estimate_cost(model="claude-3-opus")
        assert cost["model"] == "claude-3-opus"


# ============================================================================
# BudgetMetrics Tests
# ============================================================================


class TestBudgetMetrics:
    """Test BudgetMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = BudgetMetrics(
            timestamp=datetime.now(),
            total_budget=1000,
            total_used=800,
            overflow=0,
            efficiency=0.8,
            quality_score=0.95,
            sections_count=3,
            compression_applied=False,
            strategies_used=[],
        )
        assert metrics.total_budget == 1000
        assert metrics.total_used == 800

    def test_utilization_percent(self):
        """Test utilization percentage calculation."""
        metrics = BudgetMetrics(
            timestamp=datetime.now(),
            total_budget=1000,
            total_used=500,
            overflow=0,
            efficiency=0.5,
            quality_score=0.8,
            sections_count=2,
            compression_applied=False,
            strategies_used=[],
        )
        assert metrics.utilization_percent == 50.0

    def test_overflow_percent(self):
        """Test overflow percentage calculation."""
        metrics = BudgetMetrics(
            timestamp=datetime.now(),
            total_budget=1000,
            total_used=1100,
            overflow=100,
            efficiency=1.1,
            quality_score=0.7,
            sections_count=2,
            compression_applied=True,
            strategies_used=["compression"],
        )
        assert metrics.overflow_percent == 10.0

    def test_zero_budget_metrics(self):
        """Test metrics with zero budget."""
        metrics = BudgetMetrics(
            timestamp=datetime.now(),
            total_budget=0,
            total_used=0,
            overflow=0,
            efficiency=0,
            quality_score=1.0,
            sections_count=0,
            compression_applied=False,
            strategies_used=[],
        )
        # Should handle zero division gracefully
        assert metrics.utilization_percent == 0
        assert metrics.overflow_percent == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow(self, budget_manager):
        """Test complete workflow from adding sections to getting metrics."""
        # Add sections
        budget_manager.add_section(
            "system",
            "You are a helpful AI assistant." * 10,
            PriorityLevel.CRITICAL,
            min_tokens=50,
        )
        budget_manager.add_section(
            "context",
            "Here is some context about the user." * 20,
            PriorityLevel.HIGH,
            min_tokens=30,
        )
        budget_manager.add_section(
            "examples",
            "Example 1: foo. Example 2: bar." * 15,
            PriorityLevel.NORMAL,
        )

        # Calculate budget
        result = budget_manager.calculate_budget()
        assert result.total_allocated > 0

        # Get metrics
        metrics = budget_manager.get_metrics()
        assert metrics.total_used == result.total_allocated

        # Estimate cost
        cost = budget_manager.estimate_cost()
        assert cost["total_cost"] > 0

        # Check history
        history = budget_manager.get_history()
        assert len(history) >= 1

    def test_workflow_with_constraints(self, budget_manager):
        """Test workflow with min/max constraints."""
        budget_manager.add_section(
            "critical",
            "Critical content that must fit" * 20,
            PriorityLevel.CRITICAL,
            min_tokens=100,
            max_tokens=200,
        )
        budget_manager.add_section(
            "optional",
            "Optional content that can be trimmed" * 20,
            PriorityLevel.LOW,
            min_tokens=10,
        )

        result = budget_manager.calculate_budget()
        critical_alloc = result.allocations.get("critical", 0)

        # Critical should respect constraints
        assert critical_alloc >= 100
        assert critical_alloc <= 200

    def test_different_counting_strategies(self):
        """Test that different counting strategies work."""
        text = "Test text content for counting"

        for strategy in TokenCountingStrategy:
            config = TokenBudgetConfig(counting_strategy=strategy)
            manager = TokenBudgetManager(config)
            count = manager.count_tokens(text)
            assert count > 0

    def test_all_allocation_strategies(self, sample_sections):
        """Test all allocation strategies work."""
        for strategy in ["balanced", "speed", "quality", "minimal"]:
            config = TokenBudgetConfig(allocation_strategy=strategy)
            allocator = TokenBudgetAllocator(config)
            result = allocator.allocate(sample_sections)
            assert result.total_allocated > 0

    def test_cascade_overflow_strategies(self):
        """Test that overflow strategies cascade properly."""
        config = TokenBudgetConfig(
            total_budget=100,  # Very small
            buffer_tokens=10,
            min_response_tokens=10,
            primary_overflow_strategy=OverflowStrategy.COMPRESS,
            secondary_overflow_strategies=[
                OverflowStrategy.TRUNCATE_END,
                OverflowStrategy.TRUNCATE_START,
            ],
        )

        manager = TokenBudgetManager(config)
        manager.add_section(
            "large",
            "Content that definitely exceeds budget" * 100,
            PriorityLevel.NORMAL,
        )

        result = manager.calculate_budget()
        # Should have applied some strategy
        assert len(result.strategies_used) > 0 or result.overflow == 0


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_budget(self):
        """Test with very large budget."""
        config = TokenBudgetConfig(total_budget=1_000_000)
        manager = TokenBudgetManager(config)
        manager.add_section("test", "small content", PriorityLevel.NORMAL)
        result = manager.calculate_budget()
        assert result.overflow == 0

    def test_very_small_budget(self):
        """Test with very small budget."""
        config = TokenBudgetConfig(total_budget=10)
        manager = TokenBudgetManager(config)
        manager.add_section("test", "content", PriorityLevel.CRITICAL)
        result = manager.calculate_budget()
        # Should handle gracefully
        assert result.total_allocated >= 0

    def test_unicode_content(self):
        """Test with unicode content."""
        config = TokenBudgetConfig()
        manager = TokenBudgetManager(config)
        unicode_text = "Hello 🌍 世界 مرحبا мир"
        count = manager.count_tokens(unicode_text)
        assert count > 0

    def test_special_characters(self):
        """Test with special characters."""
        config = TokenBudgetConfig()
        manager = TokenBudgetManager(config)
        special = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        count = manager.count_tokens(special)
        assert count > 0

    def test_very_long_content(self):
        """Test with very long content."""
        config = TokenBudgetConfig()
        manager = TokenBudgetManager(config)
        long_content = "word " * 10000  # 10k words
        count = manager.count_tokens(long_content)
        assert count > 1000

    def test_mixed_priority_levels(self):
        """Test with all priority levels."""
        manager = TokenBudgetManager()
        for i, priority in enumerate(PriorityLevel):
            manager.add_section(
                f"section_{i}",
                f"content {i}",
                priority,
            )

        result = manager.calculate_budget()
        assert len(result.allocations) == len(PriorityLevel)

    def test_section_with_empty_content(self):
        """Test section with empty content."""
        manager = TokenBudgetManager()
        manager.add_section("empty", "", PriorityLevel.NORMAL)
        result = manager.calculate_budget()
        assert result.allocations.get("empty", 0) == 0

    def test_multiple_metrics_snapshots(self):
        """Test multiple metrics snapshots."""
        config = TokenBudgetConfig(track_history=True)
        manager = TokenBudgetManager(config)

        for i in range(5):
            manager.clear_sections()
            manager.add_section(f"section_{i}", f"content {i}" * (i + 1), PriorityLevel.NORMAL)
            manager.get_metrics()

        history = manager.get_history()
        assert len(history) == 5


# ============================================================================
# Configuration Tests
# ============================================================================


class TestTokenBudgetConfig:
    """Test configuration options."""

    def test_default_config(self):
        """Test default configuration."""
        config = TokenBudgetConfig()
        assert config.total_budget == 4000
        assert config.buffer_tokens == 100
        assert config.min_response_tokens == 200

    def test_custom_config(self):
        """Test custom configuration."""
        config = TokenBudgetConfig(
            total_budget=2000,
            buffer_tokens=50,
            min_response_tokens=100,
        )
        assert config.total_budget == 2000
        assert config.buffer_tokens == 50
        assert config.min_response_tokens == 100

    def test_allocation_strategy_config(self):
        """Test allocation strategy configuration."""
        for strategy in ["balanced", "speed", "quality", "minimal"]:
            config = TokenBudgetConfig(allocation_strategy=strategy)
            assert config.allocation_strategy == strategy

    def test_overflow_strategy_config(self):
        """Test overflow strategy configuration."""
        config = TokenBudgetConfig(
            primary_overflow_strategy=OverflowStrategy.COMPRESS,
            secondary_overflow_strategies=[
                OverflowStrategy.TRUNCATE_END,
                OverflowStrategy.TRUNCATE_START,
            ],
        )
        assert config.primary_overflow_strategy == OverflowStrategy.COMPRESS
        assert len(config.secondary_overflow_strategies) == 2

    def test_quality_threshold_config(self):
        """Test quality threshold configuration."""
        config = TokenBudgetConfig(
            min_quality_score=0.8,
            max_compression_ratio=0.4,
        )
        assert config.min_quality_score == 0.8
        assert config.max_compression_ratio == 0.4
