#!/usr/bin/env python3
"""
Wrapper script to run the Athena memory server with correct database path
"""
import os
import sys
import asyncio

# Set database path before importing anything
os.environ.setdefault('MEMORY_MCP_DB_PATH', '/home/user/.work/athena/memory.db')

# Add source to path
sys.path.insert(0, '/home/user/.work/athena/src')

# Import and run the server
try:
    from athena.server import main
    asyncio.run(main())
except Exception as e:
    # Fallback: try the old memory_mcp module
    print(f"Error loading athena: {e}", file=sys.stderr)
    print("Attempting fallback to memory_mcp...", file=sys.stderr)
    try:
        # Try new Athena location first, then fallback to old location
        athena_src = '/home/user/.work/athena/src'
        if not __import__('os').path.exists(athena_src):
            athena_src = '/home/user/.work/z_old_claude/memory-mcp/src'
        sys.path.insert(0, athena_src)
        from memory_mcp.server import main
        asyncio.run(main())
    except Exception as e2:
        print(f"Failed to load memory_mcp: {e2}", file=sys.stderr)
        raise
