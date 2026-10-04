"""Fit aggregate pool depth D* to the observed March-2023 trough (Story 2.4, F-05).

Sweeps a linked ``pool_depth`` axis (both AMM reserves) over a fixed grid on the
calibrated baseline (its own seed and calm volatility, everything else fixed), runs it
with ``run_sweep`` and reads ``sweep.parquet``.

Selection rule (story 2.4 AC 2), applied mechanically:

1. ``D*`` is the smallest grid depth with ``max_depeg_bps >= target`` (default -1300,
   Chainalysis $0.87).
2. If the grid point below it misses the target, the crossing lies between the two:
   a second pass runs 5 evenly spaced depths strictly between them, and ``D*`` is the
   depth closest to the target among the refined points and the two bracketing grid
   points (ties go to the smaller depth).
3. If no grid depth reaches the target, the grid is extended by one decade only
   (``EXTENSION``, story 2.4 context constraint) and the script says so; steps 1-2 then
   apply to the extended grid. If that still misses, ``D*`` is undefined (exit 1).

Prints the grid table, the refinement table if any, then ``D* = <depth> (trough <bps>)``.
``--dry-run`` prints the grid and exits without running.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from depeg_sim.experiments.sweep import (
    SWEEP_PARQUET,
    LinkedAxis,
    SweepSpec,
    run_sweep,
)
from depeg_sim.kernel.config import load_scenario

GRID = [
    1_000_000,
    2_000_000,
    5_000_000,
    10_000_000,
    20_000_000,
    50_000_000,
    100_000_000,
    200_000_000,
    500_000_000,
]
EXTENSION = [1_000_000_000, 2_000_000_000, 5_000_000_000]
REFINE_POINTS = 5
DEPTH_PATHS = ["amm.reserve_stable", "amm.reserve_reference"]
COLUMNS = ["pool_depth", "max_depeg_bps", "terminated_by", "defender_spent", "steps_run"]


def spec_for(name: str, scenario: Path, depths: list[int]) -> SweepSpec:
    seed = load_scenario(scenario).seed
    return SweepSpec(
        version=1,
        name=name,
        base=scenario,
        linked_axes=[LinkedAxis(name="pool_depth", paths=DEPTH_PATHS, values=depths)],
        seeds=[seed],
    )


def refine_between(lo: int, hi: int) -> list[int]:
    """``REFINE_POINTS`` evenly spaced integer depths strictly between ``lo`` and ``hi``."""
    return [int(round(x)) for x in np.linspace(lo, hi, REFINE_POINTS + 2)[1:-1]]


def run_table(spec: SweepSpec, output: Path, workers: int) -> pd.DataFrame:
    sweep_dir = run_sweep(spec, output, workers=workers)
    df = pd.read_parquet(sweep_dir / SWEEP_PARQUET)
    return df[COLUMNS].sort_values("pool_depth").reset_index(drop=True)


def first_crossing(df: pd.DataFrame, target: float) -> int | None:
    """Row index of the smallest depth whose trough is at or above ``target``."""
    hits = df.index[df["max_depeg_bps"] >= target]
    return None if hits.empty else int(hits[0])


def closest(df: pd.DataFrame, target: float) -> pd.Series:
    """Row closest to ``target``; ties go to the smaller depth."""
    gap = (df["max_depeg_bps"] - target).abs()
    order = pd.DataFrame({"gap": gap, "depth": df["pool_depth"]}).sort_values(["gap", "depth"])
    return df.loc[order.index[0]]


def show(title: str, df: pd.DataFrame) -> None:
    print(title)
    print(df.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scenario", type=Path, default=Path("scenarios/calibrated-baseline.yaml"))
    p.add_argument("--target-bps", type=float, default=-1300.0)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--dry-run", action="store_true", help="List the grid and exit")
    args = p.parse_args(argv)

    if args.dry_run:
        print(f"fit_depth: scenario={args.scenario} target_bps={args.target_bps:g}")
        print(f"grid ({len(GRID)}): " + ", ".join(f"{d:,}" for d in GRID))
        print(
            "extension if no grid depth reaches the target: "
            + ", ".join(f"{d:,}" for d in EXTENSION)
        )
        return 0

    grid = run_table(spec_for("fit-depth", args.scenario, GRID), args.output, args.workers)
    show(f"grid pass (target {args.target_bps:g} bps):", grid)
    i = first_crossing(grid, args.target_bps)
    if i is None:
        print(f"no grid depth reaches {args.target_bps:g} bps; extending by one decade")
        print()
        ext = run_table(
            spec_for("fit-depth-ext", args.scenario, EXTENSION), args.output, args.workers
        )
        show("extension pass:", ext)
        grid = pd.concat([grid, ext]).reset_index(drop=True)
        i = first_crossing(grid, args.target_bps)
    if i is None:
        print("no grid depth reaches the target; D* undefined", file=sys.stderr)
        return 1
    best = grid.loc[i]
    if i > 0:
        lo, hi = int(grid.loc[i - 1, "pool_depth"]), int(grid.loc[i, "pool_depth"])
        spec = spec_for("fit-depth-refine", args.scenario, refine_between(lo, hi))
        refined = run_table(spec, args.output, args.workers)
        show(f"refine pass between {lo:,} and {hi:,}:", refined)
        candidates = pd.concat([grid.loc[[i - 1, i]], refined]).reset_index(drop=True)
        best = closest(candidates, args.target_bps)
    print(f"D* = {int(best['pool_depth'])} (trough {best['max_depeg_bps']:.1f} bps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
