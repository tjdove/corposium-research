"""Exogenous reference price: a seeded log-normal walk with scheduled shocks.

This is the Market Environment Layer. ``ReferencePrice`` is what the stablecoin is
"really worth" off-chain; the oracle publishes a lagged copy of it and agents compare
the AMM against that copy.

Update rule, once per step in ``ENVIRONMENT_UPDATE``::

    step 0:     prev = base_price
    each step:  p = prev
                if volatility_per_step > 0:
                    p *= exp(volatility_per_step * ctx.rng.standard_normal())
                if step in shocks:  p *= 1 + shocks[step] / 100
                emit price_updated {step, price: p, prev_price: prev, shock_pct}
                prev = p

``volatility_per_step`` is the per-step log-return standard deviation. Exactly one
``ctx.rng.standard_normal()`` is drawn per step when it is > 0, and **none** when it is
0, so a shock-only environment leaves the run's random stream untouched.

Shocks: the scenario field ``environment.shocks[].pct`` is a **percent**, not a
fraction. ``-5.0`` means minus five percent (``price *= 0.95``); ``0.5`` means plus
half a percent. A shock at step 0 applies to the first price. Two shocks on the same
step are summed (``-3`` and ``-2`` act as one ``-5`` shock, not ``0.97 * 0.98``). A
step's summed shock must be > -100 so the price stays positive.

Construction validates and raises ``ValueError``; ``on_phase`` never raises.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from depeg_sim.kernel.config import EnvironmentConfig, ShockEvent
from depeg_sim.kernel.interfaces import Subsystem
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext


def _shocks_by_step(shocks: Sequence[ShockEvent] | Mapping[int, float]) -> dict[int, float]:
    items = shocks.items() if isinstance(shocks, Mapping) else ((s.step, s.pct) for s in shocks)
    by_step: dict[int, float] = {}
    for step, pct in items:
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise ValueError(f"shock step must be an int >= 0, got {step!r}")
        if not math.isfinite(pct):
            raise ValueError(f"shock pct must be finite, got {pct!r}")
        by_step[step] = by_step.get(step, 0.0) + float(pct)
    for step, pct in by_step.items():
        if not pct > -100:
            raise ValueError(f"shock pct at step {step} must be > -100, got {pct}")
    return by_step


class ReferencePrice(Subsystem):
    def __init__(
        self,
        base_price: float,
        volatility_per_step: float,
        shocks: Sequence[ShockEvent] | Mapping[int, float] = (),
        name: str = "environment",
    ) -> None:
        if not (math.isfinite(base_price) and base_price > 0):
            raise ValueError(f"base_price must be > 0, got {base_price}")
        if not (math.isfinite(volatility_per_step) and volatility_per_step >= 0):
            raise ValueError(f"volatility_per_step must be >= 0, got {volatility_per_step}")
        self.name = name
        self.phases = frozenset({Phase.ENVIRONMENT_UPDATE})
        self.base_price = float(base_price)
        self.volatility_per_step = float(volatility_per_step)
        self._shocks_by_step = _shocks_by_step(shocks)
        self._price = self.base_price
        self._prev_price = self.base_price
        self.step_applied_shocks: list[tuple[int, float]] = []

    @classmethod
    def from_config(cls, cfg: EnvironmentConfig) -> ReferencePrice:
        return cls(
            base_price=cfg.base_price,
            volatility_per_step=cfg.volatility_per_step,
            shocks=cfg.shocks,
        )

    @property
    def price(self) -> float:
        """This step's reference price (``base_price`` before the first update)."""
        return self._price

    @property
    def prev_price(self) -> float:
        return self._prev_price

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        step = ctx.clock.step_index
        prev = self._price
        p = prev
        if self.volatility_per_step > 0:
            p *= math.exp(self.volatility_per_step * float(ctx.rng.standard_normal()))
        shock_pct = self._shocks_by_step.get(step, 0.0)
        if step in self._shocks_by_step:
            p *= 1 + shock_pct / 100
            self.step_applied_shocks.append((step, shock_pct))
        self._prev_price = prev
        self._price = p
        ctx.events.emit(
            step=step,
            kind="price_updated",
            source=self.name,
            payload={"step": step, "price": p, "prev_price": prev, "shock_pct": shock_pct},
        )

    def snapshot(self) -> dict:
        return {
            "price": self._price,
            "prev_price": self._prev_price,
            "step_applied_shocks": [list(s) for s in self.step_applied_shocks],
        }
