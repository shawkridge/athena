"""Performance metrics for local LLM models (embedding + reasoning)."""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingMetrics:
    """Metrics for embedding operations."""

    timestamp: str
    latency_ms: float
    dimension: int
    tokens_processed: int
    status: str  # "success" or "error"
    error_msg: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ReasoningMetrics:
    """Metrics for reasoning operations."""

    timestamp: str
    latency_ms: float
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    temperature: float
    status: str  # "success" or "error"
    error_msg: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CompressionMetrics:
    """Metrics for prompt compression operations."""

    timestamp: str
    latency_ms: float
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    status: str  # "success" or "error"
    error_msg: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class ModelPerformanceMonitor:
    """Monitor and track local LLM model performance."""

    def __init__(self, max_history: int = 1000):
        """Initialize monitor.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.embedding_metrics: List[EmbeddingMetrics] = []
        self.reasoning_metrics: List[ReasoningMetrics] = []
        self.compression_metrics: List[CompressionMetrics] = []

    def record_embedding(
        self,
        latency_ms: float,
        dimension: int,
        tokens_processed: int,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> EmbeddingMetrics:
        """Record embedding operation metrics.

        Args:
            latency_ms: Operation latency in milliseconds
            dimension: Output embedding dimension (768 for nomic-embed)
            tokens_processed: Number of tokens processed
            status: Operation status (success/error)
            error_msg: Error message if failed

        Returns:
            EmbeddingMetrics object
        """
        metric = EmbeddingMetrics(
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms,
            dimension=dimension,
            tokens_processed=tokens_processed,
            status=status,
            error_msg=error_msg,
        )

        self.embedding_metrics.append(metric)

        # Trim history
        if len(self.embedding_metrics) > self.max_history:
            self.embedding_metrics = self.embedding_metrics[-self.max_history :]

        # Log
        if status == "success":
            logger.debug(
                f"Embedding: {tokens_processed} tokens → {dimension}D in {latency_ms:.1f}ms"
            )
        else:
            logger.error(f"Embedding failed: {error_msg}")

        return metric

    def record_reasoning(
        self,
        latency_ms: float,
        prompt_tokens: int,
        output_tokens: int,
        temperature: float,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> ReasoningMetrics:
        """Record reasoning operation metrics.

        Args:
            latency_ms: Operation latency in milliseconds
            prompt_tokens: Number of prompt tokens
            output_tokens: Number of generated tokens
            temperature: Sampling temperature used
            status: Operation status (success/error)
            error_msg: Error message if failed

        Returns:
            ReasoningMetrics object
        """
        total_tokens = prompt_tokens + output_tokens

        metric = ReasoningMetrics(
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            temperature=temperature,
            status=status,
            error_msg=error_msg,
        )

        self.reasoning_metrics.append(metric)

        # Trim history
        if len(self.reasoning_metrics) > self.max_history:
            self.reasoning_metrics = self.reasoning_metrics[-self.max_history :]

        # Log
        if status == "success":
            tokens_per_sec = (output_tokens / latency_ms * 1000) if latency_ms > 0 else 0
            logger.debug(
                f"Reasoning: {output_tokens} tokens in {latency_ms:.1f}ms ({tokens_per_sec:.1f} tok/s)"
            )
        else:
            logger.error(f"Reasoning failed: {error_msg}")

        return metric

    def record_compression(
        self,
        latency_ms: float,
        original_tokens: int,
        compressed_tokens: int,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> CompressionMetrics:
        """Record prompt compression metrics.

        Args:
            latency_ms: Operation latency in milliseconds
            original_tokens: Original prompt token count
            compressed_tokens: Compressed prompt token count
            status: Operation status (success/error)
            error_msg: Error message if failed

        Returns:
            CompressionMetrics object
        """
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        metric = CompressionMetrics(
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            status=status,
            error_msg=error_msg,
        )

        self.compression_metrics.append(metric)

        # Trim history
        if len(self.compression_metrics) > self.max_history:
            self.compression_metrics = self.compression_metrics[-self.max_history :]

        # Log
        if status == "success":
            reduction_pct = (1 - compression_ratio) * 100
            logger.debug(
                f"Compression: {original_tokens} → {compressed_tokens} tokens "
                f"({reduction_pct:.1f}% reduction) in {latency_ms:.1f}ms"
            )
        else:
            logger.warning(f"Compression failed: {error_msg}")

        return metric

    def get_embedding_stats(self) -> Dict:
        """Get aggregate statistics for embedding operations.

        Returns:
            Dictionary with min/max/avg latency, success rate, etc.
        """
        if not self.embedding_metrics:
            return {}

        successful = [m for m in self.embedding_metrics if m.status == "success"]
        failed = len(self.embedding_metrics) - len(successful)

        if not successful:
            return {
                "total_operations": len(self.embedding_metrics),
                "successful": 0,
                "failed": failed,
                "success_rate": 0.0,
            }

        latencies = [m.latency_ms for m in successful]

        return {
            "total_operations": len(self.embedding_metrics),
            "successful": len(successful),
            "failed": failed,
            "success_rate": len(successful) / len(self.embedding_metrics),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "total_tokens_processed": sum(m.tokens_processed for m in successful),
            "avg_dimension": sum(m.dimension for m in successful) / len(successful),
        }

    def get_reasoning_stats(self) -> Dict:
        """Get aggregate statistics for reasoning operations.

        Returns:
            Dictionary with latency, throughput, token stats
        """
        if not self.reasoning_metrics:
            return {}

        successful = [m for m in self.reasoning_metrics if m.status == "success"]
        failed = len(self.reasoning_metrics) - len(successful)

        if not successful:
            return {
                "total_operations": len(self.reasoning_metrics),
                "successful": 0,
                "failed": failed,
                "success_rate": 0.0,
            }

        latencies = [m.latency_ms for m in successful]
        output_tokens_list = [m.output_tokens for m in successful]
        tokens_per_sec_list = [
            (m.output_tokens / m.latency_ms * 1000) if m.latency_ms > 0 else 0 for m in successful
        ]

        return {
            "total_operations": len(self.reasoning_metrics),
            "successful": len(successful),
            "failed": failed,
            "success_rate": len(successful) / len(self.reasoning_metrics),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "total_prompt_tokens": sum(m.prompt_tokens for m in successful),
            "total_output_tokens": sum(m.output_tokens for m in successful),
            "avg_output_tokens": sum(output_tokens_list) / len(output_tokens_list),
            "avg_tokens_per_sec": sum(tokens_per_sec_list) / len(tokens_per_sec_list),
        }

    def get_compression_stats(self) -> Dict:
        """Get aggregate statistics for compression operations.

        Returns:
            Dictionary with compression ratios and token savings
        """
        if not self.compression_metrics:
            return {}

        successful = [m for m in self.compression_metrics if m.status == "success"]
        failed = len(self.compression_metrics) - len(successful)

        if not successful:
            return {
                "total_operations": len(self.compression_metrics),
                "successful": 0,
                "failed": failed,
                "success_rate": 0.0,
            }

        compression_ratios = [m.compression_ratio for m in successful]
        latencies = [m.latency_ms for m in successful]

        return {
            "total_operations": len(self.compression_metrics),
            "successful": len(successful),
            "failed": failed,
            "success_rate": len(successful) / len(self.compression_metrics),
            "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios),
            "min_compression_ratio": min(compression_ratios),
            "max_compression_ratio": max(compression_ratios),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "total_tokens_saved": sum(m.original_tokens - m.compressed_tokens for m in successful),
            "avg_tokens_saved_per_operation": (
                sum(m.original_tokens - m.compressed_tokens for m in successful) / len(successful)
            ),
        }

    def get_all_stats(self) -> Dict:
        """Get all performance statistics.

        Returns:
            Dictionary with embedding, reasoning, and compression stats
        """
        return {
            "embedding": self.get_embedding_stats(),
            "reasoning": self.get_reasoning_stats(),
            "compression": self.get_compression_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def clear_history(self) -> None:
        """Clear all metrics history."""
        self.embedding_metrics.clear()
        self.reasoning_metrics.clear()
        self.compression_metrics.clear()
        logger.info("Cleared model performance metrics history")


# Global monitor instance
_monitor: Optional[ModelPerformanceMonitor] = None


def get_monitor() -> ModelPerformanceMonitor:
    """Get or create global monitor instance.

    Returns:
        ModelPerformanceMonitor instance
    """
    global _monitor

    if _monitor is None:
        _monitor = ModelPerformanceMonitor()
        logger.debug("Initialized ModelPerformanceMonitor")

    return _monitor
