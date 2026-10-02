import math

import numpy as np
import pytest
from kernel_stubs import make_config

from depeg_sim.kernel.config import RedemptionConfig
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
from depeg_sim.protocol.redemption import RedemptionModule, RedemptionRequest

SNAPSHOT_KEYS = {
    "reserves",
    "spread_bps",
    "capacity_per_step",
    "peg_price",
    "queue_depth",
    "queued_total",
    "fulfilled_total",
    "paid_total",
    "reserves_exhausted",
}


def module(reserves=1_000.0, spread_bps=10, capacity=100.0, peg_price=1.0):
    return RedemptionModule(
        reserves=reserves, spread_bps=spread_bps, capacity_per_step=capacity, peg_price=peg_price
    )


def ctx(seed=42):
    return RunContext.from_config(make_config(seed=seed))


def redeem(amount, source="redeemer", kind="redeem"):
    return Action(source=source, target="redemption", kind=kind, params={"amount_stable": amount})


def events_of(c, kind):
    return [e for e in c.events.all() if e.kind == kind]


def step(c, m):
    """Run one PROTOCOL_EVENTS settlement at the current step, then tick."""
    m.on_phase(c, Phase.PROTOCOL_EVENTS)
    c.clock.tick()


# AC 1: interfaces ---------------------------------------------------------------


def test_interfaces_and_phases():
    m = module()
    assert m.name == "redemption"
    assert m.phases == frozenset({Phase.EXECUTION, Phase.PROTOCOL_EVENTS})
    assert isinstance(m, Subsystem)
    assert isinstance(m, ActionTarget)
    assert isinstance(m, ReservesView)
    assert not isinstance(m, PegView)
    assert not isinstance(m, ActionSource)


def test_on_phase_execution_does_nothing():
    c, m = ctx(), module()
    m.execute(c, redeem(50.0))
    before = m.snapshot()
    n_events = len(c.events)
    m.on_phase(c, Phase.EXECUTION)
    assert m.snapshot() == before
    assert len(c.events) == n_events


# AC 2: execute -----------------------------------------------------------------


def test_redeem_queues_and_emits():
    c, m = ctx(), module()
    r = m.execute(c, redeem(100.0))
    assert r == ExecutionResult(ok=True, detail={"queued": 100.0, "queue_depth": 1})
    r2 = m.execute(c, redeem(25, source="other"))
    assert r2.detail == {"queued": 25.0, "queue_depth": 2}

    ev = events_of(c, "redeem_requested")
    assert [e.payload for e in ev] == [
        {"source": "redeemer", "amount_stable": 100.0, "queue_depth": 1},
        {"source": "other", "amount_stable": 25.0, "queue_depth": 2},
    ]
    assert all(e.source == "redemption" and e.step == 0 for e in ev)
    assert m.pending == [
        RedemptionRequest(source="redeemer", amount=100.0, remaining=100.0, step_requested=0),
        RedemptionRequest(source="other", amount=25.0, remaining=25.0, step_requested=0),
    ]
    assert m.queue_depth == 2
    assert m.queued_total == 125.0
    assert m.requested_total == 125.0
    assert m.reserves == 1_000.0  # queueing never pays


@pytest.mark.parametrize(
    "action, reason",
    [
        (redeem(-1.0), "amount_stable must be > 0"),
        (redeem(0.0), "amount_stable must be > 0"),
        (redeem(float("nan")), "amount_stable must be > 0"),
        (redeem(float("inf")), "amount_stable must be > 0"),
        (redeem(True), "amount_stable must be a number"),
        (redeem("10"), "amount_stable must be a number"),
        (Action(source="x", target="redemption", kind="redeem", params={}), None),
        (redeem(10.0, kind="swap"), "unknown action kind 'swap'"),
    ],
)
def test_invalid_requests_rejected(action, reason):
    c, m = ctx(), module()
    before = m.snapshot()
    r = m.execute(c, action)
    assert r.ok is False
    rej = events_of(c, "redeem_rejected")
    assert len(rej) == 1
    assert rej[0].payload["source"] == action.source
    if reason is not None:
        assert rej[0].payload["reason"] == reason
        assert r.detail == {"error": reason}
    assert events_of(c, "redeem_requested") == []
    assert m.snapshot() == before


# AC 10: construction -------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reserves": -1.0},
        {"reserves": float("nan")},
        {"spread_bps": -1},
        {"spread_bps": 10_000},
        {"spread_bps": 10.5},
        {"capacity": 0.0},
        {"capacity": -5.0},
        {"peg_price": 0.0},
        {"peg_price": -1.0},
    ],
)
def test_construction_guards(kwargs):
    with pytest.raises(ValueError):
        module(**kwargs)


def test_boundary_values_accepted():
    m = module(reserves=0.0, spread_bps=0)
    assert m.payout_per_unit == 1.0
    assert module(spread_bps=9_999).payout_per_unit == pytest.approx(0.0001)


# AC 5, 9: properties, snapshot, from_config -----------------------------------------


def test_payout_per_unit():
    assert math.isclose(module(spread_bps=10).payout_per_unit, 0.999, rel_tol=1e-15)
    assert math.isclose(module(spread_bps=50, peg_price=2.0).payout_per_unit, 1.99, rel_tol=1e-15)


def test_snapshot_keys_and_values():
    c, m = ctx(), module()
    m.execute(c, redeem(150.0))
    step(c, m)
    s = m.snapshot()
    assert set(s) == SNAPSHOT_KEYS
    assert s["capacity_per_step"] == 100.0
    assert s["queue_depth"] == 1
    assert s["queued_total"] == 50.0
    assert s["fulfilled_total"] == 100.0
    assert math.isclose(s["paid_total"], 99.9, rel_tol=1e-12)
    assert math.isclose(s["reserves"], 1_000.0 - 99.9, rel_tol=1e-12)
    assert s["reserves_exhausted"] is False


def test_from_config():
    cfg = RedemptionConfig(reserves=500.0, spread_bps=25, capacity_per_step=10.0, peg_price=1.5)
    m = RedemptionModule.from_config(cfg)
    assert (m.name, m.reserves, m.spread_bps, m.capacity_per_step, m.peg_price) == (
        "redemption",
        500.0,
        25,
        10.0,
        1.5,
    )
    baseline = make_config().redemption
    assert RedemptionModule.from_config(baseline).reserves == baseline.reserves


# AC 5: spread lever --------------------------------------------------------------


def test_set_spread_changes_future_payouts_only():
    c, m = ctx(), module(spread_bps=10, capacity=100.0)
    m.execute(c, redeem(200.0))
    step(c, m)
    paid_before = m.paid_total
    assert math.isclose(paid_before, 99.9, rel_tol=1e-12)

    m.set_spread_bps(c, 50, source="defender")
    ev = events_of(c, "spread_changed")
    assert len(ev) == 1
    assert ev[0].payload == {"old": 10, "new": 50, "source": "defender"}
    assert ev[0].step == 1
    assert m.spread_bps == 50
    assert math.isclose(m.payout_per_unit, 0.995, rel_tol=1e-15)
    assert m.paid_total == paid_before  # history untouched

    step(c, m)
    fills = events_of(c, "redeem_fulfilled")
    assert math.isclose(fills[0].payload["paid_reference"], 99.9, rel_tol=1e-12)
    assert math.isclose(fills[1].payload["paid_reference"], 99.5, rel_tol=1e-12)
    assert m.paid_total == fills[0].payload["paid_reference"] + fills[1].payload["paid_reference"]
    assert m.snapshot()["spread_bps"] == 50


def test_set_spread_default_source_and_guards():
    c, m = ctx(), module()
    m.set_spread_bps(c, 0)
    assert events_of(c, "spread_changed")[0].payload["source"] == "redemption"
    for bad in (-1, 10_000, 1.5):
        with pytest.raises(ValueError):
            m.set_spread_bps(c, bad)
    assert m.spread_bps == 0
    assert len(events_of(c, "spread_changed")) == 1


# AC 3, 7: FIFO and capacity -----------------------------------------------------------


def test_capacity_across_requests():
    c, m = ctx(), module(reserves=1_000_000.0, capacity=100.0)
    for src in ("a", "b", "c"):
        m.execute(c, redeem(60.0, source=src))

    step(c, m)  # step 0
    step(c, m)  # step 1
    step(c, m)  # step 2
    fills = [
        (e.step, e.payload["source"], e.payload["amount_stable"], e.payload["reason"])
        for e in events_of(c, "redeem_fulfilled")
    ]
    assert fills == [
        (0, "a", 60.0, "full"),
        (0, "b", 40.0, "partial_capacity"),
        (1, "b", 20.0, "full"),
        (1, "c", 60.0, "full"),
    ]
    remaining = [e.payload["remaining_request"] for e in events_of(c, "redeem_fulfilled")]
    assert remaining == [0.0, 20.0, 0.0, 0.0]
    assert m.queue_depth == 0
    assert m.fulfilled_total == 180.0
    assert m.reserves_exhausted is False


def test_partial_fill_stays_at_head():
    c, m = ctx(), module(reserves=1_000_000.0, capacity=100.0)
    m.execute(c, redeem(250.0, source="big"))
    m.execute(c, redeem(10.0, source="small"))
    step(c, m)
    assert [r.source for r in m.pending] == ["big", "small"]
    assert m.pending[0].remaining == 150.0
    assert m.pending[0].amount == 250.0
    step(c, m)
    step(c, m)
    srcs = [e.payload["source"] for e in events_of(c, "redeem_fulfilled")]
    assert srcs == ["big", "big", "big", "small"]


def test_fulfilled_event_payload():
    c, m = ctx(), module(reserves=1_000.0, capacity=100.0)
    m.execute(c, redeem(30.0))
    step(c, m)
    (e,) = events_of(c, "redeem_fulfilled")
    assert e.source == "redemption"
    assert set(e.payload) == {
        "source",
        "amount_stable",
        "paid_reference",
        "remaining_request",
        "step_requested",
        "reason",
    }
    assert e.payload["amount_stable"] == 30.0
    assert math.isclose(e.payload["paid_reference"], 29.97, rel_tol=1e-12)
    assert e.payload["reason"] == "full"
    assert math.isclose(m.reserves, 1_000.0 - 29.97, rel_tol=1e-12)


# AC 4, 8: reserves limit and exhaustion -------------------------------------------------


def test_reserves_limit_and_exhaustion():
    c, m = ctx(), module(reserves=50.0, spread_bps=10, capacity=1_000.0)
    m.execute(c, redeem(100.0))
    step(c, m)

    (fill,) = events_of(c, "redeem_fulfilled")
    assert math.isclose(fill.payload["amount_stable"], 50 / 0.999, rel_tol=1e-12)
    assert fill.payload["reason"] == "partial_reserves"
    assert fill.payload["paid_reference"] == 50.0
    assert m.reserves == 0.0
    assert m.reserves_exhausted is True
    assert m.queue_depth == 1
    assert math.isclose(m.queued_total, 100.0 - 50 / 0.999, rel_tol=1e-12)

    (ex,) = events_of(c, "reserves_exhausted")
    assert ex.step == 0
    assert ex.payload == {
        "step": 0,
        "reserves": 0.0,
        "queue_depth": 1,
        "queued_total": m.queued_total,
    }

    # Latches; no second event, no further fills.
    m.execute(c, redeem(10.0))
    step(c, m)
    step(c, m)
    assert m.reserves_exhausted is True
    assert len(events_of(c, "reserves_exhausted")) == 1
    assert len(events_of(c, "redeem_fulfilled")) == 1


def test_empty_reserves_empty_queue_is_not_exhaustion():
    c, m = ctx(), module(reserves=0.0)
    step(c, m)
    step(c, m)
    assert m.reserves_exhausted is False
    assert events_of(c, "reserves_exhausted") == []

    # Demand arriving later against empty reserves is exhaustion.
    m.execute(c, redeem(1.0))
    step(c, m)
    assert m.reserves_exhausted is True
    assert events_of(c, "reserves_exhausted")[0].step == 2
    assert events_of(c, "redeem_fulfilled") == []


def test_spending_everything_with_nothing_left_queued_is_not_exhaustion():
    # reserves exactly cover the request: full fill, reserves 0, queue empty.
    c, m = ctx(), module(reserves=99.9, spread_bps=10, capacity=1_000.0)
    m.execute(c, redeem(100.0))
    step(c, m)
    (fill,) = events_of(c, "redeem_fulfilled")
    assert fill.payload["reason"] == "full"
    assert m.reserves == pytest.approx(0.0, abs=1e-9)
    assert m.queue_depth == 0
    assert m.reserves_exhausted is False


def test_exhaustion_waits_until_queue_non_empty_after_full_drain():
    c, m = ctx(), module(reserves=99.9, spread_bps=10, capacity=1_000.0)
    m.execute(c, redeem(100.0))
    step(c, m)
    m.execute(c, redeem(5.0))
    step(c, m)
    assert m.reserves_exhausted is True
    assert [e.step for e in events_of(c, "reserves_exhausted")] == [1]


def test_settlement_never_raises_on_extreme_values():
    c, m = ctx(), module(reserves=1e-300, spread_bps=9_999, capacity=1e-300)
    m.execute(c, redeem(1e300))
    for _ in range(3):
        step(c, m)
    assert m.fulfilled_total + m.queued_total == pytest.approx(m.requested_total)


# AC 6: accounting invariant over a randomised run ----------------------------------------


def test_accounting_invariant_random_run():
    rng = np.random.default_rng(99)
    c, m = ctx(), module(reserves=50_000.0, spread_bps=10, capacity=1_000.0)
    paid_per_fill = 0.0
    seen = 0
    for i in range(200):
        for _ in range(int(rng.integers(0, 4))):
            m.execute(c, redeem(float(rng.uniform(1.0, 800.0)), source=f"a{i}"))
        if i == 100:
            m.set_spread_bps(c, 75, source="test")
        step(c, m)

        fills = events_of(c, "redeem_fulfilled")
        for e in fills[seen:]:
            paid_per_fill += e.payload["paid_reference"]
        seen = len(fills)

        assert math.isclose(
            m.fulfilled_total + m.queued_total, m.requested_total, rel_tol=0, abs_tol=1e-9
        )
        assert m.paid_total == paid_per_fill
        assert math.isclose(m.reserves + m.paid_total, 50_000.0, rel_tol=0, abs_tol=1e-9)
        assert m.reserves >= 0.0

    # Each fill paid at the spread in force at its own step.
    for e in events_of(c, "redeem_fulfilled"):
        ppu = 0.999 if e.step <= 100 else 0.9925
        assert math.isclose(e.payload["paid_reference"], e.payload["amount_stable"] * ppu)
    # The run exercised all three reasons and exhaustion.
    reasons = {e.payload["reason"] for e in events_of(c, "redeem_fulfilled")}
    assert reasons == {"full", "partial_capacity", "partial_reserves"}
    assert len(events_of(c, "reserves_exhausted")) == 1
