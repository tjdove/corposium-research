from kernel_stubs import PegStub, ReservesStub, make_config

from depeg_sim.kernel import termination
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine

ALL_ON = {
    "reserves_exhausted": True,
    "peg_recovered": {"for_steps": 3, "tolerance": 0.001},
    "max_steps": True,
}


def run(*subs, max_steps=100, term=None):
    ctx = RunContext.from_config(make_config(max_steps=max_steps, termination=term or ALL_ON))
    for s in subs:
        ctx.registry.register(s)
    return ctx, Engine(ctx).run()


def test_reserves_exhausted_fires_the_step_flag_is_set():
    ctx, result = run(ReservesStub(exhaust_at_step=7))
    assert result.terminated_by == "reserves_exhausted"
    assert result.steps_run == 8
    assert ctx.clock.step_index == 7


def test_peg_recovered_fires_after_for_steps_and_resets_on_excursion():
    ctx, result = run(PegStub([0, 0, 0.01, 0, 0, 0, 0]))
    assert result.terminated_by == "peg_recovered"
    assert ctx.clock.step_index == 5
    assert result.steps_run == 6


def test_peg_recovered_counter_resets_and_increments():
    ctx = RunContext.from_config(make_config(max_steps=100, termination=ALL_ON))
    peg = PegStub([0.0005, 0.002, -0.0009, 0.001])
    ctx.registry.register(peg)
    counts = []
    for step in range(4):
        peg._step = step
        ctx.clock.step_index = step
        assert termination.check(ctx) is None
        counts.append(ctx.term_state.consecutive_in_band)
    # in band, excursion, in band (negative side), boundary == tolerance counts as in band
    assert counts == [1, 0, 1, 2]


def test_peg_recovered_never_fires_while_out_of_band():
    _, result = run(PegStub([0.01]), max_steps=50)
    assert result.terminated_by == "max_steps"
    assert result.steps_run == 50


def test_max_steps_fires_at_exactly_max_steps():
    ctx, result = run(max_steps=10)
    assert result.terminated_by == "max_steps"
    assert result.steps_run == 10
    assert ctx.clock.step_index == 9


def test_reserves_beats_max_steps_same_step():
    _, result = run(ReservesStub(exhaust_at_step=9), max_steps=10)
    assert result.terminated_by == "reserves_exhausted"
    assert result.steps_run == 10


def test_reserves_beats_peg_same_step():
    # peg in band from step 0, for_steps 3 -> fires at step 2; reserves also at step 2
    _, result = run(ReservesStub(exhaust_at_step=2), PegStub([0.0]))
    assert result.terminated_by == "reserves_exhausted"
    assert result.steps_run == 3


def test_peg_beats_max_steps_same_step():
    _, result = run(PegStub([0.0]), max_steps=3)
    assert result.terminated_by == "peg_recovered"
    assert result.steps_run == 3


def test_missing_views_are_skipped():
    _, result = run(max_steps=5)
    assert result.terminated_by == "max_steps"
    assert result.steps_run == 5


def test_disabled_conditions_do_not_fire_even_with_views():
    term = {"reserves_exhausted": False, "peg_recovered": None, "max_steps": True}
    _, result = run(ReservesStub(exhaust_at_step=0), PegStub([0.0]), max_steps=4, term=term)
    assert result.terminated_by == "max_steps"
    assert result.steps_run == 4


def test_max_steps_caps_run_while_other_condition_pending():
    # max_steps is mandatory (story 1.4): it stops the run even though
    # reserves_exhausted is enabled and would only fire later.
    term = {"reserves_exhausted": True, "peg_recovered": None, "max_steps": True}
    _, result = run(ReservesStub(exhaust_at_step=20), max_steps=5, term=term)
    assert result.terminated_by == "max_steps"
    assert result.steps_run == 5
