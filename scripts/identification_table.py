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
import os
import sys
import tempfile
from pathlib import Path

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


def build(
    output: Path,
    workers: int = 1,
    max_steps: int | None = None,
    spec: SweepSpec | None = None,
) -> dict:
    """``{"observed": row, "cells": [...], "ladders": [...]}``; every run under ``output``."""
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
    return {"observed": obs, "cells": cells, "ladders": ladders}


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
