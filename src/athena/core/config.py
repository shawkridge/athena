"""Centralized configuration for Athena Memory System."""

import os
from pathlib import Path

# ============================================================================
# Database Configuration
# ============================================================================

# Default database path
DEFAULT_DB_PATH = Path.home() / ".athena" / "memory.db"

# Database path (can be overridden via environment variable)
ATHENA_DB_PATH = os.environ.get("ATHENA_DB_PATH", str(DEFAULT_DB_PATH))


# ============================================================================
# LLM Configuration
# ============================================================================

# LLM Provider: "ollama", "llamacpp", or "claude"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "llamacpp")
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "llamacpp")

# Ollama Configuration (Legacy)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "qwen3-vl:2b-instruct-q4_K_M")
# Use 768D embedding model (nomic-embed-text) for consistency with database schema
OLLAMA_EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# llama.cpp Configuration (Recommended for CPU)
LLAMACPP_MODELS_DIR = Path(os.environ.get("LLAMACPP_MODELS_DIR", str(Path.home() / ".athena" / "models")))
LLAMACPP_EMBEDDING_MODEL_PATH = Path(os.environ.get(
    "LLAMACPP_EMBEDDING_MODEL_PATH",
    str(LLAMACPP_MODELS_DIR / "nomic-embed-text-v2-moe.Q6_K.gguf")
))
LLAMACPP_LLM_MODEL_PATH = Path(os.environ.get(
    "LLAMACPP_LLM_MODEL_PATH",
    str(LLAMACPP_MODELS_DIR / "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf")
))
LLAMACPP_EMBEDDING_DIM = int(os.environ.get("LLAMACPP_EMBEDDING_DIM", "768"))
LLAMACPP_N_THREADS = int(os.environ.get("LLAMACPP_N_THREADS", "0"))  # 0 = auto-detect

# Claude API Configuration
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", None)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4")
CLAUDE_EMBEDDING_DIM = int(os.environ.get("CLAUDE_EMBEDDING_DIM", "768"))  # Standard embedding dimension


# ============================================================================
# Memory System Configuration
# ============================================================================

# Working Memory Capacity (Baddeley's 7±2 limit)
WORKING_MEMORY_CAPACITY = int(os.environ.get("WORKING_MEMORY_CAPACITY", "7"))

# Consolidation Strategy: "balanced", "speed", "quality", "minimal"
CONSOLIDATION_STRATEGY = os.environ.get("CONSOLIDATION_STRATEGY", "balanced")

# Enable LLM-powered features
ENABLE_LLM_FEATURES = os.environ.get("ENABLE_LLM_FEATURES", "true").lower() == "true"


# ============================================================================
# Vector Database Configuration
# ============================================================================

# Qdrant Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "semantic_memories")
QDRANT_EMBEDDING_DIM = int(os.environ.get("QDRANT_EMBEDDING_DIM", "768"))


# ============================================================================
# RAG Configuration
# ============================================================================

# RAG retrieval parameters
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
RAG_ENABLE_HYDE = os.environ.get("RAG_ENABLE_HYDE", "true").lower() == "true"
RAG_ENABLE_RERANKING = os.environ.get("RAG_ENABLE_RERANKING", "true").lower() == "true"


# ============================================================================
# Graph and Community Detection Configuration
# ============================================================================

# Community detection (GraphRAG) parameters
GRAPH_COMMUNITY_LIMIT = int(os.environ.get("GRAPH_COMMUNITY_LIMIT", "10"))
GRAPH_MIN_COMMUNITY_SIZE = int(os.environ.get("GRAPH_MIN_COMMUNITY_SIZE", "2"))

# Entity scoring weights
ENTITY_BASE_SCORE = float(os.environ.get("ENTITY_BASE_SCORE", "0.5"))
RELATION_BASE_SCORE = float(os.environ.get("RELATION_BASE_SCORE", "0.4"))

# Community-based retrieval weights
COMMUNITY_SEMANTIC_WEIGHT = float(os.environ.get("COMMUNITY_SEMANTIC_WEIGHT", "0.6"))
COMMUNITY_TEMPORAL_WEIGHT = float(os.environ.get("COMMUNITY_TEMPORAL_WEIGHT", "0.2"))
COMMUNITY_IMPORTANCE_WEIGHT = float(os.environ.get("COMMUNITY_IMPORTANCE_WEIGHT", "0.2"))


# ============================================================================
# RAG Reranking Configuration
# ============================================================================

# Reranking weights for multi-factor scoring
RERANK_SEMANTIC_WEIGHT = float(os.environ.get("RERANK_SEMANTIC_WEIGHT", "0.6"))
RERANK_TEMPORAL_WEIGHT = float(os.environ.get("RERANK_TEMPORAL_WEIGHT", "0.2"))
RERANK_IMPORTANCE_WEIGHT = float(os.environ.get("RERANK_IMPORTANCE_WEIGHT", "0.2"))
RERANK_CONFIDENCE_THRESHOLD = float(os.environ.get("RERANK_CONFIDENCE_THRESHOLD", "0.5"))


# ============================================================================
# Query and Search Configuration
# ============================================================================

# Query result limits
DEFAULT_QUERY_LIMIT = int(os.environ.get("DEFAULT_QUERY_LIMIT", "10"))
MAX_QUERY_RESULTS = int(os.environ.get("MAX_QUERY_RESULTS", "100"))

# Search parameters
MIN_SIMILARITY_THRESHOLD = float(os.environ.get("MIN_SIMILARITY_THRESHOLD", "0.3"))
DEFAULT_SIMILARITY_THRESHOLD = float(os.environ.get("DEFAULT_SIMILARITY_THRESHOLD", "0.5"))


# ============================================================================
# Consolidation and Learning Configuration
# ============================================================================

# Consolidation batch sizes
CONSOLIDATION_BATCH_SIZE = int(os.environ.get("CONSOLIDATION_BATCH_SIZE", "100"))
CONSOLIDATION_MIN_EVENTS = int(os.environ.get("CONSOLIDATION_MIN_EVENTS", "50"))

# Pattern extraction parameters
PATTERN_MIN_CONFIDENCE = float(os.environ.get("PATTERN_MIN_CONFIDENCE", "0.5"))
PATTERN_MIN_FREQUENCY = int(os.environ.get("PATTERN_MIN_FREQUENCY", "2"))
PATTERN_UNCERTAINTY_THRESHOLD = float(os.environ.get("PATTERN_UNCERTAINTY_THRESHOLD", "0.5"))


# ============================================================================
# Performance and Optimization Configuration
# ============================================================================

# Batch operation parameters
BATCH_INSERT_SIZE = int(os.environ.get("BATCH_INSERT_SIZE", "100"))
BATCH_UPDATE_SIZE = int(os.environ.get("BATCH_UPDATE_SIZE", "100"))

# Caching parameters
CACHE_SIZE = int(os.environ.get("CACHE_SIZE", "1000"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

# Query optimization
ENABLE_QUERY_CACHING = os.environ.get("ENABLE_QUERY_CACHING", "true").lower() == "true"
ENABLE_VECTOR_CACHING = os.environ.get("ENABLE_VECTOR_CACHING", "true").lower() == "true"


# ============================================================================
# Logging Configuration
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DEBUG = os.environ.get("DEBUG", "0") == "1"
