"""Plotting tools: generate matplotlib figures from Tiled run data."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import fastmcp

from bluesky_tiled_mcp._tools.runs import _lookup_run


def register(mcp: "fastmcp.FastMCP", get_client) -> None:
    @mcp.tool()
    def plot_run(
        uid: str,
        stream: str = "primary",
        x: Optional[str] = None,
        y: Optional[list[str]] = None,
        title: Optional[str] = None,
    ):
        """Plot signals from a Bluesky run on a single figure, returning a PNG image.

        All 1-D signals are overlaid on the same axes (one line each), with a
        legend — matching the BestEffortCallback style used during live scans.
        2-D signals (detector images) are shown as separate heatmap subplots below.

        The x-axis defaults to ``time`` (relative seconds from run start).  Pass
        ``x`` to use a motor or any other variable instead.

        Parameters
        ----------
        uid:
            Run UID (full or unique prefix).
        stream:
            Event stream to plot (default: ``"primary"``).
        x:
            Variable for the x-axis.  Defaults to ``"time"`` (relative seconds).
            Use ``"seq_num"`` or a motor name if preferred.
        y:
            Variables to plot.  Defaults to all 1-D data variables except
            ``time`` and ``seq_num``.
        title:
            Plot title.  Defaults to ``"<plan_name> — scan_id <id>"``.
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        from fastmcp.utilities.types import Image

        client = get_client()
        run = _lookup_run(client, uid)

        if stream not in run:
            available = list(run.keys())
            raise KeyError(f"Stream {stream!r} not found. Available: {available}")

        ds = run[stream].read()
        all_vars = list(ds.data_vars)

        # --- Resolve x variable -----------------------------------------------
        x_var = x
        if x_var is None:
            # Prefer a real motor (non-time dim coord or data var that looks like a motor)
            candidates = [
                v for v in all_vars
                if v not in ("time", "seq_num")
                and ds[v].ndim == 1
                and v in (ds.coords or {})
            ]
            x_var = candidates[0] if candidates else "time"

        # --- Resolve y variables (1-D signals only) ---------------------------
        exclude = {x_var, "time", "seq_num"}
        if y:
            y_1d = [v for v in y if v in ds.data_vars and ds[v].ndim == 1]
            y_2d = [v for v in y if v in ds.data_vars and ds[v].ndim >= 2]
        else:
            y_1d = [v for v in all_vars if v not in exclude and ds[v].ndim == 1]
            y_2d = [v for v in all_vars if v not in exclude and ds[v].ndim >= 2]

        if not y_1d and not y_2d:
            raise ValueError("No plottable data variables found in this stream.")

        # --- Build x-axis data ------------------------------------------------
        if x_var in ds.data_vars:
            x_data = ds[x_var].values
        elif x_var in ds.coords:
            x_data = ds.coords[x_var].values
        else:
            x_data = np.arange(list(ds.sizes.values())[0] if ds.sizes else 0)

        x_label = x_var
        if x_var == "time" and len(x_data) > 0:
            x_data = x_data - x_data[0]
            x_label = "time (s)"

        # --- Build title ------------------------------------------------------
        start = run.metadata.get("start", {})
        if title is None:
            plan = start.get("plan_name", "run")
            scan_id = start.get("scan_id", "?")
            title = f"{plan} — scan_id {scan_id}"

        # --- Layout: one subplot per 1-D signal, shared x-axis --------------
        n_1d = max(len(y_1d), 1)
        n_rows = n_1d + len(y_2d)
        fig, axes = plt.subplots(
            n_rows, 1,
            figsize=(8, 3 * n_rows),
            sharex=True,
            squeeze=False,
        )
        fig.suptitle(title)

        for i, var_name in enumerate(y_1d):
            ax = axes[i, 0]
            ax.plot(x_data, ds[var_name].values)
            ax.set_ylabel(var_name)
            ax.grid(True, alpha=0.3)

        if not y_1d:
            axes[0, 0].set_visible(False)

        # Bottom-most 1-D axes gets the x label
        axes[n_1d - 1, 0].set_xlabel(x_label)

        for i, var_name in enumerate(y_2d, start=n_1d):
            ax = axes[i, 0]
            im = ax.imshow(
                ds[var_name].values,
                aspect="auto",
                origin="lower",
                interpolation="nearest",
            )
            fig.colorbar(im, ax=ax)
            ax.set_title(var_name)
            dims = list(ds[var_name].dims)
            ax.set_xlabel(dims[1] if len(dims) > 1 else "col")
            ax.set_ylabel(dims[0] if dims else "row")

        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)

        return Image(data=buf.read(), format="png")

