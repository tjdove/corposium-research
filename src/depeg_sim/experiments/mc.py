"""Monte Carlo aggregation: per-grid-point distributions over seeds.

``aggregate_mc(sweep_dir)`` reads ``sweep.parquet`` (one row per run) and writes
``mc.parquet`` (one row per grid point). Grid points are the distinct combinations of
the **axis columns**, which are read from the sweep manifest's resolved ``axes`` list
(linked-axis names and ordinary axis paths, in expansion order), never guessed from the
DataFrame. ``seed`` and ``index`` are never group keys.

Columns, in this fixed order::

    <axis columns, spec order>, n,
    for m in METRICS:  m_mean, m_std, m_p05, m_p50, m_p95 [, m_n if m in NULLABLE]
    p_reserves_exhausted, p_reserves_exhausted_lo, p_reserves_exhausted_hi,
    p_reserves_exhausted_term, p_peg_recovered, p_max_steps

Statistics use only non-null values (a metric is null where it has no meaning, e.g.
``steps_to_sustained_recovery`` on a run that never recovered). ``std`` uses
``ddof=1`` and is NaN with fewer than 2 values. Percentiles are
``numpy.percentile(method="linear")``. ``m_n`` counts the non-null values of a nullable
metric. A metric absent from ``sweep.parquet`` (a sweep run before Story 2.7 added the
bought-stable and holder columns) aggregates to NaN. ``p_reserves_exhausted`` is the
share of runs whose ``reserves_exhausted`` flag is set, with Wilson 95% bounds. The three
``terminated_by`` shares sum to 1. Rows are sorted by the axis columns in spec order.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from depeg_sim.analysis.stats import wilson
from depeg_sim.experiments.sweep import SWEEP_MANIFEST, SWEEP_PARQUET

MC_PARQUET = "mc.parquet"

METRICS: tuple[str, ...] = (
    "max_depeg_bps",
    "step_of_max_depeg",
    "final_depeg_bps",
    "steps_to_first_band_entry",
    "steps_to_sustained_recovery",
    "steps_run",
    "redemption_paid_total",
    "defender_spent",
    "defender_interventions",
    "attacker_pnl",
    "arbitrageur_pnl",
    "defender_bought_stable",
    "holder_bought_stable",
    "holder_pnl",
)
NULLABLE = frozenset({"steps_to_first_band_entry", "steps_to_sustained_recovery"})
STATS = ("mean", "std", "p05", "p50", "p95")
TERMINATIONS = (
    ("p_reserves_exhausted_term", "reserves_exhausted"),
    ("p_peg_recovered", "peg_recovered"),
    ("p_max_steps", "max_steps"),
)


def axis_columns(manifest: dict) -> list[str]:
    """Axis column names from a sweep manifest, in expansion (spec) order."""
    return [axis["name"] for axis in manifest["axes"]]


def _metric_stats(values: pd.Series | None) -> dict[str, float]:
    if values is None:  # a sweep.parquet written before the metric existed
        return dict.fromkeys(STATS, np.nan)
    v = pd.to_numeric(values, errors="coerce").to_numpy(dtype="float64")
    v = v[~np.isnan(v)]
    if v.size == 0:
        return dict.fromkeys(STATS, np.nan)
    p05, p50, p95 = np.percentile(v, [5, 50, 95], method="linear")
    return {
        "mean": float(v.mean()),
        "std": float(v.std(ddof=1)) if v.size >= 2 else np.nan,
        "p05": float(p05),
        "p50": float(p50),
        "p95": float(p95),
    }


def _grid_point(runs: pd.DataFrame) -> dict[str, float]:
    row: dict[str, float] = {"n": len(runs)}
    for m in METRICS:
        stats = _metric_stats(runs.get(m))
        row |= {f"{m}_{s}": stats[s] for s in STATS}
        if m in NULLABLE:
            row[f"{m}_n"] = int(pd.to_numeric(runs[m], errors="coerce").notna().sum())
    k = int(runs["reserves_exhausted"].astype(bool).sum())
    lo, hi = wilson(k, len(runs))
    row |= {
        "p_reserves_exhausted": k / len(runs),
        "p_reserves_exhausted_lo": lo,
        "p_reserves_exhausted_hi": hi,
    }
    for col, reason in TERMINATIONS:
        row[col] = float((runs["terminated_by"] == reason).mean())
    return row


def aggregate_mc(sweep_dir: Path) -> Path:
    """Aggregate ``sweep_dir/sweep.parquet`` into ``sweep_dir/mc.parquet``."""
    sweep_dir = Path(sweep_dir)
    manifest = json.loads((sweep_dir / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    axes = axis_columns(manifest)
    runs = pd.read_parquet(sweep_dir / SWEEP_PARQUET)
    missing = [c for c in axes if c not in runs.columns]
    if missing:
        raise ValueError(f"{sweep_dir / SWEEP_PARQUET} lacks axis columns {missing}")

    rows = []
    if axes:
        for key, group in runs.groupby(axes, sort=True, dropna=False):
            key = key if isinstance(key, tuple) else (key,)
            rows.append(dict(zip(axes, key, strict=True)) | _grid_point(group))
    else:
        rows.append(_grid_point(runs))
    mc = pd.DataFrame(rows)
    out = sweep_dir / MC_PARQUET
    mc.to_parquet(out, index=False, engine="pyarrow")
    return out


def aggregate_and_report(sweep_dir: Path) -> Path:
    """``aggregate_mc`` plus the two CLI lines."""
    out = aggregate_mc(sweep_dir)
    manifest = json.loads((Path(sweep_dir) / SWEEP_MANIFEST).read_text(encoding="utf-8"))
    mc = pd.read_parquet(out)
    seeds = len(manifest["seeds"])
    print(
        f"mc: {manifest['sweep_name']} grid_points={len(mc)} seeds={seeds} "
        f"runs={int(mc['n'].sum())}"
    )
    print(f"wrote: {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="depeg-mc", description="Aggregate a sweep over seeds.")
    p.add_argument("sweep_dir", type=Path, help="A sweep output directory")
    args = p.parse_args(argv)
    for name in (SWEEP_PARQUET, SWEEP_MANIFEST):
        if not (args.sweep_dir / name).is_file():
            print(f"error: {args.sweep_dir / name} not found", file=sys.stderr)
            return 2
    try:
        aggregate_and_report(args.sweep_dir)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot aggregate {args.sweep_dir}: {exc!r}", file=sys.stderr)
        return 3
    return 0
