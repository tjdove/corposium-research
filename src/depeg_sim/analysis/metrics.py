"""Per-step metrics: one flat row per recorded step, collected in ``METRIC_UPDATE``.

The collector is a read-only hook. It is registered **last** (after the agents), so
within ``METRIC_UPDATE`` it runs after every agent's ``settle`` and sees settled
balances. It never emits actions or events and never mutates anything.

A row is recorded when ``step % record_every == 0``. Columns are fixed (``COLUMNS``).
Agent columns use the first registered agent of each type; a missing module, agent or
unpublished oracle price gives ``NaN``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pandas as pd

from depeg_sim.agents.base import Agent
from depeg_sim.kernel.interfaces import Subsystem
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

COLUMNS: tuple[str, ...] = (
    "step",
    "elapsed_seconds",
    "reference_price",
    "oracle_price",
    "amm_price",
    "peg_deviation",
    "amm_reserve_stable",
    "amm_reserve_reference",
    "redemption_reserves",
    "redemption_queue_depth",
    "redemption_queued_total",
    "attacker_stable",
    "attacker_reference",
    "attacker_pnl",
    "arbitrageur_pnl",
    "defender_reference",
    "defender_spent",
    "defender_pnl",
)

INT_COLUMNS = frozenset({"step", "elapsed_seconds"})
NAN = math.nan


def _num(x: Any) -> float:
    return NAN if x is None else float(x)


def first_agent(ctx: RunContext, agent_type: str) -> Agent | None:
    for sub in ctx.registry.all():
        if isinstance(sub, Agent) and sub.type == agent_type:
            return sub
    return None


class MetricsCollector(Subsystem):
    def __init__(self, record_every: int = 1, name: str = "metrics") -> None:
        if isinstance(record_every, bool) or not isinstance(record_every, int) or record_every < 1:
            raise ValueError(f"record_every must be an int >= 1, got {record_every!r}")
        self.name = name
        self.phases = frozenset({Phase.METRIC_UPDATE})
        self.record_every = record_every
        self.rows: list[dict[str, float]] = []

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        if ctx.clock.step_index % self.record_every == 0:
            self.rows.append(self.collect(ctx))

    def collect(self, ctx: RunContext) -> dict[str, float]:
        reg = ctx.registry

        def get(name: str) -> Any | None:
            return reg.get(name) if name in reg else None

        env, oracle, amm, red = get("environment"), get("oracle"), get("amm"), get("redemption")
        atk = first_agent(ctx, "attacker")
        arb = first_agent(ctx, "arbitrageur")
        dfn = first_agent(ctx, "defender")
        has_amm = amm is not None
        row = {
            "step": ctx.clock.step_index,
            "elapsed_seconds": ctx.clock.elapsed_seconds,
            "reference_price": NAN if env is None else env.price,
            "oracle_price": NAN if oracle is None else _num(oracle.price),
            "amm_price": amm.spot_price if has_amm else NAN,
            "peg_deviation": amm.peg_deviation if has_amm else NAN,
            "amm_reserve_stable": amm.reserve_stable if has_amm else NAN,
            "amm_reserve_reference": amm.reserve_reference if has_amm else NAN,
            "redemption_reserves": NAN if red is None else red.reserves,
            "redemption_queue_depth": NAN if red is None else red.queue_depth,
            "redemption_queued_total": NAN if red is None else red.queued_total,
            "attacker_stable": NAN if atk is None else atk.balances["stable"],
            "attacker_reference": NAN if atk is None else atk.balances["reference"],
            "attacker_pnl": atk.pnl(ctx) if atk is not None and has_amm else NAN,
            "arbitrageur_pnl": arb.pnl(ctx) if arb is not None and has_amm else NAN,
            "defender_reference": NAN if dfn is None else dfn.balances["reference"],
            "defender_spent": NAN if dfn is None else dfn.spent,
            "defender_pnl": dfn.pnl(ctx) if dfn is not None and has_amm else NAN,
        }
        return {k: int(v) if k in INT_COLUMNS else float(v) for k, v in row.items()}

    def to_dataframe(self) -> pd.DataFrame:
        """Rows as a DataFrame: ``step`` and ``elapsed_seconds`` int64, the rest float64."""
        df = pd.DataFrame(self.rows, columns=list(COLUMNS))
        return df.astype({c: "int64" if c in INT_COLUMNS else "float64" for c in COLUMNS})

    def snapshot(self) -> dict:
        return {"rows": len(self.rows)}
