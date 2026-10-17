"""Liquidity provider (Story 3.8): liquidity that leaves when the peg looks lost.

Owns ``share`` of the AMM pool at the start (the rest belongs to passive LPs who never
move). Each step, in this order (one action at most)::

    lp_withdraw  share_remaining > DUST
                 and amm.peg_deviation < -panic_threshold_pct / 100
                 -> remove_liquidity, fraction = removed / amm.lp_supply,
                    removed = min(pace * share_remaining, share_remaining)
    lp_sell      elif after_withdrawal == "sell" and undisposed_stable > DUST
                 -> swap sell_stable, amount_in = disposal_pace * undisposed_stable
    lp_redeem    elif after_withdrawal == "redeem" and undisposed_stable > DUST
                 -> redeem, amount_stable = min(undisposed_stable,
                                                disposal_pace * undisposed_stable)
    lp_done      elif share_remaining <= DUST (it has nothing left in the pool)
    lp_hold      else

It is one-way: it never adds liquidity back, and once the price is back above its panic
threshold it simply holds what is left in the pool. It never draws from ``ctx.rng``.

What it does with the stable it withdrew (Story 5.4, ``after_withdrawal``): ``hold`` (the
default, and Story 3.8's LP) sits on it. ``sell`` and ``redeem`` dispose of
``disposal_pace`` of the stable it holds and has not already sold or queued
(``undisposed_stable``) on each step it does not withdraw, whatever the price: a sale on
the AMM (fee on input, no price limit), or a request at the back of the redemption
module's FIFO queue, the same queue the holder and arbitrageur use, with no priority and
no wait for an empty queue (unlike the holder). Withdrawing comes first, so while spot is
below the panic price and it still has shares it withdraws, and it disposes only once it
has stopped. The reference a sale or redemption pays is held; it never re-adds liquidity
(ADR-0031). Withdrawn reference is never touched.

``undisposed_stable`` is its own counter, not ``available_stable``: it rises by each
withdrawal's ``stable_out`` and falls by each executed sale's ``amount_in`` or accepted
request's ``queued``, so it shrinks geometrically to below ``DUST`` and disposal ends.
(``balances - queued_redeem`` keeps a few-ulp residue of ~1e-8 at 1e7 that never does.)

The arithmetic (Dev Notes, normative). State is kept in **share terms**: shares are
units of the *initial* pool, so the whole pool at the start is 1.0, this LP holds
``share_remaining`` of them and ``amm.lp_supply`` (1.0 at the start, times ``1 - f`` per
removal of ``f``) is the total still in the pool. The conversion to a fraction of the
*current* pool happens only at the moment of the action::

    removed  = min(pace * share_remaining, share_remaining)      # shares
    fraction = removed / lp_supply                               # of the current pool

The AMM scales both reserves by ``1 - fraction`` and ``lp_supply`` becomes
``lp_supply - removed``; this LP's ``share_remaining`` becomes ``share_remaining -
removed``. Written as fractions of the pool: if the LP owns ``S = share_remaining /
lp_supply`` of the current pool and withdraws ``s = fraction`` of it, it owns
``(S - s) / (1 - s)`` of the new pool. Example (``share`` 0.5, ``pace`` 0.1, no swaps in
between): first withdrawal removes 0.05 shares, fraction 0.05 / 1 = 0.05, leaving 0.45 of
0.95 (= (0.5 - 0.05) / 0.95); second removes 0.045 shares, fraction 0.045 / 0.95 =
0.047368..., leaving 0.405 of 0.905. With one flighty LP ``lp_supply = 1 - (share -
share_remaining)``. With several LPs withdrawing in the same step each sizes its fraction
from ``lp_supply`` as it was when it decided, so the second removes slightly more than its
shares (a known approximation; the scenarios here have one LP).

``share_remaining`` is reduced only by an executed removal (``liquidity_removed``); a
rejected one (the drain guard: a sole LP cannot remove the whole pool, ``fraction == 1``)
changes nothing and is retried next step.

Valuation. ``initial_value`` is its pool position at the first observation, valued at
peg: ``share * (reserve_reference + reserve_stable * peg_price)``. ``mark_to_market`` is
the withdrawn reserves (``balances``) marked at AMM spot plus the position still in the
pool, ``share_remaining / lp_supply * (reserve_reference + reserve_stable * spot)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from depeg_sim.agents.base import DUST, REFERENCE, STABLE, Agent, action_record
from depeg_sim.kernel.config import LPConfig
from depeg_sim.kernel.interfaces import Action

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext


class LiquidityProvider(Agent):
    type = "lp"

    def __init__(
        self,
        agent_id: str,
        share: float,
        panic_threshold_pct: float,
        pace: float,
        peg_price: float = 1.0,
        after_withdrawal: str = "hold",
        disposal_pace: float = 0.1,
    ) -> None:
        if not 0 < share <= 1:
            raise ValueError(f"share must be in (0, 1], got {share}")
        if not panic_threshold_pct > 0:
            raise ValueError(f"panic_threshold_pct must be > 0, got {panic_threshold_pct}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        if after_withdrawal not in ("hold", "sell", "redeem"):
            raise ValueError(f"after_withdrawal must be hold, sell or redeem: {after_withdrawal}")
        if not 0 < disposal_pace <= 1:
            raise ValueError(f"disposal_pace must be in (0, 1], got {disposal_pace}")
        super().__init__(agent_id, stable=0.0, reference=0.0, peg_price=peg_price)
        self.share = float(share)
        self.share_remaining = float(share)
        self.panic_threshold_pct = float(panic_threshold_pct)
        self.pace = float(pace)
        self.after_withdrawal = after_withdrawal
        self.disposal_pace = float(disposal_pace)
        self.withdrawals = 0
        self.sold_stable = 0.0  # executed AMM sales, stable in
        self.redeemed_stable = 0.0  # redemption fills, stable out
        self.undisposed_stable = 0.0  # withdrawn stable not yet sold or queued
        self._valued = False
        self._pending_removed = 0.0

    @classmethod
    def from_config(cls, cfg: LPConfig, peg_price: float = 1.0) -> LiquidityProvider:
        return cls(
            agent_id=cfg.id,
            share=cfg.share,
            panic_threshold_pct=cfg.panic_threshold_pct,
            pace=cfg.pace,
            peg_price=peg_price,
            after_withdrawal=cfg.after_withdrawal,
            disposal_pace=cfg.disposal_pace,
        )

    @property
    def panic_price(self) -> float:
        """It withdraws while AMM spot is strictly below this."""
        return self.peg_price * (1 - self.panic_threshold_pct / 100)

    def pool_fraction(self, ctx: RunContext) -> float:
        """Its fraction of the current pool: ``share_remaining / lp_supply``."""
        return self.share_remaining / self._amm(ctx).lp_supply

    def observe(self, ctx: RunContext) -> dict:
        amm = self._amm(ctx)
        if not self._valued and amm is not None:
            self.initial_value = self.share * (
                amm.reserve_reference + amm.reserve_stable * self.peg_price
            )
            self._valued = True
        obs = super().observe(ctx)
        obs["share_remaining"] = self.share_remaining
        obs["pool_fraction"] = None if amm is None else self.pool_fraction(ctx)
        return obs

    def decide(self, ctx: RunContext) -> list[Action]:
        amm = self._amm(ctx)
        self._pending_removed = 0.0
        panics = amm is not None and amm.peg_deviation < -self.panic_threshold_pct / 100
        if self.share_remaining <= DUST or not panics:
            if (action := self._disposal(ctx)) is not None:
                self.record(ctx, f"lp_{self.after_withdrawal}", self.last_obs,
                            action_record(action))  # fmt: skip
                return [action]
            rule = "lp_done" if self.share_remaining <= DUST else "lp_hold"
            self.record(ctx, rule, self.last_obs, None)
            return []
        removed = min(self.pace * self.share_remaining, self.share_remaining)
        action = Action(
            source=self.agent_id,
            target="amm",
            kind="remove_liquidity",
            params={"fraction": removed / amm.lp_supply},
        )
        self._pending_removed = removed
        self.record(ctx, "lp_withdraw", self.last_obs, action_record(action))
        return [action]

    def _disposal(self, ctx: RunContext) -> Action | None:
        """This step's sale or redemption of withdrawn stable; ``None`` when it holds."""
        avail = self.undisposed_stable
        if self.after_withdrawal == "hold" or avail <= DUST:
            return None
        if self.after_withdrawal == "sell":
            return (
                None
                if self._amm(ctx) is None
                else self._swap("sell_stable", self.disposal_pace * avail)
            )
        if self._redemption(ctx) is None:
            return None
        return Action(
            source=self.agent_id,
            target="redemption",
            kind="redeem",
            params={"amount_stable": min(avail, self.disposal_pace * avail)},
        )

    def _on_swap(self, detail: dict) -> None:
        self.sold_stable += detail["amount_in"]
        self.undisposed_stable = max(self.undisposed_stable - detail["amount_in"], 0.0)

    def settle(self, ctx: RunContext) -> None:
        for action, result in ctx.execution_results:
            if action.source != self.agent_id or not result.ok:
                continue
            if action.kind == "redeem":
                self.undisposed_stable = max(self.undisposed_stable - result.detail["queued"], 0.0)
            elif action.kind == "remove_liquidity":
                self.undisposed_stable += result.detail["stable_out"]
                self.balances[STABLE] += result.detail["stable_out"]
                self.balances[REFERENCE] += result.detail["reference_out"]
                self.share_remaining = max(self.share_remaining - self._pending_removed, 0.0)
                self.withdrawals += 1
        for event in ctx.events.at_step(ctx.clock.step_index):
            if event.kind == "redeem_fulfilled" and event.payload["source"] == self.agent_id:
                self.redeemed_stable += event.payload["amount_stable"]
        self._pending_removed = 0.0
        super().settle(ctx)

    def mark_to_market(self, ctx: RunContext) -> float:
        amm = self._amm(ctx)
        spot = amm.spot_price
        position = self.pool_fraction(ctx) * (amm.reserve_reference + amm.reserve_stable * spot)
        return self.balances[REFERENCE] + self.balances[STABLE] * spot + position

    def _snapshot_extra(self) -> dict:
        extra = {
            "share": self.share,
            "share_remaining": self.share_remaining,
            "withdrawals": self.withdrawals,
        }
        if self.after_withdrawal != "hold":  # Story 5.4: the holding LP's snapshot unchanged
            extra |= {
                "after_withdrawal": self.after_withdrawal,
                "sold_stable": self.sold_stable,
                "redeemed_stable": self.redeemed_stable,
                "undisposed_stable": self.undisposed_stable,
                "queued_redeem": self.queued_redeem,
            }
        return extra
