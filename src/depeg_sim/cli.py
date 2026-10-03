"""Command-line entry point: ``load_scenario -> run_scenario`` (which draws the chart).

Prints three lines (scenario, run outcome, run directory). Exit codes: 0 ok,
2 scenario file missing, 3 scenario invalid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from depeg_sim.experiments.runner import run_scenario
from depeg_sim.kernel.config import load_scenario


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="depeg", description="Run a depeg simulation scenario.")
    p.add_argument("scenario", type=Path, help="Path to a scenario YAML file")
    p.add_argument(
        "--output", type=Path, default=Path("output"), help="Parent directory for run output"
    )
    p.add_argument("--seed", type=int, default=None, help="Override scenario seed")
    p.add_argument("--no-chart", action="store_true", help="Skip peg_trajectory.png")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.scenario.exists():
        print(f"error: scenario not found: {args.scenario}", file=sys.stderr)
        return 2
    try:
        cfg = load_scenario(args.scenario)
    except (ValidationError, yaml.YAMLError) as exc:
        print(f"error: invalid scenario {args.scenario}:\n{exc}", file=sys.stderr)
        return 3
    seed = cfg.seed if args.seed is None else args.seed
    print(f"depeg-sim: scenario={cfg.name} seed={seed} hash={cfg.content_hash()[:12]}")
    run = run_scenario(
        cfg, seed_override=args.seed, output_dir=args.output, chart=not args.no_chart
    )
    s = run.summary
    depeg = "none" if s["max_depeg_bps"] is None else f"{s['max_depeg_bps']:.1f}"
    print(
        f"run: steps={s['steps_run']} terminated_by={s['terminated_by']} "
        f"max_depeg_bps={depeg} reserves_exhausted={s['reserves_exhausted']}"
    )
    print(f"wrote: {run.run_dir}")
    return 0
