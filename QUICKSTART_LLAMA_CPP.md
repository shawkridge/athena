# Quick Start: llama.cpp with Athena

Get Athena running with local LLM inference in 5 minutes.

## 1️⃣ Download Models (~10 minutes)

```bash
cd /home/user/.work/athena

./scripts/download_models.sh

# Models will be in ~/.athena/models/
# - nomic-embed-text-v1.5.Q4_K_M.gguf (550MB)
# - qwen2.5-7b-instruct-q4_k_m.gguf (4.1GB)
```

## 2️⃣ Start Docker Services

```bash
cd docker

# Start all services
docker-compose up -d

# Verify health
docker-compose ps

# Watch logs
docker-compose logs -f athena
```

## 3️⃣ Verify Servers

```bash
# Embedding server (should return 200)
curl -s http://localhost:8001/health

# Reasoning server (should return 200)
curl -s http://localhost:8002/health

# Athena server
curl -s http://localhost:8000/health | jq .
```

## 4️⃣ Test Embedding

```bash
curl -X POST http://localhost:8001/embedding \
  -H "Content-Type: application/json" \
  -d '{"content":"hello world"}' | jq '.embedding | length'

# Expected output: 768
```

## 5️⃣ Test Memory Storage

```bash
# Store a memory
curl -X POST http://localhost:8000/tools/remember/execute \
  -H "Content-Type: application/json" \
  -d '{
    "content":"test memory event",
    "memory_type":"fact"
  }' | jq .

# Expected: memory ID returned
```

## 6️⃣ Test Memory Recall

```bash
# Query stored memories
curl -X POST http://localhost:8000/tools/recall/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query":"memory event",
    "k":5
  }' | jq .
```

## Troubleshooting

### Services won't start
```bash
# Check Docker
docker ps -a

# View logs
docker-compose logs llamacpp-embeddings
docker-compose logs llamacpp-reasoning

# Restart
docker-compose restart
```

### Models not found
```bash
# Download models
./scripts/download_models.sh

# Verify location
ls -lh ~/.athena/models/

# Check Docker can see them
docker volume ls | grep llamacpp
```

### Slow response (timeouts)
- Ensure 16GB+ RAM available
- Check CPU isn't throttled
- Increase context size if needed

## Performance

| Operation | Time |
|-----------|------|
| Embedding | 50-150ms |
| Reasoning (100 tokens) | 3-5 seconds |
| Total pipeline | 2-7 seconds |

## Architecture

```
Athena Server (8000)
    ↓
Embedding Server (8001) ←→ nomic-embed-text-v1.5
    ↓
PostgreSQL + pgvector
    ↓
Reasoning Server (8002) ←→ Qwen2.5-7B-Instruct
    ↓
Claude API (for validation)
```

## Next Steps

- Read [LLAMA_CPP_SETUP.md](./LLAMA_CPP_SETUP.md) for detailed configuration
- Check [consolidation pipeline](./src/athena/consolidation/) for pattern extraction
- Enable LLMLingua-2: `pip install llmlingua`

## Support

```bash
# Check all services healthy
docker-compose ps

# Monitor performance
docker stats

# View detailed logs
docker-compose logs -f

# Clean up (stops containers, keeps volumes)
docker-compose down

# Full reset (removes everything)
docker-compose down -v
```

---

**Status**: ✅ Production Ready | **Models**: Optimized for CPU | **License**: Open Source
