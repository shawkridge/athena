"""Compression Manager - Coordinates all compression strategies (v1.1).

Unified interface for:
- Temporal decay compression
- Importance-weighted budgeting
- Consolidation compression
"""

from typing import List, Optional, Tuple
from datetime import datetime

from .base import (
    TemporalDecayCompressor,
    ImportanceWeightedBudgeter,
    ConsolidationCompressor,
)
from .models import (
    CompressionConfig,
    CompressedMemory,
)


class CompressionManager:
    """
    Unified compression manager for all strategies.

    Coordinates temporal decay, importance budgeting, and consolidation compression.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        """
        Initialize compression manager.

        Args:
            config: CompressionConfig with all sub-configs (default: defaults)
        """
        self.config = config or CompressionConfig()
        self.config.validate()

        # Initialize compressors
        self.temporal_decay = TemporalDecayCompressor(self.config.temporal_decay)
        self.importance_budgeter = ImportanceWeightedBudgeter(self.config.importance_budgeting)
        self.consolidation = ConsolidationCompressor(self.config.consolidation_compression)

        # Metrics tracking
        self.operations_count = 0
        self.total_tokens_original = 0
        self.total_tokens_compressed = 0

    # ========================================================================
    # Temporal Decay Compression
    # ========================================================================

    def compress_with_decay(self, memory: dict) -> CompressedMemory:
        """
        Compress memory using temporal decay strategy.

        Args:
            memory: Memory dict with content, created_at

        Returns:
            CompressedMemory with age-based compression
        """
        if not self.config.temporal_decay.enable:
            raise ValueError("Temporal decay compression is disabled")

        result = self.temporal_decay.compress(memory)
        self._record_compression(result)
        return result

    def decompress_with_decay(self, memory_id: int) -> str:
        """
        Retrieve full content after temporal decay compression.

        Args:
            memory_id: Memory ID to decompress

        Returns:
            Full original content
        """
        return self.temporal_decay.decompress(memory_id)

    # ========================================================================
    # Importance-Weighted Budgeting
    # ========================================================================

    def select_with_budget(
        self,
        memories: List[dict],
        token_budget: int = 2000,
    ) -> Tuple[List[dict], int]:
        """
        Select highest-value memories within token budget.

        Args:
            memories: List of memory dicts
            token_budget: Maximum tokens to allocate

        Returns:
            Tuple of (selected_memories, tokens_used)
        """
        if not self.config.importance_budgeting.enable:
            raise ValueError("Importance budgeting is disabled")

        selected, tokens_used = self.importance_budgeter.retrieve_within_budget(
            memories,
            token_budget=token_budget,
        )

        return selected, tokens_used

    def get_budget_summary(
        self,
        memories: List[dict],
        token_budget: int = 2000,
    ) -> dict:
        """
        Get summary of budget-constrained selection.

        Args:
            memories: List of memory dicts
            token_budget: Maximum tokens to allocate

        Returns:
            Summary dict with efficiency metrics
        """
        return self.importance_budgeter.get_budget_summary(memories, token_budget)

    # ========================================================================
    # Consolidation Compression
    # ========================================================================

    def compress_consolidation(self, consolidation: dict) -> CompressedMemory:
        """
        Compress consolidation with executive summary.

        Args:
            consolidation: Consolidation dict with full_content, created_at

        Returns:
            CompressedMemory with executive summary
        """
        if not self.config.consolidation_compression.enable:
            raise ValueError("Consolidation compression is disabled")

        # Rename 'full_content' to 'content' for compressor interface
        memory = {
            "id": consolidation.get("id", 0),
            "content": consolidation.get("full_content", consolidation.get("content", "")),
            "created_at": consolidation.get("created_at", datetime.now()),
        }

        result = self.consolidation.compress(memory)
        self._record_compression(result)
        return result

    def extract_executive_summary(self, full_content: str) -> str:
        """
        Extract ultra-short executive summary from consolidation.

        Args:
            full_content: Full consolidated memory content

        Returns:
            Executive summary (~20 tokens)
        """
        return self.consolidation.extract_executive_summary(full_content)

    # ========================================================================
    # Strategy Selection
    # ========================================================================

    def select_compression_strategy(
        self,
        memory: dict,
        strategy: Optional[str] = None,
    ) -> CompressedMemory:
        """
        Select and apply appropriate compression strategy.

        Strategies:
        - "decay": Age-based temporal decay
        - "consolidation": Executive summary for consolidated memories
        - "auto": Select based on memory type/age (default)

        Args:
            memory: Memory dict
            strategy: Compression strategy name

        Returns:
            CompressedMemory result
        """
        if not strategy or strategy == "auto":
            # Auto-select strategy based on memory characteristics
            memory_type = memory.get("entity_type", "fact")
            age_days = self._get_memory_age(memory)

            if memory_type == "consolidation" or "consolidation" in memory.get("tags", []):
                # Use consolidation strategy for consolidated memories
                strategy = "consolidation"
            else:
                # Use decay strategy for regular memories
                strategy = "decay"

        if strategy == "decay":
            return self.compress_with_decay(memory)
        elif strategy == "consolidation":
            return self.compress_consolidation(memory)
        else:
            raise ValueError(f"Unknown compression strategy: {strategy}")

    # ========================================================================
    # Metrics & Analytics
    # ========================================================================

    def get_compression_stats(self) -> dict:
        """
        Get compression statistics.

        Returns:
            Dict with compression metrics
        """
        overall_ratio = (
            self.total_tokens_compressed / self.total_tokens_original
            if self.total_tokens_original > 0
            else 0.0
        )

        return {
            "total_operations": self.operations_count,
            "total_tokens_original": self.total_tokens_original,
            "total_tokens_compressed": self.total_tokens_compressed,
            "tokens_saved": self.total_tokens_original - self.total_tokens_compressed,
            "overall_compression_ratio": overall_ratio,
            "average_compression_ratio": overall_ratio,
            "compression_percentage": (1.0 - overall_ratio) * 100,
        }

    def reset_stats(self):
        """Reset compression statistics."""
        self.operations_count = 0
        self.total_tokens_original = 0
        self.total_tokens_compressed = 0

    # ========================================================================
    # Configuration
    # ========================================================================

    def get_configuration(self) -> dict:
        """Get current compression configuration."""
        return self.config.to_dict()

    def update_configuration(self, updates: dict):
        """
        Update compression configuration.

        Args:
            updates: Dict of configuration updates
        """
        # Parse and apply updates to config
        if "temporal_decay" in updates:
            td_config = self.config.temporal_decay
            td_updates = updates["temporal_decay"]
            if "decay_schedule" in td_updates:
                td_config.decay_schedule.update(td_updates["decay_schedule"])
            if "min_fidelity" in td_updates:
                td_config.min_fidelity = td_updates["min_fidelity"]

        if "importance_budgeting" in updates:
            ib_config = self.config.importance_budgeting
            ib_updates = updates["importance_budgeting"]
            if "weights" in ib_updates:
                ib_config.weights.update(ib_updates["weights"])
            if "min_usefulness_score" in ib_updates:
                ib_config.min_usefulness_score = ib_updates["min_usefulness_score"]

        self.config.validate()

    # ========================================================================
    # Private Helpers
    # ========================================================================

    def _record_compression(self, result: CompressedMemory):
        """Record compression operation for metrics."""
        self.operations_count += 1
        self.total_tokens_original += result.tokens_original
        self.total_tokens_compressed += result.tokens_compressed

    def _get_memory_age(self, memory: dict) -> int:
        """Get memory age in days."""
        created_at = memory.get("created_at")
        if not created_at:
            return 0

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return (datetime.now() - created_at).days
