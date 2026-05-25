"""Natural-language tool-selection tests for bluesky-tiled-mcp.

Each test sends a natural-language prompt to an Ollama-hosted LLM with the
MCP server tools available (via the OpenAI tool-use API) and asserts that the
LLM chose the correct tool.  The LLM's prose reply is not evaluated.

Requirements
------------
- Ollama running with ``llama3.2:1b`` (or the model set via ``OLLAMA_MODEL``)
- ``bluesky-tiled-mcp-server`` on PATH
- Tiled server running at ``TILED_URI`` (default: http://localhost:8765)
- Tests are automatically skipped when Ollama is unreachable
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
TILED_URI = os.environ.get("TILED_URI", "http://localhost:8765")


def _ollama_available() -> bool:
    try:
        import httpx

        r = httpx.get(OLLAMA_BASE_URL.replace("/v1", ""), timeout=3.0)
        return r.status_code < 500
    except Exception:
        return False


skip_no_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason=f"Ollama not running at {OLLAMA_BASE_URL}",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_mcp_tools_as_openai_schema() -> list[dict]:
    """Start the MCP server and return its tools in OpenAI function-call format."""
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    transport = StdioTransport(
        command="bluesky-tiled-mcp-server",
        args=["--tiled-uri", TILED_URI],
    )
    async with Client(transport) as client:
        tools = await client.list_tools()

    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools. "
    "You MUST always call one of the available tools to fulfill the user's request. "
    "Never respond in plain text — always invoke a tool."
)


async def _ask_llm(prompt: str, tools: list[dict]) -> Optional[str]:
    """Send *prompt* to Ollama with *tools* and return the first tool name called."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    response = await client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=tools,
        tool_choice="required",
    )
    choice = response.choices[0]
    tool_calls = getattr(choice.message, "tool_calls", None)
    if tool_calls:
        return tool_calls[0].function.name
    return None


# ---------------------------------------------------------------------------
# NL tests
# ---------------------------------------------------------------------------

_TOOLS: list[dict] = []  # populated once per session


@pytest.fixture(scope="session", autouse=True)
def _load_tools():
    global _TOOLS
    loop = asyncio.new_event_loop()
    try:
        _TOOLS = loop.run_until_complete(_get_mcp_tools_as_openai_schema())
    finally:
        loop.close()


@skip_no_ollama
async def test_nl_list_runs():
    """'List the recent runs' → list_runs."""
    tool = await _ask_llm("List the most recent experimental runs.", _TOOLS)
    assert tool == "list_runs", f"Unexpected tool: {tool!r}"


@skip_no_ollama
async def test_nl_search_runs():
    """'Find all count scans' → search_runs."""
    tool = await _ask_llm("Find all runs that used the count plan.", _TOOLS)
    assert tool == "search_runs", f"Unexpected tool: {tool!r}"


@skip_no_ollama
async def test_nl_get_run_metadata():
    """'Show me the metadata for a run' → get_run_metadata."""
    tool = await _ask_llm(
        "Show me the start and stop metadata for run abc123.", _TOOLS
    )
    assert tool == "get_run_metadata", f"Unexpected tool: {tool!r}"


@skip_no_ollama
async def test_nl_list_streams():
    """'What data streams are available?' → list_streams."""
    tool = await _ask_llm(
        "What event streams are available in run abc123?", _TOOLS
    )
    assert tool == "list_streams", f"Unexpected tool: {tool!r}"


@skip_no_ollama
async def test_nl_plot_run():
    """'Plot the data for a run' → plot_run."""
    tool = await _ask_llm(
        "Plot the primary stream data for the most recent run.", _TOOLS
    )
    assert tool == "plot_run", f"Unexpected tool: {tool!r}"
