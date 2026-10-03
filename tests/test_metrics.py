import math

import pandas as pd
import pytest
from agent_world import config

from depeg_sim.analysis.metrics import COLUMNS, MetricsCollector
from depeg_sim.experiments.runner import build_world
from depeg_sim.kernel.config import ScenarioConfig
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.scheduler import Phase

EXPECTED = [
    "step",
    "elapsed_seconds",
    "reference_price",
    "oracle_price",
    "amm_price",
    "peg_deviation",
    "amm_reserve_stable",
    "amm_reserve_reference",
    "redemption_reserves",
    "redemption_queue_depth",
    "redemption_queued_total",
    "attacker_stable",
    "attacker_reference",
    "attacker_pnl",
    "arbitrageur_pnl",
    "defender_reference",
    "defender_spent",
    "defender_pnl",
]


def run(cfg: ScenarioConfig):
    ctx = RunContext.from_config(cfg)
    world = build_world(cfg, ctx)
    result = Engine(ctx).run()
    return ctx, world, result, world["metrics"].to_dataframe()


def cfg_with(*, max_steps=200, record_every=1, agents=None, recovery=True) -> ScenarioConfig:
    data = config(max_steps=max_steps).model_dump(mode="json")
    if not recovery:  # retuned baseline ends peg_recovered at step 192
        data["termination"]["peg_recovered"] = None
    data["metrics"]["record_every"] = record_every
    if agents is not None:
        data["agents"] = agents
    return ScenarioConfig.model_validate(data)


def test_columns_exact():
    assert list(COLUMNS) == EXPECTED
    _, _, _, df = run(cfg_with(max_steps=60))
    assert list(df.columns) == EXPECTED
    assert len(df) == 60
    assert df["step"].tolist() == list(range(60))
    assert df["elapsed_seconds"].tolist() == [12 * s for s in range(60)]
    assert df["step"].dtype == "int64"
    assert all(df[c].dtype == "float64" for c in EXPECTED[2:])


def test_record_every_5():
    _, _, result, df = run(cfg_with(max_steps=200, record_every=5, recovery=False))
    assert result.steps_run == 200
    assert len(df) == 40
    assert df["step"].tolist() == list(range(0, 200, 5))


def test_values_match_modules_and_settled_balances():
    ctx, world, _, df = run(cfg_with(max_steps=60))
    last = df.iloc[-1]
    amm, red = world["amm"], world["redemption"]
    atk, arb, dfn = world["attacker-1"], world["arb-1"], world["defender-1"]
    assert last["amm_price"] == amm.spot_price
    assert last["peg_deviation"] == amm.peg_deviation
    assert last["amm_reserve_stable"] == amm.reserve_stable
    assert last["redemption_reserves"] == red.reserves
    assert last["redemption_queue_depth"] == red.queue_depth
    assert last["reference_price"] == world["environment"].price
    assert last["oracle_price"] == world["oracle"].price
    # METRIC_UPDATE after the agents' settle: the row holds settled balances.
    assert last["attacker_stable"] == atk.balances["stable"]
    assert last["attacker_reference"] == atk.balances["reference"]
    assert last["attacker_pnl"] == atk.pnl_last
    assert last["arbitrageur_pnl"] == arb.pnl_last
    assert last["defender_reference"] == dfn.balances["reference"]
    assert last["defender_spent"] == dfn.spent
    assert last["defender_pnl"] == dfn.pnl_last
    # Attack starts at step 50: the step-50 row already shows the sale.
    assert df.loc[49, "attacker_stable"] == 300_000.0
    assert df.loc[50, "attacker_stable"] == pytest.approx(270_000.0)


def test_agent_columns_nan_when_absent():
    agents = [{"type": "attacker", "id": "a", "capital": 1_000, "start_step": 0, "pace": 0.1}]
    _, _, _, df = run(cfg_with(max_steps=10, agents=agents))
    for col in ("arbitrageur_pnl", "defender_reference", "defender_spent", "defender_pnl"):
        assert df[col].isna().all()
    assert df["attacker_stable"].notna().all()


def test_collector_is_last_and_read_only():
    ctx = RunContext.from_config(cfg_with(max_steps=5))
    world = build_world(ctx.config, ctx)
    m = world["metrics"]
    assert ctx.registry.all()[-1] is m
    assert m.phases == frozenset({Phase.METRIC_UPDATE})
    n_events = len(ctx.events)
    m.on_phase(ctx, Phase.METRIC_UPDATE)
    assert len(ctx.events) == n_events
    assert m.snapshot() == {"rows": 1}


def test_missing_modules_give_nan():
    ctx = RunContext.from_config(cfg_with(max_steps=5))
    row = MetricsCollector().collect(ctx)
    assert list(row) == EXPECTED
    assert all(math.isnan(row[c]) for c in EXPECTED[2:])


def test_empty_dataframe_has_columns():
    df = MetricsCollector().to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == EXPECTED and df.empty


@pytest.mark.parametrize("bad", [0, -1, 1.5, True])
def test_record_every_guard(bad):
    with pytest.raises(ValueError):
        MetricsCollector(record_every=bad)
