"""Story 3.8 AC 1: ``remove_liquidity`` on the constant-product AMM."""

import math

import pytest
from test_amm import ctx, events_of, pool, swap_action

from depeg_sim.kernel.interfaces import Action
from depeg_sim.protocol.amm import AMMError, LiquidityResult


def remove_action(fraction, source="lp-1"):
    return Action(
        source=source, target="amm", kind="remove_liquidity", params={"fraction": fraction}
    )


def test_both_reserves_scale_and_spot_is_unchanged():
    amm = pool(rs=1_200_000.0, rr=900_000.0)
    spot0, k0 = amm.spot_price, amm.k
    r = amm.remove_liquidity(0.25)
    assert isinstance(r, LiquidityResult)
    assert (r.stable_out, r.reference_out) == (300_000.0, 225_000.0)
    assert (amm.reserve_stable, amm.reserve_reference) == (900_000.0, 675_000.0)
    assert (r.reserve_stable_after, r.reserve_reference_after) == (900_000.0, 675_000.0)
    assert math.isclose(amm.spot_price, spot0, rel_tol=1e-15)
    assert math.isclose(amm.k, k0 * 0.75**2, rel_tol=1e-15)


@pytest.mark.parametrize("fractions", [(0.1,), (0.5, 0.5), (0.1, 0.2, 0.3, 0.9), (1e-9, 0.999)])
def test_k_scales_by_the_square_of_what_remains(fractions):
    amm = pool(rs=1_000_000.0, rr=870_000.0)
    k0, spot0 = amm.k, amm.spot_price
    remains = 1.0
    for f in fractions:
        amm.remove_liquidity(f)
        remains *= 1 - f
    assert math.isclose(amm.k, k0 * remains**2, rel_tol=1e-12)
    assert math.isclose(amm.lp_supply, remains, rel_tol=1e-12)
    assert math.isclose(amm.spot_price, spot0, rel_tol=1e-12)
    assert amm.liquidity_removals == len(fractions)


def test_a_swap_after_a_withdrawal_has_larger_impact():
    full, half = pool(), pool()
    half.remove_liquidity(0.5)
    a = full.swap(50_000, "sell_stable")
    b = half.swap(50_000, "sell_stable")
    assert b.spot_after < a.spot_after < 1.0
    assert b.slippage < a.slippage < 0
    assert b.amount_out < a.amount_out


def test_swap_path_unchanged_on_an_untouched_pool():
    # lp_supply is never read by a swap; an untouched pool's snapshot has no liquidity keys
    amm = pool()
    amm.swap(1_000, "sell_stable")
    assert "lp_supply" not in amm.snapshot() and amm.lp_supply == 1.0


def test_snapshot_gains_liquidity_fields_after_a_removal():
    amm = pool()
    amm.remove_liquidity(0.2)
    snap = amm.snapshot()
    assert snap["lp_supply"] == pytest.approx(0.8)
    assert snap["liquidity_removals"] == 1
    assert snap["reserve_stable"] == pytest.approx(800_000.0)


def test_full_withdrawal_hits_the_drain_guard():
    amm = pool()
    before = amm.snapshot()
    with pytest.raises(AMMError, match="would drain reserves"):
        amm.remove_liquidity(1.0)
    assert amm.snapshot() == before and amm.lp_supply == 1.0


@pytest.mark.parametrize("bad", [0, 0.0, -0.1, 1.0000001, 2, math.nan, math.inf, None, "0.5", True])
def test_invalid_fraction_raises_without_mutating(bad):
    amm = pool()
    before = amm.snapshot()
    with pytest.raises(AMMError):
        amm.remove_liquidity(bad)
    assert amm.snapshot() == before


def test_execute_emits_liquidity_removed():
    c = ctx()
    amm = pool()
    res = amm.execute(c, remove_action(0.1))
    assert res.ok
    (ev,) = events_of(c, "liquidity_removed")
    assert ev.source == "amm" and ev.step == c.clock.step_index
    assert ev.payload == res.detail
    assert set(ev.payload) == {
        "source",
        "fraction",
        "stable_out",
        "reference_out",
        "reserve_stable",
        "reserve_reference",
    }
    assert ev.payload["source"] == "lp-1" and ev.payload["fraction"] == 0.1
    assert ev.payload["stable_out"] == pytest.approx(100_000.0)
    assert ev.payload["reserve_reference"] == amm.reserve_reference
    assert events_of(c, "swap_executed") == events_of(c, "swap_rejected") == []


@pytest.mark.parametrize(
    ("fraction", "reason"),
    [
        (1.0, "would drain reserves"),
        (0, "fraction must be in (0, 1]"),
        (1.5, "fraction must be in (0, 1]"),
        (None, "fraction must be a number"),
        ("0.1", "fraction must be a number"),
    ],
)
def test_execute_rejects_and_emits_liquidity_rejected(fraction, reason):
    c = ctx()
    amm = pool()
    before = amm.snapshot()
    res = amm.execute(c, remove_action(fraction))
    assert res.ok is False and res.detail == {"error": reason}
    (ev,) = events_of(c, "liquidity_rejected")
    assert ev.payload == {"source": "lp-1", "fraction": fraction, "reason": reason}
    assert amm.snapshot() == before
    assert events_of(c, "swap_rejected") == []


def test_unknown_kinds_still_reject_as_swaps():
    c = ctx()
    res = pool().execute(c, swap_action(1_000, kind="add_liquidity"))
    assert res.ok is False and "unknown action kind" in res.detail["error"]
    assert len(events_of(c, "swap_rejected")) == 1
