"""Story 2.6 AC 1, 3: the holder (par-expecting buyer), with real modules and manual phases."""

import pytest
from agent_world import config, decisions, events_of, rules, world

from depeg_sim.agents.arbitrageur import _reference_to_reach
from depeg_sim.agents.base import DUST
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
    w.set_spot(0.95)  # the fill cap to 0.98 is ~14.9k here, so pace (5k) binds
    (act,) = w.step(h)
    assert act.target == "amm" and act.params == {"amount_in": 5_000.0, "side": "buy_stable"}
    assert rules(w, "h") == ["hold_buy"]
    assert h.balances["reference"] == pytest.approx(95_000.0)
    assert h.balances["stable"] > 5_000.0  # bought below par
    assert h.bought_stable == h.balances["stable"] and h.spent_reference == 5_000.0
    w.set_spot(0.95)  # push spot back below the entry price
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
    h = holder(stable=500.0)
    assert w.redemption.queue_depth == 1
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_wait"]


def test_small_balance_redeems_all_when_queue_empty():
    w = world(capacity=100.0)
    h = holder(stable=600.0)  # tranche cap 100 x 10 = 1000 > 600
    (act,) = w.step(h)
    assert act.target == "redemption" and act.kind == "redeem"
    assert act.params == {"amount_stable": 600.0}
    assert rules(w, "h") == ["hold_redeem"]
    assert decisions(w, "h")[0].observed["capacity_per_step"] == 100.0


def test_large_holder_redeems_one_tranche_per_clear_step():
    w = world(capacity=100.0)
    h = holder(stable=1_000_000.0)  # far more than the channel pays in 10 steps
    (act,) = w.step(h)
    assert act.params == {"amount_stable": 1_000.0}  # capacity x redeem_horizon_steps
    # 100 paid this step, 900 of its own tranche still queued: it waits while it drains
    assert h.queued_redeem == pytest.approx(900.0)
    assert h.balances["stable"] == pytest.approx(1_000_000.0 - 100.0)
    for _ in range(9):
        assert w.step(h) == []
    assert w.redemption.queue_depth == 0 and h.queued_redeem == pytest.approx(0.0)
    (act2,) = w.step(h)  # queue clear again: the next tranche
    assert act2.params == {"amount_stable": 1_000.0}
    assert rules(w, "h") == ["hold_redeem"] + ["hold_wait"] * 9 + ["hold_redeem"]
    assert h.balances["stable"] == pytest.approx(1_000_000.0 - 1_100.0)


def test_tranche_follows_current_capacity():
    w = world(capacity=100.0)
    h = holder(stable=1_000_000.0)
    w.redemption.capacity_per_step = 5_000.0  # e.g. a capacity_schedule step
    (act,) = w.step(h)
    assert act.params == {"amount_stable": 50_000.0}


def test_redeem_when_capacity_false_never_redeems():
    w = world()
    h = holder(stable=1_000.0, redeem=False)
    w.step(h)
    assert rules(w, "h") == ["hold_wait"]


def test_redeem_horizon_steps_is_a_constructor_default():
    w = world(capacity=100.0)
    h = Holder("h", capital=1.0, entry_discount_pct=2.0, pace=0.05, redeem_horizon_steps=3)
    h.balances["stable"] = 1_000.0
    (act,) = w.step(h)
    assert act.params == {"amount_stable": 300.0}


# full cycle ----------------------------------------------------------------------------


def test_full_cycle_buy_then_redeem_at_par_is_profitable_and_ends_done():
    w = world(capacity=1_000_000.0, spread_bps=10)  # ppu 0.999
    h = holder(capital=10_000.0, pace=1.0)
    w.set_spot(0.95)  # cap ~14.9k > 10k
    w.step(h)  # buys with everything
    assert h.balances["reference"] == 0.0 and h.balances["stable"] > 10_000.0
    w.set_spot(0.99)  # the market recovers above the entry price
    w.step(h)  # no reference left: redeem
    w.step(h)  # nothing left; proceeds are reference but spot is above the entry
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
        {"redeem_horizon_steps": 0},
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
    assert (h.redeem_when_capacity, h.redeem_horizon_steps) == (False, 10)
    assert h.peg_price == 2.0 and h.entry_price == pytest.approx(2.0 * 0.97)
    assert h.balances == {"stable": 0.0, "reference": 7.0} and h.initial_value == 7.0
    cfg = HolderConfig(type="holder", id="z", capital=1, entry_discount_pct=0, pace=1)
    assert Holder.from_config(cfg).redeem_when_capacity is True


def test_snapshot_counters():
    w = world()
    h = holder()
    w.set_spot(0.95)
    w.step(h)
    snap = h.snapshot()
    assert snap["type"] == "holder"
    assert snap["spent_reference"] == 5_000.0 and snap["bought_stable"] > 5_000.0


def _redeem(source, amount):
    return Action(
        source=source, target="redemption", kind="redeem", params={"amount_stable": amount}
    )


# Story 3.1: fill-price limit ----------------------------------------------------------


def test_buy_that_would_overshoot_is_capped_at_the_entry_price():
    w = world(fee_bps=1)
    h = holder(capital=1_000_000.0, pace=0.5)  # pace term 500k, far past the entry price
    w.set_spot(0.95)
    cap = _reference_to_reach(w.amm.k, w.amm.reserve_reference, h.entry_price)
    (act,) = w.step(h)
    assert act.params["amount_in"] == cap  # the arbitrageur's helper, reused unchanged
    assert cap < 0.5 * 1_000_000.0
    spot = w.amm.spot_price
    assert spot <= h.entry_price + 1e-9
    # the helper ignores the 1 bp fee, so spot lands a hair below: < 0.1 bps
    assert (h.entry_price - spot) / h.entry_price < 0.1 / 10_000
    assert rules(w, "h") == ["hold_buy"]


def test_buy_that_would_not_overshoot_is_uncapped():
    w = world(fee_bps=1)
    h = holder(capital=100_000.0, pace=0.05)
    w.set_spot(0.95)
    cap = _reference_to_reach(w.amm.k, w.amm.reserve_reference, h.entry_price)
    (act,) = w.step(h)
    assert cap > 5_000.0 and act.params["amount_in"] == 5_000.0
    assert w.amm.spot_price < h.entry_price


def test_dust_buy_falls_through_to_redeem():
    # smaller term (pace x a dust reference) <= DUST: no buy; the redeem rule applies
    w = world()
    h = holder(stable=1_000.0)
    h.balances["reference"] = 1e-9
    w.set_spot(0.95)
    (act,) = w.step(h)
    assert act.kind == "redeem" and rules(w, "h") == ["hold_redeem"]


def test_dust_cap_falls_through_to_done():
    # spot a hair below the entry price: the cap term is <= DUST; nothing held: hold_done
    w = world()
    h = holder()
    w.set_spot(h.entry_price * (1 - 1e-15))
    assert w.amm.spot_price < h.entry_price
    assert _reference_to_reach(w.amm.k, w.amm.reserve_reference, h.entry_price) <= DUST
    assert w.step(h) == []
    assert rules(w, "h") == ["hold_done"]


class _UncappedHolder(Holder):
    """The pre-3.1 rule (ADR-0021): ``pace x reference`` whenever spot < entry price."""

    def _buy_amount(self, ctx):
        amm = self._amm(ctx)
        if amm is None or not amm.spot_price < self.entry_price:
            return 0.0
        return self.pace * self.balances["reference"]


def _two_steps(h):
    """Holder buy, attacker dump of 60k stable, holder buy; spot after each holder step."""
    w = world(fee_bps=1)
    w.set_spot(0.975)
    w.step(h)
    after_first = w.amm.spot_price
    w.amm.swap(60_000.0, "sell_stable")  # the attacker's dump between holder buys
    w.step(h)
    return after_first, w.amm.spot_price


@pytest.mark.parametrize(
    "cls, above_par",
    [(_UncappedHolder, True), (Holder, False)],
    ids=["old-rule-overshoots", "capped"],
)
def test_two_step_sawtooth(cls, above_par):
    # replay ratio: holder capital 0.55 x pool depth, pace 0.05 (a 27.5k buy into 1M)
    h = cls("h", capital=550_000.0, entry_discount_pct=2.0, pace=0.05)
    first, second = _two_steps(h)
    assert (max(first, second) > 1.0) is above_par
    if not above_par:
        assert first <= h.entry_price + 1e-9 and second <= h.entry_price + 1e-9
