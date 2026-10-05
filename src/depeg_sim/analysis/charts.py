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


# -- sweep charts (Story 2.7) ------------------------------------------------------------
#
# Both read only ``mc.parquet`` and the sweep ``manifest.json`` (axes, seeds, the resolved
# ``base_config``; ADR-0014 pattern). Each panel is 10x6 in; footer
# ``sweep=<name> base_hash=<12>``. Categorical series use a validated colour-blind-safe
# order and always carry a distinct marker as well, so identity is never colour alone.

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
    fig.text(
        0.995,
        0.002,
        f"sweep={manifest['sweep_name']} base_hash={manifest['base_scenario_hash'][:12]}",
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
        lx = [math.log(d) for d, _ in points]
        ly = [math.log(x) for _, x in points]
        mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
        slope = sum((a - mx) * (b - my) for a, b in zip(lx, ly, strict=True)) / sum(
            (a - mx) ** 2 for a in lx
        )
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
