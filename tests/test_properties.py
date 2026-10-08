"""Story 3.5 AC 5: property-style tests over random sequences from a seeded Generator.

No property-testing library: each case is a plain parametrised seed, so a failure names
the seed and reruns identically.
"""

import math

import numpy as np
import pytest
from kernel_stubs import PegStub, make_config
from test_reference_recovery import RefStub, term

from depeg_sim.kernel.context import RunContext
from depeg_sim.kernel.engine import Engine
from depeg_sim.kernel.interfaces import Action
from depeg_sim.protocol.amm import BUY_STABLE, SELL_STABLE, ConstantProductAMM
from depeg_sim.protocol.redemption import RedemptionModule

SEEDS = range(20)


# -- AMM: k never decreases between liquidity events --------------------------------------


@pytest.mark.parametrize("fee_bps", [0, 4, 30, 100])
@pytest.mark.parametrize("seed", SEEDS)
def test_amm_k_non_decreasing_between_liquidity_events(seed, fee_bps):
    """Random swaps with random liquidity removals mixed in (Story 3.8): across a swap ``k``
    never decreases; across a removal of ``f`` it scales by exactly ``(1 - f)**2`` and spot
    is unchanged. The swap draws come first in each iteration, so the swap sequence is the
    one this test drew before removals existed."""
    rng = np.random.default_rng(seed)
    amm = ConstantProductAMM(
        reserve_stable=1_000_000.0, reserve_reference=1_000_000.0, fee_bps=fee_bps
    )
    removal_rng = np.random.default_rng(10_000 + seed)
    for _ in range(300):
        if removal_rng.random() < 0.05:
            f = float(10 ** removal_rng.uniform(-6, math.log10(0.5)))
            k0, spot0 = amm.k, amm.spot_price
            amm.remove_liquidity(f)
            assert math.isclose(amm.k, k0 * (1 - f) ** 2, rel_tol=1e-12)
            assert math.isclose(amm.spot_price, spot0, rel_tol=1e-12)
        side = SELL_STABLE if rng.random() < 0.5 else BUY_STABLE
        r_in = amm.reserve_stable if side == SELL_STABLE else amm.reserve_reference
        # sizes from dust to half the input reserve, log-uniform
        amount = r_in * 10 ** rng.uniform(-9, math.log10(0.5))
        k0, rs0, rr0 = amm.k, amm.reserve_stable, amm.reserve_reference
        r = amm.swap(amount, side)
        if fee_bps:
            assert amm.k >= k0
        else:  # fee-free: k is constant up to float rounding of the product
            assert amm.k >= k0 * (1 - 1e-12)
        assert amm.reserve_stable > 0 and amm.reserve_reference > 0
        assert 0 < r.amount_out < (rr0 if side == SELL_STABLE else rs0)
        if side == SELL_STABLE:
            assert amm.reserve_stable == rs0 + amount and amm.spot_price < rr0 / rs0
        else:
            assert amm.reserve_reference == rr0 + amount and amm.spot_price > rr0 / rs0


# -- Redemption: every request is paid, queued or rejected --------------------------------

INVALID = (0.0, -5.0, float("nan"), float("inf"), "10", True, None)


def _request(rng, step):
    """A random request: mostly valid, sometimes a bad amount, sometimes a bad kind."""
    u = rng.random()
    if u < 0.15:
        bad = INVALID[int(rng.integers(len(INVALID)))]
        return Action(source="r", target="redemption", kind="redeem",
                      params={"amount_stable": bad})  # fmt: skip
    amount = float(10 ** rng.uniform(-3, 3))
    kind = "redeem" if u < 0.95 else "withdraw"  # unknown kind: rejected with its amount
    src = f"agent-{int(rng.integers(3))}"
    return Action(source=src, target="redemption", kind=kind, params={"amount_stable": amount})


def _drive(seed, on_step=None):
    """120 steps of random requests against a random redemption channel; ``on_step``
    runs after each step's ``process`` with the running tallies."""
    rng = np.random.default_rng(seed)
    reserves0 = float(rng.uniform(500, 20_000))
    red = RedemptionModule(
        reserves=reserves0,
        spread_bps=int(rng.integers(0, 200)),
        capacity_per_step=float(rng.uniform(5, 200)),
    )
    ctx = RunContext.from_config(make_config(max_steps=1_000))
    t = {"reserves0": reserves0, "positive": 0.0, "rejected_positive": 0.0, "rejected": 0}
    for step in range(120):
        ctx.clock.step_index = step
        for _ in range(int(rng.integers(0, 4))):
            a = _request(rng, step)
            amt = a.params["amount_stable"]
            res = red.execute(ctx, a)
            positive = isinstance(amt, float) and math.isfinite(amt) and amt > 0
            t["positive"] += amt if positive else 0.0
            if not res.ok:
                t["rejected"] += 1
                t["rejected_positive"] += amt if positive else 0.0
        before = red.fulfilled_total
        red.process(ctx)
        t["filled_this_step"] = red.fulfilled_total - before
        if on_step:
            on_step(red, t)
    return red, ctx, t


@pytest.mark.parametrize("seed", SEEDS)
def test_redemption_accounting_over_random_requests(seed):
    def check(red, t):
        assert t["filled_this_step"] <= red.capacity_per_step * (1 + 1e-12)
        # requested = paid (fulfilled) + queued + rejected, in stable units
        assert red.requested_total == pytest.approx(red.fulfilled_total + red.queued_total)
        assert t["positive"] == pytest.approx(
            red.fulfilled_total + red.queued_total + t["rejected_positive"]
        )
        # reference out of reserves is exactly what was paid
        assert red.reserves >= 0
        assert red.reserves + red.paid_total == pytest.approx(t["reserves0"], rel=1e-12)

    red, ctx, t = _drive(seed, check)
    events = ctx.events.all()
    fills = [e for e in events if e.kind == "redeem_fulfilled"]
    assert sum(e.payload["amount_stable"] for e in fills) == pytest.approx(red.fulfilled_total)
    assert sum(e.payload["paid_reference"] for e in fills) == pytest.approx(red.paid_total)
    assert sum(e.kind == "redeem_rejected" for e in events) == t["rejected"]


def test_random_requests_reach_both_limits():
    """The sequences above are not all easy: some exhaust the reserves, some fill
    partially against the per-step capacity."""
    exhausted = capacity_limited = 0
    for seed in SEEDS:
        red, ctx, _ = _drive(seed)
        reasons = {e.payload["reason"] for e in ctx.events.all() if e.kind == "redeem_fulfilled"}
        exhausted += red.reserves_exhausted
        capacity_limited += "partial_capacity" in reasons
    assert exhausted >= 2 and capacity_limited >= 10


# -- Termination: both criteria at their edges --------------------------------------------

IN, OUT = 0.0005, 0.01  # within / outside the 10 bps tolerance of term()


def _run(reference, deviations, *, for_steps, max_steps=50, published=1.0):
    ctx = RunContext.from_config(
        make_config(max_steps=max_steps, termination=term(reference, for_steps, 0.001))
    )
    ctx.registry.register(PegStub(deviations))
    if published is not None:
        ctx.registry.register(RefStub(published=published))
    return ctx, Engine(ctx).run()


@pytest.mark.parametrize("reference", ["par", "oracle"])
@pytest.mark.parametrize("for_steps", [1, 3, 7])
def test_exactly_for_steps_in_band_recovers(reference, for_steps):
    # out for 4 steps, then in band from step 4 on: recovered at step 4 + for_steps - 1
    ctx, result = _run(reference, [OUT] * 4 + [IN], for_steps=for_steps)
    assert result.terminated_by == "peg_recovered"
    assert result.steps_run == 4 + for_steps
    assert ctx.term_state.consecutive_in_band == for_steps


@pytest.mark.parametrize("reference", ["par", "oracle"])
@pytest.mark.parametrize("for_steps", [2, 3, 7])
def test_one_step_short_does_not_recover(reference, for_steps):
    # in band for for_steps - 1 steps, out once, repeated until max_steps
    block = [IN] * (for_steps - 1) + [OUT]
    ctx, result = _run(reference, block * 20, for_steps=for_steps, max_steps=len(block) * 20)
    assert result.terminated_by == "max_steps"
    assert ctx.term_state.consecutive_in_band == 0  # the last step is the excursion


@pytest.mark.parametrize("for_steps", [2, 3, 7])
def test_one_step_short_at_the_horizon_does_not_recover(for_steps):
    # the run ends (max_steps) one step before the in-band stretch would complete
    ctx, result = _run("par", [OUT] * 4 + [IN], for_steps=for_steps, max_steps=4 + for_steps - 1)
    assert result.terminated_by == "max_steps"
    assert ctx.term_state.consecutive_in_band == for_steps - 1


def test_oracle_criterion_with_no_oracle_registered_never_recovers():
    # spot exactly at par every step: par recovers at for_steps; oracle never does
    _, par = _run("par", [0.0], for_steps=3, published=None)
    assert (par.terminated_by, par.steps_run) == ("peg_recovered", 3)
    ctx, ora = _run("oracle", [0.0], for_steps=3, published=None)
    assert (ora.terminated_by, ora.steps_run) == ("max_steps", 50)
    assert ctx.term_state.consecutive_in_band == 0
