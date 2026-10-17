"""Story 5.2 AC 3-5: how wide the family of fits is on the par-reference replay.

Runs ``sweeps/usdc-par-depth-x-capital.yaml`` (pool depth x ladder-B capital, both as
multiples of D* and C*) and the ladder runs, then prints three tables:

1. **Cells inside ±10%** of the observed trough: every grid cell whose ``max_depeg_bps``
   is within 10% of the observed one.
2. **C\\* range inside ±5%, per depth:** for each pool depth, the holder capital (as a
   multiple of ladder B's C*) over which the trough, linearly interpolated between
   adjacent grid points on the capital axis, lies within 5% of the observed trough. A
   depth can give several disjoint ranges, or none.
3. **Ladders side by side** at D*: ladders A, B, C (ADR-0030) each at its own C* from
   Story 3.7 and each at ladder B's C*, plus the continuous ladder (AC 5: 2, 4, ..., 20%
   at 10% each) at ladder B's C*.
4. **Three C\\*** (Story 5.6): ladder B's C* from the three fit records ``FITS``
   (observed reference; par reference, channel open; par reference, channel closed), each
   run at C* and at a 5-point linear scan ``C* + k x step`` (k = -2..2), where ``step`` is
   the spacing of that fit's second refinement (recomputed from the record's runs with
   ``fit_holder``'s rule; points on that refinement's lattice are rounded as it rounded
   them, so k = ±1 are the runs the fit already made when C* is on it). The ±10% range
   is the capital over which the trough, linearly interpolated between the scan points,
   lies within 10% of the observed trough (``capital_ranges``); the row also says how
   many scan points are inside.

The observed trough (the target) and every per-run metric come from
``scripts/replay_table.py`` (``observed_row``, ``simulated_row``; ADR-0033 ruling 3):
trough bps and hours, "first back in band after the trough", hours in band over
27-96 h, holder bought / redeemed / PnL. The sweep's own ``steps_to_first_band_entry`` is
null on these scenarios (they have no ``peg_recovered`` condition), so re-entry is taken
from ``simulated_row``. Model units (1M = $234.6M).

Nothing is fitted here; the C* values are constants with their sources. Deterministic
(seed 42, constant reference, no wall clock in the output). ``--max-steps`` shortens
every run (smoke test).

    python scripts/identification_table.py [--output DIR] [--workers N] [--max-steps N]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
from fit_holder import REFINE_POINTS, S, closest, neighbours, refine_between, with_holder
from replay_table import OBSERVED_FROM, observed_row, simulated_row

from depeg_sim.analysis.charts import _band
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import (
    SweepSpec,
    cell_run_dir,
    expand,
    load_sweep,
    run_sweep,
    set_path,
)
from depeg_sim.kernel.config import load_scenario

SPEC = Path("sweeps/usdc-par-depth-x-capital.yaml")
BASE = Path("scenarios/usdc-2023-tranches-par.yaml")
DEPTH, CAPITAL = "pool_depth", "holder_capital"
WIDE, NARROW = 0.10, 0.05  # AC 3: cells inside ±10%; C* ranges inside ±5%

# Fitted total capital per ladder, Story 3.7 (ADR-0030 Decision 4; B is also
# docs/calibration/fits/holder-ladder-b.json). Not re-fitted.
LADDERS = {
    "A (1/2/5% at 50/30/20)": ([(1.0, 0.5), (2.0, 0.3), (5.0, 0.2)], 8_333_333),
    "B (2/5/10/20% at 25% each)": ([(2.0, 0.25), (5.0, 0.25), (10.0, 0.25), (20.0, 0.25)],
                                   10_833_333),
    "C (1/2/5/10/15% at 20% each)": ([(1.0, 0.2), (2.0, 0.2), (5.0, 0.2), (10.0, 0.2),
                                     (15.0, 0.2)], 10_000_000),
}  # fmt: skip
C_STAR_B = LADDERS["B (2/5/10/20% at 25% each)"][1]
# AC 5: uniform over 2-20% in 10 equal tranches of 10% each
CONTINUOUS = ("continuous (2, 4, ..., 20% at 10% each)", [(2.0 * k, 0.1) for k in range(1, 11)])
# Table 4 (Story 5.6): ladder B's three fit records, each with the scenario it was fitted on
FITS_DIR = Path("docs/calibration/fits")
FITS = {
    "observed reference, channel open": FITS_DIR / "holder-ladder-b.json",
    "par reference, channel open": FITS_DIR / "holder-ladder-b-par.json",
    "par reference, channel closed": FITS_DIR / "holder-ladder-b-closed.json",
}
SCAN = (-2, -1, 0, 1, 2)  # multiples of the second refinement's spacing around C*


def within(trough: float, target: float, tol: float) -> bool:
    return abs(trough - target) <= tol * abs(target)


def capital_ranges(
    caps: list[float], troughs: list[float], lo: float, hi: float
) -> list[tuple[float, float]]:
    """The capital values over which the piecewise-linear interpolant of ``troughs``
    (over sorted ``caps``) lies in ``[lo, hi]``; touching pieces are merged."""
    pieces: list[tuple[float, float]] = []
    points = list(zip(caps, troughs, strict=True))
    for (x0, t0), (x1, t1) in itertools.pairwise(points):
        if t0 == t1:
            if lo <= t0 <= hi:
                pieces.append((x0, x1))
            continue
        # x where the line through (x0, t0), (x1, t1) reaches each bound, clipped to [x0, x1]
        a, b = (x0 + (bound - t0) * (x1 - x0) / (t1 - t0) for bound in (lo, hi))
        a, b = max(min(a, b), x0), min(max(a, b), x1)
        if a <= b:
            pieces.append((a, b))
    merged: list[tuple[float, float]] = []
    for a, b in pieces:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def _shorten(cfg, max_steps: int | None):
    return cfg if max_steps is None else set_path(cfg, "steps.max_steps", max_steps)


def ladder_config(tranches: list[tuple[float, float]], capital: float, max_steps: int | None):
    cfg = set_path(load_scenario(BASE), "agents[type=holder].capital", capital)
    cfg = set_path(
        cfg,
        "agents[type=holder].tranches",
        [{"entry_discount_pct": d, "share": s} for d, s in tranches],
    )
    return _shorten(cfg, max_steps)


def refine_step(record: dict) -> tuple[float, float]:
    """``(lo, spacing)`` of the fit's second refinement (``lo`` its lower end), replaying
    ``fit_holder``'s rule on the record's runs: grid pick and its neighbours, first
    refinement, re-pick and neighbours."""
    args, runs = record["inputs"]["args"], record["result"]["runs"]
    df = pd.DataFrame(runs)
    target = args["target_bps"]
    seen = df[df["holder_capital"].isin(args["grid"])].sort_values("holder_capital")
    for _ in range(2):
        pick = int(closest(seen, target)["holder_capital"])
        lo, hi = neighbours(seen["holder_capital"].astype(int).tolist(), pick)
        refined = refine_between(lo, hi)
        seen = df[df["holder_capital"].isin(set(seen["holder_capital"]) | set(refined))]
        seen = seen.sort_values("holder_capital").reset_index(drop=True)
    if set(seen["holder_capital"]) != set(df["holder_capital"]):
        raise ValueError("the record's runs are not the two-pass rule's")
    return lo, (hi - lo) / (REFINE_POINTS + 1)


def scan_capitals(c_star: int, lo: float, step: float) -> list[int]:
    """``C* + k x step`` for k in ``SCAN``, from C*'s point on the lattice ``lo + j x step``
    when C* is on it (within the fit's rounding), else from C* itself."""
    on_lattice = lo + round((c_star - lo) / step) * step
    anchor = on_lattice if abs(on_lattice - c_star) <= 0.5 else c_star
    return [int(round(anchor + k * step)) for k in SCAN]


def fit_scan(label: str, path: Path, output: Path, window_h, max_steps: int | None) -> dict:
    """One fit record's C* and its 5-point scan, each run as ``fit_holder`` ran it."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    args, c_star = record["inputs"]["args"], record["result"]["c_star"]
    lo, step = refine_step(record)
    tranches = [tuple(t) for t in args["tranches"]]
    base = with_holder(Path(record["inputs"]["scenario"]), 0.0, args["pace"], tranches)
    scan = []
    for k, capital in zip(SCAN, scan_capitals(c_star, lo, step), strict=True):
        cfg = set_path(base, "agents[type=holder].capital", capital)
        cfg = _shorten(set_path(cfg, "name", f"identification-{path.stem}-{k:+d}"), max_steps)
        run = run_scenario(cfg, output_dir=output, chart=False)
        scan.append({"capital": capital} | simulated_row(label, run.run_dir, window_h))
    return {"label": label, "fit": path.name, "c_star": c_star, "step": step, "scan": scan}


def build(
    output: Path,
    workers: int = 1,
    max_steps: int | None = None,
    spec: SweepSpec | None = None,
) -> dict:
    """``{"observed": row, "cells": [...], "ladders": [...], "fits": [...]}``; every run
    under ``output``."""
    base = load_scenario(OBSERVED_FROM)
    attacker = next(a for a in base.agents if a.type == "attacker")
    start_h = attacker.start_step * base.steps.interval_seconds / 3600
    obs = observed_row(
        base.environment.price_series_path,
        base.redemption.peg_price,
        _band(base.model_dump(mode="json")),
        start_h,
    )
    spec = spec or load_sweep(SPEC)
    if max_steps is not None:
        spec = spec.model_copy(update={"max_steps": max_steps})
    run_sweep(spec, output, workers=workers)
    cells = []
    for cell in expand(spec):
        row = simulated_row(cell.config.name, cell_run_dir(cell, output), obs["window_h"])
        cells.append({DEPTH: cell.axis_values[DEPTH], CAPITAL: cell.axis_values[CAPITAL]} | row)

    ladders = []
    runs = [(f"{name}, own C*", t, c) for name, (t, c) in LADDERS.items()]
    runs += [(f"{name}, ladder B's C*", t, C_STAR_B) for name, (t, _) in LADDERS.items()]
    runs.append((f"{CONTINUOUS[0]}, ladder B's C*", CONTINUOUS[1], C_STAR_B))
    for i, (label, tranches, capital) in enumerate(runs):
        cfg = ladder_config(tranches, capital, max_steps)
        cfg = set_path(cfg, "name", f"identification-ladder-{i}")
        run = run_scenario(cfg, output_dir=output, chart=False)
        ladders.append({"capital": capital} | simulated_row(label, run.run_dir, obs["window_h"]))
    fits = [fit_scan(lb, p, output, obs["window_h"], max_steps) for lb, p in FITS.items()]
    return {"observed": obs, "cells": cells, "ladders": ladders, "fits": fits}


def _h(v: float | None) -> str:
    return "never" if v is None else f"{v:.1f}"


def _fmt_range(ranges: list[tuple[float, float]]) -> str:
    return "none" if not ranges else ", ".join(f"{a:.3f}-{b:.3f}" for a, b in ranges)


def format_tables(result: dict) -> str:
    obs, cells, ladders = result["observed"], result["cells"], result["ladders"]
    target = obs["trough_bps"]
    out = [f"observed trough {target:,.1f} bps at {obs['trough_h']:.1f} h (the target)", ""]

    out.append(f"1. cells inside ±{WIDE:.0%} ({target * (1 + WIDE):,.1f} to "
               f"{target * (1 - WIDE):,.1f} bps)")  # fmt: skip
    head = (
        f"{'depth xD*':>9} {'capital xC*':>11} {'trough bps':>10} {'gap':>6} {'h':>5} "
        f"{'re-entry h':>10} {'in band h':>9} {'holder bought':>13} {'holder redeemed':>15} "
        f"{'holder PnL':>10}"
    )
    out += [head, "-" * len(head)]
    inside = [c for c in cells if within(c["trough_bps"], target, WIDE)]
    for c in sorted(inside, key=lambda c: (c[DEPTH], c[CAPITAL])):
        gap = (c["trough_bps"] - target) / abs(target)
        out.append(
            f"{c[DEPTH]:>9g} {c[CAPITAL]:>11g} {c['trough_bps']:>10,.1f} {gap:>+6.1%} "
            f"{c['trough_h']:>5.1f} {_h(c['reentry_h']):>10} {c['in_band_h']:>9.1f} "
            f"{c['holder_bought']:>13,.0f} {c['holder_redeemed']:>15,.0f} {c['holder_pnl']:>10,.0f}"
        )
    if not inside:
        out.append("(none)")
    out.append(f"{len(inside)} of {len(cells)} cells")

    lo, hi = target * (1 + NARROW), target * (1 - NARROW)
    out += ["", f"2. capital (x ladder B's C* = {C_STAR_B:,}) with the trough inside "
            f"±{NARROW:.0%} ({lo:,.1f} to {hi:,.1f} bps), linear between grid points"]  # fmt: skip
    head = f"{'depth xD*':>9}  {'troughs at the capital grid (bps)':<60}  C* range (x C*)"
    out += [head, "-" * len(head)]
    for depth in sorted({c[DEPTH] for c in cells}):
        col = sorted((c for c in cells if c[DEPTH] == depth), key=lambda c: c[CAPITAL])
        caps = [c[CAPITAL] for c in col]
        troughs = [c["trough_bps"] for c in col]
        grid = " ".join(f"{t:,.0f}" for t in troughs)
        out.append(f"{depth:>9g}  {grid:<60}  {_fmt_range(capital_ranges(caps, troughs, lo, hi))}")
    out.append(
        f"capital grid (x C*): {' '.join(f'{c:g}' for c in sorted({c[CAPITAL] for c in cells}))}"
    )

    out += ["", "3. ladders at D*, par reference"]
    head = (
        f"{'ladder, capital':<58} {'capital':>11} {'trough bps':>10} {'gap':>6} {'h':>5} "
        f"{'re-entry h':>10} {'in band h':>9} {'holder bought':>13} {'holder PnL':>10}"
    )
    out += [head, "-" * len(head)]
    for r in ladders:
        gap = (r["trough_bps"] - target) / abs(target)
        out.append(
            f"{r['label']:<58} {r['capital']:>11,} {r['trough_bps']:>10,.1f} {gap:>+6.1%} "
            f"{r['trough_h']:>5.1f} {_h(r['reentry_h']):>10} {r['in_band_h']:>9.1f} "
            f"{r['holder_bought']:>13,.0f} {r['holder_pnl']:>10,.0f}"
        )
    lo, hi = target * (1 + WIDE), target * (1 - WIDE)
    out += ["", f"4. ladder B's C* by fit, with a 5-point scan at the second refinement's "
            f"spacing; ±{WIDE:.0%} range ({lo:,.1f} to {hi:,.1f} bps), linear between "
            "scan points"]  # fmt: skip
    head = (
        f"{'fit':<33} {'C*':>11} {'$B':>5} {'trough bps':>10} {'gap':>6} {'h':>5} "
        f"{'re-entry h':>10} {'step':>9}  {'scan troughs, k = -2..2 (bps)':<36}  "
        f"{'±10% range (capital)':<23} inside"
    )
    out += [head, "-" * len(head)]
    for f in result["fits"]:
        r = f["scan"][SCAN.index(0)]
        gap = (r["trough_bps"] - target) / abs(target)
        caps = [s["capital"] for s in f["scan"]]
        troughs = [s["trough_bps"] for s in f["scan"]]
        span = ", ".join(f"{a:,.0f}-{b:,.0f}" for a, b in capital_ranges(caps, troughs, lo, hi))
        n_in = sum(within(t, target, WIDE) for t in troughs)
        out.append(
            f"{f['label']:<33} {f['c_star']:>11,} {f['c_star'] / S / 1e9:>5.2f} "
            f"{r['trough_bps']:>10,.1f} {gap:>+6.1%} {r['trough_h']:>5.1f} "
            f"{_h(r['reentry_h']):>10} {f['step']:>9,.0f}  "
            f"{' '.join(f'{t:,.0f}' for t in troughs):<36}  {span or 'none':<23} "
            f"{n_in} of {len(troughs)}"
        )
    for f in result["fits"]:
        out.append(
            f"  {f['label']} ({f['fit']}) scan: "
            + "; ".join(
                f"{s['capital']:,} -> {s['trough_bps']:,.1f} at {s['trough_h']:.1f} h"
                for s in f["scan"]
            )
        )
    lo_h, hi_h = obs["window_h"]
    out += ["", f"gap: (trough - observed) / |observed|, + is shallower; in band h over "
            f"{lo_h:.0f}-{hi_h:.0f} h; model units (1M = $234.6M)"]  # fmt: skip
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--output", type=Path, default=None, help="keep the runs here (default: temp)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    p.add_argument("--max-steps", type=int, default=None, help="shorten every run (smoke test)")
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="identification-") as tmp:
        result = build(args.output or Path(tmp), args.workers, args.max_steps)
    print(format_tables(result))
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # skip teardown: pyarrow's thread pool can abort there (see depeg_sim.mc)
