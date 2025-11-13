"""Entry point for running Athena MCP daemon.

Usage:
    python -m athena.mcp           # Run daemon with stdio transport
    python -m athena.mcp --help    # Show options
"""

import sys
from .server_daemon import main

if __name__ == "__main__":
    main()
