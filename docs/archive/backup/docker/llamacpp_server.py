#!/usr/bin/env python3
"""
Simple llama.cpp HTTP server for embeddings.
Provides a basic FastAPI server that exposes embeddings endpoints.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="llama.cpp Server", version="0.1.0")

# Try to load actual llama-cpp-python, fall back to mock
try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = False  # Will be True after model loads
    MODEL_LOADED = False
    LLAMA_INSTANCE = None

    # Try to load model if it exists
    model_path = os.environ.get('MODEL_PATH', os.path.expanduser('~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf'))
    if os.path.exists(model_path):
        try:
            print(f"Loading model from {model_path}...", file=sys.stderr)
            LLAMA_INSTANCE = Llama(
                model_path=model_path,
                embedding=True,
                n_threads=int(os.environ.get('LLAMACPP_THREADS', '8'))
            )
            HAS_LLAMA_CPP = True
            MODEL_LOADED = True
            print("Model loaded successfully!", file=sys.stderr)
        except Exception as e:
            print(f"Error loading model: {e}", file=sys.stderr)
            HAS_LLAMA_CPP = False
            MODEL_LOADED = False
    else:
        print(f"Model not found at {model_path}", file=sys.stderr)
        print("Using mock embeddings for testing", file=sys.stderr)
        HAS_LLAMA_CPP = False

except ImportError:
    print("llama-cpp-python not installed, using mock embeddings", file=sys.stderr)
    HAS_LLAMA_CPP = False
    MODEL_LOADED = False
    LLAMA_INSTANCE = None


class EmbeddingRequest(BaseModel):
    text: Optional[str] = None
    input: Optional[str] = None  # Alternative field name
    content: Optional[str] = None  # Alternative field name for Athena compatibility


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model: str = "llamacpp"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": MODEL_LOADED,
        "using_mock": not HAS_LLAMA_CPP
    }


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for text."""
    text = request.text or request.input or request.content
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if HAS_LLAMA_CPP and LLAMA_INSTANCE:
        try:
            embedding = LLAMA_INSTANCE.embed(text)
            return EmbeddingResponse(embedding=embedding)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
    else:
        # Return mock embeddings for testing
        # 384-dimensional embedding filled with mock data
        embedding = [0.1 * (i % 10) for i in range(384)]
        return EmbeddingResponse(embedding=embedding)


@app.post("/embedding", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for text (alias for /embeddings)."""
    return await generate_embeddings(request)


if __name__ == "__main__":
    port = int(os.environ.get("LLAMACPP_PORT", 8001))
    host = "0.0.0.0"
    print(f"Starting llama.cpp server on {host}:{port}", file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="info")
