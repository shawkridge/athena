"""Abstract base classes for compression strategies (v1.1).

Defines common interface and utilities for all compression operations.
"""

import re
from abc import ABC, abstractmethod
from datetime import datetime

from .models import CompressedMemory, CompressionLevel


class BaseCompressor(ABC):
    """Abstract base for all compression strategies."""

    def __init__(self, config):
        """
        Initialize compressor.

        Args:
            config: Configuration object (TemporalDecayConfig, etc.)
        """
        self.config = config

    @abstractmethod
    def compress(self, memory: dict) -> CompressedMemory:
        """
        Compress a single memory.

        Args:
            memory: Memory dict with content, created_at, etc.

        Returns:
            CompressedMemory with compression metadata
        """
        pass

    @abstractmethod
    def decompress(self, memory_id: int) -> str:
        """
        Retrieve original uncompressed content.

        Args:
            memory_id: ID of memory to retrieve

        Returns:
            Original content string
        """
        pass

    @staticmethod
    def estimate_tokens(content: str, tokens_per_char: float = 0.25) -> int:
        """
        Estimate token count.

        Simple heuristic: ~4 chars per token (0.25 tokens per char)

        Args:
            content: Text content
            tokens_per_char: Conversion ratio (default: 0.25)

        Returns:
            Estimated token count
        """
        if not content:
            return 0
        return max(1, int(len(content) * tokens_per_char))

    @staticmethod
    def calculate_compression_ratio(original_len: int, compressed_len: int) -> float:
        """
        Calculate compression ratio.

        Args:
            original_len: Length of original content
            compressed_len: Length of compressed content

        Returns:
            Ratio (compressed_len / original_len), or 0.0 if original_len is 0
        """
        if original_len == 0:
            return 0.0
        return min(1.0, compressed_len / original_len)


# ============================================================================
# Concrete Compressor Implementations (Stubs)
# ============================================================================


class TemporalDecayCompressor(BaseCompressor):
    """Compression based on memory age (temporal decay)."""

    def compress(self, memory: dict) -> CompressedMemory:
        """
        Compress memory based on age.

        Age-based levels:
        - < 7 days: Level 0 (no compression)
        - 7-30 days: Level 1 (50% compression)
        - 30-90 days: Level 2 (80% compression)
        - > 90 days: Level 3 (95% compression)
        """
        # Validate input
        if not memory or "content" not in memory:
            raise ValueError("Memory must have 'content' field")
        if "created_at" not in memory:
            raise ValueError("Memory must have 'created_at' field")

        content = memory["content"]
        created_at = memory["created_at"]
        memory_id = memory.get("id", 0)

        # Calculate age in days
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        age_days = (datetime.now() - created_at).days

        # Determine compression level
        compression_level = self.config.get_level(age_days)

        # Token counts
        tokens_original = self.estimate_tokens(content)

        # Apply compression
        if compression_level == CompressionLevel.NONE:
            compressed_content = content
            tokens_compressed = tokens_original
            fidelity = 1.0
        elif compression_level == CompressionLevel.SUMMARY:
            # Level 1: ~50% compression (detailed summary)
            compressed_content = self._compress_to_summary(content)
            tokens_compressed = self.estimate_tokens(compressed_content)
            fidelity = 0.5
        elif compression_level == CompressionLevel.GIST:
            # Level 2: ~80% compression (key points only)
            compressed_content = self._compress_to_gist(content)
            tokens_compressed = self.estimate_tokens(compressed_content)
            fidelity = 0.2
        else:  # CompressionLevel.REFERENCE
            # Level 3: ~95% compression (metadata only)
            compressed_content = self._compress_to_reference(memory)
            tokens_compressed = self.estimate_tokens(compressed_content)
            fidelity = 0.05

        # Preserve created_at from source memory
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return CompressedMemory(
            memory_id=memory_id,
            content_full=content,
            content_compressed=(
                compressed_content if compression_level != CompressionLevel.NONE else None
            ),
            compression_level=compression_level,
            compression_timestamp=datetime.now(),
            tokens_original=tokens_original,
            tokens_compressed=tokens_compressed,
            fidelity=fidelity,
            created_at=created_at,  # Preserve original creation time
            updated_at=datetime.now(),  # Update modification time
        )

    def decompress(self, memory_id: int) -> str:
        """Retrieve original full content."""
        # In production, would fetch from database
        # For now, return placeholder (actual implementation integrates with DB)
        return f"Original content for memory {memory_id}"

    def _compress_to_summary(self, content: str) -> str:
        """
        Create detailed summary (~50% compression).

        Keeps: first + last sentences, action verbs, entities.
        Target: ~100-150 tokens (50% of typical 200-300 token memory).
        """
        sentences = self._split_sentences(content)

        if len(sentences) == 0:
            return content
        if len(sentences) == 1:
            return sentences[0]

        # Keep first and last sentence
        summary_parts = [sentences[0]]

        # Extract key actions and entities from middle
        if len(sentences) > 2:
            middle_text = " ".join(sentences[1:-1])
            key_actions = self._extract_key_actions(middle_text)
            if key_actions:
                summary_parts.append(key_actions)

        summary_parts.append(sentences[-1])

        return " ".join(summary_parts)

    def _compress_to_gist(self, content: str) -> str:
        """
        Create ultra-short gist (~80% compression).

        Extracts one-sentence summary with subject + action + object.
        Target: ~20-25 tokens.

        Examples:
        - "User implemented JWT authentication with testing"
        - "Fixed CORS configuration and deployment issues"
        """
        sentences = self._split_sentences(content)

        if len(sentences) == 0:
            return "No content"

        # Start with first sentence (usually subject)
        first = sentences[0]

        # Extract actions and entities
        actions = self._extract_key_actions(content)

        if actions:
            # Combine: first sentence + actions
            return f"{first} {actions}".strip()

        # Fallback: just first sentence
        return first

    def _compress_to_reference(self, memory: dict) -> str:
        """
        Create metadata-only reference (~95% compression).

        Minimal representation: id + created_at + extracted topic
        Target: ~5 tokens

        Format: "Memory #{id} ({created_at}): {extracted_topic}"
        """
        memory_id = memory.get("id", "?")
        created_at = memory.get("created_at", "unknown")
        content = memory.get("content", "")

        # Extract topic (first 5-8 words as topic hint)
        topic = self._extract_topic(content)

        return f"Memory #{memory_id} ({created_at}): {topic}"

    @staticmethod
    def _split_sentences(text: str) -> list:
        """Split text into sentences."""
        if not text:
            return []

        # Simple sentence splitting on . ! ?
        sentences = re.split(r"[.!?]+", text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    @staticmethod
    def _extract_key_actions(text: str) -> str:
        """
        Extract action verbs and key entities from text.

        Common actions: implement, fix, add, remove, create, update, test, deploy, etc.
        """
        if not text:
            return ""

        # List of common action verbs in memory contexts
        action_keywords = [
            "implement",
            "fix",
            "add",
            "remove",
            "create",
            "update",
            "test",
            "deploy",
            "configure",
            "integrate",
            "refactor",
            "optimize",
            "analyze",
            "improve",
            "resolve",
            "verify",
            "migrate",
            "validate",
            "debug",
            "enhance",
            "support",
        ]

        # Look for action keywords in text
        found_actions = []
        for keyword in action_keywords:
            if keyword in text.lower():
                # Find the phrase containing this action
                pattern = rf"\b{keyword}\w*[^.!?]*"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    phrase = match.group(0).strip()
                    # Limit to reasonable length
                    if len(phrase) > 100:
                        phrase = phrase[:100]
                    found_actions.append(phrase)

        if found_actions:
            # Return first 2 actions joined
            return ", ".join(found_actions[:2])

        # Fallback: return first 50 chars of middle text
        return text[:50].strip()

    @staticmethod
    def _extract_topic(text: str, max_words: int = 7) -> str:
        """
        Extract topic from text (first few words).

        Target: 2-7 words, ~10-15 tokens
        """
        if not text:
            return "unknown"

        words = text.split()[:max_words]
        topic = " ".join(words)

        # Clean up (remove trailing punctuation)
        topic = re.sub(r"[.!?:,;]+$", "", topic)

        return topic


class ImportanceWeightedBudgeter(BaseCompressor):
    """
    Selection-based compressor (not content compression).

    This doesn't compress content, but selects best memories within token budget.
    Implements the retrieve_with_budget() tool.
    """

    def compress(self, memory: dict) -> CompressedMemory:
        """Not applicable - this compressor works on retrieval, not storage."""
        raise NotImplementedError("Use ImportanceBudgeter for retrieval instead")

    def decompress(self, memory_id: int) -> str:
        """Retrieve original content (no compression applied)."""
        # This compressor doesn't store compressed content
        return f"Memory {memory_id}"

    def calculate_importance_score(self, memory: dict) -> float:
        """
        Calculate importance score for memory.

        Uses: usefulness (40%), recency (30%), frequency (20%), domain (10%)

        Args:
            memory: Memory dict with usefulness_score, created_at, access_count, entity_type

        Returns:
            Importance score (0.0-1.0)
        """
        # Extract fields with defaults
        usefulness = memory.get("usefulness_score", 0.5)
        access_count = memory.get("access_count", 0)
        entity_type = memory.get("entity_type", "fact")

        # Parse created_at if string
        created_at = memory.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        # Calculate age in days
        if created_at:
            age_days = (datetime.now() - created_at).days
        else:
            age_days = 0

        # Use the config's calculation method
        score = self.config.calculate_value_score(
            usefulness=usefulness,
            age_days=age_days,
            access_count=access_count,
            entity_type=entity_type,
        )

        return score

    def retrieve_within_budget(self, memories: list, token_budget: int = 2000) -> tuple:
        """
        Select highest-value memories within token budget.

        Args:
            memories: List of memory dicts
            token_budget: Maximum tokens to allocate

        Returns:
            Tuple of (selected_memories, total_tokens_used)
        """
        if not memories or token_budget <= 0:
            return [], 0

        # Score all memories
        scored_memories = []
        for memory in memories:
            score = self.calculate_importance_score(memory)

            # Skip very low-value memories
            if score < self.config.min_usefulness_score:
                continue

            # Estimate tokens
            content = memory.get("content", "")
            tokens = self.estimate_tokens(content)

            scored_memories.append(
                {
                    "memory": memory,
                    "score": score,
                    "tokens": tokens,
                }
            )

        # Sort by importance score (descending)
        scored_memories.sort(key=lambda x: x["score"], reverse=True)

        # Select memories within budget
        selected = []
        tokens_used = 0

        for item in scored_memories:
            memory_tokens = item["tokens"]
            if tokens_used + memory_tokens <= token_budget:
                selected.append(item["memory"])
                tokens_used += memory_tokens
            else:
                # Check if we can fit a partial memory (at least half the budget remaining)
                remaining_budget = token_budget - tokens_used
                if remaining_budget > 100:  # Arbitrary minimum
                    # Could implement truncation here
                    pass
                break

        return selected, tokens_used

    def select_best_within_budget(self, memories: list, token_budget: int = 2000) -> list:
        """
        Convenience method - returns only selected memories.

        Args:
            memories: List of memory dicts
            token_budget: Maximum tokens to allocate

        Returns:
            Selected memories list
        """
        selected, _ = self.retrieve_within_budget(memories, token_budget)
        return selected

    def get_budget_summary(self, memories: list, token_budget: int = 2000) -> dict:
        """
        Get summary of budget-constrained selection.

        Args:
            memories: List of memory dicts
            token_budget: Maximum tokens to allocate

        Returns:
            Dict with summary stats
        """
        selected, tokens_used = self.retrieve_within_budget(memories, token_budget)

        return {
            "total_candidates": len(memories),
            "selected_count": len(selected),
            "tokens_budget": token_budget,
            "tokens_used": tokens_used,
            "tokens_remaining": token_budget - tokens_used,
            "coverage_percentage": ((len(selected) / len(memories) * 100) if memories else 0),
            "selection_efficiency": ((tokens_used / token_budget) if token_budget > 0 else 0),
        }


class ConsolidationCompressor(BaseCompressor):
    """Generate compressed summaries during consolidation."""

    def compress(self, memory: dict) -> CompressedMemory:
        """
        Generate executive summary from consolidated content.

        Creates ultra-short summary (~20 tokens) from full consolidation (200+ tokens)

        Args:
            memory: Memory dict with content, created_at, id

        Returns:
            CompressedMemory with executive summary
        """
        # Validate input
        if not memory or "content" not in memory:
            raise ValueError("Memory must have 'content' field")
        if "created_at" not in memory:
            raise ValueError("Memory must have 'created_at' field")

        content = memory["content"]
        created_at = memory["created_at"]
        memory_id = memory.get("id", 0)

        # Generate executive summary
        executive_summary = self.extract_executive_summary(content)

        # Token counts
        tokens_original = self.estimate_tokens(content)
        tokens_compressed = self.estimate_tokens(executive_summary)

        # Fidelity: ultra-compressed (similar to reference level)
        fidelity = 0.05  # Executive summary = ~5% of original content

        # Preserve created_at from source memory
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return CompressedMemory(
            memory_id=memory_id,
            content_full=content,
            content_compressed=executive_summary,
            content_executive=executive_summary,  # Store as both
            compression_level=CompressionLevel.REFERENCE,
            compression_timestamp=datetime.now(),
            tokens_original=tokens_original,
            tokens_compressed=tokens_compressed,
            fidelity=fidelity,
            created_at=created_at,
            updated_at=datetime.now(),
            compression_generated_at=datetime.now(),
        )

    def decompress(self, memory_id: int) -> str:
        """
        Retrieve original full content.

        In production, would fetch from database using memory_id.
        For now, returns placeholder indicating retrieval point.

        Args:
            memory_id: ID of memory to retrieve

        Returns:
            Full content string (placeholder for now)
        """
        # In Week 3 phase 2, this will integrate with database
        return f"[Retrieval point: Memory #{memory_id}]"

    def extract_executive_summary(self, full_content: str) -> str:
        """
        Extract ultra-short executive summary from full consolidation.

        Args:
            full_content: Full consolidated memory content

        Returns:
            Executive summary (~20 tokens, target 10-30)
        """
        if not full_content or not full_content.strip():
            return ""

        # Parse sentences
        sentences = self._split_sentences(full_content)
        if not sentences:
            return ""

        # If very short, return as-is (don't over-compress)
        if len(full_content) < 100:
            return sentences[0]

        # Extract key elements
        first_sentence = sentences[0]
        all_actions = self._extract_all_key_actions(full_content)

        # Build ultra-short summary: subject + key action + outcome
        # Strategy: combine first sentence subject with most important action

        # Start with first sentence as base (usually has subject)
        summary_parts = [first_sentence]

        # Add most important action if different from first sentence
        if all_actions:
            # Take first action (usually the most recent/important)
            primary_action = all_actions[0]

            # Check if action already in first sentence
            if primary_action.lower() not in first_sentence.lower():
                summary_parts.append(primary_action)

        # Combine and limit
        summary = " ".join(summary_parts)

        # If too long, truncate to last complete phrase
        # Target: ~20 tokens = ~80 characters (4 chars per token)
        max_chars = 100  # ~25 tokens
        if len(summary) > max_chars:
            # Truncate at word boundary
            summary = summary[:max_chars]
            last_space = summary.rfind(" ")
            if last_space > 50:  # Ensure minimum content (12-13 tokens)
                summary = summary[:last_space].strip()

        # Ensure proper ending
        if summary and not summary.endswith((".", "!", "?")):
            summary += "."

        return summary.strip()

    def _extract_all_key_actions(self, text: str) -> list:
        """
        Extract all key action phrases from text.

        Returns list of action phrases, ordered by position.
        """
        if not text:
            return []

        action_keywords = [
            "implement",
            "fix",
            "add",
            "remove",
            "create",
            "update",
            "test",
            "deploy",
            "configure",
            "integrate",
            "refactor",
            "optimize",
            "analyze",
            "improve",
            "resolve",
            "verify",
            "migrate",
            "validate",
            "debug",
            "enhance",
            "support",
            "compress",
            "extract",
            "design",
            "build",
            "develop",
        ]

        found_actions = []
        text_lower = text.lower()

        for keyword in action_keywords:
            if keyword in text_lower:
                # Find all occurrences
                start = 0
                while True:
                    idx = text_lower.find(keyword, start)
                    if idx == -1:
                        break

                    # Extract phrase around keyword
                    phrase_start = max(0, idx - 20)
                    phrase_end = min(len(text), idx + len(keyword) + 40)
                    phrase = text[phrase_start:phrase_end].strip()

                    # Clean up phrase (remove leading/trailing incomplete words)
                    if phrase_start > 0:
                        first_space = phrase.find(" ")
                        if first_space > 0:
                            phrase = phrase[first_space:].strip()

                    # Keep phrase if reasonable length
                    if 10 < len(phrase) < 120:
                        found_actions.append(phrase)

                    start = idx + len(keyword)

        # Remove duplicates while preserving order
        seen = set()
        unique_actions = []
        for action in found_actions:
            action_lower = action.lower()
            if action_lower not in seen:
                seen.add(action_lower)
                unique_actions.append(action)

        return unique_actions

    @staticmethod
    def _split_sentences(text: str) -> list:
        """Split text into sentences."""
        if not text:
            return []

        # Split on sentence boundaries
        sentences = re.split(r"[.!?]+", text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences


# ============================================================================
# Utility Base Classes
# ============================================================================


class CompressionValidator:
    """Validates compression operations and results."""

    @staticmethod
    def validate_compression(
        original: str, compressed: str, target_ratio: float = 0.1, min_fidelity: float = 0.85
    ) -> bool:
        """
        Validate compressed content.

        Args:
            original: Original content
            compressed: Compressed content
            target_ratio: Target compression ratio (default: 0.1 = 10x)
            min_fidelity: Minimum acceptable fidelity (default: 0.85)

        Returns:
            True if compression meets validation criteria
        """
        if not original or not compressed:
            return False

        ratio = BaseCompressor.calculate_compression_ratio(len(original), len(compressed))

        # Compression should reduce size
        if ratio >= 1.0:
            return False

        # Should meet target ratio (within 20%)
        if ratio > target_ratio * 1.2:
            return False

        # Compressed should preserve some content
        if len(compressed) < len(original) * (1.0 - min_fidelity):
            return False

        return True

    @staticmethod
    def validate_memory_dict(memory: dict) -> bool:
        """
        Validate memory dict has required fields.

        Args:
            memory: Memory dictionary

        Returns:
            True if memory has required fields
        """
        required_fields = ["id", "content", "created_at"]
        return all(field in memory for field in required_fields)


class CompressionMetricsCollector:
    """Collects metrics from compression operations."""

    def __init__(self):
        """Initialize metrics collector."""
        self.total_memories = 0
        self.compressed_memories = 0
        self.total_tokens_original = 0
        self.total_tokens_compressed = 0
        self.compression_operations = []

    def record_compression(
        self,
        memory_id: int,
        original_tokens: int,
        compressed_tokens: int,
        compression_level: CompressionLevel,
    ):
        """Record a compression operation."""
        self.total_memories += 1
        if compression_level != CompressionLevel.NONE:
            self.compressed_memories += 1

        self.total_tokens_original += original_tokens
        self.total_tokens_compressed += compressed_tokens

        self.compression_operations.append(
            {
                "memory_id": memory_id,
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "compression_level": compression_level,
                "timestamp": datetime.now(),
            }
        )

    def get_summary(self) -> dict:
        """Get compression metrics summary."""
        total_saved = self.total_tokens_original - self.total_tokens_compressed

        return {
            "total_memories": self.total_memories,
            "compressed_memories": self.compressed_memories,
            "total_tokens_original": self.total_tokens_original,
            "total_tokens_compressed": self.total_tokens_compressed,
            "total_tokens_saved": total_saved,
            "overall_ratio": (
                self.total_tokens_compressed / self.total_tokens_original
                if self.total_tokens_original > 0
                else 0.0
            ),
            "compression_percentage": (
                (self.compressed_memories / self.total_memories * 100)
                if self.total_memories > 0
                else 0.0
            ),
        }
