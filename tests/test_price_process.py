import math

import pytest
from kernel_stubs import make_config

from depeg_sim.environment.price_process import ReferencePrice
from depeg_sim.kernel.config import EnvironmentConfig, ShockEvent
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import ActionSource, ActionTarget, PegView, Subsystem
from depeg_sim.kernel.scheduler import Phase


def run(env, *, max_steps=100, seed=42):
    ctx = RunContext.from_config(make_config(max_steps=max_steps, seed=seed))
    ctx.registry.register(env)
    result = Engine(ctx).run()
    return ctx, result


def updates(result):
    return [e for e in result.events if e.kind == "price_updated"]


def prices(result):
    return [e.payload["price"] for e in updates(result)]


# AC 2 ------------------------------------------------------------------------


def test_is_a_subsystem_on_environment_update_only():
    env = ReferencePrice(base_price=1.0, volatility_per_step=0.0)
    assert env.name == "environment"
    assert env.phases == frozenset({Phase.ENVIRONMENT_UPDATE})
    assert isinstance(env, Subsystem)
    assert not isinstance(env, ActionSource)
    assert not isinstance(env, ActionTarget)
    assert not isinstance(env, PegView)


def test_price_before_first_update_is_base():
    env = ReferencePrice(base_price=0.98, volatility_per_step=0.01)
    assert env.price == 0.98
    assert env.prev_price == 0.98


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_price": 0.0, "volatility_per_step": 0.0},
        {"base_price": -1.0, "volatility_per_step": 0.0},
        {"base_price": math.nan, "volatility_per_step": 0.0},
        {"base_price": 1.0, "volatility_per_step": -0.1},
        {"base_price": 1.0, "volatility_per_step": math.inf},
        {"base_price": 1.0, "volatility_per_step": 0.0, "shocks": {-1: 5.0}},
        {"base_price": 1.0, "volatility_per_step": 0.0, "shocks": {3: -100.0}},
        {"base_price": 1.0, "volatility_per_step": 0.0, "shocks": {3: math.nan}},
        {
            "base_price": 1.0,
            "volatility_per_step": 0.0,
            "shocks": [ShockEvent(step=3, pct=-60.0), ShockEvent(step=3, pct=-50.0)],
        },
    ],
)
def test_invalid_construction_raises_value_error(kwargs):
    with pytest.raises(ValueError):
        ReferencePrice(**kwargs)


# AC 3 / 4 --------------------------------------------------------------------


def test_flat_price_and_rng_untouched_over_100_steps():
    env = ReferencePrice(base_price=1.0, volatility_per_step=0.0)
    ctx = RunContext.from_config(make_config(max_steps=100))
    ctx.registry.register(env)
    before = ctx.rng.bit_generator.state
    result = Engine(ctx).run()
    after = ctx.rng.bit_generator.state

    assert result.steps_run == 100
    evs = updates(result)
    assert [e.step for e in evs] == list(range(100))
    assert all(e.source == "environment" for e in evs)
    assert all(
        e.payload == {"step": e.step, "price": 1.0, "prev_price": 1.0, "shock_pct": 0.0}
        for e in evs
    )
    assert before == after


def test_one_normal_draw_per_step_when_volatile():
    env = ReferencePrice(base_price=1.0, volatility_per_step=0.01)
    ctx, result = run(env, max_steps=50, seed=7)
    rng = RunContext.from_config(make_config(seed=7)).rng
    expected, p = [], 1.0
    for _ in range(50):
        p *= math.exp(0.01 * rng.standard_normal())
        expected.append(p)
    assert prices(result) == expected
    assert ctx.rng.bit_generator.state == rng.bit_generator.state


def test_prev_price_chains():
    env = ReferencePrice(base_price=1.0, volatility_per_step=0.01)
    _, result = run(env, max_steps=20)
    evs = updates(result)
    assert evs[0].payload["prev_price"] == 1.0
    for a, b in zip(evs, evs[1:], strict=False):
        assert b.payload["prev_price"] == a.payload["price"]
    assert env.price == evs[-1].payload["price"]
    assert env.prev_price == evs[-1].payload["prev_price"]


def test_shock_at_step_zero_applies_to_first_price():
    env = ReferencePrice(1.0, 0.0, [ShockEvent(step=0, pct=-5.0)])
    _, result = run(env, max_steps=3)
    evs = updates(result)
    assert evs[0].payload == {"step": 0, "price": 0.95, "prev_price": 1.0, "shock_pct": -5.0}
    assert prices(result) == [0.95, 0.95, 0.95]
    assert [e.payload["shock_pct"] for e in evs] == [-5.0, 0.0, 0.0]


def test_shock_at_step_n_applies_at_n_only():
    env = ReferencePrice(1.0, 0.0, [ShockEvent(step=10, pct=2.0)])
    _, result = run(env, max_steps=15)
    ps = prices(result)
    assert ps[:10] == [1.0] * 10
    assert all(math.isclose(p, 1.02, rel_tol=1e-15) for p in ps[10:])
    assert [e.step for e in updates(result) if e.payload["shock_pct"] != 0.0] == [10]


def test_shock_pct_is_percent_not_fraction():
    env = ReferencePrice(2.0, 0.0, {1: 0.5})
    _, result = run(env, max_steps=2)
    assert math.isclose(prices(result)[1], 2.0 * 1.005, rel_tol=1e-15)


def test_two_shocks_same_step_sum():
    env = ReferencePrice(1.0, 0.0, [ShockEvent(step=4, pct=-3.0), ShockEvent(step=4, pct=-2.0)])
    _, result = run(env, max_steps=6)
    evs = updates(result)
    assert evs[4].payload["shock_pct"] == -5.0
    assert math.isclose(evs[4].payload["price"], 0.95, rel_tol=1e-15)
    assert env.step_applied_shocks == [(4, -5.0)]


def test_shock_only_environment_does_not_consume_rng():
    env = ReferencePrice(1.0, 0.0, [ShockEvent(step=3, pct=-10.0)])
    ctx = RunContext.from_config(make_config(max_steps=10))
    ctx.registry.register(env)
    before = ctx.rng.bit_generator.state
    Engine(ctx).run()
    assert ctx.rng.bit_generator.state == before


def test_shock_applies_after_volatility_draw():
    env = ReferencePrice(1.0, 0.01, {0: -5.0})
    _, result = run(env, max_steps=1, seed=3)
    z = RunContext.from_config(make_config(seed=3)).rng.standard_normal()
    assert prices(result)[0] == 1.0 * math.exp(0.01 * z) * (1 + -5.0 / 100)


# AC 5 ------------------------------------------------------------------------


def test_same_seed_same_sequence_different_seed_differs():
    def seq(seed):
        return prices(run(ReferencePrice(1.0, 0.01), max_steps=100, seed=seed)[1])

    a, b, c = seq(1), seq(1), seq(2)
    assert a == b
    assert a != c
    assert len(set(a)) > 1
    assert all(p > 0 for p in a)


# AC 10 / 12 --------------------------------------------------------------------


def test_snapshot_full_state():
    env = ReferencePrice(1.0, 0.0, {2: 1.0})
    assert env.snapshot() == {"price": 1.0, "prev_price": 1.0, "step_applied_shocks": []}
    run(env, max_steps=5)
    snap = env.snapshot()
    assert set(snap) == {"price", "prev_price", "step_applied_shocks"}
    assert snap["price"] == env.price
    assert snap["prev_price"] == env.prev_price
    assert snap["step_applied_shocks"] == [[2, 1.0]]


def test_from_config():
    cfg = EnvironmentConfig(
        base_price=1.01, volatility_per_step=0.002, shocks=[{"step": 5, "pct": -5.0}]
    )
    env = ReferencePrice.from_config(cfg)
    assert env.name == "environment"
    assert env.base_price == 1.01
    assert env.volatility_per_step == 0.002
    assert env.price == 1.01
    _, result = run(ReferencePrice.from_config(EnvironmentConfig(shocks=cfg.shocks)), max_steps=6)
    assert math.isclose(prices(result)[5], 0.95, rel_tol=1e-15)


def test_from_baseline_scenario_config():
    env = ReferencePrice.from_config(make_config().environment)
    assert env.price == 1.0
    assert env.volatility_per_step == 0.0


def test_module_docstring_says_pct_is_percent():
    import depeg_sim.environment.price_process as mod

    assert "**percent**, not a" in mod.__doc__
    assert "``-5.0`` means minus five percent" in mod.__doc__


# Story 2.5: observed series -------------------------------------------------------


def write_series(path, closes, start=1_678_406_400, spacing=3600):
    rows = ["unix,close"] + [f"{start + i * spacing},{c}" for i, c in enumerate(closes)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_series_interpolates_to_steps_and_holds_last(tmp_path):
    closes = [1.0, 0.9, 0.95, 0.97, 0.99]  # hourly: 300 twelve-second steps per candle
    env = ReferencePrice.from_series(write_series(tmp_path / "s.csv", closes), 12)
    assert len(env.series) == 4 * 300 + 1
    _, result = run(env, max_steps=1500)
    p = prices(result)
    assert p[0] == 1.0
    assert math.isclose(p[150], 0.95)  # midpoint of 1.0 and 0.9
    assert math.isclose(p[300], 0.9)
    assert math.isclose(p[450], 0.925)
    assert p[1200] == 0.99 and p[1499] == 0.99  # past the end: last close holds
    assert [e.payload["step"] for e in updates(result)][:3] == [0, 1, 2]


def test_series_draws_nothing_from_the_rng(tmp_path):
    env = ReferencePrice.from_series(write_series(tmp_path / "s.csv", [1.0, 0.9]), 12)
    ctx, _ = run(env, max_steps=50)
    fresh = RunContext.from_config(make_config(max_steps=50, seed=42))
    assert ctx.rng.standard_normal() == fresh.rng.standard_normal()


def test_series_needs_unix_and_close(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("time,price\n1,1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="lacks columns"):
        ReferencePrice.from_series(bad, 12)


def test_from_config_uses_the_series(tmp_path):
    path = write_series(tmp_path / "s.csv", [0.98, 0.99])
    env = ReferencePrice.from_config(EnvironmentConfig(price_series_path=path), 12)
    assert env.series is not None and env.price == 0.98
