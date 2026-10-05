"""Regenerate every committed figure in ``docs/figures/`` from its named source (Story 2.9).

Scenario figures run their scenario here (seconds each). Sweep figures read the sweep's
output directory, ``<sweeps-dir>/<spec name>/`` (``mc.parquet`` + ``manifest.json``),
which ``make figures`` produces first with ``python -m depeg_sim.sweep <spec> --mc``. A
sweep directory whose manifest ``spec_hash`` is missing or differs from
``sweep_spec_hash(spec)`` is refused before anything is written: it was run from another
spec or another base scenario.

Writes ``docs/figures/<file>`` for each figure and ``docs/figures/manifest.json``::

    {"<figure>": {"file", "source", "source_hash", "function", "commit"}}

``source_hash`` is ``check_figures.source_hash`` (the guard recomputes it); ``commit`` is
``git rev-parse HEAD`` at generation time, suffixed ``-dirty`` if code or inputs differ
from it.

``--quick`` is a smoke test, not a regeneration: every sweep runs with
``seeds: {count: 2}`` into a temporary directory, every figure is drawn there, and the
only thing written to ``docs/figures/`` is the gitignored ``quick-ok`` marker.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from check_figures import MANIFEST, is_sweep, source_hash

from depeg_sim.analysis import charts
from depeg_sim.experiments.mc import aggregate_mc
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.sweep import (
    SWEEP_MANIFEST,
    SeedRange,
    load_sweep,
    run_sweep,
    sweep_spec_hash,
)
from depeg_sim.kernel.config import load_scenario

FIGURES_DIR = MANIFEST.parent
QUICK_MARKER = FIGURES_DIR / "quick-ok"
QUICK_SEEDS = 2
INPUTS = ("src", "scenarios", "sweeps", "scripts", "data", "pyproject.toml")


def _peg(run_dir: Path) -> Path:
    return Path(run_dir) / charts.PEG_TRAJECTORY  # drawn by run_scenario(chart=True)


@dataclass(frozen=True)
class Figure:
    file: str
    source: str
    function: Callable[[Path], Path]

    @property
    def name(self) -> str:
        return Path(self.file).stem

    @property
    def function_name(self) -> str:
        fn = charts.plot_peg_trajectory if self.function is _peg else self.function
        return f"{fn.__module__}.{fn.__name__}"


FIGURES = (
    Figure("peg_trajectory_baseline.png", "scenarios/soros-baseline.yaml", _peg),
    Figure("peg_trajectory_calibrated.png", "scenarios/calibrated-baseline.yaml", _peg),
    Figure("peg_trajectory_1992.png", "scenarios/soros-1992.yaml", _peg),
    Figure("peg_trajectory_1992_no_defense.png", "scenarios/soros-1992-no-defense.yaml", _peg),
    Figure(
        "validation_overlay_usdc_2023.png",
        "scenarios/usdc-2023.yaml",
        charts.plot_validation_overlay,
    ),
    Figure(
        "threshold_surface.png",
        "sweeps/threshold-surface-ref-mc.yaml",
        charts.plot_threshold_surface,
    ),
    Figure(
        "time_to_parity.png", "sweeps/threshold-surface-ref-mc.yaml", charts.plot_time_to_parity
    ),
    Figure(
        "threshold_surface_par.png",
        "sweeps/threshold-surface-mc.yaml",
        charts.plot_threshold_surface,
    ),
    Figure("budget_depth.png", "sweeps/budget-x-depth-mc.yaml", charts.plot_budget_depth),
    Figure("oracle_sensitivity.png", "sweeps/oracle-lag-mc.yaml", charts.plot_oracle_sensitivity),
)


def git_commit() -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *INPUTS], capture_output=True, text=True, check=True
    ).stdout.strip()
    return f"{head}-dirty" if dirty else head


def check_sweep_dirs(sweeps_dir: Path) -> list[str]:
    """Problems with the sweep outputs the full run would plot; empty if all match."""
    problems = []
    for spec_path in sorted({f.source for f in FIGURES if is_sweep(Path(f.source))}):
        sweep_dir = sweeps_dir / load_sweep(spec_path).name
        manifest = sweep_dir / SWEEP_MANIFEST
        if not (sweep_dir / "mc.parquet").is_file() or not manifest.is_file():
            problems.append(f"{sweep_dir}: no mc.parquet/manifest.json; run the sweep with --mc")
            continue
        recorded = json.loads(manifest.read_text(encoding="utf-8")).get("spec_hash")
        expected = sweep_spec_hash(spec_path)
        if recorded != expected:
            problems.append(
                f"{sweep_dir}: spec_hash {str(recorded)[:12]} does not match {spec_path} "
                f"({expected[:12]}); rerun `python -m depeg_sim.sweep {spec_path} --mc`"
            )
    return problems


def render(fig: Figure, work: Path, sweeps_dir: Path) -> Path:
    """Draw one figure; returns the PNG path (inside ``work`` or the sweep directory)."""
    if is_sweep(Path(fig.source)):
        return fig.function(sweeps_dir / load_sweep(fig.source).name)
    run = run_scenario(load_scenario(fig.source), output_dir=work / "runs", chart=True)
    return fig.function(run.run_dir)


def quick_sweeps(work: Path, workers: int) -> Path:
    """Every figure sweep with ``QUICK_SEEDS`` seeds into ``work/sweeps``; aggregated."""
    out = work / "sweeps"
    for spec_path in sorted({f.source for f in FIGURES if is_sweep(Path(f.source))}):
        spec = load_sweep(spec_path)
        start = spec.seeds.start if isinstance(spec.seeds, SeedRange) else spec.seeds[0]
        spec = spec.model_copy(update={"seeds": SeedRange(count=QUICK_SEEDS, start=start)})
        t0 = time.monotonic()
        aggregate_mc(run_sweep(spec, out, workers=workers))
        print(f"quick sweep: {spec.name} ({time.monotonic() - t0:.0f} s)", flush=True)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--quick", action="store_true", help="2-seed smoke test into a temp dir")
    p.add_argument("--sweeps-dir", type=Path, default=Path("output"))
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = p.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="make-figures-") as tmp:
        work = Path(tmp)
        if args.quick:
            sweeps_dir = quick_sweeps(work, args.workers)
        else:
            sweeps_dir = args.sweeps_dir
            problems = check_sweep_dirs(sweeps_dir)
            if problems:
                for line in problems:
                    print(f"make_figures: refused: {line}", file=sys.stderr)
                return 2
        rendered = {}
        for fig in FIGURES:
            rendered[fig] = render(fig, work, sweeps_dir)
            print(f"drew: {fig.file} <- {fig.source}", flush=True)
        if args.quick:
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)
            QUICK_MARKER.write_text("".join(f"{f.file}\n" for f in FIGURES), encoding="utf-8")
            print(f"quick: ok, {len(FIGURES)} figures drawn; wrote {QUICK_MARKER} only")
            return 0

        commit = git_commit()
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        manifest = {}
        for fig, png in rendered.items():
            shutil.copyfile(png, FIGURES_DIR / fig.file)
            manifest[fig.name] = {
                "file": fig.file,
                "source": fig.source,
                "source_hash": source_hash(Path(fig.source)),
                "function": fig.function_name,
                "commit": commit,
            }
    text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    MANIFEST.write_text(text, encoding="utf-8")
    print(f"wrote: {len(manifest)} figures and {MANIFEST} (commit {commit[:12]})")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)  # skip teardown: pyarrow's thread pool can abort there (see depeg_sim.mc)
