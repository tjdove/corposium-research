"""Command-line entry point.

Loads and validates the scenario (Story 1.2) and runs the kernel (Story 1.3) with
no subsystems registered, so only ``max_steps`` can fire. Story 1.8 registers the
protocol modules and agents and writes run output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from depeg_sim.kernel.config import load_scenario
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="depeg", description="Run a depeg simulation scenario.")
    p.add_argument("scenario", type=Path, help="Path to a scenario YAML file")
    p.add_argument("--output", type=Path, default=Path("output"), help="Output directory")
    p.add_argument("--seed", type=int, default=None, help="Override scenario seed")
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
    ctx = RunContext.from_config(cfg, seed_override=args.seed)
    print(f"depeg-sim: scenario={cfg.name} seed={ctx.seed} hash={cfg.content_hash()[:12]}")
    result = Engine(ctx).run()
    print(f"run: steps={result.steps_run} terminated_by={result.terminated_by}")
    return 0
