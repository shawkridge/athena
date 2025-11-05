"""Prompt caching support for Anthropic Claude API.

Research Finding: "Anthropic Prompt Caching (GA Dec 2024)"
- 90% cost reduction on cached tokens
- 85% latency reduction
- 5-minute TTL (refreshed on use)
- Up to 4 cache breakpoints per message
- Pricing: 0.1x reads, 1.25x-2x writes

Provides:
- Context block identification and caching
- Cache hit tracking and metrics
- Cost savings calculation
- Integration with cost tracking system
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CacheBlockType(str, Enum):
    """Types of content that can be cached."""

    SYSTEM_INSTRUCTIONS = "system_instructions"  # System prompt (large, rarely changes)
    CONTEXT_BLOCK = "context_block"  # Consolidated memory context
    REFERENCE_MATERIAL = "reference_material"  # Technical docs, examples
    CONVERSATION_HISTORY = "conversation_history"  # Multi-turn conversation
    KNOWLEDGE_BASE = "knowledge_base"  # Extracted knowledge blocks
    RETRIEVED_MEMORIES = "retrieved_memories"  # RAG search results
    TASK_DEFINITION = "task_definition"  # Task instructions


class CacheStatus(str, Enum):
    """Cache status for a block."""

    NOT_CACHED = "not_cached"
    PENDING_CACHE = "pending_cache"  # Waiting for cache write
    CACHED = "cached"  # Successfully cached
    STALE = "stale"  # Expired (>5min)
    INVALID = "invalid"  # Changed since caching


@dataclass
class CacheBlock:
    """Single cacheable content block."""

    block_id: str
    block_type: CacheBlockType
    content: str
    content_hash: str = ""  # SHA256 of content
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    access_count: int = 0

    # Cache metadata
    cached_at: Optional[datetime] = None
    cache_status: CacheStatus = CacheStatus.NOT_CACHED
    cache_tokens: int = 0  # Tokens stored in cache
    input_tokens: int = 0  # Tokens needed to set cache (1.25-2x cache_tokens)

    def __post_init__(self):
        """Compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()

    def is_stale(self, ttl_minutes: int = 5) -> bool:
        """Check if cache is stale (>TTL since last access)."""
        if self.cached_at is None:
            return False
        age = datetime.now() - self.cached_at
        return age > timedelta(minutes=ttl_minutes)

    def estimate_tokens(self) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(self.content) // 4


@dataclass
class CacheMetrics:
    """Metrics for prompt caching performance."""

    total_blocks: int = 0
    cached_blocks: int = 0
    pending_blocks: int = 0
    stale_blocks: int = 0

    total_cache_tokens: int = 0  # Tokens in cache
    total_input_tokens: int = 0  # Tokens spent writing cache

    cache_hits: int = 0  # Number of cache hits (reuses)
    cache_misses: int = 0

    def cache_hit_rate(self) -> float:
        """Cache hit rate (0.0-1.0)."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def estimated_tokens_without_cache(self, avg_query_tokens: int = 500) -> int:
        """Estimate tokens needed without caching."""
        # Each cache hit saves sending the cached context
        return (self.cache_hits * self.total_cache_tokens) + (
            (self.cache_hits + self.cache_misses) * avg_query_tokens
        )

    def estimated_tokens_with_cache(self, avg_query_tokens: int = 500) -> int:
        """Estimate tokens with caching."""
        cache_write_cost = self.total_input_tokens
        cache_read_cost = self.cache_hits * 100  # Rough: 10% of full context

        return (
            cache_write_cost
            + cache_read_cost
            + ((self.cache_hits + self.cache_misses) * avg_query_tokens)
        )

    def token_savings_percentage(self) -> float:
        """Percentage token savings from caching."""
        without = self.estimated_tokens_without_cache()
        with_cache = self.estimated_tokens_with_cache()

        if without == 0:
            return 0.0

        return (without - with_cache) / without

    def estimated_cost_savings(
        self, cost_per_cache_token: float = 0.0000005, cost_per_regular_token: float = 0.000005
    ) -> dict:
        """Estimate cost savings.

        Args:
            cost_per_cache_token: Cost per read token from cache (0.1x regular)
            cost_per_regular_token: Regular input token cost

        Returns:
            Dictionary with cost estimates
        """
        without_cache = (
            self.estimated_tokens_without_cache() * cost_per_regular_token
        )
        with_cache = (
            (self.total_input_tokens * cost_per_regular_token * 1.5)  # Write cost
            + (self.cache_hits * 100 * cost_per_cache_token)  # Read from cache
            + ((self.cache_hits + self.cache_misses) * 500 * cost_per_regular_token)
        )

        return {
            "cost_without_cache": without_cache,
            "cost_with_cache": with_cache,
            "savings": without_cache - with_cache,
            "savings_percentage": (without_cache - with_cache) / without_cache
            if without_cache > 0
            else 0.0,
        }


@dataclass
class CachingRecommendation:
    """Recommendation for what to cache."""

    block_type: CacheBlockType
    block_id: str
    content_size_tokens: int
    estimated_hit_rate: float  # 0.0-1.0
    priority: str  # "high", "medium", "low"
    reason: str  # Why this should be cached

    estimated_monthly_savings: float = 0.0
    implementation_effort: str = "easy"  # easy, medium, hard


class PromptCacheManager:
    """Manages prompt caching for Anthropic Claude API."""

    def __init__(self):
        """Initialize cache manager."""
        self.blocks: dict[str, CacheBlock] = {}
        self.cache_ttl_minutes = 5  # Anthropic's default

    def create_cache_block(
        self,
        block_type: CacheBlockType,
        content: str,
        block_id: Optional[str] = None,
    ) -> CacheBlock:
        """Create cacheable content block.

        Args:
            block_type: Type of content
            content: Content to cache
            block_id: Optional block ID (auto-generated if not provided)

        Returns:
            Created cache block
        """
        if block_id is None:
            block_id = f"{block_type.value}_{len(self.blocks)}"

        block = CacheBlock(block_id=block_id, block_type=block_type, content=content)
        self.blocks[block_id] = block

        logger.debug(f"Created cache block {block_id} ({block_type.value})")
        return block

    def mark_cached(
        self, block_id: str, cache_tokens: int, input_tokens: int
    ) -> bool:
        """Mark block as cached (after successful API call).

        Args:
            block_id: Block ID
            cache_tokens: Tokens stored in cache
            input_tokens: Tokens used to write cache

        Returns:
            True if successful
        """
        if block_id not in self.blocks:
            logger.warning(f"Block {block_id} not found")
            return False

        block = self.blocks[block_id]
        block.cache_status = CacheStatus.CACHED
        block.cached_at = datetime.now()
        block.cache_tokens = cache_tokens
        block.input_tokens = input_tokens

        logger.info(
            f"Marked {block_id} as cached "
            f"({cache_tokens} tokens, {input_tokens} write cost)"
        )
        return True

    def record_cache_hit(self, block_id: str) -> bool:
        """Record that cached block was used.

        Args:
            block_id: Block ID

        Returns:
            True if successful
        """
        if block_id not in self.blocks:
            logger.warning(f"Block {block_id} not found")
            return False

        block = self.blocks[block_id]

        # Update cache status if stale
        if block.is_stale(self.cache_ttl_minutes):
            block.cache_status = CacheStatus.STALE
            logger.debug(f"Block {block_id} cache is stale")
            return False

        block.access_count += 1
        block.last_accessed = datetime.now()

        logger.debug(f"Recorded cache hit for {block_id} (total: {block.access_count})")
        return True

    def get_metrics(self) -> CacheMetrics:
        """Get caching metrics.

        Returns:
            Aggregate cache metrics
        """
        metrics = CacheMetrics()

        for block in self.blocks.values():
            metrics.total_blocks += 1
            metrics.total_cache_tokens += block.cache_tokens
            metrics.total_input_tokens += block.input_tokens

            if block.cache_status == CacheStatus.CACHED:
                metrics.cached_blocks += 1
            elif block.cache_status == CacheStatus.PENDING_CACHE:
                metrics.pending_blocks += 1
            elif block.cache_status == CacheStatus.STALE:
                metrics.stale_blocks += 1

            metrics.cache_hits += block.access_count

        # Estimate misses as blocks that exist but weren't accessed via cache
        metrics.cache_misses = metrics.total_blocks - metrics.cache_hits

        return metrics

    def get_recommendations(self) -> list[CachingRecommendation]:
        """Get caching recommendations.

        Returns:
            Sorted list of blocks to cache (by priority)
        """
        recommendations = []

        # Analyze each block type
        type_stats: dict[str, list[CacheBlock]] = {}
        for block in self.blocks.values():
            if block.block_type not in type_stats:
                type_stats[block.block_type] = []
            type_stats[block.block_type].append(block)

        # High priority: Large, frequently-reused blocks
        for block_type, blocks in type_stats.items():
            if not blocks:
                continue

            # Estimate hit rate based on access count
            total_access = sum(b.access_count for b in blocks)
            avg_size = sum(b.estimate_tokens() for b in blocks) // len(blocks)

            if total_access > 2 and avg_size > 200:
                priority = "high"
                reason = f"Large ({avg_size} tokens) and frequently reused"
            elif total_access > 1 and avg_size > 100:
                priority = "medium"
                reason = f"Medium size ({avg_size} tokens) and reused"
            else:
                priority = "low"
                reason = f"Small or infrequently accessed"

            estimated_hit_rate = min(total_access / max(total_access + 1, 10), 1.0)

            rec = CachingRecommendation(
                block_type=block_type,
                block_id=f"{block_type.value}_group",
                content_size_tokens=avg_size,
                estimated_hit_rate=estimated_hit_rate,
                priority=priority,
                reason=reason,
                estimated_monthly_savings=avg_size * estimated_hit_rate * 20,
            )
            recommendations.append(rec)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 3))

        return recommendations

    def optimize_cache_blocks(self) -> dict:
        """Analyze and optimize cache configuration.

        Returns:
            Optimization report
        """
        metrics = self.get_metrics()
        recommendations = self.get_recommendations()

        # Find inefficient blocks
        stale_blocks = [b for b in self.blocks.values() if b.is_stale()]
        unused_blocks = [b for b in self.blocks.values() if b.access_count == 0]

        report = {
            "metrics": metrics,
            "recommendations": recommendations,
            "stale_blocks_count": len(stale_blocks),
            "unused_blocks_count": len(unused_blocks),
            "optimization_opportunities": [],
        }

        # Add optimization opportunities
        if stale_blocks:
            report["optimization_opportunities"].append(
                {
                    "issue": "Stale cache blocks",
                    "count": len(stale_blocks),
                    "action": "Refresh or remove stale blocks to free cache space",
                    "savings": len(stale_blocks) * 100,
                }
            )

        if unused_blocks:
            report["optimization_opportunities"].append(
                {
                    "issue": "Unused cache blocks",
                    "count": len(unused_blocks),
                    "action": "Remove unused blocks, they waste cache writes",
                    "savings": sum(b.input_tokens for b in unused_blocks),
                }
            )

        if metrics.cache_hit_rate() < 0.5 and metrics.total_blocks > 2:
            report["optimization_opportunities"].append(
                {
                    "issue": "Low cache hit rate",
                    "rate": metrics.cache_hit_rate(),
                    "action": "Consolidate small blocks or adjust TTL settings",
                    "savings": "variable",
                }
            )

        return report

    def summary_report(self) -> str:
        """Generate summary report.

        Returns:
            Human-readable report
        """
        metrics = self.get_metrics()
        recommendations = self.get_recommendations()

        lines = [
            "=" * 60,
            "PROMPT CACHING SUMMARY REPORT",
            "=" * 60,
            "",
            f"Total Blocks: {metrics.total_blocks}",
            f"Cached Blocks: {metrics.cached_blocks}",
            f"Pending Blocks: {metrics.pending_blocks}",
            f"Stale Blocks: {metrics.stale_blocks}",
            "",
            f"Total Cache Tokens: {metrics.total_cache_tokens:,}",
            f"Cache Write Cost: {metrics.total_input_tokens:,} tokens",
            f"Cache Hit Rate: {metrics.cache_hit_rate():.1%}",
            f"Token Savings: {metrics.token_savings_percentage():.1%}",
            "",
            "COST ESTIMATES (based on Claude 3.5 Sonnet pricing)",
            "-" * 60,
        ]

        savings = metrics.estimated_cost_savings()
        lines.extend(
            [
                f"Cost without cache: ${savings['cost_without_cache']:.4f}",
                f"Cost with cache: ${savings['cost_with_cache']:.4f}",
                f"Savings: ${savings['savings']:.4f} ({savings['savings_percentage']:.1%})",
                "",
                "TOP CACHING RECOMMENDATIONS",
                "-" * 60,
            ]
        )

        for i, rec in enumerate(recommendations[:3], 1):
            lines.extend(
                [
                    f"{i}. {rec.block_type.value.replace('_', ' ').title()}",
                    f"   Priority: {rec.priority.upper()}",
                    f"   Size: {rec.content_size_tokens} tokens",
                    f"   Est. Hit Rate: {rec.estimated_hit_rate:.1%}",
                    f"   Reason: {rec.reason}",
                    f"   Monthly Savings: ${rec.estimated_monthly_savings:.2f}",
                    "",
                ]
            )

        return "\n".join(lines)

    def integration_guide(self) -> str:
        """Get integration guide for Claude API.

        Returns:
            Integration instructions
        """
        return """
PROMPT CACHING INTEGRATION GUIDE
=================================

1. IDENTIFY CACHEABLE CONTENT
   - System instructions (usually constant)
   - Reference material (technical docs, examples)
   - Retrieved context blocks (from RAG)
   - Conversation history

2. CREATE CACHE BLOCKS
   manager = PromptCacheManager()
   block = manager.create_cache_block(
       CacheBlockType.SYSTEM_INSTRUCTIONS,
       system_prompt_text
   )

3. SEND CACHED REQUEST (Anthropic API)
   response = anthropic.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=1024,
       system=[
           {
               "type": "text",
               "text": system_instructions,
               "cache_control": {"type": "ephemeral"}
           }
       ],
       messages=[...]
   )

4. RECORD CACHE RESULTS
   manager.mark_cached(
       block_id,
       cache_tokens=response.usage.cache_creation_input_tokens,
       input_tokens=response.usage.cache_read_input_tokens
   )

5. TRACK CACHE HITS
   manager.record_cache_hit(block_id)

6. MONITOR PERFORMANCE
   metrics = manager.get_metrics()
   print(manager.summary_report())

COST BREAKDOWN
==============
- Cache write: 1.25x regular token cost (ephemeral)
- Cache write: 2x regular token cost (session/permanent)
- Cache read: 0.1x regular token cost (90% savings!)

CACHING LIMITS
==============
- TTL: 5 minutes from last access
- Per-message blocks: Up to 4 cache breakpoints
- Min cached content: ~1024 tokens for efficiency
- Max cache per conversation: Limited by model

BEST PRACTICES
==============
1. Cache system instructions (large, constant)
2. Cache reference material (large, reused)
3. Cache retrieved context blocks (RAG results)
4. Don't cache frequently-changing content
5. Monitor cache hit rate (target: >70%)
6. Remove stale blocks to free space
"""
