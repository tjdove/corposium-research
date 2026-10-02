"""RedemptionModule registered in a real Engine. No ReservesStub: the
reserves_exhausted termination reads the module through registry.find(ReservesView)."""

import math

from kernel_stubs import SourceStub, make_config

from depeg_sim.kernel import termination
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import Action, ReservesView
from depeg_sim.protocol.redemption import RedemptionModule

RESERVES = 500_000.0  # reference
SPREAD_BPS = 10
CAPACITY = 25_000.0  # stable per step
REQUEST = 30_000.0  # stable per step
MAX_STEPS = 100
TERMINATION = {"reserves_exhausted": True, "peg_recovered": None, "max_steps": True}


def build(*, termination=TERMINATION, request=REQUEST):
    cfg = make_config(max_steps=MAX_STEPS, termination=termination)
    ctx = RunContext.from_config(cfg)
    red = RedemptionModule(reserves=RESERVES, spread_bps=SPREAD_BPS, capacity_per_step=CAPACITY)
    ctx.registry.register(red)
    if request is not None:
        ctx.registry.register(
            SourceStub(
                name="redeemer",
                target="redemption",
                kind="redeem",
                params={"amount_stable": request},
            )
        )
    return ctx, red


def kinds(result, kind):
    return [e for e in result.events if e.kind == kind]


def expected_exhaustion_step():
    # Payout per stable unit: ppu = 1.0 * (1 - 10 / 10_000) = 0.999 reference.
    ppu = 1.0 * (1 - SPREAD_BPS / 10_000)
    # Stable the reserves can buy back in total: 500_000 / 0.999 = 500_500.5005...
    affordable = RESERVES / ppu
    # Requests (30_000/step) exceed capacity (25_000/step), so every step fills exactly
    # the capacity and the backlog grows 5_000/step: the queue is never empty.
    assert REQUEST > CAPACITY
    # Full-capacity steps 0..19 redeem 20 * 25_000 = 500_000 stable; step 20 fills the
    # last 500.5 and the reserves are gone with demand still queued.
    # 500_500.5 / 25_000 = 20.02 -> ceil = 21 steps touch reserves, the last is index 20.
    return math.ceil(affordable / CAPACITY) - 1


def test_exhaustion_terminates_the_run():
    ctx, red = build()
    result = Engine(ctx).run()
    exhaust_step = expected_exhaustion_step()

    assert result.terminated_by == "reserves_exhausted"
    assert result.steps_run == exhaust_step + 1
    assert result.steps_run < MAX_STEPS

    (ex,) = kinds(result, "reserves_exhausted")
    assert ex.step == exhaust_step
    assert ex.source == "redemption"
    assert red.reserves_exhausted is True
    assert red.reserves == 0.0

    (term,) = kinds(result, "run_terminated")
    assert term.step == exhaust_step
    assert term.payload == {"reason": "reserves_exhausted", "steps_run": result.steps_run}

    requested = kinds(result, "redeem_requested")
    assert len(requested) == result.steps_run
    fills = kinds(result, "redeem_fulfilled")
    per_step = {}
    for e in fills:
        per_step[e.step] = per_step.get(e.step, 0.0) + e.payload["amount_stable"]
    assert all(math.isclose(per_step[s], CAPACITY) for s in range(exhaust_step))
    assert fills[-1].step == exhaust_step
    assert fills[-1].payload["reason"] == "partial_reserves"
    assert math.isclose(per_step[exhaust_step], RESERVES / 0.999 - exhaust_step * CAPACITY)

    assert math.isclose(red.paid_total, RESERVES, rel_tol=1e-12)
    assert math.isclose(red.fulfilled_total, RESERVES / 0.999, rel_tol=1e-12)
    assert math.isclose(
        red.fulfilled_total + red.queued_total, result.steps_run * REQUEST, rel_tol=1e-12
    )


def test_repeat_run_is_identical():
    r1 = Engine(build()[0]).run()
    r2 = Engine(build()[0]).run()
    assert r1.events == r2.events
    assert r1.decisions == r2.decisions
    assert (r1.steps_run, r1.terminated_by) == (r2.steps_run, r2.terminated_by)


def redeem(amount):
    return Action(source="x", target="redemption", kind="redeem", params={"amount_stable": amount})


def test_module_is_the_reserves_view_and_termination_reads_it():
    ctx = RunContext.from_config(make_config(max_steps=MAX_STEPS, termination=TERMINATION))
    red = RedemptionModule(reserves=99.9, spread_bps=SPREAD_BPS, capacity_per_step=CAPACITY)
    ctx.registry.register(red)
    assert ctx.registry.find(ReservesView) is red
    assert termination.check(ctx) is None

    # 100 stable * 0.999 = 99.9 reference: reserves spent, queue empty -> not exhaustion.
    red.execute(ctx, redeem(100.0))
    red.process(ctx)
    assert red.reserves == 0.0
    assert red.queue_depth == 0
    assert termination.check(ctx) is None

    # Demand against empty reserves -> exhaustion, and termination sees it.
    red.execute(ctx, redeem(1.0))
    red.process(ctx)
    assert red.reserves_exhausted is True
    assert termination.check(ctx) == "reserves_exhausted"


def test_flag_ignored_when_termination_disabled():
    off = {"reserves_exhausted": False, "peg_recovered": None, "max_steps": True}
    ctx, red = build(termination=off)
    result = Engine(ctx).run()
    assert result.terminated_by == "max_steps"
    assert result.steps_run == MAX_STEPS
    assert red.reserves_exhausted is True
    assert len(kinds(result, "reserves_exhausted")) == 1
    assert kinds(result, "reserves_exhausted")[0].step == expected_exhaustion_step()
