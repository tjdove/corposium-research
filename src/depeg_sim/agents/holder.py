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

Tranches (Story 3.7). With ``tranches`` (a ladder of ``(entry_discount_pct, share)``,
discounts strictly increasing) the holder keeps one book per tranche: a reference balance
that starts at ``capital x share`` and the stable that tranche bought. ``hold_buy`` then
emits one swap per tranche whose entry price is above spot, deepest entry first, each
``min(pace x tranche reference, cap_i)`` where ``cap_i`` lifts spot to *that tranche's*
entry price. The caps are chained within the step: after tranche ``i`` buys ``a``, the next
tranche sizes from ``reserve_reference + a`` and checks its entry against the implied spot
``(reserve_reference + a)^2 / k`` (fee ignored, as for the single cap), so no tranche lifts
the price past its own entry and a shallow tranche buys only above the deep tranches' fills,
as a ladder of resting bids would fill. The redeem and exit rules are unchanged and act on
the pooled stable; the reference a redemption pays (or an exit sale returns) is credited to
the tranches pro rata to the stable each held before it, which also reduces pro rata.
The holder's ``balances`` stay the pooled totals. A single tranche is the scalar form: its
book *is* the holder's book, so with one tranche (share 1) every output is identical to
``entry_discount_pct`` alone. With two or more, buy decisions carry ``tranche`` (its index)
on each action and snapshots carry the per-tranche books.
"""

from __future__ import annotations

from collections.abc import Sequence
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
        entry_discount_pct: float | None,
        pace: float,
        redeem_when_capacity: bool = True,
        redeem_horizon_steps: int = 10,
        peg_price: float = 1.0,
        exit_discount_pct: float | None = None,
        tranches: Sequence[tuple[float, float]] | None = None,
    ) -> None:
        if not capital > 0:
            raise ValueError(f"capital must be > 0, got {capital}")
        if (tranches is None) == (entry_discount_pct is None):
            raise ValueError("give exactly one of entry_discount_pct and tranches")
        ladder = [(entry_discount_pct, 1.0)] if tranches is None else list(tranches)
        if not ladder:
            raise ValueError("tranches must not be empty")
        for discount, share in ladder:
            if not 0 <= discount < 100:
                raise ValueError(f"entry_discount_pct must be in [0, 100), got {discount}")
            if not 0 < share <= 1:
                raise ValueError(f"tranche share must be in (0, 1], got {share}")
        if abs(sum(share for _, share in ladder) - 1) > 1e-9:
            raise ValueError(f"tranche shares must sum to 1, got {[sh for _, sh in ladder]}")
        discounts = [d for d, _ in ladder]
        if any(b <= a for a, b in zip(discounts, discounts[1:], strict=False)):
            raise ValueError(f"tranche entry discounts must strictly increase, got {discounts}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        if not redeem_horizon_steps > 0:
            raise ValueError(f"redeem_horizon_steps must be > 0, got {redeem_horizon_steps}")
        if exit_discount_pct is not None and not (discounts[-1] < exit_discount_pct < 100):
            raise ValueError(
                "exit_discount_pct must be in (entry_discount_pct, 100), got "
                f"{exit_discount_pct} with entry_discount_pct {discounts[-1]}"
            )
        super().__init__(agent_id, stable=0.0, reference=capital, peg_price=peg_price)
        self.capital = float(capital)
        self.entry_discount_pct = float(discounts[0])  # the shallowest: it starts buying here
        self.tranche_discounts = [float(d) for d in discounts]
        self.tranche_shares = [float(sh) for _, sh in ladder]
        self.tranche_reference = [self.capital * sh for sh in self.tranche_shares]
        self.tranche_stable = [0.0] * len(ladder)
        self.tranche_spent = [0.0] * len(ladder)
        self.laddered = len(ladder) > 1
        self._pending: list[tuple[Action, int]] = []
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
        tranches = (
            None
            if cfg.tranches is None
            else [(t.entry_discount_pct, t.share) for t in cfg.tranches]
        )
        return cls(
            agent_id=cfg.id,
            capital=cfg.capital,
            entry_discount_pct=cfg.entry_discount_pct,
            pace=cfg.pace,
            redeem_when_capacity=cfg.redeem_when_capacity,
            peg_price=peg_price,
            exit_discount_pct=cfg.exit_discount_pct,
            tranches=tranches,
        )

    @property
    def entry_price(self) -> float:
        """It buys strictly below this AMM spot (the shallowest tranche's entry price)."""
        return self.peg_price * (1 - self.entry_discount_pct / 100)

    @property
    def tranche_entry_prices(self) -> list[float]:
        return [self.peg_price * (1 - d / 100) for d in self.tranche_discounts]

    def _reference_of(self, i: int) -> float:
        """Tranche ``i``'s reference; a single tranche's book is the holder's own."""
        return self.tranche_reference[i] if self.laddered else self.balances[REFERENCE]

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
        if self.laddered:
            obs["tranche_entry_prices"] = self.tranche_entry_prices
            obs["tranche_reference"] = list(self.tranche_reference)
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

    def _buys(self, ctx: RunContext) -> list[tuple[int, float]]:
        """``(tranche, reference)`` to spend this step, deepest entry first: for each tranche
        whose entry price is above the (implied) spot, ``min(pace x its reference, cap)``,
        ``cap`` from the arbitrageur's sizing (fee ignored) chained across tranches. Buys of
        at most ``DUST`` are dropped."""
        amm = self._amm(ctx)
        if amm is None:
            return []
        k, r, spot = amm.k, amm.reserve_reference, amm.spot_price
        buys = []
        for i in reversed(range(len(self.tranche_discounts))):
            entry = self.tranche_entry_prices[i]
            if not spot < entry:
                continue
            amount = min(self.pace * self._reference_of(i), _reference_to_reach(k, r, entry))
            if amount > DUST:
                buys.append((i, amount))
                r += amount
                spot = r * r / k
        return buys

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
        self._pending = []
        if buys := self._buys(ctx):
            self._pending = [(self._swap("buy_stable", amount), i) for i, amount in buys]
            records = [
                action_record(a) | ({"tranche": i} if self.laddered else {})
                for a, i in self._pending
            ]
            record = records[0] if len(records) == 1 else records  # ADR-0011
            self.record(ctx, "hold_buy", self.last_obs, record)
            return [a for a, _ in self._pending]
        if (tranche := self._tranche(ctx)) > DUST:
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

    def settle(self, ctx: RunContext) -> None:
        """The tranche books, then the pooled balances (``Agent.settle``)."""
        for action, result in ctx.execution_results:
            if action.source != self.agent_id or not result.ok or action.kind != "swap":
                continue
            d = result.detail
            if d["side"] == "sell_stable":
                self._unwind(d["amount_in"], d["amount_out"])
                continue
            (i,) = [i for a, i in self._pending if a is action]
            self.tranche_reference[i] -= d["amount_in"]
            self.tranche_stable[i] += d["amount_out"]
            self.tranche_spent[i] += d["amount_in"]
        for event in ctx.events.at_step(ctx.clock.step_index):
            if event.kind == "redeem_fulfilled" and event.payload["source"] == self.agent_id:
                self._unwind(event.payload["amount_stable"], event.payload["paid_reference"])
        self._pending = []
        super().settle(ctx)

    def _unwind(self, stable: float, reference: float) -> None:
        """Pooled ``stable`` left the holder for ``reference``: pro rata to tranche stable
        (to tranche share when no tranche holds any, e.g. stable set by hand)."""
        total = sum(self.tranche_stable)
        weights = self.tranche_stable if total > DUST else self.tranche_shares
        norm = sum(weights)
        for i, w in enumerate(weights):
            f = w / norm
            self.tranche_stable[i] = max(self.tranche_stable[i] - stable * f, 0.0)
            self.tranche_reference[i] += reference * f

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
        if self.laddered:  # Story 3.7: one tranche is the scalar form, snapshot unchanged
            extra["tranches"] = [
                {
                    "entry_discount_pct": d,
                    "share": sh,
                    "reference": r,
                    "stable": st,
                    "spent_reference": sp,
                }
                for d, sh, r, st, sp in zip(
                    self.tranche_discounts,
                    self.tranche_shares,
                    self.tranche_reference,
                    self.tranche_stable,
                    self.tranche_spent,
                    strict=True,
                )
            ]
        return extra
