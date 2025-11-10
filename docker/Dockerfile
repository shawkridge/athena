# Dockerfile for Athena Memory MCP System (Phase 3)
# Multi-stage build for production deployment

FROM python:3.13-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Production Stage
# ============================================================================

FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set Python path
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Copy application source
COPY src/ src/
COPY scripts/ scripts/
COPY monitoring/ monitoring/
COPY . .

# Create non-root user
RUN groupadd -r athena && useradd -r -g athena athena
USER athena

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 9000

# Use tini as init process (proper signal handling)
ENTRYPOINT ["/usr/bin/tini", "--"]

# Start memory MCP server
CMD ["python", "-m", "athena.mcp.server"]
