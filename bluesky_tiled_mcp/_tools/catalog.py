"""Catalog-level tools: list and search runs."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional

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


def _run_summary(uid: str, run) -> dict:
    """Extract a lightweight summary dict from a BlueskyRun client node."""
    start = dict(run.metadata.get("start", {}))
    stop = dict(run.metadata.get("stop", {}))
    return {
        "uid": uid,
        "scan_id": start.get("scan_id"),
        "plan_name": start.get("plan_name"),
        "start_time": _ts_to_iso(start.get("time")),
        "stop_time": _ts_to_iso(stop.get("time")),
        "exit_status": stop.get("exit_status"),
        "num_events": stop.get("num_events"),
    }


def register(mcp: "fastmcp.FastMCP", get_client) -> None:
    @mcp.resource("tiled://catalog/runs")
    def resource_runs() -> list[dict]:
        """Paginated list of runs in the Tiled catalog (first 20)."""
        client = get_client()
        results = []
        for uid, run in list(client.items())[:20]:
            results.append(_run_summary(uid, run))
        return results

    @mcp.tool()
    def list_runs(
        limit: int = 20,
        offset: int = 0,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> list[dict]:
        """List runs in the Tiled catalog.

        Parameters
        ----------
        limit:
            Maximum number of runs to return (default 20).
        offset:
            Number of runs to skip from the most recent (default 0).
        since:
            ISO-8601 datetime string; only include runs started after this time.
        until:
            ISO-8601 datetime string; only include runs started before this time.
        """
        client = get_client()
        items = list(client.items())
        # items are in insertion order; reverse to get newest-first
        items = list(reversed(items))

        since_ts: Optional[float] = None
        until_ts: Optional[float] = None
        if since:
            since_ts = datetime.datetime.fromisoformat(since).timestamp()
        if until:
            until_ts = datetime.datetime.fromisoformat(until).timestamp()

        filtered: list[tuple[str, Any]] = []
        for uid, run in items:
            start_time = run.metadata.get("start", {}).get("time")
            if since_ts is not None and (start_time is None or start_time < since_ts):
                continue
            if until_ts is not None and (start_time is None or start_time > until_ts):
                continue
            filtered.append((uid, run))

        page = filtered[offset : offset + limit]
        return [_run_summary(uid, run) for uid, run in page]

    @mcp.tool()
    def search_runs(
        plan_name: Optional[str] = None,
        scan_id: Optional[int] = None,
        uid_prefix: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search runs by metadata fields.

        Parameters
        ----------
        plan_name:
            Filter to runs with this plan name (substring match).
        scan_id:
            Filter to runs with this exact scan ID.
        uid_prefix:
            Filter to runs whose UID starts with this prefix.
        since:
            ISO-8601 datetime; only runs started after this time.
        until:
            ISO-8601 datetime; only runs started before this time.
        limit:
            Maximum results to return (default 20).
        """
        client = get_client()
        items = list(reversed(list(client.items())))

        since_ts: Optional[float] = None
        until_ts: Optional[float] = None
        if since:
            since_ts = datetime.datetime.fromisoformat(since).timestamp()
        if until:
            until_ts = datetime.datetime.fromisoformat(until).timestamp()

        results = []
        for uid, run in items:
            start = run.metadata.get("start", {})
            if plan_name is not None and plan_name not in str(start.get("plan_name", "")):
                continue
            if scan_id is not None and start.get("scan_id") != scan_id:
                continue
            if uid_prefix is not None and not uid.startswith(uid_prefix):
                continue
            t = start.get("time")
            if since_ts is not None and (t is None or t < since_ts):
                continue
            if until_ts is not None and (t is None or t > until_ts):
                continue
            results.append(_run_summary(uid, run))
            if len(results) >= limit:
                break

        return results
