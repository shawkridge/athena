"""Gisting and prompt caching for efficient context management.

Gisting is the practice of pre-computing summaries of documents and caching
them using prompt caching to reduce token usage and API costs.

References:
- Anthropic Prompt Caching: https://docs.anthropic.com/en/docs/build/prompt-caching
- Token budget optimization: Reduce context size by 70-90%
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GistCacheEntry:
    """Represents a cached gist with metadata."""

    gist_id: str  # Hash of original content
    original_hash: str  # SHA256 hash of original content
    summary: str  # Pre-computed summary
    content_type: str  # "document" | "code" | "memory" | "query"
    original_length: int  # Token count of original
    summary_length: int  # Token count of summary
    compression_ratio: float  # original / summary
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    cache_tokens_saved: int = 0  # Estimated tokens saved via caching
    model_used: str = "claude-3-5-haiku"


@dataclass
class CacheMetrics:
    """Metrics for cache performance."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    total_input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_savings_percentage: float = 0.0
    avg_compression_ratio: float = 1.0


class GistManager:
    """Manages document gisting and prompt caching for cost optimization."""

    def __init__(self, cache_dir: Optional[str | Path] = None, max_cache_size_mb: int = 100):
        """Initialize gist manager.

        Args:
            cache_dir: Directory for persistent cache (None = memory only)
            max_cache_size_mb: Maximum cache size before eviction

        References:
            - Prompt Caching: up to 5 min cached content per request
            - Cache tokens are 10% cost vs input tokens
            - Optimal hit rate: 70%+ for cost savings
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024

        # In-memory cache
        self._gist_cache: Dict[str, GistCacheEntry] = {}
        self._metrics = CacheMetrics()
        self._cache_size_bytes = 0

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_persisted_cache()

    def gist_document(
        self,
        content: str,
        content_type: str = "document",
        max_summary_tokens: int = 200,
        force_regenerate: bool = False,
    ) -> Tuple[str, GistCacheEntry]:
        """Create a gist (summary) of a document with prompt caching.

        Args:
            content: Document content to summarize
            content_type: Type of content ("document", "code", "memory", "query")
            max_summary_tokens: Maximum tokens for summary
            force_regenerate: If True, regenerate even if cached

        Returns:
            Tuple of (summary, cache_entry) with caching metadata

        Strategy:
            1. Hash content to get gist_id
            2. Check cache (memory then disk)
            3. If miss: generate summary using Claude
            4. Store in cache with metadata
            5. Track metrics for cost analysis
        """
        # Compute content hash
        content_hash = self._compute_hash(content)
        gist_id = f"{content_type}:{content_hash[:16]}"

        # Check cache
        if not force_regenerate:
            cached = self._get_from_cache(gist_id)
            if cached:
                self._metrics.cache_hits += 1
                cached.last_accessed = datetime.now()
                cached.access_count += 1
                # Estimate tokens saved (cache tokens are 10% cost)
                cached.cache_tokens_saved = int(cached.original_length * 0.9)
                return cached.summary, cached
        else:
            self._metrics.cache_misses += 1

        # Generate summary
        summary = self._generate_summary(content, content_type, max_summary_tokens)

        # Create cache entry
        entry = GistCacheEntry(
            gist_id=gist_id,
            original_hash=content_hash,
            summary=summary,
            content_type=content_type,
            original_length=self._estimate_tokens(content),
            summary_length=self._estimate_tokens(summary),
            compression_ratio=len(content) / max(len(summary), 1),
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            cache_tokens_saved=0,
        )

        # Store in cache
        self._store_in_cache(gist_id, entry)

        # Update metrics
        self._metrics.cache_misses += 1
        self._metrics.total_input_tokens += entry.original_length
        self._update_metrics()

        logger.info(f"Gisted {content_type}: {len(content):.0f} chars → {len(summary):.0f} "
                    f"({entry.compression_ratio:.1f}x compression)")

        return summary, entry

    def batch_gist_documents(
        self,
        documents: List[Tuple[str, str]],  # (content, content_type) tuples
        max_summary_tokens: int = 200,
        force_regenerate: bool = False,
    ) -> List[Tuple[str, GistCacheEntry]]:
        """Batch gist multiple documents.

        Args:
            documents: List of (content, content_type) tuples
            max_summary_tokens: Maximum tokens per summary
            force_regenerate: Regenerate all or use cache

        Returns:
            List of (summary, cache_entry) tuples
        """
        results = []

        for content, content_type in documents:
            summary, entry = self.gist_document(
                content=content,
                content_type=content_type,
                max_summary_tokens=max_summary_tokens,
                force_regenerate=force_regenerate,
            )
            results.append((summary, entry))

        return results

    def get_cached_gist(self, gist_id: str) -> Optional[GistCacheEntry]:
        """Retrieve a cached gist entry.

        Args:
            gist_id: ID of gist to retrieve

        Returns:
            Cache entry if found, None otherwise
        """
        if gist_id in self._gist_cache:
            entry = self._gist_cache[gist_id]
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            return entry

        if self.cache_dir:
            cached = self._get_from_disk(gist_id)
            if cached:
                self._gist_cache[gist_id] = cached
                return cached

        return None

    def invalidate_gist(self, gist_id: str) -> bool:
        """Invalidate a gist from cache.

        Args:
            gist_id: ID of gist to remove

        Returns:
            True if removed, False if not found
        """
        removed = False

        if gist_id in self._gist_cache:
            entry = self._gist_cache.pop(gist_id)
            # Estimate size reduction
            entry_size = len(entry.gist_id) + len(entry.summary) + 200
            self._cache_size_bytes -= entry_size
            removed = True

        if self.cache_dir:
            cache_file = self.cache_dir / f"{gist_id}.json"
            if cache_file.exists():
                cache_file.unlink()
                removed = True

        if removed:
            logger.info(f"Invalidated gist: {gist_id}")

        return removed

    def invalidate_old_gists(self, days_old: int = 30) -> int:
        """Remove gists older than specified days.

        Args:
            days_old: Age threshold in days

        Returns:
            Number of gists removed
        """
        cutoff = datetime.now() - timedelta(days=days_old)
        to_remove = []

        for gist_id, entry in self._gist_cache.items():
            if entry.created_at < cutoff:
                to_remove.append(gist_id)

        for gist_id in to_remove:
            self.invalidate_gist(gist_id)

        logger.info(f"Invalidated {len(to_remove)} gists older than {days_old} days")
        return len(to_remove)

    def get_cache_metrics(self) -> CacheMetrics:
        """Get current cache performance metrics.

        Returns:
            Cache metrics including hit rate and cost savings
        """
        self._update_metrics()
        return self._metrics

    def clear_cache(self, include_disk: bool = True) -> int:
        """Clear all cached gists.

        Args:
            include_disk: If True, also clear persistent cache

        Returns:
            Number of gists cleared
        """
        count = len(self._gist_cache)

        self._gist_cache.clear()
        self._cache_size_bytes = 0

        if include_disk and self.cache_dir:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

        logger.info(f"Cleared cache: {count} gists removed")
        return count

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "total_gists": len(self._gist_cache),
            "cache_size_mb": self._cache_size_bytes / (1024 * 1024),
            "max_size_mb": self.max_cache_size_bytes / (1024 * 1024),
            "hit_rate": self._metrics.hit_rate,
            "cache_hits": self._metrics.cache_hits,
            "cache_misses": self._metrics.cache_misses,
            "avg_compression_ratio": self._metrics.avg_compression_ratio,
            "cost_savings_percent": self._metrics.cost_savings_percentage,
        }

    # Private helper methods

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using simple heuristic.

        Claude models approximate tokens as:
        - Average word = 1.3 tokens
        - Whitespace/punctuation handled separately

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Simple heuristic: ~4 chars per token on average
        return max(1, len(text) // 4)

    def _generate_summary(
        self, content: str, content_type: str, max_tokens: int
    ) -> str:
        """Generate summary using Claude.

        Args:
            content: Content to summarize
            content_type: Type of content
            max_tokens: Maximum summary tokens

        Returns:
            Generated summary (or fallback if API unavailable)
        """
        try:
            from anthropic import Anthropic

            client = Anthropic()

            # Build prompt based on content type
            if content_type == "code":
                prompt = (
                    f"Summarize this code in {max_tokens} tokens. "
                    "Focus on: purpose, key functions, important patterns.\n\n{content}"
                )
            elif content_type == "memory":
                prompt = (
                    f"Summarize this memory/event in {max_tokens} tokens. "
                    "Include: key facts, timeline, impact.\n\n{content}"
                )
            elif content_type == "query":
                prompt = (
                    f"Rephrase this query concisely in {max_tokens} tokens.\n\n{content}"
                )
            else:  # document
                prompt = (
                    f"Summarize this document in {max_tokens} tokens. "
                    "Capture: main ideas, key points, conclusions.\n\n{content}"
                )

            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text

        except ImportError:
            logger.warning("Anthropic client not available, using fallback")
            return self._fallback_summary(content, max_tokens)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}, using fallback")
            return self._fallback_summary(content, max_tokens)

    def _fallback_summary(self, content: str, max_tokens: int) -> str:
        """Create simple fallback summary when LLM unavailable.

        Args:
            content: Content to summarize
            max_tokens: Maximum tokens (guides summary length)

        Returns:
            Simple summary
        """
        # Simple extraction: first N sentences
        sentences = content.split(". ")[:3]
        summary = ". ".join(sentences)

        if not summary.endswith("."):
            summary += "."

        return summary[:max_tokens * 4]  # Approximate max chars

    def _store_in_cache(self, gist_id: str, entry: GistCacheEntry) -> None:
        """Store gist in cache (memory + disk if configured).

        Args:
            gist_id: ID of gist
            entry: Cache entry to store
        """
        # Store in memory
        self._gist_cache[gist_id] = entry
        # Estimate size: entry object serialization
        entry_size = len(entry.gist_id) + len(entry.summary) + 200  # Rough estimate
        self._cache_size_bytes += entry_size

        # Check cache size and evict if needed
        if self._cache_size_bytes > self.max_cache_size_bytes:
            self._evict_old_entries()

        # Store on disk if configured
        if self.cache_dir:
            self._store_to_disk(gist_id, entry)

    def _get_from_cache(self, gist_id: str) -> Optional[GistCacheEntry]:
        """Retrieve gist from memory or disk cache.

        Args:
            gist_id: ID of gist

        Returns:
            Cache entry if found, None otherwise
        """
        # Check memory cache first (fastest)
        if gist_id in self._gist_cache:
            return self._gist_cache[gist_id]

        # Check disk cache if configured
        if self.cache_dir:
            entry = self._get_from_disk(gist_id)
            if entry:
                # Load into memory cache for faster access
                self._gist_cache[gist_id] = entry
                return entry

        return None

    def _store_to_disk(self, gist_id: str, entry: GistCacheEntry) -> None:
        """Persist gist to disk.

        Args:
            gist_id: ID of gist
            entry: Cache entry to persist
        """
        try:
            cache_file = self.cache_dir / f"{gist_id}.json"
            cache_data = asdict(entry)

            # Serialize datetime objects
            cache_data["created_at"] = entry.created_at.isoformat()
            cache_data["last_accessed"] = entry.last_accessed.isoformat()

            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to persist gist {gist_id}: {e}")

    def _get_from_disk(self, gist_id: str) -> Optional[GistCacheEntry]:
        """Load gist from disk cache.

        Args:
            gist_id: ID of gist

        Returns:
            Cache entry if found, None otherwise
        """
        try:
            cache_file = self.cache_dir / f"{gist_id}.json"

            if cache_file.exists():
                with open(cache_file, "r") as f:
                    data = json.load(f)

                # Deserialize datetime objects
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])

                return GistCacheEntry(**data)

        except Exception as e:
            logger.warning(f"Failed to load gist {gist_id}: {e}")

        return None

    def _evict_old_entries(self) -> None:
        """Evict least recently used entries when cache is full.

        Uses LRU (Least Recently Used) eviction policy.
        """
        # Sort by last_accessed and remove oldest 10%
        sorted_gists = sorted(
            self._gist_cache.items(),
            key=lambda x: x[1].last_accessed,
        )

        evict_count = max(1, len(sorted_gists) // 10)

        for gist_id, _ in sorted_gists[:evict_count]:
            self.invalidate_gist(gist_id)

        logger.info(f"Evicted {evict_count} old gists due to cache size limit")

    def _update_metrics(self) -> None:
        """Update cache metrics.

        Calculates hit rate, cost savings, compression ratio, etc.
        """
        total = self._metrics.cache_hits + self._metrics.cache_misses

        if total > 0:
            self._metrics.hit_rate = self._metrics.cache_hits / total

        # Calculate cost savings
        # Cache tokens cost 10% of input tokens
        cache_tokens_cost = self._metrics.cache_read_tokens * 0.1
        total_cost = self._metrics.total_input_tokens

        if total_cost > 0:
            self._metrics.cost_savings_percentage = (
                (total_cost - cache_tokens_cost) / total_cost
            ) * 100

        # Calculate average compression ratio
        if self._gist_cache:
            total_ratio = sum(
                e.compression_ratio for e in self._gist_cache.values()
            )
            self._metrics.avg_compression_ratio = total_ratio / len(self._gist_cache)

    def _load_persisted_cache(self) -> None:
        """Load all persisted gists from disk cache."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))

            for cache_file in cache_files:
                gist_id = cache_file.stem

                try:
                    entry = self._get_from_disk(gist_id)
                    if entry:
                        self._gist_cache[gist_id] = entry
                        self._cache_size_bytes += len(cache_file.read_bytes())
                except Exception as e:
                    logger.warning(f"Failed to load gist {gist_id}: {e}")

            logger.info(f"Loaded {len(self._gist_cache)} gists from disk cache")

        except Exception as e:
            logger.warning(f"Failed to load persisted cache: {e}")


def create_gist_manager(
    cache_dir: Optional[str | Path] = None, max_cache_size_mb: int = 100
) -> GistManager:
    """Factory function to create a GistManager.

    Args:
        cache_dir: Optional directory for persistent cache
        max_cache_size_mb: Maximum cache size in MB

    Returns:
        GistManager instance
    """
    return GistManager(cache_dir, max_cache_size_mb)
