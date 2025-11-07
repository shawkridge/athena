"""Advanced token budgeting system for managing LLM token allocation.

This module implements a sophisticated token budgeting system that:

1. **Accurate Token Counting**: Provides token counting for various input types
   - Text counting using multiple strategies (character-based, whitespace-based, LLM-aware)
   - Code token counting with syntax awareness
   - Structured data token estimation

2. **Priority-Based Allocation**: Intelligent allocation of tokens to sections
   - Hierarchical priority system (critical > high > normal > low)
   - Dynamic allocation based on importance and dependencies
   - Support for guaranteed minimums and hard caps

3. **Overflow Handling**: Multiple strategies to handle budget overruns
   - Compression-based reduction (remove low-priority tokens)
   - Truncation strategies (from start, from end, from middle)
   - Delegation (move content to other sections)
   - Quality degradation (reduce detail level)

4. **Metrics & Monitoring**: Track budget usage and efficiency
   - Real-time allocation tracking
   - Historical metrics and trends
   - Cost estimation for API calls
   - Quality impact assessment

5. **Multi-Strategy Support**: Different budgeting approaches
   - Balanced: Fair distribution with priority weighting
   - Speed: Optimize for fast responses
   - Quality: Prioritize best results
   - Minimal: Pack maximum content

Target Metrics:
- Token accuracy: Within 5% of actual
- Budget adherence: <5% overflow
- Allocation speed: <100ms for typical operations
- Cost estimation accuracy: Within 10% of actual
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class TokenCountingStrategy(Enum):
    """Different strategies for counting tokens."""

    CHARACTER_BASED = "character"      # ~4 characters per token
    WHITESPACE_BASED = "whitespace"    # Split on whitespace
    WORD_BASED = "word"                # Average word length
    CLAUDE_ESTIMATE = "claude"         # Claude's actual token counting


class PriorityLevel(Enum):
    """Priority levels for budget allocation."""

    CRITICAL = 5   # System prompt, critical context
    HIGH = 4       # Important context, query clarification
    NORMAL = 3     # Regular content, examples
    LOW = 2        # Supporting details, nice-to-have
    MINIMAL = 1    # Filler, can be removed first


class OverflowStrategy(Enum):
    """Strategies for handling budget overruns."""

    COMPRESS = "compress"              # Use compression to reduce size
    TRUNCATE_START = "truncate_start"  # Remove from beginning
    TRUNCATE_END = "truncate_end"      # Remove from end
    TRUNCATE_MIDDLE = "truncate_middle"# Remove from middle
    DELEGATE = "delegate"              # Move to lower-priority section
    DEGRADE = "degrade"                # Reduce detail level


@dataclass
class TokenSection:
    """Represents a section of the token budget."""

    name: str                           # Section identifier
    content: str                        # Actual content
    priority: PriorityLevel             # Priority level
    token_count: int = 0                # Calculated token count
    min_tokens: int = 0                 # Minimum tokens to preserve
    max_tokens: Optional[int] = None    # Hard limit for this section
    compressed: bool = False            # Whether content is compressed
    original_count: Optional[int] = None # Token count before compression
    compression_ratio: float = 1.0      # Ratio of compression applied
    metadata: Dict = field(default_factory=dict)  # Custom metadata


@dataclass
class TokenBudgetConfig:
    """Configuration for token budgeting."""

    # Budget limits
    total_budget: int = 4000            # Total tokens available
    buffer_tokens: int = 100            # Reserve tokens for safety
    min_response_tokens: int = 200      # Tokens reserved for response

    # Counting strategy
    counting_strategy: TokenCountingStrategy = TokenCountingStrategy.CHARACTER_BASED

    # Allocation strategy
    allocation_strategy: str = "balanced"  # balanced, speed, quality, minimal

    # Overflow handling
    primary_overflow_strategy: OverflowStrategy = OverflowStrategy.COMPRESS
    secondary_overflow_strategies: List[OverflowStrategy] = field(
        default_factory=lambda: [
            OverflowStrategy.TRUNCATE_END,
            OverflowStrategy.TRUNCATE_START,
            OverflowStrategy.DEGRADE
        ]
    )

    # Quality thresholds
    min_quality_score: float = 0.70     # Minimum acceptable quality
    max_compression_ratio: float = 0.3  # Don't compress below 30% of original

    # Behavior
    allow_overflow: bool = False        # Allow exceeding budget if necessary
    max_overflow_percent: float = 0.1   # Max 10% overflow if allowed
    track_history: bool = True          # Track allocation history

    # Performance
    cache_calculations: bool = True     # Cache token count calculations
    batch_size: int = 10                # Process sections in batches


@dataclass
class AllocationResult:
    """Result of token allocation."""

    allocations: Dict[str, int]         # Section name -> allocated tokens
    total_allocated: int                # Total tokens allocated
    total_available: int                # Total tokens available
    overflow: int                       # Tokens over budget (if any)
    quality_score: float                # Overall quality score (0-1)
    strategies_used: List[str]          # Strategies applied
    details: Dict = field(default_factory=dict)  # Additional details


@dataclass
class BudgetMetrics:
    """Metrics for token budget usage."""

    timestamp: datetime                 # When measured
    total_budget: int                   # Total budget
    total_used: int                     # Tokens used
    overflow: int                       # Tokens over budget
    efficiency: float                   # Tokens used / total budget
    quality_score: float                # Quality (0-1)
    sections_count: int                 # Number of sections
    compression_applied: bool           # Whether compression was used
    strategies_used: List[str]          # Strategies applied

    @property
    def utilization_percent(self) -> float:
        """Percentage of budget utilized."""
        return (self.total_used / self.total_budget * 100) if self.total_budget > 0 else 0

    @property
    def overflow_percent(self) -> float:
        """Percentage over budget."""
        return (self.overflow / self.total_budget * 100) if self.total_budget > 0 else 0


class TokenCounter:
    """Handles token counting with multiple strategies."""

    def __init__(self, strategy: TokenCountingStrategy = TokenCountingStrategy.CHARACTER_BASED):
        """Initialize token counter.

        Args:
            strategy: Strategy to use for counting
        """
        self.strategy = strategy
        self._cache: Dict[str, int] = {}

    def count_tokens(self, text: str, use_cache: bool = True) -> int:
        """Count tokens in text.

        Args:
            text: Text to count
            use_cache: Whether to use cached result

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Check cache
        if use_cache and text in self._cache:
            return self._cache[text]

        # Count based on strategy
        if self.strategy == TokenCountingStrategy.CHARACTER_BASED:
            count = self._count_character_based(text)
        elif self.strategy == TokenCountingStrategy.WHITESPACE_BASED:
            count = self._count_whitespace_based(text)
        elif self.strategy == TokenCountingStrategy.WORD_BASED:
            count = self._count_word_based(text)
        elif self.strategy == TokenCountingStrategy.CLAUDE_ESTIMATE:
            count = self._count_claude_estimate(text)
        else:
            count = self._count_character_based(text)

        # Cache result
        if use_cache:
            self._cache[text] = count

        return count

    def _count_character_based(self, text: str) -> int:
        """Count tokens using character-based estimation.

        Claude's tokenizer roughly maps ~4 characters to 1 token.
        Accounts for whitespace and punctuation separately.
        """
        # Remove excessive whitespace
        normalized = ' '.join(text.split())

        # Base: roughly 4 chars per token
        char_tokens = len(normalized) / 4

        # Add tokens for special structure
        newline_count = text.count('\n')
        tab_count = text.count('\t')
        punctuation_count = sum(1 for c in text if c in '.,!?;:()[]{}')

        # Punctuation and structure typically add 0.1-0.2 tokens each
        extra_tokens = (newline_count * 0.2 + tab_count * 0.15 + punctuation_count * 0.05)

        return max(1, int(char_tokens + extra_tokens))

    def _count_whitespace_based(self, text: str) -> int:
        """Count tokens using whitespace-based estimation.

        Simpler approach: count words as tokens, adjust for length.
        """
        words = text.split()
        if not words:
            return 0

        # Base count: one token per word
        base_count = len(words)

        # Adjustment for word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        adjustment = 0

        # Long words might be multiple tokens
        if avg_word_length > 8:
            adjustment = int(base_count * 0.15)

        return base_count + adjustment

    def _count_word_based(self, text: str) -> int:
        """Count tokens using word-based estimation."""
        words = text.split()
        return max(1, len(words))

    def _count_claude_estimate(self, text: str) -> int:
        """Claude's token counting estimate.

        This is a simplified version. In production, would use Claude's API.
        For now, uses a more sophisticated estimation.
        """
        # Use character-based as approximation for Claude
        char_count = len(text)

        # Claude tokenizer is more complex, but generally:
        # - Average: 4-5 characters per token
        # - But varies by content

        # Approximate based on character distribution
        # English text: ~4.5 chars per token
        # Code: ~3 chars per token (more punctuation)
        # Numbers: ~2 chars per token

        is_code = any(pattern in text for pattern in ['import ', 'def ', 'class ', 'async ', '://'])
        is_numeric = sum(c.isdigit() for c in text) / len(text) > 0.3 if text else False

        if is_code:
            base_ratio = 3.0
        elif is_numeric:
            base_ratio = 2.5
        else:
            base_ratio = 4.5

        return max(1, int(char_count / base_ratio))

    def clear_cache(self) -> None:
        """Clear token count cache."""
        self._cache.clear()


class TokenBudgetAllocator:
    """Allocates tokens to sections based on priority and strategy."""

    def __init__(self, config: TokenBudgetConfig):
        """Initialize allocator.

        Args:
            config: Budget configuration
        """
        self.config = config
        self.counter = TokenCounter(config.counting_strategy)

    def allocate(self, sections: List[TokenSection]) -> AllocationResult:
        """Allocate tokens to sections.

        Args:
            sections: List of sections to allocate

        Returns:
            Allocation result with assigned tokens per section
        """
        if not sections:
            return AllocationResult(
                allocations={},
                total_allocated=0,
                total_available=self._get_available_tokens(),
                overflow=0,
                quality_score=1.0,
                strategies_used=[]
            )

        # Calculate available tokens
        available = self._get_available_tokens()

        # Handle edge case: if available budget is zero or negative, allocate minimally
        if available <= 0:
            allocations = {}
            for section in sections:
                # Give at least 1 token if there's any space at all
                allocations[section.name] = max(1, min(1, available + 1))
            return AllocationResult(
                allocations=allocations,
                total_allocated=sum(allocations.values()),
                total_available=available,
                overflow=abs(min(0, available)),
                quality_score=0.0,
                strategies_used=["emergency_minimal"]
            )

        # Count tokens in each section
        for section in sections:
            section.token_count = self.counter.count_tokens(section.content)

        # Apply allocation strategy
        if self.config.allocation_strategy == "balanced":
            allocations = self._allocate_balanced(sections, available)
        elif self.config.allocation_strategy == "speed":
            allocations = self._allocate_speed(sections, available)
        elif self.config.allocation_strategy == "quality":
            allocations = self._allocate_quality(sections, available)
        elif self.config.allocation_strategy == "minimal":
            allocations = self._allocate_minimal(sections, available)
        else:
            allocations = self._allocate_balanced(sections, available)

        # Check for overflow
        total_allocated = sum(allocations.values())
        overflow = max(0, total_allocated - available)

        # Handle overflow if needed
        strategies_used = []
        if overflow > 0:
            allocations, strategies_used = self._handle_overflow(
                sections, allocations, overflow
            )
            total_allocated = sum(allocations.values())
            overflow = max(0, total_allocated - available)

        # Calculate quality score
        quality_score = self._calculate_quality_score(sections, allocations)

        return AllocationResult(
            allocations=allocations,
            total_allocated=total_allocated,
            total_available=available,
            overflow=overflow,
            quality_score=quality_score,
            strategies_used=strategies_used
        )

    def _get_available_tokens(self) -> int:
        """Get available tokens for content."""
        return (
            self.config.total_budget
            - self.config.buffer_tokens
            - self.config.min_response_tokens
        )

    def _allocate_balanced(
        self, sections: List[TokenSection], available: int
    ) -> Dict[str, int]:
        """Balanced allocation: weight by priority."""
        allocations = {}
        total_requested = sum(s.token_count for s in sections)

        # If we have enough space, give everyone what they need (respecting min/max)
        if total_requested <= available:
            for section in sections:
                # Start with the actual content size
                allocated = section.token_count

                # Respect minimum
                allocated = max(allocated, section.min_tokens)

                # Respect maximum
                if section.max_tokens is not None:
                    allocated = min(allocated, section.max_tokens)

                allocations[section.name] = allocated
            return allocations

        # Otherwise, allocate proportionally by priority
        priority_scores = self._calculate_priority_scores(sections)
        total_priority = sum(priority_scores.values())

        # First pass: allocate proportionally
        allocations = {}
        for section in sections:
            priority_score = priority_scores.get(section.name, 1.0)
            weight = priority_score / total_priority if total_priority > 0 else 1.0 / len(sections)
            allocated = max(1, int(available * weight))

            # Respect maximums first
            if section.max_tokens is not None:
                allocated = min(allocated, section.max_tokens)

            allocations[section.name] = allocated

        # Second pass: ensure minimums are respected (adjust if needed)
        total_allocated = sum(allocations.values())
        remaining = available - total_allocated

        for section in sections:
            current = allocations[section.name]
            if current < section.min_tokens and remaining > 0:
                # Increase allocation to meet minimum
                increase = min(section.min_tokens - current, remaining)
                allocations[section.name] += increase
                remaining -= increase

        return allocations

    def _allocate_speed(
        self, sections: List[TokenSection], available: int
    ) -> Dict[str, int]:
        """Speed allocation: prioritize fast-to-process content."""
        allocations = {}

        # Prefer shorter sections for faster processing
        sections_by_size = sorted(sections, key=lambda s: s.token_count)

        remaining = available
        for section in sections_by_size:
            # Give priority sections more tokens
            if section.priority in (PriorityLevel.CRITICAL, PriorityLevel.HIGH):
                allocated = min(section.token_count, remaining)
            else:
                # Lower priority gets less
                allocated = min(section.token_count // 2, remaining)

            allocated = max(allocated, section.min_tokens)
            if section.max_tokens is not None:
                allocated = min(allocated, section.max_tokens)

            allocations[section.name] = allocated
            remaining -= allocated

            if remaining <= 0:
                break

        return allocations

    def _allocate_quality(
        self, sections: List[TokenSection], available: int
    ) -> Dict[str, int]:
        """Quality allocation: maximize information preservation."""
        allocations = {}

        # Allocate based on priority, favoring complete content
        priority_groups = self._group_by_priority(sections)

        remaining = available
        for priority in sorted(priority_groups.keys(), reverse=True):
            sections_in_priority = priority_groups[priority]

            # Try to allocate full content for high-priority sections
            for section in sections_in_priority:
                allocated = min(section.token_count, remaining)
                allocated = max(allocated, section.min_tokens)

                if section.max_tokens is not None:
                    allocated = min(allocated, section.max_tokens)

                allocations[section.name] = allocated
                remaining -= allocated

                if remaining <= 0:
                    break

            if remaining <= 0:
                break

        return allocations

    def _allocate_minimal(
        self, sections: List[TokenSection], available: int
    ) -> Dict[str, int]:
        """Minimal allocation: pack maximum content."""
        allocations = {}

        # Sort by priority, then by size (smaller first for packing)
        priority_scores = self._calculate_priority_scores(sections)
        sections_sorted = sorted(
            sections,
            key=lambda s: (-priority_scores.get(s.name, 1.0), s.token_count)
        )

        remaining = available
        for section in sections_sorted:
            # Allocate as much as possible for high-priority
            allocated = min(section.token_count, remaining)
            allocated = max(allocated, section.min_tokens)

            if section.max_tokens is not None:
                allocated = min(allocated, section.max_tokens)

            allocations[section.name] = allocated
            remaining -= allocated

        return allocations

    def _calculate_priority_scores(self, sections: List[TokenSection]) -> Dict[str, float]:
        """Calculate priority score for each section."""
        scores = {}
        for section in sections:
            # Base score from priority level
            base_score = section.priority.value

            # Adjustment for size (smaller sections get slight boost)
            size_adjustment = max(0.8, 1.0 - (section.token_count / 1000))

            scores[section.name] = base_score * size_adjustment

        return scores

    def _group_by_priority(self, sections: List[TokenSection]) -> Dict[int, List[TokenSection]]:
        """Group sections by priority level."""
        groups = defaultdict(list)
        for section in sections:
            groups[section.priority.value].append(section)
        return groups

    def _handle_overflow(
        self, sections: List[TokenSection], allocations: Dict[str, int], overflow: int
    ) -> Tuple[Dict[str, int], List[str]]:
        """Handle token budget overflow.

        Args:
            sections: Original sections
            allocations: Current allocations
            overflow: Tokens over budget

        Returns:
            Updated allocations and list of strategies used
        """
        strategies_used = []
        remaining_overflow = overflow

        section_map = {s.name: s for s in sections}

        # Try each overflow strategy in order
        for strategy in [self.config.primary_overflow_strategy] + self.config.secondary_overflow_strategies:
            if remaining_overflow <= 0:
                break

            if strategy == OverflowStrategy.COMPRESS:
                result = self._apply_compression_strategy(allocations, remaining_overflow)
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("compression")

            elif strategy == OverflowStrategy.TRUNCATE_END:
                result = self._apply_truncate_strategy(allocations, remaining_overflow, position="end")
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("truncate_end")

            elif strategy == OverflowStrategy.TRUNCATE_START:
                result = self._apply_truncate_strategy(allocations, remaining_overflow, position="start")
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("truncate_start")

            elif strategy == OverflowStrategy.TRUNCATE_MIDDLE:
                result = self._apply_truncate_strategy(allocations, remaining_overflow, position="middle")
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("truncate_middle")

            elif strategy == OverflowStrategy.DELEGATE:
                result = self._apply_delegation_strategy(allocations, remaining_overflow, section_map)
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("delegation")

            elif strategy == OverflowStrategy.DEGRADE:
                result = self._apply_degradation_strategy(allocations, remaining_overflow)
                reduction, updated_allocs = result
                if reduction > 0:
                    allocations = updated_allocs
                    remaining_overflow -= reduction
                    strategies_used.append("degradation")

        return allocations, strategies_used

    def _apply_compression_strategy(
        self, allocations: Dict[str, int], target_reduction: int
    ) -> Tuple[int, Dict[str, int]]:
        """Apply compression to reduce token usage.

        Returns:
            Tuple of (tokens_reduced, updated_allocations)
        """
        updated = allocations.copy()
        total_reduction = 0

        # Compress low-priority sections first
        # This is a simplified version - real implementation would use
        # the compression module from athena.efficiency.compression

        # For now, reduce low-priority sections by target compression ratio
        for section_name, allocated in list(updated.items()):
            if total_reduction >= target_reduction:
                break

            # Estimate compression benefit (assume 30% reduction possible)
            potential_reduction = int(allocated * 0.3)

            if potential_reduction > 0:
                reduction = min(potential_reduction, target_reduction - total_reduction)
                updated[section_name] = max(1, allocated - reduction)
                total_reduction += reduction

        return total_reduction, updated

    def _apply_truncate_strategy(
        self, allocations: Dict[str, int], target_reduction: int, position: str = "end"
    ) -> Tuple[int, Dict[str, int]]:
        """Apply truncation strategy.

        Returns:
            Tuple of (tokens_reduced, updated_allocations)
        """
        updated = allocations.copy()
        total_reduction = 0

        # Reduce from low-priority sections
        sections_by_priority = sorted(updated.items(), key=lambda x: x[1])  # Smaller allocations first

        for section_name, allocated in sections_by_priority:
            if total_reduction >= target_reduction:
                break

            # Can reduce by up to 50% of allocation
            max_reduction = int(allocated * 0.5)
            reduction = min(max_reduction, target_reduction - total_reduction)

            if reduction > 0:
                updated[section_name] = max(1, allocated - reduction)
                total_reduction += reduction

        return total_reduction, updated

    def _apply_delegation_strategy(
        self, allocations: Dict[str, int], target_reduction: int, section_map: Dict[str, TokenSection]
    ) -> Tuple[int, Dict[str, int]]:
        """Delegate content to lower-priority section.

        Returns:
            Tuple of (tokens_reduced, updated_allocations)
        """
        # Find highest-priority section with excess capacity
        # and move content from low-priority to it
        # This is a conceptual approach - real implementation depends on content structure

        return 0, allocations  # Simplified for now

    def _apply_degradation_strategy(
        self, allocations: Dict[str, int], target_reduction: int
    ) -> Tuple[int, Dict[str, int]]:
        """Reduce detail level to save tokens.

        Returns:
            Tuple of (tokens_reduced, updated_allocations)
        """
        updated = allocations.copy()
        total_reduction = 0

        # Reduce less important sections more aggressively
        for section_name, allocated in list(updated.items()):
            if total_reduction >= target_reduction:
                break

            # More aggressive reduction: 40-60%
            reduction_ratio = 0.4  # Can be tuned per section
            max_reduction = int(allocated * reduction_ratio)
            reduction = min(max_reduction, target_reduction - total_reduction)

            if reduction > 0:
                updated[section_name] = max(1, allocated - reduction)
                total_reduction += reduction

        return total_reduction, updated

    def _calculate_quality_score(
        self, sections: List[TokenSection], allocations: Dict[str, int]
    ) -> float:
        """Calculate overall quality score.

        Factors:
        - Coverage: % of original content preserved
        - Priority: whether high-priority sections are complete
        - Balance: distribution fairness
        """
        total_requested = sum(s.token_count for s in sections)
        total_allocated = sum(allocations.values())

        # Coverage: 50% weight
        coverage_score = min(1.0, total_allocated / total_requested) if total_requested > 0 else 1.0

        # Priority completeness: 30% weight
        critical_sections = [s for s in sections if s.priority == PriorityLevel.CRITICAL]
        if critical_sections:
            critical_complete = sum(
                1 for s in critical_sections
                if allocations.get(s.name, 0) >= s.token_count
            )
            priority_score = critical_complete / len(critical_sections)
        else:
            priority_score = 1.0

        # Balance: 20% weight
        allocation_ratios = [
            allocations.get(s.name, 0) / s.token_count
            for s in sections
            if s.token_count > 0
        ]
        if allocation_ratios:
            # Penalize imbalance (variance)
            avg_ratio = sum(allocation_ratios) / len(allocation_ratios)
            variance = sum((r - avg_ratio) ** 2 for r in allocation_ratios) / len(allocation_ratios)
            balance_score = max(0, 1.0 - variance)  # Lower variance = higher score
        else:
            balance_score = 1.0

        # Weighted combination
        quality = (
            0.5 * coverage_score +
            0.3 * priority_score +
            0.2 * balance_score
        )

        return quality


class TokenBudgetManager:
    """Main interface for token budgeting."""

    def __init__(self, config: Optional[TokenBudgetConfig] = None):
        """Initialize budget manager.

        Args:
            config: Budget configuration (uses defaults if not provided)
        """
        self.config = config or TokenBudgetConfig()
        self.allocator = TokenBudgetAllocator(self.config)
        self.counter = TokenCounter(self.config.counting_strategy)

        # Metrics tracking
        self.metrics_history: List[BudgetMetrics] = []
        self._current_sections: List[TokenSection] = []

    def add_section(
        self,
        name: str,
        content: str,
        priority: PriorityLevel = PriorityLevel.NORMAL,
        min_tokens: int = 0,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Add a section to budget.

        Args:
            name: Section identifier
            content: Section content
            priority: Priority level
            min_tokens: Minimum tokens to preserve
            max_tokens: Hard limit for section
            metadata: Custom metadata
        """
        section = TokenSection(
            name=name,
            content=content,
            priority=priority,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            metadata=metadata or {}
        )
        self._current_sections.append(section)

    def clear_sections(self) -> None:
        """Clear all sections."""
        self._current_sections = []

    def calculate_budget(self) -> AllocationResult:
        """Calculate token allocation for current sections.

        Returns:
            Allocation result
        """
        return self.allocator.allocate(self._current_sections)

    def get_allocation(self, section_name: str) -> int:
        """Get allocated tokens for a section.

        Args:
            section_name: Name of section

        Returns:
            Allocated token count
        """
        if not self._current_sections:
            return 0

        result = self.calculate_budget()
        return result.allocations.get(section_name, 0)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        return self.counter.count_tokens(text)

    def get_metrics(self) -> BudgetMetrics:
        """Get current budget metrics.

        Returns:
            Current metrics snapshot
        """
        result = self.calculate_budget()

        metrics = BudgetMetrics(
            timestamp=datetime.now(),
            total_budget=self.config.total_budget,
            total_used=result.total_allocated,
            overflow=result.overflow,
            efficiency=result.total_allocated / self.config.total_budget,
            quality_score=result.quality_score,
            sections_count=len(self._current_sections),
            compression_applied=any(s.compressed for s in self._current_sections),
            strategies_used=result.strategies_used
        )

        if self.config.track_history:
            self.metrics_history.append(metrics)

        return metrics

    def estimate_cost(
        self,
        model: str = "claude-3-5-sonnet",
        input_cost_per_mtok: float = 3.0,
        output_cost_per_mtok: float = 15.0
    ) -> Dict[str, float]:
        """Estimate API cost.

        Args:
            model: Model to estimate cost for
            input_cost_per_mtok: Cost per million input tokens (USD)
            output_cost_per_mtok: Cost per million output tokens (USD)

        Returns:
            Cost breakdown
        """
        result = self.calculate_budget()

        input_tokens = result.total_allocated
        output_tokens = self.config.min_response_tokens

        input_cost = (input_tokens / 1_000_000) * input_cost_per_mtok
        output_cost = (output_tokens / 1_000_000) * output_cost_per_mtok

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost
        }

    def get_history(self) -> List[BudgetMetrics]:
        """Get metrics history.

        Returns:
            List of historical metrics
        """
        return self.metrics_history.copy()

    def clear_history(self) -> None:
        """Clear metrics history."""
        self.metrics_history = []
