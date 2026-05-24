"""FastMCP application for the Tiled MCP server.

Usage
-----
Instantiate the server by calling :func:`create_server`, passing a callable
``get_client`` that returns a configured Tiled catalog client.  The callable
is invoked on every tool/resource access so the client can be recreated if
the connection is lost.
"""

from __future__ import annotations

from typing import Callable

import fastmcp

from bluesky_tiled_mcp._tools import catalog, plotting, runs


def create_server(get_client: Callable) -> fastmcp.FastMCP:
    """Create and return the configured FastMCP application.

    Parameters
    ----------
    get_client:
        Zero-argument callable that returns a ready-to-use Tiled catalog
        client (a ``BlueskyRun``-aware container from ``tiled.client``).
        Called on every tool or resource invocation.
    """
    mcp = fastmcp.FastMCP(
        name="bluesky-tiled",
        instructions=(
            "Read and visualise Bluesky experimental data from a Tiled catalog server. "
            "Use the available tools to list runs, search by metadata, "
            "inspect run documents, list event streams, read tabular "
            "or array data as JSON, and plot data as PNG images."
        ),
    )

    # --- Tools & Resources ---------------------------------------------------

    catalog.register(mcp, get_client)
    runs.register(mcp, get_client)
    plotting.register(mcp, get_client)

    return mcp
