import pytest
from kernel_stubs import RecordingStub, RngStub, SourceStub, TargetStub, make_config

from depeg_sim.kernel.context import Registry, RunContext
from depeg_sim.kernel.interfaces import KernelError, PegView
from depeg_sim.kernel.scheduler import Phase


def test_from_config_uses_config_seed_and_interval():
    cfg = make_config(seed=7)
    ctx = RunContext.from_config(cfg)
    assert ctx.seed == 7
    assert ctx.clock.interval_seconds == cfg.steps.interval_seconds
    assert ctx.clock.step_index == 0
    assert ctx.action_queue == []
    assert ctx.output_dir is None


def test_same_seed_same_rng_sequence():
    cfg = make_config()
    a = RunContext.from_config(cfg).rng.random(20)
    b = RunContext.from_config(cfg).rng.random(20)
    assert a.tolist() == b.tolist()


def test_seed_override_wins():
    cfg = make_config(seed=42)
    base = RunContext.from_config(cfg)
    over = RunContext.from_config(cfg, seed_override=43)
    assert over.seed == 43
    assert base.rng.random(5).tolist() != over.rng.random(5).tolist()
    same = RunContext.from_config(make_config(seed=43))
    assert RunContext.from_config(cfg, seed_override=43).rng.random(5).tolist() == (
        same.rng.random(5).tolist()
    )


def test_seed_override_zero_is_honoured():
    assert RunContext.from_config(make_config(seed=42), seed_override=0).seed == 0


def test_registry_preserves_registration_order():
    reg = Registry()
    names = ["z", "a", "m"]
    for n in names:
        reg.register(RecordingStub(n))
    assert [s.name for s in reg.all()] == names
    assert [s.name for s in reg.by_phase(Phase.EXECUTION)] == names


def test_registry_rejects_duplicate_name():
    reg = Registry()
    reg.register(RecordingStub("x"))
    with pytest.raises(KernelError, match="duplicate"):
        reg.register(RecordingStub("x"))


def test_registry_rejects_non_subsystem():
    with pytest.raises(KernelError):
        Registry().register(object())


def test_registry_by_phase_filters():
    reg = Registry()
    reg.register(RecordingStub("all"))
    reg.register(RecordingStub("oracle", {Phase.ORACLE_UPDATE}))
    assert [s.name for s in reg.by_phase(Phase.ORACLE_UPDATE)] == ["all", "oracle"]
    assert [s.name for s in reg.by_phase(Phase.EXECUTION)] == ["all"]


def test_registry_sources_targets_get_find():
    reg = Registry()
    reg.register(RngStub())
    reg.register(TargetStub("t2"))
    reg.register(SourceStub("s1", target="t2"))
    reg.register(TargetStub("t1"))
    assert [s.name for s in reg.sources()] == ["s1"]
    assert [s.name for s in reg.targets()] == ["t2", "t1"]
    assert reg.get("t1").name == "t1"
    assert "t1" in reg and "nope" not in reg
    assert reg.find(PegView) is None
    with pytest.raises(KernelError, match="nope"):
        reg.get("nope")
