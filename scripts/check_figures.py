"""Stale-figure guard (Story 2.9 AC 4; code hash Story 3.5 AC 3).

Recomputes the source hash of every figure in ``docs/figures/manifest.json`` and compares
it with the hash recorded when the figure was made. A figure is stale when the scenario
or sweep it was made from has changed since. Exit 0 if every figure is current; exit 1
naming each stale figure (and each figure whose PNG or source is missing).

The manifest's top-level ``code_hash`` (``code_hash()``: sha256 over the package source,
``src/depeg_sim/**/*.py``) is compared too, but a mismatch only **warns**: the figures
were drawn by other code, which may or may not change their numbers (a docstring edit
does not). The warning names both hashes and exits 0; with ``GITHUB_ACTIONS`` set it is
also a ``::warning::`` annotation. The hard gate for code is the freeze checklist in
``docs/REPRODUCIBILITY.md`` (``make figures``, then a guard with no warning).

Source hash: ``content_hash()`` for a scenario (``scenarios/*.yaml``); ``sweep_spec_hash``
for a sweep (``sweeps/*.yaml``). The guard never runs a scenario or a sweep and never
compares PNG bytes: matplotlib output is not byte-stable across versions and platforms.
``make figures-quick`` is the separate smoke test that the pipeline still executes.

Fit records (Story 4.1): every ``docs/calibration/fits/*.json`` written by a fit script's
``--write`` is checked with ``fit_record.check_fit``: a scenario or data file whose hash
no longer matches the record, or a missing input, fails like a stale figure; a changed
fit script only warns, like the code hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from fit_record import FITS, check_fits

MANIFEST = Path("docs/figures/manifest.json")
CODE_HASH = "code_hash"  # top-level manifest key; every other key is a figure
PACKAGE = Path("src/depeg_sim")


def code_hash(package: Path = PACKAGE) -> str:
    """sha256 over every ``*.py`` under ``package`` in sorted relative-path order, each
    file contributing its relative POSIX path, a NUL, its bytes and a NUL (so a rename or
    a moved line between files changes the hash)."""
    package = Path(package)
    h = hashlib.sha256()
    for path in sorted(package.rglob("*.py"), key=lambda p: p.relative_to(package).as_posix()):
        h.update(path.relative_to(package).as_posix().encode("utf-8") + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def figures_of(manifest: dict) -> dict[str, dict]:
    return {name: entry for name, entry in manifest.items() if name != CODE_HASH}


def code_warning(manifest: dict, package: Path = PACKAGE) -> str | None:
    """The warning for a code-hash mismatch (or a manifest with none); None when equal."""
    recorded, now = manifest.get(CODE_HASH), code_hash(package)
    if recorded == now:
        return None
    was = "no code_hash" if recorded is None else f"code_hash {recorded}"
    return (
        f"WARNING: figures were drawn by other code: manifest has {was}, "
        f"{PACKAGE}/**/*.py now hashes to {now}. Numbers may differ; run `make figures` "
        "before the freeze (docs/REPRODUCIBILITY.md)"
    )


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
    figures = figures_of(json.loads(manifest_path.read_text(encoding="utf-8")))
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
            what = " or its base scenario" if is_sweep(source) else ""
            problems.append(
                f"{name}: STALE, {source}{what} changed (manifest {entry['source_hash'][:12]}, "
                f"now {now[:12]}); regenerate with `make figures`"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--fits", type=Path, default=FITS)
    args = p.parse_args(argv)
    if not args.manifest.is_file():
        print(f"figures-check: {args.manifest} not found", file=sys.stderr)
        return 1
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    n = len(figures_of(manifest))
    warning = code_warning(manifest)
    fit_problems, fit_warnings, n_fits = check_fits(args.fits)
    for line in ([warning] if warning else []) + fit_warnings:
        print(f"figures-check: {line}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title=figures-check::{line}")
    problems = stale_figures(args.manifest) + fit_problems
    if problems:
        for line in problems:
            print(f"figures-check: {line}", file=sys.stderr)
        print(
            f"figures-check: FAIL, {len(problems)} problem(s) in {n} figures and {n_fits} fits",
            file=sys.stderr,
        )
        return 1
    code = "code differs, see warning" if warning else "code_hash matches"
    fits = "a fit script differs, see warning" if fit_warnings else "script hashes match"
    print(f"figures-check: ok, {n} figures match their sources ({code})")
    print(f"figures-check: ok, {n_fits} fits match their inputs ({fits})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
