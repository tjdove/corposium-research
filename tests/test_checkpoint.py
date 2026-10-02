import json

import numpy as np
from kernel_stubs import RngStub, TargetStub, make_config

from depeg_sim.kernel.checkpoint import write_checkpoint
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION


def run(tmp_path, max_steps=12, every=5):
    ctx = RunContext.from_config(
        make_config(max_steps=max_steps, checkpoint_every=every), output_dir=tmp_path
    )
    ctx.registry.register(RngStub())
    ctx.registry.register(TargetStub())
    return Engine(ctx).run()


def test_checkpoints_at_cadence_and_termination(tmp_path):
    result = run(tmp_path)
    assert [p.name for p in result.checkpoints] == [
        "step-000005.json",
        "step-000010.json",
        "step-000012.json",
    ]
    assert all(p.exists() for p in result.checkpoints)
    steps = [json.loads(p.read_text())["step"] for p in result.checkpoints]
    assert steps == [5, 10, 12]


def test_no_duplicate_final_checkpoint_when_cadence_hits_last_step(tmp_path):
    result = run(tmp_path, max_steps=10, every=5)
    assert [p.name for p in result.checkpoints] == ["step-000005.json", "step-000010.json"]


def test_no_checkpoints_without_cadence(tmp_path):
    assert run(tmp_path, every=None).checkpoints == []
    assert list(tmp_path.iterdir()) == []


def test_no_checkpoints_without_output_dir():
    ctx = RunContext.from_config(make_config(max_steps=12, checkpoint_every=5))
    assert Engine(ctx).run().checkpoints == []


def test_checkpoint_shape_and_sorted_keys(tmp_path):
    result = run(tmp_path)
    text = result.checkpoints[0].read_text()
    data = json.loads(text)
    assert list(data) == sorted(data)
    assert list(data) == [
        "elapsed_seconds",
        "phase_order_version",
        "rng_state",
        "step",
        "subsystems",
    ]
    assert data["step"] == 5
    assert data["elapsed_seconds"] == 5 * 12
    assert data["phase_order_version"] == PHASE_ORDER_VERSION
    assert data["rng_state"]["bit_generator"] == "PCG64"
    assert data["subsystems"] == {
        "rng": {"n_draws": 5, "last": data["subsystems"]["rng"]["last"]},
        "target": {"received": 0},
    }
    assert text == json.dumps(data, sort_keys=True, indent=None)


def test_rng_state_round_trips(tmp_path):
    ctx = RunContext.from_config(make_config())
    ctx.rng.random(17)
    path = tmp_path / "cp.json"
    write_checkpoint(ctx, path)
    restored = np.random.default_rng()
    restored.bit_generator.state = json.loads(path.read_text())["rng_state"]
    assert restored.random(10).tolist() == ctx.rng.random(10).tolist()


def test_checkpoint_bytes_identical_across_runs(tmp_path):
    a = run(tmp_path / "a")
    b = run(tmp_path / "b")
    assert [p.read_bytes() for p in a.checkpoints] == [p.read_bytes() for p in b.checkpoints]
