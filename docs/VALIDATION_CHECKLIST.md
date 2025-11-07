# Athena Qdrant + llama.cpp Integration - Validation Checklist

**Date:** January 2025
**Status:** ✅ Code Implementation Complete - Ready for Model Download & Testing

---

## 📋 Pre-Deployment Checklist

### Architecture Design
- [x] **Hybrid database design**: SQLite (metadata) + Qdrant (vectors)
- [x] **Dual-write pattern**: Store in both databases atomically
- [x] **Query routing**: Qdrant for search, SQLite for metadata
- [x] **Graceful fallback**: SQLite search if Qdrant unavailable
- [x] **Deletion handling**: Remove from both databases

### Code Implementation
- [x] **Config file** (`src/athena/core/config.py`):
  - Lines 21-41: llama.cpp configuration
  - Dimension matching: 768D across all components
  - Provider selection: `EMBEDDING_PROVIDER = "llamacpp"`

- [x] **llama.cpp wrapper** (`src/athena/core/llamacpp_client.py`):
  - `LlamaCppEmbedding` class for embeddings
  - `LlamaCppLLM` class for text generation
  - Auto-threading support
  - Graceful error handling

- [x] **Embeddings provider** (`src/athena/core/embeddings.py`):
  - Multi-provider support (ollama/llamacpp)
  - Auto-detection and fallback logic
  - Dimension reporting

- [x] **MemoryStore dual-write** (`src/athena/memory/store.py`):
  - `remember()`: Store in SQLite + Qdrant (lines 89-148)
  - `forget()`: Delete from both (lines 150-168)
  - Error recovery if one database fails

- [x] **Semantic search** (`src/athena/memory/search.py`):
  - `_recall_qdrant()`: Qdrant search path (lines 76-127)
  - `_recall_sqlite()`: Fallback search path (lines 129-203)
  - Filtering by project_id and memory_type

- [x] **Dependencies** (`pyproject.toml`):
  - `llama-cpp-python>=0.2.0` added
  - `huggingface-hub>=0.20.0` added

- [x] **Model downloader** (`scripts/download_llama_models.sh`):
  - Automated HuggingFace model download
  - Progress tracking and verification
  - Proper error handling

### Model Selection
- [x] **Embedding model**: nomic-embed-text-v2-moe
  - Repository: nomic-ai/nomic-embed-text-v2-moe-GGUF
  - Quantization: Q6_K (397 MB)
  - Dimensions: 768 (perfect match)
  - Context: 512 tokens

- [x] **LLM model**: DeepSeek-R1-Distill-Qwen-7B
  - Repository: bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF
  - Quantization: Q4_K_M (4.68 GB)
  - Parameters: 7B
  - Context: 32K tokens
  - Specialization: SOTA reasoning

### Integration Testing
- [x] **Integration test** (`test_qdrant_llamacpp_integration.py`):
  1. Config validation
  2. MemoryStore initialization
  3. Dual-write pattern (SQLite + Qdrant)
  4. Semantic search via Qdrant
  5. Memory deletion (both DBs)
  6. Qdrant statistics

---

## 🚀 Deployment Steps

### Phase 1: Environment Setup

```bash
# 1. Install dependencies
pip install llama-cpp-python>=0.2.0 huggingface-hub>=0.20.0 qdrant-client>=1.7.0

# 2. Verify installation
python -c "import llama_cpp; print('✅ llama-cpp-python')"
python -c "import qdrant_client; print('✅ qdrant-client')"
python -c "from athena.core.llamacpp_client import LlamaCppEmbedding; print('✅ Athena integration')"
```

### Phase 2: Model Download

```bash
# 1. Create models directory
mkdir -p ~/.athena/models

# 2. Download models (takes ~10-15 minutes)
./scripts/download_llama_models.sh

# 3. Verify downloads
ls -lh ~/.athena/models/
# Expected:
#   397 MB  nomic-embed-text-v2-moe.Q6_K.gguf
#   4.7 GB  DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf
```

### Phase 3: Service Startup

```bash
# 1. Start Qdrant
docker-compose up -d qdrant

# 2. Verify Qdrant health
curl http://localhost:6333/health

# 3. Start Athena MCP server
docker-compose up -d athena-http

# 4. Check logs
docker-compose logs -f athena-http
```

### Phase 4: Integration Testing

```bash
# Run comprehensive integration test
python test_qdrant_llamacpp_integration.py

# Expected output:
# ✅ Configuration Validation
# ✅ MemoryStore Initialization
# ✅ Dual-Write Pattern (SQLite + Qdrant)
# ✅ Semantic Search (Qdrant)
# ✅ Memory Deletion (SQLite + Qdrant)
# ✅ Qdrant Collection Statistics
# ✅ ALL TESTS PASSED
```

---

## ✅ Verification Tests

### Test 1: Config Validation
**Expected Behavior:**
```
✓ Embedding Provider: llamacpp
✓ LLM Provider: llamacpp
✓ Qdrant URL: http://localhost:6333
✓ Qdrant Embedding Dim: 768
✅ Dimension Match: 768D
```

### Test 2: MemoryStore Init
**Expected Behavior:**
```
✓ Embedding backend: llamacpp
✓ Embedding dimensions: 768D
✓ Qdrant enabled: http://localhost:6333
✓ Qdrant health check: PASSED
```

### Test 3: Dual-Write Pattern
**Expected Behavior:**
```
✓ Stored memory ID: 1
✓ Found in SQLite metadata
✓ Found in Qdrant vectors
```

### Test 4: Semantic Search
**Expected Behavior:**
```
Query: 'container technology'
Results: 3
  1. Docker containers provide process isolation...
     Similarity: 0.887
     Rank: 1
  2. Kubernetes orchestrates container deployments...
     Similarity: 0.856
     Rank: 2
✅ Semantic search working via Qdrant
```

### Test 5: Memory Deletion
**Expected Behavior:**
```
✓ Deleted memory 1
✓ Confirmed: Deleted from SQLite
✓ Confirmed: Deleted from Qdrant
```

---

## 🔧 Troubleshooting Guide

### Issue: "llama_cpp module not found"
```bash
# Solution: Install with build support
pip install llama-cpp-python --no-cache-dir
```

### Issue: "Qdrant connection refused"
```bash
# Solution: Ensure Qdrant is running
docker-compose ps qdrant
docker-compose logs qdrant
```

### Issue: "Model file not found"
```bash
# Solution: Download models
./scripts/download_llama_models.sh
ls ~/.athena/models/
```

### Issue: "Dimension mismatch (768 vs 1024)"
```bash
# Solution: Verify embedding model outputs 768D
python -c "
from athena.core.embeddings import EmbeddingModel
e = EmbeddingModel(provider='llamacpp')
print(f'Dimensions: {e.embedding_dim}')
"
# Expected: Dimensions: 768
```

### Issue: "Slow inference (< 5 tokens/sec)"
```bash
# Solution: Check CPU threads
export LLAMACPP_N_THREADS=8  # Use more threads
python test_qdrant_llamacpp_integration.py

# Or use smaller model for speed:
export LLAMACPP_LLM_MODEL_PATH=~/.athena/models/Qwen2.5-Coder-3B-Q5_K_M.gguf
```

---

## 📊 Component Verification Matrix

| Component | Database | Expected Behavior | Verification |
|-----------|----------|-------------------|--------------|
| **Embedding Generation** | llama.cpp | Output 768-dim vectors | `embeddings.py:46` |
| **Vector Storage** | Qdrant | Store with metadata | `qdrant_adapter.py:112` |
| **Metadata Storage** | SQLite | Store without vectors | `store.py:128` |
| **Semantic Search** | Qdrant | Fast similarity search | `search.py:102` |
| **Metadata Fetch** | SQLite | Join vectors with content | `database.py:813` |
| **Memory Deletion** | Both | Atomic delete from both | `store.py:160` |
| **Fallback Search** | SQLite | Work if Qdrant down | `search.py:129` |

---

## 🎯 Success Criteria

### Deployment Success
- [ ] All models downloaded to `~/.athena/models/`
- [ ] Qdrant container running and healthy
- [ ] Athena HTTP server running
- [ ] Integration test passes (6/6 tests)

### Performance Baseline
- [ ] Embedding generation: > 1000 vectors/sec
- [ ] Semantic search: < 200ms per query
- [ ] Memory storage: > 500 ops/sec
- [ ] LLM inference: > 5 tokens/sec

### Stability Requirements
- [ ] No memory leaks during long-running consolidation
- [ ] Graceful fallback if Qdrant unavailable
- [ ] Proper error messages for misconfigurations
- [ ] Recovery from transient network errors

---

## 📋 Final Checklist Before Production

- [ ] All code changes peer-reviewed
- [ ] Integration tests passing (6/6)
- [ ] Performance benchmarks baseline established
- [ ] Disaster recovery plan documented
- [ ] Monitoring/logging configured
- [ ] Documentation updated
- [ ] Release notes prepared

---

## 🎉 Completion Status

**Code Implementation:** ✅ COMPLETE (9/9 files)
**Testing Framework:** ✅ READY (integration test written)
**Documentation:** ✅ COMPLETE (this checklist + summary doc)
**Models:** ⏳ PENDING (download script ready, awaiting execution)
**Validation:** ⏳ PENDING (test ready, awaiting model download)

**Next Step:** Run `./scripts/download_llama_models.sh` to download models and run tests.
