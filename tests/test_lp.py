"""Story 3.8 AC 2, 3: the flighty liquidity provider, with real modules and manual phases."""

import math
from pathlib import Path

import pydantic
import pytest
from agent_world import config, decisions, events_of, rules, world

from depeg_sim.agents.attacker import Attacker
from depeg_sim.agents.factory import build_agents
from depeg_sim.agents.lp import LiquidityProvider
from depeg_sim.kernel.config import LPConfig, ScenarioConfig, load_scenario

LP = {"type": "lp", "id": "lp-1", "share": 0.5, "panic_threshold_pct": 5.0, "pace": 0.1}


def lp(share=0.5, threshold=5.0, pace=0.1):
    return LiquidityProvider("lp", share=share, panic_threshold_pct=threshold, pace=pace)


# hold / withdraw / done ---------------------------------------------------------------


def test_holds_above_the_threshold():
    w = world(fee_bps=0)
    p = lp()
    w.set_spot(0.96)  # -400 bps, panic below -500
    w.step(p)
    w.set_spot(0.9500001)  # just above -500 bps (0.95 itself is -0.05000000000000004 in floats)
    w.step(p)
    assert rules(w, "lp") == ["lp_hold", "lp_hold"]
    assert w.ctx.execution_results == [] and p.share_remaining == 0.5
    assert w.amm.lp_supply == 1.0


def test_withdraws_at_pace_below_the_threshold():
    w = world(fee_bps=0)
    p = lp()
    w.set_spot(0.9)
    rs0, rr0 = w.amm.reserve_stable, w.amm.reserve_reference
    (act,) = w.step(p)
    assert act.target == "amm" and act.kind == "remove_liquidity"
    assert act.params == {"fraction": pytest.approx(0.05)}
    assert rules(w, "lp") == ["lp_withdraw"]
    assert p.share_remaining == pytest.approx(0.45)
    assert w.amm.reserve_stable == pytest.approx(0.95 * rs0)
    assert p.balances == {
        "stable": pytest.approx(0.05 * rs0),
        "reference": pytest.approx(0.05 * rr0),
    }
    (ev,) = events_of(w, "liquidity_removed")
    assert ev.payload["source"] == "lp"


def test_two_consecutive_withdrawals_pin_the_share_arithmetic():
    # Dev Notes: withdrawing s from a pool in which the LP holds S leaves (S - s)/(1 - s).
    w = world(fee_bps=0)
    p = lp(share=0.5, pace=0.1)
    w.set_spot(0.9)
    rs0 = w.amm.reserve_stable
    (a1,) = w.step(p)
    assert a1.params["fraction"] == pytest.approx(0.05)  # 0.05 shares of a supply of 1
    assert w.amm.lp_supply == pytest.approx(0.95)
    assert p.pool_fraction(w.ctx) == pytest.approx((0.5 - 0.05) / (1 - 0.05))
    (a2,) = w.step(p)
    assert a2.params["fraction"] == pytest.approx(0.045 / 0.95)  # 0.047368...
    assert a2.params["fraction"] == pytest.approx(0.0473684210526, rel=1e-10)
    s1 = 0.45 / 0.95
    assert p.pool_fraction(w.ctx) == pytest.approx(
        (s1 - a2.params["fraction"]) / (1 - a2.params["fraction"])
    )
    assert p.share_remaining == pytest.approx(0.405)
    assert w.amm.lp_supply == pytest.approx(0.905)
    assert p.pool_fraction(w.ctx) == pytest.approx(0.405 / 0.905)
    # with no swaps in between, what it took out is exactly its withdrawn shares of the pool
    assert p.balances["stable"] == pytest.approx((0.5 - 0.405) * rs0, rel=1e-12)


def test_stops_at_zero_share():
    w = world(fee_bps=0)
    p = lp(share=0.5, pace=1.0)
    w.set_spot(0.9)
    w.step(p)
    assert p.share_remaining == 0.0 and w.amm.lp_supply == pytest.approx(0.5)
    w.set_spot(0.8, stable=w.amm.reserve_stable)
    assert w.step(p) == []
    assert rules(w, "lp") == ["lp_withdraw", "lp_done"]


def test_geometric_pace_runs_down_to_done():
    w = world(fee_bps=0)
    p = lp(share=0.5, pace=0.5)
    w.set_spot(0.9)
    for _ in range(40):
        w.step(p)
    rs = rules(w, "lp")
    assert rs[0] == "lp_withdraw" and rs[-1] == "lp_done"
    assert "lp_withdraw" not in rs[rs.index("lp_done") :]
    assert w.amm.lp_supply == pytest.approx(0.5, abs=1e-8)


def test_price_unchanged_and_k_scales_by_a_withdrawal():
    w = world(fee_bps=30)
    p = lp(share=0.5, pace=0.2)
    w.set_spot(0.8)
    spot0, k0 = w.amm.spot_price, w.amm.k
    (act,) = w.step(p)
    f = act.params["fraction"]
    assert f == pytest.approx(0.1)
    assert math.isclose(w.amm.spot_price, spot0, rel_tol=1e-12)
    assert math.isclose(w.amm.k, k0 * (1 - f) ** 2, rel_tol=1e-12)


def test_a_swap_after_a_withdrawal_has_larger_impact():
    def dump(withdraw: bool) -> float:
        w = world(fee_bps=30)
        w.set_spot(0.9)
        if withdraw:
            w.step(lp(share=0.5, pace=1.0))
        atk = Attacker("atk", capital=50_000, start_step=0, pace=1.0)
        w.step(atk)
        return w.amm.spot_price

    assert dump(True) < dump(False) < 0.9


def test_one_way_never_re_adds():
    w = world(fee_bps=0)
    p = lp(share=0.5, pace=0.1)
    w.set_spot(0.9)
    w.step(p)
    w.set_spot(1.0, stable=w.amm.reserve_stable)  # back at par
    for _ in range(3):
        assert w.step(p) == []
    assert rules(w, "lp") == ["lp_withdraw", "lp_hold", "lp_hold", "lp_hold"]
    assert p.share_remaining == pytest.approx(0.45) and w.amm.lp_supply == pytest.approx(0.95)


def test_sole_lp_cannot_drain_the_pool():
    w = world(fee_bps=0)
    p = lp(share=1.0, pace=1.0)
    w.set_spot(0.9)
    w.step(p)
    (ev,) = events_of(w, "liquidity_rejected")
    assert ev.payload["reason"] == "would drain reserves"
    assert p.share_remaining == 1.0 and p.balances == {"stable": 0.0, "reference": 0.0}
    assert w.amm.lp_supply == 1.0


def test_decision_records():
    w = world(fee_bps=0)
    p = lp()
    w.set_spot(0.99)
    w.step(p)
    w.set_spot(0.9)
    w.step(p)
    hold, wd = decisions(w, "lp")
    assert hold.rule == "lp_hold" and hold.action is None
    assert hold.observed["share_remaining"] == 0.5 and hold.observed["pool_fraction"] == 0.5
    assert wd.rule == "lp_withdraw"
    assert wd.action == {
        "target": "amm",
        "kind": "remove_liquidity",
        "params": {"fraction": pytest.approx(0.05)},
    }
    assert wd.observed["peg_deviation"] == pytest.approx(-0.1)


def test_pnl_marks_withdrawn_reserves_and_position_at_spot():
    w = world(fee_bps=0)
    p = lp(share=0.5, pace=0.1)
    w.step(p)  # at par: values the position
    assert p.initial_value == pytest.approx(0.5 * 2_000_000.0)
    assert p.pnl_last == pytest.approx(0.0)
    w.set_spot(0.9)  # by hand: spot 0.9 on 1M stable
    w.step(p)
    # whole pool marked at 0.9: 1M stable x 0.9 + 0.9M reference = 1.8M; it owns half
    assert p.mark_to_market(w.ctx) == pytest.approx(0.5 * 1_800_000.0)
    assert p.pnl_last == pytest.approx(-100_000.0)


def test_never_draws_from_rng():
    w = world(fee_bps=0)
    before = w.ctx.rng.bit_generator.state
    p = lp()
    for price in (1.0, 0.9, 0.8, 0.99):
        w.set_spot(price, stable=w.amm.reserve_stable)
        w.step(p)
    assert w.ctx.rng.bit_generator.state == before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"share": 0},
        {"share": 1.5},
        {"threshold": 0},
        {"pace": 0},
        {"pace": 1.1},
    ],
)
def test_invalid_construction(kwargs):
    with pytest.raises(ValueError):
        lp(**kwargs)


def test_snapshot():
    p = lp()
    snap = p.snapshot()
    assert snap["type"] == "lp"
    assert (snap["share"], snap["share_remaining"], snap["withdrawals"]) == (0.5, 0.5, 0)


# config and factory -------------------------------------------------------------------


def test_config_parses_in_the_union_and_builds():
    data = config().model_dump(mode="json")
    data["agents"].append(dict(LP))
    cfg = ScenarioConfig.model_validate(data)
    assert isinstance(cfg.agents[-1], LPConfig)
    agent = build_agents(cfg)[-1]
    assert isinstance(agent, LiquidityProvider)
    assert (agent.agent_id, agent.share, agent.panic_threshold_pct, agent.pace) == (
        "lp-1",
        0.5,
        5.0,
        0.1,
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"share": 0},
        {"share": 1.01},
        {"panic_threshold_pct": 0},
        {"pace": 0},
        {"pace": 1.5},
        {"extra": 1},
    ],
)
def test_config_bounds(bad):
    with pytest.raises(pydantic.ValidationError):
        LPConfig.model_validate(LP | bad)


# Every scenario's content_hash() as of Story 3.7 (commit 24c2a6e). LPConfig is a new
# union member, so none of them moves.
HASHES_3_7 = {
    "calibrated-baseline": "44ac03c60e5f561cc88e9d2a3e00a11dfccf3893ef95e326c2348195ec1c9d4a",
    "calibrated-baseline-ou": "741f1bdd00120fa73f099669178f9bbc362e64ee762b8185abaf5e1dd058946c",
    "calibrated-stress": "17b24b458e47a6aa483a4883cc384740ea5df25fd31d83fa6c835e5fc672d414",
    "soros-1992-no-defense": "516edaef47958a1c24474d75ff18ef9a56a749570c860efd362564d05bffc02b",
    "soros-1992": "f4e26ae664407d5e53b761d54bfd3b0d29e7b773c8af4a0253753f95cce86270",
    "soros-baseline": "2e09f431ce748e725a3ab84c123711b08b16e276b6af05ee506caa7daac5dd85",
    "soros-volatile": "84ad0b810807e84b0b07faed41aa50c4d2f8821328d0facef15fc1a50976867b",
    "usdc-2023": "2c3aeaa9825d0c04a937ba6b1c97087bc59547b2ccf5e9b344e83b6dc3871531",
    "usdc-2023-tranches": "da3383d4e156754f3f16f95808704acc650afb11c3754dcca321347e004a5868",
}


@pytest.mark.parametrize("name", sorted(HASHES_3_7))
def test_existing_scenario_hashes_unchanged(name):
    h = load_scenario(Path("scenarios") / f"{name}.yaml").content_hash()
    assert h == HASHES_3_7[name]


# the scenario (AC 4) ------------------------------------------------------------------

LP_SCENARIO = Path("scenarios/calibrated-baseline-lp.yaml")


def test_lp_scenario_hash_is_pinned():
    assert load_scenario(LP_SCENARIO).content_hash() == (
        "4707a65abb67784c2b21d5f178cbc207c4db6ca99d487b861bf13ff6e4b3fe16"
    )


def test_lp_scenario_is_ou_plus_one_lp():
    ou = load_scenario(Path("scenarios/calibrated-baseline-ou.yaml")).model_dump(mode="json")
    lp_ = load_scenario(LP_SCENARIO).model_dump(mode="json")
    assert lp_["name"] == "calibrated-baseline-lp"
    *rest, added = lp_["agents"]
    assert added == LP
    for d in (ou, lp_):
        del d["name"]
    lp_["agents"] = rest
    assert lp_ == ou


def test_lp_scenario_header_states_the_assumptions():
    header = LP_SCENARIO.read_text(encoding="utf-8").split("version:")[0]
    assert "ASSUMPTIONS WITH NO PUBLIC ANCHOR" in header and "ADR-0031" in header
    for line in ("share 0.5", "threshold 5%", "pace 0.1", "holder's 2% entry"):
        assert line in header, line
