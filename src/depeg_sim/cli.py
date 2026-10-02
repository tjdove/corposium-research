"""Command-line entry point.

Story 1.1 ships this as a stub that validates the argument and reports that the
kernel is not yet implemented. Story 1.8 wires it to the engine.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


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
    print(f"depeg-sim: scenario={args.scenario} output={args.output} seed={args.seed}")
    print("kernel not implemented yet (see docs/epics.md, Story 1.3)")
    return 0
