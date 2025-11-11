#!/bin/bash
# Start both Athena MCP server and llamacpp server

set -e

echo "Starting Athena services..."

# Start llamacpp server in the background
echo "Starting llamacpp embeddings server on port 8001..."
python /app/llamacpp_server.py &
LLAMACPP_PID=$!

# Wait for llamacpp to be ready (with timeout)
echo "Waiting for llamacpp to be ready..."
MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✓ llamacpp is ready"
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
  sleep 1
done

if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
  echo "✗ llamacpp failed to start within timeout"
  kill $LLAMACPP_PID || true
  exit 1
fi

# Start Athena MCP server in the foreground
echo "Starting Athena MCP server on port 8000..."
exec python -m athena.server
