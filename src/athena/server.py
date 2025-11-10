#!/usr/bin/env python3
"""Memory MCP server entry point."""

import asyncio
import sys
from pathlib import Path

from .mcp.handlers import MemoryMCPServer


def get_db_path() -> Path:
    """Get database path from environment or use default.

    Returns:
        Path to database file
    """
    import os

    db_path_env = os.getenv("ATHENA_DB_PATH")
    if db_path_env:
        return Path(db_path_env)

    # Default: ~/.athena/memory.db
    default_path = Path.home() / ".athena" / "memory.db"
    return default_path


async def main():
    """Main entry point."""
    db_path = get_db_path()
    server = MemoryMCPServer(db_path)

    try:
        # Initialize database schema asynchronously
        await server.store.db.initialize()

        # Run MCP server
        await server.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        server.store.close()


if __name__ == "__main__":
    asyncio.run(main())
