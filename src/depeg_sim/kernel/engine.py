"""Step loop. Orchestrates subsystems; contains no mechanism logic.

One step runs every phase in ``PHASES`` order. Within each phase:

1. If the phase is ``AGENT_DECISION``, ``ctx.action_queue`` and
   ``ctx.execution_results`` are cleared first, so both only ever hold the current
   step's actions and their results.
2. ``on_phase(ctx, phase)`` is called on every registered subsystem whose
   ``phases`` contains the phase, in registration order.
3. Then the kernel's phase-specific action runs:
   - ``AGENT_DECISION``: every ``ActionSource`` (registration order) is asked to
     ``decide(ctx)`` and its actions are appended to ``ctx.action_queue``.
   - ``ACTION_QUEUE``: nothing; hooks in this phase see the full queue.
   - ``EXECUTION``: each queued action is routed, in queue order, to the
     ``ActionTarget`` named by ``action.target``, and ``(action, result)`` is
     appended to ``ctx.execution_results``. An unknown target is a ``KernelError``,
     never a skip.
   - ``PERSISTENCE``: a checkpoint is written if one is due.

Ordering subtlety: ``on_phase`` hooks run *before* the kernel's phase-specific
action in every phase. A module registered for ``EXECUTION`` therefore gets
``on_phase(EXECUTION)`` before any action is routed to it, and an
``ActionSource`` registered for ``AGENT_DECISION`` gets ``on_phase`` before
``decide``. A module that needs to act after all actions have settled should
use ``PROTOCOL_EVENTS``.

Queue clearing: the story's step loop clears the queue at the start of
``ACTION_QUEUE``, but ``ACTION_QUEUE`` follows ``AGENT_DECISION`` in
``PHASES``, so that would discard every action before ``EXECUTION``. The clear
is done at the start of ``AGENT_DECISION`` instead (see story 1.3 Completion
Notes).

After the last phase, ``termination.check`` runs. If a condition fires the run
stops (writing a final checkpoint when checkpointing is enabled and one was not
already written this step); otherwise the clock ticks and the next step begins.

The kernel emits exactly two events itself: ``run_started`` (step 0) and
``run_terminated`` (the last step index).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from depeg_sim.kernel import termination
from depeg_sim.kernel.checkpoint import write_checkpoint
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.events import Decision, Event
from depeg_sim.kernel.interfaces import Action, ActionTarget, KernelError
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION, PHASES, Phase

KERNEL_SOURCE = "kernel"


@dataclass
class RunResult:
    steps_run: int
    terminated_by: str
    events: list[Event]
    decisions: list[Decision]
    checkpoints: list[Path]


class Engine:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.checkpoints: list[Path] = []

    def run(self) -> RunResult:
        ctx = self.ctx
        ctx.events.emit(
            step=ctx.clock.step_index,
            kind="run_started",
            source=KERNEL_SOURCE,
            payload={
                "seed": ctx.seed,
                "scenario_hash": ctx.config.content_hash(),
                "phase_order_version": PHASE_ORDER_VERSION,
            },
        )
        while True:
            self._step()
            reason = termination.check(ctx)
            if reason is not None:
                break
            ctx.clock.tick()

        steps_run = ctx.clock.step_index + 1
        if self._checkpointing() and not self._checkpoint_due():
            self._write_checkpoint()
        ctx.events.emit(
            step=ctx.clock.step_index,
            kind="run_terminated",
            source=KERNEL_SOURCE,
            payload={"reason": reason, "steps_run": steps_run},
        )
        return RunResult(
            steps_run=steps_run,
            terminated_by=reason,
            events=ctx.events.all(),
            decisions=ctx.decisions.all(),
            checkpoints=list(self.checkpoints),
        )

    def _step(self) -> None:
        ctx = self.ctx
        registry = ctx.registry
        for phase in PHASES:
            if phase is Phase.AGENT_DECISION:
                ctx.action_queue.clear()
                ctx.execution_results.clear()
            for sub in registry.by_phase(phase):
                sub.on_phase(ctx, phase)
            if phase is Phase.AGENT_DECISION:
                for src in registry.sources():
                    ctx.action_queue.extend(src.decide(ctx))
            elif phase is Phase.EXECUTION:
                for action in ctx.action_queue:
                    self._route(action)
            elif phase is Phase.PERSISTENCE and self._checkpoint_due():
                self._write_checkpoint()

    def _route(self, action: Action) -> None:
        ctx = self.ctx
        step = ctx.clock.step_index
        if action.target not in ctx.registry:
            raise KernelError(f"step {step}: unknown action target {action.target!r} in {action}")
        target = ctx.registry.get(action.target)
        if not isinstance(target, ActionTarget):
            raise KernelError(
                f"step {step}: subsystem {action.target!r} is not an ActionTarget; "
                f"cannot execute {action}"
            )
        ctx.execution_results.append((action, target.execute(ctx, action)))

    def _checkpointing(self) -> bool:
        return (
            self.ctx.output_dir is not None and self.ctx.config.metrics.checkpoint_every is not None
        )

    def _checkpoint_due(self) -> bool:
        if not self._checkpointing():
            return False
        every = self.ctx.config.metrics.checkpoint_every
        return (self.ctx.clock.step_index + 1) % every == 0

    def _write_checkpoint(self) -> None:
        steps_done = self.ctx.clock.step_index + 1
        path = self.ctx.output_dir / "checkpoints" / f"step-{steps_done:06d}.json"
        write_checkpoint(self.ctx, path)
        self.checkpoints.append(path)
