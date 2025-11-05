"""
Compression module for Memory MCP v1.1.

Three core compression strategies for 5-10x context window expansion:

1. **Temporal Decay Compression**: Compress memories based on age
   - < 7d: 100% fidelity | 7-30d: 50% compression
   - 30-90d: 80% compression | >90d: 95% compression
   - Mimics human memory decay

2. **Importance-Weighted Budgeting**: Smart memory selection within token budget
   - Scores: usefulness (40%), recency (30%), frequency (20%), domain (10%)
   - Returns highest-value memories within token constraint
   - No schema changes (uses existing fields)

3. **Consolidation Compression**: Generate executive summaries
   - During consolidation: create full pattern + ultra-short summary
   - ~8-12x compression (200 tokens → 20 tokens)
   - Enables massive context savings in retrieval

All features are optional (default disabled) with graceful degradation.
"""

from .base import (
    BaseCompressor,
    CompressionMetricsCollector,
    CompressionValidator,
    ConsolidationCompressor,
    ImportanceWeightedBudgeter,
    TemporalDecayCompressor,
)
from .manager import CompressionManager
from .models import (
    CompressionConfig,
    CompressionLevel,
    CompressionMetrics,
    CompressedMemory,
    ConsolidationCompressionConfig,
    ImportanceWeightedBudgetConfig,
    TemporalDecayConfig,
)
from .schema import CompressionSchema
from .tools import (
    BudgetedRetrievalResult,
    CompressedMemoryResult,
    ConsolidateWithCompressionTool,
    ConsolidationCompressionResult,
    RetrieveWithBudgetTool,
    RetrieveWithDecayTool,
    get_tool_definitions,
)

__all__ = [
    # Configuration models
    "CompressionConfig",
    "TemporalDecayConfig",
    "ImportanceWeightedBudgetConfig",
    "ConsolidationCompressionConfig",
    # Core data models
    "CompressedMemory",
    "CompressionMetrics",
    "CompressionLevel",
    # API result models
    "CompressedMemoryResult",
    "BudgetedRetrievalResult",
    "ConsolidationCompressionResult",
    # Base classes
    "BaseCompressor",
    "TemporalDecayCompressor",
    "ImportanceWeightedBudgeter",
    "ConsolidationCompressor",
    # Manager
    "CompressionManager",
    # Utilities
    "CompressionValidator",
    "CompressionMetricsCollector",
    # Schema validation
    "CompressionSchema",
    # MCP tools
    "RetrieveWithDecayTool",
    "RetrieveWithBudgetTool",
    "ConsolidateWithCompressionTool",
    # Tool registration
    "get_tool_definitions",
]

__version__ = "1.1.0"
__features__ = [
    "temporal_decay",
    "importance_budgeting",
    "consolidation_compression",
]
