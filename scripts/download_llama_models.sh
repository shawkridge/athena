#!/bin/bash
# Download GGUF models for Athena (llama.cpp optimized)
#
# Models:
# - nomic-embed-text-v2-moe (Q6_K, 397 MB) - Embedding model
# - DeepSeek-R1-Distill-Qwen-7B (Q4_K_M, 4.68 GB) - LLM

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Athena Model Downloader (llama.cpp)${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Configuration
MODELS_DIR="${HOME}/.athena/models"
EMBEDDING_MODEL="nomic-embed-text-v2-moe.Q6_K.gguf"
LLM_MODEL="DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf"

# HuggingFace repositories
EMBEDDING_REPO="nomic-ai/nomic-embed-text-v2-moe-GGUF"
LLM_REPO="bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF"

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Models directory: ${MODELS_DIR}"
echo -e "  Embedding model:  ${EMBEDDING_MODEL} (397 MB)"
echo -e "  LLM model:        ${LLM_MODEL} (4.68 GB)"
echo -e "  ${GREEN}Total size: ~5.1 GB${NC}"
echo ""

# Check if huggingface-cli is installed
if ! command -v huggingface-cli &> /dev/null; then
    echo -e "${RED}Error: huggingface-cli not found${NC}"
    echo -e "${YELLOW}Installing huggingface_hub...${NC}"
    pip install -U huggingface_hub
fi

# Create models directory
mkdir -p "${MODELS_DIR}"
cd "${MODELS_DIR}"

echo -e "${BLUE}Downloading models to: ${MODELS_DIR}${NC}"
echo ""

# Download embedding model
EMBEDDING_PATH="${MODELS_DIR}/${EMBEDDING_MODEL}"
if [ -f "${EMBEDDING_PATH}" ]; then
    echo -e "${GREEN}✓ Embedding model already exists: ${EMBEDDING_MODEL}${NC}"
else
    echo -e "${YELLOW}Downloading embedding model (397 MB)...${NC}"
    huggingface-cli download "${EMBEDDING_REPO}" \
        "${EMBEDDING_MODEL}" \
        --local-dir . \
        --local-dir-use-symlinks False

    if [ -f "${EMBEDDING_PATH}" ]; then
        echo -e "${GREEN}✓ Embedding model downloaded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to download embedding model${NC}"
        exit 1
    fi
fi
echo ""

# Download LLM model
LLM_PATH="${MODELS_DIR}/${LLM_MODEL}"
if [ -f "${LLM_PATH}" ]; then
    echo -e "${GREEN}✓ LLM model already exists: ${LLM_MODEL}${NC}"
else
    echo -e "${YELLOW}Downloading LLM model (4.68 GB)...${NC}"
    echo -e "${YELLOW}This may take several minutes depending on your connection${NC}"
    huggingface-cli download "${LLM_REPO}" \
        "${LLM_MODEL}" \
        --local-dir . \
        --local-dir-use-symlinks False

    if [ -f "${LLM_PATH}" ]; then
        echo -e "${GREEN}✓ LLM model downloaded successfully${NC}"
    else
        echo -e "${RED}✗ Failed to download LLM model${NC}"
        exit 1
    fi
fi
echo ""

# Verify files
echo -e "${BLUE}Verifying downloaded models...${NC}"
echo ""

if [ -f "${EMBEDDING_PATH}" ]; then
    EMBED_SIZE=$(du -h "${EMBEDDING_PATH}" | cut -f1)
    echo -e "${GREEN}✓ ${EMBEDDING_MODEL}${NC}"
    echo -e "  Size: ${EMBED_SIZE}"
    echo -e "  Path: ${EMBEDDING_PATH}"
else
    echo -e "${RED}✗ ${EMBEDDING_MODEL} not found${NC}"
fi
echo ""

if [ -f "${LLM_PATH}" ]; then
    LLM_SIZE=$(du -h "${LLM_PATH}" | cut -f1)
    echo -e "${GREEN}✓ ${LLM_MODEL}${NC}"
    echo -e "  Size: ${LLM_SIZE}"
    echo -e "  Path: ${LLM_PATH}"
else
    echo -e "${RED}✗ ${LLM_MODEL} not found${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}✓ Model download complete!${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Install llama-cpp-python:"
echo -e "     ${BLUE}pip install llama-cpp-python${NC}"
echo ""
echo -e "  2. Set environment variables (optional):"
echo -e "     ${BLUE}export EMBEDDING_PROVIDER=llamacpp${NC}"
echo -e "     ${BLUE}export LLM_PROVIDER=llamacpp${NC}"
echo ""
echo -e "  3. Start Athena:"
echo -e "     ${BLUE}docker-compose up -d${NC}"
echo ""
echo -e "${YELLOW}Models will be automatically detected at:${NC}"
echo -e "  ${MODELS_DIR}"
echo ""
