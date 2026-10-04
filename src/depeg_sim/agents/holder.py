"""Holder (the par-expecting buyer): buys the discounted stable and redeems it at par.

The spec's "holder" family with the opposite sign (Story 2.6, F-08): market makers and
funds who bought USDC at $0.88 because they expected Circle to redeem at $1, or the
1992 convergence traders before their belief broke. Starts holding ``capital``
reference. Each step, in this order (one action at most)::

    hold_buy     spot < peg_price * (1 - entry_discount_pct / 100) and reference > 0
                 -> swap buy_stable, amount_in = pace * reference
    hold_redeem  elif redeem_when_capacity and available_stable > 0
                 and redemption.queue_depth == 0
                 and redemption.capacity_per_step >= redeem_fraction_min * available_stable
                 -> redeem all available stable
    hold_wait    elif stable > 0 (held, or queued and not yet paid)
    hold_done    else

The redeem condition keeps it from queueing behind other redeemers or into a channel
that would take more than ~``1 / redeem_fraction_min`` steps to pay it. It never sells
on the AMM (no panic rule in this story) and never draws from ``ctx.rng``. ``hold_done``
is not terminal: if the discount reappears and it still has reference, it buys again.

``bought_stable`` and ``spent_reference`` count its executed buys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from depeg_sim.agents.base import DUST, REFERENCE, STABLE, Agent, action_record
from depeg_sim.kernel.config import HolderConfig
from depeg_sim.kernel.interfaces import Action

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext


class Holder(Agent):
    type = "holder"

    def __init__(
        self,
        agent_id: str,
        capital: float,
        entry_discount_pct: float,
        pace: float,
        redeem_when_capacity: bool = True,
        redeem_fraction_min: float = 0.1,
        peg_price: float = 1.0,
    ) -> None:
        if not capital > 0:
            raise ValueError(f"capital must be > 0, got {capital}")
        if not 0 <= entry_discount_pct < 100:
            raise ValueError(f"entry_discount_pct must be in [0, 100), got {entry_discount_pct}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        if not 0 < redeem_fraction_min <= 1:
            raise ValueError(f"redeem_fraction_min must be in (0, 1], got {redeem_fraction_min}")
        super().__init__(agent_id, stable=0.0, reference=capital, peg_price=peg_price)
        self.capital = float(capital)
        self.entry_discount_pct = float(entry_discount_pct)
        self.pace = float(pace)
        self.redeem_when_capacity = bool(redeem_when_capacity)
        self.redeem_fraction_min = float(redeem_fraction_min)
        self.bought_stable = 0.0
        self.spent_reference = 0.0

    @classmethod
    def from_config(cls, cfg: HolderConfig, peg_price: float = 1.0) -> Holder:
        return cls(
            agent_id=cfg.id,
            capital=cfg.capital,
            entry_discount_pct=cfg.entry_discount_pct,
            pace=cfg.pace,
            redeem_when_capacity=cfg.redeem_when_capacity,
            peg_price=peg_price,
        )

    @property
    def entry_price(self) -> float:
        """It buys strictly below this AMM spot."""
        return self.peg_price * (1 - self.entry_discount_pct / 100)

    def observe(self, ctx: RunContext) -> dict:
        obs = super().observe(ctx)
        red = self._redemption(ctx)
        obs["entry_price"] = self.entry_price
        obs["queue_depth"] = None if red is None else red.queue_depth
        obs["capacity_per_step"] = None if red is None else red.capacity_per_step
        obs["queued_redeem"] = self.queued_redeem
        return obs

    def _can_redeem(self, ctx: RunContext) -> bool:
        red = self._redemption(ctx)
        avail = self.available_stable
        return (
            self.redeem_when_capacity
            and red is not None
            and avail > DUST
            and red.queue_depth == 0
            and red.capacity_per_step >= self.redeem_fraction_min * avail
        )

    def decide(self, ctx: RunContext) -> list[Action]:
        amm = self._amm(ctx)
        if (
            amm is not None
            and amm.spot_price < self.entry_price
            and self.balances[REFERENCE] > DUST
        ):
            action = self._swap("buy_stable", self.pace * self.balances[REFERENCE])
            rule = "hold_buy"
        elif self._can_redeem(ctx):
            action = Action(
                source=self.agent_id,
                target="redemption",
                kind="redeem",
                params={"amount_stable": self.available_stable},
            )
            rule = "hold_redeem"
        else:
            rule = "hold_wait" if self.balances[STABLE] > DUST else "hold_done"
            self.record(ctx, rule, self.last_obs, None)
            return []
        self.record(ctx, rule, self.last_obs, action_record(action))
        return [action]

    def _on_swap(self, detail: dict) -> None:
        self.bought_stable += detail["amount_out"]
        self.spent_reference += detail["amount_in"]

    def _snapshot_extra(self) -> dict:
        return {
            "bought_stable": self.bought_stable,
            "spent_reference": self.spent_reference,
            "queued_redeem": self.queued_redeem,
        }
