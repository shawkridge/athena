#!/usr/bin/env python3
"""
Wrapper script to run the Athena memory server with correct database path
"""
import os
import sys
import asyncio

# Set database path before importing anything
os.environ.setdefault('ATHENA_DB_PATH', '/home/user/.athena/memory.db')

# Add source to path for development
sys.path.insert(0, '/home/user/.work/athena/src')

# Import and run the server
from athena.mcp.handlers import MemoryMCPServer

async def main():
    """Start the Athena MCP server"""
    db_path = os.environ.get('ATHENA_DB_PATH', '/home/user/.athena/memory.db')
    server = MemoryMCPServer(db_path=db_path)

    try:
        await server.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        server.store.close()

if __name__ == '__main__':
    asyncio.run(main())
