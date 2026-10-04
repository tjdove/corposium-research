"""Fit the par-expecting buyer's capital C* to the observed March-2023 trough (Story 2.6, F-08).

On the USDC replay (``scenarios/usdc-2023.yaml``), with D* and everything else held fixed,
puts one holder in the scenario (``entry_discount_pct``, ``pace``, ``redeem_when_capacity
true``; an existing holder entry is replaced) and sweeps its ``capital`` with
``run_sweep``, reading ``sweep.parquet``.

Selection rule (story 2.6 AC 4), applied mechanically:

1. Run the log grid ``GRID``. The pick is the grid capital whose ``max_depeg_bps`` is
   closest to the target (default -1373, the Bitstamp hourly low 0.86267).
2. Refine with 5 evenly spaced capitals strictly between the pick's two grid neighbours
   (between the pick and its one neighbour at either end of the grid).
3. ``C*`` is the capital closest to the target among the grid and refined points (ties go
   to the smaller capital).

Prints the grid table, the refinement table, then ``C* = <units> (trough <bps>) ≈
$<dollars>`` with dollars = units / s (SOURCES.md). ``--dry-run`` prints the grid and exits.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from depeg_sim.experiments.sweep import SWEEP_PARQUET, SweepSpec, run_sweep
from depeg_sim.kernel.config import ScenarioConfig, load_scenario

GRID = [1_000_000, 2_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000, 100_000_000]
REFINE_POINTS = 5
S = 1_000_000 / 234_600_000  # model units per $ (SOURCES.md)
HOLDER_ID = "holder-1"
CAPITAL_PATH = "agents[type=holder].capital"
COLUMNS = ["holder_capital", "max_depeg_bps", "step_of_max_depeg", "terminated_by", "steps_run"]


def with_holder(scenario: Path, entry_discount: float, pace: float) -> ScenarioConfig:
    """The scenario with exactly one holder (capital is a placeholder; the sweep sets it)."""
    data = load_scenario(scenario).model_dump(mode="json")
    agents = [a for a in data["agents"] if a["type"] != "holder"]
    agents.append(
        {
            "type": "holder",
            "id": HOLDER_ID,
            "capital": GRID[0],
            "entry_discount_pct": entry_discount,
            "pace": pace,
            "redeem_when_capacity": True,
        }
    )
    data["agents"] = agents
    return ScenarioConfig.model_validate(data)


def write_base(cfg: ScenarioConfig, output: Path) -> Path:
    """Write the holder-bearing base where the sweep can load it (series path is absolute)."""
    output.mkdir(parents=True, exist_ok=True)
    path = output / "fit-holder-base.yaml"
    path.write_text(yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False), "utf-8")
    return path


def spec_for(name: str, base: Path, capitals: list[int]) -> SweepSpec:
    return SweepSpec(
        version=1,
        name=name,
        base=base,
        axes={CAPITAL_PATH: capitals},
        seeds=[load_scenario(base).seed],
    )


def refine_between(lo: int, hi: int) -> list[int]:
    """``REFINE_POINTS`` evenly spaced integer capitals strictly between ``lo`` and ``hi``."""
    return [int(round(x)) for x in np.linspace(lo, hi, REFINE_POINTS + 2)[1:-1]]


def run_table(spec: SweepSpec, output: Path, workers: int) -> pd.DataFrame:
    df = pd.read_parquet(run_sweep(spec, output, workers=workers) / SWEEP_PARQUET)
    df = df.rename(columns={CAPITAL_PATH: "holder_capital"})
    return df[COLUMNS].sort_values("holder_capital").reset_index(drop=True)


def closest(df: pd.DataFrame, target: float) -> pd.Series:
    """Row closest to ``target``; ties go to the smaller capital."""
    gap = (df["max_depeg_bps"] - target).abs()
    order = pd.DataFrame({"gap": gap, "c": df["holder_capital"]}).sort_values(["gap", "c"])
    return df.loc[order.index[0]]


def neighbours(grid: list[int], pick: int) -> tuple[int, int]:
    i = grid.index(pick)
    return grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]


def show(title: str, df: pd.DataFrame) -> None:
    print(title)
    print(df.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scenario", type=Path, default=Path("scenarios/usdc-2023.yaml"))
    p.add_argument("--target-bps", type=float, default=-1373.0)
    p.add_argument("--entry-discount", type=float, default=2.0)
    p.add_argument("--pace", type=float, default=0.05)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--dry-run", action="store_true", help="List the grid and exit")
    args = p.parse_args(argv)

    print(
        f"fit_holder: scenario={args.scenario} target_bps={args.target_bps:g} "
        f"entry_discount_pct={args.entry_discount:g} pace={args.pace:g}"
    )
    print(f"grid ({len(GRID)}): " + ", ".join(f"{c:,}" for c in GRID))
    if args.dry_run:
        return 0

    cfg = with_holder(args.scenario, args.entry_discount, args.pace)
    base = write_base(cfg, args.output / "fit-holder-base")
    grid = run_table(spec_for("fit-holder", base, GRID), args.output, args.workers)
    show(f"grid pass (target {args.target_bps:g} bps):", grid)
    pick = int(closest(grid, args.target_bps)["holder_capital"])
    lo, hi = neighbours(GRID, pick)
    refined = run_table(
        spec_for("fit-holder-refine", base, refine_between(lo, hi)), args.output, args.workers
    )
    show(f"refine pass between {lo:,} and {hi:,} (grid pick {pick:,}):", refined)
    best = closest(pd.concat([grid, refined]).reset_index(drop=True), args.target_bps)
    c_star = int(best["holder_capital"])
    print(
        f"C* = {c_star} (trough {best['max_depeg_bps']:.1f} bps) ≈ ${c_star / S:,.0f} "
        f"at s = {S:.10f} units/$"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
