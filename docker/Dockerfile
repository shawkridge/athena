# Dockerfile for Athena Memory MCP System (Phase 3)
# Multi-stage build for production deployment

FROM python:3.13-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install all Python dependencies to system site-packages
# (not --user to avoid permission issues with non-root user later)
# Note: PostgreSQL only, no SQLite
RUN pip install --no-cache-dir \
    anthropic>=0.7.0 \
    pydantic>=2.0 \
    sqlalchemy>=2.0 \
    psycopg[binary]>=3.1.0 \
    psycopg-pool>=3.1.0 \
    qdrant-client>=1.7.0 \
    numpy>=1.20 \
    scipy>=1.7 \
    scikit-learn>=1.0 \
    mcp>=1.18 \
    fastapi>=0.104 \
    uvicorn>=0.24 \
    httpx>=0.24 \
    ollama>=0.1.0 \
    llama-cpp-python>=0.2.0 \
    huggingface-hub>=0.20.0 \
    pyyaml>=6.0 \
    psutil>=5.0.0

# ============================================================================
# Production Stage
# ============================================================================

FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tini \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python site-packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Install remaining critical packages (in case build didn't complete all)
RUN pip install --no-cache-dir \
    mcp>=1.18 \
    fastapi \
    uvicorn

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Copy application source
COPY src/ src/
COPY scripts/ scripts/
COPY monitoring/ monitoring/
COPY docker/llamacpp_server.py /app/
COPY docker/start_services.sh /app/
COPY . .

# Make startup script executable
RUN chmod +x /app/start_services.sh

# Clean Python cache to avoid bytecode issues
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /app -name "*.pyc" -delete 2>/dev/null; \
    true

# Create non-root user, home directory, and fix permissions
RUN groupadd -r athena && \
    useradd -r -g athena -m -d /home/athena athena && \
    chown -R athena:athena /app && \
    chmod -R u+rwX,g+rX,o-rwx /app && \
    mkdir -p /home/athena/.athena && \
    chown -R athena:athena /home/athena
USER athena

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
# 8000: Athena MCP server
# 8001: llamacpp embeddings server
# 9000: Prometheus metrics
EXPOSE 8000 8001 9000

# Use tini as init process (proper signal handling)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Start both services using startup script
CMD ["/app/start_services.sh"]
