"""Constant-product AMM: one STABLE/REF pool as a formal state machine.

State:      ``reserve_stable``, ``reserve_reference``, ``fee_bps``,
            ``cumulative_fees_stable``, ``cumulative_fees_reference``.
Actions:    ``swap`` with side ``"sell_stable"`` (stable in, reference out) or
            ``"buy_stable"`` (reference in, stable out); ``remove_liquidity`` with
            ``fraction`` (Story 3.8, below).
Execution:  Uniswap-V2 style, fee taken on input and left in the pool::

                net_in       = amount_in * (1 - fee_bps / 10_000)
                fee          = amount_in - net_in
                out          = reserve_out * net_in / (reserve_in + net_in)
                reserve_in  += amount_in
                reserve_out -= out

Invariant:  ``k = reserve_stable * reserve_reference`` never decreases across a swap; it
            changes otherwise only at a liquidity event, by exactly ``(1 - fraction)**2``.
Events:     ``swap_executed``, ``swap_rejected``, ``liquidity_removed`` and
            ``liquidity_rejected`` (emitted by ``execute``).
Outputs:    ``Quote`` / ``SwapResult``, ``spot_price``, ``peg_deviation``, ``snapshot()``.

Prices are quoted as **reference per unit stable**: ``spot_price = reserve_reference /
reserve_stable``. ``execution_price`` uses the same unit for both sides (``out /
amount_in`` when selling stable, ``amount_in / out`` when buying it), and ``slippage =
(execution_price - spot_before) / spot_before``, so it is negative when selling stable
and positive when buying it.

Peg deviation sign convention: ``peg_deviation = spot_price / peg_price - 1.0``.
Selling stable pushes ``spot_price`` **down**, so ``peg_deviation`` goes **negative**
under a stable-selling attack and positive when stable is bought. ``peg_deviation`` is
the ``PegView`` the kernel's ``peg_recovered`` termination check reads.

Amounts are floats in token units (not Decimal, not integer wei). The goal is
reproducibility, not wei-exactness; integer-exact behaviour is checked by the Anvil
replay (Epic 3 stretch). Fees accrue in the input token of each swap, so they are
kept per token: ``cumulative_fees_stable`` sums ``fee_paid`` over ``sell_stable``
swaps and ``cumulative_fees_reference`` over ``buy_stable`` swaps.

Invalid swaps raise ``AMMError`` from ``quote`` / ``swap``. ``execute`` catches these
and turns them into ``ExecutionResult(ok=False)`` plus a ``swap_rejected`` event. It
never raises.

Liquidity removal (Story 3.8). ``remove_liquidity(fraction)``, ``0 < fraction <= 1``,
withdraws that fraction of the *current* pool pro rata::

    stable_out     = reserve_stable * fraction
    reference_out  = reserve_reference * fraction
    reserve_*     -= *_out          # both scale by (1 - fraction)

so spot is unchanged (up to float rounding) and ``k`` scales by ``(1 - fraction)**2``.
The drain guard applies as for swaps: a removal that would leave either reserve at or
below zero (``fraction == 1``) raises ``AMMError("would drain reserves")``. ``lp_supply``
is the outstanding liquidity in units of the initial pool (1.0 at construction, times
``1 - fraction`` per removal): a liquidity provider who owned ``share`` of the initial
pool and still holds ``s`` of it owns ``s / lp_supply`` of the current pool. There is no
add: liquidity only leaves. Swaps neither read nor change ``lp_supply``, so the swap
path is unchanged; ``snapshot()`` carries the liquidity fields only after a removal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from depeg_sim.kernel.config import AMMConfig
from depeg_sim.kernel.interfaces import Action, ActionTarget, ExecutionResult
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

SELL_STABLE = "sell_stable"
BUY_STABLE = "buy_stable"
SIDES = frozenset({SELL_STABLE, BUY_STABLE})
BPS = 10_000


class AMMError(Exception):
    """An invalid swap or liquidity request (bad side, bad amount, reserve drain)."""


@dataclass(frozen=True)
class Quote:
    side: str
    amount_in: float
    amount_out: float
    execution_price: float
    spot_before: float
    spot_after: float
    slippage: float
    fee_paid: float


@dataclass(frozen=True)
class SwapResult(Quote):
    reserve_stable_after: float
    reserve_reference_after: float


@dataclass(frozen=True)
class LiquidityResult:
    fraction: float
    stable_out: float
    reference_out: float
    reserve_stable_after: float
    reserve_reference_after: float


class ConstantProductAMM(ActionTarget):
    def __init__(
        self,
        reserve_stable: float,
        reserve_reference: float,
        fee_bps: int,
        peg_price: float = 1.0,
        name: str = "amm",
    ) -> None:
        if not 0 <= fee_bps < BPS:
            raise ValueError(f"fee_bps must be in [0, {BPS}), got {fee_bps}")
        if not (reserve_stable > 0 and reserve_reference > 0):
            raise ValueError(
                f"reserves must be > 0, got stable={reserve_stable}, reference={reserve_reference}"
            )
        if not peg_price > 0:
            raise ValueError(f"peg_price must be > 0, got {peg_price}")
        self.name = name
        self.phases = frozenset({Phase.EXECUTION})
        self.reserve_stable = float(reserve_stable)
        self.reserve_reference = float(reserve_reference)
        self.fee_bps = int(fee_bps)
        self.peg_price = float(peg_price)
        self.cumulative_fees_stable = 0.0
        self.cumulative_fees_reference = 0.0
        self.lp_supply = 1.0
        self.liquidity_removals = 0

    @classmethod
    def from_config(cls, cfg: AMMConfig, peg_price: float) -> ConstantProductAMM:
        return cls(
            reserve_stable=cfg.reserve_stable,
            reserve_reference=cfg.reserve_reference,
            fee_bps=cfg.fee_bps,
            peg_price=peg_price,
        )

    # -- views -------------------------------------------------------------

    @property
    def spot_price(self) -> float:
        """Reference per unit stable."""
        return self.reserve_reference / self.reserve_stable

    @property
    def peg_deviation(self) -> float:
        """``spot_price / peg_price - 1.0``; negative when stable trades below peg."""
        return self.spot_price / self.peg_price - 1.0

    @property
    def k(self) -> float:
        return self.reserve_stable * self.reserve_reference

    # -- math --------------------------------------------------------------

    def _apply_fee(self, amount_in: float) -> tuple[float, float]:
        net_in = amount_in * (1 - self.fee_bps / BPS)
        return net_in, amount_in - net_in

    @staticmethod
    def _out_for_in(net_in: float, r_in: float, r_out: float) -> float:
        return r_out * net_in / (r_in + net_in)

    def _compute(self, amount_in: float, side: str) -> SwapResult:
        """The swap as it would execute now. Pure; raises ``AMMError`` if invalid."""
        if not isinstance(side, str) or side not in SIDES:
            raise AMMError(f"unknown side {side!r}")
        if not (math.isfinite(amount_in) and amount_in > 0):
            raise AMMError("amount_in must be > 0")

        if side == SELL_STABLE:
            r_in, r_out = self.reserve_stable, self.reserve_reference
        else:
            r_in, r_out = self.reserve_reference, self.reserve_stable

        net_in, fee = self._apply_fee(amount_in)
        out = self._out_for_in(net_in, r_in, r_out)
        if out >= r_out:
            raise AMMError("would drain reserve_out")

        new_in, new_out = r_in + amount_in, r_out - out
        if side == SELL_STABLE:
            stable_after, reference_after = new_in, new_out
            execution_price = out / amount_in
        else:
            stable_after, reference_after = new_out, new_in
            execution_price = amount_in / out

        spot_before = self.spot_price
        return SwapResult(
            side=side,
            amount_in=amount_in,
            amount_out=out,
            execution_price=execution_price,
            spot_before=spot_before,
            spot_after=reference_after / stable_after,
            slippage=(execution_price - spot_before) / spot_before,
            fee_paid=fee,
            reserve_stable_after=stable_after,
            reserve_reference_after=reference_after,
        )

    def quote(self, amount_in: float, side: str) -> Quote:
        """What ``swap`` would return, without changing state."""
        r = self._compute(amount_in, side)
        return Quote(
            side=r.side,
            amount_in=r.amount_in,
            amount_out=r.amount_out,
            execution_price=r.execution_price,
            spot_before=r.spot_before,
            spot_after=r.spot_after,
            slippage=r.slippage,
            fee_paid=r.fee_paid,
        )

    def swap(self, amount_in: float, side: str) -> SwapResult:
        """Execute a swap: updates reserves and the input token's fee counter only."""
        r = self._compute(amount_in, side)
        self.reserve_stable = r.reserve_stable_after
        self.reserve_reference = r.reserve_reference_after
        if side == SELL_STABLE:
            self.cumulative_fees_stable += r.fee_paid
        else:
            self.cumulative_fees_reference += r.fee_paid
        return r

    def remove_liquidity(self, fraction: float) -> LiquidityResult:
        """Withdraw ``fraction`` of the current pool: both reserves scale by
        ``1 - fraction``. Raises ``AMMError`` without mutating on an invalid fraction or
        one that would drain the reserves."""
        if isinstance(fraction, bool) or not isinstance(fraction, int | float):
            raise AMMError("fraction must be a number")
        fraction = float(fraction)
        if not (math.isfinite(fraction) and 0 < fraction <= 1):
            raise AMMError("fraction must be in (0, 1]")
        stable_out = self.reserve_stable * fraction
        reference_out = self.reserve_reference * fraction
        stable_after = self.reserve_stable - stable_out
        reference_after = self.reserve_reference - reference_out
        if not (stable_after > 0 and reference_after > 0):
            raise AMMError("would drain reserves")
        self.reserve_stable = stable_after
        self.reserve_reference = reference_after
        self.lp_supply *= 1 - fraction
        self.liquidity_removals += 1
        return LiquidityResult(
            fraction=fraction,
            stable_out=stable_out,
            reference_out=reference_out,
            reserve_stable_after=stable_after,
            reserve_reference_after=reference_after,
        )

    # -- Subsystem / ActionTarget -----------------------------------------

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        """No per-phase behaviour; the AMM only acts when actions are routed to it."""

    def execute(self, ctx: RunContext, action: Action) -> ExecutionResult:
        if action.kind == "remove_liquidity":
            return self._execute_remove(ctx, action)
        params = action.params
        side = params.get("side")
        amount_in = params.get("amount_in")
        try:
            if action.kind != "swap":
                raise AMMError(f"unknown action kind {action.kind!r}")
            if isinstance(amount_in, bool) or not isinstance(amount_in, int | float):
                raise AMMError("amount_in must be a number")
            r = self.swap(float(amount_in), side)
        except AMMError as exc:
            reason = str(exc)
            ctx.events.emit(
                step=ctx.clock.step_index,
                kind="swap_rejected",
                source=self.name,
                payload={
                    "source": action.source,
                    "side": side,
                    "amount_in": amount_in,
                    "reason": reason,
                },
            )
            return ExecutionResult(ok=False, detail={"error": reason})

        payload = {
            "source": action.source,
            "side": r.side,
            "amount_in": r.amount_in,
            "amount_out": r.amount_out,
            "execution_price": r.execution_price,
            "spot_before": r.spot_before,
            "spot_after": r.spot_after,
            "slippage": r.slippage,
            "fee_paid": r.fee_paid,
            "reserve_stable": r.reserve_stable_after,
            "reserve_reference": r.reserve_reference_after,
        }
        ctx.events.emit(
            step=ctx.clock.step_index, kind="swap_executed", source=self.name, payload=payload
        )
        return ExecutionResult(ok=True, detail=payload)

    def _execute_remove(self, ctx: RunContext, action: Action) -> ExecutionResult:
        fraction = action.params.get("fraction")
        try:
            r = self.remove_liquidity(fraction)
        except AMMError as exc:
            reason = str(exc)
            ctx.events.emit(
                step=ctx.clock.step_index,
                kind="liquidity_rejected",
                source=self.name,
                payload={"source": action.source, "fraction": fraction, "reason": reason},
            )
            return ExecutionResult(ok=False, detail={"error": reason})

        payload = {
            "source": action.source,
            "fraction": r.fraction,
            "stable_out": r.stable_out,
            "reference_out": r.reference_out,
            "reserve_stable": r.reserve_stable_after,
            "reserve_reference": r.reserve_reference_after,
        }
        ctx.events.emit(
            step=ctx.clock.step_index, kind="liquidity_removed", source=self.name, payload=payload
        )
        return ExecutionResult(ok=True, detail=payload)

    def snapshot(self) -> dict:
        snap = {
            "reserve_stable": self.reserve_stable,
            "reserve_reference": self.reserve_reference,
            "fee_bps": self.fee_bps,
            "k": self.k,
            "spot_price": self.spot_price,
            "cumulative_fees_stable": self.cumulative_fees_stable,
            "cumulative_fees_reference": self.cumulative_fees_reference,
        }
        if self.liquidity_removals:  # Story 3.8: snapshots without a removal unchanged
            snap |= {"lp_supply": self.lp_supply, "liquidity_removals": self.liquidity_removals}
        return snap
