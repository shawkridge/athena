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
OLLAMA_EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6B")

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
# Logging Configuration
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
DEBUG = os.environ.get("DEBUG", "0") == "1"
