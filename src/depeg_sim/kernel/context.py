"""Run context: everything one run owns, plus the subsystem registry.

The context is the single handle passed to every subsystem hook. It owns the
run's only random generator (``rng``); the kernel itself never draws from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from depeg_sim.kernel.clock import Clock
from depeg_sim.kernel.config import ScenarioConfig
from depeg_sim.kernel.events import DecisionTrace, EventSink
from depeg_sim.kernel.interfaces import (
    Action,
    ActionSource,
    ActionTarget,
    ExecutionResult,
    KernelError,
    Subsystem,
)
from depeg_sim.kernel.scheduler import Phase


class Registry:
    """Subsystems by name, in registration order. Registration order is call order;
    the registry never sorts."""

    def __init__(self) -> None:
        self._subs: dict[str, Subsystem] = {}

    def register(self, sub: Subsystem) -> None:
        if not isinstance(sub, Subsystem):
            raise KernelError(
                f"{sub!r} does not implement Subsystem (needs name, phases, on_phase and snapshot)"
            )
        if sub.name in self._subs:
            raise KernelError(f"duplicate subsystem name: {sub.name!r}")
        self._subs[sub.name] = sub

    def get(self, name: str) -> Subsystem:
        try:
            return self._subs[name]
        except KeyError:
            raise KernelError(f"no subsystem registered as {name!r}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._subs

    def __len__(self) -> int:
        return len(self._subs)

    def all(self) -> list[Subsystem]:
        return list(self._subs.values())

    def by_phase(self, phase: Phase) -> list[Subsystem]:
        return [s for s in self._subs.values() if phase in s.phases]

    def sources(self) -> list[ActionSource]:
        return [s for s in self._subs.values() if isinstance(s, ActionSource)]

    def targets(self) -> list[ActionTarget]:
        return [s for s in self._subs.values() if isinstance(s, ActionTarget)]

    def find(self, protocol: type) -> Any | None:
        """First registered subsystem satisfying ``protocol`` (a runtime-checkable
        Protocol), or None."""
        for s in self._subs.values():
            if isinstance(s, protocol):
                return s
        return None


@dataclass
class PegRecoveredTracker:
    consecutive_in_band: int = 0


@dataclass
class RunContext:
    config: ScenarioConfig
    seed: int
    rng: np.random.Generator
    clock: Clock
    events: EventSink = field(default_factory=EventSink)
    decisions: DecisionTrace = field(default_factory=DecisionTrace)
    registry: Registry = field(default_factory=Registry)
    action_queue: list[Action] = field(default_factory=list)
    execution_results: list[tuple[Action, ExecutionResult]] = field(default_factory=list)
    term_state: PegRecoveredTracker = field(default_factory=PegRecoveredTracker)
    output_dir: Path | None = None

    @classmethod
    def from_config(
        cls,
        config: ScenarioConfig,
        seed_override: int | None = None,
        output_dir: Path | None = None,
    ) -> RunContext:
        """Build a fresh context. ``seed_override`` (the CLI ``--seed``) wins over
        ``config.seed`` when given. ``output_dir`` is where checkpoints go; with
        None, no checkpoints are written."""
        seed = config.seed if seed_override is None else seed_override
        return cls(
            config=config,
            seed=seed,
            rng=np.random.default_rng(seed),
            clock=Clock(config.steps.interval_seconds),
            output_dir=output_dir,
        )
