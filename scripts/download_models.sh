#!/bin/bash
#
# Download GGUF models for llama.cpp servers
#
# Usage:
#   ./scripts/download_models.sh          # Download all models to ~/.athena/models
#   ./scripts/download_models.sh /custom/path  # Download to custom path
#

set -e

# Configuration
MODELS_DIR="${1:-$HOME/.athena/models}"
HUGGINGFACE_MIRROR="${HUGGINGFACE_MIRROR:-https://huggingface.co}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Athena llama.cpp Model Downloader                  ║${NC}"
echo -e "${BLUE}║     Downloads optimized GGUF quantizations             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create models directory
mkdir -p "$MODELS_DIR"
echo -e "${GREEN}✓${NC} Using models directory: ${BLUE}$MODELS_DIR${NC}"
echo ""

# Check for required tools
if ! command -v curl &> /dev/null; then
    echo -e "${RED}✗ Error: curl is required but not installed${NC}"
    exit 1
fi

echo -e "${BLUE}Checking disk space...${NC}"
AVAILABLE_SPACE=$(df "$MODELS_DIR" | awk 'NR==2 {print $4}')
REQUIRED_SPACE=$((3 * 1024 * 1024))  # ~3GB in KB
if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo -e "${RED}✗ Warning: Only ${AVAILABLE_SPACE}KB available, need ~3GB${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo -e "${GREEN}✓${NC} Sufficient disk space available"
echo ""

# Model definitions: (name, url, size_mb, description)
MODELS=(
    "nomic-embed-text-v1.5.Q4_K_M.gguf:nomic-ai/nomic-embed-text-v1.5-GGUF:550:Embedding model (768D, 550MB)"
    "Qwen3-VL-4B-Instruct-Q4_K_M.gguf:Qwen/Qwen3-VL-4B-Instruct-GGUF:2500:Reasoning model (4B, 2.5GB)"
)

# Download function with retry logic
download_model() {
    local filename="$1"
    local repo="$2"
    local size_mb="$3"
    local description="$4"

    local filepath="$MODELS_DIR/$filename"

    if [ -f "$filepath" ]; then
        local actual_size=$(du -m "$filepath" | cut -f1)
        if [ "$actual_size" -ge $((size_mb - 50)) ]; then
            echo -e "${GREEN}✓${NC} ${description}"
            echo -e "  Already exists: ${BLUE}$filepath${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠${NC} ${description}"
            echo -e "  Incomplete download detected, removing..."
            rm -f "$filepath"
        fi
    fi

    echo -e "${BLUE}⇩${NC} Downloading ${description}"
    echo -e "  From: ${BLUE}${repo}${NC}"
    echo -e "  Size: ~${size_mb}MB"

    local url="${HUGGINGFACE_MIRROR}/${repo}/resolve/main/${filename}"

    # Use curl with progress bar and resume capability
    if curl -L \
        --progress-bar \
        --continue-at - \
        --output "$filepath" \
        "$url" 2>&1; then

        # Verify download size
        local actual_size=$(du -m "$filepath" | cut -f1)
        if [ "$actual_size" -ge $((size_mb - 50)) ]; then
            echo -e "${GREEN}✓${NC} Downloaded successfully"
            echo ""
            return 0
        else
            echo -e "${RED}✗${NC} Download incomplete (${actual_size}MB, expected ~${size_mb}MB)"
            rm -f "$filepath"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} Download failed"
        rm -f "$filepath"
        return 1
    fi
}

# Download all models
echo -e "${BLUE}Downloading models...${NC}"
echo ""

FAILED=0
for model_info in "${MODELS[@]}"; do
    IFS=':' read -r filename repo size description <<< "$model_info"

    if ! download_model "$filename" "$repo" "$size" "$description"; then
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All models downloaded successfully!${NC}"
    echo ""
    echo -e "Models directory: ${BLUE}$MODELS_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Start Docker services:"
    echo -e "     ${BLUE}cd docker && docker-compose up -d${NC}"
    echo ""
    echo "  2. Verify servers are healthy:"
    echo -e "     ${BLUE}docker-compose logs -f llamacpp-embeddings${NC}"
    echo -e "     ${BLUE}docker-compose logs -f llamacpp-reasoning${NC}"
    echo ""
    echo "  3. Test embedding server:"
    echo -e "     ${BLUE}curl -X POST http://localhost:8001/embedding -H 'Content-Type: application/json' -d '{\"content\":\"hello world\"}'${NC}"
    echo ""
else
    echo -e "${RED}✗ ${FAILED} model(s) failed to download${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  - Check internet connection"
    echo "  - Verify disk space (need ~3GB)"
    echo "  - Try again later (HuggingFace may be rate limiting)"
    echo "  - Manual download: ${BLUE}https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF${NC}"
    echo -e "                  ${BLUE}https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF${NC}"
    exit 1
fi

echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create summary file
cat > "$MODELS_DIR/README.md" << 'EOF'
# Athena llama.cpp Models

This directory contains GGUF quantized models for local inference.

## Models

### nomic-embed-text-v1.5.Q4_K_M.gguf
- **Purpose**: Generate 768-dimensional semantic embeddings
- **Size**: ~550MB
- **Speed**: ~3,000 tokens/sec on CPU
- **Quality**: MTEB score 62.39 (top 10)
- **Source**: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF

### Qwen3-VL-4B-Instruct-Q4_K_M.gguf
- **Purpose**: Local reasoning for pattern extraction and consolidation
- **Size**: ~2.5GB
- **Speed**: 40-50 tokens/sec on CPU (2x faster than Qwen2.5-7B)
- **Quality**: Best-in-class reasoning for 4B models with vision capabilities
- **Source**: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF

## Usage with llama.cpp

### Embedding Server
```bash
./llama-server \
  -m nomic-embed-text-v1.5.Q4_K_M.gguf \
  --embedding \
  --ctx-size 8192 \
  --port 8001
```

### Reasoning Server
```bash
./llama-server \
  -m qwen2.5-7b-instruct-q4_k_m.gguf \
  --ctx-size 32768 \
  --port 8002
```

## Performance Notes

- **Memory**: ~3GB RAM total (550MB + 2.5GB + overhead)
- **CPU**: 8-12 threads recommended
- **GPU**: Optional (add `--n-gpu-layers 35` for CUDA acceleration)
- **Speed**: 3000 tok/s embedding, 40-50 tok/s reasoning on CPU
- **Benefits**: 40% smaller footprint, 2x faster consolidation

## Alternative Quantizations

If you have different storage/speed requirements:

- **Smaller**: Use Q3_K_S (smaller but lower quality)
- **Larger**: Use Q6_K (larger but higher quality)
- **GPU**: Use Q5_K_M or Q6_K on VRAM-constrained GPUs

Download alternatives from the HuggingFace repositories above.
EOF

echo -e "${GREEN}✓${NC} Created README.md in $MODELS_DIR"
echo ""
