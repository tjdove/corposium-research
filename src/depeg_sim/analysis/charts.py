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

import hashlib
import io
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


# -- validation overlay (Story 2.5) ----------------------------------------------------

VALIDATION_OVERLAY = "validation_overlay.png"
BPS = 10_000


def _band(config: dict) -> float:
    """Recovery band as a fraction: the scenario's ``peg_recovered.tolerance`` if armed,
    else the ADR-0013 rule ``fee + arbitrageur min profit + 10 bps``."""
    rec = config["termination"].get("peg_recovered")
    if rec is not None:
        return rec["tolerance"]
    arb = next((a for a in config["agents"] if a["type"] == "arbitrageur"), None)
    min_profit = 0 if arb is None else arb["min_profit_bps"]
    return (config["amm"]["fee_bps"] + min_profit + 10) / BPS


def _last_outside(hours: pd.Series, dev: pd.Series, band: float) -> tuple[float | None, bool]:
    """Time of the last point outside ``band`` and whether it is the series' last point
    (i.e. the price never re-entered the band for good: censored)."""
    outside = dev.abs() > band
    if not outside.any():
        return None, False
    i = outside[outside].index[-1]
    return float(hours.loc[i]), i == dev.index[-1]


def _first_inside_after(hours: pd.Series, dev: pd.Series, band: float, t0: float) -> float | None:
    hit = hours[(hours >= t0) & (dev.abs() <= band)]
    return None if hit.empty else float(hit.iloc[0])


def validation_comparison(run_dir: Path) -> dict:
    """Observed (the CSV named in the manifest, re-read; hourly closes) vs simulated (AMM
    spot) numbers for ``docs/calibration/VALIDATION.md``. Hours are from the series
    start. Raises ``ValueError`` if the run has no series or the file changed since."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    config = manifest["config"]
    path = config["environment"].get("price_series_path")
    if path is None:
        raise ValueError(f"{run_dir} has no environment.price_series_path")
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest.get("price_series_sha256"):
        raise ValueError(f"{path} changed since the run (sha256 differs from the manifest)")
    obs = pd.read_csv(io.BytesIO(raw))
    obs_h = (obs["unix"] - obs["unix"].iloc[0]) / 3600
    obs_dev = obs["close"] / config["redemption"]["peg_price"] - 1
    sim = pd.read_parquet(run_dir / TIMESERIES)
    sim_h = sim["elapsed_seconds"] / 3600
    sim_dev = sim["peg_deviation"]
    band = _band(config)
    interval = config["steps"]["interval_seconds"]
    schedule = config["redemption"].get("capacity_schedule") or []
    cap_h = schedule[0]["step"] * interval / 3600 if schedule else None
    attacker = next((a for a in config["agents"] if a["type"] == "attacker"), None)
    oi, si = int(obs_dev.idxmin()), int(sim_dev.idxmin())
    obs_last, obs_cens = _last_outside(obs_h, obs_dev, band)
    sim_last, sim_cens = _last_outside(sim_h, sim_dev, band)
    out = {
        "band_bps": band * BPS,
        "attack_start_h": None if attacker is None else attacker["start_step"] * interval / 3600,
        "capacity_change_h": cap_h,
        "observed_trough_bps": float(obs_dev.loc[oi]) * BPS,
        "observed_trough_h": float(obs_h.loc[oi]),
        "simulated_trough_bps": float(sim_dev.loc[si]) * BPS,
        "simulated_trough_h": float(sim_h.loc[si]),
        "observed_last_outside_band_h": obs_last,
        "observed_last_outside_censored": bool(obs_cens),
        "simulated_last_outside_band_h": sim_last,
        "simulated_last_outside_censored": bool(sim_cens),
        "observed_end_h": float(obs_h.iloc[-1]),
        "simulated_end_h": float(sim_h.iloc[-1]),
    }
    if cap_h is not None:
        at = lambda h, d, t: float(d[h <= t].iloc[-1]) * BPS  # noqa: E731
        out |= {
            "observed_at_capacity_change_bps": at(obs_h, obs_dev, cap_h),
            "simulated_at_capacity_change_bps": at(sim_h, sim_dev, cap_h),
            "observed_first_in_band_after_change_h": _first_inside_after(
                obs_h, obs_dev, band, cap_h
            ),
            "simulated_first_in_band_after_change_h": _first_inside_after(
                sim_h, sim_dev, band, cap_h
            ),
        }
    return out


def plot_validation_overlay(run_dir: Path) -> Path:
    """One panel: observed reference (the manifest's CSV, re-read) and simulated AMM
    price, both in bps from peg, x in elapsed hours from the series start."""
    run_dir = Path(run_dir)
    cmp = validation_comparison(run_dir)
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    config = manifest["config"]
    obs = pd.read_csv(config["environment"]["price_series_path"])
    obs_h = (obs["unix"] - obs["unix"].iloc[0]) / 3600
    sim = pd.read_parquet(run_dir / TIMESERIES)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150, constrained_layout=True)
    band = cmp["band_bps"]
    ax.axhspan(-band, band, color=BAND, alpha=0.6, lw=0, label=f"ADR-0013 band ±{band:g} bps")
    ax.axhline(0, color=GREY, lw=0.8, ls="--")
    peg = config["redemption"]["peg_price"]
    ax.plot(
        obs_h,
        (obs["close"] / peg - 1) * BPS,
        color=BLUE,
        lw=1.4,
        marker=".",
        ms=3,
        label="observed USDC/USD (hourly close)",
    )
    ax.plot(
        sim["elapsed_seconds"] / 3600,
        sim["peg_deviation"] * BPS,
        color=DARK,
        lw=1.4,
        label="simulated AMM price",
    )
    markers = (
        (cmp["attack_start_h"], "attack starts", -4, "right"),
        (cmp["capacity_change_h"], "redemption capacity changes", 4, "left"),
    )
    for x, text, dx, ha in markers:
        if x is not None:
            ax.axvline(x, color=GREY, lw=1.0, ls=":")
            ax.annotate(
                text,
                xy=(x, 0.45),
                xycoords=("data", "axes fraction"),
                xytext=(dx, 0),
                textcoords="offset points",
                fontsize=8,
                color=GREY,
                ha=ha,
            )
    for who, color, dy in (("observed", BLUE, -30), ("simulated", DARK, 8)):
        h, v = cmp[f"{who}_trough_h"], cmp[f"{who}_trough_bps"]
        ax.annotate(
            f"{who} trough {v:,.0f} bps at {h:.1f} h",
            xy=(h, v),
            xytext=(40, dy),
            textcoords="offset points",
            fontsize=8,
            color=color,
            arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
        )
    ax.set_xlabel("elapsed time from series start (hours)")
    ax.set_ylabel("deviation from peg (bps)")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        f"{manifest['scenario_name']} (seed {manifest['seed']}): observed vs simulated", fontsize=11
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
    out = run_dir / VALIDATION_OVERLAY
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
