"""Chainlink-style price oracle: a stale, rule-gated copy of a reference price.

A mechanism, not an actor. Once per step in ``ORACLE_UPDATE`` it reads
``source.price`` and publishes it only when a rule fires, checked in this order::

    ref = source.price
    if never published:                                  publish(ref, "initial")
    elif step - last_update_step >= heartbeat_steps:     publish(ref, "heartbeat")
    elif |ref / published - 1| * 100 >= threshold_pct:   publish(ref, "deviation")
    else:                                                no-op

The order only decides the ``reason`` string; the published value is ``ref`` either
way. ``deviation_threshold_pct`` is a percent (``0.5`` = half a percent). A threshold
of ``0`` means no deviation filtering: the deviation branch fires every step, so the
oracle publishes every step.

Phase order runs ``ENVIRONMENT_UPDATE`` before ``ORACLE_UPDATE``, so the oracle always
sees the current step's reference price.

The oracle holds a direct reference to its price source (anything with a ``price``
attribute); it does not look it up through the registry. It is deliberately **not** a
``PegView``: termination reads the AMM's peg deviation, and agents compare the AMM
against this oracle's ``price``. Neither an ``ActionSource`` nor an ``ActionTarget``.

Event: ``oracle_updated`` with ``{step, price, reason}``, only when it publishes.
Construction validates and raises ``ValueError``; ``on_phase`` never raises.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from depeg_sim.kernel.config import OracleConfig
from depeg_sim.kernel.interfaces import Subsystem
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

INITIAL = "initial"
HEARTBEAT = "heartbeat"
DEVIATION = "deviation"


@runtime_checkable
class PriceSource(Protocol):
    @property
    def price(self) -> float: ...


class Oracle(Subsystem):
    def __init__(
        self,
        heartbeat_steps: int,
        deviation_threshold_pct: float,
        source: PriceSource,
        name: str = "oracle",
    ) -> None:
        if isinstance(heartbeat_steps, bool) or not isinstance(heartbeat_steps, int):
            raise ValueError(f"heartbeat_steps must be an int, got {heartbeat_steps!r}")
        if heartbeat_steps <= 0:
            raise ValueError(f"heartbeat_steps must be > 0, got {heartbeat_steps}")
        if not (math.isfinite(deviation_threshold_pct) and deviation_threshold_pct >= 0):
            raise ValueError(f"deviation_threshold_pct must be >= 0, got {deviation_threshold_pct}")
        if not isinstance(source, PriceSource):
            raise ValueError(f"source must expose a price, got {type(source).__name__}")
        self.name = name
        self.phases = frozenset({Phase.ORACLE_UPDATE})
        self.heartbeat_steps = heartbeat_steps
        self.deviation_threshold_pct = float(deviation_threshold_pct)
        self.source = source
        self._published_price: float | None = None
        self._last_update_step: int | None = None
        self._staleness_steps = 0

    @classmethod
    def from_config(cls, cfg: OracleConfig, source: PriceSource) -> Oracle:
        return cls(
            heartbeat_steps=cfg.heartbeat_steps,
            deviation_threshold_pct=cfg.deviation_threshold_pct,
            source=source,
        )

    # -- views -------------------------------------------------------------

    @property
    def price(self) -> float | None:
        """The published price; ``None`` until the first publish."""
        return self._published_price

    @property
    def published_price(self) -> float | None:
        """Alias of ``price``: satisfies the kernel's ``ReferenceView`` (Story 2.8)."""
        return self._published_price

    @property
    def last_update_step(self) -> int | None:
        return self._last_update_step

    @property
    def staleness_steps(self) -> int:
        """Steps since the last publish as of the latest ``ORACLE_UPDATE``; 0 before
        the first publish and on a publishing step."""
        return self._staleness_steps

    @property
    def reference_price(self) -> float:
        """Pass-through to ``source.price``, for diagnostics only."""
        return self.source.price

    # -- Subsystem ---------------------------------------------------------

    def _reason(self, step: int, ref: float) -> str | None:
        if self._published_price is None or self._last_update_step is None:
            return INITIAL
        if step - self._last_update_step >= self.heartbeat_steps:
            return HEARTBEAT
        published = self._published_price
        if published == 0:
            deviation_pct = 0.0 if ref == 0 else math.inf
        else:
            deviation_pct = abs(ref / published - 1) * 100
        if deviation_pct >= self.deviation_threshold_pct:
            return DEVIATION
        return None

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        step = ctx.clock.step_index
        ref = self.source.price
        reason = self._reason(step, ref)
        if reason is not None:
            self._published_price = ref
            self._last_update_step = step
            ctx.events.emit(
                step=step,
                kind="oracle_updated",
                source=self.name,
                payload={"step": step, "price": ref, "reason": reason},
            )
        if self._last_update_step is not None:
            self._staleness_steps = step - self._last_update_step

    def snapshot(self) -> dict:
        return {
            "published_price": self._published_price,
            "last_update_step": self._last_update_step,
        }
