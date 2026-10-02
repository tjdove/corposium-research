"""Checkpoint writer.

A checkpoint captures the run at the end of a step: ``step`` is the number of
steps completed (so the checkpoint written while step index 49 runs has
``step == 50``) and ``elapsed_seconds`` is the matching clock time. Keys are
sorted and the dump is compact so two deterministic runs produce identical bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION


def checkpoint_data(ctx: RunContext) -> dict:
    steps_done = ctx.clock.step_index + 1
    return {
        "step": steps_done,
        "elapsed_seconds": steps_done * ctx.clock.interval_seconds,
        "phase_order_version": PHASE_ORDER_VERSION,
        "rng_state": ctx.rng.bit_generator.state,
        "subsystems": {s.name: s.snapshot() for s in ctx.registry.all()},
    }


def write_checkpoint(ctx: RunContext, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(checkpoint_data(ctx), sort_keys=True, indent=None)
    path.write_text(text, encoding="utf-8")
