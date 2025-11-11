#!/bin/bash
# Start both Athena MCP server and llamacpp server

set -e

echo "Starting Athena services..."

# Start llamacpp server in the background
echo "Starting llamacpp embeddings server on port 8001..."
python /app/llamacpp_server.py &
LLAMACPP_PID=$!

# Give llamacpp a moment to start
sleep 2

# Start Athena MCP server in the foreground
echo "Starting Athena MCP server on port 8000..."
exec python -m athena.server
