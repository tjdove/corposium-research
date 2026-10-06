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
import itertools
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
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


def _include_texts(fig, ax, texts, pad: float = 0.03) -> None:
    """Lower the y-axis bottom until every text box sits inside the axes (Story 2.9: the
    2.6 overlay clipped the observed-trough label). Offsets are in points, so lowering the
    limit moves the anchor up relative to the axes; two passes settle it."""
    for _ in range(2):
        fig.canvas.draw()
        to_axes = ax.transAxes.inverted()
        lowest = min(to_axes.transform(t.get_window_extent())[0, 1] for t in texts)
        if lowest >= pad:
            return
        lo, hi = ax.get_ylim()
        # bottom at fraction ``lowest`` must move to ``pad``: grow the span accordingly
        ax.set_ylim(lo - (pad - lowest) * (hi - lo) / (1 - pad), hi)


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
    labels = []
    for who, color, dy in (("observed", BLUE, -30), ("simulated", DARK, 8)):
        h, v = cmp[f"{who}_trough_h"], cmp[f"{who}_trough_bps"]
        labels.append(
            ax.annotate(
                f"{who} trough {v:,.0f} bps at {h:.1f} h",
                xy=(h, v),
                xytext=(40, dy),
                textcoords="offset points",
                fontsize=8,
                color=color,
                arrowprops={"arrowstyle": "-", "color": color, "lw": 0.8},
            )
        )
    _include_texts(fig, ax, labels)
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


# -- sweep charts (Story 2.7) ------------------------------------------------------------
#
# Both read only ``mc.parquet`` and the sweep ``manifest.json`` (axes, seeds, the resolved
# ``base_config``; ADR-0014 pattern). Each panel is 10x6 in; footer
# ``sweep=<name> spec_hash=<12> base_hash=<12>``. Categorical series use a validated
# colour-blind-safe order and always carry a distinct marker as well, so identity is never
# colour alone.

THRESHOLD_SURFACE = "threshold_surface.png"
ORACLE_SENSITIVITY = "oracle_sensitivity.png"
USD_PER_UNIT = 234.6  # $ per model unit: 1,000,000 units = $234.6M (SOURCES.md, s)
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4")
MARKERS = ("o", "s", "^", "D", "v")
SEQ_BLUE = ("#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")
DEPTH_PATH = "amm.reserve_stable"
CAPITAL_PATH = "agents[type=attacker].capital"
HEARTBEAT_PATH = "oracle.heartbeat_steps"
THRESHOLD_PATH = "oracle.deviation_threshold_pct"
DODGE = 1.06  # horizontal offset factor between threshold series on the log heartbeat axis


def _read_sweep(sweep_dir: Path) -> tuple[pd.DataFrame, dict]:
    from depeg_sim.experiments.mc import MC_PARQUET
    from depeg_sim.experiments.sweep import SWEEP_MANIFEST

    mc = pd.read_parquet(sweep_dir / MC_PARQUET)
    manifest = json.loads((sweep_dir / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    return mc, manifest


def _axis_named(manifest: dict, path: str) -> str:
    """The column name of the axis that sets ``path``."""
    for axis in manifest["axes"]:
        if path in axis["paths"]:
            return axis["name"]
    raise ValueError(f"sweep {manifest['sweep_name']!r} has no axis setting {path!r}")


def _p_broken(mc: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """``p_stays_broken = 1 - p_peg_recovered`` with Wilson 95% bounds."""
    from depeg_sim.analysis.stats import wilson

    p = 1.0 - mc["p_peg_recovered"]
    k = (p * mc["n"]).round().astype(int)
    bounds = [wilson(int(ki), int(ni)) for ki, ni in zip(k, mc["n"], strict=True)]
    return p, pd.Series([b[0] for b in bounds]), pd.Series([b[1] for b in bounds])


def _usd(units: float, usd_per_unit: float) -> str:
    v = units * usd_per_unit
    return f"${v / 1e9:,.2f}B" if v >= 1e9 else f"${v / 1e6:,.0f}M"


def _criterion(rec: dict) -> str:
    """``peg_recovered.reference`` as the heading names it (absent in pre-2.8 manifests
    means par)."""
    return f"reference={rec.get('reference', 'par')}"


def _against(rec: dict) -> str:
    return "the published oracle price" if rec.get("reference") == "oracle" else "par"


def _sweep_footer(fig, manifest: dict) -> None:
    """``sweep=<name> spec_hash=<12> base_hash=<12>``; ``spec_hash`` (``sweep_spec_hash``,
    the number ``docs/figures/manifest.json`` records) is absent in pre-2.9 manifests."""
    spec = f" spec_hash={manifest['spec_hash'][:12]}" if manifest.get("spec_hash") else ""
    # reserve a bottom strip so the (now longer) footer never overlaps the x label
    fig.get_layout_engine().set(rect=(0, 0.025, 1, 0.975))
    fig.text(
        0.995,
        0.002,
        f"sweep={manifest['sweep_name']}{spec} base_hash={manifest['base_scenario_hash'][:12]}",
        ha="right",
        va="bottom",
        fontsize=7,
        family="monospace",
        color=GREY,
    )


def plot_threshold_surface(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Left: heatmap of ``p_stays_broken`` over pool depth x attacker capital with the 0.5
    contour and each cell's Wilson half-width. Right: ``p_stays_broken`` against the
    absorbed ratio ``capital / (defender_bought + holder_bought + redemption_paid)`` (means
    over seeds), one marker per depth, with one binomial logistic fit through every cell."""
    from matplotlib.colors import LinearSegmentedColormap

    from depeg_sim.analysis.stats import fit_logistic

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    depth_col, cap_col = _axis_named(manifest, DEPTH_PATH), _axis_named(manifest, CAPITAL_PATH)
    d_star = base["amm"]["reserve_stable"]
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    resources = defender["budget"] + base["redemption"]["reserves"]

    mc = mc.sort_values([depth_col, cap_col]).reset_index(drop=True)
    mc["p"], mc["lo"], mc["hi"] = _p_broken(mc)
    absorbed = (
        mc["defender_bought_stable_mean"].fillna(0)
        + mc["holder_bought_stable_mean"].fillna(0)
        + mc["redemption_paid_total_mean"].fillna(0)
    )
    mc["absorbed_ratio"] = mc[cap_col] / absorbed
    depths = sorted(mc[depth_col].unique())
    caps = sorted(mc[cap_col].unique())
    grid = mc.pivot(index=depth_col, columns=cap_col, values="p").loc[depths, caps]
    half = ((mc["hi"] - mc["lo"]) / 2).to_numpy().reshape(len(depths), len(caps))

    fig, (left, right) = plt.subplots(1, 2, figsize=(20, 6), dpi=150, constrained_layout=True)

    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    im = left.imshow(grid.to_numpy(), origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=1)
    if (grid.to_numpy() >= 0.5).any() and (grid.to_numpy() < 0.5).any():
        left.contour(grid.to_numpy(), levels=[0.5], colors=[ORANGE], linewidths=2.0)
    for i in range(len(depths)):
        for j in range(len(caps)):
            v = grid.iat[i, j]
            left.text(
                j,
                i,
                f"{v:.2f}\n±{half[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if v >= 0.55 else DARK,
            )
    left.set_xticks(range(len(caps)))
    left.set_xticklabels(
        [f"{c / resources:.2g}×\n{_usd(c, usd_per_unit)}" for c in caps], fontsize=8
    )
    left.set_yticks(range(len(depths)))
    left.set_yticklabels(
        [f"{d / d_star:.3g}× D*\n{_usd(d, usd_per_unit)}" for d in depths], fontsize=8
    )
    left.set_xlabel("attacker capital (× defender budget + redemption reserves; $)")
    left.set_ylabel("pool depth per side (× D*; $)")
    left.set_title(
        "p(stays broken): heatmap, orange line = 0.5 contour, ± Wilson 95% half-width", fontsize=10
    )
    fig.colorbar(im, ax=left, label="p_stays_broken = 1 − p_peg_recovered", shrink=0.9)

    k = (mc["p"] * mc["n"]).round().astype(int).tolist()
    a, b = fit_logistic(mc["absorbed_ratio"].tolist(), k, mc["n"].astype(int).tolist())
    x50 = -a / b
    for idx, d in enumerate(depths):
        g = mc[mc[depth_col] == d]
        right.errorbar(
            g["absorbed_ratio"],
            g["p"],
            yerr=[g["p"] - g["lo"], g["hi"] - g["p"]],
            fmt=MARKERS[idx % len(MARKERS)],
            ms=7,
            color=SERIES[idx % len(SERIES)],
            ecolor=BAND,
            elinewidth=1.0,
            mec="white",
            mew=0.8,
            label=f"depth {d / d_star:.3g}× D*",
        )
    xs = pd.Series(sorted(mc["absorbed_ratio"]))
    span = xs.iloc[-1] - xs.iloc[0]
    fine = [xs.iloc[0] - 0.05 * span + i * 1.1 * span / 200 for i in range(201)]
    right.plot(
        fine,
        [1 / (1 + math.exp(-(a + b * x))) for x in fine],
        color=DARK,
        lw=1.6,
        label=f"logistic fit, all cells: 0.5 at {x50:.3f}",
    )
    right.axhline(0.5, color=GREY, lw=0.8, ls="--")
    right.axvline(1.0, color=GREY, lw=0.8, ls=":")
    right.set_xlabel(
        "absorbed ratio = capital / (defender bought + holder bought + redemption paid)"
    )
    right.set_ylabel("p_stays_broken")
    right.set_ylim(-0.04, 1.04)
    right.set_title("F-03 collapse test: one curve across depths?", fontsize=10)
    right.legend(loc="upper left", fontsize=8, frameon=False)
    right.spines[["top", "right"]].set_visible(False)

    rec = base["termination"]["peg_recovered"]
    red = base["redemption"]
    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    hours = horizon * base["steps"]["interval_seconds"] / 3600
    deliverable = red["capacity_per_step"] * horizon
    fig.suptitle(
        f"{manifest['sweep_name']}: where the peg stays broken, criterion "
        f"{_criterion(rec)} "
        f"(volatility {base['environment']['volatility_per_step']:g}/step, calm per F-04; "
        f"holder present; {len(manifest['seeds'])} seeds per cell)\n"
        f"stays broken = not back within ±{rec['tolerance'] * BPS:g} bps of "
        f"{_against(rec)} for "
        f"{rec['for_steps']:,} steps by step {horizon:,} ({hours:.0f} h). Not reserve "
        f"exhaustion: redemption can pay only {deliverable / 1e6:.1f}M of "
        f"{red['reserves'] / 1e6:.1f}M reserves within the horizon (F-06).",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / THRESHOLD_SURFACE
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_oracle_sensitivity(sweep_dir: Path) -> Path:
    """Two stacked panels on a shared log heartbeat axis, one line per deviation threshold:
    the trough (``max_depeg_bps`` mean, p05-p95 band; the primary result) and
    ``p_stays_broken`` with Wilson bars and the F-04 floor (the calibrated cell's value: the
    base scenario's own attack at the calibrated oracle). The calibrated cell is ringed."""
    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    hb_col = _axis_named(manifest, HEARTBEAT_PATH)
    th_col = _axis_named(manifest, THRESHOLD_PATH)
    mc = mc.sort_values([th_col, hb_col]).reset_index(drop=True)
    mc["p"], mc["lo"], mc["hi"] = _p_broken(mc)
    cal_hb = base["oracle"]["heartbeat_steps"]
    cal_th = base["oracle"]["deviation_threshold_pct"]
    cal = mc[(mc[hb_col] == cal_hb) & (mc[th_col] == cal_th)]

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10, 12), dpi=150, sharex=True, constrained_layout=True
    )
    thresholds = sorted(mc[th_col].unique())
    for idx, th in enumerate(thresholds):
        g = mc[mc[th_col] == th]
        color, marker = SERIES[idx % len(SERIES)], MARKERS[idx % len(MARKERS)]
        label = f"threshold {th:g}%" + (" (zero lag, ADR-0009)" if th == 0 else "")
        # small multiplicative dodge on the log axis so coincident lines stay visible
        x = g[hb_col] * DODGE ** (idx - (len(thresholds) - 1) / 2)
        for q in ("p05", "p95"):
            top.plot(x, g[f"max_depeg_bps_{q}"], color=color, lw=0.9, ls=":")
        top.plot(x, g["max_depeg_bps_mean"], color=color, marker=marker, ms=7, lw=2, label=label)
        bottom.errorbar(
            x,
            g["p"],
            yerr=[g["p"] - g["lo"], g["hi"] - g["p"]],
            color=color,
            marker=marker,
            ms=7,
            lw=2,
            capsize=3,
            label=label,
        )
    lo_t, hi_t = mc["max_depeg_bps_mean"].min(), mc["max_depeg_bps_mean"].max()
    top.text(
        0.99,
        0.98,
        f"mean trough across all {len(mc)} cells: {lo_t:,.1f} to {hi_t:,.1f} bps "
        f"(range {hi_t - lo_t:.1f} bps); dotted lines = p05 and p95",
        transform=top.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=GREY,
    )
    if not cal.empty:
        c = cal.iloc[0]
        cal_x = cal_hb * DODGE ** (thresholds.index(cal_th) - (len(thresholds) - 1) / 2)
        for ax, y in ((top, c["max_depeg_bps_mean"]), (bottom, c["p"])):
            ax.plot(
                [cal_x],
                [y],
                marker="o",
                ms=16,
                mfc="none",
                mec=DARK,
                mew=1.5,
                ls="none",
                label=f"calibrated cell ({cal_hb}, {cal_th:g}%)",
            )
        bottom.axhline(
            c["p"],
            color=GREY,
            lw=1.0,
            ls="--",
            label=f"F-04 floor {c['p']:.2f}: base attack at the calibrated oracle",
        )
    top.set_xscale("log")
    top.set_ylabel("trough: max_depeg_bps (mean; dotted p05, p95)")
    top.set_title("Trough against oracle heartbeat (primary result)", fontsize=10)
    top.legend(loc="lower left", fontsize=8, frameon=False)
    bottom.set_ylabel("p_stays_broken (Wilson 95%)")
    bottom.set_ylim(-0.04, 1.04)
    interval = base["steps"]["interval_seconds"]
    bottom.set_xlabel(f"oracle heartbeat (steps of {interval} s, log scale)")
    bottom.set_title(
        "p_stays_broken: under stress volatility most seeds never re-enter the band "
        "regardless of the attack (F-04)",
        fontsize=10,
    )
    bottom.legend(loc="lower left", fontsize=8, frameon=False)
    hbs = sorted(mc[hb_col].unique())
    bottom.set_xticks(hbs)
    bottom.set_xticklabels([f"{h:g}\n{h * interval / 60:g} min" for h in hbs], fontsize=8)
    for ax in (top, bottom):
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        f"{manifest['sweep_name']}: does oracle lag matter? "
        f"(volatility {base['environment']['volatility_per_step']:g}/step, "
        f"{len(manifest['seeds'])} seeds per cell)",
        fontsize=11,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / ORACLE_SENSITIVITY
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# -- budget x depth (Story 2.8) -----------------------------------------------------------

BUDGET_DEPTH = "budget_depth.png"
BUDGET_PATH = "agents[type=defender].budget"


def budget_crossing(budgets: list[float], p: list[float]) -> tuple[float | None, str]:
    """Budget at which ``p_stays_broken`` falls through 0.5 as budget rises, by linear
    interpolation between the grid budgets. Returns ``(budget, "crossing")``, or
    ``(None, "below")`` when even the smallest budget holds (p < 0.5 everywhere), or
    ``(None, "above")`` when no budget in the grid holds (p >= 0.5 everywhere)."""
    pairs = sorted(zip(budgets, p, strict=True))
    if all(pi < 0.5 for _, pi in pairs):
        return None, "below"
    for (b0, p0), (b1, p1) in itertools.pairwise(pairs):
        if p0 >= 0.5 > p1:
            return b0 + (0.5 - p0) * (b1 - b0) / (p1 - p0), "crossing"
    return None, "above"


def loglog_slope(points: list[tuple[float, float]]) -> float:
    """Least-squares slope of ``log y`` on ``log x`` through ``(x, y)`` points (>= 2)."""
    lx = [math.log(x) for x, _ in points]
    ly = [math.log(y) for _, y in points]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    return sum((a - mx) * (b - my) for a, b in zip(lx, ly, strict=True)) / sum(
        (a - mx) ** 2 for a in lx
    )


def plot_budget_depth(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Left: heatmap of ``p_stays_broken`` over pool depth x defender budget with the 0.5
    contour. Right: each depth row's 0.5-crossing budget against depth on log-log axes,
    rows whose crossing lies outside the grid drawn as bounds, a slope-1 reference line
    (F-11's hypothesis: the crossing budget scales with depth) and the fitted slope."""
    from matplotlib.colors import LinearSegmentedColormap

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    depth_col, budget_col = _axis_named(manifest, DEPTH_PATH), _axis_named(manifest, BUDGET_PATH)
    d_star = base["amm"]["reserve_stable"]
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    attacker = next(a for a in base["agents"] if a["type"] == "attacker")
    b_cal = defender["budget"]
    resources = b_cal + base["redemption"]["reserves"]
    rec = base["termination"]["peg_recovered"]

    mc = mc.sort_values([depth_col, budget_col]).reset_index(drop=True)
    mc["p"], mc["lo"], mc["hi"] = _p_broken(mc)
    depths = sorted(mc[depth_col].unique())
    budgets = sorted(mc[budget_col].unique())
    grid = mc.pivot(index=depth_col, columns=budget_col, values="p").loc[depths, budgets]
    half = ((mc["hi"] - mc["lo"]) / 2).to_numpy().reshape(len(depths), len(budgets))

    fig, (left, right) = plt.subplots(1, 2, figsize=(20, 6), dpi=150, constrained_layout=True)
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    values = grid.to_numpy()
    im = left.imshow(values, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=1)
    if (values >= 0.5).any() and (values < 0.5).any():
        left.contour(values, levels=[0.5], colors=[ORANGE], linewidths=2.0)
    for i in range(len(depths)):
        for j in range(len(budgets)):
            v = values[i, j]
            left.text(
                j,
                i,
                f"{v:.2f}\n±{half[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if v >= 0.55 else DARK,
            )
    left.set_xticks(range(len(budgets)))
    left.set_xticklabels(
        [f"{b / b_cal:.3g}× budget\n{_usd(b, usd_per_unit)}" for b in budgets], fontsize=8
    )
    left.set_yticks(range(len(depths)))
    left.set_yticklabels(
        [f"{d / d_star:.3g}× D*\n{_usd(d, usd_per_unit)}" for d in depths], fontsize=8
    )
    left.set_xlabel("defender budget (× calibrated budget; $)")
    left.set_ylabel("pool depth per side (× D*; $)")
    left.set_title(
        "p(stays broken): heatmap, orange line = 0.5 contour, ± Wilson 95% half-width",
        fontsize=10,
    )
    fig.colorbar(im, ax=left, label="p_stays_broken = 1 − p_peg_recovered", shrink=0.9)

    points, bounds = [], []
    for d in depths:
        g = mc[mc[depth_col] == d]
        x, kind = budget_crossing(g[budget_col].tolist(), g["p"].tolist())
        if kind == "crossing":
            points.append((d, x))
        else:
            bounds.append((d, budgets[0] if kind == "below" else budgets[-1], kind))
    if points:
        right.plot(
            [d for d, _ in points],
            [x for _, x in points],
            marker="o",
            ms=8,
            color=SERIES[0],
            lw=2,
            label="0.5 crossing budget (linear interpolation)",
        )
    for kind, marker, text in (
        ("below", "v", "not reached: holds at the smallest budget (crossing below)"),
        ("above", "^", "not reached: no budget in the grid holds (crossing above)"),
    ):
        pts = [(d, b) for d, b, k in bounds if k == kind]
        if pts:
            right.plot(
                [d for d, _ in pts],
                [b for _, b in pts],
                ls="none",
                marker=marker,
                ms=10,
                mfc="white",
                mec=SERIES[1],
                mew=1.8,
                label=text,
            )
    if points:
        d0, x0 = points[len(points) // 2]
        right.plot(
            [depths[0], depths[-1]],
            [x0 * depths[0] / d0, x0 * depths[-1] / d0],
            color=GREY,
            ls="--",
            lw=1.2,
            label="slope 1 (budget ∝ depth), through the middle crossing",
        )
    if len(points) >= 2:
        slope = loglog_slope(points)
        right.plot([], [], ls="none", label=f"least-squares log–log slope: {slope:.2f}")
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xticks(depths)
    right.set_xticklabels([f"{d / d_star:.3g}× D*" for d in depths], fontsize=8)
    right.set_yticks(budgets)
    right.set_yticklabels([f"{b / b_cal:.3g}×" for b in budgets], fontsize=8)
    right.minorticks_off()
    right.set_xlabel("pool depth per side (log)")
    right.set_ylabel("defender budget at the 0.5 crossing (× calibrated, log)")
    right.set_title("Does the budget that holds scale with depth? (F-11)", fontsize=10)
    right.legend(loc="upper left", fontsize=8, frameon=False)
    right.spines[["top", "right"]].set_visible(False)

    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    hours = horizon * base["steps"]["interval_seconds"] / 3600
    fig.suptitle(
        f"{manifest['sweep_name']}: defender budget against pool depth, criterion "
        f"{_criterion(rec)} (attacker {attacker['capital'] / resources:.3g}× nominal resources "
        f"= {_usd(attacker['capital'], usd_per_unit)}; volatility "
        f"{base['environment']['volatility_per_step']:g}/step; holder present; "
        f"{len(manifest['seeds'])} seeds per cell)\n"
        f"stays broken = not back within ±{rec['tolerance'] * BPS:g} bps of {_against(rec)} "
        f"for {rec['for_steps']:,} steps by step {horizon:,} ({hours:.0f} h)",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / BUDGET_DEPTH
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# -- time to parity (Story 2.9) -------------------------------------------------------------

TIME_TO_PARITY = "time_to_parity.png"


def _tick_labels(manifest: dict, axis: dict, values: list, usd_per_unit: float) -> list[str]:
    """Tick labels for a sweep axis: depth as × D*, capital as × resources, else raw."""
    base = manifest["base_config"]
    if DEPTH_PATH in axis["paths"]:
        d_star = base["amm"]["reserve_stable"]
        return [f"{v / d_star:.3g}× D*\n{_usd(v, usd_per_unit)}" for v in values]
    if CAPITAL_PATH in axis["paths"]:
        defender = next(a for a in base["agents"] if a["type"] == "defender")
        resources = defender["budget"] + base["redemption"]["reserves"]
        return [f"{v / resources:.2g}×\n{_usd(v, usd_per_unit)}" for v in values]
    return [f"{v:g}" for v in values]


def _axis_label(axis: dict) -> str:
    if DEPTH_PATH in axis["paths"]:
        return "pool depth per side (× D*; $)"
    if CAPITAL_PATH in axis["paths"]:
        return "attacker capital (× defender budget + redemption reserves; $)"
    return axis["name"]


def time_to_parity_hours(mc: pd.DataFrame, interval_seconds: float) -> pd.Series:
    """Median hours from run start to first re-entry per cell:
    ``(step_of_max_depeg + steps_to_first_band_entry) × interval / 3600``.

    ``steps_to_first_band_entry`` is counted from the trough, so the trough step is added
    back. The median of the sum equals the trough step plus the median entry only when the
    trough step is the same for every seed in the cell; raises ``ValueError`` naming the
    cells where it is not. NaN where fewer than half the seeds ever re-enter ("never")."""
    spread = (mc["step_of_max_depeg_p05"] != mc["step_of_max_depeg_p95"]) | (
        mc["step_of_max_depeg_std"].fillna(0) > 0
    )
    if spread.any():
        bad = mc.index[spread].tolist()
        raise ValueError(
            f"trough step differs across seeds in cell rows {bad}: time from run start "
            "cannot be taken as trough step + median steps to first band entry"
        )
    hours = (
        (mc["step_of_max_depeg_p50"] + mc["steps_to_first_band_entry_p50"])
        * interval_seconds
        / 3600
    )
    never = mc["steps_to_first_band_entry_n"] < mc["n"] / 2
    return hours.where(~never)


def plot_time_to_parity(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Heatmap over the sweep's two axes of the median hours from run start to the first
    re-entry into the recovery band (``time_to_parity_hours``). Cells where fewer than half
    the seeds ever re-enter are hatched and labelled "never" (the price is lost). A dashed
    contour marks the latest start that can still hold ``for_steps`` by ``max_steps``:
    finite cells beyond it are lost on the clock. Reads only ``mc.parquet`` + manifest."""
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    if len(manifest["axes"]) != 2:
        raise ValueError(f"sweep {manifest['sweep_name']!r} needs exactly two axes")
    y_axis, x_axis = manifest["axes"]
    y_col, x_col = y_axis["name"], x_axis["name"]
    rec = base["termination"]["peg_recovered"]
    interval = base["steps"]["interval_seconds"]
    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    horizon_h = horizon * interval / 3600
    deadline_h = (horizon - rec["for_steps"]) * interval / 3600

    mc = mc.sort_values([y_col, x_col]).reset_index(drop=True)
    mc["hours"] = time_to_parity_hours(mc, interval)
    ys = sorted(mc[y_col].unique())
    xs = sorted(mc[x_col].unique())
    grid = mc.pivot(index=y_col, columns=x_col, values="hours").loc[ys, xs].to_numpy()
    never = pd.isna(grid)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150, constrained_layout=True)
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=horizon_h)
    # The deadline boundary follows cell edges: a segment wherever a cell that first
    # re-enters before the deadline meets one that re-enters after it or never.
    late = never | (np.nan_to_num(grid, nan=horizon_h) >= deadline_h)
    for i in range(len(ys)):
        for j in range(len(xs)):
            if j + 1 < len(xs) and late[i, j] != late[i, j + 1]:
                ax.plot([j + 0.5] * 2, [i - 0.5, i + 0.5], color=ORANGE, lw=2.2, ls="--")
            if i + 1 < len(ys) and late[i, j] != late[i + 1, j]:
                ax.plot([j - 0.5, j + 0.5], [i + 0.5] * 2, color=ORANGE, lw=2.2, ls="--")
    for i in range(len(ys)):
        for j in range(len(xs)):
            if never[i, j]:
                ax.add_patch(
                    Rectangle(
                        (j - 0.5, i - 0.5),
                        1,
                        1,
                        facecolor="white",
                        edgecolor=GREY,
                        hatch="///",
                        lw=0.0,
                    )
                )
                ax.text(
                    j,
                    i,
                    "never",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=DARK,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0},
                )
                continue
            v = grid[i, j]
            tag = "\nclock" if v >= deadline_h else ""
            ax.text(
                j,
                i,
                f"{v:.1f} h{tag}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if v >= 0.55 * horizon_h else DARK,
            )
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(_tick_labels(manifest, x_axis, xs, usd_per_unit), fontsize=8)
    ax.set_yticks(range(len(ys)))
    ax.set_yticklabels(_tick_labels(manifest, y_axis, ys, usd_per_unit), fontsize=8)
    ax.set_xlabel(_axis_label(x_axis))
    ax.set_ylabel(_axis_label(y_axis))
    ax.set_title(
        f"orange dashed = {deadline_h:.0f} h, the latest first re-entry that can still hold "
        f"{rec['for_steps']:,} steps by step {horizon:,}; hatched = never re-enters",
        fontsize=9,
    )
    fig.colorbar(im, ax=ax, label="median hours from run start to first re-entry", shrink=0.9)
    fig.suptitle(
        f"{manifest['sweep_name']}: time to parity, criterion {_criterion(rec)} "
        f"({len(manifest['seeds'])} seeds per cell)\n"
        f"median hours from run start (trough step + steps to first band entry) to first "
        f"re-entry within ±{rec['tolerance'] * BPS:g} bps of {_against(rec)}\n"
        f"clock = re-enters, but after {deadline_h:.0f} h; price = never re-enters by step "
        f"{horizon:,} ({horizon_h:.0f} h)",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / TIME_TO_PARITY
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


POLICY_COMPARISON = "policy_comparison.png"
REFERENCE_POLICY = "calibrated"


def _base_axis(manifest: dict) -> dict:
    """The manifest's base axis (the entry with ``bases``; ADR-0025)."""
    for axis in manifest["axes"]:
        if "bases" in axis:
            return axis
    raise ValueError(f"sweep {manifest['sweep_name']!r} has no base axis")


def plot_policy_comparison(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Three panels over attacker capital (× the reference base's defender budget +
    redemption reserves), one line per policy (the sweep's base axis), the reference
    policy ``calibrated`` drawn heavier: (a) median hours from run start to first re-entry
    into the recovery band (``time_to_parity_hours``), cells where fewer than half the
    seeds re-enter drawn as "never" at the horizon with an open marker, plus the deadline
    after which a re-entry cannot hold ``for_steps`` by ``max_steps``; (b) mean defender
    spend with its p05–p95 band (no defender = 0); (c) ``p_stays_broken`` with Wilson 95%
    bars. Points are dodged sideways per policy so coinciding series stay visible. Reads
    only ``mc.parquet`` + manifest."""
    from matplotlib.ticker import FuncFormatter

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    policy_col = _base_axis(manifest)["name"]
    policies = list(_base_axis(manifest)["values"])
    cap_col = _axis_named(manifest, CAPITAL_PATH)
    rec = base["termination"]["peg_recovered"]
    interval = base["steps"]["interval_seconds"]
    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    horizon_h = horizon * interval / 3600
    deadline_h = (horizon - rec["for_steps"]) * interval / 3600
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    budget = defender["budget"]
    resources = budget + base["redemption"]["reserves"]

    mc = mc.sort_values([policy_col, cap_col]).reset_index(drop=True)
    mc["hours"] = time_to_parity_hours(mc, interval)
    mc["ratio"] = mc[cap_col] / resources
    p, lo, hi = _p_broken(mc)
    mc["p"], mc["p_lo"], mc["p_hi"] = p, lo, hi
    ratios = sorted(mc["ratio"].unique())
    # Policies often coincide (every buyer spends its whole budget; no-defense and
    # spread-only share p = 1): dodge each policy sideways by a fixed share of the
    # smallest ratio gap so every series stays visible. Tick labels stay on the true ratio.
    gap = min(np.diff(ratios)) if len(ratios) > 1 else 1.0
    dodge = {n: (i - (len(policies) - 1) / 2) * 0.08 * gap for i, n in enumerate(policies)}

    others = iter(zip(SERIES, MARKERS, strict=False))
    style = {}
    for name in policies:
        if name == REFERENCE_POLICY:
            style[name] = {"color": DARK, "marker": "o", "lw": 3.0, "ms": 8, "zorder": 5}
        else:
            color, marker = next(others)
            style[name] = {"color": color, "marker": marker, "lw": 1.6, "ms": 7, "zorder": 3}

    fig, (ax_t, ax_s, ax_p) = plt.subplots(
        1, 3, figsize=(15, 5.6), dpi=150, sharex=True, constrained_layout=True
    )
    for name in policies:
        g = mc[mc[policy_col] == name].sort_values("ratio")
        st = style[name]
        line = {"color": st["color"], "lw": st["lw"], "zorder": st["zorder"]}
        x = g["ratio"].to_numpy() + dodge[name]

        # (a) time to parity; "never" at the horizon with an open marker
        hours = g["hours"].to_numpy()
        never = np.isnan(hours)
        shown = np.where(never, horizon_h, hours)
        ax_t.plot(x, shown, label=name, **line)
        ax_t.plot(
            x[~never],
            shown[~never],
            ls="none",
            marker=st["marker"],
            ms=st["ms"],
            color=st["color"],
            zorder=st["zorder"],
        )
        ax_t.plot(
            x[never],
            shown[never],
            ls="none",
            marker=st["marker"],
            ms=st["ms"] + 2,
            mfc="white",
            mec=st["color"],
            mew=2,
            zorder=st["zorder"] + 1,
        )

        # (b) defender spend, mean with p05-p95 band; no defender = 0
        mean = g["defender_spent_mean"].fillna(0).to_numpy()
        ax_s.fill_between(
            x,
            g["defender_spent_p05"].fillna(0),
            g["defender_spent_p95"].fillna(0),
            color=st["color"],
            alpha=0.15,
            lw=0,
        )
        ax_s.plot(x, mean, marker=st["marker"], ms=st["ms"], **line)

        # (c) p_stays_broken with Wilson bars
        ax_p.errorbar(
            x,
            g["p"],
            yerr=[g["p"] - g["p_lo"], g["p_hi"] - g["p"]],
            marker=st["marker"],
            ms=st["ms"],
            capsize=3,
            **line,
        )

    ax_t.axhline(deadline_h, color=ORANGE, ls="--", lw=1.4, zorder=1)
    ax_t.text(
        ratios[0],
        deadline_h,
        f" deadline {deadline_h:.0f} h",
        va="bottom",
        ha="left",
        fontsize=8,
        color=DARK,
    )
    ax_t.axhline(horizon_h, color=GREY, ls=":", lw=1.0, zorder=1)
    ax_t.text(
        ratios[0],
        horizon_h,
        f" never (horizon {horizon_h:.0f} h)",
        va="bottom",
        ha="left",
        fontsize=8,
        color=DARK,
    )
    ax_t.set_ylim(0, horizon_h * 1.08)
    ax_t.set_ylabel("median hours from run start to first re-entry")
    ax_t.set_title("(a) time to parity (open marker = never)", fontsize=10)

    ax_s.axhline(budget, color=GREY, ls=":", lw=1.0, zorder=1)
    ax_s.text(
        ratios[0],
        budget,
        f" budget {_usd(budget, usd_per_unit)} (calibrated)",
        va="bottom",
        ha="left",
        fontsize=8,
        color=DARK,
    )
    ax_s.set_ylim(0, budget * 1.12)
    ax_s.set_yticks([budget * q for q in (0, 0.25, 0.5, 0.75, 1.0)])
    ax_s.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _usd(v, usd_per_unit) if v else "0"))
    ax_s.set_ylabel("defender spend ($; mean, p05–p95 band)")
    ax_s.set_title("(b) defender spend", fontsize=10)

    ax_p.set_ylim(-0.03, 1.03)
    ax_p.set_ylabel("p(stays broken), Wilson 95%")
    ax_p.set_title("(c) p(stays broken)", fontsize=10)

    for ax in (ax_t, ax_s, ax_p):
        ax.set_xticks(ratios)
        ax.set_xticklabels(
            [f"{r:.2g}×\n{_usd(r * resources, usd_per_unit)}" for r in ratios], fontsize=8
        )
        ax.set_xlabel("attacker capital (× defender budget + redemption reserves; $)")
        ax.grid(axis="y", color=BAND, lw=0.6)
        ax.set_axisbelow(True)
    ax_t.legend(title="policy", fontsize=8, title_fontsize=8, loc="lower right")
    fig.suptitle(
        f"{manifest['sweep_name']}: defender policies, criterion {_criterion(rec)} "
        f"({len(manifest['seeds'])} seeds per point)\n"
        f"re-entry = first step within ±{rec['tolerance'] * BPS:g} bps of {_against(rec)}; "
        f"recovered = held for {rec['for_steps']:,} steps by step {horizon:,}",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / POLICY_COMPARISON
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


HOLDER_EXIT = "holder_exit.png"
HOLDER_EXIT_PATH = "agents[type=holder].exit_discount_pct"
HOLDER_CAPITAL_PATH = "agents[type=holder].capital"


def _exit_label(v: float) -> str:
    return "never sells" if pd.isna(v) else f"sells below\n−{v:g}%"


def plot_holder_exit(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Story 3.3: the holder's exit rule x holder capital. Left: heatmap of
    ``p_reserves_exhausted`` over exit discount (columns; ``null`` first, labelled "never
    sells") x holder capital (rows, as a multiple of the base scenario's holder capital).
    Right, two panels over the same exit columns with one line per capital: mean hours to
    reserves exhaustion (``steps_run_mean``; a filled marker where every seed exhausts, an
    open one where only some do, so the mean includes ``max_steps`` runs, and "not
    exhausted" at the horizon where none do), and mean holder PnL with its p05–p95 range.
    Reads only ``mc.parquet`` + manifest."""
    from matplotlib.ticker import FuncFormatter

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    exit_col = _axis_named(manifest, HOLDER_EXIT_PATH)
    cap_col = _axis_named(manifest, HOLDER_CAPITAL_PATH)
    holder = next(a for a in base["agents"] if a["type"] == "holder")
    attacker = next(a for a in base["agents"] if a["type"] == "attacker")
    unit = holder["capital"]
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    resources = defender["budget"] + base["redemption"]["reserves"]
    interval = base["steps"]["interval_seconds"]
    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    horizon_h = horizon * interval / 3600

    exits = sorted(mc[exit_col].unique(), key=lambda v: (not pd.isna(v), 0 if pd.isna(v) else v))
    caps = sorted(mc[cap_col].unique())
    col = {("nan" if pd.isna(v) else v): i for i, v in enumerate(exits)}
    mc = mc.assign(_x=[col["nan" if pd.isna(v) else v] for v in mc[exit_col]])
    cap_labels = [
        f"{c / unit:g}× ({_usd(c, usd_per_unit)}; {c / attacker['capital']:.2f}× attacker)"
        for c in caps
    ]

    fig = plt.figure(figsize=(15, 6.4), dpi=150, constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 1])
    ax_h = fig.add_subplot(gs[:, 0])
    ax_t = fig.add_subplot(gs[0, 1])
    ax_p = fig.add_subplot(gs[1, 1], sharex=ax_t)

    # left: p_reserves_exhausted heatmap
    grid = np.full((len(caps), len(exits)), np.nan)
    for _, r in mc.iterrows():
        grid[caps.index(r[cap_col]), int(r["_x"])] = r["p_reserves_exhausted"]
    from matplotlib.colors import ListedColormap

    im = ax_h.imshow(
        grid, cmap=ListedColormap(SEQ_BLUE), vmin=0, vmax=1, origin="lower", aspect="auto"
    )
    for i in range(len(caps)):
        for j in range(len(exits)):
            v = grid[i, j]
            ax_h.text(
                j,
                i,
                "–" if np.isnan(v) else f"{v:.2f}",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if v >= 0.6 else DARK,
            )
    ax_h.set_xticks(range(len(exits)))
    ax_h.set_xticklabels([_exit_label(v) for v in exits], fontsize=8)
    ax_h.set_yticks(range(len(caps)))
    ax_h.set_yticklabels([lab.replace(" (", "\n(") for lab in cap_labels], fontsize=8)
    ax_h.set_xlabel("holder exit rule (one-way: sells everything on the AMM, never re-enters)")
    ax_h.set_ylabel("holder capital (× base holder C*)")
    ax_h.set_title("p(reserves exhausted)", fontsize=10)
    fig.colorbar(im, ax=ax_h, fraction=0.05, pad=0.02, label="p(reserves exhausted)")

    # right: exhaustion time and holder PnL, one line per capital
    styles = list(zip(SERIES, MARKERS, strict=False))
    for k, (c, lab) in enumerate(zip(caps, cap_labels, strict=True)):
        color, marker = styles[k]
        g = mc[mc[cap_col] == c].sort_values("_x")
        x = g["_x"].to_numpy(dtype=float)
        p = g["p_reserves_exhausted"].to_numpy()
        hours = g["steps_run_mean"].to_numpy() * interval / 3600
        shown = np.where(p > 0, hours, horizon_h)
        ax_t.plot(x, shown, color=color, lw=1.6, label=lab)
        full, part, none = p >= 1, (p > 0) & (p < 1), p <= 0
        ax_t.plot(x[full], shown[full], ls="none", marker=marker, ms=8, color=color)
        for mask in (part, none):
            ax_t.plot(
                x[mask], shown[mask], ls="none", marker=marker, ms=9, mfc="white", mec=color, mew=2
            )
        bn = usd_per_unit / 1e9  # PnL drawn in $B so the axis ticks are round dollars
        ax_p.fill_between(
            x, g["holder_pnl_p05"] * bn, g["holder_pnl_p95"] * bn, color=color, alpha=0.15, lw=0
        )
        ax_p.plot(x, g["holder_pnl_mean"] * bn, color=color, lw=1.6, marker=marker, ms=8)

    ax_t.axhline(horizon_h, color=GREY, ls=":", lw=1.0)
    ax_t.text(
        0, horizon_h, f" not exhausted (horizon {horizon_h:.0f} h)", va="bottom", fontsize=8,
        color=DARK,
    )  # fmt: skip
    lo = np.nanmin(mc["steps_run_mean"]) * interval / 3600
    ax_t.set_ylim(min(lo * 0.97, horizon_h * 0.5), horizon_h * 1.08)
    ax_t.set_ylabel("mean hours to reserves exhausted")
    ax_t.set_title("time to exhaustion (open marker: not every seed exhausts)", fontsize=10)
    ax_t.legend(title="holder capital", fontsize=7, title_fontsize=7, loc="center right")

    ax_p.axhline(0, color=GREY, ls="--", lw=1.0)
    ax_p.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+,.0f}" if v else "0"))
    ax_p.set_ylabel("holder PnL ($B; mean, p05–p95 band)")
    ax_p.set_title("holder PnL (marked at final AMM spot)", fontsize=10)
    ax_p.set_xticks(range(len(exits)))
    ax_p.set_xticklabels([_exit_label(v) for v in exits], fontsize=8)
    plt.setp(ax_t.get_xticklabels(), visible=False)
    for ax in (ax_t, ax_p):
        ax.grid(axis="y", color=BAND, lw=0.6)
        ax.set_axisbelow(True)

    fig.suptitle(
        f"{manifest['sweep_name']}: does the 1992 analogue need the believer to switch sides? "
        f"attacker {attacker['capital'] / resources:.3g}× (defender budget + reserves) "
        f"({len(manifest['seeds'])} seeds per cell)",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / HOLDER_EXIT
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# -- budget x attack (Story 3.4) ------------------------------------------------------------

BUDGET_ATTACK = "budget_attack.png"
# Fitted calibrated depth per side (ADR-0019 amendment, Story 2.5). A label only: the
# budget x attack sweep overrides the depth, so its manifest base_config no longer holds D*.
D_STAR = 16_666_667


def p_never_reenters(mc: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """The price-loss probability ``1 - steps_to_first_band_entry_n / n`` (share of seeds
    that never get back within the recovery band) with Wilson 95% bounds. Unlike
    ``p_stays_broken`` it does not count a late re-entry (the clock) as a loss."""
    from depeg_sim.analysis.stats import wilson

    k = (mc["n"] - mc["steps_to_first_band_entry_n"]).astype(int)
    bounds = [wilson(int(ki), int(ni)) for ki, ni in zip(k, mc["n"], strict=True)]
    p = (k / mc["n"]).astype(float)
    return p, pd.Series([b[0] for b in bounds]), pd.Series([b[1] for b in bounds])


def plot_budget_attack(sweep_dir: Path, usd_per_unit: float = USD_PER_UNIT) -> Path:
    """Left: heatmap of p(never re-enters) (``p_never_reenters``) over defender budget x
    attacker capital with the 0.5 contour. Right: each attack column's 0.5-crossing budget
    (``budget_crossing``) against attack on log-log axes, columns whose crossing lies
    outside the grid drawn as bounds, slope-1 (budget proportional to the attack) and
    slope-0 (one budget whatever the attack) reference lines through the middle crossing,
    and the least-squares slope. Reads only ``mc.parquet`` + manifest."""
    from matplotlib.colors import LinearSegmentedColormap

    sweep_dir = Path(sweep_dir)
    mc, manifest = _read_sweep(sweep_dir)
    base = manifest["base_config"]
    budget_col, cap_col = _axis_named(manifest, BUDGET_PATH), _axis_named(manifest, CAPITAL_PATH)
    defender = next(a for a in base["agents"] if a["type"] == "defender")
    b_cal = defender["budget"]
    resources = b_cal + base["redemption"]["reserves"]
    depth = base["amm"]["reserve_stable"]
    rec = base["termination"]["peg_recovered"]

    mc = mc.sort_values([budget_col, cap_col]).reset_index(drop=True)
    mc["p"], mc["lo"], mc["hi"] = p_never_reenters(mc)
    budgets = sorted(mc[budget_col].unique())
    caps = sorted(mc[cap_col].unique())
    values = mc.pivot(index=budget_col, columns=cap_col, values="p").loc[budgets, caps].to_numpy()
    half = ((mc["hi"] - mc["lo"]) / 2).to_numpy().reshape(len(budgets), len(caps))

    fig, (left, right) = plt.subplots(1, 2, figsize=(20, 6), dpi=150, constrained_layout=True)
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
    im = left.imshow(values, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=1)
    if (values >= 0.5).any() and (values < 0.5).any():
        left.contour(values, levels=[0.5], colors=[ORANGE], linewidths=2.0)
    for i in range(len(budgets)):
        for j in range(len(caps)):
            v = values[i, j]
            left.text(
                j,
                i,
                f"{v:.2f}\n±{half[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if v >= 0.55 else DARK,
            )
    left.set_xticks(range(len(caps)))
    left.set_xticklabels(
        [f"{c / resources:.3g}× resources\n{_usd(c, usd_per_unit)}" for c in caps], fontsize=8
    )
    left.set_yticks(range(len(budgets)))
    left.set_yticklabels(
        [f"{b / b_cal:.3g}× budget\n{_usd(b, usd_per_unit)}" for b in budgets], fontsize=8
    )
    left.set_xlabel("attacker capital (× calibrated defender budget + redemption reserves; $)")
    left.set_ylabel("defender budget (× calibrated budget; $)")
    left.set_title(
        "p(never re-enters): heatmap, orange line = 0.5 contour, ± Wilson 95% half-width",
        fontsize=10,
    )
    fig.colorbar(im, ax=left, label="p(never re-enters) = 1 − re-entering seeds / n", shrink=0.9)

    points, bounds = [], []
    for c in caps:
        g = mc[mc[cap_col] == c]
        x, kind = budget_crossing(g[budget_col].tolist(), g["p"].tolist())
        if kind == "crossing":
            points.append((c, x))
        else:
            bounds.append((c, budgets[0] if kind == "below" else budgets[-1], kind))
    if points:
        right.plot(
            [c for c, _ in points],
            [x for _, x in points],
            marker="o",
            ms=8,
            color=SERIES[0],
            lw=2,
            label="0.5 crossing budget (linear interpolation)",
        )
    for kind, marker, text in (
        ("below", "v", "not reached: holds at the smallest budget (crossing below)"),
        ("above", "^", "not reached: no budget in the grid holds (crossing above)"),
    ):
        pts = [(c, b) for c, b, k in bounds if k == kind]
        if pts:
            right.plot(
                [c for c, _ in pts],
                [b for _, b in pts],
                ls="none",
                marker=marker,
                ms=10,
                mfc="white",
                mec=SERIES[1],
                mew=1.8,
                label=text,
            )
    if points:
        c0, x0 = points[len(points) // 2]
        right.plot(
            [caps[0], caps[-1]],
            [x0 * caps[0] / c0, x0 * caps[-1] / c0],
            color=GREY,
            ls="--",
            lw=1.2,
            label="slope 1 (budget ∝ attack), through the middle crossing",
        )
        right.plot(
            [caps[0], caps[-1]],
            [x0, x0],
            color=GREY,
            ls=":",
            lw=1.4,
            label="slope 0 (one budget whatever the attack), through the middle crossing",
        )
    if len(points) >= 2:
        slope = loglog_slope(points)
        right.plot([], [], ls="none", label=f"least-squares log–log slope: {slope:.2f}")
    right.set_xscale("log")
    right.set_yscale("log")
    right.set_xticks(caps)
    right.set_xticklabels([f"{c / resources:.3g}×" for c in caps], fontsize=8)
    right.set_yticks(budgets)
    right.set_yticklabels([f"{b / b_cal:.3g}×" for b in budgets], fontsize=8)
    right.minorticks_off()
    right.set_xlabel("attacker capital (× resources, log)")
    right.set_ylabel("defender budget at the 0.5 crossing (× calibrated, log)")
    right.set_title("What does the budget that holds the price have to match?", fontsize=10)
    right.legend(loc="upper left", fontsize=8, frameon=False)
    right.spines[["top", "right"]].set_visible(False)

    horizon = manifest.get("max_steps") or base["steps"]["max_steps"]
    hours = horizon * base["steps"]["interval_seconds"] / 3600
    fig.suptitle(
        f"{manifest['sweep_name']}: defender budget against attack size at pool depth "
        f"{depth / D_STAR:.3g}× D* ({_usd(depth, usd_per_unit)} per side), criterion "
        f"{_criterion(rec)} (volatility {base['environment']['volatility_per_step']:g}/step; "
        f"holder present; {len(manifest['seeds'])} seeds per cell)\n"
        f"price lost = never back within ±{rec['tolerance'] * BPS:g} bps of {_against(rec)} "
        f"by step {horizon:,} ({hours:.0f} h); a late re-entry (the clock) is not counted",
        fontsize=10,
    )
    _sweep_footer(fig, manifest)
    out = sweep_dir / BUDGET_ATTACK
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
