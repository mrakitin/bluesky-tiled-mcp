"""Per-run tools: metadata, stream listing, and data reading."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import fastmcp


def _ts_to_iso(ts) -> Optional[str]:
    """Convert a Unix timestamp float to an ISO-8601 UTC string, or None."""
    if ts is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(float(ts), tz=datetime.timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(ts)


def _convert_timestamps(doc: dict) -> dict:
    """Return a copy of a document with known timestamp fields converted to ISO-8601."""
    out = dict(doc)
    for key in ("time",):
        if key in out:
            out[key] = _ts_to_iso(out[key])
    return out


def register(mcp: "fastmcp.FastMCP", get_client) -> None:
    @mcp.tool()
    def get_run_metadata(uid: str) -> dict:
        """Get the start and stop documents for a run.

        Parameters
        ----------
        uid:
            The run UID (full or unique prefix).
        """
        client = get_client()
        run = _lookup_run(client, uid)
        return {
            "uid": uid,
            "start": _convert_timestamps(dict(run.metadata.get("start", {}))),
            "stop": _convert_timestamps(dict(run.metadata.get("stop", {}))),
        }

    @mcp.tool()
    def list_streams(uid: str) -> list[str]:
        """List available event streams for a run.

        Parameters
        ----------
        uid:
            The run UID (full or unique prefix).
        """
        client = get_client()
        run = _lookup_run(client, uid)
        return list(run.keys())

    @mcp.tool()
    def get_run_data(
        uid: str,
        stream: str = "primary",
        variables: Optional[list[str]] = None,
        max_rows: int = 1000,
    ) -> dict:
        """Read data from an event stream of a run.

        Returns the stream data as a JSON-serialisable dict (xarray Dataset
        converted via ``to_dict()``).  Large arrays are truncated to
        ``max_rows`` rows.

        Parameters
        ----------
        uid:
            The run UID (full or unique prefix).
        stream:
            Stream name to read (default: ``"primary"``).
        variables:
            Optional list of variable names to include.  Omit to return all.
        max_rows:
            Maximum number of rows/events to return (default 1000).
        """
        client = get_client()
        run = _lookup_run(client, uid)

        if stream not in run:
            available = list(run.keys())
            raise KeyError(f"Stream {stream!r} not found. Available: {available}")

        ds = run[stream].read()

        if variables:
            available_vars = set(ds.data_vars) | set(ds.coords)
            selected = [v for v in variables if v in available_vars]
            if selected:
                ds = ds[selected]

        # Truncate to avoid sending huge payloads
        if ds.dims:
            first_dim = list(ds.dims)[0]
            size = ds.dims[first_dim]
            if size > max_rows:
                ds = ds.isel({first_dim: slice(0, max_rows)})

        return _dataset_to_dict(ds)


def _lookup_run(client, uid: str):
    """Look up a run by full UID or unique prefix."""
    # Try exact match first
    if uid in client:
        return client[uid]
    # Try prefix scan
    matches = [k for k in client.keys() if k.startswith(uid)]
    if len(matches) == 1:
        return client[matches[0]]
    if len(matches) > 1:
        raise KeyError(f"UID prefix {uid!r} is ambiguous — {len(matches)} matches found.")
    raise KeyError(f"Run with UID {uid!r} not found in catalog.")


def _dataset_to_dict(ds) -> dict:
    """Convert an xarray Dataset to a JSON-serialisable dict."""
    import numpy as np

    def _convert(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if hasattr(value, "values"):  # xarray DataArray
            return value.values.tolist()
        return value

    result: dict = {
        "dims": dict(ds.dims),
        "coords": {},
        "data_vars": {},
        "attrs": dict(ds.attrs),
    }
    for name, coord in ds.coords.items():
        result["coords"][str(name)] = {
            "dims": list(coord.dims),
            "data": _convert(coord),
            "attrs": dict(coord.attrs),
        }
    for name, var in ds.data_vars.items():
        result["data_vars"][str(name)] = {
            "dims": list(var.dims),
            "data": _convert(var),
            "attrs": dict(var.attrs),
        }
    return result
