"""Session-aware context management with token efficiency optimization.

Implements Phase 3 optimizations:
- Session memory cache (deduplication)
- Token estimation and budget tracking
- Adaptive formatting based on relevance
- Enhanced prioritization with recency decay
- TOON (Token-Oriented Object Notation) serialization for ~40% token savings
"""

import os
import json
import time
import tempfile
import sys
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Try to import TOON encoder (may not be available in all environments)
try:
    # Adjust path for hook environment
    sys.path.insert(0, '/home/user/.work/athena/src')
    from athena.core.toon_encoder import TOONEncoder
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False
    TOONEncoder = None  # type: ignore

# Session cache location (per-session to avoid interference)
SESSION_CACHE_DIR = os.path.join(tempfile.gettempdir(), ".claude_session_cache")


@dataclass
class TokenBudget:
    """Track token usage for current session."""

    total_budget: int = 2000  # Conservative estimate per interaction
    used_tokens: int = 0
    remaining_tokens: int = field(init=False)

    def __post_init__(self):
        self.remaining_tokens = self.total_budget - self.used_tokens

    def use_tokens(self, tokens: int) -> bool:
        """Consume tokens from budget. Returns True if successful."""
        if tokens <= self.remaining_tokens:
            self.used_tokens += tokens
            self.remaining_tokens -= tokens
            return True
        return False

    def reset(self):
        """Reset budget for new interaction."""
        self.used_tokens = 0
        self.remaining_tokens = self.total_budget


@dataclass
class CachedMemory:
    """Track injected memory for deduplication."""

    memory_id: str
    injection_time: float
    relevance_score: float
    content: str
    inject_count: int = 1
    last_injected: float = field(default_factory=time.time)


class SessionMemoryCache:
    """Track injected memories to prevent redundant injections."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize session cache.

        Args:
            session_id: Unique session identifier (from Claude Code)
        """
        self.session_id = session_id or self._get_default_session_id()
        self.injected_memories: Dict[str, CachedMemory] = {}
        self.cache_file = self._get_cache_file()
        self._load_cache()

    def _get_default_session_id(self) -> str:
        """Generate session ID from PID and timestamp."""
        pid = os.getpid()
        timestamp = int(time.time() * 1000)
        return f"session_{pid}_{timestamp}"

    def _get_cache_file(self) -> str:
        """Get cache file path for this session."""
        os.makedirs(SESSION_CACHE_DIR, exist_ok=True)
        return os.path.join(SESSION_CACHE_DIR, f"{self.session_id}.json")

    def _load_cache(self):
        """Load cache from disk if exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    for mem_id, cached in data.get('memories', {}).items():
                        self.injected_memories[mem_id] = CachedMemory(**cached)
                logger.debug(f"Loaded {len(self.injected_memories)} cached memories")
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")

    def _save_cache(self):
        """Persist cache to disk."""
        try:
            data = {
                'session_id': self.session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'memories': {
                    mem_id: asdict(cached)
                    for mem_id, cached in self.injected_memories.items()
                }
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")

    def should_inject(self, memory_id: str, min_relevance_increase: float = 0.1) -> bool:
        """Determine if memory should be injected (deduplication).

        Args:
            memory_id: Memory ID to check
            min_relevance_increase: Skip re-injection unless relevance increased by this much

        Returns:
            True if memory should be injected
        """
        if memory_id not in self.injected_memories:
            return True

        cached = self.injected_memories[memory_id]
        # Skip if recently injected (within 5 minutes)
        if time.time() - cached.last_injected < 300:
            return False

        return True

    def mark_injected(self, memory_id: str, relevance_score: float, content: str):
        """Mark memory as injected."""
        if memory_id in self.injected_memories:
            cached = self.injected_memories[memory_id]
            cached.inject_count += 1
            cached.last_injected = time.time()
            cached.relevance_score = relevance_score
        else:
            self.injected_memories[memory_id] = CachedMemory(
                memory_id=memory_id,
                injection_time=time.time(),
                relevance_score=relevance_score,
                content=content
            )
        self._save_cache()

    def get_injection_stats(self) -> Dict:
        """Get statistics about this session's injections."""
        if not self.injected_memories:
            return {"total_injected": 0, "unique_memories": 0}

        return {
            "total_injected": sum(m.inject_count for m in self.injected_memories.values()),
            "unique_memories": len(self.injected_memories),
            "avg_relevance": sum(m.relevance_score for m in self.injected_memories.values()) / len(self.injected_memories),
        }


class TokenEstimator:
    """Estimate token counts for text (approximation)."""

    # Rough estimation: 1 token ≈ 4 characters (OpenAI's estimate)
    CHARS_PER_TOKEN = 4

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text."""
        return max(1, len(text) // TokenEstimator.CHARS_PER_TOKEN)

    @staticmethod
    def truncate_to_budget(text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        max_chars = max_tokens * TokenEstimator.CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars].rsplit(' ', 1)[0]
        return truncated + "..."


class AdaptiveFormatter:
    """Format context based on relevance score and token budget."""

    # Formatting tiers
    HIGH_RELEVANCE_THRESHOLD = 0.85
    MEDIUM_RELEVANCE_THRESHOLD = 0.70

    @staticmethod
    def format_memory(
        memory_id: str,
        title: str,
        content: str,
        relevance_score: float,
        memory_type: str = "memory",
        timestamp: Optional[str] = None
    ) -> Tuple[str, int]:
        """Format memory with adaptive detail level.

        Args:
            memory_id: Unique memory identifier
            title: Memory title/summary
            content: Full content
            relevance_score: 0.0-1.0 relevance score
            memory_type: Type of memory (e.g., "implementation", "procedure")
            timestamp: ISO timestamp

        Returns:
            (formatted_text, estimated_tokens)
        """
        if relevance_score >= AdaptiveFormatter.HIGH_RELEVANCE_THRESHOLD:
            # Full context for high relevance
            formatted = AdaptiveFormatter._format_full(
                memory_id, title, content, relevance_score, memory_type
            )
        elif relevance_score >= AdaptiveFormatter.MEDIUM_RELEVANCE_THRESHOLD:
            # Summary only for medium relevance
            formatted = AdaptiveFormatter._format_summary(
                memory_id, title, content[:100], relevance_score, memory_type
            )
        else:
            # Reference only for low relevance
            formatted = AdaptiveFormatter._format_reference(
                memory_id, title, relevance_score
            )

        tokens = TokenEstimator.estimate_tokens(formatted)
        return formatted, tokens

    @staticmethod
    def _format_full(
        memory_id: str, title: str, content: str, relevance: float, mem_type: str
    ) -> str:
        """Full context format (~200 tokens)."""
        return (
            f"- **[{mem_type}]** {title}\n"
            f"  Content: {content[:200]}\n"
            f"  Relevance: {relevance:.0%} (ID: {memory_id[:8]})\n"
        )

    @staticmethod
    def _format_summary(
        memory_id: str, title: str, preview: str, relevance: float, mem_type: str
    ) -> str:
        """Summary format (~80 tokens)."""
        return (
            f"- [{mem_type}] {title}\n"
            f"  {preview}\n"
            f"  (ID: {memory_id[:8]})\n"
        )

    @staticmethod
    def _format_reference(
        memory_id: str, title: str, relevance: float
    ) -> str:
        """Reference-only format (~30 tokens)."""
        return f"- {title} ({memory_id[:8]})\n"


class PrioritizationAlgorithm:
    """Enhanced prioritization with recency decay and success tracking."""

    # Decay function: how much weight to give memories by age
    RECENCY_DECAY = {
        "1_hour": 1.0,      # <1 hour: full weight
        "1_day": 0.9,       # <1 day: 90%
        "1_week": 0.7,      # <1 week: 70%
        "1_month": 0.5,     # <1 month: 50%
        "older": 0.3,       # >1 month: 30%
    }

    # Scoring weights
    WEIGHTS = {
        "semantic_similarity": 0.40,
        "recency": 0.25,
        "importance": 0.20,
        "access_frequency": 0.10,
        "success_indicator": 0.05,
    }

    @staticmethod
    def calculate_recency_score(timestamp_iso: str) -> float:
        """Calculate recency score with decay.

        Args:
            timestamp_iso: ISO format timestamp

        Returns:
            Recency score (0.3-1.0)
        """
        try:
            mem_time = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
            now = datetime.utcnow().replace(tzinfo=None)
            mem_time = mem_time.replace(tzinfo=None)
            age = now - mem_time
        except:
            # If parsing fails, treat as old
            return PrioritizationAlgorithm.RECENCY_DECAY["older"]

        if age < timedelta(hours=1):
            return PrioritizationAlgorithm.RECENCY_DECAY["1_hour"]
        elif age < timedelta(days=1):
            return PrioritizationAlgorithm.RECENCY_DECAY["1_day"]
        elif age < timedelta(weeks=1):
            return PrioritizationAlgorithm.RECENCY_DECAY["1_week"]
        elif age < timedelta(days=30):
            return PrioritizationAlgorithm.RECENCY_DECAY["1_month"]
        else:
            return PrioritizationAlgorithm.RECENCY_DECAY["older"]

    @staticmethod
    def calculate_composite_score(
        semantic_similarity: float,
        timestamp_iso: Optional[str] = None,
        importance: float = 0.5,
        access_frequency: int = 1,
        success_indicator: bool = False,
    ) -> float:
        """Calculate composite relevance score.

        Args:
            semantic_similarity: 0.0-1.0
            timestamp_iso: ISO timestamp (for recency calculation)
            importance: 0.0-1.0 (user-assigned)
            access_frequency: Number of times accessed
            success_indicator: Did this lead to positive outcome?

        Returns:
            Composite score (0.0-1.0)
        """
        recency = PrioritizationAlgorithm.calculate_recency_score(
            timestamp_iso or datetime.utcnow().isoformat()
        )

        # Normalize frequency (cap at 10)
        frequency_score = min(access_frequency / 10.0, 1.0)

        success_score = 1.0 if success_indicator else 0.5

        composite = (
            semantic_similarity * PrioritizationAlgorithm.WEIGHTS["semantic_similarity"] +
            recency * PrioritizationAlgorithm.WEIGHTS["recency"] +
            importance * PrioritizationAlgorithm.WEIGHTS["importance"] +
            frequency_score * PrioritizationAlgorithm.WEIGHTS["access_frequency"] +
            success_score * PrioritizationAlgorithm.WEIGHTS["success_indicator"]
        )

        return min(composite, 1.0)

    @staticmethod
    def rank_memories(memories: List[Dict]) -> List[Dict]:
        """Rank memories by composite score.

        Args:
            memories: List of memory dicts with relevance, timestamp, importance, etc.

        Returns:
            Sorted list (highest score first)
        """
        scored = []
        for mem in memories:
            score = PrioritizationAlgorithm.calculate_composite_score(
                semantic_similarity=mem.get("semantic_similarity", mem.get("relevance", 0.5)),
                timestamp_iso=mem.get("timestamp"),
                importance=mem.get("importance", 0.5),
                access_frequency=mem.get("access_count", 1),
                success_indicator=mem.get("success_indicator", False),
            )
            mem_copy = mem.copy()
            mem_copy["composite_score"] = score
            scored.append(mem_copy)

        return sorted(scored, key=lambda x: x["composite_score"], reverse=True)


class SessionContextManager:
    """High-level session context manager combining all Phase 3 components."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize session manager."""
        self.session_id = session_id
        self.cache = SessionMemoryCache(session_id)
        self.budget = TokenBudget()
        self.formatter = AdaptiveFormatter()
        self.prioritizer = PrioritizationAlgorithm()

    def should_inject_memory(self, memory_id: str) -> bool:
        """Check if memory should be injected (deduplication)."""
        return self.cache.should_inject(memory_id)

    def format_context_adaptive(
        self,
        memories: List[Dict],
        max_tokens: int = 500,
    ) -> Tuple[str, List[str], int]:
        """Format memories with adaptive detail based on relevance and budget.

        Args:
            memories: List of memory dicts with relevance, content, etc.
            max_tokens: Maximum tokens to use

        Returns:
            (formatted_text, injected_memory_ids, total_tokens_used)
        """
        # Rank and filter memories
        ranked = self.prioritizer.rank_memories(memories)

        # Use only memories that should be injected (deduplication)
        candidates = [m for m in ranked if self.should_inject_memory(m["id"])]

        # Format with adaptive detail, respecting budget
        formatted_lines = []
        injected_ids = []
        total_tokens = 0

        for mem in candidates:
            if total_tokens >= max_tokens:
                break

            formatted, tokens = self.formatter.format_memory(
                memory_id=mem["id"],
                title=mem.get("title", "Memory"),
                content=mem.get("content", ""),
                relevance_score=mem.get("composite_score", 0.5),
                memory_type=mem.get("type", "memory"),
                timestamp=mem.get("timestamp"),
            )

            if total_tokens + tokens <= max_tokens:
                formatted_lines.append(formatted)
                injected_ids.append(mem["id"])
                total_tokens += tokens
                self.cache.mark_injected(mem["id"], mem.get("composite_score", 0.5), mem.get("content", ""))

        full_text = "".join(formatted_lines) if formatted_lines else ""
        return full_text, injected_ids, total_tokens

    def format_context_toon(
        self,
        memories: List[Dict],
        max_tokens: int = 500,
    ) -> Tuple[str, List[str], int]:
        """Format memories as TOON (Token-Oriented Object Notation).

        TOON achieves ~40% token reduction vs JSON for uniform arrays of objects.
        This is the preferred format for working memory injection.

        Args:
            memories: List of memory dicts with relevance, content, etc.
            max_tokens: Maximum tokens to use (TOON uses ~60% of JSON budget)

        Returns:
            (toon_formatted_text, injected_memory_ids, estimated_tokens_used)
        """
        if not TOON_AVAILABLE or TOONEncoder is None:
            # Fallback to adaptive formatting if TOON not available
            return self.format_context_adaptive(memories, max_tokens)

        # Rank and filter memories (same as adaptive)
        ranked = self.prioritizer.rank_memories(memories)
        candidates = [m for m in ranked if self.should_inject_memory(m["id"])]

        # Filter to high-relevance items for TOON (top-K only)
        # TOON tabular format works best with consistent data
        toon_items = []
        injected_ids = []

        for mem in candidates[:7]:  # TOON works best with 7±2 items (Baddeley's limit)
            # Include core fields
            toon_item = {
                "id": mem["id"][:8],  # Shorten IDs
                "title": mem.get("title", "Memory"),
                "type": mem.get("type", "memory"),
                "importance": round(mem.get("importance", 0.5), 2),
                "score": round(mem.get("composite_score", 0.5), 2),
            }
            toon_items.append(toon_item)
            injected_ids.append(mem["id"])
            self.cache.mark_injected(mem["id"], mem.get("composite_score", 0.5), mem.get("content", ""))

        # Encode to TOON
        if toon_items:
            toon_text = TOONEncoder.encode_working_memory(toon_items)
        else:
            toon_text = ""

        # Estimate tokens (TOON is ~60% of JSON size)
        estimated_tokens = max(1, len(toon_text) // 4)  # Conservative estimate

        return toon_text, injected_ids, estimated_tokens

    def get_session_stats(self) -> Dict:
        """Get statistics about this session."""
        return {
            "session_id": self.session_id,
            "cache_stats": self.cache.get_injection_stats(),
            "budget": {
                "total": self.budget.total_budget,
                "used": self.budget.used_tokens,
                "remaining": self.budget.remaining_tokens,
            }
        }
