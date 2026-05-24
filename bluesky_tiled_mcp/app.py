"""
Module-level FastMCP app for use with ``fastmcp dev inspector`` and similar tools.

Reads connection settings from environment variables (all optional):

  TILED_URI        Tiled server URI (default: http://localhost:8000)
  TILED_API_KEY    API key for authenticated Tiled servers (default: not set)

Usage with the inspector::

    fastmcp dev inspector bluesky_queueserver/tiled_mcp_server/app.py

Or with environment overrides::

    TILED_URI=http://myserver:8000 fastmcp dev inspector bluesky_queueserver/tiled_mcp_server/app.py
"""

from __future__ import annotations

import os

from bluesky_tiled_mcp.server import create_server

_tiled_uri = os.environ.get("TILED_URI", "http://localhost:8000")
_tiled_api_key = os.environ.get("TILED_API_KEY", None)

_client_cache: list = []


def _get_client():
    if _client_cache:
        return _client_cache[0]

    from tiled.client import from_uri

    client = from_uri(_tiled_uri, api_key=_tiled_api_key)
    _client_cache.append(client)
    return client


# Module-level FastMCP instance — discovered automatically by fastmcp tools
mcp = create_server(_get_client)
