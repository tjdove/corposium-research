"""AMM registered in a real Engine. No PegStub: peg_recovered reads the AMM's
peg_deviation through registry.find(PegView)."""

import math

from kernel_stubs import SourceStub, make_config

from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import PegView
from depeg_sim.protocol.amm import ConstantProductAMM

PEG_BAND = {"for_steps": 5, "tolerance": 0.001}


def build(*, max_steps, termination=None, swap=None, seed=42):
    cfg = make_config(max_steps=max_steps, termination=termination, seed=seed)
    ctx = RunContext.from_config(cfg)
    amm = ConstantProductAMM.from_config(cfg.amm, peg_price=cfg.redemption.peg_price)
    ctx.registry.register(amm)
    if swap is not None:
        ctx.registry.register(SourceStub(name="seller", target="amm", kind="swap", params=swap))
    return ctx, amm


def kinds(result, kind):
    return [e for e in result.events if e.kind == kind]


def test_one_swap_per_step_moves_reserves():
    ctx, amm = build(max_steps=20, swap={"amount_in": 100.0, "side": "sell_stable"})
    k0 = amm.k
    result = Engine(ctx).run()

    assert result.terminated_by == "max_steps"
    assert result.steps_run == 20
    executed = kinds(result, "swap_executed")
    assert len(executed) == 20
    assert [e.step for e in executed] == list(range(20))
    assert all(e.source == "amm" and e.payload["source"] == "seller" for e in executed)
    assert kinds(result, "swap_rejected") == []

    assert amm.reserve_stable == 1_000_000 + 20 * 100.0
    assert amm.reserve_reference < 1_000_000
    assert math.isclose(
        amm.reserve_reference,
        1_000_000 - sum(e.payload["amount_out"] for e in executed),
        rel_tol=1e-12,
    )
    assert amm.k > k0
    assert amm.peg_deviation < 0
    assert math.isclose(amm.cumulative_fees, 20 * 0.3, rel_tol=1e-9)


def test_amm_is_the_peg_view():
    ctx, amm = build(max_steps=1)
    assert ctx.registry.find(PegView) is amm


def test_selling_every_step_keeps_peg_recovered_from_firing():
    term = {"reserves_exhausted": False, "peg_recovered": PEG_BAND, "max_steps": True}
    ctx, amm = build(
        max_steps=20, termination=term, swap={"amount_in": 10_000.0, "side": "sell_stable"}
    )
    result = Engine(ctx).run()

    assert result.terminated_by == "max_steps"
    assert result.steps_run == 20
    assert len(kinds(result, "swap_executed")) == 20
    assert amm.peg_deviation < -PEG_BAND["tolerance"]
    assert ctx.term_state.consecutive_in_band == 0


def test_no_trades_peg_recovered_fires_at_for_steps():
    term = {"reserves_exhausted": False, "peg_recovered": PEG_BAND, "max_steps": True}
    ctx, amm = build(max_steps=20, termination=term)
    result = Engine(ctx).run()

    assert result.terminated_by == "peg_recovered"
    assert result.steps_run == PEG_BAND["for_steps"]
    assert amm.peg_deviation == 0.0
    assert kinds(result, "swap_executed") == []


def test_rejected_swaps_do_not_stop_the_run():
    ctx, amm = build(max_steps=5, swap={"amount_in": -1.0, "side": "sell_stable"})
    before = amm.snapshot()
    result = Engine(ctx).run()

    assert result.terminated_by == "max_steps"
    assert len(kinds(result, "swap_rejected")) == 5
    assert kinds(result, "swap_executed") == []
    assert amm.snapshot() == before


def test_same_seed_same_events():
    swap = {"amount_in": 250.0, "side": "buy_stable"}
    r1 = Engine(build(max_steps=15, swap=swap)[0]).run()
    r2 = Engine(build(max_steps=15, swap=swap)[0]).run()
    assert r1.events == r2.events
