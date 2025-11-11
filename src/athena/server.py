#!/usr/bin/env python3
"""Athena Memory System Server - HTTP wrapper for MCP."""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point - starts HTTP server with async database initialization."""
    import uvicorn
    from .http.server import AthenaHTTPServer
    from .core.database_postgres import PostgresDatabase

    # PostgreSQL configuration from environment or defaults
    db_host = os.getenv("ATHENA_POSTGRES_HOST", "postgres")
    db_port = int(os.getenv("ATHENA_POSTGRES_PORT", "5432"))
    db_name = os.getenv("ATHENA_POSTGRES_DB", "athena")
    db_user = os.getenv("ATHENA_POSTGRES_USER", "athena")
    db_password = os.getenv("ATHENA_POSTGRES_PASSWORD", "athena_dev")

    # Get server configuration from environment
    host = os.getenv("ATHENA_HOST", "0.0.0.0")
    port = int(os.getenv("ATHENA_PORT", "8000"))
    debug = os.getenv("DEBUG", "0") == "1"

    try:
        # Initialize database
        logger.info(f"Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}")
        db = PostgresDatabase(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
        )

        # Initialize database schema asynchronously
        logger.info("Initializing database schema")
        await db.initialize()
        logger.info("Database initialized successfully")

        # Create and configure HTTP server
        logger.info(f"Starting HTTP server on {host}:{port}")
        http_server = AthenaHTTPServer(host=host, port=port, debug=debug)

        # Setup FastAPI startup/shutdown handlers
        http_server.app.add_event_handler("startup", http_server.startup)
        http_server.app.add_event_handler("shutdown", http_server.shutdown)

        # Create uvicorn config and server (use async API to avoid nested event loops)
        config = uvicorn.Config(
            http_server.app,
            host=host,
            port=port,
            log_level="info",
            reload=debug,
        )
        server = uvicorn.Server(config)

        # Run server in current event loop (don't create a new one)
        logger.info("HTTP server started")
        await server.serve()

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run async initialization then HTTP server
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
