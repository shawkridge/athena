"""MCP tool definitions for compression features (v1.1).

This module defines the three core compression MCP tools:
1. retrieve_with_decay() - Temporal decay compression
2. retrieve_with_budget() - Importance-weighted budgeting
3. consolidate_with_compression() - Consolidation with executive summaries
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


# ============================================================================
# Data Models for MCP Tool Results
# ============================================================================


@dataclass
class CompressedMemoryResult:
    """Result from compression-enabled retrieval."""

    memory_id: int
    content: str  # Which version: full or compressed
    compression_level: int  # 0=none, 1=summary, 2=gist, 3=reference
    tokens_original: int
    tokens_compressed: int
    fidelity: float  # 1.0=full, 0.5=50% quality
    is_compressed: bool


@dataclass
class BudgetedRetrievalResult:
    """Result from budget-constrained retrieval."""

    memories: List[dict]  # List of memories within budget
    tokens_used: int
    token_budget: int
    efficiency: float  # tokens_used / budget
    average_usefulness: float
    dropped_memories: int  # How many couldn't fit in budget
    selected_count: int


@dataclass
class ConsolidationCompressionResult:
    """Result from consolidation with compression."""

    consolidations: int  # Total patterns created
    compressed: int  # With executive summary
    tokens_saved: List[float]  # Per consolidation
    average_compression: float  # e.g., 9.5x
    total_tokens_saved: int
    errors: List[str] = None  # Any errors during consolidation


# ============================================================================
# MCP Tool 1: retrieve_with_decay()
# ============================================================================


class RetrieveWithDecayTool:
    """
    Retrieve memories with optional temporal decay compression.

    Compresses memories based on age:
    - < 7 days: 100% fidelity (full content)
    - 7-30 days: 50% compression (detailed summary)
    - 30-90 days: 80% compression (gist only)
    - > 90 days: 95% compression (reference + metadata)

    This mimics human memory decay while preserving retrieval capability.
    """

    name = "retrieve_with_decay"
    description = "Retrieve memories with optional temporal decay compression based on age"

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for semantic retrieval"
            },
            "apply_decay": {
                "type": "boolean",
                "description": "Whether to apply temporal decay compression (default: true)",
                "default": True
            },
            "min_fidelity": {
                "type": "number",
                "description": "Minimum fidelity to return (0.0-1.0). "
                              "If memory would compress below threshold, return uncompressed. "
                              "Default: 0.5 (don't return < 50% quality)",
                "default": 0.5,
                "minimum": 0.0,
                "maximum": 1.0
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default: 10)",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            "decay_schedule": {
                "type": "object",
                "description": "Override default decay schedule (optional). "
                              "Keys: 'recent', 'detailed', 'gist', 'reference'. "
                              "Values: age in days",
                "properties": {
                    "recent": {"type": "integer", "description": "Threshold for recent (days)"},
                    "detailed": {"type": "integer", "description": "Threshold for detailed (days)"},
                    "gist": {"type": "integer", "description": "Threshold for gist (days)"},
                    "reference": {"type": "integer", "description": "Threshold for reference (days)"}
                }
            }
        },
        "required": ["query"]
    }

    @staticmethod
    async def execute(query: str,
                     apply_decay: bool = True,
                     min_fidelity: float = 0.5,
                     limit: int = 10,
                     decay_schedule: Optional[dict] = None) -> List[CompressedMemoryResult]:
        """
        Execute retrieve_with_decay operation.

        Args:
            query: Search query
            apply_decay: Whether to apply decay (default: True)
            min_fidelity: Minimum fidelity threshold (default: 0.5)
            limit: Max results (default: 10)
            decay_schedule: Override default schedule (optional)

        Returns:
            List of CompressedMemoryResult objects

        Example:
            # Get memories, compress if > 30 days old
            results = await retrieve_with_decay(
                "JWT implementation strategy",
                apply_decay=True,
                min_fidelity=0.5
            )

            for result in results:
                if result.is_compressed:
                    print(f"[Compressed Level {result.compression_level}] {result.content}")
                else:
                    print(f"[Full] {result.content}")
        """
        # NOTE: Full implementation requires UnifiedMemoryManager integration (Week 3)
        # This placeholder shows the expected behavior

        from .models import TemporalDecayConfig
        from .base import TemporalDecayCompressor

        # Build config
        config = TemporalDecayConfig(enable=apply_decay)
        if decay_schedule:
            config.decay_schedule.update(decay_schedule)
        config.min_fidelity = min_fidelity

        # Create compressor
        compressor = TemporalDecayCompressor(config)

        # NOTE: In production, would:
        # 1. Call UnifiedMemoryManager.smart_retrieve(query, k=limit)
        # 2. For each memory, call compressor.compress()
        # 3. Filter by min_fidelity
        # 4. Return as CompressedMemoryResult list

        # Placeholder: Return empty for now (full implementation in Week 3)
        return []


# ============================================================================
# MCP Tool 2: retrieve_with_budget()
# ============================================================================


class RetrieveWithBudgetTool:
    """
    Retrieve highest-value memories within token budget.

    Uses importance-weighted scoring based on:
    - usefulness_score (40%)
    - recency boost (30%)
    - access_frequency (20%)
    - domain_relevance (10%)

    Selects best memories within token budget constraint.
    """

    name = "retrieve_with_budget"
    description = "Retrieve highest-value memories within token budget"

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for semantic retrieval"
            },
            "token_budget": {
                "type": "integer",
                "description": "Maximum tokens to use (default: 2000)",
                "default": 2000,
                "minimum": 100,
                "maximum": 50000
            },
            "min_usefulness": {
                "type": "number",
                "description": "Only return memories with usefulness >= threshold (default: 0.5)",
                "default": 0.5,
                "minimum": 0.0,
                "maximum": 1.0
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Include token cost estimates in result (default: false)",
                "default": False
            }
        },
        "required": ["query"]
    }

    @staticmethod
    async def execute(query: str,
                     token_budget: int = 2000,
                     min_usefulness: float = 0.5,
                     include_metadata: bool = False) -> BudgetedRetrievalResult:
        """
        Execute retrieve_with_budget operation.

        Args:
            query: Search query
            token_budget: Max tokens to use (default: 2000)
            min_usefulness: Minimum usefulness threshold (default: 0.5)
            include_metadata: Include detailed cost info (default: False)

        Returns:
            BudgetedRetrievalResult with memories + usage stats

        Example:
            # Get best memories in 1000 tokens
            result = await retrieve_with_budget(
                query="Database connection pooling",
                token_budget=1000
            )

            print(f"Retrieved {len(result.memories)} memories")
            print(f"Used {result.tokens_used} / {result.token_budget} tokens")
            print(f"Efficiency: {result.efficiency:.1%}")

            for memory in result.memories:
                print(f"- {memory['content'][:100]}...")
        """
        # NOTE: Full implementation requires UnifiedMemoryManager integration (Week 3)
        # This placeholder shows the expected behavior

        from .models import ImportanceWeightedBudgetConfig
        from .base import ImportanceWeightedBudgeter

        # Build config
        config = ImportanceWeightedBudgetConfig(enable=True)
        config.min_usefulness_score = min_usefulness

        # Create budgeter
        budgeter = ImportanceWeightedBudgeter(config)

        # NOTE: In production, would:
        # 1. Call UnifiedMemoryManager.smart_retrieve(query, k=50) to get candidates
        # 2. Call budgeter.retrieve_within_budget(candidates, token_budget)
        # 3. Calculate average usefulness from selected
        # 4. Return BudgetedRetrievalResult with stats

        # Placeholder: Return empty for now (full implementation in Week 3)
        return BudgetedRetrievalResult(
            memories=[],
            tokens_used=0,
            token_budget=token_budget,
            efficiency=0.0,
            average_usefulness=0.0,
            dropped_memories=0,
            selected_count=0,
        )


# ============================================================================
# MCP Tool 3: consolidate_with_compression()
# ============================================================================


class ConsolidateWithCompressionTool:
    """
    Run consolidation, optionally generating compressed executive summaries.

    Consolidation is the process of:
    1. Grouping episodic events into themes
    2. Extracting patterns
    3. Storing as semantic memories
    4. (New) Generating ultra-short executive summaries

    Executive summaries are ~20 tokens vs 200+ for full consolidation,
    enabling massive context savings.
    """

    name = "consolidate_with_compression"
    description = "Run consolidation with optional executive summary compression"

    input_schema = {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "integer",
                "description": "Project ID to consolidate"
            },
            "max_age_days": {
                "type": "integer",
                "description": "Only consolidate events older than this (default: 30)",
                "default": 30,
                "minimum": 1,
                "maximum": 365
            },
            "generate_compression": {
                "type": "boolean",
                "description": "Generate compressed executive summaries (default: true)",
                "default": True
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview consolidation without writing to DB (default: false)",
                "default": False
            }
        },
        "required": ["project_id"]
    }

    @staticmethod
    async def execute(project_id: int,
                     max_age_days: int = 30,
                     generate_compression: bool = True,
                     dry_run: bool = False) -> ConsolidationCompressionResult:
        """
        Execute consolidate_with_compression operation.

        Args:
            project_id: Project to consolidate
            max_age_days: Only consolidate events older than this (default: 30)
            generate_compression: Also create executive summaries (default: True)
            dry_run: Preview without writing (default: False)

        Returns:
            ConsolidationCompressionResult with metrics

        Example:
            # Run consolidation with compression enabled
            result = await consolidate_with_compression(
                project_id=1,
                max_age_days=14,  # Consolidate events > 2 weeks old
                generate_compression=True
            )

            print(f"Created {result.consolidations} patterns")
            print(f"Compressed {result.compressed} of them")
            print(f"Average compression: {result.average_compression:.1f}x")
            print(f"Total tokens saved: {result.total_tokens_saved}")

            # Example: 5 consolidations, all compressed
            # Created 5 patterns
            # Compressed 5 of them
            # Average compression: 9.5x
            # Total tokens saved: 3400
        """
        # NOTE: Full implementation in Week 3
        # Requires ConsolidationCompressor integration + manager integration

        # Placeholder structure for Week 3 implementation:
        # 1. Call UnifiedMemoryManager.get_consolidatable_events(project_id, max_age_days)
        # 2. For each consolidation, call ConsolidationCompressor.compress()
        # 3. Track metrics (consolidations, compressed, tokens_saved)
        # 4. If not dry_run, save to database
        # 5. Return ConsolidationCompressionResult

        return ConsolidationCompressionResult(
            consolidations=0,
            compressed=0,
            tokens_saved=[],
            average_compression=0.0,
            total_tokens_saved=0,
            errors=None if not dry_run else ["Placeholder: Implementation pending Week 3"],
        )


# ============================================================================
# Tool Registration (for MCP Server)
# ============================================================================


COMPRESSION_TOOLS = [
    RetrieveWithDecayTool,
    RetrieveWithBudgetTool,
    ConsolidateWithCompressionTool,
]


def get_tool_definitions():
    """Get MCP tool definitions for registration."""
    return [
        {
            "name": RetrieveWithDecayTool.name,
            "description": RetrieveWithDecayTool.description,
            "inputSchema": RetrieveWithDecayTool.input_schema,
        },
        {
            "name": RetrieveWithBudgetTool.name,
            "description": RetrieveWithBudgetTool.description,
            "inputSchema": RetrieveWithBudgetTool.input_schema,
        },
        {
            "name": ConsolidateWithCompressionTool.name,
            "description": ConsolidateWithCompressionTool.description,
            "inputSchema": ConsolidateWithCompressionTool.input_schema,
        },
    ]
