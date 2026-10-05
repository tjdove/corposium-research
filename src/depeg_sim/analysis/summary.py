"""Run summary: the handful of numbers a reader wants from one run.

Depeg figures are in basis points of ``peg_deviation`` (negative = below peg).
``max_depeg_bps`` is the most negative recorded deviation; ``step_of_max_depeg`` is the
first step where it occurs.

Recovery, per ADR-0013 (``tol = termination.peg_recovered.tolerance``):

- ``steps_to_first_band_entry``: steps from ``step_of_max_depeg`` to the first later
  recorded step with ``abs(peg_deviation) <= tol``. This is the first *touch* of the band,
  which can be a brief overshoot (2 steps in the baseline). ``None`` if the band is never
  re-entered or the scenario has no ``peg_recovered`` condition.
- ``steps_to_sustained_recovery``: ``steps_run - peg_recovered.for_steps -
  step_of_max_depeg`` when ``terminated_by == "peg_recovered"``; else ``None``. The run
  ended after holding the band for ``for_steps`` steps, so this counts steps from the trough
  to the start of that final in-band stretch. This is the number the research note quotes.

Both recovery metrics use the criterion's own deviation (Story 2.8): with
``peg_recovered.reference: par`` (default) the band test is on ``peg_deviation`` (AMM vs
par); with ``oracle`` it is on ``amm_price / oracle_price - 1`` (AMM vs the published
oracle price), where a step before the first publish (``oracle_price`` NaN) is out of
band, as in ``termination.check``. ``max_depeg_bps``, ``step_of_max_depeg`` and
``final_depeg_bps`` are always against par.

Values are plain Python types (no numpy scalars, no NaN) so the summary serialises to
strict JSON. Missing agents give ``None``.

``defender_bought_stable`` and ``holder_bought_stable`` are the stable each agent received
from its executed AMM buys (``amount_out``), the first defender and holder in the world.
With ``redemption_paid_total`` they are the three sinks for the attacker's stable at
calibrated scale; Story 2.7's absorbed ratio is ``capital`` over their sum.
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
    "steps_to_first_band_entry",
    "steps_to_sustained_recovery",
    "reserves_exhausted",
    "redemption_paid_total",
    "defender_spent",
    "defender_interventions",
    "attacker_pnl",
    "arbitrageur_pnl",
    "defender_bought_stable",
    "holder_bought_stable",
    "holder_pnl",
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
    max_depeg = step_of_max = final = first_entry = sustained = None
    if dev.notna().any():
        i = int(dev.idxmin())
        max_depeg = float(dev.loc[i]) * BPS
        step_of_max = int(steps.loc[i])
        final = float(dev.dropna().iloc[-1]) * BPS
        rec = cfg.termination.peg_recovered
        if rec is not None:
            crit = dev
            if rec.reference == "oracle":
                crit = metrics_df["amm_price"] / metrics_df["oracle_price"] - 1.0
            in_band = crit.abs() <= rec.tolerance  # NaN (unpublished oracle) -> False
            after = metrics_df.loc[(steps > step_of_max) & in_band, "step"]
            if not after.empty:
                first_entry = int(after.iloc[0]) - step_of_max
            if result.terminated_by == "peg_recovered":
                sustained = result.steps_run - rec.for_steps - step_of_max

    red = world.get("redemption")
    atk, arb, dfn, hld = (
        _first(world, t) for t in ("attacker", "arbitrageur", "defender", "holder")
    )
    return {
        "scenario": cfg.name,
        "seed": _seed(result),
        "scenario_hash": cfg.content_hash(),
        "steps_run": result.steps_run,
        "terminated_by": result.terminated_by,
        "max_depeg_bps": max_depeg,
        "step_of_max_depeg": step_of_max,
        "final_depeg_bps": final,
        "steps_to_first_band_entry": first_entry,
        "steps_to_sustained_recovery": sustained,
        "reserves_exhausted": bool(red is not None and red.reserves_exhausted),
        "redemption_paid_total": None if red is None else _float(red.paid_total),
        "defender_spent": None if dfn is None else _float(dfn.spent),
        "defender_interventions": None if dfn is None else dfn.interventions,
        "attacker_pnl": None if atk is None else _float(atk.pnl_last),
        "arbitrageur_pnl": None if arb is None else _float(arb.pnl_last),
        "defender_bought_stable": None if dfn is None else _float(dfn.bought_stable),
        "holder_bought_stable": None if hld is None else _float(hld.bought_stable),
        "holder_pnl": None if hld is None else _float(hld.pnl_last),
        "phase_order_version": PHASE_ORDER_VERSION,
        "package_version": __version__,
    }
