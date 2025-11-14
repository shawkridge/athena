#!/usr/bin/env python3
"""
llama.cpp HTTP server for text generation (reasoning/completion).
Heavy server for Qwen3-VL model - handles query expansion and reasoning tasks.
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from llama_cpp import Llama

app = FastAPI(title="llama.cpp Reasoning Server", version="0.1.0")

# Load reasoning model (required, fail-fast)
reasoning_model_path = os.environ.get('REASONING_MODEL_PATH',
                                      os.path.expanduser('~/.athena/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf'))
if not os.path.exists(reasoning_model_path):
    raise FileNotFoundError(f"Reasoning model not found at {reasoning_model_path}")

print(f"Loading reasoning model from {reasoning_model_path}...", file=sys.stderr)
REASONING_INSTANCE = Llama(
    model_path=reasoning_model_path,
    n_ctx=2048,  # Context window for generation
    n_threads=int(os.environ.get('LLAMACPP_THREADS', '8')),
    n_gpu_layers=-1  # Use GPU if available
)
print("Reasoning model loaded successfully!", file=sys.stderr)


class CompletionRequest(BaseModel):
    prompt: str
    n_predict: int = 256
    temperature: float = 0.7
    top_p: float = 0.9
    stop: Optional[List[str]] = None


class CompletionResponse(BaseModel):
    content: str
    tokens_predicted: int
    model: str = "Qwen3-VL-4B-Instruct"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": "Qwen3-VL-4B-Instruct",
        "server": "reasoning-only"
    }


@app.post("/completion", response_model=CompletionResponse)
async def generate_completion(request: CompletionRequest):
    """Generate text completion using Qwen3-VL model."""
    try:
        # Configure stop sequences
        stop_sequences = request.stop or ["\n\nUser:", "Human:"]

        # Generate completion
        output = REASONING_INSTANCE(
            prompt=request.prompt,
            max_tokens=request.n_predict,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=stop_sequences
        )

        # Extract results
        generated_text = output["choices"][0]["text"]
        tokens_predicted = output.get("usage", {}).get("completion_tokens", 0)

        return CompletionResponse(
            content=generated_text,
            tokens_predicted=tokens_predicted
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Completion error: {str(e)}")


if __name__ == "__main__":
    port = int(os.environ.get("REASONING_PORT", 8002))
    host = "0.0.0.0"
    print(f"Starting llama.cpp reasoning server on {host}:{port}", file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="info")
