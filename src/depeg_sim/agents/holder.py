"""Holder (the par-expecting buyer): buys the discounted stable and redeems it at par.

The spec's "holder" family with the opposite sign (Story 2.6, F-08): market makers and
funds who bought USDC at $0.88 because they expected Circle to redeem at $1, or the
1992 convergence traders before their belief broke. Starts holding ``capital``
reference. Each step, in this order (one action at most)::

    hold_exit    exit_discount_pct is set, not yet exited,
                 and spot < exit_price = peg_price * (1 - exit_discount_pct / 100)
                 -> swap sell_stable, amount_in = available_stable (none if <= DUST);
                    sets ``exited``
    hold_done    elif exited (one-way: never buys or redeems again)
    hold_buy     elif spot < entry_price = peg_price * (1 - entry_discount_pct / 100)
                 and min(pace * reference, cap) > DUST
                 -> swap buy_stable, amount_in = min(pace * reference, cap)
    hold_redeem  elif redeem_when_capacity and available_stable > 0
                 and redemption.queue_depth == 0
                 -> redeem min(available_stable,
                               redemption.capacity_per_step * redeem_horizon_steps)
    hold_wait    elif stable > 0 (held, or queued and not yet paid)
    hold_done    else

``cap`` is the fill-price limit (Story 3.1): the reference that lifts AMM spot to
``entry_price``, from the arbitrageur's closed form ``_reference_to_reach`` reused
unchanged. That form ignores the AMM fee, so with a fee spot lands slightly below
``entry_price`` (by ``fee x amount / sqrt(k x entry_price)``: under 0.1 bps at the
calibrated 1 bp fee), never above it. The holder never lifts the price past the
price at which it is willing to buy, which removes the ADR-0021 sawtooth above par.
When the buy amount is at most ``DUST`` it does not buy and falls through to the
rules below.

The redeem condition keeps it from queueing behind other redeemers. It redeems in
tranches the channel can pay within ``redeem_horizon_steps`` (default 10) at the current
capacity, so the condition is in market units, not in multiples of its own balance
(Story 2.6 Rulings). A tranche usually takes several steps to pay; while it drains, the
queue is not empty and the holder waits, then queues the next tranche. It never sells
on the AMM except by ``hold_exit`` and never draws from ``ctx.rng``. Before an exit,
``hold_done`` is not terminal: if the discount reappears and it still has reference, it
buys again.

The exit rule (Story 3.3) is the convergence trader switching sides: the first time spot
is below ``exit_price`` it sells, in one swap, every stable it holds that is not already
queued for redemption. It cancels nothing: queued tranches are still paid and settle as
usual. ``exited`` is one-way; from then on every step is ``hold_done``. With
``exit_discount_pct`` unset (``None``) the rule never fires. ``hold_exit`` is recorded once,
on the step it fires, with no action when there was nothing to sell.

``bought_stable`` and ``spent_reference`` count its executed buys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from depeg_sim.agents.arbitrageur import _reference_to_reach
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
        redeem_horizon_steps: int = 10,
        peg_price: float = 1.0,
        exit_discount_pct: float | None = None,
    ) -> None:
        if not capital > 0:
            raise ValueError(f"capital must be > 0, got {capital}")
        if not 0 <= entry_discount_pct < 100:
            raise ValueError(f"entry_discount_pct must be in [0, 100), got {entry_discount_pct}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        if not redeem_horizon_steps > 0:
            raise ValueError(f"redeem_horizon_steps must be > 0, got {redeem_horizon_steps}")
        if exit_discount_pct is not None and not (entry_discount_pct < exit_discount_pct < 100):
            raise ValueError(
                "exit_discount_pct must be in (entry_discount_pct, 100), got "
                f"{exit_discount_pct} with entry_discount_pct {entry_discount_pct}"
            )
        super().__init__(agent_id, stable=0.0, reference=capital, peg_price=peg_price)
        self.capital = float(capital)
        self.entry_discount_pct = float(entry_discount_pct)
        self.pace = float(pace)
        self.redeem_when_capacity = bool(redeem_when_capacity)
        self.redeem_horizon_steps = int(redeem_horizon_steps)
        self.bought_stable = 0.0
        self.spent_reference = 0.0
        self.exit_discount_pct = None if exit_discount_pct is None else float(exit_discount_pct)
        self.exited = False
        self.sold_stable = 0.0

    @classmethod
    def from_config(cls, cfg: HolderConfig, peg_price: float = 1.0) -> Holder:
        return cls(
            agent_id=cfg.id,
            capital=cfg.capital,
            entry_discount_pct=cfg.entry_discount_pct,
            pace=cfg.pace,
            redeem_when_capacity=cfg.redeem_when_capacity,
            peg_price=peg_price,
            exit_discount_pct=cfg.exit_discount_pct,
        )

    @property
    def entry_price(self) -> float:
        """It buys strictly below this AMM spot."""
        return self.peg_price * (1 - self.entry_discount_pct / 100)

    @property
    def exit_price(self) -> float | None:
        """It sells everything once, strictly below this AMM spot; ``None``: never."""
        if self.exit_discount_pct is None:
            return None
        return self.peg_price * (1 - self.exit_discount_pct / 100)

    def observe(self, ctx: RunContext) -> dict:
        obs = super().observe(ctx)
        red = self._redemption(ctx)
        obs["entry_price"] = self.entry_price
        obs["queue_depth"] = None if red is None else red.queue_depth
        obs["capacity_per_step"] = None if red is None else red.capacity_per_step
        obs["queued_redeem"] = self.queued_redeem
        if self.exit_discount_pct is not None:
            obs["exit_price"] = self.exit_price
            obs["exited"] = self.exited
        return obs

    def _tranche(self, ctx: RunContext) -> float:
        """Stable to redeem this step; 0 when the redeem rule does not apply."""
        red = self._redemption(ctx)
        avail = self.available_stable
        if not self.redeem_when_capacity or red is None or avail <= DUST or red.queue_depth:
            return 0.0
        return min(avail, red.capacity_per_step * self.redeem_horizon_steps)

    def _buy_amount(self, ctx: RunContext) -> float:
        """Reference to spend this step: ``min(pace x reference, cap)`` while spot is below
        the entry price, else 0. ``cap`` reuses the arbitrageur's sizing (fee ignored)."""
        amm = self._amm(ctx)
        if amm is None or not amm.spot_price < self.entry_price:
            return 0.0
        cap = _reference_to_reach(amm.k, amm.reserve_reference, self.entry_price)
        return min(self.pace * self.balances[REFERENCE], cap)

    def _exits_now(self, ctx: RunContext) -> bool:
        if self.exit_price is None or self.exited:
            return False
        amm = self._amm(ctx)
        return amm is not None and amm.spot_price < self.exit_price

    def decide(self, ctx: RunContext) -> list[Action]:
        if self._exits_now(ctx):
            self.exited = True
            amount = self.available_stable
            action = self._swap("sell_stable", amount) if amount > DUST else None
            self.record(ctx, "hold_exit", self.last_obs, action and action_record(action))
            return [] if action is None else [action]
        if self.exited:
            self.record(ctx, "hold_done", self.last_obs, None)
            return []
        if (amount := self._buy_amount(ctx)) > DUST:
            action = self._swap("buy_stable", amount)
            rule = "hold_buy"
        elif (tranche := self._tranche(ctx)) > DUST:
            action = Action(
                source=self.agent_id,
                target="redemption",
                kind="redeem",
                params={"amount_stable": tranche},
            )
            rule = "hold_redeem"
        else:
            rule = "hold_wait" if self.balances[STABLE] > DUST else "hold_done"
            self.record(ctx, rule, self.last_obs, None)
            return []
        self.record(ctx, rule, self.last_obs, action_record(action))
        return [action]

    def _on_swap(self, detail: dict) -> None:
        if detail["side"] == "sell_stable":
            self.sold_stable += detail["amount_in"]
            return
        self.bought_stable += detail["amount_out"]
        self.spent_reference += detail["amount_in"]

    def _snapshot_extra(self) -> dict:
        extra = {
            "bought_stable": self.bought_stable,
            "spent_reference": self.spent_reference,
            "queued_redeem": self.queued_redeem,
        }
        if self.exit_discount_pct is not None:  # Story 3.3: older snapshots unchanged
            extra |= {"exited": self.exited, "sold_stable": self.sold_stable}
        return extra
