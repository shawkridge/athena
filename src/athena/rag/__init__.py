"""Advanced RAG (Retrieval-Augmented Generation) components."""

from .hyde import HyDEConfig, HyDERetriever
from .llm_client import ClaudeLLMClient, LLMClient, OllamaLLMClient, create_llm_client
from .manager import RAGConfig, RAGManager, RAGStrategy
from .prompt_caching import (
    CacheBlock,
    CacheBlockType,
    CacheMetrics,
    CacheStatus,
    PromptCacheManager,
)
from .query_expansion import (
    QueryExpander,
    QueryExpansionConfig,
    QueryExpansions,
    batch_expand,
)
from .query_transform import QueryTransformConfig, QueryTransformer, batch_transform
from .reflective import ReflectiveRAG, ReflectiveRAGConfig, get_iteration_metrics
from .reranker import LLMReranker, RerankerConfig, analyze_reranking_impact
from .uncertainty import (
    AbstentionReason,
    ConfidenceLevel,
    UncertaintyCalibrator,
    UncertaintyConfig,
    UncertaintyMetrics,
)

__all__ = [
    "LLMClient",
    "ClaudeLLMClient",
    "OllamaLLMClient",
    "create_llm_client",
    "HyDERetriever",
    "HyDEConfig",
    "LLMReranker",
    "RerankerConfig",
    "analyze_reranking_impact",
    "QueryExpander",
    "QueryExpansionConfig",
    "QueryExpansions",
    "batch_expand",
    "QueryTransformer",
    "QueryTransformConfig",
    "batch_transform",
    "ReflectiveRAG",
    "ReflectiveRAGConfig",
    "get_iteration_metrics",
    "RAGManager",
    "RAGConfig",
    "RAGStrategy",
    "UncertaintyCalibrator",
    "UncertaintyConfig",
    "UncertaintyMetrics",
    "ConfidenceLevel",
    "AbstentionReason",
    "PromptCacheManager",
    "CacheBlock",
    "CacheBlockType",
    "CacheMetrics",
    "CacheStatus",
]
