"""Token tracking and cost analysis for consolidation pipeline.

Tracks tokens before/after compression and caching to calculate:
- Compression ratio and effectiveness
- Cache hit rates and savings
- Cost reduction (estimated based on token counts)
- Quality preservation metrics

Integration with prompt caching and compression modules to provide
comprehensive token economy insights for the consolidation system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TokenSource(str, Enum):
    """Source of tokens in the consolidation pipeline."""

    CONSOLIDATION_PROMPT = "consolidation_prompt"  # Initial consolidation context
    COMPRESSED_PROMPT = "compressed_prompt"  # After LLMLingua-2 compression
    CLAUDE_INPUT = "claude_input"  # Actual tokens sent to Claude
    CLAUDE_OUTPUT = "claude_output"  # Response from Claude
    LOCAL_LLM = "local_llm"  # Local reasoning (Qwen/llama.cpp)
    CACHE_HIT = "cache_hit"  # Reused from cache


class CompressionMetric(str, Enum):
    """Metrics for compression effectiveness."""

    RATIO = "ratio"  # Compression ratio (0.35 = 35% of original)
    TOKENS_SAVED = "tokens_saved"  # Absolute tokens removed
    LATENCY = "latency"  # Compression latency in ms
    QUALITY_PRESERVATION = "quality_preservation"  # 0-1 semantic preservation


@dataclass
class TokenCount:
    """Token count at a specific stage."""

    source: TokenSource
    count: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """Human-readable token count."""
        return f"{self.source.value}: {self.count:,} tokens"


@dataclass
class CompressionResult:
    """Result of compression operation."""

    original_tokens: int
    compressed_tokens: int
    compression_ratio: float  # 0-1, where 0.35 = 35% of original
    tokens_saved: int
    latency_ms: float
    quality_preservation: float  # 0-1, where 1.0 = 100% semantic preservation
    compression_method: str = "llmlinguia-2"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate compression metrics."""
        assert 0 <= self.compression_ratio <= 1, "Ratio must be 0-1"
        assert 0 <= self.quality_preservation <= 1, "Quality must be 0-1"
        assert self.tokens_saved == (self.original_tokens - self.compressed_tokens)
        assert self.compressed_tokens == int(self.original_tokens * self.compression_ratio)

    @property
    def compression_percentage(self) -> float:
        """Return compression as percentage (0-100)."""
        return (1 - self.compression_ratio) * 100

    def __str__(self) -> str:
        """Human-readable compression result."""
        return (
            f"Compression: {self.original_tokens:,} → {self.compressed_tokens:,} "
            f"({self.compression_percentage:.1f}% reduction, {self.latency_ms:.0f}ms)"
        )


@dataclass
class CacheResult:
    """Result of cache lookup."""

    cache_hit: bool
    tokens_sent_to_claude: int  # Tokens after cache hit
    tokens_saved_via_cache: int  # Tokens reused from cache
    cache_age_seconds: Optional[int] = None  # How long cached
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    @property
    def cache_savings_percentage(self) -> float:
        """Return cache savings as percentage."""
        if self.cache_hit:
            total = self.tokens_sent_to_claude + self.tokens_saved_via_cache
            if total == 0:
                return 0.0
            return (self.tokens_saved_via_cache / total) * 100
        return 0.0

    def __str__(self) -> str:
        """Human-readable cache result."""
        if self.cache_hit:
            return (
                f"Cache HIT: {self.tokens_saved_via_cache:,} tokens reused "
                f"(sent {self.tokens_sent_to_claude:,}, saved {self.cache_savings_percentage:.1f}%)"
            )
        return "Cache MISS: fresh consolidation required"


@dataclass
class ConsolidationTokenMetrics:
    """Complete token metrics for a consolidation cycle."""

    original_tokens: int  # Tokens in original consolidation prompt
    after_local_reasoning: int = 0  # Tokens after local LLM processing
    after_compression: Optional[int] = None  # Tokens after compression
    final_tokens_to_claude: int = 0  # Final tokens sent to Claude
    tokens_from_claude: int = 0  # Response tokens from Claude

    # Compression details
    compression_result: Optional[CompressionResult] = None

    # Cache details
    cache_result: Optional[CacheResult] = None

    # Timing
    local_reasoning_ms: float = 0.0
    compression_ms: float = 0.0
    cache_lookup_ms: float = 0.0
    claude_call_ms: float = 0.0
    total_ms: float = 0.0

    timestamp: datetime = field(default_factory=datetime.now)
    consolidation_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens sent to Claude."""
        return self.final_tokens_to_claude

    @property
    def total_tokens_processed(self) -> int:
        """Total tokens processed (input + output)."""
        return self.final_tokens_to_claude + self.tokens_from_claude

    @property
    def compression_ratio(self) -> float:
        """Compression ratio from original to Claude input."""
        if self.original_tokens == 0:
            return 1.0
        return self.final_tokens_to_claude / self.original_tokens

    @property
    def compression_percentage(self) -> float:
        """Compression as percentage reduction."""
        return (1 - self.compression_ratio) * 100

    @property
    def tokens_saved_total(self) -> int:
        """Total tokens saved vs original."""
        return self.original_tokens - self.final_tokens_to_claude

    @property
    def cost_reduction_percentage(self) -> float:
        """Estimated cost reduction percentage.

        Accounts for:
        - Compression: reduce tokens before Claude
        - Caching: avoid Claude call entirely (90% savings)
        """
        if self.original_tokens == 0:
            return 0.0

        base_cost = self.original_tokens

        # Compression savings
        if self.compression_result:
            after_compression = self.compression_result.compressed_tokens
        else:
            after_compression = self.final_tokens_to_claude

        # Cache savings (90% cost reduction on cached tokens)
        if self.cache_result and self.cache_result.cache_hit:
            # Cached query cost ~0.1x (90% savings)
            cost_after_cache = after_compression * 0.1
        else:
            cost_after_cache = after_compression

        return ((base_cost - cost_after_cache) / base_cost) * 100

    def __str__(self) -> str:
        """Human-readable metrics summary."""
        lines = [
            "Consolidation Token Metrics:",
            f"  Original tokens: {self.original_tokens:,}",
            f"  Final tokens to Claude: {self.final_tokens_to_claude:,}",
            f"  Compression: {self.compression_percentage:.1f}%",
            f"  Tokens saved: {self.tokens_saved_total:,}",
        ]

        if self.cache_result:
            lines.append(
                f"  Cache: {self.cache_result.cache_hit and 'HIT' or 'MISS'} "
                f"({self.cache_result.cache_savings_percentage:.1f}% savings)"
            )

        lines.append(f"  Cost reduction: {self.cost_reduction_percentage:.1f}%")
        lines.append(f"  Total latency: {self.total_ms:.0f}ms")

        return "\n".join(lines)


@dataclass
class TokenTracker:
    """Track tokens throughout consolidation pipeline."""

    consolidation_id: str
    original_tokens: int

    # Stage tracking
    tokens_after_local_reasoning: Optional[int] = None
    tokens_after_compression: Optional[int] = None
    tokens_to_claude: Optional[int] = None
    tokens_from_claude: Optional[int] = None

    # Results
    compression_result: Optional[CompressionResult] = None
    cache_result: Optional[CacheResult] = None

    # Timing (milliseconds)
    local_reasoning_start: Optional[float] = None
    compression_start: Optional[float] = None
    cache_lookup_start: Optional[float] = None
    claude_call_start: Optional[float] = None

    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def record_local_reasoning(self, tokens_after: int, latency_ms: float) -> None:
        """Record local reasoning output tokens and latency."""
        self.tokens_after_local_reasoning = tokens_after
        self.metadata["local_reasoning_ms"] = latency_ms

    def record_compression(self, result: CompressionResult) -> None:
        """Record compression result."""
        self.compression_result = result
        self.tokens_after_compression = result.compressed_tokens
        self.metadata["compression_ms"] = result.latency_ms

    def record_cache_lookup(self, result: CacheResult, latency_ms: float) -> None:
        """Record cache lookup result."""
        self.cache_result = result
        self.metadata["cache_lookup_ms"] = latency_ms

    def record_claude_call(self, input_tokens: int, output_tokens: int, latency_ms: float) -> None:
        """Record Claude API call."""
        self.tokens_to_claude = input_tokens
        self.tokens_from_claude = output_tokens
        self.metadata["claude_call_ms"] = latency_ms

    def to_metrics(self) -> ConsolidationTokenMetrics:
        """Convert tracker to final metrics."""
        return ConsolidationTokenMetrics(
            original_tokens=self.original_tokens,
            after_local_reasoning=self.tokens_after_local_reasoning or 0,
            after_compression=self.tokens_after_compression,
            final_tokens_to_claude=self.tokens_to_claude or 0,
            tokens_from_claude=self.tokens_from_claude or 0,
            compression_result=self.compression_result,
            cache_result=self.cache_result,
            local_reasoning_ms=self.metadata.get("local_reasoning_ms", 0),
            compression_ms=self.metadata.get("compression_ms", 0),
            cache_lookup_ms=self.metadata.get("cache_lookup_ms", 0),
            claude_call_ms=self.metadata.get("claude_call_ms", 0),
            consolidation_id=self.consolidation_id,
            metadata=self.metadata,
        )


class TokenMetricsAggregator:
    """Aggregate token metrics across multiple consolidations."""

    def __init__(self):
        """Initialize aggregator."""
        self.metrics: list[ConsolidationTokenMetrics] = []
        self.compression_results: list[CompressionResult] = []
        self.cache_results: list[CacheResult] = []

    def add_metrics(self, metrics: ConsolidationTokenMetrics) -> None:
        """Add metrics from a consolidation cycle."""
        self.metrics.append(metrics)
        if metrics.compression_result:
            self.compression_results.append(metrics.compression_result)
        if metrics.cache_result:
            self.cache_results.append(metrics.cache_result)

    @property
    def total_consolidations(self) -> int:
        """Number of consolidations tracked."""
        return len(self.metrics)

    @property
    def total_original_tokens(self) -> int:
        """Sum of original tokens across all consolidations."""
        return sum(m.original_tokens for m in self.metrics)

    @property
    def total_final_tokens(self) -> int:
        """Sum of final tokens sent to Claude."""
        return sum(m.final_tokens_to_claude for m in self.metrics)

    @property
    def average_compression_ratio(self) -> float:
        """Average compression ratio (0.35 = 35% of original)."""
        if not self.metrics:
            return 1.0
        return self.total_final_tokens / self.total_original_tokens

    @property
    def average_compression_percentage(self) -> float:
        """Average compression as percentage reduction."""
        return (1 - self.average_compression_ratio) * 100

    @property
    def average_cache_hit_rate(self) -> float:
        """Cache hit rate (0-1)."""
        if not self.cache_results:
            return 0.0
        hits = sum(1 for r in self.cache_results if r.cache_hit)
        return hits / len(self.cache_results)

    @property
    def total_tokens_saved(self) -> int:
        """Total tokens saved across all consolidations."""
        return self.total_original_tokens - self.total_final_tokens

    @property
    def average_cost_reduction_percentage(self) -> float:
        """Average cost reduction percentage."""
        if not self.metrics:
            return 0.0
        return sum(m.cost_reduction_percentage for m in self.metrics) / len(self.metrics)

    def get_summary(self) -> str:
        """Get summary statistics."""
        lines = [
            "=== Token Metrics Summary ===",
            f"Consolidations: {self.total_consolidations}",
            f"Original tokens: {self.total_original_tokens:,}",
            f"Final tokens to Claude: {self.total_final_tokens:,}",
            f"Tokens saved: {self.total_tokens_saved:,}",
            f"Average compression: {self.average_compression_percentage:.1f}%",
            f"Cache hit rate: {self.average_cache_hit_rate:.1%}",
            f"Average cost reduction: {self.average_cost_reduction_percentage:.1f}%",
        ]

        if self.compression_results:
            avg_latency = sum(r.latency_ms for r in self.compression_results) / len(
                self.compression_results
            )
            avg_quality = sum(r.quality_preservation for r in self.compression_results) / len(
                self.compression_results
            )
            lines.extend(
                [
                    f"Average compression latency: {avg_latency:.0f}ms",
                    f"Average quality preservation: {avg_quality:.1%}",
                ]
            )

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        return self.get_summary()
