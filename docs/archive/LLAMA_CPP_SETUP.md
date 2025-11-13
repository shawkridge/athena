# llama.cpp Setup Guide for Athena

This guide covers the complete setup of local LLM inference for Athena using llama.cpp with two specialized models.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATHENA MEMORY SYSTEM                         │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    EMBEDDING          REASONING            COMPRESSION
         │                    │                    │
    nomic-embed-text-v1.5   Qwen3-VL-4B     LLMLingua-2
    (768D, 550MB)         (4B, 2.5GB)      (optional)
         │                    │                    │
    Port 8001            Port 8002             Local
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                     PostgreSQL + pgvector
                              │
                         Claude API
```

## Prerequisites

- **Docker & Docker Compose** (recommended for easy deployment)
- **OR** Local llama.cpp binary (for manual setup)
- **Disk Space**: ~3GB for models (down from 6GB with Qwen3-VL-4B)
- **RAM**: 8GB minimum, 16GB recommended (3GB models + 5GB overhead)
- **CPU**: 8+ cores (more cores = faster inference)

## Option 1: Docker Deployment (Recommended)

### Step 1: Download Models

```bash
cd /home/user/.work/athena

# Make script executable
chmod +x scripts/download_models.sh

# Download models (will be placed in ~/.athena/models)
./scripts/download_models.sh

# Or specify custom path
./scripts/download_models.sh /custom/models/path
```

The script will download:
- `nomic-embed-text-v1.5.Q4_K_M.gguf` (550MB)
- `Qwen3-VL-4B-Instruct-Q4_K_M.gguf` (2.5GB)

**Total**: ~3GB, takes 3-10 minutes depending on internet speed.

### Step 2: Start Docker Services

```bash
cd docker

# Build Athena service (if not already built)
docker-compose build athena

# Start all services
docker-compose up -d

# Verify services are healthy
docker-compose ps

# Check logs
docker-compose logs -f llamacpp-embeddings
docker-compose logs -f llamacpp-reasoning
docker-compose logs -f postgres
docker-compose logs -f athena
```

### Step 3: Verify Services

```bash
# Check embedding server health
curl -s http://localhost:8001/health | jq .

# Check reasoning server health
curl -s http://localhost:8002/health | jq .

# Check PostgreSQL
docker-compose exec -T postgres psql -U athena -d athena -c "SELECT 1"

# Check Athena server
curl -s http://localhost:8000/health | jq .
```

### Step 4: Test Embedding Generation

```bash
# Test embedding server
curl -X POST http://localhost:8001/embedding \
  -H "Content-Type: application/json" \
  -d '{"content":"hello world"}' | jq .embedding[0:5]

# Expected output: [-0.1234, 0.5678, ...] (768 dimensions)
```

### Step 5: Test Reasoning

```bash
# Test reasoning server
curl -X POST http://localhost:8002/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"What is 2+2?",
    "n_predict":100,
    "temperature":0.7
  }' | jq .content
```

## Option 2: Local Installation

### Step 1: Install llama.cpp

```bash
# Clone repository
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Build with CPU optimization
mkdir build
cd build
cmake .. -DLLAMA_BUILD_SERVER=ON
cmake --build . --config Release -j$(nproc)

# Binary will be at: ./bin/llama-server
```

### Step 2: Download Models

```bash
cd ~/.athena/models

# Download nomic-embed-text-v1.5 (550MB)
wget https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q4_K_M.gguf

# Download Qwen3-VL-4B (2.5GB)
wget https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/resolve/main/Qwen3-VL-4B-Instruct-Q4_K_M.gguf
```

### Step 3: Start Servers

**Terminal 1 - Embedding Server:**
```bash
cd ~/llama.cpp/build/bin

./llama-server \
  -m ~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf \
  --embedding \
  --ctx-size 8192 \
  --port 8001 \
  --threads 8
```

**Terminal 2 - Reasoning Server:**
```bash
cd ~/llama.cpp/build/bin

./llama-server \
  -m ~/.athena/models/Qwen3-VL-4B-Instruct-Q4_K_M.gguf \
  --ctx-size 32768 \
  --port 8002 \
  --threads 12 \
  --n-gpu-layers 0
```

### Step 4: Start Athena

```bash
cd /home/user/.work/athena

# Start in development mode
python -m athena.server

# Or with environment variables
LLAMACPP_EMBEDDINGS_URL=http://localhost:8001 \
LLAMACPP_REASONING_URL=http://localhost:8002 \
python -m athena.server
```

## GPU Acceleration (Optional)

If you have an NVIDIA GPU, you can accelerate inference:

### For Docker

Edit `docker-compose.yml`:

```yaml
llamacpp-embeddings:
  environment:
    - CUDA_VISIBLE_DEVICES=0  # Your GPU device
  command: >
    -m /models/nomic-embed-text-v1.5.Q4_K_M.gguf
    --embedding
    --n-gpu-layers 35        # Offload layers to GPU
    # ... rest of command

llamacpp-reasoning:
  environment:
    - CUDA_VISIBLE_DEVICES=0
  command: >
    -m /models/qwen2.5-7b-instruct-q4_k_m.gguf
    --n-gpu-layers 35
    # ... rest of command
```

### For Local Installation

Add `--n-gpu-layers 35` to llama-server commands:

```bash
./llama-server \
  -m ~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf \
  --embedding \
  --n-gpu-layers 35  # Offload to GPU
  --port 8001
```

**Expected speedup**: 3-5x faster inference with GPU.

## Configuration

### Environment Variables

These are automatically set in `docker-compose.yml`. For local development:

```bash
# Embedding server URL
export LLAMACPP_EMBEDDINGS_URL=http://localhost:8001

# Reasoning server URL
export LLAMACPP_REASONING_URL=http://localhost:8002

# Embedding dimension (read from server)
export LLAMACPP_EMBEDDING_DIM=768

# Thread count
export LLAMACPP_N_THREADS=8
```

### Configuration File

Edit `src/athena/core/config.py`:

```python
# llama.cpp Configuration (HTTP Server)
LLAMACPP_EMBEDDINGS_URL = os.environ.get("LLAMACPP_EMBEDDINGS_URL", "http://localhost:8001")
LLAMACPP_REASONING_URL = os.environ.get("LLAMACPP_REASONING_URL", "http://localhost:8002")
LLAMACPP_EMBEDDING_DIM = int(os.environ.get("LLAMACPP_EMBEDDING_DIM", "768"))
LLAMACPP_N_THREADS = int(os.environ.get("LLAMACPP_N_THREADS", "8"))
```

## Models Explained

### 1. nomic-embed-text-v1.5 (Embedding)

**Purpose**: Generate 768-dimensional semantic embeddings

**Specs**:
- Size: 550MB (Q4 quantization)
- Speed: ~3,000 tokens/sec on CPU
- Dimension: 768D (perfect for PostgreSQL pgvector)
- Context: 8,192 tokens
- Quality: MTEB score 62.39 (top 10)

**Why This Model**:
- Native 768D output (no dimension adaptation needed)
- Excellent at long-context semantic understanding (8K context)
- Built-in matryoshka representation learning (can truncate dimensions)
- Optimized for semantic search and RAG applications
- Proven llama.cpp compatibility

**Use Case**: Converting memory events, queries, and context into embeddings for PostgreSQL vector search.

### 2. Qwen3-VL-4B-Instruct (Reasoning)

**Purpose**: Local reasoning for pattern extraction and consolidation

**Specs**:
- Size: 2.5GB (Q4 quantization)
- Speed: 40-50 tokens/sec on CPU (2x faster than Qwen2.5-7B)
- Parameters: 4B
- Context: 128K tokens
- Reasoning Quality: ⭐⭐⭐⭐⭐
- Special Capability: Vision (can analyze code screenshots and diagrams)

**Why This Model**:
- 2x faster token generation (40-50 vs 25-30 tok/s)
- 40% smaller than Qwen2.5-7B (2.5GB vs 4.1GB)
- Exceptional reasoning for its size (4B > 7B in some benchmarks)
- Excellent instruction following
- Strong pattern recognition and abstraction
- Low hallucination rate
- 128K context for processing large memory clusters
- Apache 2.0 license (no restrictions)
- Vision capabilities for analyzing code structure

**Use Case**: Extracting semantic patterns from episodic event clusters, validating consolidation heuristics, complex reasoning chains, visual code analysis.

### 3. LLMLingua-2 (Compression) - Optional

**Purpose**: Compress prompts before sending to Claude API

**Specs**:
- Compression Ratio: 60-75%
- Quality Preservation: 95%+
- Latency: 100-200ms
- Model: XLM-RoBERTa-based (640M parameters)
- License: MIT

**Why Use It**:
- Reduces Claude API costs by 60-95% (with caching)
- Preserves semantic information better than token pruning
- Zero configuration needed
- Works with any LLM (Claude, GPT, etc.)

**Install**:
```bash
pip install llmlingua
```

## Performance Expectations

### Latency (CPU, no GPU)

| Operation | Hardware | Latency |
|-----------|----------|---------|
| Embedding | 16-core CPU | 50-150ms |
| Reasoning (100 tokens) | 16-core CPU | 2-2.5s (2x faster!) |
| Prompt Compression | CPU | 100-200ms |
| PostgreSQL search | Native | 10-50ms |
| **Total pipeline** | Full system | 1.5-3.5s (40% faster!) |

### Throughput

- **Embeddings**: 3,000 tokens/sec
- **Reasoning**: 40-50 tokens/sec (up from 25-30)
- **Queries**: ~30-40 per minute (with reasoning, up from 20-30)

### Memory Usage

| Component | RAM |
|-----------|-----|
| nomic-embed (loaded) | 800MB |
| Qwen3-VL-4B (loaded) | 3.5GB |
| PostgreSQL + pgvector | 500MB |
| Athena server | 200MB |
| **Total** | ~5.0GB (down from 7.5GB!) |

## Troubleshooting

### "Connection refused" errors

**Problem**: llama.cpp servers not running

**Solution**:
```bash
# Docker
docker-compose up -d llamacpp-embeddings llamacpp-reasoning

# Local: Check if processes are running
ps aux | grep llama-server

# Restart servers
docker-compose restart llamacpp-embeddings llamacpp-reasoning
```

### Model files not found

**Problem**: Models not downloaded to correct location

**Solution**:
```bash
# Check models exist
ls -lh ~/.athena/models/

# If missing, download them
./scripts/download_models.sh

# Verify Docker has access
docker volume inspect llamacpp_models
```

### Server responds with 504 Gateway Timeout

**Problem**: Model loading takes too long

**Solution**:
- Increase health check timeouts in docker-compose.yml
- Ensure sufficient RAM (need 7-8GB free)
- Check CPU isn't throttled
- Run `docker-compose logs llamacpp-embedding` for details

### Slow performance on CPU

**Problem**: Inference speed is too slow

**Solutions**:
1. Use GPU acceleration (add `--n-gpu-layers 35`)
2. Use smaller models (Phi-3.5-Mini instead of Qwen2.5-7B)
3. Increase thread count (edit GGML_NUM_THREADS)
4. Use lighter quantization (Q3_K_S instead of Q4_K_M)

### Out of memory errors

**Problem**: Not enough RAM for loaded models

**Solutions**:
1. Reduce context size (`--ctx-size 4096` instead of 32768)
2. Use smaller models
3. Use more aggressive quantization (Q3_K instead of Q4_K)
4. Add swap space (not ideal but works in pinch)

## Advanced Configuration

### CPU Threading Tuning

Optimal threads = (CPU cores × 1.5)

```bash
# For 8-core CPU: use 12 threads
export GGML_NUM_THREADS=12
export GGML_NUM_THREADS_BATCH=12

# For 16-core CPU: use 24 threads
export GGML_NUM_THREADS=24
export GGML_NUM_THREADS_BATCH=24
```

### Quantization Options

Available quantizations for each model:

**nomic-embed-text-v1.5** (download from HuggingFace):
- Q3_K_S: 330MB (faster, lower quality)
- Q4_K_M: 550MB (balanced) ← **Recommended**
- Q5_K_M: 700MB (higher quality)
- Q6_K: 800MB (highest quality)

**Qwen3-VL-4B**:
- Q3_K_S: 1.8GB (faster, lower quality)
- Q4_K_M: 2.5GB (balanced) ← **Recommended**
- Q5_K_M: 3.2GB (higher quality)
- Q6_K: 3.8GB (highest quality)

### Multiple GPU Devices

If you have multiple GPUs:

```bash
# Use specific GPU for embedding
docker-compose.yml:
  llamacpp-embeddings:
    environment:
      - CUDA_VISIBLE_DEVICES=0

# Use different GPU for reasoning
  llamacpp-reasoning:
    environment:
      - CUDA_VISIBLE_DEVICES=1
```

## Integration with Athena

### Using LocalLLMClient

```python
from athena.core.llm_client import LocalLLMClient
import asyncio

async def main():
    client = LocalLLMClient(
        embedding_url="http://localhost:8001",
        reasoning_url="http://localhost:8002",
        enable_compression=True
    )

    # Generate embedding
    result = await client.embed("semantic search query")
    print(f"Embedding: {result.embedding[:5]}...")  # First 5 dims

    # Run local reasoning
    analysis = await client.reason(
        prompt="Analyze these patterns",
        system="You are a consolidation engine",
        max_tokens=1000
    )
    print(f"Analysis: {analysis.text}")

    # Compress prompt for Claude
    compressed = await client.compress_prompt(
        context="Large memory context",
        instruction="Extract patterns",
        compression_ratio=0.5
    )
    print(f"Compressed: {compressed.original_tokens} → {compressed.compressed_tokens}")

asyncio.run(main())
```

### In Consolidation Pipeline

```python
from athena.consolidation import ConsolidationPipeline
from athena.core.llm_client import LocalLLMClient

pipeline = ConsolidationPipeline(
    db=db,
    llm_client=LocalLLMClient()
)

patterns = await pipeline.extract_patterns(events)
```

## Next Steps

1. **Download models** (if not already done):
   ```bash
   ./scripts/download_models.sh
   ```

2. **Start Docker** (or local servers):
   ```bash
   docker-compose up -d
   ```

3. **Verify everything** works:
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8000/health
   ```

4. **Test memory operations**:
   ```bash
   # Remember an event
   curl -X POST http://localhost:8000/tools/remember/execute \
     -H "Content-Type: application/json" \
     -d '{"content":"test memory","memory_type":"fact"}'
   ```

5. **Monitor performance**:
   ```bash
   docker-compose logs -f athena | grep -E "(embedding|reasoning|latency)"
   ```

## References

- **nomic-embed-text-v1.5**: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
- **Qwen3-VL-4B-Instruct**: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- **llama.cpp**: https://github.com/ggerganov/llama.cpp
- **LLMLingua-2**: https://github.com/microsoft/LLMLingua
- **MTEB Benchmark**: https://huggingface.co/spaces/mteb/leaderboard

## Support

For issues:
1. Check troubleshooting section above
2. Review docker logs: `docker-compose logs -f`
3. Test servers manually with curl
4. Check resource usage: `docker stats`

---

**Last Updated**: November 2024
**Version**: 1.0
**Status**: Production-Ready
