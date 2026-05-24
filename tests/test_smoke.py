"""Smoke tests for bluesky-tiled-mcp.

Unit tests verify tool registration without any external services.
Integration tests start the real ``bluesky-tiled-mcp-server`` binary via stdio
against a Tiled server and talk to it using ``fastmcp.Client``.

Integration tests require a running Tiled server and are skipped when it is
not available.  In CI, the Tiled server is started before ``pytest`` runs.
"""

from __future__ import annotations

import asyncio
import os

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "list_runs",
    "search_runs",
    "get_run_metadata",
    "list_streams",
    "get_run_data",
    "plot_run",
}

TILED_URI = os.environ.get("TILED_URI", "http://localhost:8765")


def _tiled_available(uri: str = TILED_URI) -> bool:
    """Return True if a Tiled server is responding at ``uri``."""
    try:
        import httpx

        r = httpx.get(uri, timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


skip_no_tiled = pytest.mark.skipif(
    not _tiled_available(),
    reason=f"Tiled server not running at {TILED_URI}",
)


# ---------------------------------------------------------------------------
# Unit tests (no external services needed)
# ---------------------------------------------------------------------------


def test_server_creates():
    """Server can be instantiated with a dummy client factory."""
    from bluesky_tiled_mcp.server import create_server

    mcp = create_server(lambda: None)
    assert mcp is not None


def test_expected_tools_registered():
    """All expected tool names are registered on the server."""
    from bluesky_tiled_mcp.server import create_server

    mcp = create_server(lambda: None)
    tools = asyncio.run(mcp.list_tools())
    registered = {t.name for t in tools}
    missing = EXPECTED_TOOLS - registered
    assert not missing, f"Missing tools: {missing}"


# ---------------------------------------------------------------------------
# Integration tests (require a running Tiled server)
# ---------------------------------------------------------------------------


@skip_no_tiled
async def test_list_tools_via_stdio():
    """MCP server starts and lists the expected tools over stdio."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command="bluesky-tiled-mcp-server",
        args=["--tiled-uri", TILED_URI],
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS.issubset(names)


@skip_no_tiled
async def test_list_runs_empty():
    """``list_runs`` returns a list (empty on a fresh catalog)."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command="bluesky-tiled-mcp-server",
        args=["--tiled-uri", TILED_URI],
    )
    async with Client(transport) as client:
        result = await client.call_tool("list_runs")
        assert not result.is_error
        data = result.data
        assert isinstance(data, list)
        # In CI the catalog is empty; locally it may contain runs
        if data:
            first = data[0]
            assert "uid" in first
            assert "plan_name" in first


@skip_no_tiled
async def test_search_runs_empty():
    """``search_runs`` returns a list (may be empty for unusual plan names)."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command="bluesky-tiled-mcp-server",
        args=["--tiled-uri", TILED_URI],
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "search_runs",
            {"plan_name": "__nonexistent_plan_xyz__"},
        )
        assert not result.is_error
        data = result.data
        assert isinstance(data, list)
        assert data == []
