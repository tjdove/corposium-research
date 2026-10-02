"""Termination check, evaluated once per step after PERSISTENCE.

Conditions are checked in fixed precedence order ``reserves_exhausted``,
``peg_recovered``, ``max_steps``; the first that fires is returned. The kernel
reads domain state only through the ``ReservesView`` / ``PegView`` accessors; a
condition whose view no subsystem provides is skipped.
"""

from __future__ import annotations

from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.interfaces import PegView, ReservesView


def check(ctx: RunContext) -> str | None:
    term = ctx.config.termination

    if term.reserves_exhausted:
        view = ctx.registry.find(ReservesView)
        if view is not None and view.reserves_exhausted:
            return "reserves_exhausted"

    if term.peg_recovered is not None:
        view = ctx.registry.find(PegView)
        if view is not None:
            tracker = ctx.term_state
            if abs(view.peg_deviation) <= term.peg_recovered.tolerance:
                tracker.consecutive_in_band += 1
            else:
                tracker.consecutive_in_band = 0
            if tracker.consecutive_in_band >= term.peg_recovered.for_steps:
                return "peg_recovered"

    if term.max_steps and ctx.clock.step_index + 1 >= ctx.config.steps.max_steps:
        return "max_steps"

    return None
