"""Defender (Bank of England): spends a reference budget to hold the peg.

Starts holding ``budget`` reference. Defense is on while
``amm.peg_deviation < -threshold_pct / 100``; there is no hysteresis band in v1.

In defense, each step it buys stable on the AMM with::

    x = min(spend_pace * reference_balance,
            sqrt(k * peg_price) - R,            # closed form: lifts spot back to peg
            max_spend - spent)                  # political will (no cap if unset)

and skips the buy when ``x <= 0`` (rule ``defend_budget_exhausted``).

Spread lever: if ``spread_adjust_bps > 0``, on entering defense it raises the
redemption spread from its current value ``base`` to ``base + spread_adjust_bps``
(capped at 9_999) through ``redemption.set_spread_bps(ctx, ..., source=agent_id)``,
once. When deviation returns within band it restores ``base``, once. It calls
``set_spread_bps`` only when the value would change, so ``spread_changed`` events
mark real lever pulls.

``spent`` is reference actually sent to the AMM (``amount_in`` of its own executed
swaps, applied in ``settle``), not planned spend. ``interventions`` counts those
executed buys.

Rules: ``defend_buy``, ``defend_spread_widen`` (the step the spread is widened; its
record's action is the list ``[spread change, buy]`` when it also buys),
``defend_spread_restore``, ``defend_budget_exhausted``, ``defend_idle``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from depeg_sim.agents.arbitrageur import _reference_to_reach
from depeg_sim.agents.base import DUST, REFERENCE, Agent, action_record
from depeg_sim.kernel.config import DefenderConfig
from depeg_sim.kernel.interfaces import Action

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

MAX_SPREAD_BPS = 9_999


def _spread_record(bps: int) -> dict:
    return {"target": "redemption", "kind": "set_spread_bps", "params": {"bps": bps}}


class Defender(Agent):
    type = "defender"

    def __init__(
        self,
        agent_id: str,
        budget: float,
        threshold_pct: float,
        spend_pace: float,
        spread_adjust_bps: int = 0,
        max_spend: float | None = None,
        peg_price: float = 1.0,
    ) -> None:
        if not budget > 0:
            raise ValueError(f"budget must be > 0, got {budget}")
        if not threshold_pct > 0:
            raise ValueError(f"threshold_pct must be > 0, got {threshold_pct}")
        if not 0 < spend_pace <= 1:
            raise ValueError(f"spend_pace must be in (0, 1], got {spend_pace}")
        if spread_adjust_bps < 0:
            raise ValueError(f"spread_adjust_bps must be >= 0, got {spread_adjust_bps}")
        if max_spend is not None and max_spend < 0:
            raise ValueError(f"max_spend must be >= 0, got {max_spend}")
        super().__init__(agent_id, stable=0.0, reference=budget, peg_price=peg_price)
        self.budget = float(budget)
        self.threshold_pct = float(threshold_pct)
        self.spend_pace = float(spend_pace)
        self.spread_adjust_bps = spread_adjust_bps
        self.max_spend = max_spend
        self.spent = 0.0
        self.interventions = 0
        self.spread_widened = False
        self.base_spread: int | None = None

    @classmethod
    def from_config(cls, cfg: DefenderConfig, peg_price: float = 1.0) -> Defender:
        return cls(
            agent_id=cfg.id,
            budget=cfg.budget,
            threshold_pct=cfg.threshold_pct,
            spend_pace=cfg.spend_pace,
            spread_adjust_bps=cfg.spread_adjust_bps,
            max_spend=cfg.max_spend,
            peg_price=peg_price,
        )

    def _buy_size(self, amm) -> float:
        remaining = math.inf if self.max_spend is None else self.max_spend - self.spent
        return min(
            self.spend_pace * self.balances[REFERENCE],
            _reference_to_reach(amm.k, amm.reserve_reference, amm.peg_price),
            remaining,
        )

    def decide(self, ctx: RunContext) -> list[Action]:
        amm, redemption = self._amm(ctx), self._redemption(ctx)
        obs = self.last_obs
        actions: list[Action] = []
        records: list[dict] = []

        if amm.peg_deviation < -self.threshold_pct / 100:
            rule = None
            if self.spread_adjust_bps > 0 and redemption is not None and not self.spread_widened:
                base = redemption.spread_bps
                target = min(base + self.spread_adjust_bps, MAX_SPREAD_BPS)
                if target != base:
                    redemption.set_spread_bps(ctx, target, source=self.agent_id)
                    self.base_spread = base
                    self.spread_widened = True
                    records.append(_spread_record(target))
                    rule = "defend_spread_widen"
            x = self._buy_size(amm)
            if x > DUST:
                actions.append(self._swap("buy_stable", x))
                records.append(action_record(actions[0]))
                rule = rule or "defend_buy"
            rule = rule or "defend_budget_exhausted"
        elif self.spread_widened:
            if redemption.spread_bps != self.base_spread:
                redemption.set_spread_bps(ctx, self.base_spread, source=self.agent_id)
                records.append(_spread_record(self.base_spread))
            self.spread_widened = False
            rule = "defend_spread_restore"
        else:
            rule = "defend_idle"

        if not records:
            action = None
        elif len(records) == 1:
            action = records[0]
        else:
            action = records
        self.record(ctx, rule, obs, action)
        return actions

    def _on_swap(self, detail: dict) -> None:
        if detail["side"] == "buy_stable":
            self.spent += detail["amount_in"]
            self.interventions += 1

    def _snapshot_extra(self) -> dict:
        return {
            "spent": self.spent,
            "interventions": self.interventions,
            "spread_widened": self.spread_widened,
        }
