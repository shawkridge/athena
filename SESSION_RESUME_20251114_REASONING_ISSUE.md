# Session Resume: Reasoning Service Issue Found - November 14, 2025

## TL;DR

✅ Hooks are fully validated (14/14 tests passing)
⚠️ Found underlying issue: Reasoning service (port 8002) not implemented
🎯 Next session: Fix llamacpp_server.py to provide `/completion` endpoint for reasoning

---

## What We Accomplished

### ✅ Hook Validation Complete
- Created 14 comprehensive tests across 3 test files
- All tests passing (100% success rate)
- Fixed critical embeddings endpoint bug (`/v1/embeddings` → `/embeddings`)
- Hooks production-ready

### ⚠️ Root Cause of "Reasoning Failed" Error Found

**Problem**:
- E2E tests show "Reasoning failed: All connection attempts failed"
- Query expansion tries to call `localhost:8002/completion`
- But llamacpp_server.py only provides `/embeddings` endpoint on port 8001

**Current State**:
```
llamacpp_server.py (docker/llamacpp_server.py):
├─ Port 8001: /health ✅
├─ Port 8001: /embeddings ✅
└─ Port 8002: /completion ❌ MISSING - NOT IMPLEMENTED

Expected by code:
├─ Port 8001: Embeddings (nomic-embed-text) ✅ WORKING
└─ Port 8002: Reasoning (Qwen2.5-7B) ❌ NOT PROVIDED
```

---

## Technical Details

### File Structure
- **Embeddings Server**: `/home/user/.work/athena/docker/llamacpp_server.py`
  - Current: Only provides `/embeddings` endpoint
  - Status: Running on port 8001 ✅
  - Process: `python /home/user/.work/athena/docker/llamacpp_server.py`

- **Expected Reasoning Server**: Not implemented
  - Should: Provide `/completion` endpoint
  - Port: 8002 (per config)
  - Model: Qwen2.5-7B-Instruct

### Configuration
**File**: `src/athena/core/config.py`
```python
# Line 30 - Embeddings (WORKING)
LLAMACPP_EMBEDDINGS_URL = "http://localhost:8001"

# Line 33 - Reasoning (NOT PROVIDED)
LLAMACPP_REASONING_URL = "http://localhost:8002"

# Line ??? - Query expansion enabled but can't run
RAG_QUERY_EXPANSION_ENABLED = True  # Tries to use port 8002
```

### Error Call Chain
```
SemanticSearch.recall()
  ↓ If RAG_QUERY_EXPANSION_ENABLED
  ↓ create_llm_client("local")
  ↓ LocalLLMClientSync(localhost:8002)
  ↓ POST to /completion endpoint
  ↓ "All connection attempts failed" (port not listening)
```

---

## What Needs To Be Fixed

### Option A: Add Reasoning to llamacpp_server.py (RECOMMENDED)
Add `/completion` endpoint to existing `docker/llamacpp_server.py`:
1. Import/initialize Qwen2.5-7B model
2. Add POST `/completion` endpoint that mirrors embeddings pattern
3. Optionally: Run on port 8002 or add to existing 8001 with path prefix

**Advantage**: Single server, simpler management

### Option B: Create Separate Reasoning Server
Create new `reasoning_server.py`:
1. Similar FastAPI structure
2. Load Qwen2.5-7B model
3. Provide `/completion` endpoint
4. Run on port 8002

**Advantage**: Separation of concerns

### Option C: Use Existing Model Loading Pattern
The embeddings server already has model loading code:
```python
LLAMA_INSTANCE = Llama(
    model_path=model_path,
    embedding=True,  # ← Just add another instance with embedding=False
    n_threads=8
)
```

Could add:
```python
REASONING_INSTANCE = Llama(
    model_path="~/.athena/models/Qwen2.5-7B-Instruct.gguf",
    embedding=False,  # ← For reasoning, not embedding
    n_threads=8
)
```

---

## Impact

### Why Hooks Aren't Affected
✅ Hooks use basic semantic search (PostgreSQL pgvector)
✅ Hooks don't use query expansion
✅ Hooks work with or without reasoning service

### Why Tests Show Failure
❌ E2E test explicitly tests query expansion
❌ Query expansion requires reasoning service
❌ Service connection fails → error messages

---

## Files to Review/Modify

### Primary
- `/home/user/.work/athena/docker/llamacpp_server.py` (main fix location)
  - Lines 73-94: Embeddings endpoint pattern
  - Lines 100-103: Port/server startup code
  - Add reasoning endpoint following same pattern

### Reference
- `src/athena/core/config.py` (line 33)
  - Shows expected reasoning URL
- `src/athena/rag/llm_client.py` (lines 187-240)
  - Shows what `/completion` endpoint should accept
- `src/athena/core/llm_client.py` (lines 221-240)
  - Shows expected JSON format

---

## Next Session Action Items

### Priority 1: Fix Reasoning Server
1. [ ] Add `/completion` endpoint to llamacpp_server.py
2. [ ] Support JSON request format: `{"prompt": "...", "n_predict": 2048, ...}`
3. [ ] Return format: `{"content": "...", "tokens_predicted": N}`
4. [ ] Test endpoint: `curl -X POST http://localhost:8002/completion -H "Content-Type: application/json" -d '{"prompt":"test"}'`

### Priority 2: Verify Fix
1. [ ] Re-run E2E tests: `python tests/e2e_memory_system.py`
2. [ ] Verify no "Reasoning failed" errors
3. [ ] Confirm basic search still works

### Priority 3: Document
1. [ ] Update CONTRIBUTING.md with dual-server setup
2. [ ] Document port 8001 vs 8002 separation
3. [ ] Add reasoning server startup instructions

---

## Current Test Status

| Category | Result | Details |
|----------|--------|---------|
| Hook Validation | ✅ 14/14 | Production-ready |
| Hook Integration | ✅ 7/7 | All passing |
| Hook Evaluation | ✅ 7/7 | 100% quality score |
| E2E Tests | ⚠️ 5/6 | Fails on query expansion (expected) |
| **Reasoning Service** | ❌ MISSING | Needs implementation |

---

## Git Status

**Recent Commits**:
```
e9f4039 docs: Final session resume - hooks fully validated
2a554a1 test: Comprehensive hook evaluation (7/7 tests passing)
d3dbc82 fix: Fix llamacpp embeddings endpoint
```

**No breaking changes needed** - hooks work fine. Just need to add the reasoning service that was planned but not implemented.

---

## Quick Reference: What Changed

### Bug Fixed Today
- ❌ Embeddings endpoint was `/v1/embeddings` (404)
- ✅ Fixed to `/embeddings` (working)
- Result: 9 semantic memories now created

### Issue Found (Not Yet Fixed)
- ❌ Reasoning endpoint on port 8002 doesn't exist
- Status: Gracefully degrades, but query expansion fails
- Action: Add `/completion` endpoint to llamacpp_server.py

---

## Context for Implementation

### Expected /completion Endpoint

Based on code in `src/athena/core/llm_client.py` lines 221-231:

**Request**:
```json
{
  "prompt": "user input here",
  "n_predict": 2048,
  "temperature": 0.7,
  "top_p": 0.9,
  "stop": ["\n\nUser:", "Human:"]
}
```

**Response**:
```json
{
  "content": "generated text here",
  "tokens_predicted": 125
}
```

### Model Configuration

From `docker/llamacpp_server.py`:
```python
# Embedding model (port 8001) - WORKING
model_path = "~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf"
Llama(model_path=model_path, embedding=True)

# Reasoning model (port 8002) - NEEDS IMPLEMENTATION
model_path = "~/.athena/models/Qwen2.5-7B-Instruct.gguf"
Llama(model_path=model_path, embedding=False)
```

---

## Session Metadata

- **Date**: November 14, 2025
- **Duration**: ~4 hours
- **Accomplishments**: Hook validation + root cause analysis
- **Issues Found**: 2 (embeddings endpoint ✅ fixed, reasoning service ⚠️ found)
- **Tests Created**: 14 comprehensive tests
- **Status**: Hooks production-ready, reasoning service needs implementation

---

**Ready for next session**: Clear context and implement `/completion` endpoint in llamacpp_server.py
