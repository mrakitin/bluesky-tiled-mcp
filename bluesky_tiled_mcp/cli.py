"""Command-line entry point for the Tiled MCP server.

Run with::

    bluesky-tiled-mcp-server [options]

The server communicates with AI clients (Copilot, Claude Desktop, etc.) via
stdio using the Model Context Protocol (MCP).
"""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bluesky-tiled-mcp-server",
        description=(
            "MCP server for a Tiled catalog. "
            "Exposes Bluesky runs as MCP tools and resources over stdio."
        ),
    )
    parser.add_argument(
        "--tiled-uri",
        default="http://localhost:8000",
        metavar="URI",
        help="Base URI of the Tiled server (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--tiled-api-key",
        default=None,
        metavar="KEY",
        help="API key for authenticated Tiled servers (omit for public servers).",
    )
    return parser


def _make_get_client(args: argparse.Namespace):
    """Return a factory that lazily creates and caches a Tiled catalog client."""
    _cache: list = []

    def get_client():
        if _cache:
            return _cache[0]

        from tiled.client import from_uri

        client = from_uri(args.tiled_uri, api_key=args.tiled_api_key)
        _cache.append(client)
        return client

    return get_client


def main(argv=None) -> None:
    """Entry point for the ``bluesky-tiled-mcp-server`` command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        from bluesky_tiled_mcp.server import create_server
    except ImportError as exc:
        print(
            f"ERROR: Could not import Tiled MCP server dependencies: {exc}\n"
            "Make sure fastmcp and tiled are installed.",
            file=sys.stderr,
        )
        sys.exit(1)

    get_client = _make_get_client(args)
    mcp = create_server(get_client)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
