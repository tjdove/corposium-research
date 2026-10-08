"""Liquidity provider (Story 3.8): liquidity that leaves when the peg looks lost.

Owns ``share`` of the AMM pool at the start (the rest belongs to passive LPs who never
move). Each step, in this order (one action at most)::

    lp_done      share_remaining <= DUST (it has nothing left in the pool)
    lp_withdraw  elif amm.peg_deviation < -panic_threshold_pct / 100
                 -> remove_liquidity, fraction = removed / amm.lp_supply,
                    removed = min(pace * share_remaining, share_remaining)
    lp_hold      else

It is one-way: it never adds liquidity back, and once the price is back above its panic
threshold it simply holds what is left. It never swaps, never redeems and never draws
from ``ctx.rng``.

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
    ) -> None:
        if not 0 < share <= 1:
            raise ValueError(f"share must be in (0, 1], got {share}")
        if not panic_threshold_pct > 0:
            raise ValueError(f"panic_threshold_pct must be > 0, got {panic_threshold_pct}")
        if not 0 < pace <= 1:
            raise ValueError(f"pace must be in (0, 1], got {pace}")
        super().__init__(agent_id, stable=0.0, reference=0.0, peg_price=peg_price)
        self.share = float(share)
        self.share_remaining = float(share)
        self.panic_threshold_pct = float(panic_threshold_pct)
        self.pace = float(pace)
        self.withdrawals = 0
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
        if self.share_remaining <= DUST:
            self.record(ctx, "lp_done", self.last_obs, None)
            return []
        if amm is None or not amm.peg_deviation < -self.panic_threshold_pct / 100:
            self.record(ctx, "lp_hold", self.last_obs, None)
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

    def settle(self, ctx: RunContext) -> None:
        for action, result in ctx.execution_results:
            if action.source != self.agent_id or action.kind != "remove_liquidity":
                continue
            if result.ok:
                self.balances[STABLE] += result.detail["stable_out"]
                self.balances[REFERENCE] += result.detail["reference_out"]
                self.share_remaining = max(self.share_remaining - self._pending_removed, 0.0)
                self.withdrawals += 1
        self._pending_removed = 0.0
        super().settle(ctx)

    def mark_to_market(self, ctx: RunContext) -> float:
        amm = self._amm(ctx)
        spot = amm.spot_price
        position = self.pool_fraction(ctx) * (amm.reserve_reference + amm.reserve_stable * spot)
        return self.balances[REFERENCE] + self.balances[STABLE] * spot + position

    def _snapshot_extra(self) -> dict:
        return {
            "share": self.share,
            "share_remaining": self.share_remaining,
            "withdrawals": self.withdrawals,
        }
