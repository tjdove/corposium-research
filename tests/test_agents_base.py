import math

import pytest
from agent_world import config, decisions, world

from depeg_sim.agents.arbitrageur import Arbitrageur
from depeg_sim.agents.attacker import Attacker
from depeg_sim.agents.base import Agent
from depeg_sim.agents.defender import Defender
from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.interfaces import (
    Action,
    ActionSource,
    ActionTarget,
    ExecutionResult,
    PegView,
    ReservesView,
    Subsystem,
)
from depeg_sim.kernel.scheduler import Phase

BASE_KEYS = {"agent_id", "type", "balances", "initial_value", "pnl_last"}


def agents():
    return [
        Attacker("atk", capital=1_000.0, start_step=0, pace=0.5),
        Arbitrageur("arb", capital=2_000.0, min_profit_bps=20),
        Defender("def", budget=3_000.0, threshold_pct=1.0, spend_pace=0.2),
    ]


class Idle(Agent):
    type = "idle"

    def decide(self, ctx):
        self.record(ctx, "idle", self.last_obs, None)
        return []


# AC 2: contract ------------------------------------------------------------------


def test_agents_are_action_sources_with_three_phases():
    for a in agents():
        assert isinstance(a, Subsystem)
        assert isinstance(a, ActionSource)
        assert not isinstance(a, ActionTarget)
        assert not isinstance(a, ReservesView)
        assert not isinstance(a, PegView)
        assert a.name == a.agent_id
        assert a.phases == frozenset(
            {Phase.STATE_OBSERVATION, Phase.AGENT_DECISION, Phase.METRIC_UPDATE}
        )


def test_initial_balances_and_value():
    atk, arb, dfn = agents()
    assert atk.balances == {"stable": 1_000.0, "reference": 0.0}
    assert arb.balances == {"stable": 0.0, "reference": 2_000.0}
    assert dfn.balances == {"stable": 0.0, "reference": 3_000.0}
    assert [a.initial_value for a in (atk, arb, dfn)] == [1_000.0, 2_000.0, 3_000.0]
    assert Attacker("a", 1_000.0, 0, 0.5, peg_price=2.0).initial_value == 2_000.0


def test_abstract_agent_cannot_be_built():
    with pytest.raises(TypeError):
        Agent("x", 0.0, 0.0)


def test_on_phase_dispatch():
    w = world()
    a = Idle("idle", stable=10.0, reference=5.0)
    a.on_phase(w.ctx, Phase.STATE_OBSERVATION)
    assert a.last_obs["spot_price"] == 1.0
    a.on_phase(w.ctx, Phase.AGENT_DECISION)  # no-op: kernel calls decide
    assert len(w.ctx.decisions) == 0


def test_observe_contents():
    w = world()
    w.step()  # oracle publishes 1.0
    w.set_spot(0.98)
    a = Idle("idle", stable=10.0, reference=5.0)
    obs = a.observe(w.ctx)
    assert obs["spot_price"] == pytest.approx(0.98)
    assert obs["oracle_price"] == 1.0
    assert obs["peg_deviation"] == pytest.approx(-0.02)
    assert obs["balances"] == {"stable": 10.0, "reference": 5.0}
    assert obs["step"] == 1
    obs["balances"]["stable"] = 0  # a copy
    assert a.balances["stable"] == 10.0


def test_observe_tolerates_missing_modules():
    ctx = RunContext.from_config(config())
    obs = Idle("idle", 0.0, 1.0).observe(ctx)
    assert obs["spot_price"] is None and obs["oracle_price"] is None


# settle with scripted execution_results ------------------------------------------------


def swap_result(source, side, amount_in, amount_out, ok=True):
    action = Action(source, "amm", "swap", {"amount_in": amount_in, "side": side})
    detail = {"side": side, "amount_in": amount_in, "amount_out": amount_out} if ok else {}
    return action, ExecutionResult(ok=ok, detail=detail)


def test_settle_applies_own_ok_swaps_only():
    w = world()
    a = Idle("me", stable=1_000.0, reference=500.0)
    w.ctx.execution_results.extend(
        [
            swap_result("me", "sell_stable", 100.0, 98.0),
            swap_result("other", "sell_stable", 50.0, 49.0),
            swap_result("me", "buy_stable", 200.0, 199.0),
            swap_result("me", "sell_stable", 7.0, 0.0, ok=False),
        ]
    )
    a.settle(w.ctx)
    assert a.balances == {"stable": 1_000.0 - 100.0 + 199.0, "reference": 500.0 + 98.0 - 200.0}


def test_settle_applies_own_redeem_fills_at_this_step_only():
    w = world()
    a = Idle("me", stable=1_000.0, reference=0.0)
    ev = w.ctx.events
    ev.emit(
        0,
        "redeem_fulfilled",
        "redemption",
        {"source": "me", "amount_stable": 1.0, "paid_reference": 1.0},
    )
    w.ctx.clock.tick()
    w.ctx.execution_results.append(
        (
            Action("me", "redemption", "redeem", {"amount_stable": 300.0}),
            ExecutionResult(ok=True, detail={"queued": 300.0, "queue_depth": 1}),
        )
    )
    ev.emit(
        1,
        "redeem_fulfilled",
        "redemption",
        {"source": "other", "amount_stable": 5.0, "paid_reference": 4.0},
    )
    ev.emit(
        1,
        "redeem_fulfilled",
        "redemption",
        {"source": "me", "amount_stable": 200.0, "paid_reference": 199.8},
    )
    a.settle(w.ctx)
    assert a.balances == {"stable": 800.0, "reference": 199.8}
    assert a.queued_redeem == pytest.approx(100.0)
    assert a.available_stable == pytest.approx(700.0)


def test_mark_to_market_and_pnl():
    w = world()
    w.set_spot(0.9)
    a = Idle("me", stable=1_000.0, reference=500.0)
    assert a.mark_to_market(w.ctx) == pytest.approx(500.0 + 900.0)
    assert a.pnl(w.ctx) == pytest.approx(1_400.0 - 1_500.0)
    a.settle(w.ctx)
    assert a.pnl_last == pytest.approx(-100.0)


# AC 9: trace gating and shape ---------------------------------------------------------


@pytest.mark.parametrize("trace", [True, False])
def test_one_decision_per_agent_per_step_or_none(trace):
    w = world(trace=trace)
    ags = agents()
    for _ in range(10):
        w.step(*ags)
    ds = decisions(w)
    if not trace:
        assert ds == []
        return
    assert len(ds) == 10 * 3
    for step in range(10):
        assert sorted(d.agent_id for d in ds if d.step == step) == ["arb", "atk", "def"]
    for d in ds:
        for key in ("spot_price", "oracle_price", "peg_deviation", "balances"):
            assert key in d.observed
        assert set(d.observed["balances"]) == {"stable", "reference"}


def test_record_list_action_is_wrapped():
    w = world()
    a = Idle("me", 0.0, 1.0)
    a.record(w.ctx, "r", {"x": 1}, [{"a": 1}, {"b": 2}])
    a.record(w.ctx, "r", {"x": 1}, {"a": 1})
    a.record(w.ctx, "r", {"x": 1}, None)
    assert [d.action for d in decisions(w)] == [{"actions": [{"a": 1}, {"b": 2}]}, {"a": 1}, None]


# AC 11: snapshots ------------------------------------------------------------------


def test_snapshot_keys_per_type():
    atk, arb, dfn = agents()
    assert set(atk.snapshot()) == BASE_KEYS | {"sold_total"}
    assert set(arb.snapshot()) == BASE_KEYS | {"pending_plans"}
    assert set(dfn.snapshot()) == BASE_KEYS | {"spent", "interventions", "spread_widened"}
    s = atk.snapshot()
    assert s["type"] == "attacker" and s["agent_id"] == "atk"
    assert arb.snapshot()["type"] == "arbitrageur"
    assert dfn.snapshot()["type"] == "defender"
    s["balances"]["stable"] = 0  # a copy
    assert atk.balances["stable"] == 1_000.0


def test_snapshot_after_steps_reflects_settlement():
    w = world()
    atk = Attacker("atk", capital=1_000.0, start_step=0, pace=0.5)
    w.step(atk)
    s = atk.snapshot()
    assert s["sold_total"] == 500.0
    assert s["balances"]["stable"] == 500.0
    assert math.isclose(s["pnl_last"], atk.pnl(w.ctx))
    assert s["pnl_last"] < 0
