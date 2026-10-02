import math

import pytest
from agent_world import decisions, events_of, rules, world

from depeg_sim.agents.attacker import Attacker
from depeg_sim.kernel.config import AttackerConfig


def test_waits_then_sells_at_pace():
    w = world()
    atk = Attacker("atk", capital=1_000.0, start_step=5, pace=0.1)
    sizes = []
    for _ in range(8):
        acts = w.step(atk)
        sizes.append([a.params["amount_in"] for a in acts])
    assert sizes[:5] == [[]] * 5
    assert sizes[5] == [pytest.approx(100.0)]
    assert sizes[6] == [pytest.approx(90.0)]
    assert sizes[7] == [pytest.approx(81.0)]
    assert rules(w, "atk") == ["attack_waiting"] * 5 + ["attack_dump"] * 3
    assert all(a.target == "amm" and a.params["side"] == "sell_stable" for a in w.ctx.action_queue)
    assert atk.balances["stable"] == pytest.approx(1_000.0 * 0.9**3)
    assert atk.sold_total == pytest.approx(271.0)
    executed = events_of(w, "swap_executed")
    assert atk.balances["reference"] == pytest.approx(
        sum(e.payload["amount_out"] for e in executed)
    )
    assert decisions(w, "atk")[5].action == {
        "target": "amm",
        "kind": "swap",
        "params": {"amount_in": pytest.approx(100.0), "side": "sell_stable"},
    }


def test_stops_below_price():
    w = world()
    # 50% of 200k into a 1M pool each step drives spot below 0.9 within a few steps.
    atk = Attacker("atk", capital=400_000.0, start_step=0, pace=0.5, stop_below_price=0.9)
    for _ in range(6):
        w.step(atk)
    r = rules(w, "atk")
    assert "attack_stop_price" in r
    first_stop = r.index("attack_stop_price")
    assert all(x == "attack_dump" for x in r[:first_stop])
    assert all(x == "attack_stop_price" for x in r[first_stop:])
    assert w.amm.spot_price < 0.9
    stopped_obs = decisions(w, "atk")[first_stop].observed
    assert stopped_obs["spot_price"] < 0.9
    assert len(events_of(w, "swap_executed")) == first_stop


def test_stop_price_lifts_when_price_recovers():
    w = world()
    atk = Attacker("atk", capital=1_000.0, start_step=0, pace=0.1, stop_below_price=0.95)
    w.set_spot(0.94)
    w.step(atk)
    w.set_spot(1.0)
    w.step(atk)
    assert rules(w, "atk") == ["attack_stop_price", "attack_dump"]


def test_exhausted_after_selling_everything():
    w = world()
    atk = Attacker("atk", capital=1_000.0, start_step=0, pace=1.0)
    w.step(atk)
    w.step(atk)
    w.step(atk)
    assert rules(w, "atk") == ["attack_dump", "attack_exhausted", "attack_exhausted"]
    assert atk.balances["stable"] == 0.0
    assert len(events_of(w, "swap_executed")) == 1


def test_construction_guards_and_from_config():
    for kw in ({"capital": 0}, {"pace": 0}, {"pace": 1.5}, {"start_step": -1}):
        args = {"agent_id": "a", "capital": 1.0, "start_step": 0, "pace": 0.1} | kw
        with pytest.raises(ValueError):
            Attacker(**args)
    cfg = AttackerConfig(
        type="attacker", id="z", capital=5.0, start_step=3, pace=0.2, stop_below_price=0.97
    )
    a = Attacker.from_config(cfg, peg_price=1.0)
    assert (a.agent_id, a.capital, a.start_step, a.pace, a.stop_below_price) == (
        "z",
        5.0,
        3,
        0.2,
        0.97,
    )
    assert math.isclose(a.initial_value, 5.0)


def test_never_draws_from_rng():
    w = world()
    state = w.ctx.rng.bit_generator.state
    atk = Attacker("atk", capital=1_000.0, start_step=0, pace=0.3)
    for _ in range(5):
        w.step(atk)
    assert w.ctx.rng.bit_generator.state == state
