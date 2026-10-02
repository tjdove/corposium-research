"""Stub subsystems for kernel tests. Test-only; nothing here is a real module.

These are the only place reserve or peg notions appear for Story 1.3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from depeg_sim.kernel.config import ScenarioConfig, load_scenario
from depeg_sim.kernel.interfaces import Action, ExecutionResult, Subsystem
from depeg_sim.kernel.scheduler import PHASES, Phase

BASELINE = Path("scenarios/soros-baseline.yaml")


def make_config(
    *,
    max_steps: int = 10,
    termination: dict[str, Any] | None = None,
    checkpoint_every: int | None = None,
    seed: int = 42,
) -> ScenarioConfig:
    """Baseline scenario with the kernel-relevant fields overridden."""
    data = load_scenario(BASELINE).model_dump(mode="json")
    data["seed"] = seed
    data["steps"]["max_steps"] = max_steps
    data["termination"] = termination or {
        "reserves_exhausted": False,
        "peg_recovered": None,
        "max_steps": True,
    }
    data["metrics"]["checkpoint_every"] = checkpoint_every
    return ScenarioConfig.model_validate(data)


class RecordingStub(Subsystem):
    """Records (step, phase) for every on_phase call. Inherits default snapshot()."""

    def __init__(self, name: str, phases=PHASES) -> None:
        self.name = name
        self.phases = frozenset(phases)
        self.calls: list[tuple[int, Phase]] = []

    def on_phase(self, ctx, phase: Phase) -> None:
        self.calls.append((ctx.clock.step_index, phase))


class RngStub:
    """Purely structural Subsystem: draws once per step and emits the draw."""

    def __init__(self, name: str = "rng") -> None:
        self.name = name
        self.phases = frozenset({Phase.ENVIRONMENT_UPDATE})
        self.draws: list[float] = []

    def on_phase(self, ctx, phase: Phase) -> None:
        x = float(ctx.rng.random())
        self.draws.append(x)
        ctx.events.emit(ctx.clock.step_index, "draw", self.name, {"x": x})

    def snapshot(self) -> dict:
        return {"n_draws": len(self.draws), "last": self.draws[-1] if self.draws else None}


class ReservesStub(Subsystem):
    """Implements ReservesView: flag goes true at ``exhaust_at_step``."""

    def __init__(self, exhaust_at_step: int, name: str = "reserves") -> None:
        self.name = name
        self.phases = frozenset({Phase.PROTOCOL_EVENTS})
        self.exhaust_at_step = exhaust_at_step
        self._exhausted = False

    def on_phase(self, ctx, phase: Phase) -> None:
        if ctx.clock.step_index >= self.exhaust_at_step:
            self._exhausted = True

    @property
    def reserves_exhausted(self) -> bool:
        return self._exhausted


class PegStub(Subsystem):
    """Implements PegView: deviation for the current step from a fixed list
    (last value repeats past the end)."""

    def __init__(self, deviations: list[float], name: str = "peg") -> None:
        self.name = name
        self.phases = frozenset({Phase.METRIC_UPDATE})
        self.deviations = deviations
        self._step = 0

    def on_phase(self, ctx, phase: Phase) -> None:
        self._step = ctx.clock.step_index

    @property
    def peg_deviation(self) -> float:
        return self.deviations[min(self._step, len(self.deviations) - 1)]


class SourceStub(Subsystem):
    """ActionSource: one action per step to ``target``. By default a ``ping`` with
    ``{"n": step}``; pass ``kind`` and ``params`` to send something else (the same
    params every step)."""

    def __init__(
        self,
        name: str = "source",
        target: str = "target",
        phases=(),
        kind: str = "ping",
        params: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.phases = frozenset(phases)
        self.target = target
        self.kind = kind
        self.params = params
        self.log: list[tuple[str, int]] = []

    def on_phase(self, ctx, phase: Phase) -> None:
        self.log.append(("on_phase", ctx.clock.step_index))

    def decide(self, ctx) -> list[Action]:
        step = ctx.clock.step_index
        self.log.append(("decide", step))
        params = {"n": step} if self.params is None else dict(self.params)
        return [Action(source=self.name, target=self.target, kind=self.kind, params=params)]


class TargetStub(Subsystem):
    """ActionTarget: records each action it receives, and on_phase calls."""

    def __init__(self, name: str = "target", phases=()) -> None:
        self.name = name
        self.phases = frozenset(phases)
        self.received: list[Action] = []
        self.log: list[tuple[str, int]] = []

    def on_phase(self, ctx, phase: Phase) -> None:
        self.log.append(("on_phase", ctx.clock.step_index))

    def execute(self, ctx, action: Action) -> ExecutionResult:
        self.received.append(action)
        self.log.append(("execute", ctx.clock.step_index))
        return ExecutionResult(ok=True, detail={})

    def snapshot(self) -> dict:
        return {"received": len(self.received)}


class QueueObserverStub(Subsystem):
    """Records the queue length it sees in each phase it is registered for."""

    def __init__(self, phases, name: str = "observer") -> None:
        self.name = name
        self.phases = frozenset(phases)
        self.seen: list[tuple[int, Phase, int]] = []

    def on_phase(self, ctx, phase: Phase) -> None:
        self.seen.append((ctx.clock.step_index, phase, len(ctx.action_queue)))


class ScriptedPriceSource(Subsystem):
    """A price source for oracle tests: on ENVIRONMENT_UPDATE, ``price`` becomes
    ``prices[step]`` (last value repeats past the end). ``price`` is also a plain
    attribute, so a test can set it directly without running a phase."""

    def __init__(self, prices: list[float], name: str = "scripted") -> None:
        self.name = name
        self.phases = frozenset({Phase.ENVIRONMENT_UPDATE})
        self.prices = list(prices)
        self.price = self.prices[0]

    def on_phase(self, ctx, phase: Phase) -> None:
        self.price = self.prices[min(ctx.clock.step_index, len(self.prices) - 1)]
