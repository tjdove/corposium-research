"""Single-run primitive: scenario config in, run directory out.

``build_world`` registers subsystems in a fixed order, which is also their call order
within each phase::

    environment, oracle, amm, redemption, <agents in config order>, metrics

Metrics is last so that in ``METRIC_UPDATE`` it sees balances the agents have just
settled. ``run_scenario`` is what Epic 2's sweep runner will call once per point.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from depeg_sim.agents.factory import build_agents
from depeg_sim.analysis.metrics import MetricsCollector
from depeg_sim.analysis.summary import summarize
from depeg_sim.environment.price_process import ReferencePrice
from depeg_sim.experiments.writer import run_id_for, write_run
from depeg_sim.kernel.config import ScenarioConfig
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine, RunResult
from depeg_sim.kernel.interfaces import Subsystem
from depeg_sim.protocol.amm import ConstantProductAMM
from depeg_sim.protocol.oracle import Oracle
from depeg_sim.protocol.redemption import RedemptionModule


@dataclass
class RunArtifacts:
    run_dir: Path
    result: RunResult
    summary: dict
    metrics: pd.DataFrame
    manifest: dict


def build_world(cfg: ScenarioConfig, ctx: RunContext) -> dict[str, Subsystem]:
    """Build and register every subsystem; returns them by name, in registration order."""
    env = ReferencePrice.from_config(cfg.environment)
    oracle = Oracle.from_config(cfg.oracle, source=env)
    amm = ConstantProductAMM.from_config(cfg.amm, peg_price=cfg.redemption.peg_price)
    red = RedemptionModule.from_config(cfg.redemption)
    metrics = MetricsCollector(record_every=cfg.metrics.record_every)
    world: dict[str, Any] = {}
    for sub in (env, oracle, amm, red, *build_agents(cfg), metrics):
        ctx.registry.register(sub)
        world[sub.name] = sub
    return world


def run_scenario(
    cfg: ScenarioConfig,
    *,
    seed_override: int | None = None,
    output_dir: Path,
    chart: bool = True,
) -> RunArtifacts:
    """Run one scenario into ``output_dir/<run_id>/``. An existing directory for the
    same run_id is replaced, so a rerun never mixes old and new files. With ``chart``
    the peg trajectory PNG is drawn too; sweeps pass ``False`` (pyplot is then never
    imported)."""
    seed = cfg.seed if seed_override is None else seed_override
    run_dir = Path(output_dir) / run_id_for(cfg, seed)
    if run_dir.exists():
        shutil.rmtree(run_dir)
    ctx = RunContext.from_config(cfg, seed_override=seed_override, output_dir=run_dir)
    world = build_world(cfg, ctx)
    result = Engine(ctx).run()
    df = world["metrics"].to_dataframe()
    summary = summarize(cfg, result, df, world)
    manifest = write_run(run_dir, cfg, result, df, summary)
    if chart:
        from depeg_sim.analysis.charts import plot_peg_trajectory

        plot_peg_trajectory(run_dir)
    return RunArtifacts(
        run_dir=run_dir, result=result, summary=summary, metrics=df, manifest=manifest
    )
