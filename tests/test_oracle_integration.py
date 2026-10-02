"""ReferencePrice + Oracle + AMM in a real Engine, registered in the 1.8 order:
environment, oracle, amm."""

from kernel_stubs import make_config

from depeg_sim.environment.price_process import ReferencePrice
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import PegView
from depeg_sim.protocol.amm import ConstantProductAMM
from depeg_sim.protocol.oracle import Oracle


def build(seed=42):
    cfg = make_config(max_steps=100, seed=seed)
    ctx = RunContext.from_config(cfg)
    env = ReferencePrice(base_price=1.0, volatility_per_step=0.001)
    oracle = Oracle(heartbeat_steps=10, deviation_threshold_pct=1.0, source=env)
    amm = ConstantProductAMM.from_config(cfg.amm, peg_price=cfg.redemption.peg_price)
    for sub in (env, oracle, amm):
        ctx.registry.register(sub)
    return ctx, env, oracle, amm


def kinds(result, kind):
    return [e for e in result.events if e.kind == kind]


def test_oracle_tracks_reference_price_through_engine():
    ctx, env, oracle, amm = build()
    assert [s.name for s in ctx.registry.all()] == ["environment", "oracle", "amm"]
    result = Engine(ctx).run()

    assert result.terminated_by == "max_steps"
    assert result.steps_run == 100

    price_by_step = {e.step: e.payload["price"] for e in kinds(result, "price_updated")}
    assert sorted(price_by_step) == list(range(100))

    ups = kinds(result, "oracle_updated")
    assert 10 <= len(ups) <= 100
    assert all(e.payload["price"] == price_by_step[e.step] for e in ups)
    assert ups[0].step == 0 and ups[0].payload["reason"] == "initial"
    gaps = [b.step - a.step for a, b in zip(ups, ups[1:], strict=False)]
    assert max(gaps) <= 10

    assert oracle.price == price_by_step[oracle.last_update_step]
    assert oracle.reference_price == env.price == price_by_step[99]
    assert ctx.registry.find(PegView) is amm


def test_repeat_run_is_identical():
    r1 = Engine(build()[0]).run()
    r2 = Engine(build()[0]).run()
    assert r1.events == r2.events
    assert r1.decisions == r2.decisions


def test_different_seed_changes_prices():
    r1 = Engine(build(seed=42)[0]).run()
    r2 = Engine(build(seed=43)[0]).run()
    p1 = [e.payload["price"] for e in kinds(r1, "price_updated")]
    p2 = [e.payload["price"] for e in kinds(r2, "price_updated")]
    assert p1 != p2
