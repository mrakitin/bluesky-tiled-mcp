# bluesky-tiled-mcp

MCP server for [Tiled](https://blueskyproject.io/tiled/) — exposes Bluesky experimental data as [Model Context Protocol](https://modelcontextprotocol.io/) tools so AI agents can list, search, read, and plot scan data.

## Installation

```bash
pip install bluesky-tiled-mcp
```

## Usage

```bash
# Connect to a local Tiled server (no API key — public)
bluesky-tiled-mcp-server

# With API key
bluesky-tiled-mcp-server --tiled-uri http://localhost:8000 --tiled-api-key mykey
```

## LM Studio configuration (`~/.lmstudio/mcp.json`)

```json
{
  "mcpServers": {
    "bluesky-tiled": {
      "command": "bluesky-tiled-mcp-server",
      "args": ["--tiled-uri", "http://localhost:8000"]
    }
  }
}
```

## Available tools

| Tool | Description |
|------|-------------|
| `list_runs` | List runs with pagination and time filters |
| `search_runs` | Filter by `plan_name`, `scan_id`, `uid_prefix`, time range |
| `get_run_metadata` | Start + stop documents for a run |
| `list_streams` | Available event streams (`primary`, `baseline`, …) |
| `get_run_data` | Read a stream as a JSON dict (xarray → dict) |
| `plot_run` | Generate a PNG plot (signals vs. time, stacked subplots) |

## Environment variables (for `fastmcp dev inspector`)

| Variable | Default | Description |
|----------|---------|-------------|
| `TILED_URI` | `http://localhost:8000` | Tiled server URI |
| `TILED_API_KEY` | — | API key (omit for public servers) |
