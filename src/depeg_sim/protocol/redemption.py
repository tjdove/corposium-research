"""Redemption facility: the peg's price promise, with finite reserves and throughput.

One stable unit is redeemable for ``peg_price`` reference, less a spread, from a
finite reserve, at a bounded rate. When demand exceeds the rate, requests queue.

State:      ``reserves`` (reference units), ``spread_bps``, ``capacity_per_step``
            (**stable** units per step), a FIFO queue of ``RedemptionRequest``.
Actions:    ``redeem`` with ``params = {"amount_stable": float}``, routed in
            ``EXECUTION``; it only queues the request.
Settlement: on ``PROTOCOL_EVENTS`` each step, ``process(ctx)`` fills the queue in
            FIFO order::

                ppu        = peg_price * (1 - spread_bps / 10_000)   # reference per stable
                affordable = reserves / ppu                          # stable
                fill       = min(remaining_request, remaining_capacity, affordable)
                paid       = fill * ppu                              # reference

            A partially filled request stays at the head with its remainder.
            ``redeem_fulfilled.reason`` is ``"full"``, ``"partial_reserves"`` (the
            fill used up the reserves) or ``"partial_capacity"`` (it used up this
            step's capacity).
Exhaustion: ``reserves_exhausted`` (the ``ReservesView`` the kernel's termination
            check reads) becomes True the first step reserves are effectively zero
            **and** the queue is non-empty. It latches and its event is emitted once.
            Empty reserves with nothing queued is a defense that spent everything and
            was not tested further, not a failure.

Capacity schedule (Story 2.5): ``capacity_schedule`` is a list of ``(step,
capacity_per_step)`` with strictly ascending steps. At the start of ``PROTOCOL_EVENTS``
on a scheduled step, before ``process``, capacity changes to the new value and
``capacity_changed {step, old, new}`` is emitted (once per entry). It stands for a
redemption channel whose throughput changes on a known date, e.g. banks reopening.

Units: capacity and queue amounts are stable; reserves and payouts are reference.
Epic 2 calibrates ``capacity_per_step`` to real redemption throughput per slot.

``paid_total`` accumulates each fill's payout at the spread in force at fill time.
``set_spread_bps`` therefore changes future payouts only; history is never
recomputed.

Construction raises ``ValueError`` on invalid parameters. ``execute`` and
``on_phase`` never raise for domain reasons: a bad request becomes
``ExecutionResult(ok=False)`` plus a ``redeem_rejected`` event.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from depeg_sim.kernel.config import RedemptionConfig
from depeg_sim.kernel.interfaces import Action, ActionTarget, ExecutionResult
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

BPS = 10_000
EPS = 1e-12  # stable-unit residue below this is treated as zero
EXHAUSTED_UNITS = 1e-9  # reserves below this many units' payout cannot pay anything

FULL = "full"
PARTIAL_CAPACITY = "partial_capacity"
PARTIAL_RESERVES = "partial_reserves"


@dataclass
class RedemptionRequest:
    """One queued request. Mutable: ``remaining`` shrinks as it is filled."""

    source: str
    amount: float
    remaining: float
    step_requested: int


def _check_spread(bps: int) -> int:
    if isinstance(bps, bool) or not isinstance(bps, int) or not 0 <= bps < BPS:
        raise ValueError(f"spread_bps must be an int in [0, {BPS}), got {bps!r}")
    return bps


class RedemptionModule(ActionTarget):
    def __init__(
        self,
        reserves: float,
        spread_bps: int,
        capacity_per_step: float,
        peg_price: float = 1.0,
        name: str = "redemption",
        capacity_schedule: Sequence[tuple[int, float]] = (),
    ) -> None:
        if not (math.isfinite(reserves) and reserves >= 0):
            raise ValueError(f"reserves must be >= 0, got {reserves}")
        _check_spread(spread_bps)
        if not (math.isfinite(capacity_per_step) and capacity_per_step > 0):
            raise ValueError(f"capacity_per_step must be > 0, got {capacity_per_step}")
        if not (math.isfinite(peg_price) and peg_price > 0):
            raise ValueError(f"peg_price must be > 0, got {peg_price}")
        schedule = [(int(st), float(c)) for st, c in capacity_schedule]
        steps = [st for st, _ in schedule]
        if any(st < 0 for st in steps) or any(
            b <= a for a, b in zip(steps, steps[1:], strict=False)
        ):
            raise ValueError(
                f"capacity_schedule steps must be >= 0 and strictly ascending: {steps}"
            )
        if any(not (math.isfinite(c) and c > 0) for _, c in schedule):
            raise ValueError("capacity_schedule capacities must be > 0")
        self._schedule = dict(schedule)
        self.name = name
        self.phases = frozenset({Phase.EXECUTION, Phase.PROTOCOL_EVENTS})
        self.capacity_per_step = float(capacity_per_step)
        self.peg_price = float(peg_price)
        self._reserves = float(reserves)
        self._spread_bps = spread_bps
        self._queue: deque[RedemptionRequest] = deque()
        self._requested_total = 0.0
        self._fulfilled_total = 0.0
        self._paid_total = 0.0
        self._exhausted = False

    @classmethod
    def from_config(cls, cfg: RedemptionConfig) -> RedemptionModule:
        return cls(
            reserves=cfg.reserves,
            spread_bps=cfg.spread_bps,
            capacity_per_step=cfg.capacity_per_step,
            peg_price=cfg.peg_price,
            capacity_schedule=[(c.step, c.capacity_per_step) for c in cfg.capacity_schedule],
        )

    # -- views -------------------------------------------------------------

    @property
    def reserves(self) -> float:
        """Reference units left to pay redemptions with."""
        return self._reserves

    @property
    def spread_bps(self) -> int:
        return self._spread_bps

    @property
    def payout_per_unit(self) -> float:
        """Reference paid per stable unit redeemed, at the current spread."""
        return self.peg_price * (1 - self._spread_bps / BPS)

    @property
    def queue_depth(self) -> int:
        """Number of pending requests (a partially filled head counts as one)."""
        return len(self._queue)

    @property
    def queued_total(self) -> float:
        """Stable units still pending."""
        return sum(r.remaining for r in self._queue)

    @property
    def requested_total(self) -> float:
        """Stable units ever accepted into the queue."""
        return self._requested_total

    @property
    def fulfilled_total(self) -> float:
        """Stable units redeemed so far."""
        return self._fulfilled_total

    @property
    def paid_total(self) -> float:
        """Reference paid so far, each fill at its own fill-time payout."""
        return self._paid_total

    @property
    def reserves_exhausted(self) -> bool:
        return self._exhausted

    @property
    def pending(self) -> list[RedemptionRequest]:
        """Copy of the queue, head first."""
        return list(self._queue)

    # -- levers ------------------------------------------------------------

    def set_spread_bps(self, ctx: RunContext, bps: int, source: str = "redemption") -> None:
        """Change the spread for future fills; emits ``spread_changed``. Raises
        ``ValueError`` if ``bps`` is outside ``[0, 10_000)``."""
        _check_spread(bps)
        old, self._spread_bps = self._spread_bps, bps
        ctx.events.emit(
            step=ctx.clock.step_index,
            kind="spread_changed",
            source=self.name,
            payload={"old": old, "new": bps, "source": source},
        )

    # -- Subsystem / ActionTarget -----------------------------------------

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        """Settlement runs on ``PROTOCOL_EVENTS``; nothing happens on ``EXECUTION``
        (requests arrive through ``execute``)."""
        if phase is Phase.PROTOCOL_EVENTS:
            self._apply_schedule(ctx)
            self.process(ctx)

    def _apply_schedule(self, ctx: RunContext) -> None:
        step = ctx.clock.step_index
        if step not in self._schedule:
            return
        old, new = self.capacity_per_step, self._schedule[step]
        self.capacity_per_step = new
        ctx.events.emit(
            step=step,
            kind="capacity_changed",
            source=self.name,
            payload={"step": step, "old": old, "new": new},
        )

    def execute(self, ctx: RunContext, action: Action) -> ExecutionResult:
        step = ctx.clock.step_index
        amount = action.params.get("amount_stable")
        reason = None
        if action.kind != "redeem":
            reason = f"unknown action kind {action.kind!r}"
        elif isinstance(amount, bool) or not isinstance(amount, int | float):
            reason = "amount_stable must be a number"
        elif not (math.isfinite(amount) and amount > 0):
            reason = "amount_stable must be > 0"
        if reason is not None:
            ctx.events.emit(
                step=step,
                kind="redeem_rejected",
                source=self.name,
                payload={"source": action.source, "reason": reason},
            )
            return ExecutionResult(ok=False, detail={"error": reason})

        amount = float(amount)
        self._queue.append(
            RedemptionRequest(
                source=action.source, amount=amount, remaining=amount, step_requested=step
            )
        )
        self._requested_total += amount
        depth = len(self._queue)
        ctx.events.emit(
            step=step,
            kind="redeem_requested",
            source=self.name,
            payload={"source": action.source, "amount_stable": amount, "queue_depth": depth},
        )
        return ExecutionResult(ok=True, detail={"queued": amount, "queue_depth": depth})

    def process(self, ctx: RunContext) -> None:
        """Fill the queue FIFO up to this step's capacity and the reserves."""
        step = ctx.clock.step_index
        cap = self.capacity_per_step
        ppu = self.payout_per_unit
        while self._queue and cap > EPS and self._reserves > 0:
            req = self._queue[0]
            affordable = self._reserves / ppu
            fill = min(req.remaining, cap, affordable)
            if fill <= 0:
                break
            if fill >= affordable:
                # Reserves-limited: pay out exactly what is left, no float residue.
                paid = self._reserves
                self._reserves = 0.0
            else:
                paid = fill * ppu
                self._reserves -= paid
            cap -= fill
            req.remaining -= fill
            if req.remaining < EPS:
                req.remaining = 0.0
            self._fulfilled_total += fill
            self._paid_total += paid

            if req.remaining == 0.0:
                reason = FULL
            elif self._reserves == 0.0:
                reason = PARTIAL_RESERVES
            else:
                reason = PARTIAL_CAPACITY
            ctx.events.emit(
                step=step,
                kind="redeem_fulfilled",
                source=self.name,
                payload={
                    "source": req.source,
                    "amount_stable": fill,
                    "paid_reference": paid,
                    "remaining_request": req.remaining,
                    "step_requested": req.step_requested,
                    "reason": reason,
                },
            )
            if req.remaining == 0.0:
                self._queue.popleft()

        if not self._exhausted and self._queue and self._reserves < ppu * EXHAUSTED_UNITS:
            self._exhausted = True
            ctx.events.emit(
                step=step,
                kind="reserves_exhausted",
                source=self.name,
                payload={
                    "step": step,
                    "reserves": self._reserves,
                    "queue_depth": self.queue_depth,
                    "queued_total": self.queued_total,
                },
            )

    def snapshot(self) -> dict:
        return {
            "reserves": self._reserves,
            "spread_bps": self._spread_bps,
            "capacity_per_step": self.capacity_per_step,
            "peg_price": self.peg_price,
            "queue_depth": self.queue_depth,
            "queued_total": self.queued_total,
            "fulfilled_total": self._fulfilled_total,
            "paid_total": self._paid_total,
            "reserves_exhausted": self._exhausted,
        }
