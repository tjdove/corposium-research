import math

import pytest
from kernel_stubs import make_config

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
from depeg_sim.protocol.amm import (
    AMMError,
    ConstantProductAMM,
    Quote,
    SwapResult,
)

QUOTE_FIELDS = {
    "side",
    "amount_in",
    "amount_out",
    "execution_price",
    "spot_before",
    "spot_after",
    "slippage",
    "fee_paid",
}


def pool(fee_bps=30, rs=1_000_000.0, rr=1_000_000.0, peg_price=1.0):
    return ConstantProductAMM(
        reserve_stable=rs, reserve_reference=rr, fee_bps=fee_bps, peg_price=peg_price
    )


def ctx(seed=42):
    return RunContext.from_config(make_config(seed=seed))


def swap_action(amount_in, side="sell_stable", kind="swap", source="trader"):
    return Action(
        source=source, target="amm", kind=kind, params={"amount_in": amount_in, "side": side}
    )


def events_of(c, kind):
    return [e for e in c.events.all() if e.kind == kind]


# AC 9: hand-computed case -----------------------------------------------------


def test_hand_computed_sell_stable():
    amm = pool()
    r = amm.swap(1_000, "sell_stable")
    # net_in = 997; out = 1_000_000 * 997 / 1_000_997
    assert math.isclose(r.amount_out, 996.006981, rel_tol=1e-9)
    assert math.isclose(r.amount_out, 1_000_000 * 997 / 1_000_997, rel_tol=1e-12)
    assert math.isclose(r.fee_paid, 3.0, rel_tol=1e-9)
    assert r.spot_after < r.spot_before
    assert r.spot_before == 1.0
    assert math.isclose(r.execution_price, r.amount_out / 1_000, rel_tol=1e-12)
    assert math.isclose(
        r.slippage, (r.execution_price - r.spot_before) / r.spot_before, rel_tol=1e-12
    )
    assert math.isclose(r.slippage, -0.003993019, rel_tol=1e-6)
    assert r.reserve_stable_after == 1_001_000.0
    assert math.isclose(r.reserve_reference_after, 1_000_000 - r.amount_out, rel_tol=1e-12)


# AC 3 / AC 4: quote is pure, swap mutates ------------------------------------


def test_quote_does_not_change_state():
    amm = pool()
    before = amm.snapshot()
    q = amm.quote(1_000, "sell_stable")
    assert amm.snapshot() == before
    assert isinstance(q, Quote) and not isinstance(q, SwapResult)
    assert set(q.__dataclass_fields__) == QUOTE_FIELDS


def test_quote_matches_swap():
    amm = pool()
    q = amm.quote(5_000, "buy_stable")
    r = amm.swap(5_000, "buy_stable")
    for f in QUOTE_FIELDS:
        assert getattr(q, f) == getattr(r, f)


def test_swap_updates_reserves_and_fees():
    amm = pool()
    r = amm.swap(1_000, "sell_stable")
    assert set(r.__dataclass_fields__) == QUOTE_FIELDS | {
        "reserve_stable_after",
        "reserve_reference_after",
    }
    assert amm.reserve_stable == r.reserve_stable_after
    assert amm.reserve_reference == r.reserve_reference_after
    assert amm.cumulative_fees_stable == r.fee_paid
    assert amm.cumulative_fees_reference == 0.0


def test_fees_accrue_in_input_token():
    amm = pool()
    amm.swap(1_000, "sell_stable")
    assert math.isclose(amm.cumulative_fees_stable, 3.0, rel_tol=1e-9)
    assert amm.cumulative_fees_reference == 0.0
    r = amm.swap(2_000, "buy_stable")
    assert math.isclose(amm.cumulative_fees_reference, r.fee_paid, rel_tol=1e-12)
    assert math.isclose(amm.cumulative_fees_stable, 3.0, rel_tol=1e-9)


def test_buy_stable_moves_spot_up():
    amm = pool()
    r = amm.swap(1_000, "buy_stable")
    assert r.spot_after > r.spot_before
    assert math.isclose(r.amount_out, 1_000_000 * 997 / 1_000_997, rel_tol=1e-12)
    assert math.isclose(r.execution_price, 1_000 / r.amount_out, rel_tol=1e-12)
    assert r.slippage > 0
    assert r.reserve_reference_after == 1_001_000.0


def test_zero_fee_round_trip_restores_pool():
    amm = pool(fee_bps=0)
    out = amm.swap(1_000, "sell_stable").amount_out
    amm.swap(out, "buy_stable")
    assert math.isclose(amm.reserve_stable, 1_000_000, rel_tol=1e-12)
    assert math.isclose(amm.reserve_reference, 1_000_000, rel_tol=1e-12)


# AC 5: invariant ---------------------------------------------------------------


def test_k_never_decreases_over_1000_seeded_swaps():
    c = ctx(seed=12345)
    amm = pool()
    k0 = amm.k
    for _ in range(1_000):
        side = "sell_stable" if c.rng.random() < 0.5 else "buy_stable"
        amount = float(c.rng.uniform(1, 10_000))
        k_before = amm.k
        amm.swap(amount, side)
        assert amm.k >= k_before
    assert amm.k > k0
    assert amm.cumulative_fees_stable > 0
    assert amm.cumulative_fees_reference > 0


def test_zero_fee_k_constant_to_float_precision():
    c = ctx(seed=7)
    amm = pool(fee_bps=0)
    k0 = amm.k
    for _ in range(200):
        side = "sell_stable" if c.rng.random() < 0.5 else "buy_stable"
        amm.swap(float(c.rng.uniform(1, 10_000)), side)
    assert math.isclose(amm.k, k0, rel_tol=1e-9)


# AC 6: spot and peg deviation ---------------------------------------------------


def test_fresh_pool_spot_and_deviation():
    amm = pool(rs=1_000_000, rr=2_000_000)
    assert amm.spot_price == 2.0
    assert pool().peg_deviation == 0.0


def test_deviation_negative_after_sell_positive_after_buy():
    a = pool()
    a.swap(10_000, "sell_stable")
    assert a.peg_deviation < 0
    b = pool()
    b.swap(10_000, "buy_stable")
    assert b.peg_deviation > 0


def test_deviation_uses_injected_peg_price():
    amm = pool(rs=1_000_000, rr=1_010_000, peg_price=1.01)
    assert math.isclose(amm.peg_deviation, 0.0, abs_tol=1e-15)
    amm2 = pool(peg_price=0.5)
    assert math.isclose(amm2.peg_deviation, 1.0, rel_tol=1e-12)


# AC 8: validation ---------------------------------------------------------------


@pytest.mark.parametrize("amount", [0, -5, 0.0, float("nan"), float("inf")])
def test_non_positive_amount_raises_amm_error(amount):
    with pytest.raises(AMMError, match="amount_in must be > 0"):
        pool().quote(amount, "sell_stable")


def test_unknown_side_raises_amm_error():
    with pytest.raises(AMMError, match="unknown side"):
        pool().swap(1, "sideways")


def test_drain_guard_rejects_without_mutating():
    amm = pool(fee_bps=0, rs=1.0, rr=1e-300)
    before = amm.snapshot()
    # out = 1e-300 * 1e300 / (1 + 1e300) rounds to exactly reserve_out in floats
    with pytest.raises(AMMError, match="would drain reserve_out"):
        amm.swap(1e300, "sell_stable")
    assert amm.snapshot() == before


@pytest.mark.parametrize("fee_bps", [-1, 10_000, 20_000])
def test_fee_bps_out_of_range_raises_value_error(fee_bps):
    with pytest.raises(ValueError, match="fee_bps"):
        pool(fee_bps=fee_bps)


@pytest.mark.parametrize("fee_bps", [0, 9_999])
def test_fee_bps_bounds_accepted(fee_bps):
    assert pool(fee_bps=fee_bps).fee_bps == fee_bps


@pytest.mark.parametrize(
    "kwargs", [{"rs": 0.0}, {"rr": -1.0}, {"peg_price": 0.0}], ids=["rs0", "rr-neg", "peg0"]
)
def test_invalid_construction_raises_value_error(kwargs):
    with pytest.raises(ValueError):
        pool(**kwargs)


# AC 2 / AC 10: contract ---------------------------------------------------------


def test_protocol_conformance():
    amm = pool()
    assert isinstance(amm, Subsystem)
    assert isinstance(amm, ActionTarget)
    assert isinstance(amm, PegView)
    assert not isinstance(amm, ActionSource)
    assert not isinstance(amm, ReservesView)


def test_name_and_phases():
    amm = pool()
    assert amm.name == "amm"
    assert amm.phases == frozenset({Phase.EXECUTION})


def test_snapshot_keys_and_values():
    amm = pool()
    amm.swap(1_000, "sell_stable")
    snap = amm.snapshot()
    assert set(snap) == {
        "reserve_stable",
        "reserve_reference",
        "fee_bps",
        "k",
        "spot_price",
        "cumulative_fees_stable",
        "cumulative_fees_reference",
    }
    assert "cumulative_fees" not in snap
    assert snap["k"] == amm.reserve_stable * amm.reserve_reference
    assert snap["spot_price"] == amm.spot_price
    assert snap["cumulative_fees_stable"] == 3.0
    assert snap["cumulative_fees_reference"] == 0.0
    assert snap["fee_bps"] == 30


def test_on_phase_is_noop():
    c = ctx()
    amm = pool()
    before = amm.snapshot()
    for phase in Phase:
        amm.on_phase(c, phase)
    assert amm.snapshot() == before
    assert len(c.events) == 0


# AC 11: from_config -----------------------------------------------------------


def test_from_config():
    cfg = make_config()
    amm = ConstantProductAMM.from_config(cfg.amm, peg_price=cfg.redemption.peg_price)
    assert amm.reserve_stable == cfg.amm.reserve_stable
    assert amm.reserve_reference == cfg.amm.reserve_reference
    assert amm.fee_bps == cfg.amm.fee_bps
    assert amm.peg_price == cfg.redemption.peg_price
    assert amm.name == "amm"


# AC 7: execute ----------------------------------------------------------------


def test_execute_swap_emits_swap_executed():
    c = ctx()
    amm = pool()
    res = amm.execute(c, swap_action(1_000, source="attacker-1"))
    assert isinstance(res, ExecutionResult) and res.ok
    (ev,) = events_of(c, "swap_executed")
    assert ev.source == "amm"
    assert ev.step == c.clock.step_index
    assert ev.payload == res.detail
    assert set(ev.payload) == {
        "source",
        "side",
        "amount_in",
        "amount_out",
        "execution_price",
        "spot_before",
        "spot_after",
        "slippage",
        "fee_paid",
        "reserve_stable",
        "reserve_reference",
    }
    assert ev.payload["source"] == "attacker-1"
    assert ev.payload["side"] == "sell_stable"
    assert math.isclose(ev.payload["amount_out"], 996.006981, rel_tol=1e-9)
    assert ev.payload["reserve_stable"] == amm.reserve_stable
    assert ev.payload["reserve_reference"] == amm.reserve_reference


def test_execute_unknown_kind_rejected():
    c = ctx()
    amm = pool()
    before = amm.snapshot()
    res = amm.execute(c, swap_action(1_000, kind="mint"))
    assert res.ok is False
    assert "unknown action kind" in res.detail["error"]
    (ev,) = events_of(c, "swap_rejected")
    assert ev.source == "amm"
    assert ev.payload == {
        "source": "trader",
        "side": "sell_stable",
        "amount_in": 1_000,
        "reason": res.detail["error"],
    }
    assert events_of(c, "swap_executed") == []
    assert amm.snapshot() == before


@pytest.mark.parametrize(
    ("amount", "side", "reason"),
    [
        (0, "sell_stable", "amount_in must be > 0"),
        (-5, "buy_stable", "amount_in must be > 0"),
        (1_000, "sideways", "unknown side"),
        (None, "sell_stable", "amount_in must be a number"),
        ("100", "sell_stable", "amount_in must be a number"),
        (True, "sell_stable", "amount_in must be a number"),
    ],
)
def test_execute_invalid_swap_rejected_not_raised(amount, side, reason):
    c = ctx()
    amm = pool()
    before = amm.snapshot()
    res = amm.execute(c, swap_action(amount, side=side))
    assert res.ok is False
    assert reason in res.detail["error"]
    (ev,) = events_of(c, "swap_rejected")
    assert ev.payload["reason"] == res.detail["error"]
    assert ev.payload["amount_in"] == amount
    assert ev.payload["side"] == side
    assert amm.snapshot() == before


def test_execute_drain_rejected():
    c = ctx()
    amm = pool(fee_bps=0, rs=1.0, rr=1e-300)
    res = amm.execute(c, swap_action(1e300))
    assert res.ok is False
    assert res.detail == {"error": "would drain reserve_out"}
    (ev,) = events_of(c, "swap_rejected")
    assert ev.payload["reason"] == "would drain reserve_out"


def test_execute_missing_params_rejected():
    c = ctx()
    res = pool().execute(c, Action(source="t", target="amm", kind="swap", params={}))
    assert res.ok is False
    (ev,) = events_of(c, "swap_rejected")
    assert ev.payload == {
        "source": "t",
        "side": None,
        "amount_in": None,
        "reason": "amount_in must be a number",
    }
