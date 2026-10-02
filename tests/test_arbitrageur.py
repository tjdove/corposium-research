import math

import pytest
from agent_world import decisions, events_of, rules, world

from depeg_sim.agents.arbitrageur import (
    Arbitrageur,
    _reference_to_reach,
    _stable_to_reach,
)
from depeg_sim.kernel.config import ArbitrageurConfig
from depeg_sim.protocol.amm import ConstantProductAMM

BIG = 10_000_000.0


def arb(capital=BIG, min_profit_bps=20, latency=0, stable=0.0):
    a = Arbitrageur("arb", capital=capital, min_profit_bps=min_profit_bps, latency_steps=latency)
    a.balances["stable"] = stable
    return a


# band ----------------------------------------------------------------------------


def test_idle_at_parity_and_inside_band():
    w = world()
    a = arb()
    w.step(a)  # spot == oracle
    w.set_spot(0.996)  # -40 bps; band is fee 30 + min 20 = 50 bps
    w.step(a)
    w.set_spot(1.004)  # +40 bps, and no stable to sell anyway
    w.step(a)
    assert rules(w, "arb") == ["arb_idle"] * 3
    assert w.ctx.execution_results == []
    assert a.pending == []


def test_band_uses_amm_fee_not_a_constant():
    # fee 100 + min 20 = 120 bps band: a -100 bps gap is inside it.
    w = world(fee_bps=100)
    a = arb()
    w.set_spot(0.99)
    w.step(a)
    assert rules(w, "arb") == ["arb_idle"]
    assert decisions(w, "arb")[0].observed["fee_bps"] == 100
    # Same gap with fee 30 is outside the 50 bps band.
    w2 = world(fee_bps=30)
    w2.set_spot(0.99)
    w2.step(arb())
    assert rules(w2, "arb") == ["arb_buy_amm"]


def test_buys_below_band_with_closed_form_size():
    w = world()
    a = arb()
    w.set_spot(0.98)
    k, r = w.amm.k, w.amm.reserve_reference
    (act,) = w.step(a)
    assert act.target == "amm" and act.params["side"] == "buy_stable"
    assert act.params["amount_in"] == pytest.approx(math.sqrt(k * 1.0) - r, rel=1e-12)
    assert rules(w, "arb") == ["arb_buy_amm"]
    # fee 30: undershoots the target slightly, within 0.5%, on the correct side.
    assert w.amm.spot_price < 1.0
    assert w.amm.spot_price == pytest.approx(1.0, rel=5e-3)


def test_buy_capped_by_capital():
    w = world()
    a = arb(capital=1_000.0)
    w.set_spot(0.98)
    (act,) = w.step(a)
    assert act.params["amount_in"] == 1_000.0
    assert a.balances["reference"] == 0.0
    assert a.balances["stable"] > 1_000.0  # bought below peg


def test_sells_above_band_with_closed_form_size():
    w = world()
    a = arb(stable=BIG)
    w.set_spot(1.02)
    k, s = w.amm.k, w.amm.reserve_stable
    (act,) = w.step(a)
    assert act.params["side"] == "sell_stable"
    assert act.params["amount_in"] == pytest.approx(math.sqrt(k / 1.0) - s, rel=1e-12)
    assert rules(w, "arb") == ["arb_sell_amm"]
    assert w.amm.spot_price > 1.0
    assert w.amm.spot_price == pytest.approx(1.0, rel=5e-3)


def test_no_sell_without_stable():
    w = world()
    a = arb()
    w.set_spot(1.02)
    assert w.step(a) == []
    assert rules(w, "arb") == ["arb_idle"]


# AC 8: sizing precision, fee 0 ---------------------------------------------------------


@pytest.mark.parametrize("start, target", [(0.95, 1.0), (0.8, 1.05), (1.0, 1.3)])
def test_reference_to_reach_exact_with_zero_fee(start, target):
    amm = ConstantProductAMM(1_000_000.0, 1_000_000.0 * start, fee_bps=0)
    x = _reference_to_reach(amm.k, amm.reserve_reference, target)
    amm.swap(x, "buy_stable")
    assert abs(amm.spot_price / target - 1) < 1e-9


@pytest.mark.parametrize("start, target", [(1.05, 1.0), (1.3, 0.9), (1.0, 0.7)])
def test_stable_to_reach_exact_with_zero_fee(start, target):
    amm = ConstantProductAMM(1_000_000.0, 1_000_000.0 * start, fee_bps=0)
    y = _stable_to_reach(amm.k, amm.reserve_stable, target)
    amm.swap(y, "sell_stable")
    assert abs(amm.spot_price / target - 1) < 1e-9


def test_sizing_clamped_at_zero():
    assert _reference_to_reach(100.0, 20.0, 1.0) == 0.0  # spot 4 already above 1
    assert _stable_to_reach(100.0, 20.0, 1.0) == 0.0  # spot 0.25 already below 1


def test_agent_trade_restores_oracle_price_with_zero_fee():
    w = world(fee_bps=0)
    w.set_spot(0.97)
    w.step(arb())
    assert abs(w.amm.spot_price / 1.0 - 1) < 1e-9


# latency ---------------------------------------------------------------------------


def test_latency_two_plan_at_step_3_executes_at_step_5():
    w = world()
    a = arb(latency=2)
    for _ in range(3):
        w.step(a)  # steps 0-2 at parity
    w.set_spot(0.98)
    acts = [w.step(a) for _ in range(3)]  # steps 3, 4, 5; nothing else moves the pool
    assert acts[0] == [] and acts[1] == []
    assert len(acts[2]) == 1 and acts[2][0].params["side"] == "buy_stable"
    assert rules(w, "arb") == ["arb_idle"] * 3 + [
        "arb_waiting_latency",
        "arb_waiting_latency",
        "arb_buy_amm",
    ]
    assert decisions(w, "arb")[3].observed["pending_plans"] == [
        {"kind": "buy_amm", "step": 3, "amount": pytest.approx(acts[2][0].params["amount_in"])}
    ]
    assert a.pending == []


def test_plan_dropped_when_opportunity_vanishes_before_latency():
    w = world()
    a = arb(latency=2)
    w.set_spot(0.98)
    w.step(a)
    w.set_spot(1.0)
    w.step(a)
    w.step(a)
    assert rules(w, "arb") == ["arb_waiting_latency", "arb_idle", "arb_idle"]
    assert w.ctx.execution_results == []


def test_plan_refresh_keeps_first_seen_step_and_latest_size():
    w = world()
    a = arb(latency=1)
    w.set_spot(0.98)
    w.step(a)  # step 0: plan seen
    w.set_spot(0.97)
    k, r = w.amm.k, w.amm.reserve_reference
    (act,) = w.step(a)  # step 1: 0 + 1 <= 1, executes the refreshed size
    assert act.params["amount_in"] == pytest.approx(math.sqrt(k) - r, rel=1e-12)


# redeem route --------------------------------------------------------------------------


def test_prefers_redeem_when_payout_beats_spot():
    w = world()
    a = arb(stable=1_000.0)
    w.set_spot(0.98)  # ppu 0.999 > 0.98
    (act,) = w.step(a)
    assert act.target == "redemption" and act.kind == "redeem"
    assert act.params == {"amount_stable": 1_000.0}
    assert rules(w, "arb") == ["arb_redeem"]
    # filled in PROTOCOL_EVENTS the same step and settled in METRIC_UPDATE
    (fill,) = events_of(w, "redeem_fulfilled")
    assert a.balances["stable"] == 0.0
    assert a.balances["reference"] == pytest.approx(BIG + fill.payload["paid_reference"])
    assert fill.payload["paid_reference"] == pytest.approx(999.0)
    # The buy opportunity is still there and executes next step (one action per step).
    (act2,) = w.step(a)
    assert act2.params["side"] == "buy_stable"


def test_redeem_preferred_over_selling_above_payout_only_when_payout_higher():
    w = world()
    a = arb(stable=1_000.0)
    w.set_spot(0.9995)  # inside the band, but ppu 0.999 < spot: no redeem
    assert w.step(a) == []


def test_queued_stable_is_not_redeemed_twice():
    w = world(capacity=100.0)
    a = arb(stable=1_000.0, capital=1.0)
    w.set_spot(0.98)
    w.step(a)  # step 0: redeems all 1000; 100 filled this step, 900 queued
    assert a.queued_redeem == pytest.approx(900.0)
    assert a.available_stable == 0.0
    w.step(a)  # step 1: nothing free to redeem; recycles proceeds into an AMM buy
    w.step(a)  # step 2: redeems only the stable bought at step 1
    requested = [x.payload["amount_stable"] for x in events_of(w, "redeem_requested")]
    assert requested == [1_000.0, pytest.approx(_bought(w))]
    assert rules(w, "arb") == ["arb_redeem", "arb_buy_amm", "arb_redeem"]
    assert a.balances["stable"] == pytest.approx(1_000.0 - 300.0 + _bought(w))
    assert a.queued_redeem == pytest.approx(a.balances["stable"])


def _bought(w):
    return sum(
        e.payload["amount_out"]
        for e in events_of(w, "swap_executed")
        if e.payload["source"] == "arb" and e.payload["side"] == "buy_stable"
    )


# misc ----------------------------------------------------------------------------------


def test_construction_guards_and_from_config():
    for kw in ({"capital": 0}, {"min_profit_bps": -1}, {"latency_steps": -1}):
        args = {"agent_id": "a", "capital": 1.0, "min_profit_bps": 0} | kw
        with pytest.raises(ValueError):
            Arbitrageur(**args)
    cfg = ArbitrageurConfig(
        type="arbitrageur", id="z", capital=7.0, min_profit_bps=15, latency_steps=4
    )
    a = Arbitrageur.from_config(cfg)
    assert (a.agent_id, a.capital, a.min_profit_bps, a.latency_steps) == ("z", 7.0, 15, 4)


def test_snapshot_pending_plans():
    w = world()
    a = arb(latency=5)
    w.set_spot(0.98)
    w.step(a)
    (plan,) = a.snapshot()["pending_plans"]
    assert plan["kind"] == "buy_amm" and plan["step"] == 0 and plan["amount"] > 0
