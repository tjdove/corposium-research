"""Probe for an ADR-0017-style outcome boundary at calibrated depth (Story 2.4 AC 4).

Varies the attacker on a scenario as ``capital = ratio x (defender budget + redemption
reserves)``, with every other parameter fixed, over a range of seeds; runs it with
``run_sweep``, aggregates with ``aggregate_mc`` and prints the outcome shares per ratio
from ``mc.parquet`` (plus the median trough and mean defender spend for context).

Alongside, F-06's deliverable reserves ``min(reserves, capacity_per_step x max_steps)``,
the flip ratio F-06 predicts, ``(budget + deliverable) / (budget + reserves)``, and each
row's ``ratio_deliverable = capital / (budget + deliverable)`` (F-06 predicts the flip at 1).

``--dry-run`` prints the cells and exits without running.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from depeg_sim.experiments.mc import aggregate_mc
from depeg_sim.experiments.sweep import LinkedAxis, SeedRange, SweepSpec, run_sweep
from depeg_sim.kernel.config import load_scenario

CAPITAL_PATH = "agents[type=attacker].capital"
SEED_START = 1000
COLUMNS = [
    "ratio",
    "ratio_deliverable",
    "n",
    "p_reserves_exhausted",
    "p_peg_recovered",
    "p_max_steps",
    "max_depeg_bps_p50",
    "defender_spent_mean",
]


def resources(scenario: Path) -> float:
    """``defender budget + redemption reserves`` of the scenario's first defender."""
    cfg = load_scenario(scenario)
    defender = next(a for a in cfg.agents if a.type == "defender")
    return defender.budget + cfg.redemption.reserves


def deliverable(scenario: Path) -> tuple[float, float]:
    """``(defender budget, deliverable reserves)``: what the redemption channel can pay
    within ``max_steps`` at ``capacity_per_step`` (F-06)."""
    cfg = load_scenario(scenario)
    defender = next(a for a in cfg.agents if a.type == "defender")
    red = cfg.redemption
    return defender.budget, min(red.reserves, red.capacity_per_step * cfg.steps.max_steps)


def spec_for(scenario: Path, ratios: list[float], seeds: int) -> SweepSpec:
    total = resources(scenario)
    return SweepSpec(
        version=1,
        name="probe-boundary",
        base=scenario,
        linked_axes=[
            LinkedAxis(
                name="attacker_capital",
                paths=[CAPITAL_PATH],
                values=[round(r * total, 2) for r in ratios],
            )
        ],
        seeds=SeedRange(count=seeds, start=SEED_START),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scenario", type=Path, default=Path("scenarios/calibrated-baseline.yaml"))
    p.add_argument("--ratios", default="0.5,0.75,1.0,1.25,1.5,2.0")
    p.add_argument("--seeds", type=int, default=8)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--dry-run", action="store_true", help="List the cells and exit")
    args = p.parse_args(argv)
    ratios = [float(r) for r in args.ratios.split(",")]
    spec = spec_for(args.scenario, ratios, args.seeds)
    total = resources(args.scenario)

    seeds = spec.seed_list()
    print(
        f"probe_boundary: scenario={args.scenario} budget+reserves={total:,.0f} "
        f"ratios={len(ratios)} seeds={len(seeds)} ({seeds[0]}..{seeds[-1]}) "
        f"cells={len(ratios) * len(seeds)}"
    )
    budget, deliv = deliverable(args.scenario)
    print(
        f"deliverable reserves = {deliv:,.0f}; F-06 predicted flip ratio = "
        f"(budget + deliverable) / (budget + reserves) = {(budget + deliv) / total:.3f}"
    )
    if args.dry_run:
        for r, c in zip(ratios, spec.linked_axes[0].values, strict=True):
            print(f"ratio {r:g}: capital {c:,.2f}")
        return 0

    sweep_dir = run_sweep(spec, args.output, workers=args.workers)
    mc = pd.read_parquet(aggregate_mc(sweep_dir))
    mc["ratio"] = (mc["attacker_capital"] / total).round(4)
    mc["ratio_deliverable"] = (mc["attacker_capital"] / (budget + deliv)).round(4)
    print(mc[COLUMNS].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
