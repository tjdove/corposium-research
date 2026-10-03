"""Run summary: the handful of numbers a reader wants from one run.

Depeg figures are in basis points of ``peg_deviation`` (negative = below peg).
``max_depeg_bps`` is the most negative recorded deviation; ``step_of_max_depeg`` is the
first step where it occurs. ``time_to_recovery_steps`` is the number of steps from
``step_of_max_depeg`` to the first later recorded step with
``abs(peg_deviation) <= termination.peg_recovered.tolerance``; ``None`` if that never
happens or the scenario has no ``peg_recovered`` condition.

Values are plain Python types (no numpy scalars, no NaN) so the summary serialises to
strict JSON. Missing agents give ``None``.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from depeg_sim import __version__
from depeg_sim.agents.base import Agent
from depeg_sim.kernel.config import ScenarioConfig
from depeg_sim.kernel.engine import RunResult
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION

SUMMARY_KEYS: tuple[str, ...] = (
    "scenario",
    "seed",
    "scenario_hash",
    "steps_run",
    "terminated_by",
    "max_depeg_bps",
    "step_of_max_depeg",
    "final_depeg_bps",
    "time_to_recovery_steps",
    "reserves_exhausted",
    "redemption_paid_total",
    "defender_spent",
    "defender_interventions",
    "attacker_pnl",
    "arbitrageur_pnl",
    "phase_order_version",
    "package_version",
)

BPS = 10_000


def _first(world: dict[str, Any], agent_type: str) -> Agent | None:
    for sub in world.values():
        if isinstance(sub, Agent) and sub.type == agent_type:
            return sub
    return None


def _float(x: Any) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) else x


def _seed(result: RunResult) -> int:
    started = next(e for e in result.events if e.kind == "run_started")
    return int(started.payload["seed"])


def summarize(
    cfg: ScenarioConfig, result: RunResult, metrics_df: pd.DataFrame, world: dict[str, Any]
) -> dict:
    dev = metrics_df["peg_deviation"]
    steps = metrics_df["step"]
    max_depeg = step_of_max = final = recovery = None
    if dev.notna().any():
        i = int(dev.idxmin())
        max_depeg = float(dev.loc[i]) * BPS
        step_of_max = int(steps.loc[i])
        final = float(dev.dropna().iloc[-1]) * BPS
        rec = cfg.termination.peg_recovered
        if rec is not None:
            after = metrics_df.loc[(steps > step_of_max) & (dev.abs() <= rec.tolerance), "step"]
            if not after.empty:
                recovery = int(after.iloc[0]) - step_of_max

    red = world.get("redemption")
    atk, arb, dfn = (_first(world, t) for t in ("attacker", "arbitrageur", "defender"))
    return {
        "scenario": cfg.name,
        "seed": _seed(result),
        "scenario_hash": cfg.content_hash(),
        "steps_run": result.steps_run,
        "terminated_by": result.terminated_by,
        "max_depeg_bps": max_depeg,
        "step_of_max_depeg": step_of_max,
        "final_depeg_bps": final,
        "time_to_recovery_steps": recovery,
        "reserves_exhausted": bool(red is not None and red.reserves_exhausted),
        "redemption_paid_total": None if red is None else _float(red.paid_total),
        "defender_spent": None if dfn is None else _float(dfn.spent),
        "defender_interventions": None if dfn is None else dfn.interventions,
        "attacker_pnl": None if atk is None else _float(atk.pnl_last),
        "arbitrageur_pnl": None if arb is None else _float(arb.pnl_last),
        "phase_order_version": PHASE_ORDER_VERSION,
        "package_version": __version__,
    }
