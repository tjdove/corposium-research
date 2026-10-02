"""Arbitrageur (the market): closes the gap between the AMM and the oracle, late.

Starts holding ``capital`` reference. In ``observe`` it looks for three opportunities,
using the AMM's own ``fee_bps`` (never a hard-coded fee) in the band::

    band = (amm.fee_bps + min_profit_bps) / 10_000
    redeem    if available_stable > 0 and redemption.payout_per_unit > spot
              -> redeem all available stable (preferred to selling on the AMM)
    sell_amm  elif spot > oracle * (1 + band) and available_stable > 0
              -> y = min(available_stable, sqrt(k / oracle) - S)
    buy_amm   if spot < oracle * (1 - band)
              -> x = min(reference, sqrt(k * oracle) - R)

The closed forms move spot exactly to the oracle price when the fee is 0. With a fee
the input is reduced before the curve, so spot slightly undershoots the target; this
is accepted, not solved iteratively.

Latency: each opportunity becomes a plan stamped with the step it was first seen. A
plan executes in ``decide`` once ``plan.step + latency_steps <= step``. Plans form a
FIFO and at most one executes per step. A later observation that sees the same kind
of opportunity refreshes the plan's size but keeps its original step, so latency is
counted from first sight. An observation that no longer sees an opportunity of that
kind drops the plan (the market moved before the arbitrageur reacted). At execution
the size is clamped to the balance held then.

Rules: ``arb_buy_amm``, ``arb_sell_amm``, ``arb_redeem`` (a plan executed),
``arb_waiting_latency`` (plans pending, none ready), ``arb_idle`` (nothing pending).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from depeg_sim.agents.base import DUST, REFERENCE, Agent, action_record
from depeg_sim.kernel.config import ArbitrageurConfig
from depeg_sim.kernel.interfaces import Action

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

BPS = 10_000
BUY_AMM = "buy_amm"
SELL_AMM = "sell_amm"
REDEEM = "redeem"
RULES = {BUY_AMM: "arb_buy_amm", SELL_AMM: "arb_sell_amm", REDEEM: "arb_redeem"}


def _reference_to_reach(k: float, r: float, target: float) -> float:
    """Reference to swap in (fee ignored) to lift spot ``R/S`` to ``target``: R' = sqrt(k*p)."""
    return max(math.sqrt(k * target) - r, 0.0)


def _stable_to_reach(k: float, s: float, target: float) -> float:
    """Stable to swap in (fee ignored) to lower spot ``R/S`` to ``target``: S' = sqrt(k/p)."""
    return max(math.sqrt(k / target) - s, 0.0)


@dataclass
class Plan:
    kind: str
    step: int
    amount: float


class Arbitrageur(Agent):
    type = "arbitrageur"

    def __init__(
        self,
        agent_id: str,
        capital: float,
        min_profit_bps: int,
        latency_steps: int = 0,
        peg_price: float = 1.0,
    ) -> None:
        if not capital > 0:
            raise ValueError(f"capital must be > 0, got {capital}")
        if min_profit_bps < 0:
            raise ValueError(f"min_profit_bps must be >= 0, got {min_profit_bps}")
        if latency_steps < 0:
            raise ValueError(f"latency_steps must be >= 0, got {latency_steps}")
        super().__init__(agent_id, stable=0.0, reference=capital, peg_price=peg_price)
        self.capital = float(capital)
        self.min_profit_bps = min_profit_bps
        self.latency_steps = latency_steps
        self.pending: list[Plan] = []

    @classmethod
    def from_config(cls, cfg: ArbitrageurConfig, peg_price: float = 1.0) -> Arbitrageur:
        return cls(
            agent_id=cfg.id,
            capital=cfg.capital,
            min_profit_bps=cfg.min_profit_bps,
            latency_steps=cfg.latency_steps,
            peg_price=peg_price,
        )

    def _opportunities(self, ctx: RunContext, obs: dict) -> dict[str, float]:
        amm, redemption = self._amm(ctx), self._redemption(ctx)
        spot, oracle = obs["spot_price"], obs["oracle_price"]
        seen: dict[str, float] = {}
        if amm is None:
            return seen
        avail = self.available_stable
        k = amm.k
        if avail > DUST and redemption is not None and redemption.payout_per_unit > spot:
            seen[REDEEM] = avail
        if oracle is None:  # AMM-vs-oracle trades need a published price
            return seen
        band = (amm.fee_bps + self.min_profit_bps) / BPS
        if REDEEM not in seen and spot > oracle * (1 + band) and avail > DUST:
            y = min(avail, _stable_to_reach(k, amm.reserve_stable, oracle))
            if y > DUST:
                seen[SELL_AMM] = y
        if spot < oracle * (1 - band):
            x = min(self.balances[REFERENCE], _reference_to_reach(k, amm.reserve_reference, oracle))
            if x > DUST:
                seen[BUY_AMM] = x
        return seen

    def observe(self, ctx: RunContext) -> dict:
        obs = super().observe(ctx)
        amm, redemption = self._amm(ctx), self._redemption(ctx)
        spot, oracle = obs["spot_price"], obs["oracle_price"]
        obs["fee_bps"] = None if amm is None else amm.fee_bps
        obs["gap_bps"] = None if spot is None or oracle is None else (spot / oracle - 1) * BPS
        obs["payout_per_unit"] = None if redemption is None else redemption.payout_per_unit

        seen = self._opportunities(ctx, obs)
        step = ctx.clock.step_index
        kept = [p for p in self.pending if p.kind in seen]
        for p in kept:
            p.amount = seen.pop(p.kind)
        kept.extend(Plan(kind=kind, step=step, amount=amt) for kind, amt in seen.items())
        self.pending = kept
        obs["pending_plans"] = [asdict(p) for p in self.pending]
        return obs

    def _action_for(self, plan: Plan) -> Action | None:
        if plan.kind == BUY_AMM:
            amount = min(plan.amount, self.balances[REFERENCE])
            return self._swap("buy_stable", amount) if amount > DUST else None
        amount = min(plan.amount, self.available_stable)
        if amount <= DUST:
            return None
        if plan.kind == SELL_AMM:
            return self._swap("sell_stable", amount)
        return Action(
            source=self.agent_id,
            target="redemption",
            kind="redeem",
            params={"amount_stable": amount},
        )

    def decide(self, ctx: RunContext) -> list[Action]:
        step = ctx.clock.step_index
        for plan in [p for p in self.pending if p.step + self.latency_steps <= step]:
            self.pending.remove(plan)
            action = self._action_for(plan)
            if action is not None:
                self.record(ctx, RULES[plan.kind], self.last_obs, action_record(action))
                return [action]
        rule = "arb_waiting_latency" if self.pending else "arb_idle"
        self.record(ctx, rule, self.last_obs, None)
        return []

    def _snapshot_extra(self) -> dict:
        return {"pending_plans": [asdict(p) for p in self.pending]}
