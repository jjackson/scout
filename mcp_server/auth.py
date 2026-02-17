"""Authentication helpers for the MCP server.

Extracts OAuth tokens from MCP request metadata. Tokens are injected
by the Django chat view at the transport layer and are never visible
to the LLM.
"""

from __future__ import annotations

from typing import Any


def extract_oauth_tokens(meta: dict[str, Any] | None) -> dict[str, str]:
    """Extract OAuth tokens from MCP request _meta field.

    Args:
        meta: The _meta dict from an MCP tool call. May be None.

    Returns:
        Dict mapping provider ID to access token string.
        Empty dict if no tokens present.
    """
    if not meta:
        return {}
    return meta.get("oauth_tokens", {})
