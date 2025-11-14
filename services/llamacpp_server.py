#!/usr/bin/env python3
"""
llama.cpp HTTP server for embeddings only.
Lightweight server for fast semantic embeddings (nomic-embed-text).
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from llama_cpp import Llama

app = FastAPI(title="llama.cpp Embeddings Server", version="0.1.0")

# Load embedding model (required, fail-fast)
embedding_model_path = os.environ.get('EMBEDDING_MODEL_PATH',
                                      os.path.expanduser('~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf'))
if not os.path.exists(embedding_model_path):
    raise FileNotFoundError(f"Embedding model not found at {embedding_model_path}")

print(f"Loading embedding model from {embedding_model_path}...", file=sys.stderr)
EMBEDDING_INSTANCE = Llama(
    model_path=embedding_model_path,
    embedding=True,
    n_threads=int(os.environ.get('LLAMACPP_THREADS', '8'))
)
print("Embedding model loaded successfully!", file=sys.stderr)


class EmbeddingRequest(BaseModel):
    text: Optional[str] = None
    input: Optional[str] = None  # Alternative field name
    content: Optional[str] = None  # Alternative field name for Athena compatibility


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model: str = "nomic-embed-text-v1.5"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": "nomic-embed-text-v1.5",
        "server": "embeddings-only"
    }


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for text."""
    text = request.text or request.input or request.content
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        embedding = EMBEDDING_INSTANCE.embed(text)
        return EmbeddingResponse(embedding=embedding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")


@app.post("/embedding", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for text (alias for /embeddings)."""
    return await generate_embeddings(request)


if __name__ == "__main__":
    port = int(os.environ.get("EMBEDDINGS_PORT", 8001))
    host = "0.0.0.0"
    print(f"Starting llama.cpp embeddings server on {host}:{port}", file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="info")
