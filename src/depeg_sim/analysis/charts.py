"""Charts. Rendered headless (Agg) from a run directory alone.

House conventions, for every chart this project publishes:

- 10x6 in, 150 dpi, ``constrained_layout=True``.
- x-axis in elapsed **minutes**.
- Deviation in **bps**; dashed zero line; recovery tolerance as a light band.
- Event markers: attacker start is one vertical line; defender buys are short ticks
  along the top of the deviation panel, not full-height lines.
- One dark line for deviation; distinct, colour-blind-safe colours (blue/orange) for
  the two reserve lines, with a legend. No red/green semantic colouring.
- Footer ``scenario=<name> seed=<seed> hash=<12>`` in small monospace.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from depeg_sim.experiments.writer import EVENTS, MANIFEST, TIMESERIES  # noqa: E402

PEG_TRAJECTORY = "peg_trajectory.png"
DARK = "#222222"
BLUE = "#1f77b4"
ORANGE = "#e08214"
GREY = "#666666"
BAND = "#d9d9d9"


def _first_agent_id(config: dict, agent_type: str) -> str | None:
    return next((a["id"] for a in config["agents"] if a["type"] == agent_type), None)


def _swap_steps(run_dir: Path, source: str | None, side: str) -> list[int]:
    steps = []
    if source is None:
        return steps
    with open(run_dir / EVENTS, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if (
                e["kind"] == "swap_executed"
                and e["payload"]["source"] == source
                and e["payload"]["side"] == side
            ):
                steps.append(e["step"])
    return steps


def plot_peg_trajectory(run_dir: Path) -> Path:
    """Two stacked panels: peg deviation (bps) over reserve levels, x in minutes."""
    run_dir = Path(run_dir)
    df = pd.read_parquet(run_dir / TIMESERIES)
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    config = manifest["config"]
    interval = config["steps"]["interval_seconds"]
    minutes = df["elapsed_seconds"] / 60

    attack = _swap_steps(run_dir, _first_agent_id(config, "attacker"), "sell_stable")
    buys = _swap_steps(run_dir, _first_agent_id(config, "defender"), "buy_stable")

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10, 6), dpi=150, sharex=True, constrained_layout=True
    )

    rec = config["termination"].get("peg_recovered")
    if rec is not None:
        tol = rec["tolerance"] * 10_000
        top.axhspan(-tol, tol, color=BAND, alpha=0.6, lw=0, label=f"recovery band ±{tol:g} bps")
    top.axhline(0, color=GREY, lw=0.8, ls="--")
    top.plot(minutes, df["peg_deviation"] * 10_000, color=DARK, lw=1.4, label="AMM peg deviation")
    if attack:
        x = attack[0] * interval / 60
        for ax in (top, bottom):
            ax.axvline(x, color=GREY, lw=1.0, ls=":")
        top.annotate(
            "attack starts",
            xy=(x, 0.03),
            xycoords=("data", "axes fraction"),
            xytext=(4, 0),
            textcoords="offset points",
            fontsize=8,
            color=GREY,
        )
    if buys:
        top.vlines(
            [s * interval / 60 for s in buys],
            0.92,
            1.0,
            transform=top.get_xaxis_transform(),
            color=ORANGE,
            lw=1.2,
            label="defender buy",
        )
    top.set_ylabel("deviation from peg (bps)")
    top.legend(loc="lower right", fontsize=8, frameon=False)

    bottom.plot(minutes, df["redemption_reserves"], color=BLUE, lw=1.4, label="redemption reserves")
    bottom.plot(minutes, df["defender_reference"], color=ORANGE, lw=1.4, label="defender budget")
    bottom.set_ylabel("reference units")
    bottom.set_xlabel("elapsed time (minutes)")
    bottom.legend(loc="best", fontsize=8, frameon=False)
    bottom.ticklabel_format(axis="y", style="plain")

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    fig.suptitle(
        f"{manifest['scenario_name']} (seed {manifest['seed']}): "
        f"peg deviation and reserves — ended by {summary['terminated_by']}",
        fontsize=11,
    )
    fig.text(
        0.995,
        0.002,
        f"scenario={manifest['scenario_name']} seed={manifest['seed']} "
        f"hash={manifest['scenario_hash'][:12]}",
        ha="right",
        va="bottom",
        fontsize=7,
        family="monospace",
        color=GREY,
    )
    for ax in (top, bottom):
        ax.spines[["top", "right"]].set_visible(False)

    out = run_dir / PEG_TRAJECTORY
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
