import math

import pytest
from agent_world import decisions, events_of, rules, world

from depeg_sim.agents.defender import Defender
from depeg_sim.kernel.config import DefenderConfig


def defender(budget=1_000_000.0, pace=0.2, adjust=0, max_spend=None, threshold=1.0):
    return Defender(
        "def",
        budget=budget,
        threshold_pct=threshold,
        spend_pace=pace,
        spread_adjust_bps=adjust,
        max_spend=max_spend,
    )


def test_idle_above_threshold():
    w = world()
    d = defender()
    w.step(d)
    w.set_spot(0.995)  # -0.5%, threshold 1%
    w.step(d)
    assert rules(w, "def") == ["defend_idle", "defend_idle"]
    assert w.ctx.execution_results == []


def test_buys_below_threshold_sized_by_pace():
    w = world()
    d = defender(budget=100_000.0, pace=0.2)
    w.set_spot(0.98)
    gap = math.sqrt(w.amm.k * 1.0) - w.amm.reserve_reference  # ~9_950
    (act,) = w.step(d)
    assert act.params["side"] == "buy_stable"
    assert act.params["amount_in"] == pytest.approx(min(0.2 * 100_000.0, gap))
    assert act.params["amount_in"] == pytest.approx(gap)  # gap is the binding cap here
    assert rules(w, "def") == ["defend_buy"]
    assert d.spent == act.params["amount_in"]
    assert d.interventions == 1
    assert d.balances["reference"] == pytest.approx(100_000.0 - gap)


def test_buy_capped_by_pace():
    w = world()
    d = defender(budget=10_000.0, pace=0.1)
    w.set_spot(0.9)
    (act,) = w.step(d)
    assert act.params["amount_in"] == pytest.approx(1_000.0)


def test_closed_form_restores_peg_with_zero_fee():
    w = world(fee_bps=0)
    d = defender()
    w.set_spot(0.95)
    w.step(d)
    assert abs(w.amm.spot_price / 1.0 - 1) < 1e-9


def test_never_exceeds_max_spend():
    w = world()
    d = defender(budget=1_000_000.0, pace=0.2, max_spend=1_000.0)
    for _ in range(6):
        w.set_spot(0.95)  # keep pushing the pool back down
        w.step(d)
    assert d.spent == pytest.approx(1_000.0)
    assert d.spent <= 1_000.0 + 1e-9
    r = rules(w, "def")
    assert r[0] == "defend_buy"
    assert r[-1] == "defend_budget_exhausted"
    assert sum(1 for x in r if x == "defend_buy") == d.interventions
    spent_from_events = sum(
        e.payload["amount_in"]
        for e in events_of(w, "swap_executed")
        if e.payload["source"] == "def"
    )
    assert d.spent == pytest.approx(spent_from_events)


def test_budget_exhausted_when_reference_gone():
    w = world()
    d = defender(budget=100.0, pace=1.0)
    w.set_spot(0.9)
    w.step(d)
    w.set_spot(0.9)
    w.step(d)
    assert rules(w, "def") == ["defend_buy", "defend_budget_exhausted"]
    assert d.balances["reference"] == 0.0


def test_widens_once_and_restores_once():
    w = world(spread_bps=10)
    d = defender(adjust=50)
    for _ in range(3):
        w.set_spot(0.95)
        w.step(d)
    assert w.redemption.spread_bps == 60
    assert d.spread_widened is True
    w.set_spot(1.0)
    w.step(d)
    w.step(d)
    changes = events_of(w, "spread_changed")
    assert [(e.step, e.payload) for e in changes] == [
        (0, {"old": 10, "new": 60, "source": "def"}),
        (3, {"old": 60, "new": 10, "source": "def"}),
    ]
    assert w.redemption.spread_bps == 10
    assert d.spread_widened is False
    assert rules(w, "def") == [
        "defend_spread_widen",
        "defend_buy",
        "defend_buy",
        "defend_spread_restore",
        "defend_idle",
    ]
    first = decisions(w, "def")[0].action
    assert first["actions"][0] == {
        "target": "redemption",
        "kind": "set_spread_bps",
        "params": {"bps": 60},
    }
    assert first["actions"][1]["params"]["side"] == "buy_stable"
    assert decisions(w, "def")[3].action == {
        "target": "redemption",
        "kind": "set_spread_bps",
        "params": {"bps": 10},
    }
    assert d.interventions == 3


def test_no_spread_call_without_adjust():
    w = world()
    d = defender(adjust=0)
    w.set_spot(0.95)
    w.step(d)
    w.set_spot(1.0)
    w.step(d)
    assert events_of(w, "spread_changed") == []
    assert rules(w, "def") == ["defend_buy", "defend_idle"]


def test_widen_capped_below_10000():
    w = world(spread_bps=9_990)
    d = defender(adjust=50)
    w.set_spot(0.95)
    w.step(d)
    assert w.redemption.spread_bps == 9_999


def test_widen_without_budget_still_records_widen():
    w = world()
    d = defender(adjust=50, max_spend=0.0)
    w.set_spot(0.95)
    assert w.step(d) == []
    assert rules(w, "def") == ["defend_spread_widen"]
    assert decisions(w, "def")[0].action["params"] == {"bps": 60}


def test_construction_guards_and_from_config():
    base = {"agent_id": "a", "budget": 1.0, "threshold_pct": 1.0, "spend_pace": 0.1}
    for kw in (
        {"budget": 0},
        {"threshold_pct": 0},
        {"spend_pace": 0},
        {"spend_pace": 2},
        {"spread_adjust_bps": -1},
        {"max_spend": -1},
    ):
        with pytest.raises(ValueError):
            Defender(**(base | kw))
    cfg = DefenderConfig(
        type="defender",
        id="z",
        budget=9.0,
        threshold_pct=2.0,
        spend_pace=0.5,
        spread_adjust_bps=25,
        max_spend=4.0,
    )
    d = Defender.from_config(cfg)
    assert (d.agent_id, d.budget, d.threshold_pct, d.spend_pace, d.spread_adjust_bps) == (
        "z",
        9.0,
        2.0,
        0.5,
        25,
    )
    assert d.max_spend == 4.0


# -- Story 3.2: buy flag and spread cap --------------------------------------------------


def test_buy_false_never_buys_and_still_widens_and_restores():
    w = world(spread_bps=10)
    d = Defender(
        "def",
        budget=1_000_000.0,
        threshold_pct=1.0,
        spend_pace=0.2,
        spread_adjust_bps=200,
        buy=False,
    )
    for _ in range(3):
        w.set_spot(0.95)
        assert w.step(d) == []
    w.set_spot(1.0)
    w.step(d)
    w.step(d)
    r = rules(w, "def")
    assert r == [
        "defend_spread_widen",
        "defend_idle",
        "defend_idle",
        "defend_spread_restore",
        "defend_idle",
    ]
    assert "defend_buy" not in r and "defend_budget_exhausted" not in r
    assert decisions(w, "def")[0].action == {
        "target": "redemption",
        "kind": "set_spread_bps",
        "params": {"bps": 210},
    }
    assert [e.payload["new"] for e in events_of(w, "spread_changed")] == [210, 10]
    assert (d.spent, d.interventions, d.bought_stable) == (0.0, 0, 0.0)
    assert d.balances["reference"] == 1_000_000.0
    assert all(e.payload["source"] != "def" for e in events_of(w, "swap_executed"))


def test_buy_false_without_spread_is_idle_in_defense():
    w = world()
    d = Defender("def", budget=1.0, threshold_pct=1.0, spend_pace=0.2, buy=False)
    w.set_spot(0.9)
    assert w.step(d) == []
    assert rules(w, "def") == ["defend_idle"]
    assert events_of(w, "spread_changed") == []


def test_max_spread_bps_caps_the_widen():
    w = world(spread_bps=10)
    d = Defender(
        "def",
        budget=1_000.0,
        threshold_pct=1.0,
        spend_pace=0.2,
        spread_adjust_bps=200,
        max_spread_bps=150,
    )
    w.set_spot(0.95)
    w.step(d)
    assert w.redemption.spread_bps == 150


def test_max_spread_bps_below_base_never_lowers_the_spread():
    w = world(spread_bps=100)
    d = Defender(
        "def",
        budget=1_000.0,
        threshold_pct=1.0,
        spend_pace=0.2,
        spread_adjust_bps=200,
        max_spread_bps=50,
    )
    w.set_spot(0.95)
    w.step(d)
    assert w.redemption.spread_bps == 100
    assert events_of(w, "spread_changed") == []
    assert rules(w, "def") == ["defend_buy"]


def test_buy_and_cap_from_config_and_guards():
    cfg = DefenderConfig(
        type="defender",
        id="z",
        budget=9.0,
        threshold_pct=1.0,
        spend_pace=0.2,
        spread_adjust_bps=200,
        buy=False,
        max_spread_bps=300,
    )
    d = Defender.from_config(cfg)
    assert (d.buy, d.max_spread_bps) == (False, 300)
    dflt = Defender.from_config(
        DefenderConfig(type="defender", id="y", budget=9.0, threshold_pct=1.0, spend_pace=0.2)
    )
    assert (dflt.buy, dflt.max_spread_bps) == (True, 9_999)
    base = {"agent_id": "a", "budget": 1.0, "threshold_pct": 1.0, "spend_pace": 0.1}
    for bad in (-1, 10_000):
        with pytest.raises(ValueError):
            Defender(**base, max_spread_bps=bad)
