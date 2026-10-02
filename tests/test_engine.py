import pytest
from kernel_stubs import (
    QueueObserverStub,
    RecordingStub,
    RngStub,
    SourceStub,
    TargetStub,
    make_config,
)

from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine, RunResult
from depeg_sim.kernel.events import Event
from depeg_sim.kernel.interfaces import Action, ExecutionResult, KernelError
from depeg_sim.kernel.scheduler import PHASE_ORDER_VERSION, PHASES, Phase


def make_ctx(*subs, max_steps=3, **kw):
    ctx = RunContext.from_config(make_config(max_steps=max_steps), **kw)
    for s in subs:
        ctx.registry.register(s)
    return ctx


# AC 12 -----------------------------------------------------------------------


def test_all_phase_stub_sees_phases_in_order_every_step():
    rec = RecordingStub("rec")
    Engine(make_ctx(rec, max_steps=4)).run()
    assert rec.calls == [(step, p) for step in range(4) for p in PHASES]


def test_subset_stub_sees_only_its_phases():
    sub = RecordingStub("sub", {Phase.PERSISTENCE, Phase.ORACLE_UPDATE})
    Engine(make_ctx(sub, max_steps=3)).run()
    expected = [(s, p) for s in range(3) for p in (Phase.ORACLE_UPDATE, Phase.PERSISTENCE)]
    assert sub.calls == expected


def test_dispatch_within_phase_follows_registration_order():
    order = []

    class Tagged(RecordingStub):
        def on_phase(self, ctx, phase):
            order.append((phase, self.name))

    Engine(make_ctx(Tagged("b"), Tagged("a"), max_steps=1)).run()
    assert order == [(p, n) for p in PHASES for n in ("b", "a")]


# AC 6 ------------------------------------------------------------------------


def test_actions_routed_to_target_in_queue_order():
    src1 = SourceStub("s1", target="t")
    src2 = SourceStub("s2", target="t")
    tgt = TargetStub("t")
    Engine(make_ctx(src1, tgt, src2, max_steps=3)).run()
    assert [(a.source, a.params["n"]) for a in tgt.received] == [
        ("s1", 0),
        ("s2", 0),
        ("s1", 1),
        ("s2", 1),
        ("s1", 2),
        ("s2", 2),
    ]
    assert tgt.received[0] == Action(source="s1", target="t", kind="ping", params={"n": 0})


def test_execution_results_recorded_in_queue_order_and_cleared_each_step():
    class ResultTarget(TargetStub):
        def execute(self, ctx, action):
            super().execute(ctx, action)
            return ExecutionResult(ok=True, detail={"src": action.source, "n": action.params["n"]})

    seen = []

    class ResultObserver(RecordingStub):
        def on_phase(self, ctx, phase):
            seen.append((ctx.clock.step_index, phase, list(ctx.execution_results)))

    rob = ResultObserver("rob", {Phase.AGENT_DECISION, Phase.PROTOCOL_EVENTS})
    ctx = make_ctx(
        SourceStub("s1", target="t"),
        ResultTarget("t"),
        SourceStub("s2", target="t"),
        rob,
        max_steps=3,
    )
    Engine(ctx).run()
    for step in range(3):
        at = {phase: res for s, phase, res in seen if s == step}
        assert at[Phase.AGENT_DECISION] == []  # cleared before decide hooks
        got = at[Phase.PROTOCOL_EVENTS]
        assert [(a.source, a.params["n"]) for a, _ in got] == [("s1", step), ("s2", step)]
        assert [r.detail for _, r in got] == [{"src": "s1", "n": step}, {"src": "s2", "n": step}]
        assert all(r.ok for _, r in got)
    assert len(ctx.execution_results) == 2  # last step's results remain after the run


def test_actions_route_by_target_name():
    t1, t2 = TargetStub("t1"), TargetStub("t2")
    Engine(make_ctx(SourceStub("a", target="t2"), t1, t2, max_steps=2)).run()
    assert t1.received == []
    assert len(t2.received) == 2


def test_queue_holds_only_current_step_actions():
    obs = QueueObserverStub(
        {Phase.AGENT_DECISION, Phase.ACTION_QUEUE, Phase.EXECUTION, Phase.PERSISTENCE}
    )
    Engine(make_ctx(SourceStub(), TargetStub(), obs, max_steps=3)).run()
    for step in range(3):
        seen = {phase: n for s, phase, n in obs.seen if s == step}
        # cleared before AGENT_DECISION hooks; one action queued after decide()
        assert seen == {
            Phase.AGENT_DECISION: 0,
            Phase.ACTION_QUEUE: 1,
            Phase.EXECUTION: 1,
            Phase.PERSISTENCE: 1,
        }


def test_on_phase_runs_before_kernel_phase_action():
    """Documented ordering subtlety: hooks run before decide/execute in the same phase."""
    src = SourceStub("src", target="tgt", phases={Phase.AGENT_DECISION})
    tgt = TargetStub("tgt", phases={Phase.EXECUTION})
    Engine(make_ctx(src, tgt, max_steps=2)).run()
    assert src.log == [("on_phase", 0), ("decide", 0), ("on_phase", 1), ("decide", 1)]
    assert tgt.log == [("on_phase", 0), ("execute", 0), ("on_phase", 1), ("execute", 1)]


def test_unknown_target_raises_kernel_error_with_action_and_step():
    ctx = make_ctx(SourceStub("src", target="ghost"), max_steps=3)
    with pytest.raises(KernelError) as exc:
        Engine(ctx).run()
    msg = str(exc.value)
    assert "step 0" in msg
    assert "'ghost'" in msg
    assert "Action(" in msg


def test_target_that_is_not_action_target_raises():
    ctx = make_ctx(SourceStub("src", target="rec"), RecordingStub("rec"), max_steps=3)
    with pytest.raises(KernelError, match="not an ActionTarget"):
        Engine(ctx).run()


# AC 9 ------------------------------------------------------------------------


def test_run_result_fields(tmp_path):
    ctx = RunContext.from_config(make_config(max_steps=4, checkpoint_every=2), output_dir=tmp_path)
    ctx.registry.register(RngStub())

    class Decider(RecordingStub):
        def on_phase(self, ctx, phase):
            ctx.decisions.record(ctx.clock.step_index, self.name, "always", {}, None)

    ctx.registry.register(Decider("d", {Phase.AGENT_DECISION}))
    result = Engine(ctx).run()
    assert isinstance(result, RunResult)
    assert result.steps_run == 4
    assert result.terminated_by == "max_steps"
    assert [d.step for d in result.decisions] == [0, 1, 2, 3]
    assert [p.name for p in result.checkpoints] == ["step-000002.json", "step-000004.json"]
    kinds = [e.kind for e in result.events]
    assert kinds == ["run_started"] + ["draw"] * 4 + ["run_terminated"]


def test_kernel_events():
    cfg = make_config(max_steps=3)
    result = Engine(RunContext.from_config(cfg)).run()
    assert result.events == [
        Event(
            step=0,
            kind="run_started",
            source="kernel",
            payload={
                "seed": 42,
                "scenario_hash": cfg.content_hash(),
                "phase_order_version": PHASE_ORDER_VERSION,
            },
        ),
        Event(
            step=2,
            kind="run_terminated",
            source="kernel",
            payload={"reason": "max_steps", "steps_run": 3},
        ),
    ]


# AC 10 -----------------------------------------------------------------------


def _deterministic_run(out, seed_override=None):
    ctx = RunContext.from_config(
        make_config(max_steps=25, checkpoint_every=10),
        seed_override=seed_override,
        output_dir=out,
    )
    ctx.registry.register(RngStub("rng-a"))
    ctx.registry.register(RngStub("rng-b"))
    return Engine(ctx).run()


def test_determinism_identical_events_and_checkpoint_bytes(tmp_path):
    a = _deterministic_run(tmp_path / "a")
    b = _deterministic_run(tmp_path / "b")
    assert a.events == b.events
    assert len(a.events) == 2 + 2 * 25
    assert len(a.checkpoints) == 3
    assert [p.read_bytes() for p in a.checkpoints] == [p.read_bytes() for p in b.checkpoints]


def test_different_seed_changes_draws(tmp_path):
    a = _deterministic_run(tmp_path / "a")
    b = _deterministic_run(tmp_path / "b", seed_override=43)
    draws = lambda r: [e.payload["x"] for e in r.events if e.kind == "draw"]  # noqa: E731
    assert draws(a) != draws(b)
