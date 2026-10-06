"""Attacker-multiple scan on the 1992 analogue (Story 3.3 AC 4).

Replaces the scratch scan scripts of Stories 2.5, 2.6 and 3.1. Varies the attacker on
``soros-1992`` as ``capital = multiple x QUANTUM`` (Quantum's ~$10bn short in model units,
so the committed 6x is 255,754,476) over ``--range start:stop:step`` (inclusive), one seed,
with the holder's capital and exit rule set by ``--holder-capital`` and ``--exit``. Runs it
with ``run_sweep`` and prints one row per multiple and the flip.

The **flip** is the smallest scanned multiple from which every larger scanned multiple
exhausts reserves (``reserves_exhausted``); multiples below it that exhaust anyway are
listed separately (F-07's isolated exhaustions). No flip if the largest multiple does not
exhaust. ``ratio = capital / (defender budget + redemption reserves)``.

``--exit none`` (default) is the holder that never sells. ``--dry-run`` prints the cells
and exits without running.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from depeg_sim.experiments.sweep import LinkedAxis, SweepSpec, run_sweep
from depeg_sim.kernel.config import load_scenario

QUANTUM = 42_625_746  # soros-1992.yaml: Quantum's ~$10bn short; the scenario is 6x this
CAPITAL_PATH = "agents[type=attacker].capital"
HOLDER_CAPITAL = "agents[type=holder].capital"
HOLDER_EXIT = "agents[type=holder].exit_discount_pct"
COLUMNS = [
    "multiple",
    "ratio",
    "terminated_by",
    "steps_run",
    "max_depeg_bps",
    "final_depeg_bps",
    "redemption_paid_total",
    "holder_bought_stable",
    "holder_pnl",
]


def multiples(spec: str) -> list[float]:
    """``start:stop:step`` -> the inclusive grid, rounded to 6 places (no float drift)."""
    start, stop, step = (float(x) for x in spec.split(":"))
    if not step > 0 or stop < start:
        raise ValueError(f"bad --range {spec!r}: need start <= stop and step > 0")
    n = int(round((stop - start) / step))
    return [round(start + i * step, 6) for i in range(n + 1)]


def parse_exit(value: str) -> float | None:
    return None if value.lower() in {"none", "null"} else float(value)


def flip(df: pd.DataFrame) -> tuple[float | None, list[float]]:
    """``(flip multiple, isolated exhaustions below it)`` from rows sorted by multiple."""
    df = df.sort_values("multiple")
    exhausted = df["reserves_exhausted"].astype(bool).tolist()
    ms = df["multiple"].tolist()
    if not exhausted or not exhausted[-1]:
        return None, [m for m, e in zip(ms, exhausted, strict=True) if e]
    i = len(ms) - 1
    while i > 0 and exhausted[i - 1]:
        i -= 1
    return ms[i], [m for m, e in zip(ms[:i], exhausted[:i], strict=True) if e]


def _slug(x: float | None) -> str:
    return "none" if x is None else f"{x:g}"


def spec_for(
    scenario: Path, ms: list[float], holder_capital: float | None, exit_: float | None, seed: int
) -> SweepSpec:
    overrides: dict = {HOLDER_EXIT: exit_}
    if holder_capital is not None:
        overrides[HOLDER_CAPITAL] = holder_capital
    cap = "base" if holder_capital is None else f"{holder_capital:.0f}"
    return SweepSpec(
        version=1,
        name=f"scan-1992-h{cap}-x{_slug(exit_)}-s{seed}",
        base=scenario,
        linked_axes=[
            LinkedAxis(name="multiple", paths=[CAPITAL_PATH], values=ms, scales=[QUANTUM])
        ],
        seeds=[seed],
        overrides=overrides,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scenario", type=Path, default=Path("scenarios/soros-1992.yaml"))
    p.add_argument("--holder-capital", type=float, default=None, help="default: the scenario's")
    p.add_argument("--exit", default="none", help="exit_discount_pct, or 'none' (never sells)")
    p.add_argument("--range", default="4.0:7.0:0.1", help="start:stop:step, inclusive")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--dry-run", action="store_true", help="List the cells and exit")
    args = p.parse_args(argv)
    ms = multiples(args.range)
    exit_ = parse_exit(args.exit)
    spec = spec_for(args.scenario, ms, args.holder_capital, exit_, args.seed)

    cfg = load_scenario(args.scenario)
    defender = next(a for a in cfg.agents if a.type == "defender")
    holder = next(a for a in cfg.agents if a.type == "holder")
    total = defender.budget + cfg.redemption.reserves
    h_cap = holder.capital if args.holder_capital is None else args.holder_capital
    print(
        f"scan_1992: scenario={args.scenario} holder_capital={h_cap:,.0f} "
        f"exit_discount_pct={_slug(exit_)} seed={args.seed} multiples={len(ms)} "
        f"({ms[0]:g}..{ms[-1]:g}) budget+reserves={total:,.0f}"
    )
    if args.dry_run:
        for m in ms:
            print(f"multiple {m:g}: capital {m * QUANTUM:,.2f} ratio {m * QUANTUM / total:.3f}")
        return 0

    sweep_dir = run_sweep(spec, args.output, workers=args.workers)
    df = pd.read_parquet(sweep_dir / "sweep.parquet")
    df["ratio"] = (df["multiple"] * QUANTUM / total).map("{:.3f}".format)
    print(df[COLUMNS].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    at, isolated = flip(df)
    if at is None:
        print(f"flip: none in {ms[0]:g}..{ms[-1]:g} (the largest multiple does not exhaust)")
    else:
        print(f"flip: {at:g} (ratio {at * QUANTUM / total:.3f})")
    print(f"exhausted below the flip: {', '.join(f'{m:g}' for m in isolated) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
