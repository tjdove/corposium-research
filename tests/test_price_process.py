import math

import numpy as np
import pytest
from kernel_stubs import make_config
from pydantic import ValidationError

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


# Story 3.6: mean-reverting (OU) reference -----------------------------------------------


def test_kappa_zero_is_the_random_walk_exactly():
    walk = ReferencePrice(base_price=1.0, volatility_per_step=0.01)
    ou0 = ReferencePrice(base_price=1.0, volatility_per_step=0.01, mean_reversion_per_step=0.0)
    ca, ra = run(walk, max_steps=200, seed=7)
    cb, rb = run(ou0, max_steps=200, seed=7)
    assert prices(ra) == prices(rb)  # exact float equality, not approx
    assert ca.rng.bit_generator.state == cb.rng.bit_generator.state


def test_ou_update_rule_and_one_draw_per_step():
    kappa, sigma, base = 0.05, 0.01, 1.0
    env = ReferencePrice(base_price=base, volatility_per_step=sigma, mean_reversion_per_step=kappa)
    ctx, result = run(env, max_steps=50, seed=7)
    rng = RunContext.from_config(make_config(seed=7)).rng
    expected, lp = [], math.log(base)
    for _ in range(50):
        lp += kappa * (math.log(base) - lp) + sigma * float(rng.standard_normal())
        expected.append(math.exp(lp))
    assert prices(result) == pytest.approx(expected, rel=1e-15)
    assert ctx.rng.bit_generator.state == rng.bit_generator.state  # one draw per step


def test_ou_without_volatility_draws_nothing_and_decays_a_shock():
    env = ReferencePrice(
        base_price=1.0, volatility_per_step=0.0, shocks={0: -10.0}, mean_reversion_per_step=0.5
    )
    ctx = RunContext.from_config(make_config(max_steps=20))
    ctx.registry.register(env)
    before = ctx.rng.bit_generator.state
    result = Engine(ctx).run()
    assert ctx.rng.bit_generator.state == before
    ps = prices(result)
    assert ps[0] == pytest.approx(0.9)
    # each step halves the log gap to base
    assert math.log(ps[1]) == pytest.approx(0.5 * math.log(0.9))
    assert abs(math.log(ps[-1])) < 1e-5


def test_kappa_one_pins_the_price_to_base():
    # the class accepts kappa = 1 (the config field stops below 1)
    flat = ReferencePrice(base_price=1.02, volatility_per_step=0.0, mean_reversion_per_step=1.0,
                          shocks={3: 5.0})  # fmt: skip
    _, r = run(flat, max_steps=10)
    assert prices(r) == pytest.approx([1.02] * 3 + [1.02 * 1.05] + [1.02] * 6, rel=1e-15)
    noisy = ReferencePrice(base_price=1.02, volatility_per_step=0.01, mean_reversion_per_step=1.0)
    _, r = run(noisy, max_steps=30, seed=3)
    rng = RunContext.from_config(make_config(seed=3)).rng
    assert prices(r) == pytest.approx(
        [1.02 * math.exp(0.01 * float(rng.standard_normal())) for _ in range(30)], rel=1e-14
    )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_ou_recovers_its_ar1_coefficient_and_stationary_sd(seed):
    kappa, sigma = 0.02, 0.001
    env = ReferencePrice(base_price=1.0, volatility_per_step=sigma, mean_reversion_per_step=kappa)
    _, r = run(env, max_steps=40_000, seed=seed)
    x = np.log(np.array(prices(r)))[1_000:]  # drop the burn-in from base
    phi = float(np.dot(x[:-1], x[1:]) / np.dot(x[:-1], x[:-1]))
    assert phi == pytest.approx(1 - kappa, abs=0.004)
    assert float(x.std()) == pytest.approx(sigma / math.sqrt(1 - (1 - kappa) ** 2), rel=0.1)


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
def test_invalid_mean_reversion_raises(bad):
    with pytest.raises(ValueError, match="mean_reversion_per_step"):
        ReferencePrice(base_price=1.0, volatility_per_step=0.0, mean_reversion_per_step=bad)


@pytest.mark.parametrize("bad", [-0.1, 1.0, 2.0])
def test_config_field_is_in_zero_one(bad):
    with pytest.raises(ValidationError, match="mean_reversion_per_step"):
        EnvironmentConfig(mean_reversion_per_step=bad)


def test_series_forbids_mean_reversion(tmp_path):
    path = write_series(tmp_path / "s.csv", [0.98, 0.99])
    with pytest.raises(ValidationError, match="mean_reversion_per_step must be 0"):
        EnvironmentConfig(price_series_path=path, mean_reversion_per_step=0.01)


def test_from_config_passes_kappa():
    env = ReferencePrice.from_config(
        EnvironmentConfig(volatility_per_step=0.001, mean_reversion_per_step=0.01)
    )
    assert env.mean_reversion_per_step == 0.01


def test_kappa_enters_the_hash_only_when_set():
    from depeg_sim.kernel.config import ScenarioConfig, load_scenario

    base = load_scenario("scenarios/calibrated-baseline.yaml")
    assert base.content_hash()[:12] == "44ac03c60e5f"
    data = base.model_dump(mode="json")
    data["environment"]["mean_reversion_per_step"] = 0.0
    assert ScenarioConfig.model_validate(data).content_hash() == base.content_hash()
    data["environment"]["mean_reversion_per_step"] = 0.001
    assert ScenarioConfig.model_validate(data).content_hash() != base.content_hash()


def test_explicit_kappa_zero_run_is_byte_identical(tmp_path):
    from depeg_sim.experiments.runner import run_scenario
    from depeg_sim.kernel.config import ScenarioConfig, load_scenario

    base = load_scenario("scenarios/soros-volatile.yaml")  # draws every step
    data = base.model_dump(mode="json")
    data["environment"]["mean_reversion_per_step"] = 0.0
    a = run_scenario(base, output_dir=tmp_path / "a", chart=False)
    b = run_scenario(ScenarioConfig.model_validate(data), output_dir=tmp_path / "b", chart=False)
    for name in ("timeseries.parquet", "summary.json", "events.jsonl", "decisions.jsonl"):
        assert (a.run_dir / name).read_bytes() == (b.run_dir / name).read_bytes(), name
