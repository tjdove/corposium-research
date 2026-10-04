"""Story 2.6 AC 1, 3: the holder (par-expecting buyer), with real modules and manual phases."""

import pytest
from agent_world import config, decisions, events_of, rules, world

from depeg_sim.agents.factory import build_agents
from depeg_sim.agents.holder import Holder
from depeg_sim.kernel.config import HolderConfig, ScenarioConfig
from depeg_sim.kernel.interfaces import Action

RULES = {"hold_buy", "hold_redeem", "hold_wait", "hold_done"}


def holder(capital=100_000.0, discount=2.0, pace=0.05, redeem=True, stable=0.0):
    h = Holder(
        "h", capital=capital, entry_discount_pct=discount, pace=pace, redeem_when_capacity=redeem
    )
    h.balances["stable"] = stable
    return h


# buy rule ------------------------------------------------------------------------------


def test_waits_above_the_discount():
    w = world()
    h = holder()
    w.set_spot(0.99)  # -100 bps, entry is 0.98
    w.step(h)
    w.set_spot(0.98)  # at the entry price: strictly below is required
    w.step(h)
    assert rules(w, "h") == ["hold_done", "hold_done"]
    assert w.ctx.execution_results == []


def test_buys_below_the_discount_at_pace():
    w = world()
    h = holder()
    w.set_spot(0.97)
    (act,) = w.step(h)
    assert act.target == "amm" and act.params == {"amount_in": 5_000.0, "side": "buy_stable"}
    assert rules(w, "h") == ["hold_buy"]
    assert h.balances["reference"] == pytest.approx(95_000.0)
    assert h.balances["stable"] > 5_000.0  # bought below par
    assert h.bought_stable == h.balances["stable"] and h.spent_reference == 5_000.0
    w.set_spot(0.97)  # its own buy lifted spot to the entry price; push it back below
    (act2,) = w.step(h)  # pace applies to the remaining balance
    assert act2.params["amount_in"] == pytest.approx(0.05 * 95_000.0)


def test_buy_takes_priority_over_redeem():
    w = world()
    h = holder(stable=1_000.0)
    w.set_spot(0.97)
    (act,) = w.step(h)
    assert act.kind == "swap" and rules(w, "h") == ["hold_buy"]


def test_no_buy_without_reference():
    w = world()
    h = holder(capital=1.0, stable=1_000_000.0, redeem=False)
    h.balances["reference"] = 0.0
    w.set_spot(0.9)
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_wait"]


def test_never_sells_on_the_amm():
    w = world()
    h = holder(stable=10_000.0, redeem=False)
    w.set_spot(1.05)
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_wait"]


# redeem rule ---------------------------------------------------------------------------


def test_waits_while_the_queue_is_not_empty():
    w = world(capacity=100.0)
    w.redemption.execute(w.ctx, _redeem("other", 1_000.0))  # someone else is queued
    h = holder(stable=500.0)  # capacity 100 >= 0.1 x 500
    assert w.redemption.queue_depth == 1
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_wait"]


def test_waits_while_capacity_is_short():
    w = world(capacity=99.0)
    h = holder(stable=1_000.0)  # needs capacity >= 100
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_wait"]
    assert decisions(w, "h")[0].observed["capacity_per_step"] == 99.0


def test_redeems_all_when_queue_empty_and_capacity_suffices():
    w = world(capacity=100.0)
    h = holder(stable=1_000.0)
    (act,) = w.step(h)
    assert act.target == "redemption" and act.kind == "redeem"
    assert act.params == {"amount_stable": 1_000.0}
    assert rules(w, "h") == ["hold_redeem"]
    # 100 paid this step, 900 still queued and still owned
    assert h.queued_redeem == pytest.approx(900.0)
    assert h.balances["stable"] == pytest.approx(900.0)
    # its own request is now the queue: it waits, it does not redeem twice
    assert w.step(h) == []
    assert rules(w, "h")[-1] == "hold_wait"


def test_redeem_when_capacity_false_never_redeems():
    w = world()
    h = holder(stable=1_000.0, redeem=False)
    w.step(h)
    assert rules(w, "h") == ["hold_wait"]


def test_redeem_fraction_min_is_a_constructor_default():
    w = world(capacity=100.0)
    h = Holder("h", capital=1.0, entry_discount_pct=2.0, pace=0.05, redeem_fraction_min=0.5)
    h.balances["stable"] = 1_000.0  # needs capacity >= 500
    w.step(h)
    assert rules(w, "h") == ["hold_wait"]


# full cycle ----------------------------------------------------------------------------


def test_full_cycle_buy_then_redeem_at_par_is_profitable_and_ends_done():
    w = world(capacity=1_000_000.0, spread_bps=10)  # ppu 0.999
    h = holder(capital=10_000.0, pace=1.0)
    w.set_spot(0.97)
    w.step(h)  # buys with everything
    assert h.balances["reference"] == 0.0 and h.balances["stable"] > 10_000.0
    w.step(h)  # spot still 0.97, no reference: redeem
    w.step(h)  # nothing left
    assert rules(w, "h") == ["hold_buy", "hold_redeem", "hold_done"]
    (fill,) = events_of(w, "redeem_fulfilled")
    assert fill.payload["source"] == "h" and fill.payload["reason"] == "full"
    assert h.balances["stable"] == 0.0 and h.queued_redeem == 0.0
    assert h.balances["reference"] == pytest.approx(h.bought_stable * 0.999)
    assert h.pnl(w.ctx) > 0 and h.pnl_last == pytest.approx(h.pnl(w.ctx))


def test_one_decision_per_step_with_known_rules():
    w = world(capacity=200.0)
    h = holder(capital=10_000.0, pace=0.5)
    prices = [1.0, 0.97, 0.97, 0.99, 0.99, 0.99, 1.0]
    for p in prices:
        w.set_spot(p)
        w.step(h)
    ds = decisions(w, "h")
    assert [d.step for d in ds] == list(range(len(prices)))
    assert set(rules(w, "h")) <= RULES
    assert rules(w, "h")[:3] == ["hold_done", "hold_buy", "hold_buy"]


def test_no_trace_records_nothing():
    w = world(trace=False)
    w.set_spot(0.97)
    w.step(holder())
    assert decisions(w) == []


def test_never_draws_from_rng():
    w = world()
    before = w.ctx.rng.bit_generator.state
    h = holder(stable=100.0)
    for p in (0.97, 0.99, 1.0):
        w.set_spot(p)
        w.step(h)
    assert w.ctx.rng.bit_generator.state == before


# construction and factory --------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        {"capital": 0},
        {"entry_discount_pct": -1},
        {"entry_discount_pct": 100},
        {"pace": 0},
        {"pace": 1.5},
        {"redeem_fraction_min": 0},
    ],
)
def test_construction_guards(kw):
    args = {"agent_id": "h", "capital": 1.0, "entry_discount_pct": 2.0, "pace": 0.1} | kw
    with pytest.raises(ValueError):
        Holder(**args)


def test_from_config_and_factory():
    data = config().model_dump(mode="json")
    data["redemption"]["peg_price"] = 2.0
    data["agents"].append(
        {
            "type": "holder",
            "id": "h",
            "capital": 7.0,
            "entry_discount_pct": 3.0,
            "pace": 0.2,
            "redeem_when_capacity": False,
        }
    )
    *_, h = build_agents(ScenarioConfig.model_validate(data))
    assert isinstance(h, Holder) and h.name == "h"
    assert (h.capital, h.entry_discount_pct, h.pace) == (7.0, 3.0, 0.2)
    assert (h.redeem_when_capacity, h.redeem_fraction_min) == (False, 0.1)
    assert h.peg_price == 2.0 and h.entry_price == pytest.approx(2.0 * 0.97)
    assert h.balances == {"stable": 0.0, "reference": 7.0} and h.initial_value == 7.0
    cfg = HolderConfig(type="holder", id="z", capital=1, entry_discount_pct=0, pace=1)
    assert Holder.from_config(cfg).redeem_when_capacity is True


def test_snapshot_counters():
    w = world()
    h = holder()
    w.set_spot(0.97)
    w.step(h)
    snap = h.snapshot()
    assert snap["type"] == "holder"
    assert snap["spent_reference"] == 5_000.0 and snap["bought_stable"] > 5_000.0


def _redeem(source, amount):
    return Action(
        source=source, target="redemption", kind="redeem", params={"amount_stable": amount}
    )
