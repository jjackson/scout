"""
Scout MCP Server.

Database access layer for the Scout agent, exposed via the Model Context
Protocol. This is a standalone service — no Django dependency.

Usage:
    # stdio transport (for local clients)
    python -m mcp_server

    # HTTP transport (for networked clients)
    python -m mcp_server --transport streamable-http

    # Specify host/port for HTTP
    python -m mcp_server --transport streamable-http --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("scout")


# --- Tools will be registered here as the service is built out ---


@mcp.tool()
def execute_sql(query: str) -> dict:
    """Execute a read-only SQL query against the project database.

    Args:
        query: A SQL SELECT query to execute.

    Returns:
        A dict with columns, rows, row_count, and error (null on success).
    """
    raise NotImplementedError


@mcp.tool()
def get_schema() -> dict:
    """Return the database schema (tables, columns, types, relationships).

    Returns:
        A dict describing all tables and their columns.
    """
    raise NotImplementedError


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,  # never write to stdout with stdio transport
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scout MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8100, help="HTTP port (default: 8100)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    _configure_logging(args.verbose)

    logger.info("Starting Scout MCP server (transport=%s)", args.transport)

    kwargs: dict = {"transport": args.transport}
    if args.transport == "streamable-http":
        kwargs["host"] = args.host
        kwargs["port"] = args.port

    mcp.run(**kwargs)


if __name__ == "__main__":
    main()
