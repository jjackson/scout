"""
MCP client for connecting the Scout agent to the MCP data server.

Provides a singleton MultiServerMCPClient that connects to the Scout MCP
server over streamable HTTP and converts MCP tools into LangChain-compatible
tools for use with ToolNode.
"""

from __future__ import annotations

import logging

from django.conf import settings
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

_mcp_client: MultiServerMCPClient | None = None


async def get_mcp_client() -> MultiServerMCPClient:
    """Get or create the MCP client singleton."""
    global _mcp_client
    if _mcp_client is None:
        url = settings.MCP_SERVER_URL
        logger.info("Creating MCP client connecting to %s", url)
        _mcp_client = MultiServerMCPClient(
            {
                "scout-data": {
                    "transport": "streamable_http",
                    "url": url,
                }
            }
        )
    return _mcp_client


async def get_mcp_tools() -> list:
    """Load MCP tools as LangChain tools.

    Returns a list of LangChain-compatible tools that proxy calls to the
    Scout MCP server (query, list_tables, describe_table, get_metadata).
    """
    client = await get_mcp_client()
    tools = await client.get_tools()
    logger.info("Loaded %d MCP tools: %s", len(tools), [t.name for t in tools])
    return tools
