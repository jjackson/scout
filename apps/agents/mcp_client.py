"""
MCP client for connecting the Scout agent to the MCP data server.

Provides a singleton MultiServerMCPClient that connects to the Scout MCP
server over streamable HTTP and converts MCP tools into LangChain-compatible
tools for use with ToolNode.
"""

from __future__ import annotations

import asyncio
import logging
import time

from django.conf import settings
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

_mcp_client: MultiServerMCPClient | None = None
_mcp_lock = asyncio.Lock()

# Circuit breaker state
_consecutive_failures: int = 0
_last_failure_time: float = 0.0
_CIRCUIT_BREAKER_THRESHOLD = 5  # failures before opening circuit
_CIRCUIT_BREAKER_COOLDOWN = 30.0  # seconds before retrying after circuit opens


class MCPServerUnavailable(Exception):
    """Raised when the MCP server is unreachable and the circuit breaker is open."""


async def get_mcp_client() -> MultiServerMCPClient:
    """Get or create the MCP client singleton.

    Thread-safe via asyncio.Lock. Includes circuit breaker logic to avoid
    hammering an unreachable MCP server.
    """
    global _mcp_client, _consecutive_failures, _last_failure_time

    # Check circuit breaker before acquiring lock
    if _consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
        elapsed = time.monotonic() - _last_failure_time
        if elapsed < _CIRCUIT_BREAKER_COOLDOWN:
            raise MCPServerUnavailable(
                f"MCP server circuit breaker open ({_consecutive_failures} consecutive failures). "
                f"Retry in {_CIRCUIT_BREAKER_COOLDOWN - elapsed:.0f}s."
            )
        logger.info("Circuit breaker cooldown elapsed, allowing retry")

    async with _mcp_lock:
        if _mcp_client is not None:
            return _mcp_client

        url = settings.MCP_SERVER_URL
        logger.info("Creating MCP client connecting to %s", url)
        try:
            _mcp_client = MultiServerMCPClient(
                {
                    "scout-data": {
                        "transport": "streamable_http",
                        "url": url,
                    }
                }
            )
            _consecutive_failures = 0
            return _mcp_client
        except Exception:
            _consecutive_failures += 1
            _last_failure_time = time.monotonic()
            logger.error(
                "MCP client creation failed (attempt %d)", _consecutive_failures
            )
            raise


async def get_mcp_tools() -> list:
    """Load MCP tools as LangChain tools.

    Returns a list of LangChain-compatible tools that proxy calls to the
    Scout MCP server (query, list_tables, describe_table, get_metadata).

    Includes circuit breaker: after repeated failures, raises
    MCPServerUnavailable instead of trying again immediately.
    """
    global _mcp_client, _consecutive_failures, _last_failure_time

    try:
        client = await get_mcp_client()
        tools = await client.get_tools()
        logger.info("Loaded %d MCP tools: %s", len(tools), [t.name for t in tools])
        _consecutive_failures = 0
        return tools
    except MCPServerUnavailable:
        raise
    except Exception:
        _consecutive_failures += 1
        _last_failure_time = time.monotonic()
        # Reset client so next attempt creates a fresh one
        _mcp_client = None
        logger.error(
            "MCP tool loading failed (attempt %d)", _consecutive_failures
        )
        raise


def reset_circuit_breaker() -> None:
    """Reset the circuit breaker state. Useful for testing."""
    global _mcp_client, _consecutive_failures, _last_failure_time
    _mcp_client = None
    _consecutive_failures = 0
    _last_failure_time = 0.0
