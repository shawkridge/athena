"""Cost tracking and optimization recommendations for memory systems.

Addresses research finding: "Cost efficiency is critical" (Rank theme 2,
Credibility high from 2024-2025 LLM Memory Research)

Tracks:
- Embedding API costs (Claude, Ollama)
- Storage costs (database size, vector store size)
- Query costs (search operations, reranking)
- Memory operation costs (consolidation, garbage collection)

Provides:
- Cost optimization recommendations
- Prompt caching potential savings (90% reduction mentioned in research)
- Quantization savings estimates
- Budget alerts and thresholds
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CostType(str, Enum):
    """Types of memory system costs."""

    EMBEDDING = "embedding"  # Embedding generation
    VECTOR_SEARCH = "vector_search"  # Vector similarity search
    LEXICAL_SEARCH = "lexical_search"  # BM25 keyword search
    RERANKING = "reranking"  # LLM-based reranking
    CONSOLIDATION = "consolidation"  # Pattern extraction & consolidation
    STORAGE = "storage"  # Database/vector store storage
    RETRIEVAL = "retrieval"  # General retrieval operation
    API_CALL = "api_call"  # API call to Claude/Ollama


class OptimizationStrategy(str, Enum):
    """Strategies for cost optimization."""

    PROMPT_CACHING = "prompt_caching"  # Cache frequently reused context (90% savings)
    QUANTIZATION = "quantization"  # 4-bit/8-bit quantization for embeddings
    BATCH_PROCESSING = "batch_processing"  # Batch multiple operations
    LAZY_LOADING = "lazy_loading"  # Load memories only when needed
    CONSOLIDATION = "consolidation"  # Consolidate episodic→semantic (reduces vector count)
    LOCAL_EMBEDDINGS = "local_embeddings"  # Use local Ollama instead of API
    CACHING_LAYER = "caching_layer"  # Cache search results
    PRUNING = "pruning"  # Remove low-value memories


@dataclass
class CostEntry:
    """Single cost transaction."""

    cost_type: CostType
    amount: float  # Cost in dollars (or relative units)
    timestamp: datetime = field(default_factory=datetime.now)
    operation_id: Optional[str] = None  # ID of operation that incurred cost
    metadata: dict = field(default_factory=dict)  # Additional context

    def __str__(self) -> str:
        """Human-readable cost entry."""
        return f"{self.cost_type.value}: ${self.amount:.6f}"


@dataclass
class CostMetrics:
    """Aggregate cost metrics."""

    period_name: str  # e.g., "today", "this_week", "this_month"
    total_cost: float = 0.0
    cost_by_type: dict[str, float] = field(default_factory=dict)

    # Volume metrics
    embedding_count: int = 0
    search_count: int = 0
    reranking_count: int = 0
    api_call_count: int = 0

    # Efficiency metrics
    cost_per_embedding: float = 0.0
    cost_per_search: float = 0.0
    cost_per_api_call: float = 0.0

    def __str__(self) -> str:
        """Human-readable cost summary."""
        lines = [
            f"=== Cost Summary: {self.period_name} ===",
            f"Total Cost: ${self.total_cost:.2f}",
            f"Embeddings: {self.embedding_count} @ ${self.cost_per_embedding:.6f} each",
            f"Searches: {self.search_count} @ ${self.cost_per_search:.6f} each",
            f"API Calls: {self.api_call_count} @ ${self.cost_per_api_call:.6f} each",
        ]

        if self.cost_by_type:
            lines.append("\nCost by Type:")
            for cost_type, amount in sorted(
                self.cost_by_type.items(), key=lambda x: x[1], reverse=True
            ):
                pct = (amount / self.total_cost * 100) if self.total_cost > 0 else 0
                lines.append(f"  {cost_type}: ${amount:.2f} ({pct:.1f}%)")

        return "\n".join(lines)


@dataclass
class OptimizationRecommendation:
    """Recommendation for cost optimization."""

    strategy: OptimizationStrategy
    title: str
    description: str
    potential_savings: float  # Estimated savings as percentage (0.0-1.0)
    difficulty: str  # "easy", "medium", "hard"
    estimated_implementation_time_minutes: int

    # Cost impact
    one_time_cost: float = 0.0  # One-time setup cost
    monthly_savings: float = 0.0  # Estimated monthly savings
    roi_months: Optional[float] = None  # Months to recoup investment

    def __str__(self) -> str:
        """Human-readable recommendation."""
        lines = [
            f"Strategy: {self.strategy.value}",
            f"Title: {self.title}",
            f"Description: {self.description}",
            f"Potential Savings: {self.potential_savings * 100:.0f}%",
            f"Difficulty: {self.difficulty}",
            f"Implementation Time: {self.estimated_implementation_time_minutes} min",
        ]

        if self.monthly_savings > 0:
            lines.append(f"Monthly Savings: ${self.monthly_savings:.2f}")
            if self.roi_months:
                lines.append(f"ROI: {self.roi_months:.1f} months")

        return "\n".join(lines)


class CostTracker:
    """Tracks memory system costs and provides optimization recommendations."""

    def __init__(self):
        """Initialize cost tracker."""
        self.entries: list[CostEntry] = []
        self.budget_threshold: float = 100.0  # Monthly budget in dollars

    def record_cost(
        self,
        cost_type: CostType,
        amount: float,
        operation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """Record cost transaction.

        Args:
            cost_type: Type of cost
            amount: Cost amount in dollars
            operation_id: Optional operation ID
            metadata: Optional metadata about cost
        """
        entry = CostEntry(
            cost_type=cost_type,
            amount=amount,
            operation_id=operation_id,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        logger.debug(f"Recorded cost: {entry}")

    def get_metrics(self, period_name: str = "all_time") -> CostMetrics:
        """Get cost metrics.

        Args:
            period_name: Name of time period

        Returns:
            Aggregate cost metrics
        """
        metrics = CostMetrics(period_name=period_name)

        # Sum costs by type
        cost_by_type: dict[str, float] = {}
        volume_by_type: dict[str, int] = {}

        for entry in self.entries:
            cost_type = entry.cost_type.value
            cost_by_type[cost_type] = cost_by_type.get(cost_type, 0) + entry.amount
            volume_by_type[cost_type] = volume_by_type.get(cost_type, 0) + 1

        # Compute metrics
        metrics.total_cost = sum(e.amount for e in self.entries)
        metrics.cost_by_type = cost_by_type

        # Volume metrics
        metrics.embedding_count = volume_by_type.get(CostType.EMBEDDING.value, 0)
        metrics.search_count = volume_by_type.get(CostType.VECTOR_SEARCH.value, 0)
        metrics.reranking_count = volume_by_type.get(CostType.RERANKING.value, 0)
        metrics.api_call_count = volume_by_type.get(CostType.API_CALL.value, 0)

        # Per-unit costs
        if metrics.embedding_count > 0:
            metrics.cost_per_embedding = (
                cost_by_type.get(CostType.EMBEDDING.value, 0) / metrics.embedding_count
            )
        if metrics.search_count > 0:
            metrics.cost_per_search = (
                cost_by_type.get(CostType.VECTOR_SEARCH.value, 0) / metrics.search_count
            )
        if metrics.api_call_count > 0:
            metrics.cost_per_api_call = (
                cost_by_type.get(CostType.API_CALL.value, 0) / metrics.api_call_count
            )

        return metrics

    def get_recommendations(self) -> list[OptimizationRecommendation]:
        """Get optimization recommendations based on current costs.

        Returns:
            Sorted list of recommendations (highest savings first)
        """
        recommendations = []
        metrics = self.get_metrics()

        # Recommendation 1: Prompt Caching (90% savings mentioned in research)
        if metrics.api_call_count > 0:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.PROMPT_CACHING,
                    title="Enable Prompt Caching for Anthropic API",
                    description=(
                        "Cache frequently reused context blocks between API calls. "
                        "Research shows 90% cost reduction and 85% latency reduction. "
                        "GA Dec 2024 on Anthropic API."
                    ),
                    potential_savings=0.90,
                    difficulty="easy",
                    estimated_implementation_time_minutes=30,
                    monthly_savings=metrics.cost_by_type.get(CostType.API_CALL.value, 0) * 0.9,
                )
            )

        # Recommendation 2: Local Embeddings
        if metrics.embedding_count > 50:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.LOCAL_EMBEDDINGS,
                    title="Switch to Local Ollama Embeddings",
                    description=(
                        "Replace cloud embedding APIs (Claude, OpenAI) with local "
                        "Ollama nomic-embed-text. Zero API costs after setup."
                    ),
                    potential_savings=1.0,  # 100% of embedding costs
                    difficulty="easy",
                    estimated_implementation_time_minutes=20,
                    monthly_savings=metrics.cost_by_type.get(CostType.EMBEDDING.value, 0),
                )
            )

        # Recommendation 3: Consolidation
        if metrics.embedding_count > 100:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.CONSOLIDATION,
                    title="Increase Consolidation Frequency",
                    description=(
                        "Consolidate episodic→semantic more frequently to reduce "
                        "vector count by 70-85%. This cuts storage and search costs."
                    ),
                    potential_savings=0.75,
                    difficulty="medium",
                    estimated_implementation_time_minutes=15,
                    monthly_savings=(
                        metrics.cost_by_type.get(CostType.STORAGE.value, 0) * 0.75
                        + metrics.cost_by_type.get(CostType.VECTOR_SEARCH.value, 0) * 0.5
                    ),
                )
            )

        # Recommendation 4: Batch Processing
        if metrics.search_count > 20:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.BATCH_PROCESSING,
                    title="Batch Search Operations",
                    description=(
                        "Group multiple queries together for batch processing. "
                        "Reduces overhead and connection costs."
                    ),
                    potential_savings=0.15,
                    difficulty="easy",
                    estimated_implementation_time_minutes=30,
                    monthly_savings=metrics.cost_by_type.get(CostType.VECTOR_SEARCH.value, 0)
                    * 0.15,
                )
            )

        # Recommendation 5: Reranking Optimization
        if metrics.reranking_count > 10:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.LAZY_LOADING,
                    title="Make Reranking Optional (Lazy)",
                    description=(
                        "Only perform expensive LLM reranking for high-stakes queries. "
                        "Skip for low-confidence searches where ranking is unlikely."
                    ),
                    potential_savings=0.50,
                    difficulty="medium",
                    estimated_implementation_time_minutes=45,
                    monthly_savings=metrics.cost_by_type.get(CostType.RERANKING.value, 0) * 0.5,
                )
            )

        # Recommendation 6: Memory Pruning
        if metrics.total_cost > 50:
            recommendations.append(
                OptimizationRecommendation(
                    strategy=OptimizationStrategy.PRUNING,
                    title="Prune Low-Value Memories",
                    description=(
                        "Remove memories with low usefulness scores (<0.3) "
                        "to reduce storage and search overhead."
                    ),
                    potential_savings=0.20,
                    difficulty="easy",
                    estimated_implementation_time_minutes=15,
                    monthly_savings=metrics.cost_by_type.get(CostType.STORAGE.value, 0) * 0.2,
                )
            )

        # Sort by potential monthly savings
        recommendations.sort(key=lambda r: r.monthly_savings, reverse=True)

        return recommendations

    def get_budget_status(self) -> dict:
        """Get budget status and alerts.

        Returns:
            Dictionary with budget status, percentage used, alerts
        """
        metrics = self.get_metrics()
        usage_pct = (metrics.total_cost / self.budget_threshold) * 100

        status = "OK"
        alert = None

        if usage_pct >= 90:
            status = "CRITICAL"
            alert = f"Budget critical: {usage_pct:.0f}% used"
        elif usage_pct >= 75:
            status = "WARNING"
            alert = f"Budget warning: {usage_pct:.0f}% used"
        elif usage_pct >= 50:
            status = "CAUTION"
            alert = f"Budget halfway: {usage_pct:.0f}% used"

        return {
            "budget_threshold": self.budget_threshold,
            "current_cost": metrics.total_cost,
            "usage_percentage": usage_pct,
            "status": status,
            "alert": alert,
            "remaining_budget": self.budget_threshold - metrics.total_cost,
        }

    def summary_report(self) -> str:
        """Generate comprehensive cost summary report.

        Returns:
            Human-readable summary report
        """
        metrics = self.get_metrics()
        budget = self.get_budget_status()
        recommendations = self.get_recommendations()

        lines = [
            "=" * 60,
            "MEMORY SYSTEM COST TRACKING REPORT",
            "=" * 60,
            "",
            str(metrics),
            "",
            "BUDGET STATUS",
            "-" * 60,
            f"Threshold: ${budget['budget_threshold']:.2f}",
            f"Current: ${budget['current_cost']:.2f}",
            f"Usage: {budget['usage_percentage']:.1f}%",
            f"Status: {budget['status']}",
            f"Remaining: ${budget['remaining_budget']:.2f}",
        ]

        if budget["alert"]:
            lines.append(f"Alert: ⚠️  {budget['alert']}")

        if recommendations:
            lines.append("")
            lines.append("TOP OPTIMIZATION RECOMMENDATIONS")
            lines.append("-" * 60)
            for i, rec in enumerate(recommendations[:3], 1):
                lines.append(f"{i}. {rec.title}")
                lines.append(f"   Savings: {rec.potential_savings * 100:.0f}%")
                if rec.monthly_savings > 0:
                    lines.append(f"   Monthly Savings: ${rec.monthly_savings:.2f}")
                lines.append("")

        return "\n".join(lines)
