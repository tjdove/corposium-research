"""The only types the kernel talks to.

Protocol modules and agents implement these structurally (or subclass them
explicitly). The kernel never imports a concrete module; it routes ``Action``
objects by ``target`` name without knowing what they mean.

``snapshot()`` is optional in the sense that a class which explicitly subclasses
``Subsystem`` (or ``ActionSource`` / ``ActionTarget``) inherits the default
``{}``. A purely structural implementer must define it, because ``Registry``
checks ``isinstance(sub, Subsystem)`` on registration.

``ReservesView``, ``PegView`` and ``ReferenceView`` are the read-only accessors the
termination check consumes; a subsystem that can answer them simply exposes the
property.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext


class KernelError(Exception):
    """Raised when the kernel is wired or driven incorrectly."""


@dataclass(frozen=True)
class Action:
    source: str
    target: str
    kind: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    detail: Mapping[str, Any]


@runtime_checkable
class Subsystem(Protocol):
    name: str
    phases: frozenset[Phase]

    def on_phase(self, ctx: RunContext, phase: Phase) -> None: ...

    def snapshot(self) -> dict:
        return {}


@runtime_checkable
class ActionSource(Subsystem, Protocol):
    def decide(self, ctx: RunContext) -> list[Action]: ...


@runtime_checkable
class ActionTarget(Subsystem, Protocol):
    def execute(self, ctx: RunContext, action: Action) -> ExecutionResult: ...


@runtime_checkable
class ReservesView(Protocol):
    @property
    def reserves_exhausted(self) -> bool: ...


@runtime_checkable
class PegView(Protocol):
    @property
    def peg_deviation(self) -> float: ...  # fraction; 0.0 = at peg

    @property
    def spot_price(self) -> float: ...  # reference per unit stable


@runtime_checkable
class ReferenceView(Protocol):
    """The market price a venue is judged against under ``peg_recovered.reference:
    oracle`` (Story 2.8): the oracle's *published* price, ``None`` before its first
    publish. ``Registry.find`` returns the first registered subsystem that has it."""

    @property
    def published_price(self) -> float | None: ...
