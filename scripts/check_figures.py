"""Stale-figure guard (Story 2.9 AC 4).

Recomputes the source hash of every figure in ``docs/figures/manifest.json`` and compares
it with the hash recorded when the figure was made. A figure is stale when the scenario
or sweep it was made from has changed since. Exit 0 if every figure is current; exit 1
naming each stale figure (and each figure whose PNG or source is missing).

Source hash: ``content_hash()`` for a scenario (``scenarios/*.yaml``); ``sweep_spec_hash``
for a sweep (``sweeps/*.yaml``). The guard never runs a scenario or a sweep and never
compares PNG bytes: matplotlib output is not byte-stable across versions and platforms.
``make figures-quick`` is the separate smoke test that the pipeline still executes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MANIFEST = Path("docs/figures/manifest.json")


def is_sweep(source: Path) -> bool:
    return Path(source).parts[0] == "sweeps"


def source_hash(source: Path) -> str:
    """The hash a figure's manifest entry records for its source file."""
    from depeg_sim.experiments.sweep import sweep_spec_hash
    from depeg_sim.kernel.config import load_scenario

    if is_sweep(source):
        return sweep_spec_hash(source)
    return load_scenario(source).content_hash()


def stale_figures(manifest_path: Path) -> list[str]:
    """One line per problem, ``<figure>: <reason>``; empty when every figure is current.
    Figure files resolve against the manifest's directory, sources against the working
    directory (the repo root)."""
    manifest_path = Path(manifest_path)
    figures = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = []
    for name, entry in figures.items():
        source = Path(entry["source"])
        if not (manifest_path.parent / entry["file"]).is_file():
            problems.append(f"{name}: figure file {entry['file']} is missing")
        if not source.is_file():
            problems.append(f"{name}: source {source} is missing")
            continue
        now = source_hash(source)
        if now != entry["source_hash"]:
            problems.append(
                f"{name}: STALE, {source} changed (manifest {entry['source_hash'][:12]}, "
                f"now {now[:12]}); regenerate with `make figures`"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    args = p.parse_args(argv)
    if not args.manifest.is_file():
        print(f"figures-check: {args.manifest} not found", file=sys.stderr)
        return 1
    problems = stale_figures(args.manifest)
    n = len(json.loads(args.manifest.read_text(encoding="utf-8")))
    if problems:
        for line in problems:
            print(f"figures-check: {line}", file=sys.stderr)
        print(f"figures-check: FAIL, {len(problems)} problem(s) in {n} figures", file=sys.stderr)
        return 1
    print(f"figures-check: ok, {n} figures match their sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
