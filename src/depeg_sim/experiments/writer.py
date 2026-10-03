"""Write one run's artifacts to ``run_dir`` (ADR-0004: files + manifest, no database).

Everything is written once, at the end of the run, from in-memory data::

    timeseries.parquet   metrics rows (pyarrow, no index)
    summary.json         summarize() output (sorted keys, indent 2)
    events.jsonl         one event per line: {step, kind, source, payload}
    decisions.jsonl      one decision per line (only when metrics.trace_decisions)
    manifest.json        provenance; ``files`` lists everything in run_dir at write time
                         (checkpoints included, the chart written afterwards not)

``manifest.json`` also carries ``config``, the resolved scenario, so tools that only
see ``run_dir`` (the chart) can read scenario parameters. Every file except the
manifest's ``created_utc`` is a deterministic function of scenario + seed.
"""

from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from depeg_sim import __version__
from depeg_sim.kernel.config import ScenarioConfig
from depeg_sim.kernel.engine import RunResult
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION

TIMESERIES = "timeseries.parquet"
SUMMARY = "summary.json"
EVENTS = "events.jsonl"
DECISIONS = "decisions.jsonl"
MANIFEST = "manifest.json"


def run_id_for(cfg: ScenarioConfig, seed: int) -> str:
    return f"{cfg.name}-{seed}-{cfg.content_hash()[:8]}"


def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2) + "\n"


def _jsonl(path: Path, records) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


def write_run(
    run_dir: Path,
    cfg: ScenarioConfig,
    result: RunResult,
    metrics_df: pd.DataFrame,
    summary: dict,
) -> dict:
    """Write the run's files and return the manifest."""
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_df.to_parquet(run_dir / TIMESERIES, index=False, engine="pyarrow")
    (run_dir / SUMMARY).write_text(_dump(summary), encoding="utf-8")
    _jsonl(
        run_dir / EVENTS,
        (
            {"step": e.step, "kind": e.kind, "source": e.source, "payload": e.payload}
            for e in result.events
        ),
    )
    if cfg.metrics.trace_decisions:
        _jsonl(
            run_dir / DECISIONS,
            (
                {
                    "step": d.step,
                    "agent_id": d.agent_id,
                    "rule": d.rule,
                    "observed": d.observed,
                    "action": d.action,
                }
                for d in result.decisions
            ),
        )
    files = sorted(p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file())
    seed = summary["seed"]
    manifest = {
        "run_id": run_id_for(cfg, seed),
        "scenario_name": cfg.name,
        "scenario_hash": cfg.content_hash(),
        "seed": seed,
        "phase_order_version": PHASE_ORDER_VERSION,
        "package_version": __version__,
        "python_version": platform.python_version(),
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": sorted({*files, MANIFEST}),
        "config": cfg.model_dump(mode="json"),
    }
    (run_dir / MANIFEST).write_text(_dump(manifest), encoding="utf-8")
    return manifest
