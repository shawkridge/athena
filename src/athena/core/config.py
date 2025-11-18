"""Centralized configuration for Athena Memory System."""

import os

# ============================================================================
# Database Configuration
# ============================================================================
# System uses PostgreSQL exclusively with pgvector for all operations.
# SQLite and Qdrant backends have been removed.


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

# llama.cpp Configuration (HTTP Server)
# Embedding server: nomic-embed-text-v1.5 (768D embeddings)
LLAMACPP_EMBEDDINGS_URL = os.environ.get("LLAMACPP_EMBEDDINGS_URL", "http://localhost:8001")
# Reasoning server: Qwen2.5-7B-Instruct (pattern extraction, consolidation)
LLAMACPP_REASONING_URL = os.environ.get("LLAMACPP_REASONING_URL", "http://localhost:8002")
LLAMACPP_EMBEDDING_DIM = int(os.environ.get("LLAMACPP_EMBEDDING_DIM", "768"))
LLAMACPP_N_THREADS = int(os.environ.get("LLAMACPP_N_THREADS", "8"))  # Optimal: (CPU cores × 1.5)

# Claude API Configuration
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", None)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4")
CLAUDE_EMBEDDING_DIM = int(
    os.environ.get("CLAUDE_EMBEDDING_DIM", "768")
)  # Standard embedding dimension


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
# RAG Configuration
# ============================================================================

# RAG retrieval parameters
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
RAG_ENABLE_HYDE = os.environ.get("RAG_ENABLE_HYDE", "true").lower() == "true"
RAG_ENABLE_RERANKING = os.environ.get("RAG_ENABLE_RERANKING", "true").lower() == "true"

# Query expansion parameters
RAG_QUERY_EXPANSION_ENABLED = (
    os.environ.get("RAG_QUERY_EXPANSION_ENABLED", "true").lower() == "true"
)
RAG_QUERY_EXPANSION_VARIANTS = int(os.environ.get("RAG_QUERY_EXPANSION_VARIANTS", "4"))
RAG_QUERY_EXPANSION_CACHE = os.environ.get("RAG_QUERY_EXPANSION_CACHE", "true").lower() == "true"
RAG_QUERY_EXPANSION_CACHE_SIZE = int(os.environ.get("RAG_QUERY_EXPANSION_CACHE_SIZE", "1000"))


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
# TOON Serialization Configuration
# ============================================================================

# Enable TOON format for token-efficient LLM input
ENABLE_TOON_FORMAT = os.environ.get("ENABLE_TOON_FORMAT", "false").lower() == "true"

# Use TOON for specific data types
TOON_USE_EPISODIC_EVENTS = os.environ.get("TOON_USE_EPISODIC_EVENTS", "true").lower() == "true"
TOON_USE_KNOWLEDGE_GRAPH = os.environ.get("TOON_USE_KNOWLEDGE_GRAPH", "true").lower() == "true"
TOON_USE_PROCEDURAL = os.environ.get("TOON_USE_PROCEDURAL", "true").lower() == "true"
TOON_USE_SEMANTIC_SEARCH = os.environ.get("TOON_USE_SEMANTIC_SEARCH", "true").lower() == "true"
TOON_USE_METRICS = os.environ.get("TOON_USE_METRICS", "true").lower() == "true"

# TOON encoding timeout (seconds)
TOON_ENCODING_TIMEOUT = int(os.environ.get("TOON_ENCODING_TIMEOUT", "10"))

# Fallback to JSON if TOON fails
TOON_FALLBACK_TO_JSON = os.environ.get("TOON_FALLBACK_TO_JSON", "true").lower() == "true"

# Minimum token savings threshold for TOON (in percent)
TOON_MIN_TOKEN_SAVINGS = float(os.environ.get("TOON_MIN_TOKEN_SAVINGS", "15.0"))


# ============================================================================
# Prompt Optimization Configuration (Compression & Caching)
# ============================================================================

# Enable prompt compression (LLMLingua-2)
COMPRESSION_ENABLED = os.environ.get("COMPRESSION_ENABLED", "true").lower() == "true"

# Target compression ratio (0.35 = 35% of original tokens)
COMPRESSION_RATIO_TARGET = float(os.environ.get("COMPRESSION_RATIO_TARGET", "0.35"))

# Minimum compression ratio to accept (discard if below this)
COMPRESSION_MIN_RATIO = float(os.environ.get("COMPRESSION_MIN_RATIO", "0.60"))

# Minimum semantic preservation score (0-1)
COMPRESSION_MIN_PRESERVATION = float(os.environ.get("COMPRESSION_MIN_PRESERVATION", "0.95"))

# Compression latency budget (milliseconds)
COMPRESSION_LATENCY_BUDGET_MS = int(os.environ.get("COMPRESSION_LATENCY_BUDGET_MS", "300"))

# Enable Claude prompt caching
PROMPT_CACHING_ENABLED = os.environ.get("PROMPT_CACHING_ENABLED", "true").lower() == "true"

# Cache TTL (seconds, default 5 minutes)
PROMPT_CACHE_TTL_SECONDS = int(os.environ.get("PROMPT_CACHE_TTL_SECONDS", "300"))

# Maximum cache size (number of cached prompts)
PROMPT_CACHE_MAX_SIZE = int(os.environ.get("PROMPT_CACHE_MAX_SIZE", "100"))

# Cache block types to enable
PROMPT_CACHE_BLOCK_TYPES = os.environ.get(
    "PROMPT_CACHE_BLOCK_TYPES", "system_instructions,context_block,retrieved_memories"
).split(",")

# Cost per 1K input tokens (USD) for Claude
CLAUDE_COST_PER_1K_INPUT = float(os.environ.get("CLAUDE_COST_PER_1K_INPUT", "0.003"))

# Cost per 1K cached input tokens (USD, 90% discount on base cost)
CLAUDE_COST_PER_1K_CACHED_INPUT = float(os.environ.get("CLAUDE_COST_PER_1K_CACHED_INPUT", "0.0003"))

# Cost per 1K output tokens (USD)
CLAUDE_COST_PER_1K_OUTPUT = float(os.environ.get("CLAUDE_COST_PER_1K_OUTPUT", "0.015"))


# ============================================================================
# Logging Configuration
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DEBUG = os.environ.get("DEBUG", "0") == "1"
