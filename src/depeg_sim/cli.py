"""Command-line entry point.

Loads and validates the scenario (Story 1.2), then reports that the kernel is not
yet implemented. Story 1.8 wires it to the engine.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from depeg_sim.kernel.config import load_scenario


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
    print(f"depeg-sim: scenario={cfg.name} seed={cfg.seed} hash={cfg.content_hash()[:12]}")
    print("kernel not implemented yet (see docs/epics.md, Story 1.3)")
    return 0
