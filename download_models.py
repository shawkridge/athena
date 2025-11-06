#!/usr/bin/env python3
"""
Download GGUF models for Athena (llama.cpp optimized)

Models:
- nomic-embed-text-v2-moe (Q6_K, 397 MB) - Embedding model
- DeepSeek-R1-Distill-Qwen-7B (Q4_K_M, 4.68 GB) - LLM
"""

import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_header(text):
    print(f"{BLUE}{'='*44}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'='*44}{NC}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def print_error(text):
    print(f"{RED}✗ {text}{NC}")

def print_info(text):
    print(f"{YELLOW}{text}{NC}")

def main():
    print_header("Athena Model Downloader (llama.cpp)")

    # Configuration
    models_dir = Path.home() / ".athena" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    models = [
        {
            "repo": "nomic-ai/nomic-embed-text-v2-moe-GGUF",
            "filename": "nomic-embed-text-v2-moe.Q6_K.gguf",
            "size": "397 MB",
            "description": "Embedding model"
        },
        {
            "repo": "bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF",
            "filename": "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
            "size": "4.68 GB",
            "description": "LLM"
        }
    ]

    print_info("Configuration:")
    print(f"  Models directory: {models_dir}")
    print(f"  Total models: {len(models)}")
    print(f"  {GREEN}Total size: ~5.1 GB{NC}\n")

    # Download models
    for model in models:
        model_path = models_dir / model["filename"]

        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print_success(f"{model['filename']} ({size_mb:.1f} MB)")
            print(f"  Path: {model_path}")
        else:
            print_info(f"Downloading {model['description']} ({model['size']})...")
            print(f"  From: {model['repo']}")

            try:
                file_path = hf_hub_download(
                    repo_id=model["repo"],
                    filename=model["filename"],
                    local_dir=str(models_dir),
                    local_dir_use_symlinks=False
                )

                size_mb = Path(file_path).stat().st_size / (1024 * 1024)
                print_success(f"{model['filename']} ({size_mb:.1f} MB)")
                print(f"  Path: {file_path}\n")
            except Exception as e:
                print_error(f"Failed to download {model['filename']}")
                print(f"  Error: {str(e)}\n")
                return False

    # Verify files
    print("\n" + BLUE + "="*44 + NC)
    print(f"{GREEN}✓ Model download complete!{NC}")
    print(BLUE + "="*44 + NC + "\n")

    print_info("Next steps:")
    print(f"  1. Install llama-cpp-python:")
    print(f"     {BLUE}pip install llama-cpp-python{NC}\n")
    print(f"  2. Set environment variables (optional):")
    print(f"     {BLUE}export EMBEDDING_PROVIDER=llamacpp{NC}")
    print(f"     {BLUE}export LLM_PROVIDER=llamacpp{NC}\n")
    print(f"  3. Start Athena:")
    print(f"     {BLUE}docker-compose up -d{NC}\n")
    print_info(f"Models will be automatically detected at: {models_dir}\n")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
