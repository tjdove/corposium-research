"""Parameter sweeps: expand a grid of scenario overrides, run every cell, aggregate.

A sweep spec (``sweeps/<name>.yaml``) names a base scenario and the config paths to vary::

    version: 1
    name: pool-depth-x-attacker
    base: scenarios/soros-baseline.yaml       # relative to the working directory
    linked_axes:                               # several paths moving as one axis
      - name: pool_depth
        paths: [amm.reserve_stable, amm.reserve_reference]
        values: [250000, 500000, 1000000, 2000000]
        scales: [1, 1]                         # optional: path i gets value x scales[i]
    axes:                                      # one path per axis; column name = path
      agents[type=attacker].capital: [100000, 300000, 600000, 1200000]
    seeds: [42]                                # or {count: 16, start: 1000} -> 1000..1015
    overrides: {}                              # fixed path -> value for every cell
    max_steps: 2000                            # optional steps.max_steps override

Paths (``set_path``): ``a.b`` (attribute), ``a[0].b`` (list index) and
``agents[type=attacker].b`` (first list element whose ``type`` matches).

Cells are the Cartesian product of linked axes (spec order), then ordinary axes (spec
order), then seeds; ``index`` counts in that order from 0. Each cell's config is the base
with ``overrides`` applied, then the axis values, then ``max_steps``, then ``seed``, and
``name = f"{spec.name}/{index:04d}"``.

ADR-0013 guard: varying ``amm.fee_bps`` or an arbitrageur ``min_profit_bps`` moves the
arbitrage band, so ``expand`` refuses unless ``termination.peg_recovered.tolerance`` is
also an axis or an override.

Output (``run_sweep``)::

    <output_dir>/<spec.name>/
      manifest.json                      spec, seeds and the resolved base config (ADR-0014)
      sweep.parquet                      one row per cell, sorted by index
      <index:04d>-<seed>-<hash8>/        a normal run directory per cell (no chart)

The cell directory is ``run_scenario``'s own ``<run_id>`` under ``output_dir``: the cell's
``name`` already starts with ``<spec.name>/<index:04d>``. Workers use a ``spawn`` pool;
``workers=1`` runs in-process. Aggregation always reads each cell's ``summary.json``
from disk, so ``sweep.parquet`` is byte-identical for any worker count.
"""

from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing
import platform
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from depeg_sim import __version__
from depeg_sim.analysis.summary import SUMMARY_KEYS
from depeg_sim.experiments.runner import run_scenario
from depeg_sim.experiments.writer import SUMMARY, run_id_for
from depeg_sim.kernel.config import ScenarioConfig, load_scenario

SWEEP_PARQUET = "sweep.parquet"
SWEEP_MANIFEST = "manifest.json"
TOLERANCE_PATH = "termination.peg_recovered.tolerance"


class SweepPathError(ValueError):
    """A config path that does not resolve."""


class SweepSpecError(ValueError):
    """A sweep spec that is well-formed but not allowed."""


# -- set_path -------------------------------------------------------------------------

_SEGMENT = re.compile(r"([A-Za-z_]\w*)(?:\[(?:(\d+)|type=([A-Za-z_]\w*))\])?")


def _parse(path: str) -> list[tuple[str, int | None, str | None]]:
    segs = []
    for part in path.split("."):
        m = _SEGMENT.fullmatch(part)
        if m is None:
            raise SweepPathError(f"bad config path {path!r}: cannot parse segment {part!r}")
        name, idx, typ = m.groups()
        segs.append((name, None if idx is None else int(idx), typ))
    return segs


def _set(obj: Any, segs: list, value: Any, path: str) -> Any:
    (name, idx, typ), rest = segs[0], segs[1:]
    if not isinstance(obj, BaseModel) or name not in type(obj).model_fields:
        raise SweepPathError(f"unknown config path {path!r}: no field {name!r}")
    child = getattr(obj, name)
    if idx is None and typ is None:
        new_child = _set(child, rest, value, path) if rest else value
    else:
        if not isinstance(child, list):
            raise SweepPathError(f"unknown config path {path!r}: {name!r} is not a list")
        if typ is not None:
            i = next((k for k, x in enumerate(child) if getattr(x, "type", None) == typ), None)
        else:
            i = idx if idx < len(child) else None
        if i is None:
            sel = idx if typ is None else f"type={typ}"
            raise SweepPathError(f"unknown config path {path!r}: no element {name}[{sel}]")
        new_child = list(child)
        new_child[i] = _set(child[i], rest, value, path) if rest else value
    if not rest and idx is None and typ is None:
        # Leaf attribute: validate (and coerce) the value through the parent's model.
        return type(obj).model_validate({**dict(obj), name: new_child})
    return obj.model_copy(update={name: new_child})


def set_path(cfg: ScenarioConfig, path: str, value: Any) -> ScenarioConfig:
    """A new config with ``path`` set to ``value``; ``cfg`` is unchanged. Raises
    ``SweepPathError`` for a path that does not resolve and ``pydantic.ValidationError``
    for a value the model rejects."""
    new = _set(cfg, _parse(path), value, path)
    return ScenarioConfig.model_validate(new.model_dump())  # re-run model validators


# -- spec ---------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LinkedAxis(_Strict):
    """Several paths moving as one axis. ``scales`` (optional, one per path, all > 0)
    sets path ``i`` to ``value * scales[i]``; omitted means every path gets ``value``
    unchanged. A scale of exactly 1 leaves the value untouched (no int -> float).
    ``expand`` checks the length and sign (``SweepSpecError``)."""

    name: str
    paths: list[str] = Field(min_length=1)
    values: list[Any] = Field(min_length=1)
    scales: list[float] | None = None

    def path_values(self, value: Any) -> list[tuple[str, Any]]:
        """``(path, value to set)`` for one axis value."""
        scales = self.scales or [1.0] * len(self.paths)
        return [
            (p, value if sc == 1 else value * sc) for p, sc in zip(self.paths, scales, strict=True)
        ]


class SeedRange(_Strict):
    """``{count: N, start: s}`` in a spec: the seeds ``s, s+1, ..., s+N-1``."""

    count: int = Field(gt=0)
    start: int = Field(default=0, ge=0)


class SweepSpec(_Strict):
    version: Literal[1]
    name: str = Field(pattern=r"^[A-Za-z0-9_.-]+$")
    base: Path
    linked_axes: list[LinkedAxis] = Field(default_factory=list)
    axes: dict[str, list[Any]] = Field(default_factory=dict)
    seeds: list[int] | SeedRange

    @field_validator("seeds")
    @classmethod
    def _non_empty(cls, v: list[int] | SeedRange) -> list[int] | SeedRange:
        if isinstance(v, list) and not v:
            raise ValueError("seeds must not be empty")
        return v

    def seed_list(self) -> list[int]:
        """The expanded seeds, in order."""
        if isinstance(self.seeds, SeedRange):
            return list(range(self.seeds.start, self.seeds.start + self.seeds.count))
        return list(self.seeds)

    overrides: dict[str, Any] = Field(default_factory=dict)
    max_steps: int | None = Field(default=None, gt=0)

    def axis_list(self) -> list[LinkedAxis]:
        """Every axis in expansion order; an ordinary axis is a one-path linked axis."""
        plain = [LinkedAxis(name=p, paths=[p], values=v) for p, v in self.axes.items()]
        return [*self.linked_axes, *plain]


def load_sweep(path: Path) -> SweepSpec:
    with open(path, encoding="utf-8") as f:
        return SweepSpec.model_validate(yaml.safe_load(f))


@dataclass(frozen=True)
class SweepCell:
    index: int
    seed: int
    axis_values: dict[str, Any]
    config: ScenarioConfig


def _moves_arb_band(path: str) -> bool:
    return path == "amm.fee_bps" or (path.startswith("agents") and path.endswith(".min_profit_bps"))


def _check_adr_0013(spec: SweepSpec, base: ScenarioConfig) -> None:
    touched = [p for a in spec.axis_list() for p in a.paths] + list(spec.overrides)
    band = [p for p in touched if _moves_arb_band(p)]
    if band and base.termination.peg_recovered is not None and TOLERANCE_PATH not in touched:
        raise SweepSpecError(
            f"sweep {spec.name!r} varies {', '.join(band)}, which moves the arbitrage band; "
            f"{TOLERANCE_PATH} must also be an axis or an override (ADR-0013), or "
            "peg_recovered becomes unreachable for reasons unrelated to the defense"
        )


def expand(spec: SweepSpec) -> list[SweepCell]:
    base = load_scenario(spec.base)
    _check_adr_0013(spec, base)
    axes = spec.axis_list()
    names = [a.name for a in axes]
    if len(set(names)) != len(names):
        raise SweepSpecError(f"duplicate axis names in sweep {spec.name!r}: {names}")
    for a in axes:
        if a.scales is not None and len(a.scales) != len(a.paths):
            raise SweepSpecError(
                f"linked axis {a.name!r}: {len(a.scales)} scales for {len(a.paths)} paths"
            )
        if a.scales is not None and not all(sc > 0 for sc in a.scales):
            raise SweepSpecError(f"linked axis {a.name!r}: scales must be > 0, got {a.scales}")
    for path, value in spec.overrides.items():
        base = set_path(base, path, value)
    cells = []
    combos = itertools.product(*(a.values for a in axes), spec.seed_list())
    for index, (*values, seed) in enumerate(combos):
        cfg = base
        for axis, value in zip(axes, values, strict=True):
            for path, v in axis.path_values(value):
                cfg = set_path(cfg, path, v)
        if spec.max_steps is not None:
            cfg = set_path(cfg, "steps.max_steps", spec.max_steps)
        cfg = set_path(cfg, "seed", seed)
        cfg = set_path(cfg, "name", f"{spec.name}/{index:04d}")
        cells.append(SweepCell(index, seed, dict(zip(names, values, strict=True)), cfg))
    return cells


# -- running --------------------------------------------------------------------------


def cell_run_dir(cell: SweepCell, output_dir: Path) -> Path:
    return Path(output_dir) / run_id_for(cell.config, cell.seed)


def _run_cell(args: tuple[SweepCell, Path]) -> dict:
    """Worker: one cell, one run directory. Module-level so ``spawn`` can pickle it."""
    cell, output_dir = args
    arts = run_scenario(cell.config, output_dir=output_dir, chart=False)
    return {"index": cell.index, "seed": cell.seed, **cell.axis_values, **arts.summary}


def _row(cell: SweepCell, output_dir: Path) -> dict:
    """``index, seed, <axis columns>, <summary keys in SUMMARY_KEYS order>`` for one cell,
    read from its ``summary.json`` on disk (which is written with sorted keys)."""
    summary = json.loads((cell_run_dir(cell, output_dir) / SUMMARY).read_text(encoding="utf-8"))
    ordered = {k: summary[k] for k in SUMMARY_KEYS if k in summary}
    ordered |= {k: v for k, v in summary.items() if k not in ordered}
    return {"index": cell.index, "seed": cell.seed, **cell.axis_values, **ordered}


def run_sweep(spec: SweepSpec, output_dir: Path, workers: int = 1) -> Path:
    """Run every cell and aggregate. Returns ``output_dir/<spec.name>``, which is
    replaced if it exists."""
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")
    cells = expand(spec)
    output_dir = Path(output_dir)
    sweep_dir = output_dir / spec.name
    if sweep_dir.exists():
        shutil.rmtree(sweep_dir)
    sweep_dir.mkdir(parents=True)
    jobs = [(c, output_dir) for c in cells]
    if workers == 1:
        for job in jobs:
            _run_cell(job)
    else:
        with multiprocessing.get_context("spawn").Pool(workers) as pool:
            pool.map(_run_cell, jobs, chunksize=1)

    df = pd.DataFrame([_row(c, output_dir) for c in cells]).sort_values("index")
    df.to_parquet(sweep_dir / SWEEP_PARQUET, index=False, engine="pyarrow")
    manifest = {
        "sweep_name": spec.name,
        "base_scenario_hash": load_scenario(spec.base).content_hash(),
        "base_config": load_scenario(spec.base).model_dump(mode="json"),
        "axes": [a.model_dump(mode="json", exclude_none=True) for a in spec.axis_list()],
        "seeds": spec.seed_list(),
        "overrides": spec.overrides,
        "max_steps": spec.max_steps,
        "cell_count": len(cells),
        "package_version": __version__,
        "python_version": platform.python_version(),
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    (sweep_dir / SWEEP_MANIFEST).write_text(text, encoding="utf-8")
    return sweep_dir


# -- CLI ----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="depeg-sweep", description="Run a parameter sweep.")
    p.add_argument("spec", type=Path, help="Path to a sweep YAML file")
    p.add_argument("--workers", type=int, default=1, help="Worker processes (default 1)")
    p.add_argument("--output", type=Path, default=Path("output"), help="Parent output directory")
    p.add_argument("--mc", action="store_true", help="Aggregate over seeds into mc.parquet")
    args = p.parse_args(argv)
    if not args.spec.exists():
        print(f"error: sweep spec not found: {args.spec}", file=sys.stderr)
        return 2
    try:
        spec = load_sweep(args.spec)
        if not spec.base.exists():
            print(f"error: base scenario not found: {spec.base}", file=sys.stderr)
            return 2
        cells = expand(spec)
    except (ValidationError, yaml.YAMLError, SweepPathError, SweepSpecError) as exc:
        print(f"error: invalid sweep {args.spec}:\n{exc}", file=sys.stderr)
        return 3
    print(f"sweep: {spec.name} cells={len(cells)} workers={args.workers}")
    sweep_dir = run_sweep(spec, args.output, workers=args.workers)
    print(f"wrote: {sweep_dir / SWEEP_PARQUET}")
    if args.mc:
        from depeg_sim.experiments.mc import aggregate_and_report

        aggregate_and_report(sweep_dir)
    return 0
