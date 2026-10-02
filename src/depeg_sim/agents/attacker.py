"""Attacker (Soros): dumps a stable position into the AMM at a fixed pace.

Starts holding ``capital`` stable (the borrow that funds it is off-model). From
``start_step`` on, each step it sells ``pace * stable_balance`` on the AMM
(``sell_stable``), so the sell size decays geometrically. Rules, checked in order:

==========================  ====================================================
``attack_waiting``          ``step < start_step``
``attack_exhausted``        ``stable_balance < 1e-9``
``attack_stop_price``       ``stop_below_price`` set and ``spot < stop_below_price``
``attack_dump``             otherwise: sell ``pace * stable_balance``
==========================  ====================================================

v1 never buys back, so its PnL is the cost of the attack (negative by design).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from depeg_sim.agents.base import DUST, STABLE, Agent, action_record
from depeg_sim.kernel.config import AttackerConfig
from depeg_sim.kernel.interfaces import Action

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext


class Attacker(Agent):
    type = "attacker"

    def __init__(
        self,
        agent_id: str,
        capital: float,
        start_step: int,
        pace: float,
        stop_below_price: float | None = None,
        peg_price: float = 1.0,
    ) -> None:
        if not capital > 0:
            raise ValueError(f"capital must be > 0, got {capital}")
        if start_step < 0:
            raise ValueError(f"start_step must be >= 0, got {start_step}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        super().__init__(agent_id, stable=capital, reference=0.0, peg_price=peg_price)
        self.capital = float(capital)
        self.start_step = start_step
        self.pace = float(pace)
        self.stop_below_price = stop_below_price
        self.sold_total = 0.0

    @classmethod
    def from_config(cls, cfg: AttackerConfig, peg_price: float = 1.0) -> Attacker:
        return cls(
            agent_id=cfg.id,
            capital=cfg.capital,
            start_step=cfg.start_step,
            pace=cfg.pace,
            stop_below_price=cfg.stop_below_price,
            peg_price=peg_price,
        )

    def decide(self, ctx: RunContext) -> list[Action]:
        obs = self.last_obs
        stable = self.balances[STABLE]
        actions: list[Action] = []
        if ctx.clock.step_index < self.start_step:
            rule = "attack_waiting"
        elif stable < DUST:
            rule = "attack_exhausted"
        elif self.stop_below_price is not None and obs["spot_price"] < self.stop_below_price:
            rule = "attack_stop_price"
        else:
            rule = "attack_dump"
            actions.append(self._swap("sell_stable", self.pace * stable))
        self.record(ctx, rule, obs, action_record(actions[0]) if actions else None)
        return actions

    def _on_swap(self, detail: dict) -> None:
        if detail["side"] == "sell_stable":
            self.sold_total += detail["amount_in"]

    def _snapshot_extra(self) -> dict:
        return {"sold_total": self.sold_total}
